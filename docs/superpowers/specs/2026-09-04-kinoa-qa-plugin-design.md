# kinoa-qa — QA plugin design

**Jira:** KING-22737 ([AQA][TECH][AI] QA Plugin) · **Author:** Dmytro Kapeliukh · **Date:** 2026-09-04
**Status:** Design (brainstormed, pending review) · **Supersedes concept:** kinoa-specs–centric flow-test-plan (KING-22475)

---

## 1. Context & problem

The QA concept has shifted. Under KING-22475 we built `flow-test-plan` inside the
`kinoa-dev` plugin: it generated QA test plans into the central **kinoa-specs**
repo. KING-22737 changes the ground under that:

- **kinoa-specs may no longer be maintained.** OpenSpec `spec.md` files now live in
  each **service repo** (kinoa-dev keeps working exactly as before; whether it still
  copies specs into kinoa-specs is orthogonal and irrelevant to QA).
- The QA source of truth becomes **Jira Story + product-requirement description (PRD)
  + OpenSpec spec files** — read from wherever they now live.
- The pipeline is **SoT → Test Plan → Test Cases → Allure TestOps**, and from there
  the scenarios are tested and automated.

We therefore need a **standalone QA plugin** that assembles that source of truth and
produces test cases in Allure TestOps, decoupled from kinoa-dev.

## 2. Goals / non-goals

**Goals (this spec):**
- A standalone Claude Code plugin, `kinoa-qa`, run by a QA engineer for a Jira Story.
- Assemble the SoT (Story + PRD + specs), generate a validator-checked **Test Plan**,
  and — after a human gate — **upsert Test Cases into Allure TestOps** (project KINOA).
- Isolate every external system behind a thin adapter so vendors are swappable and the
  core is testable.
- Reuse and adapt the proven flow-test-plan assets (QA-lens generation contract,
  no-fabrication rule, deterministic validator, `test-plan.md` format), repointed from
  kinoa-specs to TestOps.

**Non-goals (named later stages, designed as seams, not built here):**
- Playwright/automation scaffolding in kinoa-test-automation (downstream stage).
- A CI-triggered, unattended run (the core is built human-gated; a CI hook slots in
  behind the same pipeline later).
- Full Story→subtask→PR auto-discovery (an MVP-level Story-driven discovery ships; the
  exhaustive walk is a later refinement behind the same interface).

## 3. Decisions (resolved in brainstorming)

| # | Decision | Choice |
|---|---|---|
| System of record | Where cases durably live | **Allure TestOps** (project KINOA); git files are reviewable intermediates only |
| Spec discovery | How specs are found across 20+ repos | One `SpecResolver` interface; **Story-driven discovery** now, exhaustive auto later |
| PRD source | What "PRD" is | **Story description/AC (baseline) + linked Confluence (enrichment)** |
| Trigger | Who runs it, where the gate is | **QA-run, local, human-gated** before any TestOps write; CI hook later |
| Scope | Where the plugin ends | **At TestOps cases**; Playwright automation is a later stage |
| Repo access | Reading service repos | **`gh` remote (default)**, `--spec-path` local override |
| SoT hardness | What is required | **Only the Jira Story**; PRD and specs both degrade gracefully if absent |

## 4. Architecture

A new, fully standalone GitHub repo **`kinoa-qa`**, packaged as a Claude Code plugin
that mirrors kinoa-dev's structure (so install/marketplace mechanics are identical).

```
kinoa-qa/                         ← new standalone repo, QA-owned
├─ .claude-plugin/plugin.json     ← manifest (same shape as kinoa-dev)
├─ marketplace.json               ← install source
├─ skills/
│  └─ testplan/                   ← orchestrator skill (the "flow")
│     ├─ SKILL.md                 ← Steps A–E: assemble → generate → validate → gate → upsert
│     ├─ references/
│     │  ├─ sot-assembly.md       ← gather + merge the three inputs, hardness tiers
│     │  ├─ generation.md         ← QA-lens rules (adapted from flow-test-plan)
│     │  ├─ test-plan-format.md   ← reviewable intermediate + TestOps field mapping
│     │  └─ testops-sync.md       ← upsert / idempotency / traceability
│     ├─ scripts/
│     │  ├─ validate_test_plan.py         ← deterministic, adapted from flow-test-plan
│     │  └─ test_validate_test_plan.py
│     ├─ evals/evals.json
│     └─ services.json            ← optional service→repo override registry
└─ docs/superpowers/specs/…       ← this design doc lives here once the repo exists
```

**Command.** Slash commands derive from the skill *name* (a lesson from flow-test-plan),
so skill `testplan` → **`/kinoa-qa:testplan <STORY-KEY> [--target …] [--repo …] [--spec-path …] [--dry-run]`**.

**Decoupling from kinoa-dev (hard rule).** `kinoa-qa` has **zero code dependency** on
kinoa-dev. It depends only on *artifacts and conventions* kinoa-dev produces — OpenSpec
`spec.md` files in service repos, and the Jira/[AQA] conventions. We **lift-and-adapt**
(copy, not import) the four reusable flow-test-plan assets and repoint them at TestOps.

**Orchestration shape.** The main agent orchestrates and validates; heavy reading (the
Story/PRD/spec → cases derivation) happens in a **fresh-context generation subagent**,
exactly as in flow-test-plan. Every external system is reached only through an adapter.

## 5. The pipeline (Steps A–E)

**Step A — SoT assembly** (main agent, via adapters, no writes):
- `RequirementsReader.story(<STORY-KEY>)` → Jira Story description + acceptance criteria
  (Atlassian MCP `getJiraIssue`) and its subtasks; also extracts the **affected-repo
  references** carried by the Story (see §6).
- `RequirementsReader.prd(<STORY>)` → linked Confluence pages (`getConfluencePage` /
  remote links) — enrichment; absent is fine.
- `SpecResolver(service, capability[, ref])` → `spec.md` text per resolved target —
  enrichment; unresolvable is fine (see §7).
- Produces one in-memory **SoT bundle**: `{ story, acceptance, prd?, specs[] }`.

**Step B — Generation** (fresh-context subagent, the only heavy reader): given the SoT
bundle + `generation.md` (QA-lens rules) + `test-plan-format.md`, returns exactly one
artifact — the `test-plan.md` content. Each case carries `type/priority/source/
preconditions/steps/expected`; untestable or scenario-less requirements become `⚠️ GAP`
lines (no fabrication); each case's `source:` traces to a named spec `### Requirement /
#### Scenario` **or** a Story acceptance-criterion.

**Step C — Validate** (deterministic Python, gates the run): `validate_test_plan.py` —
`required-fields`, `source-valid`, `scenario-coverage`, `gap-honesty`. FAIL → one
regeneration retry with the validator detail → still FAIL → stop **before** the human
gate and surface the failing checks. A failing plan never reaches TestOps.

**Step D — Human gate:** the validated `test-plan.md` is written locally and presented
to the QA engineer. **Nothing has touched TestOps yet.** QA edits/approves; edits are
re-validated before Step E.

**Step E — TestOps upsert** (`TestOpsWriter`, Allure MCP): on approval each case is
**idempotently upserted** into project KINOA — `testops_find_testcases` by the stable
traceability key → `testops_create_testcase` or `testops_update_testcase`; the returned
`@allure.id` is written back into `test-plan.md`. `⚠️ GAP` lines are never pushed.

## 6. Vendor adapters (the external-system boundary)

| Adapter | Vendor | Reads/Writes | Backends / notes |
|---|---|---|---|
| `SpecResolver` | GitHub / filesystem | reads `spec.md` (+ delta when present) | `gh` remote (default, ref-pinnable); `--spec-path` local; discovery from the Story |
| `RequirementsReader` | Atlassian MCP | reads Jira + Confluence | Jira Story/AC (required); Confluence PRD (optional); extracts affected-repo refs |
| `TestOpsWriter` | Allure MCP | writes/updates cases | `find`/`create`/`update` testcase, `create_sharedstep`; `--dry-run` logs intended calls |

**`SpecResolver` — reading `spec.md` across 20+ repos.** One job: given
`(service, capability[, ref])` return the spec text. The plugin talks only to this,
never to GitHub/filesystem directly — that is what lets discovery evolve without
touching the generator.

- **Default backend — GitHub via `gh`:**
  `gh api repos/<owner>/<repo>/contents/openspec/specs/<capability>/spec.md --jq .content | base64 -d`
  (optionally `?ref=<sha|branch|PR-head>`). Chosen because QA machines don't keep all
  20+ repos cloned, `gh` is already authenticated, reads are stateless, and a ref pins
  traceability.
- **Override backend — local path:** `--spec-path <dir>` / `--repo-root <path>` reads
  `openspec/specs/<capability>/spec.md` off a checkout (offline / already-cloned repos).

**Discovery — Story-driven.** The `RequirementsReader` extracts affected-repo
references from the Story and hands them to `SpecResolver`. The Story-reference
convention is **not yet firmly established**, so the resolver accepts the common forms
**in priority order** and degrades:
1. **Jira dev-status** linked PRs/branches (most precise — pins owner/repo + ref);
2. **remote/issue links** to the repos (ref defaults to the repo's default branch);
3. a **structured field / labels** mapped to repos (via `services.json` for owner +
   `specs_root`);
4. **manual override** — `--repo owner/name` / `--target service/capability` /
   `--spec-path`.

Design note: QA should standardize on one Story-reference form to make discovery
reliable; the resolver tolerates all four until then. The exhaustive
subtask→PR walk is a later refinement behind this same interface.

## 7. SoT model & hardness tiers

- **Required:** the Jira Story (description + acceptance criteria). A missing Story /
  Atlassian-down is the **only** hard stop.
- **Enrichment, degrade independently if absent:** Confluence **PRD** and service-repo
  **specs**. Either or both may be missing and the pipeline still runs.

A run from **Story + PRD alone** (no specs) is a first-class, supported mode — not a
failure path. In that mode `scenario-coverage` is N/A and the quality check becomes
"every acceptance criterion is represented, nothing fabricated"; each case's `source:`
cites a Story AC (e.g. `KING-22737 › AC-2`). When specs are resolvable they add spec
scenarios as additional case sources and enable richer, more precise cases.

## 8. `test-plan.md` format & TestOps mapping

One `test-plan.md` per `(service, capability)` (or per Story when spec-less) holds
**N cases**; at Step E **each `TC-n` becomes exactly one Allure TestOps case**. The
`.md` is the reviewable intermediate; TestOps is the system of record.

```markdown
# QA Test Plan — kinoa-client-support-tool / admin-authentication
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: kinoa-client-support-tool/admin-authentication@<ref> · generated: 2026-09-04 · spec-sha: a1b2c3d4e5f6

## Cases

### TC-1 · A tenant token creates an Author account
- type: functional            # functional | negative | edge | regression | e2e | nonfunctional
- priority: P1                # P1 | P2 | P3
- source: admin-authentication › Google Workspace sign-in › A tenant token creates an Author account
- preconditions: no account row exists for anna@kinoa.io
- steps:
  1. present an OIDC user request (email=anna@kinoa.io, hd=kinoa.io, email_verified=true)
  2. invoke the OIDC user service to load that user
- expected: a principal for anna@kinoa.io is returned AND exactly one account row exists with role AUTHOR

## Gaps
- ⚠️ GAP: Rate-limit headers on the token endpoint — spec states no observable behavior to assert
```

**Field → TestOps mapping (Step E):**

| test-plan.md field | Allure TestOps case field |
|---|---|
| `### TC-n · <title>` | case **name** |
| `type` | **tag** (`functional`/… + constant `spec-derived` tag) |
| `priority` (P1/P2/P3) | **severity** (critical/normal/minor) |
| `source` | **description** + `source` label + Jira **link** to the Story |
| `preconditions` | **precondition** field |
| `steps` | **scenario steps** |
| `expected` | **expected result** |
| — (post-upsert) | `@allure.id` written back into the `.md` |

**Idempotency / traceability key.** Each case carries a deterministic label,
`traceability = <STORY>/<service>/<capability>/<source-scenario-slug>` (slug = lowercase,
non-alphanumeric runs collapsed to `-`, trimmed). Step E finds by this label — not the
fuzzy title — then updates or creates. Re-running a Story is always safe: 0 duplicates.

## 9. Error handling & degradation

Principle: **read-only until the human approves; then idempotent, so any failure is
safe to re-run.**

| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | Hard stop at Step A (Story is the required baseline). Nothing written. |
| Confluence PRD missing/unreachable | Proceed Story-only; header records `prd: none`. Not an error. |
| Spec unresolved (not found / unregistered / `gh` unauthed / target fails) | **Do not break.** Continue with Story + PRD; header records `specs: none (<reason>)`; warn at the gate; surface the resolver error so QA can fix and re-run for fuller coverage. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Generation subagent fails | One retry, then stop and surface. |
| Validator FAIL | One regeneration retry → still FAIL → stop **before** the gate, surface failing checks. Never ships. |
| QA rejects at the gate | Nothing pushed; edits re-validated before Step E. |
| TestOps write fails mid-batch (partial upsert) | No rollback — every upsert is keyed and independent; a re-run finds-and-updates what landed and creates the rest. Report per-case; write `@allure.id`s back as they succeed. |
| TestOps unreachable at Step E | The reviewed `test-plan.md` is on disk — nothing lost. Re-run Step E later against the same file. |

**Invariants (hard rules).**
- Service repos are **read-only** — never written.
- TestOps is written **only after human approval** (Step D gate).
- Upserts are **idempotent, keyed by traceability label** — safe re-runs, no duplicates.
- **No fabrication** — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- The **deterministic validator gates** before the human sees the plan.
- **Standalone** — zero code dependency on kinoa-dev.

## 10. Testing strategy

Weighted toward the two highest-risk parts: the deterministic validator and the
idempotent TestOps upsert (because TestOps is the system of record).

1. **Validator unit tests (no LLM).** Lift flow-test-plan's `test_validate_test_plan.py`
   and extend: `source-valid` accepts a spec scenario *or* a `KING-… › AC-n` citation;
   `scenario-coverage` is **skipped when `specs: none`** (mode check = every AC
   represented); `gap-honesty`, `required-fields` (incl. `preconditions`), em-dash
   `⚠️ GAP` format unchanged. Fixtures for both modes (spec-grounded and business-only).
2. **Generation evals (`evals.json` harness).** Small **synthetic golden fixtures** as
   the backbone → assert plan *properties* (coverage, no-fabrication, `source:`
   traceability, degradation modes: Story-only, Story+PRD-no-specs, PRD-absent). The
   real 71-case admin-authentication capability is kept only as an **optional** larger
   sample, not the backbone.
3. **Adapter contract tests + `--dry-run`.** Each adapter tested against a stub;
   `SpecResolver` → local fixture + recorded `gh api` payload; `RequirementsReader` →
   recorded Jira/Confluence JSON; `TestOpsWriter --dry-run` → logs the exact
   create/update calls (with keys) instead of hitting TestOps (also the QA preview of
   Step E).
4. **Idempotency test (highest-risk).** Run twice against one fixture through the
   `TestOpsWriter` stub → assert the second run is **0 creates, N updates** on the same
   keys. A bug here corrupts the system of record, so this is the flagship test.
5. **Manual acceptance smoke.** One real end-to-end run on a chosen capability against
   project KINOA (dry-run, then a real upsert into a `spec-derived` suite), validating
   `@allure.id` write-back and the chain Story → (spec scenario | AC) → TC-n → TestOps.

## 11. Open questions & future work

- **Story→repo reference convention** — standardize on one form (dev-status preferred)
  so `SpecResolver` discovery is reliable; the resolver tolerates all four until then.
- **Auto-resolver** — the exhaustive subtask→PR walk, behind the existing interface.
- **Playwright/automation stage** — scaffold from TestOps `@allure.id`s in
  kinoa-test-automation (reuse the pilot / a `testops-to-playwright` flow).
- **CI hook** — an unattended run behind the same pipeline, review shifting into TestOps.
- **TestOps structure** — suite/tree layout for `spec-derived` cases in project KINOA
  (epic = service, feature = capability, story = requirement) to confirm with the team.
- **Fate of flow-test-plan / PR #17** — decide whether the kinoa-specs-based skill is
  retired, frozen, or kept for repos still syncing to kinoa-specs.
