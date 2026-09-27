---
name: smoke-run
description: Run a Story's "Smoke test" sub-task against the built feature via the Playwright MCP, and report whether the feature is live, works and is testable — back to the Jira sub-task plus a shareable artifact. Optionally, on request and only inside kinoa-test-automation, save the run as a @smoke Playwright spec. Use when asked to execute a smoke plan or verify that a built Story is ready for deeper testing. Invoke for `/kinoa-qa:smoke-run <SMOKE-SUBTASK-KEY>`.
---

# Smoke run → report on the Jira sub-task

`/kinoa-qa:smoke-run <SMOKE-SUBTASK-KEY>`

## Purpose

Execute a Story's smoke plan against the built feature and report **whether the feature is live,
works, and is testable** — the gate that lets deeper testing proceed. The report goes back to the
Jira sub-task where the plan lives, plus a shareable artifact.

Committing the run as a Playwright spec is **opt-in, not the default** — see "Do not commit a spec by
default" below. Ask for it explicitly when a smoke test has earned it.

## Lifecycle: a short series, then retirement

A smoke plan is run **a handful of times while the Story is in flight** — when the feature first
appears, after a fix, before hand-off — and then retired. It is not standing coverage and it is not a
one-shot either, which is why runs are comments (a series has a history) and the plan is a description
(edited in place, always current).

Two consequences worth stating, because both were review findings:

- **Re-runs are normal, so a known defect must not read like a new one.** Annotate it — see below.
- **Retire it deliberately.** When the Story ships, either the check earns permanent coverage and
  becomes a regression test via kinoa-test-automation's `testops-to-playwright`, or it stops being
  run. A plan nobody has run in a month, still showing a red conformance verdict, teaches people to
  ignore red.

## Use when

- User asks to run a smoke test for a Story, or to verify a built feature against its smoke plan.
- User asks to turn an existing smoke plan into an automated test.
- Input is a "Smoke test" Jira sub-task produced by `/kinoa-qa:smoke-plan` — nothing else.

## Not this skill

- **Writing** the plan → `smoke-plan` (`/kinoa-qa:smoke-plan`, `<plugin>/skills/smoke-plan/SKILL.md`).
- Automating a full manual regression case from TestOps → kinoa-test-automation's
  `testops-to-playwright`.
- Running existing manual cases with the model in the loop every time → kinoa-test-automation's
  `testops-manual-run` (the KING-22127 POC — the inverse mechanism, deliberately).

## Prerequisites

Discover tool names with `ToolSearch` before assuming any are present.

**Check the first two at the start, before anything else.** If either is missing, name exactly what is
missing and stop — do not start a run that cannot drive the browser or post its report and evidence.

- **Playwright MCP** — `ToolSearch` with `query: "playwright browser"`. This is the driver for phase A.
  **Not** the Claude Chrome extension: the Playwright MCP runs the same engine as our suite, so what it
  finds is already expressible as `getByTestId` / `getByRole` and fits kinoa-test-automation's
  locator rules. Keep the Chrome extension only for paths we cannot log into programmatically, e.g.
  SSO.
- **`JIRA_EMAIL` and `JIRA_API_TOKEN`** in the environment — the two Jira scripts post the report and
  upload the evidence with them. Check only that each is set; never print either value. Name the one
  that is missing and point at the token setup in the header of
  `<plugin>/skills/smoke-run/scripts/jiraAttach.mjs`. A `jiraReport.mjs … --dry-run` rehearsal needs
  neither and is not gated on them.

  The start check proves only that both are set, not that the token will work. `jiraReport.mjs`
  **always posts through the `api.atlassian.com` gateway** and ignores `JIRA_HOST`, so it needs a
  token the gateway accepts: a scoped token with the classic `read:jira-work` + `write:jira-work`
  scopes. A classic unscoped token passes the start check and fails only at the final post.
  `JIRA_HOST` affects `jiraAttach.mjs` only.
- **Atlassian MCP** — to read the sub-task and its remote links, rewrite the `Latest run:` line and
  raise Sub-bugs.
- **Allure TestOps MCP** — not used. The case id comes from a Jira remote link or from the user
  (step 1), and the MCP cannot upload a launch (step 9).
- The feature must be **built and deployed** to the target environment. If it is not, stop and say so;
  do not report every step as `blocked` when the real answer is "not deployed yet".

## Inside kinoa-test-automation, or not

Check once, at the start, with `git remote get-url origin` in the working directory. The run is
**inside kinoa-test-automation** when that succeeds and the URL ends in `kinoa-test-automation` or
`kinoa-test-automation.git`. Anything else — not a git repo, no `origin`, another repo — is
**outside**, and three things change. Say each one to the user when it applies:

- **Test data is set up through the UI**, because the repo's API helpers are not there (step 3).
- **Saving the run as a `.smoke.ts` spec is refused** (step 7): the spec is built from
  kinoa-test-automation's page objects, fixtures and `SMOKE` Playwright project.
- **The TestOps launch is skipped** (step 9): the only thing that can feed one is the saved spec's
  `allure-results/`, and the spec is saved only inside kinoa-test-automation. The Jira report and
  the artifact are unaffected.

## Step outcomes

Judge every step per `<plugin>/skills/shared/step-outcome-contract.md` — `pass` / `fail` / `blocked`,
evidence on every non-pass, no step silently dropped. Read that file; do not restate its rules here.
It defines the step level only; the run-level verdicts and report shape below belong to this skill.

## Two verdicts, not one

A conformance verdict alone is misleading, because "failed" reads as "the feature is broken" when it
often means "one expected value disagrees with a stale spec". Every smoke run reports **both**:

- **Feature verdict** — `live` / `partially live` / `not live`. Can deeper test cases now be written
  against this feature? **Derived from the `[GATE]` steps alone**, by the table below.
- **Conformance verdict** — `passed` / `failed` / `blocked`, the overall status from the contract.
  Derived from *all* steps: any `fail` → `failed`; else any `blocked` → `blocked`; else `passed`.

**Deriving the feature verdict.** This is mechanical — do not judge it by feel:

| Gate steps | Feature verdict | Means |
| --- | --- | --- |
| Every `[GATE]` step `pass` | 🟢 `live` | Write deeper tests now |
| At least one `pass`, **and** at least one `fail` or `blocked` | 🟡 `partially live` | Part of it is testable. **Say which part is not** |
| No `[GATE]` step passes, or the entry point cannot be reached | 🔴 `not live` | Stop. Nothing else is worth reporting |
| The plan tags **no** `[GATE]` steps | ⚠️ cannot derive | Not a verdict. Fix the plan before reporting — see `smoke-plan` |

The last row is a real failure mode, not a formality: `smoke-run` needs the literal string `[GATE]` and
a plan without it leaves the skill unable to report a verdict it is required to report.

They are independent, and the combination is the useful signal:

| Feature | Conformance | Means |
| --- | --- | --- |
| `live` | `passed` | Ready. Deeper testing can proceed |
| `live` | `failed` | It works, but something disagrees with the spec — a defect *or* a stale spec. Deeper testing can still proceed |
| `live` | `blocked` | It works; some expected values are not yet agreed. Deeper testing can proceed |
| `partially live` | any | Name the part that is not testable, so the next person knows what to avoid |
| `not live` | anything | Nothing else matters. Stop and report |

#### A `fail` says whether it blocked anything

A reader seeing `fail` on a gate step reasonably assumes the run stopped there. Usually it did not. So
every `fail` records two things beyond the evidence:

- **Did it block?** A failure that stopped later steps is the exception, and the following steps will be
  `blocked` anyway. A failure that changed nothing downstream is marked **non-blocking** — and the run
  **keeps going**. Do not abandon a run over a cosmetic miss.
- **Is it tracked?** Every `fail` ends up with an issue key: an existing one if the defect is already
  filed, a new Sub-bug if not. **Including the cosmetic ones** — the calibration run left a missing
  placeholder untracked, and it stayed invisible until a human read the report and asked about it.

A known, filed defect is still a `fail`. It is annotated `fail (known KING-22355)` and the count reads
`2 fail (2 known)`, but the conformance verdict **stays red**. It is never softened to `blocked`, never
excused to `pass`, and a run where every failure is known is still `failed` — the day that goes yellow
is the day nobody reads it.

**Only these stop a run**: the feature is not deployed, its entry point cannot be found, or
preconditions cannot be provisioned. An unanswered question about an expected *value* never does —
it blocks its own step and nothing more.

## Report shape

One report per run, **posted as a comment** on the Jira sub-task. A published artifact carries the
same content in a readable form for sharing; it never carries *different* content.

**Results go in comments, never in the description.** The description is the *plan* — what to test,
edited in place, always current. A run is an *event*: it has a date, and it is one of a series. Writing
results into the description overwrites the previous run, so a feature that went red, then green,
leaves no trace of having done so.

The one exception is a **single pointer line** at the top of the description, rewritten by each run:

```markdown
> **Latest run: 11 Aug 2026 — 🟢 feature `live` · 🔴 conformance `failed` (11 pass / 2 fail / 0 blocked).**
> Full report in the comments. **This description is the plan; every run is a comment.**
```

One line is cheap to keep accurate and answers "does this work right now?" without scrolling. A full
results block in the description is not — it goes stale silently, which is exactly how KING-22281 ended
up asserting two different outcomes at once.

Order is deliberate: **verdicts, then what they mean for the reader, then detail.** Someone scanning
the ticket needs "can I test this now?" answered in the first two lines. The step table is reference.

**You do not write the report by hand.** Describe the run as JSON and let
`<plugin>/skills/smoke-run/scripts/jiraReport.mjs` render it — the exact field list is in that file's header.
The shape in brief:

```json
{
  "issue": "KING-22281", "date": "11 Aug 2026", "env": "TEST",
  "driver": "model-driven (Playwright MCP)",
  "featureVerdict": "live",
  "grounding": {"liveConfirmedOnly": 8, "total": 13},
  "steps": [
    {"n": 2, "gate": true, "title": "…", "outcome": "fail",
     "evidence": "…", "screenshot": "step-02-dropdown-no-placeholder.png",
     "blocking": false, "known": "KING-22420"}
  ],
  "notAttempted": "none — all 13 steps accounted for",
  "raised": ["…"], "openQuestions": ["…"], "environmentLeft": "…",
  "artifact": "https://claude.ai/code/artifact/…"
}
```

The script computes the conformance verdict and the counts from the outcomes, and refuses to post
(nothing is sent, exit 1) when:

- `issue` is not an issue key, or `steps` is not a non-empty array;
- a step's `outcome` is not `pass`, `fail` or `blocked`, or a step has no `title`;
- a non-`pass` step has no `evidence`;
- a `fail` has no `screenshot` (unless `screenshotWaived` gives the reason), or a `screenshot` is not
  named `step-NN-what-it-shows.png` (`.jpg` / `.webp` also accepted);
- no step is tagged `gate`, or `featureVerdict` is not `live` / `partially live` / `not live`, or it
  contradicts the gate steps' outcomes.

A `fail` with no `known` key is only warned about, not refused. Let it — do not work around a
rejection by editing the outcomes.

**The script checks nothing else, so the rest is yours to ensure:** that `steps` holds every step
of the plan (it cannot compare against the plan), and that the Not attempted, Grounding, Raised and
Environment left blocks below are filled in — it posts a report without them.

Five blocks are mandatory, because each was a real failure before it became a rule:

| Block | Why |
| --- | --- |
| **Both verdicts** | A lone `failed` reads as "the feature is broken" when it usually means a stale spec string |
| **Not attempted** | Every step listed or explicitly accounted for — silent omission reads as coverage |
| **Grounding** | How many expected results came only from observed behaviour. Those steps cannot detect a day-one defect, and a reader deserves to know that before trusting a green |
| **Raised** | A defect described only inside a run report is a defect nobody acts on. Give it a ticket — including the cosmetic ones |
| **Environment left** | Say whether a broken state was left for reproduction or cleaned up. Never leave shared data broken silently |

## Workflow

### 0) No branch needed for the default path

The default run writes nothing to the repo — it reports to Jira and an artifact. Skip straight to
step 1.

**Only if the user asked for a spec** (step 7), inside kinoa-test-automation, branch before writing
any file:

```bash
git fetch origin develop
git switch -c feature/JIRA-ID/short-description origin/develop
```

Use the Story's key: `feature/KING-21500/smoke-players-geo-export`.

### 1) Read the plan

Fetch the "Smoke test" sub-task with `getJiraIssue`. Pull out: preconditions, numbered steps and one
expected result each.

Then find the **TestOps case id** — the one rule for it, used by the spec's `@allure.id` (step 7) and
the launch (step 9): read `getJiraIssueRemoteIssueLinks` on the sub-task for a remote link titled
`Allure TestOps case <id>`. With no such link, use an id the user gives. With neither, there is no
case id, no `@allure.id` and no launch — say so (step 9); never invent one. That remote link is meant
to be written by the planned push of a smoke plan to TestOps (`/kinoa-qa:testplan --from-smoke`,
KING-23102), which is not built, so today the id normally comes from the user.

If the sub-task carries **open questions** from `smoke-plan`, **do not treat them as a reason to defer
the run.** A question about an expected *value* blocks that step's verdict, nothing else — the feature
verdict does not depend on it. Only a question that prevents execution entirely (where the feature
lives, what data is required, which permissions) is worth stopping for.

Better still: **many open questions are answerable by running.** If the step can be executed and the
result observed, run it and report what you saw as a finding for the Story owner. That is usually
faster and more reliable than waiting for someone to recall a decision — on the first calibration run
it settled a question that had been blocking the plan.

Run the **testability-gate** steps first (tagged by `smoke-plan`). They determine the feature verdict:
is it deployed, reachable, does the main path complete, can deeper tests be written against it? Report
that verdict even if later conformance steps fail or stay blocked.

### 1.5) Choose the project deliberately — never a CI project

**A run creates and mutates real data**, and this skill does so as part of its normal path. Confirm
which project to run in before starting, and prefer a personal sandbox.

**Never run in `Autotest Project` or `Autotest Project 2…21`.** Those are the pool the e2e suite draws
from (kinoa-test-automation's `config/game.config.ts`), and the damage is not always obvious — creating an entity at a
priority already in use silently *shifts other entities' priorities* to make room, mutating data the
run did not create.

Whatever you use, record what the run created and anything it changed as a side effect in the report's
**Environment left** block, with enough detail to undo it.

### 2) Log in — and never read the password

The Playwright MCP starts a **fresh browser with no session**, so the app under test is logged out.
Resolve this before touching the plan's steps.

**Ask the user to log in** in the MCP browser, and wait. One prompt at the start beats a run that
reports every step `blocked`.

**Never read, echo or reconstruct the operator credential.** Inside kinoa-test-automation it lives in
`OPERATOR_PWD` in the gitignored `config/.env.<env>` and that repo is deliberately arranged so Claude
cannot read it — its `.claudeignore` blocks `.env.*` and its `.claude/settings.json` puts `cat .env*`
behind a prompt. But `echo` is allow-listed there (`Bash(echo:*)`), so `echo $OPERATOR_PWD` would run
**unprompted** and drop a shared password into the transcript, from where it can reach a snapshot, a
Jira attachment or a published artifact. Do not do this. It has happened once already.

Those protections are kinoa-test-automation's, not this plugin's. Outside that repo nothing blocks the
read, so the rule is the only guard: never echo, print or read a secret, and when the run needs the
operator password, ask the user to provide it through the environment — never in the chat.

If a saved session is available (a Playwright `storageState` file), prefer it — no interaction, no
secret in context.

#### Redact credentials from evidence

Before attaching or publishing **any** screenshot, accessibility snapshot or network log, check it
carries no password, token, cookie or `Authorization` header. A login screen mid-type, a snapshot of a
filled password field, or a network log of the auth request are all disqualifying. Discard and retake
rather than crop — a cropped image still contains the pixels in many formats.

### 3) Phase A — model-driven first run

Drive `mcp__playwright__browser_*` through the steps in order.

- Inside kinoa-test-automation, provision preconditions the way the repo already does: **API over
  UI**. Check `api/controler/` for an existing method before clicking through setup screens — it is
  faster and less brittle, and the generated spec will want the same path. Outside it, set the data up
  through the UI and say so in the report.
- `browser_snapshot` before acting on a new screen; it gives the accessibility tree the locators come
  from. Prefer `browser_find` / role-based targeting over guessing selectors.
- After each step, judge it against its expected result and record the outcome. **Screenshot every
  `fail` as you go** — `browser_take_screenshot` with `filename: "step-NN-what-it-shows.png"`,
  zero-padded. Do not leave it until the end: the screen has moved on by then, and the report cannot
  be posted without it. Screenshot `blocked` steps too wherever there is a screen worth showing.
- **As you go, record the locator that actually worked for each element.** This is the real payload of
  phase A — phase B is built from it, and re-deriving it later means exploring the DOM twice.
- When a step is `blocked`, do not improvise a workaround that changes what is being tested. Record it,
  and continue only if later steps are still meaningful.

Emit the run report before touching any code. **The report is a deliverable in its own right** — if the
feature is broken, that is the answer, and the user may well not want a spec committed yet. Ask.

### 4) Show the report and wait — before any Jira write

**Nothing reaches Jira before the user has seen it and said yes.** `smoke-plan` already works this way;
a run is no different, and it writes more: a comment, attachments, a description pointer, sometimes a
Sub-bug on someone else's Story.

Show the verdicts, the step table and what you are about to write — the comment, the files, the pointer
line, any Sub-bug — then stop. On a yes, write it. If the user amends a verdict, amend the report; do
not argue the judgement back at them, they can see the screen and you cannot.

The two exceptions, because both are read-only or already the user's own decision: reading the plan, and
capturing screenshots to a local directory.

### 5) Report back to Jira, and publish an artifact

This is the deliverable. Two places, because they serve different readers:

1. **A comment on the Jira sub-task**, posted with **`<plugin>/skills/smoke-run/scripts/jiraReport.mjs`** —
   never hand-written Markdown. Write the run as JSON (shape in the script header) and let the script
   build it:

   ```bash
   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json                  # post
   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json --update <id>    # re-post after adding the artifact link
   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json --dry-run        # validate without posting
   ```

   The script renders native Jira — coloured verdict panels, `PASS`/`FAIL`/`BLOCKED` lozenges, a `GATE`
   marker on gate steps — which reads far better than a Markdown table. More importantly it **refuses
   to post** a report where a non-pass step has no evidence, a `fail` carries no screenshot, or the
   feature verdict contradicts the gate steps (the full list is under "Report shape"), and it
   **computes the conformance verdict from the step outcomes** rather than taking your word for it.
   It does not check that every plan step is present or that the Not attempted, Grounding, Raised
   and Environment left blocks are filled — that is on you.

   **Never write the report into the description** — that is the plan, and overwriting it destroys the
   run history. Update only the single `Latest run:` pointer line at the top of the description, adding
   it if absent.
2. **A published artifact — always, not on request.** It is the *mirror* of the Jira comment: same
   verdicts, same steps, same findings, with the screenshots embedded inline rather than attached
   below. Two formats of one report, and they must never say different things.

   **One artifact per plan, updated in place** — pass the existing URL when republishing so the link
   stays stable. A new URL per run means somebody has to share each one again, and artifacts are
   private until shared.

   **Cross-link them.** Put the artifact URL in the report JSON's `artifact` field and re-run with
   `--update <id>`; the Jira comment then links the artifact, and the artifact's footer links back to
   the ticket. Either one found alone leads to the other.

Raise anything that looks like a product defect as a **Sub-bug on the Story**, matching the sibling
bugs' format there (`Precondition` / `STR` / `ER` / `AR`). Label an inferred cause as inferred. A
finding buried in a run report is not a finding anyone will act on.

#### Attach the evidence — `<plugin>/skills/smoke-run/scripts/jiraAttach.mjs`

The Atlassian MCP can write comments but **cannot upload files**. Use the plugin's helper instead, which
posts to Jira's REST attachment endpoint:

```bash
node <plugin>/skills/smoke-run/scripts/jiraAttach.mjs KING-22355 \
  .playwright-mcp/bug-1-field-deleted.png \
  .playwright-mcp/bug-2-conflict-persists.png
```

It needs `JIRA_EMAIL` and `JIRA_API_TOKEN` in the environment (checked at the start — see
Prerequisites — and set up as the script header says). If they are missing it says exactly how to set
them — **do not fall back to silently skipping the attachment.**

Rules:

- **Attach to whichever issue the evidence belongs to** — run evidence on the smoke-test sub-task,
  defect evidence on the Sub-bug. Not everything on one ticket.
- **Attach before you reference the images in text.** Never write "screenshots attached" or
  "screenshots to follow" until the upload has actually succeeded and you have seen the confirmation.
  A ticket that promises evidence which never arrives is worse than one with none.
- **If the upload fails** — wrong permissions, network — say so plainly with the script's error and
  its hint, fix the cause and re-run the upload. Do not leave the ticket claiming otherwise.
- Follow the evidence rules in `<plugin>/skills/shared/step-outcome-contract.md`: the screenshot must
  show the failure, not the setup for it, and its filename must say what it shows.

#### Leave a reproducible state, or restore it

When a defect needed deliberate setup, decide which is more useful and **say which you chose**:
leaving the failing state in place so the next person reproduces it in one step (then ask on the
ticket that they restore it afterwards), or cleaning up and documenting the setup recipe. Silently
leaving broken data in a shared project is not an option.

### 6) Do not commit a spec by default

**Stop here unless the user explicitly asks for a spec.** A Story smoke test typically runs a handful
of times — once on TEST, maybe once on preprod, a couple of re-runs after fixes — and then the feature
graduates into regression coverage and the smoke test is done. A committed spec does not repay its
maintenance over that lifecycle, and the artefacts it adds are more surface to keep in sync.

Two things make this concrete in this product:

- **Stable attributes are scarce.** The KING-19550 runs found none on the export dialog — every
  control was reached by text. A spec written from that is text-locator-bound.
- **The text itself is unstable.** On that same feature the PRD, the design and the build disagreed
  three ways on the very strings such a spec would assert.

**When a smoke check has earned permanent coverage** — a core feature, re-run every release — do not
grow this skill into a regression suite. Use
`.claude/skills/testops-to-playwright/SKILL.md` in kinoa-test-automation, which already does that job
properly: it creates the TestOps case, wires `@allure.id`, and produces a
regression test rather than a smoke test wearing one's clothes.

### 7) Opt-in — save the run as a spec

**Inside kinoa-test-automation only.** Outside it (see "Inside kinoa-test-automation, or not"), refuse
the save and say why: the spec is built from kinoa-test-automation's page objects, fixtures, data
generators and `SMOKE` Playwright project, and none of them is in this working directory. The run
report stands on its own.

Write `tests/smoke/<feature>.smoke.ts`. The `.smoke.ts` suffix is load-bearing — see "Why this stays
out of the shard map" below. **Never name a smoke file `*.test.ts`.**

```ts
import { playerAndInAppFixture as test } from "../../fixtures/inAppFixture";
import { allure } from "allure-playwright";
import { expect } from "@playwright/test";

test.beforeEach(async () => {
    await allure.feature('smoke');
    await allure.story('<Story summary>');
})

test.describe('Smoke. <Feature>.', () => {
    test('<what it proves> @smoke @allure.id=<case id from step 1>', async ({ page, dashboardAPI }) => {
        // ...
    });
});
```

With no case id from step 1, leave `@allure.id=…` out of the title — never put a placeholder there.

Follow the repo's rules — they are not relaxed for smoke tests:

- **Page objects** for all UI interaction, in `pages/`. Extend an existing page object rather than
  creating a new one. Locators are class-level private fields, never inline. Methods that `fill`/`click`
  assert their post-condition. Decorate user-facing methods with `@step`. Invoke
  `.claude/skills/page-object-author/SKILL.md` in kinoa-test-automation for this part instead of
  reasoning from scratch.
- **Locator priority**: unique id / `data-testid` / `name` first, then `getByRole` / `getByLabel` /
  `getByPlaceholder`. **Never XPath.** If phase A only worked via a fragile CSS path, record a
  `data-testid` request for FE rather than committing the fragile locator.
- **Test data**: runtime values from `datafactory/*Generator.ts`, static payloads from `resources/**`
  JSON. No large literals in the test body, no re-shaping generator output in the test.
- **Fixtures**: reuse an existing one from `fixtures/` (`baseFixture` plus the domain composition).
- **Assertion messages state the failure, not the intent** — `expect(x, "Geo filter kept non-DE rows")`,
  never `"Verify geo filter works"`.
- **No file-header docstring** summarizing the scenario. The `@allure.id` and the body are the source
  of truth.
- Cleanup in `afterEach` via API helpers.

Cover every step that ran. A step that was `blocked` in phase A becomes either a `test.fixme` with the
reason, or is left out with an explicit note in the report — never silently absent.

### 8) Verify the spec (opt-in path only, inside kinoa-test-automation)

```bash
npx playwright test --project=SMOKE tests/smoke/<feature>.smoke.ts
npx eslint tests/smoke/<feature>.smoke.ts pages/<changed page objects>
```

Both must be green before reporting done. Paste the actual output — a green run is the evidence, not
your memory of one.

Then confirm kinoa-test-automation's main suite is untouched:

```bash
node scripts/rebalanceShards.mjs --check   # must exit 0, with no regeneration needed
```

### 9) Allure TestOps (opt-in path only)

**No TestOps case is created by default** — the Jira sub-task is the source of truth. A launch can
come only from this path — a spec saved and run inside kinoa-test-automation, with a case id from
step 1 (the remote link, else the user's id).

What exists is this: kinoa-test-automation's `playwright.config.ts` reports through
`allure-playwright`, so the step 8 run writes `allure-results/` in the working directory, and with a
case id each result carries `@allure.id`. **Nothing uploads it.** That repo has no upload step —
no `allurectl`, no npm script; its TestOps launches come from its Jenkins CI jobs, and the `SMOKE`
project has no Jenkins pipeline (KING-22214). The Allure TestOps MCP cannot upload a launch either.
So publishing a smoke run as a TestOps launch is **not automated**: do not claim a launch, and do not
invent a way to upload one. Tell the user where `allure-results/` is and that it carries the case id.

**Say that no launch was published, and why** — the run is outside kinoa-test-automation, no spec was
saved, there is no case id, or, when all three hold, that uploading is not automated. The Jira report
is unaffected.

## Why this stays out of the shard map

This is kinoa-test-automation's Playwright setup. The `SMOKE` project in `playwright.config.ts` uses `testMatch: '**/*.smoke.ts'`. It stays isolated by
construction, and nothing needs remembering:

- The `KINOA` project matches only `**/*.test.ts`, so smoke tests never join the sharded e2e run.
- `scripts/rebalanceShards.mjs` walks only `.test.ts` files, so a new smoke file never invalidates
  `shards/shards.json` and **no rebalance is required** when adding one.

Both guarantees rest entirely on the filename suffix. Naming a smoke file `*.test.ts` drops it into the
sharded suite *and* breaks every CI shard until someone rebalances. Keep `.smoke.ts`.

Smoke tests are run locally for now — a Jenkins pipeline for the `SMOKE` project is explicitly out of
scope (KING-22214).

## Output to user

- **Both verdicts, feature first** — `live` / `partially live` / `not live`, then the conformance
  verdict. A reader's first question is "can we test this feature now?", not "did every string
  match". See "Two verdicts, not one" above.
- The run report (contract format), including any `blocked` steps and open questions.
- The Jira sub-task comment link, and the published artifact link.
- Any Sub-bug raised for a suspected product defect.
- Any `data-testid` requests for FE that came out of locator discovery.
- *Opt-in path only:* path of the committed spec and any page objects touched, the exact verify
  commands and their result, and — when a case id existed — the path of the `allure-results/` the
  run wrote.
- That no TestOps launch was published, and why (step 9).

## Guardrails

- **Do not commit a spec unless asked.** The default deliverable is the report, not code.
- Never commit a spec for a run whose outcome the user has not seen.
- Never soften a `fail` into a passing assertion to get a green spec. A smoke test that encodes the bug
  as expected behavior is worse than no test.
- Don't add `.only` / `.skip` (CI-forbidden), except a deliberate documented `test.fixme` for a
  `blocked` step.
- Don't widen the spec into regression coverage; it proves the Story, nothing more.
