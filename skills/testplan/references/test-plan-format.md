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

story: <STORY-KEY> · title: <story title> · target: <service>/<capability>@<ref> · generated: <YYYY-MM-DD>
prd: <resolved | none (<reason>)>
openspec: <<capability>@<sha12> | none | none (<reason>)>
design: <<backend> | none (<reason>)>
images: <<n> read | <n> read (<k> failed: <reason>) | none | none (<reason>)>
scope: <e2e | story>
```
> `title:` is the Jira Story summary verbatim, on the same logical line as `story:`. It is
> required: Step E composes the `Suite` custom field as `[<STORY-KEY>] <story title>` by
> reading it back from this header, so a Step E re-run in a fresh session needs no Jira call.
> `scope:` is written only when the plan has one; omit the line entirely for a
> Story-scoped plan. It is the plan's **test scope** — "in-scope set" keeps its own meaning, the
> reconciliation set. It is optional, written on its own line, and takes exactly two values:
> `e2e` or `story`. **Absent means `story`**, so every plan written before this field stays
> valid; the default is applied by the consumer (the validator and Step E), never by the
> parser, so "this plan says `story`" and "this plan says nothing" stay distinguishable and a
> regeneration that drops the field is reported rather than silently demoting an e2e plan.
> Any other value — `E2E`, `integration`, an empty value — FAILs validation (`scope-valid`)
> naming the value and the allowed set. One run produces one kind of test.
> `scope:` is **never sent to TestOps as a payload field of its own.** It changes exactly two
> other values (see the mapping table below) and nothing else: `Suite`, `Story`, `Component`,
> `issues`, tags and the description are identical in both scopes.
> The `openspec:`, `design:` and `images:` lines are informational. `openspec: none` is the
> ordinary path — a service repo may simply have no OpenSpec files; only a spec the QA
> engineer explicitly asked for, or a resolver error, carries a `(<reason>)` and warns at the
> gate. The validator decides its OpenSpec-grounded checks purely from the `--openspec`
> arguments it is given, not from these lines. `design:` records which Figma backend
> answered (remote or the local desktop server), or why none did. `images: none` is
> likewise the ordinary path for a Story with no image attachment. `images: <n> read`
> means every image attachment was read; `images: <n> read (<k> failed: <reason>)` means
> some were read and some failed or were skipped — it never claims none were read when
> some were; `images: none (<reason>)` is reserved for when nothing at all could be
> read. Only the last two carry a `(<reason>)` and warn at the gate. The header is
> informational only — the validator does not parse it.

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
- allure-id: 12907           # optional, written back by Step E — never by the author
- type: functional            # functional | negative | edge | regression | e2e | nonfunctional
- priority: P1                # P1 | P2 | P3
- purpose: Verify <what this case proves>.   # one sentence, begins "Verify"
- source: ac: AC-<n>          # OR  QA-added: <reason>   — business grounding ONLY
- openspec-ref: <capability>#<Requirement>/<Scenario>   # optional, context enrichment
- design-ref: <fileKey>/<nodeId> — <frame name>         # optional, authoritative traceability
- image-ref: <attachment-id> — <filename>   # optional, authoritative traceability
- preconditions: <state that must hold>
  <a second state statement on its own line>
- steps:
  1. <action>
     → expected: <what the system does in response>
  2. <action>
     → expected: <what the system does in response>
- expected: <the overall pass condition>
```
Field order is fixed: `allure-id`, `type`, `priority`, `purpose`, `source`, `openspec-ref`,
`design-ref`, `image-ref`, `preconditions`, `steps`, `expected`. `type`, `priority`,
`purpose`, `source`, `preconditions`, `steps` and `expected` are required (validator
`required-fields`); `allure-id`, `openspec-ref`, `design-ref` and `image-ref` are optional.

- **`allure-id:`** is the **assigned** TestOps case identity and the **first** field under the
  case heading. It is written back by **Step E** after it creates the case, and by nothing
  else: the QA engineer never types it and the generation subagent never authors or invents
  one. **Its absence is the normal first-run state** — a plan whose cases have never been
  upserted carries no ids at all and is fully valid. On a regeneration Step B copies each
  surviving case's id forward verbatim; a case it genuinely replaces comes back without one.
  The validator checks the **shape** only (`allure-id-valid`): a present `allure-id` must be a
  positive integer, so a malformed id cannot reach Step E and address the wrong case. Whether
  the id still exists in TestOps is Step E's business — the validator is offline.

- **`### TC-<n> · <title>`** — the `TC-<n>` is a plan-local handle for review and for the
  `## Conflicts` / `## Gaps` cross-references. It is **not** part of the TestOps case name:
  only `<title>` is pushed. The title is a clean behavioural statement — e.g.
  `Project selection dropdown populates with all accessible destination projects`.
- **`purpose:`** is one sentence beginning "Verify", stating what the case proves. It becomes
  the TestOps `description`; it is not a restatement of the title and not a list of steps.
- **`preconditions:`** is the state that must hold before step 1. Several statements go on
  their own continuation lines and reach TestOps newline-separated.

### Per-step expected results

`steps` are `  N. <action>` numbered lines. Every step MUST carry **at least one**
`     → expected: <result>` line below it; how many more are allowed depends on the plan's
test scope:

- **Story scope** (`scope: story`, or no `scope:` line) — **exactly one** per step, no more and
  no less. A step with two FAILs the validator (`required-fields`) naming it:
  `step N has M expected results (exactly one is allowed)`.
- **`scope: e2e`** — a step **may carry several** `→ expected:` lines, written one under the
  other. Each becomes its **own `expected_body` block** in that step's `expectedResultSteps`,
  in the order written.

A step with **no** expected result FAILs under **both** scopes — `step N has no expected
result` — because a TestOps step body without an expected block asserts nothing. The
case-level `expected:` stays: it is the overall pass condition, not a repeat of the last step.

Worked example:

```
### TC-2 · Export is blocked when no destination project is selected
- type: negative
- priority: P2
- purpose: Verify that the Export action stays disabled until a destination project is chosen.
- source: ac: AC-3
- preconditions: The user has access to 5 destination projects.
  The user is on the In-App Template list page.
- steps:
  1. Click the Export button on any In-App template.
     → expected: The "Export In-App Template" modal opens with the Export button disabled.
  2. Select a destination project from the dropdown.
     → expected: The Export button becomes enabled.
- expected: Export is unavailable without a destination project and available once one is chosen.
```

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
- **`image-ref:`** points at the Story image attachment behind an image-derived AC. Like a
  mockup and unlike a spec, an image **may ground an `expected:`**. It is validated
  **syntactically only** — the validator never calls Jira — and it may only accompany an
  `ac:` source. The attachment id is one or more digits (leading zeros and `0` itself parse,
  unlike `allure-id`) and the filename may itself contain an em dash, so the value is
  matched, never split.

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

Each `<source>` is one of `story` / `prd` / `design` / `openspec` / `image`, each named at most once
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
| `allure-id` | **not sent in the body** — it is the update key: Step E calls `testops_update_testcase(id=<allure-id>)`. Absent → Step E reconciles, creates, and writes the assigned id back into this file |
| `### TC-n · <title>` | `name` = `"<title>"` — the `TC-n` prefix is **stripped** |
| `purpose` | `description` (plus a one-line provenance suffix naming `openspec-ref:` / `design-ref:` / `image-ref:` when present) |
| `type` / `priority` | not pushed — no `type-*` / `priority-*` tags |
| `source` | not pushed — it is provenance for the reader of the plan only |
| `design-ref` | not pushed as its own field — rides the provenance suffix on `description`, exactly as `image-ref` does |
| `image-ref` | not pushed as its own field — rides the provenance suffix on `description`, exactly as `design-ref` does |
| `preconditions` | `precondition` (newline-separated) |
| `steps` | `scenario.steps[]` — each step `{"type": "body", "body": "<action>", "expectedResultSteps": [{"type": "expected_body", "body": "<expected>"}]}`, numbering stripped; one `expected_body` per `→ expected:` line, in order — exactly one under Story scope, one or more under `scope: e2e` |
| `expected` | `expectedResult` — the case-level pass condition |
| `title:` header | `customFields.Suite` = `[<STORY-KEY>] <story title>`, composed from the header — never re-fetched from Jira |
| — | `customFields`: `Story` / `Component` / `Feature` from `--story-field` / `--component` / `--feature` or their `config.json` defaults (shipped empty) |
| `story:` header | `issues` = `[{"name": "Kinoa-Allure", "value": "<STORY-KEY>"}]` — there is **no** `links` array |
| `scope:` header | **not sent as a field.** It changes two values only: under `scope: e2e`, `customFields.Feature` = `"e2e scope"` and `status` = `"Review"`. Under `scope: story` or an absent `scope:`, `Feature` comes from the caller as before and `status` stays `"Draft"` |
| — | `status` = `"Draft"`, or `"Review"` under `scope: e2e`; `workflow` = `"Manual Kinoa"`; `testLayer` is never sent |
| — | `tags` = `qa-generated`, and nothing else |

**Tag policy: `qa-generated` only.** It is the only fleet-level handle for finding or
bulk-rolling-back plugin-authored cases. No tag carries identity: a case is found by its
assigned `allure-id`, never by a tag derived from its content. Everything else is gone:
`type-*` and `priority-*` duplicated real Allure fields, and `openspec-context` /
`design-backed` are replaced by the provenance suffix on `description`.

`Story`, `Component` and `Feature` values MUST already exist in the project — Allure rejects an
unknown value **silently** and the whole creation fails — so Step E checks them before any write
and aborts naming the offending value. The check is a by-value case lookup: it can prove a value
is *in use*, never that it exists, so a value created in Allure that no case uses yet is passed
with `--allow-unverified-fields` (see `testops-sync.md`, Gate 0b). `Suite` is exempt: Allure
creates Suite values on the fly.

`## Gaps` and `## Conflicts` lines are never pushed to TestOps.

## Migration note

This format is a breaking change, twice over. A `test-plan.md` written before it — `source:
scenario:` cases, no `## Acceptance Criteria`, no `## Conflicts` header, no `purpose:`, steps
as bare numbered lines with no `→ expected:` — is **rejected** by the validator, not upgraded
in place. The parser still reads an old-shape plan (a bare step parses with no expected result)
precisely so the validator can FAIL it naming both reasons — the missing `purpose:` and the
steps with no expected result — rather than crash. Delete the plan and regenerate from Step B;
pre-existing plans are regenerated, never hand-patched. Nothing had been upserted when this
landed, so no TestOps case carries the old vocabulary or the old payload shape. From the first
real upsert onward a case's identity is its assigned `allure-id:`, so editing `source:`, the
title or the `TC-n` prefix re-keys nothing and strands nothing — the id is carried forward,
never re-derived.
