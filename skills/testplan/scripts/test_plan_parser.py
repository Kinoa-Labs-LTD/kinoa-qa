import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import parse_spec, parse_cases, parse_gaps, parse_acs

SPEC = """## capability
### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
#### Scenario: Bad password
- WHEN y
### Requirement: Rate limiting
"""

PLAN = """# QA Test Plan — svc / cap
story: KING-1 · target: svc/cap@main · generated: 2026-09-07 · spec-sha: abc

## Acceptance Criteria
- AC-1: Users can sign in
- AC-2: Bad passwords are rejected

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- source: scenario: Sign-in/Happy path
- preconditions: a user exists
- steps:
  1. enter valid credentials
  2. submit
- expected: the user is signed in

## Gaps
- ⚠️ GAP: Rate limiting — spec states no observable behavior to assert
"""

class TestParsers(unittest.TestCase):
    def test_parse_spec_scenarios_and_scenarioless_reqs(self):
        scenarios, reqs_without = parse_spec(SPEC)
        self.assertEqual(scenarios, {"Sign-in/Happy path", "Sign-in/Bad password"})
        self.assertEqual(reqs_without, {"Rate limiting"})

    def test_parse_cases_fields_and_steps(self):
        cases = parse_cases(PLAN)
        self.assertEqual(len(cases), 1)
        c = cases[0]
        self.assertEqual(c["id"], "TC-1")
        self.assertEqual(c["title"], "Happy path sign-in")
        self.assertEqual(c["tags"]["type"], "functional")
        self.assertEqual(c["tags"]["source"], "scenario: Sign-in/Happy path")
        self.assertEqual(c["tags"]["preconditions"], "a user exists")
        self.assertEqual(c["tags"]["expected"], "the user is signed in")
        self.assertEqual(len(c["steps"]), 2)

    def test_parse_gaps(self):
        self.assertEqual(parse_gaps(PLAN), {"Rate limiting"})

    def test_parse_acs(self):
        self.assertEqual(parse_acs(PLAN), {"AC-1": "Users can sign in", "AC-2": "Bad passwords are rejected"})

if __name__ == "__main__":
    unittest.main()
