# KING-99009 — widget create and clone via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99009
**Under test:** `kinoa_widget_create`, `kinoa_widget_clone`, on the **deployed test stand**
**Plan version:** 1 (2026-10-20)
**Report to produce:** `KING-99009-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none
**Decisions from the interview:** artifacts are kept; no role flip (the account is Operator); one
replica; writes enabled; no known issues; story-vs-stand tool check: both tools listed.
**Checked against:** `tools/list of 2026-10-20; server source not available`

This file is an eval fixture of the `mcp-run` skill: a fictional domain with fictional,
literal fixed data, written before the owner ruling of 2026-10-26 that validation lives in the
backend. It is not a plan of a real story.

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `P2` | `7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c` — *Widget sandbox 2* (same company as `P1`) |
| `PLAYER1` | `p_8f2a1c77` — exists in `P1` only |
| `PLAYER2` | `p_3c9d0e14` — exists in `P1` only |
| `FOREIGN` | `00000000-0000-4000-8000-0000000000ff` |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING99009-QA-<STAMP>` |

| Handle | `name` | Game | What it is | Created in | Intended end state |
|---|---|---|---|---|---|
| `W_A` | `NAME-src` | `P1` | the widget whose name the rule cases reuse | `pre-03` | exists |
| — | `NAME-c1` | `P1` | the clone of a source that does not exist | `clone-rule-01` | never created (refused) |

**Name limit:** 30 — no `maxLength` in `tools/list`, so the default; longest name 30, longest key 0

## 1. Execution rules

`mcp-plan references/rules.md`,
`mcp-plan references/report-spec.md`,
`mcp-plan references/fixed-data.md`. Domain facts: both tools are
writes; a widget name is unique in its game; no tool of this domain carries its own rate cap.

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_create` is listed |
| `pre-02` | `tools/list` | `kinoa_widget_clone` is listed |
| `pre-03` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-src"}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` | 1. `meta.confirmToken` present. 2. `data.created` = `true`. `Record: W_A` = `data.widget.id` |

## A1. kinoa_widget_create

| Id | Call | Expected |
|---|---|---|
| `create-rule-01` | `kinoa_widget_create {"game_id": P1, "name": "NAME-src"}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; a violation on `name`; no `meta.confirmToken` |

## A2. kinoa_widget_clone

| Id | Call | Expected |
|---|---|---|
| `clone-rule-01` | 1. `kinoa_widget_clone {"game_id": P1, "source_id": FOREIGN, "name": "NAME-c1"}` 2. the call of step 1 plus `"confirm_token": <token of step 1>` 3. `kinoa_widget_list {"game_id": P1, "search": "NAME-c1"}` | 1. a preview, or already the refusal of step 2 (then step 2 is not sent). Also record: whether `meta.confirmToken` is present. 2. `error.code` = `VALIDATION_FAILED`, a violation on `id`. Also record: the violation's `rule` and `hint`. 3. `data.items` = `[]` |
| `clone-rule-02` | `kinoa_widget_clone {"game_id": P1, "source_id": W_A, "name": "NAME-src"}` | `ok: false`; `error.code` = `VALIDATION_FAILED`; no `meta.confirmToken` |

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only
this domain knows: section 6 has one row for the AC bullet "a widget name is unique in its game"
(`create-rule-01`, `clone-rule-02`) and one for "a clone needs an existing source"
(`clone-rule-01`); nothing is irreversible.
