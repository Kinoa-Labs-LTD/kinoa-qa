---
name: mcp-plan
description: Use when asked to write or revise a QA test plan for a Kinoa MCP story — a JIRA story whose deliverable is new kinoa_* MCP tools, tested black-box through the deployed stand's MCP connector by a separate execution chat — including a new plan version after a run ("v2", "update the plan from the last report", "fold the report findings into the plan").
---

# Writing a test plan for a Kinoa MCP story

The plan is handed to a **separate execution chat** that has this plugin and the deployed stand's
MCP connector; the repo, if it is open there, is read-only (`references/rules.md`, target and
method). It has to run start to finish from the file alone.

This file is procedure only. Every rule the plan must follow has one home in `references/`
(the ownership table is in [`references/file-layout.md`](references/file-layout.md#where-each-rule-lives)).
Each step below names what to read before it, with the harness's file read tool. Nothing is read
earlier, and no reference is used from memory, because the references change after every run. The
shell runs only the commands this file prints (`references/rules.md`, target and method).

## 0. Branch state, when the source is open

A plan is built from the default branch. If this chat can see the
kinoa-mcp source, run one cheap check first, with the repo root written in place of
`<repo root>`. Run it even when the operator says the branch is up to date:
the line is the evidence, the claim is not. An up-to-date line needs no question — go on with §1.

```bash
git -C <repo root> fetch --quiet && git -C <repo root> status --branch --porcelain | head -1
```

The line must name `develop` or `master`, and it must carry no `[behind N]`. Any other branch, or
a branch behind its remote, means the code in front of you is not the code the plan will be
checked against. Stop and show the operator that line as it is. Do not run `git pull`,
`git checkout`, `git stash` or `git diff`, and do not read the incoming changes to work out what
differs: only the operator pulls or switches the branch. (`git fetch` changes no file of the
project.) Continue after the operator says the branch is updated, and run the check again first. The
plan's `**Checked against:** commit <sha>` line names the commit that check shows.

## 1. Find what exists

Read first, and only these: [`references/fixed-data.md`](references/fixed-data.md) — the constants
the interview collects, and what a missing one does — and
[`references/file-layout.md`](references/file-layout.md#finding-the-files), the section on finding
the files.

Plans and reports live in `~/.kinoa-qa/mcp/`, outside the plugin, so a plugin update keeps them
(`file-layout.md`). The `mkdir` creates the two folders on a first use and changes nothing after.
If either folder cannot be created or written, stop before the interview and name the path: a
plan that cannot be saved is lost with the chat.

```bash
mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports
ls ~/.kinoa-qa/mcp/plans/ | grep -- '<KEY>-'
ls ~/.kinoa-qa/mcp/reports/ | grep -- '<KEY>-'
```

- **Nothing there** — new plan, version 1.
- **A plan exists** — a new version, next `N`, new file; the old file stays, and the new one keeps
  the old case ids (`plan-template.md`, stable case ids).
- **Reports exist** — from each report of the story, newest first, read only the header
  (section 1), the findings (section 4), the notes (section 5) and the rows labelled
  `Plan defect for the next version` in `Not covered / blocked` (section 8); no other section
  shapes the next version. Find the parts with the harness's file-search tool — the pattern
  `^## |Plan defect` on the report file gives the line of every section heading and of every
  plan-defect row — then read each part with the file read tool, from its heading to the next
  heading (offset and limit), and section 8 from its first plan-defect row. Find the sections by
  name, not by number (`file-layout.md`, comparing runs). Their findings, notes and sub-bugs go in
  §1.2 and the reports on `**Earlier runs:**` (`plan-template.md`, §1.2). Their plan-defect rows
  are fixed in the new version. Their cases are added in the mapping pass of §4, never first.

Say which files you found and which one you will write, before writing. The first message carries
the branch line (only when it failed), the files found and the whole interview of §2.

## 2. Ask before writing

Do not start writing until these are answered. All of them go out in the first message, so the
interview takes one reply, not ten: question 1 first, then every other question the request has
not already answered, each with its proposed default where the list below gives one. Ask the
operator to confirm or correct them in one answer. A default is a proposal, not an answer: one
that the reply does not confirm, by name or by a yes to all, is asked once more before writing.
A §0 value never has a default (question 1).

1. **Fixed test data** — first, with no default: the literal value of every constant
   `fixed-data.md` leaves to the operator (`P1`, `P2`, `COMPANY`, `ADMIN_API`, `PLAYER1`,
   `PLAYER2`, every outside fixture and every pre-existing entity the plan leans on). When the
   previous plan version or the operator's saved fixture in memory holds them, show those values
   and ask for a yes. Where they may come from, and what to answer "look them up yourself" with:
   `fixed-data.md`, games and players (empty means ask).
2. **The story** — no default: JIRA URL, and which tools it adds, each by its exact name, unless
   the request already gives both. These names are the tool inventory of the preflight
   (`plan-template.md`, the preflight).
3. **Artifact policy** — default: keep everything the run creates; the other choice is self-clean.
4. **Delete semantics as known today** — hard, soft, or a status flip. Default: `unknown, the sem
   cases establish it`. It becomes a hypothesis.
5. **Irreversible tools** — no default: publish, activate, deprecate, hard delete. Each needs its
   own subject.
6. **Checkpoints** — how many role states Part B may put in place. Default: the number the
   previous plan version used, else one per role state the mapping of question 9 needs, plus the
   restore. The run applies them itself through the admin role API, reads the rows in the
   preflight and restores them at the end (`rules.md`, Part A / Part B), so the rows in effect now
   are not asked. Build Part B around it.
7. **Replica count, and whether writes are disabled** (`KINOA_MCP_DRY_RUN`). Default: the
   previous plan version's header decisions, else `unknown` — the rate-limit probe is then graded
   `OBSERVED`, and the run reads the write mode off its first preview (`stand-facts.md`, the
   dry-run kill-switch). Decides how the rate-limit probe is graded and what the plan can claim to
   cover. Size a flood to what the connector can send (`stand-facts.md`, connector).
8. **Is the server source available in this chat?** Not asked: this chat can see whether the
   kinoa-mcp repo is open, so state what it sees and let the operator correct it. It decides
   whether layer 4 and the hypothesis table are designed from code or from `tools/list` only (see
   `plan-template.md`), and where the answer to question 9 comes from.
9. **Which roles may call which of the new tools.** Default, shown tool by tool: the AC when the
   story states it; else `roles.yml` when the repo is open. With neither there is no default: the
   answer comes from the story owner (`plan-template.md`, with and without the server source).
   Part B cannot be designed without it.
10. **Known issues on the story** — no default. Only what the passed story itself carries: bugs
   linked to it, a known-issues list in its description or in a comment, and the sub-bugs filed
   from an earlier run (found through the reports of §1). Ask for the JIRA key and one line of
   description for each.
   Never search JIRA for related issues, never open an issue the story does not link, and never
   guess that a related bug or task exists: an issue the story does not name is not a known issue
   of this plan. A bug key found
   in the source — a code comment, a commit message — is not one either: the hypothesis names the
   code line, never the key. They belong in §1.2, and they do not shape the coverage (see §4).

**After the answers, check the story's tools against the stand.** Compare every tool name the
story gives with the `tools/list` of the connector this chat sees (the list, not a tool call).
Show the operator every story tool that is not listed, and every listed tool of the domain that
the story does not name. A missing tool is not deployed yet, or it has another name. The plan
still gets its inventory case and its tool section, both expected from the story; the operator's
answer goes in the header decisions. A chat with no connector cannot make this check: the header
decisions say `not done: no connector in this chat`, and the run's inventory cases make it.

## 3. Check the tree, do not change it

Run the check script now, before the first write:

```bash
bash <plugin>/skills/mcp-plan/scripts/check-layout.sh
```

A `PROBLEM` line it prints now was not caused by the plan: do not fix it, and name it in the
hand-over, the chat's last message to the operator.

The planning chat changes no file of the plugin, no reference and no SKILL file, and adds only
its own new plan to `~/.kinoa-qa/mcp/plans/`. The maintainer changes the references in one
pruning pass between runs
([`file-layout.md`](references/file-layout.md#maintaining-the-rules--one-pruning-pass-per-run)).
The plan follows the references as they are now, and no plan text grants an exception to one.
When the reports read in §1 show a lesson about the process — a rule that misled the run, a
missing rule that cost cases, a plan defect a rule would have prevented — write it in the
hand-over under **Rule change proposals**, one line each: the lesson, the report it came from
(file name, and the finding, note or section-8 row), and the home file it belongs in, from the
[ownership table](references/file-layout.md#where-each-rule-lives). With no such lesson,
the hand-over says `Rule change proposals: none`.

## 4. Write it

Read before the first write, in this order: [`references/plan-template.md`](references/plan-template.md)
(the skeleton, cases-are-data, the section order, the preflight, stable ids, the three soundness
rules, hypotheses), [`references/rules.md`](references/rules.md) — only target and method, Part A / Part B,
statuses, writes, subjects and artifacts, and delete semantics; partial runs, capture at the call
and pauses are run-only — [`references/stand-facts.md`](references/stand-facts.md) (the admin
role API, budgets, dry-run, connector) and
[`references/report-spec.md`](references/report-spec.md) (what the run will produce).
Read [`references/language.md`](references/language.md) at the first prose sentence — the header —
and not before. `references/report-blocks.md` is not read here: the execution chat writes the
blocks, and a plan only points at them.

Coverage in this order, because code knowledge contaminates a black-box judgement:

1. **CRUD** — a happy-path case for every tool, on its own subject.
2. **Validations** — schema, tool rules, then the gap hunt.
3. **Role-based access** — one checkpoint per role state.
4. **Grey box** — loophole hunting designed from the source. Last, never mixed into layers 1-3.

Layers 1-3 need only the story, `tools/list` and the role mapping (§2, question 9), never the
code. Layer 4 and the hypothesis table (§1.1) need the server source; what to do when it is not
available is in
[`plan-template.md`](references/plan-template.md#with-and-without-the-server-source), and where
`tools/list` comes from when this chat has no connector is in
[`plan-template.md`](references/plan-template.md#without-a-connector).

**The story comes first, the known bugs come second.** Build the coverage above from the
acceptance criteria and the story text alone. Then make one pass over the known issues — the bugs
linked to the story, the findings of every earlier report, the sub-bugs filed from a run, and
nothing found by searching (§2, question 10) — and map each one onto the plan that already exists:

- a case already covers it, by the covering rule for its kind of row (`plan-template.md`, §1.2)
  → put that case id in its §1.2 row and change nothing else;
- no case covers it → add a case in the tool section it belongs to, with the next free number in
  its `<tool>-<kind>` group, and put that id in the §1.2 row.

A known issue never gets a section of its own, never reorders the sections and never replaces an
AC-derived case, because a plan shaped by its bugs stops covering the AC the bugs are not about.
Each one ends up in §1.2 with at least one case id
([`plan-template.md`](references/plan-template.md#the-skeleton)).

Split into **Part A** (no permission change, runs unattended) and **Part B** (role-gated). Lay the
sections out in the fixed order and give every row a stable id, per
[`plan-template.md`](references/plan-template.md#the-fixed-section-order).

**The file is written in pieces, and each piece is designed when it is written.** The file is
created with the harness's file write tool, every later piece is added with the harness's file
edit tool, and a row is checked by reading it. First write the header, §0 and §1, with §1.1 and
§1.2 as headings only. Then append one section per write: Preflight, each tool section,
§Hand-off, each Part B checkpoint, REPORT. Only then read the code: write §Grey and insert it
before §Hand-off, add the grey-box probes of Part B, and fill §1.1. Then update §0's artifacts
table, the `**Name limit:**` line and the header's `**Checked against:**` with what §Grey added.
Design the cases of a section only while writing that section, and never design the whole plan in
one reasoning step: it hits the output limit before the first line is saved. §1.2 gets its case
ids in the mapping pass above, once the tool sections exist.

## 5. Before calling it finished

**The script checks the shape.** `bash <plugin>/skills/mcp-plan/scripts/check-layout.sh` passes, or
prints no `PROBLEM` line but those it printed in §3, which the hand-over names. What it fails on,
and what each check reads, is in the comment above each numbered check in the script, which is
the one home of that list (`file-layout.md`, maintaining the rules).

**You check the meaning.** Each line names a rule; its definition is in the file in brackets.

- The three soundness rules hold: traced subject by subject in call order, and no case can only
  ever be `BLOCKED` (`plan-template.md`).
- Every row is data, a length probe's value a literal that shows its length, and every reason is
  commentary (`plan-template.md`, cases are data).
- Every `Expected` cell opens with its deciding assertion, the rest after `Also record:`
  (`plan-template.md`, cases are data).
- Every value a case takes from an earlier case is a `Record:` handle of that case, and every
  count is relative to a `BASE_` handle or scoped to the stamp (`plan-template.md`, cases are
  data).
- Every `gap` and `grey-NN` id appears in §1.1 or in the REPORT section's AC list
  (`plan-template.md`, hypotheses).
- The preflight records `USER_ID` and then `ROLES_BEFORE`, in that order (`plan-template.md`, the
  preflight).
- Each delete or lifecycle tool's `sem` cases run the whole determination, in order (`rules.md`).
- The inventory has one case per tool the story names, with the story's names
  (`plan-template.md`, the preflight).
- No case expects a refusal that an owner ruling calls correct: a non-uuid player id, a `${…}`
  in a field name, a reused confirm token (`rules.md`, statuses).
- Each §1.2 row's case really covers it, by the rule of its row (`file-layout.md`, comparing
  runs; `plan-template.md`, §1.2), and every known issue of the story has a row. None of them
  added a section or changed the section order (§4 above, `plan-template.md`).
- Every §0 value came from the interview, none found by the chat (`fixed-data.md`, games and
  players).
- The artifacts table carries the real `name`/`key` of each subject, and the `**Name limit:**`
  numbers were measured on them (`plan-template.md`; `fixed-data.md`, naming every artifact).
- No COMPANY-scope checkpoint tries to tell `P1` from `P2` (`fixed-data.md`).
- Every checkpoint prints its request block in the three shapes, with the handles `ADMIN_API`,
  `USER_ID`, `COMPANY`, `P1`, `P2` and no other scope; the last checkpoint restores
  `ROLES_BEFORE` (`stand-facts.md`, the admin role API; `rules.md`, Part A / Part B).
- Section 1 is pointers plus domain facts (`plan-template.md`).
- Nothing ran but the commands this file prints, no script was written anywhere, and no file of the
  project changed — git's own fetch refs aside (`rules.md`,
  target and method). In `~/.kinoa-qa/mcp/plans/` only the new plan file was added, and no file of
  the plugin changed: no reference and no SKILL file (§3).
- Every process lesson of the reports read in §1 is a line under `Rule change proposals` in the
  hand-over, with its report and its home file, or the hand-over says `none` (§3).

## Red flags — stop and re-read the references

Each row is a thought that sounds like an exception to a rule. The answer names the rule's home;
it does not define the rule.

### Scope — the story and the served surface, with the shell idle

When one of these fires, the plan is built from something other than the story and `tools/list`,
or the chat changes a file that is not its plan.

| Thought | What it actually is |
|---|---|
| "The reference is long, I remember what it says" | References change after every run. Read the current file (the read lines above). |
| "The operator said the branch is up to date, so §0 can be skipped" | Run the check anyway; a claim is not the line (§0). |
| "No connector, so I'll read the tools' code to learn their arguments" | Read only the served surface; the implementation is layer 4 (`plan-template.md`, without a connector). |
| "A script to check my own rows is not testing the stand" | The rule covers every purpose; a row is checked by reading it (`rules.md`, target and method). |
| "`roles.yml` disagrees with the AC, I'll offer to fix it before the run" | The code is read-only and the chat offers no edit; the case expects the AC (`rules.md`, target and method). |
| "The last run taught a lesson, I'll fix the reference now" | The planning chat edits no reference; the lesson is a line under `Rule change proposals` in the hand-over (§3). |
| "This plan needs an exception to a reference, the header can record it" | The plan follows the reference; the change is a line under `Rule change proposals` (§3). |

### Fixed data and roles

A guessed or discovered value makes the plan write into a game nobody chose.

| Thought | What it actually is |
|---|---|
| "The operator said to look the games up myself" | Answer with the list of values you need and wait (`fixed-data.md`, empty means ask). |
| "The last plan, or my memory, has these ids, no need to ask again" | Show them and get a yes; silence is not a yes (`fixed-data.md`, empty means ask). |
| "The operator is leaving, an unfinished plan is worse than a guessed game" | A plan that waits for one answer is still right tomorrow (`fixed-data.md`, empty means ask). |
| "The operator can set the rows in the admin panel, the block is optional" | A checkpoint without its request block makes the run stop and ask (`rules.md`, Part A / Part B). |

### Coverage — the story first

When one of these fires, a tool or a bug ends up unproven while the plan reads as complete.

| Thought | What it actually is |
|---|---|
| "The story lists eight known bugs — that is the test plan" | Coverage comes from the AC; the bugs are mapped onto it afterwards (§4). |
| "The stand lists these tools, so I'll take the inventory from `tools/list`" | A list built from the stand cannot show a missing tool (`plan-template.md`, the preflight). |
| "The delete tool is covered by the token-replay probe" | A tool proven only in §Grey is not covered (`plan-template.md`, soundness rules). |
| "That bug is fixed and merged, a hypothesis note is enough" | Full case, same repro, own id, listed in §1.2 (`plan-template.md`, §1.2). |
| "The schema has no `maxLength`, so a descriptive suffix is safe" | With no declared limit the limit is 30 (`fixed-data.md`, naming every artifact). |
| "A row that ends `BLOCKED` still shows the reader what was not checked" | A check that can only be `BLOCKED` is a §1 line, not a case (`plan-template.md`, soundness rules). |
| "The run will see which part of the `Expected` cell matters" | The deciding assertion opens the cell; the rest follows `Also record:` (`plan-template.md`, cases are data). |
| "The probe is interesting, it can stay unwired" | A `gap` or `grey` row with no §1.1 row and no AC bullet is dropped (`plan-template.md`, hypotheses). |
| "The operator says the delete is irreversible, but the `sem` cases can settle that" | An irreversible tool is an interview answer, not a hypothesis: no case undoes it (§2, question 5; `rules.md`, subjects and artifacts). |
| "The last run's row went out fine, but the new rule says the connector converts it" | A row an earlier report shows was sent and graded stays a case (`plan-template.md`, soundness rules). |
| "The game was empty when I looked, so `exactly 2 items` holds" | Counts are relative to a `BASE_` handle or scoped to the stamp (`plan-template.md`, cases are data). |

### Pace — writing the file

| Thought | What it actually is |
|---|---|
| "I have the whole plan designed, one write saves tool calls" | One write hits the output limit. One section per append (§4). |

Some plans in `~/.kinoa-qa/mcp/plans/` may be worked examples, moved there from the zip copy, that
cannot be run; how to tell them is in `file-layout.md`, finding the files.
