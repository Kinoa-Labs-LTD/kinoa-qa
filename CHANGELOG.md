# Changelog

What changed in each released version of the `kinoa-qa` plugin, newest first.

Check the version you have with `claude plugin list`; if it is older than the top entry here,
update with the two commands in the README's **Versions and updating** section.

The version lives in `.claude-plugin/plugin.json` and nowhere else. Claude Code updates an
installed plugin **only when that string changes**, so a merge that does not bump it never
reaches anyone who already installed the plugin.

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
