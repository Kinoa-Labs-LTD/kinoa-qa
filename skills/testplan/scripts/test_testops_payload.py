import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from testops_payload import slugify, traceability_tag, case_to_payload

CASE = {
    "id": "TC-1", "title": "Happy path sign-in",
    "tags": {"type": "functional", "priority": "P1",
             "source": "ac: AC-1",
             "preconditions": "a user exists", "expected": "signed in"},
    "steps": ["1. enter valid credentials", "2. submit"],
}


def _case(**tags):
    c = {"id": "TC-9", "title": "Sign-in", "steps": ["1. go"],
         "tags": {"type": "functional", "priority": "P2", "source": "ac: AC-1"}}
    c["tags"].update(tags)
    return c


def _payload(case):
    return case_to_payload(case, story="KING-1", service="svc", capability="cap",
                           jira_base_url="https://kinoadev.atlassian.net")

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
        p = case_to_payload(CASE, story="KING-1", service="svc", capability="cap",
                            jira_base_url="https://kinoadev.atlassian.net")
        self.assertEqual(p["name"], "TC-1 · Happy path sign-in")
        self.assertEqual(p["precondition"], "a user exists")
        self.assertEqual(p["expectedResult"], "signed in")
        self.assertEqual([s["body"] for s in p["scenario"]["steps"]],
                         ["enter valid credentials", "submit"])   # numbering stripped
        self.assertEqual(p["scenario"]["steps"][0]["type"], "body")
        self.assertIn("qa-generated", p["tags"])
        self.assertNotIn("spec-derived", p["tags"])
        self.assertIn("type-functional", p["tags"])
        self.assertIn("priority-p1", p["tags"])
        self.assertIn(traceability_tag("KING-1", "svc", "cap", CASE["tags"]["source"], CASE["title"], CASE["tags"]["type"]), p["tags"])
        self.assertEqual(p["links"][0]["url"], "https://kinoadev.atlassian.net/browse/KING-1")

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
    """Every plugin-authored case always carries qa-generated; openspec-context and
    design-backed ride additively off the case's openspec-ref / design-ref fields.
    The retired spec-derived tag must never be emitted."""

    def test_every_case_tags_qa_generated(self):
        for case in (_case(), _case(**{"openspec-ref": "Sign-in/Happy path"}),
                     _case(**{"design-ref": "abc123/1:2 — Sign-in"})):
            self.assertIn("qa-generated", _payload(case)["tags"])

    def test_openspec_ref_adds_openspec_context(self):
        t = _payload(_case(**{"openspec-ref": "Sign-in/Happy path"}))["tags"]
        self.assertIn("openspec-context", t)
        self.assertNotIn("design-backed", t)

    def test_design_ref_adds_design_backed(self):
        t = _payload(_case(**{"design-ref": "abc123/1:2 — Sign-in"}))["tags"]
        self.assertIn("design-backed", t)
        self.assertNotIn("openspec-context", t)

    def test_both_refs_carry_both_tags(self):
        t = _payload(_case(**{"openspec-ref": "Sign-in/Happy path",
                              "design-ref": "abc123/1:2 — Sign-in"}))["tags"]
        self.assertIn("openspec-context", t)
        self.assertIn("design-backed", t)

    def test_business_only_case_carries_neither_context_tag(self):
        t = _payload(_case())["tags"]
        self.assertNotIn("openspec-context", t)
        self.assertNotIn("design-backed", t)

    def test_no_payload_emits_spec_derived(self):
        for case in (_case(), _case(**{"openspec-ref": "Sign-in/Happy path"}),
                     _case(**{"design-ref": "abc123/1:2 — Sign-in"})):
            self.assertNotIn("spec-derived", _payload(case)["tags"])

    def test_description_carries_openspec_and_design_refs(self):
        d = _payload(_case(**{"openspec-ref": "auth#Sign-in/Happy path",
                              "design-ref": "abc123/1:2 — Sign-in"}))["description"]
        self.assertIn("openspec-ref: auth#Sign-in/Happy path", d)
        self.assertIn("design-ref: abc123/1:2 — Sign-in", d)

    def test_description_omits_absent_refs(self):
        d = _payload(_case())["description"]
        self.assertNotIn("openspec-ref", d)
        self.assertNotIn("design-ref", d)


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
