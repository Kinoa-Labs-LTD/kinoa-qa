# Stand facts — the admin role API, budgets, dry-run, connector

Facts about the deployed stand and the connector that reaches it. They are not the operator's
fixture: the constants a plan writes into its §0 are in [`fixed-data.md`](fixed-data.md). The
planning chat reads this file when it writes the plan; the execution chat reads it before case 1.

Contents: [the admin role API](#the-admin-role-api) · [server budgets and timings](#server-budgets-and-timings)
· [the dry-run kill-switch](#the-dry-run-kill-switch) · [connector](#connector).

## The admin role API

The stand's admin panel manages the `user_role` rows through a small HTTP API under `ADMIN_API`.
It has no login: the network gates it, so the machine that runs a plan must reach the stand's
`/internal/` paths (VPN). The requests below were verified on the test stand, 2026-09-29. It is
the one channel besides the connector, and
[`rules.md`](rules.md#target-and-method) says what it may be used for. These are the only three
requests, with the handles a plan writes and the run replaces by the literal values:

| Purpose | Request | Answer |
|---|---|---|
| Read the rows in effect | `curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"` | `200`, a JSON array of `{"scopeType", "scopeId", "role"}`; `[]` when the user has no row |
| Set one row (create or replace) | `curl -sS -o /dev/null -w '%{http_code}\n' -X PUT -H 'content-type: application/json' "ADMIN_API/users/USER_ID/roles" --data-raw '{"scopeType":"COMPANY","scopeId":"COMPANY","role":"operator"}'` | `204` |
| Remove one row | `curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P1"` | `204`, also when the row was not there |

- `scopeType` is `COMPANY` or `GAME`; `scopeId` is `COMPANY` for a company row and `P1` or `P2`
  for a game row — a plan never names another scope, because a row for a scope outside the
  fixture changes the caller's access to a game the run does not test and cannot restore. `role`
  is one of the names `roles.yml` defines, in lower case; the plans use `viewer`, `operator`,
  `tester` and `owner`. A `PUT` for a scope that already has a row replaces its role: one row per
  (user, scope).
- **Removing all rows is one `DELETE` per row the `GET` showed.** There is no bulk delete, and a
  `DELETE` for a scope with no row is harmless, so a checkpoint that wants "no row" deletes the
  three scopes a plan can hold (`COMPANY`, `GAME` `P1`, `GAME` `P2`) without reading first.
- A checkpoint's request block is `DELETE`s, then `PUT`s, then the `GET`, one command per line,
  in a ```` ```bash ```` fence under "Rows wanted", and nothing else in the fence. The restore
  checkpoint's `PUT`s cannot be printed in advance: the block holds the `DELETE`s and a comment
  line `# then one PUT per row of ROLES_BEFORE`, and the run writes those `PUT`s from the shape
  above. `curl` is called with `-sS` and no `-L`, `-k` or `--retry`, and with no header besides
  the two shown.
- The API's answer is stand setup, never a case result; what the run does when it is not the
  expected one is in [`rules.md`](rules.md#part-a--part-b).

## Server budgets and timings

**Verified at kinoa-mcp commit `bf41280`, 2026-09-30** (the budgets, TTLs, the dry-run switch
and the two confirm-token messages below). A planning chat with the repo open re-checks them,
plans with the values it read, and lists a value that differs under `Rule change proposals` in its hand-over (`../SKILL.md`, §3); a
chat without the repo uses them as given.

Design the cases around these, and state them in the plan.

**A tool's own cap comes from the served surface.** A tool may carry a cap of its own on top of
these budgets, charged on the executing leg only, never on a write's preview. The plan takes each
story tool's cap from what the story and that tool's `tools/list` description declare, and writes
it in §1 as a domain fact, because a list kept in this file goes stale when a tool changes. Known
at commit `bf41280`, as a hint where to look and never as the answer:
`kinoa_audience_check_player`, `kinoa_abtest_check_player`, `kinoa_player_summary`,
`kinoa_user_list_players_export` and `kinoa_webhook_test`. When the served description and this
hint disagree, the description wins.

| Budget | Value |
|---|---|
| Executing writes | 10 / minute / user — **per replica** |
| Preview legs | 60 / minute / user — **per replica** |
| A tool's own cap | as the tool declares — per (user, tool), **per replica** |
| Confirm-token TTL | 10 minutes; tokens are stateless, so any replica accepts one |
| Role cache | 10 s, keyed per (user, game) — the wait after a `user_role` change is in `rules.md` |
| Games claim | up to 15 minutes — a different clock from the role cache, see `rules.md` |
| Game → company cache | 10 minutes (relevant to COMPANY-scope role cases) |

**Every rate limit is per replica.** The limiters are in-process sliding logs with no shared store,
so on an N-replica stand the effective ceiling is N × limit, and which replica serves a given call
is not observable through the protocol. Two consequences for the plan: the cut-off point of a flood
probe is not a testable number, and `RATE_LIMITED` failing to appear at call 11 is not a defect.
Grade the dedicated rate-limit probe **`OBSERVED`**, recording the call number where the limit did
bite — `PASS`/`FAIL` only if the run has been told the stand runs a single replica.

**How the flood is sent.** The probe sends its calls as parallel tool calls in one message, as many
as the connector takes, and repeats that until the window is full. That is the only fast path the
chat has: no script, no loop and no bearer token borrowed from the connector (`rules.md`, target
and method). If the calls cannot be sent fast enough to reach the limit inside one window, the probe
is `OBSERVED` with the number of calls that did go out, whatever the replica count.

A write-heavy plan still keeps executing writes to **≤ 8 per minute** with an explicit 60 s pause
between write blocks: a per-replica ceiling only ever gives more headroom than the single-replica
number, so pacing to the strict number is always safe. The run keeps the same pace: at most 8
executing writes a minute outside the flood probe, and the plan's pauses are kept, not shortened.
Parallel calls
are for the flood only. The steps of a case, and the cases themselves, go out one call at a time in
the plan's order.

A `RATE_LIMITED` answer outside the dedicated rate-limit probe invalidates that case. On the
**confirm** leg the token survives it — the server proves the token before charging the write
budget — so the recovery is to wait and repeat the *same* confirm call. Re-previewing instead mints
a second token for one intended change and muddies any token-replay evidence.

## The dry-run kill-switch

`kinoa-mcp.safety.dry-run` (env `KINOA_MCP_DRY_RUN`) stops every write tool at preview and issues
**no** confirm token. It is a server-side switch: a run cannot turn it off, and no argument works
around it. Detect it on the run's first preview — `meta.dryRun: true`, `meta.confirmToken: null`,
and an instruction line saying writes are currently disabled.

If it is on, say so in the report's first line and record every executing write as
`BLOCKED — writes disabled server-side (dry-run)`, never `FAIL`: the server was told not to
write. Reads, schema validations,
preview legs and the permission-denial probes are unaffected and still run.

## Connector

The deployed stand is reached through its MCP connector (`kinoa`, HTTP `/mcp`, OAuth). If the
session's tool list has none of its `kinoa_*` tools, the `kinoa` connector is missing or not
logged in: the whole run is `BLOCKED` before case 1, with no report file, and the operator is told
to add the `kinoa` connector or log in to it (`mcp-run/SKILL.md`, §1). Never fall back to the
local stdio server, which resolves roles from a property and therefore cannot test the role model
at all.

**What the connector does to a call.** It may change with the connector version. A case whose
call the connector changes or cannot send ends with the fixed label of its fact:

| What the connector does | A case it stops | Label |
|---|---|---|
| It converts a top-level argument to its declared JSON type before the call leaves: `"true"` → `true`, `"3"` → `3`, `123` → `"123"`, or refuses to send it. An explicit `null` sent to a string argument goes out as the text `"null"`; a `null` sent to an object argument reaches the server as `null`. An element inside an array is sent as it is | a row that needs a top-level value of another JSON type, or a `null` for a string, to reach the server | `BLOCKED — the connector converts the argument type` (a refusal gets the same label) |
| It sends parallel tool calls one after another, about 1.5 s each, so about 40 calls leave per minute | a flood probe for the 60 / minute preview limit cannot reach it; the 10 / minute write limit is reached only when the write round trips are short | the flood is `OBSERVED` with its count (budgets, how the flood is sent) |
| It does not show the `tools/list` annotations | a case that asserts an annotation | `BLOCKED — annotations not shown by the connector`; the write list uses the `confirm_token` fallback (`rules.md`, writes) |
| It reads `tools/list` once per session, never again | a Part B case that expects `tools/list` to change after a role flip | `BLOCKED — the connector does not re-read tools/list` |
