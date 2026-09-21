import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import parse_cases
from testops_payload import (slugify, case_to_payload, target_marker, parse_target,
                             STATUS, E2E_STATUS)

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

    def test_payload_shape(self):
        p = _payload(CASE)
        self.assertEqual(p["name"], "Happy path sign-in")          # no TC-n prefix
        self.assertNotIn("TC-", p["name"])
        self.assertEqual(p["description"],
                         "Verify an admin with valid credentials reaches the dashboard."
                         "\nTarget: service=svc; capability=cap; scope=story")
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

class TestTagVocabulary(unittest.TestCase):
    """The emitted vocabulary is exactly one tag: qa-generated.
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
        # purpose + one provenance line + the target marker
        self.assertEqual(len(d.splitlines()), 3)
        self.assertEqual(d.splitlines()[-1],
                         "Target: service=svc; capability=cap; scope=story")

    def test_description_carries_image_provenance(self):
        d = _payload(_case(**{"image-ref": "10001 — hero.png"}))["description"]
        self.assertIn("image-ref: 10001 — hero.png", d)

    def test_description_carries_all_three_refs_in_order(self):
        d = _payload(_case(**{"openspec-ref": "auth#Sign-in/Happy path",
                              "design-ref": "abc123/1:2 — Sign-in",
                              "image-ref": "10001 — hero.png"}))["description"]
        provenance_line = d.splitlines()[1]
        self.assertEqual(
            provenance_line,
            "Provenance: openspec-ref: auth#Sign-in/Happy path; "
            "design-ref: abc123/1:2 — Sign-in; image-ref: 10001 — hero.png")

    def test_description_omits_absent_refs(self):
        d = _payload(_case())["description"]
        self.assertEqual(d, "Verify sign-in works.\n"
                            "Target: service=svc; capability=cap; scope=story")
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


class TestDerivedKeyIsGone(unittest.TestCase):
    """KING-22861: identity is the assigned Allure case id, not a derived hash. The
    `tp-` tag and `traceability_tag` are removed; `qa-generated` stays as the fleet-level
    handle and KING-22795's retired-taxonomy pin still holds."""

    def test_traceability_tag_is_no_longer_importable(self):
        import testops_payload
        self.assertFalse(hasattr(testops_payload, "traceability_tag"),
                         "traceability_tag must be gone: identity is the assigned allure-id")

    def test_tags_are_exactly_qa_generated(self):
        for case in (_case(), _case(**{"openspec-ref": "Sign-in/Happy path"}),
                     _case(**{"design-ref": "abc123/1:2 — Sign-in"})):
            self.assertEqual(_payload(case)["tags"], ["qa-generated"])


class TestTargetMarker(unittest.TestCase):
    """The description carries a machine-read target marker so reconciliation can narrow
    `issue = "<STORY-KEY>"` — which returns every target's cases — down to this plan's
    service and capability. The marker must round-trip through `parse_target`."""

    def test_marker_is_the_last_description_line(self):
        d = _payload(CASE)["description"]
        self.assertEqual(d.splitlines()[-1],
                         "Target: service=svc; capability=cap; scope=story")

    def test_reconciliation_parses_the_target_back_out(self):
        self.assertEqual(parse_target(_payload(CASE)["description"]),
                         ("svc", "cap", "story"))

    def test_marker_round_trips_for_multiword_targets(self):
        c = case_to_payload(CASE, story="KING-1", service="In App Templates",
                            capability="Export / Import", custom_fields=FIELDS)
        self.assertEqual(parse_target(c["description"]),
                         ("in-app-templates", "export-import", "story"))
        self.assertEqual(target_marker("In App Templates", "Export / Import"),
                         "Target: service=in-app-templates; capability=export-import; "
                         "scope=story")

    def test_parse_target_returns_none_when_there_is_no_marker(self):
        self.assertIsNone(parse_target("Verify sign-in works."))
        self.assertIsNone(parse_target(""))
        self.assertIsNone(parse_target(None))

    def test_two_targets_of_one_story_are_distinguishable(self):
        a = _payload(CASE)["description"]
        b = case_to_payload(CASE, story="KING-1", service="svc", capability="other",
                            custom_fields=FIELDS)["description"]
        self.assertNotEqual(parse_target(a), parse_target(b))

    def test_every_target_the_plugin_can_be_invoked_with_round_trips(self):
        """A run with no `--target`, or with only one half of it, must still emit a marker
        `parse_target` can read back. Empty is a value, not an absence."""
        for service, capability in (("", ""), ("svc", ""), ("", "cap"), ("svc", "cap"),
                                    ("In App Templates", ""), ("none", "none")):
            with self.subTest(target=(service, capability)):
                marker = target_marker(service, capability)
                self.assertEqual(parse_target("Purpose line.\n" + marker),
                                 (slugify(service), slugify(capability), "story"))

    def test_no_target_run_emits_a_parseable_empty_marker(self):
        self.assertEqual(target_marker("", ""),
                         "Target: service=; capability=; scope=story")
        self.assertEqual(parse_target(target_marker(None, None)), ("", "", "story"))

    def test_targets_that_differ_compare_unequal_even_when_half_empty(self):
        pairs = (("", ""), ("svc", ""), ("", "cap"), ("svc", "cap"), ("none", "none"))
        parsed = [parse_target(target_marker(s, c)) for s, c in pairs]
        self.assertEqual(len(set(parsed)), len(pairs))

    def test_marker_survives_a_case_with_no_purpose(self):
        c = dict(CASE, tags=dict(CASE["tags"], purpose=""))
        self.assertEqual(parse_target(_payload(c)["description"]), ("svc", "cap", "story"))


def _scoped(case, scope):
    return case_to_payload(case, story="KING-1", service="svc", capability="cap",
                           custom_fields=FIELDS, scope=scope)


def _without_marker(description):
    """The description minus its `Target:` marker line. The marker's own fields are pinned by
    the marker's own tests, so comparing the two scopes here stays about the prose."""
    return "\n".join(l for l in description.split("\n") if not l.startswith("Target:"))


MULTI_EXPECTED_CASE = {
    "id": "TC-2", "title": "Publish flow",
    "tags": {"type": "functional", "priority": "P1", "source": "ac: AC-1",
             "purpose": "Verify publishing reaches every channel.",
             "preconditions": "a draft exists", "expected": "published"},
    "steps": [{"action": "publish", "expected": "the banner shows",
               "extra_expected": ["the WS event arrives", "the InBox row appears"]}],
}


class TestScopeChangesExactlyTwoThings(unittest.TestCase):
    """The test scope changes the status and nothing else in the payload. Everything a case
    carries besides `status` — and besides the marker, which narrows reconciliation — must be
    byte-identical under both scopes, or an e2e run would silently reshape its cases."""

    def test_e2e_scope_is_in_review(self):
        self.assertEqual(_scoped(CASE, "e2e")["status"], "Review")

    def test_story_scope_and_default_are_draft(self):
        for scope in ("story", None):
            self.assertEqual(_scoped(CASE, scope)["status"], "Draft")
        self.assertEqual(_payload(CASE)["status"], "Draft")

    def test_only_the_status_and_the_marker_differ_between_scopes(self):
        story, e2e = _scoped(CASE, "story"), _scoped(CASE, "e2e")
        self.assertNotEqual(story["status"], e2e["status"])
        self.assertEqual(set(story), set(e2e))
        for key in story:
            if key == "status":
                continue
            if key == "description":
                self.assertEqual(_without_marker(story[key]), _without_marker(e2e[key]))
                continue
            self.assertEqual(story[key], e2e[key], key)

    def test_the_named_fields_are_identical_field_by_field(self):
        story, e2e = _scoped(CASE, "story"), _scoped(CASE, "e2e")
        for payload in (story, e2e):
            self.assertEqual(payload["customFields"],
                             [{"name": "Suite", "value": "[KING-1] Admin sign-in"},
                              {"name": "Story", "value": "Template"},
                              {"name": "Component", "value": "Game-Settings"},
                              {"name": "Feature", "value": "In-Apps"}])
            self.assertEqual(payload["issues"], [{"name": "Kinoa-Allure", "value": "KING-1"}])
            self.assertEqual(payload["tags"], ["qa-generated"])
        # Outside the loop: inside it the first pass compared `story` with itself, so that
        # half of the assertion could not fail.
        self.assertEqual(e2e["scenario"], story["scenario"])

    def test_a_step_emits_one_expected_block_per_expected_result_in_order(self):
        steps = _scoped(MULTI_EXPECTED_CASE, "e2e")["scenario"]["steps"]
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["expectedResultSteps"],
                         [{"type": "expected_body", "body": "the banner shows"},
                          {"type": "expected_body", "body": "the WS event arrives"},
                          {"type": "expected_body", "body": "the InBox row appears"}])


class TestStoryLinkIsLoadBearing(unittest.TestCase):
    """`issues` is the only way to find a case whose assigned id was lost, so a payload
    must never be emitted with a blank or missing Story link — such a case is unfindable."""

    def test_blank_story_raises(self):
        for story in ("", "   ", None):
            with self.assertRaises(ValueError):
                case_to_payload(CASE, story=story, service="svc", capability="cap",
                                custom_fields=FIELDS)

    def test_issues_is_never_emitted_blank(self):
        issues = _payload(CASE)["issues"]
        self.assertEqual(issues, [{"name": "Kinoa-Allure", "value": "KING-1"}])
        self.assertTrue(all(i["value"].strip() for i in issues))


# What every case written before this ticket carries: the two-field marker KING-22861 shipped.
LEGACY_MARKER = "Target: service=in-app-templates; capability=export-import"


class TestMarkerCarriesTheScope(unittest.TestCase):
    """The marker is reconciliation's only narrowing key, so it must carry the test scope
    too: without it an e2e run and a Story run of one Story and target claim each other's
    cases. A marker written before this ticket has no scope and must report it as absent."""

    def test_marker_emits_the_scope_field_last(self):
        self.assertEqual(target_marker("svc", "cap", "e2e"),
                         "Target: service=svc; capability=cap; scope=e2e")
        self.assertEqual(target_marker("svc", "cap", "story"),
                         "Target: service=svc; capability=cap; scope=story")

    def test_absent_scope_is_written_as_story(self):
        self.assertEqual(target_marker("svc", "cap"),
                         "Target: service=svc; capability=cap; scope=story")

    def test_marker_round_trips_all_three_fields(self):
        for scope in ("e2e", "story"):
            with self.subTest(scope=scope):
                marker = target_marker("In App Templates", "Export / Import", scope)
                self.assertEqual(parse_target("Purpose.\n" + marker),
                                 ("in-app-templates", "export-import", scope))

    def test_payload_marker_carries_the_payload_scope(self):
        self.assertEqual(parse_target(_scoped(CASE, "e2e")["description"]),
                         ("svc", "cap", "e2e"))
        self.assertEqual(parse_target(_scoped(CASE, "story")["description"]),
                         ("svc", "cap", "story"))
        self.assertEqual(parse_target(_scoped(CASE, None)["description"]),
                         ("svc", "cap", "story"))

    def test_the_two_scopes_of_one_target_compare_unequal(self):
        e2e = parse_target(_scoped(CASE, "e2e")["description"])
        story = parse_target(_scoped(CASE, "story")["description"])
        self.assertNotEqual(e2e, story)
        self.assertEqual(e2e[:2], story[:2])

    def test_a_legacy_two_field_marker_still_parses_with_the_scope_absent(self):
        self.assertEqual(parse_target("Verify export works.\n" + LEGACY_MARKER),
                         ("in-app-templates", "export-import", None))

    def test_a_legacy_marker_scope_is_absent_not_guessed_as_story(self):
        self.assertIsNone(parse_target(LEGACY_MARKER)[2])
        self.assertNotEqual(parse_target(LEGACY_MARKER),
                            parse_target(target_marker("in-app-templates",
                                                       "export-import", "story")))


class TestTheFirstTwoNarrowingFieldsAreUntouched(unittest.TestCase):
    """Adding a third narrowing field must not weaken what KING-22861 shipped: the Story
    link, the `qa-generated` tag and the service/capability halves of the marker behave
    exactly as they did, for a three-field marker and for a legacy two-field one alike."""

    def test_the_story_link_is_unchanged_in_both_scopes(self):
        for scope in ("e2e", "story", None):
            with self.subTest(scope=scope):
                self.assertEqual(_scoped(CASE, scope)["issues"],
                                 [{"name": "Kinoa-Allure", "value": "KING-1"}])

    def test_qa_generated_is_still_the_only_tag_in_both_scopes(self):
        for scope in ("e2e", "story", None):
            with self.subTest(scope=scope):
                self.assertEqual(_scoped(CASE, scope)["tags"], ["qa-generated"])

    def test_the_halves_still_slugify_and_survive_being_empty(self):
        for service, capability in (("", ""), ("svc", ""), ("", "cap"),
                                    ("In App Templates", "Export / Import")):
            with self.subTest(target=(service, capability)):
                parsed = parse_target(target_marker(service, capability, "e2e"))
                self.assertEqual(parsed[:2], (slugify(service), slugify(capability)))

    def test_two_targets_of_one_scope_still_compare_unequal(self):
        a = parse_target(target_marker("svc", "cap", "e2e"))
        b = parse_target(target_marker("svc", "other", "e2e"))
        self.assertNotEqual(a, b)

    def test_a_legacy_markers_halves_read_exactly_as_before(self):
        self.assertEqual(parse_target(LEGACY_MARKER)[:2],
                         ("in-app-templates", "export-import"))
        self.assertIsNone(parse_target("Verify sign-in works."))
        self.assertIsNone(parse_target(""))
        self.assertIsNone(parse_target(None))



class ScopeNormalisationTest(unittest.TestCase):
    """`target_marker` slugifies the scope, so comparing the raw string let a marker say
    `scope=e2e` while the status stayed `Draft` — a case reconciliation would later claim
    as e2e with Story-scoped field values. Gate 0a rejects such a scope, so this is the
    second line of defence, not the first."""

    CASE = {"id": "TC-1", "title": "A", "tags": {"type": "functional", "priority": "high"},
            "steps": [{"action": "do", "expected": ["ok"]}], "preconditions": []}
    FIELDS = {"Suite": "[KING-1] T", "Story": "S", "Component": "C", "Feature": "F"}

    def _payload(self, scope):
        return case_to_payload(self.CASE, story="KING-1", service="s", capability="c",
                               custom_fields=dict(self.FIELDS), scope=scope)

    def test_an_odd_cased_scope_agrees_with_its_marker(self):
        for scope in ("E2E", " e2e ", "E2e"):
            with self.subTest(scope=scope):
                payload = self._payload(scope)
                self.assertEqual(payload["status"], E2E_STATUS)
                self.assertIn("scope=e2e", payload["description"].splitlines()[-1])

    def test_a_story_scope_is_unaffected(self):
        for scope in ("story", "STORY", None):
            with self.subTest(scope=scope):
                payload = self._payload(scope)
                self.assertEqual(payload["status"], STATUS)
                self.assertIn("scope=story", payload["description"].splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
