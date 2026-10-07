# KING-99008 — widgets via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99008
**Under test:** `kinoa_widget_list`, `kinoa_widget_create`, `kinoa_widget_get`, `kinoa_widget_update`, on the **deployed test stand**
**Plan version:** 2 (2026-09-26)
**Report to produce:** `KING-99008-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** `KING-99008-widgets-test-report-20260925-0900.md`
**Decisions from the interview:** artifacts are kept; one checkpoint plus a restore, applied by
the run through the admin role API; one replica, writes enabled; Viewer may call
`kinoa_widget_list` and `kinoa_widget_get`, Operator may call all four tools (AC); the account is
a COMPANY Operator; no bug is filed in JIRA.
**Checked against:** `tools/list of 2026-09-26; server source not available`

This file is an eval fixture of the `mcp-run` skill: a fictional domain with fictional,
literal fixed data. It is not a plan of a real story.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `P2` | `7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c` — *Widget sandbox 2* (same company as `P1`) |
| `COMPANY` | `7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d` — the company of `P1` and `P2` |
| `ADMIN_API` | `https://mcp-test.example.com/internal/mcp-admin/api` |
| `PLAYER1` | `p_8f2a1c77` — exists in `P1` only |
| `PLAYER2` | `p_3c9d0e14` — exists in `P1` only |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING99008-QA-<STAMP>` |

| Handle | `name` | Game | What it is | Created in | Intended end state |
|---|---|---|---|---|---|
| `W_A` | `NAME-a` | `P1` | the widget that is read, updated and read again under Viewer | `create-ok-01` | exists, size 5 |
| `W_R` | `NAME-r` | `P1` | reserved for `role-update-01`: no Part A case writes to it | `create-ok-02` | exists, size 3 |

**Name limit:** 30 — no `maxLength` in `tools/list`, no limit in the story; longest name 28, longest key 0

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: list and get are
read-only; create and update are writes; no tool of this domain carries its own rate cap.

### 1.2 Known issues and the cases that cover them

| Finding | Filed as | What it is | Cases |
|---|---|---|---|
| F1 (0900) | — | an unknown widget id answers `TOOL_EXECUTION_FAILED` | `get-iso-01` |
| N1 (0900) | — | the update answer gives `size` as a text value | `update-ok-01` |

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_list` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_create` is listed |
| `pre-03` | `tools/list` | `kinoa_widget_get` is listed |
| `pre-04` | `tools/list` | `kinoa_widget_update` is listed |
| `pre-05` | `kinoa_system_ping {}` | `ok: true`; `data.user_id` present. `Record: USER_ID` |

## A1. `kinoa_widget_list`

| Id | Call | Expected |
|---|---|---|
| `list-ok-01` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true`; `data.items` is an array; the paging fields are present |

## A2. `kinoa_widget_create`

| Id | Call | Expected |
|---|---|---|
| `create-ok-01` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-a", "size": 3}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `data.status` = `preview`; `meta.confirmToken` present. 2. `ok: true`; `data.created` = `true`; `data.widget.id` present. `Record: W_A` |
| `create-ok-02` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-r", "size": 3}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `data.status` = `preview`. 2. `ok: true`; `data.created` = `true`; `data.widget.id` present. `Record: W_R` |
| `create-val-01` | `kinoa_widget_create {"game_id": P1, "size": 3}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; a violation on `name`; no token |

## A3. `kinoa_widget_get`

| Id | Call | Expected |
|---|---|---|
| `get-ok-01` | `kinoa_widget_get {"game_id": P1, "widget_id": W_A}` | `ok: true`; `data.widget.id` = `W_A`; `data.widget.size` = `3` |
| `get-iso-01` | `kinoa_widget_get {"game_id": P1, "widget_id": "00000000-0000-4000-8000-0000000000aa"}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; violation `rule` = `widget_not_found`, `path` = `widget_id` |

## A4. `kinoa_widget_update`

| Id | Call | Expected |
|---|---|---|
| `update-ok-01` | 1. `kinoa_widget_update {"game_id": P1, "widget_id": W_A, "size": 5}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` 3. `kinoa_widget_get {"game_id": P1, "widget_id": W_A}` | 1. `ok: true`; `data.status` = `preview`; `meta.confirmToken` present. 2. `ok: true`; `data.updated` = `true`; `data.widget.size` = `5` (a number). 3. `ok: true`; `data.widget.size` = `5` |

# PART B — role-gated checks

Every checkpoint states the complete `user_role` state wanted for `USER_ID` (from `pre-05`) and
prints the requests that put it in place. The run sends them, reads the rows back with the `GET`,
compares them with the rows wanted, waits at least 20 s, then runs the table.

## B1. Checkpoint 1 — Viewer everywhere

Rows wanted (complete state): **no** `user_role` row for `USER_ID`, at any scope.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=COMPANY&scopeId=COMPANY"
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P1"
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P2"
curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"
```

| Id | Call | Expected |
|---|---|---|
| `role-list-01` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true` |
| `role-get-01` | `kinoa_widget_get {"game_id": P1, "widget_id": W_A}` | `ok: true`; `data.widget.id` = `W_A` |
| `role-update-01` | `kinoa_widget_update {"game_id": P1, "widget_id": W_R, "size": 9}` | `ok: false`; `error.code` = `PERMISSION_DENIED`; the message names `kinoa_widget_update`; no token |

## B2. Checkpoint 2 — restore

Rows wanted (complete state): the rows of `ROLES_BEFORE`, the snapshot the run took before B1.
B1 set no row, so nothing is deleted first.

```bash
# one PUT per row of ROLES_BEFORE, in the PUT shape of stand-facts.md (the admin role API)
curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"
```

| Id | Call | Expected |
|---|---|---|
| `role-list-02` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true` |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What
only this domain knows: section 6 has one row per AC bullet (an agent can list and read widgets;
an Operator can create and update widgets; a Viewer cannot update); nothing is irreversible.
