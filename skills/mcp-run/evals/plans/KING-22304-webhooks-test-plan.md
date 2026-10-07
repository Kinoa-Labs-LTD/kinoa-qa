# KING-22304 — Webhooks via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-22304
**Under test:** `kinoa_webhook_list`, `kinoa_webhook_get`, `kinoa_webhook_create`,
`kinoa_webhook_clone`, `kinoa_webhook_update`, `kinoa_webhook_status`, `kinoa_webhook_test`, on the
**deployed test stand**
**Plan version:** 1 (2026-09-16)
**Fixed data:** redacted on 2026-09-23 — the game ids, player ids, account and user id in this file are `<…>` placeholders (see `mcp-plan references/fixed-data.md`, "Games and players"); this file is a worked example and cannot be run until a new plan version carries literal values in §0
**Report to produce:** `KING-22304-webhooks-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none
**Decisions from the interview:** artifacts are kept (nothing self-cleans); delete semantics as
known today: `kinoa_webhook_status` target `DELETED` is a hard delete of a DRAFT webhook (the row is
gone), target `DEPRECATED` is a terminal status flip (the row stays), target `ACTIVE` cannot be
reversed to DRAFT — all three are hypotheses (H4, H5, H6); irreversible tools: `kinoa_webhook_status`
with every target, and `kinoa_webhook_test` (a real call to a third party) — each gets its own
subject; three role flips plus a restore (Viewer on both games; Tester on both games; GAME
Operator on `P1` plus COMPANY Viewer; original rows restored); the stand runs **one replica** with
**writes enabled**, so the rate-limit probes are graded `PASS`/`FAIL` at the exact cut-off and
`pre-08` only confirms `meta.dryRun` = `false`; the test target is the operator-owned endpoint
`https://<WEBHOOK_TARGET>` (`TARGET` in §0); the role-to-tool mapping is `roles.yml` at
the commit below — Viewer: `kinoa_webhook_list`, `kinoa_webhook_get`; Tester: those plus
`kinoa_webhook_test`; Operator: all seven; Owner: everything; Developer: only what Viewer has.
Known issues: none — the story has no comments, no linked bug (its only link is "is blocked by
KING-21968", a completed story), and no earlier run; the sub-tasks KING-22546, KING-22547 and
KING-22548 are tasks, not bugs, and were `In Testing` on 2026-09-16, KING-22549 ("[QA] Test") was
`In Progress`, and the story was `In Progress`.
**Checked against:** `commit adef2a1` (`develop`, the merge of the feature branch) — files read:
`tools/webhook/*.java` (all ten), `tools/McpToolRegistry.java`, `tools/ToolArgs.java`,
`client/webhook/WebhooksClient.java`, `commons/dtos/webhook/*.java`, `commons/dtos/ToolPreview.java`,
`commons/dtos/ToolErrorCode.java`, `commons/dtos/PagedData.java`, `safety/WriteGuard.java`,
`safety/ConfirmTokenService.java`, `domain/permission/PermissionService.java`, `roles.yml`,
`application.yml` (the server instructions and the safety budgets), and the names of the tests in
`func/Webhook*FuncTest.java`. The budgets of `fixed-data.md` were re-checked at this commit: write
10/min, preview 60/min, confirm TTL 10 min, role cache 10 s, game-to-company cache 10 min —
unchanged. Whether the stand runs this commit is not known to the plan; `pre-01` records what the
stand serves. On 2026-09-16 `P1` held **no** webhooks and `P2` held five pre-existing ones (read
through the connector); those numbers are the baseline of the paging cases.

---

## 0. Fixed test data

The constants are from `mcp-plan references/fixed-data.md`. In every table below,
`P1`, `P2`, `FOREIGN`, `NAME`, `KEY`, `TARGET`, `DEAD`, the JSON fragments and every recorded
handle stand for their literal values. Substitute them before sending a call. A JSON fragment
(`FIELDS_1`, `JSON_1`, …) is pasted into the call as it is written here.

| Constant | Value |
|---|---|
| `P1` | `<P1_GAME_ID>` — *<P1_GAME_NAME>* |
| `P2` | `<P2_GAME_ID>` — *<P2_GAME_NAME>* |
| `PLAYER1` | `<PLAYER1_ID>` — exists in `P1` only; no webhook tool takes a player, so it is unused here |
| `PLAYER2` | `<PLAYER2_ID>` — exists in `P1` only; unused here |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `P2_ACTIVE` | `<P2_ACTIVE_WEBHOOK_ID>` — the pre-existing ACTIVE webhook `test` of `P2` (read-only; `pre-07` confirms it) |
| `NO_SUCH` | `00000000-0000-4000-8000-00000000dead` — a well-formed uuid that is no webhook |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING22304-QA-<STAMP>` — 22 characters; prefix of every webhook name this plan creates. A name may hold at most 50 characters, so every suffix below is at most 28 characters |
| `KEY` | `king22304_qa_<STAMP with '-'→'_'>` — 26 characters; prefix of every webhook key this plan creates. A key may hold at most 50 characters, so every suffix below is at most 24 characters |
| `TARGET` | `https://<WEBHOOK_TARGET>` — the operator-owned test target. It answers every method with `200`. Its free plan caps the requests per day, so this plan fires at most 20 times per run (counted in §1) |
| `DEAD` | `https://kinoa-qa-unreachable.invalid/hook` — a host that never resolves (`.invalid` is reserved), for the unreachable-target case |
| `JSON_1` | `"{\"event\": \"${event}\"}"` — a json body with one COMMON placeholder |
| `FIELDS_1` | `[{"name": "event", "fieldType": "STRING", "order": 1}]` |
| `JSON_FULL` | `"{\"event\": \"${event}\", \"amount\": ${amount}, \"vip\": ${vip}}"` |
| `HEADERS_FULL` | `{"Content-Type": "application/json", "X-Kinoa-Run": "${run}"}` |
| `FIELDS_FULL` | `[{"name": "event", "fieldType": "STRING", "placeholderType": "COMMON", "description": "event name", "required": true, "order": 1}, {"name": "amount", "fieldType": "NUMBER", "required": false, "default": 12, "order": 2}, {"name": "vip", "fieldType": "BOOLEAN", "order": 3}, {"name": "run", "fieldType": "STRING", "required": false, "default": "qa", "order": 4}]` |
| `JSON_PERS` | `"{\"event\": \"${event}\", \"player\": \"{{playerName}}\"}"` |
| `FIELDS_PERS` | `[{"name": "event", "fieldType": "STRING", "order": 1}, {"name": "playerName", "fieldType": "STRING", "placeholderType": "PERSONALIZED", "order": 2}]` |
| `JSON_2` | `"{\"event\": \"${event}\", \"extra\": \"${extra}\"}"` |
| `FIELDS_2` | `[{"name": "event", "fieldType": "STRING", "order": 1}, {"name": "extra", "fieldType": "STRING", "order": 2}]` |
| `S50` | the letter `A` repeated 50 times; `S51` = 51 times; `S128` = 128 times; `S129` = 129 times; `S255` = 255 times; `S256` = 256 times |
| `U256` | `TARGET/qa/` followed by the letter `a` repeated enough times to make exactly 256 characters; `U257` = the same with one more `a` |

### Artifacts table

One row per subject the plan creates. The report cites the real name and key, never the handle.
Every webhook is created in `P1` unless the row says `P2`. A handle written as `Record:` in a case
is that webhook's `id` from the response of the executing leg.

| Handle | `name` / `key` | Game | What it is | Created in | Intended end state |
|---|---|---|---|---|---|
| `SEED_A` | `NAME-seed-a` / `KEY_seed_a` | `P1` | read fixture: DRAFT, `POST TARGET/qa/seed-a`, `JSON_1`, `FIELDS_1`. **Reserved**: no case writes to it after `pre-10` | `pre-10` | `exists (status: DRAFT)` |
| `SEED_B` | `NAME-seed-b` / `KEY_seed_b` | `P1` | read and fire fixture: ACTIVE, same definition. **Reserved**: no write after `pre-12`; fired by `test-ok-01`, `grey-01` and `role-test-02` | `pre-11`, activated in `pre-12` | `exists (status: ACTIVE)` — irreversible |
| `SEED_C` | `NAME-seed-c` / `KEY_seed_c` | `P1` | read fixture: DEPRECATED, same definition. **Reserved**: its status is never touched after `pre-13`; the only write sent to it is the description probe `update-gap-01`, which may or may not be accepted | `pre-11`, deprecated in `pre-13` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible |
| `MAIN` | `NAME-main` / `KEY_main`, renamed to `NAME-main-v2` / `KEY_main_v2` in `update-ok-02` | `P1` | the create happy path; edited as DRAFT in §A5; activated in `status-ok-01`; deprecated in `status-ok-02` | `create-ok-01` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible |
| `FULL` | `NAME-full` / `KEY_full` | `P1` | the full parameter set: type, description, `HEADERS_FULL`, `JSON_FULL`, `FIELDS_FULL`; fired as DRAFT | `create-ok-02` | `exists (status: DRAFT)` |
| `PERS` | `NAME-pers` / `KEY_pers` | `P1` | one PERSONALIZED placeholder (`FIELDS_PERS`) | `create-ok-03` | `exists (status: DRAFT)` |
| `GETM` | `NAME-get` / `KEY_get` | `P1` | GET webhook with the placeholder in the url, no json | `create-ok-04` | `exists (status: DRAFT)` |
| `MIN` | `NAME-min` / `KEY_min` | `P1` | the smallest webhook: no json, no fields, no headers | `create-sem-02` | `exists (status: DRAFT)` |
| `CLONE_A` | derived by the service from `SEED_A` (a "copy" variant) | `P1` | clone without overrides | `clone-ok-01` | `exists (status: DRAFT)` |
| `CLONE_A2` | derived by the service from `SEED_A` (a second free variant) | `P1` | a second clone without overrides | `clone-sem-02` | `exists (status: DRAFT)` |
| `CLONE_B` | `NAME-clone-b` / `KEY_clone_b` | `P1` | clone of ACTIVE `SEED_B` with explicit name and key | `clone-ok-02` | `exists (status: DRAFT)` |
| `CLONE_C` | `NAME-clone-c` / `KEY_clone_c` | `P1` | clone of DEPRECATED `SEED_C` (the revival path) | `clone-ok-03` | `exists (status: DRAFT)` |
| `ACT_UPD` | `NAME-act-upd` / `KEY_act_upd` | `P1` | the ACTIVE-update subject: created and activated in §A5, then a NEW field is added | `update-ok-06` | `exists (status: ACTIVE)` — irreversible |
| `ST_DD` | `NAME-st-dd` / `KEY_st_dd` | `P1` | DRAFT → DEPRECATED without ever being ACTIVE | `status-sem-01` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible |
| `ST_DEL` | `NAME-st-del` / `KEY_st_del` | `P1` | the delete determination subject | `status-ok-03` | `hard-deleted (id no longer resolves)` |
| `ST_TWIN` | `NAME-st-twin` / `KEY_st_twin` | `P1` | the untouched twin of `ST_DEL`, the control | `status-ok-03` | `exists (status: DRAFT)` |
| `DEAD_WH` | `NAME-dead` / `KEY_dead` | `P1` | `POST DEAD`, for the unreachable-target fire | `test-sem-01` | `exists (status: DRAFT)` |
| `FIRE` | `NAME-fire` / `KEY_fire` | `P1` | the rate-limit flood subject of §A8 | `grey-01` | `exists (status: DRAFT)` |
| `RP` | `NAME-rp` / `KEY_rp` | `P1` | the token-replay subject of §A8 | `grey-03` | `exists (status: DRAFT)` |
| `EXP` | `NAME-exp` / `KEY_exp` | `P1` | the token-expiry subject of §A8 (previewed at the start of §A8, confirmed 10 minutes later) | `grey-13` | never created (the token has expired) |
| `SCOPE_P1` | `NAME-scope-p1` / `KEY_scope_p1` | `P1` | created under the GAME Operator row of checkpoint B3 | `role-create-05` | `exists (status: DRAFT)` |
| `RESTORE` | `NAME-restore` / `KEY_restore` | `P1` | created after the rows are restored, to prove the restore | `role-create-06` | `exists (status: DRAFT)` |
| conditional | `NAME-getj`, `NAME-r4`, `NAME-r6`, `NAME-r8`, `NAME-r10`, `NAME-r11`, `NAME-ru3`, and a blank-named clone | `P1` | created only if a `gap` or `rule` row that expects a refusal is answered `ok: true` (`GETJ`, `R4`, `R6`, `R8`, `R10`, `R11`, `RU3`, `CLONE_BLANK`) | the row named in §A3 / §A4 | `exists (status: DRAFT)` if created |

## 1. Execution rules

The rules are in `mcp-plan references/rules.md`; the report contract is in
`mcp-plan references/report-spec.md`; the constants and budgets are in
`mcp-plan references/fixed-data.md`. What only this domain knows:

- **Write tools** (no `readOnlyHint: true`): `kinoa_webhook_create`, `kinoa_webhook_clone`,
  `kinoa_webhook_update`, `kinoa_webhook_status`, `kinoa_webhook_test`. Every one of them reads
  the webhook on **both** legs (`clone`, `update`, `status`, `test`) or builds its preview from the
  arguments alone (`create`), so an unknown id fails on the preview leg and no token is issued.
- **`kinoa_webhook_test` carries its own cap**: 10 calls per minute per (user, tool), charged on
  the executing leg only. The general write budget is also 10 per minute and is checked **first**,
  so the two caps cannot be told apart by the protocol (H8).
- **Irreversible**: `kinoa_webhook_status` with every target — `ACTIVE` never goes back to DRAFT,
  `DEPRECATED` is terminal, `DELETED` erases the row — and `kinoa_webhook_test`, whose effect lands
  on the target, outside Kinoa.
- **Test fires per run**: at most 22 requests reach `TARGET` — `test-ok-01`, `test-ok-02`,
  `test-gap-01`, `test-gap-02`, `test-gap-03`, `test-gap-04` (the last three only if the service
  accepts the values), `grey-01` × 11 plus its retry in step 4, `grey-04` × 2 (if the token is
  replayable), `role-test-02`. The `DEAD_WH` fire never reaches it. Do not add fires.
- **Reserved for later parts**: `SEED_A`, `SEED_B`, `SEED_C` are written only in §A0 and then read
  or fired; Part B reads `SEED_A`, fires `SEED_B`, and creates `SCOPE_P1` and `RESTORE`.
- **Pre-existing data**: `P1` holds no webhooks before the run. `P2` holds five (`test`, `test2`,
  `test3`, `test3_clone`, `1234…7890`); they are read-only and only `P2_ACTIVE` is named in a call.
- **Not under test**: `kinoa_games_list` and `kinoa_system_ping` are helpers. The dashboard UI,
  the webhook service's own upgrade (the kinoa-bom 4.x AC bullet) and the audit log are not
  reachable through the protocol; they are listed in report section 8.
- **Placeholder syntax**: `${name}` is a COMMON field, `{{name}}` a PERSONALIZED one. The service
  refuses a declared field nobody references and a reference nobody declares. `DATE`, `VERSION`,
  `ENUMERATION`, `AB_SETTINGS` and `STRING_ARRAY` render unquoted and cannot sit inside the json
  body.

### 1.1 Known deviations to confirm through the protocol

| # | AC / expectation | What the code appears to do | Cases |
|---|---|---|---|
| H1 | "the compact view carries urlTemplate, method, headers, json and fields" | The listing returns summaries only: `id`, `name`, `key`, `status`, `urlTemplate`, and with `detailed` the bookkeeping. `requestMethod`, `headers`, `json` and `fields` are in **no** listing, by design (the tool description says so). Expected today: a `FAIL` of this AC clause; `kinoa_webhook_get` carries them, so the caller has a way around it | `list-ok-01`, `list-ok-02`, `get-ok-01` |
| H2 | create takes "name, key, type, description, urlTemplate, method, headers, json, fields and security" | The create schema has no `security` argument, and `additionalProperties: false` rejects it before the tool runs. Expected today: the rejection; graded against the AC as a `FAIL` whose severity depends on whether the dashboard offers `security` — the run cannot see the dashboard and says so | `create-schema-08` |
| H3 | "an invalid target returns a clear error naming the allowed targets" | An unknown target word is rejected by the schema (`enum`), and the validator's text lists the three values. A **disallowed move** (for example ACTIVE → DELETED) is refused by the service, and its text is mapped to violations as it comes — whether it names the allowed targets is the service's wording. `UNPROVEN` until the run reads it | `status-schema-01`, `status-rule-02`, `status-rule-03`, `status-rule-04`, `status-rule-05`, `status-rule-06` |
| H4 | "DELETED (wraps the hard-delete endpoint, DRAFT only — the preview warns)" | `DELETE /webhooks/{id}`: after it `kinoa_webhook_get` answers `webhook_not_found`, and the webhook is absent from the unfiltered listing and from every status filter. The preview carries the warning "will be permanently erased — there is no soft delete and no undo". On a non-DRAFT webhook the service refuses | `status-ok-03`, `status-sem-02`, `status-sem-03`, `status-rule-03`, `status-rule-05` |
| H5 | `DEPRECATED` "is TERMINAL" (tool description) | A status flip: the row stays, `kinoa_webhook_get` answers with `status: DEPRECATED`, the webhook is listed under the `DEPRECATED` filter and in the unfiltered listing. Afterwards every target is refused | `pre-13`, `status-ok-02`, `status-sem-01`, `status-sem-04`, `status-rule-04`, `status-rule-05`, `status-rule-06` |
| H6 | `ACTIVE` "publishes a DRAFT" | Sent as a JSON Patch on `/status` with **no** `If-Match`; the preview says "This transition is not conditioned on an ETag". Not an AC breach; recorded `OBSERVED` | `status-ok-01` |
| H7 | "kinoa_webhook_update applies partial updates; nothing is silently lost" | JSON Merge Patch: an omitted argument keeps its value; `headers` merges member by member and a `null` value removes one header; `fields` is an array and is **replaced whole**, so a placeholder left out is removed — with a warning in the preview. Silent loss would be a `FAIL`; a warned loss is the documented behaviour | `update-ok-01` to `update-ok-05`, `update-sem-01`, `update-sem-02` |
| H8 | "rate-limited to 10 calls a minute" (server instructions and tool description) | The 11th executing fire inside a minute is refused, but by the general write budget (`Write rate limit exceeded`), which runs before the tool's own cap; the tool's own text (`Rate limit exceeded for kinoa_webhook_test`) is not observable while both caps are 10. One replica: `PASS`/`FAIL` on call 11 | `grey-01`, `grey-02` |
| H9 | "When the target cannot be reached at all … it answers 200 with an "error" member" | The service's transport failure is proxied as `status: 200` with a body `{"error": "..."}` and the tool answers `ok: true`. If the service refuses to **create** a webhook whose host does not resolve, the case is `BLOCKED` and that refusal is recorded | `test-sem-01` |
| H10 | `kinoa_webhook_test` "Every required placeholder needs a value" | The service answers 422 with the platform's `{"errors": {field: [...]}}` body, and the tool maps it to `VALIDATION_FAILED`. If the body has another shape, the tool reports it as the **target's** answer (`ok: true`, `response.status` = `422`) — that misreport is a `FAIL` | `test-rule-01`, `test-gap-02` |
| H11 | update on an ACTIVE webhook: "the service freezes its name, key, urlTemplate, requestMethod and headers and allows only NEW fields" | The tool only **warns** in the preview; the refusal is the service's. If the confirm leg answers `ok: true` and the frozen member changed, the description is wrong (`FAIL`) | `update-rule-02`, `update-rule-03`, `update-ok-06` |
| H12 | reads of another game's webhook | The service answers 404 for a webhook of another game, and the tool says `No webhook '<id>' found in game '<P1>'`. An `ok: true` that returns `P2`'s webhook under `P1` is a critical `FAIL` | `get-iso-02`, `clone-iso-02`, `update-iso-02`, `status-iso-02`, `test-iso-02` |
| H13 | the key rule "starts with a letter, then letters, digits, '_' or '-'" (schema description) | The schema checks only `maxLength: 50`; the format is the service's rule and comes back as a violation on `key`. `P2`'s pre-existing keys `1234567890` and `www` predate the rule | `create-rule-04` |
| H14 | `search` "matches a substring of the webhook NAME, or an exact webhook id" | Sent as the service's `name` parameter. Whether the match ignores case, and whether an exact id really matches, is the service's behaviour: `OBSERVED` where no AC decides | `list-sem-04` to `list-sem-08` |
| H15 | repo convention: the server instructions name every tool family | `application.yml` at `adef2a1` carries the webhook paragraph. Expected: `PASS` | `pre-09` |
| H16 | AC: the write tools are "covered by preview/confirm, rate limiting and audit" | Preview/confirm and the rate limits are observable; the audit log is not. Recorded `BLOCKED` for the audit half | `grey-16` |
| H17 | "the new webhook starts as DRAFT" | The create body sends no `status`; the service forces DRAFT. A create response with another status is a `FAIL` | `create-ok-01` to `create-ok-04` |
| H18 | PERSONALIZED placeholders on create | The tool passes `placeholderType: PERSONALIZED` through. Whether the service needs the name to match a player field is unknown — the case is graded on the AC (it lists the type) and the refusal, if any, is quoted | `create-ok-03`, `test-gap-03` |

### 1.2 Known issues and the cases that cover them

Omitted: the story carries no known issue and there is no earlier run (see the header).

# PART A — everything that needs no permission change

Part A runs start to finish with the account's current rights (Operator or Owner on both games).
Executing writes are kept to at most 8 per minute, with a 60 s pause between write blocks.

## A0. Preflight

Confirms the tool list, the fixed data and the baseline, and creates the three read fixtures
`SEED_A` (DRAFT), `SEED_B` (ACTIVE) and `SEED_C` (DEPRECATED). `pre-08` is the run's first
preview: read `meta.dryRun` there. `pre-09` settles H15. `pre-13` is the first sight of H5. Five
executing writes happen here (`pre-10` to `pre-13`); pause 60 s before §A3.

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` (and the `initialize` result if the connector shows it) | Record the server version if visible. All seven tools are listed: `kinoa_webhook_list`, `kinoa_webhook_get`, `kinoa_webhook_create`, `kinoa_webhook_clone`, `kinoa_webhook_update`, `kinoa_webhook_status`, `kinoa_webhook_test`. A missing tool makes every case of its section `BLOCKED` |
| `pre-02` | `tools/list` — annotations | `readOnlyHint: true` on `list` and `get`; `readOnlyHint: false` on `create`, `clone`, `update`, `status`, `test`. `destructiveHint: true` on `update`, `status`, `test`; `destructiveHint: false` on `list`, `get`, `create`, `clone`. `idempotentHint: true` on `list`, `get`, `update`; `idempotentHint: false` on `create`, `clone`, `status`, `test`. `openWorldHint: true` on `test` **only**; `openWorldHint: false` on the other six. A non-empty `title` on all seven. `BLOCKED` if the connector does not expose annotations; then the write list is the five tools whose input schema names `confirm_token` |
| `pre-03` | `tools/list` — input schemas | The five write tools declare `confirm_token` (string); `list` and `get` do not. All seven declare `additionalProperties: false`. Required sets: `list` `[game_id]`; `get` `[game_id, webhook_id]`; `create` `[game_id, name, key, url_template, request_method]`; `clone` `[game_id, webhook_id]`; `update` `[game_id, webhook_id]`; `status` `[game_id, webhook_id, target]`; `test` `[game_id, webhook_id]`. `name` and `key` have `maxLength: 50`; `description` `maxLength: 255`; `url_template` `maxLength: 256`; `request_method` `enum` `[GET, POST, PUT, PATCH]`; `deprecation_reason` `maxLength: 128`; `target` `enum` `[ACTIVE, DEPRECATED, DELETED]`; `status` items `enum` `[DRAFT, ACTIVE, DEPRECATED]`; `page_size` `minimum: 1`, `maximum: 100`; `fields` items require `[name, fieldType, order]` with `additionalProperties: false`, `fieldType` an `enum` of 13 values without `UNKNOWN`, `placeholderType` `enum` `[COMMON, PERSONALIZED]`; `create.headers` values are `string`, `update.headers` values are `["string", "null"]` |
| `pre-04` | `tools/list` — descriptions | Record verbatim: the sentence of `kinoa_webhook_list` that starts "It does NOT carry the request definition"; the words "DELETE is not offered" in `kinoa_webhook_create`; the sentence of `kinoa_webhook_update` about `fields` being "replaced WHOLE"; the sentence of `kinoa_webhook_status` that `DEPRECATED` "is TERMINAL"; the sentences of `kinoa_webhook_test` about "10 calls a minute" and about a 200 whose body is `{"error": "..."}`. `Record: DESCRIPTIONS` |
| `pre-05` | `kinoa_system_ping {}` | `ok: true`; `data.userId` present. `Record: USER_ID` |
| `pre-06` | `kinoa_games_list {}` | Both `P1` and `P2` are in the result with exactly these ids. If one is missing, every later case on that game is `BLOCKED` |
| `pre-07` | 1. `kinoa_webhook_list {"game_id": P1, "page_size": 100}` 2. `kinoa_webhook_list {"game_id": P2, "response_format": "detailed", "page_size": 100}` | 1. `ok: true`; `Record: BASE_P1` = `data.totalItems` (expected `0`; a higher number is a leftover of an earlier run — record the names). 2. `ok: true`; `data.totalItems` ≥ 5; one item has `id` = `P2_ACTIVE`, `name` = `test`, `status` = `ACTIVE`. `Record: P2_TOTAL` = `data.totalItems`. If `P2_ACTIVE` is missing, every case that names it is `BLOCKED` |
| `pre-08` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-seed-a", "key": "KEY_seed_a", "url_template": "TARGET/qa/seed-a", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` | `ok: true`; `data.status` = `preview`; `data.tool` = `kinoa_webhook_create`; `data.intendedChange` = `{"name": "NAME-seed-a", "key": "KEY_seed_a", "status": "DRAFT", "call": "POST TARGET/qa/seed-a", "fieldCount": 1}`; `data.message` = `Will create DRAFT webhook 'NAME-seed-a' calling POST TARGET/qa/seed-a.`; `meta.confirmToken` present; `meta.dryRun` = `false`; `meta.expiresAt` about 10 minutes ahead. `Record: DRY_RUN` = `meta.dryRun`, `TOKEN_SEED_A` = `meta.confirmToken`. If `DRY_RUN` is `true`, every executing leg of this plan is `BLOCKED — writes disabled server-side (dry-run)` |
| `pre-09` | the `initialize` result — its `instructions` field (read it once, verbatim) | The text names all seven webhook tools and says that the listing "does NOT carry the request definition", that the copy "is DRAFT too", that `fields` "replaces the whole placeholder set", and that `kinoa_webhook_test` "makes an ACTUAL HTTP call". A missing tool name is a `FAIL` graded `minor` (H15). `Record: INSTRUCTIONS`. `BLOCKED — the connector does not show the initialize result` if the field cannot be read |
| `pre-10` | the call of `pre-08` plus `"confirm_token": TOKEN_SEED_A` | `ok: true`; `data.webhook.id` present; `data.webhook.status` = `DRAFT`; `data.webhook.name` = `NAME-seed-a`; `data.webhook.key` = `KEY_seed_a`; `data.webhook.urlTemplate` = `TARGET/qa/seed-a`; `data.webhook.requestMethod` = `POST`; `data.webhook.json` = the string of `JSON_1`; `data.webhook.fields` has one item with `name` = `event`, `fieldType` = `STRING`, `order` = `1`. `Record: SEED_A` (the `id`) |
| `pre-11` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-seed-b", "key": "KEY_seed_b", "url_template": "TARGET/qa/seed-b", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` from step 1 3. `kinoa_webhook_create {"game_id": P1, "name": "NAME-seed-c", "key": "KEY_seed_c", "url_template": "TARGET/qa/seed-c", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 4. the same plus `confirm_token` from step 3 | 2. `ok: true`; `data.webhook.status` = `DRAFT`. `Record: SEED_B`. 4. `ok: true`; `data.webhook.status` = `DRAFT`. `Record: SEED_C` |
| `pre-12` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": SEED_B, "target": "ACTIVE"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` | 1. `ok: true`; a preview; `data.intendedChange.currentStatus` = `DRAFT`; `data.intendedChange.target` = `ACTIVE`. 2. `ok: true`; `data.webhookId` = `SEED_B`; `data.target` = `ACTIVE`; `data.previousStatus` = `DRAFT`; `data.applied` = `true`. 3. `data.webhook.status` = `ACTIVE` |
| `pre-13` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": SEED_C, "target": "DEPRECATED", "deprecation_reason": "qa seed fixture"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | 1. `ok: true`; a preview; `data.warnings` contains `Deprecation is terminal: webhook 'NAME-seed-c' can never be reactivated, only cloned.` 2. `ok: true`; `data.target` = `DEPRECATED`; `data.previousStatus` = `DRAFT`; `data.applied` = `true`. 3. `data.webhook.status` = `DEPRECATED`; `data.webhook.deprecationReason` = `qa seed fixture`; `data.webhook.deprecationInitiatorId` present (H5) |

## A1. `kinoa_webhook_list`

Covers the AC bullet "kinoa_webhook_list returns webhooks in the unified pagination envelope with
server-side search (response_format: concise | detailed); the compact view carries urlTemplate,
method, headers, json and fields". `list-ok-01` and `list-ok-02` settle H1. The subjects are the
three seeds of §A0 and the pre-existing webhooks of `P2`. `TOTAL_P1` is `BASE_P1` + 3.
`list-sem-04` to `list-sem-08` settle H14. `list-sem-12` is the baseline of the delete
determination in §A6.

| Id | Call | Expected |
|---|---|---|
| `list-ok-01` | `kinoa_webhook_list {"game_id": P1}` | `ok: true`; `data.page` = `1`; `data.pageSize` = `20`; `data.totalItems` = `TOTAL_P1`; `data.totalPages` = `1`; `data.hasMore` = `false`; `data.responseFormat` = `concise`. Every item has `id`, `name`, `key`, `status`, `urlTemplate`. `SEED_A` has `status` = `DRAFT`, `SEED_B` `ACTIVE`, `SEED_C` `DEPRECATED`; their `urlTemplate` values are `TARGET/qa/seed-a`, `-b`, `-c`. Record whether any item carries `requestMethod`, `headers`, `json` or `fields` — expected today: none does, a `FAIL` of the AC clause (H1). `Record: TOTAL_P1` |
| `list-ok-02` | `kinoa_webhook_list {"game_id": P1, "response_format": "detailed"}` | `ok: true`; `data.responseFormat` = `detailed`; the same ids as `list-ok-01`; every item has `createdTs` (number), `updatedTs` (number), `authorId`, `updatedAuthorId`; the `SEED_C` item has `deprecationReason` = `qa seed fixture` and `deprecationInitiatorId`; no item has `requestMethod`, `headers`, `json` or `fields` (H1) |
| `list-sem-01` | `kinoa_webhook_list {"game_id": P1, "page": 1, "page_size": 1}` | Exactly one item; `data.pageSize` = `1`; `data.totalItems` = `TOTAL_P1`; `data.totalPages` = `TOTAL_P1`; `data.hasMore` = `true`. `Record: FIRST` (its `id`) |
| `list-sem-02` | `kinoa_webhook_list {"game_id": P1, "page": 2, "page_size": 1}` | Exactly one item and its `id` differs from `FIRST`; `data.page` = `2` |
| `list-sem-03` | `kinoa_webhook_list {"game_id": P1, "page": 9999, "page_size": 1}` | `ok: true`; `data.items` = `[]`; `data.hasMore` = `false`; `data.totalItems` = `TOTAL_P1` |
| `list-sem-04` | `kinoa_webhook_list {"game_id": P1, "search": "seed-"}` | `ok: true`; exactly three items: `SEED_A`, `SEED_B`, `SEED_C`; every `name` contains `seed-`; `data.totalItems` = `3` |
| `list-sem-05` | `kinoa_webhook_list {"game_id": P1, "search": "SEED-A"}` | `OBSERVED`: record whether `SEED_A` is returned (the search ignores case) or `data.items` = `[]` (it does not). No error (H14) |
| `list-sem-06` | `kinoa_webhook_list {"game_id": P1, "search": SEED_A}` (the id as the search text) | `ok: true`; exactly one item and its `id` = `SEED_A` (an exact id matches). `data.items` = `[]` is a `FAIL` of the tool description (H14) |
| `list-sem-07` | `kinoa_webhook_list {"game_id": P1, "key": "seed_b"}` | `ok: true`; exactly one item, `id` = `SEED_B`; `data.totalItems` = `1` |
| `list-sem-08` | `kinoa_webhook_list {"game_id": P1, "search": "zzz-no-such-webhook-zzz"}` | `ok: true`; `data.items` = `[]`; `data.totalItems` = `0`; `data.totalPages` = `0`; `data.hasMore` = `false` |
| `list-sem-09` | `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT"], "page_size": 100}` | Every item has `status` = `DRAFT`; `SEED_A` is present; `SEED_B` and `SEED_C` are absent |
| `list-sem-10` | `kinoa_webhook_list {"game_id": P1, "status": ["ACTIVE"], "page_size": 100}` | Every item has `status` = `ACTIVE`; `SEED_B` is present; `SEED_A` and `SEED_C` are absent |
| `list-sem-11` | `kinoa_webhook_list {"game_id": P1, "status": ["DEPRECATED"], "page_size": 100}` | Every item has `status` = `DEPRECATED`; `SEED_C` is present; `SEED_A` and `SEED_B` are absent (H5) |
| `list-sem-12` | `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT", "ACTIVE", "DEPRECATED"], "page_size": 100}` | `data.totalItems` = `TOTAL_P1` (the unfiltered listing hides no status); the sum of the `totalItems` of `list-sem-09`, `-10`, `-11` = `TOTAL_P1` |
| `list-sem-13` | `kinoa_webhook_list {"game_id": P1, "search": "seed-", "status": ["ACTIVE"]}` | Exactly one item, `id` = `SEED_B` (the filters combine) |
| `list-schema-01` | `kinoa_webhook_list {}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; one violation with `rule` = `input_schema`, no `path`, text names `game_id`; no `data` |
| `list-schema-02` | `kinoa_webhook_list {"game_id": P1, "page_size": 101}` | `ok: false`; `VALIDATION_FAILED`; the violation `path` = `/page_size` |
| `list-schema-03` | `kinoa_webhook_list {"game_id": P1, "page_size": 0}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/page_size` |
| `list-schema-04` | `kinoa_webhook_list {"game_id": P1, "page": 0}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/page` |
| `list-schema-05` | `kinoa_webhook_list {"game_id": P1, "response_format": "full"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/response_format` |
| `list-schema-06` | `kinoa_webhook_list {"game_id": P1, "status": ["DELETED"]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/status/0` (`DELETED` is a lifecycle target, not a listing status) |
| `list-schema-07` | `kinoa_webhook_list {"game_id": P1, "status": "DRAFT"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/status` (a string where an array is declared). `BLOCKED` if the connector refuses to send a string for an array argument |
| `list-schema-08` | `kinoa_webhook_list {"game_id": P1, "foo": "bar"}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `foo` |
| `list-schema-09` | `kinoa_webhook_list {"game_id": P1, "confirm_token": "x"}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `confirm_token` (a read tool has no such argument) |
| `list-gap-01` | `kinoa_webhook_list {"game_id": P1, "search": "' OR 1=1 --"}` | `ok: true`; `data.items` = `[]`; no error text |
| `list-gap-02` | `kinoa_webhook_list {"game_id": P1, "search": "%"}` | `OBSERVED`: record whether `data.items` is empty or equals the unfiltered listing (a `LIKE` wildcard reaching the database). Never `TOOL_EXECUTION_FAILED` |
| `list-gap-03` | `kinoa_webhook_list {"game_id": P1, "search": "", "key": ""}` | `ok: true`; the same items as `list-ok-01` (blank filters are dropped) |
| `list-gap-04` | `kinoa_webhook_list {"game_id": P1, "status": []}` | `ok: true`; the same items as `list-ok-01` (an empty filter is no filter) |
| `list-iso-01` | `kinoa_webhook_list {"game_id": FOREIGN}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED`; message `You do not have access to game '00000000-0000-4000-8000-0000000000ff'`; no `data` |
| `list-iso-02` | `kinoa_webhook_list {"game_id": ""}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED`; message `Tool 'kinoa_webhook_list' requires a game argument` |
| `list-iso-03` | `kinoa_webhook_list {"game_id": P2, "page_size": 100}` | `ok: true`; `data.totalItems` = `P2_TOTAL`; `P2_ACTIVE` is present with `status` = `ACTIVE`; no item has a `name` starting with `NAME` (nothing of this run leaked into `P2`) |
| `list-iso-04` | `kinoa_webhook_list {"game_id": P1, "search": P2_ACTIVE}` | `ok: true`; `data.items` = `[]` (an id of another game does not resolve in `P1`) |
| `list-iso-05` | `kinoa_webhook_list {"game_id": " <P1_GAME_ID> "}` (one space before and after) | `ok: true`; the same items as `list-ok-01` (the id is trimmed before the call) |

## A2. `kinoa_webhook_get`

Covers the AC clause "kinoa_webhook_get returns the full webhook" and is the second half of H1:
the definition the listing lacks must be here. The subjects are the three seeds and `P2_ACTIVE`;
nothing is written. `get-iso-02` and `get-iso-03` settle H12 for reads.

| Id | Call | Expected |
|---|---|---|
| `get-ok-01` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` | `ok: true`; `data.webhook.id` = `SEED_A`; `name` = `NAME-seed-a`; `key` = `KEY_seed_a`; `status` = `DRAFT`; `urlTemplate` = `TARGET/qa/seed-a`; `requestMethod` = `POST`; `json` = the string of `JSON_1`; `fields` = one item with `name` = `event`, `fieldType` = `STRING`, `placeholderType` = `COMMON`, `required` = `true`, `order` = `1`; `createdTs` and `updatedTs` are numbers; `authorId` and `updatedAuthorId` present; no `deprecationReason`, no `deprecationInitiatorId`. Record whether `headers` is present (the create sent none) |
| `get-ok-02` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | `ok: true`; `status` = `DEPRECATED`; `deprecationReason` = `qa seed fixture`; `deprecationInitiatorId` present; the definition (`urlTemplate`, `requestMethod`, `json`, `fields`) is still returned in full (H5: the row stays) |
| `get-sem-01` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` | `ok: true`; `status` = `ACTIVE`; `updatedTs` ≥ `createdTs`; `json` and `fields` equal those of `get-ok-01` (activation changed nothing but the status) |
| `get-sem-02` | 1. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` 2. the same call again | `data.webhook` of step 2 equals `data.webhook` of step 1 member by member, `fields` in the same order (two reads of one unchanged webhook do not differ) |
| `get-sem-03` | `kinoa_webhook_get {"game_id": P2, "webhook_id": P2_ACTIVE}` | `ok: true`; `data.webhook.id` = `P2_ACTIVE`; `name` = `test`; `status` = `ACTIVE`. `OBSERVED`: record `urlTemplate` (on 2026-09-16 it was the word `test`, not a URL — pre-existing data the service accepted before the URL rule; a note, not a finding) |
| `get-schema-01` | `kinoa_webhook_get {"game_id": P1}` | `ok: false`; `VALIDATION_FAILED`; one violation, no `path`, text names `webhook_id` |
| `get-schema-02` | `kinoa_webhook_get {"webhook_id": SEED_A}` | `ok: false`; `VALIDATION_FAILED`; one violation, no `path`, text names `game_id` |
| `get-schema-03` | `kinoa_webhook_get {"game_id": P1, "webhook_id": 123}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/webhook_id`. `BLOCKED` if the connector refuses to send a number for a string argument |
| `get-schema-04` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A, "response_format": "detailed"}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `response_format` (the get tool has no format argument) |
| `get-gap-01` | `kinoa_webhook_get {"game_id": P1, "webhook_id": ""}` | `ok: false`; either `VALIDATION_FAILED` with a `webhook_not_found` violation on `webhook_id`, or a schema rejection. `TOOL_EXECUTION_FAILED` is a `FAIL` (a blank id turns the request into `GET /webhooks/`, which is the listing, and the tool cannot read a list as one webhook) |
| `get-gap-02` | `kinoa_webhook_get {"game_id": P1, "webhook_id": " SEED_A "}` (one space before and after the id) | `ok: true`; `data.webhook.id` = `SEED_A` (the id is trimmed) |
| `get-gap-03` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A in UPPER CASE}` | `OBSERVED`: record whether the service resolves the id regardless of case (`ok: true`) or answers `webhook_not_found`. Never `TOOL_EXECUTION_FAILED` |
| `get-iso-01` | `kinoa_webhook_get {"game_id": P1, "webhook_id": NO_SUCH}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; one violation with `path` = `webhook_id`, `rule` = `webhook_not_found`, `got` = `NO_SUCH`, `hint` = `No webhook '00000000-0000-4000-8000-00000000dead' found in game '<P1_GAME_ID>'; check kinoa_webhook_list` |
| `get-iso-02` | `kinoa_webhook_get {"game_id": P1, "webhook_id": P2_ACTIVE}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` on `webhook_id` naming `P2_ACTIVE` and game `P1`. An `ok: true` that returns the webhook `test` of `P2` is a **critical** `FAIL` (H12) |
| `get-iso-03` | `kinoa_webhook_get {"game_id": P2, "webhook_id": SEED_A}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `SEED_A` and game `P2` (H12) |
| `get-iso-04` | `kinoa_webhook_get {"game_id": FOREIGN, "webhook_id": SEED_A}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED`; message `You do not have access to game '00000000-0000-4000-8000-0000000000ff'` (the game check runs before the read) |
| `get-iso-05` | `kinoa_webhook_get {"game_id": "<P1_GAME_ID_UPPERCASE>", "webhook_id": SEED_A}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED` (the claim is compared as text). Not `AUTHORIZATION_UNAVAILABLE` |

## A3. `kinoa_webhook_create`

Covers the AC bullet "kinoa_webhook_create creates the same webhooks with the same parameter set
as the dashboard UI — no more, no less: … the new webhook starts as DRAFT" (H2, H17, H18) and the
placeholder rules of the tool description (H13). The subjects are `MAIN`, `FULL`, `PERS`, `GETM`
and `GETJ`, all new. The create preview is built from the arguments and reaches no service, so
every content rule is refused on the **confirm** leg, and a refused confirm still spends one write
of the budget: pause 60 s after every 8 executing legs of this section (the `ok` and `rule` rows
together). Every `rule` row ends with a listing that proves nothing was created.

| Id | Call | Expected |
|---|---|---|
| `create-ok-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-main", "key": "KEY_main", "url_template": "TARGET/qa/main", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 2>}` | 1. `ok: true`; `data.status` = `preview`; `data.intendedChange.status` = `DRAFT`; `data.intendedChange.fieldCount` = `1`; `meta.confirmToken` present. 2. `ok: true`; `data.webhook.id` present; `status` = `DRAFT` (H17); `name` = `NAME-main`; `key` = `KEY_main`; `urlTemplate` = `TARGET/qa/main`; `requestMethod` = `POST`; `json` = the string of `JSON_1`; `fields[0]` has `name` = `event`, `fieldType` = `STRING`, `placeholderType` = `COMMON`, `required` = `true`, `order` = `1` — the AC says `required — default true`, so an absent or `false` `required` is a `FAIL`. `Record: MAIN`. 3. `data.webhook` equals `data.webhook` of step 2 member by member |
| `create-ok-02` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-full", "key": "KEY_full", "type": "qa-full", "description": "full parameter set", "url_template": "TARGET/qa/full", "request_method": "POST", "headers": HEADERS_FULL, "json": JSON_FULL, "fields": FIELDS_FULL}` 2. `kinoa_webhook_list {"game_id": P1, "search": "full"}` 3. the call of step 1 plus `confirm_token` 4. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 3>}` | 1. `ok: true`; a preview; `data.intendedChange.fieldCount` = `4`; `data.intendedChange.call` = `POST TARGET/qa/full`. 2. `data.items` = `[]` (the preview created nothing). 3. `ok: true`; `status` = `DRAFT`; `type` = `qa-full`; `description` = `full parameter set`; `headers` = `HEADERS_FULL`; `json` = the string of `JSON_FULL`; `fields` has 4 items in `order` 1, 2, 3, 4: `event` (`STRING`, `COMMON`, `description` = `event name`, `required` = `true`), `amount` (`NUMBER`, `required` = `false`, `defaultValue` = the number `12`), `vip` (`BOOLEAN`, `required` = `true`), `run` (`STRING`, `required` = `false`, `defaultValue` = `qa`). `Record: FULL`. 4. equals step 3 |
| `create-ok-03` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-pers", "key": "KEY_pers", "url_template": "TARGET/qa/pers", "request_method": "POST", "json": JSON_PERS, "fields": FIELDS_PERS}` 2. the same plus `confirm_token` | 2. `ok: true`; `status` = `DRAFT`; `fields` has two items; the item `playerName` has `placeholderType` = `PERSONALIZED`; `json` = the string of `JSON_PERS`. `Record: PERS`. If the service refuses, quote its violation: the AC lists `placeholderType: COMMON | PERSONALIZED`, so a refusal of a well-formed PERSONALIZED field is a `FAIL` unless the violation says the name must match a player field — then `OBSERVED` and a note (H18) |
| `create-ok-04` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-get", "key": "KEY_get", "url_template": "TARGET/qa/get/${event}", "request_method": "GET", "fields": FIELDS_1}` 2. the same plus `confirm_token` | 1. `data.intendedChange.call` = `GET TARGET/qa/get/${event}`. 2. `ok: true`; `status` = `DRAFT`; `requestMethod` = `GET`; `urlTemplate` = `TARGET/qa/get/${event}`; no `json` (or `json` = `null`). `Record: GETM` |
| `create-sem-01` | `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT"], "search": "NAME-"}` | `MAIN`, `FULL`, `PERS`, `GETM` are all present with `status` = `DRAFT`; `data.totalItems` = 5 (the four plus `SEED_A`) |
| `create-sem-02` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-min", "key": "KEY_min", "url_template": "TARGET/qa/min", "request_method": "POST"}` (no `json`, no `fields`, no `headers`) 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 2>}` | 1. a preview with `data.intendedChange.fieldCount` = `0`. 2. `ok: true`; `status` = `DRAFT`. `Record: MIN`. 3. `fields` is `[]` or absent; `json` and `headers` absent or `null` — record which (the minimum webhook the dashboard allows). If the service refuses a webhook without fields, quote the violation and grade `OBSERVED` |
| `create-schema-01` | `kinoa_webhook_create {"game_id": P1, "key": "KEY_s1", "url_template": "TARGET/qa/s1", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; one violation, no `path`, text names `name`; no `meta.confirmToken` |
| `create-schema-02` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s2", "key": "KEY_s2", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; no `path`; text names `url_template` |
| `create-schema-03` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s3", "key": "KEY_s3", "url_template": "TARGET/qa/s3", "request_method": "DELETE"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/request_method` (`DELETE` is deliberately not offered) |
| `create-schema-04` | `kinoa_webhook_create {"game_id": P1, "name": S51, "key": "KEY_s4", "url_template": "TARGET/qa/s4", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/name` |
| `create-schema-05` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s5", "key": S51, "url_template": "TARGET/qa/s5", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/key` |
| `create-schema-06` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s6", "key": "KEY_s6", "url_template": U257, "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/url_template` |
| `create-schema-07` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s7", "key": "KEY_s7", "description": S256, "url_template": "TARGET/qa/s7", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/description` |
| `create-schema-08` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s8", "key": "KEY_s8", "url_template": "TARGET/qa/s8", "request_method": "POST", "security": {"type": "none"}}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `security`. Expected today; graded against the AC parameter list as a `FAIL` (H2) whose severity the report explains |
| `create-schema-09` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s9", "key": "KEY_s9", "url_template": "TARGET/qa/s9", "request_method": "POST", "json": JSON_1, "fields": [{"name": "event", "fieldType": "STRING"}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0`; text names `order` |
| `create-schema-10` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s10", "key": "KEY_s10", "url_template": "TARGET/qa/s10", "request_method": "POST", "json": JSON_1, "fields": [{"name": "event", "fieldType": "UNKNOWN", "order": 1}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0/fieldType` |
| `create-schema-11` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s11", "key": "KEY_s11", "url_template": "TARGET/qa/s11", "request_method": "POST", "json": JSON_1, "fields": [{"name": "event", "fieldType": "STRING", "placeholderType": "PLAYER", "order": 1}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0/placeholderType` |
| `create-schema-12` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s12", "key": "KEY_s12", "url_template": "TARGET/qa/s12", "request_method": "POST", "json": JSON_1, "fields": [{"name": "event", "fieldType": "STRING", "order": 1, "foo": 1}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0`; text names `foo` |
| `create-schema-13` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s13", "key": "KEY_s13", "url_template": "TARGET/qa/s13", "request_method": "POST", "headers": {"X-Count": 5}}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/headers/X-Count` (header values are strings) |
| `create-schema-14` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s14", "key": "KEY_s14", "url_template": "TARGET/qa/s14", "request_method": "POST", "json": JSON_1, "fields": [{"name": "event", "fieldType": "STRING", "required": "yes", "order": 1}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0/required`. `BLOCKED` if the connector refuses to send a string for a boolean |
| `create-schema-15` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-s15", "key": "KEY_s15", "url_template": "TARGET/qa/s15", "request_method": "POST", "fields": "event"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields`. `BLOCKED` if the connector refuses to send a string for an array |
| `create-rule-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-main", "key": "KEY_dup_name", "url_template": "TARGET/qa/r1", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "key": "dup_name"}` | 1. a preview (the tool does not check names). 2. `ok: false`; `error.code` = `VALIDATION_FAILED`; a violation whose `path` is `name` (or `request` with `rule` = `backend_rejected`) and whose `hint` quotes the service's text; never `TOOL_EXECUTION_FAILED`. 3. `data.items` = `[]` |
| `create-rule-02` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-dup-key", "key": "KEY_main", "url_template": "TARGET/qa/r2", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "dup-key"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `key` (or `request`/`backend_rejected`) naming the duplicate. 3. `data.items` = `[]` |
| `create-rule-03` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r3", "key": "KEY_r3", "url_template": "TARGET/qa/r3", "request_method": "POST", "json": "{\"event\": \"${event}\", \"ghost\": \"${ghost}\"}", "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r3"}` | 2. `ok: false`; `VALIDATION_FAILED`; the violation names the undeclared placeholder `ghost` in its `hint` (a reference nobody declares). 3. `data.items` = `[]` |
| `create-rule-04` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r4", "key": "9KEY_r4", "url_template": "TARGET/qa/r4", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r4"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `key` (the key must start with a letter, H13). An `ok: true` is a `FAIL` of the schema's own description of `key`; then record the id as `R4` for section 9. 3. `data.items` = `[]` unless step 2 succeeded |
| `create-rule-05` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r5", "key": "KEY_r5", "url_template": "TARGET/qa/r5", "request_method": "POST", "json": JSON_1, "fields": FIELDS_2}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r5"}` | 2. `ok: false`; `VALIDATION_FAILED`; the violation names the unreferenced field `extra` (a declared field nobody references). 3. `data.items` = `[]` |
| `create-rule-06` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r6", "key": "KEY_r6", "url_template": "not a url at all", "request_method": "POST"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r6"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `urlTemplate` (or `request`/`backend_rejected`) saying the URL is not absolute http(s). 3. `data.items` = `[]`. If step 2 is `ok: true`, record `R6` for section 9 and grade `FAIL` against the schema's description "Absolute http(s) URL" |
| `create-rule-07` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r7", "key": "KEY_r7", "url_template": "TARGET/qa/r7", "request_method": "POST", "json": "{\"event\": ${event}, }", "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r7"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `json` saying the body does not parse as JSON. 3. `data.items` = `[]` |
| `create-rule-08` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r8", "key": "KEY_r8", "url_template": "TARGET/qa/r8", "request_method": "POST", "json": "{\"when\": ${when}}", "fields": [{"name": "when", "fieldType": "DATE", "order": 1}]}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r8"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation saying a `DATE` field cannot be used inside the json body (it renders unquoted). 3. `data.items` = `[]`. An `ok: true` is `OBSERVED` with a note: the tool description forbids it, the service allowed it; record `R8` |
| `create-rule-09` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r9", "key": "KEY_r9", "url_template": "TARGET/qa/r9", "request_method": "POST", "headers": {"X-Blank": ""}}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r9"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `headers` (values "must not be blank"). 3. `data.items` = `[]` |
| `create-rule-10` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r10", "key": "KEY_r10", "url_template": "TARGET/qa/r10", "request_method": "POST", "json": "{\"player\": \"${playerName}\"}", "fields": [{"name": "playerName", "fieldType": "STRING", "placeholderType": "PERSONALIZED", "order": 1}]}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r10"}` | 2. `ok: false`; `VALIDATION_FAILED` (a PERSONALIZED field referenced with the `${}` syntax: "The two syntaxes are not interchangeable"). 3. `data.items` = `[]`. An `ok: true` is a `FAIL` of the tool description; record `R10` |
| `create-rule-11` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-r11", "key": "KEY_r11", "url_template": "TARGET/qa/r11", "request_method": "POST", "json": "{\"amount\": ${amount}}", "fields": [{"name": "amount", "fieldType": "NUMBER", "required": false, "default": "12", "order": 1}]}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-r11"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on the field's default ("a NUMBER default is the number 12, not the string '12'"). 3. `data.items` = `[]`. An `ok: true` is a `FAIL` of the schema's description of `default`; record `R11` |
| `create-gap-01` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-" + 27 × "n", "key": "KEY_" + 23 × "k", "url_template": "TARGET/qa/g1", "request_method": "POST"}` — no token, never confirmed | `ok: true`; a preview (exactly 50 characters pass the schema on both `name` and `key`); `meta.confirmToken` present |
| `create-gap-02` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-g2", "key": "KEY_g2", "url_template": U256, "request_method": "POST"}` — never confirmed | `ok: true`; a preview (256 characters pass the schema) |
| `create-gap-03` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-g3", "key": "KEY_g3", "description": S255, "url_template": "TARGET/qa/g3", "request_method": "POST"}` — never confirmed | `ok: true`; a preview (255 characters pass) |
| `create-gap-04` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-getj", "key": "KEY_getj", "url_template": "TARGET/qa/getj", "request_method": "GET", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` | 2. `OBSERVED`: either `ok: true` with `requestMethod` = `GET` and the `json` kept (record `GETJ` for section 9), or `VALIDATION_FAILED` refusing a body on GET. Never `TOOL_EXECUTION_FAILED` |
| `create-gap-05` | `kinoa_webhook_create {"game_id": P1, "name": "  NAME-g5  ", "key": "KEY_g5", "url_template": "TARGET/qa/g5", "request_method": "POST"}` — never confirmed | `ok: true`; `data.intendedChange.name` = `NAME-g5` without the spaces (string arguments are trimmed before use) |
| `create-gap-06` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-g6", "key": "KEY_g6", "type": "🎉 emoji / spaces / 'quotes'", "url_template": "TARGET/qa/g6", "request_method": "POST"}` — never confirmed | `ok: true`; a preview (`type` is free-form and not validated) |
| `create-iso-01` | `kinoa_webhook_create {"game_id": FOREIGN, "name": "NAME-i1", "key": "KEY_i1", "url_template": "TARGET/qa/i1", "request_method": "POST"}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED`; no `meta.confirmToken` (the permission check runs before the write gate) |
| `create-iso-02` | `kinoa_webhook_create {"game_id": P2, "name": "NAME-i2", "key": "KEY_i2", "url_template": "TARGET/qa/i2", "request_method": "POST"}` — never confirmed | `ok: true`; a preview with a token (the account may write to `P2`; nothing is created because the token is never used) |

## A4. `kinoa_webhook_clone`

Covers the AC bullet "kinoa_webhook_clone clones a webhook (the existing copy endpoint)". The
sources are the three seeds, which are not written by a clone; the copies are `CLONE_A`,
`CLONE_B` and `CLONE_C`. `clone-ok-03` is the revival path of the tool description. The clone
preview reads the source, so an unknown id fails before a token (`clone-iso-01`, H12).

| Id | Call | Expected |
|---|---|---|
| `clone-ok-01` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 2>}` | 1. `ok: true`; `data.status` = `preview`; `data.intendedChange` = `{"sourceId": SEED_A, "sourceName": "NAME-seed-a", "name": "(a free copy of the source name)", "key": "(a free copy of the source key)", "status": "DRAFT"}`; `data.message` = `Will copy webhook 'NAME-seed-a' as a new DRAFT.` 2. `ok: true`; `data.webhook.id` ≠ `SEED_A`; `status` = `DRAFT`; `name` ≠ `NAME-seed-a`; `key` ≠ `KEY_seed_a`; `urlTemplate` = `TARGET/qa/seed-a`; `requestMethod` = `POST`; `json` = the string of `JSON_1`; `fields` equal `SEED_A`'s. `Record: CLONE_A` (id, name and key — the report cites the derived name). 3. equals step 2 |
| `clone-ok-02` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_B, "name": "NAME-clone-b", "key": "KEY_clone_b"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` | 1. `data.intendedChange.name` = `NAME-clone-b`; `data.intendedChange.key` = `KEY_clone_b`; `data.intendedChange.sourceName` = `NAME-seed-b`. 2. `ok: true`; `status` = `DRAFT` (the source is ACTIVE, the copy is not); `name` = `NAME-clone-b`; `key` = `KEY_clone_b`; `urlTemplate`, `requestMethod`, `json`, `fields` equal `SEED_B`'s. `Record: CLONE_B`. 3. `SEED_B` still has `status` = `ACTIVE`, `name` = `NAME-seed-b` (the source is untouched) |
| `clone-ok-03` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_C, "name": "NAME-clone-c", "key": "KEY_clone_c"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | 2. `ok: true`; `status` = `DRAFT`; no `deprecationReason` and no `deprecationInitiatorId` on the copy; the definition equals `SEED_C`'s. `Record: CLONE_C`. 3. `SEED_C` still `DEPRECATED` with `deprecationReason` = `qa seed fixture` |
| `clone-sem-01` | `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT"], "page_size": 100}` | `CLONE_A`, `CLONE_B`, `CLONE_C` are present with `status` = `DRAFT` |
| `clone-sem-02` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A}` 2. the same plus `confirm_token` | 2. `ok: true`; a second copy with an `id` ≠ `CLONE_A` and a `name` ≠ `CLONE_A`'s name and `key` ≠ `CLONE_A`'s key (the service finds another free variant; `idempotentHint: false`). `Record: CLONE_A2` for section 9. A `VALIDATION_FAILED` on `name` or `key` is a `FAIL` of the tool description ("derives a free "copy" variant") |
| `clone-schema-01` | `kinoa_webhook_clone {"game_id": P1}` | `ok: false`; `VALIDATION_FAILED`; no `path`; text names `webhook_id`; no token |
| `clone-schema-02` | `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "name": S51}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/name` |
| `clone-schema-03` | `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "url_template": "TARGET/qa/other"}` | `ok: false`; `VALIDATION_FAILED`; text names `url_template` (a clone takes only `name` and `key`) |
| `clone-rule-01` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "name": "NAME-seed-a", "key": "KEY_ru1"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "key": "ru1"}` | 1. a preview. 2. `ok: false`; `VALIDATION_FAILED`; a violation on `name` (or `request`/`backend_rejected`) naming the duplicate. 3. `data.items` = `[]` |
| `clone-rule-02` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "name": "NAME-ru2", "key": "KEY_seed_a"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-ru2"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `key`. 3. `data.items` = `[]` |
| `clone-rule-03` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "name": "NAME-ru3", "key": "9KEY_ru3"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-ru3"}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `key` (H13). 3. `data.items` = `[]` unless step 2 succeeded (then record `RU3`) |
| `clone-gap-01` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A, "name": ""}` 2. the same plus `confirm_token` | 1. `data.intendedChange.name` = `` (an empty text, not the "free copy" text — the tool sends what it was given). 2. `OBSERVED`: either `VALIDATION_FAILED` on `name`, or `ok: true` — then record the copy's `id`, `name` and `key` as `CLONE_BLANK` for section 9 and write a note. Never `TOOL_EXECUTION_FAILED` |
| `clone-gap-02` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": CLONE_A}` — never confirmed | `ok: true`; a preview whose `data.intendedChange.sourceName` is `CLONE_A`'s derived name (a copy can be copied) |
| `clone-iso-01` | `kinoa_webhook_clone {"game_id": P1, "webhook_id": NO_SUCH}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` on `webhook_id`; **no** `meta.confirmToken` (the source is read on the preview leg) |
| `clone-iso-02` | `kinoa_webhook_clone {"game_id": P1, "webhook_id": P2_ACTIVE}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `P2_ACTIVE` and game `P1`; no token (H12) |
| `clone-iso-03` | `kinoa_webhook_clone {"game_id": FOREIGN, "webhook_id": SEED_A}` | `ok: false`; `GAME_ACCESS_DENIED`; no token |
| `clone-iso-04` | `kinoa_webhook_clone {"game_id": P2, "webhook_id": SEED_A}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `SEED_A` and game `P2` (H12) |

## A5. `kinoa_webhook_update`

Covers the AC bullet "kinoa_webhook_update applies partial updates; nothing is silently lost"
(H7) and the freeze rule of the tool description (H11). `MAIN` is edited as a DRAFT; it leaves
this section renamed to `NAME-main-v2` / `KEY_main_v2`, with headers, two placeholders and method
`PUT`. `ACT_UPD` is created and activated here (`update-ok-08`) and is the only ACTIVE webhook
this section writes to — `SEED_B` receives previews only. `GETM` takes the empty-fields probe.
Every `rule` row ends with a read that proves nothing changed. Executing legs, refused ones
included: 15 — pause 60 s after every 8.

| Id | Call | Expected |
|---|---|---|
| `update-ok-01` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "type": "qa-main", "description": "edited as draft"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `ok: true`; `data.status` = `preview`; `data.intendedChange` = `{"webhookId": MAIN, "name": "NAME-main", "status": "DRAFT", "changes": ["type", "description"]}`; `data.message` = `Will update webhook 'NAME-main' (DRAFT): type, description.`; `data.warnings` has exactly one entry, starting `The preview does not hold webhook 'NAME-main'`; `meta.confirmToken` present. 2. `ok: true`; `data.webhook.type` = `qa-main`; `description` = `edited as draft`; `name`, `key`, `urlTemplate`, `requestMethod`, `json`, `fields` unchanged from `create-ok-01`. 3. equals step 2 |
| `update-ok-02` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "name": "NAME-main-v2", "key": "KEY_main_v2"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_list {"game_id": P1, "search": "main-v2"}` | 2. `ok: true`; `name` = `NAME-main-v2`; `key` = `KEY_main_v2`; `type` = `qa-main` and `description` = `edited as draft` are kept. 3. exactly one item, `id` = `MAIN` |
| `update-ok-03` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "headers": {"X-A": "a", "X-B": "b"}}` 2. the same plus `confirm_token` | 1. `data.intendedChange.changes` = `["headers"]`. 2. `ok: true`; `data.webhook.headers` = `{"X-A": "a", "X-B": "b"}` |
| `update-ok-04` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "headers": {"X-B": "b2", "X-C": "c"}}` 2. the same plus `confirm_token` | 2. `ok: true`; `headers` = `{"X-A": "a", "X-B": "b2", "X-C": "c"}` (merged member by member: `X-A` kept, `X-B` replaced, `X-C` added) |
| `update-ok-05` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "headers": {"X-A": null}}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 2. `ok: true`; `headers` = `{"X-B": "b2", "X-C": "c"}` (a `null` value removes that header). 3. the same `headers`. If `X-A` is still present, the removal was lost without an error — a `FAIL` (H7) |
| `update-ok-06` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "json": JSON_2, "fields": FIELDS_2}` 2. the same plus `confirm_token` | 1. `data.warnings` contains `fields replaces the whole placeholder set: the webhook will end up with exactly the placeholders sent here, and any not listed are removed.` and the "does not hold" sentence; no warning about a frozen member. 2. `ok: true`; `json` = the string of `JSON_2`; `fields` has two items, `event` (order 1) and `extra` (order 2), both `COMMON`, `required` = `true` |
| `update-ok-07` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "url_template": "TARGET/qa/main-v2", "request_method": "PUT"}` 2. the same plus `confirm_token` | 2. `ok: true`; `urlTemplate` = `TARGET/qa/main-v2`; `requestMethod` = `PUT`; `status` still `DRAFT` (a draft's url and method are free to change) |
| `update-ok-08` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-act-upd", "key": "KEY_act_upd", "url_template": "TARGET/qa/act-upd", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_status {"game_id": P1, "webhook_id": <id of step 2>, "target": "ACTIVE"}` 4. the same plus `confirm_token` 5. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 2>}` | 2. `ok: true`; `status` = `DRAFT`. `Record: ACT_UPD`. 4. `ok: true`; `data.applied` = `true`. 5. `status` = `ACTIVE` |
| `update-ok-09` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": ACT_UPD, "json": JSON_2, "fields": FIELDS_2}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 1. `data.intendedChange.status` = `ACTIVE`; `data.warnings` contains `This webhook is ACTIVE, so its existing placeholder fields are locked and only NEW ones may be added; a fields array that drops or alters an existing placeholder will be refused.` and the "replaces the whole placeholder set" sentence; no warning naming frozen members (`json` and `fields` are not frozen). 2. `ok: true`; `fields` has `event` and the NEW `extra`; `json` = the string of `JSON_2`. 3. `status` = `ACTIVE`; the same `fields`. A `VALIDATION_FAILED` here is a `FAIL` of the description "allows only NEW fields" (H11) |
| `update-ok-10` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": ACT_UPD, "description": "edited while active"}` 2. the same plus `confirm_token` | 1. `data.warnings` has exactly one entry (the "does not hold" sentence — `description` is not frozen). 2. `ok: true`; `description` = `edited while active`; `status` = `ACTIVE` |
| `update-sem-01` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `data.warnings` contains the "replaces the whole placeholder set" sentence. 2. `ok: true`; `fields` has exactly one item, `event`; `extra` is gone; `json` = the string of `JSON_1`. 3. the same. The loss is announced in step 1, so this is the documented behaviour (H7); a step 1 without that warning is a `FAIL` |
| `update-sem-02` | `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | `type` = `qa-main`; `description` = `edited as draft`; `headers` = `{"X-B": "b2", "X-C": "c"}`; `urlTemplate` = `TARGET/qa/main-v2`; `requestMethod` = `PUT`; `name` = `NAME-main-v2`; `key` = `KEY_main_v2`; `status` = `DRAFT` (every member set earlier survived the later partial updates that did not name it — nothing was lost by silence, H7) |
| `update-sem-03` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "description": "never confirmed"}` — no token, never confirmed 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `ok: true`; a preview. 2. `description` = `edited as draft` (the preview leg wrote nothing) |
| `update-sem-04` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": SEED_B, "url_template": "TARGET/qa/seed-b-moved", "headers": {"X-Q": "q"}}` — no token, never confirmed | `ok: true`; a preview; `data.intendedChange.status` = `ACTIVE`; `data.warnings` contains `This webhook is ACTIVE, and the service freezes url_template, headers once a webhook leaves DRAFT — the call will be refused naming those members. Clone it with kinoa_webhook_clone to change them.` (the caller's argument names, not the wire's) |
| `update-schema-01` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "request_method": "DELETE"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/request_method`; no token |
| `update-schema-02` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "headers": {"X-N": 7}}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/headers/X-N` (a header value is a string or `null`) |
| `update-schema-03` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "fields": [{"name": "event", "order": 1}]}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/fields/0`; text names `fieldType` |
| `update-schema-04` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "status": "ACTIVE"}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `status` (the status is not an argument of this tool; `kinoa_webhook_status` owns it) |
| `update-schema-05` | `kinoa_webhook_update {"game_id": P1, "description": "x"}` | `ok: false`; `VALIDATION_FAILED`; no `path`; text names `webhook_id` |
| `update-schema-06` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "name": S51}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/name` |
| `update-rule-01` | `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; one violation with `path` = `arguments`, `rule` = `no_changes`, `hint` = `Provide at least one field to change: name, key, type, description, url_template, request_method, headers, json, fields`; no `meta.confirmToken` |
| `update-rule-02` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": ACT_UPD, "url_template": "TARGET/qa/act-upd-moved"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 1. a preview whose `data.warnings` names `url_template` as frozen. 2. `ok: false`; `VALIDATION_FAILED`; a violation whose `path` is `urlTemplate` (or `request`/`backend_rejected`) quoting the service's refusal; never `TOOL_EXECUTION_FAILED`. 3. `urlTemplate` = `TARGET/qa/act-upd`. An `ok: true` in step 2 with the url changed is a `FAIL` of the tool description (H11) |
| `update-rule-03` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": ACT_UPD, "name": "NAME-act-upd-renamed"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `name` (frozen). 3. `name` = `NAME-act-upd` (H11) |
| `update-rule-04` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": ACT_UPD, "json": "{\"extra\": \"${extra}\"}", "fields": [{"name": "extra", "fieldType": "STRING", "order": 2}]}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 1. `data.warnings` contains the "existing placeholder fields are locked" sentence. 2. `ok: false`; `VALIDATION_FAILED` (the array drops the existing placeholder `event`). 3. `fields` still has `event` and `extra`; `json` = the string of `JSON_2` (H11) |
| `update-rule-05` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "json": "{\"event\": \"${event}\", \"ghost\": \"${ghost}\"}"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 2. `ok: false`; `VALIDATION_FAILED`; the violation names `ghost` (a reference nobody declares — the placeholder rules are the same as on create). 3. `json` = the string of `JSON_1` |
| `update-rule-06` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "key": "KEY_seed_a"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 2. `ok: false`; `VALIDATION_FAILED`; a violation on `key` (unique per game). 3. `key` = `KEY_main_v2` |
| `update-gap-01` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": SEED_C, "description": "edited while deprecated"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | 1. `data.intendedChange.status` = `DEPRECATED`; no frozen warning (`description` is not in the frozen list). 2. `OBSERVED`: either `VALIDATION_FAILED` (a DEPRECATED webhook accepts nothing) or `ok: true` with the description changed — record which. 3. `status` = `DEPRECATED` in both cases |
| `update-gap-02` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "headers": {"X-Nope": null}}` 2. the same plus `confirm_token` | 2. `ok: true`; `headers` = `{"X-B": "b2", "X-C": "c"}` (removing a header that does not exist changes nothing and is not an error) |
| `update-gap-03` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "description": null}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `data.intendedChange.changes` = `["description"]`. 2. `OBSERVED`: record whether `description` is now absent (an explicit `null` is a merge-patch removal) or unchanged, or whether the schema rejects `null` for `description`. Never `TOOL_EXECUTION_FAILED`. 3. the same as step 2 |
| `update-gap-04` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": GETM, "url_template": "TARGET/qa/get", "fields": []}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": GETM}` | 2. `OBSERVED`: either `ok: true` with `fields` = `[]` or absent and `urlTemplate` = `TARGET/qa/get`, or `VALIDATION_FAILED` if the service needs at least one field — record which. 3. consistent with step 2 |
| `update-gap-05` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": MAIN, "type": "qa-main"}` 2. the same plus `confirm_token` | 2. `ok: true`; `type` = `qa-main` (a change to the same value is accepted; `idempotentHint: true`) |
| `update-iso-01` | `kinoa_webhook_update {"game_id": P1, "webhook_id": NO_SUCH, "description": "x"}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` on `webhook_id`; no `meta.confirmToken` |
| `update-iso-02` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": P2_ACTIVE, "description": "cross-game"}` 2. `kinoa_webhook_get {"game_id": P2, "webhook_id": P2_ACTIVE}` | 1. `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `P2_ACTIVE` and game `P1`; no token (H12). 2. `description` = `test` (untouched) |
| `update-iso-03` | `kinoa_webhook_update {"game_id": FOREIGN, "webhook_id": MAIN, "description": "x"}` | `ok: false`; `GAME_ACCESS_DENIED`; no token |
| `update-iso-04` | `kinoa_webhook_update {"game_id": P2, "webhook_id": MAIN, "description": "x"}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `MAIN` and game `P2` (H12) |

## A6. `kinoa_webhook_status`

Covers the AC bullet "kinoa_webhook_status handles the lifecycle with a target parameter …
ACTIVE, DEPRECATED and DELETED (wraps the hard-delete endpoint, DRAFT only — the preview warns);
an invalid target returns a clear error naming the allowed targets" — H3, H4, H5, H6. `MAIN`
goes DRAFT → ACTIVE → DEPRECATED. `ST_DEL` is deleted and `ST_TWIN` is its untouched control:
`status-sem-02` and `status-sem-03` are the **delete determination** (`rules.md`). `ST_DD` goes
DRAFT → DEPRECATED and then takes every refusal a DEPRECATED webhook must give; `ACT_UPD` takes
the refusals an ACTIVE one must give. The seeds receive nothing here. Executing legs, refused
ones included: 12 — pause 60 s after `status-sem-01`.

| Id | Call | Expected |
|---|---|---|
| `status-ok-01` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": MAIN, "target": "ACTIVE"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `ok: true`; `data.status` = `preview`; `data.intendedChange` has `webhookId` = `MAIN`, `name` = `NAME-main-v2`, `currentStatus` = `DRAFT`, `target` = `ACTIVE`; `data.message` = `Will move webhook 'NAME-main-v2' (DRAFT) to ACTIVE.`; `data.warnings` = exactly `["Once ACTIVE the webhook starts firing at its target, and its name, key, urlTemplate, requestMethod and headers can no longer be changed.", "This transition is not conditioned on an ETag, so a change somebody else makes in the meantime is not detected."]` (H6, `OBSERVED` for the second sentence). 2. `ok: true`; `data` = `{"webhookId": MAIN, "name": "NAME-main-v2", "target": "ACTIVE", "previousStatus": "DRAFT", "applied": true}`. 3. `status` = `ACTIVE`; `updatedTs` > the `updatedTs` of `update-sem-02` |
| `status-ok-02` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": MAIN, "target": "DEPRECATED", "deprecation_reason": "qa: retired after activation"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": MAIN}` | 1. `data.intendedChange.currentStatus` = `ACTIVE`; `data.warnings` = `["Deprecation is terminal: webhook 'NAME-main-v2' can never be reactivated, only cloned."]`. 2. `ok: true`; `data.target` = `DEPRECATED`; `data.previousStatus` = `ACTIVE`; `data.applied` = `true`. 3. `status` = `DEPRECATED`; `deprecationReason` = `qa: retired after activation`; `deprecationInitiatorId` present; the definition is still returned (H5) |
| `status-ok-03` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-st-del", "key": "KEY_st_del", "url_template": "TARGET/qa/st-del", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_create {"game_id": P1, "name": "NAME-st-twin", "key": "KEY_st_twin", "url_template": "TARGET/qa/st-twin", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 4. the same plus `confirm_token` 5. `kinoa_webhook_list {"game_id": P1, "page_size": 100}` | 2. `ok: true`; `status` = `DRAFT`. `Record: ST_DEL`. 4. `ok: true`; `status` = `DRAFT`. `Record: ST_TWIN`. 5. both present. `Record: TOTAL_BEFORE_DELETE` = `data.totalItems` |
| `status-ok-04` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_DEL, "target": "DELETED"}` 2. the same plus `confirm_token` | 1. `ok: true`; a preview; `data.intendedChange.currentStatus` = `DRAFT`; `data.intendedChange.target` = `DELETED`; `data.warnings` = `["Webhook 'NAME-st-del' will be permanently erased — there is no soft delete and no undo."]` (the AC: "the preview warns"). 2. `ok: true`; `data` = `{"webhookId": ST_DEL, "name": "NAME-st-del", "target": "DELETED", "previousStatus": "DRAFT", "applied": true}` |
| `status-sem-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-st-dd", "key": "KEY_st_dd", "url_template": "TARGET/qa/st-dd", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_status {"game_id": P1, "webhook_id": <id of step 2>, "target": "DEPRECATED", "deprecation_reason": "qa: retired as a draft"}` 4. the same plus `confirm_token` 5. `kinoa_webhook_get {"game_id": P1, "webhook_id": <id of step 2>}` | 2. `Record: ST_DD`. 4. `ok: true`; `data.previousStatus` = `DRAFT`; `data.target` = `DEPRECATED`. 5. `status` = `DEPRECATED`; `deprecationReason` = `qa: retired as a draft` (a draft can be retired without ever being active, H5) |
| `status-sem-02` | 1. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_DEL}` 2. `kinoa_webhook_list {"game_id": P1, "page_size": 100}` (paged to the end if `hasMore`) 3. `kinoa_webhook_list {"game_id": P1, "search": ST_DEL}` | 1. `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `ST_DEL`. 2. `ST_DEL` is absent; `ST_TWIN` is present; `data.totalItems` = `TOTAL_BEFORE_DELETE` − 1 + 1 (`ST_DD` was created since) = `TOTAL_BEFORE_DELETE`. 3. `data.items` = `[]` (H4: the row is gone) |
| `status-sem-03` | 1. `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT"], "page_size": 100}` 2. `kinoa_webhook_list {"game_id": P1, "status": ["ACTIVE"], "page_size": 100}` 3. `kinoa_webhook_list {"game_id": P1, "status": ["DEPRECATED"], "page_size": 100}` 4. `kinoa_webhook_list {"game_id": P1, "status": ["DRAFT", "ACTIVE", "DEPRECATED"], "page_size": 100}` 5. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_TWIN}` | 1.–3. `ST_DEL` is absent from every filter; `ST_TWIN` is in step 1 only. 4. `ST_DEL` absent; `data.totalItems` equals the unfiltered total of `status-sem-02` step 2 (the default listing hides no status). 5. `ok: true`; `status` = `DRAFT`; the twin is untouched. Verdict for report section 3: `kinoa_webhook_status` target `DELETED` is a **hard delete** (H4) |
| `status-sem-04` | 1. `kinoa_webhook_list {"game_id": P1, "status": ["DEPRECATED"], "page_size": 100}` 2. `kinoa_webhook_list {"game_id": P1, "page_size": 100}` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_DD}` | 1. `MAIN`, `ST_DD`, `SEED_C` are present. 2. all three present as well. 3. `ok: true`; `status` = `DEPRECATED`. Verdict for section 3: target `DEPRECATED` is a **soft delete** (a terminal status flip; the row stays gettable and listable, H5) |
| `status-schema-01` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "PAUSED"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/target`; the violation text lists `ACTIVE`, `DEPRECATED` and `DELETED` (the schema half of H3); no token |
| `status-schema-02` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN}` | `ok: false`; `VALIDATION_FAILED`; no `path`; text names `target` |
| `status-schema-03` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED", "deprecation_reason": S129}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/deprecation_reason` |
| `status-schema-04` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "active"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/target` (the enum is upper case) |
| `status-schema-05` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED", "reason": "wrong argument name"}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `reason` |
| `status-rule-01` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED"}` 2. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED", "deprecation_reason": "   "}` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_TWIN}` | 1. `ok: false`; `VALIDATION_FAILED`; one violation with `path` = `deprecation_reason`, `rule` = `required`, `hint` starting `target DEPRECATED needs a deprecation_reason (up to 128 characters)`; no `meta.confirmToken`. 2. the same (a blank reason is no reason). 3. `status` = `DRAFT` |
| `status-rule-02` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ACT_UPD, "target": "ACTIVE"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 1. `ok: true`; a preview with `currentStatus` = `ACTIVE` (the tool does not know the matrix). 2. `ok: false`; `VALIDATION_FAILED`; a violation quoting the service's refusal; record whether its text names the targets the current status allows (H3). An `ok: true` with `applied` = `true` is `OBSERVED` (a no-op activation) and a note. 3. `status` = `ACTIVE` |
| `status-rule-03` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ACT_UPD, "target": "DELETED"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ACT_UPD}` | 1. a preview with the "permanently erased" warning. 2. `ok: false`; `VALIDATION_FAILED` (delete is DRAFT only, H4); record whether the text names the allowed targets (H3). 3. `ok: true`; `status` = `ACTIVE`. A `webhook_not_found` in step 3 is a **critical** `FAIL`: an ACTIVE webhook was erased |
| `status-rule-04` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_DD, "target": "ACTIVE"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_DD}` | 2. `ok: false`; `VALIDATION_FAILED` ("A webhook that is already DEPRECATED accepts nothing"); record the text (H3). 3. `status` = `DEPRECATED`. An `ok: true` is a `FAIL` of the tool description (deprecation "cannot be reactivated") — H5 |
| `status-rule-05` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_DD, "target": "DELETED"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_DD}` | 2. `ok: false`; `VALIDATION_FAILED`. 3. `status` = `DEPRECATED` (H4, H5) |
| `status-rule-06` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_DD, "target": "DEPRECATED", "deprecation_reason": "second reason"}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": ST_DD}` | 2. `ok: false`; `VALIDATION_FAILED`. 3. `deprecationReason` = `qa: retired as a draft` (the first reason is kept; H5) |
| `status-gap-01` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED", "deprecation_reason": S128}` — no token, never confirmed | `ok: true`; a preview (128 characters pass the schema); `meta.confirmToken` present |
| `status-gap-02` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "ACTIVE", "deprecation_reason": "not needed"}` — never confirmed | `ok: true`; a preview (the reason is ignored for `ACTIVE`; `OBSERVED`) |
| `status-gap-03` | `kinoa_webhook_status {"game_id": P1, "webhook_id": ST_TWIN, "target": "DEPRECATED", "deprecation_reason": " qa "}` — never confirmed | `ok: true`; a preview (a reason with real text passes the blank check) |
| `status-iso-01` | `kinoa_webhook_status {"game_id": P1, "webhook_id": NO_SUCH, "target": "ACTIVE"}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` on `webhook_id`; no `meta.confirmToken` |
| `status-iso-02` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": P2_ACTIVE, "target": "DEPRECATED", "deprecation_reason": "cross-game"}` 2. `kinoa_webhook_get {"game_id": P2, "webhook_id": P2_ACTIVE}` | 1. `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `P2_ACTIVE` and game `P1`; no token (H12). 2. `status` = `ACTIVE` |
| `status-iso-03` | `kinoa_webhook_status {"game_id": FOREIGN, "webhook_id": ST_TWIN, "target": "ACTIVE"}` | `ok: false`; `GAME_ACCESS_DENIED`; no token |
| `status-iso-04` | `kinoa_webhook_status {"game_id": P2, "webhook_id": ST_TWIN, "target": "DELETED"}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `ST_TWIN` and game `P2`; no token (H12) |

## A7. `kinoa_webhook_test`

Covers the AC bullet "kinoa_webhook_test fires the webhook with the given field values — a real
HTTP call to the external target, guarded as a write and available to the Tester role; the
response (status, body) is returned so the operator sees how the target answered" — H9, H10,
H18. Every fire in this section reaches `TARGET` except `test-sem-01`, which fires `DEAD_WH` at a
host that does not resolve. `SEED_B` (ACTIVE) and `FULL` (DRAFT) are fired; `PERS` is fired once
as a probe. Fires here: 5 to `TARGET`, 1 to `DEAD`. The response `status` is the target's answer
and is never a verdict on the tool.

| Id | Call | Expected |
|---|---|---|
| `test-ok-01` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "qa-fire"}}` 2. the same plus `confirm_token` | 1. `ok: true`; `data.status` = `preview`; `data.intendedChange` has `webhookId` = `SEED_B`, `name` = `NAME-seed-b`, `call` = `POST TARGET/qa/seed-b`; `data.message` = `Will really call POST TARGET/qa/seed-b on behalf of webhook 'NAME-seed-b'.`; `data.warnings` = `["This reaches a system outside Kinoa. Whatever the call triggers there — a charge, an order, a notification — cannot be undone from here."]`; `meta.confirmToken` present. 2. `ok: true`; `data.webhookId` = `SEED_B`; `data.request` = `{"method": "POST", "url": "TARGET/qa/seed-b"}`; `data.response.status` = `200`; `data.response.headers` is an object; `data.response.body` is a string; no `data.response.truncated`. Record the body verbatim |
| `test-ok-02` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": FULL, "values": {"event": "qa-full", "amount": 7, "vip": true}}` 2. the same plus `confirm_token` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": FULL}` | 2. `ok: true`; `data.response.status` = `200` (a DRAFT webhook can be fired — "Works in any status, including DRAFT"); the `run` placeholder was not sent and has a default, so the call is accepted. 3. `status` = `DRAFT` (firing changes nothing in Kinoa) |
| `test-sem-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-dead", "key": "KEY_dead", "url_template": "DEAD", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. `kinoa_webhook_test {"game_id": P1, "webhook_id": <id of step 2>, "values": {"event": "qa-dead"}}` 4. the same plus `confirm_token` | 2. `ok: true`; `status` = `DRAFT`. `Record: DEAD_WH`. If the service refuses the host, quote the violation and mark `BLOCKED — the service refuses an unresolvable host` (H9). 4. `ok: true`; `data.response.status` = `200`; `data.response.body` parses as JSON with an `error` member describing the transport failure (H9). A `TOOL_EXECUTION_FAILED` or a `5xx` status is a `FAIL` of the tool description |
| `test-sem-02` | `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "never"}}` — no token, never confirmed | `ok: true`; a preview. The preview leg makes no call: nothing new appears at `TARGET` (the operator can check the Beeceptor console; if not, `OBSERVED`) |
| `test-schema-01` | `kinoa_webhook_test {"game_id": P1}` | `ok: false`; `VALIDATION_FAILED`; no `path`; text names `webhook_id`; no token |
| `test-schema-02` | `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": "event=qa"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/values` (an object is declared). `BLOCKED` if the connector refuses to send a string for an object |
| `test-schema-03` | `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "value": {"event": "qa"}}` | `ok: false`; `VALIDATION_FAILED`; the violation text names `value` (the argument is `values`) |
| `test-rule-01` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": FULL, "values": {"amount": 7}}` (no `event`, no `vip` — both required) 2. the same plus `confirm_token` | 1. a preview (values are checked by the service). 2. `ok: false`; `error.code` = `VALIDATION_FAILED`; violations naming `event` and `vip` (or the member the service blames), `hint` quoting its text; **not** `ok: true` with `data.response.status` = `422` — that would report "the target answered" when nothing was sent (H10) |
| `test-rule-02` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-nourl", "key": "KEY_nourl", "url_template": "TARGET/qa/nourl", "request_method": "POST"}` — never confirmed | `ok: true`; a preview. This row records that the tool's own `no_url_template` refusal cannot be reached through the protocol: the schema requires `url_template` on create, and update cannot clear it (`url_template` is a `string`). `BLOCKED — a webhook without a url template cannot be made through the tools` |
| `test-gap-01` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "qa-extra", "unknownName": "x"}}` 2. the same plus `confirm_token` | 2. `OBSERVED`: either `ok: true` with `data.response.status` = `200` (an unknown value name is ignored) or `VALIDATION_FAILED` naming `unknownName` — record which. Never `TOOL_EXECUTION_FAILED` |
| `test-gap-02` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": FULL, "values": {"event": "qa-typed", "amount": "7", "vip": true}}` 2. the same plus `confirm_token` | 2. Expected by the tool description ("a NUMBER placeholder takes 12, not the string '12'"): `ok: false`; `VALIDATION_FAILED` naming `amount`. An `ok: true` with `status` = `200` is `OBSERVED` and a note (the service coerced the text). An `ok: true` with `data.response.status` = `422` is a `FAIL` (H10) |
| `test-gap-03` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": PERS, "values": {"event": "qa-pers", "playerName": "qa-player"}}` 2. the same plus `confirm_token` | 2. `OBSERVED`: record whether a PERSONALIZED placeholder can be given a value in a test fire (`ok: true`, `status` = `200`) or the service refuses (`VALIDATION_FAILED`, quote it). `BLOCKED` if `create-ok-03` did not create `PERS` (H18) |
| `test-gap-04` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B}` (no `values` at all) 2. the same plus `confirm_token` | 2. `ok: false`; `VALIDATION_FAILED` naming `event` (required, no default) — the tool sends an empty map. An `ok: true` with `status` = `200` means the service sent an unrendered `${event}`: `OBSERVED` and a note |
| `test-iso-01` | `kinoa_webhook_test {"game_id": P1, "webhook_id": NO_SUCH, "values": {"event": "x"}}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` on `webhook_id`; no `meta.confirmToken` (the webhook is read on the preview leg) |
| `test-iso-02` | `kinoa_webhook_test {"game_id": P1, "webhook_id": P2_ACTIVE, "values": {}}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `P2_ACTIVE` and game `P1`; no token (H12: a webhook of another game cannot be fired from `P1`) |
| `test-iso-03` | `kinoa_webhook_test {"game_id": FOREIGN, "webhook_id": SEED_B, "values": {"event": "x"}}` | `ok: false`; `GAME_ACCESS_DENIED`; no token |
| `test-iso-04` | `kinoa_webhook_test {"game_id": P2, "webhook_id": SEED_B, "values": {"event": "x"}}` | `ok: false`; `VALIDATION_FAILED`; `webhook_not_found` naming `SEED_B` and game `P2` |

## A8. Grey box

Designed from the source at `adef2a1`: `WriteGuard`, `ConfirmTokenService`, the two rate limiters
of `McpToolRegistry`, `WebhookBackendErrors`. `grey-01` and `grey-02` settle H8 on the single
replica the stand runs (`PASS`/`FAIL` at call 11). `grey-01` uses its own subject `FIRE`;
`grey-03` to `grey-12` use `RP`; `grey-13` needs a 10-minute wait and starts at the beginning of
this section. `grey-14` needs a quiet minute with no preview before it. Fires to `TARGET` here:
11 in `grey-01`, 1 in `grey-04`.

| Id | Call | Expected |
|---|---|---|
| `grey-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-fire", "key": "KEY_fire", "url_template": "TARGET/qa/fire", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token`, then wait 60 s 3. for `NN` from `01` to `11`, inside one minute: `kinoa_webhook_test {"game_id": P1, "webhook_id": FIRE, "values": {"event": "flood-NN"}}` then the same plus its `confirm_token` 4. if a confirm answered `RATE_LIMITED`: wait 60 s, then re-send that exact confirm call with the same token | 2. `Record: FIRE`. 3. Confirms 1–10 are `ok: true` with `data.response.status` = `200`; confirm 11 is `ok: false`, `error.code` = `RATE_LIMITED`, message `Write rate limit exceeded`, hint `Retry shortly; your confirm token stays valid until it expires` (the write budget runs before the tool's own cap, H8); every preview in step 3 is `ok: true`. One replica: `PASS` if the cut-off is exactly call 11, `FAIL` otherwise. 4. `ok: true`; `data.response.status` = `200` (the token survived the denial). `BLOCKED` if the connector cannot place 11 confirms inside one minute; record the span |
| `grey-02` | During step 3 of `grey-01`, right after the `RATE_LIMITED` answer: 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": FIRE, "values": {"event": "probe"}}` — no token, never confirmed 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": FIRE}` 3. `kinoa_webhook_list {"game_id": P1}` | 1. `ok: true`; a preview with a token (previews are not charged to the write budget). 2. and 3. `ok: true` (reads are not charged). `BLOCKED` if `grey-01` never hit the limit. Record that the tool's own message `Rate limit exceeded for kinoa_webhook_test` was not seen (H8) |
| `grey-03` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-rp", "key": "KEY_rp", "url_template": "TARGET/qa/rp", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` 3. the exact call of step 2 again, same token 4. `kinoa_webhook_list {"game_id": P1, "search": "NAME-rp"}` | 2. `ok: true`. `Record: RP`. 3. Either `ok: false` with `VALIDATION_FAILED` on `name`/`key` (the token is accepted, the service refuses the duplicate) or `CONFIRM_TOKEN_INVALID` (single use was added since). Record which. **Never** a second webhook. 4. exactly one item, `id` = `RP` |
| `grey-04` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": RP, "values": {"event": "replay"}}` 2. the same plus `confirm_token` 3. the exact call of step 2 again, same token | 2. `ok: true`; `status` = `200`. 3. `OBSERVED`: a stateless token is accepted again and the target is called a second time (`ok: true`), or `CONFIRM_TOKEN_INVALID`. Record which — a replayable fire token is a note for the story owner: the tool's own warning says the effect "cannot be undone" |
| `grey-05` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g5"}` 2. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g5-ALTERED", "confirm_token": <token of step 1>}` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": RP}` | 2. `ok: false`; `error.code` = `CONFIRM_TOKEN_INVALID`; message `payload mismatch: arguments differ from the previewed call`; hint `Call the tool without confirm_token to get a fresh preview and token`. 3. no `description` (nothing was written) |
| `grey-06` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g6"}` 2. `kinoa_webhook_update {"game_id": P2, "webhook_id": RP, "description": "g6", "confirm_token": <token of step 1>}` | 2. `ok: false`; `CONFIRM_TOKEN_INVALID`; message `payload mismatch: arguments differ from the previewed call` (the game is part of the arguments) |
| `grey-07` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g7"}` 2. `kinoa_webhook_status {"game_id": P1, "webhook_id": RP, "description": "g7", "confirm_token": <token of step 1>}` | 2. `ok: false`; `VALIDATION_FAILED` naming `description` (the schema of `kinoa_webhook_status` rejects the argument before the token is read). Record that the cross-tool check cannot be reached with these two schemas; the cross-tool message is proven in `grey-08` |
| `grey-08` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": RP, "target": "ACTIVE"}` — never confirmed under this tool 2. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "target": "ACTIVE", "confirm_token": <token of step 1>}` 3. `kinoa_webhook_clone {"game_id": P1, "webhook_id": RP, "confirm_token": <token of step 1>}` 4. `kinoa_webhook_get {"game_id": P1, "webhook_id": RP}` | 2. `ok: false`; `VALIDATION_FAILED` naming `target` (schema first). 3. `ok: false`; `CONFIRM_TOKEN_INVALID`; message `confirm token was issued for another tool` (the clone schema accepts the same argument set, so the token check is reached). 4. `status` = `DRAFT`; no copy was made |
| `grey-09` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g9", "type": "t9"}` 2. `kinoa_webhook_update {"type": "t9", "description": "g9", "webhook_id": RP, "game_id": P1, "confirm_token": <token of step 1>}` | 2. `ok: true`; `description` = `g9`; `type` = `t9` (key order is not part of the payload digest) |
| `grey-10` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g10"}` 2. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g10", "type": "added between the legs", "confirm_token": <token of step 1>}` | 2. `ok: false`; `CONFIRM_TOKEN_INVALID`; `payload mismatch: arguments differ from the previewed call` (an added argument is binding) |
| `grey-11` | Four calls, each `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g11", "confirm_token": <T>}` with `T` = 1. a fresh token of this call with one character changed in the middle of its signature; 2. the same fresh token with one character changed in the middle of its payload; 3. the token with its `.` removed; 4. the payload part followed by `.` and nothing | Each: `ok: false`; `error.code` = `CONFIRM_TOKEN_INVALID`; `hint` says to call the tool without `confirm_token`. Messages: 1. and 2. `invalid confirm token signature`; 3. `malformed confirm token`; 4. `invalid confirm token signature`. No stack trace; never `TOOL_EXECUTION_FAILED` |
| `grey-12` | `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g12", "confirm_token": ""}` | `ok: true`; a preview with a fresh token (a blank token is treated as no token — the designed behaviour, `OBSERVED`) |
| `grey-13` | 1. at the start of §A8: `kinoa_webhook_create {"game_id": P1, "name": "NAME-exp", "key": "KEY_exp", "url_template": "TARGET/qa/exp", "request_method": "POST"}` 2. at least 10 minutes later: the same plus `confirm_token` from step 1 3. `kinoa_webhook_list {"game_id": P1, "search": "NAME-exp"}` | 2. `ok: false`; `CONFIRM_TOKEN_INVALID`; message `confirm token expired`. 3. `data.items` = `[]`. `BLOCKED` if the 10 minutes could not be waited |
| `grey-14` | After a quiet minute: 61 calls of `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "preview-flood"}` — no token, none confirmed — inside one minute | Calls 1–60 are `ok: true` previews; call 61 is `ok: false`, `RATE_LIMITED`, message `Preview rate limit exceeded`, hint `Slow down and retry shortly; previews are capped per user`. One replica: `PASS`/`FAIL` on call 61. `BLOCKED` if the connector cannot place 61 calls inside one minute; record how many it placed |
| `grey-15` | A confirm token minted by another Kinoa account, used by this account | `BLOCKED — needs a second account`. Code-read only: the payload binds `user` (`confirm token was issued for another user`) |
| `grey-16` | The audit log for this run's calls | `BLOCKED — not observable through the protocol` (H16, the audit half of the AC) |
| `grey-17` | A concurrent change of `RP` between the read and the write inside one `kinoa_webhook_update` execute leg | `BLOCKED — needs a second writer the protocol cannot provide`. Code-read only: a 412 becomes the violation `webhook_changed_concurrently`, a 428 the violation `etag_unavailable` |
| `grey-18` | Read every error envelope captured so far in Part A | No stack trace, no internal hostname or URL (nothing ending in `.kindev.net`, no cluster-local name, no `localhost`), no bearer token, no HTML page, no data of another game. A `TOOL_EXECUTION_FAILED` message that carries a downstream response body is recorded with that body |
| `grey-19` | Read every failure captured so far in Part A | Each is `isError` with `ok: false`, `error.code` in {`VALIDATION_FAILED`, `GAME_ACCESS_DENIED`, `PERMISSION_DENIED`, `CONFIRM_TOKEN_INVALID`, `RATE_LIMITED`, `TOOL_EXECUTION_FAILED`}, `error.message`; validation failures carry `error.violations[]` with `rule` and `hint`, and `path` for every non-root violation. No success envelope carries a failure |
| `grey-20` | Read every `data.response.body` captured in §A7 and `grey-01` | Each is a string of at most 8192 characters; no body carries `truncated: true` unless it is exactly 8192 characters long. The `headers` object never carries an `Authorization` value of Kinoa's own (the target's headers only) |
| `grey-21` | `kinoa_webhook_test {"game_id": P1, "webhook_id": RP, "values": {"event": {"nested": "object"}}}` — no token, never confirmed | `ok: true`; a preview (the schema types `values` as an object with untyped members; the service decides on the execute leg, which is not run here). `OBSERVED` |
| `grey-22` | `kinoa_webhook_create {"game_id": 123, "name": "NAME-g22", "key": "KEY_g22", "url_template": "TARGET/qa/g22", "request_method": "POST"}` | `ok: false`; `VALIDATION_FAILED`; `path` = `/game_id`. `BLOCKED` if the connector refuses to send a number for a string argument |
| `grey-23` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "g23"}` 2. `kinoa_webhook_update {"game_id": " <P1_GAME_ID> ", "webhook_id": RP, "description": "g23", "confirm_token": <token of step 1>}` | 2. `ok: false`; `CONFIRM_TOKEN_INVALID`; `payload mismatch: arguments differ from the previewed call` — the digest binds the argument as sent, and the trim happens after it (`OBSERVED` if the stand answers `ok: true`: then the digest is computed on trimmed values; record it) |

## A9. Hand-off

Proves that the subjects Part B needs are in the state Part B expects, mints the token Part B
re-sends under a weaker role, and freezes the inventory for report section 9.

| Id | Call | Expected |
|---|---|---|
| `handoff-01` | 1. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | 1. `status` = `DRAFT`; `name` = `NAME-seed-a`; `json` = the string of `JSON_1`; `fields` = one item `event`; `updatedTs` equals the one of `get-ok-01`. 2. `status` = `ACTIVE`; `name` = `NAME-seed-b`; `fields` = one item `event` (nothing in Part A wrote to it). 3. `status` = `DEPRECATED`; `deprecationReason` = `qa seed fixture` (or the description changed by `update-gap-01`, if that case was `ok: true`) |
| `handoff-02` | `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "demotion"}` — no token, never confirmed in Part A | `ok: true`; a preview. `Record: TOKEN_DEMOTION` = `meta.confirmToken`, and the time it was minted |
| `handoff-03` | 1. `kinoa_webhook_list {"game_id": P1, "response_format": "detailed", "page_size": 100}` (paged to the end if `hasMore`) 2. `kinoa_webhook_list {"game_id": P2, "page_size": 100}` | 1. Every item whose `name` starts with `NAME` (or is a derived copy name) is recorded with its `id`, `key` and `status`: this is the draft of report section 9. `ST_DEL` is absent. 2. `data.totalItems` = `P2_TOTAL`; no item of this run |

# PART B — role-gated checks

Four checkpoints. Before the first one, the admin-panel owner records the `user_role` rows that
exist for `USER_ID` now — `ORIG_ROWS` — and the run writes them into the report. Each checkpoint
states the complete set of rows wanted, then the run stops and waits for confirmation, then waits
at least 20 seconds, then asserts. The mapping asserted against is the one in the header: Viewer
may call `kinoa_webhook_list` and `kinoa_webhook_get`; Tester may also call `kinoa_webhook_test`;
Operator may call all seven. A denial names the role and the tool, for example
`Role 'viewer' is not permitted to call tool 'kinoa_webhook_create'`, and a denied write receives
no token. Both games belong to one company, so a COMPANY row always covers both. The seeds are the
subjects: `SEED_A` is read, `SEED_B` is fired once (`role-test-02`), `SEED_C` receives nothing.
`SCOPE_P1` and `RESTORE` are created in `P1`; nothing is ever written to `P2`.

## B1. Checkpoint 1 — Viewer on both games

Rows wanted (complete state): `GAME` `P1` = `viewer`; `GAME` `P2` = `viewer`; no `COMPANY` row.
Stop and wait for confirmation, then wait 20 s. `role-update-02` re-sends `TOKEN_DEMOTION`: the
permission check runs before the token check, so the answer is `PERMISSION_DENIED` whether or not
the token has expired, and nothing is written.

| Id | Call | Expected |
|---|---|---|
| `role-list-01` | 1. `kinoa_webhook_list {"game_id": P1}` 2. `kinoa_webhook_list {"game_id": P2}` | Both `ok: true`; step 1 has the same ids as `handoff-03` step 1 (a Viewer reads the whole listing) |
| `role-list-02` | `tools/list` | All seven webhook tools are still listed under Viewer (`OBSERVED`: the registry does not filter the tool list by role; being listed is not being permitted) |
| `role-get-01` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` | `ok: true`; `status` = `DRAFT`; the full definition is returned (a Viewer may read the request definition) |
| `role-create-01` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-viewer", "key": "KEY_viewer", "url_template": "TARGET/qa/viewer", "request_method": "POST"}` 2. `kinoa_webhook_list {"game_id": P1, "search": "NAME-viewer"}` | 1. `ok: false`; `error.code` = `PERMISSION_DENIED`; message `Role 'viewer' is not permitted to call tool 'kinoa_webhook_create'`; no `meta.confirmToken`; no `data`. 2. `data.items` = `[]` |
| `role-create-02` | `kinoa_webhook_create {"game_id": FOREIGN, "name": "NAME-viewer", "key": "KEY_viewer", "url_template": "TARGET/qa/viewer", "request_method": "POST"}` | `ok: false`; `error.code` = `PERMISSION_DENIED` (the role check answers before the game check); no token |
| `role-clone-01` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A}` 2. `kinoa_webhook_list {"game_id": P1, "page_size": 100}` | 1. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_clone`; no token. 2. `data.totalItems` equals the total of `handoff-03` step 1 |
| `role-update-01` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": SEED_A, "description": "viewer edit"}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` | 1. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_update`; no token. 2. no `description` |
| `role-update-02` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "demotion", "confirm_token": TOKEN_DEMOTION}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": RP}` | 1. `ok: false`; `error.code` = `PERMISSION_DENIED` (not `CONFIRM_TOKEN_INVALID`: the permission check comes first). An `ok: true` is a **critical** `FAIL` (a token minted under Operator executed under Viewer). 2. `description` ≠ `demotion` |
| `role-status-01` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": SEED_A, "target": "ACTIVE"}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` | 1. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_status`; no token. 2. `status` = `DRAFT` |
| `role-test-01` | `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "viewer"}}` | `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_test`; no token (a Viewer cannot fire; the AC gives the tool to Tester) |

## B2. Checkpoint 2 — Tester on both games

Rows wanted (complete state): `GAME` `P1` = `tester`; `GAME` `P2` = `tester`; no `COMPANY` row.
Stop and wait for confirmation, then wait 20 s. This checkpoint is the AC clause "available to the
Tester role": the fire is allowed, every other write is not. One fire reaches `TARGET`.

| Id | Call | Expected |
|---|---|---|
| `role-list-03` | `kinoa_webhook_list {"game_id": P1}` | `ok: true` (Tester includes Viewer) |
| `role-get-02` | `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` | `ok: true`; `status` = `ACTIVE`; `fields` = one item `event` |
| `role-test-02` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "tester-fire"}}` 2. the same plus `confirm_token` | 1. `ok: true`; a preview with `meta.confirmToken`. 2. `ok: true`; `data.response.status` = `200` (a Tester may fire a webhook) |
| `role-test-03` | `kinoa_webhook_test {"game_id": FOREIGN, "webhook_id": SEED_B, "values": {"event": "x"}}` | `ok: false`; `error.code` = `GAME_ACCESS_DENIED` (the tool is permitted to Tester, so the call reaches the game check); no token |
| `role-create-03` | `kinoa_webhook_create {"game_id": P1, "name": "NAME-tester", "key": "KEY_tester", "url_template": "TARGET/qa/tester", "request_method": "POST"}` | `ok: false`; `PERMISSION_DENIED`; message `Role 'tester' is not permitted to call tool 'kinoa_webhook_create'`; no token |
| `role-clone-02` | `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A}` | `ok: false`; `PERMISSION_DENIED` naming `tester` and `kinoa_webhook_clone`; no token |
| `role-update-03` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": SEED_B, "description": "tester edit"}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` | 1. `ok: false`; `PERMISSION_DENIED` naming `tester` and `kinoa_webhook_update`; no token. 2. no `description` |
| `role-status-02` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": SEED_A, "target": "ACTIVE"}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` | 1. `ok: false`; `PERMISSION_DENIED` naming `tester` and `kinoa_webhook_status`; no token (a Tester "cannot create, edit or publish one"). 2. `status` = `DRAFT` |

## B3. Checkpoint 3 — GAME Operator on `P1`, COMPANY Viewer

Rows wanted (complete state): `COMPANY` (the company of `P1` and `P2`) = `viewer`; `GAME` `P1` =
`operator`; no `GAME` row for `P2`. Stop and wait for confirmation, then wait 20 s. The GAME row
must win on `P1`; `P2` falls back to the COMPANY row. `SCOPE_P1` is created in `P1`; every call on
`P2` is denied, so `P2` stays untouched.

| Id | Call | Expected |
|---|---|---|
| `role-list-04` | 1. `kinoa_webhook_list {"game_id": P1}` 2. `kinoa_webhook_list {"game_id": P2}` | Both `ok: true` |
| `role-create-04` | `kinoa_webhook_create {"game_id": P2, "name": "NAME-scope-p2", "key": "KEY_scope_p2", "url_template": "TARGET/qa/scope-p2", "request_method": "POST"}` | `ok: false`; `PERMISSION_DENIED`; message `Role 'viewer' is not permitted to call tool 'kinoa_webhook_create'` (the COMPANY row applies to `P2`); no token |
| `role-create-05` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-scope-p1", "key": "KEY_scope_p1", "url_template": "TARGET/qa/scope-p1", "request_method": "POST", "json": JSON_1, "fields": FIELDS_1}` 2. the same plus `confirm_token` | 1. `ok: true`; a preview with a token (Operator through the GAME row). 2. `ok: true`; `status` = `DRAFT`. `Record: SCOPE_P1` |
| `role-clone-03` | 1. `kinoa_webhook_clone {"game_id": P1, "webhook_id": SEED_A}` — never confirmed 2. `kinoa_webhook_clone {"game_id": P2, "webhook_id": P2_ACTIVE}` | 1. `ok: true`; a preview. 2. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_clone`; no token |
| `role-update-04` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": SCOPE_P1, "description": "scope"}` — never confirmed 2. `kinoa_webhook_update {"game_id": P2, "webhook_id": P2_ACTIVE, "description": "scope"}` 3. `kinoa_webhook_get {"game_id": P2, "webhook_id": P2_ACTIVE}` | 1. `ok: true`; a preview. 2. `ok: false`; `PERMISSION_DENIED` naming `viewer`; no token. 3. `description` = `test` |
| `role-status-03` | 1. `kinoa_webhook_status {"game_id": P1, "webhook_id": SCOPE_P1, "target": "ACTIVE"}` — never confirmed 2. `kinoa_webhook_status {"game_id": P2, "webhook_id": P2_ACTIVE, "target": "DEPRECATED", "deprecation_reason": "scope probe"}` 3. `kinoa_webhook_get {"game_id": P2, "webhook_id": P2_ACTIVE}` | 1. `ok: true`; a preview. 2. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_status`; no token. 3. `status` = `ACTIVE` |
| `role-test-04` | 1. `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "scope"}}` — never confirmed 2. `kinoa_webhook_test {"game_id": P2, "webhook_id": P2_ACTIVE, "values": {}}` | 1. `ok: true`; a preview. 2. `ok: false`; `PERMISSION_DENIED` naming `viewer` and `kinoa_webhook_test` (a Viewer cannot fire); no token |

## B4. Checkpoint 4 — original rows restored

Rows wanted (complete state): exactly `ORIG_ROWS`, as recorded before B1. This is the last change.
Stop and wait for confirmation, then wait 20 s. `role-update-05` re-sends `TOKEN_DEMOTION` under a
permitted role; by now it is far past its 10-minute life, so the token check is what answers.

| Id | Call | Expected |
|---|---|---|
| `role-get-03` | 1. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_A}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_B}` 3. `kinoa_webhook_get {"game_id": P1, "webhook_id": SEED_C}` | 1. `status` = `DRAFT`, no `description`. 2. `status` = `ACTIVE`, no `description`. 3. `status` = `DEPRECATED` (the seeds left Part B as they entered it) |
| `role-update-05` | 1. `kinoa_webhook_update {"game_id": P1, "webhook_id": RP, "description": "demotion", "confirm_token": TOKEN_DEMOTION}` 2. `kinoa_webhook_get {"game_id": P1, "webhook_id": RP}` | 1. `ok: false`; `error.code` = `CONFIRM_TOKEN_INVALID`; message `confirm token expired` (`OBSERVED` if the token is somehow still inside its 10 minutes and executes; then step 2 shows `demotion`). 2. `description` ≠ `demotion` unless step 1 executed |
| `role-create-06` | 1. `kinoa_webhook_create {"game_id": P1, "name": "NAME-restore", "key": "KEY_restore", "url_template": "TARGET/qa/restore", "request_method": "POST"}` 2. the same plus `confirm_token` | 1. a preview with a token. 2. `ok: true`; `status` = `DRAFT`. `Record: RESTORE` (the account writes again) |
| `role-test-05` | `kinoa_webhook_test {"game_id": P1, "webhook_id": SEED_B, "values": {"event": "restored"}}` — never confirmed | `ok: true`; a preview with a token (no fire) |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only this domain
knows:

- **Section 1**: `Run reason` = `first run`; `Previous report` = `none`; `ORIG_ROWS` as recorded
  before B1; the value of `DRY_RUN` from `pre-08`; the replica count (one) as told by the operator.
- **Section 3**: the verdict on `kinoa_webhook_status` per target — `DELETED` from `status-ok-04`,
  `status-sem-02`, `status-sem-03` (expected: hard delete, DRAFT only); `DEPRECATED` from
  `status-ok-02`, `status-sem-01`, `status-sem-04` (expected: soft delete, a terminal status flip);
  `ACTIVE` from `status-ok-01` and `status-rule-04` (one-way). Also the number of fires that
  reached `TARGET`, from the operator's Beeceptor console if available.
- **Section 6**: one row per AC bullet, in this order: (1) `kinoa_webhook_list` envelope, search,
  `response_format`, the compact view's members, and `kinoa_webhook_get` full webhook — §A1, §A2,
  H1; (2) `kinoa_webhook_create` parameter set and DRAFT start — §A3, H2, H17, H18; (3)
  `kinoa_webhook_clone` — §A4; (4) `kinoa_webhook_update` partial, nothing silently lost, ETag —
  §A5, H7, H11, and `grey-17` for the ETag half; (5) `kinoa_webhook_status` targets and the
  invalid-target error — §A6, H3, H4, H5, H6; (6) `kinoa_webhook_test` real call, guarded as a
  write, Tester role, response returned — §A7, `role-test-02`, H8, H9, H10; (7) the service
  upgrade to kinoa-bom 4.x — not observable, section 8; (8) write tools guarded by
  preview/confirm, rate limiting and audit, Viewer/Operator mapping, the validation contract —
  `pre-02`, `pre-03`, every `schema` row, §A8, Part B, H16; (9) the demo — list, create with
  fields, test-fire, activate, deprecate — `list-ok-01`, `create-ok-02`, `test-ok-02`,
  `status-ok-01`, `status-ok-02`.
- **Section 7**: verdicts on H1 to H18 from §1.1.
- **Section 8**: the kinoa-bom upgrade bullet, the audit half of bullet (8) (`grey-16`), the
  `security` question of H2 (whether the dashboard offers it — the run cannot see the dashboard),
  `grey-15` (a second account), `grey-17` (a concurrent writer), `test-rule-02` (a webhook without
  a url template), and every row graded `BLOCKED`.
- **Section 9**: every handle of the §0 artifacts table that got an id, plus the conditional ones
  (`MIN`, `CLONE_A2`, and `GETJ`, `R4`, `R6`, `R8`, `R10`, `R11`, `RU3`, `CLONE_BLANK` if they
  were created), labelled after a fresh `kinoa_webhook_get`. `SEED_B`, `ACT_UPD` are
  `exists (status: ACTIVE) — irreversible`; `SEED_C`, `MAIN`, `ST_DD` are
  `soft-deleted (status: DEPRECATED, still gettable) — irreversible`; `ST_DEL` is
  `hard-deleted (id no longer resolves)`. `MAIN` is cited by its final name `NAME-main-v2` /
  `KEY_main_v2`, `CLONE_A` and `CLONE_A2` by the names the service derived.
- **Section 10**: `ORIG_ROWS`, and whether B4 restored them.
