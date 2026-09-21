# sot-assembly.md — Step A (read-only)

Assemble the SoT bundle. It has two tiers, and the difference is enforced downstream:

| Tier | Members | Authority |
|---|---|---|
| **Authoritative** | `{ story, acceptance, prd?, designs[], images[] }` | Decides what a case asserts; may ground an `expected:`. |
| **Contextual** | `{ openspecs[] }` | Enriches `preconditions`/`steps` only; may never own an `expected:`. |

Only the Story is required. The PRD, the mockups, the Story images and the OpenSpec files
each degrade independently, and none of them is a hard stop. Story, PRD, mockup and image
have no precedence between one another — a direct contradiction between them is a
`## Conflicts` line, not something Step A arbitrates.

## 1. RequirementsReader — the Story (Atlassian MCP, required)
`getJiraIssue(<STORY-KEY>)` → description + acceptance criteria + subtasks. Keep its raw
JSON response as `issue_json` — including `fields.attachment` — for the ImageReader
(section 4) to consume; it is not re-fetched there.
Missing Story / MCP down → HARD STOP (the one required input).

## 2. PRDReader — the Confluence PRD (Atlassian MCP, authoritative)
The PRD is a first-class business source, not an afterthought: it grounds acceptance
criteria exactly as the Story does.

1. Collect every Confluence link on the Story (description, the remote-link/web-link
   fields, and linked-page macros).
2. `getConfluencePage(id)` for each → the PRD text.
3. Absent or unreachable → header `prd: none (<reason>)`, warn at the gate, continue on
   the Story (and mockups) alone. Never a hard stop.

A Confluence PRD/HLD is never called a "spec" in this plugin.

## 3. DesignReader — Figma mockups (Figma MCP, authoritative)

A mockup linked from the Story is a **business requirement**, in the authoritative tier
with Story and PRD. Read the frames so Step B's subagent sees the real UI — states,
labels, empty and error variants — rather than guessing from prose.

### Extract the links
Scan the Story **description** and its **link fields** (remote links, web links, the Design
field if the project has one) for `figma.com` URLs. From each URL take:
- `fileKey` — the segment after `/file/`, `/design/` or `/proto/`;
- `nodeId` — the `node-id` query parameter (normalise `1-23` → `1:23`).
A URL with no `node-id` addresses the whole file: call `get_metadata` first and read the
top-level frames it names.

### Pick a backend (remote preferred, local fallback)
The plugin ships **no `mcpServers` config** — Figma is a host-environment dependency, like
Atlassian and TestOps. Probe at runtime, in this order:

1. **Remote Figma server** — preferred: a run works headless, with no Figma desktop app
   open and no file selected.
2. **Local desktop server** — fallback when the remote is not connected: faster, and it
   sees unpublished local edits.
3. Neither reachable → the `design: none` degradation below. Not an error.

### Read each frame
Per `(fileKey, nodeId)`, on the chosen backend:
- `get_screenshot(fileKey, nodeId)` — the rendered frame;
- `get_design_context(fileKey, nodeId)` — structure, layer/frame names, text content,
  variants and variable bindings.

Each frame enters the bundle as:
```
designs[ { fileKey, nodeId, frameName, context } ]
```
`frameName` is the frame's name as Figma reports it; `context` is the combined screenshot +
design-context payload handed to the Step B subagent.

### The `design:` header line
Record which backend answered: `design: remote` or `design: local`. When no frame was read,
record the reason instead — `design: none (no figma link on story)`,
`design: none (figma mcp not connected)`, `design: none (node not found)`.

### Degradation
| Situation | Behavior |
|---|---|
| No Figma link on the Story | `design: none (no figma link on story)`; continue; warn at the gate. |
| Figma MCP absent — neither remote nor local reachable | `design: none (figma mcp not connected)`; continue; warn at the gate. |
| A frame fails to read (node gone, no permission) | `design: none (<reason>)` for that frame; continue with the rest; warn at the gate. |

Never a hard stop — Figma degrades exactly like the PRD.

## 4. ImageReader — Story image attachments (Jira REST, authoritative)

An image attached to the Story is a **business requirement**, in the authoritative tier
with Story, PRD and mockups.

Selection and retrieval are implemented in `scripts/jira_attachments.py`:
`select_image_attachments(issue_json, base_url=...)` returns `(kept, skipped)`, then
`fetch_attachment(...)` is called per kept record. **Every** image attachment on the Story
is read, not only those the description embeds — an inline media placeholder's id does not
map onto an attachment id, so filtering by embedding would silently drop images.

Credentials are `JIRA_EMAIL` + `JIRA_API_TOKEN` from the environment (`credentials()`); the
base URL is `jira_base_url` from `config.json`. The plugin owns no credentials of its own,
exactly as it owns no MCP configuration. Images above the 10 MB cap (`MAX_BYTES`) are
skipped with their reason; a non-image attachment is ignored, silently.

`select_image_attachments` returns each kept record as `{ id, filename, mimeType, size,
content_url }` — it carries no image bytes. A Step B subagent cannot be handed raw bytes in
a text prompt, so Step A writes each image to disk and hands over a path instead:

1. Create a run-scoped temporary directory (e.g. `mkdtemp`).
2. Per kept record, call `fetch_attachment(record["content_url"], email=..., token=...)`
   and write the returned bytes to `<tmpdir>/<attachment-id>-<filename>`.
3. The bundle entry is that file's absolute path: `images[ { id, filename, mimeType, path
   } ]` — `path` replaces `bytes`.

Step B is then given those image paths (alongside the SoT bundle and the references) so its
subagent can read each file directly, as an actual image, not a description of one.

### The `images:` header line
- `images: <n> read` — every image attachment was read successfully.
- `images: <n> read (<k> failed: <reason>)` — some were read and some failed or were
  skipped (e.g. one exceeded the 10 MB cap while the rest were fetched).
- `images: none` — the Story has no image attachment. Not a degradation, no gate warning.
- `images: none (<reason>)` — nothing at all could be read (credentials unset, every fetch
  failed, etc.).
The header is informational only; the validator does not parse it.

### Degradation
| Situation | Behavior |
|---|---|
| No image attachment on the Story | `images: none`; no gate warning. |
| Credentials unset (`JIRA_EMAIL`/`JIRA_API_TOKEN` missing) | `images: none (jira credentials not set)`; continue; warn at the gate. |
| A fetch 404s or is rejected, and it is the only image | `images: none (<reason>)`; continue; warn at the gate. |
| A fetch 404s or is rejected, but at least one other image succeeded | `images: <n> read (<k> failed: <reason>)`; continue; warn at the gate. |
| An image exceeds the 10 MB cap | skipped with its reason, folded into the same partial-failure count as above; warn at the gate. |
| A non-image attachment | ignored silently — not a degradation. |

Never a hard stop — images degrade exactly like the PRD and Figma.

## 5. OpenSpecReader — service-repo `spec.md` files (contextual, optional by design)

**Affected-repo + capability discovery** — validated on KING-20951, implemented in
`scripts/openspec_resolver.py` (gh-only, no Jira dev-status needed):

a. `keys = story + subtasks`; for each, `gh search prs "<key>" --owner <ORG>`;
b. keep PRs whose **title starts with one of those keys** (drops "Release to *"
   aggregate PRs and cross-referenced tickets); the Atlassian MCP does **not**
   expose Jira dev-status, so title is the signal;
c. for each kept PR, `gh api repos/<repo>/pulls/<n>/files` → match
   `openspec/(changes/<id>/)?specs/<cap>/spec.md` → the exact `<cap>`;
d. read the archived `openspec/specs/<cap>/spec.md` at the repo default branch;
e. repos with no OpenSpec spec change (pure-frontend, older services) contribute
   nothing — **this is normal**, see the degradation rule below.

Fallbacks when the key-in-PR convention is absent: `services.json` mapping, or the
CLI overrides `--repo` / `--target` / `--openspec-path`.

### OpenSpecResolver (GitHub `gh` default; local override)
Interface: `(service, capability[, ref]) -> spec text`. Backends:
- **Default — `gh` remote:**
  ```bash
  gh api "repos/<owner>/<repo>/contents/<specs_root>/<capability>/spec.md?ref=<ref>" --jq '.content' | base64 -d
  ```
  `<specs_root>` defaults to `openspec/specs` (from `services.json` or convention).
- **Override — local:** `--openspec-path <dir>` reads `<dir>/openspec/specs/<capability>/spec.md`.

### Degradation — two distinct cases
- **No OpenSpec file exists** (the repo has none, or no affected repo ships specs): the
  **ordinary path**, not a fallback mode and not a degradation. Header `openspec: none`,
  **no** gate warning. Generation proceeds from the ACs exactly as it always does.
- **A spec the QA engineer explicitly requested failed**, or the resolver errored
  (`--target` / `--repo` / `--openspec-path` given but unresolvable, `gh` unauthed, one
  target of several fails): still non-fatal, but header `openspec: none (<reason>)` and a
  **warning at the human gate**. `--continue-on-missing` opts into partial multi-target
  runs; the default aborts a multi-target run only if the QA engineer asks.

### The `openspec:` header line
When an OpenSpec file is resolved, record `openspec: <capability>@<first 12 of sha256(spec
text)>` in the header for traceability; `openspec: none` when there is none, and
`openspec: none (<reason>)` only for the requested-but-failed case above.
