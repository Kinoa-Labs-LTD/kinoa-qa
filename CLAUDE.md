# kinoa-qa

The markdown under `skills/testplan/` is the implementation for the
agent-driven steps, not documentation about it: a reference file that
misdescribes the validator is a defect, not a typo.

Every `## Section` the test-plan format declares required must be enforced by
`validate_test_plan.py`, or the format doc is lying to the generator that
reads it.

Every test file ends with `if __name__ == "__main__": unittest.main()` and defines
nothing after it — a class appended below that block runs under `discover` but not
on a direct run, so the file reports a false green.

A fenced command in a skill doc is an instruction an agent will run. Before
writing one, check the script has a `__main__` entry point — a module without
one exits 0 and does nothing, so the step silently never happens.
