# KING-24108 — cut the token cost of `mcp-run` and `mcp-plan` without lowering quality

**Ticket:** https://kinoadev.atlassian.net/browse/KING-24108 (two change requests in its description:
Part 1 = `mcp-plan`, Part 2 = `mcp-run`). **Date:** 2026-11-09. **Plugin today:** 0.7.3.

This document is the design a builder plans from. It records what the operator decided, what the
designer decided (marked *designer's call*), and what is left to the builder. The ticket text is
the requirement; where this document narrows or corrects it, it says so and why.

## 1. Intent and why

Two measured runs on 2026-11-06 and 2026-11-09 showed where the money goes:

| Run | Cost | Driver |
|---|---|---|
| `/kinoa-qa:mcp-plan`, 731-case regression plan, Fable 5.1 main chat | $56.11 | $21 of output writing case rows the main chat had already designed; 150k tokens of reader hand-backs carried through ~40 requests; the context grew to 955k |
| `/kinoa-qa:mcp-run`, the same plan, one chat, Sonnet 5.5 | $123.81 | 89 % cache reads: 1,076 requests at an average context of 512k; 65 idle ping requests; the report's own edits echoed back into the context |

The cost driver in both is **context size × number of requests**. The fix is the same in both: keep
the strong, interactive, judgment-heavy work in the main chat, and run the mechanical, long, bulk
work in **fresh sub-agent contexts** that write to files and return a short summary. Plans, reports,
case ids and the write discipline (one case at a time into the file, capture at the call) do not
change: they are what makes a run resumable and a report trustworthy.

## 2. Goals, non-goals, anti-goals

**Goals**

- `mcp-run`: a full run of the KING-23083 pre plan costs ≤ 50 % of the 20261109-0846 run, loses no
  case, and gives the same grades for cases whose behaviour on the stand did not change.
- `mcp-plan`: the main chat writes designs, not rows; reader extracts live on disk; a measured
  default for the writer model.
- Every rule keeps one home (`file-layout.md`, ownership table); `check-layout.sh` passes after
  every step; no existing eval assertion is weakened; the unit tests stay green.

**Non-goals**

- No change to the plan format beyond the new `§1.4 Segments` table and the id exception of 4.2,
  to the report format beyond a segment paragraph and a fixed shape for recorded values in
  section 3 (4.8), to the case id scheme, or to grading rules.
- No script that writes plan rows or report rows. Rows are written with the file edit tool.
- No change to the testplan, smoke-plan, smoke-run or token-report skills.

**Anti-goals** (a result that technically works but is a failure)

- A writer or segment agent that decides coverage or grading on its own.
- A segment agent that asks the operator, or a permission prompt that silently kills a run.
- A rule copied into a second file, a plan that restates a rule, a SKILL that defines one.
- A skill text that describes a harness behaviour nobody has seen work (CLAUDE.md: a skill
  describes what runs today).

## 3. Constraints the builder must keep

- The closed command list in `rules.md` (target and method) is the single statement of what the
  shell may run. Anything new the agents run is added there, in both skills' fenced blocks, with
  its condition.
- `check-layout.sh` check 4 keeps every owned phrase in its home; the self-test fails otherwise.
  The phrase `designed when it is written` is owned by `mcp-plan/SKILL.md` and must stay there in
  its new meaning (the design of a section is made when that section is written, by the main chat).
- Row checks gated by plan date keep their gates; a new check gets its own `FROM` date (the day
  the release is cut), so no old plan fails.
- Every test file ends with the `unittest.main()` block and defines nothing after it.
- A delimited value may contain the delimiter: every new parser is tested on one that does.
- User data lives under `~/.kinoa-qa/`; evals point `HOME` at a scratch home.
- Prose in the references follows `language.md` (B1–B2 English, one idea per sentence).
- Red-flag cells stay short (about 25 words) and point at a home, never define a rule.

## 4. Decisions

### 4.1 Order and packaging (operator: sequential; designer: the order)

Two PRs on one branch `chore/KING-24108-cost-pass`, merged in this order, each with its own
version, CHANGELOG entry and measurement. Sequential costs no more tokens than one PR; it costs less
risk: the second measurement cannot invalidate the first release, and each review reads one skill.

| PR | Version | Skill | Measurement in the PR |
|---|---|---|---|
| 1 | 0.8.0 | `mcp-run` (plus the §1.4 table in `plan-template.md` and the step of `mcp-plan/SKILL.md` that writes it) | one real re-run of the KING-23083 pre plan (operator: yes) |
| 2 | 0.9.0 | `mcp-plan` writers and reader extracts | the three-section writer test on `sonnet` and `opus` |

### 4.2 Segments (`mcp-run`, ticket Part 2, Part 1)

- **One domain = one segment, no cut by case count** (operator's decision). A domain is one or
  more whole tool families that one story delivers. A family is the first word after `kinoa_` in
  the tool name (`tag`, `template`, `abtest`, …). The plan's `§1.4 Segments` table names the
  domains. The planner may cut a family into its sub-families when each has its own story or plan
  (`feature_schema`, `feature_setting`, `feature_config` are three), and may join whole families
  into one domain when one story delivers them (`language` and `localization` are one, KING-23336;
  `projects` with 4 cases joins `tag`, *designer's call*). A family is never split across segments
  except into sub-families. The planner states the choice in the row; check 27 does not judge it
  (4.9).
  Consequence the operator accepted: in the KING-23083 pre plan the largest segments are
  `feature` (146 cases if not cut into its three sub-families; the planner should cut it) and
  `abtest` (91 cases).
- **A segment is a consecutive run of Part A tool sections.** The preflight (§A0), §Grey, §Hand-off
  and Part B are not segments. §Grey runs in its own segment agent (ticket); §Hand-off runs in the
  main chat (*designer's call*: 3 read-only cases that gate Part B, which the main chat runs).
- **§1.4 table columns:** segment id (`S1`…), sections (`A5`–`A10`), handles read from earlier
  segments, handles recorded, executing writes planned, and the planner's note on the cut.
- **Safe-point rules the planner checks:** no confirm token minted in one segment is confirmed in a
  later one, except the token-expiry pair below; no wait spans the boundary; every `Record:` value
  a later segment needs is recorded inside its own segment.
- **The token-expiry pair:** the case that mints the token for the expiry probe (today `grey-06`)
  is placed in the **first segment that holds its subject**, never in the preflight (its subject
  does not exist yet), and the case that confirms it stays in §Grey. The plan names both cases in
  §Grey's paragraph. The mint is a preview only, so it does not break the "grey probes last" rule
  of `rules.md` (Part A / Part B, last bullet) — that bullet gets the one-clause exception.
  **The mint row keeps its `grey-NN` id** wherever it sits (*designer's call*): `grey-06` was
  graded in 20261109-0846, so check 22 makes the next version keep the id, and check 17 already
  reads `grey-NN` ids anywhere in Part A. `plan-template.md`, stable case ids, gets the one-line
  exception: the mint row of the token-expiry pair keeps its `grey-NN` id inside a tool section.
- **Old plans (no §1.4):** the run derives the segments mechanically — a new segment starts at every
  Part A tool section whose first word after `kinoa_` differs from the previous section's — writes
  the derived table into section 3 of the report before the first segment, and adds a
  `Plan defect for the next version` row in section 8. Interleaved families (A73 language, A74–75
  localization, A76 language …) give several small segments; that is accepted, the defect row fixes
  it in the next version.

### 4.3 The orchestrator (`mcp-run`, ticket Part 2, Part 2)

- **The main chat runs itself:** §1, the `Run reason` question (with the segment model, below), the
  `curl` shapes, the report file, the preflight (all `pre-` cases, `ROLES_BEFORE`), §Hand-off,
  Part B with every checkpoint and the 20 s wait, and the finish.
- **A segment agent runs:** each segment of §1.4 (or of the derived table) and §Grey, one at a time,
  never two at once; the main chat waits for its return before anything else touches the report.
  While a segment agent runs, the main chat edits no file.
- **Small-run exception** (*designer's call*): segments are used only when the run's Part A slice
  holds **more than 6 cases outside the preflight** — the tool-section cases the run will actually
  send, pulled-in cases included; `pre-` cases never count. Below that, the main chat runs Part A
  as today. This keeps a tiny partial run, and the Part A cases a Part-B-only run pulls in, out of
  a sub-agent that would cost more to brief than to run; it is also what keeps eval 7
  (`part-b-only-run`, 2 pulled-in cases) and the transcript evals passing. The fixture plans have
  2–7 tool-section cases in Part A, so a full-run eval on `KING-99008-widgets-test-plan-v2.md`
  (7 outside its 5 `pre-` cases) segments and every other existing eval does not.
- **Section 9 re-resolve runs in its own agent** (operator: as recommended): after Part B, the
  main chat starts one agent that re-resolves every created id, writes the section 9 rows itself
  (the main chat is idle, so the one-writer rule holds) and returns the row count per label.
- **Segment model** (operator: as recommended): new key `mcp.segment_model` in `config.json`,
  default `sonnet`, next to `mcp.reader_model`. The `Run reason` question shows it as the proposed
  default; the operator may name another model in the one reply. README documents the key.
- **In Claude Code the sub-agent is the `Agent` tool, type `general-purpose`, with `model` set.**
  `segments.md` says so as the one known example, not as the rule. Sub-agents in Claude Code CLI see
  the connector's `kinoa_*` tools (the story readers already read Jira through one). Cowork is not
  verified: `segments.md` says nothing about it until a run shows it. A segment agent that finds no
  `kinoa_*` tool returns `stopped: connector not visible`, and the main chat tells the operator;
  the fallback to a single-chat run is **not** written as a rule in this release (anti-goal: an
  unverified behaviour).

### 4.4 `references/segments.md` (new; owned rows in `file-layout.md`)

One home for three things. The brief carries no rule text; it points at the references.

**The brief** (the main chat fills the values): the plan path, the segment id and its sections
and case range (first and last id); the report path and the run stamp; the references to read
first, in the order of the post-compaction checklist step 1 (`rules.md`, pauses); the handles the
segment reads, as names only — the agent rebuilds their values from section 3 of the report, never
from the brief; the time of the last executing write before the segment; the segment model is not
in the brief (it is the dispatch's `model`); the stop conditions, by pointer to `segments.md`.
Finding and note ids are **not** in the brief (ticket said the brief gives them; *designer's call*:
the agent reads the highest `F<n>` and `N<n>` in the file, like the handles, so there is one
source).

**The return shape**, short, no envelopes: the last case with a row; the status counts of its
range; the finding and note ids it added; the handles it recorded (names only); the time of its
last executing write; deviations from the rules, one line each; `done` or `stopped: <reason>`.

**Stop conditions.** The agent never asks the operator. It stops at a safe point (the last case has
its row, no executing leg in flight) and returns `stopped: <reason>` when: the `kinoa_*` tools are
missing or the connector lost its authorization or a listed project answers
`PROJECT_ACCESS_DENIED`; or a permission prompt is denied. A defect, a grading doubt or a missing
ruling is not a stop: finding or note, as today, and the segment goes on. **Deviation from the
ticket** (*designer's call, to confirm*): the ticket's third stop, "the same call fails with
`TOOL_EXECUTION_FAILED` after the one retry and the next cases depend on its subject", is not
adopted. `rules.md` (statuses, partial runs) already grades that case `FAIL` and marks each
dependent `BLOCKED — <handle> not recorded by <case id>`, Part A runs unattended by rule, and a
stop there gives the operator nothing to fix. The segment goes on as today.

**What the agent does inside its range** is exactly what an execution chat does today: one case at
a time into the file, capture at the call, the pace, the owner rulings, the section 3 paragraphs,
the finding and note blocks, the section 8 rows. It reads the plan and the report by search, never
whole (4.6).

### 4.5 The main chat's check after each segment

From the file, not from the summary: `bash <plugin>/skills/mcp-plan/scripts/check-layout.sh status
<report file>` prints the status counts of the case status table, the last case with a row, the
plan cases with no row in plan order, the highest finding and note ids, and every recorded handle
it finds in section 3 in the fixed shape of 4.8 (`Record: X` = …) with its line number. The main
chat compares that handle list with the segment's `§1.4` row; a handle missing from it, or printed
as `not recorded`, makes the main chat read that paragraph. A gap (a case of the range with no row)
is run again by a new segment agent from the first case with no row. Continuous ids: the agent's returned ids follow the highest id before the segment with no
gap, else the main chat reads section 4/5 headings with the status mode's output and names the gap
in section 3.

**Stops and resume** (ticket Part 3): on `stopped`, the main chat tells the operator the reason in
one short message (blocker first) and, when fixed, starts a new segment agent from the first case
with no row. A dead agent (no return) is treated as a compaction: the main chat reads the end of
the case status table and starts a new agent from the first case with no row; when that case is a
write, the agent reads its subject first (checklist step 4). Resume of the whole run in a new chat
(`continue <report file>`) is unchanged; the new chat finds the segment paragraphs in section 3.

### 4.6 Reading by search, and the closed command list

`rules.md`, target and method, gains for the **execution chat** what the planning chat already has:
`grep -nE '<pattern>' <file>` on the plan file and the report file only, where the harness has no
file-search tool. A segment agent reads the plan rows of its range and the report lines it needs
(section 1, the section 3 paragraphs that carry its handles, the end of the status table, section
10) by search plus the file read tool with offset and limit; a whole plan or report is never read
inside a segment. The finish in the main chat is the only place that reads sections in full. The
`mcp-run/SKILL.md` fenced block prints the `grep -nE` line with the two patterns the run needs
(a heading or row search in the plan; a section heading, `Record:` or case row search in the
report). **Permission shapes:** the `Run reason` message of §1 step 6 asks the operator to allow,
before case 1, the three `curl` shapes as today plus the `sleep <n>` and `grep -nE` shapes, since a
denied prompt inside a segment agent is a stop (*designer's call*; the 20261109-0846 run had a
`sleep 60` refused by the harness). `test_mcp_skills.py` checks that step 6 names all five.

### 4.7 Pace without idle pings (ticket Part 4)

`stand-facts.md`, budgets, states: **a pause is due when the budget needs it**: before an executing
write, if 8 executing writes went out in the last 60 s, wait until the oldest of them is 60 s old.
The plan's pause lines are budget points the run may skip when the count is lower; "the plan's
pauses are kept, not shortened" is replaced by this. **A pause is filled first** with work that
spends no write budget (reads, refused previews, schema cases, report work). **When a wait cannot
be filled**, the run waits with the harness's background wait and then sends one
`kinoa_system_ping` to read the server clock; the ping loop stays only as the fallback where no
background wait exists.

In Claude Code the background wait is `Bash` with `run_in_background: true` and the command
`sleep <n>`, where `<n>` is the seconds still missing; the harness re-invokes the chat once when it
ends, and the chat does nothing toward the stand until then. The closed list's `sleep 60` entry
becomes `sleep <n>` in that form, and `background.md` records why the old "foreground only" rule
existed (a 2026-10-15 run slept in the background and went on without waiting). **Spike first:**
before this rule is written, a throwaway `Agent` sub-agent runs a background `sleep 20` and reports
whether the completion notice reached it; if it does not, the segment agent uses the ping loop and
`stand-facts.md` says so. The segment agent returns the times of its executing writes of the last
60 s before its return (up to eight), and the main chat passes them to the next agent, so the
budget rule holds across the boundary with the same arithmetic (*designer's call*; the ticket said
one time). `plan-template.md`
says a wait step inside a case is written as a budget point, counted toward the five steps as
today.

### 4.8 Report section 3 (ticket Part 5, widened)

`report-spec.md`, section 3, gains: one paragraph per segment — the segment id and sections, the
model, start and end time, the times of the executing writes of its last 60 s, the return status
(`done`, or `stopped` with the reason and the case it stopped at), and `re-dispatched from <case>`
when a gap was run again. **A recorded value has one shape** (*designer's call*, so the status
mode and a resuming chat can find it): `Record: <HANDLE>` = `<value>` on its own line or inside the
paragraph, and `Record: <HANDLE>` not recorded (<case id>) when the case that should record it
failed or was blocked; `capture at the call` in `rules.md` points at it. The 20261109-0846 report
writes handles three ways, which is why the shape is fixed now. Records for passing cases stay
short: the ids, the status and the values a later case or the finish needs; verbatim envelopes stay
mandatory for what a finding, a note, a hypothesis verdict or a `Record:` value rests on. The
post-compaction checklist (`rules.md`, pauses) names the segment paragraphs among what a resuming
chat reads.

### 4.9 `check-layout.sh` changes (PR 1)

- **`status <report>` sub-command.** Usage becomes `check-layout.sh [<data folder>]` or
  `check-layout.sh status <report file>`. The status mode reads the report alone and the plan its
  section 1 `**Plan file:**` line names (resolved against the report's folder, `../plans/…`);
  prints `PASS n · FAIL n · OBSERVED n · BLOCKED n · rows n of N` where N is the plan's case count,
  `last row: <id>`, `no row: <ids in plan order>` (or `none`), `highest finding: F<n>` and
  `highest note: N<n>` (or `none`), then one line per `Record:` of section 3 in the shape of 4.8
  (`<line>: Record: X = …` or `<line>: Record: X not recorded`). The `**Plan file:**` line is read
  in the three shapes already on disk (a bullet with `../plans/…`, with a `, plan version` tail,
  a bare name plus link). Exit 0 (it reports, it does not judge), 2 on usage. It must finish in
  well under a second on the 343 KB regression report; it runs after every segment.
- **Check 27, `§1.4 Segments`**, for stable-id plans whose `**Plan version:**` date is on or after
  the release date: the `### 1.4` heading and table exist; every `## A<n>.` tool section (n ≥ 1)
  is in exactly one segment row; segments are consecutive and in order; every handle a segment's
  `Call` cells use that some case records (`Record: X` in an `Expected` cell) is recorded in the
  same or an earlier segment (handles of §0 excluded; uses in §Grey, §Hand-off and Part B are
  always fine); a `grey-NN` row inside a tool section is named in §Grey's paragraph. PROBLEM per
  rule. The domain grouping itself is the planner's judgment and is not checked. An older plan
  prints nothing (the run derives).
- Tests: `test_check_layout.py` for the status mode (a status cell with an escaped pipe in the
  third column; a report whose plan is missing; an in-progress report with no section 10) and for
  check 27 (a section in no segment, a handle recorded in a later segment, the gate by date);
  `test_mcp_skills.py` for the fenced command and the usage change.

### 4.10 Evals (`mcp-run/evals/evals.json`, PR 1)

No existing assertion is weakened. Every existing prompt is re-read against the small-run
exception; a prompt that says "do not call any connector tool" keeps passing because its Part A
slice is ≤ 10 cases or already finished. New:

- Eval 9, `segment-agent-stops-without-asking`: a full first run of `KING-99008-widgets-test-plan-v2.md`
  (7 tool-section cases in Part A, over the threshold of 6); the prompt simulates the preflight
  answers for the main chat. Assertions: the
  main chat runs the preflight itself; it starts exactly one segment agent, on `mcp.segment_model`,
  whose brief names only Part A sections and no Part B case or `curl` line; the agent finds no
  `kinoa_*` tool, asks nothing and returns `stopped`; the main chat reports the blocker in one
  short message, grades no case of the segment, and section 3 holds the segment paragraph with
  `stopped`; the scratch-home and real folders rules as in every eval.
- The other Part 6 assertions of the ticket (one row per case after the run, a dead agent
  replaced, the pace across a boundary) cannot be checked without a stand. They go into the
  measured-run checklist of PR 1 (4.12), not into `evals.json`.
- **PR 1 also runs the three plan-generating `mcp-plan` evals** (0, 2, 4) once (*designer's
  call*): check 27 fires on plans dated the eval day, so a generated plan without `§1.4` would
  fail their "check-layout.sh passes" assertion. PR 1 changes what `mcp-plan` writes, so its bar
  includes them; their fixture plans are small (4–16 cases), so the cost is small next to the
  measured run.

### 4.11 SKILL and reference edits (PR 1), one home each

| Change | Home | Also touched (pointer only) |
|---|---|---|
| `§1.4 Segments`, safe points, the mint-first-segment rule and its `grey-NN` id exception, budget points | `plan-template.md` | `mcp-plan/SKILL.md` §4 (writes §1.4 after the tool sections), §5 checklist line |
| The shape of a recorded value in section 3 | `report-spec.md` section 3 | `rules.md` capture at the call (pointer) |
| The five permission shapes asked at step 6 | `mcp-run/SKILL.md` §1 | `test_mcp_skills.py` |
| Brief, return shape, stop conditions, the small-run exception, the Cowork silence | `segments.md` (new) | `mcp-run/SKILL.md` §2, red flags |
| Pauses rewritten: the segment boundary is the context hand-over; (1) and (2) stay for a new chat; checkpoint rule unchanged; checklist reads segment paragraphs | `rules.md` pauses | `mcp-run/SKILL.md` Context red flags |
| Closed list: `grep -nE` for the execution chat; `sleep <n>` background form | `rules.md` target and method | both SKILL fences |
| Grey-probes-last exception for the mint | `rules.md` Part A / Part B | — |
| Budget-driven pause, fill first, background wait, spike result | `stand-facts.md` budgets | — |
| Segment paragraph, short passing records | `report-spec.md` section 3 | — |
| Ownership rows: `segments.md`, status mode, `mcp.segment_model` | `file-layout.md` | README config section |
| Main chat as orchestrator, §3 finish with the section 9 agent, red flags ("the summary says done", "the agent can ask", "one segment is small, run it inline" when over 10) | `mcp-run/SKILL.md` | — |
| Why the foreground-only sleep rule existed; the 2026-11-09 cost evidence | `background.md` | — |

### 4.12 Measured run (PR 1, operator: yes)

Run the KING-23083 pre plan **as it is** (no `§1.4`, so the run derives the segments; writing a
v2 first would cost what PR 2 is meant to save) with the new skill, then `/kinoa-qa:token-report`.
**The operator runs it** in their own chat (it needs the connector login, the VPN to `ADMIN_API`
and the `P1` access that failed once on 2026-11-09), on a **Sonnet 5.5 main chat**, so the
comparison with the Sonnet 5.5 baseline is like for like (*designer's call, to confirm*). PR 1
is not merged before the run is recorded; on a miss the operator decides whether to merge with the
miss stated in the CHANGELOG or to iterate first. Record next to the 20261109-0846 figures: total
cost, requests, average context, cost per segment agent, main-chat cost. Checklist: every plan case has exactly one row;
segment paragraphs present; no 60 s window with more than 8 executing writes (read from the
section 3 times); the grades of cases whose stand behaviour did not change equal the previous
report's; the pace held across each boundary. The result goes into the CHANGELOG entry and into
`background.md`. Target: ≤ 50 % of $123.81. A miss is reported as a miss, with the segment sizes.

### 4.13 `mcp-plan` writers (ticket Part 1, change 1; PR 2)

- **The main chat writes a compact design per section**, in its own reasoning and in the brief, not
  in the plan: the subjects and handles it creates or reads, the case ids in order, one line per
  case saying what it proves and which §1.2/§1.3 rows and §1.1 hypotheses it covers, and where the
  budget points go. The §4 rule "designed when it is written" now means: the design of a section is
  made when that section is written, by the main chat, never for the whole plan at once.
- **Writers run one at a time** (*designer's call*: two Edit-tool writers on one file race and lose
  rows), one per section or per small group of sections of one domain. The brief gives: the design;
  the plan-template rules for rows by pointer (cases are data, the `Expected` cell shape, `len<N>-`
  probes, `Record:` handles, every `game_id` a §0 value); the §0 handles; the tool names of the
  section — with a connector the writer loads their schemas itself through the harness (in Claude
  Code: ToolSearch), so the main chat loads none; **without a connector** the brief names where
  the served surface is, as `plan-template.md` ("without a connector") defines it: the source
  files of `**Checked against:**` to read for the served text only, or the file
  `~/.kinoa-qa/mcp/work/<KEY>-<domain>/tools-list.md` into which the main chat saved the
  `tools/list` the operator pasted, once, with the file write tool (*designer's call*; eval 4 has
  no connector); the closed command list by pointer (`rules.md`, target and method:
  the writer runs no shell command at all); the instruction to append the rows under the section's
  heading with the file edit tool and return the id list it wrote and nothing else.
- **The main chat verifies**: `check-layout.sh` after each writer (17 s on the real folder today;
  acceptable per section), then reads that section's rows against its design and fixes or
  re-dispatches. Subject tracing across sections (the three soundness rules), §1.1, §1.2, §Grey,
  §0's artifacts table, the `**Name limit:**` line and `§1.4` stay with the main chat.
- **`mcp.writer_model`** in `config.json`, default set by the measurement (4.15), documented in
  README next to the other two keys.
- **Red flags** added to `mcp-plan/SKILL.md`: "the writer can design the edge cases itself"; "skip
  reading the rows, the script passed"; "two writers in parallel are faster".

### 4.14 Reader extracts on disk (ticket Part 1, change 2; PR 2)

- Each reader writes its extract to `~/.kinoa-qa/mcp/work/<KEY>-<domain>/readers/<batch>.md`
  and returns: one status line per key (`read` / `empty` / `unreadable: <error>`), the counts of
  bug, rules and facts rows, and the file path. The brief's "write no file" becomes "write only
  your extract file, nothing else".
- **The merge** (`story-readers.md`): the main chat reads, from the extract files, the bug rows and
  the facts rows whole, and for the rules one line per row (key, place, field and clause in about
  ten words — the reader writes this line as the first line of every rules row, so the merge needs
  no reading of the quotes). The interview message shows: the status list; the bug list and the
  facts list inline; the rules as that one-line list with the path of the merged file. The operator
  can still move an item between kinds or overrule a newer-wins row in the one reply, because every
  item has a line in the message (operator: as recommended).
- **When the main chat designs a tool section**, it reads the full rules rows of that domain from
  the extract file (it cannot design the covering cases otherwise; the ticket's "that text never
  enters the main context" holds for the facts and for the rules of the other domains). The writer
  reads the same rows to quote them verbatim into §1.3 (`language.md`: quote as written).
- **The work folder is kept** (*designer's call*: deleting needs `rm`, which the closed list does
  not have and should not get). `file-layout.md` gets the folder in its table: written by the
  readers, read by the main chat and the writers, kept after the plan is finished, named in the
  hand-over. The `mkdir` of §1 gains `~/.kinoa-qa/mcp/work`. The lines of §3 and §5 "adds only its
  own new plan" become "adds only its own new plan to `plans/` and its own work folder under
  `work/`"; the eval assertion "the real `~/.kinoa-qa/mcp/plans/` and `reports/` are unchanged"
  is unchanged and still true.
- **Eval 4** (`new-plan-with-research-subtask`): its assertion "the orchestrator reads no
  sub-entity text" is reworded without weakening: the orchestrator reads only the merged lists and,
  per section, the rules rows of that section's domain from the extract file; it never reads a
  sub-entity through the Jira connector itself. A new assertion: the extract file exists under
  `<scratch home>/.kinoa-qa/mcp/work/`.
- In an eval the pasted sub-entity text still goes to the readers in the brief; they write the file
  the same way.

### 4.15 Writer measurement (PR 2, before `mcp.writer_model` is set)

Done once, by the builder, exactly as the ticket says: three sections of existing plans in
`~/.kinoa-qa/mcp/plans/` (one CRUD-heavy, one lifecycle with `sem` cases, one with grey or schema
probes; 10–20 cases each), a compact design derived from the existing rows, one writer on `sonnet`
and one on `opus` per section with the new brief, output to scratch files, the row checks of
`check-layout.sh` on a scratch copy of the plan with the section swapped in, a side-by-side read
for missing assertions, wrong handles, a refusal decided on the wrong leg, an `Expected` cell
without its deciding clause. Record per section and model: cost from `/kinoa-qa:token-report`,
check result, differences marked harmless or defect. Set `mcp.writer_model` to the cheapest model
with no defect; when both show the same defect, fix the brief and repeat that section. Known bias,
stated in the hand-over: a design derived from finished rows is more complete than a real one, so
the measurement answers the model question, not the brief's robustness.

### 4.16 Versions, docs, tests (both PRs)

- `.claude-plugin/plugin.json` version and a CHANGELOG entry per PR (the CI requires the bump).
- README: the config keys, the mcp-run usage section (segments, the status mode line), the
  mcp-plan usage section (writers, the work folder).
- `test_mcp_skills.py`: the fenced commands of both SKILL files still name real files; the new
  fenced lines (`status`, `grep -nE`, `sleep <n>`) are covered by `fenced_plugin_commands`; the
  connector check of §1 step 1 is unchanged.
- `python3 -m unittest discover -p "test_*.py" -v` in `skills/testplan/scripts` green;
  `bash skills/mcp-plan/scripts/check-layout.sh skills/mcp-run/evals` prints no PROBLEM;
  `check-distribution.sh` on both skill folders clean.
- The real data folder prints one pre-existing PROBLEM today
  (`KING-22308-feature-settings-test-report-20261014-1507.md`, no counts table); it is not fixed
  by this work and is named in the hand-over.

## 5. Left to the builder

- The exact wording of every reference change, in `language.md` English, with the owned phrases
  kept.
- The §1.4 table's exact column names and the check 27 parser (awk or perl, as the other checks).
- The status mode's output format beyond the fields named in 4.9.
- The brief's exact text in `segments.md`, and the writer brief's exact text in
  `mcp-plan/SKILL.md` §4 (or a short `references/writers.md` if §4 grows past a screen — then an
  ownership row for it).
- Which three sections the writer measurement uses.
- The spike's outcome and its wording in `stand-facts.md`.
- How the segment paragraph names the model (the dispatch value, e.g. `sonnet`).

## 6. Open for the operator

- 4.12: the measured run is the operator's own chat, on Sonnet 5.5, before PR 1 merges, and a
  miss is the operator's call (designer's proposal).
- 4.4: the ticket's `TOOL_EXECUTION_FAILED` stop is not adopted (designer's call, stated with
  its reason; the operator may put it back, and then `rules.md` statuses and partial runs change
  too).
- 4.2: the measured run derives one 146-case `feature` segment from the pre plan, because the
  plan has no §1.4; the next plan version should cut it into its three sub-families.

## 7. Builder-check round (2026-11-09)

A reviewer read this document cold and asked nine questions. They are settled above: the
threshold is 6 tool-section cases and never counts the preflight (4.3); the third stop condition
is dropped (4.4); recorded values get one shape and the status mode prints them (4.5, 4.8, 4.9);
the measured run's executor, model and gate are stated (4.12); PR 1's bar includes `mcp-plan`
evals 0, 2 and 4 (4.10); the mint row keeps its `grey-NN` id (4.2); step 6 asks for five
permission shapes (4.6); a writer without a connector reads the served surface from the source or
the saved `tools-list.md` (4.13); a domain may hold several whole families (4.2); the pace
hand-over passes up to eight write times (4.7).
