# Plan skeleton

The plan is one file in `~/.kinoa-qa/mcp/plans/`; its name, its version and the rule
that a revision is a new file are in [`file-layout.md`](file-layout.md#file-names).

This file owns the plan rules the ownership table lists for it
([`file-layout.md`](file-layout.md#where-each-rule-lives)). The execution rules themselves live in [`rules.md`](rules.md) and
the report contract in [`report-spec.md`](report-spec.md). A plan links to them and never copies
them.

Contents: [the skeleton](#the-skeleton) · [rules are pointers](#rules-are-pointers) ·
[cases are data, prose is commentary](#cases-are-data-prose-is-commentary) (with the one row of
each shape) · [the fixed section order](#the-fixed-section-order) · [the preflight](#the-preflight) ·
[stable case ids](#stable-case-ids) · [the three soundness rules](#the-three-rules-that-decide-whether-a-plan-is-sound) ·
[hypotheses](#hypotheses-are-the-plans-real-work) · [with and without the server source](#with-and-without-the-server-source)
(and [without a connector](#without-a-connector)).

## The skeleton

```markdown
# <KEY> — <domain> via the AI agent: Test Plan

**Story:** <JIRA URL>
**Under test:** the tool names, on the **deployed test stand**
**Plan version:** N (<date>) — 1 for a file with no suffix, else the `-v<N>` of the file name
**Report to produce:** `<KEY>-<domain>-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** the reports of the previous versions of this plan, oldest first, or "none"
**Decisions from the interview:** artifact policy, the checkpoints of Part B (applied by the run
through the admin role API), replica count, write mode, the role-to-tool mapping the plan was built on, the
story-vs-stand tool check (tools missing, extra or renamed, and the operator's answer — or
`not done: no connector in this chat`) — one line each
**Research inputs:** <KEY> — <title>, one per sub-entity of the story that gave §1.3 at least one
row, whatever its type, or "none". A sub-entity read and found empty or rule-less is not listed
here; it is in the interview message only (`mcp-plan SKILL.md`, §2)
**Checked against:** `commit <sha>` and the files read, when the server source was open, else
`tools/list of <date>; server source not available` (see "With and without the server source")

## 0. Fixed test data
The constants table, per `mcp-plan references/fixed-data.md`, with the **literal value** the interview
gave for every constant — a `<…>` placeholder or an empty cell here makes the plan not runnable —
plus the **artifacts table**: one row per
artifact inside the stamp scope, probes and twins included — handle, the **actual `name` / `key`
it will be created with** (the `NAME`/`KEY` stamp plus a descriptive suffix, not the handle),
game, what it is, intended end state, and `Expected`: `yes`, or `no` for a name sent for an
expected refusal. The report cites those real names, not the handles, so the plan fixes them up
front; the run grades a leftover against the `Expected` mark (`mcp-plan references/rules.md`,
writes).

## 1. Execution rules
Pointers only: `mcp-plan references/rules.md`, `mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`, `mcp-plan references/stand-facts.md`. Then the facts only this
domain knows, one line each: which tool
carries its own rate cap, which tools are irreversible, which subjects are reserved for Part B,
what is not under test although the story mentions it (a tool, a case left out for an entity
nobody can name or create, or a check that could only ever be `BLOCKED` on this stand — the third
soundness rule — each line naming what is missing and why).

### 1.1 Known deviations to confirm through the protocol
| # | AC / expectation | What the code appears to do | Cases |
One numbered hypothesis per deviation found by comparing the AC against the implementation, each
wired to the case ids that settle it. The delete-semantics question lives here too.

### 1.2 Known issues and the cases that cover them
| Finding | Filed as | What it is | Cases |
One row per known issue of this story: every finding **and every note** of every earlier report,
every sub-bug filed from a run, and every bug linked to the story or listed as known in it — fixed
and merged ones included. `Finding` holds the report id with its report (`F3 (0855)`, `N2 (1117)`),
or `—` when the issue was never in a report. `Filed as` holds the JIRA key, and the report reuses
that key for the `TRACKED in <KEY>` marker (`mcp-plan references/report-blocks.md`). Every row names at
least one case, and what counts as covering depends on the row:
- **a finding of an earlier run** — the case that found it (same id, kept) when that case found
  this finding alone, else a new case that runs its repro; never a case shared with another finding
  or one that only touches the same tool. This is the full-case rule of
  `mcp-plan references/file-layout.md` (comparing runs);
- **a note of an earlier run** — a case that sends the call of the note's `What was seen`, so the
  run can say `fixed` or `still present` for it; when no case sends it, a case of its own;
- **a linked bug or sub-bug that was never in a report** — an AC-derived case that shows it, else
  a case of its own.
A new case goes in the tool section it belongs to (order of work: `mcp-plan SKILL.md`). The subsection
is left out, heading included, only when the story has no known issue and there is no earlier run.

### 1.3 Research results and the cases that cover them
| Source | Rule | Served contract | Cases |
One row per clause that a case can check on its own, of every research input the header names,
written as the input states it (quote as written, `mcp-plan references/language.md`). A field
whose rule holds several clauses gives several rows, one per clause, so each clause traces to
its own case; a sentence that states two rules gives two rows. Example, the table of a
research sub-task: `name — required; 1..255 characters; not trimmed (whitespace counts)` is
three rows (`name` required / `name` 1..255 / `name` not trimmed); `slots[].title — required;
unique among siblings` is two; the sentence "the status of a new widget is always DRAFT; a
status sent on create is refused" is two. A qualifier in brackets such as `(case-sensitive)`,
the type the schema already gives the field, and the UI default of a required field each stays in its clause's row:
`slots[].level — number, required, the UI sets 1` is one row. `Source` is the key and the place in its text (a table
name, a heading, a comment's date and author). `Served contract` says what `tools/list` or the
served schema says about the same thing: `same`, `absent`, the differing text, or
`not checked: no connector` when the planning chat has no connector (the run's inventory and
schema cases settle it). `Cases` holds at least one case id, or `not reachable: <why>` for a rule
the protocol cannot exercise (a UI-only control such as a hidden button, a modal's confirmation
text). A field the input marks "no rule" is not a rule and gets no row. A row with an empty
`Cases` cell means the plan is not finished. Three rules decide which cases cover a row:
- **a rule the served contract agrees with** (same limit, same charset, same requiredness) is
  covered by a `schema` or `rule` case of layer 2 that sends the boundary the research names — the
  research gives the values, the case sends them. It may be a case that already exists for the AC;
  then only the id is added;
- **a rule the served contract contradicts or does not carry** is a hypothesis. Examples: the
  research says required and the schema says optional; the research names a charset the schema
  does not declare; the research gives a UI default the tool does not set. It gets a §1.1 row
  whose `AC / expectation` column cites the research row, plus the cases that settle it, and the
  §1.3 row names the same ids. A rule that expects a refusal (a limit, a duplicate, an argument
  the entity does not take) is decided on the refusal envelope, like any `rule` case. A rule about
  a **stored value** (a required field, a default) is decided on the **entity read back through
  the protocol**, never on the write's envelope. After a write that omits the field, the read
  shows a value the research calls valid: a number for a required numeric field such as a
  `level`, the default for a UI default. The read is the entity's `_get`, or its `_list` row when
  the tool set has no `_get`. When no read exposes the field, the row says
  `not reachable: no read exposes <field>`. A `PASS` on the write with no read-back proves nothing
  about what the dashboard will load;
- **every happy-path `ok` case sends every field the research marks required**, with the
  research's default where the served schema leaves it optional, so the entities the run creates
  are the entities a dashboard user would create. The omit-the-field probe lives in its own `gap`
  case on its own subject, never in the `ok` case;
- **a rule about trimming or whitespace** ("not trimmed", "whitespace counts") is covered by two
  cases: a value with surrounding whitespace, read back as sent, and a whitespace-only value,
  whose `Expected` follows the research (for "whitespace counts": accepted and stored as sent).
  Only the whitespace-only value tells "trimmed, then refused as empty" from "whitespace
  counts".
The subsection is left out, heading included, only when the header says `**Research inputs:** none`.
`check-layout.sh` check 21 reads the header line and the rows.

# PART A — everything that needs no permission change
§A0 Preflight, opened by the tool inventory (see "The preflight"), then one section per tool in
the fixed order below, then §Grey, then §Hand-off.

# PART B — role-gated checks
Opens with one line that states both numbers: `<N> role checkpoints, then the restore`
(`mcp-plan SKILL.md`, §2, question 6: the operator's number counts role states only).
One checkpoint per role state, built by `mcp-plan references/rules.md` (Part A / Part B): the rows
wanted as the complete state, then the request block that puts them in place (the three request
shapes: `mcp-plan references/stand-facts.md`, the admin role API), then the table. The last checkpoint
restores `ROLES_BEFORE`. Grey-box probes under a restricted role go last, reusing the final
checkpoint's state. A case that runs after the restore expects the answer the same call got in
Part A, named by its case id (`as get-ok-01`), never a fixed role: Part A ran under
`ROLES_BEFORE`, whatever those rows were.

# REPORT
A pointer to `mcp-plan references/report-spec.md` plus what only this domain knows: the AC bullets for
the traceability table, the hypothesis ids, and which artifacts are irreversible.
```

## Rules are pointers

Section 1 of a plan holds pointers and domain facts. A plan names a reference as plain text,
`mcp-plan references/<file>.md`, never as a link: the plan lives in `~/.kinoa-qa/mcp/plans/`, away
from the plugin, so a link into the plugin does not resolve. Section 1 does not restate the
language rule, the two-leg write rule, the notes rule, the statuses or the delete semantics. The
execution chat
reads those from the references, which are the single home of each rule
([`file-layout.md`](file-layout.md#where-each-rule-lives)). A rule copied into a plan goes stale.

## Cases are data, prose is commentary

Every case is one row of a three-column table, and the row holds nothing else:

| Column | Holds | Never holds |
|---|---|---|
| `Id` | the stable id, see below | — |
| `Call` | the tool name and the **full JSON arguments**. Several calls are numbered `1.` `2.` inside the cell, and both legs of a write are two numbered steps | a description of a value instead of the value, or of calls instead of the calls (`and so on`, `...`) |
| `Expected` | the deciding assertion first, then the literal label `Also record:` and the rest (see below); numbered like the calls when there are several; plus `Record: <handle>` when a later case needs a value from this one | the reason for the case, the AC it comes from, the hypothesis it settles, what an earlier run found |

Everything that is not a call or an assertion is **commentary**, and commentary lives in the short
paragraph above the table: what the section proves, which subjects it uses, which hypotheses it
settles, which AC bullets it covers. A human reads the paragraph and skips the table. The execution
chat runs the table and skips the paragraph. The judge maps ids to AC bullets through the REPORT
section's AC list (§1.1 holds only the deviations), not through the rows.

**The `Expected` cell opens with the one assertion that grades the case.** When the case has
several steps, each step's part opens with its own deciding assertion, and the case is decided by
the executing leg's outcome read, not by the preview wording. The deciding clause of a preview
leg is only that the preview came back with its token (`meta.confirmToken` present); what the
preview says goes after the label. A row that expects a refusal from the backend — every `rule`
row, and every `gap`, `sem`, `iso` or `role` row whose refusal is not the input schema or the
permission check of the role mapping — sends both legs and then a read, because the backend validates only on the executing
leg (`rules.md`, writes). Its step 1 opens with `a preview, or already the refusal of step 2`,
step 2 opens with the refusal, and the read shows that nothing changed. Only a `schema` row and
a refusal by the permission check expect no token on the preview leg. Everything else comes after the literal label `Also record:`,
written exactly so, with nothing between the words and the colon. A mismatch before the label is
the case's `FAIL`. A mismatch after it is a note, never a status (`rules.md`, statuses), so no
status word (`OBSERVED`, `BLOCKED`, `FAIL`) follows the label: a status the cell cannot decide
comes from its rule in `rules.md` or `stand-facts.md`, not from the row.

**Every value a case takes from an earlier case is a `Record:` handle**, never "the widget
above": an id, a name, or the state an earlier write left. A case that expects what an earlier
write changed uses a handle that write case records, so the write comes along: a partial run
pulls in earlier cases only along `Record:` values (`rules.md`, partial runs).

**A count is never an absolute number.** Artifacts are kept, so the fixture games hold the
leftovers of earlier runs. An assertion on a count, or on "exactly N items", is written relative
to a baseline that a preflight `pre-` case records (`BASE_<X>` + n), or on a filter scoped to this
run's stamp (`NAME` / `KEY`). A `BASE_<X>` + n assertion names the handles it counts,
`BASE_P1 + 2 (W_A, W_B)`, so a refused create blocks the count instead of failing it (`rules.md`,
partial runs). A filter that an earlier run's artifacts also match, such as `seed-`, is not a
scope. Every artifact inside the stamp scope, probes and twins included, is a row of the §0
artifacts table (the skeleton); `check-layout.sh` check 18 reads the `NAME-`, `NAME_S-` and `KEY_` literals
of every `Call` cell against it, and a literal that only starts an artifact's name, such as a
search scoped to the stamp, passes.

**Every `game_id` and `target_game_id` is a §0 value**: a handle §0 names (`P1`, `P2`,
`FOREIGN`) or a literal §0 holds. A row that probes another value — an empty string, a value
that is no uuid, a uuid in capitals — writes that value in its `Expected` cell too, so a reader
sees it is the probe. `check-layout.sh` check 24 reads them.

**A length or volume probe writes its value out in full, with no handle in it**, so a reader can
count it. The value starts with `len<N>-`, where `N` is the length of the whole value in
characters, prefix included, then counted filler blocks of `0123456789` up to exactly `N`
characters. The shape is required, not an example: `check-layout.sh` check 19 counts every
`"len<N>-…"` literal of a `Call` cell. Never a description such as "255 characters of `A`".

`check-layout.sh` reads the `Call` cells for the rest of this section too: check 23 decodes every
`{…}` argument object as JSON once the handles are taken as strings, and check 25 reports a cell
that describes its calls (`and so on`, `up to the last page`, `...` or `…` in an argument object).

Two limits keep a row atomic:

- A case has one purpose. If the `Expected` cell asserts two unrelated things, it is two cases.
- A case has at most five steps. A step is one tool call, so the two legs of a write are two steps.
  A wait inside a case is its own numbered step in the `Call` cell — `wait 60 s` measured by
  `kinoa_system_ping`, or `sleep 60` (`stand-facts.md`, budgets) — like the `curl` step of
  `pre-04`, and it counts toward the five.
  A longer scenario is split, and the later case starts from a `Record:` value of the earlier one.
  The one exception is a flood probe (`stand-facts.md`, how the flood is sent): its repeated call
  is one step, written once with the count, because splitting it would reset the window it fills.

Case rows are never simplified or shortened for language reasons. The id, the full JSON arguments
and the expected result stay complete and literal. If a shorter sentence would make a case unclear,
keep the exact wording and add a plain sentence in the commentary paragraph instead.

### One row of each shape

A fictional domain, `kinoa_widget_*`, so the shapes are not mistaken for a real story. This block
is the only example of the plan shape; do not open an old plan to see the format.

````markdown
| Id | Call | Expected |
|---|---|---|
| `get-ok-01` | `kinoa_widget_get {"game_id": P1, "widget_id": W_A}` | `data.widget.id` = `W_A`. Also record: `ok: true`; `data.widget.name` = `NAME-widget-a` |
| `create-ok-01` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-widget-b", "size": 3}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` 3. `kinoa_widget_get {"game_id": P1, "widget_id": W_B}` | 1. `meta.confirmToken` present. Also record: `ok: true`; `data.status` = `preview`; `data.intendedChange.name` = `NAME-widget-b`. 2. `data.created` = `true`. `Record: W_B` = `data.widget.id`. 3. `data.widget.size` = `3`. Also record: `ok: true`; `data.widget.name` = `NAME-widget-b` |
| `create-rule-01` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-widget-b", "size": 2}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` 3. `kinoa_widget_list {"game_id": P1, "search": "NAME-widget-b"}` | 1. a preview, or already the refusal of step 2 (then step 2 is not sent). Also record: whether `meta.confirmToken` is present. 2. `error.code` = `VALIDATION_FAILED`, a violation on `name`. Also record: `ok: false`; the violation's `rule` and `hint`. 3. `data.items` holds only `W_B` |
| `list-sem-01` | `kinoa_widget_list {"game_id": P1, "page_size": 100}` | `data.totalItems` = `BASE_P1` + 2 (`W_A`, `W_B`). Also record: `W_A` and `W_B` are among the items |

## B2. Checkpoint 2 — COMPANY Operator, GAME Viewer on `P1`

Rows wanted (complete state): `COMPANY` = `operator`; `GAME` `P1` = `viewer`; no `GAME` row for `P2`.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -X DELETE "ADMIN_API/users/USER_ID/roles?scopeType=GAME&scopeId=P2"
curl -sS -o /dev/null -w '%{http_code}\n' -X PUT -H 'content-type: application/json' "ADMIN_API/users/USER_ID/roles" --data-raw '{"scopeType":"COMPANY","scopeId":"COMPANY","role":"operator"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X PUT -H 'content-type: application/json' "ADMIN_API/users/USER_ID/roles" --data-raw '{"scopeType":"GAME","scopeId":"P1","role":"viewer"}'
curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"
```

| Id | Call | Expected |
|---|---|---|
| `role-create-02` | `kinoa_widget_create {"game_id": P1, "name": "NAME-widget-c", "size": 1}` | `error.code` = `PERMISSION_DENIED`. Also record: `ok: false`; the message names `kinoa_widget_create`; no token |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only this domain knows:
- **Section 3**: the verdict on `kinoa_widget_delete`, from `delete-ok-01` and `delete-sem-01`.
- **Section 6**, one row per AC bullet: "an agent can read a widget" — `get-ok-01`, `get-iso-01`;
  "create refuses a size outside 1–10" — `create-ok-01`, `create-schema-01`, `create-gap-01`;
  "a confirm token binds the previewed arguments" — `grey-01`. Hypothesis ids from §1.1.
- **Section 9**: `kinoa_widget_delete` is irreversible.
````

## The fixed section order

Part A has one section per tool, and inside each tool section the same kinds in the same order.
The order never changes between plans and never changes between versions of one plan, so a reader
who knows one plan can navigate any other, and two stories can be compared section by section.
Section 1 keeps its own order too: §1.1 hypotheses, §1.2 known issues, §1.3 research results
(the skeleton).

**Tools** in Part A are ordered read tools first, then write tools, in this order of verb:

1. `list`, then `get`;
2. other reads, in this order: `references`, `players_count`, `check_player`, `players_export`,
   then any other read;
3. `create`, then `clone` when it is a tool of its own;
4. `update`, then the membership writes `players_add`, `players_remove`, `players_import`;
5. `test` and `test_edit` (a test fire or a test version);
6. lifecycle: `status`, `hide`, `publish`, `deprecate`;
7. `delete`;
8. cross-game: `export`;
9. any tool that fits none of these, in the order the story lists them.

Whether a tool is a read or a write is its `readOnlyHint` (`rules.md`, writes), not its verb:
`players_export` is a read, `test` is a write.

**Kinds** inside a tool section, in this order, skipping a kind the tool has no cases for:

| Kind | Id segment | What it holds |
|---|---|---|
| Happy path | `ok` | The successful call(s) on the tool's own subject. Both legs of a write. Every tool has at least one. |
| Semantics | `sem` | What the tool really does: list inventory and paging, lifecycle transitions and `availableActions`, and the delete determination (the procedure is in `rules.md`, delete semantics). |
| Schema | `schema` | Rejections the server makes against the declared input schema, in the error envelope: missing required, enum, range, length, `additionalProperties`, an object where an array is declared. If a row sends a top-level value of another JSON type (a string for a boolean or an integer, a number for a string), a `null` for a string argument, or an empty string for an argument declared string-or-null, the connector converts it before the call leaves, so the row cannot reach the server: it is not written, and that check belongs in a functional test (`stand-facts.md`, connector). The registry checks the schema before the tool runs and answers `ok: false`, `error.code` = `VALIDATION_FAILED`, a violation with `rule` = `input_schema` and `path` = the argument path without the leading slash (`name`, `resources/0/resource_key`; `null` for a root-level error) — verified at commit `e375f2d`, 2026-10-15. The violations are in `error.violations[]`. A missing required argument is a root-level error: its `path` is `null` and only the wording names the argument (`required property 'game_id' not found`). The `Expected` cell asserts the code, the rule and the pointer; never the violation's wording, which is the validator's and depends on the locale. |
| Tool rules | `rule` | Rejections the tool or its backend makes: cross-field, backend-state, semantic. A write's rule is graded on the executing leg, so the row sends both legs and a read (cases are data, above). |
| Gap hunt | `gap` | Inputs the documented rules do not cover, sent to see what happens. Every row is wired to a §1.1 hypothesis or to an AC bullet (hypotheses, below). |
| Isolation | `iso` | Unknown id, foreign game, cross-game reads, not-found shapes. |

Then the cross-tool sections, in this order: **§Grey** (confirm-token integrity, argument seams,
rate limits and budgets, disclosure; every `grey-NN` row wired like a `gap` row), **§Hand-off**
(verifies the Part B subjects are untouched).
Part B is one section per checkpoint, and inside a checkpoint the cases follow the same tool order.

## The preflight

§A0 proves that the stand carries what the story delivers before any case uses it. It opens with
the **tool inventory**: one case per tool the story names, in the order the story lists them, and
nothing else comes before them.

- The tool names come from the story (its description and its AC), written exactly as the story
  writes them. They never come from `tools/list`: a list built from the stand cannot show that a
  tool is missing.
- Each case is one `tools/list` call with one assertion: that tool is listed. Schemas and
  descriptions are separate `pre-` cases after the inventory, and so are the annotations when the
  connector shows them; a connector that does not (`stand-facts.md`, connector) makes the
  annotation check a §1 line instead of a case (the third soundness rule).
- Right after the `pre-` case that records `USER_ID`, one `pre-` case sends the `GET` of the admin
  role API (`stand-facts.md`, the admin role API) and records its body as `ROLES_BEFORE`. Its
  `Call` cell is that `GET` line, with the handles. It is the run's only snapshot of the role rows
  (`rules.md`, Part A / Part B).
- A tool that the story names under another name than the stand uses is not renamed in the plan.
  The inventory case always keeps the story's name and fails when the stand differs, and the
  planning chat tells the operator about the mismatch (`../SKILL.md`, §2). The `Call` cells of the
  tool's section use the stand's name only when the operator confirmed the rename in the header
  decisions; otherwise they use the story's name, and the run blocks them.
- In a later version of a plan whose preflight predates the inventory, the inventory cases take the
  next free `pre-NN` numbers and still open §A0.

```markdown
| `pre-01` | `tools/list` | `kinoa_widget_list` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_create` is listed |
| `pre-03` | `kinoa_system_ping {}` | `data.userId` present. `Record: USER_ID` |
| `pre-04` | `curl -sS -H 'accept: application/json' "ADMIN_API/users/USER_ID/roles"` | `200` and a JSON array (`[]` allowed). `Record: ROLES_BEFORE` = the body |
| `pre-05` | `kinoa_widget_list {"game_id": P1, "page_size": 100}` | `ok: true`. `Record: BASE_P1` = `data.totalItems` |
```

What a missing tool does to the run is in [`rules.md`](rules.md#statuses).

## Stable case ids

An id names the tool, the kind and a number, and it never changes once a plan version has been run.

| Section | Id shape | Example |
|---|---|---|
| Preflight | `pre-NN` | `pre-03` |
| A tool section | `<tool>-<kind>-NN` | `update-ok-01`, `status-sem-04`, `create-schema-07` |
| Grey box | `grey-NN` | `grey-05` |
| Hand-off | `handoff-NN` | `handoff-01` |
| Part B | `role-<tool>-NN` | `role-create-03` |

`<tool>` is the tool name without the `kinoa_<domain>_` prefix, with `_` written as `-`
(`kinoa_bundle_test_edit` → `test-edit`). `NN` is two digits, counted within one `<tool>-<kind>`
group. Role cases are numbered within `role-<tool>` across all checkpoints. The id does not encode
the checkpoint on purpose: the number of role flips changes between plan versions, and an id that
named the checkpoint would have to change with it.

The rules that make ids survive a rebuild:

- **Never renumber.** Inserting a case does not shift its neighbours. The new case takes the next
  free `NN` in its group, even if it sits in the middle of the table. Free means after the highest
  number any earlier version used, with no gap; `check-layout.sh` check 26 reads it.
- **Never reuse.** A case removed in a later version retires its id.
- **A plan carries no version note and no change log.** Two versions
  are compared by their stable ids: an id in one file only was added or retired, and the same id
  with another `Call` or `Expected` cell was edited. The changes that are not cases live where they
  belong — §1.2, §0, the header decisions.
- **A changed meaning is a new id.** Editing an expected value because a bug was fixed keeps the id.
  Pointing the case at a different behaviour retires the old id and takes a new one.
- Findings and notes in the report cite these ids on their `Case:` line, and the comparison table
  in a re-run report relies on them being the same across versions.

## The three rules that decide whether a plan is sound

**Every tool gets a happy-path case in its own section**, kind `ok`, on a subject created for it.
A tool whose only successful call happens in §Grey is not covered — that is how a `_delete` ends
up proven by a token-replay probe and its real semantics never get established.

**A reserved subject is never written to before its part.** Trace every subject through the plan in
order before calling it finished: if a probe activates, floods, empties or deletes something a later
case expects untouched, that later case is already broken on paper. Give the probe its own subject.

**A check that can only ever be `BLOCKED` on this stand is not a case.** That is a check the
connector cannot send — a value of another JSON type, an annotation it does not show, a
`tools/list` it does not re-read (`stand-facts.md`, connector) — or one that needs a second
account, a second writer, an audit log or anything else the protocol does not show. It is one
line under §1 "not under test", naming what is missing and why, and report section 8 lists those
lines (`report-spec.md`). A row that an earlier report shows was sent and graded is not one of
them: the report is the evidence, so the row stays a case. A hypothesis that needs the source and
has no case stays in §1.1 as `UNPROVEN`, as before.

## Hypotheses are the plan's real work

The pre-execution comparison of AC against implementation is what turns a run from "click every
tool" into "check the specific places this implementation and its story disagree". Each hypothesis
names what the AC promises, what the code appears to do instead, and the case ids that will settle
it.

A hypothesis is not a finding. It becomes one only when the protocol shows it, and it gets a verdict
either way in report section 7.

**Every `gap` row and every `grey-NN` row is wired to a hypothesis or to an AC bullet.** The
row's id appears in the `Cases` column of a §1.1 row, or in the row of the AC bullet it protects
in the REPORT section's AC list. A row wired to neither is dropped before the plan is finished. The
wiring lives in §1.1 and in REPORT, never in the row: a row holds no "why" (cases are data).
`check-layout.sh` check 17 reads the ids.

## With and without the server source

Layers 1–3 of the order of work (`../SKILL.md`, §4) do not need the server source. Two things do,
and both depend on one fact, stated in interview question 8: **is the kinoa-mcp repository open
in the planning chat?**

If it is:

- §1.1 compares each acceptance criterion against the implementation, and the column "what the code
  appears to do" is filled from the code.
- §Grey is designed from the source: the write guard, the token digest, the argument handling, the
  rate limiters, the error mapping.
- The header carries `**Checked against:** commit <sha>` and names the files that were read.

If it is not:

- §1.1 compares each acceptance criterion against the tool descriptions, the schemas and the
  annotations in `tools/list`. The column is renamed "what `tools/list` says", and a hypothesis
  that needs the code is written as `UNPROVEN — needs the source` and gets no case.
- §Grey holds only the generic probes the references already define: confirm-token replay and
  cross-tool reuse, argument seams (`null`, unknown argument, key order), rate limits and budgets
  (`OBSERVED`), error disclosure. It does not claim to be designed from source.
- The header says `**Checked against:** tools/list of <date>; server source not available` so a
  reader knows why §Grey is thin and why some hypotheses are unproven.

### Without a connector

Layers 1–3 need `tools/list` for the argument names, the schemas, the descriptions and the
annotations of the tools. A planning chat with no connector gets them in this order, and never by
reading how a tool works:

1. **The source is open:** read, for each tool, only the text that `tools/list` would serve — the
   tool's name, its description, its input schema (the schema constants and the fragments they
   splice in) and its annotations. That is the served surface, taken from the file instead of the
   wire. Do not read the tool's `call()`, `preview()`, lookups, clients or tests yet: they are
   layer 4 (`../SKILL.md`, §4).
2. **The source is not open:** ask the operator to paste the `tools/list` output of the story's
   tools. Until it is there, write only what the story fixes, and name the missing surface in the
   first message.

The header's `**Checked against:**` line then says `served surface read from source at commit
<sha>; no connector in this chat` (case 1) or `tools/list pasted by the operator on <date>`
(case 2), and the story-vs-stand decision says `not done: no connector in this chat`. The run's
inventory and annotation cases still check the real stand.

The role-to-tool mapping for Part B comes from interview question 9 (`../SKILL.md`, §2). Where
`roles.yml` and the AC differ, the case expects the AC and the gap is a §1.1 hypothesis
(`rules.md`, target and method). The plan states the mapping it was built on, so the execution
chat asserts against a written claim.
