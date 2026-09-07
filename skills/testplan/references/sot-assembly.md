# sot-assembly.md — Step A (read-only)

Assemble the SoT bundle `{ story, acceptance, prd?, specs[] }`. Only the Story is
required; PRD and specs each degrade independently.

## RequirementsReader (Atlassian MCP)
1. `getJiraIssue(<STORY-KEY>)` → description + acceptance criteria + subtasks.
   Missing Story / MCP down → HARD STOP (the one required input).
2. **Affected-repo + capability discovery** — validated on KING-20951, implemented in
   `scripts/spec_resolver.py` (gh-only, no Jira dev-status needed):
   a. `keys = story + subtasks`; for each, `gh search prs "<key>" --owner <ORG>`;
   b. keep PRs whose **title starts with one of those keys** (drops "Release to *"
      aggregate PRs and cross-referenced tickets); the Atlassian MCP does **not**
      expose Jira dev-status, so title is the signal;
   c. for each kept PR, `gh api repos/<repo>/pulls/<n>/files` → match
      `openspec/(changes/<id>/)?specs/<cap>/spec.md` → the exact `<cap>`;
   d. read the archived `openspec/specs/<cap>/spec.md` at the repo default branch;
   e. repos with no OpenSpec spec change (pure-frontend, older services) contribute
      nothing → that slice runs business-only.
   Fallbacks when the key-in-PR convention is absent: `services.json` mapping, or the
   CLI overrides `--repo` / `--target` / `--spec-path`.
3. PRD: for each Confluence link on the Story, `getConfluencePage(id)`. Absent → skip,
   set `specs`/`prd` degradation notes in the header. Never a hard stop.

## SpecResolver (GitHub `gh` default; local override)
Interface: `(service, capability[, ref]) -> spec text`. Backends:
- **Default — `gh` remote:**
  ```bash
  gh api "repos/<owner>/<repo>/contents/<specs_root>/<capability>/spec.md?ref=<ref>" --jq '.content' | base64 -d
  ```
  `<specs_root>` defaults to `openspec/specs` (from `services.json` or convention).
- **Override — local:** `--spec-path <dir>` reads `<dir>/openspec/specs/<capability>/spec.md`.

Any resolution failure (not found / unregistered / `gh` unauthed / one target fails) is
NON-fatal: continue in business-only mode, record `specs: none (<reason>)` in the header,
and surface the error at the human gate. `--continue-on-missing` opts into partial
multi-target runs; the default aborts a multi-target run only if the QA engineer asks.

## spec-sha
When a spec is resolved, record `spec-sha: <first 12 of sha256(spec text)>` in the header
for traceability; `none` in business-only mode.
