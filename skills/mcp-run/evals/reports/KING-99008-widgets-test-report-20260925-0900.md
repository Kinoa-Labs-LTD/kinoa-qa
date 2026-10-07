# KING-99008 — widgets via the AI agent: Test Report

> This file is an eval fixture of the `mcp-run` skill: the fictional baseline of
> `KING-99008-widgets-test-plan-v2.md`, from a run of its version 1. It is not a report of a real
> run.

## 1. Header

- Date (UTC): 2026-09-25 09:00. Stand: the deployed test stand, through the `kinoa` connector.
- Caller `user_id`: `u_41c7`. Fixed data used: *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`), *Widget sandbox 2* (`7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c`), company `7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d`.
- Run: `20260925-0900`. Plan file: `KING-99008-widgets-test-plan.md`, version 1.
- Run reason: `first run`. Previous report: `none`.

## 2. Overall status

`RED`. PASS 15 / FAIL 1 / OBSERVED 0 / BLOCKED 0 (16 cases). Findings: 1. Notes: 1.
First run of this plan.

## 3. What was done, per part

Part A ran start to finish. The widgets `KING99008-QA-20260925-0900-a` (id
`1f0e9d8c-7b6a-4594-8382-71605f4e3d2c`) and `KING99008-QA-20260925-0900-r` (id
`2a1b0c9d-8e7f-46a5-9b4c-3d2e1f0a9b8c`) were created in *Widget sandbox*
(`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`).

B1: the `GET` showed no row after the first attempt; the cases ran after a 20 s wait. B2: the
`GET` showed the `COMPANY` `operator` row again after the first attempt.

## 4. Findings

### F1 — `kinoa_widget_get` answers an unknown widget id with an internal error   [severity: moderate]
Case: get-iso-01   Tool: kinoa_widget_get   Part: A

Steps to reproduce:

1. Read a widget id that belongs to no widget.
   Request: `kinoa_widget_get {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"00000000-0000-4000-8000-0000000000aa"}`
   Response: `{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"NotFound: 404 Not Found on GET /api/widgets/00000000-0000-4000-8000-0000000000aa","hint":"Retry the call."}}`

Expected: the plan expects `VALIDATION_FAILED` with the violation `widget_not_found` on `widget_id`.

Actual: `{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"NotFound: 404 Not Found on GET /api/widgets/00000000-0000-4000-8000-0000000000aa","hint":"Retry the call."}}`.
The hint tells the caller to retry a call that can never work.

Isolation: the same call with the id `1f0e9d8c-7b6a-4594-8382-71605f4e3d2c` of
`KING99008-QA-20260925-0900-a` answered `ok: true`.

## 5. Notes

### N1 — `kinoa_widget_update` returns `size` as a text value   [impact: low]
Case: update-ok-01   Tool: kinoa_widget_update   Part: A

What was seen: the execute leg of `kinoa_widget_update {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"1f0e9d8c-7b6a-4594-8382-71605f4e3d2c","size":5,"confirm_token":"eyJ0…Up1"}`
returned `{"ok":true,"data":{"updated":true,"widget":{"id":"1f0e9d8c-7b6a-4594-8382-71605f4e3d2c","size":"5"}}}`.
`kinoa_widget_get` on the same widget returns `size` as the number `5`.

Why it is not a finding: the value is right, and no acceptance criterion names its JSON type.

## 6. AC traceability

| AC bullet | Cases | Verdict | Finding |
|---|---|---|---|
| an agent can list and read widgets | list-ok-01, get-ok-01, get-iso-01, role-list-01, role-get-01, role-list-02 | FAIL | F1 |
| an Operator can create and update widgets | create-ok-01, create-ok-02, create-val-01, update-ok-01 | PASS | — |
| a Viewer cannot update | role-update-01 | PASS | — |

## 7. Hypothesis verdicts

None.

## 8. Not covered / blocked

None.

## 9. Artifacts left behind

| Entity | Game | Label |
|---|---|---|
| widget `KING99008-QA-20260925-0900-a` (`1f0e9d8c-7b6a-4594-8382-71605f4e3d2c`) | *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) | `exists (status: active)` |
| widget `KING99008-QA-20260925-0900-r` (`2a1b0c9d-8e7f-46a5-9b4c-3d2e1f0a9b8c`) | *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) | `exists (status: active)` |

## 10. Role rows at the end of the run

`ROLES_BEFORE`: `[{"scopeType":"COMPANY","scopeId":"7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d","role":"operator"}]`.
The last `GET`: the same row. `restored`.
