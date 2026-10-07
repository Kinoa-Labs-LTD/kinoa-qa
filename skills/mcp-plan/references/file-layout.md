# Where plans and reports live

Both skills keep their output in one data folder, `~/.kinoa-qa/mcp/`, outside the plugin, so a
plugin update keeps it. Nothing is written to the plugin folder or to the repo root.

| What | Folder |
|---|---|
| Test plans | `~/.kinoa-qa/mcp/plans/` |
| Test reports | `~/.kinoa-qa/mcp/reports/` |

Both SKILL files create the two folders first, with
`mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports`, and stop, naming the path, when one
cannot be created or written. Each skill writes into its own folder and reads the other one:

- `/kinoa-qa:mcp-plan` writes a plan into `~/.kinoa-qa/mcp/plans/`, and reads earlier reports
  from `~/.kinoa-qa/mcp/reports/` to see what the last run found.
- `/kinoa-qa:mcp-run` reads a plan from `~/.kinoa-qa/mcp/plans/`, and writes its report into
  `~/.kinoa-qa/mcp/reports/`, never into the working directory.

## File names

**Plan:** `<KEY>-<domain>-test-plan.md`, or `<KEY>-<domain>-test-plan-v<N>.md` for revision `N`.

- A file with no `-v<N>` suffix is version 1.
- A revision is a **new file**, not an edit of the old one. Version 3 of the resources plan is
  `KING-21979-resources-test-plan-v3.md`, and `-v2` stays on disk next to it.
- The version in the file name and the `**Plan version:**` line in the header must be the same
  number.
- Every version stays on disk.
- A plan carries no version note: two versions are compared by their stable case ids
  ([`plan-template.md`](plan-template.md#stable-case-ids)).

**Report:** `<KEY>-<domain>-test-report-<STAMP>.md`.

- `STAMP` is the run stamp from [`fixed-data.md`](fixed-data.md#naming-every-artifact): UTC
  `yyyyMMdd-HHmm`, captured once at the start of execution. The same stamp names every artifact the
  run creates on the stand, so the file name and the leftovers on the stand match.
- **One file per run. Never overwrite an earlier report.** A re-run after a bug fix is a new file
  with a new stamp.
- Sorting the folder by name puts the runs of one story in time order.

## Many reports for one plan

The same plan is run more than once. Common reasons:

- the first run found defects, they were fixed, and the plan is run again to check the fixes;
- the tools were changed for another reason, and the plan is run again to check that nothing broke;
- the plan itself was revised, and the new version is run.

Every report must say which run it is, so the files can be compared later. Report section 1 carries
these lines, in addition to what [`report-spec.md`](report-spec.md) already asks for:

| Line | Value |
|---|---|
| `Run` | `<STAMP>` — the same stamp as in the file name |
| `Plan file` | the plan file name **and** its version number |
| `Run reason` | `first run` · `re-run after fixes` · `regression check` · `new plan version` |
| `Previous report` | the file name of the previous report for the same `<KEY>-<domain>`, or `none` |

A partial run takes one of these values too; report section 3 names its slice
([`rules.md`](rules.md#partial-runs)).

## Finding the files

Search by the story key, never by guessing a name:

```bash
ls ~/.kinoa-qa/mcp/plans/ | grep -- 'KING-22279-'   # plans for one story
ls ~/.kinoa-qa/mcp/reports/ | grep -- 'KING-22279-' # every run of that story, oldest first
```

- **The newest plan wins.** With several versions, take the highest `-v<N>`, unless the user names
  a file. Say which file you picked before you start.
- **The newest report in which a case ran is the baseline.** Take the last name in the sorted
  report list for the same `<KEY>-<domain>`, skipping a report whose overall status is
  `BLOCKED — <reason>`. A run blocked before case 1 writes no report file at all
  (`mcp-run/SKILL.md`, §1).
- If the folder holds nothing for that story key, it is a first run. Say so; do not go looking in
  the repo root or anywhere else.
- **Worked examples.** A plan with a `**Fixed data:** redacted` header line, a plan that
  `check-layout.sh` prints as `LEGACY` or `REDACTED`, and a report with `<…>` placeholders in
  place of its ids show how a file is built and serve as a baseline for comparison; they cannot
  be run as they are. A plan with literal §0 values is this installation's own.
- **A resumed run reuses its report file.** When the operator names an existing report file, or
  says "continue", the run is the one that file records: same `Run` stamp, same file, next case
  after the last row of its case status table (`report-spec.md`, the case status table); a
  resume inside Part B reads `ROLES_BEFORE` from section 10 and never takes the snapshot again
  (`rules.md`, pauses).

## Comparing runs

A re-run is only useful if it answers "what changed since last time". So:

- **Before the run**, the execution chat reads the previous report's section 4 (findings) and
  section 5 (notes), and lists the finding and note ids it has to re-check. Reports written before
  2026-09-09 have nine sections and no Notes section: their findings are section 4,
  `Not covered / blocked` is section 7, and there are no notes to re-check. When the previous
  report's comparison table has `not re-tested` rows (a partial run always does), those ids are
  on the list too, each taken from the report that last had its block, because a run that skipped
  an id does not close it.
- **During the run**, each of those ids is re-checked through the case the plan's §1.2 names for
  it. An id with no §1.2 row is re-run from the old block's steps, at the end of its part, as
  `Case: <old id> (plan v<N>)` ([`report-spec.md`](report-spec.md#the-overall-status)). Never a
  shortcut. A partial run re-checks only the ids whose case is in its run
  ([`rules.md`](rules.md#partial-runs)).
- **After the run**, section 2 of the new report carries the comparison table described in
  [`report-spec.md`](report-spec.md#comparing-with-the-previous-run).

**A finding from an earlier run keeps a full case in every later plan version.** This holds when the
bug is marked fixed, when its fix is merged, and when a sub-bug was filed and closed. A fix is a
claim until the protocol shows it. So:

- the case keeps the original repro steps and its own id; a merged fix changes only the `Expected`
  cell, never removes or shortens the case;
- a finding is never covered by a hypothesis note, a commentary sentence or a single shared
  assertion in place of its case — one finding, at least one case of its own;
- every earlier finding and note, and every sub-bug filed from a run, has its §1.2 row and case by
  the row rule of [`plan-template.md`](plan-template.md#the-skeleton); the report's comparison
  table takes its `fixed` / `still present` verdicts from those cases;
- a finding the owner later ruled expected keeps its case too. Only its `Expected` cell changes,
  to the ruling, as for a merged fix; the comparison row is `ruled expected`.

Findings keep their ids across runs of the same plan. `F3` in run 2 is the same defect as `F3` in
run 1. A defect found for the first time in run 2 gets the next free id, counting from the highest
id used in run 1. Never renumber a finding: the id is how two reports are read side by side.

## Where each rule lives

Every rule has exactly one home. The other files, the two SKILL files and every plan link to that
home and do not restate it. When a rule changes, one file changes.

| Rule | Home |
|---|---|
| Folders, file names, plan versions, one report per run, finding the files (worked examples included), comparing runs | `file-layout.md` (this file) |
| History behind the rules | `background.md` — maintainer only: the pruning pass |
| Simple English (B1–B2), and the text that must stay exact | `language.md` — read at the first write of prose |
| The execution rules, one `##` section each: target and method, Part A / Part B, statuses (owner rulings and scope exclusions included), partial runs, writes, subjects and artifacts, delete semantics, capture at the call, pauses (the hand-over to a new chat included) | `rules.md` |
| Games and players (the constants, empty means ask, the run reads §0); naming every artifact (stamps, the name limit, short prefixes); the fictional values of the examples and fixtures | `fixed-data.md` |
| The admin role API, server budgets and timings, the dry-run kill-switch, the connector | `stand-facts.md` |
| The plan's shape, one section each as its contents line lists them | `plan-template.md` |
| The report sections, the overall status, comparing with the previous run, naming things | `report-spec.md` |
| The finding block (and the tracked marker), the note block, the artifact contract, the model | `report-blocks.md` — execution chat only, at its first finding or note |
| How a planning chat proceeds: its numbered steps, checklist and red flags | `mcp-plan/SKILL.md` |
| How an execution chat proceeds: its numbered steps and red flags | `mcp-run/SKILL.md` |

A SKILL file holds procedure, checklists and red flags. A checklist line or a red-flag row may name
a rule in a few words and point at its home; it never defines the rule. A plan holds cases,
hypotheses and domain facts, and no rule text at all.

## Maintaining the rules — one pruning pass per run

The rules grow from what the runs find. The way they grow decides whether they stay readable.
This is the maintainer's work, done outside the planning and the execution chats: neither chat
changes a reference, and each hands its lessons over instead (`mcp-plan/SKILL.md`, §3;
`mcp-run/SKILL.md`, §3).

- **A lesson from a run goes into exactly one file**, chosen from the table above. If the lesson is a
  rationalization a chat used, it also gets **one row** in the red-flags table of the SKILL file
  whose chat used it, and nothing else.
- **After each run, the maintainer does one pruning pass** over the references and the two SKILL
  files. Its input is the `Rule change proposals` of the planning and execution chats'
  hand-overs and the `Plan defect for the next version` rows of the latest reports; a proposal
  is checked against
  its report before it becomes a rule. For every rule ask: is this its home, and does every other
  mention link here instead of restating? Merge the copies into the home. Delete a rule that no
  run has needed.
- **Do not add a rule between runs** because it sounds sensible. A rule earns its place by a run that
  went wrong without it. The red-flags table is the record of those runs.
- **Run the check script** after the pass. Both chats run it too, before finishing a plan or a
  report, as their SKILL files print it: `bash <plugin>/skills/mcp-plan/scripts/check-layout.sh`. What
  each numbered check looks for is in the comment above it in the script, which is the one home of
  that list. A phrase check is paraphrase-blind: it catches a copied sentence, not a reworded one,
  so the pruning pass above is still the real check.
- **During the pruning pass, read [`background.md`](background.md)**: it keeps the run behind
  each rule, which is how you tell a rule no run has needed. A reason stays in the rule's home
  only when the rule makes no sense without it, as one short clause. A fact that holds only
  at one commit of kinoa-mcp keeps a one-line `verified at commit <sha>, <date>` stamp in its
  home; the story of how it was found goes into `background.md`.

## Links inside the files

A plan links to nothing in the plugin, and neither does a report: plans and reports live in
`~/.kinoa-qa/mcp/`, away from the plugin folder, so they name a reference as plain text. Between
plans and reports the links are relative, so a link works when the file is opened from its own
folder:

| From | To | Written as |
|---|---|---|
| a plan | a reference | `mcp-plan references/rules.md`, plain text |
| a report | its plan | `../plans/<plan file>` |
| a report | a reference | `mcp-plan references/report-spec.md`, plain text |
| a report | an earlier report | `<report file name>` (same folder) |
