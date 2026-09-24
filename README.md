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

Leave them empty and every run must pass `--story-field`, `--component` and `--feature`;
otherwise Step E stops before writing anything, naming each missing field. Fill them in and
those flags become optional overrides. **This is the most common reason a first run stops.**

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
[--allow-unverified-fields] [--dry-run]
```

Every plan this command generates is an **e2e plan** — the full-coverage format: per-AC
functional, negative, edge, regression and nonfunctional cases, `scope: e2e` written in the
plan header, cases created in TestOps as **`Review`** under the `Feature` you passed. There is
no flag that changes the format. The other format, `smoke` — one short functional scenario,
created as `Draft` — is not generated by this command, and no flow of this plugin produces
one yet; smoke plans are made outside it. The validator accepts both (`scope: smoke | e2e`; a
plan without the line is e2e) and rejects anything else, the retired `story` value included.
This command validates and pushes e2e plans only: a plan whose header says `scope: smoke`
stops at Step C and is never pushed.

`--dry-run` prints the intended TestOps actions and writes nothing.

### Every argument, and whether you must pass it

| Argument | Required? | What it is for |
|---|---|---|
| `<STORY-KEY>` | **Always** | The Jira Story to build the plan from — the one genuinely mandatory input. No Story, no run: Step A hard-stops. Everything else in the bundle (PRD, mockups, images, specs) degrades without stopping the run. |
| `--story-field <value>` | **For Step E**, unless `testops.custom_fields.story` is filled in | The Allure `Story` custom field. Checked before any write: the value must already be in use in the project, because Allure rejects an unknown value *silently* and fails the whole creation. |
| `--component <value>` | **For Step E**, unless `testops.custom_fields.component` is filled in | The Allure `Component` custom field. Same pre-flight check. |
| `--feature <value>` | **For Step E**, unless `testops.custom_fields.feature` is filled in | The Allure `Feature` custom field. Same pre-flight check. The plugin never sets it for you. |
| `--target <service>/<capability>` | Optional | Names which service capability the plan covers. It decides the plan's filename, is written into each case's `Target:` marker — which is how a re-run finds its own cases — and tells the OpenSpec resolver which `spec.md` to look for. Without it the plan is `<STORY-KEY>-no-target-e2e.test-plan.md`. |
| `--repo <owner>/<name>` | Optional | Overrides which GitHub repo the OpenSpec spec is read from, when the Story's PRs don't identify it and `services.json` has no mapping. |
| `--openspec-path <dir>` | Optional | Reads the spec from a local checkout (`<dir>/openspec/specs/<capability>/spec.md`) instead of GitHub. Useful when the spec isn't pushed yet. |
| `--allow-unverified-fields` | Optional | Downgrades one pre-flight check to a warning: the check proves a custom-field value is *in use*, never that it exists, so a value you just created in Allure that no case uses yet would otherwise abort the run. Use it when you know the value is real. |
| `--dry-run` | Optional | Writes nothing to Allure TestOps and never refuses. Steps A–D run in full; Step E performs only its read-only lookups and prints the create/update it would do per case. |

Only `<STORY-KEY>` is unconditionally required. The three custom-field flags are the usual
reason a first run stops — `config.json` ships their defaults **empty on purpose**, so that no
run inherits another team's values by accident. Fill them in once and the flags become
optional overrides.

### Three runs you will actually type

```bash
# a dry run — writes nothing to Allure TestOps
/kinoa-qa:testplan KING-1234 --dry-run

# a real run
/kinoa-qa:testplan KING-1234 --story-field Template --component Game-Settings --feature In-Apps

# a real run for one service capability, enriched by its OpenSpec spec
/kinoa-qa:testplan KING-1234 --target in-app-templates/export --story-field Template --component Game-Settings --feature In-Apps
```

**A dry run** does everything except write. Steps A–D run in full — the Story is read, the plan
is generated to its stable path, the validator gates it — and Step E performs only its
read-only lookups, printing the create/update it *would* do per case. It still needs the
custom-field values (Gate 0b runs, so a preview cannot promise a batch that could not land),
and it never writes an `allure-id:` back into the plan. Use it to see what a first push would
do to a project you share with other people.

**A real run** covers the Story. Every acceptance criterion is cited by at least one case (an
uncovered AC fails validation); a case may cite several (`source: ac: AC-1, AC-2`); a step
carries one or more `→ expected:` lines, each becoming its own expected-result block in
TestOps, in order; and the cases arrive in TestOps as **`Review`** under the `Feature` you
passed. `type:` is one of `functional`, `negative`, `edge`, `regression` or `nonfunctional`,
and is not pushed.

**A run with `--target`** is the same run scoped to one service capability: the target names
the plan file (`KING-1234-in-app-templates-export-e2e.test-plan.md`), is written into each
case's `Target:` marker so a re-run finds its own cases, and tells the OpenSpec resolver which
`spec.md` to read as context.

The plan file always ends in `-e2e`. A plan left from an earlier version at a
`…-story.test-plan.md` path is **not read**: rename it to `…-e2e.test-plan.md` and set
`scope: e2e` in its header before the next run. Its `allure-id:` lines then carry over, and
Step E updates those cases by id. Without the rename they are lost, and reconciliation does
not find the old cases either: a TestOps case whose `Target:` marker still carries the old
Story scope value is outside the e2e in-scope set, so it is neither matched nor reported, and
the run creates the cases again. Project KINOA has no such case (checked 2026-09-24: no
plugin-authored case existed before 0.3.0).

One limitation worth knowing: e2e is this plugin's default output, but it does **not** encode
your e2e suite's house style — its naming grammar, stepper structure and publish and WS/InBox
blocks live outside this repo and are not ported. A generated plan follows the rules this repo
validates (every case grounded in an acceptance criterion, `purpose:` beginning "Verify"), and
the generator is told not to invent that house style. See
`skills/testplan/references/generation.md`, "What the e2e suite's house style is".

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