# Changelog

What changed in each released version of the `kinoa-qa` plugin, newest first.

Check the version you have with `claude plugin list`; if it is older than the top entry here,
update with the two commands in the README's **Versions and updating** section.

The version lives in `.claude-plugin/plugin.json` and nowhere else. Claude Code updates an
installed plugin **only when that string changes**, so a merge that does not bump it never
reaches anyone who already installed the plugin.

## 0.7.2 — 2026-10-26

**`mcp-plan` and `mcp-run`: validation lives in the backend** (KING-23809). A preview that
mints a confirm token for input the backend then refuses on the confirm leg is no longer a
finding: validation in the backend only is a requirement (owner ruling of 2026-10-26, which
replaces the ruling of 2026-10-12). Update the plugin before the next plan or run.

- **`rules.md`.** Statuses: a new owner ruling. Writes: a row that expects a backend refusal (a
  taken name, an unknown or non-uuid id, a wrong state, a backend role rule) is graded on the
  executing leg and its read; a refusal already on the preview passes too; the token and the
  leg that refused are recorded after `Also record:`. Only the MCP server's own checks — the input
  schema and the role mapping — are still graded on the preview leg. A plan row written before
  the ruling is graded the same way and named in section 8 as a plan defect. When the run cannot
  tell whether such a behaviour is a defect, it writes a note, never a finding on doubt alone,
  and never leaves it out. Pauses (b): the preview-leg row of a dropped connector is now only a
  row that expects an MCP-server refusal.
- **`report-blocks.md`.** Note or finding: the one exception to "when the run cannot decide, it
  writes a finding".
- **`plan-template.md`.** Cases are data: a backend-refusal row sends both legs and a read; a new
  `create-rule-01` example row; the `rule` kind says so.
- **`mcp-plan/SKILL.md`, `mcp-run/SKILL.md`.** §5 checklist lines and red-flag rows for the new
  grading. `background.md` records why. `check-layout.sh` check 4 owns the new rule's phrase.
- **Evals.** `mcp-run` eval 8 (`backend-only-validation-preview-token`) with the fixture plan
  `KING-99009-widgets-test-plan.md`.

## 0.7.1 — 2026-10-16

**`mcp-plan` and `mcp-run`: the gaps the 0.7.0 eval run found** (KING-23440, the eval run of
2026-10-16: 31 of 42 `mcp-plan` assertions passed, 42 of 42 `mcp-run`; two `mcp-run` evals
were refused by the API). The references and both SKILL files changed; update the plugin before
the next plan or run. The plan and report shapes do not change; the new checks are date-gated.

- **`mcp-plan/SKILL.md`.** §0: the branch-state line also prints `git rev-parse --short HEAD`,
  the sha of `**Checked against:**` (no allowed command printed it before). §1: the planner
  reads the `### Case status` table of each report too (which rows were sent and graded; a
  report without it: all of section 8), and finds the parts with the printed `grep -nE` line
  where the harness has no file-search tool. §2: a question the request answered is listed once under **From
  your request** and not asked; the checkpoint number counts role states only, the restore
  comes on top; a key that only a sub-entity's links or text name is never cited. §3: the
  hand-over says which check numbers ran, and a property checked only by reading is
  `checked by reading, not verified`. Three red-flag rows here and one in `mcp-run/SKILL.md`
  (a quick `ls -la` or `echo` is a script too); §3 step 5 of `mcp-run` is checked from the
  chat's own record, with no command.
- **`rules.md`.** Target and method: `git rev-parse` joins the planning chat's list; where the
  harness has no file-search tool, `grep -nE '<pattern>' <file>` and
  `grep -rlE '<pattern>' <folder>` are the one allowed search (extended patterns, so `|`
  separates alternatives) (no `wc`, `cat`, `sed`, `head`,
  `find`, `ls -la`, `echo`). Statuses: a report written from a transcript writes the write
  list's source, `USER_ID` and `ROLES_BEFORE` as `not captured` and infers nothing. Pauses (b):
  a row graded on the preview leg gets its row when that envelope is captured; Part A / Part B:
  the 20 s role-cache wait is measured like the pause between write blocks and recorded, and
  after a failed or timed-out `PUT`/`DELETE` the rows in effect are unknown until a `GET`
  answers; "the case in
  flight gets no row" applies when the deciding envelope was not. A hand-over opens report
  section 2 with the `paused` line, which `report-spec.md` (the overall status) defines.
- **`plan-template.md`.** §1.3 has one row per clause a case can check on its own (with an
  example; a qualifier in brackets, the schema's type and a UI default stay in their clause's
  row); a rule about trimming or whitespace gets two cases, one of them whitespace-only;
  Part B opens with `<N> role checkpoints, then the restore`; every `game_id` and
  `target_game_id` is a §0 value or a probe its `Expected` cell names (check 24).
- **`file-layout.md`.** A finding the owner ruled expected keeps its §1.2 row, which says so.
- **`story-readers.md`.** A linked issue about another surface is `nothing`, not a fact; a key
  that only a sub-entity's links or text name stays inside the quoted row.
- **`report-blocks.md`, `language.md`.** Fourth artifact label
  `not re-checked (last seen: status <x> in <case>)`, only when no call is allowed.
- **`mcp-run/SKILL.md`.** §1: a report from a transcript takes the operator's stamp and runs no
  `date`; a report file the operator names but that is missing is created under the given
  stamp and section 3 says so; a plan with no Part B gets no `curl` lines and no snapshot
  `GET`; a plan with Part B but no `ADMIN_API` gets a plan-defect row and the operator applies
  the rows. The commands of the §1 block run at the step that names them, none before step 1.
- **`check-layout.sh`.** Check 18 reads `NAME_S-` and `KEY_…` literals too, in Part A and
  Part B; a literal that only starts an artifact's name (a search scoped to the stamp) passes.
  New checks, for plans dated 2026-10-16 or later: 22 (a plan of version 2 or later keeps every
  row the newest report's case status table graded), 23 (every `{…}` argument object is JSON
  once the handles are strings), 24 (every `game_id` / `target_game_id` is a §0 value or named
  in its `Expected` cell as the probe), 25 (no `and so on` or `up to the last page` in a `Call`
  cell, and no `...` or `…` inside an argument object outside its strings). A report whose
  section 2 opens with `paused` is PAUSED for check 15 and gives no WARN for check 20. New
  check 26: a plan of version 2 or later numbers each new id from the next free number of its
  group, with no gap. Check 24 matches a value as a whole token and prints a `<…>` placeholder
  whole; check 23 accepts a placeholder that holds `->`.
- **Evals.** `mcp-plan`: eval 3 uses KING-99104 with the story text pasted; eval 0's row
  assertion is split into five; eval 1's id assertion into four, plus one for the graded rows; new assertions for the
  graded rows, the cited keys, the `grep -n` read, the `game_id` values, the honest hand-over
  and the §1.3 row count (11). `mcp-run`: eval 3 gets its seeded report
  `KING-99003-user-lists-test-report-20260923-1400.md` and the hand-over observables; the "no
  script" clause reads "writes no script and runs only the commands SKILL.md prints"; new
  assertions for the order of step 1, the early stop, `tools/list` fidelity, the plan-defect
  rows, the fourth artifact label, the 16-row table and the unread role. Eval 7's oracle answers
  the listing differently before and after the `-r` create; eval 5's unrun B2/B3 cases must be
  `BLOCKED` rows; eval 2 grades every finding block, not one.

## 0.7.0 — 2026-10-16

**`mcp-plan` and `mcp-run`: no tool-call limit, a pruning pass of the rules, and every sub-entity
of a story is a plan input** (KING-23440). The references in
`<plugin>/skills/mcp-plan/references/` changed; both skills read them, so update the plugin
before the next plan or run.

- **No limit on tool calls** (`rules.md`, pauses). An `mcp-run` chat no longer hands over because
  of a call count, a large context or a compaction; the "about 120 tool calls" line is gone. The
  report file is always current, and a compaction starts the **post-compaction checklist**
  (re-read the rules and the plan, reconcile the case status table, rebuild the handles from the
  file, reuse a confirm token while it is valid). A connector that drops and comes back in the
  same chat gets the lost call again in place; a hand-over happens only for a connector that
  does not come back or when the operator asks. `mcp-run` §1 step 7 (resume) points at the
  checklist; its command block gains `sleep 60`, allowed only where the harness runs it in the
  foreground (`stand-facts.md`, budgets), and the pause between write blocks is measured with
  `kinoa_system_ping`.
- **Rules from the runs of 2026-10-12 … 2026-10-15.** A row that expects a refusal with no token
  is graded on the preview leg, and "the preview approves what the confirm refuses" is one
  finding per tool; after a refused executing leg the subject is read back (`rules.md`, writes).
  Finding ids stay in discovery order and section 4 opens with the ids by severity
  (`report-blocks.md`, `report-spec.md`). Partial runs: a handle anywhere in the row pulls in
  its recording case, a read with a missing handle is still sent and `BLOCKED`, a precondition
  wired to no handle is a plan defect (`rules.md`, partial runs). A checkpoint block whose rows
  are already in place is not sent (`rules.md`, Part A / Part B); a case after the restore
  expects the answer the same call got in Part A. An empty string for a string-or-null argument
  is converted by the connector (`stand-facts.md`). Plan shape (`plan-template.md`): the §0
  artifacts table has an `Expected` column, a `BASE_<X> + n` count names its handles, a wait is
  its own numbered step, a length probe is `len<N>-…` of exactly `N` characters, and a violation
  `path` has no leading slash (verified at kinoa-mcp commit `e375f2d`). A report name may carry
  `-<letters>` after the stamp for a side-by-side run (`file-layout.md`). `mcp-run` §1 step 6
  prints the three `curl` shapes to allow before case 1.
- **Every sub-entity of the story is a plan input** (`mcp-plan`). The planning chat reads the
  story itself and dispatches **readers** — sub-agents on the model in `config.json`
  (`mcp.reader_model`, default `sonnet`) — one per batch of at most ten keys, to read every
  sub-task, sub-bug and linked issue whole (new reference `story-readers.md`). The first message
  lists each one as `read`, `empty` or `unreadable` with the bugs, rules and facts taken from it.
  The plan header gets `**Research inputs:**` and the plan a **§1.3 Research results** table:
  one row per rule, its `Served contract`, and the cases that cover it; a rule the served schema
  contradicts is a §1.1 hypothesis whose deciding case reads the entity back, and every
  happy-path case sends every field the research marks required. Question 10's no-search rule is
  unchanged.
- **`check-layout.sh`**: four new checks — `NAME-` literals of `Call` cells must be in the §0
  artifacts table (18), `len<N>-` probes are counted (19), a runnable plan that says
  `**Earlier runs:** none` while a report exists gets a WARN (20; a redacted plan is skipped), and `**Research inputs:**` / §1.3 are checked
  against each other (21). Checks 3 and 13 accept the side-by-side suffix. Checks 18 and 19 apply
  to plans dated 2026-10-16 or later.
- **Eval**: `mcp-plan` gains `new-plan-with-research-subtask` (a fictional story with a research
  sub-task, a work item that carries a rule, an empty sub-task and a linked issue).

## 0.6.1 — 2026-10-12

**`smoke-plan`, `smoke-run` and the README point to the kinoa-aqa plugin for automation and page
objects** (KING-23157).

- **Promoting a smoke check** to a regression test → `/kinoa-aqa:testops-to-playwright` (kinoa-aqa
  plugin, inside kinoa-test-automation).
- **Page object rules** → `/kinoa-aqa:page-object-author`, the same way.
- The smoke-testing guide's flow diagram names `/kinoa-aqa:testops-to-playwright`.

## 0.6.0 — 2026-10-07

**Two new skills, `/kinoa-qa:mcp-plan` and `/kinoa-qa:mcp-run`, moved in from the shared
`qa-mcp-skill` copy, where they were `mcp-qa-plan` and `mcp-qa-execute`** (KING-23152). They keep
their plan rules, case format and report format; what changed is below.

- **New skill `/kinoa-qa:mcp-plan`.** Writes or revises the test plan of a Kinoa MCP story: new
  `kinoa_*` tools, tested black-box through the deployed stand's `kinoa` connector. Its rules live
  in `<plugin>/skills/mcp-plan/references/`.
- **New skill `/kinoa-qa:mcp-run`.** Runs such a plan through the connector and writes the test
  report. It has no references of its own: it reads `mcp-plan`'s, through relative links inside
  the plugin.
- **Plans and reports live in `~/.kinoa-qa/mcp/`.** Plans in `~/.kinoa-qa/mcp/plans/`, reports in
  `~/.kinoa-qa/mcp/reports/`, outside the plugin folder, so a plugin update keeps them. Both skills
  create the two folders first and stop, naming the path, when they cannot.
- **Plans and reports name the references as plain text**, e.g. `mcp-plan references/rules.md`,
  never as a link into the plugin. A report still links to its plan, `../plans/<plan file>`.
- **Connector check.** `mcp-run` looks for the connector's `kinoa_*` tools (e.g.
  `kinoa_system_ping`) before anything else, with no call. With none, it says the `kinoa`
  connector is missing or not logged in, and stops before it writes a report file.
- **No zip.** The skills ship with the plugin; no `.skill` file or zip is built or shipped.
- **`check-layout.sh [<data folder>]`.** `bash <plugin>/skills/mcp-plan/scripts/check-layout.sh`
  checks the two skill folders and the plans and reports of a data folder, by default
  `~/.kinoa-qa/mcp/`; it fails, naming the path, when that folder does not exist. It no longer
  checks links in the data folder or in `evals/`, and the `--dist` flag (check 8) is gone.
- **Eval fixtures.** The plans and reports the evals use sit in
  `<plugin>/skills/mcp-run/evals/plans/` and `…/evals/reports/`: the fictional widgets and
  user-lists examples and the redacted KING-22304 webhooks plan with its report. Every eval of
  both skills copies them into `<scratch home>/.kinoa-qa/mcp/` and runs the skill with
  `HOME=<scratch home>`, so the real `~/.kinoa-qa/mcp/` stays untouched; CI runs
  `check-layout.sh` on them.
- **`check-distribution.sh <folder>...` guards the skill folders.** CI runs it on
  `skills/mcp-plan` and `skills/mcp-run`, fixtures included: it fails on an e-mail outside
  `example.com/org/net` and on a non-fictional uuid used as a game, player or user id, also inside
  a confirm token. The fictional values are read from the "Fictional values" section of
  `mcp-plan references/fixed-data.md`. It no longer takes `.skill` or zip archives.

**Rollout:** **update the plugin first** (`/plugin marketplace update kinoa-qa`, then
`/plugin update kinoa-qa@kinoa-qa`). Then move your plans and reports into
`~/.kinoa-qa/mcp/plans/` and `~/.kinoa-qa/mcp/reports/`, and then delete only the `mcp-qa-plan`
and `mcp-qa-execute` folders from `~/.claude/skills` or `<kinoa-mcp checkout>/.claude/skills`,
wherever you installed them.
`mcp-qa-ready` is a separate skill and not part of this plugin: keep it where it is, but after the
move it no longer finds the plans, the reports or the `mcp-plan` references.

## 0.5.0 — 2026-09-28

**`/kinoa-qa:testplan --from-smoke <SUBTASK-KEY>` pushes a Story's smoke plan to Allure
TestOps** (KING-23102). Until now a smoke plan lived only as the "Smoke test" Jira sub-task
`smoke-plan` writes, and `testplan` stopped on any `scope: smoke` plan.

- **The push.** The agent saves the raw sub-task, parent Story and remote-link responses into
  one input file; `smoke_to_plan.py` converts them, with no LLM step, into a `scope: smoke`
  plan at `~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>-smoke.test-plan.md` (or
  `-no-target-smoke`). It then goes through the validator, the review gate and Step E as one
  `Draft` case under the `Feature` you pass. The Story key comes from the plan header, never
  the sub-task key. The plan is never hand-edited: fix the sub-task and re-push.
- **Refusals, with the reason:** a sub-task with no or an empty `## Preconditions`, a step
  without exactly one expected result, no `[GATE]` step, a Story with no acceptance-criteria
  list, an `[AC-n]` past the Story's count, or remote links naming two different cases.
  `[AC-n]` means the n-th criterion of the parent Story, counted from 1; `smoke-plan` now
  states that rule.
- **The case id lives on the sub-task.** On a separate yes at the gate, after Step E,
  `jira_remote_link.py` writes one remote link titled `Allure TestOps case <id>` — the one
  `smoke-run` reads — updating in place on a re-push the link it wrote, or any link whose
  title starts `Allure TestOps case <digits>` (`case_id_from_title`, the rule
  `smoke_to_plan.py` reads the id with). Not on `--dry-run`, never unattended.
  A re-push updates the case by that id only when it carries `qa-generated`, the same Story
  and `scope=smoke`.
- **Token scope.** The link needs `JIRA_EMAIL` + `JIRA_API_TOKEN` with the classic
  `write:jira-work` scope and the Jira "Link issues" permission. Without them (exit 3), or on
  an unreadable config or a refused write (exit 1), the case stays pushed and you get the
  title — and the URL, whenever the config names the TestOps host and project — to add by
  hand. Exit 2 is a usage error only. A `testplan` run
  without `--from-smoke` still needs only `read:jira-work` and never writes to Jira.
- **Config.** `config.json` gains `testops.base_url`, used for the link's case URL.
- `smoke-run`: with more than one `Allure TestOps case …` link on a sub-task, it asks you
  which id to use.

## 0.4.0 — 2026-09-25

**Two new skills, `/kinoa-qa:smoke-plan` and `/kinoa-qa:smoke-run`, moved in from
kinoa-test-automation** (KING-23103, per the KING-22942 taxonomy). They keep their workflow;
what changed is below.

- **New skill `/kinoa-qa:smoke-plan <STORY-KEY>`.** Turns a Story into a "Smoke test" Jira
  sub-task: numbered steps, one expected result each, every result tagged with its source.
  It now aims at **about 2–5 steps — a target, not a limit** (it was 5–12). It **creates no
  Allure TestOps case**; the push of a smoke plan to TestOps is planned (KING-23102), not
  built.
- **New skill `/kinoa-qa:smoke-run <SMOKE-SUBTASK-KEY>`.** Runs the sub-task in a browser via
  the Playwright MCP and reports two verdicts (feature, conformance) as a Jira comment plus a
  published artifact. Its two scripts ship with it and are run as
  `node <plugin>/skills/smoke-run/scripts/jiraReport.mjs` and `…/jiraAttach.mjs` (Node 18+,
  no npm dependencies).
- **Start checks.** `smoke-run` checks for the Playwright MCP and for `JIRA_EMAIL` +
  `JIRA_API_TOKEN` before anything else, names what is missing and stops. The plugin still
  ships no `mcpServers` config: add a Playwright server named `playwright` yourself — see the
  README's **Prerequisites**. A `jiraReport.mjs … --dry-run` rehearsal needs no credentials.
- **Removed: the file-path fallback.** With the Jira variables unset, `smoke-run` used to hand
  you the screenshot paths to attach yourself. It now stops at the start instead.
- **Inside kinoa-test-automation only:** API data setup, saving the run as a
  `tests/smoke/<feature>.smoke.ts` spec, and that spec's `@allure.id` (the case id from an
  `Allure TestOps case <id>` remote link on the sub-task, else an id you give). The spec's run
  writes `allure-results/`; publishing it as a TestOps launch is not automated, and `smoke-run`
  says no launch was published. "Inside" means the working directory's `origin` URL ends in
  `kinoa-test-automation` or `kinoa-test-automation.git`. Anywhere else `smoke-run` sets data up through the UI, refuses the
  spec save and skips the launch, and says why in each case; the Jira report is unaffected.
- **`testplan` is unchanged in behaviour.** Its docs now say smoke plans come from
  `/kinoa-qa:smoke-plan` as a Jira sub-task; a plan whose header says `scope: smoke` still
  stops at Step C.
- CI sets up Node 20 and runs the two scripts through `node` from the Python suite.

**Rollout:** kinoa-test-automation removes its own copies of the two skills and scripts after
0.4.0 is released. **Update the plugin before that** (`/plugin marketplace update kinoa-qa`,
then `/plugin update kinoa-qa@kinoa-qa`), or the smoke skills disappear for you.

## 0.3.0 — 2026-09-24

**Two plan formats, `smoke` and `e2e`, and `testplan` generates e2e only.** The header's
`scope:` is the plan's format (KING-22942 taxonomy, KING-23104).

- **Breaking: `scope: story` is removed.** `scope:` takes `smoke | e2e`, case-sensitive; any
  other value, `story` included, FAILs `scope-valid` naming the allowed set. An absent
  `scope:` now means **e2e** (it meant `story`), in the validator, the payload status and the
  target marker. Every generated plan writes `scope: e2e` in its header.
- **Breaking: the plan file is `…-e2e.test-plan.md`.** A `…-story.test-plan.md` left by 0.2.x
  is no longer read. **Action required to keep its ids:** rename it to `…-e2e.test-plan.md`
  and set `scope: e2e` in its header before the next run, so its `allure-id:` lines carry
  over and Step E updates those cases by id. Reconciliation does not find the old cases
  otherwise: a TestOps case whose `Target:` marker carries the old Story scope value is
  outside the e2e in-scope set, is neither matched nor reported, and is created again.
  Project KINOA has no such case (checked 2026-09-24).
- **E2E cases reach TestOps as `Review` with the caller's `Feature`.** The plugin no longer
  forces a `Feature` value for e2e, and `--feature` on an e2e plan is no longer an error. A
  smoke plan's cases are `Draft`. The `--scope` flag is gone; passing it stops the run with
  the reason.
- **Multi-AC sources.** `source: ac: AC-1, AC-2` cites several acceptance criteria;
  `source-valid`, `ac-coverage` and `conflict-resolution` check each id.
- **New check `type-valid`.** `type:` is one of `functional`, `negative`, `edge`,
  `regression`, `nonfunctional`; `type: e2e` FAILs, pointing at `scope: e2e`.
- **New check `smoke-shape`.** A smoke plan has exactly one case, `type: functional`; under
  smoke an uncovered AC is advisory, and a missing `## Acceptance Criteria` still FAILs. The
  smoke rules apply only to exactly `scope: smoke`.
- **New check `sections-present`.** A plan without a `## Cases` or a `## Gaps` header FAILs,
  naming each missing header; `## Gaps` may still be empty.
- **`testplan` validates and pushes e2e plans only.** A plan whose header says `scope: smoke`
  stops at Step C and is never pushed; no flow of this plugin produces a smoke plan yet.
- The scope carry-forward and the `SCOPE CHANGED` report of `plan_writer.py` are removed: a
  regenerated plan's header is taken as written.

## 0.2.1 — 2026-09-22

Documentation correctness only; no behaviour change.

- `sot-assembly.md` described a `--continue-on-missing` flag that the skill never accepted and
  that appears in no usage line. The sentence is gone, replaced by what actually happens when
  one OpenSpec target of several fails: the rest resolve and the failure is reported at the
  human gate.

## 0.2.0 — 2026-09-21

**Step A now reads image attachments on the Jira Story.** A requirement that lives in a
screenshot pasted into the Story becomes an acceptance criterion instead of a `⚠️ GAP`.

- Images join the **authoritative tier** of the SoT bundle, with the Story, the PRD and Figma
  frames: what an image shows may ground an `expected:`.
- New optional case field `image-ref: <attachment-id> — <filename>`, validated offline by the
  new `image-ref-valid` check (syntax and `ac:`-source pairing only, never a Jira call).
- `image` joins `story` / `prd` / `design` / `openspec` as a `## Conflicts` source.
- New `images:` header line: `<n> read`, `<n> read (<k> failed: <reason>)`, `none`, or
  `none (<reason>)`.
- Image provenance rides the `Provenance:` line on the TestOps `description`, exactly as
  `openspec-ref` and `design-ref` do.

**Action required to use it:** export `JIRA_EMAIL` and `JIRA_API_TOKEN` (a scoped token needs
`read:jira-work`). Without them the run continues and records
`images: none (jira credentials not set)` — it is never a hard stop, so an un-configured
install behaves exactly as 0.1.0 did.

The Jira cloud id is resolved automatically from `jira_base_url`; a scoped token cannot use the
site host, and nothing about that needs configuring.

## 0.1.0

First released version: the `/kinoa-qa:testplan` orchestrator — Jira Story (+ optional
Confluence PRD, linked Figma mockups and service-repo OpenSpec specs) into a validator-checked
`test-plan.md`, then an idempotent Allure TestOps upsert behind a human gate.
