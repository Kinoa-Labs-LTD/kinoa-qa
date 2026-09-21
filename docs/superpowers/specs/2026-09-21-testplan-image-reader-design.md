# Design — ImageReader in Step A of the `testplan` plugin

Date: 2026-09-21
Status: approved for planning

## Problem

A Jira Story may carry its requirement in an embedded image — a mockup pasted into the
description, a screenshot of a config screen, an annotated flow. Step A reads the Story as
text only, so that requirement never reaches the Step B subagent and never becomes an
acceptance criterion.

This is not hypothetical. KING-18454 ("Eligibility checkboxes for Milestones in-app") carries
an image in its description; the generated plan covers 13 criteria from the description text
and records a `⚠️ GAP` for the image, while the Story *title* promises an operator-facing
checkbox the description never describes. The image is the likeliest place that requirement
lives, and the plugin cannot see it.

## Decision

Add a fifth reader to Step A — `ImageReader` — that downloads the Story's image attachments
and puts them in the **authoritative tier** of the SoT bundle, alongside the Story text, the
PRD and Figma frames. What an image shows is a business requirement: it may ground an
`expected:`, exactly as a Figma frame may.

Two choices were settled with the QA engineer before this document:

1. **Retrieval is an authenticated REST fetch** using `JIRA_EMAIL` + `JIRA_API_TOKEN` from the
   environment, so a run stays headless. The plugin owns no credentials — it documents and
   probes for them, exactly as it does for the Atlassian, Figma, TestOps and `gh` tools.
2. **Provenance is a new `image-ref:` field** on a case, mirroring `design-ref:`. Reusing
   `design-ref:` was rejected: its grammar is a Figma coordinate (`<fileKey>/<nodeId>`), and
   overloading it would make one field mean two different things.

## The SoT bundle after this change

| Tier | Members | Authority |
|---|---|---|
| Authoritative | `{ story, acceptance, prd?, designs[], images[] }` | Decides what a case asserts; may ground an `expected:`. |
| Contextual | `{ openspecs[] }` | Enriches `preconditions`/`steps` only. |

`images[]` degrades independently of the PRD, the mockups and the specs, and is never a hard
stop. Story, PRD, mockup and image have **no precedence between one another**: a direct
contradiction between an image and another business source is a `## Conflicts` line naming
`image` as one side, never something Step A arbitrates.

## Components

### 1. `scripts/jira_attachments.py` (new)

Two units, split so that all the judgement is testable offline and the I/O is one thin
function.

```
select_image_attachments(issue_json, *, max_bytes=10_485_760) -> (kept, skipped)
```
Pure. Reads `fields.attachment` (absent, `null` or empty → `([], [])`, never an exception),
keeps entries whose `mimeType` starts with `image/`, and splits off those above the size cap.
Each kept record is `{id, filename, mimeType, size, content_url}`. Each skipped record carries
a `reason` so the caller can warn without re-deriving it.

```
fetch_attachment(content_url, *, email, token) -> bytes
```
The only network call. HTTP Basic auth over stdlib `urllib.request` — the plugin's scripts
carry no third-party dependencies and this one will not be the first. Raises a typed error the
caller turns into a degradation reason; it never lets an exception escape Step A as a crash.

Credentials come from `JIRA_EMAIL` and `JIRA_API_TOKEN`; the base URL from the existing
`config.json` key `jira_base_url`. The endpoint is
`<jira_base_url>/rest/api/3/attachment/content/<id>`.

**All image attachments on the Story are read**, not only those the description embeds. The
inline media placeholders in a description body carry a Media API id that does not map cleanly
onto an attachment id, so filtering by embedding would silently drop images. Reading them all
is the honest superset.

### 2. `test-plan-format.md` (contract change)

- Header gains an `images:` line: `images: <n> read`, `images: none` when the Story has no
  image attachment, or `images: none (<reason>)` when retrieval was attempted and failed.
  Informational, like `openspec:` and `design:`.
- New optional case field `image-ref: <attachment-id> — <filename>`, in fixed field order
  immediately after `design-ref:`. Full order becomes: `allure-id`, `type`, `priority`,
  `purpose`, `source`, `openspec-ref`, `design-ref`, `image-ref`, `preconditions`, `steps`,
  `expected`. (Field order is a format-doc rule the author follows; the validator checks
  fields, not their order, today — this change does not alter that.)
- `image` joins `story` / `prd` / `design` / `openspec` as a `## Conflicts` source.
- TestOps mapping: `image-ref` is **never a payload field**. It rides the `Provenance:` line on
  the payload `description`, exactly as `design-ref` does. No new tag — the tag policy stays
  `qa-generated` only.

### 3. `validate_test_plan.py` (new check)

`image-ref-valid`, modelled on `design-ref-valid`: syntax and source pairing only, never a
network call — the validator is offline.

- `IMAGE_REF_RE = ^\d+\s+—\s+\S.*$` — a positive integer attachment id, an em dash, a
  non-empty filename. A **regex match**, not a split: `design-ref` is already written this way,
  so a filename containing an em dash cannot be truncated. This repo has shipped two silent
  truncations from delimiter splitting; the test suite will pin the behaviour with a filename
  that contains an em dash.
- An `image-ref` requires an `ac:` source — an image enters through the acceptance criteria,
  not as a source kind of its own.
- `CONFLICT_SOURCES` gains `image`.

### 4. Documentation the agent executes

`sot-assembly.md` gains the `ImageReader` section (extraction, credentials, endpoint, the
`images:` header line, degradation table). `generation.md` gains the rules for deriving ACs
from images — no-fabrication still applies, a decorative or unreadable image is a `⚠️ GAP` and
never an invented case, and an image that contradicts another source is a conflict line.
`SKILL.md` gains the Step A mention, its reference-table row and its degradation rows.
`README.md` gains the two environment variables and a dependency-table row.

These files are the implementation for the agent-driven steps, not documentation about it — a
reference that misdescribes the validator is a defect.

## Degradation

Every row continues the run and warns at the Step D gate. None is a hard stop.

| Situation | `images:` header | Gate |
|---|---|---|
| Story has no image attachment | `images: none` | no warning — the ordinary path |
| `JIRA_EMAIL` or `JIRA_API_TOKEN` unset | `images: none (jira credentials not set)` | warn |
| An attachment 404s or auth is rejected | `images: none (<reason>)` for that file, others continue | warn |
| An image exceeds the size cap | that file skipped with its reason, others continue | warn |
| A non-image attachment | ignored silently — not a degradation | no warning |

## Testing

TDD, tests before implementation.

- `test_jira_attachments.py` (new): selection keeps only `image/*`; a missing, null or empty
  `attachment` field returns empty rather than raising; the size cap splits kept from skipped
  and records a reason; the content URL is composed from `jira_base_url` and the attachment id.
- `test_validate_test_plan.py` (extended): a valid `image-ref` passes; a malformed one fails
  naming the case; an `image-ref` with a `QA-added:` source fails; a filename containing an em
  dash survives intact; `image` is accepted as a conflict source and an unknown source is still
  rejected.

The full suite must be green, and the shipped eval fixtures must still validate unchanged — the
`image-ref` field is optional, so every existing plan stays valid.

## Out of scope

- Re-running KING-18454 through the new path (a follow-up, on request).
- Images embedded in a Confluence PRD.
- Any OCR or image-preprocessing step — the Step B subagent reads the image directly.
