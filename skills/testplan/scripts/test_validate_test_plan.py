# test_validate_test_plan.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, tempfile
from validate_test_plan import validate, build_arg_parser

SPEC = """### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
### Requirement: Rate limiting
"""

SPEC_B = """### Requirement: Sign-in
#### Scenario: Happy path
- WHEN y
"""

# A second repo owning the SAME capability name (`auth`) with different scenarios.
SPEC_OTHER_REPO = """### Requirement: Sign-out
#### Scenario: Token revoked
- WHEN z
"""

# The pre-KING-22798 shape: a `scenario:` source, no `## Acceptance Criteria`,
# no `## Conflicts` header. Kept as the old-shape fixture (task 2.5).
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

PLAN_OPENSPEC_MODE = """# QA Test Plan — svc / cap
## Acceptance Criteria
- AC-1: Users can sign in
## Cases
### TC-1 · Happy path
- type: functional
- priority: P1
- purpose: Verify a user with valid credentials is signed in.
- source: ac: AC-1
- openspec-ref: Sign-in/Happy path
- preconditions: a user exists
- steps:
  1. enter valid credentials
     → expected: the session opens
- expected: signed in
## Conflicts
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
- purpose: Verify a user can sign in.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. sign in
     → expected: the session opens
- expected: signed in
### TC-2 · Reject bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
     → expected: an error is shown
- expected: rejected
## Conflicts
## Gaps
"""

# A third case for the plans that need three ids in play; spliced in before `## Conflicts`.
CASE_TC3 = """### TC-3 · Sign out
- type: functional
- priority: P2
- purpose: Verify a user can sign out.
- source: ac: AC-1
- preconditions: a user is signed in
- steps:
  1. sign out
     → expected: the session closes
- expected: signed out
"""

CONFLICT_LINE = ("- ⚠️ CONFLICT: AC-2 · story: bad passwords rejected vs "
                 "openspec: bad passwords accepted — no case generated for AC-2\n")

# AC-2 is contradicted, so it carries no case (and is exempt from ac-coverage).
PLAN_CONFLICT = """# QA Test Plan — KING-1
## Acceptance Criteria
- AC-1: Users can sign in
- AC-2: Bad passwords rejected
## Cases
### TC-1 · Sign in
- type: functional
- priority: P1
- purpose: Verify a user can sign in.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. sign in
     → expected: the session opens
- expected: signed in
## Conflicts
""" + CONFLICT_LINE + """## Gaps
"""


def _write(tmp, text, name="f.md"):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def _write_spec(tmp, text, capability=None):
    d = tmp if capability is None else os.path.join(tmp, capability)
    os.makedirs(d, exist_ok=True)
    return _write(d, text, "spec.md")


def _checks(report):
    return {c["name"]: c for c in report["checks"]}


class TestValidate(unittest.TestCase):
    def test_spec_mode_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE)
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertTrue(r["ok"], r["checks"])

    def test_business_mode_pass_without_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE)
            r = validate(plan, None)
            self.assertTrue(r["ok"], r["checks"])
            self.assertIn("n/a", _checks(r)["scenario-coverage"]["detail"])

    def test_unmarked_scenarioless_req_fails_gap_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- ⚠️ GAP: Rate limiting — no observable behavior to assert\n", ""))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertFalse(r["ok"])
            self.assertFalse(_checks(r)["gap-honesty"]["ok"])

    def test_uncovered_ac_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "### TC-2 · Reject bad password\n- type: negative\n- priority: P1\n"
                "- purpose: Verify a wrong password is rejected.\n"
                "- source: ac: AC-2\n- preconditions: a user exists\n- steps:\n"
                "  1. sign in with wrong password\n     → expected: an error is shown\n"
                "- expected: rejected\n", ""))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse(_checks(r)["ac-coverage"]["ok"])

    def test_scenario_source_without_spec_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            r = validate(plan, None)  # scenario: source is no longer a source kind
            self.assertFalse(r["ok"])
            self.assertFalse(_checks(r)["source-valid"]["ok"])

    def test_missing_required_field_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace("- preconditions: a user exists\n", "", 1))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse(_checks(r)["required-fields"]["ok"])


# --- 2.1 business grounding mandatory, spec coverage advisory ---------------
class TestBusinessGroundingMandatory(unittest.TestCase):
    def test_scenario_source_rejected_even_with_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- source: ac: AC-1", "- source: scenario: Sign-in/Happy path"))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertFalse(_checks(r)["source-valid"]["ok"])
            self.assertEqual(1, r["exit_code"])

    def test_missing_ac_section_fails_ac_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "## Acceptance Criteria\n- AC-1: Users can sign in\n", ""))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertFalse(_checks(r)["ac-coverage"]["ok"])
            self.assertIn("missing", _checks(r)["ac-coverage"]["detail"])

    def test_uncovered_scenario_is_advisory_not_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- openspec-ref: Sign-in/Happy path\n", "").replace(
                "- ⚠️ GAP: Rate limiting",
                "- ⚠️ GAP: Sign-in/Happy path — covered by manual exploration\n- ⚠️ GAP: Rate limiting"))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertTrue(_checks(r)["scenario-coverage"]["ok"], _checks(r)["scenario-coverage"])
            self.assertIn("advisory", _checks(r)["scenario-coverage"]["detail"])
            self.assertTrue(r["ok"], r["checks"])


# --- 2.2 conflict-resolution and the HOLD outcome ---------------------------
class TestConflictResolution(unittest.TestCase):
    def test_unannotated_conflict_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_CONFLICT), None)
            self.assertEqual("HOLD", r["outcome"])
            self.assertEqual(2, r["exit_code"])
            self.assertTrue(r["ok"], r["checks"])
            self.assertEqual(1, len(r["unresolved_conflicts"]))
            self.assertIn("openspec", r["unresolved_conflicts"][0]["claim"])

    def test_annotated_conflict_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Once annotated, AC-2 is no longer exempt: the re-run generates its case.
            text = PLAN_CONFLICT.replace(
                "— no case generated for AC-2\n",
                "— no case generated for AC-2\n  → resolved: business wins\n").replace(
                "## Conflicts\n", """### TC-2 · Reject bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
     → expected: an error is shown
- expected: rejected
## Conflicts
""")
            r = validate(_write(tmp, text), None)
            self.assertEqual("PASS", r["outcome"])
            self.assertEqual(0, r["exit_code"])

    def test_annotated_conflict_without_its_case_fails_ac_coverage(self):
        # Annotating alone is not enough: the exemption is gone, so the re-run must also
        # carry AC-2's regenerated case. Annotation only => FAIL on ac-coverage.
        with tempfile.TemporaryDirectory() as tmp:
            text = PLAN_CONFLICT.replace(
                "\u2014 no case generated for AC-2\n",
                "\u2014 no case generated for AC-2\n  \u2192 resolved: business wins\n")
            r = validate(_write(tmp, text), None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["ac-coverage"]["ok"])
            self.assertIn("AC-2", _checks(r)["ac-coverage"]["detail"])

    def test_unrecognised_resolved_annotation_fails(self):
        for annotation in ("TBD", "resolved by QA", "spec wins"):
            with self.subTest(annotation=annotation), tempfile.TemporaryDirectory() as tmp:
                text = PLAN_CONFLICT.replace(
                    "\u2014 no case generated for AC-2\n",
                    f"\u2014 no case generated for AC-2\n  \u2192 resolved: {annotation}\n")
                r = validate(_write(tmp, text), None)
                self.assertEqual("FAIL", r["outcome"])
                self.assertEqual(1, r["exit_code"])
                detail = _checks(r)["conflict-resolution"]["detail"]
                self.assertFalse(_checks(r)["conflict-resolution"]["ok"])
                self.assertIn(annotation, detail)

    def test_documented_resolved_annotations_are_accepted(self):
        case = """### TC-2 \u00b7 Reject bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
     → expected: an error is shown
- expected: rejected
## Conflicts
"""
        for annotation in ("business wins",
                           "spec wins, AC updated",
                           "business wins \u2014 the Story is authoritative here"):
            with self.subTest(annotation=annotation), tempfile.TemporaryDirectory() as tmp:
                text = PLAN_CONFLICT.replace(
                    "\u2014 no case generated for AC-2\n",
                    f"\u2014 no case generated for AC-2\n  \u2192 resolved: {annotation}\n"
                ).replace("## Conflicts\n", case)
                r = validate(_write(tmp, text), None)
                self.assertEqual("PASS", r["outcome"], r["checks"])

    def test_empty_conflicts_section_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_BUSINESS_MODE), None)
            self.assertEqual("PASS", r["outcome"])
            self.assertEqual(0, r["exit_code"])

    def test_missing_conflicts_header_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_BUSINESS_MODE.replace("## Conflicts\n", "")), None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["conflict-resolution"]["ok"])

    def test_contradicted_ac_is_exempt_from_ac_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_CONFLICT), None)
            self.assertTrue(_checks(r)["ac-coverage"]["ok"], _checks(r)["ac-coverage"])

    def test_case_citing_a_contradicted_ac_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = PLAN_CONFLICT.replace("## Conflicts\n", """### TC-2 · Reject bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
     → expected: an error is shown
- expected: rejected
## Conflicts
""")
            r = validate(_write(tmp, text), None)
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["conflict-resolution"]["ok"])
            self.assertIn("TC-2", _checks(r)["conflict-resolution"]["detail"])

    def test_unrecognised_conflict_line_fails(self):
        for broken in ("- CONFLICT: AC-2 \u00b7 story: a vs prd: b \u2014 no case\n",
                       "The story says one thing and the PRD says another.\n"):
            with self.subTest(line=broken), tempfile.TemporaryDirectory() as tmp:
                text = PLAN_CONFLICT.replace(CONFLICT_LINE, broken)
                r = validate(_write(tmp, text), None)
                self.assertEqual(1, r["exit_code"])
                self.assertFalse(_checks(r)["conflict-resolution"]["ok"])
                self.assertIn("unrecognised", _checks(r)["conflict-resolution"]["detail"])

    def test_resolved_annotation_after_a_blank_line_is_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = PLAN_CONFLICT.replace(
                "\u2014 no case generated for AC-2\n",
                "\u2014 no case generated for AC-2\n\n  \u2192 resolved: business wins\n").replace(
                "## Conflicts\n", """### TC-2 \u00b7 Reject bad password
- type: negative
- priority: P1
- purpose: Verify a wrong password is rejected.
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
     → expected: an error is shown
- expected: rejected
## Conflicts
""")
            r = validate(_write(tmp, text), None)
            self.assertEqual("PASS", r["outcome"])
            self.assertEqual([], r["unresolved_conflicts"])

    def test_every_side_of_a_three_sided_conflict_is_validated(self):
        three = ("- \u26a0\ufe0f CONFLICT: AC-2 \u00b7 story: 7 days vs prd: 24 hours vs "
                 "{third}: 30 days \u2014 no case generated for AC-2\n")
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_CONFLICT.replace(
                CONFLICT_LINE, three.format(third="confluence"))), None)
            self.assertEqual(1, r["exit_code"])
            self.assertIn("confluence", _checks(r)["conflict-resolution"]["detail"])
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_CONFLICT.replace(
                CONFLICT_LINE, three.format(third="design"))), None)
            self.assertEqual("HOLD", r["outcome"])
            self.assertTrue(_checks(r)["conflict-resolution"]["ok"])

    def test_unknown_conflict_source_side_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = PLAN_CONFLICT.replace("openspec: bad passwords accepted",
                                         "hallway: bad passwords accepted")
            r = validate(_write(tmp, text), None)
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["conflict-resolution"]["ok"])


# --- 2.3 openspec-ref targets across one or more specs ----------------------
class TestOpenspecRefValid(unittest.TestCase):
    def test_unknown_openspec_ref_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- openspec-ref: Sign-in/Happy path", "- openspec-ref: Sign-in/Nope"))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertFalse(_checks(r)["openspec-ref-valid"]["ok"])

    def test_openspec_ref_without_any_spec_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_OPENSPEC_MODE), None)
            self.assertFalse(_checks(r)["openspec-ref-valid"]["ok"])

    def test_unqualified_ref_with_two_specs_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE)
            a = _write_spec(tmp, SPEC, "cap-a")
            b = _write_spec(tmp, SPEC_B, "cap-b")
            r = validate(plan, [a, b])
            self.assertFalse(_checks(r)["openspec-ref-valid"]["ok"])

    def test_same_capability_in_two_repos_does_not_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _write_spec(os.path.join(tmp, "repo-a"), SPEC, "auth")
            b = _write_spec(os.path.join(tmp, "repo-b"), SPEC_OTHER_REPO, "auth")
            for ref in ("auth#Sign-in/Happy path", "auth#Sign-out/Token revoked"):
                with self.subTest(ref=ref):
                    plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                        "- openspec-ref: Sign-in/Happy path", "- openspec-ref: " + ref))
                    r = validate(plan, [a, b])
                    self.assertTrue(_checks(r)["openspec-ref-valid"]["ok"],
                                    _checks(r)["openspec-ref-valid"])

    def test_unqualified_ref_with_two_same_named_capabilities_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _write_spec(os.path.join(tmp, "repo-a"), SPEC, "auth")
            b = _write_spec(os.path.join(tmp, "repo-b"), SPEC_OTHER_REPO, "auth")
            r = validate(_write(tmp, PLAN_OPENSPEC_MODE), [a, b])
            self.assertFalse(_checks(r)["openspec-ref-valid"]["ok"])
            self.assertIn("ambiguous", _checks(r)["openspec-ref-valid"]["detail"])

    def test_qualified_ref_resolves_with_two_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- openspec-ref: Sign-in/Happy path",
                "- openspec-ref: cap-b#Sign-in/Happy path"))
            a = _write_spec(tmp, SPEC, "cap-a")
            b = _write_spec(tmp, SPEC_B, "cap-b")
            r = validate(plan, [a, b])
            self.assertTrue(_checks(r)["openspec-ref-valid"]["ok"],
                            _checks(r)["openspec-ref-valid"])


class TestCliFlags(unittest.TestCase):
    def test_openspec_flag_replaces_the_old_spec_spelling(self):
        ap = build_arg_parser()
        flags = {o for a in ap._actions for o in a.option_strings}
        self.assertIn("--openspec", flags)
        self.assertNotIn("--spec", flags)
        self.assertEqual(ap.parse_args(["p.md", "--openspec", "s.md"]).openspec, ["s.md"])

    def test_openspec_flag_is_repeatable(self):
        ap = build_arg_parser()
        args = ap.parse_args(["p.md", "--openspec", "a.md", "--openspec", "b.md"])
        self.assertEqual(["a.md", "b.md"], args.openspec)


# --- 2.4 gap-honesty for scenario-level gaps --------------------------------
class TestScenarioGapHonesty(unittest.TestCase):
    def test_uncovered_scenario_unmarked_fails_gap_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace("- openspec-ref: Sign-in/Happy path\n", ""))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertFalse(_checks(r)["gap-honesty"]["ok"])
            self.assertIn("Sign-in/Happy path", _checks(r)["gap-honesty"]["detail"])

    def test_naming_the_uncovered_scenario_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_OPENSPEC_MODE.replace(
                "- openspec-ref: Sign-in/Happy path\n", "").replace(
                "- ⚠️ GAP: Rate limiting",
                "- ⚠️ GAP: Sign-in/Happy path — covered by manual exploration\n- ⚠️ GAP: Rate limiting"))
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertTrue(_checks(r)["gap-honesty"]["ok"], _checks(r)["gap-honesty"])


    def test_scenario_named_in_an_unresolved_conflict_is_exempt(self):
        # An uncovered scenario is "a Gap OR a Conflict": naming it in an unresolved
        # conflict line is enough, exactly as its AC is exempt from ac-coverage.
        conflict = ("- \u26a0\ufe0f CONFLICT: AC-1 \u00b7 story: bad passwords rejected vs "
                    "openspec: Sign-in/Happy path signs anyone in "
                    "\u2014 no case generated for AC-1\n")
        base = PLAN_OPENSPEC_MODE.replace("- openspec-ref: Sign-in/Happy path\n", "").replace(
            "- source: ac: AC-1", "- source: QA-added: smoke")
        with tempfile.TemporaryDirectory() as tmp:
            spec = _write_spec(tmp, SPEC, "cap")
            unresolved = validate(_write(tmp, base.replace("## Conflicts\n",
                                                           "## Conflicts\n" + conflict)), spec)
            self.assertTrue(_checks(unresolved)["gap-honesty"]["ok"],
                            _checks(unresolved)["gap-honesty"])
            self.assertEqual("HOLD", unresolved["outcome"])
            # Annotated, the exemption is gone and the Gap line is owed again.
            annotated = validate(_write(tmp, base.replace(
                "## Conflicts\n",
                "## Conflicts\n" + conflict.replace(
                    "for AC-1\n", "for AC-1\n  \u2192 resolved: business wins\n")), "b.md"), spec)
            self.assertFalse(_checks(annotated)["gap-honesty"]["ok"])
            self.assertIn("Sign-in/Happy path", _checks(annotated)["gap-honesty"]["detail"])


# --- 2.5 an old-shape plan is rejected --------------------------------------
class TestOldShapePlanRejected(unittest.TestCase):
    def test_old_shape_plan_fails_with_all_three_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            spec = _write_spec(tmp, SPEC, "cap")
            r = validate(plan, spec)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            c = _checks(r)
            self.assertFalse(c["source-valid"]["ok"])          # source: scenario:
            self.assertFalse(c["ac-coverage"]["ok"])           # no ## Acceptance Criteria
            self.assertFalse(c["conflict-resolution"]["ok"])   # no ## Conflicts header


# --- G2 2.1 purpose and one expected result per step ------------------------
class TestPurposeAndPerStepExpected(unittest.TestCase):
    def test_case_without_purpose_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "- purpose: Verify a user can sign in.\n", "", 1))
            r = validate(plan, None)
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["required-fields"]["ok"])
            detail = _checks(r)["required-fields"]["detail"]
            self.assertIn("TC-1", detail)
            self.assertIn("purpose", detail)

    def test_step_without_expected_result_fails_naming_the_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "  1. sign in with wrong password\n     \u2192 expected: an error is shown\n",
                "  1. sign in with wrong password\n"
                "     \u2192 expected: an error is shown\n"
                "  2. retry with the same password\n", 1))
            r = validate(plan, None)
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["required-fields"]["ok"])
            detail = _checks(r)["required-fields"]["detail"]
            self.assertIn("TC-2", detail)
            self.assertIn("step 2", detail)
            self.assertIn("no expected result", detail)
            self.assertNotIn("step 1", detail)

    def test_step_with_two_expected_results_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "  1. sign in\n     \u2192 expected: the session opens\n",
                "  1. sign in\n     \u2192 expected: the session opens\n"
                "     \u2192 expected: the dashboard loads\n", 1))
            r = validate(plan, None)
            self.assertEqual(1, r["exit_code"])
            self.assertFalse(_checks(r)["required-fields"]["ok"])
            detail = _checks(r)["required-fields"]["detail"]
            self.assertIn("TC-1", detail)
            self.assertIn("step 1", detail)
            self.assertIn("2 expected results", detail)

    def test_well_formed_multi_step_case_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "  1. sign in\n     \u2192 expected: the session opens\n",
                "  1. sign in\n     \u2192 expected: the session opens\n"
                "  2. open the dashboard\n     \u2192 expected: the dashboard loads\n", 1))
            r = validate(plan, None)
            self.assertTrue(_checks(r)["required-fields"]["ok"],
                            _checks(r)["required-fields"])
            self.assertEqual(0, r["exit_code"])


# --- G2 2.2 an old-shape plan is rejected on the new format break -----------
class TestOldShapeStepsRejected(unittest.TestCase):
    def test_bare_numbered_steps_fail_naming_purpose_and_the_step(self):
        # Distinct from TestOldShapePlanRejected, which pins the KING-22798 break
        # (source:/AC section/Conflicts header). This pins the KING-22795 break.
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            r = validate(plan, None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            check = _checks(r)["required-fields"]
            self.assertFalse(check["ok"])
            self.assertIn("TC-1", check["detail"])
            self.assertIn("purpose", check["detail"])
            self.assertIn("step 1 has no expected result", check["detail"])


# --- 2.6 design-ref is syntactically validated ------------------------------
class TestDesignRef(unittest.TestCase):
    def _plan_with(self, ref, source="- source: ac: AC-1"):
        return PLAN_BUSINESS_MODE.replace(
            "- source: ac: AC-1", source + "\n- design-ref: " + ref, 1)

    def test_well_formed_design_ref_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, self._plan_with("abc123/1:24 — Empty state")), None)
            self.assertTrue(_checks(r)["design-ref-valid"]["ok"], _checks(r)["design-ref-valid"])
            self.assertEqual(0, r["exit_code"])

    def test_design_ref_without_node_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, self._plan_with("abc123 — Empty state")), None)
            self.assertFalse(_checks(r)["design-ref-valid"]["ok"])

    def test_design_ref_without_frame_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, self._plan_with("abc123/1:24")), None)
            self.assertFalse(_checks(r)["design-ref-valid"]["ok"])

    def test_design_ref_with_non_ac_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = self._plan_with("abc123/1:24 — Empty state",
                                   source="- source: QA-added: smoke coverage")
            # AC-1 now has no case, so only the design-ref pairing check is asserted.
            r = validate(_write(tmp, text), None)
            self.assertFalse(_checks(r)["design-ref-valid"]["ok"])
            self.assertIn("TC-1", _checks(r)["design-ref-valid"]["detail"])


# --- a blank expected result is as missing as no expected result at all -----
class TestBlankExpectedRejected(unittest.TestCase):
    """A bare `→ expected:` yields an empty string, which the payload builder drops.
    The validator must refuse it so no step reaches TestOps without an expected body."""

    def test_bare_expected_marker_fails_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "→ expected: the session opens", "→ expected:", 1))
            r = validate(plan, None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            check = _checks(r)["required-fields"]
            self.assertFalse(check["ok"])
            self.assertIn("step 1 has no expected result", check["detail"])

    def test_whitespace_only_expected_fails_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "→ expected: the session opens", "→ expected:   ", 1))
            r = validate(plan, None)
            self.assertEqual(1, r["exit_code"])
            self.assertIn("step 1 has no expected result",
                          _checks(r)["required-fields"]["detail"])


class TestAllureIdValid(unittest.TestCase):
    """`allure-id:` is the assigned TestOps identity, written by Step E. The validator checks
    its SHAPE — a positive integer — and its UNIQUENESS across the plan, so neither a
    malformed id nor an id carried by two cases can reach Step E and address the wrong case.
    Absence is the ordinary first-run state and must stay valid."""

    def test_absent_allure_id_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_BUSINESS_MODE), None)
            self.assertEqual("PASS", r["outcome"])
            check = _checks(r)["allure-id-valid"]
            self.assertTrue(check["ok"])
            self.assertIn("no case carries an allure-id", check["detail"])

    def test_valid_allure_id_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "### TC-1 · Sign in\n", "### TC-1 · Sign in\n- allure-id: 12907\n", 1))
            r = validate(plan, None)
            self.assertEqual("PASS", r["outcome"])
            self.assertTrue(_checks(r)["allure-id-valid"]["ok"])

    def test_non_numeric_allure_id_fails_naming_the_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                "### TC-2 · Reject bad password\n",
                "### TC-2 · Reject bad password\n- allure-id: TC-12907\n", 1))
            r = validate(plan, None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            check = _checks(r)["allure-id-valid"]
            self.assertFalse(check["ok"])
            self.assertIn("TC-2", check["detail"])
            self.assertIn("TC-12907", check["detail"])

    def test_non_positive_and_malformed_ids_fail(self):
        for bad in ("0", "-3", "12.5", "12 907", "", "12907x"):
            with self.subTest(allure_id=bad), tempfile.TemporaryDirectory() as tmp:
                plan = _write(tmp, PLAN_BUSINESS_MODE.replace(
                    "### TC-1 · Sign in\n",
                    "### TC-1 · Sign in\n- allure-id: %s\n" % bad, 1))
                r = validate(plan, None)
                self.assertEqual(1, r["exit_code"])
                self.assertFalse(_checks(r)["allure-id-valid"]["ok"])

    def test_two_cases_sharing_an_id_fail_naming_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE
                          .replace("### TC-1 · Sign in\n",
                                   "### TC-1 · Sign in\n- allure-id: 12907\n", 1)
                          .replace("### TC-2 · Reject bad password\n",
                                   "### TC-2 · Reject bad password\n- allure-id: 12907\n", 1))
            r = validate(plan, None)
            self.assertEqual("FAIL", r["outcome"])
            self.assertEqual(1, r["exit_code"])
            check = _checks(r)["allure-id-valid"]
            self.assertFalse(check["ok"])
            self.assertIn("TC-1", check["detail"])
            self.assertIn("TC-2", check["detail"])
            self.assertIn("12907", check["detail"])

    def test_three_cases_with_one_collision_fail_naming_the_colliding_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE
                          .replace("## Conflicts\n", CASE_TC3 + "## Conflicts\n", 1)
                          .replace("### TC-1 · Sign in\n",
                                   "### TC-1 · Sign in\n- allure-id: 100\n", 1)
                          .replace("### TC-2 · Reject bad password\n",
                                   "### TC-2 · Reject bad password\n- allure-id: 200\n", 1)
                          .replace("### TC-3 · Sign out\n",
                                   "### TC-3 · Sign out\n- allure-id: 200\n", 1))
            r = validate(plan, None)
            self.assertEqual(1, r["exit_code"])
            check = _checks(r)["allure-id-valid"]
            self.assertFalse(check["ok"])
            self.assertIn("TC-2", check["detail"])
            self.assertIn("TC-3", check["detail"])
            self.assertIn("200", check["detail"])

    def test_distinct_ids_on_every_case_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE
                          .replace("### TC-1 · Sign in\n",
                                   "### TC-1 · Sign in\n- allure-id: 100\n", 1)
                          .replace("### TC-2 · Reject bad password\n",
                                   "### TC-2 · Reject bad password\n- allure-id: 200\n", 1))
            r = validate(plan, None)
            self.assertEqual("PASS", r["outcome"])
            self.assertTrue(_checks(r)["allure-id-valid"]["ok"])

    def test_one_id_among_cases_without_ids_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE
                          .replace("## Conflicts\n", CASE_TC3 + "## Conflicts\n", 1)
                          .replace("### TC-2 · Reject bad password\n",
                                   "### TC-2 · Reject bad password\n- allure-id: 12907\n", 1))
            r = validate(plan, None)
            self.assertEqual("PASS", r["outcome"])
            check = _checks(r)["allure-id-valid"]
            self.assertTrue(check["ok"])
            self.assertIn("1/3", check["detail"])

    def test_allure_id_is_not_a_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_BUSINESS_MODE), None)
            self.assertTrue(_checks(r)["required-fields"]["ok"])
            self.assertNotIn("allure-id", _checks(r)["required-fields"]["detail"])


# A header prologue in front of PLAN_BUSINESS_MODE, so the scope value can be varied.
def _with_scope(scope):
    """PLAN_BUSINESS_MODE preceded by a real header; `scope` None means the field is absent."""
    header = ("story: KING-1 · title: A story title · target: svc/cap@main · "
              "generated: 2026-09-17\n")
    if scope is not None:
        header += f"scope: {scope}\n"
    return PLAN_BUSINESS_MODE.replace("## Acceptance Criteria",
                                      header + "\n## Acceptance Criteria", 1)


class ScopeValidTest(unittest.TestCase):
    def _check(self, scope):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, _with_scope(scope)), None)
            return r, _checks(r)["scope-valid"]

    def test_e2e_passes(self):
        r, check = self._check("e2e")
        self.assertTrue(check["ok"], check["detail"])
        self.assertEqual("PASS", r["outcome"])

    def test_story_passes(self):
        r, check = self._check("story")
        self.assertTrue(check["ok"], check["detail"])
        self.assertEqual("PASS", r["outcome"])

    def test_an_absent_scope_passes(self):
        r, check = self._check(None)
        self.assertTrue(check["ok"], check["detail"])
        self.assertEqual("PASS", r["outcome"])

    def test_a_plan_with_no_header_at_all_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, PLAN_BUSINESS_MODE), None)
            self.assertTrue(_checks(r)["scope-valid"]["ok"])

    def test_uppercase_e2e_fails_naming_the_value_and_the_allowed_set(self):
        r, check = self._check("E2E")
        self.assertFalse(check["ok"])
        self.assertIn("E2E", check["detail"])
        self.assertIn("e2e", check["detail"])
        self.assertIn("story", check["detail"])
        self.assertEqual("FAIL", r["outcome"])
        self.assertEqual(1, r["exit_code"])

    def test_an_unrecognised_value_fails_naming_it(self):
        r, check = self._check("integration")
        self.assertFalse(check["ok"])
        self.assertIn("integration", check["detail"])
        self.assertIn("e2e", check["detail"])
        self.assertIn("story", check["detail"])
        self.assertEqual("FAIL", r["outcome"])

    def test_an_empty_value_fails(self):
        r, check = self._check("")
        self.assertFalse(check["ok"])
        self.assertIn("e2e", check["detail"])
        self.assertIn("story", check["detail"])
        self.assertEqual("FAIL", r["outcome"])

    def test_scope_is_not_a_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, _with_scope(None)), None)
            self.assertTrue(_checks(r)["required-fields"]["ok"])
            self.assertNotIn("scope", _checks(r)["required-fields"]["detail"])


# --- 2.1 several expected results per step are an e2e-only relaxation -------
TWO_EXPECTED_STEP = ("  1. sign in\n     \u2192 expected: the session opens\n"
                     "     \u2192 expected: the dashboard loads\n")
ONE_EXPECTED_STEP = "  1. sign in\n     \u2192 expected: the session opens\n"


def _with_scope_and_steps(scope, steps):
    """`_with_scope` with TC-1's single step replaced by `steps`."""
    return _with_scope(scope).replace(ONE_EXPECTED_STEP, steps, 1)


class MultiExpectedPerStepTest(unittest.TestCase):
    def _validate(self, scope, steps=TWO_EXPECTED_STEP):
        with tempfile.TemporaryDirectory() as tmp:
            r = validate(_write(tmp, _with_scope_and_steps(scope, steps)), None)
            return r, _checks(r)["required-fields"]

    def test_two_expected_results_pass_under_e2e(self):
        r, check = self._validate("e2e")
        self.assertTrue(check["ok"], check["detail"])
        self.assertEqual("PASS", r["outcome"])
        self.assertEqual(0, r["exit_code"])

    def test_two_expected_results_fail_under_story_naming_the_step(self):
        r, check = self._validate("story")
        self.assertFalse(check["ok"])
        self.assertEqual("TC-1: step 1 has 2 expected results (exactly one is allowed)",
                         check["detail"])
        self.assertEqual(1, r["exit_code"])

    def test_two_expected_results_fail_with_the_scope_absent(self):
        r, check = self._validate(None)
        self.assertFalse(check["ok"])
        self.assertEqual("TC-1: step 1 has 2 expected results (exactly one is allowed)",
                         check["detail"])
        self.assertEqual(1, r["exit_code"])

    def test_three_expected_results_pass_under_e2e(self):
        r, check = self._validate(
            "e2e", TWO_EXPECTED_STEP + "     \u2192 expected: the badge clears\n")
        self.assertTrue(check["ok"], check["detail"])
        self.assertEqual(0, r["exit_code"])

    def test_a_step_with_no_expected_result_fails_under_e2e(self):
        r, check = self._validate("e2e", ONE_EXPECTED_STEP + "  2. open the dashboard\n")
        self.assertFalse(check["ok"])
        self.assertIn("TC-1: step 2 has no expected result", check["detail"])
        self.assertEqual(1, r["exit_code"])

    def test_a_step_with_no_expected_result_fails_under_story(self):
        r, check = self._validate("story", ONE_EXPECTED_STEP + "  2. open the dashboard\n")
        self.assertFalse(check["ok"])
        self.assertIn("TC-1: step 2 has no expected result", check["detail"])
        self.assertEqual(1, r["exit_code"])

    def test_a_blank_expected_result_still_fails_under_e2e(self):
        r, check = self._validate("e2e", "  1. sign in\n     \u2192 expected:\n")
        self.assertFalse(check["ok"])
        self.assertIn("step 1 has no expected result", check["detail"])


# --- 2.2 the Story-scoped rejection is byte-identical to before -------------
class StoryScopeMultiExpectedUnchangedTest(unittest.TestCase):
    """Pins the rule KING-22795 shipped: under Story scope the check name, the message and
    the exit code of a multi-expected step must survive the e2e relaxation unchanged."""

    EXPECTED_DETAIL = "TC-1: step 1 has 2 expected results (exactly one is allowed)"

    def _report(self, scope):
        with tempfile.TemporaryDirectory() as tmp:
            return validate(_write(tmp, _with_scope_and_steps(scope, TWO_EXPECTED_STEP)), None)

    def test_message_and_check_name_unchanged_with_the_scope_absent(self):
        r = self._report(None)
        check = _checks(r)["required-fields"]
        self.assertFalse(check["ok"])
        self.assertEqual(self.EXPECTED_DETAIL, check["detail"])
        self.assertEqual("FAIL", r["outcome"])
        self.assertEqual(1, r["exit_code"])

    def test_message_and_check_name_unchanged_under_story(self):
        r = self._report("story")
        check = _checks(r)["required-fields"]
        self.assertFalse(check["ok"])
        self.assertEqual(self.EXPECTED_DETAIL, check["detail"])
        self.assertEqual("FAIL", r["outcome"])
        self.assertEqual(1, r["exit_code"])

    def test_message_unchanged_on_a_headerless_plan(self):
        # The pre-scope shape: no header at all, exactly as KING-22795 left it.
        with tempfile.TemporaryDirectory() as tmp:
            text = PLAN_BUSINESS_MODE.replace(ONE_EXPECTED_STEP, TWO_EXPECTED_STEP, 1)
            r = validate(_write(tmp, text), None)
            check = _checks(r)["required-fields"]
            self.assertEqual("required-fields", check["name"])
            self.assertEqual(self.EXPECTED_DETAIL, check["detail"])
            self.assertEqual(1, r["exit_code"])


PLAN_IMAGE_REF = """# QA Test Plan — KING-1 · svc / cap
story: KING-1 · title: T · generated: 2026-09-21
images: 1 read

## Acceptance Criteria

- AC-1: The eligibility checkbox is disabled while a progression is active.

## Cases

### TC-1 · Eligibility checkbox is disabled during a progression
- type: functional
- priority: P1
- purpose: Verify that the checkbox is disabled while a progression is active.
- source: ac: AC-1
- image-ref: 10231 — milestone-eligibility.png
- preconditions: An operator is on the in-app configuration screen.
- steps:
  1. Open the in-app configuration screen.
     → expected: The eligibility checkbox is visible and disabled.
- expected: The checkbox cannot be toggled during a progression.

## Conflicts

## Gaps
"""


class ImageRefValid(unittest.TestCase):
    def _run(self, plan_text):
        with tempfile.TemporaryDirectory() as tmp:
            return validate(_write(tmp, plan_text), None)

    def test_well_formed_image_ref_passes(self):
        r = self._run(PLAN_IMAGE_REF)
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])

    def test_filename_containing_an_em_dash_is_not_truncated(self):
        r = self._run(PLAN_IMAGE_REF.replace("milestone-eligibility.png",
                                             "milestone — eligibility.png"))
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])

    def test_malformed_image_ref_fails_naming_the_case(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "- image-ref: 10231 — milestone-eligibility.png",
            "- image-ref: milestone-eligibility.png"))
        self.assertEqual(1, r["exit_code"])
        self.assertIn("TC-1", _checks(r)["image-ref-valid"]["detail"])

    def test_non_numeric_attachment_id_fails(self):
        r = self._run(PLAN_IMAGE_REF.replace("10231 —", "abc —"))
        self.assertEqual(1, r["exit_code"])
        self.assertFalse(_checks(r)["image-ref-valid"]["ok"])

    def test_image_ref_requires_an_ac_source(self):
        r = self._run(PLAN_IMAGE_REF
                      .replace("- source: ac: AC-1",
                               "- source: QA-added: operator sanity check")
                      .replace("- AC-1: The eligibility checkbox is disabled while a "
                               "progression is active.\n", ""))
        self.assertEqual(1, r["exit_code"])
        self.assertIn("ac:", _checks(r)["image-ref-valid"]["detail"])

    def test_non_ascii_digit_attachment_id_fails(self):
        r = self._run(PLAN_IMAGE_REF.replace("10231 —", "٣ —"))
        self.assertEqual(1, r["exit_code"])
        self.assertFalse(_checks(r)["image-ref-valid"]["ok"])

    def test_absent_image_ref_is_valid(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "- image-ref: 10231 — milestone-eligibility.png\n", ""))
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])


class ImageConflictSource(unittest.TestCase):
    def _run(self, plan_text):
        with tempfile.TemporaryDirectory() as tmp:
            return validate(_write(tmp, plan_text), None)

    def test_image_is_an_accepted_conflict_source(self):
        plan = PLAN_IMAGE_REF.replace(
            "- AC-1: The eligibility checkbox is disabled while a progression is active.",
            "- AC-1: The eligibility checkbox is disabled while a progression is active.\n"
            "- AC-2: The eligibility checkbox is required.").replace(
            "## Conflicts\n",
            "## Conflicts\n\n- ⚠️ CONFLICT: AC-2 · story: the checkbox is optional vs "
            "image: the frame shows it required — no case was generated for AC-2\n")
        r = self._run(plan)
        # An unannotated conflict is HOLD, not FAIL: the source vocabulary accepted `image`.
        self.assertEqual(2, r["exit_code"], r["checks"])

    def test_unknown_conflict_source_is_still_rejected(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "## Conflicts\n",
            "## Conflicts\n\n- ⚠️ CONFLICT: AC-1 · story: a vs screenshot: b — none\n"))
        self.assertEqual(1, r["exit_code"])


if __name__ == "__main__":
    unittest.main()
