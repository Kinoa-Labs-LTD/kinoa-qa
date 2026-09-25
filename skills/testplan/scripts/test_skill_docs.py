# test_skill_docs.py
"""The skill's markdown is its implementation (CLAUDE.md): a reference that misdescribes the
validator is a defect. These tests keep the retired taxonomy vocabulary out of the docs an
agent reads, and keep the evals and their fixtures loadable and consistent with the scopes
the validator accepts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json, re, unittest

from plan_parser import SCOPES, parse_cases, parse_header
from testops_payload import case_to_payload

# repo root: skills/testplan/scripts/ -> ../../..
SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ROOT = os.path.abspath(os.path.join(SKILL_DIR, "..", ".."))
EVALS_DIR = os.path.join(SKILL_DIR, "evals")
FIXTURES_DIR = os.path.join(EVALS_DIR, "fixtures")

# Fixtures that carry an invalid `scope:` on purpose, so an eval can watch `scope-valid` FAIL.
# Listed by path relative to FIXTURES_DIR; each one must really be invalid (tested below).
INVALID_SCOPE_FIXTURES = ("e2e-scope/test-plan-unknown-scope.md",)

# Retired vocabulary: (label, pattern). Plain substrings, matched case-sensitively except
# the Feature value, which has been written both ways.
STALE = (
    ("e2e scope", re.compile(r"e2e scope", re.I)),
    ('or "story"', re.compile(r'or "story"')),
    ("scope: story", re.compile(r"scope: story")),
    ("scope=story", re.compile(r"scope=story")),
    ("type: e2e", re.compile(r"type: e2e")),
    ("six case types", re.compile(r"six case types", re.I)),
    ("SCOPE CHANGED", re.compile(r"SCOPE CHANGED")),
    ("--scope", re.compile(r"--scope\b")),
)

# A retired value may still be named where the line says it is rejected — and the failure
# word must follow the value closely (at most two words between, after an optional closing
# backtick), so an unrelated "fails" later on the line does not excuse it.
_SAYS_IT_FAILS = re.compile(
    r"`?\s*(?:\S+\s+){0,2}?(?:\bFAILs?\b|\bfails?\b|\bis retired\b|\bis rejected\b)")
_MAY_BE_NAMED_AS_FAILING = {"type: e2e", "scope: story"}

# `--scope` survives only in SKILL.md's stop rule and error row, which say the flag is gone.
_SCOPE_FLAG_GONE = "the flag is gone"


def _named_as_failing(pattern, line):
    """True when every occurrence of the retired value on `line` is directly followed by
    the word that says it fails."""
    return all(_SAYS_IT_FAILS.match(line, m.end()) for m in pattern.finditer(line))


def stale_hits(doc_name, text):
    """Every line of `text` that uses retired vocabulary, as [(line number, label, line)].

    `doc_name` is the file's basename; it decides the one per-file exception. Pure so the
    checker is proven on synthetic stale text, not only on a tree that happens to be clean.
    """
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for label, pattern in STALE:
            if not pattern.search(line):
                continue
            if label in _MAY_BE_NAMED_AS_FAILING and _named_as_failing(pattern, line):
                continue
            if label == "--scope" and doc_name == "SKILL.md" and _SCOPE_FLAG_GONE in line:
                continue
            hits.append((number, label, line.strip()))
    return hits


def agent_docs():
    """SKILL.md, the README and every reference file: what an agent or a QA engineer reads."""
    paths = [os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(ROOT, "README.md")]
    paths += sorted(glob.glob(os.path.join(SKILL_DIR, "references", "**", "*"), recursive=True))
    return [p for p in paths if os.path.isfile(p)]


class StaleHitsChecker(unittest.TestCase):
    def test_catches_each_retired_term(self):
        for text in ('Feature = "e2e scope"', 'scope = header or "story"', "scope: story",
                     "Target: service=a; capability=b; scope=story", "- type: e2e",
                     "one of the six case types", "report SCOPE CHANGED at the gate",
                     "pass --scope e2e"):
            with self.subTest(text=text):
                self.assertEqual(1, len(stale_hits("generation.md", text)), text)

    def test_catches_the_feature_value_whatever_its_case(self):
        self.assertTrue(stale_hits("README.md", "Feature `E2E scope` is set for you"))

    def test_names_the_line_number_and_the_term(self):
        self.assertEqual([(2, "--scope", "use --scope story")],
                         stale_hits("README.md", "fine line\nuse --scope story\n"))

    def test_a_retired_value_named_as_failing_is_allowed(self):
        self.assertEqual([], stale_hits("test-plan-format.md",
                                        "`type: e2e` FAILs `type-valid`, pointing at the header"))
        self.assertEqual([], stale_hits("test-plan-format.md",
                                        "`scope: story` is retired and fails `scope-valid`"))

    def test_a_failure_word_elsewhere_on_the_line_does_not_excuse_the_value(self):
        for text in ("`scope: story` is fine; nothing fails",
                     "use `type: e2e` for journeys, since the smoke format fails them",
                     "`scope: story` FAILs `scope-valid`, but `scope: story` is fine here"):
            with self.subTest(text=text):
                self.assertTrue(stale_hits("test-plan-format.md", text), text)

    def test_the_fail_exception_does_not_cover_other_terms(self):
        self.assertTrue(stale_hits("testops-sync.md", 'Feature "e2e scope" fails nothing'))
        self.assertTrue(stale_hits("SKILL.md", "--scope FAILs"))

    def test_scope_flag_is_allowed_only_in_skill_md_where_it_is_gone(self):
        line = "If the caller passes `--scope`, stop: the flag is gone."
        self.assertEqual([], stale_hits("SKILL.md", line))
        self.assertTrue(stale_hits("README.md", line))
        self.assertTrue(stale_hits("SKILL.md", "pass `--scope e2e` for a journey"))


class NoStaleVocabulary(unittest.TestCase):
    def test_the_docs_list_is_not_empty(self):
        names = [os.path.basename(p) for p in agent_docs()]
        for expected in ("SKILL.md", "README.md", "test-plan-format.md", "generation.md",
                         "testops-sync.md"):
            self.assertIn(expected, names)

    def test_no_doc_uses_retired_vocabulary(self):
        for path in agent_docs():
            with open(path, encoding="utf-8") as f:
                hits = stale_hits(os.path.basename(path), f.read())
            with self.subTest(doc=os.path.relpath(path, ROOT)):
                self.assertEqual([], hits, "retired vocabulary in {}: {}".format(
                    os.path.relpath(path, ROOT), hits))


class EvalsLoad(unittest.TestCase):
    def test_evals_json_loads_with_unique_ids(self):
        with open(os.path.join(EVALS_DIR, "evals.json"), encoding="utf-8") as f:
            data = json.load(f)
        ids = [e["id"] for e in data["evals"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_fixture_json_loads(self):
        paths = glob.glob(os.path.join(FIXTURES_DIR, "**", "*.json"), recursive=True)
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=os.path.relpath(path, FIXTURES_DIR)):
                with open(path, encoding="utf-8") as f:
                    json.load(f)

    def test_every_file_an_eval_names_exists(self):
        with open(os.path.join(EVALS_DIR, "evals.json"), encoding="utf-8") as f:
            data = json.load(f)
        for e in data["evals"]:
            for rel in e.get("files", []):
                with self.subTest(eval=e["id"], file=rel):
                    self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)


class FixtureScopes(unittest.TestCase):
    def _plan_fixtures(self):
        for path in sorted(glob.glob(os.path.join(FIXTURES_DIR, "**", "*.md"), recursive=True)):
            with open(path, encoding="utf-8") as f:
                yield os.path.relpath(path, FIXTURES_DIR).replace(os.sep, "/"), f.read()

    def test_every_plan_fixture_scope_is_smoke_or_e2e(self):
        for rel, text in self._plan_fixtures():
            scope = parse_header(text).get("scope")
            if scope is None or rel in INVALID_SCOPE_FIXTURES:
                continue
            with self.subTest(fixture=rel):
                self.assertIn(scope, SCOPES)

    def test_each_listed_invalid_fixture_is_really_invalid(self):
        texts = dict(self._plan_fixtures())
        for rel in INVALID_SCOPE_FIXTURES:
            with self.subTest(fixture=rel):
                self.assertIn(rel, texts)
                scope = parse_header(texts[rel]).get("scope")
                self.assertIsNotNone(scope)
                self.assertNotIn(scope, SCOPES)


class ReferenceShapePayload(unittest.TestCase):
    """The reference-shape fixture is a checked payload, not the builder's own output; this
    builds it from the fixture plan with the inputs the reference-shape eval names and
    compares key by key, so the builder and the fixture cannot drift apart unnoticed."""

    CUSTOM_FIELDS = {
        "Suite": "[KING-18454] As an operator I want to have Eligibility checkboxes for "
                 "Milestones in-app",
        "Story": "Template", "Component": "In-Apps", "Feature": "Milestones"}

    def test_built_payload_equals_the_fixture_key_by_key(self):
        shape = os.path.join(FIXTURES_DIR, "reference-shape")
        with open(os.path.join(shape, "test-plan.md"), encoding="utf-8") as f:
            cases = parse_cases(f.read())
        with open(os.path.join(shape, "expected-payload.json"), encoding="utf-8") as f:
            expected = json.load(f)
        self.assertEqual(1, len(cases))
        built = case_to_payload(cases[0], story="KING-18454", service="kinoa-in-app",
                                capability="milestones-eligibility",
                                custom_fields=self.CUSTOM_FIELDS)
        self.assertEqual(sorted(expected), sorted(built))
        for key in expected:
            with self.subTest(key=key):
                self.assertEqual(expected[key], built[key])


if __name__ == "__main__":
    unittest.main()
