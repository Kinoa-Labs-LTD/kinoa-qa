---
name: testplan
description: Build a validator-checked QA test plan from a Jira Story (+ optional Confluence PRD + optional linked Figma mockups + optional service-repo OpenSpec specs) and, after a human gate, idempotently upsert the cases into Allure TestOps. Invoke for `/kinoa-qa:testplan <STORY-KEY>`.
---

# testplan — Jira Story → Allure TestOps cases

`/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>]
[--openspec-path <dir>] [--story-field <value>] [--component <value>] [--feature <value>]
[--allow-unverified-fields] [--dry-run]`

`/kinoa-qa:testplan --from-smoke <SUBTASK-KEY> [--target <service>/<capability>]
[--story-field <value>] [--component <value>] [--feature <value>] [--allow-unverified-fields]
[--dry-run]`

`testplan` **generates e2e plans only**. With `--from-smoke <SUBTASK-KEY>` it generates
nothing: it pushes a Story's smoke plan instead. `/kinoa-qa:smoke-plan` writes that plan as a
"Smoke test" Jira sub-task; `smoke_to_plan.py` converts the sub-task, deterministically and
with no LLM step, into a `scope: smoke` `test-plan.md`, which Steps C–E then validate, gate
and push as one `Draft` case — see "Steps A–B under `--from-smoke`". Outside `--from-smoke`,
a plan whose header says `scope: smoke` is a stop at Step C and is never pushed.

"Spec" in this plugin means an OpenSpec `spec.md` file generated from service-repo code;
a Confluence PRD/HLD is never called a "spec" here.

## Source of truth

The **authoritative tier** is the Jira Story + the Confluence PRD + any Figma mockup
linked from the Story + any image attached to the Story. Those sources decide what a case
asserts, and they have **no precedence between one another**. OpenSpec `spec.md` files are
**supporting context only**: they may shape a case's `preconditions` and `steps`, never its
`expected`. A mockup or a Story image, unlike a spec, IS a business requirement — what a
frame or an image shows becomes an acceptance criterion.

Every case is therefore grounded in one or more acceptance criteria
(`source: ac: AC-<n>[, AC-<m>…]`, a comma-separated list, or `QA-added: <reason>`); spec provenance rides along as an optional `openspec-ref:` and
mockup provenance as an optional `design-ref:`.

OpenSpec files are optional by design: a repo with none is the ordinary path, not a
degraded run.

The main agent orchestrates, validates, gates, and upserts. **Heavy reading (Story/PRD/
mockups/spec → cases) happens in a fresh-context subagent (Step B)** — the main agent does
not read the whole spec/PRD itself.

| What | Reference |
|---|---|
| Assemble the SoT; adapters (Jira, Confluence, Figma, `gh`) incl. Story image attachments (ImageReader) | `references/sot-assembly.md` |
| QA-lens derivation rules, conflicts, no-fabrication | `references/generation.md` |
| Exact `test-plan.md` shape + TestOps mapping | `references/test-plan-format.md` |
| Idempotent TestOps upsert, custom-field pre-flight, `--dry-run` | `references/testops-sync.md` |
| Deterministic validator (script, not an LLM) | `scripts/validate_test_plan.py` |
| `--from-smoke`: smoke sub-task → `scope: smoke` plan; the sub-task's remote link | `scripts/smoke_to_plan.py`, `scripts/jira_remote_link.py` |

## Step A — Assemble the SoT (read-only)
Follow `references/sot-assembly.md`. Result: the SoT bundle — authoritative
`{ story, acceptance, prd?, designs[], images[] }` (each `images[]` entry is `{ id,
filename, mimeType, path }`, where `path` is the absolute path of a file Step A wrote to a
run-scoped temporary directory) plus contextual `{ openspecs[] }`. Only the Story is
required; PRD, mockups, images and specs degrade independently. Step A creates the
temporary directory and writes each fetched image to it; it otherwise never writes.

## Step B — Generate (fresh-context subagent)

**The plan lives at one stable path per Story and target:**

```
~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>-e2e.test-plan.md
```
`<service>` and `<capability>` come from `--target`; lowercase them and replace every
character outside `[a-z0-9]` with `-`. The last segment is always `-e2e`, the format of every
plan this skill generates. Outside `--from-smoke` this skill reads and writes no other plan
path; a `--from-smoke` run uses the `-smoke` path instead (see "Steps A–B under `--from-smoke`").
A run with no `--target` uses `<STORY-KEY>-no-target-e2e.test-plan.md`. The path is **not** the invoking directory and **not**
a service repo (those are READ-ONLY): a plan written to the cwd is per-run, so the
`allure-id:` values in it are lost the moment the QA engineer runs from somewhere else.
The file is a machine-local cache, never committed — one plan per `--target` so two targets
of the same Story never overwrite each other. `mkdir -p ~/.kinoa-qa/plans` first.

**Write it atomically**: write to a temp file in the same directory, then `rename` it over the
stable path, so an interrupted or concurrent run never leaves a half-written plan. **Lifecycle**:
the directory is a cache the QA engineer may delete at will, whole or per file — the cost is the
assigned ids, so the next run for that Story+target reconciles every case at the reconciliation
gate instead of updating by id. Nothing else is lost; nothing prunes it automatically.

**The format of the plan.** Every plan this skill generates is e2e: Step B writes
`scope: e2e` explicitly in its header (`references/test-plan-format.md`), so no reader has to
know that an absent `scope:` also means e2e. There is no scope flag: if the caller passes
`--scope`, **stop before Step A** and say why: the flag is gone, e2e is the only plan `testplan`
generates. A `scope:` value other than `smoke` or `e2e` never gets past Step C: `scope-valid`
FAILs it naming the value and the allowed set. A `scope: smoke` plan passes the validator but,
outside `--from-smoke`, still stops at Step C, before the gate (see "E2E only" there).

**Read the previous plan at that path before generating.** If it exists, pass its full text
to the subagent as `previous_plan`. Dispatch a subagent with the SoT bundle +
`previous_plan` (when present) + `references/generation.md` +
`references/test-plan-format.md` + the `images[].path` files for the subagent to read
directly as images alongside the bundle. It returns exactly one artifact: the `test-plan.md`
content, with `scope: e2e` in its header, carrying `allure-id:` forward for every case it keeps (see
`references/generation.md`, "Carrying `allure-id:` forward"). Then, before writing:

```bash
python3 <plugin>/skills/testplan/scripts/plan_writer.py --previous <previous-plan> --new <subagent-plan> [--json]
```
It prints the **merged plan to stdout** and the **merge report to stderr** (`--json` for a
machine-readable report). Capture stdout; that is what gets written to the stable path. A
non-zero exit means no merged plan — do **not** write the subagent's plan instead, or every
assigned id is lost. On a first run there is no previous plan: skip the merge, write the
subagent's plan as-is, and every case is "new" at the gate.

The merged plan's header is the regenerated plan's header exactly as the subagent wrote it;
nothing is taken from the previous plan's header. The merge re-applies the **mechanical**
half — a case whose title is unchanged (ignoring case and whitespace runs) keeps its id
whether or not the subagent carried it — and reports the carried / retained / unmatched /
orphaned lists for the Step D gate. It never guesses: a reworded title comes back as `unmatched`, for the human to judge.

## Steps A–B under `--from-smoke` — convert the sub-task (no generation)

A `--from-smoke` run replaces Steps A and B. It reads no PRD, no Figma, no image and no
OpenSpec file, dispatches no subagent, and no LLM step writes or edits the plan: the plan is
the converter's output, merged with the previous plan's ids.

1. **Save the raw responses, unmodified, into one input file.** With the Atlassian MCP:
   `getJiraIssue(<SUBTASK-KEY>, responseContentFormat="markdown")`, then the parent Story
   (the sub-task's `fields.parent.key`) with `getJiraIssue(<STORY-KEY>,
   responseContentFormat="markdown", expand="names", fields=["*all"])` — the `names` map is
   how the converter finds the Story's acceptance-criteria field when the description has no
   criteria list — then `getJiraIssueRemoteIssueLinks(<SUBTASK-KEY>)`.
   Write them, exactly as returned, as one JSON object to a run-scoped temporary file:
   `{"subtask": <sub-task response>, "story": <Story response>, "remote_links": <links
   response>}` (`[]` when the sub-task has no remote link). Never trim, summarise or rewrite a
   response — the converter reads only this file and has no network access. From here on the
   Story key is the plan header's `story:`, never `<SUBTASK-KEY>`.
2. **Convert.** First the stable path, then the plan:

   ```bash
   python3 <plugin>/skills/testplan/scripts/smoke_to_plan.py --input <input.json> [--target <service>/<capability>] --print-path
   python3 <plugin>/skills/testplan/scripts/smoke_to_plan.py --input <input.json> [--target <service>/<capability>]
   ```
   `--print-path` prints `~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>-smoke.test-plan.md`
   (`<STORY-KEY>-no-target-smoke.test-plan.md` without `--target`); without it the plan is
   printed on stdout. The plan is one `functional` P1 case titled with the sub-task summary
   minus its `Smoke test: ` prefix; its preconditions and steps are the sub-task's
   `## Preconditions` and `## Steps` (one `→ expected:` each, source tags stripped), its
   `source: ac: …` comes from the steps' `[AC-n]` tags, `## Acceptance Criteria` lists the
   parent Story's acceptance criteria, and each unanswered `## Open questions` item becomes a
   `⚠️ GAP` line. An `Allure TestOps case <id>` remote link on the sub-task becomes the case's
   first field, `- allure-id: <id>`: the plan cache is machine-local, so that link is the only
   durable record of the case id.

   **Exit 1 is a refusal**: stderr reads `refused: <reason>` and stdout is empty. Stop, name
   the reason, write nothing. The fix is always on the sub-task or its Story — for example a
   missing or empty `## Preconditions` (the converter never invents one), a step without
   exactly one expected result, no `[GATE]` step, a Story with no acceptance-criteria list,
   an `[AC-n]` past the Story's count, or two remote links naming different cases — then
   re-run.
3. **Merge the ids** with the previous plan at that stable path, exactly as in Step B:
   `plan_writer.py --previous <stable path> --new <converted plan>`, capturing stdout, and
   write it atomically. With no previous plan, write the converted plan as-is. An id that came
   from the remote link but is not in the previous plan is reported as `suspect`; that is
   expected on a machine that never pushed this sub-task, and Step E's read-back verifies it.

**A `--from-smoke` plan is never hand-edited.** A wrong case is fixed on the sub-task and the
push re-run. A reworded sub-task summary keeps its id through the remote link; without the
link it comes back `unmatched` and goes to the reconciliation gate.

## Step C — Validate (deterministic, gates the run)
```bash
python3 <plugin>/skills/testplan/scripts/validate_test_plan.py <plan> [--openspec <spec.md> ...]
```
(`--openspec` is repeatable; pass one per resolved OpenSpec file, and none when there is
no spec.) The validator has **three outcomes**:

| Exit | Outcome | Meaning | What happens next |
|---|---|---|---|
| 0 | PASS | Structurally valid, no unresolved conflict. | Proceed to the Step D gate. |
| 1 | FAIL | Structurally invalid (missing field, bad `source:`, uncited AC in an e2e plan, dishonest gap, unknown `openspec-ref`, malformed `design-ref`, malformed `image-ref`, **missing `## Conflicts` header**, a missing `## Cases` or `## Gaps` header, a `scope:` other than `smoke` or `e2e`, a `type:` outside the five case types, a smoke plan that is not exactly one `functional` case). | One regeneration retry with the validator detail → still FAIL → **STOP before the human gate**; never ships. Under `--from-smoke` there is no retry (below). |
| 2 | HOLD | Structurally valid, but ≥1 `## Conflicts` line has no `→ resolved: …`. | **Proceeds to the Step D gate** (conflicts shown first). Step E refuses to upsert. |

FAIL stops before the gate. HOLD does not — a HOLD plan is exactly the thing the QA
engineer must see.

**E2E only, unless the run is `--from-smoke`.** Before you run the validator, read the plan
header with `plan_parser.parse_header`. `testplan` goes on only when the header says
`scope: e2e` or has no `scope:` line (which means e2e). A header that says `scope: smoke` is a
**stop** here, whatever the validator would say, unless the run is `--from-smoke`: report that
outside `--from-smoke` `testplan` validates and pushes e2e plans only, and do not go to the
gate or to Step E. The plan is never pushed. Any other value goes to the validator, and
`scope-valid` FAILs it. A `--from-smoke` run goes on only with a header that says
`scope: smoke`, which the converter always writes, and runs the validator with no
`--openspec`.

**Under `--from-smoke`, a FAIL is a converter defect.** Stop and report the validator detail
as a defect of `smoke_to_plan.py`: no regeneration retry, and never an edit to the plan to
make it pass.

Checks run, in order: `required-fields`, `source-valid`, `openspec-ref-valid`,
`design-ref-valid`, `image-ref-valid`, `allure-id-valid` (shape and uniqueness of a present
`allure-id:` only — never checked against TestOps), `scenario-coverage` (**advisory** —
reports a count, never fails), `ac-coverage` (`## Acceptance Criteria` is required in both
formats; each id of a comma-separated `ac:` list counts as cited; an uncovered AC is a hard
fail for an e2e plan, the scope absent included, and **advisory** under `scope: smoke`; an AC
named by an unresolved conflict is exempt), `conflict-resolution` (a case citing, anywhere in
its `ac:` list, an AC an unresolved conflict contradicts is itself a failure), `gap-honesty`
(requirement- and scenario-level), `scope-valid` (`smoke` or `e2e`, case-sensitive; absent
means `e2e`), `type-valid` (`functional`, `negative`, `edge`, `regression` or
`nonfunctional`; `type: e2e` fails pointing at `scope: e2e`), `smoke-shape` (under
`scope: smoke`, exactly one case and it is `type: functional`; n/a for an e2e plan),
`sections-present` (the `## Cases` and `## Gaps` headers are present, in both formats;
`## Gaps` may be empty; each missing header is named). The smoke rules — one `→ expected:`
per step, advisory `ac-coverage`, `smoke-shape` — apply only when the header says exactly
`scope: smoke`; `Smoke` or any other invalid value FAILs `scope-valid` and gets the e2e
rules.

## Step D — Human gate
Present the validated plan from its stable path —
`~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>-e2e.test-plan.md`, or `…-smoke.test-plan.md`
under `--from-smoke` — to the QA engineer, naming that path. **Nothing has touched TestOps yet.**

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

**Under `--from-smoke`** the plan is never hand-edited: a wrong case is fixed on the sub-task
and the push re-run from the start, and a reworded case with no id goes to the reconciliation
gate. Ask one more question here, as a separate yes from the approval: may Step E, once it has
created or updated the case, write the sub-task's remote link `Allure TestOps case <id>`? No
means the push goes ahead and no link is written.

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
header. `--feature` is honoured for every plan: `resolve_custom_fields` takes no scope and never
sets `Feature` itself. The **format** (smoke or e2e) is read from the same header with
`plan_parser.parse_header` and passed to `case_to_payload` only: an e2e plan (`scope: e2e`, or
the scope absent) gets `status` `"Review"` and a `scope=e2e` target marker. `case_to_payload`
maps a `scope: smoke` plan to `"Draft"` and `scope=smoke`; only a `--from-smoke` run reaches
Step E with one, and its `Feature` is the caller's, like every run's. Nothing else in the
payload differs between the formats. The verification is a by-value case lookup, so it proves a value is *in use*, not that
it exists; `--allow-unverified-fields` downgrades that one check to a warning. Details, order
and the exact calls are in `references/testops-sync.md` (Gate 0).
Otherwise follow `references/testops-sync.md`. **Identity is the assigned Allure case id, not
anything derived from the case's content.** Per case, its `- allure-id:` decides the path:

- **id present** — read the case back first and **refuse to update it unless it carries the
  `qa-generated` tag AND the same Story** — and, under a `scope: smoke` plan, unless its
  `Target:` marker says `scope=smoke`, so an id that resolves to an e2e case is refused and
  named; only then `testops_update_testcase(id=<allure-id>)`.
  An id that no longer exists in TestOps is reported and the case falls through to
  reconciliation — never re-created silently under the missing id.
- **id absent** — reconcile, never create blind: one
  `testops_find_testcases(aql='issue = "<STORY-KEY>"')` (the AQL field is `issue`, **singular**)
  narrowed to this run's target **and format** by the `Target: service=…; capability=…;
  scope=…` marker in the description, a proposed mapping
  shown at the **reconciliation gate**, and a create only for what the QA engineer confirms is
  new. **Any** unidentified case against a non-empty in-scope set — a mixed plan included, not
  just a plan with no ids at all — **writes nothing** for any case until a mapping is confirmed;
  unattended, it aborts non-zero. Orphans are listed and never touched.

After a create, write the returned id back into the plan at the stable path as
`- allure-id: <id>`. With `--dry-run`, the read-only lookups still run and the intended actions
are printed; nothing is written and it never refuses.

**Under `--from-smoke`, Step E takes the Story key from the plan header's `story:`**
everywhere — `issues`, the `issue = "<STORY-KEY>"` lookup, `resolve_custom_fields`, the
read-back — never the sub-task key typed after `--from-smoke`.

**Then the remote link** — only under `--from-smoke`, only when the QA engineer said yes at
Step D, and only after Step E created or updated the case; never under `--dry-run`, never on an
unattended run. With the case's id:

```bash
python3 <plugin>/skills/testplan/scripts/jira_remote_link.py --issue <SUBTASK-KEY> --case-id <allure-id>
```
It lists the sub-task's remote links and updates in place, by its link id, the first one that
carries the globalId `kinoa-qa:smoke-case:<SUBTASK-KEY>` or a title matching
`^Allure TestOps case (\d+)\b` (a hand-added one included, a suffix such as
`Allure TestOps case 4711 (smoke)` too; `case_id_from_title` in `jira_remote_link.py`, the
rule `smoke_to_plan.py` reads the id with); with none, it creates the link with that
globalId. A re-push therefore never adds a second link, and no link is ever deleted. The link's URL is
`<testops.base_url>/project/<testops.project_id>/test-cases/<id>` from `config.json`; the Jira
site is `jira_base_url`, overridden by `JIRA_BASE_URL`. It authenticates with `JIRA_EMAIL` /
`JIRA_API_TOKEN` (a token with the classic `write:jira-work` scope) and picks the host by
`JIRA_HOST`: `auto` (the `api.atlassian.com` gateway, then the site), `gateway` or `site`.
Exit 0: written, and it says created or updated. Exit 3: `JIRA_EMAIL` or `JIRA_API_TOKEN` is
unset; nothing is sent. Exit 1: `config.json` is unreadable or incomplete, or Jira refused or
failed a request — a 401/403 names the classic `write:jira-work` scope and the Jira "Link
issues" permission. Exit 2: a usage error (a bad `--issue` or `--case-id`). **A failed link
never undoes the push**: the case stays; name the reason and repeat the lines the script
prints on stderr, for the QA engineer to add the link by hand on the sub-task. On exit 3, and
on exit 1 from a refused or failed request, they are a `title:` and a `url:` line. On exit 1
from the config, the `title:` line is always printed, and the `url:` line only when the config
still names `testops.base_url` and `testops.project_id`; without it, the URL is
`<TestOps host>/project/<project id>/test-cases/<id>`.

**Tag policy: `qa-generated` only.** The content-derived identity tag, `type-*`, `priority-*`, `openspec-context`,
`design-backed` and `spec-derived` are retired; OpenSpec, mockup and Story-image provenance
rides as a `Provenance:` line on the payload `description`, and the target marker as its
last line.

## Degradation
| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | HARD STOP at Step A (only required input). |
| Confluence PRD absent/unreachable | Proceed Story-only; header `prd: none`. |
| No OpenSpec files exist (normal) | Ordinary path, not a degradation; header `openspec: none`; **no** gate warning. |
| A requested OpenSpec file failed (`--target`/`--repo`/`--openspec-path`, `gh` unauthed, resolver error) | Continue; header `openspec: none (<reason>)`; warn at the gate. |
| Figma unreachable (no MCP, both backends down) or no frame linked | Continue; header `design: none (<reason>)`; warn at the gate; never a hard stop. |
| Story has no image attachment | Ordinary path, not a degradation; header `images: none`; **no** gate warning. |
| Jira credentials unset (`JIRA_EMAIL`/`JIRA_API_TOKEN`) | Continue; header `images: none (jira credentials not set)`; warn at the gate; never a hard stop. |
| An image fetch fails (404, rejected) and it was the only image | Continue; header `images: none (<reason>)`; warn at the gate; never a hard stop. |
| An image fetch fails (404, rejected) but at least one other image was read | Continue; header `images: <n> read (<k> failed: <reason>)`; warn at the gate; never a hard stop. |
| An image exceeds the 10 MB cap | Continue; folded into the same partial-failure count as a failed fetch (`images: <n> read (<k> failed: <reason>)`, or `images: none (<reason>)` if it was the only image); warn at the gate; never a hard stop. |
| No plan at the stable path (first run for this Story+target) | Ordinary path, not a degradation; generate without `previous_plan`; every case is "new" at the gate. |
| The plan at the stable path is unreadable (permissions, corrupt, not parseable as a plan) | **Never overwrite it.** Stop before generating, name the path and the reason, and let the QA engineer move or repair it — regenerating over it would destroy the only copy of the assigned ids. |
| Two Step B runs write the same Story+target plan concurrently, or a write is interrupted | Write-to-temp-then-`rename` keeps the file whole — it is either the old plan or the new one, never a partial. The writes are **not** serialised: last writer wins, so a plan merged from a stale read can lose ids added meanwhile. Two engineers on one box, or two terminals, must not run Step B for the same Story+target at once. |
| `~/.kinoa-qa/plans/` cannot be created or written | Stop before Step B naming the path; nothing is generated, because a plan that cannot be persisted loses its ids again. |
| The caller passes `--scope` | **Stop before Step A**: the flag is gone, and e2e is the only plan `testplan` generates. Nothing is read or written. |
| Outside `--from-smoke`, the plan this skill is about to validate or push has a header that says `scope: smoke` | **Stop at Step C**, before the gate, and say why: outside `--from-smoke` `testplan` validates and pushes e2e plans only. The plan is never pushed. |
| `--from-smoke`: `smoke_to_plan.py` refuses (exit 1, `refused: <reason>`) | Stop before Step C naming the reason; nothing is written. Fix the sub-task or its Story and re-run. |
| `--from-smoke`: the validator FAILs the converter's output | A converter defect: stop and report it. No regeneration retry, no edit to the plan. |
| `--from-smoke`: an `allure-id` resolves to a case whose `Target:` marker does not say `scope=smoke` | That case is skipped and named; nothing is written for it. |
| `--from-smoke`: Jira credentials unset (`jira_remote_link.py` exit 3), or the config unreadable or incomplete, or the link write refused or failed (exit 1) | The pushed case stays. Name the reason (a 401/403 names the classic `write:jira-work` scope and the "Link issues" permission) and print the `title:` and `url:` lines the script printed, to add the link by hand (a config error with no readable `testops.base_url`/`testops.project_id` prints the `title:` line alone). |
| A plan header carries a `scope:` other than `smoke` or `e2e` (`story` included) | Step C FAILs (`scope-valid`) naming the value and the allowed set `smoke, e2e`, so the run stops before the gate. |
| A `…-story.test-plan.md` exists for this Story and target | It is **ignored** — the stable path always ends in `-e2e` — so the run generates as a first run and every case comes back with no `allure-id:`. Nothing is overwritten. To keep its ids, the QA engineer renames it to `…-e2e.test-plan.md` and sets `scope: e2e` in its header before Step B: its `allure-id:` lines are in the file, so they carry over and Step E updates those cases by id. Without the rename, reconciliation does **not** find the old cases: a TestOps case whose `Target:` marker still carries the old Story scope value is outside the e2e in-scope set, so it is neither matched nor reported, and the run creates the cases again. Project KINOA has no such case (checked 2026-09-24: no plugin-authored case existed before 0.3.0). |
| A plan exists at the old three-segment path `<STORY-KEY>-<service>-<capability>.test-plan.md` | It is **not found** — the stable path carries the format — so the run generates as a first run, exactly as for a `-story` file. To keep the ids, rename it to `…-e2e.test-plan.md` and set `scope: e2e` before Step B. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Spec contradicts Story/PRD | `⚠️ CONFLICT:` line (`openspec` vs the business side); the business `expected` is never overridden; HOLD. |
| Business sources contradict each other (no precedence — HOLD) | Story vs PRD vs mockup: `⚠️ CONFLICT:` naming every side with its artifact; no winner picked; the contradicted AC yields **no case**; HOLD. |
| Conflict left unannotated | Validator exits 2; the plan still reaches the gate, Step E refuses the upsert until every line carries `→ resolved: …`. |
| Generation fails | One retry, then stop and surface. |
| Validator FAIL | One retry → stop before the gate; never ships. Under `--from-smoke`, no retry (a converter defect). |
| QA rejects at the gate | Nothing pushed; edits re-validated. |
| A custom-field value is unset (no flag, empty `config.json` default) | Abort at Step E's Gate 0b naming the field and the flag; nothing is looked up, nothing is written. |
| A custom-field value is used by no existing case (it may still exist in Allure) | Abort at Step E's Gate 0b naming the field and the value. Re-run with `--allow-unverified-fields` to downgrade it to a warning when the value was just created in Allure and no case uses it yet. |
| A plan has at least one unidentified case and the target already has in-scope cases (a mixed plan included) | Step E **writes nothing** — no create, no update. It prints the proposed mapping and the orphan list and stops until the QA engineer confirms a mapping; an unattended run aborts non-zero rather than creating blind. |
| An `allure-id` no longer exists in TestOps | Not a crash: report `allure-id <id> for TC-<n> no longer exists in project KINOA`, treat that case as unidentified and let it reconcile with the rest. Never create silently under the missing id. |
| A TestOps case carries a two-field `Target:` marker, written before the `scope=` field existed | Its scope reads as unrecorded, never as `e2e`, so it matches no run and is reported once rather than silently claimed by the first format that pushes. It is never an orphan the plugin acts on: the QA engineer adopts it by adding its `- allure-id:` to the plan by hand. |
| An `allure-id` resolves to a case without `qa-generated` or with a different Story | That case is skipped and the mismatch is named; nothing is written for it. The plugin never overwrites a case it cannot prove it wrote. |
| TestOps write fails mid-batch | No rollback — cases already created have their ids written back into the plan, so a re-run updates them instead of duplicating. |
| TestOps unreachable | The plan is on disk at the stable path; re-run Step E later. |

## Invariants
- Service repos are READ-ONLY.
- TestOps is written ONLY after the Step D human gate. Jira is written only under
  `--from-smoke`: one remote link on the sub-task, after Step E, on its own yes.
- Upserts are idempotent, keyed by the **Allure case id assigned on first create** and
  carried forward in the plan as `- allure-id:` — an id present is updated in place after
  the verification read, an id absent is reconciled against the Story and target and
  confirmed by the QA engineer before anything is written. No duplicates on re-run.
- **`testplan` generates e2e plans only**, each with `scope: e2e` written in its header, at a
  stable path ending in `-e2e`. A regenerated plan's header is taken as written, never from
  the previous plan, and an absent `scope:` means e2e. Outside `--from-smoke` a plan whose
  header says `scope: smoke` stops at Step C and is never pushed. A `--from-smoke` plan is
  `smoke_to_plan.py`'s output from the saved sub-task, Story and remote-link responses alone,
  at a stable path ending in `-smoke`, never written by an LLM or by hand. The two formats
  never share a reconciliation in-scope set.
- No fabrication — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- **A spec never overrides a business expected result; conflicts are surfaced, never
  resolved.**
- The deterministic validator gates before the human sees the plan.
- Standalone — zero code dependency on kinoa-dev.
