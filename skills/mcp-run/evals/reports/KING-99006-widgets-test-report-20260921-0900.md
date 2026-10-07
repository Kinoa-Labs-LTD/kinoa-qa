# KING-99006 — widget players via the AI agent: Test Report

> This file is an eval fixture of the `mcp-run` skill: the fictional baseline of
> `KING-99006-widgets-test-plan.md`, written before the owner rulings of 2026-09-24. It is not a
> report of a real run.

## 1. Header

- Date (UTC): 2026-09-21 09:00. Stand: the deployed test stand, through the `kinoa` connector.
- Caller `user_id`: `u_41c7`. Fixed data used: *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`), player `p_8f2a1c77`.
- Run: `20260921-0900`. Plan file: `KING-99006-widgets-test-plan.md`, version 1.
- Run reason: `first run`. Previous report: `none`.

## 2. Overall status

`RED`. PASS 4 / FAIL 2 / OBSERVED 0 / BLOCKED 0 (6 cases). Findings: 2. Notes: 0.
First run of this plan.

## 3. What was done, per part

Part A ran start to finish. The widget `KING99006-QA-20260921-0900-players` (id
`9e8d7c6b-5a49-4382-9170-6f5e4d3c2b1a`) was created in `pre-03`.

## 4. Findings

### F1 — a confirm token of `kinoa_widget_players_add` can be used a second time   [severity: minor]
Case: grey-01   Tool: kinoa_widget_players_add   Part: A

Steps to reproduce:

1. Preview adding `p_8f2a1c77`.
   Request: `kinoa_widget_players_add {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"9e8d7c6b-5a49-4382-9170-6f5e4d3c2b1a","player_ids":["p_8f2a1c77"]}`
   Response: `{"ok":true,"data":{"status":"preview","intendedChange":{"playerIds":1}},"meta":{"confirmToken":"eyJ0…Ad1","dryRun":false}}`
2. Confirm it.
   Request: the call of step 1 plus `"confirm_token":"eyJ0…Ad1"`
   Response: `{"ok":true,"data":{"added":1,"alreadyInWidget":0}}`
3. Send the confirm call of step 2 again.
   Request: the call of step 2, unchanged
   Response: `{"ok":true,"data":{"added":0,"alreadyInWidget":1}}`

Expected: the plan expects `CONFIRM_TOKEN_INVALID` on the second use.

Actual: `{"ok":true,"data":{"added":0,"alreadyInWidget":1}}`. The token executed a second time.

Isolation: no control probe was available.

### F2 — `kinoa_widget_players_add` accepts a player id that is not a uuid   [severity: minor]
Case: players-add-gap-01   Tool: kinoa_widget_players_add   Part: A

Steps to reproduce:

1. Preview adding `abc 123!`.
   Request: `kinoa_widget_players_add {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","widget_id":"9e8d7c6b-5a49-4382-9170-6f5e4d3c2b1a","player_ids":["abc 123!"]}`
   Response: `{"ok":true,"data":{"status":"preview","intendedChange":{"playerIds":1}},"meta":{"confirmToken":"eyJ0…Gp2","dryRun":false}}`

Expected: the plan expects `VALIDATION_FAILED` on `player_ids`.

Actual: `{"ok":true,"data":{"status":"preview","intendedChange":{"playerIds":1}},"meta":{"confirmToken":"eyJ0…Gp2","dryRun":false}}`.

Isolation: `players-add-ok-01` with `p_8f2a1c77` answered the same way.

## 5. Notes

No notes.

## 6. AC traceability

| AC bullet | Cases | Verdict | Finding |
|---|---|---|---|
| an agent can add players to a widget | players-add-ok-01, players-add-gap-01, grey-01 | FAIL | F1, F2 |

## 7. Hypothesis verdicts

None.

## 8. Not covered / blocked

None.

## 9. Artifacts left behind

| Entity | Game | Label |
|---|---|---|
| widget `KING99006-QA-20260921-0900-players` (`9e8d7c6b-5a49-4382-9170-6f5e4d3c2b1a`) | *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) | `exists (status: active)` |

## 10. Role rows at the end of the run

No role flip; the rows were not changed.
