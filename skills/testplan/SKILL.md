---
name: testplan
description: Build a validator-checked QA test plan from a Jira Story (+ optional Confluence PRD + optional linked Figma mockups + optional service-repo OpenSpec specs) and, after a human gate, idempotently upsert the cases into Allure TestOps. Invoke for `/kinoa-qa:testplan <STORY-KEY>`.
---

# testplan — Jira Story → Allure TestOps cases

`/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>]
[--openspec-path <dir>] [--story-field <value>] [--component <value>] [--feature <value>]
[--allow-unverified-fields] [--dry-run]`

"Spec" in this plugin means an OpenSpec `spec.md` file generated from service-repo code;
a Confluence PRD/HLD is never called a "spec" here.

## Source of truth

The **authoritative tier** is the Jira Story + the Confluence PRD + any Figma mockup
linked from the Story. Those three decide what a case asserts, and they have **no
precedence between one another**. OpenSpec `spec.md` files are **supporting context
only**: they may shape a case's `preconditions` and `steps`, never its `expected`. A
mockup, unlike a spec, IS a business requirement — what a frame shows becomes an
acceptance criterion.

Every case is therefore grounded in an acceptance criterion (`source: ac: AC-<n>` or
`QA-added: <reason>`); spec provenance rides along as an optional `openspec-ref:` and
mockup provenance as an optional `design-ref:`.

OpenSpec files are optional by design: a repo with none is the ordinary path, not a
degraded run.

The main agent orchestrates, validates, gates, and upserts. **Heavy reading (Story/PRD/
mockups/spec → cases) happens in a fresh-context subagent (Step B)** — the main agent does
not read the whole spec/PRD itself.

| What | Reference |
|---|---|
| Assemble the SoT; adapters (Jira, Confluence, Figma, `gh`) | `references/sot-assembly.md` |
| QA-lens derivation rules, conflicts, no-fabrication | `references/generation.md` |
| Exact `test-plan.md` shape + TestOps mapping | `references/test-plan-format.md` |
| Idempotent TestOps upsert, custom-field pre-flight, `--dry-run` | `references/testops-sync.md` |
| Deterministic validator (script, not an LLM) | `scripts/validate_test_plan.py` |

## Step A — Assemble the SoT (read-only)
Follow `references/sot-assembly.md`. Result: the SoT bundle — authoritative
`{ story, acceptance, prd?, designs[] }` plus contextual `{ openspecs[] }`. Only the Story
is required; PRD, mockups and specs degrade independently. Never write.

## Step B — Generate (fresh-context subagent)

**The plan lives at one stable path per Story and target:**

```
~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>.test-plan.md
```
`<service>` and `<capability>` come from `--target`; lowercase them and replace every
character outside `[a-z0-9]` with `-`. A run with no `--target` uses
`<STORY-KEY>-no-target.test-plan.md`. The path is **not** the invoking directory and **not**
a service repo (those are READ-ONLY): a plan written to the cwd is per-run, so the
`allure-id:` values in it are lost the moment the QA engineer runs from somewhere else.
The file is a machine-local cache, never committed — one plan per `--target` so two targets
of the same Story never overwrite each other. `mkdir -p ~/.kinoa-qa/plans` first.

**Write it atomically**: write to a temp file in the same directory, then `rename` it over the
stable path, so an interrupted or concurrent run never leaves a half-written plan. **Lifecycle**:
the directory is a cache the QA engineer may delete at will, whole or per file — the cost is the
assigned ids, so the next run for that Story+target reconciles every case at the reconciliation
gate instead of updating by id. Nothing else is lost; nothing prunes it automatically.

**Read the previous plan at that path before generating.** If it exists, pass its full text
to the subagent as `previous_plan`. Dispatch a subagent with the SoT bundle +
`previous_plan` (when present) + `references/generation.md` +
`references/test-plan-format.md`. It returns exactly one artifact: the `test-plan.md`
content, carrying `allure-id:` forward for every case it keeps (see
`references/generation.md`, "Carrying `allure-id:` forward"). Then, before writing:

```bash
python3 <plugin>/skills/testplan/scripts/plan_writer.py --previous <previous-plan> --new <subagent-plan> [--json]
```
It prints the **merged plan to stdout** and the **merge report to stderr** (`--json` for a
machine-readable report). Capture stdout; that is what gets written to the stable path. A
non-zero exit means no merged plan — do **not** write the subagent's plan instead, or every
assigned id is lost. On a first run there is no previous plan: skip the merge, write the
subagent's plan as-is, and every case is "new" at the gate.

The merge re-applies the **mechanical** half — a case whose title is unchanged (ignoring case
and whitespace runs) keeps its id whether or not the subagent carried it — and reports the
carried / retained / unmatched / orphaned lists for the Step D gate. It never guesses: a
reworded title comes back as `unmatched`, for the human to judge.

## Step C — Validate (deterministic, gates the run)
```bash
python3 <plugin>/skills/testplan/scripts/validate_test_plan.py <plan> [--openspec <spec.md> ...]
```
(`--openspec` is repeatable; pass one per resolved OpenSpec file, and none when there is
no spec.) The validator has **three outcomes**:

| Exit | Outcome | Meaning | What happens next |
|---|---|---|---|
| 0 | PASS | Structurally valid, no unresolved conflict. | Proceed to the Step D gate. |
| 1 | FAIL | Structurally invalid (missing field, bad `source:`, uncited AC, dishonest gap, unknown `openspec-ref`, malformed `design-ref`, **missing `## Conflicts` header**). | One regeneration retry with the validator detail → still FAIL → **STOP before the human gate**; never ships. |
| 2 | HOLD | Structurally valid, but ≥1 `## Conflicts` line has no `→ resolved: …`. | **Proceeds to the Step D gate** (conflicts shown first). Step E refuses to upsert. |

FAIL stops before the gate. HOLD does not — a HOLD plan is exactly the thing the QA
engineer must see.

Checks run: `required-fields`, `source-valid`, `scenario-coverage` (**advisory** — reports
a count, never fails), `ac-coverage` (hard fail; an AC named by an unresolved conflict is
exempt, and a case citing such an AC is itself a failure), `gap-honesty` (requirement- and
scenario-level), `conflict-resolution`, `openspec-ref-valid`, `design-ref-valid`.

## Step D — Human gate
Present the validated plan from `~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>.test-plan.md`
to the QA engineer, naming that path. **Nothing has touched TestOps yet.**

Read `## Conflicts` out **first** — before anything else — naming each unresolved
contradiction and the artifact on each side; the plugin has picked no winner.

**Then show the identity merge, before the cases** — this is the human's only chance to
catch a bad merge before Step E writes. List, from `merge_allure_ids`' report:

- **kept an id** — case, title, `allure-id` (carried forward, or already in the plan);
- **new** — case and title with no id: Step E will reconcile or create it;
- **ids in the previous plan no case claimed** — a replaced or deleted case; the TestOps
  case it points at is left alone.

A case in the "new" list that the QA engineer recognises as a rewording of a kept case is
corrected **in the file** by hand (`- allure-id: <id>` as the first field) and Step C
re-runs. The plugin never resolves that itself.

For a conflict, the QA engineer annotates `→ resolved: <business wins | spec wins, AC updated>` in the file and
Step C re-runs. Warn about any explicitly requested spec that failed to resolve, an absent
PRD, or Figma being unreachable. On edits, re-run Step C. Proceed to Step E only on
explicit approval.

## Step E — TestOps upsert

Order: Gate 0a (validator) → Gate 0b (custom fields) → per-id read-back and update →
**reconciliation gate** → create only what was confirmed. The reconciliation gate is a
**second human stop, inside Step E** — Step D closed on the merge report and cannot carry it.
Any unidentified case against a non-empty in-scope set stops the whole run there until a
mapping is confirmed; unattended, it aborts non-zero. Details in
`references/testops-sync.md` ("Reconciliation", §3 and §5).

Re-run the validator first. **Exit 2 (HOLD) refuses the upsert** — name the unresolved
conflicts and stop; approval at the gate does not override an unannotated conflict.
Then run the custom-field pre-flight: resolve `Suite`/`Story`/`Component`/`Feature`, and
**abort naming the offending field and value** if one is unset or is unverified — Allure fails
the whole creation silently on an unknown value. Each of `Story`/`Component`/`Feature` comes
from its flag (`--story-field` / `--component` / `--feature`), else the matching
`testops.custom_fields.*` default in `config.json`, else the run aborts; the shipped defaults
are **empty** on purpose, so a default run needs the flags. `Suite` is composed from the plan
header. The verification is a by-value case lookup, so it proves a value is *in use*, not that
it exists; `--allow-unverified-fields` downgrades that one check to a warning. Details, order
and the exact calls are in `references/testops-sync.md` (Gate 0).
Otherwise follow `references/testops-sync.md`. **Identity is the assigned Allure case id, not
anything derived from the case's content.** Per case, its `- allure-id:` decides the path:

- **id present** — read the case back first and **refuse to update it unless it carries the
  `qa-generated` tag AND the same Story**; only then `testops_update_testcase(id=<allure-id>)`.
  An id that no longer exists in TestOps is reported and the case falls through to
  reconciliation — never re-created silently under the missing id.
- **id absent** — reconcile, never create blind: one
  `testops_find_testcases(aql='issue = "<STORY-KEY>"')` (the AQL field is `issue`, **singular**)
  narrowed to this run's target by the `Target:` marker in the description, a proposed mapping
  shown at the **reconciliation gate**, and a create only for what the QA engineer confirms is
  new. **Any** unidentified case against a non-empty in-scope set — a mixed plan included, not
  just a plan with no ids at all — **writes nothing** for any case until a mapping is confirmed;
  unattended, it aborts non-zero. Orphans are listed and never touched.

After a create, write the returned id back into the plan at the stable path as
`- allure-id: <id>`. With `--dry-run`, the read-only lookups still run and the intended actions
are printed; nothing is written and it never refuses.

**Tag policy: `qa-generated` only.** The content-derived identity tag, `type-*`, `priority-*`, `openspec-context`,
`design-backed` and `spec-derived` are retired; OpenSpec and mockup provenance rides as a
`Provenance:` line on the payload `description`, and the target marker as its last line.

## Degradation
| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | HARD STOP at Step A (only required input). |
| Confluence PRD absent/unreachable | Proceed Story-only; header `prd: none`. |
| No OpenSpec files exist (normal) | Ordinary path, not a degradation; header `openspec: none`; **no** gate warning. |
| A requested OpenSpec file failed (`--target`/`--repo`/`--openspec-path`, `gh` unauthed, resolver error) | Continue; header `openspec: none (<reason>)`; warn at the gate. |
| Figma unreachable (no MCP, both backends down) or no frame linked | Continue; header `design: none (<reason>)`; warn at the gate; never a hard stop. |
| No plan at the stable path (first run for this Story+target) | Ordinary path, not a degradation; generate without `previous_plan`; every case is "new" at the gate. |
| The plan at the stable path is unreadable (permissions, corrupt, not parseable as a plan) | **Never overwrite it.** Stop before generating, name the path and the reason, and let the QA engineer move or repair it — regenerating over it would destroy the only copy of the assigned ids. |
| Two Step B runs write the same Story+target plan concurrently, or a write is interrupted | Write-to-temp-then-`rename` keeps the file whole — it is either the old plan or the new one, never a partial. The writes are **not** serialised: last writer wins, so a plan merged from a stale read can lose ids added meanwhile. Two engineers on one box, or two terminals, must not run Step B for the same Story+target at once. |
| `~/.kinoa-qa/plans/` cannot be created or written | Stop before Step B naming the path; nothing is generated, because a plan that cannot be persisted loses its ids again. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Spec contradicts Story/PRD | `⚠️ CONFLICT:` line (`openspec` vs the business side); the business `expected` is never overridden; HOLD. |
| Business sources contradict each other (no precedence — HOLD) | Story vs PRD vs mockup: `⚠️ CONFLICT:` naming every side with its artifact; no winner picked; the contradicted AC yields **no case**; HOLD. |
| Conflict left unannotated | Validator exits 2; the plan still reaches the gate, Step E refuses the upsert until every line carries `→ resolved: …`. |
| Generation fails | One retry, then stop and surface. |
| Validator FAIL | One retry → stop before the gate; never ships. |
| QA rejects at the gate | Nothing pushed; edits re-validated. |
| A custom-field value is unset (no flag, empty `config.json` default) | Abort at Step E's Gate 0b naming the field and the flag; nothing is looked up, nothing is written. |
| A custom-field value is used by no existing case (it may still exist in Allure) | Abort at Step E's Gate 0b naming the field and the value. Re-run with `--allow-unverified-fields` to downgrade it to a warning when the value was just created in Allure and no case uses it yet. |
| A plan has at least one unidentified case and the target already has in-scope cases (a mixed plan included) | Step E **writes nothing** — no create, no update. It prints the proposed mapping and the orphan list and stops until the QA engineer confirms a mapping; an unattended run aborts non-zero rather than creating blind. |
| An `allure-id` no longer exists in TestOps | Not a crash: report `allure-id <id> for TC-<n> no longer exists in project KINOA`, treat that case as unidentified and let it reconcile with the rest. Never create silently under the missing id. |
| An `allure-id` resolves to a case without `qa-generated` or with a different Story | That case is skipped and the mismatch is named; nothing is written for it. The plugin never overwrites a case it cannot prove it wrote. |
| TestOps write fails mid-batch | No rollback — cases already created have their ids written back into the plan, so a re-run updates them instead of duplicating. |
| TestOps unreachable | The plan is on disk at the stable path; re-run Step E later. |

## Invariants
- Service repos are READ-ONLY.
- TestOps is written ONLY after the Step D human gate.
- Upserts are idempotent, keyed by the **Allure case id assigned on first create** and
  carried forward in the plan as `- allure-id:` — an id present is updated in place after
  the verification read, an id absent is reconciled against the Story and target and
  confirmed by the QA engineer before anything is written. No duplicates on re-run.
- No fabrication — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- **A spec never overrides a business expected result; conflicts are surfaced, never
  resolved.**
- The deterministic validator gates before the human sees the plan.
- Standalone — zero code dependency on kinoa-dev.
