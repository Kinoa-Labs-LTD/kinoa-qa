# KING-99007 — widgets via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99007
**Under test:** `kinoa_widget_list`, `kinoa_widget_create`, on the **deployed test stand**
**Plan version:** 1 (2026-09-29)
**Report to produce:** `KING-99007-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none
**Decisions from the interview:** artifacts are kept; two checkpoints plus a restore, applied by
the run through the admin role API; one replica, writes enabled; Viewer may call
`kinoa_widget_list`, Operator may call both tools (AC); no known issues.
**Checked against:** `tools/list of 2026-09-29; server source not available`

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

| Handle | Name | Game | What it is | End state |
|---|---|---|---|---|
| `W_B` | `NAME-b` | `P1` | created at B2 by the COMPANY Operator | exists, active |

**Name limit:** 30 — no `maxLength` in `tools/list`, no limit in the story; longest name 28, longest key 0

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: `kinoa_widget_list`
is read-only; `kinoa_widget_create` is a write; no tool of this domain carries its own rate cap.

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_list` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_create` is listed |
| `pre-03` | `kinoa_system_ping {}` | `ok: true`; `data.user_id` present. `Record: USER_ID` |

## A1. `kinoa_widget_list`

| Id | Call | Expected |
|---|---|---|
| `list-ok-01` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true`; `data.items` is an array |

## Hand-off

| Id | Call | Expected |
|---|---|---|
| `handoff-01` | `kinoa_widget_list {"game_id": P1, "limit": 1}` | `ok: true` |

# PART B — role-gated checks

Every checkpoint states the complete `user_role` state wanted for `USER_ID` (from `pre-03`) and
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
| `role-create-01` | `kinoa_widget_create {"game_id": P1, "name": "NAME-viewer"}` | `ok: false`; `error.code` = `PERMISSION_DENIED`; the message names `kinoa_widget_create`; no token |

## B2. Checkpoint 2 — COMPANY Operator

Rows wanted (complete state): `COMPANY` = `operator`; no `GAME` row for `P1`; no `GAME` row for `P2`.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P1"
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P2"
curl -sS -o /dev/null -w '%{http_code}\n' -X PUT -H 'content-type: application/json' "ADMIN_API/users/USER_ID/roles" --data-raw '{"scopeType":"COMPANY","scopeId":"COMPANY","role":"operator"}'
curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"
```

| Id | Call | Expected |
|---|---|---|
| `role-list-02` | `kinoa_widget_list {"game_id": P2, "limit": 50}` | `ok: true` |
| `role-create-02` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-b"}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `ok: true`; `meta.confirmToken` present. 2. `ok: true`; `data.widget.id` present. `Record: W_B` |

## B3. Checkpoint 3 — restore

Rows wanted (complete state): the rows of `ROLES_BEFORE`, the snapshot the run took before B1.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=COMPANY&scopeId=COMPANY"
# then one PUT per row of ROLES_BEFORE, in the PUT shape of stand-facts.md (the admin role API)
curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"
```

| Id | Call | Expected |
|---|---|---|
| `role-list-03` | `kinoa_widget_list {"game_id": P1, "limit": 50}` | `ok: true` |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only this domain
knows: section 6 has one row per AC bullet (Viewer lists; Operator creates); nothing is
irreversible.
