# KING-24108 PR 1 iteration — context management in the run (0.8.1)

Addendum to [the cost-pass design](2026-11-09-KING-24108-cost-pass-design.md). Same branch,
`chore/KING-24108-cost-pass`. The parent spec still holds wherever this one is silent.

## 1. Intent

The measured run of 0.8.0 (report 20261109-1725, CHANGELOG 0.8.0) cost $112.56: 91 % of the
one-chat baseline. Segments halved the average context (512k → 266k), but requests rose 53 %
(1,076 → 1,641). The transcript shows three causes:

- **One request per case.** "One case at a time into the file" makes every case one stand call and
  one report edit. In every large agent, the edits roughly equal the stand calls (S5: 136 calls,
  177 edits; S8c: 143 and 139; S3: 135 and 121).
- **A heavy opening.** Every agent reads seven reference files whole, and the plan's §0 whole,
  before its first case. That is 120–165k of context, re-read on every request after it. It is
  91M of the agents' 355M context tokens. The harness's own 68k at the open is not in our hands.
- **A heavy main chat**, at $20.64 and an average context of 411k. It loads all the tool schemas,
  reads three full project lists, and keeps several 3–4k-character download links in its
  context.

The operator's framing (2026-11-09): **this is an iteration to improve context management in the
run phase, not a chase after a figure.** There is no cost target. The token report of the next real
run shows the effect.

## 2. Goals, non-goals, anti-goals

**Goals**

1. A segment agent writes its report rows **once per plan section**, not once per case (operator
   decision, 2026-11-09).
2. A segment agent reads **only the reference sections it needs**, not whole files.
3. The main chat keeps less in its context: schemas, project lists and long links.
4. A **targeted grade check** at the finish (operator decision, 2026-11-09).

The earlier draft had a fifth goal: a misgrade fix for `grey-10` / `grey-11`. It was dropped after
the builder check. `stand-facts.md` (budgets) grades a rate-limit probe `OBSERVED` unless the stand
is known to run a single replica, so the Grey agent's `OBSERVED` was right. The `PASS` of run
20261109-0846 was the slip.

**Non-goals**

- Splitting a large domain across agents. The operator parked it on 2026-11-09: a split by case
  count alone is a weak measure, because response size varies (about 2.8k to 4k of context per
  case across the large segments).
- The harness's 68k opening context. A custom agent type would need a spike first.
- `mcp-plan` (PR 2).
- A dedicated measured re-run (designer's call, §6).

**Anti-goals.** These make it a failure even if it is cheaper:

- the regression grades get worse;
- an envelope a finding needs is lost;
- a section's rows are lost without the main chat noticing and re-running them.

## 3. Decided by the operator

- **Per-section writes** in segment agents. Losing a section's rows when an agent dies is accepted:
  each agent already covers whole sections, and the saving is worth more than per-case safety.
- **A targeted grade check after the report is fully written.** It checks only the rows where a
  misgrade is likely and costly, not the whole report. A full-report reviewer was rejected: it
  would have to re-read most of the run to judge 698 `PASS` rows.
- **No split of domains** in this iteration.
- **No bar.** This is an iteration, not a target.

## 4. The design

### 4.1 Per-section writes (segment agents only)

- `rules.md`, capture at the call: "one case at a time into the file" stays the rule for the main
  chat. A segment agent instead writes **per plan section**. When the last case of a `## A<n>.`
  section has run, and before the first call of the next section, the agent writes into the report
  file, in as few edits as the file tool allows:
  - the rows of every case of that section;
  - the `Record:` values in its section 3 paragraph;
  - every finding or note block the section produced, envelopes included.
- **What does not move.** These stay at the moment they happen:
  - Envelopes are still captured verbatim from the tool result: per-section writing changes *when*
    they reach the file, not *what* is written.
  - Isolation evidence is still taken while the state is live.
  - A `Record:` value that a later case of the same section uses is used from the agent's own
    context. It reaches the file with the section.
- **A section with a finding** writes its block at section end like any other. The finding id is
  taken from the file at that moment. One agent at a time makes that safe.
- **Compaction or a stop inside a section.**
  - A segment agent that finds its context summarized stops at once, with
    `stopped: context compacted`. It writes nothing it no longer holds verbatim.
  - The safe point of `segments.md` stop conditions becomes "the last *section* it ran has its
    rows".
  - A stop condition that fires mid-section writes the rows of the cases already run in that
    section, if their envelopes are still in its context, and then returns.
  - The main chat's existing gap check (`segments.md`, the return is a summary) finds the cases of
    the range with no row. A **recovery agent** takes them, under this rule (operator decision,
    2026-11-09, which replaces the earlier "block the lost writes" call):
    - **Sections already written are untouched.** Only the lost section is redone.
    - **Find the lost attempt's subjects.** The agent first reads the subjects the lost attempt
      created, by their stamp names (listing or `_get`). Their ids go into section 9 as artifacts
      of this run, so cleanup still finds them. No case is graded from them.
    - **Re-run the whole section with fresh subjects.** It starts from the section's first case.
      Every name it creates carries a re-run suffix after the stamp (for example
      `Q23083-<stamp>-r1-cat-a`), so nothing collides with the lost attempt. Its `Record:` values
      replace the lost ones. The grades come from the fresh calls, so they are real evidence.
    - **Block only where the starting state is gone.**
      - Before a case that needs a subject the section did not create (an earlier section's
        handle, or a §0 fixture) to be in a given state, the agent reads that subject's current
        state.
      - If the precondition still holds, the case runs.
      - If the lost writes already changed it beyond repair (for example an update that went out,
        or an irreversible activation), the case is `BLOCKED`. Its section 8 row names the lost
        section.
    - **Section 3** gets one line: which section was lost, that it was re-run with the suffix, and
      which cases were blocked.
    - The rule lives in `segments.md` (stop conditions and the main chat's check), with a pointer
      from `mcp-run/SKILL.md` §2. The re-run suffix belongs with the naming rule in `fixed-data.md`.
      The measured run had no agent die, so this path is rare.
- **Section 3 records** the change once, in the segment paragraph shape (`report-spec.md`): no new
  field is needed. The paragraph already gives the range and the last row.

### 4.2 Read only the needed sections (segment agents)

- The brief's **What to read first** stops pointing at step 1 of the post-compaction checklist
  (seven files whole). `segments.md` gets one table, **What a segment agent reads**, with one row
  per reference section: file and heading.
  - The agent finds each heading with the harness's **file-search tool**, never a shell `grep` on
    the references, and reads that range only, with an offset and a limit.
  - In a harness with no file-search tool, it reads the named files whole, as today.
  - So the closed command list and the five permission shapes stay as they are (*designer's call*,
    builder-check question 6).
- **One home holds**: the rules stay where they are, and the table names headings, not rule text.
  No digest file is copied from the references (*designer's call*: a copied digest would be a
  second home that drifts).
- **A test** (`test_mcp_skills.py`) checks that every heading the table names exists in its file,
  so a renamed heading fails the suite instead of silently dropping a rule.
- **Which headings go in the table** is the builder's work, from what a Part A case actually needs:
  - statuses, writes, partial runs, delete semantics, capture at the call;
  - budgets and the connector in `stand-facts.md`;
  - the case status table, recorded values and the segment paragraph in `report-spec.md`;
  - cases are data, in `plan-template.md`;
  - the finding and note blocks in `report-blocks.md`, read only when the section produces one;
  - games and players, and naming, in `fixed-data.md`;
  - `language.md`, whole if it is short.
  - Headings a segment agent never needs stay out: Part B, checkpoints, pauses for a new chat, the
    finish, the overall status, the comparison table.
- **§0 of the plan is read by search too.** The agent greps the §0 constants and the handle names
  its brief lists, then reads the hits. It never reads §0 whole.
- **The post-compaction checklist** is unchanged for the main chat. A segment agent never resumes
  after compaction (§4.1), so it does not use the checklist.

### 4.3 A leaner main chat

- **Tool schemas.** The main chat loads only the schemas of the tools its own cases call: the
  preflight, §Hand-off and Part B. It loads them by exact name, in one load, at step 6. It never
  loads them by keyword or all at once. Segment agents load their own.
- **Long values are recorded short** in the main chat's working text: a project list is read once,
  and only the rows the run uses are noted; a download link is recorded by its length and
  host. This only fixes what the run keeps after the call. Whether these rules belong in
  `rules.md`, capture at the call, as a shortening of what is not evidence, or in `mcp-run/SKILL.md`
  is the builder's call. Envelopes that are evidence are still verbatim.
- **Not in our hands.** The harness appends the tool's schema to a refused call, about 3k tokens
  for each of roughly 20 Part B refusals. Background notes it as a known cost and does not work
  around it.

### 4.4 The targeted grade check (finish)

- In a run with segments, the finish gets one more agent, **the check agent**, on
  `mcp.segment_model`. It runs after the section 9 agent, before the main chat's `check-layout.sh`
  of finish step 1.
  - It reads only the targeted rows. Finish step 4, the language read-back, stays as it is
    (*designer's call*, builder-check question 4).
  - In a run without segments, the main chat does the same check itself.
  - The measured run's extra finish agents (the "cleanup" agent and the "sections 6 and 7" agent)
    are not in the skill: the main chat improvised them. This design does not add them.
- **What it checks.** These rows only:
  - every row whose status is `FAIL`, `OBSERVED` or `BLOCKED`;
  - every case whose status differs from the previous report's, when section 1 names one.
  - For each, it reads the plan's `Expected` cell and the section 3 evidence of that case, and
    answers: does the grade follow the deciding clause?
- **How it gets the list.** A new `check-layout.sh` mode, `grades <report> [<previous report>]`.
  - It matches the two reports' case status tables by case id, not by row order.
  - It prints each targeted row's id with its status, and the previous status where it differs, so
    the agent reads only those rows. A case with no row in the previous report prints `new`.
  - It **skips** `BLOCKED` rows with a fixed label that needs no judgement: excluded by the
    operator, and the dry-run block. It also skips the grade-change check for them (*designer's
    call*, builder-check question 5). The builder takes the exact labels from `rules.md`, partial
    runs.
  - The mode follows the same conventions as `status`: no `-` arguments, exit 2 on an unreadable
    file, and tests in `test_check_layout.py`, including a case id or cell that contains the
    delimiter.
- **What it may change: nothing** (*designer's call*, builder-check question 3).
  - It never runs a stand call, and it never edits the report.
  - It returns, for each row it would correct: the case id, the old and new grade, and the clause
    and evidence that decide it. It also returns the rows it doubts, and any finding it finds
    unsupported.
  - **The main chat applies each correction with everything that follows from it:**
    - the case status table;
    - a finding block for a new `FAIL`, written from the section 3 envelopes. If those envelopes
      are not there, the case is `BLOCKED — response not captured`, not `FAIL`;
    - a withdrawn finding for a `FAIL` that becomes `PASS`;
    - a section 8 row for a new `BLOCKED`;
    - one section 3 line naming each change.
  - The section 2 counts and the section 6 and 7 verdicts are written after this, as today.
    `check-layout.sh` of finish step 1 then runs on the corrected report. That way one writer edits
    the report at the finish, and the check runs once.
- **Return**: the rows checked, the corrections proposed, and the rows doubted, in the
  `segments.md` return style. Finish step 5 reads the section 3 line with the `deviations` lines.
- **What it does not cover**: a `PASS` that should have been a `FAIL` and whose grade did not change
  since the previous run. That would need a re-grade, and the operator accepted the gap.

## 5. Constraints (from the parent spec and CLAUDE.md)

- One home per rule.
- The closed command list in `rules.md` is the only shell authority. `check-layout.sh grades` is
  added to it and to the `mcp-run` fence.
- No skill text describes harness behaviour that has not been seen.
- Every new test file section ends with the `unittest.main` block.
- Delimiter-in-value tests are required for the `grades` mode.
- Nothing under the real `~/.kinoa-qa/mcp/` is edited. Evals use a scratch HOME.
- Plugin version **0.8.1** (*designer's call*): the 0.8.0 entry keeps its measured run attached
  to the shape it measured. CHANGELOG and README follow.

## 6. Left to the builder, and the designer's calls

- **Measurement** (*designer's call*): no dedicated re-run of the KING-23083 pre plan.
  - Run the `mcp-run` evals 0–9 against the 0.8.0 results (75/84) for regressions.
  - Add or extend an eval that shows a segment agent writing per section; eval 9's fixture is the
    natural place.
  - Add an eval in which the check agent proposes correcting a planted wrong grade, and the main
    chat applies it with its finding block. The planted grade is a `PASS` on a case whose section
    3 envelope contradicts the deciding clause. It is not a flood probe, because a flood probe's
    `OBSERVED` is correct (`stand-facts.md`).
  - The first real run after merge records its token report in the CHANGELOG.
- The exact reading table of §4.2.
- The home of the main-chat shortening rule (§4.3).
- Whether the `grades` mode reads the case status table of both reports by case id. It should,
  because rows may be in a different order.
- Whether the section 9 agent's paragraph line (parked in the 0.8.0 ledger) is folded into §4.4's
  finish wording now. It touches the same step.
