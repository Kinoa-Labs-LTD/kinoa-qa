# generation.md — deriving cases from the SoT bundle

Input: the SoT bundle `{ story, acceptance, prd?, specs[] }` assembled in Step A.
Output: exactly one `test-plan.md` (per `references/test-plan-format.md`) + nothing else.

## Source discipline (which `source:` to use)
- A case grounded in a **spec scenario** → `source: scenario: <Requirement>/<Scenario>`
  (the heading text, verbatim). Only when a spec was resolved.
- A case grounded only in a **business requirement** → `source: ac: AC-<n>`, and that
  `AC-<n>` MUST be listed in `## Acceptance Criteria` (derive the AC list from the Story
  description/acceptance-criteria + PRD).
- A genuinely QA-motivated case with no direct scenario/AC → `source: QA-added: <reason>`
  (use sparingly; it is not an escape hatch for laziness).

## The five QA-lens rules
1. **Functional (happy path):** one case per spec scenario / per acceptance criterion,
   asserting the stated behavior.
2. **Negative / edge:** where a scenario or AC implies a boundary or invalid input
   (a limit, a required field, an auth failure), add a `type: negative` or `type: edge`
   case — the boundary must be implied by the source text, never invented.
3. **Regression (contract):** if a resolved spec/PRD indicates a shared contract change
   (an API payload, an event schema, a shared response), add a `type: regression` case
   asserting backward compatibility. (Spec mode; skip if no contract signal.)
4. **End-to-end:** only when the SoT describes a cross-component flow the Story spans;
   otherwise omit. (Business-only runs rarely warrant e2e — prefer functional/negative.)
5. **Nonfunctional:** only when the source text states an observable nonfunctional
   requirement (a timeout, a rate limit with an asserted response). Never infer silently.

## No fabrication (hard rule)
An untestable or scenario-less requirement is NOT turned into a case. In spec mode, name
each scenario-less requirement in a `## Gaps` `- ⚠️ GAP: <Requirement> — <reason>` line.
Do not invent an `expected` you cannot ground in the source.

## Degradation
- **No spec resolved:** run in business-only mode — derive `## Acceptance Criteria` from
  Story + PRD, source every case with `ac:`; set header `specs: none (<reason>)`; expect
  coarser cases. Rules 3–5 apply only where the PRD explicitly states the behavior.
- **No PRD:** proceed on the Story alone; the acceptance criteria come from the Story's
  own acceptance-criteria/description fields.

## Self-check (before returning)
State that you expect `python3 scripts/validate_test_plan.py <plan> [--spec <spec>]` to
report `RESULT: PASS` on your output. This is a self-check, not a substitute for Step C
actually running the validator.
