# KING-22304 — Webhooks via the AI agent: Test Report

> **Redacted on 2026-09-23.** The two fixture games, the two players, the account and the user id of this run are `<…>` placeholders (see `mcp-plan references/fixed-data.md`, "Games and players"). Names and ids of the entities the run created are unchanged.

## 1. Header

**Date (UTC):** 2026-09-16, run started 09:44 UTC
**Stand:** the deployed Kinoa test stand
**MCP connector:** `kinoa` (Streamable HTTP `/mcp`, OAuth browser login), authorized in this session
**Account:** `<ACCOUNT_EMAIL>`
**Run:** `20260916-0944`
**Plan file:** [`KING-22304-webhooks-test-plan.md`](../plans/KING-22304-webhooks-test-plan.md), plan version 1
**Run reason:** first run
**Previous report:** none

### Fixed data actually used

| Constant | Value |
|---|---|
| `P1` | `<P1_GAME_ID>` — *<P1_GAME_NAME>* |
| `P2` | `<P2_GAME_ID>` — *<P2_GAME_NAME>* |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `NO_SUCH` | `00000000-0000-4000-8000-00000000dead` |
| `P2_ACTIVE` | `<P2_ACTIVE_WEBHOOK_ID>` — the pre-existing ACTIVE webhook `test` of *<P2_GAME_NAME>* |
| `STAMP` | `20260916-0944` |
| `NAME` | `KING22304-QA-20260916-0944` |
| `KEY` | `king22304_qa_20260916_0944` |
| `TARGET` | `https://<WEBHOOK_TARGET>` |
| `DEAD` | `https://kinoa-qa-unreachable.invalid/hook` |

`PLAYER1` (`<PLAYER1_ID>`) and `PLAYER2`
(`<PLAYER2_ID>`) are not used: no webhook tool takes a player.

**Dry-run switch:** off. `meta.dryRun` came back `false` on the run's first preview (`pre-08`), so every write tool could be executed.
**Replica count:** one, as told by the story owner in the plan interview.
**`ORIG_ROWS`:** not provided to the run — see section 10.

## 2. Overall status
**RED** — the run recorded 20 failed cases.

| Status | Cases |
|---|---|
| `PASS` | 204 |
| `FAIL` | 20 |
| `OBSERVED` | 16 |
| `BLOCKED` | 13 |
| **Total** | **253** — every case of the plan, counted once |

Notes are not statuses and are not counted above: the run wrote **4** of them.

Part A holds 224 of those cases (177 `PASS`, 19 `FAIL`, 15 `OBSERVED`, 13 `BLOCKED`) and Part B the
other 29 (27 `PASS`, 1 `FAIL`, 1 `OBSERVED`, 0 `BLOCKED`).

The 20 failed cases come from eight defects, not twenty:

- **F1** — 6 cases: `list-ok-01`, `list-ok-02`, `list-sem-04`, `list-sem-12`, `status-sem-02`, `status-sem-03`
- **F2** — 4 cases: `create-sem-01`, `update-ok-02`, `status-sem-04`, `handoff-03`
- **F3** — 6 cases: `create-iso-01`, `clone-iso-03`, `update-iso-03`, `status-iso-03`, `test-iso-03`, `role-test-03`
- **F4** — 1 case: `status-rule-06`
- **F5** — 2 cases: `grey-19`, `grey-22`
- **F6** — 1 case: `create-rule-08`
- **F7** — no failed case: `update-gap-01` is `OBSERVED`, because the plan let that case pass either way and the defect is in the preview it did not assert on
- **F8** — no failed case: `grey-04` is `OBSERVED` for the same reason

F1 and F2 are two blind spots of the same listing, so ten of the twenty failures are one or the
other seen from a different case.

**After review by the story owner**, three items first written as notes were re-classified as
defects and are now F6, F7 and F8. That review also corrected one case grade: `create-rule-08` was
first recorded `PASS` because the call was refused, but the plan asked for a violation that names
the field type, and the message does not, so the case is `FAIL`. The counts above are the corrected
ones.

First run of this plan.

## 3. What was done, per part

### How a case was graded

A case is `FAIL` when any assertion in its `Expected` cell did not hold. That rule is mechanical on
purpose, so the count can be checked. It means one defect can fail several cases: the two listing
defects F1 and F2 together account for ten of the twenty failures. Section 2 lists the cases under
each finding, so the number of failed cases is not the number of separate problems. Two findings,
F7 and F8, have no failed case at all: the plan allowed those cases to pass either way, and the
defect sits in behaviour the case did not assert on.

### Part A — preflight (§A0)

The connector served all seven webhook tools and every input schema matched what the plan expected,
including the `maxLength` values, the three enums and `additionalProperties: false` on all seven
(`pre-03`). The tool descriptions carried every sentence the plan quotes (`pre-04`). Two preflight
cases are `BLOCKED`: this connector does not expose the tool annotations (`pre-02`), so the write
list was taken from the five tools whose input schema declares `confirm_token` — `kinoa_webhook_create`,
`kinoa_webhook_clone`, `kinoa_webhook_update`, `kinoa_webhook_status` and `kinoa_webhook_test`; and
the server instructions from the `initialize` result reach this session cut off before the webhook
paragraph, so `pre-09` could not be checked.

The run's first preview answered `meta.dryRun: false`, so the dry-run kill-switch was off and every
write tool could be executed. The game *<P1_GAME_NAME>*
(`<P1_GAME_ID>`) held no webhooks at the start, and *<P2_GAME_NAME>*
(`<P2_GAME_ID>`) held the five pre-existing ones the plan lists. The three
read fixtures were created and brought to their states: `KING22304-QA-20260916-0944-seed-a` (DRAFT),
`-seed-b` (ACTIVE) and `-seed-c` (DEPRECATED).

### Part A — `kinoa_webhook_list` (§A1) and `kinoa_webhook_get` (§A2)

Paging, the `key` filter, the three single-status filters, the combination of `search` with a status
filter, and every schema rejection behaved as the plan expected. The search ignores upper and lower
case and also matches an exact webhook id. Two blind spots came out of this section and govern much
of the rest of the report: the default listing leaves out every DEPRECATED webhook (F1), and the
`search` argument inherits the same blind spot.

`kinoa_webhook_get` returned the full definition for all three seeds, including the deprecation
reason and the initiator for the DEPRECATED one, and answered `webhook_not_found` for an unknown id,
for a webhook of the other game in both directions, and for a blank id. The listing does not carry
`requestMethod`, `headers`, `json` or the placeholder fields in either response format, so the
compact-view half of the first acceptance criterion is not met (H1, section 6).

### Part A — `kinoa_webhook_create` (§A3) and `kinoa_webhook_clone` (§A4)

Every create happy path worked and every new webhook started as `DRAFT`. The full parameter set
round-tripped exactly: `type`, `description`, headers with a placeholder, a json body with three
placeholders, and four fields with their types, descriptions, `required` flags and typed defaults —
a `NUMBER` default came back as the number `12` and a `STRING` default as `"qa"`. A `PERSONALIZED`
placeholder was accepted without needing a matching player field. The smallest possible webhook, with
no json, no fields and no headers, was accepted.

All fifteen schema rejections and ten of the eleven tool-rule rejections behaved correctly, with
clear violations: a duplicate name or key, a key that does not start with a letter, a url that is not an
absolute http(s) URL, a json body that does not parse, a placeholder referenced but not declared, a
field declared but not referenced, a blank header value, a `PERSONALIZED` field referenced with the
`${}` syntax, and a `NUMBER` default sent as a string. `security` is not part of the create schema
(H2, section 6). The eleventh rule is F6: a `DATE` placeholder inside the json body is refused, which
is right, but with the same message a broken json body gets. This section also produced F2: a webhook created with a `type` cannot be found by
any listing.

Cloning worked in all three directions: from a DRAFT, from an ACTIVE source and from a DEPRECATED one
— the last being the revival path the tool description promises. Without a name and key the service
derived `KING22304-QA-20260916-0944-seed-a (copy 1)` and, on a second clone of the same source,
`(copy 2)`, each with a matching derived key. The copy always started as DRAFT and the source was
never touched.

### Part A — `kinoa_webhook_update` (§A5)

The partial-update contract held completely, and nothing was lost by silence (H7). `headers` merged
member by member, a header mapped to `null` was removed, removing a header that does not exist was
accepted and changed nothing, and every member set by an earlier call survived the later calls that
did not name it. The `fields` array is replaced whole, and the preview announced that in the same
words the tool description uses before the placeholder was dropped, so the loss is documented rather
than silent. The freeze rule on an ACTIVE webhook (H11) worked in both directions: a NEW placeholder
field was added to an ACTIVE webhook and the description could be edited, while the name, the url
template and a `fields` array that drops an existing placeholder were each refused with a clear
violation, and the preview warned about the frozen members beforehand. An update with no changeable
argument was refused with `rule: no_changes` and a hint listing the nine editable members.

One probe could not be run: this connector turns a JSON `null` for a string-typed argument into the
text `"null"`, so `update-gap-03` is `BLOCKED` and the webhook
`KING22304-QA-20260916-0944-main-v2` now carries the literal description `null`.

### Part A — `kinoa_webhook_status` (§A6), and the delete verdict

All three targets work and the previews carry the right warnings: the activation warning about
freezing and about the missing ETag condition, the terminal-deprecation warning, and, for a delete,
"Webhook '…' will be permanently erased — there is no soft delete and no undo." `deprecation_reason`
is required for `DEPRECATED` and a blank reason is treated as no reason. A refused transition names
what the current status allows, for example "cannot change from ACTIVE to DELETED; ACTIVE allows:
DEPRECATED". The one exception is F4: deprecating an already deprecated webhook answers
`TOOL_EXECUTION_FAILED` with the raw downstream 409 body.

**The delete verdict, per target:**

- **`DELETED` is a hard delete.** After the confirmed call on `KING22304-QA-20260916-0944-st-del`
  (id `86074660-04d5-4260-a382-93292599023e`), `kinoa_webhook_get` answered `webhook_not_found`, the
  webhook was absent from the unfiltered listing, absent from each of the three status filters and
  from all three together, and absent from a search by its exact id. Its untouched twin
  `KING22304-QA-20260916-0944-st-twin` (id `ebebb536-ddf0-4a90-a1bf-13da204325de`) was still there
  and still DRAFT, which rules out a listing problem. It is refused on anything that is not a DRAFT.
- **`DEPRECATED` is a soft delete** — a terminal status flip. The row stays, `kinoa_webhook_get`
  returns it in full with `deprecationReason` and `deprecationInitiatorId`, and it is listed under
  the `DEPRECATED` filter. Afterwards the webhook is read-only: activation, deletion and a second
  deprecation are all refused, and `kinoa_webhook_update` is refused too. A DRAFT can be retired
  this way without ever having been ACTIVE.
- **`ACTIVE` is one way.** No tool moves a webhook back to DRAFT. Moving an ACTIVE webhook to ACTIVE
  again is accepted as a no-op and answers `applied: true` (note N4).

The unfiltered listing total (12) was smaller than the all-statuses total (14) at the moment of the
determination, which is F1 rather than anything about the delete.

### Part A — `kinoa_webhook_test` (§A7)

The fire tool did what the acceptance criterion promises. The preview names the real call and warns
that it reaches a system outside Kinoa; the executing leg returned the target's own status, headers
and body. A DRAFT webhook can be fired, and firing changed nothing in Kinoa. A target whose host does
not resolve came back exactly as the tool description says — `status` `200` with a body
`{"error":"I/O error on POST request for \"https://kinoa-qa-unreachable.invalid/hook\": kinoa-qa-unreachable.invalid: Name does not resolve"}`
(H9). Missing and wrongly typed placeholder values are refused by the service and mapped to
`VALIDATION_FAILED` with one violation per field — they are never reported as a 422 from the target
(H10). An unknown value name is refused by name. A `PERSONALIZED` placeholder can be given a value in
a test fire.

Fifteen real HTTP calls reached the operator's test target
`https://<WEBHOOK_TARGET>` during Part A, plus one to the unresolvable host. The
Beeceptor console was not available to this run, so the count is the run's own, taken from the
executing legs that answered.

### Part A — grey box (§A8)

The confirm-token contract is sound. The digest binds the tool, the caller and every argument as
sent: a changed value, an added argument and a changed `game_id` were each refused with
`payload mismatch: arguments differ from the previewed call`, while a different key order was
accepted. A token minted by `kinoa_webhook_status` and presented to `kinoa_webhook_clone` was refused
with `confirm token was issued for another tool`. Four tampered tokens gave `invalid confirm token
signature` or `malformed confirm token`, with no stack trace. A blank token is treated as no token
and returns a fresh preview. Tokens are stateless and not single use, which is harmless for a create
(the service refuses the duplicate) but means a test fire can be replayed — F8.

Three grey-box areas could not be reached through this connector and are `BLOCKED`, with the
measurements in section 8: both rate-limit probes, because the connector is far too slow to place
eleven executing calls or sixty-one previews inside one minute; a second Kinoa account; a concurrent
writer; and the audit log, which the protocol does not expose. No error envelope of Part A carried a
stack trace, an internal hostname, a bearer token, an HTML page or the data of another game.

### Part A — hand-off (§A9)

The three seeds entered Part B in the states Part B expects, with `KING22304-QA-20260916-0944-seed-a`
unchanged since it was first read. The demotion token was minted for `role-update-02`. The inventory
listing that should have been the draft of section 9 turned out to be short by six webhooks — two
hidden by F1 and four by F2 — so section 9 was built from the run's own record of every id it
created and confirmed with `kinoa_webhook_get` at the end. The game *<P2_GAME_NAME>* was untouched: it
still holds exactly its five pre-existing webhooks and nothing from this run.

### Part B — the role model

Four checkpoints were applied by the admin-panel owner, each confirmed before the run asserted
anything, each followed by a wait past the 10-second role cache. All 29 Part B cases ran; none was
blocked.

**B1, Viewer on both games.** The boundary is exactly where the mapping says. A Viewer reads the
whole listing and the full request definition of a webhook, and is refused `create`, `clone`,
`update`, `status` and `test`, each with `PERMISSION_DENIED` naming the role and the tool. The
security case of the whole run passed here: the confirm token minted 10 minutes earlier, while the
account still had write rights, was refused with `PERMISSION_DENIED` and **not** with
`CONFIRM_TOKEN_INVALID`, and the webhook `KING22304-QA-20260916-0944-rp` still reads
`"description":"g9"` rather than `"demotion"`. The permission check runs before the token check, so
a token cannot outlive the rights of the person who made it.

**B2, Tester on both games.** This checkpoint decides the AC clause "available to the Tester role",
and it is met: the fire was previewed and executed and the target answered `200` at 11:00:19 UTC,
while `create`, `clone`, `update` and `status` were each refused naming role `tester`. The one
failed case of Part B is here — `role-test-03`, which is F3 again and in its sharpest form, because
the account held `tester` on both of its games and the answer still named role `viewer`.

**B3, COMPANY Viewer with a GAME Operator row on one game.** Scope precedence works in both
directions: the GAME row wins on *<P1_GAME_NAME>*, where the account created
`KING22304-QA-20260916-0944-scope-p1` and got previews from all four write tools, while *<P2_GAME_NAME>*,
which had no GAME row, fell back to the COMPANY Viewer row and refused every write. This checkpoint
needed two attempts: the first application left the GAME row for *<P2_GAME_NAME>* from B2 in place, so
that game answered "Role 'tester'" instead of "Role 'viewer'". The run reported the mismatch rather
than assert against it, the stale row was removed, and the P2 half then ran correctly. Nothing was
written to *<P2_GAME_NAME>* at any point in the run.

**B4, the original rows restored.** The seeds left Part B exactly as they entered it. The account
writes again — `KING22304-QA-20260916-0944-restore` was created — and the demotion token, by then
far past its 10-minute life, came back as `CONFIRM_TOKEN_INVALID` with the message
`confirm token expired`. That last answer also supplies the evidence `grey-13` was meant to produce
and could not.

### Run events

The MCP connector dropped and reconnected three times during Part A, at about 10:03, 10:27 and 10:34
UTC. Each time the run continued from the next case; no case was lost and no call was left in an
unknown state, because every write of this plan is confirmed explicitly and the read that follows it
showed the result. One probe was run wrongly and re-run: the confirm-token expiry (`grey-13`) was
first confirmed 9 minutes and 52 seconds after the token was minted, which is inside the 10-minute
life, so it executed and created the webhook `KING22304-QA-20260916-0944-exp` that the plan intended
never to exist. A fresh token was minted for `KING22304-QA-20260916-0944-exp2` and confirmed after
its 10 minutes had really passed.

## 4. Findings

### F1 — the default webhook listing hides every DEPRECATED webhook, so a game inventory is short   [severity: moderate]
Case: list-ok-01   Tool: kinoa_webhook_list   Part: A

Steps to reproduce:

1. Create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) — preview leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","url_template":"https://<WEBHOOK_TARGET>/qa/seed-c","request_method":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","order":1}]}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_create","intendedChange":{"name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DRAFT","call":"POST https://<WEBHOOK_TARGET>/qa/seed-c","fieldCount":1},"message":"Will create DRAFT webhook 'KING22304-QA-20260916-0944-seed-c' calling POST https://<WEBHOOK_TARGET>/qa/seed-c. No changes were made. …"},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IkdxeW5NSW9tYzhhbXdXZlZQLVRKQk1jcGhsaEVPOUN5MHh5czZVbkhhOFki…Gv1YQM2dI4wxAufHhLz1vOY7f3ClsNV39TBb5wTvbqk","expiresAt":"2026-09-16T09:56:48Z","correlationId":"a591061c-f3a0-4a56-805e-bc5135f35856","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","url_template":"https://<WEBHOOK_TARGET>/qa/seed-c","request_method":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","order":1}],"confirm_token":"eyJhcmdzSGFzaCI6IkdxeW5NSW9tYzhhbXdXZlZQLVRKQk1jcGhsaEVPOUN5MHh5czZVbkhhOFki…Gv1YQM2dI4wxAufHhLz1vOY7f3ClsNV39TBb5wTvbqk"}`
   Response: `{"ok":true,"data":{"webhook":{"id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-c","requestMethod":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","placeholderType":"COMMON","required":true,"order":1}],"createdTs":1789552016653,"updatedTs":1789552016667,"authorId":"<USER_ID>","updatedAuthorId":"<USER_ID>"}}}`
   The webhook is `KING22304-QA-20260916-0944-seed-c`, id `53445ae1-78d6-4601-9e8b-5b1e1e731304`.
3. Retire it — preview leg.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","target":"DEPRECATED","deprecation_reason":"qa seed fixture"}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_status","intendedChange":{"target":"DEPRECATED","webhookId":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","currentStatus":"DRAFT"},"message":"Will move webhook 'KING22304-QA-20260916-0944-seed-c' (DRAFT) to DEPRECATED. …","warnings":["Deprecation is terminal: webhook 'KING22304-QA-20260916-0944-seed-c' can never be reactivated, only cloned."]},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6Iks1NzdWdXVxU1Bvb3k5YmM5UDZaOWVZcDZhYVNGTzVIckxFbXZabHBLWFEi…Uw6cVtYu2wSEZQm5__KMMvU8u7p80Pk6cpurdHuPzZM","expiresAt":"2026-09-16T09:57:21Z","correlationId":"53e8e58f-da2f-4d15-9551-80591efa619c","dryRun":false}}`
4. Repeat step 3 with the same arguments plus the token — execute leg.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","target":"DEPRECATED","deprecation_reason":"qa seed fixture","confirm_token":"eyJhcmdzSGFzaCI6Iks1NzdWdXVxU1Bvb3k5YmM5UDZaOWVZcDZhYVNGTzVIckxFbXZabHBLWFEi…Uw6cVtYu2wSEZQm5__KMMvU8u7p80Pk6cpurdHuPzZM"}`
   Response: `{"ok":true,"data":{"webhookId":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","target":"DEPRECATED","previousStatus":"DRAFT","applied":true}}`
5. List the game's webhooks with no filter at all.
   Request: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>"}`
   Response: `{"ok":true,"data":{"items":[{"id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3","name":"KING22304-QA-20260916-0944-seed-a","key":"king22304_qa_20260916_0944_seed_a","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-a"},{"id":"fdd7105b-eb96-451b-ab2a-55d65c0bd750","name":"KING22304-QA-20260916-0944-seed-b","key":"king22304_qa_20260916_0944_seed_b","status":"ACTIVE","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-b"}],"page":1,"pageSize":20,"totalItems":2,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`
   `KING22304-QA-20260916-0944-seed-c` is not in the list, and `totalItems` is `2`.
6. List the same game and name all three statuses.
   Request: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","status":["DRAFT","ACTIVE","DEPRECATED"],"page_size":100}`
   Response: `{"ok":true,"data":{"items":[{"id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3","name":"KING22304-QA-20260916-0944-seed-a","key":"king22304_qa_20260916_0944_seed_a","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-a"},{"id":"fdd7105b-eb96-451b-ab2a-55d65c0bd750","name":"KING22304-QA-20260916-0944-seed-b","key":"king22304_qa_20260916_0944_seed_b","status":"ACTIVE","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-b"},{"id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DEPRECATED","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-c"}],"page":1,"pageSize":100,"totalItems":3,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`
   The same game now has three webhooks and `totalItems` is `3`.

Expected: the `status` argument of `kinoa_webhook_list` says in its own schema description
"Keep only webhooks in these states; omit for all". So a call that omits `status` must return
every webhook of the game. The unfiltered total and the all-statuses total must be the same
number.

Actual: step 5 returns `{"ok":true,"data":{"items":[…two items…],"page":1,"pageSize":20,"totalItems":2,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`.
The unfiltered listing returns 2 webhooks and step 6 returns 3. The DEPRECATED webhook
`KING22304-QA-20260916-0944-seed-c` (id `53445ae1-78d6-4601-9e8b-5b1e1e731304`) is missing from
the default listing. An agent that lists a game to take stock of it reports one webhook too few,
and nothing in the answer says a status was left out. The agent would also tell the user that a
retired webhook does not exist. The caller can still see it, but only by naming every status in
the call.

Isolation: the DEPRECATED filter alone finds the same webhook, so the row and the index are fine —
`kinoa_webhook_list {"game_id":"<P1_GAME_ID>","status":["DEPRECATED"],"page_size":100}`
returned `{"ok":true,"data":{"items":[{"id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DEPRECATED","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-c"}],"page":1,"pageSize":100,"totalItems":1,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`.
`kinoa_webhook_get` on the same id also answers in full with `status` `DEPRECATED`, so only the
default listing is affected. The three single-status filters return 1 + 1 + 1 = 3, which is the
all-statuses total and not the unfiltered total. The `search` argument inherits the same blind
spot: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","search":"seed-"}`
returned only two of the three webhooks whose name holds `seed-`. Four cases of §A1 show this one
defect: `list-ok-01`, `list-ok-02`, `list-sem-04` and `list-sem-12`. `response_format` makes no
difference — the `detailed` listing is short in the same way.

### F2 — a webhook created with a `type` is missing from every listing, so it can never be found again   [severity: major]
Case: create-sem-01   Tool: kinoa_webhook_list   Part: A

Steps to reproduce:

1. Create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) whose only
   extra argument is `type` — preview leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-typed","key":"king22304_qa_20260916_0944_typed","type":"qa-typed","url_template":"https://<WEBHOOK_TARGET>/qa/typed","request_method":"POST"}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_create","intendedChange":{"name":"KING22304-QA-20260916-0944-typed","key":"king22304_qa_20260916_0944_typed","status":"DRAFT","call":"POST https://<WEBHOOK_TARGET>/qa/typed","fieldCount":0},"message":"Will create DRAFT webhook 'KING22304-QA-20260916-0944-typed' calling POST https://<WEBHOOK_TARGET>/qa/typed. No changes were made. …"},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6InJtdHpZWTQ3b1JpMFlLU3NEbWRrQ0VtdGYxT1AtM1Q4LTF1cFVTMFpHQmMi…sjnE9n-PzWFeWalyzfLlXAJQu2gWJTzYj2K0GRzodtg","expiresAt":"2026-09-16T10:08:02Z","correlationId":"bed9d1a7-73d9-4d1a-a8b6-33c15b2d3149","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-typed","key":"king22304_qa_20260916_0944_typed","type":"qa-typed","url_template":"https://<WEBHOOK_TARGET>/qa/typed","request_method":"POST","confirm_token":"eyJhcmdzSGFzaCI6InJtdHpZWTQ3b1JpMFlLU3NEbWRrQ0VtdGYxT1AtM1Q4LTF1cFVTMFpHQmMi…sjnE9n-PzWFeWalyzfLlXAJQu2gWJTzYj2K0GRzodtg"}`
   Response: `{"ok":true,"data":{"webhook":{"id":"3c2b8ba3-c71c-4878-b036-d1114ef1e9cc","name":"KING22304-QA-20260916-0944-typed","key":"king22304_qa_20260916_0944_typed","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/typed","requestMethod":"POST","type":"qa-typed","createdTs":1789552690332,"updatedTs":1789552690338,"authorId":"<USER_ID>","updatedAuthorId":"<USER_ID>"}}}`
   The webhook is `KING22304-QA-20260916-0944-typed`, id `3c2b8ba3-c71c-4878-b036-d1114ef1e9cc`,
   status `DRAFT`.
3. List the game's webhooks and name every status, so no status filter can hide anything.
   Request: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","status":["DRAFT","ACTIVE","DEPRECATED"],"page_size":100}`
   Response: `{"ok":true,"data":{"items":[{"id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3","name":"KING22304-QA-20260916-0944-seed-a","key":"king22304_qa_20260916_0944_seed_a","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-a"},{"id":"fdd7105b-eb96-451b-ab2a-55d65c0bd750","name":"KING22304-QA-20260916-0944-seed-b","key":"king22304_qa_20260916_0944_seed_b","status":"ACTIVE","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-b"},{"id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DEPRECATED","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-c"},{"id":"ff70147f-5605-4710-99cc-f58528ca307d","name":"KING22304-QA-20260916-0944-main","key":"king22304_qa_20260916_0944_main","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/main"},{"id":"3334645d-e665-4f6c-af63-f8b3987f2943","name":"KING22304-QA-20260916-0944-pers","key":"king22304_qa_20260916_0944_pers","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/pers"},{"id":"885d1246-571f-4f34-86ba-6c9b3e0f0876","name":"KING22304-QA-20260916-0944-get","key":"king22304_qa_20260916_0944_get","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/get/${event}"}],"page":1,"pageSize":100,"totalItems":6,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`
   `KING22304-QA-20260916-0944-typed` is not there, and `totalItems` is `6`.
4. Search the listing for the name of the new webhook.
   Request: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","search":"typed"}`
   Response: `{"ok":true,"data":{"items":[],"page":1,"pageSize":20,"totalItems":0,"totalPages":0,"hasMore":false,"responseFormat":"concise"}}`
5. Read the same webhook by its id.
   Request: `kinoa_webhook_get {"game_id":"<P1_GAME_ID>","webhook_id":"3c2b8ba3-c71c-4878-b036-d1114ef1e9cc"}`
   Response: `{"ok":true,"data":{"webhook":{"id":"3c2b8ba3-c71c-4878-b036-d1114ef1e9cc","name":"KING22304-QA-20260916-0944-typed","key":"king22304_qa_20260916_0944_typed","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/typed","requestMethod":"POST","type":"qa-typed","createdTs":1789552690000,"updatedTs":1789552690000,"authorId":"<USER_ID>","updatedAuthorId":"<USER_ID>"}}}`
   The webhook exists and is readable. Only the listing cannot see it.

Expected: `kinoa_webhook_create` "creates the same webhooks with the same parameter set as the
dashboard UI", and `type` is one of that parameter set — its schema calls it a "Free-form grouping
label the dashboard shows; not validated". `kinoa_webhook_list` must then return that webhook like
any other, because the AC says the tool "returns webhooks in the unified pagination envelope".

Actual: step 3 returns a listing of 6 webhooks with `"totalItems":6`, and
`KING22304-QA-20260916-0944-typed` (id `3c2b8ba3-c71c-4878-b036-d1114ef1e9cc`) is not one of
them. The webhook is invisible to `kinoa_webhook_list` under every status filter, under `search`
by name, under `search` by its exact id and under the `key` filter. `kinoa_webhook_get` still
returns it. An agent can therefore create a webhook and then be unable to find it again: the id
from the create response is the only way back to it, and the listing is the tool the other
webhook tools tell the agent to use to get an id. If the agent loses that id, the webhook is out
of reach for every webhook tool, and an ACTIVE one would keep firing at its target with no way
to list it.

Isolation: the trigger is the `type` argument alone. The webhook of step 2 was created with only
the five required arguments plus `type`, and it disappeared. The webhook
`KING22304-QA-20260916-0944-main` (id `ff70147f-5605-4710-99cc-f58528ca307d`) was created in the
same game, in the same minute, with the same `url_template` shape, the same `request_method`, a
`json` body and a placeholder field — but no `type` — and step 3 shows it in the listing. The
second webhook of this run that carries a `type`,
`KING22304-QA-20260916-0944-full` (id `ce95fc83-7cb5-43c4-9f9f-9f17899422a0`, `type` `qa-full`),
is missing from the same listing in the same way, so the behaviour is repeatable and is not about
`headers`, `description` or the number of placeholder fields. None of the six visible webhooks
carries a `type`.

A `type` added later by an ordinary edit hides the webhook in the same way, so an operator can
lose a webhook that was listed a moment ago. `KING22304-QA-20260916-0944-main`
(id `ff70147f-5605-4710-99cc-f58528ca307d`) was in the listing of step 3 above. It was then
updated with
`kinoa_webhook_update {"game_id":"<P1_GAME_ID>","webhook_id":"ff70147f-5605-4710-99cc-f58528ca307d","type":"qa-main","description":"edited as draft","confirm_token":"eyJhcmdzSGFzaCI6ImNpcUdBdXJaeHRBcmE4RElaM1pVMk1iR0g3b2hiZDBDbTZNQUg4NGYxVkUi…0mF5jxFFjTdEvZn6VVNVk2OZ2NgSDIvbtjnOGfUqW-M"}`,
which answered
`{"ok":true,"data":{"webhook":{"id":"ff70147f-5605-4710-99cc-f58528ca307d","name":"KING22304-QA-20260916-0944-main",…,"type":"qa-main","description":"edited as draft","createdTs":1789552541000,"updatedTs":1789553562283,…}}}`.
The very next call,
`kinoa_webhook_list {"game_id":"<P1_GAME_ID>","status":["DRAFT","ACTIVE","DEPRECATED"],"page_size":100}`,
returned 11 items and `KING22304-QA-20260916-0944-main` was no longer one of them. Nothing in the
update response warns that the webhook will leave the listing.

See also F1, which is a different blind spot of the same listing: F1 hides a whole status, F2
hides a single webhook whatever its status.

### F3 — a write on a game the caller cannot reach is refused with a role message, which points at the wrong cause   [severity: minor]
Case: create-iso-01, clone-iso-03, update-iso-03, status-iso-03, test-iso-03, role-test-03   Tool: kinoa_webhook_create, kinoa_webhook_clone, kinoa_webhook_update, kinoa_webhook_status, kinoa_webhook_test   Part: A and B

Steps to reproduce:

1. Ask to create a webhook in a game that belongs to nobody — a well-formed uuid that is not a
   Kinoa game. Only the preview leg is needed, because a denied write never gets a token.
   Request: `kinoa_webhook_create {"game_id":"00000000-0000-4000-8000-0000000000ff","name":"KING22304-QA-20260916-0944-i1","key":"king22304_qa_20260916_0944_i1","url_template":"https://<WEBHOOK_TARGET>/qa/i1","request_method":"POST"}`
   Response: `{"ok":false,"error":{"code":"PERMISSION_DENIED","message":"Role 'viewer' is not permitted to call tool 'kinoa_webhook_create'"}}`
   There is no `meta.confirmToken` and no `data`, so the write gate was never reached.
2. Read a listing of the same unreachable game, to see what a read answers for it.
   Request: `kinoa_webhook_list {"game_id":"00000000-0000-4000-8000-0000000000ff"}`
   Response: `{"ok":false,"error":{"code":"GAME_ACCESS_DENIED","message":"You do not have access to game '00000000-0000-4000-8000-0000000000ff'"}}`
   The same game id, a different tool, and a different answer.

Expected: the plan's `create-iso-01` expects `error.code` = `GAME_ACCESS_DENIED` and no
`meta.confirmToken`, because the caller has no access to that game at all. The caller holds a
writing role on both fixture games, so "Role 'viewer'" describes a role the caller does not have
anywhere.

Actual: step 1 returns
`{"ok":false,"error":{"code":"PERMISSION_DENIED","message":"Role 'viewer' is not permitted to call tool 'kinoa_webhook_create'"}}`.
The call is refused and nothing is written, so the protection itself works. The problem is only
the message. An agent reads it as "my role is too low" and will ask an administrator for the
Operator role, when the real problem is the game id: the caller cannot reach that game. The two
tools also answer differently for one and the same game id, so an agent cannot learn one rule
for "no access to this game".

This finding is uncertain on purpose, and the reader may decide the plan is what is wrong rather
than the server. The behaviour follows the documented order of the checks: the role check runs
before the game check, and a game the caller cannot reach has no role row and no company, so the
effective role falls back to Viewer. The plan's own Part B row `role-create-02` expects exactly
this code for the same call under a Viewer role. What the run cannot decide is whether
`PERMISSION_DENIED` is the right answer when the role is only a fallback for a game that does not
exist for this caller.

Part B made this sharper. At checkpoint B2 the account held the role `tester` on both of its
games, and a fire aimed at the same unreachable game still answered
`kinoa_webhook_test {"game_id":"00000000-0000-4000-8000-0000000000ff","webhook_id":"fdd7105b-eb96-451b-ab2a-55d65c0bd750","values":{"event":"x"}}`
→ `{"ok":false,"error":{"code":"PERMISSION_DENIED","message":"Role 'viewer' is not permitted to call tool 'kinoa_webhook_test'"}}`.
The message named `viewer`, a role the caller held on neither game, while a fire on its own game
worked in the same minute. So the role in the message is not the caller's role at all: it is the
fallback the server uses for a game it cannot resolve. That case, `role-test-03`, is the sixth
and last failed case of this finding.

Isolation: the difference comes from the tool, not from the game id. `kinoa_webhook_list` and
`kinoa_webhook_get` are permitted to the Viewer role, so for the same unreachable game id they
run past the role check and answer `GAME_ACCESS_DENIED` — step 2 shows this, and
`kinoa_webhook_get {"game_id":"00000000-0000-4000-8000-0000000000ff","webhook_id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3"}`
answered `{"ok":false,"error":{"code":"GAME_ACCESS_DENIED","message":"You do not have access to game '00000000-0000-4000-8000-0000000000ff'"}}`
as well. `kinoa_webhook_create` is not permitted to Viewer, so the role check answers first. The
same call against the game *<P2_GAME_NAME>* (`<P2_GAME_ID>`), which the caller
can reach, returns a normal preview with a token, so the caller's writing role is real.

### F4 — deprecating a webhook that is already deprecated answers with an internal error that carries the raw downstream body   [severity: moderate]
Case: status-rule-06   Tool: kinoa_webhook_status   Part: A

Steps to reproduce:

1. Create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) — preview leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-st-dd","key":"king22304_qa_20260916_0944_st_dd","url_template":"https://<WEBHOOK_TARGET>/qa/st-dd","request_method":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","order":1}]}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_create","intendedChange":{"name":"KING22304-QA-20260916-0944-st-dd","key":"king22304_qa_20260916_0944_st_dd","status":"DRAFT","call":"POST https://<WEBHOOK_TARGET>/qa/st-dd","fieldCount":1},"message":"Will create DRAFT webhook 'KING22304-QA-20260916-0944-st-dd' calling POST https://<WEBHOOK_TARGET>/qa/st-dd. …"},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IkM0YXdVRkt1a0JKcjNTcTJPTWJfTWotRWc1U3JRbDhQcFFBMzdCXzNYX1Ei…cnCAaBcfAOKO2dwgpyDQg9CtSrJXIv2taoHxNJezYg0","expiresAt":"2026-09-16T10:32:23Z","correlationId":"65b98977-ea9c-43cf-9f18-ffb5cc77bace","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Request: the call of step 1 plus `"confirm_token":"eyJhcmdzSGFzaCI6IkM0YXdVRkt1a0JKcjNTcTJPTWJfTWotRWc1U3JRbDhQcFFBMzdCXzNYX1Ei…cnCAaBcfAOKO2dwgpyDQg9CtSrJXIv2taoHxNJezYg0"`
   Response: `{"ok":true,"data":{"webhook":{"id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","name":"KING22304-QA-20260916-0944-st-dd","key":"king22304_qa_20260916_0944_st_dd","status":"DRAFT",…}}}`
   The webhook is `KING22304-QA-20260916-0944-st-dd`, id `e94edaa1-bf30-42af-a04b-88bb30fb454c`.
3. Retire it — preview leg.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","target":"DEPRECATED","deprecation_reason":"qa: retired as a draft"}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_status","intendedChange":{"target":"DEPRECATED","webhookId":"e94edaa1-bf30-42af-a04b-88bb30fb454c","name":"KING22304-QA-20260916-0944-st-dd","currentStatus":"DRAFT"},"message":"Will move webhook 'KING22304-QA-20260916-0944-st-dd' (DRAFT) to DEPRECATED. …","warnings":["Deprecation is terminal: webhook 'KING22304-QA-20260916-0944-st-dd' can never be reactivated, only cloned."]},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6ImZJSkhXVFAzV3h5R1g1R1BfajVCWTZFM3Z4enY2a2xWLVd3OHRjTVlFX3ci…Aku3HgLk3dbS2rr4cz1yqq_S-l4SaAhVdfzz_h5H-O4","expiresAt":"2026-09-16T10:32:37Z","correlationId":"8b97ecca-912b-400e-8dd7-7a71a9695205","dryRun":false}}`
4. Repeat step 3 with the same arguments plus the token — execute leg.
   Request: the call of step 3 plus `"confirm_token":"eyJhcmdzSGFzaCI6ImZJSkhXVFAzV3h5R1g1R1BfajVCWTZFM3Z4enY2a2xWLVd3OHRjTVlFX3ci…Aku3HgLk3dbS2rr4cz1yqq_S-l4SaAhVdfzz_h5H-O4"`
   Response: `{"ok":true,"data":{"webhookId":"e94edaa1-bf30-42af-a04b-88bb30fb454c","name":"KING22304-QA-20260916-0944-st-dd","target":"DEPRECATED","previousStatus":"DRAFT","applied":true}}`
   The webhook is now DEPRECATED.
5. Ask to retire the same webhook a second time — preview leg. The tool gives a normal preview and a token.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","target":"DEPRECATED","deprecation_reason":"second reason"}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_status","intendedChange":{"target":"DEPRECATED","webhookId":"e94edaa1-bf30-42af-a04b-88bb30fb454c","name":"KING22304-QA-20260916-0944-st-dd","currentStatus":"DEPRECATED"},"message":"Will move webhook 'KING22304-QA-20260916-0944-st-dd' (DEPRECATED) to DEPRECATED. …","warnings":["Deprecation is terminal: webhook 'KING22304-QA-20260916-0944-st-dd' can never be reactivated, only cloned."]},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IkV5UGZCekZxMmZMeW8tUktLcGJZR2Jrb3dkRzN4aC10cXkxR2p5d0lqSjQi…DFLk8lvNUBYbETbe9daAufwvqdMFBJS6cipAmu5wFCQ","expiresAt":"2026-09-16T10:36:11Z","correlationId":"3f9427e9-32b6-4cc6-9c16-07624899f3d9","dryRun":false}}`
6. Repeat step 5 with the same arguments plus the token — execute leg.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","target":"DEPRECATED","deprecation_reason":"second reason","confirm_token":"eyJhcmdzSGFzaCI6IkV5UGZCekZxMmZMeW8tUktLcGJZR2Jrb3dkRzN4aC10cXkxR2p5d0lqSjQi…DFLk8lvNUBYbETbe9daAufwvqdMFBJS6cipAmu5wFCQ"}`
   Response: `{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"Conflict: 409 Conflict: \"{\"error\":\"Webhook is already deprecated\"}\""}}`
7. Read the webhook back — nothing was changed.
   Response of `kinoa_webhook_get {"game_id":"<P1_GAME_ID>","webhook_id":"e94edaa1-bf30-42af-a04b-88bb30fb454c"}`:
   `{"ok":true,"data":{"webhook":{"id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","name":"KING22304-QA-20260916-0944-st-dd","key":"king22304_qa_20260916_0944_st_dd","status":"DEPRECATED",…,"deprecationReason":"qa: retired as a draft","deprecationInitiatorId":"<USER_ID>"}}}`
   The first reason is kept, so the second call changed nothing.

Expected: the AC says "an invalid target returns a clear error naming the allowed targets", and the
tool description says "A webhook that is already DEPRECATED accepts nothing. Any other move is
refused naming the targets the current status allows." So this call must come back as
`VALIDATION_FAILED` with a violation that says the webhook is already deprecated. `TOOL_EXECUTION_FAILED`
is the code for an internal error, and a user asking for a state the webhook is already in is not an
internal error.

Actual: step 6 returns
`{"ok":false,"error":{"code":"TOOL_EXECUTION_FAILED","message":"Conflict: 409 Conflict: \"{\"error\":\"Webhook is already deprecated\"}\""}}`.
There is no `error.violations` array, so an agent that reads violations to find out what to fix
gets nothing. The message is the raw answer of the downstream service, with the HTTP status, the
word `Conflict` twice and a JSON body inside a JSON string. An agent is likely to read
`TOOL_EXECUTION_FAILED` as "the Kinoa MCP server is broken, retry later" and retry a call that can
never succeed.

Isolation: the same webhook answers correctly for the other two targets, so only this one
combination is wrong. `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"e94edaa1-bf30-42af-a04b-88bb30fb454c","target":"ACTIVE","confirm_token":"…"}`
returned `{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"1 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"status","rule":"backend_rejected","hint":"status deprecated webhook is read-only"}]}}`,
and the same call with `"target":"DELETED"` returned
`{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"1 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"request","rule":"backend_rejected","hint":"deprecated webhook is read-only"}]}}`.
Both are clean validation answers for the same webhook in the same state. A refused transition on
an ACTIVE webhook is also clean: `target` `DELETED` on `KING22304-QA-20260916-0944-act-upd`
(id `7ca58a94-a5ed-4241-9981-5f4617635fec`) answered
`{"ok":false,"error":{"code":"VALIDATION_FAILED",…,"violations":[{"path":"request","rule":"backend_rejected","hint":"cannot change from ACTIVE to DELETED; ACTIVE allows: DEPRECATED"}]}}`,
which is exactly the shape the AC asks for. So the tool can map this class of refusal properly; the
409 for a repeated deprecation is the one case it does not catch.

### F5 — a game id that is not a uuid is answered as a temporary outage, so an agent retries a call that can never work   [severity: moderate]
Case: grey-22   Tool: kinoa_webhook_list, kinoa_webhook_create   Part: A

Steps to reproduce:

1. List the webhooks of a game whose id is not a uuid.
   Request: `kinoa_webhook_list {"game_id":"not-a-uuid"}`
   Response: `{"ok":false,"error":{"code":"AUTHORIZATION_UNAVAILABLE","message":"Authorization is temporarily unavailable"}}`
2. Do the same with a short number as the game id.
   Request: `kinoa_webhook_list {"game_id":"123"}`
   Response: `{"ok":false,"error":{"code":"AUTHORIZATION_UNAVAILABLE","message":"Authorization is temporarily unavailable"}}`
3. Try a write tool with the same kind of game id, to show it is not only the listing.
   Request: `kinoa_webhook_create {"game_id":"123","name":"KING22304-QA-20260916-0944-g22","key":"king22304_qa_20260916_0944_g22","url_template":"https://<WEBHOOK_TARGET>/qa/g22","request_method":"POST"}`
   Response: `{"ok":false,"error":{"code":"AUTHORIZATION_UNAVAILABLE","message":"Authorization is temporarily unavailable"}}`
   No `meta.confirmToken`, so nothing could be written.
4. Use a well-formed uuid that belongs to no game, for comparison.
   Request: `kinoa_webhook_list {"game_id":"00000000-0000-4000-8000-0000000000ff"}`
   Response: `{"ok":false,"error":{"code":"GAME_ACCESS_DENIED","message":"You do not have access to game '00000000-0000-4000-8000-0000000000ff'"}}`
   The same kind of mistake — a game the caller cannot use — but a clear, permanent answer.

Expected: a `game_id` the caller cannot use must come back as `GAME_ACCESS_DENIED`, the way step 4
shows. The shape of the id does not change that: `not-a-uuid` is a permanent mistake in the
caller's own arguments, and no amount of waiting will make it work.

Actual: steps 1, 2 and 3 return
`{"ok":false,"error":{"code":"AUTHORIZATION_UNAVAILABLE","message":"Authorization is temporarily unavailable"}}`.
The word "temporarily" tells the caller to try again later. An agent will retry the call, get the
same answer, and may keep retrying, because the message says the problem is on the server side and
will pass. The real problem is in the argument the agent sent, and the answer never says so. This
also hides a real outage: when the authorization backend is truly down, the caller sees the same
message and cannot tell the two apart.

Isolation: the id only has to stop being a uuid. The same tool, the same account and the same
minute answer `GAME_ACCESS_DENIED` for the well-formed uuid of step 4, and answer normally for the
real game *<P1_GAME_NAME>* (`<P1_GAME_ID>`). An upper-case uuid is
also answered properly: `kinoa_webhook_get {"game_id":"<P1_GAME_ID_UPPERCASE>","webhook_id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3"}`
returned `{"ok":false,"error":{"code":"GAME_ACCESS_DENIED","message":"You do not have access to game '<P1_GAME_ID_UPPERCASE>'"}}`.
So the server can answer a bad game id correctly; it is only a value that cannot be read as a uuid
that turns into an outage message. Both a read tool and a write tool behave the same way, so the
problem sits before the tool, in the part that resolves the caller's role for the game.

### F6 — a DATE placeholder inside the json body is refused as "not valid JSON", which points the caller at the wrong mistake   [severity: minor]
Case: create-rule-08   Tool: kinoa_webhook_create   Part: A

Steps to reproduce:

1. Ask to create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) whose
   json body references a `DATE` field — preview leg. The preview is built from the arguments and
   reaches no service, so it succeeds.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-r8","key":"king22304_qa_20260916_0944_r8","url_template":"https://<WEBHOOK_TARGET>/qa/r8","request_method":"POST","json":"{\"when\": ${when}}","fields":[{"name":"when","fieldType":"DATE","order":1}]}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_create","intendedChange":{"name":"KING22304-QA-20260916-0944-r8","key":"king22304_qa_20260916_0944_r8","status":"DRAFT","call":"POST https://<WEBHOOK_TARGET>/qa/r8","fieldCount":1},"message":"Will create DRAFT webhook 'KING22304-QA-20260916-0944-r8' calling POST https://<WEBHOOK_TARGET>/qa/r8. No changes were made. …"},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IjRYdFpWVjl1UVVRRk5LYkVFMkQ3dEM3bVVFN0JEazcta3AtZ1NYck1LY1Ei…vo6Fyl3iIeCJ1q7n6p9H4hbLV_C2GQ9p9OvRrXQ-BSk","expiresAt":"2026-09-16T10:14:43Z","correlationId":"c9726c66-3999-44a2-a00e-d57ad72631df","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-r8","key":"king22304_qa_20260916_0944_r8","url_template":"https://<WEBHOOK_TARGET>/qa/r8","request_method":"POST","json":"{\"when\": ${when}}","fields":[{"name":"when","fieldType":"DATE","order":1}],"confirm_token":"eyJhcmdzSGFzaCI6IjRYdFpWVjl1UVVRRk5LYkVFMkQ3dEM3bVVFN0JEazcta3AtZ1NYck1LY1Ei…vo6Fyl3iIeCJ1q7n6p9H4hbLV_C2GQ9p9OvRrXQ-BSk"}`
   Response: `{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"1 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"json","rule":"backend_rejected","hint":"json must be valid JSON once placeholders are substituted"}]}}`
3. Check that nothing was created.
   Request: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","search":"KING22304-QA-20260916-0944-r8"}`
   Response: `{"ok":true,"data":{"items":[],"page":1,"pageSize":20,"totalItems":0,"totalPages":0,"hasMore":false,"responseFormat":"concise"}}`

Expected: the tool's own description says that `DATE`, `VERSION`, `ENUMERATION`, `AB_SETTINGS` and
`STRING_ARRAY` fields "render unquoted, so they work in urlTemplate and headers but cannot be used
inside the json body". A violation for this case must therefore name the field and its type, so the
caller knows the field type is the problem. The plan expected "a violation saying a `DATE` field
cannot be used inside the json body".

Actual: step 2 returns
`{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"1 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"json","rule":"backend_rejected","hint":"json must be valid JSON once placeholders are substituted"}]}}`.
This is the same message a genuinely broken json body gets. The caller's json is in fact well
formed — `{"when": ${when}}` becomes valid JSON as soon as the placeholder renders a quoted value —
so an agent reading this message will look for a syntax mistake that is not there. It has no way to
learn that the fix is to change `fieldType`, or to move the placeholder into `url_template` or a
header. Nothing is created, so nothing is lost; the cost is the caller's time and a wrong repair.

Isolation: the message is not specific to this rule. The same `"hint"` came back for a json body
that really does not parse — `create-rule-07` sent `json` `"{\"event\": ${event}, }"` with a trailing
comma and a `STRING` field, and got the identical violation
`{"path":"json","rule":"backend_rejected","hint":"json must be valid JSON once placeholders are substituted"}`.
So two different mistakes give one message. By contrast the neighbouring placeholder rules do name
the member at fault: `create-rule-03` answered
`{"path":"json","rule":"backend_rejected","hint":"json references undeclared placeholder ${ghost}"}`
and `create-rule-05` answered
`{"path":"fields[extra]","rule":"backend_rejected","hint":"fields[extra] is not referenced as ${extra} in urlTemplate, headers or json"}`.
The service can clearly produce a precise violation for a placeholder problem; it does not for this
one.

### F7 — the preview of an edit to a DEPRECATED webhook gives no warning and still hands out a confirm token, although the call can never succeed   [severity: minor]
Case: update-gap-01   Tool: kinoa_webhook_update   Part: A

Steps to reproduce:

1. Create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) — preview leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","url_template":"https://<WEBHOOK_TARGET>/qa/seed-c","request_method":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","order":1}]}`
   Response: `{"ok":true,"data":{"status":"preview",…},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IkdxeW5NSW9tYzhhbXdXZlZQLVRKQk1jcGhsaEVPOUN5MHh5czZVbkhhOFki…Gv1YQM2dI4wxAufHhLz1vOY7f3ClsNV39TBb5wTvbqk","expiresAt":"2026-09-16T09:56:48Z","correlationId":"a591061c-f3a0-4a56-805e-bc5135f35856","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Response: `{"ok":true,"data":{"webhook":{"id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","key":"king22304_qa_20260916_0944_seed_c","status":"DRAFT",…}}}`
   The webhook is id `53445ae1-78d6-4601-9e8b-5b1e1e731304`.
3. Retire it, so it becomes DEPRECATED — preview then execute.
   Request: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","target":"DEPRECATED","deprecation_reason":"qa seed fixture","confirm_token":"eyJhcmdzSGFzaCI6Iks1NzdWdXVxU1Bvb3k5YmM5UDZaOWVZcDZhYVNGTzVIckxFbXZabHBLWFEi…Uw6cVtYu2wSEZQm5__KMMvU8u7p80Pk6cpurdHuPzZM"}`
   Response: `{"ok":true,"data":{"webhookId":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","target":"DEPRECATED","previousStatus":"DRAFT","applied":true}}`
4. Ask to edit its description — preview leg. This is the step that should warn.
   Request: `kinoa_webhook_update {"game_id":"<P1_GAME_ID>","webhook_id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","description":"edited while deprecated"}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_update","intendedChange":{"webhookId":"53445ae1-78d6-4601-9e8b-5b1e1e731304","name":"KING22304-QA-20260916-0944-seed-c","status":"DEPRECATED","changes":["description"]},"message":"Will update webhook 'KING22304-QA-20260916-0944-seed-c' (DEPRECATED): description. No changes were made. Show this preview to the user for approval, then call the same tool again with identical arguments plus confirm_token from meta.","warnings":["The preview does not hold webhook 'KING22304-QA-20260916-0944-seed-c': if somebody else changes it before you confirm, this call is refused rather than overwriting them — re-run the preview if it sits unapproved for long."]},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6Im1GdkRnYzdmdUgwb25rSUlfZlNwLXk5QXEzSVRWRVNQdHZpTWo5Q3FLdWsi…hGQfi68uTpsYca_XubpyOfBUIbcKYmFmFOUH9qQVlnk","expiresAt":"2026-09-16T10:29:22Z","correlationId":"cffe5a59-61ea-4454-93c9-8e9c2bd475fc","dryRun":false}}`
   The preview says "Will update", prints `"status":"DEPRECATED"`, carries only the generic
   concurrency warning, and issues a confirm token.
5. Confirm it, as the preview told the caller to.
   Request: `kinoa_webhook_update {"game_id":"<P1_GAME_ID>","webhook_id":"53445ae1-78d6-4601-9e8b-5b1e1e731304","description":"edited while deprecated","confirm_token":"eyJhcmdzSGFzaCI6Im1GdkRnYzdmdUgwb25rSUlfZlNwLXk5QXEzSVRWRVNQdHZpTWo5Q3FLdWsi…hGQfi68uTpsYca_XubpyOfBUIbcKYmFmFOUH9qQVlnk"}`
   Response: `{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"1 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"status","rule":"backend_rejected","hint":"status deprecated webhook is read-only"}]}}`

Expected: the preview is the tool's safety step, and it already knows the status — it prints
`"status":"DEPRECATED"` in `intendedChange`. It must warn that the call will be refused, the way the
same tool warns for an ACTIVE webhook. `update-sem-04` shows that warning working:
"This webhook is ACTIVE, and the service freezes url_template, headers once a webhook leaves
DRAFT — the call will be refused naming those members. Clone it with kinoa_webhook_clone to change
them."

Actual: step 4 returns a preview whose `warnings` array holds only the generic sentence about the
preview not holding the webhook, plus a usable confirm token and the instruction "Show this preview
to the user for approval". An operator approves an edit that cannot happen. The refusal arrives only
at step 5, after the approval, and it spends one call of the write budget. For an agent driving a
human approval loop this is the worst shape: it asks a person to approve something it could have
known was impossible.

Actual, second half: the message also reads oddly. The violation is reported on `path` `status`,
an argument the caller never sent and which `kinoa_webhook_update` does not even accept
(`update-schema-04` shows `status` is rejected as an unknown property), and the hint
"status deprecated webhook is read-only" reads as though two sentences were joined.

Isolation: the same tool warns correctly for the other frozen state, so the warning mechanism
exists and only this status is missing from it. `update-sem-04` on the ACTIVE webhook
`KING22304-QA-20260916-0944-seed-b` (id `fdd7105b-eb96-451b-ab2a-55d65c0bd750`) produced the frozen
warning before the call, and `update-rule-02` then showed the matching refusal. The DEPRECATED
webhook is refused for every write tool, not only `update` — `status-rule-04` and `status-rule-05`
both answered "deprecated webhook is read-only" — and none of those previews warned either, so the
gap covers the whole read-only state.

### F8 — one approval of a test fire can be replayed for ten minutes, so an irreversible external call can happen many times   [severity: major]
Case: grey-04   Tool: kinoa_webhook_test   Part: A

Steps to reproduce:

1. Create a webhook in *<P1_GAME_NAME>* (`<P1_GAME_ID>`) — preview leg.
   Request: `kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-rp","key":"king22304_qa_20260916_0944_rp","url_template":"https://<WEBHOOK_TARGET>/qa/rp","request_method":"POST","json":"{\"event\": \"${event}\"}","fields":[{"name":"event","fieldType":"STRING","order":1}]}`
   Response: `{"ok":true,"data":{"status":"preview",…},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6IjRieXN1V2ttMVRsNnYyRUVBcHRZOV9UVWVOaGM3R2ZGeWdMNjNLTnk3azgi…SB8S5NqRPU8uaoT14x5Pn8CU4axKWZRF7fNngI9NSGw","expiresAt":"2026-09-16T10:42:12Z","correlationId":"da359658-f450-4f8e-a2e1-40aee690bdc3","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Response: `{"ok":true,"data":{"webhook":{"id":"523b2879-2a32-4b6f-b874-53b96058e9b2","name":"KING22304-QA-20260916-0944-rp","key":"king22304_qa_20260916_0944_rp","status":"DRAFT",…}}}`
   The webhook is id `523b2879-2a32-4b6f-b874-53b96058e9b2`.
3. Ask to fire it — preview leg. This is the one and only approval the operator gives.
   Request: `kinoa_webhook_test {"game_id":"<P1_GAME_ID>","webhook_id":"523b2879-2a32-4b6f-b874-53b96058e9b2","values":{"event":"replay"}}`
   Response: `{"ok":true,"data":{"status":"preview","tool":"kinoa_webhook_test","intendedChange":{"call":"POST https://<WEBHOOK_TARGET>/qa/rp","name":"KING22304-QA-20260916-0944-rp","webhookId":"523b2879-2a32-4b6f-b874-53b96058e9b2"},"message":"Will really call POST https://<WEBHOOK_TARGET>/qa/rp on behalf of webhook 'KING22304-QA-20260916-0944-rp'. No changes were made. …","warnings":["This reaches a system outside Kinoa. Whatever the call triggers there — a charge, an order, a notification — cannot be undone from here."]},"meta":{"confirmToken":"eyJhcmdzSGFzaCI6Ik1hOXEzRlp4cjBTempERmEta1dIdm1xX3g4SkhsS20xZnowejNTRmkxVkki…QqyQJHgD5JaKDDqBjp-IPggwDXWHU7gri_UOeWv0Bbg","expiresAt":"2026-09-16T10:42:45Z","correlationId":"0c5c8f39-117d-4bf7-81b0-0fb394720ef6","dryRun":false}}`
4. Confirm it once. The third party is called.
   Request: `kinoa_webhook_test {"game_id":"<P1_GAME_ID>","webhook_id":"523b2879-2a32-4b6f-b874-53b96058e9b2","values":{"event":"replay"},"confirm_token":"eyJhcmdzSGFzaCI6Ik1hOXEzRlp4cjBTempERmEta1dIdm1xX3g4SkhsS20xZnowejNTRmkxVkki…QqyQJHgD5JaKDDqBjp-IPggwDXWHU7gri_UOeWv0Bbg"}`
   Response: `{"ok":true,"data":{"webhookId":"523b2879-2a32-4b6f-b874-53b96058e9b2","request":{"method":"POST","url":"https://<WEBHOOK_TARGET>/qa/rp"},"response":{"status":200,"headers":{…,"date":"Wed, 16 Sep 2026 10:32:53 GMT",…},"body":"Hey ya! Great to see you here. Btw, nothing is configured for this request path. Create a rule and start building a mock API."}}}`
5. Send the very same call again, with the very same token. No new approval, no new preview.
   Request: `kinoa_webhook_test {"game_id":"<P1_GAME_ID>","webhook_id":"523b2879-2a32-4b6f-b874-53b96058e9b2","values":{"event":"replay"},"confirm_token":"eyJhcmdzSGFzaCI6Ik1hOXEzRlp4cjBTempERmEta1dIdm1xX3g4SkhsS20xZnowejNTRmkxVkki…QqyQJHgD5JaKDDqBjp-IPggwDXWHU7gri_UOeWv0Bbg"}`
   Response: `{"ok":true,"data":{"webhookId":"523b2879-2a32-4b6f-b874-53b96058e9b2","request":{"method":"POST","url":"https://<WEBHOOK_TARGET>/qa/rp"},"response":{"status":200,"headers":{…,"date":"Wed, 16 Sep 2026 10:33:01 GMT",…},"body":"Hey ya! Great to see you here. Btw, nothing is configured for this request path. Create a rule and start building a mock API."}}}`
   The target answered a second time, eight seconds after the first, from one approval.

Expected: the acceptance criterion says the write tools are "covered by preview/confirm", and this
tool's own preview warns that what the call triggers outside Kinoa — "a charge, an order, a
notification" — "cannot be undone from here". A confirm token for an effect that cannot be undone
must authorise exactly one such effect. Otherwise the gate counts approvals but not actions.

Actual: step 5 returns `{"ok":true,…"response":{"status":200,…"date":"Wed, 16 Sep 2026 10:33:01 GMT",…}}`,
a second real HTTP call to the third party. The token stays usable for its full 10-minute life, so
one approval authorises any number of fires in that window. The likely way this bites nobody on
purpose: an agent that retries a call it thinks timed out will send the same arguments and the same
token, and will double-fire a charge or an order without ever knowing. The operator who approved one
call has no way to ask for a single-use token.

Isolation: replay is harmless for every other write tool of this domain, because the service
refuses the repeated effect, so `kinoa_webhook_test` is the only place it matters. `grey-03` replayed
a create token — the exact same call of step 2, sent a second time — and got
`{"ok":false,"error":{"code":"VALIDATION_FAILED","message":"2 validation violation(s)","hint":"Fix every listed violation and retry the call","violations":[{"path":"name","rule":"backend_rejected","hint":"name has already been taken"},{"path":"key","rule":"backend_rejected","hint":"key has already been taken"}]}}`,
and the listing afterwards showed exactly one webhook. The difference is that a webhook has a unique
name and key to collide on, while an outgoing HTTP call has nothing to collide on: the second fire
is indistinguishable from a first. The token machinery itself is sound in every other respect —
`grey-05`, `grey-06`, `grey-10` and `grey-23` show the digest binding every argument, `grey-08`
shows it binding the tool, `grey-11` shows a tampered token refused, and `role-update-02` shows it
refused after the caller lost the right to write. Only single use is missing.

This severity may deserve raising. Stateless confirm tokens are a deliberate design of this server,
so making the fire token single-use is a product decision rather than a plain repair, and the reader
may judge the repeated firing of an irreversible external action to be `critical` rather than
`major`.

## 5. Notes

### N1 — the `search` argument passes the database wildcard `%` through, so a search for `%` returns everything   [impact: low]
Case: list-gap-02   Tool: kinoa_webhook_list   Part: A

What was seen: `kinoa_webhook_list {"game_id":"<P1_GAME_ID>","search":"%"}`
returned `{"ok":true,"data":{"items":[{"id":"68eb81bc-42c1-4978-aa7b-ed4be55a57b3","name":"KING22304-QA-20260916-0944-seed-a","key":"king22304_qa_20260916_0944_seed_a","status":"DRAFT","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-a"},{"id":"fdd7105b-eb96-451b-ab2a-55d65c0bd750","name":"KING22304-QA-20260916-0944-seed-b","key":"king22304_qa_20260916_0944_seed_b","status":"ACTIVE","urlTemplate":"https://<WEBHOOK_TARGET>/qa/seed-b"}],"page":1,"pageSize":20,"totalItems":2,"totalPages":1,"hasMore":false,"responseFormat":"concise"}}`.
That is the same answer as the listing with no `search` at all. No webhook of this game has a `%`
in its name, so a substring match should return nothing. The `%` reaches the database as a `LIKE`
wildcard.

Why it is not a finding: the call succeeds, the answer stays inside the game, and no acceptance
criterion says what a wildcard character in `search` does. A search for ordinary text still works
correctly, and text with a `%` in it is rare in a webhook name.

Suggested action: escape `%` and `_` in the `search` and `key` values before they reach the
database, so the arguments are matched as plain text.

### N2 — the pre-existing webhook `test` of *<P2_GAME_NAME>* has the word `test` as its url template, which today's rules refuse   [impact: low]
Case: get-sem-03   Tool: kinoa_webhook_get   Part: A

What was seen: `kinoa_webhook_get {"game_id":"<P2_GAME_ID>","webhook_id":"<P2_ACTIVE_WEBHOOK_ID>"}`
returned `{"ok":true,"data":{"webhook":{"id":"<P2_ACTIVE_WEBHOOK_ID>","name":"test","key":"test","status":"ACTIVE","urlTemplate":"test","requestMethod":"GET","json":"{\"test\":\"${Test}\"}","fields":[{"name":"Test","fieldType":"STRING","placeholderType":"COMMON","description":"asdf","required":true,"defaultValue":"asdf","order":0}],"description":"test","createdTs":1682341418000,"updatedTs":1689841546000,"authorId":"<OTHER_USER_ID>","updatedAuthorId":"<OTHER_USER_ID>"}}}`.
This webhook is ACTIVE and its `urlTemplate` is the word `test`, not a URL. Its field `Test` has
`order` `0`. A create with that url template is refused today: `create-rule-06` got
`{"path":"urlTemplate","rule":"backend_rejected","hint":"urlTemplate must be an absolute http(s) URL"}`.

Why it is not a finding: this is old data from 2023 that the service accepted before it had a URL
rule. The tool reads it back correctly and no webhook tool of this run wrote to it. Nothing is
broken for the caller.

Suggested action: no action for the tools. Whoever cleans up the *<P2_GAME_NAME>* game may want to
retire this row, because an ACTIVE webhook with no real url cannot fire anywhere.

### N3 — a create response reports timestamps in milliseconds, and every later read rounds the same timestamp to the second   [impact: low]
Case: create-ok-01   Tool: kinoa_webhook_create   Part: A

What was seen: the execute leg of
`kinoa_webhook_create {"game_id":"<P1_GAME_ID>","name":"KING22304-QA-20260916-0944-main","key":"king22304_qa_20260916_0944_main",…}`
returned `…"createdTs":1789552540551,"updatedTs":1789552540563,…` for the webhook
`KING22304-QA-20260916-0944-main`, id `ff70147f-5605-4710-99cc-f58528ca307d`. The read right
after it, `kinoa_webhook_get {"game_id":"<P1_GAME_ID>","webhook_id":"ff70147f-5605-4710-99cc-f58528ca307d"}`,
returned `…"createdTs":1789552541000,"updatedTs":1789552541000,…` for the same webhook. The two
answers differ by 449 milliseconds, and the read also makes `createdTs` and `updatedTs` equal
where the create response had them 12 milliseconds apart.

Why it is not a finding: nothing is lost and no acceptance criterion says how precise a timestamp
is. Both values point at the same second, and the webhook itself did not change between the two
calls. The same difference appeared on every create of this run, so it is the shape of the
answers, not a data problem.

Suggested action: report the timestamps with the same precision everywhere, so that an agent
which compares a create response with a later read does not think the webhook was changed.

### N4 — moving an ACTIVE webhook to ACTIVE is accepted and answers `applied: true`, although nothing changed   [impact: low]
Case: status-rule-02   Tool: kinoa_webhook_status   Part: A

What was seen: `kinoa_webhook_status {"game_id":"<P1_GAME_ID>","webhook_id":"7ca58a94-a5ed-4241-9981-5f4617635fec","target":"ACTIVE","confirm_token":"eyJhcmdzSGFzaCI6IklIdGFKYzNEckdSQk92QlM0aW9BOHFETVhmWWZyY0ZwT2NIOF9FeXB2b28i…9kfs1fj0SkU1MEVfqfMoM1l3oHqX3I-z57EM1IiFtgk"}`
on the already ACTIVE webhook `KING22304-QA-20260916-0944-act-upd` returned
`{"ok":true,"data":{"webhookId":"7ca58a94-a5ed-4241-9981-5f4617635fec","name":"KING22304-QA-20260916-0944-act-upd","target":"ACTIVE","previousStatus":"ACTIVE","applied":true}}`.
The preview before it said "Will move webhook '…' (ACTIVE) to ACTIVE."

Why it is not a finding: nothing is broken. The webhook was ACTIVE before and is ACTIVE after, and a
read right afterwards showed `"status":"ACTIVE"` with the same definition. The tool description says
"Any other move is refused", and ACTIVE to ACTIVE is arguably not a move at all.

Suggested action: either refuse the no-op the way the other wrong transitions are refused, or answer
`applied: false`, so an agent that reads `applied` does not record a change that never happened.

## 6. AC traceability

| # | Acceptance criterion | Cases | Verdict | Finding |
|---|---|---|---|---|
| 1 | `kinoa_webhook_list` returns webhooks in the unified pagination envelope with server-side search (`response_format: concise │ detailed`); the compact view carries `urlTemplate`, method, `headers`, `json` and `fields`; `kinoa_webhook_get` returns the full webhook | §A1 (all 33 cases), §A2 (all 17 cases), H1 | **not met** | F1, F2, and the compact-view clause: no listing carries `requestMethod`, `headers`, `json` or `fields` in either format (H1). The envelope, the paging, the search and `kinoa_webhook_get` itself are correct |
| 2 | `kinoa_webhook_create` creates the same webhooks with the same parameter set as the dashboard UI — no more, no less; the new webhook starts as DRAFT | §A3 (all 38 cases), H2, H17, H18 | **met, with three reservations** | The parameter set round-trips exactly and every create starts as DRAFT. `security` is not offered (H2); a webhook created with a `type` cannot be found again (F2); and the refusal of a `DATE` placeholder inside the json body does not say why (F6) |
| 3 | `kinoa_webhook_clone` clones a webhook (the existing copy endpoint) | §A4 (all 17 cases) | **met** | — |
| 4 | `kinoa_webhook_update` applies partial updates; nothing is silently lost | §A5 (all 30 cases), H7, H11; `grey-17` for the ETag half | **met, with one reservation** | The update contract itself is correct in full. F7 is about its preview: an edit to a DEPRECATED webhook is previewed and given a token although the call can never succeed. The ETag half is not observable (`grey-17`, section 8). The one failed case, `update-ok-02`, failed on its listing step only (F2) |
| 5 | `kinoa_webhook_status` handles the lifecycle with a target parameter — ACTIVE, DEPRECATED and DELETED (wraps the hard-delete endpoint, DRAFT only — the preview warns); an invalid target returns a clear error naming the allowed targets | §A6 (all 26 cases), H3, H4, H5, H6 | **met, with one exception** | F4: a repeated deprecation answers `TOOL_EXECUTION_FAILED` with the raw downstream body instead of a clear error. Every other transition and refusal is correct, and the delete warning is exactly as promised |
| 6 | `kinoa_webhook_test` fires the webhook with the given field values — a real HTTP call to the external target, guarded as a write and available to the Tester role; the response (status, body) is returned so the operator sees how the target answered | §A7 (all 19 cases), `role-test-02`, H8, H9, H10 | **met, with one reservation** | The fire is real, the target's status, headers and body come back, and `role-test-02` proves the Tester role may fire it while it may not create, clone, update or publish one. The reservation is F8: the confirm token is replayable, so "guarded as a write" holds for one approval but not for one action |
| 7 | The webhook service upgrade to kinoa-bom 4.x | — | **not observable** | Section 8 |
| 8 | The write tools are covered by preview/confirm, rate limiting and audit; the Viewer/Operator mapping; the validation contract | `pre-02`, `pre-03`, every `schema` row of every section, §A8, Part B (all 29 cases), H16 | **met, except what cannot be observed, with two reservations** | Preview and confirm are proven for the argument digest, the tool binding, tampering and demotion (`role-update-02`). The two reservations are F8, a fire token that can be replayed within its 10 minutes, and F7, a preview that approves a call which cannot succeed. The role mapping is correct at Viewer, Tester and Operator, and GAME scope beats COMPANY scope. The validation contract holds everywhere except F4 and F5. The rate limits are not testable through this connector and the audit log is not observable (section 8) |
| 9 | The demo: list, create with fields, test-fire, activate, deprecate | `list-ok-01`, `create-ok-02`, `test-ok-02`, `status-ok-01`, `status-ok-02` | **met, with one caveat** | Every step of the demo works. The caveat is F2: the demo webhook `KING22304-QA-20260916-0944-full` was created with a `type`, so the very first step of the demo — the listing — does not show it |

## 7. Hypothesis verdicts

| # | What it said | Verdict | Evidence |
|---|---|---|---|
| H1 | the listing does not carry the request definition, although the AC asks the compact view to carry `urlTemplate`, method, `headers`, `json` and `fields` | **CONFIRMED** | `list-ok-01`, `list-ok-02`: no item in either response format carries `requestMethod`, `headers`, `json` or `fields`. The compact view carries `id`, `name`, `key`, `status`, `urlTemplate` only; `detailed` adds `description`, the timestamps, the author ids and the deprecation reason. The AC clause is not met — see the section 6 row for bullet 1 |
| H2 | `security` is not part of the create parameter set | **CONFIRMED** | `create-schema-08`: `{"rule":"input_schema","hint":"property 'security' is not defined in the schema and the schema does not allow additional properties"}`. Whether the dashboard itself offers a security setting could not be checked from here (section 8) |
| H3 | an invalid target names the allowed targets | **CONFIRMED with one exception** | `status-schema-01` lists the three targets; `status-rule-03` answers "cannot change from ACTIVE to DELETED; ACTIVE allows: DEPRECATED". The exception is F4, where a repeated deprecation answers `TOOL_EXECUTION_FAILED` instead |
| H4 | `DELETED` is a hard delete, DRAFT only, and the preview warns | **CONFIRMED** | `status-ok-04`, `status-sem-02`, `status-sem-03`, `status-rule-03`, `status-rule-05`. The full verdict is in section 3 |
| H5 | `DEPRECATED` is terminal and the row stays | **CONFIRMED** | `pre-13`, `status-ok-02`, `status-sem-01`, `status-sem-04`, `status-rule-04`, `status-rule-05`, `status-rule-06`. The row stays, is gettable in full and is listed under the `DEPRECATED` filter; afterwards it is read-only for every tool |
| H6 | the activation is not conditioned on an ETag and says so | **CONFIRMED** | `status-ok-01`: the second warning is "This transition is not conditioned on an ETag, so a change somebody else makes in the meantime is not detected." Recorded, not a defect |
| H7 | partial updates, nothing silently lost | **CONFIRMED** | `update-ok-01` to `update-ok-05`, `update-sem-01`, `update-sem-02`. The `fields` replacement is announced in the preview before it happens, so the loss is documented rather than silent |
| H8 | the write budget answers before the tool's own 10-a-minute cap | **UNPROVEN** | `grey-01` and `grey-02` are `BLOCKED`: this connector cannot place eleven executing calls inside one minute (measurements in section 8). Neither `Write rate limit exceeded` nor `Rate limit exceeded for kinoa_webhook_test` was ever seen |
| H9 | an unreachable target answers 200 with an `error` member | **CONFIRMED** | `test-sem-01`: `"response":{"status":200,…,"body":"{\"error\":\"I/O error on POST request for \\"https://kinoa-qa-unreachable.invalid/hook\\": kinoa-qa-unreachable.invalid: Name does not resolve\"}"}` |
| H10 | missing placeholder values are mapped to `VALIDATION_FAILED`, not reported as the target's 422 | **CONFIRMED** | `test-rule-01` gives one violation per missing field ("vip is required", "event is required"); `test-gap-02` gives "amount must be a number value". No `data.response` is returned in either case |
| H11 | an ACTIVE webhook freezes its members and allows only NEW fields | **CONFIRMED** | `update-ok-09` added a NEW field to an ACTIVE webhook; `update-rule-02`, `update-rule-03` and `update-rule-04` were each refused with a violation naming the frozen member; the preview warned about it first |
| H12 | a webhook of another game is not found, never returned | **CONFIRMED** | `get-iso-02`, `get-iso-03`, `clone-iso-02`, `clone-iso-04`, `update-iso-02`, `update-iso-04`, `status-iso-02`, `status-iso-04`, `test-iso-02`, `test-iso-04`. Every one answers `webhook_not_found` naming the id and the game it was asked for, and no write leaked a token |
| H13 | the key format rule is the service's, not the schema's | **CONFIRMED** | `create-rule-04` and `clone-rule-03`: the schema accepts `9king22304_…` and the service refuses it on the confirm leg with "key must start with a letter and contain only letters, digits, '_' or '-'" |
| H14 | how `search` matches | **CONFIRMED (observed)** | `list-sem-05`: the match ignores upper and lower case. `list-sem-06`: an exact webhook id matches. `list-gap-02`: the database wildcard `%` passes through (note N1) |
| H15 | the server instructions name every webhook tool | **UNPROVEN** | `pre-09` is `BLOCKED`: the `initialize` instructions reach this session cut off before the webhook paragraph, so the text could not be read |
| H16 | preview/confirm, rate limiting and audit guard the write tools | **PARTLY CONFIRMED** | Preview and confirm work throughout §A8 and in every write case, with two gaps: F8, a fire token that can be replayed inside its 10 minutes, and F7, a preview that approves a call which can never succeed. The rate limits are `UNPROVEN` (H8) and the audit log is not observable through the protocol (`grey-16`, section 8) |
| H17 | a new webhook starts as DRAFT | **CONFIRMED** | `create-ok-01` to `create-ok-04`, and every other create of the run: `data.webhook.status` is `DRAFT` every time, and the create body never accepts a status |
| H18 | PERSONALIZED placeholders on create | **CONFIRMED** | `create-ok-03` created a webhook with a `PERSONALIZED` field with no player field to match, and `test-gap-03` fired it with a value for that placeholder and got `200` |

## 8. Not covered / blocked

| What | Why |
|---|---|
| The webhook service upgrade to kinoa-bom 4.x (AC bullet 7) | Not observable through the MCP protocol. Nothing in any tool answer names the downstream service version |
| The audit log for this run's calls (`grey-16`, the audit half of AC bullet 8) | Not observable through the MCP protocol. The report can say the writes were previewed and confirmed, but not that they were written to an audit log |
| Whether the dashboard offers a `security` setting on a webhook (part of H2) | The run reaches the stand only through the MCP connector and cannot see the dashboard UI. What is proven is that the MCP create tool has no `security` argument |
| `grey-01` — the write rate limit | The connector cannot place eleven executing calls inside one minute. The eleven confirmed fires ran from 10:38:58 to 10:40:49 UTC, a span of 111 s, mean 11.1 s per call, with at most six inside any 60-second window. The limit of ten per minute was never reached, so `RATE_LIMITED` never appeared |
| `grey-02` — the tool's own fire cap | Depends on `grey-01` reaching the limit, which it did not |
| `grey-14` — the preview rate limit | Same reason. The eleven previews of `grey-01` were minted over a span of 55 s, a mean of 5.5 s each, so about eleven previews a minute is this connector's ceiling. Sixty-one previews inside a minute is not reachable |
| `grey-15` — a confirm token minted by another account | Needs a second Kinoa account, which this run does not have |
| `grey-17` — a concurrent change between the read and the write | Needs a second writer the protocol cannot provide |
| `test-rule-02` — the tool's own `no_url_template` refusal | Cannot be reached: `url_template` is required by the create schema (`create-schema-02`) and typed as a string by the update schema, so no webhook without a url template can be made through the tools |
| `pre-02` — the tool annotations | This connector does not expose `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` or `title`. The write list was taken instead from the five tools whose input schema declares `confirm_token` |
| `grey-13` — the confirm-token expiry | The first attempt confirmed the token 8 seconds before it expired, so it executed and created `KING22304-QA-20260916-0944-exp`. The re-run token passed its ten minutes, but by then the role had been changed to Viewer for checkpoint B1, so the permission check answered first. The expiry message itself was recovered later by `role-update-05`, which answered `confirm token expired` |
| `pre-09` — the server instructions | The `initialize` instructions reach this session cut off before the webhook paragraph, so the text could not be read and H15 stays unproven |
| `get-schema-03`, `test-schema-02`, `update-gap-03` | The connector serialises arguments against the declared type, so a JSON number for a string argument arrives as a quoted string, a string for an object argument cannot be expressed, and a JSON `null` for a string argument arrives as the text `"null"`. The type violations inside array and object literals (`create-schema-13`, `create-schema-14`, `create-schema-15`, `list-schema-07`, `update-schema-02`) were reachable and all passed |

## 9. Artifacts left behind

Every row was re-resolved with `kinoa_webhook_get` after checkpoint B4, and the statuses below are
what the stand answered then. All of them live in the game *<P1_GAME_NAME>*
(`<P1_GAME_ID>`). The game *<P2_GAME_NAME>*
(`<P2_GAME_ID>`) holds nothing from this run: it still has exactly the five
webhooks it had at the start.

The run created 24 webhooks. One was hard-deleted on purpose, so 23 are left. Four of them carry a
`type` and are therefore invisible to `kinoa_webhook_list` (F2) — they are marked **not listable**
and the only way back to them is the id in this table. Two more are DEPRECATED and so are missing
from the default listing (F1), although a status filter finds them.

| Name / key | Id | State now | Notes |
|---|---|---|---|
| `KING22304-QA-20260916-0944-seed-a` / `king22304_qa_20260916_0944_seed_a` | `68eb81bc-42c1-4978-aa7b-ed4be55a57b3` | `exists (status: DRAFT)` | the read fixture; never written to after it was made |
| `KING22304-QA-20260916-0944-seed-b` / `…_seed_b` | `fdd7105b-eb96-451b-ab2a-55d65c0bd750` | `exists (status: ACTIVE)` — irreversible | fired 5 times at the test target |
| `KING22304-QA-20260916-0944-seed-c` / `…_seed_c` | `53445ae1-78d6-4601-9e8b-5b1e1e731304` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible | reason "qa seed fixture"; missing from the default listing (F1) |
| `KING22304-QA-20260916-0944-main-v2` / `…_main_v2` | `ff70147f-5605-4710-99cc-f58528ca307d` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible | **not listable** (F2, `type` `qa-main`). Reason "qa: retired after activation". Its `description` is the text `null`, left by the blocked `update-gap-03` probe |
| `KING22304-QA-20260916-0944-full` / `…_full` | `ce95fc83-7cb5-43c4-9f9f-9f17899422a0` | `exists (status: DRAFT)` | **not listable** (F2, `type` `qa-full`). The full parameter set: 4 fields, 2 headers, a 3-placeholder json body |
| `KING22304-QA-20260916-0944-pers` / `…_pers` | `3334645d-e665-4f6c-af63-f8b3987f2943` | `exists (status: DRAFT)` | one PERSONALIZED placeholder |
| `KING22304-QA-20260916-0944-get` / `…_get` | `885d1246-571f-4f34-86ba-6c9b3e0f0876` | `exists (status: DRAFT)` | GET; its placeholder set was emptied by `update-gap-04`, so it now has no fields and a plain url |
| `KING22304-QA-20260916-0944-min` / `…_min` | `2ea3bb4e-db27-4585-afcb-a6ba13e7afaa` | `exists (status: DRAFT)` | the smallest webhook: no json, no fields, no headers |
| `KING22304-QA-20260916-0944-typed` / `…_typed` | `3c2b8ba3-c71c-4878-b036-d1114ef1e9cc` | `exists (status: DRAFT)` | **not listable** (F2, `type` `qa-typed`). Created as the isolation probe for F2; not in the plan's artifact table |
| `KING22304-QA-20260916-0944-getj` / `…_getj` | `0784194c-159e-4459-ac94-d076e3c2d35f` | `exists (status: DRAFT)` | GET with a json body, which the service accepted (`create-gap-04`) |
| `KING22304-QA-20260916-0944-seed-a (copy 1)` / `…_seed_a_copy_1` | `11610cf3-e9eb-4ca0-94b7-694de02c91b4` | `exists (status: DRAFT)` | the name and key the service derived |
| `KING22304-QA-20260916-0944-seed-a (copy 2)` / `…_seed_a_copy_2` | `5a2d4ea5-bd59-4cfb-95f8-838178f61f3f` | `exists (status: DRAFT)` | the second free variant |
| `KING22304-QA-20260916-0944-clone-b` / `…_clone_b` | `9c23709f-f918-4df9-83da-604c7a0548ce` | `exists (status: DRAFT)` | copy of the ACTIVE seed |
| `KING22304-QA-20260916-0944-clone-c` / `…_clone_c` | `265a9ebc-0056-433f-bccf-809b2770ceff` | `exists (status: DRAFT)` | copy of the DEPRECATED seed — the revival path |
| `KING22304-QA-20260916-0944-act-upd` / `…_act_upd` | `7ca58a94-a5ed-4241-9981-5f4617635fec` | `exists (status: ACTIVE)` — irreversible | carries the NEW field added while ACTIVE, and `description` "edited while active" |
| `KING22304-QA-20260916-0944-st-dd` / `…_st_dd` | `e94edaa1-bf30-42af-a04b-88bb30fb454c` | `soft-deleted (status: DEPRECATED, still gettable)` — irreversible | retired straight from DRAFT; reason "qa: retired as a draft"; missing from the default listing (F1) |
| `KING22304-QA-20260916-0944-st-del` / `…_st_del` | `86074660-04d5-4260-a382-93292599023e` | `hard-deleted (id no longer resolves)` | the delete determination subject |
| `KING22304-QA-20260916-0944-st-twin` / `…_st_twin` | `ebebb536-ddf0-4a90-a1bf-13da204325de` | `exists (status: DRAFT)` | the untouched control for the delete determination |
| `KING22304-QA-20260916-0944-dead` / `…_dead` | `41de19e9-3fb3-4df6-b3ee-fa11e5d1090f` | `exists (status: DRAFT)` | points at `https://kinoa-qa-unreachable.invalid/hook`, which never resolves |
| `KING22304-QA-20260916-0944-fire` / `…_fire` | `38ba9c46-d39a-482c-9b86-c7916111bb63` | `exists (status: DRAFT)` | the flood subject; fired 11 times at the test target |
| `KING22304-QA-20260916-0944-rp` / `…_rp` | `523b2879-2a32-4b6f-b874-53b96058e9b2` | `exists (status: DRAFT)` | **not listable** (F2, `type` `t9` set by `grey-09`). The token-replay subject; `description` "g9"; fired twice |
| `KING22304-QA-20260916-0944-exp` / `…_exp` | `091bcefb-da07-4678-be9c-5976cf4d6928` | `exists (status: DRAFT)` | the plan intended this one never to exist. It was created because the first `grey-13` attempt confirmed the token 8 seconds before it expired |
| `KING22304-QA-20260916-0944-scope-p1` / `…_scope_p1` | `5d4458f3-9b3e-4b23-9a45-6dfcd0e02f92` | `exists (status: DRAFT)` | created under the GAME Operator row of checkpoint B3 |
| `KING22304-QA-20260916-0944-restore` / `…_restore` | `b62d1a07-c12e-43bd-ab2d-7570bc747401` | `exists (status: DRAFT)` | created after the roles were restored, to prove the account writes again |

Nothing named `KING22304-QA-20260916-0944-exp2`, `-viewer`, `-tester`, `-scope-p2`, `-r3` to `-r11`,
`-s1` to `-s15`, `-g1` to `-g6`, `-i1`, `-i2`, `-dup-key`, `-ru1` to `-ru3` or `-nourl` exists: every
one of those was either refused by the schema, refused by the service, or previewed and never
confirmed.

## 10. Role rows at the end of the run

**`ORIG_ROWS` was never given to the run.** The admin-panel owner was asked for it before checkpoint
B1 and three times afterwards, and chose to restore the rows themselves at checkpoint B4 without
sending their values. The report therefore cannot print the exact `scope_type` / `scope_id` / `role`
values that are in place now.

What the protocol shows after the restore, for user `<USER_ID>`:

- On *<P1_GAME_NAME>* (`<P1_GAME_ID>`) the account can create, update,
  change status and fire again — `role-create-06` created a webhook and `role-test-05` got a fire
  preview with a token. So the effective role there permits every one of the seven tools, which
  means Operator or Owner.
- The run did not probe *<P2_GAME_NAME>* (`<P2_GAME_ID>`) after the restore,
  because no Part B case needed it and the plan forbids writing to that game.

**What the run changed along the way**, in order: GAME `P1` = `viewer` and GAME `P2` = `viewer` (B1);
both GAME rows = `tester` (B2); COMPANY = `viewer` plus GAME `P1` = `operator` (B3, applied in two
steps — the stale GAME row for `P2` had to be removed separately); then the owner's restore (B4).

**Recommended check:** whoever owns the admin panel should confirm that the rows now match what was
there before 10:52 UTC on 2026-09-16, since the run cannot verify that itself.
