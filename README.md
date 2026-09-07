# kinoa-qa

QA plugin for Claude Code. Turns a Jira Story (+ optional Confluence PRD + optional
service-repo OpenSpec specs) into a validator-checked QA **Test Plan**, then — after a
human review gate — idempotently upserts **Test Cases into Allure TestOps** (project KINOA).

Standalone and decoupled from `kinoa-dev`: it depends only on the artifacts kinoa-dev
produces (OpenSpec `spec.md` files in service repos) and the Jira/[AQA] conventions.

## Usage

```
/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>] [--spec-path <dir>] [--dry-run]
```

See `docs/superpowers/specs/` for the design and `skills/testplan/SKILL.md` for the flow.