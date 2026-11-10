---
name: mcp-run
description: Use when asked to run, re-run, continue or finish a Kinoa MCP story test plan (a KING-<n>-<domain>-test-plan*.md file of mcp-plan) against the deployed stand through its MCP connector — a first run, a regression check, a re-run after fixes, a partial run of named cases, Part B only, or a run resumed after a pause — or to write or complete the test report of such a run, including from a captured transcript of requests and responses. Also use when asked to compare a run with the previous report or to grade cases against the owner rulings.
---

# Executing a Kinoa MCP story test plan

The plan file is the authority on the cases. The references are the authority on how to run them
and what the report is. This file is procedure and red flags only; it restates no rule.

This skill has no references of its own: it reads `mcp-plan`'s, in the same plugin at
`<plugin>/skills/mcp-plan/references/`; §1, step 1 checks that they are there before anything
else. Each phase below names what to read before it, with the harness's file
read tool. No reference is used from memory: the plan holds pointers, not the rules, and the
rules change after every run.

**Before case 1.** These decide what to capture while running, and none of it can be
reconstructed afterwards:

- [`rules.md`](../mcp-plan/references/rules.md) — the whole file: target and method, Part A /
  Part B, statuses, partial runs, writes, subjects, delete semantics, capture at the call, pauses
  (the hand-over to a new chat, the in-chat reconnect and the post-compaction checklist).
- [`fixed-data.md`](../mcp-plan/references/fixed-data.md) — which constants the plan's §0 must
  hold, and what a missing one does to the run.
- [`stand-facts.md`](../mcp-plan/references/stand-facts.md) — the admin role API (the three
  requests and their answers), budgets and pace, dry-run, what the connector does to a call.
- [`file-layout.md`](../mcp-plan/references/file-layout.md#finding-the-files), the sections on
  [finding the files](../mcp-plan/references/file-layout.md#finding-the-files),
  [many reports for one plan](../mcp-plan/references/file-layout.md#many-reports-for-one-plan)
  and [comparing runs](../mcp-plan/references/file-layout.md#comparing-runs).
- [`plan-template.md`](../mcp-plan/references/plan-template.md#cases-are-data-prose-is-commentary),
  the section "cases are data" only: how to read a case row, the steps, the `Record:` values.
- [`report-spec.md`](../mcp-plan/references/report-spec.md) — the ten sections, the case
  status table, the overall status, the comparison table, naming things.
- [`segments.md`](../mcp-plan/references/segments.md) — before the first segment, and before the
  question of §1, step 6: the brief, the return shape, the stop conditions, when segments are used,
  the dispatch and the check agent.

**At the first prose write** — the first paragraph of section 3, or an earlier block:
[`language.md`](../mcp-plan/references/language.md).

**At the first finding or note:** [`report-blocks.md`](../mcp-plan/references/report-blocks.md)
(the finding block, the note block, the tracked marker, the artifact contract).

## 1. Find the files

Plans and reports live in `~/.kinoa-qa/mcp/`, outside the plugin, so a plugin update keeps them
(`file-layout.md`). The `mkdir` creates the two folders on a first use and changes nothing after.
If either folder cannot be created or written, stop before case 1 and name the path: a report
that cannot be saved loses the run's evidence. Each command runs at the step that names it, and
none runs before step 1.

```bash
mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports
ls ~/.kinoa-qa/mcp/plans/ | grep -- '<KEY>-'   # pick the highest -v<N>
ls ~/.kinoa-qa/mcp/reports/ | grep -- '<KEY>-' # the runs so far, oldest first
date -u +%Y%m%d-%H%M                         # the STAMP, once, at the start of a new run; not for a report from a transcript (step 7)
grep -cE '^\| `[a-z0-9-]+` \|' ~/.kinoa-qa/mcp/plans/<plan file>   # the plan's case count
bash <plugin>/skills/mcp-plan/scripts/check-layout.sh                # before the report is finished (§3)
bash <plugin>/skills/mcp-plan/scripts/check-layout.sh status ~/.kinoa-qa/mcp/reports/<report file>   # after every segment agent returns (§2)
bash <plugin>/skills/mcp-plan/scripts/check-layout.sh grades ~/.kinoa-qa/mcp/reports/<report file> ~/.kinoa-qa/mcp/reports/<previous report>   # at the finish, the rows the check agent reads (§3); drop the last path when section 1 names no previous report
grep -nE '<pattern>' ~/.kinoa-qa/mcp/plans/<plan file>       # a segment agent's row or heading search, only where the harness has no file-search tool (rules.md, target and method)
grep -nE '<pattern>' ~/.kinoa-qa/mcp/reports/<report file>   # the same on the report: a section heading, a `Record:` line or a case row
sleep <n>                                    # the background wait of a pause the run cannot fill, in the background form of stand-facts.md (budgets)
```

1. **Check that the references and the connector are there.** Read
   [`rules.md`](../mcp-plan/references/rules.md) with the harness's file read tool; no shell command
   does this. Then look for the connector's `kinoa_*` tools, such as `kinoa_system_ping`, in the
   session's tool list, with no call. With no `kinoa_*` tool there, the `kinoa` connector is
   missing or not logged in: stop before case 1, write no report file, run nothing, and tell the
   operator to add the `kinoa` connector or log in to it (`stand-facts.md`, connector). With
   `rules.md` unreadable, the plugin is incomplete: stop the same way and tell the operator to
   update or reinstall the `kinoa-qa` plugin.
2. **Pick the plan** — the file the user names, else the highest version, after the `mkdir` and
   the `ls` of the plans folder. Say which, and its `**Plan version:**`, before case 1.
3. **Read its §0**, before any tool call. What a missing value does to the run, and what the
   runner never does about it: `fixed-data.md`, games and players (the run reads §0 and nothing
   else). A run blocked here writes no report file: the hand-over names the block and the
   constants.
4. **Pick the baseline** — the newest report for the same `<KEY>-<domain>` in which a case ran, or
   none, from the `ls` of the reports folder (`file-layout.md`, finding the files). Read its findings and its notes and write down the
   ids to re-check (older reports have no Notes section, see `file-layout.md`). When the plan says
   `**Earlier runs:** none` and a report for its `<KEY>-<domain>` exists, say in the first
   message that a new plan version is due, then run as the rules say: an id with no §1.2 row is
   re-run from its old block (`file-layout.md`, comparing runs).
5. **For a partial run, write down what runs** before case 1: the slice the operator named, the
   preflight, the cases the slice pulls in along its `Record:` values, the checkpoints that hold
   any of them, and which baseline ids it re-checks and which stay `not re-tested` (`rules.md`,
   partial runs). Every
   other case gets the exclusion label of that section.
6. **Send one message of questions before case 1** when the run will print `curl` lines, when
   it uses segments (`segments.md`, when segments are used), or when the `Run reason` value is
   missing; with none of the three, send none. The message asks for the `Run reason` value only
   when it is missing (`file-layout.md`, many reports for one plan). It prints the three `curl`
   lines of the admin role API in the shapes of `stand-facts.md`, when the run prints them, and
   the `sleep <n>` and `grep -nE` shapes of the block above. Write the plan's literal `ADMIN_API`
   in double quotes and `USER_ID` as a wildcard. Ask the operator to allow exactly those shapes
   before case 1. The Claude Code `permissions.allow` entry of the form `Bash(curl …)` is the one
   known example of how to allow them, not the rule. When the run uses segments, ask too, with
   its default from `mcp.segment_model` of `<plugin>/config.json`, which model the segment agents
   run on. The chat reads `<plugin>/config.json` with the harness's file read tool; no shell
   command does this. The operator answers in the same reply. Nothing else in Part A asks
   anything. A plan with no
   Part B: print no `curl` line and send no snapshot `GET` beyond a `pre-` case that sends it;
   section 10 says no checkpoint ran. A plan with Part B but no `ADMIN_API` in §0: print no `curl`
   line, write a `Plan defect for the next version` row in section 8 once step 8 has created the
   report file, and the operator applies the rows (`fixed-data.md`, games and players; `rules.md`, Part A / Part B).
7. **Resume, when the operator names an existing report file or says "continue".** The run is
   the one that file records: reuse its `Run` stamp, skip the `date` command, and read what
   step 3 of the post-compaction checklist lists (`rules.md`, pauses; in a report with no case
   status table, the last case with a status). Start from the next case, in the plan's order;
   the baseline and the slice stay the ones the file names. Section 3 records where the run
   paused and where it resumed; a resume inside Part B follows `rules.md`, pauses. Then go to
   §2. When the operator names a report file that is not in the folder, create it under the
   given stamp from the captured envelopes, and section 3 says the file was created, not
   resumed. A report written from a transcript takes the stamp the operator gives and runs no
   `date`; with no stamp given, ask for it before the file is created (`rules.md`, statuses, the
   transcript rule).
8. **Otherwise create the report file** `<KEY>-<domain>-test-report-<STAMP>.md` in
   `~/.kinoa-qa/mcp/reports/` before case 1, with section 1 only and its run lines
   filled in; add each later heading when its section is first written, in its numbered place
   (`report-spec.md`, the ten sections). Never overwrite an earlier report (`file-layout.md`,
   file names).

## 2. Run order

The main chat — the chat the operator started — runs the run. In a large run it gives the Part A
segments and §Grey to segment agents, one at a time, and checks the report file after each one
(`segments.md`).

1. **Preflight, in the main chat.** Three of its results decide how everything else is graded:
   the tool inventory (a story tool the stand does not list: `rules.md`, statuses), the write
   list (`rules.md`, writes) and `meta.dryRun` on the first preview (`stand-facts.md`, dry-run).
   The main chat loads only the schemas of its own tools: the tools of the preflight, of
   §Hand-off and of Part B, and in a run with no segments also those of Part A, §Grey and the
   section 9 re-resolve (the `_get` and list tools of what the run creates), by exact name, in
   one load (in Claude Code: `ToolSearch` with `select:`). It never loads them by keyword or all at once. The segment agents load their own
   (`segments.md`, what a segment agent reads).
   It keeps long values short in its working text. A list it needs once, such as the projects, is
   read once, and only the rows the run uses are written down. A download link is noted by its
   length and host. A link that is the evidence of a finding or a note stays verbatim
   (`rules.md`, capture at the call).
2. **Part A, by segments.** Count the tool-section cases the run will send and compare the count
   with the threshold (`segments.md`, when segments are used). With 6 or fewer, the main chat
   runs Part A itself, in the plan's order, and §Grey after it. With more than 6, take the
   segments from the plan's §1.4. A plan with no §1.4 is cut as `plan-template.md` says
   (segments, an older plan). Before the first segment agent starts, unless section 3 already
   holds the derived table, write both of these: the derived table into section 3, and a
   `Plan defect for the next version` row in section 8 that asks for §1.4 (add the section 8
   heading then; sections 4–7 go in before it, `report-spec.md`, the ten sections). Then start
   one segment agent per segment, in the plan's order, one at a time, with the brief of
   `segments.md`. Check each return against the file — the status line and the `Record:`
   lines — before the next agent starts (`segments.md`, the return shape). Then write the
   segment paragraph of section 3 (`report-spec.md`, section 3).
3. **§Grey.** In a run with segments, §Grey runs in one more agent after the last segment, briefed
   and checked the same way. In Part B too, the grey-box probes go last (`rules.md`, Part A /
   Part B).
4. **§Hand-off, in the main chat**, after Part A and §Grey.
5. **Part B, in the main chat, one checkpoint at a time** (`rules.md`, Part A / Part B). When the
   preflight did not record `ROLES_BEFORE`, the run sends that `GET` once before B1. At each
   checkpoint: its request block with the literal values in place of the handles, the `GET` body
   compared with the rows wanted, the 20 s wait, then the table. The last checkpoint restores
   `ROLES_BEFORE`. When the operator applies a block instead: `rules.md`, Part A / Part B.
6. **Re-check each baseline id** through the case the plan's §1.2 names for it. That case runs
   where it lives: in its segment, as one case of the agent's range, or in the main chat. An id
   with no §1.2 row is re-run from the old block by the main chat, in the part where it belongs
   (`file-layout.md`, comparing runs). A partial run re-checks only the ids it chose at §1, step 5.

**A partial run** keeps this order over the cases it runs: the preflight, the Part A cases in the
plan's order, then only the checkpoints it applies, then the restore (`rules.md`, partial runs).

**When an agent stops or dies.** On `stopped`, tell the operator the reason in one short message,
the blocker first. Once it is fixed, start a new agent from the first case with no row. When that
case is a write, its brief points at `rules.md`, a write that may have gone out without an answer
(`segments.md`, the brief). A gap that the status line shows after a `done` is run again the same
way. Two cases are exceptions:

- `stopped: connector lost` is handled as `rules.md`, pauses, says for the connector (case b).
- An agent that dies, returns nothing or returns `stopped: context compacted` leaves nothing to
  fix, so the operator is not asked. The section of the first case of its range with no row
  goes straight to
  [`segments.md`, a lost section](../mcp-plan/references/segments.md#a-lost-section): follow that section.

**One case at a time** in the main chat, with the harness's file write and edit tools. A segment
agent writes per plan section instead. What goes into the file before the next call is in
`rules.md`, capture at the call.

**Pauses, compactions and connector drops**: `rules.md`, pauses. Read it again before the next
call when the context was compacted or the connector dropped.

## 3. Finish

1. Close the grades and the ids of the report, in this order.
   - **Re-resolve every id the run created** and label it per the artifact contract
     (`report-blocks.md`). In a run with segments, one agent does this: it writes the section 9 rows
     itself and returns the count per label (`segments.md`). In a run with no segments, the main
     chat does it itself. The main chat writes the section 3
     paragraph of the section 9 agent from its return, as it does for a segment, including the
     agent's `deviations` line (`report-spec.md`, section 3).
   - **Check the risky grades.** The check agent does this. The main chat runs
     `check-layout.sh grades` (§1) for its rows. In a run with segments, it starts the agent after
     the section 9 agent has returned, with the brief of `segments.md` (the check agent). In a run
     with no segments, no agent starts: the main chat reads the listed rows itself, the same way.
     Then the main chat applies each `correct:` line, and only those lines:
     - it changes the row of the case status table;
     - a new `FAIL` gets its finding block, written from the section 3 envelopes of the case
       (`report-blocks.md`); when those envelopes are not there, the case is
       `BLOCKED — response not captured`, and not `FAIL`;
     - a `FAIL` that becomes any other status has its finding withdrawn, unless the block still
       accounts for another `FAIL` case: the block leaves section 4, its id leaves the line that
       opens section 4 (`report-blocks.md`, the finding block contract), and the other ids stay
       as they are;
     - a new `BLOCKED` gets a section 8 row;
     - one line of section 3, the check line, names every change, or says `none`
       (`report-spec.md`, recorded values and segment paragraphs).
   - **Count section 2, and write or recount sections 6 and 7,** from the case status table, with
     the finding ids and the finding count that the corrections left. The counts sum to the plan's
     case count, from the row count of §1. A partial run adds the rows
     of the cases outside its slice first (`report-spec.md`, the case status table). Then the main
     chat runs `check-layout.sh` (§1, the full form) once, and fixes what it names in the report.
     A `PROBLEM` line about any other file was not caused by the run: do not fix it, and
     name it in the hand-over.
2. Put the `TRACKED in <KEY>` marker on every finding and note whose defect already has a bug,
   taking the key from the plan's §1.2 or from the user (`report-blocks.md`).
3. Write the comparison table if section 1 names a previous report, else "First run of this plan."
4. Read the report back once, for language only, and check that nothing was lost.
5. Check that nothing ran but the connector, the commands this file prints and the request lines
   of the plan's checkpoints (plus the snapshot `GET` and the restore `PUT`s), that no script was
   written anywhere, and that no file of the project changed (`rules.md`, target and method). In
   `~/.kinoa-qa/mcp/reports/` only the report file was added or changed, and no file of the
   plugin changed (`file-layout.md`, maintaining the rules). This is checked from the chat's own
   record of what it ran and wrote; no command is run for it. In a run with segments, it also
   reads the `deviations` line of every agent in the segment paragraphs of section 3
   (`report-spec.md`, section 3). It reads the check line of section 3 in every run, and the
   hand-over names each `doubt:` and `unsupported:` item on it.
   If anything else changed, say so in the hand-over.
6. Hand over: the overall status, each `RED` item with steps, expected and actual, and the
   notes one line each. Then **Rule change proposals**: each rule that misled the run or was
   missing, one line each, with the case or section of the report it came from and its home file
   from the ownership table (`file-layout.md`, where each rule lives); or
   `Rule change proposals: none`. A plan defect is not a proposal: it is already a section 8 row.

## Red flags — stop and re-read the rules

Each row is a thought that arrives while running, and each one produces a report that cannot be
trusted. The answer names the rule's home; it does not define the rule.

### Scope — the connector is the only evidence

When one of these fires, something other than the connector produced the evidence: a script, a
borrowed bearer, a local server. The report then describes the chat's work, not the stand.

| Thought | What it actually is |
|---|---|
| "The plan restates the rules, I don't need the references" | The plan holds pointers; the rules may have changed since (`file-layout.md`, where each rule lives). |
| "A quick `ls -la` or `echo` changes nothing" | The shell runs only the printed commands; a no-op is a script too (`rules.md`, target and method). |
| "A curl or a quick SQL query would settle this faster" | Only protocol envelopes are evidence (`rules.md`, target and method). |
| "A curl loop with the connector's bearer fits 61 calls into a minute" | The flood goes out as the connector's own calls (`stand-facts.md`, how the flood is sent). |
| "The `kinoa` connector is missing or not logged in — the local stdio server will do" | Whole run `BLOCKED`; the stdio server resolves roles from a property (`stand-facts.md`, connector). |
| "This rule misled the run, I'll fix the reference now" | The run changes no reference; the lesson is a line under `Rule change proposals` in the hand-over (§3, step 6). |

### Fixed data and roles

A value the run found, or a role the `GET` has not shown, grades the wrong game or the wrong role,
and the report cannot tell.

| Thought | What it actually is |
|---|---|
| "§0 has `<P1_GAME_ID>`, I'll ask the operator for the real ids and carry on" | `BLOCKED — fixed data missing in §0` before case 1; the values go into a new plan version (`fixed-data.md`). |
| "`kinoa_games_list` shows a game with the plan's name, that must be `P1`" | A game the runner picked is not the fixture; nothing is written into it (`fixed-data.md`, the run reads §0). |
| "This case needs a role change, I will just ask now" | Part A asks nothing: `BLOCKED — deferred to Part B` (`rules.md`, Part A / Part B). |
| "Part A does not touch roles, the `GET` can wait until B1" | When the plan has a `pre-` case for the snapshot, it is sent there; only a plan with no such case, or a failed one, sends it before B1 (`rules.md`, Part A / Part B). |

### Grading

A status not read off an envelope is invented, and a note in place of a finding hides a defect.

| Thought | What it actually is |
|---|---|
| "That response was obviously fine — `PASS`, next case" | Capture first, grade second (`rules.md`, statuses; capture at the call). |
| "The cell lists five fields and one differs, so the case is `FAIL`" | Grade on the clause before `Also record:`; a mismatch after it is a note (`rules.md`, statuses). |
| "The wrong-type value came back `ok`, so the schema check is missing" | The connector converted it: `BLOCKED — the connector converts the argument type` (`stand-facts.md`, connector). |
| "Nothing could run, but there are no FAILs, so the report is `GREEN`" | A run with no case run is `BLOCKED — <reason>` (`report-spec.md`, the overall status). |
| "The preview gave a token for a taken name, so the preview approves what the confirm refuses — a finding" | Validation lives in the backend: grade the row on the confirm leg and the read; the token goes after `Also record:` (`rules.md`, writes). |
| "The plan row expects no token on the preview of invalid input" | An older row; grade it on the executing leg and name it as a plan defect in section 8 (`rules.md`, statuses). |
| "A Viewer got a token, but the confirm leg refused, so it is fine" | A refusal by the role mapping is the MCP server's own: graded on the preview leg (`rules.md`, writes). |
| "I cannot tell whether this token-then-refusal is a defect, so I'll leave it out" | Write a note that says what is uncertain; it is never dropped and never a finding on doubt alone (`rules.md`, writes). |
| "The 11th write went through, so the limit is broken" | Limits count per replica: `OBSERVED` unless the stand runs a single replica (`stand-facts.md`, budgets). |

### Pace

A batched case spends a budget the plan did not plan for, and the `RATE_LIMITED` answer
invalidates the case that got it. A skipped measured wait asserts too early (`plan-template.md`,
cases are data; `stand-facts.md`, budgets).

| Thought | What it actually is |
|---|---|
| "Batching independent cases saves time" | Parallel calls are for the flood only; one call at a time, in the plan's order (`stand-facts.md`, budgets). |

### Evidence and the report

What is not captured at the call is gone: the reader has the file, not the chat.

| Thought | What it actually is |
|---|---|
| "I'll reconstruct the envelope when I write the report" | Verbatim at the call; a response not captured is written as not captured (`rules.md`, capture at the call). |
| "That was odd, but nothing failed — no need to write it down" | That is a note: write it now, with the envelope (`rules.md`, capture at the call). |
| "Calling this a note keeps the report `GREEN`" | A note never replaces a finding; when unsure, write a finding (`report-blocks.md`, note or finding). |

### Re-runs and tracking

A comparison built on memory, or a run split over two files, reads as if defects were fixed that
were never re-tested.

| Thought | What it actually is |
|---|---|
| "The last report is right there — I will update it with this run" | One file per run, never overwritten (`file-layout.md`, file names). |
| "A resumed run needs a new stamp and a new file" | The report file names the run: same stamp, same file, next case (§1, step 7). |
| "The resumed chat is in Part B, so I take a fresh snapshot first" | `ROLES_BEFORE` comes from section 10 of the file; a new snapshot would restore a checkpoint's rows (`rules.md`, pauses). |
| "The tool works now, so that old finding is fixed" | `fixed` means the old repro was run again (`report-spec.md`, comparison table). |

### Partial runs

A slice run out of its context grades the context, and counts that skip cases read as a smaller
plan.

| Thought | What it actually is |
|---|---|
| "Only the named cases run — the case that creates their subject is not in the slice, so I'll use any widget I find" | The slice pulls in the case that records the value (`rules.md`, partial runs). |
| "The other cases did not run, so they stay out of the counts" | Each one is `BLOCKED — excluded by the operator (<date>)`, and the counts sum to the plan's case count (`rules.md`, partial runs). |
| "Part B only — the preflight and the snapshot are Part A business" | The preflight, with its snapshot, runs in every run; the restore runs in every run that applies a checkpoint (`rules.md`, partial runs). |

### Context

What the chat forgets after a compaction is gone unless it is already in the file.

| Thought | What it actually is |
|---|---|
| "I'll write up this section's cases once it is done" | Only a segment agent writes per section; in the main chat, one case at a time, before the next call (`rules.md`, capture at the call). |
| "The connector dropped, but the captured envelopes are enough to finish the report" | Ping and send the lost call again in place when it comes back; hand over only when it does not (`rules.md`, pauses). |
| "The context was compacted, but I remember what that response said" | Run the post-compaction checklist; a case with no envelope in the file is run again or `BLOCKED — response not captured` (`rules.md`, pauses). |
| "The context warning came in the middle of a checkpoint, so I hand over now" | The warning changes nothing. A checkpoint is split only by a compaction (step 8) or a connector that does not come back (`rules.md`, pauses). |
| "The chat has made many calls, I will hand over now" | There is no call limit; hand over only for a connector that does not come back or when the operator asks (`rules.md`, pauses). |
| "The references are not next to this skill, but I know the rules" | Stop before case 1 and ask for the plugin to be updated or reinstalled (§1, step 1). |
| "The summary says the segment is done, the file check can wait" | Check the file: status line, missing cases, `Record:` lines, before the next agent (`segments.md`). |
| "The agent can ask the operator this one thing" | An agent never asks; it stops at a safe point and returns `stopped` (`segments.md`). |
| "Seven cases is small, I'll run them inline" | With more than 6 tool-section cases, segment agents run them (`segments.md`). |
