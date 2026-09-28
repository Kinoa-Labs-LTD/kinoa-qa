import copy
import io
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from plan_parser import parse_acs, parse_cases, parse_conflicts, parse_gaps, parse_header
from plan_writer import merge_allure_ids
from smoke_to_plan import (SmokeRefusal, analyse, build_plan, main, parse_open_questions,
                           parse_preconditions, parse_steps, plan_path, strip_tags,
                           story_acceptance_criteria)
from validate_test_plan import validate

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "smoke_to_plan.py")
FIXTURES = os.path.join(HERE, "fixtures", "smoke")
EXPORT_FIXTURE = os.path.join(FIXTURES, "king-22281.json")
ENUM_FIXTURE = os.path.join(FIXTURES, "king-22976.json")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def node(response):
    return response["issues"]["nodes"][0]


def enum_input():
    return load(ENUM_FIXTURE)


def with_subtask_description(description, data=None):
    data = copy.deepcopy(data or enum_input())
    node(data["subtask"])["fields"]["description"] = description
    return data


def with_story_description(description, data=None):
    data = copy.deepcopy(data or enum_input())
    node(data["story"])["fields"]["description"] = description
    return data


def export_without_ac_heading():
    """KING-22281's input with its Story's `### AC` heading renamed, so the Story keeps its
    bullets but has no heading or field that opens an acceptance-criteria list."""
    data = load(EXPORT_FIXTURE)
    story = node(data["story"])
    description = story["fields"]["description"]
    assert description.count("### AC\n") == 1
    story["fields"]["description"] = description.replace("### AC\n", "### Outcomes\n")
    return data


def link(case_id, link_id=10001, title=None):
    return {"id": link_id,
            "self": "https://api.atlassian.com/ex/jira/x/rest/api/3/issue/KING-22976/remotelink/%d" % link_id,
            "globalId": "kinoa-qa:smoke-case:KING-22976",
            "object": {"url": "https://kinoa.testops.cloud/project/1/test-cases/%s" % case_id,
                       "title": title or "Allure TestOps case %s" % case_id}}


PRECONDITIONS = "## Preconditions\n\n* A signed-in operator.\n\n"


def validate_text(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "plan.test-plan.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return validate(path)


class StepParsing(unittest.TestCase):
    def step(self, steps, label):
        labels = [s["label"] for s in steps]
        self.assertIn(label, labels)
        return steps[labels.index(label)]

    def only(self, steps):
        self.assertEqual(1, len(steps))
        return steps[0]

    def test_the_three_step_grammars_all_read_the_gate(self):
        steps = parse_steps(
            "## Steps\n\n"
            "**1. `[GATE]`** Open the list.\n*Expected:* The list opens.\n\n"
            "**2. [GATE]** Click Export.\n_Expected:_ The modal opens.\n\n"
            "**3.** `[GATE]` Pick a project.\n_Expected:_ The scan starts.\n\n"
            "**4.** Wait.\n_Expected:_ The summary shows.\n")
        self.assertEqual(["1", "2", "3", "4"], [s["label"] for s in steps])
        self.assertEqual([True, True, True, False], [s["gate"] for s in steps])
        self.assertEqual(["Open the list.", "Click Export.", "Pick a project.", "Wait."],
                         [s["action"] for s in steps])

    def test_both_expected_spellings_give_one_expected_result(self):
        steps = parse_steps("## Steps\n\n**1.** `[GATE]` A.\n*Expected:* first.\n\n"
                            "**2.** B.\n_Expected:_ second.\n")
        self.assertEqual(["first.", "second."], [s["expected"] for s in steps])

    def test_a_wrapped_expected_line_continues_the_expected_result(self):
        steps = parse_steps("## Steps\n\n**2a.** Inspect the modal.\n"
                            "*Expected:* Headed **Export In-App**, a dropdown showing\n"
                            "`Select Project...`, and **Cancel**. `[Figma: Export modal]`\n")
        self.assertEqual("Headed **Export In-App**, a dropdown showing `Select Project...`, "
                         "and **Cancel**.", self.only(steps)["expected"])

    def test_a_sub_step_without_its_own_expected_folds_into_its_parent(self):
        steps = parse_steps("## Steps\n\n**2.** `[GATE]` Click **Export**.\n"
                            "_Expected:_ The modal opens. `[AC-1]`\n\n"
                            "**2a.** Keep the modal open. `[AC-2]`\n\n"
                            "**3.** Close it.\n_Expected:_ It closes.\n")
        self.assertEqual(["2", "3"], [s["label"] for s in steps])
        parent = self.step(steps, "2")
        self.assertEqual("Click **Export**. Keep the modal open.", parent["action"])
        self.assertEqual(["AC-1", "AC-2"], parent["acs"])

    def test_a_sub_step_without_expected_folds_into_the_sub_step_just_before_it(self):
        steps = parse_steps("## Steps\n\n**2.** `[GATE]` Open the modal.\n"
                            "_Expected:_ It opens.\n\n"
                            "**2a.** Fill the name.\n_Expected:_ The name shows.\n\n"
                            "**2b.** Click **Save**.\n\n"
                            "**3.** Close it.\n_Expected:_ It closes.\n")
        self.assertEqual(["2", "2a", "3"], [s["label"] for s in steps])
        self.assertEqual("Open the modal.", self.step(steps, "2")["action"])
        self.assertEqual("Fill the name. Click **Save**.", self.step(steps, "2a")["action"])

    def test_a_blank_line_inside_an_expected_result_does_not_end_it(self):
        steps = parse_steps("## Steps\n\n**1.** `[GATE]` Click **Export**.\n"
                            "*Expected:* The modal shows:\n\n"
                            "- a **Destination Project** dropdown\n"
                            "- **Export** disabled\n\n"
                            "**2.** Close it.\n_Expected:_ It closes.\n")
        self.assertEqual(["1", "2"], [s["label"] for s in steps])
        self.assertEqual("The modal shows: a **Destination Project** dropdown; **Export** "
                         "disabled", self.step(steps, "1")["expected"])

    def test_a_blank_line_inside_an_action_does_not_end_it(self):
        steps = parse_steps("## Steps\n\n**1.** `[GATE]` Open the list.\n\n"
                            "Then scroll to the last row. `[AC-2]`\n"
                            "*Expected:* The row shows.\n")
        step = self.only(steps)
        self.assertEqual("Open the list. Then scroll to the last row.", step["action"])
        self.assertEqual(["AC-2"], step["acs"])

    def test_a_sub_step_with_its_own_expected_is_its_own_step(self):
        steps = parse_steps(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        labels = [s["label"] for s in steps]
        self.assertEqual(["1", "2", "2a", "3", "4", "5", "6", "7", "8", "9", "10", "11",
                          "12", "13"], labels)
        sub = self.step(steps, "2a")
        self.assertEqual("Inspect the modal's controls.", sub["action"])
        self.assertFalse(sub["gate"])
        self.assertTrue(sub["expected"].startswith("A modal over a dimmed backdrop"))

    def test_steps_are_read_only_inside_the_steps_section(self):
        steps = parse_steps("## How to read this plan\n\n**9.** `[GATE]` Not a step.\n"
                            "_Expected:_ Nothing.\n\n"
                            "## Steps\n\n**1.** `[GATE]` Real step.\n_Expected:_ Real result.\n\n"
                            "## Open questions\n\n**1. Is the threshold 20?** Nobody said.\n\n"
                            "## Notes\n\n**2.** Also not a step.\n_Expected:_ Nope.\n")
        self.assertEqual([("1", "Real step.", "Real result.")],
                         [(s["label"], s["action"], s["expected"]) for s in steps])

    def test_the_real_open_question_shaped_like_a_step_is_not_a_step(self):
        steps = parse_steps(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        self.assertFalse(any("Reduction in manual recreation" in s["action"] for s in steps))
        self.assertEqual(["1", "2", "3", "5", "11", "12"],
                         [s["label"] for s in steps if s["gate"]])

    def test_blockquotes_run_notes_and_marked_lines_are_dropped(self):
        enum = parse_steps(node(enum_input()["subtask"])["fields"]["description"])
        export = parse_steps(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        self.assertEqual("The schema saves without error and the column persists with type "
                         "`enumeration`.", self.step(enum, "3")["expected"])
        self.assertEqual("It offers a manual value-entry mode and a file-import mode.",
                         self.step(enum, "2a")["expected"])
        self.assertEqual("Rejected with the error `Maximum 1000 values allowed`.",
                         self.step(enum, "12")["expected"])
        text = " ".join(s["action"] + " " + s["expected"] for s in enum + export)
        for dropped in ("Run note", "ANSWERED", "Known defect", "Fails on every run",
                        "Write down the entity names", "Latest run", "Step 12 asserts"):
            self.assertNotIn(dropped, text)

    def test_backticked_and_bare_tags_are_stripped(self):
        steps = parse_steps("## Steps\n\n**1.** [GATE] Open it. [AC-2]\n"
                            "_Expected:_ It opens. [Story] `[PRD: Export flow]` [live-confirmed] "
                            "`[Figma → live-confirmed]`\n")
        step = self.only(steps)
        self.assertEqual("Open it.", step["action"])
        self.assertEqual("It opens.", step["expected"])
        self.assertTrue(step["gate"])
        self.assertEqual(["AC-2"], step["acs"])

    def test_a_code_span_of_several_tags_is_stripped_whole(self):
        steps = parse_steps(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        last = self.step(steps, "13")
        self.assertTrue(last["expected"].endswith("pre-existing version is unchanged."),
                        last["expected"])

    def test_a_dated_jira_key_tag_with_a_dash_and_commas_is_stripped(self):
        clean, tags = strip_tags("It saves. `[KING-22317, 4 Sep — a, b]` Done.")
        self.assertEqual("It saves. Done.", clean)
        self.assertEqual(["[KING-22317, 4 Sep — a, b]"], tags)
        step = self.step(parse_steps(node(enum_input()["subtask"])["fields"]["description"]), "5")
        self.assertTrue(step["expected"].endswith("never returned."), step["expected"])

    def test_a_tag_value_containing_a_bracket_and_a_comma_is_stripped_whole(self):
        clean, tags = strip_tags("Opens. `[KING-1, see [x], y] z, w]` "
                                 "[PRD: Export [v2], a, b] done")
        self.assertEqual("Opens. done", clean)
        self.assertEqual(["[KING-1, see [x], y] z, w]", "[PRD: Export [v2], a, b]"], tags)

    def test_a_bare_value_tag_with_a_lone_bracket_in_its_value_is_stripped_whole(self):
        clean, tags = strip_tags("Opens. [PRD: see a] b, c] done")
        self.assertEqual("Opens. done", clean)
        self.assertEqual(["[PRD: see a] b, c]"], tags)

    def test_a_bare_value_tag_ends_at_its_first_bracket_when_no_comma_follows(self):
        clean, tags = strip_tags("Opens. [PRD: flow] x] y")
        self.assertEqual("Opens. x] y", clean)
        self.assertEqual(["[PRD: flow]"], tags)

    def test_a_bare_value_tag_does_not_swallow_a_bracket_in_parenthesised_prose(self):
        clean, tags = strip_tags("Opens. [KING-12] the list (a, b] shows")
        self.assertEqual("Opens. the list (a, b] shows", clean)
        self.assertEqual(["[KING-12]"], tags)

    def test_a_code_span_of_a_tag_and_parenthesised_prose_is_kept(self):
        clean, tags = strip_tags("Opens. `[KING-12] the list (a, b]` shows")
        self.assertEqual("Opens. `[KING-12] the list (a, b]` shows", clean)
        self.assertEqual([], tags)

    def test_two_adjacent_bare_value_tags_stay_two_tags(self):
        clean, tags = strip_tags("Opens. [PRD: flow] [Figma: modal] done")
        self.assertEqual("Opens. done", clean)
        self.assertEqual(["[PRD: flow]", "[Figma: modal]"], tags)

    def test_prose_brackets_after_a_bare_value_tag_are_kept(self):
        clean, tags = strip_tags("Opens. [PRD: flow] see [link](https://x.y) done")
        self.assertEqual("Opens. see [link](https://x.y) done", clean)
        self.assertEqual(["[PRD: flow]"], tags)

    def test_adjacent_tags_without_a_space_in_one_code_span_are_split(self):
        steps = parse_steps("## Steps\n\n**1.** Open it. `[AC-2][GATE]`\n"
                            "_Expected:_ It opens. `[AC-2][Story]`\n")
        step = self.only(steps)
        self.assertTrue(step["gate"])
        self.assertEqual(["AC-2"], step["acs"])
        self.assertEqual(("Open it.", "It opens."), (step["action"], step["expected"]))
        self.assertEqual(("It opens.", ["[AC-2]", "[Story]"]),
                         strip_tags("It opens. `[AC-2][Story]`"))

    def test_a_code_span_mixing_a_tag_and_code_is_kept(self):
        clean, tags = strip_tags("Send `[GATE] rm -rf` and a [link](https://x.y) with `code`.")
        self.assertEqual("Send `[GATE] rm -rf` and a [link](https://x.y) with `code`.", clean)
        self.assertEqual([], tags)

    def test_ac_ids_are_collected_per_step(self):
        enum = parse_steps(node(enum_input()["subtask"])["fields"]["description"])
        self.assertEqual(["AC-1"], self.step(enum, "1")["acs"])
        self.assertEqual([], self.step(enum, "2")["acs"])
        self.assertEqual(["AC-2"], self.step(enum, "7")["acs"])
        self.assertEqual(["AC-5"], self.step(enum, "10")["acs"])
        export = parse_steps(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        self.assertEqual(["AC-3"], self.step(export, "12")["acs"])

    def test_no_tag_text_or_bracket_leaks_into_real_step_text(self):
        for path in (EXPORT_FIXTURE, ENUM_FIXTURE):
            steps = parse_steps(node(load(path)["subtask"])["fields"]["description"])
            self.assertTrue(steps, path)
            for s in steps:
                for part in (s["action"], s["expected"]):
                    self.assertIsNotNone(part, (path, s["label"]))
                    for leak in ("[", "]", "GATE", "live-confirmed", "AC-", "`[", "Figma:"):
                        self.assertNotIn(leak, part, (path, s["label"], part))

    def test_real_enum_sub_task_has_thirteen_steps_and_five_gates(self):
        steps = parse_steps(node(enum_input()["subtask"])["fields"]["description"])
        self.assertEqual(13, len(steps))
        self.assertEqual(["1", "2", "3", "6", "7"], [s["label"] for s in steps if s["gate"]])

    def test_preconditions_are_one_statement_per_item_and_tag_free(self):
        pre = parse_preconditions(node(enum_input()["subtask"])["fields"]["description"])
        self.assertEqual(4, len(pre), pre)
        self.assertTrue(pre[0].startswith("Run on the **test** environment (`develop`)."))
        self.assertTrue(pre[0].endswith("cannot carry a binding at all."), pre[0])
        export = parse_preconditions(node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        self.assertIn("Destination project integration settings otherwise matching source.",
                      export)
        self.assertFalse(any("consumes its own preconditions" in p for p in export))

    def test_open_questions_carry_their_answered_mark(self):
        questions = parse_open_questions(node(enum_input()["subtask"])["fields"]["description"])
        self.assertEqual(["1", "2", "3", "4", "5", "6"], [q["label"] for q in questions])
        self.assertEqual([False, True, False, False, False, False],
                         [q["answered"] for q in questions])
        export = parse_open_questions(
            node(load(EXPORT_FIXTURE)["subtask"])["fields"]["description"])
        self.assertEqual(1, len(export))
        self.assertTrue(export[0]["text"].startswith("AC \"Reduction in manual recreation"))


class Refusals(unittest.TestCase):
    def acs(self, description, extra_fields=None, names=None):
        data = with_story_description(description)
        story = node(data["story"])
        story["fields"].update(extra_fields or {})
        if names is not None:
            story["names"] = names
        return story_acceptance_criteria(story)

    def assertRefuses(self, data, *fragments):
        with self.assertRaises(SmokeRefusal) as ctx:
            analyse(data)
        for fragment in fragments:
            self.assertIn(fragment, str(ctx.exception))

    def test_the_heading_forms_all_open_the_ac_list(self):
        for heading in ("## Acceptance criteria", "### Acceptance Criteria",
                        "**Acceptance criteria:**", "**ACCEPTANCE CRITERIA**",
                        "## acceptance criteria:"):
            self.assertEqual(["First.", "Second."],
                             self.acs("Intro.\n\n%s\n\n* First.\n* Second.\n\n## Next\n\n* No.\n"
                                      % heading), heading)

    def test_the_short_ac_headings_all_open_the_ac_list(self):
        for heading in ("### AC", "## ACs", "**AC**", "## ac:", "**ACs:**"):
            self.assertEqual(["First.", "Second."],
                             self.acs("Intro.\n\n%s\n\n* First.\n* Second.\n\n## Next\n\n* No.\n"
                                      % heading), heading)

    def test_a_heading_that_only_starts_with_ac_does_not_open_the_ac_list(self):
        for heading in ("### ACME rollout", "## ACs and more", "**Access**"):
            self.assertEqual([], self.acs("Intro.\n\n%s\n\n* First.\n* Second.\n" % heading),
                             heading)

    def test_the_real_export_story_lists_its_five_criteria_under_its_ac_heading(self):
        acs = story_acceptance_criteria(node(load(EXPORT_FIXTURE)["story"]))
        self.assertEqual(5, len(acs))
        self.assertTrue(acs[2].startswith("Exported In-App and its dependencies are created"))
        self.assertFalse(any("initially created as In-review" in a for a in acs))

    def test_the_real_export_sub_task_analyses_citing_ac_3_from_step_12(self):
        result = analyse(load(EXPORT_FIXTURE))
        self.assertEqual("KING-19550", result["story_key"])
        self.assertEqual(5, len(result["acs"]))
        self.assertEqual(["AC-3"], result["cited"])
        step12 = [s for s in result["steps"] if s["label"] == "12"]
        self.assertEqual(1, len(step12), [s["label"] for s in result["steps"]])
        self.assertEqual(["AC-3"], step12[0]["acs"])

    def test_the_real_export_plan_validates_pass(self):
        report = validate_text(build_plan(load(EXPORT_FIXTURE), "in-apps/export"))
        self.assertEqual("PASS", report["outcome"], report["checks"])
        self.assertEqual(0, report["exit_code"])

    def test_numbered_items_are_criteria(self):
        self.assertEqual(["One.", "Two."],
                         self.acs("## Acceptance criteria\n\n1. One.\n2. Two.\n"))

    def test_nested_items_and_continuation_lines_fold_into_their_parent(self):
        self.assertEqual(["Export works for a single In-App: incl. its segments and its events.",
                          "Conflicts block the export."],
                         self.acs("## Acceptance criteria\n\n"
                                  "* Export works for a single In-App:\n"
                                  "  * incl. its segments\n"
                                  "  * and its events.\n"
                                  "* Conflicts block\n  the export.\n\n"
                                  "Some later paragraph.\n* Not a criterion.\n"))

    def test_only_the_first_acceptance_criteria_heading_counts(self):
        self.assertEqual(["A."], self.acs("## Acceptance criteria\n\n* A.\n\n"
                                          "## Acceptance criteria\n\n* B.\n"))

    def test_the_real_story_lists_five_criteria_and_stops_at_the_next_heading(self):
        acs = story_acceptance_criteria(node(enum_input()["story"]))
        self.assertEqual(5, len(acs))
        self.assertTrue(acs[0].startswith("A Game Developer can select `enumeration`"))
        self.assertFalse(any("Creating or editing" in a for a in acs))

    def test_the_acceptance_criteria_field_is_the_fallback(self):
        self.assertEqual(["From the field.", "Second field item."],
                         self.acs("No list here.",
                                  extra_fields={"customfield_10500":
                                                "* From the field.\n* Second field item.\n"},
                                  names={"customfield_10500": "Acceptance Criteria"}))

    def test_a_step_with_no_expected_result_refuses_naming_the_step(self):
        self.assertRefuses(with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A.\n_Expected:_ a.\n\n"
                            "**4.** Do something.\n\n**5.** B.\n_Expected:_ b.\n"),
            "step 4", "no expected result")

    def test_a_step_with_two_expected_results_refuses_naming_the_step(self):
        self.assertRefuses(with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A.\n_Expected:_ a.\n_Expected:_ b.\n"),
            "step 1")

    def test_no_gate_step_refuses(self):
        self.assertRefuses(with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** A.\n_Expected:_ a.\n"), "[GATE]")

    def test_no_steps_section_refuses(self):
        self.assertRefuses(with_subtask_description(
            PRECONDITIONS + "**1.** `[GATE]` A.\n_Expected:_ a.\n"), "## Steps")

    def test_no_preconditions_section_refuses(self):
        self.assertRefuses(with_subtask_description(
            "## Steps\n\n**1.** `[GATE]` A.\n_Expected:_ a.\n"), "## Preconditions")

    def test_an_empty_preconditions_section_refuses(self):
        self.assertRefuses(with_subtask_description(
            "## Preconditions\n\n> only a note\n\n## Steps\n\n**1.** `[GATE]` A.\n"
            "_Expected:_ a.\n"), "## Preconditions", "empty")

    def test_a_story_with_no_acceptance_criteria_list_refuses(self):
        data = export_without_ac_heading()
        self.assertEqual([], story_acceptance_criteria(node(data["story"])))
        self.assertRefuses(data, "KING-19550", "acceptance criteria")

    def test_an_ac_past_the_story_count_refuses(self):
        self.assertRefuses(with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A.\n_Expected:_ a. `[AC-7]`\n"),
            "AC-7", "5")

    def test_an_issue_that_is_not_a_sub_task_refuses(self):
        data = enum_input()
        node(data["subtask"])["fields"]["issuetype"].update({"name": "Story", "subtask": False})
        self.assertRefuses(data, "KING-22976", "sub-task")

    def test_a_sub_task_whose_parent_is_not_a_story_refuses(self):
        data = enum_input()
        node(data["subtask"])["fields"]["parent"]["fields"]["issuetype"]["name"] = "Epic"
        self.assertRefuses(data, "KING-22976", "Story")

    def test_a_story_response_for_another_issue_refuses(self):
        data = enum_input()
        node(data["story"])["key"] = "KING-1"
        self.assertRefuses(data, "KING-22218", "KING-1")

    def test_valid_input_returns_the_ac_list_and_the_cited_ids(self):
        result = analyse(enum_input())
        self.assertEqual(5, len(result.get("acs") or []))
        self.assertEqual(["AC-1", "AC-2", "AC-5"], result.get("cited"))
        self.assertEqual("KING-22218", result.get("story_key"))

    def test_cited_acs_are_in_citation_order_without_duplicates(self):
        data = with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A. `[AC-3]`\n_Expected:_ a.\n\n"
            "**2.** B.\n_Expected:_ b. `[AC-1]` `[AC-3]`\n")
        self.assertEqual(["AC-3", "AC-1"], analyse(data)["cited"])


class PlanBuild(unittest.TestCase):
    def build(self, data=None, target="feature-settings/enum-column"):
        return build_plan(data or enum_input(), target)

    def case(self, text):
        cases = parse_cases(text)
        self.assertEqual(1, len(cases))
        return cases[0]

    def test_the_built_plan_validates_pass(self):
        report = validate_text(self.build())
        self.assertEqual("PASS", report["outcome"], report["checks"])
        self.assertEqual(0, report["exit_code"])

    def test_the_header_is_the_parent_story_in_smoke_scope(self):
        header = parse_header(self.build())
        self.assertEqual("KING-22218", header.get("story"))
        self.assertEqual("As a Game Developer I want to create a Feature Schema column of type "
                         "enumeration", header.get("title"))
        self.assertEqual("smoke", header.get("scope"))
        self.assertEqual("feature-settings/enum-column", header.get("target"))

    def test_a_story_summary_with_a_dot_and_a_colon_round_trips(self):
        data = enum_input()
        summary = "Export · Import: In-App flow · Step 2: done"
        node(data["story"])["fields"]["summary"] = summary
        node(data["subtask"])["fields"]["parent"]["fields"]["summary"] = summary
        text = self.build(data)
        self.assertEqual(summary, parse_header(text).get("title"))
        self.assertEqual("PASS", validate_text(text)["outcome"])

    def test_a_summary_the_header_would_split_refuses(self):
        data = enum_input()
        node(data["story"])["fields"]["summary"] = "Export · note: lower-case key"
        with self.assertRaises(SmokeRefusal) as ctx:
            self.build(data)
        self.assertIn("title", str(ctx.exception))

    def test_one_functional_p1_case_titled_from_the_sub_task_summary(self):
        case = self.case(self.build())
        self.assertEqual("As a Game Developer I want to create a Feature Schema column of type "
                         "enumeration", case["title"])
        self.assertEqual("functional", case["tags"]["type"])
        self.assertEqual("P1", case["tags"]["priority"])

    def test_a_summary_without_the_prefix_is_used_whole(self):
        data = enum_input()
        node(data["subtask"])["fields"]["summary"] = "Enumeration column smoke"
        self.assertEqual("Enumeration column smoke", self.case(self.build(data))["title"])

    def test_purpose_is_verify_that_and_the_title(self):
        self.assertEqual("Verify that As a Game Developer I want to create a Feature Schema "
                         "column of type enumeration.",
                         self.case(self.build())["tags"].get("purpose"))
        data = enum_input()
        node(data["subtask"])["fields"]["summary"] = "Smoke test: Export works."
        self.assertEqual("Verify that Export works.",
                         self.case(self.build(data))["tags"].get("purpose"))

    def test_source_cites_the_step_acs(self):
        self.assertEqual("ac: AC-1, AC-2, AC-5", self.case(self.build())["tags"]["source"])

    def test_source_lists_the_acs_in_citation_order(self):
        data = with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A. `[AC-3]`\n_Expected:_ a.\n\n"
            "**2.** B.\n_Expected:_ b. `[AC-1]`\n")
        text = self.build(data)
        self.assertEqual("ac: AC-3, AC-1", self.case(text)["tags"]["source"])
        self.assertEqual("PASS", validate_text(text)["outcome"])

    def test_a_capability_holding_a_slash_splits_on_the_first_slash(self):
        text = self.build(target="In App Templates/Export / Import")
        self.assertEqual("In App Templates/Export / Import", parse_header(text).get("target"))
        self.assertEqual("PASS", validate_text(text)["outcome"])
        self.assertEqual("KING-22218-in-app-templates-export---import-smoke.test-plan.md",
                         os.path.basename(plan_path("KING-22218",
                                                    "In App Templates/Export / Import")))

    def test_source_is_qa_added_without_an_ac_citation(self):
        data = with_subtask_description(
            PRECONDITIONS + "## Steps\n\n**1.** `[GATE]` A.\n_Expected:_ a. `[Story]`\n")
        text = self.build(data)
        self.assertEqual("QA-added: smoke scenario with no AC citation",
                         self.case(text)["tags"]["source"])
        self.assertEqual("PASS", validate_text(text)["outcome"])

    def test_preconditions_are_one_per_line(self):
        pre = self.case(self.build())["tags"]["preconditions"].split("\n")
        self.assertEqual(4, len(pre))
        self.assertTrue(pre[1].startswith("Operator login with rights"))
        self.assertNotIn("[", "".join(pre))

    def test_steps_parse_back_with_one_expected_result_each(self):
        steps = self.case(self.build())["steps"]
        self.assertEqual(13, len(steps))
        self.assertTrue(all(s["expected"] and not s["extra_expected"] for s in steps))
        self.assertEqual("Inspect that control.", steps[2]["action"])

    def test_expected_joins_the_gate_steps_results(self):
        expected = self.case(self.build())["tags"]["expected"]
        for part in ("`enumeration` is offered as a column type",
                     "A control appears for that column",
                     "The schema saves without error",
                     "The configuration saves successfully.",
                     "returned as **422** — not 500."):
            self.assertIn(part, expected)
        self.assertNotIn("Rejected. Matching is exact", expected)

    def test_the_acceptance_criteria_section_lists_the_story_acs(self):
        acs = parse_acs(self.build())
        self.assertEqual(["AC-1", "AC-2", "AC-3", "AC-4", "AC-5"], sorted(acs))
        self.assertTrue(acs.get("AC-3", "").startswith("The SDK supports"))

    def test_unanswered_open_questions_become_gap_lines(self):
        text = self.build()
        self.assertEqual({"Open question 1", "Open question 3", "Open question 4",
                          "Open question 5", "Open question 6"}, parse_gaps(text))
        self.assertNotIn("ANSWERED", text)

    def test_conflicts_section_is_present_and_empty(self):
        has_section, conflicts, unrecognised = parse_conflicts(self.build())
        self.assertEqual((True, [], []), (has_section, conflicts, unrecognised))

    def test_building_twice_gives_identical_text(self):
        text = self.build()
        self.assertIn("### TC-1 · ", text)
        self.assertEqual(text, self.build())

    def test_no_target_is_written_as_none(self):
        self.assertEqual("none", parse_header(build_plan(enum_input(), None)).get("target"))


class IdCarry(unittest.TestCase):
    def allure_id(self, text):
        cases = parse_cases(text)
        self.assertEqual(1, len(cases))
        return cases[0]["tags"].get("allure-id")

    def data(self, links):
        data = enum_input()
        data["remote_links"] = links
        return data

    def test_the_link_becomes_the_first_field_of_the_case(self):
        lines = build_plan(self.data([link(4711)]), "svc/cap").split("\n")
        headings = [i for i, l in enumerate(lines) if l.startswith("### TC-1 · ")]
        self.assertEqual(1, len(headings))
        self.assertEqual("- allure-id: 4711", lines[headings[0] + 1])
        self.assertEqual("PASS", validate_text("\n".join(lines))["outcome"])

    def test_a_link_title_with_text_after_the_id_carries_the_id(self):
        lines = build_plan(self.data([link(4711, title="Allure TestOps case 4711 (smoke)")]),
                           "svc/cap").split("\n")
        self.assertIn("- allure-id: 4711", lines)

    def test_a_link_title_with_surrounding_whitespace_carries_the_id(self):
        lines = build_plan(self.data([link(5, title=" Allure TestOps case 5 ")]),
                           "svc/cap").split("\n")
        self.assertIn("- allure-id: 5", lines)

    def test_case_id_zero_is_not_a_case_id(self):
        text = build_plan(self.data([link(0, title="Allure TestOps case 0")]), "svc/cap")
        self.assertIsNone(self.allure_id(text))
        self.assertNotIn("allure-id", text)

    def test_no_link_writes_no_id(self):
        text = build_plan(self.data([]), "svc/cap")
        self.assertIsNone(self.allure_id(text))

    def test_other_remote_links_are_ignored(self):
        text = build_plan(self.data([link(1, title="Export In-App PRD")]), "svc/cap")
        self.assertIsNone(self.allure_id(text))

    def test_the_link_id_survives_a_merge_with_a_previous_plan_of_another_title(self):
        previous = build_plan(self.data([]), "svc/cap").replace(
            "### TC-1 · As a Game Developer", "### TC-1 · Old wording of As a Game Developer")
        previous = previous.replace("- type: functional", "- allure-id: 999\n- type: functional")
        merged, _ = merge_allure_ids(previous, build_plan(self.data([link(4711)]), "svc/cap"))
        self.assertEqual("4711", self.allure_id(merged))

    def test_the_id_survives_a_deleted_cache_and_a_changed_target(self):
        for target in ("svc/cap", "other/thing", None):
            merged, _ = merge_allure_ids("", build_plan(self.data([link(4711)]), target))
            self.assertEqual("4711", self.allure_id(merged), target)

    def test_the_same_id_on_two_links_is_one_id(self):
        text = build_plan(self.data([link(4711), link(4711, link_id=10002)]), "svc/cap")
        self.assertEqual("4711", self.allure_id(text))

    def test_two_links_with_different_ids_refuse_naming_both(self):
        with self.assertRaises(SmokeRefusal) as ctx:
            build_plan(self.data([link(4711), link(4712, link_id=10002)]), "svc/cap")
        self.assertIn("4711", str(ctx.exception))
        self.assertIn("4712", str(ctx.exception))


class Cli(unittest.TestCase):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def write_input(self, tmp, data):
        path = os.path.join(tmp, "input.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_the_plan_is_printed_on_stdout(self):
        code, out, err = self.run_main(["--input", ENUM_FIXTURE, "--target", "svc/cap"])
        self.assertEqual(0, code, err)
        self.assertEqual(build_plan(enum_input(), "svc/cap"), out)

    def test_a_refusal_prints_its_reason_on_stderr_and_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input(tmp, export_without_ac_heading())
            code, out, err = self.run_main(["--input", path, "--target", "svc/cap"])
        self.assertEqual(1, code)
        self.assertEqual("", out)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn("KING-19550", err)

    def test_an_unreadable_input_is_a_refusal(self):
        code, out, err = self.run_main(["--input", os.path.join(FIXTURES, "missing.json")])
        self.assertEqual(1, code)
        self.assertTrue(err.startswith("refused: "), err)

    def test_a_target_without_a_capability_is_a_refusal(self):
        code, _, err = self.run_main(["--input", ENUM_FIXTURE, "--target", "svc"])
        self.assertEqual(1, code)
        self.assertIn("--target", err)

    def test_print_path_is_the_stable_smoke_path(self):
        code, out, _ = self.run_main(["--input", ENUM_FIXTURE, "--target",
                                      "Feature-Settings/Enum Column", "--print-path"])
        self.assertEqual(0, code)
        path = out.strip()
        self.assertEqual("KING-22218-feature-settings-enum-column-smoke.test-plan.md",
                         os.path.basename(path))
        self.assertTrue(os.path.dirname(path).endswith(os.path.join(".kinoa-qa", "plans")), path)
        self.assertEqual(path, plan_path("KING-22218", "Feature-Settings/Enum Column"))

    def test_print_path_without_a_target_is_no_target(self):
        code, out, _ = self.run_main(["--input", ENUM_FIXTURE, "--print-path"])
        self.assertEqual(0, code)
        self.assertEqual("KING-22218-no-target-smoke.test-plan.md",
                         os.path.basename(out.strip()))

    def test_the_script_runs_from_a_shell(self):
        proc = subprocess.run([sys.executable, SCRIPT, "--input", ENUM_FIXTURE],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertTrue(proc.stdout.startswith("# QA Test Plan"), proc.stdout[:80])


if __name__ == "__main__":
    unittest.main()
