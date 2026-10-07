# Fixed test data

Use these rigidly. Never substitute one, never discover an alternative, never let the execution chat
pick its own: a substituted value makes the report describe a game nobody agreed to test, and a
write goes into that game. The values of the games and players come from the plan's §0 and from
nowhere else; this file says what each constant must be, not what it is. The facts about the stand
itself — the admin role API, the budgets, the dry-run switch, the connector — are in
[`stand-facts.md`](stand-facts.md).

## Games and players

The constants below are the **operator's own fixture**. Their values are not part of this skill
tree: they are collected in the plan interview (`../SKILL.md`, §2, question 1) and written literally
into §0 of the plan.

| Constant | What the operator supplies | Role |
|---|---|---|
| `P1` | a game uuid and the game's name exactly as `kinoa_games_list` shows it; an operator's label goes in brackets after it | Primary game: all CRUD, validations and loophole probes |
| `P2` | a game uuid and the game's name as for `P1`; **the same company as `P1`** | Secondary game: cross-game isolation, scope precedence |
| `COMPANY` | the uuid of the company that owns `P1` and `P2`, as the admin panel's company page shows it | Scope id of every `COMPANY` row of Part B |
| `ADMIN_API` | the base URL of the stand's admin panel API: `https://<stand host>/internal/mcp-admin/api`, no trailing slash | Where the run sends the role requests of Part B ([`stand-facts.md`](stand-facts.md#the-admin-role-api)) |
| `PLAYER1` | a `player_id` that **exists in `P1` only** | First player: the positive case of every player-taking tool |
| `PLAYER2` | a second `player_id` that **exists in `P1` only** | Second player: membership contrasts, cross-game negative case |
| `FOREIGN` | fixed: `00000000-0000-4000-8000-0000000000ff` | Well-formed uuid belonging to no game — game-access-denied probes |

No login, e-mail or password is a constant. Neither chat needs one: the connector's OAuth login
identifies the caller, and the `user_role` rows of Part B are keyed by `user_id`, which the
preflight reads from `kinoa_system_ping` as `USER_ID` and the report records. A plan never asks
for an e-mail and a report never prints one. `COMPANY` and `ADMIN_API` are asked like the games, in the
same interview question, and only a plan with both can apply its own checkpoints
([`rules.md`](rules.md#part-a--part-b)); a plan without them is run with the operator applying
the rows.

Two more kinds of value are constants of the same kind — asked in the interview, written in §0
with their own handle, never found by the chat:

- a fixture outside the protocol — a webhook target URL the operator owns, a public https CSV —
  which neither chat creates, because a fixture the chat made is the chat's evidence, not the
  stand's (`rules.md`, target and method);
- a pre-existing entity in `P1` or `P2` that a plan leans on and never writes to, because the run
  cannot restore the operator's own data — an already ACTIVE webhook, a template with live
  in-apps, a calculated player field for audience rules. The operator names it (id, and name where
  it has one); a `pre-` case confirms it is there.

An entity a case needs that the operator cannot name is not an open question in the plan. The plan
creates it in an earlier case and passes it on by a `Record:` handle. When no tool can create it,
the case is left out, and section 1 of the plan names what is missing in one line. A plan never
records an exception to this file.

A `pre-` case that confirms the fixture grades the plan, not the server. An id that is missing on
the stand makes the run `BLOCKED — fixed data wrong in §0`. A name that differs from the stand is a
`Plan defect for the next version` row in report section 8, never a finding
([`report-spec.md`](report-spec.md#naming-things--the-whole-report-not-just-the-findings)).

**Empty means ask.** A constant with no value is filled in one way only: the operator gives it in
the planning chat, before anything is written — asked in the first message. The planning chat may
show the operator two things and ask whether those values still hold: the §0 of the previous
version of the same plan, and a fixture the operator saved in the chat's memory. A yes is an
answer, silence is not, and a saved value is never used without that yes, because a fixture can
change between two stories; a redacted `<…>` value is no value. Nothing else is a source: not
`kinoa_games_list` or `kinoa_player_search` through the connector, not another story's plan, not
a memory note that is not the operator's saved fixture, not a game that "looks like a test game".
An operator who says "look them up yourself" is answered with the list of values the plan needs,
not with a connector call: that permission does not make a discovered game the operator's
fixture. A plan that waits for one answer is still right tomorrow. The plan is not started until
every constant is literal, and it is not finished while §0 holds a placeholder or an empty cell
(`plan-template.md`, §0).
`check-layout.sh` check 6 enforces the shapes (its comment in the script); it cannot tell a real
value from an invented one.

**The run reads §0 and nothing else.** The execution chat takes every constant from the plan's §0.
A placeholder, an empty cell or a `**Fixed data:** redacted` header line means the plan cannot be
run: the whole run is `BLOCKED — fixed data missing in §0`, before case 1, naming the constants.
The runner never fills them in, never looks them up, and never asks for them mid-run: a value
asked mid-run lives in the chat only, so the plan stays unrunnable for the next run. They go
into a new plan version through `/kinoa-qa:mcp-plan`, and the run starts from that version.

**`P1` and `P2` must belong to the same company**, and the interview confirms it. That property
decides how the scope cases are built: a COMPANY-scope `user_role` row covers **both** games at
once, so it can never be used to give one game a role and leave the other at Viewer. Only a
GAME-scope row on `P1` plus a COMPANY row is a real precedence test (GAME wins for `P1`, COMPANY
still applies to `P2`), and "COMPANY role on P1's company does not reach P2" is not a case this
fixture can express — do not write one, because it can only pass or fail for the wrong reason.
Cross-game *isolation* cases are unaffected: they turn on the `game_id` argument and the `games[]`
claim, not on the company.

Bind the players as `PLAYER1` / `PLAYER2` **in that order**, and keep the same two players across
the plans of one installation, because the labels are how two stories' reports are compared.

Both players existing in `P1` only is a requirement, not a limitation: it turns every cross-game
player call into a ready-made negative case, and it makes "player of another game" and "player
that exists nowhere" distinguishable — a difference between those two answers is a cross-game
existence oracle.

## Naming every artifact

| Constant | Shape | Example |
|---|---|---|
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured **once** at the start of execution | `20260903-1130` |
| `NAME` | `<KEY>-QA-<STAMP>` — prefix of every name the plan creates | `KING21979-QA-20260903-1130` |
| `KEY` | `<key>_qa_<STAMP with '-'→'_'>` — prefix of every snake_case key | `king21979_qa_20260903_1130` |

One stamp per run makes its artifacts identifiable afterwards, so a run resumed after a pause keeps
its stamp (`rules.md`, pauses).

**Every name and key the plan creates fits the tightest limit of the domain.** `NAME` and `KEY`
are 26 characters on their own (`KING21970-QA-20260924-0820`), so a suffix can push a name over
a backend limit that no schema declares.

- **The limit** is the smallest of: the `maxLength` of the argument in `tools/list`, a limit the
  story states, and a limit an earlier report or a known issue of the story shows. When none of
  them gives one, the limit is **30**.
- **Measure the longest** `name` and the longest `key` of the artifacts table against it, with the
  run stamp at its full length. What counts is the value the entity is stored under, whichever
  constant builds it: an entity whose name field takes a snake_case value built from `KEY` (an
  event name, for example) is measured as a name. A string the plan creates in another field — a
  parameter name, a group, a field path — is measured against that field's own limit in the case
  that creates it, never in this line. §0 states the result in one line under the artifacts
  table, in this shape, so `check-layout.sh` can read it:
  `**Name limit:** 30 — <where the limit came from>; longest name 28, longest key 26`.
- **When a name does not fit**, use the short prefixes for every subject of that domain:

  | Constant | Shape | Example |
  |---|---|---|
  | `NAME_S` | `Q<KEY digits>-<STAMP without the century and the dash>` | `Q21970-2609240820` |
  | `KEY_S` | `q<KEY digits>_<STAMP without the century and the dash>` | `q21970_2609240820` |

  They are 17 characters and start with a letter, so 13 characters are left for the suffix under
  a limit of 30. They carry the same story and stamp, so the run's leftovers stay identifiable.
- **A length probe is never a subject**, because a name at the limit can be refused on the confirm
  leg and every later case on that subject would be `BLOCKED`. A case that sends a name at or over
  the limit, to test the bound, creates nothing that a later case needs.

## Fictional values

The worked examples of the references and the eval fixtures use values that belong to nobody, so
that a copy of them can never write into a real game: the game uuids of the `7d3e1c2…` family
(*Widget sandbox* `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`, *Widget sandbox 2*
`7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c`), their company `7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d`, the
all-zero probes `00000000-0000-4000-8000-…` such as `FOREIGN`, the all-nines probe player
`99999999-9999-4999-8999-999999999999`, players `p_8f2a1c77` and `p_3c9d0e14`, the user id
`u_41c7`, story keys `KING-99001` and up, and hosts under `example.com` (the admin API
`https://mcp-test.example.com/internal/mcp-admin/api`). A new example uses them, never a value
copied from a plan or a report.

`check-distribution.sh` reads this section: every uuid written here in full, and every
backticked uuid prefix that ends in `…`, counts as fictional. Any other uuid in a fixture
position of a shipped file fails CI.
