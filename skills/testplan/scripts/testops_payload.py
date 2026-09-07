"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body, plus the
deterministic traceability tag used as the idempotency key. stdlib-only, no network."""
import re

PRIORITY_TAG = {"P1": "priority-p1", "P2": "priority-p2", "P3": "priority-p3"}


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def traceability_tag(story, service, capability, source):
    """Deterministic, AQL-matchable tag identifying one case across re-runs."""
    parts = [p for p in (story, service, capability, source) if p]
    return "tp-" + slugify("-".join(parts))


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
    ttag = traceability_tag(story, service or "", capability or "", tags.get("source", ""))
    return {
        "name": f"{case['id']} · {case['title']}",
        "description": f"source: {tags.get('source', '')}\ntraceability: {ttag}\nstory: {story}",
        "precondition": tags.get("preconditions", ""),
        "expectedResult": tags.get("expected", ""),
        "scenario": {"steps": [{"type": "body", "body": _strip_num(s)} for s in case["steps"]]},
        "tags": _dedupe([
            "spec-derived",
            f"type-{slugify(tags.get('type', ''))}",
            PRIORITY_TAG.get(tags.get("priority", ""), "priority-unset"),
            ttag,
        ]),
        "links": [{"name": story, "url": f"{jira_base_url.rstrip('/')}/browse/{story}"}],
    }
