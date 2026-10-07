# KING-99006 — widget players via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99006
**Under test:** `kinoa_widget_create`, `kinoa_widget_players_add`, on the **deployed test stand**
**Plan version:** 1 (2026-09-20)
**Report to produce:** `KING-99006-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** `KING-99006-widgets-test-report-20260921-0900.md`
**Decisions from the interview:** artifacts are kept; no role flip (the account is Operator); one
replica; writes enabled; no known issues; story-vs-stand tool check: both tools listed.
**Checked against:** `tools/list of 2026-09-20; server source not available`

This file is an eval fixture of the `mcp-run` skill: a fictional domain with fictional,
literal fixed data, written before the owner rulings of 2026-09-24. It is not a plan of a real
story.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `P2` | `7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c` — *Widget sandbox 2* (same company as `P1`) |
| `PLAYER1` | `p_8f2a1c77` — exists in `P1` only |
| `PLAYER2` | `p_3c9d0e14` — exists in `P1` only |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING99006-QA-<STAMP>` |

| Handle | `name` | Game | What it is | Created in | Intended end state |
|---|---|---|---|---|---|
| `W_B` | `NAME-players` | `P1` | the widget whose players are added | `pre-03` | exists |

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: both tools are
writes; no tool of this domain carries its own rate cap.

### 1.2 Known issues and the cases that cover them

| Finding | Filed as | What it is | Cases |
|---|---|---|---|
| F1 (0900) | — | a confirm token can be used a second time | `grey-01` |
| F2 (0900) | — | a player id that is not a uuid is accepted | `players-add-gap-01` |

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_create` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_players_add` is listed |
| `pre-03` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-players"}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `data.status` = `preview`. 2. `ok: true`; `data.created` = `true`. `Record: W_B` |

## A1. kinoa_widget_players_add

| Id | Call | Expected |
|---|---|---|
| `players-add-ok-01` | 1. `kinoa_widget_players_add {"game_id": P1, "widget_id": W_B, "player_ids": [PLAYER1]}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `data.status` = `preview`. 2. `ok: true`; `data.added` = `1`. `Record: T_ADD` (the token of step 1) |
| `players-add-gap-01` | `kinoa_widget_players_add {"game_id": P1, "widget_id": W_B, "player_ids": ["abc 123!"]}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; a violation on `player_ids` |

## Grey

| Id | Call | Expected |
|---|---|---|
| `grey-01` | the step-2 call of `players-add-ok-01` again, with `"confirm_token": T_ADD` | `ok: false`; `error.code` = `CONFIRM_TOKEN_INVALID` (a token is used once) |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only
this domain knows: section 6 has one row for the AC bullet "an agent can add players to a widget";
nothing is irreversible.
