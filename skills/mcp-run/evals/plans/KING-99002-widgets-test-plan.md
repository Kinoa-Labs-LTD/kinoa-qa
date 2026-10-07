# KING-99002 — widgets via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99002
**Under test:** `kinoa_widget_list`, `kinoa_widget_get`, `kinoa_widget_export`, on the **deployed test stand**
**Plan version:** 1 (2026-09-23)
**Report to produce:** `KING-99002-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none
**Decisions from the interview:** artifacts are kept; no role flip (Viewer may call the two read
tools, the story gives the export to Operator, and the account is Operator); one replica; writes
enabled; no known issues; story-vs-stand tool check: `not done: no connector in this chat`.
**Checked against:** `tools/list of 2026-09-23; server source not available`

This file is an eval fixture of the `mcp-run` skill: a fictional domain with fictional,
literal fixed data. It is not a plan of a real story.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `P2` | `7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c` — *Widget sandbox 2* (same company as `P1`) |
| `PLAYER1` | `p_8f2a1c77` — exists in `P1` only |
| `PLAYER2` | `p_3c9d0e14` — exists in `P1` only |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |

Artifacts: none — the plan creates nothing.

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: list and get are
read-only, the export is a write into `P2`; no tool of this domain carries its own rate cap.

### 1.1 Known deviations to confirm through the protocol

| # | AC / expectation | What `tools/list` says | Cases |
|---|---|---|---|
| H1 | "an unknown widget id is reported as not found on `widget_id`" | nothing about the not-found shape | `get-iso-01` |

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_list` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_get` is listed |
| `pre-03` | `tools/list` | `kinoa_widget_export` is listed |
| `pre-04` | `kinoa_system_ping {}` | `ok: true`; `Record: USER_ID` |

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

## A3. kinoa_widget_export

Exports the widget `W_A` into `P2`, both legs.

| Id | Call | Expected |
|---|---|---|
| `export-ok-01` | 1. `kinoa_widget_export {"game_id": P1, "widget_id": W_A, "target_game_id": P2}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `data.status` = `preview`; `meta.confirmToken` present. 2. `ok: true`; `data.exported` = `true` |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only
this domain knows: section 6 has one row for the AC bullet "an agent can list and read a game's
widgets" and one for "an agent can export a widget to another game"; section 7 has H1; nothing
is irreversible.
