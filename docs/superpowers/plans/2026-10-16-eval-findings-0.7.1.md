# Eval findings 0.7.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps the 0.7.0 eval run of `mcp-plan` and `mcp-run` found: skill text, four new layout checks, eval assertions, version 0.7.1.

**Architecture:** Every rule gets one home (`file-layout.md`, "Where each rule lives"); the SKILL files point at it. New mechanical checks go into `check-layout.sh` with unit tests in `test_check_layout.py` and `test_mcp_skills.py`; eval changes go into the two `evals.json`. After the edits, every eval of both skills is run once in a scratch home by a subagent and graded by a second subagent.

**Tech Stack:** Markdown skill files, bash + awk + perl (`JSON::PP`) in `check-layout.sh`, Python `unittest`, Claude Code subagents for the eval run.

**Spec:** `/Users/shepeliev/Desktop/KINOA/kinoa-AI-skills/kinoa-qa-evals-20261016/CHANGE-REQUEST-kinoa-qa-eval-findings-20261016.md` (evidence next to it under `evidence/`).

## Global Constraints

- Branch `chore/KING-23440-rules-pass`; commit, never push.
- One home per rule; other files link, never restate. `check-layout.sh` check 4 (owned phrases) must stay green.
- Red-flag cells at most 25 words; prose in simple English (`language.md`).
- No plan or report under the real `~/.kinoa-qa/mcp/` is edited; every eval runs with `HOME=<scratch home>`.
- No eval assertion is weakened; a split or reworded assertion keeps every check it had.
- The new checks (22–25, check 18's KEY extension) fire only for plans dated 2026-10-16 or later.
- Version `0.7.1`, one `CHANGELOG.md` entry for the whole request.
- `python3 -m unittest discover -p "test_*.py"` in `skills/testplan/scripts` stays green; `check-layout.sh skills/mcp-run/evals` prints no PROBLEM.
- Deviation, decided up front: B.5 keeps fixed-data.md's rule (a plan whose Part B has no `ADMIN_API` is run with the operator applying the rows, plus a plan-defect row), because the request's `BLOCKED` reading contradicts fixed-data.md and its own D.6.

## Review Focus

1. Check 23 on a Call cell whose JSON string holds `{` or `}` (the owner ruling `${x} }`): the brace scanner must honour JSON strings. Test in Task 6.
2. Check 23 on a cell with an escaped `\|` inside the JSON: the held pipe byte is a plain `|` for the parser. Test in Task 6.
3. Check 24 on a `game_id` literal uuid of §0 (not a handle): accepted. Test in Task 6.
4. Check 22 on a report whose status cell is not backticked, and on a `BLOCKED` row (never required). Test in Task 6.
5. Check 18 KEY extension must not match `KEY` inside a longer token such as `CONFIRM_KEY_x`. Test in Task 6.

---

### Task 1: Part A, items in `mcp-plan/SKILL.md` and `rules.md` (A.1, A.2, A.6, A.7, A.9, A.10)

**Files:**
- Modify: `skills/mcp-plan/SKILL.md` (§0 fence, §1 "Reports exist", §2 intro, q6, q10, §3 hand-over, red-flag tables)
- Modify: `skills/mcp-plan/references/rules.md` (target and method closed list; pauses (b))
- Modify: `skills/mcp-plan/references/plan-template.md` (PART B skeleton line: the intro states both numbers)
- Modify: `skills/mcp-plan/references/story-readers.md` (keys from a sub-entity's links)

- [ ] **Step 1: A.2** — §0 fence becomes `git -C <repo root> fetch --quiet && git -C <repo root> status --branch --porcelain | head -1 && git -C <repo root> rev-parse --short HEAD`; prose: "The first line must name `develop` … The second line is the sha of `**Checked against:** commit <sha>`." rules.md closed list: "the branch-state line (`git fetch`, `git status`, `git rev-parse`)".
- [ ] **Step 2: A.9** — rules.md closed list, after `check-layout.sh`: "and, only where the harness has no file-search tool, one read-only search in two forms: `grep -n '<pattern>' <file>` for a heading or row search in one file, and `grep -rln '<pattern>' <folder>` to find source files in the kinoa-mcp repo (layer 4). Nothing else joins the list: no `wc`, `cat`, `sed`, `head`, `find`, `ls -la` or `echo`." SKILL.md §1: "Find the parts with the harness's file-search tool, or `grep -n` where there is none (`rules.md`, target and method)", and the §1 fence gains `grep -n '^## |^### Case status|Plan defect' ~/.kinoa-qa/mcp/reports/<report file>   # only where the harness has no file-search tool`.
- [ ] **Step 3: A.1** — q6: "**Checkpoints** — how many role states Part B puts in place. The number counts role states only; the restore checkpoint always comes after them and is never counted. Default: the number the previous plan version used, else one per role state the mapping of question 9 needs; the restore comes on top. … The plan's Part B intro states both numbers (`plan-template.md`, the skeleton)." plan-template.md PART B skeleton: "Its first line states both numbers: `<N> role checkpoints, then the restore`."
- [ ] **Step 4: A.6** — §2 intro: "A question the request answered is not asked. The first message lists it once under **From your request**, with the value as it will be written. "A default is a proposal, not an answer" applies only to defaults this chat proposes." Red-flag row (Fixed data and roles table): `"The operator said it, but I will confirm it anyway" | A question the request answered is not asked again (§2).`
- [ ] **Step 5: A.7** — q10: "A key that only a sub-entity's links or text name is not cited either: the plan names the sub-entity that carries it, never the key." Red-flag row (Scope table): `"The key is right there in the code comment" | The hypothesis names the code line, never the key (§2, question 10).` story-readers.md, the brief: "A key that only a linked issue's own links or text name is not a row of its own: it stays inside the quoted text of the row it came from, and the plan cites the sub-entity, not that key (`../SKILL.md`, §2, question 10)."
- [ ] **Step 6: A.10** — rules.md pauses (b), after "The case in flight gets no row.": "That holds when the deciding envelope was not captured. A row that [writes](#writes) grades on the preview leg gets its row as soon as that envelope is in the file — a `FAIL` when the preview minted a token — and the confirm leg that rule then sends is the first step of the new chat, written in the finding as "confirm leg not sent: the connector dropped"."
- [ ] **Step 7:** run `bash skills/mcp-plan/scripts/check-layout.sh skills/mcp-run/evals` → no PROBLEM; run the unit tests → OK. Commit `KING-23440 mcp-plan: checkpoints count role states, rev-parse, answered questions, cited keys, grep where no file search, confirm leg after a drop`.

### Task 2: Part A, the report read, research rows and the hand-over (A.3 text, A.4, A.5 text, A.8)

**Files:**
- Modify: `skills/mcp-plan/SKILL.md` (§1 "Reports exist"; §3 hand-over)
- Modify: `skills/mcp-plan/references/plan-template.md` (§1.3 row size with example; the whitespace rule)
- Modify: `skills/mcp-plan/references/story-readers.md` (output shape: a linked issue about another surface)
- Modify: `skills/mcp-plan/references/background.md` (one line, the regression of 2026-10-16)

- [ ] **Step 1: A.3 text** — §1 "Reports exist": add to the read set "the `### Case status` table of section 3 (which rows were sent and graded; a report without that table: all of section 8)"; the search pattern becomes `^## |^### Case status|Plan defect`; keep "no other section shapes the next version". background.md, under "The pruning pass … (KING-23440)": "- **The case status table is read by the planner; check 22**: the eval run of 2026-10-16 retired `create-schema-15` and `list-schema-07` of the webhooks v2 plan again, although the 20260916-0944 report graded both; the planner could not see the rows the report graded."
- [ ] **Step 2: A.8 rows** — plan-template.md §1.3, replace "One row per rule of every research input" with "One row per clause that a case can check on its own, of every research input the header names" and add, after the three covering rules, the example: the KING-99006 table `name: required; 1..255 characters; not trimmed` gives three rows (`name` required / `name` 1..255 / `name` not trimmed), `slots[].title: required; unique among siblings` two, and a sentence that holds one rule ("the status of a new widget is always DRAFT; a status sent on create is refused") one row per sentence clause.
- [ ] **Step 3: A.4** — plan-template.md §1.3 covering rules, new bullet: "**a rule about trimming or whitespace** ("not trimmed", "whitespace counts") is covered by two cases: a value with surrounding whitespace, read back as sent, and a whitespace-only value, whose `Expected` follows the research (for "whitespace counts": accepted and stored as sent)."
- [ ] **Step 4: A.8 nothing** — story-readers.md output shape, `facts` row: "… a sibling report, a source the text only points at. A linked issue whose content is about another surface — a dataset, a dashboard page, another tool family — is `nothing`, not a fact: a plan does not list every unrelated link as out of scope (example: "add a daily widgets dataset to the analytics catalog" on a widgets-tools story)."
- [ ] **Step 5: A.5 text** — SKILL.md §3, after the PROBLEM sentence: "The hand-over says which properties of the plan `check-layout.sh` checked, by check number. A property the chat checked only by reading is written as `checked by reading, not verified`, never as checked."
- [ ] **Step 6:** check-layout on evals, unit tests, commit `KING-23440 mcp-plan: read the case status table, §1.3 one row per clause, whitespace probes, honest hand-over`.

### Task 3: Part B, `mcp-run/SKILL.md`, `rules.md`, `report-blocks.md`, `language.md`

**Files:**
- Modify: `skills/mcp-run/SKILL.md` (§1 fence `date` comment; steps 6, 7)
- Modify: `skills/mcp-plan/references/rules.md` (statuses: the transcript rule)
- Modify: `skills/mcp-plan/references/report-blocks.md` (artifact contract: fourth label)
- Modify: `skills/mcp-plan/references/language.md` (the label list)

- [ ] **Step 1: B.1** — fence comment: `date -u +%Y%m%d-%H%M   # the STAMP, once, at the start of a new run; not for a report from a transcript (step 7)`. Step 7 gains: "A report written from a transcript takes the stamp the operator gives and runs no `date`; with no stamp given, ask for it before the file is created."
- [ ] **Step 2: B.4** — step 7: "When the operator names a report file that is not in the folder, create it under the given stamp from the captured envelopes; section 3 says the file was created, not resumed."
- [ ] **Step 3: B.5** — step 6: "A plan with no Part B: print no `curl` line; the run sends no snapshot `GET` of its own before B1 (a `pre-` case that sends it is still a case), and section 10 says no checkpoint ran. A plan with Part B but no `ADMIN_API` in §0: print no `curl` line, add a `Plan defect for the next version` row in section 8, and the operator applies the rows (`fixed-data.md`, games and players; `rules.md`, Part A / Part B)."
- [ ] **Step 4: B.2** — rules.md statuses, extend "A report written from a transcript grades the one captured attempt and says that no retry was sent." with: "Section 3 writes each value the transcript does not hold — the write list's source, `USER_ID`, `ROLES_BEFORE` — as `not captured` and names what is missing; nothing is inferred from the plan or the header. Such a value is a `Plan defect for the next version` row only when the plan itself has no case that records it."
- [ ] **Step 5: B.3** — report-blocks.md artifact contract: fourth label row `not re-checked (last seen: status <x> in <case>)` — "No `_get` was allowed (a report written from a transcript); the state is the last envelope that showed it". Prose: "used only when no call is allowed". language.md: add the label to the artifact-label list.
- [ ] **Step 6:** check-layout on evals, unit tests (test_mcp_skills `connector_check_problems` must still pass), commit `KING-23440 mcp-run: reports from a transcript, a missing report file, plans without Part B`.

### Task 4: Check 18 KEY literals and checks 22–25 in `check-layout.sh` (TDD)

**Files:**
- Modify: `skills/mcp-plan/scripts/check-layout.sh`
- Test: `skills/testplan/scripts/test_mcp_skills.py` (`CheckLayoutOnFixtures`), `skills/testplan/scripts/test_check_layout.py`

**Interfaces:**
- Produces: PROBLEM lines, exact text:
  - 18: `` `KEY_x` in the Call cell of `id` is not in the §0 artifacts table (plan-template.md, cases are data)``
  - 22: `` `id` was graded `PASS` in <report file> but is no case row of this version (plan-template.md, soundness rules)``
  - 23: `` `id` has an argument object that is not JSON once the handles are strings: <perl error, first 60 chars> (plan-template.md, cases are data)``
  - 24: `` `id` sends game_id <value>, which is no §0 value and not named in its Expected cell (fixed-data.md, games and players)``
  - 25: `` `id` describes calls instead of writing them: "<phrase>" (plan-template.md, cases are data)``

- [ ] **Step 1: tests first** (add to `CheckLayoutOnFixtures`, using `current_plan`): `test_flags_a_key_literal_missing_from_the_artifacts_table` (Call `"name": "KEY_b"`, artifacts hold `KEY_a`), `test_a_key_inside_a_longer_token_is_not_a_key_literal` (`CONFIRM_KEY_x` → no PROBLEM), `test_22_flags_a_graded_row_the_next_version_dropped` (v2 plan dated 2026-10-16 + report with `### Case status` holding `` `create-ok-02` | `PASS` `` → PROBLEM; a `BLOCKED` row → none; status not backticked → PROBLEM), `test_23_flags_a_spread_in_an_argument_object` (`[...SYS_R without SYS_R0, {"id": SYS_R0.id}]`), `test_23_accepts_handles_placeholders_and_braces_in_strings` (`{"game_id": P1, "name": "${x} }", "confirm_token": <token of step 1>, "q": "a\|b"}`), `test_24_flags_a_game_id_that_is_no_zero_value` (`"not-a-game"`), `test_24_accepts_a_probe_named_in_expected` (Expected holds `not-a-game`), `test_24_accepts_a_literal_uuid_of_zero`, `test_25_flags_and_so_on_and_an_ellipsis_in_an_object`, `test_new_checks_skip_a_plan_dated_before_2026_10_16`.
- [ ] **Step 2:** run them → FAIL (no such PROBLEM lines).
- [ ] **Step 3: implement.** Check 18: extraction in perl, pattern `(?<![A-Za-z0-9_])(NAME(?:_S)?-|KEY_)[A-Za-z0-9_-]+`. Check 22 (`plan_graded_rows`): plan file name has `-v<N>`, N ≥ 2; newest report of the same `<KEY>-<domain>` by name, skipping `-<letters>` suffixes; rows of its `### Case status` table whose status cell, backticks stripped, is `PASS`/`FAIL`/`OBSERVED`; each id must be a case row of the plan. Checks 23–25 in one perl pass (`plan_call_objects`): per stable-id row, Call cell with `PIPE_HOLD` turned into `|`; walk the cell char by char, tracking JSON strings and escapes, to cut every top-level `{…}`; for 23 replace, outside strings, `<[^>]*>` and `\b[A-Z][A-Z0-9_]*\b` (not `true|false|null`) by `"X"` and decode with `JSON::PP`; for 25 look for `...`, `…` inside each object and `and so on`, `up to the last page` anywhere in the cell; for 24 regex `"(target_)?game_id"\s*:\s*("(?:[^"\\]|\\.)*"|[^,}\s]+)` over the cell: a bare handle must occur in §0 text as a word; a quoted literal must occur in §0 or in the row's Expected cell; anything else must occur in Expected. Gate 22–25 on `NAMES_FROM` like 18–19. Comment block above each check names what it reads, in the style of 18–19.
- [ ] **Step 4:** tests pass; `check-layout.sh skills/mcp-run/evals` prints no PROBLEM.
- [ ] **Step 5: Done-when on the evidence plans.** Copy the eval 0 and eval 2 evidence plans (and the eval 1 v2 plan with the 0944 report) into a scratch data folder; run the script; expect check 25 on `status-sem-01`, `hide-sem-02`, `delete-sem-02`; check 23 on `update-rule-02`, `update-rule-03` (the `...SYS_R` rows); check 18 on `KEY_Upd_Camel`, `KEY_update_x`, `KEY_role_b`; check 24 on `list-iso-03`. Record the output for the final report.
- [ ] **Step 6:** commit `KING-23440 check-layout: KEY literals (18), graded rows stay cases (22), JSON argument objects (23), game_id values (24), no described calls (25)`.

### Task 5: Part D, the evals, and the seeded KING-99003 report

**Files:**
- Modify: `skills/mcp-plan/evals/evals.json`, `skills/mcp-run/evals/evals.json`
- Create: `skills/mcp-run/evals/reports/KING-99003-user-lists-test-report-20260923-1400.md`
- Test: `test_mcp_skills.py` `EvalFixturesExist` (the fixture tree is the closure of the evals: the new report must be listed in eval 3's `files`)

- [ ] **Step 1: D.1** eval 3: key `KING-99104`, story text pasted (a widgets story: list, get, create, delete; AC in one paragraph; "there is no JIRA connector in this chat"; no sub-entities); assertion 3 → "Calls no Kinoa connector tool (kinoa_games_list, kinoa_player_search or any other kinoa_* tool) …"; add "Runs the §0 branch-state line although the operator says the branch is up to date"; add "Lists the answers the prompt gave once, under `From your request`, with the value as it will be written, and asks none of them again".
- [ ] **Step 2: D.2** eval 0: assertion 3 → five assertions (three columns and full JSON with no `and so on`, `...` or `…` in a Call cell; id shapes; deciding assertion before `Also record:`; counts relative to `BASE_`; gap and grey ids wired); add "every refused-probe name sent with `KEY` or `NAME` is a row of the §0 artifacts table (check 18)".
- [ ] **Step 3: D.3** eval 1: assertion 6 → four (next free NN; v1 ids keep meaning; no known-issues section; section order unchanged) plus "`create-schema-15` and `list-schema-07`, which the 20260916-0944 report graded, are still cases of v2"; assertion 7 names the two forbidden forms; assertion 8 → the heading search (`grep -n` where there is no file-search tool), offset/limit reads, no `cat`, `sed`, `wc` or `head`; prompt gains "The operator's one reply to the interview: Confirmed, keep every default."
- [ ] **Step 4: D.4** eval 2: add the game_id / check 24 assertion and the honest hand-over assertion; assertion 6 keeps its text with a trailing note "(kept as a regression guard: no tool of this story takes a player id, so it cannot fail here)".
- [ ] **Step 5: D.5** eval 4: assertion 2 → 11 rows as listed, keeping the content checks.
- [ ] **Step 6: D.6** eval 3 (mcp-run): write the seeded report (sections 1–3: header with Run `20260923-1400`, section 2 `paused`, section 3 with the PB create envelope and a `### Case status` table with no row yet), list it in `files`, assertion 6 → the observables (section 2 says paused, section 10 `not restored` with the rows to put back, final message carries `continue <report file>`, no restore claimed), add the A.10 assertion.
- [ ] **Step 7: D.7** evals 2 and 4 of mcp-run: "writes no script and runs only the commands SKILL.md prints". **D.8** eval 0: assertion 4 + "runs no shell command before the block"; add the order and the no-ToolSearch assertions. **D.9** eval 1: add the stop-early assertion. **D.10** eval 2: assertion 7 reworded; add the tools/list fidelity and the section 8 plan-defect assertions. **D.11** eval 4: add the B.3 label and the §1.2 assertions. **D.12** eval 6: add the 16-row table and the preflight paragraph assertions.
- [ ] **Step 8:** `python3 -c 'import json; json.load(open(...))'` on both files; unit tests; check-layout on evals (the new report: check 3 accepts the name, check 15 skips a stamp before 20261006 — say so in the fixture's note). Commit `KING-23440 evals: key collision, seeded KING-99003 report, split assertions, new assertions from the graders`.

### Task 6: Version 0.7.1 and the changelog

**Files:**
- Modify: `.claude-plugin/plugin.json`, `CHANGELOG.md`

- [ ] **Step 1:** version `0.7.1`; changelog entry `## 0.7.1 — 2026-10-16` listing, per file, what changed (A.1–A.10, B.1–B.5, C, D).
- [ ] **Step 2:** `test_plugin_manifest.py` (top changelog version = plugin version) passes; commit `KING-23440 0.7.1: changelog`.

### Task 7: Run every eval of both skills, Part E included

- [ ] **Step 1:** checksum the real `~/.kinoa-qa`, `skills/` and the kinoa-mcp working tree.
- [ ] **Step 2:** for each of the 13 evals: scratch home under the scratchpad, copy the fixture tree, write `task.md` (the prompt with `<scratch home>` and `<plugin>` resolved), dispatch one executor subagent (general-purpose, in the background, all in parallel) with the executor prompt the 2026-10-16 run used; the executor writes `outputs/final_message.md` and `outputs/actions.md`.
- [ ] **Step 3:** for each finished run, dispatch one grader subagent with the assertions, the task, the executor's outputs, the scratch home and the subagent transcript; it writes `grading.json` (verdict and evidence per assertion, eval feedback).
- [ ] **Step 4: Part E** — evals 5 and 7 run unchanged; if refused again, rerun on another model; if that works, reword the prompt without changing what the assertions grade.
- [ ] **Step 5:** checksums again; collect the per-assertion table; copy the evidence to `/Users/shepeliev/Desktop/KINOA/kinoa-AI-skills/kinoa-qa-evals-20261016/evidence-0.7.1/`.
