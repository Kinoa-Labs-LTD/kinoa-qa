import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from testops_fields import resolve_custom_fields, check_field_values, VERIFIED_FIELDS

CONFIG = {"testops": {"project_name": "KINOA", "project_id": 1,
                      "custom_fields": {"story": "Template", "component": "Web", "feature": "Sign-in"}}}
EMPTY_CONFIG = {"testops": {"project_name": "KINOA", "project_id": 1}}


def _resolve(config=CONFIG, **kw):
    kw.setdefault("story_key", "KING-1")
    kw.setdefault("story_title", "Sign-in rework")
    return resolve_custom_fields(config, **kw)


class TestResolve(unittest.TestCase):
    def test_config_defaults_are_used(self):
        r = _resolve()
        self.assertEqual(r["missing"], [])
        self.assertEqual(r["fields"]["Story"], "Template")
        self.assertEqual(r["fields"]["Component"], "Web")
        self.assertEqual(r["fields"]["Feature"], "Sign-in")

    def test_flag_beats_config(self):
        r = _resolve(story_field="Flow Scope", component="In-App", feature="Deeplinks")
        self.assertEqual(r["fields"]["Story"], "Flow Scope")
        self.assertEqual(r["fields"]["Component"], "In-App")
        self.assertEqual(r["fields"]["Feature"], "Deeplinks")

    def test_suite_is_composed_from_the_story(self):
        self.assertEqual(_resolve()["fields"]["Suite"], "[KING-1] Sign-in rework")

    def test_missing_values_are_reported_not_guessed(self):
        r = _resolve(config=EMPTY_CONFIG)
        self.assertEqual(sorted(r["missing"]), ["Component", "Feature", "Story"])
        for f in ("Story", "Component", "Feature"):
            self.assertNotIn(f, r["fields"])

    def test_missing_report_names_the_flag(self):
        r = _resolve(config=EMPTY_CONFIG, story_field="Template", feature="Sign-in")
        self.assertEqual(r["missing"], ["Component"])
        self.assertIn("--component", " ".join(r["errors"]))
        self.assertIn("Component", " ".join(r["errors"]))

    def test_blank_values_count_as_missing(self):
        r = _resolve(config=EMPTY_CONFIG, story_field="  ", component="Web", feature="Sign-in")
        self.assertEqual(r["missing"], ["Story"])

    def test_missing_story_title_aborts_the_suite(self):
        r = _resolve(story_title="")
        self.assertIn("Suite", r["missing"])
        self.assertNotIn("Suite", r["fields"])

    def test_verified_fields_exclude_suite(self):
        self.assertEqual(sorted(VERIFIED_FIELDS), ["Component", "Feature", "Story"])


class TestFeatureIsAlwaysTheCallers(unittest.TestCase):
    """The Feature is the caller's `--feature` or the config default for every plan, whatever
    its scope. The resolver takes no scope, and no code path sets the `e2e scope` value."""

    def test_the_resolver_takes_no_scope(self):
        with self.assertRaises(TypeError):
            _resolve(scope="e2e")

    def test_an_explicit_feature_is_honoured_without_error(self):
        r = _resolve(feature="Deeplinks")
        self.assertEqual(r["fields"]["Feature"], "Deeplinks")
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["missing"], [])

    def test_the_config_default_is_the_feature_when_no_flag_is_passed(self):
        r = _resolve()                       # CONFIG defaults Feature to "Sign-in"
        self.assertEqual(r["fields"]["Feature"], "Sign-in")
        self.assertEqual(r["errors"], [])

    def test_the_callers_feature_is_the_value_gate_0b_checks(self):
        r = _resolve(feature="Deeplinks")
        check = check_field_values(r["fields"], {"Story": 1, "Component": 1, "Feature": 0},
                                   project_name="KINOA")
        self.assertFalse(check["ok"])
        self.assertIn("Feature", check["checked"])
        self.assertIn("Deeplinks", " ".join(check["errors"]))

    def test_no_code_path_sets_e2e_scope(self):
        import testops_fields
        self.assertFalse(hasattr(testops_fields, "E2E_FEATURE"))
        with open(testops_fields.__file__) as source:
            self.assertNotIn("e2e scope", source.read())


FIELDS = {"Suite": "[KING-1] Sign-in rework", "Story": "Template",
          "Component": "In-App", "Feature": "Sign-in"}


class TestCheck(unittest.TestCase):
    def test_all_values_found_is_accepted(self):
        r = check_field_values(FIELDS, {"Story": 3, "Component": 1, "Feature": 12}, project_name="KINOA")
        self.assertTrue(r["ok"])
        self.assertEqual(r["errors"], [])

    def test_a_list_of_hits_counts_as_proof(self):
        r = check_field_values(FIELDS, {"Story": [{"id": 1}], "Component": [{"id": 2}], "Feature": [{"id": 3}]},
                               project_name="KINOA")
        self.assertTrue(r["ok"])

    def test_zero_hits_is_rejected_naming_field_and_value(self):
        r = check_field_values(FIELDS, {"Story": 2, "Component": 0, "Feature": 1}, project_name="KINOA")
        self.assertFalse(r["ok"])
        self.assertEqual(len(r["errors"]), 1)
        msg = r["errors"][0]
        self.assertIn("Component", msg)
        self.assertIn("In-App", msg)
        self.assertIn("KINOA", msg)
        self.assertIn("no existing test case", msg)
        self.assertIn("--allow-unverified-fields", msg)
        self.assertNotIn("does not exist", msg)

    def test_an_empty_list_is_rejected(self):
        r = check_field_values(FIELDS, {"Story": [], "Component": [1], "Feature": [1]}, project_name="KINOA")
        self.assertFalse(r["ok"])
        self.assertIn("Template", r["errors"][0])

    def test_every_bad_value_is_reported_not_just_the_first(self):
        r = check_field_values(FIELDS, {"Story": 0, "Component": 0, "Feature": 0}, project_name="KINOA")
        self.assertEqual(len(r["errors"]), 3)

    def test_suite_is_never_looked_up(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 1, "Feature": 1}, project_name="KINOA")
        self.assertTrue(r["ok"])
        self.assertEqual(sorted(r["checked"]), ["Component", "Feature", "Story"])

    def test_a_missing_lookup_result_is_rejected_not_assumed(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 1}, project_name="KINOA")
        self.assertFalse(r["ok"])
        self.assertIn("Feature", r["errors"][0])

    def test_a_verified_run_records_no_warning(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 1, "Feature": 1}, project_name="KINOA")
        self.assertEqual(r["warnings"], [])


class TestAllowUnverified(unittest.TestCase):
    """The by-value lookup can only prove a value is USED, never that it exists. The override
    keeps the push going for a value Allure has but no case uses, and the skipped check is
    returned as a warning for the caller to print rather than swallowed."""

    def test_override_accepts_an_unverified_value(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 0, "Feature": 1},
                               project_name="KINOA", allow_unverified=True)
        self.assertTrue(r["ok"])
        self.assertEqual(r["errors"], [])

    def test_override_warns_naming_the_field_and_value(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 0, "Feature": 1},
                               project_name="KINOA", allow_unverified=True)
        self.assertEqual(len(r["warnings"]), 1)
        msg = r["warnings"][0]
        self.assertIn("Component", msg)
        self.assertIn("In-App", msg)
        self.assertIn("KINOA", msg)

    def test_override_warns_for_every_unverified_value(self):
        r = check_field_values(FIELDS, {"Story": 0, "Component": 0, "Feature": 0},
                               project_name="KINOA", allow_unverified=True)
        self.assertTrue(r["ok"])
        self.assertEqual(len(r["warnings"]), 3)

    def test_override_still_never_looks_up_suite(self):
        r = check_field_values(FIELDS, {}, project_name="KINOA", allow_unverified=True)
        self.assertEqual(sorted(r["checked"]), ["Component", "Feature", "Story"])
        self.assertNotIn("Suite", " ".join(r["warnings"]))

    def test_default_is_still_an_abort(self):
        r = check_field_values(FIELDS, {"Story": 1, "Component": 0, "Feature": 1},
                               project_name="KINOA")
        self.assertFalse(r["ok"])
        self.assertEqual(r["warnings"], [])


if __name__ == "__main__":
    unittest.main()
