# Changelog

What changed in each released version of the `kinoa-qa` plugin, newest first.

Check the version you have with `claude plugin list`; if it is older than the top entry here,
update with the two commands in the README's **Versions and updating** section.

The version lives in `.claude-plugin/plugin.json` and nowhere else. Claude Code updates an
installed plugin **only when that string changes**, so a merge that does not bump it never
reaches anyone who already installed the plugin.

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
