import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from testops_payload import slugify, traceability_tag, case_to_payload

CASE = {
    "id": "TC-1", "title": "Happy path sign-in",
    "tags": {"type": "functional", "priority": "P1",
             "source": "scenario: Sign-in/Happy path",
             "preconditions": "a user exists", "expected": "signed in"},
    "steps": ["1. enter valid credentials", "2. submit"],
}

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

    def test_payload_shape(self):
        p = case_to_payload(CASE, story="KING-1", service="svc", capability="cap",
                            jira_base_url="https://kinoadev.atlassian.net")
        self.assertEqual(p["name"], "TC-1 · Happy path sign-in")
        self.assertEqual(p["precondition"], "a user exists")
        self.assertEqual(p["expectedResult"], "signed in")
        self.assertEqual([s["body"] for s in p["scenario"]["steps"]],
                         ["enter valid credentials", "submit"])   # numbering stripped
        self.assertEqual(p["scenario"]["steps"][0]["type"], "body")
        self.assertIn("spec-derived", p["tags"])
        self.assertIn("type-functional", p["tags"])
        self.assertIn("priority-p1", p["tags"])
        self.assertIn(traceability_tag("KING-1", "svc", "cap", CASE["tags"]["source"]), p["tags"])
        self.assertEqual(p["links"][0]["url"], "https://kinoadev.atlassian.net/browse/KING-1")

if __name__ == "__main__":
    unittest.main()
