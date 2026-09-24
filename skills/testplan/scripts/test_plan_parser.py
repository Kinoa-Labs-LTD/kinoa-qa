import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import (parse_spec, parse_cases, parse_gaps, parse_acs, parse_conflicts,
                         parse_header, parse_ac_source)

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


PLAN_PER_STEP = """# QA Test Plan — svc / cap

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- purpose: Verify that a user with valid credentials can sign in.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. enter valid credentials
     → expected: the submit button becomes enabled
  2. submit
- expected: the user is signed in
"""

PLAN_TWO_EXPECTED = """# QA Test Plan — svc / cap

## Cases

### TC-1 · Happy path sign-in
- purpose: Verify that a user with valid credentials can sign in.
- steps:
  1. submit
     → expected: the dashboard loads
     → expected: a welcome toast appears
- expected: the user is signed in
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

    def test_parse_cases_pairs_a_step_with_its_expected_result(self):
        c = parse_cases(PLAN_PER_STEP)[0]
        self.assertEqual(c["steps"][0],
                         {"action": "enter valid credentials",
                          "expected": "the submit button becomes enabled",
                          "extra_expected": []})

    def test_parse_cases_reports_a_step_with_no_expected_result(self):
        c = parse_cases(PLAN_PER_STEP)[0]
        self.assertEqual(c["steps"][1],
                         {"action": "submit", "expected": None, "extra_expected": []})

    def test_parse_cases_keeps_purpose_as_a_case_field(self):
        c = parse_cases(PLAN_PER_STEP)[0]
        self.assertEqual(c["tags"]["purpose"],
                         "Verify that a user with valid credentials can sign in.")

    def test_parse_cases_records_a_second_expected_result_for_a_step(self):
        c = parse_cases(PLAN_TWO_EXPECTED)[0]
        self.assertEqual(c["steps"][0]["expected"], "the dashboard loads")
        self.assertEqual(c["steps"][0]["extra_expected"], ["a welcome toast appears"])

    def test_parse_cases_still_parses_old_shape_bare_steps(self):
        c = parse_cases(PLAN)[0]
        self.assertEqual(c["steps"],
                         [{"action": "enter valid credentials", "expected": None,
                           "extra_expected": []},
                          {"action": "submit", "expected": None, "extra_expected": []}])
        self.assertNotIn("purpose", c["tags"])


PLAN_MULTILINE_PRECONDITION = """## Cases
### TC-1 · Multi-line precondition
- type: functional
- priority: P1
- purpose: Verify the precondition survives parsing.
- source: ac: AC-1
- preconditions: Published Milestone in-app with 3 milestones and Max Eligibility = 2.
  Test player has an active instance with actual_eligibility = 2.
- steps:
  1. do the thing
     → expected: it happens
- expected: all good
"""


class TestContinuationLines(unittest.TestCase):
    def test_a_field_keeps_its_continuation_lines_newline_joined(self):
        c = parse_cases(PLAN_MULTILINE_PRECONDITION)[0]
        self.assertEqual(
            c["tags"]["preconditions"],
            "Published Milestone in-app with 3 milestones and Max Eligibility = 2.\n"
            "Test player has an active instance with actual_eligibility = 2.",
        )

    def test_continuation_lines_do_not_disturb_steps(self):
        c = parse_cases(PLAN_MULTILINE_PRECONDITION)[0]
        self.assertEqual(c["steps"],
                         [{"action": "do the thing", "expected": "it happens", "extra_expected": []}])


PLAN_WRAPPED_STEPS = """## Cases
### TC-1 · Wrapped step lines
- type: functional
- purpose: Verify a wrapped step survives parsing.
- preconditions:
  First state.
  Second state.
- steps:
  1. Do a very long action that wraps
     onto a second line here.
     → expected: it happens
     and the toast wraps too.
"""


class TestWrappedStepLines(unittest.TestCase):
    def test_a_wrapped_action_keeps_its_continuation_line(self):
        c = parse_cases(PLAN_WRAPPED_STEPS)[0]
        self.assertEqual(c["steps"][0]["action"],
                         "Do a very long action that wraps\nonto a second line here.")

    def test_a_wrapped_expected_result_keeps_its_continuation_line(self):
        c = parse_cases(PLAN_WRAPPED_STEPS)[0]
        self.assertEqual(c["steps"][0]["expected"],
                         "it happens\nand the toast wraps too.")

    def test_a_field_declared_empty_gains_no_leading_newline(self):
        c = parse_cases(PLAN_WRAPPED_STEPS)[0]
        self.assertEqual(c["tags"]["preconditions"],
                         "First state.\nSecond state.")


class TestPurposeHasOneHome(unittest.TestCase):
    def test_purpose_lives_only_in_tags(self):
        for fixture in (PLAN_PER_STEP, PLAN_TWO_EXPECTED, PLAN_MULTILINE_PRECONDITION):
            for c in parse_cases(fixture):
                self.assertNotIn("purpose", c, "purpose must have a single home in tags")

    def test_purpose_keeps_its_continuation_line(self):
        text = PLAN_PER_STEP.replace(
            "- source: ac: AC-1",
            "  It also covers the happy path.\n- source: ac: AC-1", 1)
        c = parse_cases(text)[0]
        self.assertTrue(c["tags"]["purpose"].endswith("It also covers the happy path."))


PLAN_WITH_ALLURE_ID = """# QA Test Plan — svc / cap
story: KING-1 · target: svc/cap@main · generated: 2026-09-07

## Acceptance Criteria
- AC-1: Users can sign in

## Cases

### TC-1 · Happy path sign-in
- allure-id: 12907
- type: functional
- priority: P1
- purpose: Verify a user can sign in.
- source: ac: AC-1
- openspec-ref: sign-in#Sign-in/Happy path
- design-ref: aBcD1234/12:34 — Sign-in / empty state
- preconditions: a user exists
- steps:
  1. enter valid credentials
     → expected: the session opens
- expected: the user is signed in

### TC-2 · Bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. enter a wrong password
     → expected: an error is shown
- expected: rejected

## Conflicts

## Gaps
"""


class TestAllureIdParses(unittest.TestCase):
    """`- allure-id: <id>` is an ordinary hyphenated case field: it must reach
    `case["tags"]["allure-id"]` through the existing field regex, as the first field under
    the case heading, without displacing any other field. Absence leaves the key out."""

    def test_allure_id_parses_as_a_case_field(self):
        cases = parse_cases(PLAN_WITH_ALLURE_ID)
        self.assertEqual("12907", cases[0]["tags"]["allure-id"])

    def test_allure_id_survives_alongside_the_other_hyphenated_fields(self):
        tags = parse_cases(PLAN_WITH_ALLURE_ID)[0]["tags"]
        self.assertEqual("sign-in#Sign-in/Happy path", tags["openspec-ref"])
        self.assertEqual("aBcD1234/12:34 — Sign-in / empty state", tags["design-ref"])
        self.assertEqual("functional", tags["type"])
        self.assertEqual("the user is signed in", tags["expected"])

    def test_leading_allure_id_does_not_disturb_the_case_shape(self):
        cases = parse_cases(PLAN_WITH_ALLURE_ID)
        self.assertEqual(["TC-1", "TC-2"], [c["id"] for c in cases])
        self.assertEqual("Happy path sign-in", cases[0]["title"])
        self.assertEqual(1, len(cases[0]["steps"]))
        self.assertEqual("the session opens", cases[0]["steps"][0]["expected"])

    def test_a_case_without_an_allure_id_has_no_such_tag(self):
        self.assertNotIn("allure-id", parse_cases(PLAN_WITH_ALLURE_ID)[1]["tags"])


PLAN_HEADER = """# QA Test Plan — svc / cap
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-1 · title: A story title · target: svc/cap@main · generated: 2026-09-17
prd: resolved
openspec: none
design: none
scope: e2e

## Acceptance Criteria
- AC-1: Users can sign in

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- purpose: Verify a user with valid credentials is signed in.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. enter valid credentials
     → expected: the session opens
- expected: the user is signed in
"""

PLAN_HEADER_NO_SCOPE = PLAN_HEADER.replace("scope: e2e\n", "")

# A plan whose case body contains a `story:`-looking line. Only the prologue is the header.
PLAN_HEADER_DECOY = """# QA Test Plan — svc / cap

story: KING-1 · title: A story title · target: svc/cap@main · generated: 2026-09-17

## Cases

### TC-1 · Happy path sign-in
- type: functional
- preconditions: a user exists
  story: KING-999
  scope: integration
- steps:
  1. do it
     → expected: done
- expected: ok
"""

# A plan that opens straight on a `##` heading: there is no prologue, so there is no header.
PLAN_NO_HEADER = """## Cases

### TC-1 · Happy path sign-in
- type: functional
- steps:
  1. do it
     → expected: done
- expected: ok
"""


class ParseHeaderTest(unittest.TestCase):
    def test_the_dot_separated_line_parses_into_a_dict(self):
        h = parse_header(PLAN_HEADER)
        self.assertEqual("KING-1", h["story"])
        self.assertEqual("A story title", h["title"])
        self.assertEqual("svc/cap@main", h["target"])
        self.assertEqual("2026-09-17", h["generated"])

    def test_own_line_fields_parse_alongside_them(self):
        h = parse_header(PLAN_HEADER)
        self.assertEqual("none", h["openspec"])
        self.assertEqual("none", h["design"])
        self.assertEqual("resolved", h["prd"])

    def test_scope_on_its_own_line_parses(self):
        self.assertEqual("e2e", parse_header(PLAN_HEADER)["scope"])

    def test_an_absent_scope_is_absent_not_defaulted(self):
        h = parse_header(PLAN_HEADER_NO_SCOPE)
        self.assertNotIn("scope", h)
        self.assertEqual("KING-1", h["story"])

    def test_a_plan_with_no_header_returns_an_empty_dict(self):
        self.assertEqual({}, parse_header(PLAN_NO_HEADER))

    def test_only_the_prologue_before_the_first_heading_is_read(self):
        h = parse_header(PLAN_HEADER_DECOY)
        self.assertEqual("KING-1", h["story"])
        self.assertNotIn("scope", h)

    def test_the_title_line_and_blockquotes_are_not_fields(self):
        h = parse_header(PLAN_HEADER)
        self.assertNotIn("system of record", h)
        self.assertEqual({"story", "title", "target", "generated",
                          "prd", "openspec", "design", "scope"}, set(h))



class HeaderSeparatorTest(unittest.TestCase):
    """A `·` inside a value is part of the value: `title:` holds a Jira summary verbatim,
    and Step E composes `Suite` from it, so a truncation here ships a wrong Suite silently."""

    def test_title_keeps_an_interpunct(self):
        header = parse_header(
            "story: KING-1 · title: Dashboard · Phase 2 · target: a/b@main\n\n## Cases\n")
        self.assertEqual(header["title"], "Dashboard · Phase 2")
        self.assertEqual(header["story"], "KING-1")
        self.assertEqual(header["target"], "a/b@main")

    def test_a_trailing_continuation_is_kept(self):
        header = parse_header("story: KING-1 · title: A · B · C\n\n## Cases\n")
        self.assertEqual(header["title"], "A · B · C")


class ParseAcSourceTest(unittest.TestCase):
    """`source: ac:` holds a comma-separated AC list. A part that does not start a new
    `AC-<n>` belongs to the part before it, so an unknown id is reported whole."""

    def test_a_single_id_parses(self):
        self.assertEqual(["AC-1"], parse_ac_source("ac: AC-1"))

    def test_a_list_parses_in_order(self):
        self.assertEqual(["AC-2", "AC-1", "AC-3"], parse_ac_source("ac: AC-2, AC-1,AC-3"))

    def test_duplicates_and_empty_parts_are_dropped(self):
        self.assertEqual(["AC-1", "AC-2"], parse_ac_source("ac: AC-1, , AC-2, AC-1,"))

    def test_a_non_ac_first_part_is_kept_whole(self):
        self.assertEqual(["see AC-1", "AC-2"], parse_ac_source("ac: see AC-1, AC-2"))

    def test_a_comma_inside_a_value_is_rejoined_not_split(self):
        self.assertEqual(["AC-1, as agreed with PM", "AC-2"],
                         parse_ac_source("ac: AC-1, as agreed with PM, AC-2"))


if __name__ == "__main__":
    unittest.main()
