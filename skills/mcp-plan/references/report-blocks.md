# The report blocks

The contracts for what goes inside a report: the finding block, the note block and the artifact
rows. The execution chat reads this file at its first finding or note. What must be captured at the call, before any block is written — the envelopes, the
isolation evidence, the notes, the names — is method, and it lives in
[`rules.md`](rules.md#capture-at-the-call).

What a report is — its ten sections, the overall status, the comparison with the previous run,
the language and how things are named — is in [`report-spec.md`](report-spec.md).

## The finding block contract

One defect per block. Three wrong things are three blocks even when one root cause explains all
three; each block names the others instead of absorbing them.

```markdown
### F3 — the clone loses the description that was sent, with no error and no warning   [severity: minor]
Case: create-ok-02   Tool: kinoa_widget_create   Part: A

Steps to reproduce:

1. Create the source widget — preview leg.
   Request: `kinoa_widget_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","name":"repro-src","key":"repro_src","fields":[{"name":"amount","field_type":"number","required":true}]}`
   Response: `{"ok":true,"data":{"preview":{"name":"repro-src","key":"repro_src"}},"meta":{"confirmToken":"eyJ0…9Qw","dryRun":false}}`
2. Repeat step 1 with the same arguments plus the token — execute leg.
   Request: `kinoa_widget_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","name":"repro-src","key":"repro_src","fields":[{"name":"amount","field_type":"number","required":true}],"confirm_token":"eyJ0…9Qw"}`
   Response: `{"ok":true,"data":{"widget":{"id":"4b1f2c60-1d55-4a02-9b6e-7c0e5a3f1188","name":"repro-src","key":"repro_src","description":null}}}`
   The source widget is `repro-src`, id `4b1f2c60-1d55-4a02-9b6e-7c0e5a3f1188`.
3. Clone it and send a `description` in the same call — preview leg.
   Request: `kinoa_widget_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","clone_from":"4b1f2c60-1d55-4a02-9b6e-7c0e5a3f1188","name":"repro-clone","key":"repro_clone","description":"should this survive?"}`
   Response: `{"ok":true,"data":{"preview":{"name":"repro-clone","key":"repro_clone","description":"should this survive?"}},"meta":{"confirmToken":"eyJ0…7Lk","dryRun":false}}`
   The preview still shows the description, so nothing warns the caller yet.
4. Repeat step 3 with the same arguments plus the token — execute leg.
   Request: `kinoa_widget_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","clone_from":"4b1f2c60-1d55-4a02-9b6e-7c0e5a3f1188","name":"repro-clone","key":"repro_clone","description":"should this survive?","confirm_token":"eyJ0…7Lk"}`
   Response: `{"ok":true,"data":{"widget":{"id":"8c3a91d4-0f77-4bb1-8a2e-11de6b40c923","name":"repro-clone","key":"repro_clone","description":null}}}`
   The clone is `repro-clone`, id `8c3a91d4-0f77-4bb1-8a2e-11de6b40c923`.
5. Read the clone back.
   Request: `kinoa_widget_get {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","id":"8c3a91d4-0f77-4bb1-8a2e-11de6b40c923"}`
   Response: `{"ok":true,"data":{"widget":{"id":"8c3a91d4-0f77-4bb1-8a2e-11de6b40c923","name":"repro-clone","key":"repro_clone","description":null,"fields":[{"name":"amount","field_type":"number","required":true}]}}}`
   `description` is `null`, and it was `"should this survive?"` in the request of step 4.

Expected: `data.widget.description` = `"should this survive?"` on the read-back of step 5 (the
deciding clause of `create-ok-02`). If that is not allowed, the call should be rejected for sending
`description` together with `clone_from`. The AC says "cloneFrom clones an existing widget", and
the tool description says "any field you pass alongside clone_from overrides the source".

Actual: step 5 returns `{"ok":true,"data":{"widget":{"id":"8c3a91d4-0f77-4bb1-8a2e-11de6b40c923","name":"repro-clone","key":"repro_clone","description":null,"fields":[{"name":"amount","field_type":"number","required":true}]}}}`.
The description is missing. There is no error and no warning. An agent that clones and edits in one call reports
success, but the edit is lost, and the response gives the user no way to see this.

Isolation: the same `description` on a normal create (without `clone_from`) is saved correctly, so
the field itself works. Only the clone path loses it. `name` and `key` were sent in the same way in
the same call, and both were saved, so the tool does not ignore all overrides. See also F4, which is
the second half of the same problem with clone metadata.
```

Each part earns its place:

- **Heading** — states the wrong behaviour in one short, plain sentence, readable with the plan
  closed. A case id is not a description. Section 4 lists the blocks by severity, most severe
  first. In a first run the ids follow that order, `F1..Fn`. In a re-run a defect keeps the id of
  the previous report and a new one takes the next free id (comparing with the previous run), so
  the ids are no longer in order; the blocks still are.
  The `[severity: <x>]` label takes exactly one of four values:

  | Severity | When |
  |---|---|
  | `critical` | Data is lost or changed wrongly, an irreversible action fires without consent, or a permission check is bypassed |
  | `major` | An acceptance criterion is broken and the caller has no way around it |
  | `moderate` | An acceptance criterion is broken, but the caller can reach the goal another way |
  | `minor` | The behaviour is wrong, but nothing is lost and no acceptance criterion is broken |

  **The tracked marker.** A defect that already has a bug in JIRA carries that bug key at the end of
  the heading, after the severity label:

  ```markdown
  ### F12 — `kinoa_audience_get` returns no rules tree for the default audience   [severity: minor]   TRACKED in KING-22650
  ```

  Four rules:

  - **The key only, never a URL and never a link.** Two bugs for one finding are written
    `TRACKED in KING-22650, KING-22651`.
  - **A key is never invented.** It comes from the plan's §1.2 `Filed as` column
    ([`plan-template.md`](plan-template.md#the-skeleton)) or from the user during the run. With no key the heading ends after the severity label. Never write `TRACKED in ?` or
    `TRACKED (to be filed)`.
  - **The marker says a bug exists, and nothing more.** It does not say the bug is fixed, and it
    does not change the severity or the overall status.
  - **The marker never shortens the block.** The defect was seen in this run, so it keeps its full
    repro steps, `Expected`, `Actual` and `Isolation`, exactly like an untracked finding.

  A note block takes the same marker, after its `[impact: …]` label.

- **Case / Tool / Part line** — exactly as above. For `Case: tools/list`, and for a tool-inventory
  case, the step is `Request: tools/list` and its `Response:` lists the names of every tool of the
  domain that the connector lists. `Part:` is the part where the case got its final
  status, so a case deferred from Part A and finished in Part B carries `Part: B`. For a finding
  re-checked from a previous report whose case no longer exists in the current plan, `Case:` names
  the old id and the old plan version.
- **Steps to reproduce** — numbered, self-contained, starting from nothing: every call the defect
  needs, both legs of every write, and the verification call that shows the damage. A reader holding
  only the connector and this block can run it. Real uuids for games and players, real names for
  everything the steps create — never a `P1` / `PLAYER1` placeholder, never a plan handle, never a
  step that leans on an artifact of an earlier case.

  **Every step carries both its request and its response**, on two labelled lines, exactly as in
  the example above:

  - one plain sentence saying what the step does;
  - `Request:` — the tool name and the full JSON arguments, nothing left out;
  - `Response:` — the envelope the stand actually returned for **that** step, verbatim;
  - an optional short sentence after the response, naming the id the step created or pointing at
    the field that matters in it.

  The reader judges the defect from the block alone, before running anything. Three rules keep this usable:

  - **The response is the one that step returned** (`rules.md`, capture at the call). When a
    step's response was not captured, the `Response:` line says so and the block is incomplete.
  - **Nothing that carries meaning is cut.** A long envelope may be shortened with `…` — repeated
    list items, long tokens, unrelated blocks of fields. A field the finding talks about is never
    cut, and `meta.confirmToken` / `meta.dryRun` stay whenever a write leg is shown.
  - **Both legs of a write are separate steps.** The preview leg shows the token in its response,
    and the execute leg's request shows the same arguments plus that token. This is where a
    `CONFIRM_TOKEN_INVALID` defect becomes visible without a re-run.
- **Expected** — opens with the deciding clause of the case row, the part before `Also record:`,
  not the whole cell (`plan-template.md`, cases are data); then quotes the acceptance criterion
  or the tool's own description it comes from, so the source of the expectation is visible.
- **Actual** — the envelope that proves the defect, verbatim, then one or two sentences on what it
  means and what the user-visible impact is. It is the response of the step that showed the damage,
  so it appears twice in the block: once in its step, once here. Where those sentences name the
  entity that misbehaved, they name it by its real name and id, so the claim can be checked against
  the live stand.
- **Isolation** — the control probe, the narrower repro, or the neighbouring call that works: what
  proves this cause and rules out the others. "No control probe was available" is an acceptable
  sentence; silence is not.

One list holds every block. A defect with no acceptance criterion to breach is still a block; its
severity line carries that distinction.

Each block's status is decided in the block, by Expected versus Actual. A block never discusses how
it might have been graded differently.

## The note block contract

A **note** is something the run saw that is odd, inconsistent or sloppy, but that blocks nothing.
Nothing is broken for the caller, so it is not a defect. It still goes into the report, for a
human to decide what to do with it.

### Note or finding?

| Write it as | When |
|---|---|
| A finding (section 4) | The behaviour is wrong. It breaks an acceptance criterion, or it breaks the tool's own description, or it makes a case `FAIL`. |
| A note (section 5) | Nothing is broken, but something is inconsistent or unclear and a human should look at it. Examples: two tools of the same domain answer in different shapes, an error message names the wrong argument but still rejects the call correctly, a field is always empty, a default value is surprising, the tool description is vaguer than what the tool really does, a listing sorts in an order nobody asked for. |

Three rules keep the split honest:

- **A note never replaces a finding.** Moving a defect into section 5 to keep the overall status
  `GREEN` is not allowed. Notes never change the overall status; findings do
  ([the overall status](report-spec.md#the-overall-status)).
- **When the run cannot decide, it writes a finding**, and the finding says what is uncertain. The
  reader can downgrade it; the run must not hide it.
- **A note is never invented to fill the section.** "No notes." is a valid section 5.

### The block

One note per block, numbered `N1..Nn` across the report. Two odd things are two blocks.

```markdown
### N2 — `kinoa_widget_list` returns `total` as a text value, while `kinoa_widget_get` returns a number   [impact: low]
Case: list-ok-01   Tool: kinoa_widget_list   Part: A

What was seen: `kinoa_widget_list {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","limit":50}`
returned `{"ok":true,"data":{"items":[…],"total":"12"}}`. The count came back as the text `"12"`.
The same count comes back as the number `12` from `kinoa_widget_get` on the widget
`KING21979-QA-20260903-1130-src` (id `4b1f…`), in the field `data.widget.usage_total`.

Why it is not a finding: no acceptance criterion says which JSON type `total` has, and both tools
answered the question that was asked. An agent that compares the two values still gets the right
number after it converts the text.

Suggested action: make the two tools use the same JSON type for the same count, or say in the tool
description that `total` is a text value.
```

Each part earns its place:

- **Heading** — the odd thing in one short, plain sentence, readable with the plan closed. Numbered
  `N1..Nn`. The `[impact: low|medium]` label says how much it can cost the reader. A note with high
  impact is a finding, not a note. A note that already has a bug in JIRA carries the same
  `TRACKED in <KEY>` marker after the label (see the finding block contract).
- **Case / Tool / Part line** — the same shape as in a finding block. Some notes come from outside
  a case, for example from the preflight or from reading `tools/list`. Then write `Case: preflight`
  or the plan section it came from, and keep the `Tool:` and `Part:` fields.
- **What was seen** — the exact call with full JSON arguments, and the response envelope verbatim.
  Entities are named the way the whole report names them: real `name` / `key` plus id, games by name
  and uuid, players by `player_id`. A note the reader cannot check on the stand is not useful.
- **Why it is not a finding** — one or two sentences saying what still works.
- **Suggested action** — optional, one sentence. Write it only when the fix is obvious; the decision
  belongs to the reader.

Full repro steps are not required in a note block. The call and the envelope are enough. If a note
needs a numbered repro to be understood, that is a sign it is really a finding.

## The artifact contract

Before writing section 9, re-resolve every id the run created with a `_get` call — plus the
status-filtered listing wherever the delete verdict says a deleted entity stays listable — and
record the state observed **then**, not the state assumed when it was created.

Every row carries the entity's **real name (or key) and its id**, plus the game it lives in by name
and uuid — the row is what someone uses to find the leftover and clean it up — and exactly one of
three labels:

| Label | Meaning |
|---|---|
| `exists (status: <x>)` | Resolves, and this is its status now |
| `soft-deleted (status: <x>, still gettable)` | Deleted by a tool, row survives, still readable |
| `hard-deleted (id no longer resolves)` | Gone; `_get` fails |

Add `— irreversible` to anything permanently active, permanently deprecated or undeletable. Where
the domain has child state (a test version, a computed count), record that too.

A finding cites only live ids. If a finding's subject was destroyed later in the run, its repro
steps create a fresh subject and the block says the original id no longer resolves.

A delete that contradicts its own AC or tool description — soft where hard is promised, or the
reverse — is itself a finding. So are two tools of one domain deleting differently without the AC
saying so.

## The model

The fictional `F3` and `N2` blocks in this file are the model for every finding and note block,
in structure and in language. Do not open an earlier report as a model: an earlier report is
read only as the baseline of a re-run (`file-layout.md`, comparing runs).
