---
name: testplan
description: Build a validator-checked QA test plan from a Jira Story (+ optional Confluence PRD + optional service-repo OpenSpec specs) and, after a human gate, idempotently upsert the cases into Allure TestOps. Invoke for `/kinoa-qa:testplan <STORY-KEY>`.
---

# testplan — Jira Story → Allure TestOps cases

`/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>] [--spec-path <dir>] [--dry-run]`

The main agent orchestrates, validates, gates, and upserts. **Heavy reading (Story/PRD/
spec → cases) happens in a fresh-context subagent (Step B)** — the main agent does not
read the whole spec/PRD itself.

| What | Reference |
|---|---|
| Assemble the SoT; adapters (Jira, Confluence, `gh`) | `references/sot-assembly.md` |
| QA-lens derivation rules, no-fabrication | `references/generation.md` |
| Exact `test-plan.md` shape + TestOps mapping | `references/test-plan-format.md` |
| Idempotent TestOps upsert, `--dry-run` | `references/testops-sync.md` |
| Deterministic validator (script, not an LLM) | `scripts/validate_test_plan.py` |

## Step A — Assemble the SoT (read-only)
Follow `references/sot-assembly.md`. Result: the SoT bundle `{ story, acceptance, prd?,
specs[] }`. Only the Story is required; PRD and specs degrade independently. Never write.

## Step B — Generate (fresh-context subagent)
Dispatch a subagent with the SoT bundle + `references/generation.md` +
`references/test-plan-format.md`. It returns exactly one artifact: the `test-plan.md`
content. Write it to a local working file `./<STORY-KEY>-<service>-<capability>.test-plan.md`.

## Step C — Validate (deterministic, gates the run)
```bash
python3 <plugin>/skills/testplan/scripts/validate_test_plan.py <plan> [--spec <spec>]
```
(Pass `--spec` only when a spec was resolved.) FAIL → one regeneration retry with the
validator detail → still FAIL → STOP before the human gate and surface the failing
checks. A failing plan never reaches TestOps.

## Step D — Human gate
Present the validated `test-plan.md` to the QA engineer. **Nothing has touched TestOps
yet.** If specs degraded, warn that the plan is business-only. On edits, re-run Step C.
Proceed to Step E only on explicit approval.

## Step E — TestOps upsert
Follow `references/testops-sync.md`: per case, AQL-find by the `tp-<slug>` tag →
`update` or `create` in project KINOA (id from `config.json`), then write `@allure.id`
back into the `.md`. With `--dry-run`, print intended actions instead.

## Degradation
| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | HARD STOP at Step A (only required input). |
| Confluence PRD absent/unreachable | Proceed Story-only; header `prd: none`. |
| Spec unresolved / `gh` unauthed / target fails | Continue business-only; header `specs: none (<reason>)`; warn at the gate. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Generation fails | One retry, then stop and surface. |
| Validator FAIL | One retry → stop before the gate; never ships. |
| QA rejects at the gate | Nothing pushed; edits re-validated. |
| TestOps write fails mid-batch | No rollback — keyed upsert; re-run resumes. |
| TestOps unreachable | `test-plan.md` is on disk; re-run Step E later. |

## Invariants
- Service repos are READ-ONLY.
- TestOps is written ONLY after the Step D human gate.
- Upserts are idempotent, keyed by the `tp-<slug>` tag — no duplicates on re-run.
- No fabrication — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- The deterministic validator gates before the human sees the plan.
- Standalone — zero code dependency on kinoa-dev.
