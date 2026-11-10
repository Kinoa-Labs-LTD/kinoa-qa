# KING-99010 — widgets via the AI agent: Test Report

> This file is an eval fixture of the `mcp-run` skill: a fictional run of
> `KING-99010-widgets-test-plan-v2.md`, at the point of the finish where the section 9 rows are
> written. It is not a report of a real run.

## 1. Header

- Date (UTC): 2099-12-30 12:00. Stand: the deployed test stand, through the `kinoa` connector.
- Caller `user_id`: `u_41c7`. Fixed data used: *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`), *Widget sandbox 2* (`7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c`), company `7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d`.
- Run: `20991230-1200`. Plan file: `KING-99010-widgets-test-plan-v2.md`, version 2.
- Run reason: `regression check`. Previous report: `KING-99010-widgets-test-report-20260925-0900.md`.

## 2. Overall status

`GREEN`.

| PASS | FAIL | OBSERVED | BLOCKED | Total |
|---|---|---|---|---|
| 16 | 0 | 0 | 0 | 16 |

Findings: 0. Notes: 0.

## 3. What was done, per part

The plan has no §1.4, so the run derived its segments. The tool sections A1 to A4 all belong to the
family `widget`, so they make one segment.

| Segment | Sections | First case | Last case | Family |
|---|---|---|---|---|
| `S1` | A1 to A4 | `list-ok-01` | `update-ok-01` | `widget` |

Preflight: `pre-01` to `pre-05` ran in the main chat and passed. `tools/list` lists the four tools
of the plan and `kinoa_system_ping`. `Record: USER_ID` = `u_41c7`. `ROLES_BEFORE` holds one row,
the `COMPANY` `operator` row, so Part A ran as an Operator. The first preview showed
`meta.dryRun` = `false`, so writes are enabled.

Segment `S1` (A1 to A4), model `sonnet`, started 12:02:40 UTC and ended 12:07:00 UTC. Executing
writes of the last 60 s: 12:06:20. Return: `done`. Deviations: none.

A1, `kinoa_widget_list`: `list-ok-01` passed. The answer was `ok: true`, `data.items` was an array
with 2 items, and the paging fields were present.

A2, `kinoa_widget_create`: all three cases passed. `create-ok-01` ran in two legs. The preview leg
sent `kinoa_widget_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","name":"KING99010-QA-20991230-1200-a","size":3}`
and got `{"ok":true,"data":{"status":"preview","intendedChange":{"name":"KING99010-QA-20991230-1200-a","size":3}},"meta":{"confirmToken":"eyJ0…Dq4","dryRun":false}}`.
The execute leg sent the same call plus `"confirm_token":"eyJ0…Dq4"` and got
`{"ok":true,"data":{"created":true,"widget":{"id":"5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716","name":"KING99010-QA-20991230-1200-a","size":3}},"meta":{"dryRun":false}}`.
`Record: W_A` = `5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716`.
`create-ok-02` also ran in two legs and created `KING99010-QA-20991230-1200-r`.
`Record: W_R` = `6f5e4d3c-2b1a-4a09-9e8d-7c6b5a493827`.
`create-val-01` sent no `name` and got `ok: false`, `error.code` = `VALIDATION_FAILED`, with a
violation on `name` and no token.

A3, `kinoa_widget_get`: both cases passed.
`get-ok-01` sent `kinoa_widget_get {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716"}`
and got `{"ok":true,"data":{"widget":{"id":"5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716","name":"KING99010-QA-20991230-1200-a","size":4}}}`.
The widget id is the one `create-ok-01` recorded, and the answer is `ok: true`.
`get-iso-01` sent `kinoa_widget_get {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"00000000-0000-4000-8000-0000000000aa"}`
and got `{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"The widget does not exist.","violations":[{"path":"widget_id","rule":"widget_not_found","message":"No widget has this id."}]}}`.
The earlier run answered this call with `TOOL_EXECUTION_FAILED`.

A4, `kinoa_widget_update`: `update-ok-01` passed. The preview leg sent
`kinoa_widget_update {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716","size":5}`
and showed `data.status` = `preview` with a token. The execute leg sent the same call plus the token
and got `{"ok":true,"data":{"updated":true,"widget":{"id":"5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716","size":5}},"meta":{"dryRun":false}}`.
The read-back returned `data.widget.size` = `5`.

B1, Viewer everywhere: the three `DELETE` requests answered `204`, `404` and `404`. The `GET` showed
no row after the first attempt, at 12:09:30 UTC. The cases ran after a 20 s wait. `role-list-01` and
`role-get-01` passed. `role-update-01` got `ok: false`, `error.code` = `PERMISSION_DENIED`, the
message named `kinoa_widget_update`, and the answer held no token.

B2, restore: one `PUT` put the `COMPANY` `operator` row back. The `GET` showed that row after the
first attempt, at 12:15:10 UTC. `role-list-02` passed.

No tool of this domain deletes. Nothing in the run is irreversible.

Section 9 agent, model `sonnet`, started 12:20:05 UTC and ended 12:20:40 UTC. It re-resolved both
widgets with `kinoa_widget_get`. Rows written: `exists (status: active)` 2, `soft-deleted
(status: <x>, still gettable)` 0, `hard-deleted (id no longer resolves)` 0, `not re-checked (last
seen: status <x> in <case>)` 0. Return: `done`. Deviations: none.

### Case status

| Case | Status | Finding / note / blocked row |
|---|---|---|
| `pre-01` | `PASS` | — |
| `pre-02` | `PASS` | — |
| `pre-03` | `PASS` | — |
| `pre-04` | `PASS` | — |
| `pre-05` | `PASS` | — |
| `list-ok-01` | `PASS` | — |
| `create-ok-01` | `PASS` | — |
| `create-ok-02` | `PASS` | — |
| `create-val-01` | `PASS` | — |
| `get-ok-01` | `PASS` | — |
| `get-iso-01` | `PASS` | — |
| `update-ok-01` | `PASS` | — |
| `role-list-01` | `PASS` | — |
| `role-get-01` | `PASS` | — |
| `role-update-01` | `PASS` | — |
| `role-list-02` | `PASS` | — |

## 4. Findings

None.

## 5. Notes

No notes.

## 6. AC traceability

| AC bullet | Cases | Verdict | Finding |
|---|---|---|---|
| an agent can list and read widgets | list-ok-01, get-ok-01, get-iso-01, role-list-01, role-get-01, role-list-02 | PASS | — |
| an Operator can create and update widgets | create-ok-01, create-ok-02, create-val-01, update-ok-01 | PASS | — |
| a Viewer cannot update | role-update-01 | PASS | — |

## 7. Hypothesis verdicts

None.

## 8. Not covered / blocked

| Item | Reason |
|---|---|
| Plan defect for the next version | The plan has no §1.4 Segments, so the run derived its segments. The next version needs §1.4. |

## 9. Artifacts left behind

| Entity | Game | Label |
|---|---|---|
| widget `KING99010-QA-20991230-1200-a` (`5e4d3c2b-1a09-4f8e-8d7c-6b5a49382716`) | *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) | `exists (status: active)` |
| widget `KING99010-QA-20991230-1200-r` (`6f5e4d3c-2b1a-4a09-9e8d-7c6b5a493827`) | *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) | `exists (status: active)` |

## 10. Role rows at the end of the run

`ROLES_BEFORE`: `[{"scopeType":"COMPANY","scopeId":"7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d","role":"operator"}]`.
The last `GET`: the same row. `restored`.
