"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body, plus the
deterministic traceability tag used as the idempotency key. stdlib-only, no network."""
import re
import hashlib

PRIORITY_TAG = {"P1": "priority-p1", "P2": "priority-p2", "P3": "priority-p3"}


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
    return re.sub(r"^\d+\.\s*", "", step).strip()


def _dedupe(items):
    out = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out


def case_to_payload(case, *, story, service, capability, jira_base_url):
    """Shared TestOps create/update body. Caller adds projectId (create) or id (update)."""
    tags = case["tags"]
    ttag = traceability_tag(story, service or "", capability or "", tags.get("source", ""), case.get("title", ""), tags.get("type", ""))
    openspec_ref = tags.get("openspec-ref", "")
    design_ref = tags.get("design-ref", "")
    desc = [f"source: {tags.get('source', '')}"]
    if openspec_ref:
        desc.append(f"openspec-ref: {openspec_ref}")
    if design_ref:
        desc.append(f"design-ref: {design_ref}")
    desc += [f"traceability: {ttag}", f"story: {story}"]
    return {
        "name": f"{case['id']} · {case['title']}",
        "description": "\n".join(desc),
        "precondition": tags.get("preconditions", ""),
        "expectedResult": tags.get("expected", ""),
        "scenario": {"steps": [{"type": "body", "body": _strip_num(s)} for s in case["steps"]]},
        "tags": _dedupe([
            "qa-generated",
            "openspec-context" if openspec_ref else "",
            "design-backed" if design_ref else "",
            f"type-{slugify(tags.get('type', ''))}",
            PRIORITY_TAG.get(tags.get("priority", ""), "priority-unset"),
            ttag,
        ]),
        "links": [{"name": story, "url": f"{jira_base_url.rstrip('/')}/browse/{story}"}],
    }
