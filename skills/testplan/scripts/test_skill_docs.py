# test_skill_docs.py
"""The skill's markdown is its implementation (CLAUDE.md): a reference that misdescribes the
validator is a defect. These tests keep the retired taxonomy vocabulary out of the docs an
agent reads, keep every fenced plugin command runnable and every repo-only command (of
kinoa-test-automation or kinoa-mcp) and kinoa-test-automation path labelled as such, and keep the evals and their fixtures loadable and
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
    """Every skills/*/SKILL.md, every file under skills/shared/, and mcp-plan's references, which
    mcp-run reads as its own."""
    paths = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
    paths += sorted(glob.glob(os.path.join(ROOT, "skills", "shared", "**", "*"), recursive=True))
    paths += sorted(glob.glob(os.path.join(ROOT, "skills", "mcp-plan", "references", "**", "*"),
                              recursive=True))
    return [p for p in paths if os.path.isfile(p)]


_FENCE = re.compile(r"^\s*(```|~~~)")
_PLUGIN_COMMAND = re.compile(r"\b(?:node|python3|bash)\s+<plugin>/(\S+)")
_MAIN_BLOCK = 'if __name__ == "__main__":'
_REPO_COMMAND = re.compile(r"^(?:npx |git |node scripts/)")
REPO = "kinoa-test-automation"
# The repos a fenced repo-only command may be labelled with: kinoa-test-automation for the smoke
# skills, kinoa-mcp for mcp-plan's branch check of the server source.
REPO_LABELS = (REPO, "kinoa-mcp")


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
    """Every fenced `node|python3|bash <plugin>/<path>` whose <path> is not a file under `root`, or is a
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
    """Every fenced `npx `/`git `/`node scripts/` line with no repo label (`kinoa-test-automation`
    or `kinoa-mcp`, REPO_LABELS) on the three non-blank lines above its opening fence, as
    [(line number, line)]."""
    lines = text.splitlines()
    hits = []
    for number, line, opening in fenced_lines(text):
        if not _REPO_COMMAND.match(line.strip()):
            continue
        above = [l for l in lines[:opening - 1] if l.strip()][-3:]
        if not any(label in l for l in above for label in REPO_LABELS):
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
                  "skills/shared/step-outcome-contract.md",
                  "skills/mcp-plan/SKILL.md", "skills/mcp-run/SKILL.md",
                  "skills/mcp-plan/references/rules.md", "skills/mcp-plan/references/stand-facts.md")


def assert_scans_every_skill(case, paths):
    """`paths` holds testplan's, the smoke skills' and the mcp skills' SKILL.md, the shared
    contract, mcp-plan's references (which mcp-run reads too), and every skills/*/SKILL.md on
    disk."""
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
                           ("tool.mjs", "console.log(1);\n"),
                           ("tool.sh", "#!/usr/bin/env bash\necho ok\n")):
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

    def test_a_fenced_bash_command_is_checked_like_node_and_python3(self):
        text = ("Run `bash <plugin>/skills/x/scripts/prose.sh` in prose.\n```bash\n"
                "bash <plugin>/skills/x/scripts/tool.sh ~/.kinoa-qa/mcp\n"
                "bash <plugin>/skills/x/scripts/missing.sh\n```\n")
        self.assertEqual([(4, "skills/x/scripts/missing.sh", "no such file")],
                         missing_command_targets(text, self.root))


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

    def test_a_git_fence_labelled_kinoa_mcp_passes(self):
        text = ("If this chat can see the\nkinoa-mcp source, run one check first:\n\n```bash\n"
                "git -C <repo root> fetch --quiet\n```\n")
        self.assertEqual([], unlabelled_repo_commands(text))

    def test_a_git_fence_with_kinoa_mcp_too_far_above_or_no_label_fails(self):
        too_far = ("The kinoa-mcp source.\none\ntwo\nthree\n```bash\n"
                   "git -C <repo root> fetch --quiet\n```\n")
        self.assertEqual([(6, "git -C <repo root> fetch --quiet")],
                         unlabelled_repo_commands(too_far))
        unlabelled = "If this chat can see the source:\n```bash\ngit -C <repo root> fetch\n```\n"
        self.assertEqual([(3, "git -C <repo root> fetch")], unlabelled_repo_commands(unlabelled))


class RepoOnlyCommandsAreLabelled(unittest.TestCase):
    def test_every_repo_command_in_the_docs_names_its_repo(self):
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


def testplan_docs():
    """testplan's SKILL.md and every reference file: what the testplan agent reads."""
    paths = [os.path.join(ROOT, *TESTPLAN_SKILL.split("/"))]
    paths += sorted(glob.glob(os.path.join(SKILL_DIR, "references", "**", "*"), recursive=True))
    return [rel(p) for p in paths if os.path.isfile(p)]


# Wording from before the smoke push was built; none of it may survive in the testplan docs.
SMOKE_PUSH_STALE = ("planned (KING-23102)", "(KING-23102), not built",
                    "no flow of this plugin produces or pushes one",
                    "never reads or writes any other plan path",
                    "no flow of this plugin writes one", "No flow of this plugin yet")


def fenced_plugin_commands(text):
    """Every `<plugin>/…` path a fenced `node|python3|bash` command runs, in order."""
    return [m.group(1) for _, line, _ in fenced_lines(text)
            for m in _PLUGIN_COMMAND.finditer(line)]


class SmokePushIsWired(unittest.TestCase):
    """testplan's docs give the `--from-smoke` flow end to end and no longer call it planned."""

    def setUp(self):
        self.skill = read_flat(TESTPLAN_SKILL)

    def test_the_synopsis_names_from_smoke(self):
        synopsis = self.skill[:self.skill.index("## Source of truth")]
        self.assertIn("--from-smoke <SUBTASK-KEY>", synopsis)

    def test_the_converter_and_the_link_writer_are_fenced_runnable_commands(self):
        with open(os.path.join(ROOT, *TESTPLAN_SKILL.split("/")), encoding="utf-8") as f:
            text = f.read()
        commands = fenced_plugin_commands(text)
        for script in ("skills/testplan/scripts/smoke_to_plan.py",
                       "skills/testplan/scripts/jira_remote_link.py"):
            with self.subTest(script=script):
                self.assertIn(script, commands)
        self.assertEqual([], missing_command_targets(text, ROOT))

    def test_the_step_c_stop_names_the_from_smoke_exception(self):
        step_c = section(self.skill, "Step C")
        self.assertIn("unless the run is `--from-smoke`", step_c)

    def test_a_converter_fail_is_a_defect_with_no_retry(self):
        step_c = section(self.skill, "Step C")
        self.assertIn("converter defect", step_c)
        self.assertIn("no regeneration retry", step_c)

    def test_step_d_asks_for_the_link_and_offers_no_hand_edit(self):
        step_d = section(self.skill, "Step D")
        self.assertIn("a separate yes", step_d)
        self.assertIn("never hand-edited", step_d)

    def test_step_e_takes_the_story_key_from_the_header(self):
        step_e = section(self.skill, "Step E")
        self.assertIn("the Story key from the plan header's `story:`", step_e)
        self.assertIn("never the sub-task key", step_e)

    def test_the_link_is_written_after_step_e_and_never_on_a_dry_or_unattended_run(self):
        step_e = section(self.skill, "Step E")
        self.assertIn("never under `--dry-run`", step_e)
        self.assertIn("never on an unattended run", step_e)

    def test_the_read_back_requires_scope_smoke_for_a_smoke_plan(self):
        for doc in (TESTPLAN_SKILL, "skills/testplan/references/testops-sync.md"):
            with self.subTest(doc=doc):
                self.assertIn("`Target:` marker says `scope=smoke`", read_flat(doc))

    def test_the_scope_flag_still_stops(self):
        self.assertIn("the flag is gone", self.skill)

    def test_the_stale_smoke_wording_is_gone_from_the_testplan_docs(self):
        docs = testplan_docs()
        self.assertIn("skills/testplan/references/testops-sync.md", docs)
        for doc in docs:
            text = read_flat(doc)
            for stale in SMOKE_PUSH_STALE:
                with self.subTest(doc=doc, stale=stale):
                    self.assertNotIn(stale, text)


class SmokeSkillsNameThePush(unittest.TestCase):
    """smoke-plan and smoke-run describe the push to TestOps as built."""

    def test_smoke_plan_names_the_push_and_still_creates_no_case(self):
        text = read_flat(SMOKE_PLAN_SKILL)
        for phrase in ("/kinoa-qa:testplan --from-smoke <SUBTASK-KEY>",
                       "This skill creates no Allure TestOps case."):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_smoke_plan_states_the_ac_numbering_rule(self):
        text = read_flat(SMOKE_PLAN_SKILL)
        self.assertIn("`[AC-n]` is the n-th acceptance criterion of the parent Story, counted "
                      "from 1", text)

    def test_smoke_run_says_what_happens_with_more_than_one_link(self):
        text = read_flat(SMOKE_RUN_SKILL)
        self.assertIn("more than one `Allure TestOps case …` link", text)
        self.assertIn("ask the user which id to use", text)

    def test_neither_smoke_skill_calls_the_push_planned(self):
        for doc in (SMOKE_PLAN_SKILL, SMOKE_RUN_SKILL):
            text = read_flat(doc)
            for stale in ("not built", "planned (KING-23102)", "planned push"):
                with self.subTest(doc=doc, stale=stale):
                    self.assertNotIn(stale, text)


class ReadmeDocumentsThePush(unittest.TestCase):
    def setUp(self):
        self.readme = read_flat("README.md")

    def test_the_readme_documents_from_smoke_and_its_write_scope(self):
        for phrase in ("/kinoa-qa:testplan --from-smoke <SUBTASK-KEY>",
                       "`--from-smoke` writes one remote link, which needs the classic "
                       "`write:jira-work` scope"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.readme)

    def test_the_readme_no_longer_says_testplan_never_writes_to_jira(self):
        for stale in ("`testplan` never writes to Jira",
                      "all `testplan` needs",
                      "If you only use `testplan`, `read:jira-work` alone is enough",
                      "no flow of this plugin produces a smoke `test-plan.md` yet",
                      "and `testplan` does not read it",
                      "planned (KING-23102)", "(KING-23102), not built", "KING-23102, not built",
                      "is planned and not built"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, self.readme)


def changelog_entry(version):
    """The flattened body of CHANGELOG.md's `## <version>` entry, up to the next `## `."""
    text = read_flat("CHANGELOG.md")
    start = text.index("## " + version + " ")
    end = text.find(" ## ", start + 3)
    return text[start:] if end == -1 else text[start:end]


class SmokePushIsReleased(unittest.TestCase):
    def _evals(self):
        with open(os.path.join(EVALS_DIR, "evals.json"), encoding="utf-8") as f:
            return json.load(f)["evals"]

    def test_evals_have_a_from_smoke_case(self):
        prompts = [e["prompt"] for e in self._evals() if "--from-smoke" in e["prompt"]]
        self.assertTrue(prompts)

    def test_the_step_c_stop_eval_still_describes_a_normal_run(self):
        stop = [e for e in self._evals() if e["name"] == "testplan-stops-on-a-smoke-header"]
        self.assertEqual(1, len(stop))
        self.assertNotIn("--from-smoke", stop[0]["prompt"])
        self.assertIn("stops at Step C", stop[0]["expected_output"])

    def test_the_0_5_0_entry_lists_the_push_the_scripts_and_the_scope(self):
        self.assertIn("## 0.5.0 ", read_flat("CHANGELOG.md"))
        entry = changelog_entry("0.5.0")
        for phrase in ("--from-smoke", "smoke_to_plan.py", "jira_remote_link.py",
                       "write:jira-work"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, entry)


class SmokePushDocsMatchTheScripts(unittest.TestCase):
    """The `--from-smoke` prose says what `jira_remote_link.py` and `smoke_to_plan.py` do."""

    def setUp(self):
        self.skill = read_flat(TESTPLAN_SKILL)

    def test_unset_credentials_are_exit_3_and_usage_errors_exit_2(self):
        step_e = section(self.skill, "Step E")
        self.assertIn("Exit 3: `JIRA_EMAIL` or `JIRA_API_TOKEN` is unset", step_e)
        self.assertIn("Exit 2: a usage error", step_e)
        self.assertNotIn("Exit 2: the credentials are unset", self.skill)
        self.assertIn("Jira credentials unset (`jira_remote_link.py` exit 3)", self.skill)

    def test_a_config_error_names_which_by_hand_lines_are_printed(self):
        step_e = section(self.skill, "Step E")
        self.assertIn("On exit 1 from the config, the `title:` line is always printed, and the "
                      "`url:` line only when the config still names `testops.base_url` and "
                      "`testops.project_id`", step_e)

    def test_the_story_is_read_with_its_field_names(self):
        self.assertIn('getJiraIssue(<STORY-KEY>, responseContentFormat="markdown", '
                      'expand="names", fields=["*all"])', self.skill)

    def test_the_link_rule_is_the_shared_title_matcher(self):
        rule = "`^Allure TestOps case (\\d+)\\b`"
        for doc in (TESTPLAN_SKILL, SMOKE_RUN_SKILL):
            with self.subTest(doc=doc):
                self.assertIn(rule, read_flat(doc))
        self.assertIn("case_id_from_title", self.skill)

    def test_smoke_plan_states_the_headings_where_it_lays_out_the_sub_task(self):
        steps = read_flat(SMOKE_PLAN_SKILL)
        layout = steps[steps.index("### 3) Write the steps"):steps.index("### 4)")]
        for heading in ("`## Preconditions`", "`## Steps`", "`## Open questions`"):
            with self.subTest(heading=heading):
                self.assertIn(heading, layout)


MCP_PLAN_USAGE = "Usage: `/kinoa-qa:mcp-plan`"
MCP_RUN_USAGE = "Usage: `/kinoa-qa:mcp-run`"
MCP_MIGRATION = "Moving from the zip copy of the MCP skills"
CHECK_LAYOUT = "skills/mcp-plan/scripts/check-layout.sh"


class McpSkillsAreDocumented(unittest.TestCase):
    """The README documents mcp-plan and mcp-run, their prerequisites, the data folder, the
    layout check and the move from the zip copy, as the skills and CHANGELOG 0.6.0 state them."""

    def setUp(self):
        self.readme = read_flat("README.md")

    def test_the_intro_lists_five_skills_with_their_usage_anchors(self):
        intro = self.readme[:self.readme.index("## Prerequisites")]
        self.assertIn("QA plugin for Claude Code. Five skills:", intro)
        for anchor in ("(#usage-kinoa-qamcp-plan)", "(#usage-kinoa-qamcp-run)"):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, intro)

    def test_both_usage_headings_exist(self):
        for heading in (MCP_PLAN_USAGE, MCP_RUN_USAGE):
            with self.subTest(heading=heading):
                self.assertIn("## " + heading + " ", self.readme)

    def test_the_prerequisites_have_the_kinoa_connector_and_bash_and_perl_rows(self):
        prerequisites = section(self.readme, "Prerequisites")
        for phrase in ("| **`kinoa` connector** | `mcp-run` — required |",
                       "**Checked at the start**: with no `kinoa_*` tool, `mcp-run` says the "
                       "`kinoa` connector is missing or not logged in and stops, with no report "
                       "file",
                       "| **`kinoa` connector** | `mcp-plan` — optional |",
                       "`not done: no connector in this chat`",
                       "| **bash** and **perl** | `mcp-plan`, `mcp-run` — required |",
                       "`check-layout.sh`"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, prerequisites)

    def test_each_usage_section_names_the_data_folder_and_the_layout_check(self):
        for heading in (MCP_PLAN_USAGE, MCP_RUN_USAGE):
            self.assertIn("## " + heading + " ", self.readme)
            body = section(self.readme, heading)
            for phrase in ("~/.kinoa-qa/mcp/plans/", "~/.kinoa-qa/mcp/reports/", "check-layout.sh"):
                with self.subTest(heading=heading, phrase=phrase):
                    self.assertIn(phrase, body)

    def test_the_layout_check_is_a_fenced_runnable_command_with_its_data_folder_argument(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn(CHECK_LAYOUT, fenced_plugin_commands(text))
        self.assertIn("check-layout.sh [<data folder>]", self.readme)
        self.assertIn("defaults to `~/.kinoa-qa/mcp/`", self.readme)

    def test_the_migration_moves_the_data_and_deletes_only_the_two_folders(self):
        self.assertIn("## " + MCP_MIGRATION + " ", self.readme)
        migration = section(self.readme, MCP_MIGRATION)
        for phrase in ("~/.kinoa-qa/mcp/plans/", "~/.kinoa-qa/mcp/reports/",
                       "mcp-qa-plan/docs/plans/", "mcp-qa-execute/docs/reports/",
                       "delete only the `mcp-qa-plan` and `mcp-qa-execute` folders",
                       "`~/.claude/skills`", "`<kinoa-mcp checkout>/.claude/skills`"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, migration)

    def test_the_migration_warns_that_mcp_qa_ready_no_longer_finds_its_inputs(self):
        self.assertIn("## " + MCP_MIGRATION + " ", self.readme)
        migration = section(self.readme, MCP_MIGRATION)
        self.assertIn("`mcp-qa-ready` is a separate skill and not part of this plugin", migration)
        self.assertIn("no longer finds the plans, the reports or the `mcp-plan` references",
                      migration)

    def test_the_install_check_names_all_five_commands(self):
        install = section(self.readme, "Install")
        for command in ("/kinoa-qa:testplan", "/kinoa-qa:smoke-plan", "/kinoa-qa:smoke-run",
                        "/kinoa-qa:mcp-plan", "/kinoa-qa:mcp-run"):
            with self.subTest(command=command):
                self.assertIn(command, install)


if __name__ == "__main__":
    unittest.main()
