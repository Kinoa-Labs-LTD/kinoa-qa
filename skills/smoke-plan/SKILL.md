---
name: smoke-plan
description: Turn a Jira Story into a "Smoke test" sub-task with numbered steps and expected results, grounded on the Story's acceptance criteria, its linked PRD and its Figma design. Use when asked to plan a smoke test for a Story, to check whether a Story is clear enough to test, or to prepare the input for the smoke-run skill. Invoke for `/kinoa-qa:smoke-plan <STORY-KEY>`.
---

# Story → Smoke test plan

`/kinoa-qa:smoke-plan <STORY-KEY>`

## Purpose

Read a Jira Story and produce the smallest set of steps that proves its new functionality works — as a
"Smoke test" sub-task on that Story. The sub-task is the single source of truth — the plan, the run
report and any findings all live on it.

A second, equally important output: **the plan shows whether the Story is testable at all.** A Story
that cannot be turned into clear pass-or-fail steps is a Story that is not ready, and the open
questions this skill raises are the evidence.

## Use when

- User asks to plan or draft a smoke test for a Story (e.g. "smoke plan for KING-21500").
- User asks whether a Story is clear enough to test.
- User is preparing input for `smoke-run` (`/kinoa-qa:smoke-run`, `<plugin>/skills/smoke-run/SKILL.md`).

## Not this skill

- **Running** the smoke test → `/kinoa-qa:smoke-run`.
- The Integration Skill endpoint tests (KING-21900) → kinoa-test-automation's
  `integration-skills-endpoints`. Those check integration endpoints; here "smoke" means the Story smoke
  test only.
- The OpenSpec `flow-test-plan` stage in the kinoa-dev plugin (KING-21852) — different artifact,
  different repo.
- Automating an existing TestOps case → kinoa-test-automation's `testops-to-playwright`.

This skill lives in the kinoa-qa plugin, beside `testplan`, never in the kinoa-dev plugin: kinoa-dev
skills must never write into a service repo, and the smoke pair is QA tooling. It runs from any working
directory; only `smoke-run`'s opt-in spec save writes test code, and only inside kinoa-test-automation.

## Prerequisites

Tool names are loaded at runtime — call `ToolSearch` before assuming any are present.

- **Atlassian MCP** — `ToolSearch` with `query: "jira issue"`. Needs `getJiraIssue`,
  `getJiraIssueRemoteIssueLinks`, `createJiraIssue`, `editJiraIssue`.
- **Figma MCP** — `ToolSearch` with `query: "figma design context"`. Optional but strongly preferred;
  see step 2 for the degraded path.

## Workflow

### 1) Read the Story

Fetch the Story with `getJiraIssue`, requesting `description`, `status`, `issuetype`, `parent`,
`labels`, and `comment`. Then `getJiraIssueRemoteIssueLinks` on the same key — **both** a Figma URL and
a Confluence PRD are frequently remote links rather than inline in the description, so check both
places for both.

Extract and hold separately:

- The Story statement and its **acceptance criteria** (verbatim — these are the backbone of the plan).
- The parent epic's summary, for context on what the feature belongs to.
- Any Figma URL(s).
- **Any linked Confluence PRD / HLD.** Fetch it with `getConfluencePage`. In practice this is often the
  single richest source — PRDs here carry literal UI copy (modal titles, spinner text, section
  headings, button labels) that the Story summarises away. Ground on it.
- Anything in the comments that changes scope. Comments often carry the real decision.

If the issue is not a Story (it is an Epic, a Bug, or a sub-task), say so and stop — ask the user which
Story they meant rather than planning against the wrong artifact.

**Cross-check the sources against each other before writing any step.** Do not harvest each section in
isolation. A Story's AC bullet and its "Other information" or "Side notes" block can contradict each
other outright, and that contradiction is one of the most valuable things this skill can surface —
it means two people hold different beliefs about the feature. Any conflict between AC, Story body, PRD
and design becomes an open question (step 4), never a silent pick between them.

### 2) Ground expected results on Figma

When a Figma link exists, open it read-only and navigate **only the frames belonging to this Story**:

- `get_metadata` first to see the frame structure cheaply, then `get_design_context` on the relevant
  frames, and `get_screenshot` where a visual check settles a question.
- Harvest exactly this: field and button **labels**, control **states** (disabled, loading, selected),
  **validation copy**, **empty states**, and **error states**. These make expected results concrete
  ("the Save button is disabled and shows 'Select a segment first'") instead of vague ("saving is
  prevented").

Two hard rules:

- **Figma is a source of expected results, never of locators.** Locators come from the live DOM, and
  they are discovered later by `smoke-run`. Never write a selector into the plan.
- **Never fail silently on missing access.** No Figma link on the Story, or the Figma MCP not
  reachable → state it plainly in the draft ("No Figma design linked — expected results are grounded
  on the acceptance criteria only") and continue. A plan without design grounding is still useful; a
  plan that pretends it had design grounding is not.

**On Figma access.** This skill only ever *reads* Figma; it never writes, and it is forbidden from
taking locators from the design. When a read fails with **`"you don't have edit access to this file"`,
do not take that message at face value** — it is Figma's generic permission error and it names the
highest permission you lack, not the operation attempted. Two distinct causes, with different fixes:

1. **The authenticated account is not a member of the plan that owns the file.** This is the common
   one and it blocks access completely. Run `whoami`: it returns the authenticated email and every
   plan that account belongs to. If the file's owning organisation is not in that list, the fix is to
   be **added to that plan** (or to re-authenticate the MCP as the work account, if a different login
   already has access) — *not* to be granted edit rights on the file.

   **"But I can open the design in my browser" does not contradict this.** Viewing a file and reading
   it through the MCP are different permissions. A direct file share, or link-sharing being enabled,
   grants browser viewing *without* team membership — and the MCP requires membership on top of view
   permission (Figma's own wording: "ensure the user belongs to the plan to which the file being
   accessed belongs **to as well**"). So sharing the file again will not fix it; joining the team will.
   Confirm by checking whether the owning team appears in the `whoami` plan list at all.
2. **Seat volume.** A View or Collab seat *does* get MCP reads, but only **6 tool calls per month**;
   Dev/Full seats get 200/day (Organization) or 600/day (Enterprise). Grounding one Story costs
   several calls, so a View seat is effectively unusable here even once access works. Ask for a
   **Dev seat** — for throughput, not for write permission.

Never phrase the request as needing edit access. It is untrue, and it gets refused for the wrong
reason. Until access works, fall back to the linked PRD — which usually carries the same UI copy —
and record in the draft that design grounding was unavailable.

**Every QA uses their own Figma identity — no account is shared.** The Figma MCP is a per-user OAuth
connector (tools namespaced `mcp__claude_ai_Figma__*`), deliberately *not* declared in
kinoa-test-automation's `.mcp.json` nor in this plugin, so no credential is committed and this skill
holds no token, email, or account reference. When another
person runs it, it reads Figma as *them* and sees only what their own account can see — the same way
`allure-testops` reads each person's own `ALLURE_TESTOPS_TOKEN` from their shell.

The consequence is provisioning, not secrecy: **each QA needs their own membership of the Figma team
that owns the design file**, with a Dev seat. On the Kinoa pro-tier team that is 200 calls/day; a View
seat is capped at 6/month and cannot support real use.

**Every QA who runs this skill needs their own seat — there is no shared-account shortcut.** Sharing
one login would mean handing out a password and 2FA, it destroys the audit trail (every action reads
as one person), and it is not something to set up. Budget **one Dev seat per QA who authors plans**.

Two things soften the cost:

- **Only the plan phase needs Figma.** `smoke-run` reads the sub-task, never the design, so anyone
  executing or automating a plan needs no Figma access at all.
- **Grounding happens once per Story.** The design facts are written into the sub-task as text, so a
  Story already planned by one QA needs no further Figma reads by anyone else.

A QA without a seat can still run this skill — it degrades to PRD/AC grounding and says so in the
draft. Just expect the UI-copy steps to be wrong, exactly as they were on the first KING-19550 run.

**Why design grounding matters more than the PRD.** Confirmed on the first calibration run
(KING-19550): the PRD described a modal that opens already scanning, with sections named "Entities to
create" / "Entities that already exists". The shipped UI is an inline panel whose scan starts only
after a destination is chosen, with different section labels. The **Figma design matched the shipped
UI** (frame `Destination Project`, matching the built control, against the PRD's "Select destination
environment"). PRDs are written once and go stale; designs are updated during build. When both exist
and they disagree, **the design wins** — and say so in the draft.

### 3) Write the steps

Aim at **proving the new functionality works**, not at regression coverage. Aim at about 2–5 numbered
steps — a target, not a limit. Each step is one user action with exactly one expected result.

- Steps are written for a person to read and follow, in the product's own vocabulary (`flow`, `in-app`,
  `segment`, `player event` — keep terminology consistent with the repo and the dashboard).
- Preconditions go in their own block at the top of the sub-task, not smuggled into step 1.
- One expected result per step, observable and binary — a human must be able to say pass or fail
  without interpreting. "The list updates" is not an expected result; "3 rows remain, all with
  Country = DE" is.
- Keep steps independent of test data that only exists at run time; name the *kind* of data needed
  ("a player with geo = DE") and let `smoke-run` provision it.

### 4) Traceability gate — the core of this skill

**Every expected result must cite its source.** Tag each one inline, and prefer sources higher in this
list — the ranking is the point, not the tags:

| Tag | Source | Authority |
| --- | --- | --- |
| `[AC-2]` | A specific acceptance criterion | What was **agreed**. Strongest |
| `[Story]` | The Story description | What was **asked for** |
| `[PRD: section]` | A named section of the linked Confluence PRD | A derived spec. **Verify it against the build** — PRDs here go stale |
| `[Figma: frame]` | Read off the design | A derived spec, good for micro-copy, also goes stale |
| `[live-confirmed]` | Observed in the running build | **Not a spec at all.** Last resort — see below |

#### `[live-confirmed]` — legal, ranked last, and counted

Sometimes no written source states the expected result. On the calibration Story the PRD named a modal
and three section headings that **do not exist in the product**, and the design's conflict-reason
strings differed from the build's. Grounding on the build was the only way to get a testable plan, and
it fixed a first pass that was wrong on two steps.

So the tag is **legal**. But be clear-eyed about what it costs:

**A step whose expected result was read off the build cannot fail on the run that wrote it.** It is a
change detector, not a conformance check — useful later as regression material, worthless as an answer
to "does the delivered feature match what was asked for". Three rules keep that honest:

1. **Micro-copy only, never behaviour.** *What the feature does* comes from the AC or the Story. Only
   *exactly how it words things* may come from the build. "The In-App exists in the destination" is
   `[Story]`; "the banner reads *The system has analyzed dependencies…*" is `[live-confirmed]`.
2. **Name what it overrode** when it contradicts a written source: `[Figma → live-confirmed]`,
   `[PRD → live-confirmed]`. A bare `[live-confirmed]` means *no* source covered it. The difference
   matters: one is a spec that needs correcting, the other is a spec that never existed.
3. **Count them, and say the number in the plan** — how many steps are grounded on observed behaviour
   only, and how many of those are `[GATE]`:

   > **Grounding:** 8 of 13 expected results are `[live-confirmed]` with no written source. This plan
   > cannot detect a day-one defect in those steps.

   That line is not an apology, it is a **finding**. When it reads *8 of 13*, the real message is that
   the written spec was not good enough to test against — which the PO needs to know more than they
   need a clean-looking plan.

**On a `[GATE]` step, prefer a coarse assertion the Story does cover.** "The export completes and the
In-App appears in the destination" is `[Story]`-grounded and gates just as well as a sentence about
button states. Where a gate step genuinely has no written source, it stays legal — but it is the first
thing to raise with the PO, because it means nothing written tells us what "working" looks like.

**An expected result with no source at all — not even the build — is not written as a step.** It goes into
an **Open questions** section on the sub-task, phrased as a question for the PO:

> Open question: AC-3 says the export "handles large segments". What is the threshold, and what should
> the user see above it — a warning, a queued job, or an error?

Do not guess a threshold, invent validation copy, or assume a default. Guessed expected results are
worse than absent ones: they get automated in the next step and then defended as if they were
requirements.

If open questions outnumber grounded steps, say so directly in the summary — that is the "Story is not
ready" signal this skill exists to produce.

#### Open questions must reach the Story owner

An open question buried in a sub-task nobody opens is not a question, it is a note to self. So:

1. **Keep the full list on the sub-task**, in its own `Open questions` section. That is where the
   person running the smoke test will look.
2. **Duplicate it as a comment on the parent Story**, addressed to the Story owner — but only the
   things that belong there. See "What earns a Story comment" below.
3. **Mark the affected step**, and only that step. A step whose expected result depends on an
   unanswered question cannot be judged `pass` or `fail` — it is `blocked` (see
   `<plugin>/skills/shared/step-outcome-contract.md`). Write that on the step itself.

Do not soften this into "assume Draft for now". An assumed expected result gets automated by
`smoke-run` in the next step and then defended as if it were a requirement — which is exactly the
failure the traceability gate exists to prevent.

#### What earns a Story comment

**Write where the person who must act will read it.** A comment on the Story notifies the PO, the devs
and every watcher. Spend that attention only when they must decide or know something — a Story stream
full of QA working notes trains people to stop reading it.

Comment on the parent Story when, and only when:

1. **Only the PO can answer it.** An expected value derivable from no source — which status, what
   threshold, what the copy should say. But first: **if a run could answer it, run it.** Reporting
   an observation beats asking a human to recall a decision.
2. **The Story contradicts itself.** An AC bullet against an "Other information" line, or against the
   PRD. Two people hold different beliefs about the feature; resolving that is the owner's, not QA's.
3. **The build contradicts the written spec.** Someone must correct one of them, and which one is a
   product decision. Note this is *not* a bug — the product may be right and the AC stale, as with
   `Draft` vs `In-Review` on KING-19550.
4. **An acceptance criterion is not verifiable.** A business metric with no threshold and no
   measurement source is a defect in the Story, so it belongs on the Story.
5. **The Story is not testable at all** — open questions outnumber grounded steps. That is readiness
   feedback, and it is cheapest the earlier it lands.

**Do not** put these on the Story:

| Instead of a Story comment | It goes to |
| --- | --- |
| Run results | A comment on the smoke-test sub-task |
| Plan corrections, environment or setup notes | The sub-task |
| A product defect | A **Sub-bug** on the Story — a defect needs a ticket someone can assign and close, not a comment |
| Anything QA can resolve without the PO | Nowhere |

Two rules that matter as much as the list:

- **One comment, updated in place — not a stream.** As questions get answered, edit the existing
  comment so the owner sees one current list, rather than reconstructing state from four comments
  posted over a week. Use the comment id you already have.
- **Say precisely what is blocked, and what is not.** "This smoke test cannot be evaluated" is almost
  always wrong and stalls a runnable test. Name the one step affected and state plainly that the rest
  proceeds.

Keeping the questions on **both** the sub-task and the Story is deliberate, not duplication to be
tidied away: the tester needs them while running, the owner needs them where they converse. The
*answer* lands on the Story, and is then reflected back into the plan.

#### An open question does not block the run

**Never write "this smoke test cannot be evaluated until the open questions are answered."** That
inverts the point of a smoke test. Its primary job is to establish that the delivered feature is
**live, works, and is testable** — the gate that lets deeper test cases proceed. Whether one expected
*value* matches an agreed spec is a secondary question, and it cannot stop the primary one.

So, when classifying an open question, decide which kind it is:

- **Blocks the run** — the question prevents execution at all: where the feature lives in the UI, what
  data setup is required, which permissions are needed. Without an answer nothing can be attempted.
  These are worth waiting on.
- **Blocks one judgement** — the question is about an expected *value* (which status, which copy,
  which threshold). The step still runs; only its verdict is withheld. **The plan is runnable.**

Almost all open questions are the second kind. Say so explicitly in the summary, so nobody defers a
run that would have told them something.

**And prefer running to waiting when the product can answer.** Many "open questions" are questions
about built behaviour that a single run settles by observation. If the answer is discoverable by
running the step and looking, the plan should say so and let `smoke-run` find out — reporting the
observation as a finding for the Story owner rather than asking them to recall a decision. On the
first calibration run (KING-19550) the Draft-vs-In-Review question was answered exactly this way, in
minutes, after a day of waiting on a human.

#### Mark the testability gate — with the literal tag `[GATE]`

Tag the minimal subset of steps that answer *"is this feature live and testable?"* — typically
reaching the feature, completing its main path, and confirming the states deeper tests will need.
`smoke-run` runs these first and reports the **feature verdict** from them alone. Everything else is
conformance detail and does not gate deeper testing.

**Write the marker as the literal string `[GATE]`, at the start of the step:**

```markdown
**1. `[GATE]`** Open the In-App list and open the row's Action List.
*Expected:* An **Export** action is present.
```

`smoke-run` looks for exactly that string. Any other wording — "gate", "(gate step)", bold text —
leaves it with no gate steps and no way to produce a verdict it is required to report.

**One assertion per gate step.** A gate step answers one question: *did this part of the feature work?*
Bundling several checks into it means a single cosmetic miss turns the whole gate red and the feature
verdict with it. That happened on the calibration Story: gate step 2 asserted a modal, a title, a status
chip, two buttons **and** a placeholder — the placeholder was missing, the step went `fail`, and the
report then had to explain why the run carried on anyway.

Split it. Put the gate assertion in the gate step and the detail in an untagged step beside it:

```markdown
**2. `[GATE]`** Click **Export**.
*Expected:* The export modal opens. `[Story]`

**2a.** Inspect the modal's controls.
*Expected:* Headed **Export In-App**, a **Destination Project** dropdown showing
`Select Project...`, **Cancel**, and **Export** disabled. `[Figma: Export modal]`
```

Gate green, conformance red, and no reader left wondering whether the run should have stopped.

### 5) Record `data-testid` requests

While reading the design, note any control the plan depends on that has no plausible stable attribute.
Collect these into an **FE requests** section on the sub-task:

> FE request: the geo filter chip in the Players toolbar needs a `data-testid` — no id, and its
> accessible name is the country code, which changes per row.

kinoa-test-automation's locator priority is unique id/attribute first, then role/label/placeholder,
and never XPath (see `.claude/skills/page-object-author/SKILL.md` in kinoa-test-automation). Raising the
request at plan time is much cheaper than discovering it mid-run.

### 6) Show the draft and stop

Render to the user, in the chat, before writing anything anywhere:

- The full sub-task body (preconditions, numbered steps with expected results and source tags, open
  questions, FE requests).
- A one-line testability verdict: grounded steps vs open questions.

**Nothing is created in Jira until the user explicitly confirms.** This is an
acceptance criterion of KING-22213, not a courtesy. Edits requested → revise and show again.

### 7) Create on confirmation

In this order, because each step feeds the next:

1. **Jira sub-task** — `createJiraIssue` with issue type `Sub-task`, `parent` = the Story key, summary
   `Smoke test: <Story summary>`, body as drafted. **This is the source of truth** — the plan, the run
   report and any findings all live here.
   - **`Kinoa Team` (`customfield_10131`) is required** and creation fails without it. Do not guess:
     read it off a sibling sub-task on the same Story and match that, so the smoke test lands with the
     team that owns the feature rather than with the AQA tooling team.
   - Pass `contentFormat: "markdown"` and write the body in **Markdown**. Jira wiki markup (`h2.`,
     `{{code}}`, `[text|url]`) renders literally and makes the sub-task unreadable.
2. **Comment the open questions onto the Story** — `addCommentToJiraIssue` on the parent Story, listing
   every open question and linking the new sub-task. Skip only when there are none.

**This skill creates no Allure TestOps case.** A Story smoke test runs a handful of times and
then the feature graduates into regression coverage; a TestOps case is a third representation to keep
in sync for little return, and drift between representations is a real observed failure mode. A push
of the smoke plan to TestOps through `/kinoa-qa:testplan --from-smoke` is planned (KING-23102) and not
built yet — until it exists, this skill writes to Jira only. When a smoke check is being promoted to
permanent coverage, use kinoa-test-automation's `.claude/skills/testops-to-playwright/SKILL.md`,
which owns that job properly and wires `@allure.id` as part of it.

Report back: the sub-task key, the open-question count, and the testability verdict.

## Output to user

- Sub-task key + URL.
- Step count, and how many expected results came from each source (AC / Story / Figma).
- Open questions, listed — these are for the PO, and the user should be able to paste them straight
  into a Story-refinement conversation.
- FE `data-testid` requests, if any.
- Whether Figma grounding was available.

## Guardrails

- No writes before confirmation. Ever.
- No invented expected results — untraceable becomes an open question.
- No locators, selectors, or code in the plan. It is a human-readable document.
- Don't pad the plan toward regression coverage; smoke means "does the new thing work".
- Treat the first Story as **calibration, not delivery** — we do not yet know how much the generated
  steps need editing. Record what you had to fix as a comment on KING-22213.
