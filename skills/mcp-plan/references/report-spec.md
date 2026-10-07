# The report contract

A report is written **as execution proceeds**, so a pause never loses work. Its file name, its
folder and the one-file-per-run rule are in [`file-layout.md`](file-layout.md#file-names).

A report names a reference as plain text, `mcp-plan references/<file>.md` (for example
`mcp-plan references/report-spec.md`), never as a link into the plugin. It links only to its plan
and to earlier reports ([`file-layout.md`](file-layout.md#links-inside-the-files)).

The report **is** these ten sections, in this order, each headed `## <n>. <Section>`. Nothing else
is a section.

| # | Section | What it contains |
|---|---|---|
| 1 | Header | Date (UTC), stand, MCP connector, the caller's `user_id` as `kinoa_system_ping` returned it (never a login or an e-mail), the fixed data actually used, plan file + plan version, and the four run lines from [`file-layout.md`](file-layout.md#many-reports-for-one-plan): `Run`, `Plan file`, `Run reason`, `Previous report` |
| 2 | Overall status | `GREEN` if the run has zero `FAIL`s **and** zero finding blocks, else `RED`; `BLOCKED — <reason>` when no case ran (see [the overall status](#the-overall-status)); then the counts, as the one-row table `\| PASS \| FAIL \| OBSERVED \| BLOCKED \| Total \|` counted from [the case status table](#the-case-status-table), which must sum to the plan's case count — exactly one status per plan case, so a case deferred from Part A and re-run in Part B is counted once, under the status it ended with, and the cases outside a partial run's slice are counted under their `BLOCKED` label ([`rules.md`](rules.md#partial-runs)). A partial run adds one sentence: the status covers only the cases that ran. The finding count and the note count follow as two separate numbers; neither is a status. When a previous report exists, the comparison table below closes the section |
| 3 | What was done, per part | In a partial run, a first paragraph that names the slice as the operator gave it, the cases the slice pulled in and the checkpoints applied. Then one prose paragraph per plan section and per Part B checkpoint: the preflight paragraph names the role Part A ran under, read from `ROLES_BEFORE` ([`rules.md`](rules.md#part-a--part-b)); a checkpoint paragraph gives the rows the `GET` showed after the block and when, how many attempts the block took, and, when the checkpoint fell back to the operator, why and the rows the operator pasted. Includes the delete-semantics verdict, one sentence per destructive tool. Ends with [the case status table](#the-case-status-table) |
| 4 | Findings | The body of the report: one block per defect, in the finding block contract of [`report-blocks.md`](report-blocks.md#the-finding-block-contract) |
| 5 | Notes | Every non-blocking inconsistency or flaw the run saw: one block per note, in the note block contract of [`report-blocks.md`](report-blocks.md#the-note-block-contract). Empty only if the run really saw none — then write "No notes." |
| 6 | AC traceability | One row per acceptance-criterion bullet: case ids, verdict, and the finding id where it failed |
| 7 | Hypothesis verdicts | One row per pre-execution hypothesis: `CONFIRMED` (+ finding id), `REFUTED` or `UNPROVEN`, with the case evidence |
| 8 | Not covered / blocked | One row each, with the reason. One row per "not under test" line of the plan's §1 too, with the plan's reason, so the reader sees what no case could check ([`plan-template.md`](plan-template.md#the-three-rules-that-decide-whether-a-plan-is-sound)). The cases of one operator exclusion (a partial run's slice included) share one row instead, which names every case it covers: by plan section where a whole section is excluded, by id otherwise. Then one row per plan defect the run found, labelled `Plan defect for the next version`: a §0 value or name that differs from the stand, a name prefix, a fixture, a case a rule overrules. A plan defect is not a finding and not a note |
| 9 | Artifacts left behind | One row per id the run created, labelled per the artifact contract of [`report-blocks.md`](report-blocks.md#the-artifact-contract) |
| 10 | Role rows at the end of the run | `ROLES_BEFORE` (the body of the snapshot `GET`, [`rules.md`](rules.md#part-a--part-b)), the rows the last `GET` of the run showed, and whether they are the same — `restored`, or `not restored` with the rows the operator has to put back. When no checkpoint ran, one sentence saying that the run changed no role row |

Section 3 is the run's story in prose; its case status table is the ledger. The evidence lives
in the finding blocks of section 4, which carry every request and response the reader needs. Every
`FAIL` case is accounted for in section 4, by the finding block of the defect it shows; one block
may account for several `FAIL` cases of one defect, and it names them. Every `BLOCKED` case is
accounted for in section 8, as a blocked row. A case is never in both 4 and 8. Section 6 is not an
alternative to them: it lists, per acceptance-criterion bullet, every case behind that bullet
whatever its status, so a `FAIL` case also appears there with its finding id, and a `BLOCKED` one
with its reason. An `OBSERVED` case is accounted for in section 3 only, unless it also feeds an AC
row in section 6.

Section 5 works the other way round. It is not tied to case statuses at all: a case that is a plain
`PASS` can still produce two notes, and a note never removes a case from section 4, 8 or 6.

## The case status table

Section 3 ends with a `### Case status` heading and one table: one row per plan case, in the
plan's order. Each row is added at the call ([`rules.md`](rules.md#capture-at-the-call)); the
rows of the cases outside a partial run's slice are added at the finish, each in its place and
pointing at the one section 8 exclusion row, so until then the last row is the last case run.

| Case | Status | Finding / note / blocked row |
|---|---|---|
| `create-ok-02` | `FAIL` | F3 |
| `list-ok-01` | `PASS` | N2 |
| `role-create-02` | `BLOCKED` | section 8: the fallback to the operator at B2 |

The third cell holds the finding and note ids of the case, or for a `BLOCKED` case the section 8
row that names it, or `—`. A case deferred from Part A keeps its one row, whose status changes
when Part B grades it. The section 2 counts are counted from this table, so its row count equals
their `Total`.

## The overall status

`RED` means "this run saw at least one defect". So the run is `RED` when it has a `FAIL` **or** a
finding block, and `GREEN` only when it has neither **and** at least one case ran (`PASS`, `FAIL`
or `OBSERVED`). A run in which no case ran — every case `BLOCKED`, for example
`BLOCKED — fixed data wrong in §0` raised by a `pre-` case whose fixture id is not on the stand
(`fixed-data.md`, games and players) — is `BLOCKED — <reason>`, never `GREEN`: nothing was tested.
A run blocked before case 1, by the connector or by a placeholder in §0, writes no report at all
(`file-layout.md`, finding the files). A partial run follows the same rule on the cases that ran:
the cases outside its slice are `BLOCKED` in the counts and decide nothing.
Most findings come from a `FAIL` case, but not all:

- **A finding outside a plan case is allowed.** A defect seen in the preflight, in `tools/list`, or
  while re-checking an id of the previous report whose case no longer exists is still a defect. It
  gets a full finding block. Its `Case:` line names where it was seen (`Case: preflight`,
  `Case: tools/list`, or the old id and plan version), and it takes the next free `F<n>`.
- **It changes no count.** The status counts cover the plan's cases only, so such a finding adds
  nothing to `FAIL`. It is counted in the finding count, and it makes the run `RED`.
- **The next plan version gives it a case** of its own, like every finding of an earlier run
  ([`file-layout.md`](file-layout.md#comparing-runs)).

A finding in a case that passed its `Expected` cell — the plan asserted too little, the tool
description is broken — follows the same rule: the case keeps `PASS`, the block exists, the run is
`RED`.

## Comparing with the previous run

The same plan is run more than once — after a bug fix, or to check that a change broke nothing.
[`file-layout.md`](file-layout.md) says how the files are named and how to find the previous report.
This is what the new report has to say about it.

When section 1 names a previous report, section 2 ends with this table. When `Previous report` is
`none`, the table is left out and section 2 says "First run of this plan."

```markdown
### Compared with the previous run — `KING-99002-widgets-test-report-20260915-0900.md`

| Id | What it was | Now | Evidence |
|---|---|---|---|
| F1 | widget export drops the field order | **fixed** | export-ok-01 `PASS`, the order is kept |
| F2 | `kinoa_widget_get` returns 500 for a hidden widget | **still present** | F2 in this report, same repro |
| F4 | delete leaves the preview image | **not re-tested** | needs a role change that was not applied |
| N2 | `total` comes back as text | **still present** | N1 in this report |
| — | new since the last run | F5, F6, N3 | — |

Overall: 1 of 4 findings fixed, 2 still present, 1 not re-tested, 2 new.
```

Five rules keep the table honest:

- **Every finding and every note of the previous report gets a row.** A missing row reads as
  "fixed", and the reader cannot tell the difference.
- **Only four values in the `Now` column**: `fixed`, `still present`, `not re-tested`,
  `ruled expected (owner, <date>)`. `fixed` means the repro steps of the old finding block — for a
  note, the call of its `What was seen` — were run again and the behaviour is now correct. Anything
  weaker is `not re-tested`, with the reason in the `Evidence` cell. `ruled expected` is for an old
  finding or note whose behaviour an owner ruling later called correct (`rules.md`, statuses): its
  `Evidence` cell names the ruling and the case of this run that showed the behaviour, and it has
  no block in this report.
- **Ids do not move.** A defect that is still present keeps the id it had in the first report, so
  `F2` in the table and `F2` in section 4 are the same defect. A `still present` row therefore
  always has its block in section 4 or 5 of this report, with this run's envelopes. A new defect takes the next free id
  after the highest id of the previous report.
- **The comparison table carries no bug keys.** The `TRACKED in <KEY>` marker lives on the finding
  block, which the row's id points at.- **The comparison never changes the overall status.** `GREEN` / `RED` is decided by this run's
  own `FAIL`s and findings alone ([the overall status](#the-overall-status)). A run that fixed nine
  of ten defects is still `RED`.

## Language

The whole report, every section and every table cell, follows the language rule in
[`language.md`](language.md). That file is the only home of the rule, including the list of text
that must stay exact.

## Naming things — the whole report, not just the findings

The report is read by someone who did not watch the run and cannot search its history. Every subject
it mentions must be resolvable from the file alone. Three rules, everywhere in the report — prose,
tables, findings, notes, artifacts:

- **A game is never just `P1` / `P2`.** Write the name and the uuid the first time it appears in a
  section, and the uuid every time it appears inside a tool call. The uuid is the fixture and comes
  from the plan's §0; the name is the one the stand shows. When it differs from §0, the report
  uses the stand's name, says so once in section 1, and writes the difference as a plan defect in
  section 8, never as a finding. Example:
  *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) in the fictional examples of `report-blocks.md`. A
  later reader has no copy of the plan's constants table,
  and `P1` in one story's report is not guaranteed to be `P1` in another's.
- **A player is never just `PLAYER1` / `PLAYER2`.** Write the `player_id` exactly as the plan's §0
  gives it (`rules.md`, owner rulings; for example `p_8f2a1c77`). The label may follow it in
  parentheses; it may not replace it.
- **An entity the run created is named by what it is actually called on the stand** — its real
  `name` / `key` and its id, exactly as the service stores them (`KING21979-QA-20260903-1130-clone-src`,
  id `…`). Never "the subject of case create-ok-02", never a plan handle like `SUBJ_3`, never "the twin
  from the delete determination", so a reader can look the entity up in the product.

Case ids still belong in the report — on the finding block's and the note block's `Case:` line, in
the AC traceability table, in the blocked rows. They identify *where in the plan* something happened. They never stand
in for *what* the thing was.
