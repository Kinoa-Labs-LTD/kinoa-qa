# test_validate_test_plan.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, tempfile
from validate_test_plan import validate

SPEC = """### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
### Requirement: Rate limiting
"""

PLAN_SPEC_MODE = """# QA Test Plan — svc / cap
## Cases
### TC-1 · Happy path
- type: functional
- priority: P1
- source: scenario: Sign-in/Happy path
- preconditions: a user exists
- steps:
  1. enter valid credentials
- expected: signed in
## Gaps
- ⚠️ GAP: Rate limiting — no observable behavior to assert
"""

PLAN_BUSINESS_MODE = """# QA Test Plan — KING-1 (business-only)
## Acceptance Criteria
- AC-1: Users can sign in
- AC-2: Bad passwords rejected
## Cases
### TC-1 · Sign in
- type: functional
- priority: P1
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. sign in
- expected: signed in
### TC-2 · Reject bad password
- type: negative
- priority: P1
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
- expected: rejected
## Gaps
"""

def _write(tmp, text):
    p = os.path.join(tmp, "f.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p

class TestValidate(unittest.TestCase):
    def test_spec_mode_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            spec = os.path.join(tmp, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            r = validate(plan, spec)
            self.assertTrue(r["ok"], r["checks"])

    def test_business_mode_pass_without_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE)
            r = validate(plan, None)
            self.assertTrue(r["ok"], r["checks"])
            names = {c["name"]: c for c in r["checks"]}
            self.assertIn("n/a", names["scenario-coverage"]["detail"])

    def test_unmarked_scenarioless_req_fails_gap_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE.replace("## Gaps\n- ⚠️ GAP: Rate limiting — no observable behavior to assert\n", "## Gaps\n"))
            spec = os.path.join(tmp, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            r = validate(plan, spec)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["gap-honesty"])

    def test_uncovered_ac_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace("### TC-2 · Reject bad password\n- type: negative\n- priority: P1\n- source: ac: AC-2\n- preconditions: a user exists\n- steps:\n  1. sign in with wrong password\n- expected: rejected\n", ""))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["ac-coverage"])

    def test_scenario_source_without_spec_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            r = validate(plan, None)  # scenario: source but no spec
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["source-valid"])

    def test_missing_required_field_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace("- preconditions: a user exists\n", "", 1))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["required-fields"])

if __name__ == "__main__":
    unittest.main()
