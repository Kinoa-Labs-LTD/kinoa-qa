# KING-99004 — widgets via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99004
**Under test:** `kinoa_widget_list`, `kinoa_widget_get`, on the **deployed test stand**
**Plan version:** 1 (2026-09-19)
**Fixed data:** redacted on 2026-09-23 — the game ids, player ids and the webhook target in this file are `<…>` placeholders (see `fixed-data.md`, "Games and players"); this file is a worked example and cannot be run until a new plan version carries literal values in §0
**Report to produce:** `KING-99004-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** `KING-99004-widgets-test-report-20260920-0900.md`
**Decisions from the interview:** artifacts are kept; no role flip (read tools only, Viewer may call
both per `roles.yml`); one replica; writes enabled but unused; no known issues.
**Checked against:** `tools/list of 2026-09-23; server source not available`

This file is an eval fixture of the `mcp-run` skill: a fictional domain with fictional,
redacted fixed data. It is not a plan of a real story.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `<P1_GAME_ID>` — *<P1_GAME_NAME>* |
| `P2` | `<P2_GAME_ID>` — *<P2_GAME_NAME>* (same company as `P1`) |
| `PLAYER1` | `<PLAYER1_ID>` — exists in `P1` only |
| `PLAYER2` | `<PLAYER2_ID>` — exists in `P1` only |
| `WEBHOOK_TARGET` | `<WEBHOOK_TARGET>` — the widget callback host the operator owns |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |

Artifacts: none — the plan creates nothing.

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: both tools are
read-only; no tool of this domain carries its own rate cap.

### 1.1 Known deviations to confirm through the protocol

| # | AC / expectation | What `tools/list` says | Cases |
|---|---|---|---|
| H1 | "an unknown widget id is reported as not found on `widget_id`" | nothing about the not-found shape | `get-iso-01` |

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `kinoa_system_ping {}` | `ok: true`; `Record: USER_ID` |

## A1. kinoa_widget_list

Lists the widgets of `P1`; the first item is the subject of `get-ok-01`.

| Id | Call | Expected |
|---|---|---|
| `list-ok-01` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true`; `data.items` is an array; the paging fields are present. `Record: W_A` (the first item's id) |

## A2. kinoa_widget_get

Reads one widget, then an id that belongs to no widget (settles H1).

| Id | Call | Expected |
|---|---|---|
| `get-ok-01` | `kinoa_widget_get {"game_id": P1, "widget_id": W_A}` | `ok: true`; `data.widget.id` = `W_A` |
| `get-iso-01` | `kinoa_widget_get {"game_id": P1, "widget_id": "00000000-0000-4000-8000-0000000000aa"}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; violation `rule` = `widget_not_found`, `path` = `widget_id` |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only
this domain knows: section 6 has one row for the AC bullet "an agent can list and read a game's
widgets"; section 7 has H1; nothing is irreversible.
