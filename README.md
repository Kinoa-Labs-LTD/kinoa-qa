# kinoa-qa

QA plugin for Claude Code. Turns a Jira Story (+ optional Confluence PRD + optional linked
Figma mockups + optional service-repo OpenSpec specs) into a validator-checked QA **Test Plan**, then — after a
human review gate — idempotently upserts **Test Cases into Allure TestOps** (project KINOA).

Standalone and decoupled from `kinoa-dev`: it depends only on the artifacts kinoa-dev
produces (OpenSpec `spec.md` files in service repos) and the Jira/[AQA] conventions.

## Prerequisites

The plugin ships **no `mcpServers` config**. Every server below is connected in the host
environment (your Claude Code MCP settings); the plugin probes for the tools at runtime.

| Server | Required? | Used for | If missing |
|---|---|---|---|
| **Atlassian** | Required | Jira Story (Step A, the one required input) and the Confluence PRD | No Story → hard stop at Step A. PRD only → header `prd: none (<reason>)`, warn at the gate, continue. |
| **Allure TestOps** | Required for Step E | Finding and upserting cases in project KINOA | Steps A–D still run and `test-plan.md` is on disk; the upsert is deferred until the server is back. `--dry-run` needs it only to print intended actions. |
| **Figma** | Optional | Reading mockup frames linked from the Story (`get_screenshot`, `get_design_context`) — **remote server preferred** (works headless), with the **local desktop server** as fallback | Header `design: none (<reason>)`, warn at the gate, continue — never a hard stop. Mockup-derived acceptance criteria are simply absent. |

OpenSpec specs are read with the `gh` CLI, not an MCP server; a repo with no OpenSpec file
is the ordinary path, not a degradation.

## Usage

```
/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>] [--openspec-path <dir>] [--dry-run]
```

See `skills/testplan/SKILL.md` for the flow and `skills/testplan/references/` for the current
format and vocabulary. `docs/superpowers/` holds the original design and plan as dated historical
records — they predate later vocabulary changes and are not authoritative.