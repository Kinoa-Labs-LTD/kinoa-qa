# test-plan.md format

A `test-plan.md` is the reviewable intermediate. One file → N `### TC-<n>` cases → N
Allure TestOps cases (1:1). The deterministic validator
(`scripts/validate_test_plan.py`) parses this exact shape — do not deviate.

## Header (required)

```
# QA Test Plan — <service> / <capability>          (or "— <STORY-KEY> (business-only)")
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: <STORY-KEY> · target: <service>/<capability>@<ref> · generated: <YYYY-MM-DD> · spec-sha: <sha12 | none>
specs: <resolved | none (<reason>)>
```
> The `specs:` line is informational — it records whether specs were resolved; the validator infers spec-grounded vs business-only mode purely from whether a spec file is passed to it, not from this line.

## `## Acceptance Criteria` (required in business-only mode; optional in spec mode)

```
- AC-1: <one acceptance criterion, one line>
- AC-2: <…>
```
Every listed AC MUST be cited by ≥1 case `source: ac: AC-<n>` (validator `ac-coverage`).
Omit the whole section in spec-grounded mode unless you intend to cover the ACs too.

## `## Cases` (required)

```
### TC-<n> · <title>
- type: functional            # functional | negative | edge | regression | e2e | nonfunctional
- priority: P1                # P1 | P2 | P3
- source: scenario: <Requirement>/<Scenario>   # OR  ac: AC-<n>   OR  QA-added: <reason>
- preconditions: <state that must hold>
- steps:
  1. <action>
  2. <action>
- expected: <observable outcome>
```
Field order is fixed. `steps` are `  N. ` numbered lines. All six fields are required
(validator `required-fields`).

## `## Gaps` (required section header; may be empty)

```
- ⚠️ GAP: <Requirement> — <why no case>      # em dash U+2014
```
In spec mode, every requirement with no scenario MUST appear here (validator `gap-honesty`).

## Field → Allure TestOps V2 mapping (Step E)

| test-plan.md | TestOps create/update field |
|---|---|
| `### TC-n · <title>` | `name` = `"TC-n · <title>"` |
| `type` | tag `type-<type>` |
| `priority` | tag `priority-<p>` (no first-class severity field in V2; a Severity custom field is optional, only if `testops_get_project` confirms one) |
| `source` | `description` (+ the `tp-…` traceability tag) |
| `preconditions` | `precondition` |
| `steps` | `scenario.steps[{type:"body", body}]` (numbering stripped) |
| `expected` | `expectedResult` |
| — | tags always include `spec-derived` + the `tp-<slug>` traceability tag; `links[0]` → the Jira Story |

`## Gaps` lines are never pushed to TestOps.
