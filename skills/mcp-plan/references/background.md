# Background — the runs behind the rules, and the maintainer's notes

This file shows which run made a rule necessary. Each entry is history (the report file, the
date, what happened), or a reason moved out of a rule's home. Only the
maintainer reads this file: in the pruning pass
([`file-layout.md`](file-layout.md#maintaining-the-rules--one-pruning-pass-per-run)), to see
whether a rule still has a run behind it before merging or deleting the rule. Neither the
planning chat nor the execution chat reads it.

## The runs behind the rules

### Rules are pointers

Two plans in this repo once mandated a per-case results table the report spec had already
dropped (`plan-template.md`, rules are pointers); the case status table of report section 3 is
not that table.

### Plan versions

Versions removed before the new-file rule existed cannot be restored: audiences `-v3` and `-v4`
are gone. Every version written since stays (`file-layout.md`, file names). A plan carries no
version note: owner decision, 2026-09-24.

### The player order

The audiences v3 plan and the report `KING-21973-audiences-test-report-20260902-1351.md` predate
the player-order rule and have `PLAYER1`/`PLAYER2` the other way round. The v3 plan is no longer
on disk; the v5 plan warns about the swapped labels (`fixed-data.md`, games and players).

### The connector table

The table in `stand-facts.md` (connector) was seen with the Claude Code connector in the 2026-09-24
runs: `KING-21972-events-test-report-20260924-0915.md` §8 and
`KING-21970-player-fields-test-report-20260924-0820.md` §8. In the 2026-09-17 user-lists run
(`KING-21980-user-lists-test-report-20260917-0855.md` §8) the client refused to send a string for
an integer, boolean or array argument, where the 2026-09-24 runs saw it converted.

### The name-length limit

In the player-fields run of 2026-09-24 game-meta refused names over 30 characters on the confirm
leg only, and 128 of the plan's 248 cases were `BLOCKED`: their subjects could not be created
(`KING-21970-player-fields-test-report-20260924-0820.md`, F1 and section 8). The plan's `NAME`
was 26 characters and every subject added a suffix. That report filed "every subject name must
stay at 30 characters or fewer" as a plan defect, and it became the name-length rule of
`fixed-data.md` (naming every artifact) on 2026-09-25. In the audiences run
`KING-21973-audiences-test-report-20260930-1729.md` (section 8) a probe of "255 characters of
`A`" could not be counted, and its first try was refused as too long: hence the written-out
length probe of `plan-template.md`.

### Server budgets read from the source

The budgets, TTLs, the dry-run switch and the two confirm-token messages of `stand-facts.md`
(server budgets and timings) were first read from the kinoa-mcp source at commit `c17eae4` on
2026-09-23, and read again at commit `bf41280` on 2026-09-30. At `bf41280` five tools carried a
cap of their own, each 10 / minute / user, charged on the executing leg only:
`kinoa_audience_check_player`, `kinoa_abtest_check_player`, `kinoa_player_summary`,
`kinoa_user_list_players_export` and `kinoa_webhook_test`. Until 2026-10-06 that list sat in
`stand-facts.md` as the list of capped tools; since then a plan takes each tool's cap from what
the story and the tool's `tools/list` description declare.

### Games check before role check

Since kinoa-mcp commit `bf41280` the server checks the `games[]` claim before the role. The
events report `KING-21972-events-test-report-20260924-0915.md` (F14) saw the old order, where a
write on `FOREIGN` answered `PERMISSION_DENIED` (role `viewer`). The present-tense rule is in
`rules.md` (Part A / Part B).

### Rules kept by the maintainer

Until 2026-10-06 every planning chat ran the pruning pass itself and edited the references before
it wrote a plan, and it read every earlier report of the story whole. Since 2026-10-06 the pass
is the maintainer's, the planning chat lists its lessons as `Rule change proposals` in its
hand-over, and it reads only the report parts that §1.2 needs (`mcp-plan/SKILL.md`, §1 and §3):
a report is 40–120 KB.

### The admin role API

Until 2026-09-29 every Part B checkpoint stopped and asked the operator to change the rows in the
admin panel and paste them back. In the KING-21972 run (`KING-21972-events-test-report-20260924-0915.md`)
the operator answered the stops with one word, pasted no rows even when asked twice, and the first
B2 attempt ran against a COMPANY row that did not take effect — a silent Viewer fallback that
looked like a server defect. The owner decided on 2026-09-29 that the run applies the rows itself
through the admin panel's HTTP API (`PUT`/`DELETE`/`GET …/users/<id>/roles`), reads them back with
the `GET`, and asks the operator only when the API cannot be made to show the rows wanted
(`rules.md`, Part A / Part B). The company uuid that the COMPANY rows need is asked in the plan
interview with the games, and the admin API base URL with it (owner decision, same day: asked,
not fixed in the tree). The exception was closed to that API on the same day (`rules.md`, target
and method). The three requests, their answers, that a `PUT` replaces the row of its scope and
that a `DELETE` of a missing row answers `204` were checked on the test stand on 2026-09-29; a
`GAME` `viewer` row set this way made the connector refuse a write preview with
`PERMISSION_DENIED` at once. Until 2026-10-06 `rules.md` let the operator apply a checkpoint with
no request block in a plan older than 2026-09-29. The audiences v6 plan (Part B) had to invent "a
row of `ROLES_BEFORE` on any other scope is never touched": its 2026-09-30 run found a `GAME` row
outside the fixture; that rule is now in `rules.md` (Part A / Part B).

### The tool-call limit

The line "about 120 tool calls" in `rules.md` (pauses) came in on 2026-10-06: it is in the
`2026-10-06-before-review-fixes` snapshot of the references and absent from the
`2026-10-05-before-experiments` and `2026-10-06-after-experiments` ones. No run was behind it,
and it had no entry here. On 2026-10-12 the KING-22308 feature-settings chat (report
`KING-22308-feature-settings-test-report-20261012-1535.md`, three chats under one stamp) offered
a hand-over at about 115 calls because of it, and the operator said "proceed". The templates,
A/B tests and feature-schemas runs of the same day went to 468, 755 and 763 calls in one chat
(counts from the operator, not from the reports) with no compaction. KING-23440 removed the line
on 2026-10-15: a compaction starts the post-compaction checklist, an in-chat reconnect resends
the lost call, and only a connector that does not come back, or the operator, ends a chat. The
connector drops were seen in the feature-settings report 20261014-1507 (`pre-20`,
`setting-list-schema-07`, `config-create-gap-01`, `config-update-rule-02`), the feature-schemas
report 20261014-1257 (section 8, connector drops) and the KING-22286 pushes report 20261015-1247
(six blips in one chat, no call lost).

### The pruning pass of 2026-10-12 … 2026-10-15 (KING-23440)

One line per rule, with the run behind it:

- **Preview-leg grading**, one finding per tool for "the preview approves what the confirm
  refuses" (`rules.md`, writes): KING-22308 feature-settings run 20261012-1535, F10 and F11;
  owner ruling 2026-10-12. Replaced on 2026-10-26 (KING-23809, below).
- **The wait is measured with `kinoa_system_ping`; `sleep 60` only in the foreground**
  (`stand-facts.md`, budgets): KING-22273 tags report 20261015-1107, PD-wait; KING-22288 A/B
  tests report 20261015-0916, "Run deviations" (1), a `sleep` run in the background; KING-22286
  pushes report 20261015-1247, section 3 "Pace", paced by the ping.
- **The empty string for a string-or-null argument** (`stand-facts.md`, connector): feature-settings
  reports 20261012-1535 (`config-update-schema-07`, a plain `string` took `""`) and 20261014-1507
  (`setting-update-gap-01`, `PASS` there and `BLOCKED` at its next run on the same plan version).
- **Finding ids in discovery order** (`report-blocks.md`): decided in this pass, 2026-10-15; the
  status table already carries the id at the call, so a renumbering at the finish moved ids a
  reader had already seen.
- **A read after a refused confirm** (`rules.md`, writes): KING-22286 pushes report 20261015-1247,
  F19.
- **Partial-run dependencies, counts that name their handles, every artifact in the §0 table**
  (`rules.md`, partial runs; `plan-template.md`): KING-22288 A/B tests report 20261015-0916,
  section 8 (`PART1_FIX`); feature-schemas report 20261014-1257 (`create-sem-01`); KING-22286
  pushes report, the `status-sem-10` plan defect.
- **The `curl` shapes printed before case 1; a block whose rows are in place is not sent; a case
  after the restore expects the Part A answer** (`mcp-run/SKILL.md` §1; `rules.md`, Part A /
  Part B; `plan-template.md`): KING-22273 tags report 20261015-1107, section 3 "Pause and resume"
  and PD-owner; feature-settings report 20261012-1535, `role-setting-update-05` and the "Part A
  starting state" plan defect (section 8).
- **The violation `path` without the leading slash** (`plan-template.md`): kinoa-mcp
  `McpToolRegistry.schemaViolations`, KING-23277; the strip came in with commit `c1af14c`
  (2026-10-06), verified at `e375f2d` (2026-10-15).
- **`len<N>-` probes counted by the script** (`plan-template.md`, check 19): KING-22273 tags
  report 20261015-1107, PD-literal (a 1001-character value nobody could count).
- **A plan older than its report** (check 20; `mcp-run/SKILL.md` §1 step 4): KING-22288 run
  20261015-0916 on plan v1, with the 20261012-0911 report already on disk.
- **The side-by-side suffix** (`file-layout.md`; checks 3 and 13): the two KING-22279 templates
  reports of 20261012-0741 (`-opu`, `-son`), one plan run by two chats at the same time.
- **Every sub-entity of the story is a plan input** (`story-readers.md`; `plan-template.md`,
  §1.3): the KING-22308 feature-schemas plans v1 and v2 read the research sub-task KING-22527 as
  a work item; the dashboard then refused every schema created through MCP (KING-23439,
  2026-10-13), and the root cause was filed as KING-23448 by a person, from the sub-task's
  validation table.
- **The hand-over names the check numbers; a property checked only by reading says so**
  (`mcp-plan/SKILL.md` §3): in the eval run of 2026-10-16 a planning chat wrote "every `game_id`
  is a fixture uuid" three times, and one row sent `not-a-game`. Hence check 24 too.
- **A quick `ls -la` or `echo` changes nothing** (red-flag rows of both SKILL files): in the eval
  run of the 0.7.1 skills, every chat ran read-only commands the closed list leaves out.
- **The planner reads the case status table; check 22** (`mcp-plan/SKILL.md` §1): the eval run
  of 2026-10-16 retired `create-schema-15` and `list-schema-07` of the webhooks v2 plan again,
  although the 20260916-0944 report graded both (the regression of 2026-10-06, above); the
  planner could not apply the rule because it never read the rows the report graded.

## Why the plan rules exist (moved 2026-10-06)

Moved out of the plan-side files after a blind review.

- **Fixed data.** No fixture value lives in the tree, or a shared tree would run every plan
  against one person's games. No e-mail: it is personal data, and `USER_ID` names the caller.
  Showing a saved fixture for a yes: owner decision, 2026-09-24.
- **Pre-existing entity nobody names.** The audiences v6 plan header let the run find three
  audiences and recorded "an exception to `fixed-data.md` … open until the operator names their
  ids"; `fixed-data.md` (games and players) now gives the outcome.
- **§0 after §Grey.** The blind review found §0 and `**Checked against:**` stale once §Grey added
  subjects and read code.
- **Schema check** in the registry (`VALIDATION_FAILED`, rule `input_schema`): since KING-22654.
- **Branch check.** A checkout can fall behind its remote unnoticed; reading the incoming diff
  costs more than the whole plan.
- **A finding keeps its full case:** the repro of a fixed bug often protects an AC bullet or is
  the base of another case.
- **Writing in pieces.** One reasoning step for a whole plan hit the output limit before the first
  line was saved.
- **A check that can only be `BLOCKED` is a §1 line** (2026-10-06). A review of the plans
  against five test-quality questions (real risk named; cheapest level; one outcome assertion;
  self-contained data; readable failure) found rows whose only possible status was `BLOCKED`:
  the connector cannot send them, or they need a second account, a second writer or an audit
  log. Such a row names no risk the run can check, and it inflates the counts. A proposal from
  the same review to cut the schema rows to one per tool was rejected: the schema kind stays.
  In the eval run of the same day, the webhooks v2 plan retired two schema rows as "the
  connector converts the type" although the 20260916-0944 report showed both sent and passed:
  hence the clause that a row an earlier report graded stays a case.
- **The deciding assertion first, `Also record:` after it** (2026-10-06). The same review found
  the skill weak on assertion discipline: an `Expected` cell listed every field of the response,
  so a run could not tell which mismatch was the defect and which was a note. In the eval run of
  the same day, the webhooks v2 plan wrote `Also record (OBSERVED):` on seven rows and a status
  decision after the label on three, and the events plan let the preview wording decide six
  write steps: hence the exact-label clause, check 16's label PROBLEM, and the preview-leg
  clause.
- **Every `gap` and `grey` row is wired** (2026-10-06). The same review found the skill weak on
  risk per row: probes that no hypothesis and no AC bullet named, so the reader could not say what
  a `FAIL` of that row would mean.
- **Counts relative to a baseline** (2026-10-06). Artifacts are kept, so the fixture games fill up
  with the leftovers of earlier runs, and an absolute count or a `seed-` filter matched them.
  The pattern to copy is the user-lists v3 preflight: `pre-07` records `BASE_P1_ACTIVE` and
  `BASE_P1_ALL`, and `pre-09` searches by this run's `NAME` stamp
  (`KING-21980-user-lists-test-plan-v3.md`).

## Why the run rules exist (moved 2026-10-06)

Moved out of the run-side files after a blind review.

- **The case status table.** Until 2026-10-06 `rules.md` asked for every envelope verbatim while
  `report-spec.md` called section 3 prose, not a case log, so a `PASS` envelope had no home and a
  resumed chat searched sections 1 to 3 for the last case with a status. The table is the ledger
  since then; a report written before it has none, so `check-layout.sh` check 15 skips reports
  with a `Run` stamp before 20261006.
- **The connector check at §1.** The report file was created before the first connector call, so
  a connector missing from the session left an empty report behind.
- **Mistakes old reports show:** several defects bundled under one id, a block that argues with
  its own grade, repro steps that point at case ids, and a report that opens with a results table
  (not the case status table). None of them was reviewed against the block contracts.
- **Reasons cut from the rules:** a reserved subject reused breaks its own Part B; an argument
  edited between the two write legs looks like a token expiry; a finding the owner closed costs a
  triage; repro steps without responses force a re-run.
- **`ROLES_BEFORE` is read in the preflight** (2026-10-06). Until then the `GET` went out before
  B1, so Part A ran under rows nobody had read: a Part A write refused with `PERMISSION_DENIED`
  could not be told from a defect until Part B, and the report could not say which role Part A
  ran under. As a `pre-` case right after `USER_ID`, the snapshot names Part A's role, and a
  deferred case is `BLOCKED — deferred to Part B` on evidence. A chat that resumes inside Part B
  still never takes it again.

## Validation lives in the backend (KING-23809, 2026-10-26)

The 2026-10-12 ruling made every preview token for invalid input a finding. Runs before and after
it filed the same pattern again and again, though validation in the backend only is a requirement:
the KING-22279 templates run (a duplicate slot name), the KING-22273 tags run (a category name
that another category holds, also in lower case and with spaces around it, and a rename to it)
and the KING-21979 bundles run (11 cases: an unknown id, `not-a-uuid`, an update or delete
outside DRAFT, a delete under a role that may not delete). In each one the confirm leg refused the
input. The owner ruled on 2026-10-26 that this is expected (`rules.md`, statuses
and writes): such a row is decided on the executing leg and its read. Only the MCP server's own
checks — the input schema and the role mapping — stay on the preview leg. The runs also showed
that a tool may still check a rule early (`kinoa_tag_create`, `tag_name_taken`), so a refusal on
either leg passes. When a run cannot tell whether such a behaviour is a defect, it writes a note,
not a finding: the reverse of the general rule in `report-blocks.md`, because here the doubt is
about the design, and the design is already decided.
