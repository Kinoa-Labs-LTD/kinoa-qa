# generation.md — deriving cases from the SoT bundle

Input: the SoT bundle — authoritative `{ story, acceptance, prd?, designs[] }` plus
contextual `{ openspecs[] }` — assembled in Step A.
Output: exactly one `test-plan.md` (per `references/test-plan-format.md`) + nothing else.

## Carrying `allure-id:` forward (a regeneration is a merge, not a fresh write)

Step B may hand you a **`previous_plan`** — the plan this Story and target produced last
time, read from its stable path. When it is present, you are revising that plan, not
writing a new one:

- A case you **keep** — the same behaviour under test, however its title, `type:`,
  `source:` AC number or steps have been reworded or renumbered — MUST come back carrying
  the **same `- allure-id: <id>`, copied verbatim** from the previous plan, as the first
  field under its heading. That id is the TestOps case's assigned identity; dropping it
  creates a duplicate case on the next sync.
- A case you **genuinely replace** — a different behaviour under test, not a rewording —
  comes back with **no** `allure-id:`. Step E reconciles or creates it.
- **Never invent, guess, derive or renumber an id.** An id may only be copied from the
  case it belonged to in `previous_plan`. A case that had none in `previous_plan` gets
  none from you. If you cannot tell which previous case a new case corresponds to, omit
  the id — the human gate resolves it. A wrong id silently overwrites the wrong TestOps
  case, which is worse than a duplicate.
- Do not reorder or renumber `TC-<n>` handles to "match" the previous plan; the
  `allure-id:` is the identity, `TC-<n>` is only a plan-local handle.
- No `previous_plan` means the first run for this Story and target: no case carries an id.

Step B re-applies the unambiguous part of this mechanically (`plan_writer.merge_allure_ids`
matches identical titles), and the Step D gate shows the QA engineer which cases kept an id
and which are new. Your judgement is needed exactly where the title changed.

## Precedence (read this first)

The Jira Story, the Confluence PRD and any Figma mockup linked from the Story **decide**
what a case asserts. OpenSpec `spec.md` files only **enrich** — they carry no authority
over an outcome. Concretely:

- Every case is derived from an acceptance criterion. `source:` is `ac: AC-<n>` or
  `QA-added: <reason>`; there is no `scenario:` source and no `design:` source.
- OpenSpec text may shape `preconditions` and `steps`. It may **never** decide `expected`.
- Where a spec contradicts the business sources, write a `## Conflicts` line — never a
  chosen `expected`. See "Conflicts" below.

OpenSpec files are **optional by design**. A service repo may have none, and that is the
ordinary path, not a fallback and not a degradation: the header simply reads
`openspec: none` and nothing warns. Only a spec the QA engineer explicitly asked for
(`--target` / `--repo` / `--openspec-path`), or a resolver error, carries a reason and
warns at the gate.

## Source discipline (which `source:` to use)
- A case grounded in an **acceptance criterion** → `source: ac: AC-<n>`, and that `AC-<n>`
  MUST be listed in `## Acceptance Criteria`. Derive the AC list from the Story
  description/acceptance-criteria, the PRD **and** the linked mockups.
- A genuinely QA-motivated case with no direct AC → `source: QA-added: <reason>`
  (use sparingly; it is not an escape hatch for laziness).
- A case whose wording was enriched by an OpenSpec scenario additionally carries
  `openspec-ref: <capability>#<Requirement>/<Scenario>` (qualify with `<capability>#`
  whenever more than one OpenSpec file is in the bundle). This is traceability, not
  grounding: removing the spec would not change the case's `expected`.

## The five QA-lens rules
1. **Functional (happy path):** one case per acceptance criterion, asserting the stated
   behavior.
2. **Negative / edge:** where an AC implies a boundary or invalid input (a limit, a
   required field, an auth failure), add a `type: negative` or `type: edge` case — the
   boundary must be implied by the source text, never invented.
3. **Regression (contract):** if the PRD (or an OpenSpec file, as context) indicates a
   shared contract change (an API payload, an event schema, a shared response), add a
   `type: regression` case asserting backward compatibility, grounded in the AC that
   covers it. Skip if there is no contract signal.
4. **End-to-end:** only when the SoT describes a cross-component flow the Story spans;
   otherwise omit.
5. **Nonfunctional:** only when the source text states an observable nonfunctional
   requirement (a timeout, a rate limit with an asserted response). Never infer silently.

## Authoring conventions (how each case is written)

These are the house conventions for a normal manual TC. They decide the *wording* of a case;
the QA-lens rules above decide *which* cases exist. `references/test-plan-format.md` owns the
grammar — this section owns the content that goes in it.

| Field | Convention |
|---|---|
| `allure-id:` | Never authored and never invented. Copied verbatim from the same case in `previous_plan`, or absent. See "Carrying `allure-id:` forward". |
| title (`### TC-<n> · <title>`) | A clean behavioural statement of what the system does — `Project selection dropdown populates with all accessible destination projects`. Never a `TC-` prefix inside the title, never a bare feature name, never an imperative ("Check the dropdown"). |
| `purpose:` | **One** sentence beginning "Verify", stating what the case proves — `Verify that the Destination Project dropdown excludes the source project.` Not a restatement of the title and not a summary of the steps. |
| `preconditions:` | The state that must hold before step 1, as statements, one per line. Several statements are newline-separated continuation lines, not a comma list. |
| `steps:` | User-level actions — what a tester does in the product, not API calls or internal state. |
| `→ expected:` | Exactly one per step: the observable result of that step. No step without one, no step with two. |
| `expected:` | The overall pass condition for the case, not a repeat of the last step's expected result. |

Coverage style: prefer several focused cases over one mega-case — a case that verifies three
unrelated behaviours fails for three unrelated reasons and tells the reader nothing. Order the
cases happy path first, then the negative and edge cases the analysis surfaced.

## No fabrication (hard rule)
An untestable or unassertable requirement is NOT turned into a case. Name each
requirement with no scenario, and each OpenSpec scenario covered by no case, in a
`## Gaps` line (`- ⚠️ GAP: <Requirement> — <reason>` or
`- ⚠️ GAP: <Requirement>/<Scenario> — <reason>`). Do not invent an `expected` you cannot
ground in the business sources.

## Mockups — deriving ACs from `designs[]`

Each bundle entry `designs[{ fileKey, nodeId, frameName, context }]` is a **business
requirement**, equal to the Story and the PRD. Read the screenshot and design context and
write what the frame *shows* into `## Acceptance Criteria` exactly like a PRD-derived
criterion — an empty state, a button label, a disabled control, a validation message, an
error variant. There is no separate "design AC" list and no `design:` source kind.

- The case stays `source: ac: AC-<n>` and additionally carries
  `design-ref: <fileKey>/<nodeId> — <frame name>`, taken verbatim from the bundle entry.
- Unlike a spec, a mockup **may ground an `expected:`**: "the empty list shows *No
  campaigns yet*" is an assertable outcome because the frame is authoritative.
- A frame showing detail the Story simply **omits** is an **additional AC**, not a
  conflict — add it and test it.
- A frame that **contradicts** the Story or PRD text is a `## Conflicts` line with
  `design` as one side, and that AC yields **no case** until it is annotated (see below).
- **No fabrication still applies.** A frame with no testable state — a moodboard, a
  colour study, a layout with no behaviour — produces a `- ⚠️ GAP:` line, never an
  invented case. Do not assert pixel values, spacing or colours; assert observable
  behaviour and content.
- No mockup read (`design: none (<reason>)`) simply means no mockup-derived ACs. It is not
  an excuse to guess what a screen looks like.

## Conflicts (detect them; never resolve them)

A **conflict** is a direct contradiction: two sources state outcomes that cannot both be
true of the same behaviour. Emit one `## Conflicts` line per contradiction:

```
- ⚠️ CONFLICT: <AC-n | —> · <source>: <claim> vs <source>: <claim>[ vs <source>: <claim> …] — <what was not done>
```
Each `<source>` is one of `story` / `prd` / `design` / `openspec`. Use `—` in the first
field when the contradiction belongs to no listed AC. The `vs <source>: <claim>` segment
repeats — **two or more** sides, every disagreeing source named on the SAME line. Three
sources contradicting one another is one line with three segments, not two lines and not a
line that drops a side:

```
- ⚠️ CONFLICT: AC-2 · story: a download link is valid for 7 days vs prd: an export file is retained for 24 hours vs design: the "Export · Ready" frame reads "This link expires in 30 days." — no case was generated for AC-2; Story, PRD and mockup are equal business sources and the plugin picks no winner
```

Rules:

- **Never resolve a conflict in the plan.** Pick no winner, write no `expected` from
  either side, and **never pre-fill `→ resolved:`** — that annotation is the QA engineer's
  alone. Your job is to surface, not to arbitrate. The validator accepts only
  `business wins` or `spec wins, AC updated` there, so an invented annotation FAILs.
- **Inside the authoritative tier there is no precedence.** Story, PRD and mockup are
  equal; the plugin never arbitrates between them. Story vs PRD, Story vs mockup and PRD
  vs mockup are all conflict lines naming both sides with their artifact.
- **Spec vs business is also a conflict**, not a silent loss: write
  `openspec: <claim> vs <ac-side>: <claim>` rather than quietly dropping the spec text.
- **An ADDITION is not a conflict.** A PRD or mockup that states detail the Story simply
  omits is an *additional acceptance criterion* — add it to `## Acceptance Criteria` and
  test it. Only a direct contradiction counts.
- **A contradicted AC yields no case at all.** Write the conflict line and stop there;
  nothing half-true reaches the plan. That AC is exempt from `ac-coverage` while the
  conflict is unannotated, and a case citing it is a validation failure. Once the QA
  engineer annotates `→ resolved: …` and Step C re-runs, the case is generated from the
  winning source.
- **A spec scenario named in an unresolved conflict line needs no Gap line** — the conflict
  already reports it; name the scenario in the conflict text. Once the conflict is annotated
  the scenario needs its case or a `## Gaps` line like any other.
- The section header `## Conflicts` is **always** written, even when there is nothing to
  report (an empty section). A plan without it is rejected.

An unresolved conflict makes the validator exit **2 (HOLD)**: the plan still reaches the
human gate, but the TestOps upsert refuses to run until every line carries `→ resolved:`.

## Degradation
- **No OpenSpec file:** the ordinary path. Header `openspec: none`, no warning, cases
  sourced from the ACs exactly as they always are. A spec the QA engineer explicitly
  requested that failed to resolve is the exception: header `openspec: none (<reason>)`
  and a warning at the gate.
- **No PRD:** proceed on the Story (and mockups) alone; the acceptance criteria come from
  the Story's own acceptance-criteria/description fields. Header `prd: none (<reason>)`.

## Self-check (before returning)
State that you expect `python3 scripts/validate_test_plan.py <plan> [--openspec <spec.md>]` to
report `RESULT: PASS` **or** `RESULT: HOLD` on your output, and say which one and why.

- Wrote no `## Conflicts` line → expect PASS.
- Wrote any `## Conflicts` line → expect **HOLD (exit 2), and that is the correct outcome**.
  A HOLD here means the plan did its job. It is never a reason to resolve, reword, merge or
  drop a conflict line, or to pre-fill `→ resolved:`, in order to reach PASS.

Also state, when a `previous_plan` was given, how many of its cases you kept with their
`allure-id:` copied forward and which cases you replaced (and therefore returned without an
id). A kept case that came back without its id is a defect in your output.

`RESULT: FAIL` is the only outcome you must go back and fix. This is a self-check, not a
substitute for Step C actually running the validator.
