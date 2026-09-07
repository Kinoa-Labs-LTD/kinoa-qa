# testops-sync.md — Step E (writes; only after the human gate)

Uses the Allure TestOps MCP. `project_id` from `config.json` (resolve once via
`testops_find_projects`/`testops_get_project` on `project_name` "KINOA" and cache it).

For each `### TC-<n>` case, build the body with `scripts/testops_payload.py`
`case_to_payload(case, story=…, service=…, capability=…, jira_base_url=…)` — this yields
`name, description, precondition, expectedResult, scenario.steps[], tags[], links[]`, and
the `tp-<slug>` traceability tag inside `tags`.

## Idempotent upsert (per case)
1. `ttag = testops_payload.traceability_tag(story, service, capability, source, title)` — `title` = the case's TC title; required so two cases citing the same `source` scenario (functional + negative) don't collide onto one TestOps case.
2. `testops_find_testcases(projectId, aql='tags = "<ttag>"', expand=["tags"])`.
3. **Found (≥1):** `testops_update_testcase(id=<first hit id>, **payload)`.
   **None:** `testops_create_testcase(projectId=<pid>, **payload)`.
4. Take the returned case id → write `@allure.id=<id>` back into the `test-plan.md` case
   header comment (so the file records the TestOps link).

Because the key is a stable tag (not the title), re-running a Story updates in place —
0 duplicates. A partial failure needs no rollback: re-run resumes (found→update the
landed ones, create the rest).

## `--dry-run`
Do NOT call create/update. Instead print, per case: the intended action
(create|update), the `ttag`, and the payload `name` — the QA preview of Step E.

## Degradation
- TestOps unreachable → the reviewed `test-plan.md` is already on disk; stop and tell the
  QA engineer to re-run Step E later. Nothing is lost.
- `priority` has no first-class TestOps field → it rides as a `priority-<p>` tag. If
  `testops_get_project(expand=["custom_fields"])` shows a Severity custom field, ALSO set
  it via `customFields:[{name:"Severity", value:<critical|normal|minor>}]` (P1→critical,
  P2→normal, P3→minor).
