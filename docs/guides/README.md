# Guide pages

Standalone HTML pages that explain the plugin to people who will not open this repo. They are
committed so they are versioned with the skills they describe. The published copy is a rendering;
**the file here is the source**.

| File | Live page | For |
| --- | --- | --- |
| `qa-plugin-guide.html` | [claude.ai/artifact/WDruZqhHZKEtAxTjabUS9S](https://claude.ai/artifact/WDruZqhHZKEtAxTjabUS9S) | The whole plugin: the three skills, the `testplan` pipeline, the smoke/e2e taxonomy, honest status |
| `smoke-testing-guide.html` | [claude.ai/code/artifact/a92e7012…](https://claude.ai/code/artifact/a92e7012-7787-46ba-8404-19a9b2a62cc7) | Onboarding a QA to `smoke-plan` and `smoke-run`, or presenting the smoke flow to the team |

The two pages link to each other. Both live pages are shared with the Kinoa organization.

## Viewing a page

Open the file in a browser. Each page is self-contained apart from web fonts: no build step and no
scripts. Both adapt to light and dark.

## Changing a page

**Edit the file here, then republish it** so the live page and the source stay in step. Ask Claude:

> Publish `docs/guides/<file>.html` as an artifact, passing the existing live-page URL from the table
> above so it updates in place.

Passing the URL keeps the same link, so anything already shared keeps working.

## Keeping them honest

These pages describe behaviour that changes. When a skill changes, update its `SKILL.md` first (that
is what Claude follows), then `README.md`, then the page that describes it. A stale page that looks
authoritative is worse than none.

The pages overlap the README on purpose but do not replace it: the README is the reference you use
mid-task; a guide page is the story you read once.
