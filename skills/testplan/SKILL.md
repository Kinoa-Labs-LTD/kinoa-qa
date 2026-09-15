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
Dispatch a subagent with the SoT bundle + `references/generation.md` +
`references/test-plan-format.md`. It returns exactly one artifact: the `test-plan.md`
content. Write it to a local working file `./<STORY-KEY>-<service>-<capability>.test-plan.md`.

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
Present the validated `test-plan.md` to the QA engineer. **Nothing has touched TestOps
yet.** Read `## Conflicts` out **first** — before the cases — naming each unresolved
contradiction and the artifact on each side; the plugin has picked no winner. The QA
engineer annotates `→ resolved: <business wins | spec wins, AC updated>` in the file and
Step C re-runs. Warn about any explicitly requested spec that failed to resolve, an absent
PRD, or Figma being unreachable. On edits, re-run Step C. Proceed to Step E only on
explicit approval.

## Step E — TestOps upsert
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
Otherwise follow `references/testops-sync.md`: per case, AQL-find by the `tp-<slug>` tag →
`update` or `create` in project KINOA (id from `config.json`), then write `@allure.id`
back into the `.md`. With `--dry-run`, print intended actions instead.

**Tag policy: `tp-<slug>` + `qa-generated` only.** `type-*`, `priority-*`, `openspec-context`,
`design-backed` and `spec-derived` are retired; OpenSpec and mockup provenance rides as a
`Provenance:` line on the payload `description`.

## Degradation
| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | HARD STOP at Step A (only required input). |
| Confluence PRD absent/unreachable | Proceed Story-only; header `prd: none`. |
| No OpenSpec files exist (normal) | Ordinary path, not a degradation; header `openspec: none`; **no** gate warning. |
| A requested OpenSpec file failed (`--target`/`--repo`/`--openspec-path`, `gh` unauthed, resolver error) | Continue; header `openspec: none (<reason>)`; warn at the gate. |
| Figma unreachable (no MCP, both backends down) or no frame linked | Continue; header `design: none (<reason>)`; warn at the gate; never a hard stop. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Spec contradicts Story/PRD | `⚠️ CONFLICT:` line (`openspec` vs the business side); the business `expected` is never overridden; HOLD. |
| Business sources contradict each other (no precedence — HOLD) | Story vs PRD vs mockup: `⚠️ CONFLICT:` naming every side with its artifact; no winner picked; the contradicted AC yields **no case**; HOLD. |
| Conflict left unannotated | Validator exits 2; the plan still reaches the gate, Step E refuses the upsert until every line carries `→ resolved: …`. |
| Generation fails | One retry, then stop and surface. |
| Validator FAIL | One retry → stop before the gate; never ships. |
| QA rejects at the gate | Nothing pushed; edits re-validated. |
| A custom-field value is unset (no flag, empty `config.json` default) | Abort at Step E's Gate 0b naming the field and the flag; nothing is looked up, nothing is written. |
| A custom-field value is used by no existing case (it may still exist in Allure) | Abort at Step E's Gate 0b naming the field and the value. Re-run with `--allow-unverified-fields` to downgrade it to a warning when the value was just created in Allure and no case uses it yet. |
| TestOps write fails mid-batch | No rollback — keyed upsert; re-run resumes. |
| TestOps unreachable | `test-plan.md` is on disk; re-run Step E later. |

## Invariants
- Service repos are READ-ONLY.
- TestOps is written ONLY after the Step D human gate.
- Upserts are idempotent, keyed by the `tp-<slug>` tag — no duplicates on re-run.
- No fabrication — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- **A spec never overrides a business expected result; conflicts are surfaced, never
  resolved.**
- The deterministic validator gates before the human sees the plan.
- Standalone — zero code dependency on kinoa-dev.
