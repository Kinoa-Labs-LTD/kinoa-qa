"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body, plus the
deterministic traceability tag used as the idempotency key. stdlib-only, no network."""
import re
import hashlib

# Every created case is a Draft in the manual workflow; `testLayer` is never sent.
STATUS = "Draft"
WORKFLOW = "Manual Kinoa"
ISSUE_INTEGRATION = "Kinoa-Allure"


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def traceability_tag(story, service, capability, source, title="", case_type=""):
    """Deterministic, AQL-matchable, LENGTH-BOUNDED tag identifying ONE case across re-runs.

    A readable, capped prefix (story/service/capability) + a short deterministic hash of
    the FULL key (story|service|capability|source|title|case_type). The hash:
      - keeps the tag bounded — Allure tag names are a bounded field; an over-long tag
        could be truncated/rejected on write, so a re-run's full-length AQL match would
        miss it -> a duplicate create, breaking the "0 duplicates on re-run" invariant;
      - guarantees per-case uniqueness — a functional + a negative case on one scenario
        differ by title and/or type, so they never collide onto one TestOps case;
      - is robust to non-ASCII (e.g. Cyrillic) source/title text that slugify flattens.
    Do NOT fold in the TC-n id — it renumbers across runs and would break cross-run stability.
    """
    full_key = "|".join([story or "", service or "", capability or "", source or "", title or "", case_type or ""])
    prefix = slugify("-".join([p for p in (story, service, capability) if p]))[:80]
    digest = hashlib.sha1(full_key.encode("utf-8")).hexdigest()[:10]
    return "tp-" + (prefix + "-" if prefix else "") + digest


def _strip_num(step):
    """Action text of a step. Accepts a parsed `{action, ...}` step or a bare numbered line."""
    text = step["action"] if isinstance(step, dict) else step
    return re.sub(r"^\d+\.\s*", "", text).strip()


CUSTOM_FIELD_ORDER = ("Suite", "Story", "Component", "Feature")


def _dedupe(items):
    out = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out


def _description(case, tags):
    """The case's one-sentence purpose, plus a one-line provenance suffix when the plan
    carries an `openspec-ref:` or `design-ref:`. The tags that used to carry provenance are
    retired and `tp-` is an opaque hash, so this line is its only route into TestOps."""
    purpose = (case.get("tags", {}).get("purpose") or "").strip()
    refs = [f"{k}: {tags[k].strip()}" for k in ("openspec-ref", "design-ref")
            if (tags.get(k) or "").strip()]
    if not refs:
        return purpose
    suffix = "Provenance: " + "; ".join(refs)
    return f"{purpose}\n{suffix}" if purpose else suffix


def _step_payload(step):
    """One `body` step with its expected results as `expected_body` blocks. The validator
    already rejects a step with no expected result; if one is handed over anyway the step is
    emitted without `expectedResultSteps` rather than with an empty or null block."""
    expected = []
    if isinstance(step, dict):
        if step.get("expected"):
            expected.append(step["expected"])
        expected += [e for e in (step.get("extra_expected") or []) if e]
    out = {"type": "body", "body": _strip_num(step)}
    if expected:
        out["expectedResultSteps"] = [{"type": "expected_body", "body": e} for e in expected]
    return out


def _custom_fields(custom_fields):
    """Shape the four already-resolved, already-verified values into the reference's
    {name, value} list, in the reference's order. A value the resolver reported missing must
    never reach a payload, so an absent or blank one is a build-time error, not a guess."""
    values = custom_fields or {}
    out = []
    for name in CUSTOM_FIELD_ORDER:
        value = (values.get(name) or "").strip() if isinstance(values.get(name), str) else ""
        if not value:
            raise ValueError(
                f"custom field {name} has no value — resolve and verify all of "
                f"{', '.join(CUSTOM_FIELD_ORDER)} before building a payload")
        out.append({"name": name, "value": value})
    return out


def case_to_payload(case, *, story, service, capability, custom_fields):
    """Shared TestOps create/update body. Caller adds projectId (create) or id (update).
    `story` is the Jira key, linked via `issues`; `custom_fields` are the four values from
    the resolver. No `links`, no `testLayer`, no tags beyond `tp-` and `qa-generated`."""
    tags = case["tags"]
    ttag = traceability_tag(story, service or "", capability or "", tags.get("source", ""), case.get("title", ""), tags.get("type", ""))
    return {
        "name": case["title"],
        "description": _description(case, tags),
        "precondition": tags.get("preconditions", ""),
        "expectedResult": tags.get("expected", ""),
        "status": STATUS,
        "workflow": WORKFLOW,
        "issues": [{"name": ISSUE_INTEGRATION, "value": story}],
        "customFields": _custom_fields(custom_fields),
        "scenario": {"steps": [_step_payload(s) for s in case["steps"]]},
        "tags": _dedupe(["qa-generated", ttag]),
    }
