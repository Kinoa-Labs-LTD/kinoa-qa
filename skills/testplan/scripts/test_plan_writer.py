import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import io
import subprocess
import tempfile
from plan_parser import parse_header
from plan_writer import (merge_allure_ids, insert_allure_id, build_arg_parser,
                         print_report)

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_writer.py")

PREVIOUS = """# QA Test Plan — svc / cap
story: KING-1 · title: T · target: svc/cap@main · generated: 2026-09-07

## Cases

### TC-1 · Dropdown populates with destination projects
- allure-id: 12907
- type: functional
- priority: P1
- purpose: Verify the dropdown populates.
- source: ac: AC-1
- preconditions: user is signed in
- steps:
  1. Open the dropdown
     → expected: projects are listed
- expected: the list is complete

### TC-2 · Bad password is rejected
- allure-id: 12908
- type: negative
- priority: P2
- purpose: Verify a bad password is rejected.
- source: ac: AC-2
- preconditions: user is signed out
- steps:
  1. Submit a bad password
     → expected: an error is shown
- expected: sign-in fails
"""

REGENERATED = """# QA Test Plan — svc / cap
story: KING-1 · title: T · target: svc/cap@main · generated: 2026-09-16

## Cases

### TC-1 · Dropdown populates with destination projects
- type: functional
- priority: P1
- purpose: Verify the dropdown populates.
- source: ac: AC-1
- preconditions: user is signed in
- steps:
  1. Open the dropdown
     → expected: projects are listed
- expected: the list is complete

### TC-2 · A password that fails the policy is refused
- type: negative
- priority: P2
- purpose: Verify a bad password is rejected.
- source: ac: AC-2
- preconditions: user is signed out
- steps:
  1. Submit a bad password
     → expected: an error is shown
- expected: sign-in fails
"""


class TestMergeAllureIds(unittest.TestCase):
    def test_unchanged_title_keeps_its_id(self):
        merged, report = merge_allure_ids(PREVIOUS, REGENERATED)
        self.assertIn("### TC-1 · Dropdown populates with destination projects\n"
                      "- allure-id: 12907\n- type: functional", merged)
        self.assertEqual([c["title"] for c in report["carried"]],
                         ["Dropdown populates with destination projects"])
        self.assertEqual(report["carried"][0]["allure_id"], "12907")

    def test_reworded_case_is_reported_not_guessed(self):
        merged, report = merge_allure_ids(PREVIOUS, REGENERATED)
        self.assertNotIn("12908", merged)
        self.assertEqual([c["title"] for c in report["unmatched"]],
                         ["A password that fails the policy is refused"])
        self.assertEqual([c["allure_id"] for c in report["orphaned"]], ["12908"])

    def test_title_match_ignores_case_and_whitespace_runs(self):
        regenerated = REGENERATED.replace(
            "### TC-1 · Dropdown populates with destination projects",
            "### TC-1 · dropdown  populates with destination PROJECTS")
        merged, report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertIn("### TC-1 · dropdown  populates with destination PROJECTS\n"
                      "- allure-id: 12907\n", merged)
        self.assertEqual(len(report["carried"]), 1)

    def test_duplicate_previous_title_is_ambiguous_and_never_guessed(self):
        previous = PREVIOUS.replace("### TC-2 · Bad password is rejected",
                                    "### TC-2 · Dropdown populates with destination projects")
        merged, report = merge_allure_ids(previous, REGENERATED)
        self.assertNotIn("allure-id", merged)
        self.assertEqual([c["title"] for c in report["unmatched"]],
                         ["Dropdown populates with destination projects",
                          "A password that fails the policy is refused"])

    def test_case_that_already_carries_an_id_is_retained_untouched(self):
        merged, report = merge_allure_ids(PREVIOUS, PREVIOUS)
        self.assertEqual(merged, PREVIOUS)
        self.assertEqual(report["carried"], [])
        self.assertEqual([c["allure_id"] for c in report["retained"]], ["12907", "12908"])

    def test_no_previous_plan_is_the_first_run(self):
        merged, report = merge_allure_ids("", REGENERATED)
        self.assertEqual(merged, REGENERATED)
        self.assertEqual(len(report["unmatched"]), 2)
        self.assertEqual(report["carried"], [])
        self.assertEqual(report["orphaned"], [])

    def test_previous_case_without_an_id_carries_nothing(self):
        previous = PREVIOUS.replace("- allure-id: 12907\n", "")
        merged, report = merge_allure_ids(previous, REGENERATED)
        self.assertNotIn("allure-id", merged)
        self.assertEqual(report["carried"], [])

    def test_everything_but_the_inserted_lines_is_byte_identical(self):
        merged, _ = merge_allure_ids(PREVIOUS, REGENERATED)
        self.assertEqual(merged.replace("- allure-id: 12907\n", ""), REGENERATED)


class TestInsertAllureId(unittest.TestCase):
    def test_id_lands_first_under_the_case_heading(self):
        out = insert_allure_id(REGENERATED, "TC-2", 4242)
        self.assertIn("### TC-2 · A password that fails the policy is refused\n"
                      "- allure-id: 4242\n- type: negative", out)

    def test_the_rest_of_the_file_is_byte_identical(self):
        out = insert_allure_id(REGENERATED, "TC-2", 4242)
        self.assertEqual(out.replace("- allure-id: 4242\n", ""), REGENERATED)

    def test_unknown_case_raises(self):
        with self.assertRaises(ValueError):
            insert_allure_id(REGENERATED, "TC-9", 4242)

    def test_case_that_already_has_an_id_raises(self):
        with self.assertRaises(ValueError):
            insert_allure_id(PREVIOUS, "TC-1", 4242)

    def test_malformed_id_raises(self):
        with self.assertRaises(ValueError):
            insert_allure_id(REGENERATED, "TC-1", "not-a-number")
        with self.assertRaises(ValueError):
            insert_allure_id(REGENERATED, "TC-1", 0)


class TestNewSideAmbiguity(unittest.TestCase):
    def test_duplicate_new_title_carries_nothing_and_both_are_unmatched(self):
        regenerated = REGENERATED.replace(
            "### TC-2 · A password that fails the policy is refused",
            "### TC-2 · Dropdown populates with destination projects")
        merged, report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertNotIn("allure-id", merged)
        self.assertEqual(report["carried"], [])
        self.assertEqual([c["id"] for c in report["unmatched"]], ["TC-1", "TC-2"])
        self.assertEqual([c["allure_id"] for c in report["orphaned"]], ["12907", "12908"])

    def test_duplicate_previous_title_without_an_id_is_still_ambiguous(self):
        previous = PREVIOUS.replace("- allure-id: 12907\n", "").replace(
            "### TC-2 · Bad password is rejected",
            "### TC-2 · Dropdown populates with destination projects")
        merged, report = merge_allure_ids(previous, REGENERATED)
        self.assertNotIn("allure-id", merged)
        self.assertEqual(report["carried"], [])
        self.assertEqual([c["id"] for c in report["unmatched"]], ["TC-1", "TC-2"])


class TestRetainedIdIsCorroborated(unittest.TestCase):
    def test_swapped_ids_are_suspect_not_retained(self):
        regenerated = (REGENERATED
                       .replace("### TC-1 · Dropdown populates with destination projects",
                                "### TC-1 · Dropdown populates with destination projects"
                                "\n- allure-id: 12908")
                       .replace("### TC-2 · A password that fails the policy is refused",
                                "### TC-2 · Bad password is rejected\n- allure-id: 12907"))
        _merged, report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertEqual(report["retained"], [])
        self.assertEqual([c["id"] for c in report["suspect"]], ["TC-1", "TC-2"])
        self.assertEqual([c["allure_id"] for c in report["suspect"]], ["12908", "12907"])

    def test_invented_id_is_suspect(self):
        regenerated = REGENERATED.replace(
            "### TC-1 · Dropdown populates with destination projects",
            "### TC-1 · Dropdown populates with destination projects\n- allure-id: 999999")
        _merged, report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertEqual([c["allure_id"] for c in report["suspect"]], ["999999"])
        self.assertEqual(report["retained"], [])

    def test_a_suspect_id_stays_in_the_plan_text(self):
        regenerated = REGENERATED.replace(
            "### TC-1 · Dropdown populates with destination projects",
            "### TC-1 · Dropdown populates with destination projects\n- allure-id: 999999")
        merged, _report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertIn("- allure-id: 999999", merged)


class TestOrphansByPresence(unittest.TestCase):
    def test_id_retained_under_a_different_title_does_not_suppress_its_orphan(self):
        # 12908 reappears under TC-1's title, so 12907 is carried by nobody and must be
        # reported orphaned even though 12908 itself is still in the plan.
        regenerated = REGENERATED.replace(
            "### TC-1 · Dropdown populates with destination projects",
            "### TC-1 · Something else entirely\n- allure-id: 12908")
        _merged, report = merge_allure_ids(PREVIOUS, regenerated)
        self.assertEqual([c["allure_id"] for c in report["orphaned"]], ["12907"])
        self.assertEqual([c["allure_id"] for c in report["suspect"]], ["12908"])


class TestLineEndings(unittest.TestCase):
    def test_crlf_plan_stays_crlf(self):
        merged, report = merge_allure_ids(PREVIOUS.replace("\n", "\r\n"),
                                          REGENERATED.replace("\n", "\r\n"))
        self.assertEqual(len(report["carried"]), 1)
        self.assertIn("### TC-1 · Dropdown populates with destination projects\r\n"
                      "- allure-id: 12907\r\n- type: functional", merged)
        self.assertEqual(merged.count("\n"), merged.count("\r\n"))

    def test_crlf_insert_allure_id_stays_crlf(self):
        out = insert_allure_id(REGENERATED.replace("\n", "\r\n"), "TC-2", 4242)
        self.assertIn("### TC-2 · A password that fails the policy is refused\r\n"
                      "- allure-id: 4242\r\n- type: negative", out)
        self.assertEqual(out.count("\n"), out.count("\r\n"))


class TestIdShapeMatchesTheValidator(unittest.TestCase):
    def test_leading_zero_id_is_not_a_valid_id(self):
        # validate_test_plan.py FAILs `0012`; writing it back would fail the next Gate 0a.
        with self.assertRaises(ValueError):
            insert_allure_id(REGENERATED, "TC-1", "0012")

    def test_leading_zero_id_in_the_previous_plan_is_never_carried(self):
        previous = PREVIOUS.replace("- allure-id: 12907", "- allure-id: 0012")
        merged, report = merge_allure_ids(previous, REGENERATED)
        self.assertNotIn("0012", merged)
        self.assertEqual(report["carried"], [])


class TestDuplicateCaseHandle(unittest.TestCase):
    def test_duplicate_case_handle_raises(self):
        plan = REGENERATED.replace(
            "### TC-2 · A password that fails the policy is refused",
            "### TC-1 · A password that fails the policy is refused")
        with self.assertRaises(ValueError):
            insert_allure_id(plan, "TC-1", 4242)


class TestCli(unittest.TestCase):
    def test_flags(self):
        args = build_arg_parser().parse_args(["--previous", "p.md", "--new", "n.md", "--json"])
        self.assertEqual((args.previous, args.new, args.json), ("p.md", "n.md", True))

    def test_merged_plan_on_stdout_and_report_on_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            prev, new = os.path.join(d, "p.md"), os.path.join(d, "n.md")
            open(prev, "w").write(PREVIOUS)
            open(new, "w").write(REGENERATED)
            r = subprocess.run([sys.executable, SCRIPT, "--previous", prev, "--new", new],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("- allure-id: 12907", r.stdout)
        self.assertIn("carried   TC-1", r.stderr)
        self.assertIn("orphaned  12908", r.stderr)
        self.assertNotIn("carried", r.stdout)

    def test_json_report_and_missing_previous_is_the_first_run(self):
        with tempfile.TemporaryDirectory() as d:
            new = os.path.join(d, "n.md")
            open(new, "w").write(REGENERATED)
            r = subprocess.run([sys.executable, SCRIPT, "--previous",
                                os.path.join(d, "absent.md"), "--new", new, "--json"],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, REGENERATED)
        report = json.loads(r.stderr)
        self.assertEqual(len(report["unmatched"]), 2)
        self.assertEqual(report["suspect"], [])

    def test_print_report_writes_to_the_stream_it_is_given(self):
        buf = io.StringIO()
        print_report({"carried": [], "retained": [], "unmatched": [],
                      "suspect": [{"id": "TC-1", "title": "T", "allure_id": "9",
                                   "reason": "id not in the previous plan"}],
                      "orphaned": []}, buf)
        self.assertIn("SUSPECT   TC-1", buf.getvalue())


class TestCliErrorPath(unittest.TestCase):
    def test_unreadable_new_plan_exits_1_with_a_message_not_a_traceback(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_writer.py")
        r = subprocess.run([sys.executable, script, "--previous", os.devnull,
                            "--new", os.path.join(os.path.dirname(script), "no-such-plan.md")],
                           capture_output=True, text=True)
        self.assertEqual(1, r.returncode)
        self.assertEqual("", r.stdout)
        self.assertIn("cannot read --new", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


def _with_scope(plan_text, scope):
    """The same plan with `scope: <value>` in its header prologue."""
    return plan_text.replace("## Cases", "scope: %s\n\n## Cases" % scope, 1)


class TestScopeIsCarriedForward(unittest.TestCase):
    """The merge emits the NEW plan's header verbatim, so a regeneration whose subagent
    drops `scope:` would silently demote an e2e plan to Story scope and the next push would
    write Draft over real e2e cases. The previous scope is carried forward, and a scope that
    really changed is reported at the gate rather than accepted in silence."""

    def test_a_new_plan_with_no_scope_inherits_the_previous_one(self):
        merged, report = merge_allure_ids(_with_scope(PREVIOUS, "e2e"), REGENERATED)
        self.assertEqual(parse_header(merged).get("scope"), "e2e")
        self.assertEqual(report["scope"]["effective"], "e2e")
        self.assertTrue(report["scope"]["carried_forward"])
        self.assertFalse(report["scope"]["changed"])

    def test_carrying_the_scope_forward_leaves_the_cases_alone(self):
        merged, report = merge_allure_ids(_with_scope(PREVIOUS, "e2e"), REGENERATED)
        self.assertIn("### TC-1 · Dropdown populates with destination projects\n"
                      "- allure-id: 12907\n- type: functional", merged)
        self.assertEqual([c["allure_id"] for c in report["carried"]], ["12907"])

    def test_a_changed_scope_is_reported_not_silently_accepted(self):
        merged, report = merge_allure_ids(_with_scope(PREVIOUS, "e2e"),
                                          _with_scope(REGENERATED, "story"))
        self.assertTrue(report["scope"]["changed"])
        self.assertEqual(report["scope"]["previous"], "e2e")
        self.assertEqual(report["scope"]["new"], "story")
        # Reported, not reverted: the merge reports and the human gate decides.
        self.assertEqual(report["scope"]["effective"], "story")
        self.assertEqual(parse_header(merged).get("scope"), "story")

    def test_an_unchanged_scope_is_reported_as_unchanged(self):
        merged, report = merge_allure_ids(_with_scope(PREVIOUS, "e2e"),
                                          _with_scope(REGENERATED, "e2e"))
        self.assertFalse(report["scope"]["changed"])
        self.assertFalse(report["scope"]["carried_forward"])
        self.assertEqual(report["scope"]["effective"], "e2e")
        self.assertEqual(parse_header(merged).get("scope"), "e2e")

    def test_no_scope_on_either_side_stays_absent(self):
        merged, report = merge_allure_ids(PREVIOUS, REGENERATED)
        self.assertNotIn("scope", parse_header(merged))
        self.assertEqual(report["scope"], {"previous": None, "new": None, "effective": None,
                                           "carried_forward": False, "changed": False})

    def test_a_first_run_takes_the_new_plans_scope(self):
        merged, report = merge_allure_ids("", _with_scope(REGENERATED, "e2e"))
        self.assertEqual(report["scope"]["effective"], "e2e")
        self.assertFalse(report["scope"]["changed"])
        self.assertEqual(parse_header(merged).get("scope"), "e2e")

    def test_a_new_scope_where_the_previous_plan_had_none_is_not_a_change(self):
        merged, report = merge_allure_ids(PREVIOUS, _with_scope(REGENERATED, "e2e"))
        self.assertFalse(report["scope"]["changed"])
        self.assertEqual(report["scope"]["previous"], None)
        self.assertEqual(report["scope"]["effective"], "e2e")

    def test_the_gate_view_names_a_scope_change(self):
        _, report = merge_allure_ids(_with_scope(PREVIOUS, "e2e"),
                                     _with_scope(REGENERATED, "story"))
        buf = io.StringIO()
        print_report(report, buf)
        self.assertIn("SCOPE", buf.getvalue())
        self.assertIn("e2e", buf.getvalue())
        self.assertIn("story", buf.getvalue())



class EmptyScopeTest(unittest.TestCase):
    """An empty `scope:` is a declared, invalid scope — not an absent one. Carrying the
    previous value forward there would emit a second `scope:` line, and parse_header is
    last-wins, so a plan the validator must FAIL would read as the old scope instead."""

    PREVIOUS = "story: KING-1\nscope: e2e\n\n## Cases\n\n### TC-1 · A\n- allure-id: 5\n"

    def test_an_empty_scope_is_not_overwritten(self):
        new = "story: KING-1\nscope:\n\n## Cases\n\n### TC-1 · A\n"
        merged, report = merge_allure_ids(self.PREVIOUS, new)
        self.assertEqual([l for l in merged.split("\n") if l.startswith("scope")], ["scope:"])
        self.assertFalse(report["scope"]["carried_forward"])
        self.assertEqual(parse_header(merged).get("scope"), "")

    def test_an_absent_scope_is_still_carried_forward(self):
        new = "story: KING-1\n\n## Cases\n\n### TC-1 · A\n"
        merged, report = merge_allure_ids(self.PREVIOUS, new)
        self.assertTrue(report["scope"]["carried_forward"])
        self.assertEqual(parse_header(merged).get("scope"), "e2e")


if __name__ == "__main__":
    unittest.main()
