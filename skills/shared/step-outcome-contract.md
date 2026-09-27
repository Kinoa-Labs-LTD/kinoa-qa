# Step outcome contract

> **Source:** `skills/shared/step-outcome-contract.md` in the kinoa-qa plugin. Edit only that copy.
> kinoa-test-automation keeps a read-only mirror at `.claude/skills/shared/step-outcome-contract.md`
> (testops-manual-run loads it there; `scripts/packageSkill.mjs` bundles it). Refresh the mirror with a
> plain copy of this file.

Shared reference for any skill that executes test steps and judges them against expected results.
Currently the kinoa-qa plugin's `smoke-run` (`skills/smoke-run/SKILL.md`) and kinoa-test-automation's
`testops-manual-run` — **cite this file, do not restate it.**

**Scope: how a single step is judged, and what evidence it carries.** Nothing else. Not how steps are
driven, not where a report is posted, not what verdicts a run reports overall — those belong to the
skill, because they differ per skill and this file must stay usable by any of them.

## The three outcomes

A step gets exactly one of these. There is no fourth outcome, and no blending of two.

| Outcome | Meaning |
| --- | --- |
| `pass` | The step ran **and** its expected result was observed. Both halves are required. |
| `fail` | The step ran and the expected result was **not** observed. The product behaved, but wrongly. |
| `blocked` | The step **could not be run or judged** — element not found, timeout, navigation dead-end, ambiguous instruction, missing precondition data, or a prior `blocked` step left the app in an unknown state. |

Rules that hold in every run:

- **`blocked` is not `fail`.** `fail` is a statement about the product; `blocked` is a statement about
  the run. Collapsing them reports test-harness trouble as a product defect.
- **A step that was not attempted is never `pass`.** Skipping the assertion — because the element was
  missing, because the step "looked cosmetic", or because a helper returned early — makes it `blocked`.
- **Expected result observed but by a different route than the step describes** → `pass`, with the
  deviation stated in the evidence note. Do not silently rewrite the step.
- **Partially observed expected result** (2 of 3 asserted values match) → `fail`, evidence naming which
  value diverged. Never round up to `pass`.
- Once a step is `blocked`, later steps that depend on its state are also `blocked`, not `fail`.

**Steps never silently disappear.** Every step in the source case appears in the report, or is listed
as not attempted. Walk the case top-to-bottom before reporting and confirm the counts match.

## Evidence

Every non-`pass` step carries evidence. No exceptions — an unevidenced `fail` is not actionable.

| Outcome | Evidence |
| --- | --- |
| `fail` | **A screenshot is required**, plus a note. If one genuinely cannot be produced, say why — that is itself a finding, not a licence to skip it |
| `blocked` | A note saying what stopped the run: the locator tried, the timeout hit, the ambiguous instruction. A screenshot too wherever there is a screen to show — "I looked here and it was not there" is worth seeing |
| `pass` | None needed, though a screenshot is fine to keep |

- The note describes **what was seen**, not what was wanted: `"Save button disabled, tooltip 'Select a
  segment first'"`, not `"Save should have been enabled"`.

**Name a screenshot `step-NN-what-it-shows.png`** — zero-padded number, then words:

```
step-02-dropdown-no-placeholder.png
step-10-conflict-persists-after-refresh.png
```

The number ties the image to its row without the reader guessing; the words say what they are looking
at when the row is out of sight. `step-02.png` is not enough, and `screenshot-1.png` is useless.

The kinoa-qa plugin's `skills/smoke-run/scripts/jiraReport.mjs` **rejects a report** where a `fail` carries no screenshot, or where a
screenshot is misnamed. That is deliberate: the previous rule said "a screenshot *or* a note", and the
first real run duly marked a gate step `fail` with no image — which a QA noticed before anyone else.

**A screenshot must show the failure, not the setup for it.** This is easy to get wrong on a
multi-step defect. If the bug is "the conflict persists *after* the entity is deleted", a screenshot of
the conflict *before* the deletion shows correct behaviour — it looks like evidence and proves
nothing. Capture the state that is wrong: the thing that should have changed and didn't, the value
that should have cleared and remains. Where the failure is only visible as a *difference*, capture
both states, suffixing the step number so the order is unambiguous —
`step-10a-field-deleted.png`, `step-10b-conflict-persists.png`.

## Overall status

The run's status is the worst outcome present: any `fail` → `failed`; otherwise any `blocked` →
`blocked`; otherwise `passed`. **A run with `blocked` steps is never reported as `passed`.**

A skill may add verdicts of its own on top of this — the kinoa-qa plugin's `smoke-run` reports a separate *feature verdict*
alongside it, because "is this new feature live yet?" is a different question from "did every expected
result match". That is the skill's business, defined in the skill. This file defines only the
step-level status above, so that a `fail` means the same thing wherever it appears.
