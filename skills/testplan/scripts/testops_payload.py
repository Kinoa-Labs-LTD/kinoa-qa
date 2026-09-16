"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body. Case
identity is the Allure case id assigned on first creation and carried in the plan as
`allure-id:` — never a value derived from the case's content. stdlib-only, no network."""
import re

# Every created case is a Draft in the manual workflow; `testLayer` is never sent.
STATUS = "Draft"
WORKFLOW = "Manual Kinoa"
ISSUE_INTEGRATION = "Kinoa-Allure"


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


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


def _description(case, tags, marker):
    """The case's one-sentence purpose, plus a one-line provenance suffix when the plan
    carries an `openspec-ref:` or `design-ref:`. The tags that used to carry provenance are
    retired, so this line is their only route into TestOps. The target marker is always last."""
    purpose = (case.get("tags", {}).get("purpose") or "").strip()
    refs = [f"{k}: {tags[k].strip()}" for k in ("openspec-ref", "design-ref")
            if (tags.get(k) or "").strip()]
    lines = [l for l in (purpose, "Provenance: " + "; ".join(refs) if refs else "", marker) if l]
    return "\n".join(lines)


TARGET_PREFIX = "Target: "
# Both halves may be empty: a run with no `--target` emits `Target: service=; capability=`
# and that marker must still parse, or its cases become invisible to reconciliation.
_TARGET_RE = re.compile(r"^Target:\s*service=([^;]*);\s*capability=(.*)$", re.M)


def target_marker(service, capability):
    """The description's last line: the `--target` this plan was written for. `issue = "<KEY>"`
    returns every target's cases, so reconciliation needs this to narrow. Both halves are
    slugified so the marker is a stable machine key, not free text."""
    return f"{TARGET_PREFIX}service={slugify(service or '')}; capability={slugify(capability or '')}"


def parse_target(description):
    """Read a target marker back out of a case description, as `(service, capability)`.
    Returns None when there is no marker — such a case was not written by this plugin under
    this format and must never be treated as a reconciliation match. An empty half is a
    value, not an absence: ('', '') is the target of a run invoked without `--target`."""
    if not description:
        return None
    m = _TARGET_RE.search(description)
    return (m.group(1).strip(), m.group(2).strip()) if m else None


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
    the resolver. No `links`, no `testLayer`, no tags beyond `qa-generated` — identity is the
    assigned Allure case id, not a tag."""
    if not (story or "").strip():
        raise ValueError(
            "story must be a Jira key — `issues` is the only way to find a case whose "
            "assigned allure-id was lost, so a payload is never emitted without it")
    tags = case["tags"]
    return {
        "name": case["title"],
        "description": _description(case, tags, target_marker(service, capability)),
        "precondition": tags.get("preconditions", ""),
        "expectedResult": tags.get("expected", ""),
        "status": STATUS,
        "workflow": WORKFLOW,
        "issues": [{"name": ISSUE_INTEGRATION, "value": story.strip()}],
        "customFields": _custom_fields(custom_fields),
        "scenario": {"steps": [_step_payload(s) for s in case["steps"]]},
        "tags": _dedupe(["qa-generated"]),
    }
