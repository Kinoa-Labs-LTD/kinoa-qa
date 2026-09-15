# test-plan.md format

A `test-plan.md` is the reviewable intermediate. One file → N `### TC-<n>` cases → N
Allure TestOps cases (1:1). The deterministic validator
(`scripts/validate_test_plan.py`) parses this exact shape — do not deviate.

**Source of truth.** The Jira Story, the Confluence PRD and any Figma mockup linked from
the Story are the authoritative tier: they decide what a case asserts. OpenSpec `spec.md`
files are *context only* — they may enrich a case, never own its `expected:`. A Confluence
PRD/HLD is never called a "spec" in this plugin; "spec" means an OpenSpec file.

## Header (required)

```
# QA Test Plan — <service> / <capability>          (or "— <STORY-KEY>")
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: <STORY-KEY> · target: <service>/<capability>@<ref> · generated: <YYYY-MM-DD>
prd: <resolved | none (<reason>)>
openspec: <<capability>@<sha12> | none | none (<reason>)>
design: <<backend> | none (<reason>)>
```
> The `openspec:` and `design:` lines are informational. `openspec: none` is the ordinary
> path — a service repo may simply have no OpenSpec files; only a spec the QA engineer
> explicitly asked for, or a resolver error, carries a `(<reason>)` and warns at the gate.
> The validator decides its OpenSpec-grounded checks purely from the `--openspec` arguments it is
> given, not from these lines. `design:` records which Figma backend answered (remote or
> the local desktop server), or why none did.

## `## Acceptance Criteria` (required — both modes)

```
- AC-1: <one acceptance criterion, one line>
- AC-2: <…>
```
Every case is derived from an AC, so this section is required whether or not an OpenSpec
file was resolved. ACs come from the Story, the PRD **and** the linked mockups — what a
mockup shows (an empty state, a label, an error variant) is written here like any other
business requirement. Every listed AC MUST be cited by ≥1 case `source: ac: AC-<n>`
(validator `ac-coverage`), with one exception: an AC named by an unresolved `## Conflicts`
line is exempt and MUST carry no case at all.

## `## Cases` (required)

```
### TC-<n> · <title>
- type: functional            # functional | negative | edge | regression | e2e | nonfunctional
- priority: P1                # P1 | P2 | P3
- source: ac: AC-<n>          # OR  QA-added: <reason>   — business grounding ONLY
- openspec-ref: <capability>#<Requirement>/<Scenario>   # optional, context enrichment
- design-ref: <fileKey>/<nodeId> — <frame name>         # optional, authoritative traceability
- preconditions: <state that must hold>
- steps:
  1. <action>
  2. <action>
- expected: <observable outcome>
```
Field order is fixed. `steps` are `  N. ` numbered lines. `type`, `priority`, `source`,
`preconditions`, `steps` and `expected` are required (validator `required-fields`);
`openspec-ref` and `design-ref` are optional.

- **`source:`** may cite business grounding only — `ac: AC-<n>` or `QA-added: <reason>`.
  There is no `scenario:` source and no `design:` source: a spec may not own a case, and a
  mockup enters through the AC list rather than as a source kind of its own.
- **`openspec-ref:`** points at the OpenSpec scenario that enriched the case. Spec text may
  shape `preconditions` and `steps`; it may never decide `expected`. Qualify the reference
  as `<capability>#<Requirement>/<Scenario>` whenever more than one OpenSpec file is in the
  bundle; a single-spec run may write `<Requirement>/<Scenario>` unqualified.
- **`design-ref:`** points at the Figma frame behind a mockup-derived AC. Unlike a spec, a
  mockup IS a business requirement, so a `design-ref` case may assert what the frame shows.
  It is validated **syntactically only** — the validator is offline and never calls Figma —
  and it may only accompany an `ac:` source.

## `## Conflicts` (required section header; may be empty)

```
- ⚠️ CONFLICT: <AC-n | —> · <source>: <claim> vs <source>: <claim>[ vs <source>: <claim> …] — <what was not done>
  → resolved: <business wins | spec wins, AC updated>      # added by the QA engineer
```
`vs <source>: <claim>` repeats: **two or more** sides on one line, one segment per
disagreeing source. A three-way disagreement is ONE line naming all three — never split
across lines, never trimmed to two sides. Worked three-way example:

```
- ⚠️ CONFLICT: AC-2 · story: a download link is valid for 7 days vs prd: an export file is retained for 24 hours vs design: the "Export · Ready" frame reads "This link expires in 30 days." — no case was generated for AC-2; Story, PRD and mockup are equal business sources and the plugin picks no winner
```

Each `<source>` is one of `story` / `prd` / `design` / `openspec`, each named at most once
per line (em dash U+2014 before the consequence). The plugin **surfaces** a contradiction,
it never resolves one: it picks no winner and never pre-fills `→ resolved:`. Story, PRD and
mockup have no precedence between one another; a source that merely ADDS detail the others
omit is an extra AC, not a conflict.

A contradicted AC yields **no case at all** until the conflict is annotated — nothing
half-true reaches the plan. An unresolved conflict makes the validator exit **2 (HOLD)**:
the plan is structurally valid and is still presented at the human gate (conflicts first),
but the TestOps upsert refuses to run. The QA engineer annotates `→ resolved: …` in this
file and Step C re-runs. The annotation must read `business wins` or `spec wins, AC updated`
(trailing detail after an em dash or colon is allowed); the validator FAILs any other text, so
a placeholder like `→ resolved: TBD` cannot turn a HOLD into a PASS. A plan with **no**
`## Conflicts` header at all FAILs (exit 1).

## `## Gaps` (required section header; may be empty)

```
- ⚠️ GAP: <Requirement> — <why no case>                          # requirement-level
- ⚠️ GAP: <Requirement>/<Scenario> — <why no case>               # scenario-level
```
Every requirement with no scenario, and every spec scenario covered by no case, MUST appear
here (validator `gap-honesty`). Spec coverage itself is advisory: an uncovered scenario is a
Gap or a Conflict, never a failing `scenario-coverage`. A scenario named in an **unresolved**
`## Conflicts` line is therefore exempt from `gap-honesty` — the contradiction is already
surfaced — exactly as its AC is exempt from `ac-coverage`; once the conflict is annotated the
exemption is gone and the scenario needs its case or its Gap line.

## Field → Allure TestOps V2 mapping (Step E)

| test-plan.md | TestOps create/update field |
|---|---|
| `### TC-n · <title>` | `name` = `"TC-n · <title>"` |
| `type` | tag `type-<type>` |
| `priority` | tag `priority-<p>` (no first-class severity field in V2; a Severity custom field is optional, only if `testops_get_project` confirms one) |
| `source` | `description` (+ the `tp-…` traceability tag) |
| `openspec-ref` / `design-ref` | `description` (when present) |
| `preconditions` | `precondition` |
| `steps` | `scenario.steps[{type:"body", body}]` (numbering stripped) |
| `expected` | `expectedResult` |
| — | tags always include `qa-generated` + the `tp-<slug>` traceability tag, plus `openspec-context` when the case has an `openspec-ref` and `design-backed` when it has a `design-ref`; `links[0]` → the Jira Story |

`## Gaps` and `## Conflicts` lines are never pushed to TestOps.

## Migration note

This format is a breaking change. A `test-plan.md` written before it — `source: scenario:`
cases, no `## Acceptance Criteria`, no `## Conflicts` header — is **rejected** by the
validator, not upgraded in place: the missing `## Conflicts` header is what makes an old
plan detectable. Delete it and regenerate from Step B. Nothing had been upserted when this
landed, so no TestOps case carries the old vocabulary. From the first real upsert onward the
format is frozen: changing a case's `source:` re-keys its `tp-` tag and strands the case
already in TestOps.
