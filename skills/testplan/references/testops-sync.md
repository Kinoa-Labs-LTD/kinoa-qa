# testops-sync.md — Step E (writes; only after the human gate)

Uses the Allure TestOps MCP. `project_id` from `config.json` (resolve once via
`testops_get_project` on `project_name` "KINOA" and cache it).

## Gate 0 — re-run the validator before any write

Step E starts by re-running `scripts/validate_test_plan.py` on the reviewed
`test-plan.md` (the human may have edited it at the Step D gate):

- **exit 0 (PASS)** → proceed with the upsert.
- **exit 1 (FAIL)** → abort; report the failing checks. Nothing is written.
- **exit 2 (HOLD)** → **abort**. The plan is structurally valid but carries unresolved
  `## Conflicts` lines. Name every unresolved conflict from the report's
  `unresolved_conflicts` back to the QA engineer and tell them to annotate each one
  `→ resolved: <business wins | spec wins, AC updated>` in the file and re-run Step C.
  A contradicted acceptance criterion has no case yet, so upserting a HOLD plan would
  push a knowingly incomplete suite. No case is created or updated.

For each `### TC-<n>` case, build the body with `scripts/testops_payload.py`
`case_to_payload(case, story=…, service=…, capability=…, jira_base_url=…)` — this yields
`name, description, precondition, expectedResult, scenario.steps[], tags[], links[]`, and
the `tp-<slug>` traceability tag inside `tags`.

## Tag vocabulary

| tag | when |
|---|---|
| `qa-generated` | **always** — every plugin-authored case is business-sourced |
| `openspec-context` | only when the case carries an `openspec-ref:` |
| `design-backed` | only when the case carries a `design-ref:` |
| `type-<type>` | always, from the case's `type:` |
| `priority-<p>` | always, from the case's `priority:` |
| `tp-<slug>-<digest>` | always — the traceability tag / idempotency key |

A case may carry both `openspec-context` and `design-backed`, or neither. The old
unconditional `spec-derived` tag is **retired**: no payload emits it, and no AQL filter
should be written against it.

`## Gaps` and `## Conflicts` lines are never pushed to TestOps.

## Idempotent upsert (per case)
1. `ttag = testops_payload.traceability_tag(story, service, capability, source, title, case_type)` — `title` = the case's TC title, `case_type` = the case's `type:` field; required so two cases citing the same `source` scenario (functional + negative) don't collide onto one TestOps case.
2. `testops_find_testcases(projectId, aql='tags = "<ttag>"', expand=["tags"])`.
3. **Found (≥1):** `testops_update_testcase(id=<first hit id>, **payload)`.
   **None:** `testops_create_testcase(projectId=<pid>, **payload)`.
4. Take the returned case id → write `@allure.id=<id>` back into the `test-plan.md` case
   header comment (so the file records the TestOps link).

Because the key is a tag derived from the case's identity (see "The key is frozen from
the first real upsert" below), re-running a Story with unchanged `source:`, title and
`type:` updates in place — 0 duplicates. A partial failure needs no rollback: re-run
resumes (found→update the landed ones, create the rest).

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

## The key is frozen from the first real upsert

`traceability_tag` hashes `story|service|capability|source|title|case_type`. Changing a
case's `source:` (or its title or type) therefore produces a **different** `tp-` tag: the
re-run finds no match, creates a second TestOps case, and the case written under the old
key is stranded — orphaned, still green, and invisible to the new AQL filter.

This is prospective, not a cleanup instruction: project KINOA holds zero plugin-authored
cases today, so the vocabulary and `source:` changes made here are the first keys ever
written. From the first non-dry-run upsert onward the format is frozen — a later `source:`
edit needs a deliberate migration (delete or re-tag the old case), never a silent re-run.
