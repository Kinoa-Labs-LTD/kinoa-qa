# testops-sync.md — Step E (writes; only after the human gate)

Uses the Allure TestOps MCP. `project_id` / `project_name` from `config.json` (resolve
once via `testops_get_project` on `project_name` "KINOA" and cache it).

Step E runs in this order and stops at the first refusal:

```
re-run the validator  →  resolve the custom fields  →  abort if anything is missing
→  three by-value lookups  →  check_field_values  →  abort if not ok (unverified values
   pass as warnings under --allow-unverified-fields)
→  build payloads  →  upsert
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
scenario.steps[], tags[]`, and the `tp-<slug>` traceability tag inside `tags`.

| payload key | value |
|---|---|
| `name` | the case title — the `TC-<n>` prefix is stripped |
| `description` | the case `purpose:` sentence, plus a `Provenance: openspec-ref: …; design-ref: …` line when either is present |
| `precondition` | `preconditions:`, newline-separated |
| `expectedResult` | the case-level `expected:` |
| `status` / `workflow` | `"Draft"` / `"Manual Kinoa"` — module constants; `testLayer` is never sent |
| `issues` | `[{"name": "Kinoa-Allure", "value": "<STORY-KEY>"}]` — there is **no** `links` array |
| `customFields` | `Suite`, `Story`, `Component`, `Feature` in that order, each `{name, value}` |
| `scenario.steps[]` | one `{"type": "body", "body": …}` per step, with exactly one `expected_body` in `expectedResultSteps` |
| `tags[]` | `qa-generated` + `tp-<slug>-<digest>`, nothing else |

A missing or blank custom-field value raises at build time rather than producing a half
payload — the builder is handed the four verified values or it is not called.

```json
{
  "projectId": 1,
  "name": "Project selection dropdown populates with all accessible destination projects",
  "description": "Verify that the Destination Project dropdown lists every accessible project.\nProvenance: openspec-ref: export#Export/Project list; design-ref: aB3/12:44 — Export modal",
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
  "tags": ["qa-generated", "tp-king-20326-export-templates-9f2c1ab4de"]
}
```

## Tag vocabulary

| tag | when |
|---|---|
| `qa-generated` | **always** — the only fleet-level handle for finding or bulk-rolling-back plugin-authored cases |
| `tp-<slug>-<digest>` | **always** — the traceability tag / idempotency key; a re-run finds the case by it, so it cannot be dropped |

Nothing else is emitted. `type-*` and `priority-*` are **retired** — they duplicated real
Allure fields. `openspec-context`, `design-backed` and the older unconditional `spec-derived`
are **retired** too: provenance now rides as the `Provenance:` line on `description`, because
`tp-` is an opaque hash and would otherwise leave OpenSpec and mockup provenance absent from
TestOps entirely. Write no AQL filter against any retired tag.

`## Gaps` and `## Conflicts` lines are never pushed to TestOps.

## Idempotent upsert (per case)
1. `ttag = testops_payload.traceability_tag(story, service, capability, source, title, case_type)` — `title` = the case's TC title, `case_type` = the case's `type:` field; required so two cases citing the same `source` scenario (functional + negative) don't collide onto one TestOps case.
2. `testops_find_testcases(projectId, aql='tags = "<ttag>"', expand=["tags"])`.
3. **Found (≥1):** `testops_update_testcase(id=<first hit id>, **payload)`.
   **None:** `testops_create_testcase(projectId=<pid>, **payload)`.
4. Take the returned case id → write `@allure.id=<id>` back into the `test-plan.md` case
   header comment (so the file records the TestOps link).

Because the key is a tag derived from the case's identity (see "The key is frozen from
the first real upsert" below), re-running a Story with unchanged `source:`, title and
`type:` updates in place — 0 duplicates. A partial failure needs no rollback: re-run
resumes (found→update the landed ones, create the rest).

## `--dry-run`
Do NOT call create/update. Gate 0a and Gate 0b still run — a `--dry-run` that skipped the
field pre-flight would preview a batch that cannot land. Instead print, per case: the intended
action (create|update), the `ttag`, and the payload `name` — the QA preview of Step E.

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
- `priority` has no first-class TestOps field and no longer rides as a tag. It stays in
  `test-plan.md` only; do not invent a `Severity` custom field for it — the four fields in
  `CUSTOM_FIELD_ORDER` are the whole set this plugin writes.

## The key is frozen from the first real upsert

`traceability_tag` hashes `story|service|capability|source|title|case_type`. Changing a
case's `source:` (or its title or type) therefore produces a **different** `tp-` tag: the
re-run finds no match, creates a second TestOps case, and the case written under the old
key is stranded — orphaned, still green, and invisible to the new AQL filter.

This is prospective, not a cleanup instruction: project KINOA holds zero plugin-authored
cases today, so the vocabulary and `source:` changes made here are the first keys ever
written. From the first non-dry-run upsert onward the format is frozen — a later `source:`
edit needs a deliberate migration (delete or re-tag the old case), never a silent re-run.
