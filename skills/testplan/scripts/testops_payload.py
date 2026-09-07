"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body, plus the
deterministic traceability tag used as the idempotency key. stdlib-only, no network."""
import re

PRIORITY_TAG = {"P1": "priority-p1", "P2": "priority-p2", "P3": "priority-p3"}


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def traceability_tag(story, service, capability, source, title=""):
    """Deterministic, AQL-matchable tag identifying ONE case across re-runs.

    Includes `title` so multiple cases sharing one `source` scenario (e.g. a
    functional + a negative case on the same scenario, which the QA lens
    deliberately produces) get DISTINCT tags — otherwise they collide and the
    idempotent upsert overwrites one with the other. Trade-off: a reworded title
    yields a new tag (new TestOps case + an orphan), which the human gate /
    --dry-run surfaces — acceptable vs. silent case loss. Fields are slugified
    after joining, so boundary shifts across the fixed, small-cardinality
    (story, service, capability) taxonomy values are not disambiguated; safe
    given those come from the repo/Jira taxonomy, not free text.
    """
    parts = [p for p in (story, service, capability, source, title) if p]
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
    ttag = traceability_tag(story, service or "", capability or "", tags.get("source", ""), case.get("title", ""))
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
