import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import parse_spec, parse_cases, parse_gaps, parse_acs, parse_conflicts

SPEC = """## capability
### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
#### Scenario: Bad password
- WHEN y
### Requirement: Rate limiting
"""

PLAN = """# QA Test Plan — svc / cap
story: KING-1 · target: svc/cap@main · generated: 2026-09-07 · openspec: cap@abc

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

PLAN_NEW_SHAPE = """# QA Test Plan — svc / cap
story: KING-1 · target: svc/cap@main · generated: 2026-09-07 · openspec: cap@abc

## Acceptance Criteria
- AC-1: Users can sign in

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- source: ac: AC-1
- openspec-ref: sign-in#Sign-in/Happy path
- design-ref: aBcD1234/12:34 — Sign-in / empty state
- preconditions: a user exists
- steps:
  1. enter valid credentials
- expected: the user is signed in

## Conflicts
- ⚠️ CONFLICT: AC-1 · openspec: lockout after 3 tries vs prd: lockout after 5 tries — no case generated for AC-1
- ⚠️ CONFLICT: — · story: banner is blue vs design: banner is red — banner colour not asserted
  → resolved: business wins, AC updated

## Gaps
"""

PLAN_EMPTY_CONFLICTS = """# QA Test Plan — svc / cap

## Conflicts

## Gaps
"""

PLAN_MALFORMED_CONFLICTS = """# QA Test Plan — svc / cap

## Conflicts
- CONFLICT: — \u00b7 story: banner is blue vs design: banner is red — colour not asserted
The story says blue but the design says red.

## Gaps
"""

PLAN_BLANK_BEFORE_RESOLVED = """# QA Test Plan — svc / cap

## Conflicts
- \u26a0\ufe0f CONFLICT: — \u00b7 story: banner is blue vs design: banner is red — colour not asserted

  \u2192 resolved: business wins, AC updated

## Gaps
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

    def test_parse_cases_keeps_hyphenated_keys(self):
        c = parse_cases(PLAN_NEW_SHAPE)[0]
        self.assertEqual(c["tags"]["openspec-ref"], "sign-in#Sign-in/Happy path")
        self.assertEqual(c["tags"]["design-ref"], "aBcD1234/12:34 — Sign-in / empty state")
        self.assertEqual(c["tags"]["source"], "ac: AC-1")

    def test_parse_conflicts_separates_annotated_from_unannotated(self):
        has_section, conflicts, unrecognised = parse_conflicts(PLAN_NEW_SHAPE)
        self.assertTrue(has_section)
        self.assertEqual([], unrecognised)
        self.assertEqual(len(conflicts), 2)
        self.assertFalse(conflicts[0]["annotated"])
        self.assertEqual(
            conflicts[0]["claim"],
            "AC-1 · openspec: lockout after 3 tries vs prd: lockout after 5 tries — no case generated for AC-1")
        self.assertTrue(conflicts[1]["annotated"])
        self.assertNotIn("resolved", conflicts[1]["claim"])

    def test_parse_conflicts_returns_the_annotation_text(self):
        has_section, conflicts, unrecognised = parse_conflicts(PLAN_NEW_SHAPE)
        self.assertIsNone(conflicts[0]["annotation"])
        self.assertEqual("business wins, AC updated", conflicts[1]["annotation"])

    def test_parse_conflicts_returns_the_annotation_after_a_blank_line(self):
        _, conflicts, _ = parse_conflicts(PLAN_BLANK_BEFORE_RESOLVED)
        self.assertEqual("business wins, AC updated", conflicts[0]["annotation"])

    def test_parse_conflicts_missing_section_differs_from_empty_section(self):
        self.assertEqual(parse_conflicts(PLAN), (False, [], []))
        self.assertEqual(parse_conflicts(PLAN_EMPTY_CONFLICTS), (True, [], []))

    def test_parse_conflicts_reports_lines_it_did_not_recognise(self):
        has_section, conflicts, unrecognised = parse_conflicts(PLAN_MALFORMED_CONFLICTS)
        self.assertTrue(has_section)
        self.assertEqual([], conflicts)
        self.assertEqual(2, len(unrecognised))
        self.assertTrue(unrecognised[0].startswith("- CONFLICT:"))

    def test_parse_conflicts_sees_an_annotation_after_a_blank_line(self):
        has_section, conflicts, unrecognised = parse_conflicts(PLAN_BLANK_BEFORE_RESOLVED)
        self.assertEqual(1, len(conflicts))
        self.assertTrue(conflicts[0]["annotated"])
        self.assertEqual([], unrecognised)


if __name__ == "__main__":
    unittest.main()
