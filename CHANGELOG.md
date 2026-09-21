# Changelog

What changed in each released version of the `kinoa-qa` plugin, newest first.

Check the version you have with `claude plugin list`; if it is older than the top entry here,
update with the two commands in the README's **Versions and updating** section.

The version lives in `.claude-plugin/plugin.json` and nowhere else. Claude Code updates an
installed plugin **only when that string changes**, so a merge that does not bump it never
reaches anyone who already installed the plugin.

## 0.2.0 — 2026-09-21

**Step A now reads image attachments on the Jira Story.** A requirement that lives in a
screenshot pasted into the Story becomes an acceptance criterion instead of a `⚠️ GAP`.

- Images join the **authoritative tier** of the SoT bundle, with the Story, the PRD and Figma
  frames: what an image shows may ground an `expected:`.
- New optional case field `image-ref: <attachment-id> — <filename>`, validated offline by the
  new `image-ref-valid` check (syntax and `ac:`-source pairing only, never a Jira call).
- `image` joins `story` / `prd` / `design` / `openspec` as a `## Conflicts` source.
- New `images:` header line: `<n> read`, `<n> read (<k> failed: <reason>)`, `none`, or
  `none (<reason>)`.
- Image provenance rides the `Provenance:` line on the TestOps `description`, exactly as
  `openspec-ref` and `design-ref` do.

**Action required to use it:** export `JIRA_EMAIL` and `JIRA_API_TOKEN` (a scoped token needs
`read:jira-work`). Without them the run continues and records
`images: none (jira credentials not set)` — it is never a hard stop, so an un-configured
install behaves exactly as 0.1.0 did.

The Jira cloud id is resolved automatically from `jira_base_url`; a scoped token cannot use the
site host, and nothing about that needs configuring.

## 0.1.0

First released version: the `/kinoa-qa:testplan` orchestrator — Jira Story (+ optional
Confluence PRD, linked Figma mockups and service-repo OpenSpec specs) into a validator-checked
`test-plan.md`, then an idempotent Allure TestOps upsert behind a human gate.
