# kinoa-qa

The markdown under `skills/testplan/` is the implementation for the
agent-driven steps, not documentation about it: a reference file that
misdescribes the validator is a defect, not a typo.

Every `## Section` the test-plan format declares required must be enforced by
`validate_test_plan.py`, or the format doc is lying to the generator that
reads it.
