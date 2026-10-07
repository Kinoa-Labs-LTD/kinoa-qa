# KING-99003 — user lists via the AI agent: Test Plan (excerpt)

**Story:** https://kinoadev.atlassian.net/browse/KING-99003
**Under test:** `kinoa_user_list_players_export`, `kinoa_user_list_players_import`, on the
**deployed test stand**
**Plan version:** 1 (2026-09-23)
**Report to produce:** `KING-99003-user-lists-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none
**Decisions from the interview:** artifacts are kept; one role flip (B1: Viewer on both games) plus
a restore; one replica; writes enabled; role-to-tool mapping per the story: Viewer may call
`players_export`, only Operator and above may call `players_import`.
**Checked against:** `tools/list of 2026-09-23; server source not available`

This file is an eval fixture of the `mcp-run` skill: fictional, literal fixed data, and only
the three cases the eval reaches (they reuse ids of the user-lists v2 plan; the calls are shortened for the eval).
The rest of the plan is left out.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `P2` | `7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c` — *Widget sandbox 2* (same company as `P1`) |
| `PLAYER1` | `p_8f2a1c77` — exists in `P1` only |
| `PLAYER2` | `p_3c9d0e14` — exists in `P1` only |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `CSV_URL` | `https://files.example.com/widget-qa/players-2.csv` — public https CSV the operator hosts: two lines, `p_8f2a1c77` and `p_3c9d0e14`, no header |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING99003-QA-<STAMP>` — prefix of every list name this plan creates |
| `KEY` | `king99003_qa_<STAMP with '-' → '_'>` — prefix of every explicit key this plan creates |

| Handle | Created as | Game | What it is | End state |
|---|---|---|---|---|
| `FIX` | name `NAME-fix`, key `KEY_fix` | `P1` | list holding `PLAYER1` | exists (status: active) |
| `IMP_URL` | name `NAME-imp-url`, key `KEY_imp_url` | `P1` | import-by-URL subject | exists (status: active) |
| `PB` | name `NAME-pb`, key `KEY_pb` | `P1` | Part B subject, untouched in Part A | exists (status: active) |

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: the file behind a
download link and the content fetched from `csv_url` are outside the protocol; `PB` is reserved for
Part B.

# PART A — everything that needs no permission change

## A3. kinoa_user_list_players_export

| Id | Call | Expected |
|---|---|---|
| `players-export-ok-02` | `kinoa_user_list_players_export {"game_id": P1, "user_list_id": FIX, "delivery": "link"}` | `ok: true`; `data.playersCount` = `1`; `data.fileName` = `user-list-KEY_fix.csv`; `data.downloadUrl` is an `https://` URL containing `/files/download`; `data.expiresAt` is about 10 minutes ahead; no embedded resource in `content` |

## A9. kinoa_user_list_players_import

| Id | Call | Expected |
|---|---|---|
| `players-import-ok-02` | 1. `kinoa_user_list_players_import {"game_id": P1, "user_list_id": IMP_URL, "csv_url": CSV_URL}` 2. the same plus `confirm_token` from step 1 | 1. A preview; `playerIds` = `2`; `data.message` ends with `The URL content is re-fetched when you confirm — keep the file unchanged until then.` 2. `ok: true`; `processed` = `2`; `added` = `2` |

# PART B — role-gated checks

## B1. Checkpoint 1 — GAME Viewer on `P1` and `P2`

Rows wanted (complete state): `GAME` `P1` = `viewer`; `GAME` `P2` = `viewer`; no `COMPANY` row. Stop
and wait for confirmation, wait 20 s, then run the table below.

| Id | Call | Expected |
|---|---|---|
| `role-players-import-01` | `kinoa_user_list_players_import {"game_id": P1, "user_list_id": PB, "csv_content": "p_8f2a1c77\np_3c9d0e14\n"}` | `ok: false`; `PERMISSION_DENIED` naming `kinoa_user_list_players_import`; no token |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. Section 6
has the AC bullets "Viewer can export the players of a list" and "only Operator and above can import
players"; nothing is irreversible.
