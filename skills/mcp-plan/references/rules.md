# Execution rules

This file is the single home of the execution rules. A plan links to it from its §1 and adds only
the facts of its own domain; the execution chat reads the rules here, not from the plan. The
language rule for every sentence of a plan or a report is in [`language.md`](language.md), read
at the first write of prose.

Contents: [target and method](#target-and-method) · [Part A / Part B](#part-a--part-b) ·
[statuses](#statuses) · [partial runs](#partial-runs) · [writes](#writes) ·
[subjects and artifacts](#subjects-and-artifacts) ·
[delete semantics](#delete-semantics--establish-never-assume) · [capture at the call](#capture-at-the-call) ·
[pauses](#pauses).

## Target and method

- **Deployed test stand, through its MCP connector.** Roles come from the `kinoa_mcp` DB and are
  admin-panel managed, so the local stdio server is not a substitute for the role part — it resolves
  roles from a property, and a role case run against it proves nothing about the stand.
- **The only evidence about the stand is what its MCP connector returns**, in both chats. No other
  channel — REST, SQL, a test, a script — reaches the stand, because the plan and the report are
  read as evidence about the deployed server: a script or a code change in the loop turns them
  into evidence about the script.
- **One channel besides the connector: the admin role API, for the role rows of Part B only.** It
  is stand setup, never evidence. The execution chat sends the `curl` lines a checkpoint of the
  plan prints, the snapshot `GET` and the restore `PUT`s built from
  it (Part A / Part B below), all in the shapes of [`stand-facts.md`](stand-facts.md#the-admin-role-api),
  against the `ADMIN_API` of the plan's §0 and nothing else: no other path of that API, no REST
  endpoint of a tool, no `/mcp` request, and no request for any purpose but putting the rows of a
  checkpoint in place and reading them back. What the API answers is compared with the rows
  wanted and recorded in the report (sections 3 and 10). It grades no case: every case is still
  graded on the connector's envelope alone.
- **No scripts, at any time — except the commands printed verbatim in the chat's own SKILL file,
  and the request lines of the plan's checkpoints.** That list is closed, and it is the single
  statement of what the shell may run: the planning chat runs the branch-state line (`git fetch`,
  `git status`), the `mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports` of the data folder,
  the two `ls` listings and `check-layout.sh`; the execution chat runs the same `mkdir`, the two
  `ls` listings, `date` for the stamp, the one row count of the plan, `check-layout.sh`, and the
  `curl` lines of the admin role API (the bullet above). Nothing else is run, in either phase, in
  the repo, the plugin, the data folder or a scratch folder, and for no purpose: not to check the
  chat's own plan or report, not to prepare, generate, upload or host test data such as a CSV for
  an import-by-URL tool, not to fetch a download link, not to compute a digest or a token, not to
  send many calls quickly for a rate-limit probe, and not to cross-validate a result through REST,
  SQL or a test. The repo, the plugin and the data folder are read with the harness's file read
  and file-search tools, and the plan and the report are written with the harness's file write and
  edit tools; a `cat >>`, a heredoc or a `perl -pi` is a script too, and so is a no-op such as
  `echo`. No printed command changes a file of the project; they write only git's own fetch refs
  and, with `mkdir`, the two data folders. The only printed commands that reach the
  stand are the `curl` lines of the admin role API. No plan and no run adds a script to the plugin
  or the data folder.
- **No change to the project code.** The kinoa-mcp source, `roles.yml`, the `application*.yml`
  files, the tests and the build are read-only for both chats: a fix made so a case passes turns
  the report into evidence about the fix, not about the stand. Reading them is allowed where these
  references say so: for the grey-box design and the hypothesis table in the planning chat, and to
  form a hypothesis in the execution chat. `.git` is not read either: the commit of the checkout
  comes from the branch-state line, not from listing refs. Neither chat edits, generates or
  deletes any of them, and neither chat offers to. When the code disagrees with an acceptance
  criterion — a role pattern that does not cover a tool, a schema that accepts what the AC
  rejects — the case expects the AC and fails; the gap is a finding, never a fix.
- **What the protocol cannot reach stays out of reach.** The file behind a download link, the
  content the server fetched from an import URL, a row in a database: the case grades the envelope
  and says what it could not see, because a file the chat fetched is the chat's evidence, not the
  stand's. A fixture the plan needs outside the protocol, such as a public https CSV, exists
  before the run and is named in the plan; if it is not there when the run reaches it, the case is
  `BLOCKED — fixture not available`, and the chat does not create one.
- **Black box outside §Grey.** Judge what the protocol returns against the story's acceptance
  criteria. Code knowledge informs the grey-box part only (the last layer of the order of work,
  `../SKILL.md` §4), because an expected value copied from the code can only agree with the code.

Following the letter of this rule is how the spirit is kept. "This is data preparation, not
testing", "this checks my own document, not the stand", "this link is meant to be fetched" and
"this is a one-line fix" are the ways it has been broken.

## Part A / Part B

- **Part A** is everything doable with no permission change. It runs start to finish, asking zero
  questions, because a question mid-part stops an unattended run. It runs under the rows
  `ROLES_BEFORE` shows (next bullets), and the report's section 3 states that role. A Part A case
  that turns out to need a role change — a write refused with `PERMISSION_DENIED` under a role
  that `ROLES_BEFORE` shows as insufficient — is recorded `BLOCKED — deferred to Part B` and
  Part A continues. Re-run it at the Part B checkpoint that grants the role and give it its
  final status there: a deferred case is counted **once**, under the status it ended with, not
  once per part.
- **Part B** is everything that needs a role change, one checkpoint per role state. Each checkpoint
  states the exact `user_role` rows wanted — as the **complete** desired state, so stale rows get
  removed rather than layered — and prints the request block that puts them in place: one
  `DELETE` per row to remove, one `PUT` per row to set, then the `GET` that reads the rows back
  (the shapes: [`stand-facts.md`](stand-facts.md#the-admin-role-api)). The run applies the
  checkpoint itself: it sends the block, in order, with the literal values of `ADMIN_API`,
  `COMPANY`, `P1`, `P2` from §0 and `USER_ID` from the preflight ping in place of the handles.
  Nobody is asked; only a checkpoint that prints no request block is applied by the operator.
- **The rows in effect are read, not asked**, because an asked row can be wrong. The preflight
  sends the `GET` once, in the `pre-` case right after `USER_ID` is recorded (`plan-template.md`,
  the preflight), and records its body as `ROLES_BEFORE` in report section 10. A `GET` that
  fails twice (the retry below) leaves that case `BLOCKED — ROLES_BEFORE not recorded`, and
  Part A goes on. When Part B starts and section 10 holds no `ROLES_BEFORE` — that `GET` failed,
  or the plan predates this rule and has no such case — the run sends the `GET` once before B1,
  with the retry and the operator fallback of a checkpoint block (below). A chat that resumes
  inside Part B never sends it (pauses). The restore checkpoint puts exactly those rows
  back: one `DELETE` per row the checkpoints set, one `PUT` per row of
  `ROLES_BEFORE` on a fixture scope, then the `GET`, whose body must equal `ROLES_BEFORE`. A run
  that ends before the restore checkpoint says so in section 10, with `ROLES_BEFORE` and the rows
  the last `GET` showed, so the operator can put them back.
- **A row of `ROLES_BEFORE` on a scope outside the fixture is never written.** It belongs, as it
  is, to the rows wanted of every checkpoint; the restore compares and puts back only the rows of
  the fixture scopes, and section 10 lists the other rows as the `GET` showed them.
- **The `GET` body is compared before it is trusted.** After the block, compare the rows the `GET`
  returned with the rows wanted, row by row: same scope types, same scope ids, same roles, no row
  more. A row that matches nothing — a stale `GAME` row, a `COMPANY` row for another company —
  makes the server answer as Viewer with no message, so a row mistake looks the same as a server
  defect. Rows that match: wait, then grade every case of the checkpoint at once. Rows that
  differ, a `PUT` or `DELETE` answered with anything but `204`, a `curl` error (no route, refused,
  timed out), or a `GET` that is not a `200` with a JSON array: send the whole block once more.
  When the second attempt does not match either, **fall back to the operator**: stop, show the
  request that failed and its answer, the rows wanted and the rows the last `GET` showed, and ask
  the operator to apply the rows in the admin panel and paste them as the panel shows them.
  Compare the pasted rows the same way; when they differ, ask once more. A checkpoint that fell
  back is graded after the pasted rows match; section 3 records the fallback and its reason.
  Nothing before the match is graded: a case run against rows the `GET` or the operator has not
  shown is not a case. A `curl` line that the harness's permission check stops is not an attempt:
  ask the operator once to allow it, or to apply the rows as in the fallback, and never send it
  another way.
- **Wait ≥ 20 s after the rows match** before asserting — twice the role cache
  ([`stand-facts.md`](stand-facts.md#server-budgets-and-timings)). The wait starts when the `GET`
  (or the pasted rows) matched, not when the `PUT` answered.
- **A change to the caller's game access runs on a different clock.** `GAME_ACCESS_DENIED` is
  decided from the `games[]` claim in the caller's own token, not from `user_role`: through the
  OAuth connector that claim is re-read only when the access token refreshes (the games-claim
  line of [`stand-facts.md`](stand-facts.md#server-budgets-and-timings)), so a 20 s wait proves
  nothing. Prefer a probe that needs no games change at all — `FOREIGN`, a well-formed uuid
  belonging to no game, exercises the same denial instantly for a read tool and for a write tool.
  The server checks the `games[]` claim before it looks up the role, so a write case on `FOREIGN`
  expects `GAME_ACCESS_DENIED`, and `PERMISSION_DENIED` is a `FAIL` with a finding.
- **A COMPANY-scope row covers both fixture games.** What that allows and forbids in a checkpoint
  is in [`fixed-data.md`](fixed-data.md#games-and-players).
- The grey-box probes are the last thing in each part, never interleaved with the rest, because a
  probe floods, expires or deletes what a later case expects untouched.

## Statuses

`PASS` / `FAIL` / `OBSERVED` (recorded, no AC to judge against) / `BLOCKED` (could not run — say
why). `BLOCKED` is a valid, expected outcome and always beats a guess: never write a status that was
not observed, because an invented status cannot be told from a real one.

A `FAIL` includes:

- `TOOL_EXECUTION_FAILED` in response to user input — an internal error is never an `OBSERVED`,
  because it is a defect whatever the AC says, and `OBSERVED` hides it from the counts;
- any error code that is neither the expected one nor an internal error but **misdirects the
  caller** — a permanent input mistake answered as a temporary outage, for instance.

**A `TOOL_EXECUTION_FAILED` or a 5xx whose hint says to retry** is sent once more. Before an
executing leg is sent again, the run reads the subject (`_get` or the listing): when the first
attempt took effect, there is no retry: the case is `FAIL`, and its finding block holds the
error envelope and the read. If the confirm token expired during the read, send the preview
again first. A retry that succeeds grades the case, and a note keeps the first envelope: this is
the one internal error that is a note, because a retry cleared it and nothing was left
half-done. When the retry fails too, the case
is `FAIL`, and its finding block holds both attempts and a `kinoa_system_ping` sent right after
them, so the reader can tell an outage from a defect. A report written from a transcript grades
the one captured attempt and says that no retry was sent.

**A tool the story names that the stand does not list.** Its tool-inventory case in the preflight
(`plan-template.md`, the preflight) is `FAIL`, and it gets a finding block. Every other case that
calls the tool is `BLOCKED — tool not on the stand`. The run goes on with the other tools. A header
decision that the tool is deployed under another name does not change that grade: the inventory
case keeps the story's name and fails, and its finding names the listed tool the operator pointed
to. The other cases call the stand's name only when the header records the operator's
confirmation of the rename (`plan-template.md`, the preflight).

**Owner rulings: expected behaviour, never a finding.** The owner has ruled that these behaviours
are correct. A case expects them, and a run never reports them as a finding or a note:

- **A player id or a user id is any string**, not a uuid (2026-09-24). This covers `player_id`,
  `test_player_ids`, user-list members and the caller's `user_id`. A non-uuid value is valid input.
  Blank values, the documented bounds and characters that break a URL can still be refused.
- **A `${…}` inside a field name stays in the generated body** (2026-09-24). The service strips
  only the first, outer `${` … `}` pair of a placeholder. So the field name `${x} }` gives the body
  `{"${x} }":"${${x} }}"}`, and that is expected.
- **A confirm token can be used again** while the arguments stay the same (see Writes below).

A ruling beats a plan case written before it. When a plan row still expects the refusal a ruling
calls correct, grade the case against the ruling, and name the row in section 8 of the report as
a plan defect for the next version. An old finding or note that a ruling covers gets the
`ruled expected` row of the comparison table (`report-spec.md`, comparing with the previous run),
never a block.

**A case is graded on the clause before `Also record:`.** The `Expected` cell opens with the
assertion that decides the case, per step when it has several (`plan-template.md`, cases are
data). A mismatch there is the case's `FAIL`. What follows the label is recorded; a mismatch after
it goes into a note block, never into the status. A row with no label is graded on its whole cell.

**A note is not a status.** While the run happens it will also see things that are odd or
inconsistent but block nothing: two tools answering in different shapes, a confusing message, a
field that is always empty. Each one is written down as a note, in its own report section. A note
does not change the case status, and a case with the status `PASS` can still carry notes. The
note contract, and why a note never replaces a finding, is in
[`report-blocks.md`](report-blocks.md#the-note-block-contract).

**A scope exclusion is the operator's, and it never edits the plan**, because a report already
cites the plan's rows. When the
operator decides, after a plan version was written, that a group of cases must not run (a
capability is not available, a fixture cannot exist yet), the run records each excluded case as
`BLOCKED — excluded by the operator (<date>)` with the reason in section 8 of the report, and runs
everything else. The plan file stays as it was: no marker is added to a row. An exclusion that is
meant to last goes into the next plan version, as a line in its header decisions and its §1
domain facts, and those cases keep their ids. A partial run is an exclusion too: every case
outside its slice gets the same label ([partial runs](#partial-runs)), so the counts still cover
the whole plan.

## Partial runs

The operator may ask for a slice of the plan: named cases, one plan section, or Part B only. The
slice changes which cases run, never how they run, because a case run out of its context grades
the context, not the tool.

- **The preflight always runs** (§A0 of the plan). The tool inventory, the write list and
  `USER_ID` decide how every other case is graded and how the checkpoint blocks are filled in.
  The dry-run state is read off the first preview the run gets, as in a full run.
- **A case pulls in the cases it depends on.** A case whose `Call` or `Expected` cell uses a
  `Record:` handle (an id, a name, a subject of the §0 handle table) needs the earlier case that
  records that value, so that case joins the run. A state an earlier write left is pulled in the
  same way, through the handle that write records (`plan-template.md`, cases are data). Its own
  dependencies join too, back along the chain, because a value taken
  from anywhere else is a value the run picked, not the one the plan built. A pulled case runs in
  its place in the plan's order and is graded and counted under its own status.
- **A value that was never recorded blocks the cases that use it**, in any run. When the case
  that records it failed before that point or was blocked, each case that uses the value is
  `BLOCKED — <handle> not recorded by <case id>`.
- **Every case outside the slice and not pulled in** is `BLOCKED — excluded by the operator
  (<date>)`, with the reason `outside the slice of this partial run`. These cases share one row
  in report section 8 (`report-spec.md`, the ten sections).
- **Part B in a partial run.** Only the checkpoints that hold a case of the run are applied (a
  case deferred from Part A included), each with its whole block. Every checkpoint states the
  complete role state, so it needs no earlier checkpoint. `ROLES_BEFORE` comes from the
  preflight, which always runs, or else from the one `GET` before B1, and the restore checkpoint
  runs whenever any checkpoint was applied (Part A / Part B above).
- **Part B only.** The run is the preflight, then the Part A cases that create the subjects the
  Part B cases name (pulled in by the rule above), then the checkpoints. Those Part A cases run
  before the first checkpoint, as Part A always runs before Part B. A Part B case whose subject
  could not be created gets the `not recorded` label above, naming the case that should have
  created it.
- **The overall status** comes from the usual rule (`report-spec.md`, the overall status), on the
  cases that ran. The excluded cases count as `BLOCKED` and change nothing else.
- **The previous report's ids** are re-checked only when the case that §1.2 names for them is in
  the run. Every other id gets the `not re-tested` row of the comparison table, with the reason
  `outside the slice of this partial run`. An id with no §1.2 row is re-run from its old block
  only when the operator named it.

## Writes

A write tool is one whose `tools/list` annotations do **not** carry `readOnlyHint: true` — that is
exactly how the server decides, so the preflight reads the write list off the protocol rather than
inferring it from tool names. Some connectors do not show the annotations. Then the write list is
the tools whose input schema declares a `confirm_token` property: the registry adds that property
to every write tool's served schema and no tool may declare it itself. The report's section 3
says which of the two sources the write list came from.

- **Two calls.** First without `confirm_token` → a preview envelope that changes nothing, verified
  by the read named in the case. Then the same call plus `confirm_token` → execution.
- **"The same call" means the same arguments, not the same bytes.** The token binds a digest of the
  arguments canonicalized with recursively sorted keys, so key order and whitespace are free.
  Everything else is binding: a changed value, an added argument, a dropped argument, an argument
  sent as explicit `null`, a different tool, a different caller.
- **Both rejections arrive as `CONFIRM_TOKEN_INVALID`, and only the message separates them** —
  `payload mismatch: arguments differ from the previewed call` versus `confirm token expired`.
  Quote the message in the report.
- **A confirm token is reusable while the arguments stay the same.** It is not single-use: inside
  its TTL, the same confirm call (same arguments, so the same digest) executes again. This is by
  design (owner ruling, 2026-09-24). A reuse probe never fails because the second call executed.
  It grades what the second execution did against the AC and the tool description: a refusal by
  state, an idempotent no-op, or the same previewed change done once more are all expected. It
  fails only when the second execution acts on something the preview did not show, for example a
  different row behind the same natural key. An export with `submit_replace` whose reuse deletes
  the row the first execution created and creates a new one is that failure (owner, 2026-09-24).
- A preview whose token is never confirmed simply expires. That is the normal way to probe a write
  without performing it.
- **The permission check runs before the write gate.** A role-denied or game-denied write is
  refused on the *first* leg and never receives a token, so expect `PERMISSION_DENIED` /
  `GAME_ACCESS_DENIED` in place of a preview rather than after one. A denied write also spends no
  preview budget.
- With the dry-run kill-switch on there is no second leg at all — see
  [`stand-facts.md`](stand-facts.md#the-dry-run-kill-switch).

## Subjects and artifacts

- **Artifacts stay, unless the plan's header decisions say self-clean.** Then only the plan's own
  cleanup cases delete, and section 9 labels what they left. Otherwise everything the plan creates
  is left in place and listed in the report.
  Pre-existing data in every game is read-only: never renamed, never updated, never activated,
  never deprecated, never deleted, and never used as a write subject, because the run cannot
  restore the operator's own data.
- **A subject reserved for a later case or a later part is named as such, and no earlier case writes
  to it**, because a write to it changes the state the later case asserts on. Schema-rejection
  rows may name it, since nothing reaches the service; a write may not.
- **Every destructive, irreversible or churning case gets its own subject**, created for it: the
  delete determination, the rate-limit flood, the token replays, the double-activate race.
- **When a finding will cite a deleted entity, create two identical subjects and delete one**, so
  the evidence survives.

## Delete semantics — establish, never assume

Kinoa deletes are not uniform. Some tools **hard**-delete: the row is gone, `_get` returns not found
and the entity is absent from the unfiltered listing and from every status filter. Some
**soft**-delete: a status flips to deleted / deprecated / inactive, the row stays, and the entity is
still gettable and still listable under that status. A domain can mix both across its own tools, and
a status flip can be irreversible — a delete that leaves a permanent artifact.

**One determination per delete or lifecycle tool**, never one per domain. It is a run of
consecutive `sem` cases in that tool's section, because it needs more calls than one case may
hold (five steps, `plan-template.md`). The first case starts right after the confirmed call, and
each later case starts from a `Record:` value of the one before. Together the cases run, in order:

1. `_get` on the subject;
2. the **unfiltered** listing, paged to the end;
3. the listing filtered by **every** status value the tool accepts, and by all of them together;
4. the same reads on the untouched twin, as the control.

Comparing the unfiltered total against the all-statuses total is part of the case: a smaller
unfiltered total means the default listing hides a status, so an agent asked to inventory a game
under-reports — a finding independent of the delete question.

Repo reading may form the hypothesis. Only the protocol settles it. The verdict goes in report
section 3 and governs every artifact label in section 9.

## Capture at the call

The report is written while the run happens, with the harness's file write and edit tools, and
none of what it holds can be reconstructed afterwards:

- **Verbatim, at the call, every envelope the report needs**: the request and the response that a
  finding, a note, a hypothesis verdict or a `Record:` value rests on. Every other case is
  recorded by its row in the case status table (`report-spec.md`). A reconstructed or guessed
  envelope is not evidence: a response not captured is written as not captured, and the case is
  `BLOCKED — response not captured` when its grade depends on that envelope. How a captured
  envelope may be shortened inside a block is in `report-blocks.md` (the finding block).
- **Isolation evidence while the state is live.** The control probe, the narrower repro and the
  neighbouring call that works exist only while the subject is in the state the defect needs; a
  later case or a pause changes it.
- **A note at the moment it is seen**, with its envelope, because a note written from memory at
  the end has no envelope to check.
- **Every subject by its real name and id at the moment it is created.** The report is read
  without the plan and without the chat history (`report-spec.md`, naming things), and the id is
  only in the envelope that created it.
- **One case at a time into the file.** Before the next tool call, the case just run has its row
  in the case status table, every `Record:` value it produced is in the section 3 paragraph of its
  plan section, and, when it failed or showed something odd, the envelopes its finding or note
  block needs are in the file. The block may be finished later; the envelopes may not, because a
  compaction drops what was only in the chat with no sign of what was lost. `ROLES_BEFORE` goes
  into section 10 the same way, as soon as the `GET` answers.

## Pauses

The run may span hours. Everything that expires — confirm tokens, the role cache, a rate-limit
window — is void after a pause: re-mint it and re-run the case rather than reporting the expiry as a
defect. Record where the run paused and resumed in section 3. A
run resumed in a new chat continues in the same report file under the same stamp
(`mcp-run/SKILL.md`, §1): a new stamp would make the run's own artifacts look like another
run's leftovers.

**A long run hands over to a new chat before its context runs out**, because a compaction drops
envelopes that were not yet in the file ([capture at the call](#capture-at-the-call)).

- **When:** the harness warns that the context is getting full, a compaction has happened, or the
  chat has made about 120 tool calls (connector calls, `curl` lines and file writes together).
  The number is a guide, not a limit: a run with long envelopes hands over sooner.
- **Where:** in Part A after any case, with the report file saved, because every `Record:` value
  is already in the file; in Part B only after the last case of a checkpoint. A checkpoint is
  never split between two chats: its rows, the 20 s wait and the grading of its cases belong to
  one chat, because a role state the new chat has not seen is a role state it cannot grade against.
- **How:** the hand-over names the report file, the last row of the case status table and the
  next case, and tells the operator to start a new chat with `continue <report file>`.
- **A connector that drops** or loses its authorization mid-run is handed over at once, wherever
  the run is. The case in flight gets no row; the new chat, started once the operator has
  connected it again, runs that case again, reading its subject first when the lost call was an
  executing leg (statuses, retry), and inside Part B sends its checkpoint's block again (a chat
  that resumes inside Part B, below).
- **After a compaction**, compare the case status table with the cases run before going on. A
  case whose grade depends on an envelope that is not in the file is run again, when it is a read
  or its subject is still in the state the case needs. Otherwise it is `BLOCKED — response not
  captured`. It is never graded from memory, because a summary of a response is not the response.
- **A chat that resumes inside Part B** reads `ROLES_BEFORE` from section 10 of the file and
  never takes the snapshot again, because a new snapshot would record a checkpoint's rows as the
  rows to restore. Before it grades any case, it sends the block of the checkpoint that case
  belongs to, even when an earlier chat already sent it, then compares the `GET` rows and waits
  20 s, as in Part A / Part B above.
