# kinoa-qa

QA plugin for Claude Code. Three skills:

- **`/kinoa-qa:testplan`** turns a Jira Story (+ optional Confluence PRD + optional linked
  Figma mockups + optional service-repo OpenSpec specs) into a validator-checked QA **Test
  Plan**, then — after a human review gate — idempotently upserts **Test Cases into Allure
  TestOps** (project KINOA). See [Usage: `/kinoa-qa:testplan`](#usage-kinoa-qatestplan).
- **`/kinoa-qa:smoke-plan`** turns a Jira Story into a **"Smoke test" sub-task** on that Story:
  a few numbered steps, one expected result each, every result tagged with its source (the
  acceptance criteria, the PRD, the Figma design). It writes to Jira only, after you confirm.
  See [Usage: `/kinoa-qa:smoke-plan`](#usage-kinoa-qasmoke-plan).
- **`/kinoa-qa:smoke-run`** runs that sub-task against the built feature in a real browser
  through the Playwright MCP, and reports whether the feature is **live** and whether it
  **conforms** — as a comment on the sub-task, with the evidence attached, plus a published
  artifact. See [Usage: `/kinoa-qa:smoke-run`](#usage-kinoa-qasmoke-run).

A smoke plan is a Jira sub-task, not a `test-plan.md`. `testplan` reads one only when you ask
it to push that sub-task to TestOps as one case, with `/kinoa-qa:testplan --from-smoke
<SUBTASK-KEY>` — see [Pushing a smoke sub-task to TestOps](#pushing-a-smoke-sub-task-to-testops).

**Presenting this to someone?** Two guide pages tell the story for people who will not open this
repo: the [kinoa-qa plugin guide](https://claude.ai/artifact/WDruZqhHZKEtAxTjabUS9S) (the whole
plugin) and the [smoke testing guide](https://claude.ai/code/artifact/a92e7012-7787-46ba-8404-19a9b2a62cc7)
(the smoke pair). Their sources are in [`docs/guides/`](docs/guides/README.md); this README stays
the reference you use mid-task.

Standalone and decoupled from `kinoa-dev`: it depends only on the artifacts kinoa-dev
produces (OpenSpec `spec.md` files in service repos) and the Jira/[AQA] conventions.

## Prerequisites

The plugin ships **no `mcpServers` config**. Every server below is connected in the host
environment (your Claude Code MCP settings); the plugin probes for the tools at runtime.

| Server / tool | Needed by | Used for | If missing |
|---|---|---|---|
| **Atlassian** | `testplan` — required | Jira Story (Step A, the one required input) and the Confluence PRD | No Story → hard stop at Step A. PRD only → header `prd: none (<reason>)`, warn at the gate, continue. |
| **Atlassian** | `smoke-plan`, `smoke-run` — required | `smoke-plan` reads the Story, its remote links and the PRD, then creates the sub-task and comments open questions on the Story. `smoke-run` reads the sub-task and its remote links, updates the sub-task's `Latest run:` line and raises Sub-bugs | Neither skill has anything to work from without it. |
| **Allure TestOps** | `testplan` — required for Step E | Finding and upserting cases in project KINOA | Steps A–D still run and `test-plan.md` is on disk; the upsert is deferred until the server is back. `--dry-run` needs it only to print intended actions. |
| **Allure TestOps** | `smoke-run` — not used | Nothing. The case id comes from a Jira remote link `Allure TestOps case <id>` on the sub-task (written by `testplan --from-smoke`) or from you, and the MCP cannot upload a launch | Not checked. `smoke-plan` does not use it either: it creates no TestOps case. |
| **Figma** | `testplan` — optional | Reading mockup frames linked from the Story (`get_screenshot`, `get_design_context`) — **remote server preferred** (works headless), with the **local desktop server** as fallback | Header `design: none (<reason>)`, warn at the gate, continue — never a hard stop. Mockup-derived acceptance criteria are simply absent. |
| **Figma** | `smoke-plan` — optional, strongly preferred | Reading labels, control states, validation copy and empty/error states off the Story's frames, so expected results are concrete | The draft says design grounding was unavailable and grounds on the acceptance criteria and the PRD. Access needs team membership **and** a Dev seat — see [Usage: `/kinoa-qa:smoke-plan`](#usage-kinoa-qasmoke-plan). |
| **Playwright MCP** | `smoke-run` — required | Driving the browser through the plan's steps | **Checked at the start**: `smoke-run` names it and stops. Not provided by this plugin — see [Playwright MCP](#playwright-mcp-for-smoke-run). |
| **Artifact tool** | `smoke-run` | Publishing the readable mirror of every run report (one artifact per plan, updated in place) | Claude Code's built-in `Artifact` tool, not an MCP server. Not checked at the start. |
| **Jira REST (attachments)** | `testplan` — optional, Step A | Reading image attachments on the Story | Without `JIRA_EMAIL` + `JIRA_API_TOKEN` the run continues and the header records `images: none (jira credentials not set)`. |
| **Jira REST (remote link)** | `testplan --from-smoke` — optional, after Step E | Writing the sub-task's one `Allure TestOps case <id>` remote link (`jira_remote_link.py`), on your yes at the gate | Without `JIRA_EMAIL` + `JIRA_API_TOKEN`, or when Jira refuses the write, the pushed case stays and `testplan` prints the link title and URL for you to add by hand. See [Jira API token](#jira-api-token). |
| **Jira REST (`JIRA_EMAIL` + `JIRA_API_TOKEN`)** | `smoke-run` — required | `jiraReport.mjs` posts the run report as a comment; `jiraAttach.mjs` uploads the evidence screenshots | **Checked at the start**: `smoke-run` names the missing variable and stops. A `jiraReport.mjs … --dry-run` rehearsal needs neither. See [Jira API token](#jira-api-token). |

`smoke-run`'s two scripts are Node (18 or newer) and are run as
`node <plugin>/skills/smoke-run/scripts/<name>.mjs`; they have no npm dependencies.

OpenSpec specs are read with the `gh` CLI, not an MCP server; a repo with no OpenSpec file
is the ordinary path, not a degradation.

### Playwright MCP, for smoke-run

The plugin declares no Playwright server — add it to your own Claude Code MCP settings, for
example:

```
claude mcp add -s user playwright -- npx @playwright/mcp@latest
```

`-s user` registers it at user scope because the smoke skills run from any directory; the
default (local) scope registers the server for the current project only, so `smoke-run`'s start
check would fail everywhere else.

Three things to know:

- **The server must be named `playwright`.** `smoke-run` drives the tools as
  `mcp__playwright__browser_*`; a server registered under another name gives the tools other
  names.
- **Every `mcp__playwright__*` call asks for permission** unless you allow the tools in your
  own settings — the plugin grants none (kinoa-test-automation allow-lists them in its own
  `.claude/settings.json`, which applies only inside that repo). To allow them everywhere, add
  `"mcp__playwright"` to `permissions.allow` in `~/.claude/settings.json`.
- **Screenshots land in `.playwright-mcp/` in the working directory.** kinoa-test-automation
  already ignores that directory; anywhere else, add `.playwright-mcp/` to your own
  `.gitignore` so run evidence is not committed by accident.

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

Verify with `/plugin` — `kinoa-qa` should be listed as enabled, and `/kinoa-qa:testplan`,
`/kinoa-qa:smoke-plan` and `/kinoa-qa:smoke-run` should complete as commands.

## Configure

`config.json` and `services.json` are `testplan`'s; the smoke skills read neither.

`config.json` ships with the three Allure custom-field defaults **empty on purpose**, so no
run inherits another team's values by accident:

```json
"custom_fields": { "story": "", "component": "", "feature": "" }
```

Leave them empty and every run must pass `--story-field`, `--component` and `--feature`;
otherwise Step E stops before writing anything, naming each missing field. Fill them in and
those flags become optional overrides. **This is the most common reason a first run stops.**

`testops.base_url` (`https://kinoa.testops.cloud`) and `testops.project_id` build the case URL
of the remote link `--from-smoke` writes: `<base_url>/project/<project_id>/test-cases/<id>`.

`services.json` maps a service name to the repo its OpenSpec files live in. A service that
isn't listed is fine — OpenSpec input is optional throughout.

### Jira API token

Two environment variables, `JIRA_EMAIL` and `JIRA_API_TOKEN`, are used by two skills:

- **`testplan`**, Step A, reads files attached to the Story with them — today that means
  **image attachments**, so a requirement that lives in a pasted screenshot becomes an
  acceptance criterion instead of a gap. Read only; optional.
- **`testplan --from-smoke`**, after Step E, writes the sub-task's `Allure TestOps case <id>`
  remote link with them (`jira_remote_link.py`). Optional: without them the case is still
  pushed and you add the link by hand.
- **`smoke-run`** posts its run report (`jiraReport.mjs`) and uploads its evidence
  screenshots (`jiraAttach.mjs`) with them. Required, and checked at the start.

The plugin owns no credentials, exactly as it owns no MCP configuration: everything comes from
your shell. `testplan` reads `JIRA_EMAIL` and `JIRA_API_TOKEN`; under `--from-smoke` its link
writer also reads `JIRA_BASE_URL` and `JIRA_HOST`. The two `smoke-run` scripts also read three
optional variables:

| Variable | Read by | Default |
|---|---|---|
| `JIRA_BASE_URL` | both `smoke-run` scripts, and `jira_remote_link.py` | `https://kinoadev.atlassian.net` (`jira_remote_link.py`: `jira_base_url` in `config.json`) |
| `JIRA_CLOUD_ID` | both `smoke-run` scripts | the Kinoa cloud id, for the `api.atlassian.com` gateway (`jira_remote_link.py` looks it up from the site instead) |
| `JIRA_HOST` | `jiraAttach.mjs`, and `jira_remote_link.py` | `auto`. `jiraAttach.mjs` tries the site URL, then the gateway; `jira_remote_link.py` tries the gateway, then the site. `gateway` for a scoped token, `site` for a classic unscoped one |

**One-time setup — one token serves both skills.**

1. Go to [id.atlassian.com → Security → API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   and choose **Create API token with scopes** → **Jira**. Grant only:

   | Scope | Why |
   | --- | --- |
   | `read:jira-work` | View issues and their attachments — all a `testplan` run without `--from-smoke` needs |
   | `write:jira-work` | Post the run report and create attachments (`smoke-run`), and write the sub-task's remote link (`testplan --from-smoke`). A `testplan` run without `--from-smoke` never writes to Jira |

   > ⚠ **Choose the CLASSIC scopes, not the granular ones.** `write:attachment:jira` looks
   > tighter and is what you'd reach for, but granular-scoped tokens **cannot upload
   > attachments at all** — Atlassian's gateway rejects every `POST` with
   > `401 "Unauthorized; scope does not match"` regardless of the scopes granted. It's a
   > confirmed Atlassian bug, not a config error
   > ([details](https://community.developer.atlassian.com/t/401-scope-does-not-match-issue-when-uploading-an-attachment/93805)).
   > `write:jira-work` is broader than we'd like — it also permits editing, commenting as you
   > and deleting issues — but it is the documented workaround.

   If you only run `testplan` without `--from-smoke`, `read:jira-work` alone is enough, and a
   classic token created *without* scopes works too. `--from-smoke` writes one remote link, which
   needs the classic `write:jira-work` scope and the Jira "Link issues" permission on the
   sub-task. **`smoke-run` needs the scoped token:** `jiraReport.mjs` always
   posts through the `api.atlassian.com` gateway, which a classic unscoped token cannot use — it
   passes `smoke-run`'s start check (which only sees that the variables are set) and fails at the
   final post.
2. Add to `~/.zshrc`:
   ```bash
   export JIRA_EMAIL="you@kinoa.io"
   export JIRA_API_TOKEN="<token>"
   ```
3. Open a new shell, then optionally pin `jiraAttach.mjs`'s transport to skip the probe
   (`JIRA_HOST` affects `jiraAttach.mjs` only; `jiraReport.mjs` ignores it):
   ```bash
   export JIRA_HOST=gateway   # scoped tokens; use "site" for a classic unscoped token
   ```

> **`~/.zshrc`, not `~/.zprofile`.** `.zprofile` is only read by login shells, so tooling that
> spawns a non-login shell will not see your token.

Same pattern as `ALLURE_TESTOPS_TOKEN` — per-user, in your shell, never committed. Auth is
**Basic** (`email:token`). **All Atlassian tokens now expire within a year**, so expect to
rotate. Verified working 11 Aug 2026 with a scoped token holding the classic scopes, via the
gateway.

**Note for scoped tokens.** A scoped token cannot call `https://<site>.atlassian.net/rest/...`
at all — that host answers **403** no matter which scopes the token holds. Only
`https://api.atlassian.com/ex/jira/<cloudId>/rest/...` works. You do **not** configure that for
`testplan`: `jira_base_url` stays the ordinary site URL and the cloud id is looked up
automatically. `jiraReport.mjs` always posts through the gateway and ignores `JIRA_HOST`, so it
needs a token that works there — a scoped token with the classic `read:jira-work` +
`write:jira-work` scopes. `jiraAttach.mjs` tries the site first and falls back to the gateway
unless `JIRA_HOST` pins one. It is worth knowing when a token looks correct and a call still
returns 403.

Each image `testplan` reads is capped at 10 MB; a larger attachment is skipped with its reason
and the others are still read.

**If the variables are unset**, the two skills behave differently:

- **`testplan`** continues — the header records `images: none (jira credentials not set)` and
  the gate warns. For `testplan` missing credentials only mean no image-derived acceptance
  criteria. Under `--from-smoke` they also mean no remote link: the case is still pushed, and
  `testplan` prints the link's title and URL for you to add by hand.
- **`smoke-run`** stops at the start and names the missing variable, before it drives a
  browser: a run that cannot post its report or attach its evidence is not started. A
  `jiraReport.mjs … --dry-run` rehearsal needs no credentials and is not gated.

## Usage: `/kinoa-qa:testplan`

```
/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>]
[--openspec-path <dir>] [--story-field <value>] [--component <value>] [--feature <value>]
[--allow-unverified-fields] [--dry-run]

/kinoa-qa:testplan --from-smoke <SUBTASK-KEY> [--target <service>/<capability>]
[--story-field <value>] [--component <value>] [--feature <value>]
[--allow-unverified-fields] [--dry-run]
```

Every plan this command generates is an **e2e plan** — the full-coverage format: per-AC
functional, negative, edge, regression and nonfunctional cases, `scope: e2e` written in the
plan header, cases created in TestOps as **`Review`** under the `Feature` you passed. There is
no flag that changes the format. The other format, `smoke` — one short functional scenario,
created as `Draft` — is never generated: a Story's smoke plan comes from `/kinoa-qa:smoke-plan`,
as a "Smoke test" Jira sub-task, and `--from-smoke` converts that sub-task into a smoke
`test-plan.md` and pushes it (below). The validator accepts both (`scope: smoke | e2e`; a
plan without the line is e2e) and rejects anything else, the retired `story` value included.
Without `--from-smoke` this command validates and pushes e2e plans only: a plan whose header
says `scope: smoke` stops at Step C and is never pushed.

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

A generated plan file always ends in `-e2e`. A plan left from an earlier version at a
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

### Pushing a smoke sub-task to TestOps

```bash
/kinoa-qa:testplan --from-smoke KING-5678 --story-field Template --component Game-Settings --feature In-Apps
```

`--from-smoke <SUBTASK-KEY>` takes the "Smoke test" sub-task `/kinoa-qa:smoke-plan` created and
pushes it as **one `Draft` case** under the `Feature` you passed. Nothing is generated: the
agent saves the sub-task, its parent Story and the sub-task's remote links, exactly as Jira
returns them, and `smoke_to_plan.py` converts them into a `scope: smoke` plan at
`~/.kinoa-qa/plans/<STORY-KEY>-<service>-<capability>-smoke.test-plan.md` (or
`<STORY-KEY>-no-target-smoke.test-plan.md` without `--target`). The case is titled with the
sub-task summary minus `Smoke test: `; its steps and preconditions are the sub-task's, with the
source tags stripped; its acceptance criteria are the parent Story's, and each `[AC-n]` tag
counts the Story's criteria from 1. The validator, the review gate and Step E then run as for
any plan, with the Story key taken from the plan header — never the sub-task key.

- **A refusal stops the run** and names the reason — for example a sub-task with no
  `## Preconditions`, a step without exactly one expected result, no `[GATE]` step, a Story
  with no acceptance-criteria list, or an `[AC-n]` past its count. Fix the sub-task (or the
  Story) and re-run; never edit the plan file, which is rebuilt from the sub-task every time.
- **The case id lives on the sub-task.** At the gate you are asked, as a separate yes, whether
  to record the case on the sub-task; after Step E, `jira_remote_link.py` writes one remote link
  titled `Allure TestOps case <id>` — the one `smoke-run` reads — updating it in place on a
  re-push, never adding a second. Not on `--dry-run`, never unattended. It needs `JIRA_EMAIL` +
  `JIRA_API_TOKEN` with the classic `write:jira-work` scope; without them (the script exits 3),
  or if the config is unreadable or Jira refuses (exit 1), the case stays pushed and you get the
  title and URL to add by hand (the URL only when `config.json` names `testops.base_url` and
  `testops.project_id`).
- **A re-push updates the same case**, found by the id on that remote link, and only if the
  case carries `qa-generated`, the same Story and `scope=smoke` in its `Target:` marker.

See `skills/testplan/SKILL.md` for the flow and `skills/testplan/references/` for the current
format and vocabulary. `docs/superpowers/` holds the original design and plan as dated historical
records — they predate later vocabulary changes and are not authoritative.

## Usage: `/kinoa-qa:smoke-plan`

```
/kinoa-qa:smoke-plan <STORY-KEY>
```

**Use it when** a Story has been built and you need to know what to check, or when you want to
find out early whether a Story is testable at all. It runs from any working directory.

**What it does**

1. Reads the Story, its acceptance criteria, its comments, its remote links and any linked
   Confluence PRD.
2. Opens the linked Figma design read-only and takes the real UI copy from the Story's frames —
   labels, states, validation text. Never locators: those come from the live DOM at run time.
3. Cross-checks those sources **against each other**. Contradictions become open questions, not
   guesses.
4. Writes about 2–5 numbered steps — a target, not a limit — one expected result each, every
   result tagged with its source (`[AC-2]`, `[Story]`, `[PRD: section]`, `[Figma: frame]`,
   `[live-confirmed]`). Steps that prove the feature is live are tagged `[GATE]`; `smoke-run`
   derives its feature verdict from them.
5. Shows you the draft and **stops**. Nothing reaches Jira before you confirm.
6. On your yes: creates a "Smoke test" sub-task on the Story, and comments the open questions onto
   the Story for its owner.

**What to expect**

- **It will not invent expected results.** Anything it cannot trace to a source becomes an open
  question addressed to the PO. That is the point, not a limitation.
- **Open questions do not block the test.** A question about an expected *value* withholds one
  step's verdict. Only "not deployed" / "can't find it" / "can't set up the data" stops a run.
- **It creates no Allure TestOps case.** The sub-task is the source of truth. To get one, push
  the sub-task afterwards with `/kinoa-qa:testplan --from-smoke <SUBTASK-KEY>` — see
  [Pushing a smoke sub-task to TestOps](#pushing-a-smoke-sub-task-to-testops).
- **Expect to edit it.** The steps are a strong first draft, not finished work.

**Figma is the one that catches people out.** Everyone authenticates as themselves — no account is
shared and no credential is committed. Being *able to open the file in your browser is not
enough*: the MCP additionally requires **membership of the team that owns the file**. A file shared
with you directly, or via a link, gives browser access without membership, and the MCP refuses with
a misleading `"you don't have edit access to this file"`. Run `whoami` — if the owning team is not
in the plan list, ask to be added to the team, not to be given edit rights. A View seat is capped at
6 API calls a **month**; you want a Dev seat. Only `smoke-plan` needs Figma — `smoke-run` reads the
sub-task, never the design.

See `skills/smoke-plan/SKILL.md` for the full workflow.

## Usage: `/kinoa-qa:smoke-run`

```
/kinoa-qa:smoke-run <SMOKE-SUBTASK-KEY>
```

**Use it when** the feature is built and deployed and you want to know whether it works. The
input is the "Smoke test" sub-task `smoke-plan` created.

**Start checks.** Before anything else `smoke-run` checks for the **Playwright MCP** and for
**`JIRA_EMAIL`** and **`JIRA_API_TOKEN`** in the environment (only that each is set — it never
prints them). If one is missing it names exactly what is missing and stops. It cannot tell
whether the token works: `jiraReport.mjs` always posts through the `api.atlassian.com` gateway,
so use a scoped token with the classic scopes (see [Jira API token](#jira-api-token)). It also checks once
whether it is **inside kinoa-test-automation**: the working directory is a git repo whose
`origin` URL ends in `kinoa-test-automation` or `kinoa-test-automation.git`.

**What it does** — asks you to log in to the app in the Playwright MCP's browser (it never reads
the operator password), drives the browser through the plan's steps, judges each one `pass` /
`fail` / `blocked` per `skills/shared/step-outcome-contract.md`, screenshots every `fail`, then
shows you the report and **waits for your yes before any Jira write**. On your yes it reports
twice, in two formats:

| Where | What it is |
| --- | --- |
| A comment on the Jira sub-task | The durable record, rendered by `jiraReport.mjs` as native Jira — coloured verdict panels and `PASS`/`FAIL`/`BLOCKED` lozenges. The script computes the conformance verdict from the step outcomes, and refuses to post when a step's outcome is not `pass`/`fail`/`blocked`, a step has no title, a non-pass step has no evidence, a `fail` has no screenshot (or waiver), a screenshot is not named `step-NN-….png`, no step is a gate, or the feature verdict contradicts the gate steps. It does not check that every plan step is present, or that the Not attempted, Grounding, Raised and Environment left blocks are filled — `smoke-run` has to get those right itself |
| A published artifact | The readable mirror — same content, screenshots inline. One per plan, updated in place, so the link stays stable |

It also rewrites a single `Latest run:` line at the top of the sub-task's description (the rest
of the description is the plan and is never overwritten), and raises suspected product defects
as Sub-bugs on the Story, with evidence attached.

**Two verdicts, and the distinction matters:**

| Verdict | Answers |
| --- | --- |
| **Feature** — `live` / `partially live` / `not live` | Is it deployed, reachable, does the main path work, can deeper tests be written now? Derived from the `[GATE]` steps only |
| **Conformance** — `passed` / `failed` / `blocked` | Does each expected result match what the plan says? |

`live` + `failed` is a normal and useful result: the feature works, but something disagrees with a
written spec — a defect, or a stale spec. It does not block deeper testing.

**It runs against real data.** It creates and modifies entities. Point it at a sandbox project,
never at `Autotest Project` or `Autotest Project 2…21`, which the e2e suite draws from.

### Inside kinoa-test-automation, or not

The Jira report, the evidence and the artifact work from any working directory. Three things
work **only inside kinoa-test-automation**, and outside it `smoke-run` says each one when it
applies:

| | Inside kinoa-test-automation | Anywhere else |
| --- | --- | --- |
| **Test data setup** | Through the repo's API helpers (`api/controler/`) — API over UI | Through the UI, and the report says so |
| **Saving the run as a `tests/smoke/<feature>.smoke.ts` spec** | On request only, never by default, on a new branch, built from the repo's page objects, fixtures and `SMOKE` Playwright project | Refused, with the reason |
| **The Allure TestOps case id in the spec** | Only on the save-as-spec path, and only with a case id: a remote link `Allure TestOps case <id>` on the sub-task, else an id you give. That link is written by `/kinoa-qa:testplan --from-smoke`; a sub-task never pushed has none, so the id comes from you. With more than one such link on the sub-task, `smoke-run` asks you which id to use. With a case id the spec carries `@allure.id`, and its run writes `allure-results/` (the repo's `allure-playwright` reporter). **Nothing publishes that as a TestOps launch**: kinoa-test-automation has no upload step (its launches come from its Jenkins CI jobs, and the `SMOKE` project has none), and the Allure TestOps MCP cannot upload one. `smoke-run` says no launch was published and where `allure-results/` is | No spec, so no `@allure.id` and no launch; `smoke-run` says so. The Jira report is unaffected |

**It does not write code by default.** The deliverable is the report. A Story smoke test runs a
handful of times and is then done; when a check earns permanent coverage, use
kinoa-test-automation's `testops-to-playwright` skill rather than growing the smoke test. If you
do ask for a `*.smoke.ts`, **never name it `*.test.ts`** — the suffix is what keeps it out of
kinoa-test-automation's sharded CI run.

Inside kinoa-test-automation the repo also keeps the operator password out of Claude's reach
(its `.claudeignore` and `.claude/settings.json`). Outside it nothing does: `smoke-run` never echoes a
secret, and asks you to provide the operator password through the environment, never in the chat.

### Attaching evidence to Jira

The Atlassian MCP can write comments but cannot upload files, so the plugin ships
`skills/smoke-run/scripts/jiraAttach.mjs`, which posts to Jira's REST attachment endpoint.
`smoke-run` calls it for you; to attach by hand:

```bash
node <plugin>/skills/smoke-run/scripts/jiraAttach.mjs KING-22355 ./evidence-1.png ./evidence-2.png
```

`<plugin>` is the plugin's install directory. The script needs `JIRA_EMAIL` and `JIRA_API_TOKEN`
set up as in [Jira API token](#jira-api-token) — a scoped token with the **classic**
`read:jira-work` + `write:jira-work` scopes. If they are missing it prints how to set them. The
report comment is posted the same way, by `jiraReport.mjs`:

```bash
node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json --dry-run   # validate and print, post nothing
```

`--dry-run` needs no credentials and no network.

See `skills/smoke-run/SKILL.md` for the full workflow.

### What the smoke skills will not do

- **Decide what "correct" means.** They surface contradictions between the Story, the PRD, the design
  and the build; a human resolves them.
- **Replace the regression suite.** Smoke means "does the new thing work", nothing wider.
- **Write to Jira without asking.** Both show you their output and wait for your yes first.
- **Guarantee the expected results are right.** They are traceable to a source, which is a different
  and weaker claim — on the first calibration Story the most authoritative-looking source (the PRD)
  was the wrong one. For UI copy, precedence when sources disagree is **live UI > design > PRD**;
  what the feature does still comes from the acceptance criteria and the Story.

### Troubleshooting the smoke skills

| Symptom | Cause |
| --- | --- |
| `Kinoa Team is required` | Jira mandates `customfield_10131` on the sub-task. `smoke-plan` reads it off a sibling sub-task on the same Story, never guesses it |
| Jira body renders as literal `h2.` | Wiki markup in a Markdown field — bodies must be Markdown |
| `requires re-authorization` (Atlassian) | The MCP token expired. Reconnect via `/mcp`, then restart the session |

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