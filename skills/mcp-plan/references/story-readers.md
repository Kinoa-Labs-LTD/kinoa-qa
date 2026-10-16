# Story readers — every sub-entity of the story is a plan input

The planning chat reads the main story itself and nothing below it. Everything the story carries
— its sub-tasks, its sub-bugs, its linked issues and its own comments — is read whole by
**readers**: sub-agents the planning chat dispatches at interview question 2
(`../SKILL.md`, §2). This file is the one home of how that is done: the key list and its batches,
the reading model, the read route, the brief, the output shape and the merge. The planning chat
reads it at question 2 and not before; the execution chat never reads it, because `mcp-run`
dispatches no reader.

Contents: [why readers](#why-readers) · [the orchestrator](#the-orchestrator) ·
[the read route](#the-read-route) · [the brief](#the-brief) · [the output shape](#the-output-shape)
· [the merge](#the-merge) · [in an eval](#in-an-eval).

## Why readers

- A story can carry many sub-entities. KING-22308 carries fifteen, and its research sub-task
  alone is about 10,000 characters. Read inline, they fill the planning chat's context before the
  first case is written.
- Reading and quoting needs no stronger model than the cheaper one. On 2026-10-12 a comparison on
  a 52-case slice gave the same grades at about 40% of the cost.
- The batch, not the category, is the unit of work. A reader that sees a key's description and
  its comments together settles "which text is newer" in place, where both texts are visible. One
  reader covers most stories, and a larger story still fits in a few batches.
- A sub-task's title does not say what its text holds. KING-22527 `[FE] Research validations for
  Feature Schemas` is a table of the dashboard's rules per field; a plan that treated it as a work
  item never saw that `tableFields[].level` is required there and optional in the served schema
  (verified at commit `e375f2d`, 2026-10-15).
  The dashboard then refused every schema created through MCP (KING-23439, filed as KING-23448 by
  a person, not by the run).

## The orchestrator

The planning chat is the orchestrator.

1. It reads the **main story** itself: the description, the acceptance criteria, and the lists
   of sub-tasks, sub-bugs and linked issues with their keys, types and link types. It reads
   nothing below the story, except as [the merge](#the-merge) says after two reader failures.
2. From those lists it builds **one key list** in the story's own order: sub-tasks, then
   sub-bugs, then linked issues. The story's own key goes first, for its comments only.
3. It cuts the list into **batches of at most ten keys** and dispatches **one reader per batch,
   all in one message** — in parallel when there is more than one batch — with the harness's
   sub-agent tool, on the reading model named in `<plugin>/config.json`
   (`mcp.reader_model`, default `sonnet`; in Claude Code the dispatch passes that value as its
   `model`).
   The orchestrator itself stays on the chat's own model.
4. A story with no sub-entity and no comment gets no reader.

Bug, rules and facts are kinds of output, not kinds of reader: every reader looks for all three
in every key of its batch.

## The read route

A reader reads a key through the Jira connector of the session. When the issue tools of that
connector refuse — for example a 403 "the app is not installed" — it tries, for the same key, the
connector's graph tools, or its search tool with that one key as the whole query (`key = <KEY>`).
This is a read route for a key the story carries, not the search for related issues that question
10 of the interview forbids. When nothing returns the text, the reader reports the key as
`unreadable: <error>`, and the orchestrator asks the operator to paste the text of those keys in
the one interview reply. Neither a reader nor the orchestrator opens a browser for it. (On
2026-10-15 one session got the 403 from the issue and JQL tools while the graph tools worked;
another session's run read sub-bugs through the issue tools fine.)

## The brief

The brief is the same for every reader; only the key list differs.

- Read **every key on your list whole**: its description, the names of its attachments, and its
  comments, together, key by key.
- A linked issue is read one level deep: the issue itself, never its own sub-entities or links.
  A key that only a sub-entity's own links or text name is not a row of its own: it stays inside
  the quoted text of the row it came from, and the plan cites the sub-entity, never that key
  (`../SKILL.md`, §2, question 10).
- The story's key, first on the list, is read for its comments only. Its description and
  acceptance criteria belong to the orchestrator.
- Skip a key only when it is **empty**: no description and no comment, a title alone. Report it
  as `empty`. One sentence is not empty.
- Open no key outside the list. Run no JIRA search beyond the one-key read route above. Call no
  Kinoa MCP tool. Write no file. Judge nothing about coverage: extract and quote.
- Where a comment of a key contradicts its description, give one row with both versions and mark
  the newer text as the one that stands. You are the one context that sees both.
- A source a text only points at — a Confluence page, a local file — is named as a fact and never
  fetched. The orchestrator takes it only when the operator pastes it or gives its path.

## The output shape

Per key, one status line — `<KEY>: read`, `<KEY>: empty` or `<KEY>: unreadable: <error>` — and
then rows of three kinds, or the word `nothing`. Every row names its key and the place in the
text it came from: a table name, a heading, a comment's date and author.

| Kind | What it is | Where it goes in the plan |
|---|---|---|
| **bug** | a defect report: a sub-bug, a linked bug, a known-issues list in a description or a comment | question 10 and §1.2, unchanged (`plan-template.md`, §1.2) |
| **rules** | any statement about the entity or its endpoints that a case can check: a validation table per field, an audit of what the dashboard sends and refuses, a list of what the back end now validates, a transition graph, limits, defaults — quoted as written (`language.md`). A rule found in a work item counts the same as one found in a research task. A field the text marks "no rule" is not a rule: it is `nothing` for that field | §1.3 (`plan-template.md`, §1.3) |
| **facts** | anything a case cannot check but the plan should know: tool or endpoint names, which fields the dashboard never writes, a sibling report, a source the text only points at. A linked issue whose content is about another surface — a dataset, a dashboard page, another tool family — is `nothing`, not a fact: a plan does not list every unrelated link as out of scope (example: "add a daily widgets dataset to the analytics catalog", linked to a widgets-tools story, is `nothing`) | §1 as a domain fact, or the tool inventory of question 2 |
| **nothing** | not a row kind: the key was read and holds nothing of the three kinds; said so, with the key | the interview message only |

One key may feed several kinds. A contradiction between a comment and the description is one row
with both versions and the newer one marked as standing.

## The merge

When there was more than one batch, the orchestrator merges the extracts: one list of
sub-entities marked `read`, `empty` or `unreadable`; one list of rules with duplicates folded (the
same rule in two keys is one row with both sources); one list of bugs; one list of facts. The
lists go out in the first message with the interview, so the operator can move an item between
kinds and overrule a newer-wins row in the one reply.

A reader that fails, or answers without a status line per key, is run once more on the same
batch. After that the orchestrator reads those keys itself. No key is ever skipped because a
reader failed.

## In an eval

In an eval the sub-entities arrive as pasted JIRA text in the prompt. The orchestrator hands each
reader the text of its keys in the brief instead of the keys alone; the batches, the brief, the
output shape and the merge are unchanged.
