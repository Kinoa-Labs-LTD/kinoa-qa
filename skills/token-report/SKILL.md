---
name: token-report
description: Show the token usage and estimated cost of the current Claude Code session as one table, grouped by skill run, then by agent (the main session and each subagent), then by model. Use when asked how many tokens or how much this session cost, for a token report, or which agent or skill run was the expensive one. Invoke for `/kinoa-qa:token-report`.
---

# Token report of the current session

`/kinoa-qa:token-report`

## Purpose

Tell the user where the tokens of this session went: which skill run, which agent, which model,
and what that costs at list prices. The report comes from a script; this skill only runs it and
shows what it prints. It writes no file.

## Step

Run the script (`<plugin>` is the plugin's install directory):

```bash
python3 <plugin>/skills/token-report/scripts/token_report.py
```

- **Exit 0:** show its stdout to the user unchanged — the Markdown as printed, no reformatting,
  no rounding, no rows dropped. Add nothing of your own.
- **Exit 1:** show the message it printed on stderr and stop. It prints no report then: either
  `CLAUDE_CODE_SESSION_ID` is not set, or no transcript `<projects>/*/<id>.jsonl` exists for it,
  where `<projects>` is `$CLAUDE_CONFIG_DIR/projects` when `CLAUDE_CONFIG_DIR` is set, else
  `~/.claude/projects`. Do not look for the transcript yourself or build a report by hand.

## What the report means

- **Rows.** One group per skill run, in time order, then agent → model. The agent is
  `main session` or a subagent's type with its description. Each skill run has a subtotal row; the
  last row is the session total. A skill that runs again gets its own group, `<name> (run 2)`.
- **Columns.** Input, output, cache write and cache read tokens, and the estimated cost in USD.
  A request is counted once, even when the transcript repeats it.
- **Skill runs are attributed by order.** A run starts at a slash command that loads a skill, or
  at a `Skill` tool call made before any other tool call since the user's last message, and lasts
  until the next run starts; the transcript records no end. Tokens before the first run are under
  `no skill`. A skill loaded after another tool call in the same turn (say, a reference skill
  looked up mid-task) does not start a new run; its work stays in the run that loaded it. A
  reference skill loaded as the first tool call after a user message (for example after a "go"
  answer in the middle of another skill run) still starts a new run.
- **Subagents.** A subagent counts toward the run that was active when it was started, a nested
  one through its parent, and workflow subagents are included the same way. A forked skill's agent
  (for example `code-review`) counts under that skill's own name.
- **Costs are estimates.** They come from `<plugin>/skills/token-report/prices.json`, list prices
  as of the date in the report header. A model with no price shows `no price` and is left out of
  the cost totals, which a note names; a subtotal with no priced model shows `no price` too. An
  amount under $0.01 shows 4 decimals.
- **Compare by cost, not by token count.** Cache reads dominate the token counts but are the
  cheapest tokens, so the biggest number is rarely the biggest cost.
- **Notes** under the table say when the session has no subagents or no skill runs, and the header
  says when it was resumed from earlier sessions (their tokens are included). The current turn's
  tokens may be missing or partial, since its requests are still being written. A damaged or
  half-written transcript line, or an unreadable subagent meta file, is skipped, not fatal.

## What it does not do

- It reads the current session only — not a past session by id, not a team or monthly total.
- It reads Claude Code's local transcripts, not OpenTelemetry or any billing API, and it does not
  cover other clients (Claude Desktop, claude.ai, Cursor).
- The transcript format is internal to Claude Code and may change; a report that looks wrong after
  a Claude Code update may be the format, not the session.
