# Segments — Part A in sub-agents, one at a time

The execution chat that the operator starts is the **main chat**. In a large run it does not send
the Part A cases itself. It gives each segment of Part A, and then §Grey, to a **segment agent**: a
sub-agent with a fresh context. The agents run one at a time, and the main chat checks the report
file after each one. What a segment is, and how a plan cuts Part A, is in
[`plan-template.md`](plan-template.md#segments). This file is the one home of the brief, the shape
of the return, the stop conditions, the recovery of a lost section, the check agent of the finish,
the threshold for segments and the dispatch. The main chat reads it before case 1
(`mcp-run/SKILL.md`). A segment agent reads the four sections its brief points at: [what a segment agent reads](#what-a-segment-agent-reads),
what the agent does, the return shape and the stop conditions. An agent that re-runs a lost section
reads a fifth, [a lost section](#a-lost-section). The check agent of the finish reads the table rows
that name `check` and [its own section](#the-check-agent), and no other section of this file.

Contents: [the brief](#the-brief) · [what a segment agent reads](#what-a-segment-agent-reads) ·
[what the agent does](#what-the-agent-does) ·
[the return shape](#the-return-shape) · [stop conditions](#stop-conditions) ·
[a lost section](#a-lost-section) · [the check agent](#the-check-agent) ·
[when segments are used](#when-segments-are-used) · [dispatch](#dispatch).

## The brief

The main chat fills in these values. The brief carries no rule text and no finding or note id.

- **The plan**: the full path of the plan file.
- **The range**: the segment id, its sections, and the first and the last case id. In a partial run,
  the brief lists the cases of the slice inside the segment; a segment that holds none of them gets
  no agent.
- **The report**: the full path of the report file, and the run stamp.
- **What to read first**: the table [what a segment agent reads](#what-a-segment-agent-reads), and
  the full path of the references folder, `<plugin>/skills/mcp-plan/references/`.
- **The handles the segment reads**, as names only. The agent takes their values from the
  `Record:` lines of section 3 of the report, never from the brief. The plan's §1.4 row names
  them in `Reads`. A derived segment and §Grey have no §1.4 row: there the handles are the ones
  the `Call` cells of the range use.
- **The executing writes of the last 60 s** before the segment: their times, up to eight, or
  `none`. They come from the return of the agent before, or, for the first agent, from the main
  chat's own calls.
- **When the first case is a write that an earlier agent may have sent**: one line that names the
  case and points at `rules.md`,
  [a write that may have gone out without an answer](rules.md#a-write-that-may-have-gone-out-without-an-answer).
- **When the range starts with a section that may be lost**: one line that names the section and
  the suffix `r<n>` for its re-run names, and a fifth pointer, to [a lost section](#a-lost-section).
  `<n>` is 1 for the first re-run of that section, and 2 for the next.
- **A pointer to this file**, by full path, and to its four sections:
  [what a segment agent reads](#what-a-segment-agent-reads),
  [what the agent does](#what-the-agent-does), [the return shape](#the-return-shape) and
  [stop conditions](#stop-conditions).

**The section 9 agent.** At the finish, one agent re-resolves every id the run created and writes
the section 9 rows itself (`report-blocks.md`, the artifact contract). Its brief is the same, with
section 9 in place of the range and no handles. It reads the rows of the table that name
`section 9` ([what a segment agent reads](#what-a-segment-agent-reads)). The names and ids that a
lost-section line of section 3 lists are ids the run created, and it writes their rows like the
others ([a lost section](#a-lost-section)).

## What a segment agent reads

A segment agent reads only the sections of the references that its cases need, and `language.md`
whole. It never runs the post-compaction checklist.

| File | Heading | Read by |
|---|---|---|
| `rules.md` | `## Target and method` | segment, check, section 9 |
| `rules.md` | `## Part A / Part B` | segment |
| `rules.md` | `## Statuses` | segment, check |
| `rules.md` | `## Partial runs` | segment, check |
| `rules.md` | `## Writes` | segment |
| `rules.md` | `## Subjects and artifacts` | segment, section 9 |
| `rules.md` | `## Delete semantics — establish, never assume` | segment |
| `rules.md` | `## Capture at the call` | segment |
| `rules.md` | `### The connector` | segment |
| `rules.md` | `### A write that may have gone out without an answer` | segment |
| `stand-facts.md` | `## Server budgets and timings` | segment, check |
| `stand-facts.md` | `## The dry-run kill-switch` | segment, check |
| `stand-facts.md` | `## Connector` | segment, check |
| `report-spec.md` | `## The ten sections` | segment, section 9 |
| `report-spec.md` | `## The case status table` | segment, check |
| `report-spec.md` | `## Recorded values and segment paragraphs` | segment, check |
| `report-spec.md` | `## Naming things — the whole report, not just the findings` | segment, section 9 |
| `plan-template.md` | `## Cases are data, prose is commentary` | segment, check |
| `fixed-data.md` | `## Games and players` | segment |
| `fixed-data.md` | `## Naming every artifact` | segment, section 9 |
| `report-blocks.md` | `## The finding block contract` | segment, check (only when it writes or judges a block) |
| `report-blocks.md` | `## The note block contract` | segment (only when it writes a block) |
| `report-blocks.md` | `## The artifact contract` | section 9 |
| `language.md` | (whole file, 55 lines) | segment, check, section 9 |

How to read the table:

- The agent finds each heading with the harness's file-search tool, and reads to the next heading
  of the same or a higher level, with the file read tool's offset and limit. In a harness with no
  file-search tool, it reads the named files whole.
- The Read by column also names `check` and `section 9`. A segment agent reads the rows that name
  `segment`.
- **The plan.** The agent never reads §0 whole. It searches for the §0 constants and the handle
  names its brief lists, and reads the hits. It reads the sections of its own range by search, with
  an offset and a limit.
- **The report.** The agent reads it by search: section 1 (the stamp, `USER_ID`), the `Record:`
  lines of the handles it reads, the end of the case status table, and the highest finding and note
  ids.
- **The tools.** The agent loads the schemas of the tools in the `Call` cells of its range by exact
  name, in one load (in Claude Code: `ToolSearch` with `select:`). It never loads them by keyword.
  The section 9 agent has no `Call` cells: it loads the `_get` and list tools of the entities the
  run created, by exact name, in one load.

## What the agent does

A segment agent runs the cases of its range as the execution chat runs Part A. The rules are the
same, and it reads them from their homes ([what it reads](#what-a-segment-agent-reads)), not from
the brief.

- Before its first case, it reads the plan, the report and the tool schemas as
  [what it reads](#what-a-segment-agent-reads) says. It never reads the whole plan or the whole
  report ([`rules.md`](rules.md#target-and-method)).
- Before its first case, it also reads the plan's header lines, §1 and §1.1, by search with an
  offset and a limit (they are short), and the preflight paragraph of section 3 of the report.
- It takes the next free finding and note ids from the report file. The file is the one source for
  them, as it is for the handles.
- It writes the report file once per plan section, when the section's last case has run, as
  [`rules.md`](rules.md#capture-at-the-call) says. It never keeps a finished section in its chat
  while it runs the next one.
- A case of its range that it leaves `BLOCKED`, and a plan defect it finds, get their section 8
  rows in the same write, in the shape and the place of
  [`report-spec.md`](report-spec.md#the-ten-sections) (section 8, and a section first written
  goes in its numbered place).
- It ends with the [return](#the-return-shape), or stops as the
  [stop conditions](#stop-conditions) say.

## The return shape

The return is short and holds no envelope. The envelopes are in the report file.

```text
last row: <case id>
counts: PASS n · FAIL n · OBSERVED n · BLOCKED n   (the cases of the range)
added: F<n>, N<n> … | none
recorded: <HANDLE>, … | none
writes of the last 60 s: <hh:mm:ss UTC>, … (up to eight) | none
deviations: <one line each> | none
done | stopped: <reason>
```

`recorded` holds names only. The times of `writes of the last 60 s` are dated as `stand-facts.md`
(budgets) says, with its ping before the return. `deviations` lists each place where the agent did
not follow a rule, one line each, and why. That includes any command it ran outside the closed list
and any file it changed other than the report (`rules.md`, target and method): the main chat writes
the line into section 3 (`report-spec.md`), and the finish reads it there. The section 9 agent
returns the count of its rows per label in place of `counts`, `added` and `recorded`.

**The return is a summary, not evidence.** Before it starts the next agent, the main chat runs
`check-layout.sh status` on the report file (`mcp-run/SKILL.md`, §1) and compares its output with
the return and with the plan:

- `last row` is the last case of the range, and `no row` names no case of the slice in the range.
  A case of the slice in the range with no row is a gap: it is run again (`mcp-run/SKILL.md`, §2,
  when an agent stops or dies). After a death, a return of nothing or a compaction, the section with
  no row is checked as [a lost section](#a-lost-section).
- Each handle the segment records has a `record:` line. The plan's §1.4 row names them in
  `Records`. A derived segment and §Grey have no §1.4 row: there they are the `Record:` labels in
  the `Expected` cells of the range. A handle with no line, or with
  `not recorded`, makes the main chat read that section 3 paragraph before the next agent.
- The finding and note ids follow the highest ids before the segment, with no gap. When they do
  not, the main chat reads the finding and note headings of sections 4 and 5 and names the gap in
  section 3.

The main chat then passes `writes of the last 60 s` to the next agent's brief.

## Stop conditions

A segment agent never asks the operator anything. When one of these happens, it stops at a safe
point and returns `stopped: <reason>`:

- the `kinoa_*` tools are not in its tool list after it loaded their schemas by exact name
  ([what it reads](#what-a-segment-agent-reads)): `stopped: connector not visible`;
- the connector does not come back, or has lost its authorization (`rules.md`,
  [the connector](rules.md#the-connector), case b): `stopped: connector lost`;
- a game of the plan's §0 answers `PROJECT_ACCESS_DENIED` to a case that does not expect it:
  `stopped: project access denied (<case id>, <game uuid>)`;
- a permission prompt is denied: `stopped: permission denied (<case id>, <the command or tool>)`.

**Context compacted.** An agent that finds its context summarized returns
`stopped: context compacted` at once. It writes nothing it no longer holds verbatim, and it never
runs the post-compaction checklist. The main chat recovers the section it was in
([a lost section](#a-lost-section)).

A safe point is a moment when the last section it ran has its rows and no executing leg is in
flight. A stop that fires inside a section has no such moment, so the agent first writes the rows
of the cases it ran in that section whose envelopes it still holds, with their `Record:` values
and the blocks they need, and then returns. A case it ran whose envelope it no longer holds gets
no row, and it is a gap that the main chat finds ([the return is a summary](#the-return-shape)).

These are not stops, and the segment goes on: a defect, a doubt about a grade, a missing owner
ruling, and a call that fails with `TOOL_EXECUTION_FAILED` after its retry. Each is graded as
`rules.md` says (statuses; partial runs, for the cases that depend on a value the case did not
record). A doubt is a note or a finding, never a question.

## A lost section

A section is lost when its agent died, returned nothing or returned `stopped: context compacted`,
and the section has no row, or only some of its rows. The rows of a section go in last, in one
edit (`rules.md`, capture at the call), so a dead agent normally leaves every row or none; a
section with some rows is the exception, and it is lost all the same. It is the section of the
first case of the range with no row. Nothing else makes a section lost. An agent that stopped for another reason wrote the rows of the cases it
ran first, so its section is not lost: the next agent starts from the first case with no row
(`mcp-run/SKILL.md`, §2, when an agent stops or dies).

The main chat starts one agent for the cases from that section to the end of the range, with the
brief line for a section that may be lost ([the brief](#the-brief)). The sections the lost agent
had written are not touched. For that section the agent does these things, in this order:

1. **Look for the lost attempt's subjects.** It reads every subject that the attempt may have
   created, by its stamp name, with the listing or the `_get` call. This step decides only the
   suffix. When it finds subjects, the re-run names carry the suffix `r<n>` of the brief, and step
   4 lists the subjects. When it finds none, the re-run names carry no suffix. No case is graded
   from the subjects it finds.
2. **Run the whole section again, from its first case, with fresh subjects.** The names it creates
   follow step 1 (`fixed-data.md`, naming every artifact). Its `Record:` values replace the lost
   ones. Each grade comes from the fresh calls. What the lost attempt wrote for the section gives
   way to the re-run: a row of one of its cases is replaced by the re-run's row, and a finding or
   note block whose `Case:` line names one of its cases is removed before the re-run writes its
   own blocks, which then take the next free ids in the file. A case whose re-run name would be longer than the
   plan's `**Name limit:**` is `BLOCKED`, and its section 8 row names the lost section.
3. **Block a case only when its starting state is gone.** This step applies to every lost section,
   whether step 1 found subjects or not. Before a case that needs a subject outside the section
   (an earlier section's handle, or a §0 fixture) to be in a given state, the agent reads that
   subject's state now.
   - If the state still holds, the case runs.
   - If the lost attempt changed the subject beyond repair, the case is `BLOCKED`. Its section 8
     row names the lost section. Examples: a count case built from a baseline, because the lost
     subjects are still counted; a delete whose target the lost attempt already removed; an
     activation that cannot be undone.
4. **Section 3** gets one line: which section was lost, whether it was re-run with the suffix,
   which cases were blocked, and the name and id of every subject of step 1. The section 9 agent
   writes their section 9 rows at the finish, with the usual labels (`report-blocks.md`, the
   artifact contract). The recovery agent writes no section 9 row.

## The check agent

At the finish of a run with segments, one more agent re-reads the grades that carry the most risk.
It starts after the section 9 agent has returned, and it runs on the model of `mcp.segment_model`
([dispatch](#dispatch)). In a run with no segments no agent starts: the main chat runs the same
check itself, from the same lines.

The agent never calls the stand, and it **never edits** a file. It returns what it would change.
The main chat applies each correction (`mcp-run/SKILL.md`, §3, step 1).

**The brief.** The main chat fills in these values. The brief carries no rule text.

- **The plan**: the full path of the plan file.
- **The report**: the full path of the report file.
- **The previous report**: the full path of the file that section 1 names, or `none`.
- **The rows**: the lines that `check-layout.sh grades` printed for the report, whole, with its last
  line `targeted <n> of <m>`. The mode is described in the script (`G. grades mode`).
- **What to read first**: the rows that name `check` in the table
  [what a segment agent reads](#what-a-segment-agent-reads), the full path of the references
  folder, `<plugin>/skills/mcp-plan/references/`, and a pointer to this section.

**What it does.** Before the first row, it reads the plan's header lines by search: the replica
count of the rate-limit rules is there. Then, for each listed row, and no other, it does these
things:

1. It finds the case's `Expected` cell in the plan, by search, and reads that row only.
2. It finds the case's evidence in section 3 of the report, by search. When the row has a finding
   or a note, it reads that block too.
3. It judges whether the grade follows the deciding clause: the clause before `Also record:`
   (`rules.md`, statuses), with the rate-limit rules of `stand-facts.md` (budgets).

A row that says `was <STATUS>` or `new` is judged the same way: by the `Expected` cell and the
evidence, and not by the previous report.

**The return.**

```text
checked: <n> rows
correct: <case id>: <OLD> → <NEW> — <deciding clause of the Expected cell> — <where the evidence is: section 3, line n> | none
doubt: <case id>: <why> | none
unsupported: F<n> | N<n>: <why> | none
done | stopped: <reason>
```

One `correct:` line per correction, and the same for `doubt:` and `unsupported:`. `<OLD>` and `<NEW>`
are statuses. A `doubt:` is a case where the agent cannot tell, and it never changes a grade. An
`unsupported:` line names a finding or a note that the evidence in the report does not support.
`checked` equals the `targeted` number of the rows. The agent returns `stopped: <reason>` when it
cannot read the plan or the report, or when its context is compacted. After a `stopped`, the main
chat reads the listed rows itself.

A `PASS` that should be a `FAIL`, with no change since the previous report, is not on the list, so
this check does not find it.

## When segments are used

Segments are used when the Part A slice of the run holds **more than 6 tool-section cases**: the
cases of Part A tool sections that the run will actually send, the cases the slice pulls in
included. `pre-` cases are never counted. With 6 or fewer, the main chat runs Part A and §Grey
itself.

Examples:
- a full run of a plan with 7 tool-section cases uses segments;
- a Part B only run that pulls in two Part A cases starts no segment agent;
- a report written from a transcript sends no case, so it starts no agent;
- a resumed run counts only the cases it still has to send.

When segments are used:
- every segment of the plan's §1.4, or of the derived cut, runs in its own agent;
- §Grey runs in one more agent, after the last segment;
- the section 9 agent re-resolves the created ids at the finish;
- the check agent re-reads the risky grades after it ([the check agent](#the-check-agent)).

The preflight, §Hand-off, Part B and the rest of the finish stay in the main chat in every run.

## Dispatch

**One at a time.** The main chat starts one agent, waits for its return, and checks the file before
it starts the next. While an agent runs, the main chat edits no file. Two agents never run at once.

The main chat starts each agent with the harness's sub-agent tool, on the model of
`mcp.segment_model` in `<plugin>/config.json` (default `sonnet`), unless the operator named another
model in the one message of questions before case 1 (`mcp-run/SKILL.md`, §1, step 6). The main
chat stays on its own model. The one known example: in Claude Code the main chat uses the `Agent`
tool, of type `general-purpose`, with that value as its `model`.
