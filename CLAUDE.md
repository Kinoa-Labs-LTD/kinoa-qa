# kinoa-qa

The markdown under `skills/` — every skill's SKILL.md and references, and
`skills/shared/` — is the implementation for the agent-driven steps, not
documentation about it: a reference file that misdescribes the validator, or
a SKILL.md that misdescribes what its script does, is a defect, not a typo.

A skill or reference doc describes only what this repo does today — a planned
flow, skill, flag or path is named as planned, never as if it already runs.

A skill names every plugin file the agent reads or runs as `<plugin>/skills/…` — a
repo-root path resolves only inside this repo, never for a plugin user.

A skill never writes inside `<plugin>/` — the install folder is replaced on every update.
Plans, reports and other user data live under `~/.kinoa-qa/`, and an eval points HOME at a
scratch home instead of touching the real one.

Every `## Section` the test-plan format declares required must be enforced by
`validate_test_plan.py`, or the format doc is lying to the generator that
reads it.

Every test file ends with `if __name__ == "__main__": unittest.main()` and defines
nothing after it — a class appended below that block runs under `discover` but not
on a direct run, so the file reports a false green.

A fenced command in a skill doc is an instruction an agent will run. Before
writing one, check the script has a `__main__` entry point — a module without
one exits 0 and does nothing, so the step silently never happens.

When you split a delimited line, a value may legitimately contain the delimiter — rejoin
parts that do not start a new field, and prove it with a test whose value contains one.
Two silent truncations have now shipped from this.

A parser of Jira text is tested on a raw MCP response saved under `scripts/fixtures/`, not
only on the template the skill writes — Jira reads Markdown back in a different shape.
