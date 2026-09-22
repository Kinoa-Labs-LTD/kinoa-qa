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
| **Jira REST (attachments)** | Optional, Step A | Reading image attachments on the Story | Without `JIRA_EMAIL` + `JIRA_API_TOKEN` the run continues and the header records `images: none (jira credentials not set)`. |

OpenSpec specs are read with the `gh` CLI, not an MCP server; a repo with no OpenSpec file
is the ordinary path, not a degradation.

## Install

The plugin is a Claude Code plugin served from this repository, which is its own marketplace
(`.claude-plugin/marketplace.json`). Two routes, both ending in the same place:

**From GitHub — for anyone using the plugin.** In Claude Code:

```
/plugin marketplace add Kinoa-Labs-LTD/kinoa-qa
/plugin install kinoa-qa@kinoa-qa
```

**From a local checkout — for working ON the plugin.** Point the marketplace at the directory
instead, so your edits are live without a reinstall:

```
/plugin marketplace add /path/to/kinoa-qa
/plugin install kinoa-qa@kinoa-qa
```

The same two steps work from a terminal, outside a Claude Code session:

```
claude plugin marketplace add Kinoa-Labs-LTD/kinoa-qa
claude plugin install kinoa-qa@kinoa-qa
```

Either route writes to `~/.claude/settings.json`. The result looks like this — the same shape
the sibling `kinoa-pm` and `kinoa-dev` plugins use, though those point at local directories
rather than GitHub — and you can equally well write it by hand:

```json
{
  "enabledPlugins": { "kinoa-qa@kinoa-qa": true },
  "extraKnownMarketplaces": {
    "kinoa-qa": { "source": { "source": "github", "repo": "Kinoa-Labs-LTD/kinoa-qa" } }
  }
}
```

For a local checkout the source is `{ "source": "directory", "path": "/path/to/kinoa-qa" }`.

Verify with `/plugin` — `kinoa-qa` should be listed as enabled, and `/kinoa-qa:testplan`
should complete as a command.

## Configure

`config.json` ships with the three Allure custom-field defaults **empty on purpose**, so no
run inherits another team's values by accident:

```json
"custom_fields": { "story": "", "component": "", "feature": "" }
```

Leave them empty and every run must pass `--story-field` and `--component`, plus
`--feature` under Story scope; otherwise Step E stops before writing anything, naming each
missing field. Fill them in and those flags become optional overrides. **This is the most
common reason a first run stops.**

Under `--scope e2e` the Feature is set for you to `e2e scope`, so `--feature` there is an
**error** rather than a silent discard — pass only the other two.

`services.json` maps a service name to the repo its OpenSpec files live in. A service that
isn't listed is fine — OpenSpec input is optional throughout.

### Jira API token

Two environment variables let Step A read files attached to the Story — today that means
**image attachments**, so a requirement that lives in a pasted screenshot becomes an
acceptance criterion instead of a gap:

```bash
export JIRA_EMAIL="you@kinoa.io"
export JIRA_API_TOKEN="<token>"
```

Create the token at **id.atlassian.com → Security → API tokens**. The plugin owns no
credentials, exactly as it owns no MCP configuration: it reads these two variables and
nothing else.

**Required scopes.** A token created *with* scopes needs `read:jira-work` — that is what
covers issues and their attachments. `write:jira-work` is not used. A classic token created
*without* scopes works too and needs nothing configured.

**Note for scoped tokens.** A scoped token cannot call `https://<site>.atlassian.net/rest/...`
at all — that host answers **403** no matter which scopes the token holds. Only
`https://api.atlassian.com/ex/jira/<cloudId>/rest/...` works. You do **not** configure that:
`jira_base_url` stays the ordinary site URL and the cloud id is looked up automatically. It is
worth knowing when a token looks correct and a call still returns 403.

Each image is capped at 10 MB; a larger attachment is skipped with its reason and the others
are still read.

**If the variables are unset** the run continues — the header records
`images: none (jira credentials not set)` and the gate warns. Missing credentials are never a
hard stop; they only mean no image-derived acceptance criteria.

## Usage

```
/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>]
[--openspec-path <dir>] [--story-field <value>] [--component <value>] [--feature <value>]
[--scope e2e|story] [--allow-unverified-fields] [--dry-run]
```

`--scope` sets the plan's **test scope**: `e2e` marks a cross-component journey (Feature
`e2e scope`, cases created for `Review`, several expected results allowed per step), and
`story` — the default when the flag and the plan header are both absent — keeps the caller's
Feature and creates cases as `Draft`. One run produces one kind of test. The scope is written
into the plan header and carried forward by `plan_writer.py` when a regeneration drops it; a
scope that changed is *reported* at the Step D gate rather than applied silently. Treating the
header as the source of truth from then on — aborting when a later `--scope` disagrees with it
instead of flipping cases that were already pushed — is an orchestrator rule in `SKILL.md`
Step B, not a check any script performs.

`--dry-run` prints the intended TestOps actions and writes nothing.

### Three runs you will actually type

```bash
# a dry run — writes nothing to Allure TestOps
/kinoa-qa:testplan KING-1234 --dry-run

# a real run, Story-scoped
/kinoa-qa:testplan KING-1234 --story-field Template --component Game-Settings --feature In-Apps

# an end-to-end journey plan
/kinoa-qa:testplan KING-1234 --scope e2e --story-field Template --component Game-Settings
```

**A dry run** does everything except write. Steps A–D run in full — the Story is read, the plan
is generated to its stable path, the validator gates it — and Step E performs only its
read-only lookups, printing the create/update it *would* do per case. It still needs the
custom-field values (Gate 0b runs, so a preview cannot promise a batch that could not land),
and it never writes an `allure-id:` back into the plan. Use it to see what a first push would
do to a project you share with other people.

**A real run, Story-scoped** is the ordinary run and the default — `--scope story` is what you
get when neither the flag nor the plan header says otherwise. It produces the test cases for
*one Story's own behaviours*: each case asserts one acceptance criterion, each step carries
**exactly one** `→ expected:` (a second one fails validation, naming the step), and the cases
arrive in TestOps as **`Draft`** under the `Feature` you passed. This is the run to reach for
when you are covering a ticket.

**An end-to-end journey plan** is the same Story read with a different question: not "does this
criterion hold?" but "does the whole cross-component path work?". Under `--scope e2e` three
things change and nothing else does:

- a step may carry **several** `→ expected:` lines, each becoming its own expected-result block
  in TestOps, in the order written — that is what makes a long journey expressible;
- `Feature` is set for you to **`e2e scope`**, so passing `--feature` there is an **error**
  rather than a silently discarded value;
- cases are created as **`Review`** instead of `Draft`.

`Suite`, `Story`, `Component`, the Jira link, the tags and the description are identical in
both scopes.

The two scopes never collide: each writes its own plan file (`…-story.test-plan.md` /
`…-e2e.test-plan.md`) and reconciles against its own set of cases in TestOps, so one Story can
have both without either run rewriting the other's cases. The scope is recorded in the plan
header, and from then on **the header wins** — a later `--scope` that disagrees aborts the run
rather than flipping the status and Feature of cases already pushed. To change it, edit the
`scope:` line in the plan yourself, or delete the plan.

One limitation worth knowing before you choose `e2e`: this repo does **not** encode your e2e
suite's authoring conventions — its naming grammar, stepper structure and publish/WS blocks
live outside it. An e2e plan generated here follows the same rules as any other plan
(every case grounded in an acceptance criterion, `purpose:` beginning "Verify"), and the QA
engineer supplies the house style. See `skills/testplan/references/generation.md`, "What this
plugin does NOT know about e2e authoring".

See `skills/testplan/SKILL.md` for the flow and `skills/testplan/references/` for the current
format and vocabulary. `docs/superpowers/` holds the original design and plan as dated historical
records — they predate later vocabulary changes and are not authoritative.

## Versions and updating

Which version you have:

```
claude plugin list
```

Compare it with the top entry in [CHANGELOG.md](CHANGELOG.md). If yours is older, update:

```
/plugin marketplace update kinoa-qa
/plugin update kinoa-qa@kinoa-qa
```

(The same two commands work outside a session as `claude plugin marketplace update …` /
`claude plugin update …`.) Updates are **not** automatic unless you turn on auto-update for
this marketplace yourself, in `/plugin` → Marketplaces.

### For contributors

The version lives in `.claude-plugin/plugin.json` and **nowhere else** — deliberately. Claude
Code resolves a plugin's version from `plugin.json` first and the marketplace entry second, and
silently ignores the loser when both are set, so the marketplace entry carries no `version` at
all.

**A PR that changes behaviour bumps that version and adds a `CHANGELOG.md` entry, in the same
PR.** This is not bookkeeping: Claude Code updates an installed plugin only when the version
*string changes*, so merging a feature without a bump ships it to nobody — the people who
already installed the plugin keep running the old code and have no way to tell. Semver:
patch for a fix, minor for a feature, major for a change that breaks an existing plan or
workflow.