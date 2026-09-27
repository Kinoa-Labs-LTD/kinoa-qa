# test_skill_docs.py
"""The skill's markdown is its implementation (CLAUDE.md): a reference that misdescribes the
validator is a defect. These tests keep the retired taxonomy vocabulary out of the docs an
agent reads, keep every fenced plugin command runnable and every kinoa-test-automation-only
command or path labelled as such, and keep the evals and their fixtures loadable and
consistent with the scopes the validator accepts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json, re, shutil, tempfile, unittest

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

TESTPLAN_SKILL = "skills/testplan/SKILL.md"

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

# `--scope` survives only in testplan's SKILL.md stop rule and error row, which say the flag is gone.
_SCOPE_FLAG_GONE = "the flag is gone"


def _named_as_failing(pattern, line):
    """True when every occurrence of the retired value on `line` is directly followed by
    the word that says it fails."""
    return all(_SAYS_IT_FAILS.match(line, m.end()) for m in pattern.finditer(line))


def stale_hits(doc_path, text):
    """Every line of `text` that uses retired vocabulary, as [(line number, label, line)].

    `doc_path` is the file's path from the repo root; it decides the one per-file exception.
    Pure so the checker is proven on synthetic stale text, not only on a tree that happens to
    be clean.
    """
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for label, pattern in STALE:
            if not pattern.search(line):
                continue
            if label in _MAY_BE_NAMED_AS_FAILING and _named_as_failing(pattern, line):
                continue
            if label == "--scope" and doc_path == TESTPLAN_SKILL and _SCOPE_FLAG_GONE in line:
                continue
            hits.append((number, label, line.strip()))
    return hits


def rel(path):
    """`path` relative to the repo root, with forward slashes."""
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def plugin_skill_docs():
    """Every skills/*/SKILL.md and every file under skills/shared/."""
    paths = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
    paths += sorted(glob.glob(os.path.join(ROOT, "skills", "shared", "**", "*"), recursive=True))
    return [p for p in paths if os.path.isfile(p)]


_FENCE = re.compile(r"^\s*(```|~~~)")
_PLUGIN_COMMAND = re.compile(r"\b(?:node|python3)\s+<plugin>/(\S+)")
_MAIN_BLOCK = 'if __name__ == "__main__":'
_REPO_COMMAND = re.compile(r"^(?:npx |git |node scripts/)")
REPO = "kinoa-test-automation"


def fenced_lines(text):
    """Every line inside a fenced block, as [(line number, line, line number of its opening fence)]."""
    out, opening = [], None
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            opening = number if opening is None else None
        elif opening is not None:
            out.append((number, line, opening))
    return out


def missing_command_targets(text, root):
    """Every fenced `node|python3 <plugin>/<path>` whose <path> is not a file under `root`, or is a
    `.py` without a `__main__` block, as [(line number, path, reason)]."""
    hits = []
    for number, line, _ in fenced_lines(text):
        for m in _PLUGIN_COMMAND.finditer(line):
            target = m.group(1)
            path = os.path.join(root, *target.split("/"))
            if not os.path.isfile(path):
                hits.append((number, target, "no such file"))
                continue
            if target.endswith(".py"):
                with open(path, encoding="utf-8") as f:
                    if _MAIN_BLOCK not in f.read():
                        hits.append((number, target, "no __main__ block"))
    return hits


def unlabelled_repo_commands(text):
    """Every fenced `npx `/`git `/`node scripts/` line with no `kinoa-test-automation` on the three
    non-blank lines above its opening fence, as [(line number, line)]."""
    lines = text.splitlines()
    hits = []
    for number, line, opening in fenced_lines(text):
        if not _REPO_COMMAND.match(line.strip()):
            continue
        above = [l for l in lines[:opening - 1] if l.strip()][-3:]
        if not any(REPO in l for l in above):
            hits.append((number, line.strip()))
    return hits


def repo_skill_path_hits(text):
    """Every line naming a `.claude/skills/` path without naming kinoa-test-automation, as
    [(line number, line)]."""
    return [(number, line.strip()) for number, line in enumerate(text.splitlines(), 1)
            if ".claude/skills/" in line and REPO not in line]


def agent_docs():
    """Every skill's SKILL.md, the shared files, the README and testplan's reference files: what
    an agent or a QA engineer reads."""
    paths = plugin_skill_docs() + [os.path.join(ROOT, "README.md")]
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
        self.assertTrue(stale_hits(TESTPLAN_SKILL, "--scope FAILs"))

    def test_scope_flag_is_allowed_only_in_testplan_skill_md_where_it_is_gone(self):
        line = "If the caller passes `--scope`, stop: the flag is gone."
        self.assertEqual([], stale_hits(TESTPLAN_SKILL, line))
        self.assertTrue(stale_hits("README.md", line))
        self.assertTrue(stale_hits("skills/smoke-run/SKILL.md", line))
        self.assertTrue(stale_hits("SKILL.md", line))
        self.assertTrue(stale_hits(TESTPLAN_SKILL, "pass `--scope e2e` for a journey"))


NEW_SKILL_DOCS = ("skills/smoke-plan/SKILL.md", "skills/smoke-run/SKILL.md",
                  "skills/shared/step-outcome-contract.md")


def assert_scans_every_skill(case, paths):
    """`paths` holds testplan's and the smoke skills' SKILL.md, the shared contract, and every
    skills/*/SKILL.md on disk."""
    scanned = {rel(p) for p in paths}
    on_disk = {rel(p) for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))}
    for expected in sorted({TESTPLAN_SKILL} | set(NEW_SKILL_DOCS) | on_disk):
        case.assertIn(expected, scanned)


class NoStaleVocabulary(unittest.TestCase):
    def test_the_docs_list_is_not_empty(self):
        names = [os.path.basename(p) for p in agent_docs()]
        for expected in ("SKILL.md", "README.md", "test-plan-format.md", "generation.md",
                         "testops-sync.md"):
            self.assertIn(expected, names)

    def test_every_skill_and_shared_file_is_scanned(self):
        assert_scans_every_skill(self, agent_docs())

    def test_no_doc_uses_retired_vocabulary(self):
        for path in agent_docs():
            with open(path, encoding="utf-8") as f:
                hits = stale_hits(rel(path), f.read())
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


class FencedCommandsExistChecker(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        scripts = os.path.join(self.root, "skills", "x", "scripts")
        os.makedirs(scripts)
        for name, body in (("ok.py", 'def main():\n    pass\n\nif __name__ == "__main__":\n    main()\n'),
                           ("nomain.py", "def main():\n    pass\n"),
                           ("tool.mjs", "console.log(1);\n")):
            with open(os.path.join(scripts, name), "w", encoding="utf-8") as f:
                f.write(body)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_names_only_a_fenced_command_whose_file_is_missing(self):
        text = ("Run `node <plugin>/skills/x/scripts/gone.mjs` later.\n"
                "```bash\n"
                "node <plugin>/skills/x/scripts/tool.mjs run.json --dry-run\n"
                "python3 <plugin>/skills/x/scripts/ok.py --json\n"
                "node <plugin>/skills/x/scripts/gone.mjs run.json\n"
                "```\n")
        hits = missing_command_targets(text, self.root)
        self.assertEqual([5], [h[0] for h in hits], hits)
        self.assertEqual("skills/x/scripts/gone.mjs", hits[0][1])

    def test_a_py_target_without_a_main_block_is_caught(self):
        text = "```\npython3 <plugin>/skills/x/scripts/nomain.py <plan>\n```\n"
        hits = missing_command_targets(text, self.root)
        self.assertEqual([2], [h[0] for h in hits], hits)

    def test_an_indented_fence_under_a_list_item_is_checked(self):
        text = "1. Post it:\n\n   ```bash\n   node <plugin>/skills/x/scripts/gone.mjs a\n   ```\n"
        self.assertEqual([4], [h[0] for h in missing_command_targets(text, self.root)])


class FencedCommandsExist(unittest.TestCase):
    def test_every_fenced_plugin_command_names_a_runnable_file(self):
        docs = agent_docs()
        assert_scans_every_skill(self, docs)
        for path in docs:
            with open(path, encoding="utf-8") as f:
                hits = missing_command_targets(f.read(), ROOT)
            with self.subTest(doc=rel(path)):
                self.assertEqual([], hits, "{}: {}".format(rel(path), hits))


class RepoOnlyCommandsChecker(unittest.TestCase):
    def test_an_unlabelled_repo_command_is_caught(self):
        for command in ("npx eslint tests/smoke/x.smoke.ts", "git fetch origin develop",
                        "node scripts/rebalanceShards.mjs --check"):
            text = ("Mention git fetch in prose.\n\n```bash\n"
                    "node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json\n"
                    + command + "\n```\n")
            with self.subTest(command=command):
                self.assertEqual([(5, command)], unlabelled_repo_commands(text))

    def test_the_label_must_be_on_one_of_the_three_non_blank_lines_above_the_fence(self):
        inside = "Inside kinoa-test-automation only:\n\none\n\ntwo\n```bash\nnpx eslint x\n```\n"
        self.assertEqual([], unlabelled_repo_commands(inside))
        too_far = "Inside kinoa-test-automation only:\none\ntwo\nthree\n```bash\nnpx eslint x\n```\n"
        self.assertEqual([(6, "npx eslint x")], unlabelled_repo_commands(too_far))


class RepoOnlyCommandsAreLabelled(unittest.TestCase):
    def test_every_repo_command_in_the_docs_names_kinoa_test_automation(self):
        docs = agent_docs()
        assert_scans_every_skill(self, docs)
        for path in docs:
            with open(path, encoding="utf-8") as f:
                hits = unlabelled_repo_commands(f.read())
            with self.subTest(doc=rel(path)):
                self.assertEqual([], hits, "{}: {}".format(rel(path), hits))


class NoRepoSkillPathsChecker(unittest.TestCase):
    def test_an_unguarded_repo_skill_path_is_caught_and_a_named_one_allowed(self):
        text = ("See `.claude/skills/page-object-author/SKILL.md` for locators.\n"
                "The kinoa-test-automation skill `.claude/skills/testops-to-playwright/SKILL.md`.\n"
                "The plugin skill `skills/smoke-run/SKILL.md`.\n")
        self.assertEqual([(1, "See `.claude/skills/page-object-author/SKILL.md` for locators.")],
                         repo_skill_path_hits(text))


class NoRepoSkillPaths(unittest.TestCase):
    def test_no_plugin_skill_doc_names_an_unguarded_repo_skill_path(self):
        docs = plugin_skill_docs()
        assert_scans_every_skill(self, docs)
        for path in docs:
            with open(path, encoding="utf-8") as f:
                hits = repo_skill_path_hits(f.read())
            with self.subTest(doc=rel(path)):
                self.assertEqual([], hits, "{}: {}".format(rel(path), hits))


def read_flat(relpath):
    """The file at `relpath` from the repo root with every run of whitespace made one space, so
    a phrase is found whatever line it was wrapped onto."""
    with open(os.path.join(ROOT, *relpath.split("/")), encoding="utf-8") as f:
        return " ".join(f.read().split())


def section(text, heading):
    """The body of the `## <heading>` section of flattened `text`, up to the next `## `."""
    start = text.index("## " + heading)
    end = text.find(" ## ", start + 3)
    return text[start:] if end == -1 else text[start:end]


# The testplan docs that say where smoke plans come from, now that smoke-plan ships here.
SMOKE_ORIGIN_DOCS = (TESTPLAN_SKILL, "skills/testplan/references/generation.md",
                     "skills/testplan/references/testops-sync.md", "README.md")
_MADE_OUTSIDE = re.compile(r"(?:made|come from) outside (?:this skill|this plugin|it)\b")


class SmokeSkillsAreDocumented(unittest.TestCase):
    """The docs name smoke-plan as the source of smoke plans and make no statement the smoke
    scripts falsify."""

    def test_the_testplan_docs_name_smoke_plan_as_the_source_of_smoke_plans(self):
        for doc in SMOKE_ORIGIN_DOCS:
            text = read_flat(doc)
            with self.subTest(doc=doc):
                self.assertEqual([], _MADE_OUTSIDE.findall(text))
                self.assertIn("/kinoa-qa:smoke-plan", text)

    def test_the_readme_documents_both_skills_and_the_playwright_mcp(self):
        readme = read_flat("README.md")
        self.assertIn("/kinoa-qa:smoke-plan", readme)
        self.assertIn("/kinoa-qa:smoke-run", readme)
        self.assertIn("**Playwright MCP**", section(readme, "Prerequisites"))
        self.assertIn(".playwright-mcp/", readme)
        self.assertIn("JIRA_HOST", readme)

    def test_the_readme_no_longer_makes_the_statements_the_smoke_scripts_falsify(self):
        readme = read_flat("README.md")
        for stale in ("reads these two variables and nothing else",
                      "`write:jira-work` is not used.",
                      "Missing credentials are never a hard stop"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, readme)

    def test_claude_md_names_every_skill_as_the_implementation(self):
        claude_md = read_flat("CLAUDE.md")
        self.assertNotIn("The markdown under `skills/testplan/` is the implementation", claude_md)
        self.assertIn("The markdown under `skills/` — every skill's SKILL.md", claude_md)

    def test_the_spec_no_longer_rules_out_testing_the_node_scripts(self):
        spec = read_flat("docs/superpowers/specs/2026-09-24-test-case-taxonomy-design.md")
        self.assertNotIn("adding a Node test harness to this repo is out of scope", spec)
        self.assertIn("Node 20", spec)


SMOKE_PLAN_SKILL = "skills/smoke-plan/SKILL.md"
SMOKE_RUN_SKILL = "skills/smoke-run/SKILL.md"


class SmokeSkillBehaviourIsWritten(unittest.TestCase):
    """The smoke SKILL.md files state each behaviour the agent must follow, in these phrases."""

    def assert_says(self, doc, text, phrases):
        for phrase in phrases:
            with self.subTest(doc=doc, phrase=phrase):
                self.assertIn(phrase, text)

    def test_smoke_plan_aims_at_about_two_to_five_steps_as_a_target_not_a_limit(self):
        self.assert_says(SMOKE_PLAN_SKILL, read_flat(SMOKE_PLAN_SKILL),
                         ("Aim at about 2–5 numbered steps", "a target, not a limit"))

    def test_smoke_plan_creates_no_testops_case(self):
        self.assert_says(SMOKE_PLAN_SKILL, read_flat(SMOKE_PLAN_SKILL),
                         ("This skill creates no Allure TestOps case.",))

    def test_smoke_run_checks_the_playwright_mcp_and_jira_credentials_first_and_stops(self):
        prerequisites = section(read_flat(SMOKE_RUN_SKILL), "Prerequisites")
        self.assert_says(SMOKE_RUN_SKILL, prerequisites,
                         ("Check the first two at the start, before anything else.",
                          "name exactly what is missing and stop",
                          "**Playwright MCP**",
                          "**`JIRA_EMAIL` and `JIRA_API_TOKEN`**"))

    def test_smoke_run_detects_kinoa_test_automation_from_the_origin_url_in_both_forms(self):
        inside = section(read_flat(SMOKE_RUN_SKILL), "Inside kinoa-test-automation, or not")
        self.assert_says(SMOKE_RUN_SKILL, inside,
                         ("remote get-url origin",
                          "ends in `kinoa-test-automation` or `kinoa-test-automation.git`"))

    def test_smoke_run_refuses_to_save_a_smoke_spec_outside_kinoa_test_automation(self):
        self.assert_says(SMOKE_RUN_SKILL, read_flat(SMOKE_RUN_SKILL),
                         ("Saving the run as a `.smoke.ts` spec is refused",
                          "**Inside kinoa-test-automation only.** Outside it",
                          "refuse the save and say why"))

    def test_smoke_run_takes_the_case_id_from_the_testops_remote_link(self):
        self.assert_says(SMOKE_RUN_SKILL, read_flat(SMOKE_RUN_SKILL),
                         ("a remote link titled `Allure TestOps case <id>`",
                          "never invent one"))

    def test_smoke_run_publishes_no_testops_launch(self):
        self.assert_says(SMOKE_RUN_SKILL, read_flat(SMOKE_RUN_SKILL),
                         ("**Nothing uploads it.**",
                          "do not claim a launch",
                          "**Say that no launch was published, and why**"))


if __name__ == "__main__":
    unittest.main()
