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
  and the hand-over to a new chat.
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

**At the first prose write** — the first paragraph of section 3, or an earlier block:
[`language.md`](../mcp-plan/references/language.md).

**At the first finding or note:** [`report-blocks.md`](../mcp-plan/references/report-blocks.md)
(the finding block, the note block, the tracked marker, the artifact contract).

## 1. Find the files

Plans and reports live in `~/.kinoa-qa/mcp/`, outside the plugin, so a plugin update keeps them
(`file-layout.md`). The `mkdir` creates the two folders on a first use and changes nothing after.
If either folder cannot be created or written, stop before case 1 and name the path: a report
that cannot be saved loses the run's evidence.

```bash
mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports
ls ~/.kinoa-qa/mcp/plans/ | grep -- '<KEY>-'   # pick the highest -v<N>
ls ~/.kinoa-qa/mcp/reports/ | grep -- '<KEY>-' # the runs so far, oldest first
date -u +%Y%m%d-%H%M                         # the STAMP, once, at the start of a new run
grep -cE '^\| `[a-z0-9-]+` \|' ~/.kinoa-qa/mcp/plans/<plan file>   # the plan's case count
bash <plugin>/skills/mcp-plan/scripts/check-layout.sh                # before the report is finished (§3)
```

1. **Check that the references and the connector are there.** Read
   [`rules.md`](../mcp-plan/references/rules.md) with the harness's file read tool; no shell command
   does this. Then look for the connector's `kinoa_*` tools, such as `kinoa_system_ping`, in the
   session's tool list, with no call. With no `kinoa_*` tool there, the `kinoa` connector is
   missing or not logged in: stop before case 1, write no report file, run nothing, and tell the
   operator to add the `kinoa` connector or log in to it (`stand-facts.md`, connector). With
   `rules.md` unreadable, the plugin is incomplete: stop the same way and tell the operator to
   update or reinstall the `kinoa-qa` plugin.
2. **Pick the plan** — the file the user names, else the highest version. Say which, and its
   `**Plan version:**`, before case 1.
3. **Read its §0**, before any tool call. What a missing value does to the run, and what the
   runner never does about it: `fixed-data.md`, games and players (the run reads §0 and nothing
   else). A run blocked here writes no report file: the hand-over names the block and the
   constants.
4. **Pick the baseline** — the newest report for the same `<KEY>-<domain>` in which a case ran, or
   none (`file-layout.md`, finding the files). Read its findings and its notes and write down the
   ids to re-check (older reports have no Notes section, see `file-layout.md`).
5. **For a partial run, write down what runs** before case 1: the slice the operator named, the
   preflight, the cases the slice pulls in along its `Record:` values, the checkpoints that hold
   any of them, and which baseline ids it re-checks and which stay `not re-tested` (`rules.md`,
   partial runs). Every
   other case gets the exclusion label of that section.
6. **Ask one question if it is missing**: the `Run reason` value (`file-layout.md`, many reports
   for one plan). Nothing else in Part A asks anything.
7. **Resume, when the operator names an existing report file or says "continue".** The run is
   the one that file records: reuse its `Run` stamp, skip the `date` command, and read its
   section 1, section 3 (its `Record:` values and the last row of its case status table, or in a
   report with no table the last case with a status) and section 10 for `ROLES_BEFORE`. Start
   from the next case, in the plan's order; the baseline and the slice stay the ones the file
   names. Section 3 records where the run paused and where it resumed; a resume inside Part B
   follows `rules.md`, pauses. Then go to §2.
8. **Otherwise create the report file** `<KEY>-<domain>-test-report-<STAMP>.md` in
   `~/.kinoa-qa/mcp/reports/` before case 1, with section 1 only and its run lines
   filled in; add each later heading when its section is first written. Never overwrite an earlier report (`file-layout.md`, file names).

## 2. Run order

1. **Preflight.** Three of its results decide how everything else is graded: the tool inventory
   (a story tool the stand does not list: `rules.md`, statuses), the write list (`rules.md`,
   writes) and `meta.dryRun` on the first preview (`stand-facts.md`, dry-run).
2. **Part A to completion** — its preflight records `ROLES_BEFORE`, or else the run sends that
   `GET` once before B1 — then **Part B one
   checkpoint at a time** (`rules.md`, Part A / Part B): at each checkpoint its request block
   with the literal values in place of the handles, the `GET` body compared with the rows wanted,
   the 20 s wait, then the table; the last checkpoint restores `ROLES_BEFORE`.
   When the operator applies a block instead: `rules.md`, Part A / Part B.
3. **Grey-box probes last** in each part.
4. **Re-check each baseline id** through the case the plan's §1.2 names for it, inside the part
   where it belongs; an id with no §1.2 row is re-run from the old block (`file-layout.md`,
   comparing runs). A partial run re-checks only the ids it chose at §1, step 5.
5. **A partial run** keeps this order over the cases it runs: the preflight, the Part A cases in
   the plan's order, then only the checkpoints it applies, then the restore (`rules.md`, partial
   runs).

**One case at a time**, with the harness's file write and edit tools: what goes into the file
before the next call is in `rules.md`, capture at the call.

**Hand over before the context runs out.** Keep a count of this chat's tool calls, and hand over
at the next safe point when `rules.md`, pauses (when, where, how), says so. After a compaction,
check the case status table against the cases run before the next call.

## 3. Finish

1. Re-resolve every id the run created and label it per the artifact contract (`report-blocks.md`).
   A partial run adds the rows of the cases outside its slice, then counts section 2 from the
   table (`report-spec.md`, the case status table). Then run `check-layout.sh` (§1) and fix what
   it names in the report. A `PROBLEM` line about any other file was not caused by the run: do
   not fix it, and name it in the hand-over.
2. Put the `TRACKED in <KEY>` marker on every finding and note whose defect already has a bug,
   taking the key from the plan's §1.2 or from the user (`report-blocks.md`).
3. Write the comparison table if section 1 names a previous report, else "First run of this plan."
4. Read the report back once, for language only, and check that nothing was lost.
5. Check that nothing ran but the connector, the commands this file prints and the request lines
   of the plan's checkpoints (plus the snapshot `GET` and the restore `PUT`s), that no script was
   written anywhere, and that no file of the project changed (`rules.md`, target and method). In
   `~/.kinoa-qa/mcp/reports/` only the report file was added or changed, and no file of the
   plugin changed (`file-layout.md`, maintaining the rules).
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
| "The 11th write went through, so the limit is broken" | Limits count per replica: `OBSERVED` unless the stand runs a single replica (`stand-facts.md`, budgets). |

### Pace

A batched case or a shortened pause spends a budget the plan did not plan for, and the
`RATE_LIMITED` answer invalidates the case that got it.

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
| "I'll write up this section's cases once it is done" | One case at a time, before the next call (`rules.md`, capture at the call). |
| "The connector dropped, but the captured envelopes are enough to finish the report" | Hand over at once: the report file, the last row of the case status table, `continue <report file>` (`rules.md`, pauses). |
| "The context was compacted, but I remember what that response said" | Run it again or `BLOCKED — response not captured`; never graded from memory (`rules.md`, pauses). |
| "The context warning came in the middle of a checkpoint, so I hand over now" | A checkpoint is never split between chats: finish its cases first. In Part A any case is a safe point (`rules.md`, pauses). |
| "The references are not next to this skill, but I know the rules" | Stop before case 1 and ask for the plugin to be updated or reinstalled (§1, step 1). |
