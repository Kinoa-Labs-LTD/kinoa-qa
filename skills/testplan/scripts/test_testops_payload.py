import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import parse_cases
from testops_payload import slugify, traceability_tag, case_to_payload

FIELDS = {"Suite": "[KING-1] Admin sign-in", "Story": "Template",
          "Component": "Game-Settings", "Feature": "In-Apps"}


def _step(action, expected):
    """A step exactly as `parse_cases` emits one: the plan's step NUMBER is stripped by the
    parser, so a real action never carries it. Keep this shape coupled to the parser —
    `PLAN` below re-derives the same two steps through `parse_cases` to prove it."""
    return {"action": action, "expected": expected, "extra_expected": []}


PLAN = """# QA Test Plan — svc / cap

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- purpose: Verify an admin with valid credentials reaches the dashboard.
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. enter valid credentials
     → expected: the form accepts them
  2. submit
     → expected: the dashboard opens
- expected: signed in
"""


CASE = {
    "id": "TC-1", "title": "Happy path sign-in",
    "tags": {"type": "functional", "priority": "P1",
             "source": "ac: AC-1",
             "purpose": "Verify an admin with valid credentials reaches the dashboard.",
             "preconditions": "a user exists", "expected": "signed in"},
    "steps": [_step("enter valid credentials", "the form accepts them"),
              _step("submit", "the dashboard opens")],
}


def _case(**tags):
    c = {"id": "TC-9", "title": "Sign-in",
         "steps": [_step("go", "it opens")],
         "tags": {"type": "functional", "priority": "P2", "source": "ac: AC-1",
                  "purpose": "Verify sign-in works."}}
    c["tags"].update(tags)
    return c


def _payload(case):
    return case_to_payload(case, story="KING-1", service="svc", capability="cap",
                           custom_fields=FIELDS)

class TestFixtureMirrorsTheParser(unittest.TestCase):
    """The hand-written CASE fixture must stay the shape `parse_cases` really produces,
    or a parser regression that leaked step numbers into `action` would go unseen here."""

    def test_case_steps_match_parse_cases_output(self):
        self.assertEqual(parse_cases(PLAN)[0]["steps"], CASE["steps"])

    def test_no_fixture_action_carries_a_step_number(self):
        for step in CASE["steps"] + _case()["steps"]:
            self.assertNotRegex(step["action"], r"^\d+\.")


class TestPayload(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Sign-in/Happy path!"), "sign-in-happy-path")

    def test_traceability_tag_is_deterministic_and_aql_safe(self):
        a = traceability_tag("KING-1", "svc", "cap", "scenario: Sign-in/Happy path")
        b = traceability_tag("KING-1", "svc", "cap", "scenario: Sign-in/Happy path")
        self.assertEqual(a, b)                       # re-run stability
        self.assertTrue(a.startswith("tp-"))
        self.assertRegex(a, r"^[a-z0-9-]+$")         # AQL-safe

    def test_traceability_tag_differs_per_scenario(self):
        a = traceability_tag("KING-1", "svc", "cap", "scenario: Sign-in/Happy path")
        b = traceability_tag("KING-1", "svc", "cap", "scenario: Sign-in/Bad password")
        self.assertNotEqual(a, b)

    def test_traceability_tag_distinguishes_cases_sharing_a_scenario(self):
        src = "scenario: Sign-in/Happy path"
        a = traceability_tag("KING-1", "svc", "cap", src, "Happy path sign-in")
        b = traceability_tag("KING-1", "svc", "cap", src, "Sign-in rejects a locked account")
        self.assertNotEqual(a, b)

    def test_payload_shape(self):
        p = _payload(CASE)
        self.assertEqual(p["name"], "Happy path sign-in")          # no TC-n prefix
        self.assertNotIn("TC-", p["name"])
        self.assertEqual(p["description"],
                         "Verify an admin with valid credentials reaches the dashboard.")
        self.assertEqual(p["precondition"], "a user exists")
        self.assertEqual(p["expectedResult"], "signed in")
        self.assertEqual(p["status"], "Draft")
        self.assertEqual(p["workflow"], "Manual Kinoa")
        self.assertNotIn("testLayer", p)
        self.assertNotIn("links", p)
        self.assertEqual(p["issues"], [{"name": "Kinoa-Allure", "value": "KING-1"}])
        self.assertEqual([s["body"] for s in p["scenario"]["steps"]],
                         ["enter valid credentials", "submit"])   # numbering stripped
        self.assertEqual(p["scenario"]["steps"][0]["type"], "body")

    def test_each_step_carries_exactly_one_expected_result(self):
        steps = _payload(CASE)["scenario"]["steps"]
        for step, expected in zip(steps, ["the form accepts them", "the dashboard opens"]):
            self.assertEqual(step["expectedResultSteps"],
                             [{"type": "expected_body", "body": expected}])

    def test_tags_are_only_the_traceability_key_and_qa_generated(self):
        p = _payload(CASE)
        ttag = traceability_tag("KING-1", "svc", "cap", CASE["tags"]["source"],
                                CASE["title"], CASE["tags"]["type"])
        self.assertEqual(sorted(p["tags"]), sorted(["qa-generated", ttag]))

    def test_traceability_tag_is_length_bounded(self):
        long_src = "scenario: " + "Very Long Requirement Name " * 10 + "/" + "Verbose scenario " * 10
        long_title = "An extremely verbose scenario title " * 10
        t = traceability_tag("KING-22737", "kinoa-client-support-tool", "admin-authentication",
                             long_src, long_title, "functional")
        self.assertLessEqual(len(t), 100)
        self.assertRegex(t, r"^[a-z0-9-]+$")

    def test_traceability_tag_distinguishes_cases_by_type(self):
        src, title = "scenario: Sign-in/Happy path", "Sign in"
        a = traceability_tag("KING-1", "svc", "cap", src, title, "functional")
        b = traceability_tag("KING-1", "svc", "cap", src, title, "negative")
        self.assertNotEqual(a, b)

    def test_traceability_tag_handles_non_ascii(self):
        a = traceability_tag("KING-1", "svc", "cap", "ac: AC-1", "Вхід користувача")
        b = traceability_tag("KING-1", "svc", "cap", "ac: AC-1", "Блокування акаунта")
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^[a-z0-9-]+$")

class TestTagVocabulary(unittest.TestCase):
    """The emitted vocabulary is exactly two tags: the tp- idempotency key and qa-generated.
    type-*, priority-*, openspec-context, design-backed and spec-derived are all retired;
    provenance that rode on the dropped tags now lives in the description suffix."""

    def test_every_case_tags_qa_generated(self):
        for case in (_case(), _case(**{"openspec-ref": "Sign-in/Happy path"}),
                     _case(**{"design-ref": "abc123/1:2 — Sign-in"})):
            self.assertIn("qa-generated", _payload(case)["tags"])

    def test_retired_tags_are_never_emitted(self):
        for case in (_case(), _case(**{"openspec-ref": "Sign-in/Happy path"}),
                     _case(**{"design-ref": "abc123/1:2 — Sign-in"})):
            t = _payload(case)["tags"]
            for retired in ("spec-derived", "openspec-context", "design-backed",
                            "type-functional", "priority-p2", "priority-unset"):
                self.assertNotIn(retired, t)

    def test_description_carries_openspec_and_design_provenance(self):
        d = _payload(_case(**{"openspec-ref": "auth#Sign-in/Happy path",
                              "design-ref": "abc123/1:2 — Sign-in"}))["description"]
        self.assertTrue(d.startswith("Verify sign-in works."))
        self.assertIn("openspec-ref: auth#Sign-in/Happy path", d)
        self.assertIn("design-ref: abc123/1:2 — Sign-in", d)
        self.assertEqual(len(d.splitlines()), 2)      # purpose + one provenance line

    def test_description_omits_absent_refs(self):
        d = _payload(_case())["description"]
        self.assertEqual(d, "Verify sign-in works.")
        self.assertNotIn("openspec-ref", d)
        self.assertNotIn("design-ref", d)
        self.assertNotIn("source:", d)
        self.assertNotIn("traceability:", d)


class TestCustomFields(unittest.TestCase):
    """The four custom fields arrive already resolved and verified; the builder only
    shapes them into the reference's {name, value} list and never invents a value."""

    def test_all_four_fields_are_emitted_in_reference_form(self):
        cf = _payload(CASE)["customFields"]
        self.assertEqual(cf, [{"name": "Suite", "value": "[KING-1] Admin sign-in"},
                              {"name": "Story", "value": "Template"},
                              {"name": "Component", "value": "Game-Settings"},
                              {"name": "Feature", "value": "In-Apps"}])

    def test_suite_is_the_story_key_and_title(self):
        fields = dict(FIELDS, Suite="[KING-42] Export of In-App template")
        p = case_to_payload(CASE, story="KING-42", service="svc", capability="cap",
                            custom_fields=fields)
        self.assertIn({"name": "Suite", "value": "[KING-42] Export of In-App template"},
                      p["customFields"])
        self.assertEqual(p["issues"][0]["value"], "KING-42")

    def test_a_missing_field_value_never_reaches_a_payload(self):
        for absent in ("Story", "Component", "Feature", "Suite"):
            incomplete = {k: v for k, v in FIELDS.items() if k != absent}
            with self.assertRaises(ValueError) as ctx:
                case_to_payload(CASE, story="KING-1", service="svc", capability="cap",
                                custom_fields=incomplete)
            self.assertIn(absent, str(ctx.exception))


class TestTraceabilityTagRegression(unittest.TestCase):
    """The tag's inputs and hashing are frozen: the tp- tag is TestOps' idempotency key,
    so any drift re-keys every case. This pins one fixed input to its exact current value."""

    def test_traceability_tag_output_is_frozen(self):
        self.assertEqual(
            traceability_tag("KING-22737", "kinoa-client-support-tool",
                             "admin-authentication", "ac: AC-1",
                             "Happy path sign-in", "functional"),
            "tp-king-22737-kinoa-client-support-tool-admin-authentication-51a56980d9")


if __name__ == "__main__":
    unittest.main()
