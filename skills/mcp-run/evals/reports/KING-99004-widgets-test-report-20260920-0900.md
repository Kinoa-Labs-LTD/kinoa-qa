# KING-99004 — widgets via the AI agent: Test Report

> This file is an eval fixture of the `mcp-run` skill: the fictional baseline of the
> redacted plan `KING-99004-widgets-test-plan.md`. It is not a report of a real run.

## 1. Header

- Date (UTC): 2026-09-20 09:00. Stand: the deployed test stand, through the `kinoa` connector.
- Caller `user_id`: `u_41c7`. Fixed data used: *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`).
- Run: `20260920-0900`. Plan file: `KING-99004-widgets-test-plan.md`, version 1.
- Run reason: `first run`. Previous report: `none`.

## 2. Overall status

`RED`. PASS 3 / FAIL 1 / OBSERVED 0 / BLOCKED 0 (4 cases). Findings: 1. Notes: 0.
First run of this plan.

## 3. What was done, per part

Part A ran start to finish. The preflight, the listing and the read passed; the unknown-id read
failed (F1).

## 4. Findings

### F1 — `kinoa_widget_get` answers an unknown widget id with an internal error   [severity: minor]
Case: get-iso-01   Tool: kinoa_widget_get   Part: A

Steps to reproduce:

1. Read a widget id that belongs to no widget.
   Request: `kinoa_widget_get {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"00000000-0000-4000-8000-0000000000aa"}`
   Response: `{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"NotFound: 404 Not Found","hint":"Retry the call."}}`

Expected: the plan expects `VALIDATION_FAILED` with `rule` = `widget_not_found` on `widget_id`.

Actual: `{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"NotFound: 404 Not Found","hint":"Retry the call."}}`.
The caller is told to retry a call that can never succeed.

Isolation: `get-ok-01` on an existing widget answered normally.

## 5. Notes

No notes.

## 6. AC traceability

| AC bullet | Cases | Verdict | Finding |
|---|---|---|---|
| an agent can list and read a game's widgets | list-ok-01, get-ok-01, get-iso-01 | FAIL | F1 |

## 7. Hypothesis verdicts

| Id | Verdict | Evidence |
|---|---|---|
| H1 | CONFIRMED (F1) | get-iso-01 |

## 8. Not covered / blocked

None.

## 9. Artifacts left behind

None: the plan creates nothing.

## 10. Role rows at the end of the run

No role flip; the rows were not changed.
