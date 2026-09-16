# testops-sync.md — Step E (writes; only after the human gate)

Uses the Allure TestOps MCP. `project_id` / `project_name` from `config.json` (resolve
once via `testops_get_project` on `project_name` "KINOA" and cache it).

Step E runs in this order and stops at the first refusal:

```
re-run the validator  →  resolve the custom fields  →  abort if anything is missing
→  three by-value lookups  →  check_field_values  →  abort if not ok (unverified values
   pass as warnings under --allow-unverified-fields)
→  build payloads  →  update by verified id | reconcile by Story + target
```

## Gate 0 — nothing is written until both pre-flights pass

### Gate 0a — re-run the validator

Step E starts by re-running `scripts/validate_test_plan.py` on the reviewed
`test-plan.md` (the human may have edited it at the Step D gate):

- **exit 0 (PASS)** → proceed to Gate 0b.
- **exit 1 (FAIL)** → abort; report the failing checks. Nothing is written.
- **exit 2 (HOLD)** → **abort**. The plan is structurally valid but carries unresolved
  `## Conflicts` lines. Name every unresolved conflict from the report's
  `unresolved_conflicts` back to the QA engineer and tell them to annotate each one
  `→ resolved: <business wins | spec wins, AC updated>` in the file and re-run Step C.
  A contradicted acceptance criterion has no case yet, so upserting a HOLD plan would
  push a knowingly incomplete suite. No case is created or updated.

### Gate 0b — check the custom-field values

A `Story`, `Component` or `Feature` value that does not already exist in the project makes
Allure fail the whole creation **silently**. This gate is the only thing between a typo and
a lost batch, so it runs before the first payload is built.

**What the check can and cannot prove.** There is no API that lists a custom field's values:
`testops_get_project(expand=["custom_fields"])` returns field *names* only. The only mechanism
is a by-value case search, so the lookup answers "does an existing test case use this value",
not "does this value exist in the project". A hit proves the value is in use, hence valid. Zero
hits proves only that no case uses it — a value that is legitimately new is indistinguishable
from a typo. The gate therefore aborts by default and says what it actually checked.

1. Resolve the four values with `scripts/testops_fields.py`:

   ```python
   resolve_custom_fields(config, *, story_key, story_title,
                         story_field=None, component=None, feature=None)
   # -> {"fields": {"Suite","Story","Component","Feature"}, "missing": [...], "errors": [...]}
   ```
   A `--story-field` / `--component` / `--feature` flag beats the `testops.custom_fields.*`
   default in `config.json`; those defaults ship **empty** on purpose, so a run with no flags
   reaches step 2 and aborts. `story_title` is the `title:` field of the plan header (see
   `test-plan-format.md`), read from the reviewed `test-plan.md` on disk — never from Step A's
   memory and never re-fetched from Jira, so a Step E re-run in a fresh session composes the
   same `Suite` = `[<STORY-KEY>] <story title>`.

2. **`missing` non-empty → abort.** Print `errors` verbatim; each names the field and the flag
   or config key that would supply it. Nothing is looked up and nothing is written. An unset
   value is never guessed or defaulted.

3. One by-value lookup per field in `VERIFIED_FIELDS` = `("Story", "Component", "Feature")`:

   ```json
   {"projectId": 1, "aql": "cf[\"Component\"] = \"Game-Settings\"", "expand": ["custom_fields"]}
   ```
   `Suite` is **never looked up** — Allure creates Suite values on the fly.

4. Feed the three results in, keyed by field name:

   ```python
   check_field_values(fields, lookups, project_name="KINOA", allow_unverified=False)
   # -> {"ok": bool, "errors": [...], "warnings": [...], "checked": [...]}
   ```
   `lookups[<field>]` is whatever `testops_find_testcases` returned — a count, the list of
   cases, or the response dict. Any hit passes the field; zero hits, an empty list or a field
   with no result at all is *unverified*. `allow_unverified=True` — set it from
   `--allow-unverified-fields` — moves every unverified field from `errors` to `warnings`,
   leaving `ok` true.

5. **`ok` is false → abort**, printing each error, which names the offending field and value
   and says what was checked: `Story 'Templte' — no existing test case in project KINOA uses
   this value. If it exists in Allure but is unused, re-run with --allow-unverified-fields.`
   No case is created or updated; fix the typo, or create the value in Allure, and re-run Step E.

6. **`ok` is true → proceed**, printing every `warnings` entry to the QA engineer first. A
   warning means that field was pushed unverified.

### `--allow-unverified-fields`

Downgrades Gate 0b's by-value check from an abort to a warning. It does **not** skip the check:
the three lookups still run, a hit still passes silently, and every unverified value is named in
the Step E output before the first write.

Use it when — and only when — the value was just created in Allure and no test case uses it yet,
which is exactly the case the lookup cannot distinguish from a typo. Everything else the gate
does is unaffected: step 2's unset-value abort is not overridable, and a genuinely wrong value
still fails the creation silently in Allure, which is what the flag trades away.

The script is pure and stdlib-only: the orchestrator performs the MCP lookups, the script
decides. No network in `testops_fields.py`.

## Build the payload

For each `### TC-<n>` case, build the body with `scripts/testops_payload.py`:

```python
case_to_payload(case, *, story, service, capability, custom_fields)
```

`story` is the Jira key; `custom_fields` is the `fields` dict Gate 0b checked. There is no
`jira_base_url` parameter — nothing in the payload is a URL. The result carries
`name, description, precondition, expectedResult, status, workflow, issues, customFields,
scenario.steps[], tags[]`. There is no identity tag: `tags` is exactly `["qa-generated"]`, and
a case is addressed by its assigned Allure id (`allure-id:` in the plan), never by a value
derived from its content.

| payload key | value |
|---|---|
| `name` | the case title — the `TC-<n>` prefix is stripped |
| `description` | the case `purpose:` sentence, plus a `Provenance: openspec-ref: …; design-ref: …` line when either is present, plus the target marker as the last line |
| `precondition` | `preconditions:`, newline-separated |
| `expectedResult` | the case-level `expected:` |
| `status` / `workflow` | `"Draft"` / `"Manual Kinoa"` — module constants; `testLayer` is never sent |
| `issues` | `[{"name": "Kinoa-Allure", "value": "<STORY-KEY>"}]` — there is **no** `links` array. **Load-bearing**: it is the only way to find a case whose assigned id was lost, so the builder raises on a blank or missing `story` rather than emitting an unfindable case |
| `customFields` | `Suite`, `Story`, `Component`, `Feature` in that order, each `{name, value}` |
| `scenario.steps[]` | one `{"type": "body", "body": …}` per step, with exactly one `expected_body` in `expectedResultSteps` |
| `tags[]` | `qa-generated`, nothing else |

A missing or blank custom-field value raises at build time rather than producing a half
payload — the builder is handed the four verified values or it is not called.

```json
{
  "projectId": 1,
  "name": "Project selection dropdown populates with all accessible destination projects",
  "description": "Verify that the Destination Project dropdown lists every accessible project.\nProvenance: openspec-ref: export#Export/Project list; design-ref: aB3/12:44 — Export modal\nTarget: service=in-app-templates; capability=export",
  "precondition": "The user has access to 5 destination projects.\nThe user is on the In-App Template list page.",
  "expectedResult": "All 5 destination projects are listed and the source project is not.",
  "status": "Draft",
  "workflow": "Manual Kinoa",
  "issues": [{ "name": "Kinoa-Allure", "value": "KING-20326" }],
  "customFields": [
    { "name": "Suite",     "value": "[KING-20326] Export of In-App template to a different project" },
    { "name": "Story",     "value": "Template" },
    { "name": "Component", "value": "Game-Settings" },
    { "name": "Feature",   "value": "In-Apps" }
  ],
  "scenario": {
    "steps": [
      {
        "type": "body",
        "body": "Navigate to the In-App Template list page.",
        "expectedResultSteps": [{ "type": "expected_body", "body": "The template list is visible." }]
      }
    ]
  },
  "tags": ["qa-generated"]
}
```

## The target marker

`issue = "<STORY-KEY>"` returns every case of the Story — the plugin writes one plan per
`--target`, so that set spans targets. The payload therefore records its own target as the
last line of `description`:

```
Target: service=<service>; capability=<capability>
```

Both values are slugified (lower-case, non-alphanumerics collapsed to `-`), so
`--target "In App Templates/Export / Import"` writes
`Target: service=in-app-templates; capability=export-import`. Build it with
`testops_payload.target_marker(service, capability)` and read it back with
`testops_payload.parse_target(description)`, which returns the `(service, capability)` pair or
`None` when the description carries no marker. Reconciliation slugifies its own target the same
way and compares the pair — never the raw strings.

A case with no marker is a case this plugin did not write, or wrote before this format: it is
**never** treated as a match. It is reported to the QA engineer and left alone.

## Tag vocabulary

| tag | when |
|---|---|
| `qa-generated` | **always** — the only fleet-level handle for finding or bulk-rolling-back plugin-authored cases |

`qa-generated` is the **whole** vocabulary. `type-*` and `priority-*` are **retired** — they
duplicated real Allure fields. `openspec-context`, `design-backed` and the older unconditional
`spec-derived` are **retired** too: provenance rides as the `Provenance:` line on `description`.
The `tp-<slug>-<digest>` traceability tag is **retired as well** — identity is now the assigned
Allure case id, not a hash of the case's content, three sixths of which the LLM rewrites on
every regeneration. Write no AQL filter against any retired tag.

`## Gaps` and `## Conflicts` lines are never pushed to TestOps.

## Upsert (per case) — update by verified id, or reconcile

Identity is **assigned, not derived**. The Allure case id lives in the plan as the case's first
field, `- allure-id: <id>` (see `test-plan-format.md`). Its presence decides the path:

```
allure-id present  →  read the case back  →  verify  →  testops_update_testcase(id=…)
allure-id absent   →  reconcile by Story + target  →  human confirms  →  create
```

### The id is present — verify before updating

1. Read the case back by its id — `testops_find_testcases(projectId, aql='id = <allure-id>',
   expand=["tags","customFields","issues"])`, or the equivalent single-case read.
2. **Refuse to update unless the case carries the `qa-generated` tag AND the same
   `<STORY-KEY>` in `issues`.** A stale, hand-edited or copy-pasted id would otherwise
   overwrite a human-authored case — strictly worse than the duplication this protocol exists
   to stop. On a mismatch: write nothing for that case, name the case id, the tag and the Story
   it actually carries, and tell the QA engineer to correct or remove the `allure-id:` line.
3. Both checks pass → `testops_update_testcase(id=<allure-id>, **payload)`. The `allure-id` is
   never part of the payload body; it is the address, not a field.
4. **The id no longer exists in TestOps** (deleted, or a different project) → this is a
   degradation, not a crash. Report `allure-id <id> for TC-<n> no longer exists in project
   KINOA`, treat that case as **unidentified**, and let it fall through to reconciliation below
   with the rest. Never create silently in its place.

### The id is absent — reconcile, never create blind

Absence is the ordinary first-run state. It is also what a regeneration leaves behind for a
case Step B could not carry forward, so it must not mean "create". See
"Reconciliation" below: one scoping lookup, a proposed mapping at the **reconciliation gate**
(a second human stop, inside Step E), and a create only for what the QA engineer confirms is new.

### After a create

Take the returned case id and write it back into the plan at the stable path
`~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>.test-plan.md` with
`scripts/plan_writer.py`:

```python
insert_allure_id(plan_text, case_id, allure_id)   # case_id is "TC-<n>"
```

It inserts `- allure-id: <id>` as the first field under that case's heading and leaves every
other byte of the file identical; it raises on a non-positive-integer id, an unknown case, or a
case that already has an id. Write the file back after each create, not once at the end — a run
interrupted halfway then still carries the ids it did assign, and the next run updates those
instead of duplicating them.

A partial failure needs no rollback: re-run resumes — the cases that landed now carry ids and
are updated, the rest reconcile.

## Reconciliation — every case that has no verified id

Reconciliation runs once per Step E, for the whole set of unidentified cases together, not per
case.

### 1. One scoping lookup

```json
{"projectId": 1, "aql": "issue = \"KING-20326\"",
 "expand": ["tags", "customFields", "issues", "description"]}
```

The AQL field is **`issue`, singular**. `issues = …` is not a field and errors; `issues` is only
the payload key and an `expand` option. One call per Step E, never one per case.

### 2. Narrow to this target

The Story's cases span every `--target` ever pushed for it. Keep only the cases whose
`description` carries this run's target marker — `parse_target(description)` equal to this run's
slugified `(service, capability)` — and which carry the `qa-generated` tag. Everything else
belongs to another target or to a human, and is out of scope: not a match candidate, not an
orphan, not reported as either.

### 3. The reconciliation gate — propose a mapping (inside Step E)

This is a **second human stop**, distinct from the Step D gate and after it: Step D has already
closed on the merge report, and reconciliation only runs once Step E's Gate 0a/0b have passed
and the per-id read-backs are done. Show the QA engineer every unidentified plan case against every in-scope existing case, with a
proposed action:

```
TC-2  Duplicate template name is rejected
      → update  #12907  "Duplicate template name is rejected"        (exact title match)
TC-5  Export fails when the destination project is archived
      → create  (no existing case in this target matches)
TC-7  Project dropdown lists accessible projects
      → AMBIGUOUS: #12903 "Project dropdown populates" and
                   #12911 "Project dropdown lists projects"          — choose, or skip
```

A proposal is a proposal. **Nothing is written until the QA engineer confirms the mapping**,
case by case or as a whole.

### 4. Ambiguity is never auto-resolved

Two plan cases plausibly matching one existing case, or one plan case plausibly matching two,
is reported and left to the human. The plugin does not rank, score or pick the first hit — a
wrong pick silently overwrites a real case and loses its history. An ambiguity the QA engineer
does not resolve means that case is **skipped**: neither updated nor created.

### 5. Refusal — no unconfirmed write, ever

The refusal is scoped to **any** unidentified case, not to a plan that is wholly without ids.
A MIXED plan — some cases carried their ids forward, one or two came back unmatched — is the
ordinary regeneration outcome and is fully inside the refusal.

| Run | ≥1 unidentified case, ≥1 in-scope case | Step E |
|---|---|---|
| Attended | yes | Write **nothing** — no create, no update, for **any** case in the plan, identified or not — until the QA engineer confirms the mapping at the reconciliation gate (§3). |
| Unattended (no confirmation possible) | yes | **MUST abort.** Print the full proposed mapping and the orphan list, write nothing, exit non-zero. |
| Either | no in-scope case (first run for this target) | Proceed: nothing to map onto, every case is a create. |
| Either | no unidentified case (every case carries a verified id) | Proceed: update by id, no reconciliation gate. |

"Unattended" means any run in which no QA engineer can answer the reconciliation gate — a
scheduled, piped, CI or subagent-driven invocation included. This is a **hard refusal, not
advice**: an unattended run must never create for an unidentified case, and must never fall
back to "create because no match was found". A reworded case the human was meant to map would
otherwise become a duplicate of the case it was supposed to update.

A target whose scoping lookup returns **no** in-scope case is the ordinary first run: there is
nothing to map onto, so every case is a create and Step E proceeds normally.

### 6. Orphans are listed and never touched

Any in-scope existing case that no plan case maps to is reported under **"in TestOps, not in
this plan"**, with its id and name:

```
in TestOps, not in this plan:
  #12899  Template export honours the read-only flag
```

The plugin **never deletes and never mutes** an orphan, and never edits it to mark it stale.
An orphan is usually a case whose plan entry was intentionally dropped, and deciding its fate
is the QA engineer's, in Allure. The list is information, not an action.

## `--dry-run`
Do NOT call create/update. Gate 0a and Gate 0b still run — a `--dry-run` that skipped the
field pre-flight would preview a batch that cannot land. The **read-only** reads still run too:
the per-id read-back and the one scoping lookup, so the preview is the real mapping and not a
guess. Print, per case: the intended action (`update #<id>` | `create` | `AMBIGUOUS` | `skipped
— <reason>`), the id it would address, and the payload `name`; then the orphan list.

`--dry-run` **never refuses**. The no-ids-against-a-non-empty-target refusal above is a refusal
to *write*, and a dry run writes nothing — including into the plan file, so no `allure-id:` is
inserted. It reports the mapping the QA engineer would be asked to confirm and exits 0.

## Degradation
- TestOps unreachable → the reviewed `test-plan.md` is already on disk; stop and tell the
  QA engineer to re-run Step E later. Nothing is lost.
- A custom-field value is unset (no flag, empty config default) → abort at Gate 0b naming the
  field and the flag that supplies it. Nothing is looked up, nothing is written.
- No existing case uses a `Story`, `Component` or `Feature` value → abort at Gate 0b naming the
  field and the value, and saying that is what was checked. A typo would have made Allure fail
  the whole creation silently.
- The value exists in Allure but no case uses it yet → same abort; re-run with
  `--allow-unverified-fields` to push it as a recorded warning instead.
- An `allure-id` no longer exists in TestOps → report it, treat that case as unidentified and
  let it reconcile with the rest. Never create silently under the missing id.
- An `allure-id` resolves to a case that lacks `qa-generated` or carries a different Story →
  that case is skipped, nothing is written for it, and the mismatch is named. The plugin never
  overwrites a case it cannot prove it wrote.
- The plan has ≥1 unidentified case and the target already has ≥1 in-scope case — a mixed plan,
  not only a plan with no ids at all → refuse to write anything for **any** case, print the
  proposed mapping and the orphans, and exit non-zero, unattended runs included (§5).
- A mapping is ambiguous → the case is skipped and both candidates are named; never auto-picked.
- A Story case carries no target marker → out of scope for this run: not a match candidate and
  not an orphan. It is reported once, and left alone.
- `priority` has no first-class TestOps field and no longer rides as a tag. It stays in
  `test-plan.md` only; do not invent a `Severity` custom field for it — the four fields in
  `CUSTOM_FIELD_ORDER` are the whole set this plugin writes.
