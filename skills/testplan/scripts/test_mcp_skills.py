# test_mcp_skills.py
"""The mcp-plan and mcp-run skills: their SKILL files, references, evals and eval fixtures, and
the two bash checks of mcp-plan, run with HOME pointed at a temp folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import base64, glob, json, re, shutil, subprocess, tempfile, unittest

from test_skill_docs import (CHECK_LAYOUT, fenced_lines, fenced_plugin_commands,
                             missing_command_targets, read_flat, section)

# repo root: skills/testplan/scripts/ -> ../../..
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MCP_SKILLS = ("mcp-plan", "mcp-run")
PLAN_SKILL = "skills/mcp-plan/SKILL.md"
RUN_SKILL = "skills/mcp-run/SKILL.md"
REFERENCES = "skills/mcp-plan/references"
FIXTURE_TREE = "skills/mcp-run/evals"
FIXTURE_FOLDERS = ("plans", "reports")
CHECK_DISTRIBUTION = "skills/mcp-plan/scripts/check-distribution.sh"
EVALS = {name: "skills/{}/evals/evals.json".format(name) for name in MCP_SKILLS}
FICTIONAL_GAME = "7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b"
REAL_LOOKING_GAME = "3b9f2c1e-4d5a-4e6b-8c7d-9e0f1a2b3c4d"
# Split into pieces: this file must not hold the words zip_copy_hits flags.
ZIP_WORDS = ("build" + "-dist", "qa-mcp" + "-skill", "-" + "-dist")
ZIP_SUFFIXES = ("." + "skill", "." + "zip")
_ZIP_MENTION = re.compile(r"\.(?:" + "skill|zip" + r")\b")
_MD_LINK = re.compile(r"\]\(([^)\s#]+\.md)(?:#[^)\s]*)?\)")

MKDIR = "mkdir -p ~/.kinoa-qa/mcp/plans ~/.kinoa-qa/mcp/reports"
LS_PLANS = "ls ~/.kinoa-qa/mcp/plans/ | grep -- '<KEY>-'"
LS_REPORTS = "ls ~/.kinoa-qa/mcp/reports/ | grep -- '<KEY>-'"
SKILLS_VARIABLE = "$SKILLS"
OLD_SKILL_NAMES = ("mcp-qa-plan", "mcp-qa-execute")
SCRATCH_DATA = "<scratch home>/.kinoa-qa/mcp/"

_REFERENCE_LINK = re.compile(r"\]\(([^)\s]*references/[^)\s]*)\)")
_STEP = re.compile(r"^(\d+)\.\s")


def read(rel_path):
    with open(os.path.join(ROOT, *rel_path.split("/")), encoding="utf-8") as f:
        return f.read()


def mcp_skill_files(root):
    """Every file under `root`/skills/mcp-*/, as paths relative to `root`."""
    out = []
    skills = os.path.join(root, "skills")
    for name in sorted(os.listdir(skills)) if os.path.isdir(skills) else []:
        if not name.startswith("mcp-"):
            continue
        for folder, _, files in os.walk(os.path.join(skills, name)):
            for f in sorted(files):
                out.append(os.path.relpath(os.path.join(folder, f), root).replace(os.sep, "/"))
    return sorted(out)


def skills_variable_hits(root):
    """Every line of a file under skills/mcp-*/ that names the old install-folder variable, as
    [(path from `root`, line number)]. The skills live in the plugin now, so no path is written
    against that variable any more — an evals.json included."""
    hits = []
    for rel_path in mcp_skill_files(root):
        with open(os.path.join(root, rel_path), encoding="utf-8", errors="replace") as f:
            for number, line in enumerate(f, 1):
                if SKILLS_VARIABLE in line:
                    hits.append((rel_path, number))
    return hits


def fences_command(text, command):
    """True when a fenced line, with its trailing `#` comment cut off, is exactly `command`."""
    return any(line.split(" #")[0].strip() == command for _, line, _ in fenced_lines(text))


def reference_links(text):
    """Every markdown link into a `references/` folder, as [(line number, target)]."""
    return [(number, m.group(1)) for number, line in enumerate(text.splitlines(), 1)
            for m in _REFERENCE_LINK.finditer(line)]


def reference_links_in_tree(folder):
    """reference_links over every .md file under `folder`, as [(path, line number, target)]."""
    hits = []
    for base, _, files in os.walk(folder):
        for f in sorted(files):
            if f.endswith(".md"):
                path = os.path.join(base, f)
                with open(path, encoding="utf-8") as fh:
                    hits += [(path, n, t) for n, t in reference_links(fh.read())]
    return hits


def section_lines(text, heading):
    """Like test_skill_docs.section, but on unflattened `text`, so the lines survive: from the line
    that starts with `heading` up to the next `## ` line. Raises StopIteration with no such line."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith(heading))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def numbered_steps(text):
    """The top-level `<n>. ` steps of `text` with their continuation lines, as [(n, flat text)]."""
    steps = []
    for line in text.splitlines():
        m = _STEP.match(line)
        if m:
            steps.append([int(m.group(1)), line.strip()])
        elif steps and line.startswith(" "):
            steps[-1][1] += " " + line.strip()
        elif steps and not line.strip():
            continue
        elif steps:
            break
    return [(n, body) for n, body in steps]


def connector_check_problems(skill_text):
    """What is wrong with the connector check of §1 of a run skill, as a list of reasons: step 1
    must look up `kinoa_system_ping`, say the `kinoa` connector is missing or not logged in and
    stop with no report, and the step that creates the report file must come later."""
    steps = numbered_steps(section_lines(skill_text, "## 1."))
    if not steps or steps[0][0] != 1:
        return ["§1 has no step 1"]
    first = steps[0][1]
    problems = []
    for needle in ("kinoa_system_ping", "`kinoa` connector is missing or not logged in",
                   "no report file"):
        if needle not in first:
            problems.append("step 1 does not say " + needle)
    creating = [n for n, body in steps if "create the report file" in body.lower()]
    if not creating:
        problems.append("no step creates the report file")
    elif min(creating) <= 1:
        problems.append("the report file is created in step {}".format(min(creating)))
    return problems


def run_bash(rel_script, *args, home=None, cwd=ROOT):
    """Run `bash <rel_script> <args>` from `cwd` with HOME set to `home` (a fresh temp folder when
    None) and no QA_* variable, so the operator's data folder and denylist are never read."""
    own_home = home is None
    if own_home:
        home = tempfile.mkdtemp()
    env = {k: v for k, v in os.environ.items() if not k.startswith("QA_")}
    env["HOME"] = home
    try:
        return subprocess.run(["bash", rel_script] + list(args), cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=300)
    finally:
        if own_home:
            shutil.rmtree(home, ignore_errors=True)


def flagged_lines(output):
    """The PROBLEM and WARN lines of a check's output."""
    return [l for l in output.splitlines() if l.startswith(("PROBLEM", "WARN"))]


def eval_listed_files(root):
    """Every `files` entry of both evals.json, as paths from `root` (an entry is relative to the
    folder of its skill)."""
    out = []
    for name in MCP_SKILLS:
        path = os.path.join(root, "skills", name, "evals", "evals.json")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for case in json.load(f)["evals"]:
                for entry in case.get("files", []):
                    full = os.path.normpath(os.path.join(root, "skills", name, entry))
                    out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def fixture_closure(seeds, root):
    """The files reachable from `seeds` (paths from `root`) by relative markdown links, the seeds
    included, as a sorted list of paths from `root`. A link that leaves `root` or names no file is
    not followed."""
    seen, todo = set(), list(seeds)
    while todo:
        rel = todo.pop()
        path = os.path.join(root, *rel.split("/"))
        if rel in seen or not os.path.isfile(path):
            continue
        seen.add(rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for target in _MD_LINK.findall(text):
            if re.match(r"^[a-z]+://", target):
                continue
            full = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if full.startswith(os.path.abspath(root) + os.sep):
                todo.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(seen)


def fixture_files(root):
    """Every file under the fixture tree's plans/ and reports/, as paths from `root`."""
    out = []
    for folder in FIXTURE_FOLDERS:
        base = os.path.join(root, *FIXTURE_TREE.split("/"), folder)
        for here, _, files in os.walk(base):
            out += [os.path.relpath(os.path.join(here, f), root).replace(os.sep, "/") for f in files]
    return sorted(out)


def zip_copy_hits(root):
    """What under `root`/skills/ still belongs to the old zip copy, as [(path, reason)]: a file
    named like an archive, any file naming the build script, the archive or the dist flag, and in
    an mcp-* skill any mention of an archive suffix. __pycache__ folders are not scanned."""
    hits = []
    skills = os.path.join(root, "skills")
    for here, dirs, files in os.walk(skills):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            path = os.path.join(here, f)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if f.endswith(ZIP_SUFFIXES):
                hits.append((rel, "archive file"))
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            hits += [(rel, word) for word in ZIP_WORDS if word in text]
            if rel.startswith("skills/mcp-") and _ZIP_MENTION.search(text):
                hits.append((rel, "archive suffix"))
    return hits


def duplicated_references(root):
    """Every second copy of an mcp-plan reference under `root`, as [(path, what it copies)]: a
    `skills/mcp-run/references/` folder, and any file under skills/ whose bytes equal those of a
    `skills/mcp-plan/references/*.md` other than itself."""
    hits = []
    if os.path.exists(os.path.join(root, "skills", "mcp-run", "references")):
        hits.append(("skills/mcp-run/references", "a references folder of its own"))
    originals = {}
    for path in sorted(glob.glob(os.path.join(root, "skills", "mcp-plan", "references", "*.md"))):
        with open(path, "rb") as f:
            originals.setdefault(f.read(), []).append(os.path.relpath(path, root).replace(os.sep, "/"))
    for here, dirs, files in os.walk(os.path.join(root, "skills")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            path = os.path.join(here, f)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as fh:
                copied = originals.get(fh.read(), [])
            hits += [(rel, original) for original in copied if original != rel]
    return sorted(hits)


def old_skill_name_hits(root):
    """Every line of a file under skills/mcp-*/ that names a folder of the zip copy
    (OLD_SKILL_NAMES), as [(path from `root`, line number, name)]."""
    hits = []
    for rel_path in mcp_skill_files(root):
        with open(os.path.join(root, rel_path), encoding="utf-8", errors="replace") as f:
            for number, line in enumerate(f, 1):
                hits += [(rel_path, number, name) for name in OLD_SKILL_NAMES if name in line]
    return hits


class TempTree(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def write(self, rel_path, text):
        path = os.path.join(self.root, *rel_path.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path


class NoSkillsVariable(TempTree):
    def test_flags_the_variable_in_any_file_of_an_mcp_skill(self):
        self.write("skills/mcp-x/evals/evals.json", '{"setup": "copy $SKILLS to a scratch folder"}\n')
        self.write("skills/mcp-x/SKILL.md", "fine\nls $SKILLS/plans\n")
        self.assertEqual([("skills/mcp-x/SKILL.md", 2), ("skills/mcp-x/evals/evals.json", 1)],
                         skills_variable_hits(self.root))

    def test_other_skills_are_not_scanned(self):
        self.write("skills/testplan/SKILL.md", "ls $SKILLS/plans\n")
        self.assertEqual([], skills_variable_hits(self.root))

    def test_no_file_of_either_skill_names_the_variable(self):
        self.assertEqual([], skills_variable_hits(ROOT))

    def test_each_skill_fences_a_bash_plugin_command_that_names_a_real_file(self):
        for doc in (PLAN_SKILL, RUN_SKILL):
            with self.subTest(doc=doc):
                text = read(doc)
                self.assertIn(CHECK_LAYOUT, fenced_plugin_commands(text))
                self.assertEqual([], missing_command_targets(text, ROOT))


class DataFolderIsCreated(unittest.TestCase):
    def test_a_fenced_command_counts_and_prose_does_not(self):
        self.assertTrue(fences_command("```bash\n" + MKDIR + "\n```\n", MKDIR))
        self.assertTrue(fences_command("```bash\n" + LS_PLANS + "   # newest last\n```\n", LS_PLANS))
        self.assertFalse(fences_command("Run `" + MKDIR + "` first.\n", MKDIR))
        self.assertFalse(fences_command("```bash\nmkdir -p ~/.kinoa-qa/mcp/plans\n```\n", MKDIR))

    def test_both_skills_fence_the_mkdir_and_the_two_lookups(self):
        for doc in (PLAN_SKILL, RUN_SKILL):
            text = read(doc)
            for command in (MKDIR, LS_PLANS, LS_REPORTS):
                with self.subTest(doc=doc, command=command):
                    self.assertTrue(fences_command(text, command), command)

    def test_both_skills_stop_when_the_folder_cannot_be_created(self):
        for doc in (PLAN_SKILL, RUN_SKILL):
            with self.subTest(doc=doc):
                self.assertIn("cannot be created or written", read(doc))

    def test_the_file_layout_names_the_data_folders(self):
        layout = read(REFERENCES + "/file-layout.md")
        for folder in ("`~/.kinoa-qa/mcp/plans/`", "`~/.kinoa-qa/mcp/reports/`"):
            with self.subTest(folder=folder):
                self.assertIn(folder, layout)
        self.assertNotIn("docs/plans", layout)
        self.assertNotIn("docs/reports", layout)


class PlansNameReferencesAsText(TempTree):
    def test_flags_a_link_into_references_and_passes_plain_text(self):
        self.write("plans/KING-99001-widgets-test-plan.md",
                   "The rules are in [`rules.md`](../../references/rules.md).\n"
                   "The report contract is mcp-plan references/report-spec.md.\n")
        self.write("reports/KING-99001-widgets-test-report-20990101-0000.md",
                   "**Plan file:** [`KING-99001-widgets-test-plan.md`](../plans/KING-99001-widgets-test-plan.md)\n")
        hits = reference_links_in_tree(self.root)
        self.assertEqual([(1, "../../references/rules.md")], [(n, t) for _, n, t in hits])

    def test_no_fixture_links_into_references(self):
        self.assertEqual([], reference_links_in_tree(os.path.join(ROOT, *FIXTURE_TREE.split("/"))))

    def test_the_template_and_the_report_spec_say_to_write_the_plain_name(self):
        for doc in ("plan-template.md", "report-spec.md", "file-layout.md"):
            with self.subTest(doc=doc):
                self.assertIn("`mcp-plan references/", read(REFERENCES + "/" + doc))
        template = read(REFERENCES + "/plan-template.md")
        self.assertNotIn("../../references/", template)
        self.assertNotIn("../../SKILL.md", template)

    def test_the_file_layout_links_a_report_to_its_plan_in_the_data_folder(self):
        layout = read(REFERENCES + "/file-layout.md")
        self.assertIn("`../plans/<plan file>`", layout)
        self.assertNotIn("../../../", layout)


class RunChecksTheConnectorFirst(unittest.TestCase):
    GOOD = ("## 1. Find the files\n\n"
            "1. **Check the connector.** Look for `kinoa_system_ping`. With none, the `kinoa`\n"
            "   connector is missing or not logged in: stop, with no report file.\n"
            "2. **Otherwise create the report file** before case 1.\n\n## 2. Run order\n")

    def test_a_sound_section_has_no_problem(self):
        self.assertEqual([], connector_check_problems(self.GOOD))

    def test_flags_a_report_created_before_the_check(self):
        bad = self.GOOD.replace("1. **Check", "3. **Check").replace("2. **Otherwise", "1. **Otherwise")
        self.assertEqual(["§1 has no step 1"], connector_check_problems(bad))
        swapped = ("## 1. Find\n\n1. **Otherwise create the report file** now.\n"
                   "2. Look for `kinoa_system_ping`; the `kinoa` connector is missing or not "
                   "logged in, so no report file.\n")
        problems = connector_check_problems(swapped)
        self.assertIn("the report file is created in step 1", problems)

    def test_flags_a_step_1_without_the_wording(self):
        old = self.GOOD.replace("`kinoa`\n   connector is missing or not logged in",
                                "connector\n   is not there")
        self.assertEqual(["step 1 does not say `kinoa` connector is missing or not logged in"],
                         connector_check_problems(old))

    def test_mcp_run_checks_the_connector_before_it_creates_the_report(self):
        self.assertEqual([], connector_check_problems(read(RUN_SKILL)))


class SkillsAreNamedAfterTheirFolders(unittest.TestCase):
    def test_each_frontmatter_name_is_the_folder_name(self):
        for name in MCP_SKILLS:
            with self.subTest(skill=name):
                text = read("skills/{}/SKILL.md".format(name))
                self.assertRegex(text, r"\A---\nname: {}\n".format(re.escape(name)))

    def test_mcp_run_links_the_references_of_mcp_plan(self):
        text = read(RUN_SKILL)
        self.assertIn("](../mcp-plan/references/rules.md)", text)
        self.assertNotIn("../mcp-qa-plan/", text)


class CheckLayoutOnFixtures(TempTree):
    """check-layout.sh [<data folder>]: the skill folders are always checked, the plans and reports
    are read from the data folder, and no link inside the data folder or an evals/ folder is."""

    def data_folder(self, files):
        for folder in FIXTURE_FOLDERS:
            os.makedirs(os.path.join(self.root, "data", folder), exist_ok=True)
        for rel_path, text in files.items():
            self.write("data/" + rel_path, text)
        return os.path.join(self.root, "data")

    def test_passes_on_the_fixture_tree(self):
        result = run_bash(CHECK_LAYOUT, FIXTURE_TREE)
        self.assertEqual([], flagged_lines(result.stdout), result.stdout + result.stderr)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_fails_on_a_misnamed_report(self):
        data = self.data_folder({"reports/KING-99001-widgets-test-report-today.md": "# r\n"})
        result = run_bash(CHECK_LAYOUT, data)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("PROBLEM: bad report name: KING-99001-widgets-test-report-today.md",
                      result.stdout.splitlines())

    def test_defaults_to_the_data_folder_in_home(self):
        home = os.path.join(self.root, "home")
        self.write("home/.kinoa-qa/mcp/plans/.keep", "")
        self.write("home/.kinoa-qa/mcp/reports/KING-99001-widgets-test-report-today.md", "# r\n")
        result = run_bash(CHECK_LAYOUT, home=home)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("PROBLEM: bad report name: KING-99001-widgets-test-report-today.md",
                      result.stdout.splitlines())

    def test_a_missing_data_folder_fails(self):
        result = run_bash(CHECK_LAYOUT, os.path.join(self.root, "nowhere"))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PROBLEM: no data folder")
                            for l in result.stdout.splitlines()), result.stdout)

    def test_does_not_check_links_in_the_data_folder(self):
        data = self.data_folder({"plans/KING-99001-widgets-test-plan.md":
                                 "**Plan version:** 1 (2026-01-01)\n**Earlier runs:** none\n"
                                 "See [`rules.md`](../../references/rules.md).\n"})
        result = run_bash(CHECK_LAYOUT, data)
        self.assertEqual([], flagged_lines(result.stdout), result.stdout + result.stderr)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_does_not_check_links_under_evals_but_does_elsewhere(self):
        for name in MCP_SKILLS:
            shutil.copytree(os.path.join(ROOT, "skills", name), os.path.join(self.root, "skills", name))
        data = self.data_folder({})
        dead = "See [`gone.md`](../../nowhere/gone.md).\n"
        self.write("skills/mcp-run/evals/plans/KING-99009-widgets-test-plan.md", dead)
        result = run_bash(CHECK_LAYOUT, data, cwd=self.root)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.write("skills/mcp-run/notes.md", dead)
        result = run_bash(CHECK_LAYOUT, data, cwd=self.root)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("PROBLEM: dead link in mcp-run/notes.md: ../../nowhere/gone.md",
                      result.stdout.splitlines())

    def test_takes_no_dist_flag_and_scans_no_third_skill(self):
        result = run_bash(CHECK_LAYOUT, ZIP_WORDS[2])
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        script = read(CHECK_LAYOUT)
        self.assertNotIn(ZIP_WORDS[2], script)
        self.assertNotIn("mcp-qa-ready", script)
        self.assertNotIn("docs/plans", script)
        self.assertNotIn("docs/reports", script)
        self.assertNotIn("grep -v '^https\\?", script)


class EvalFixturesExist(TempTree):
    def test_the_closure_follows_relative_links_from_the_seeds(self):
        self.write("skills/mcp-run/evals/reports/KING-99001-x-test-report-20990101-0000.md",
                   "[plan](../plans/KING-99001-x-test-plan.md) and [web](https://example.com/a.md)\n")
        self.write("skills/mcp-run/evals/plans/KING-99001-x-test-plan.md", "no links\n")
        self.write("skills/mcp-run/evals/plans/KING-99002-x-test-plan.md", "an orphan\n")
        seeds = ["skills/mcp-run/evals/reports/KING-99001-x-test-report-20990101-0000.md"]
        self.assertEqual(["skills/mcp-run/evals/plans/KING-99001-x-test-plan.md",
                          "skills/mcp-run/evals/reports/KING-99001-x-test-report-20990101-0000.md"],
                         fixture_closure(seeds, self.root))
        self.assertEqual(3, len(fixture_files(self.root)))

    def test_files_entries_are_read_relative_to_their_skill(self):
        self.write("skills/mcp-plan/evals/evals.json", json.dumps({"evals": [
            {"files": ["../mcp-run/evals/plans/a.md"]}]}))
        self.write("skills/mcp-run/evals/evals.json", json.dumps({"evals": [
            {"files": ["evals/reports/b.md"]}, {}]}))
        self.assertEqual(["skills/mcp-run/evals/plans/a.md", "skills/mcp-run/evals/reports/b.md"],
                         eval_listed_files(self.root))

    def test_every_file_an_eval_lists_exists(self):
        listed = eval_listed_files(ROOT)
        self.assertTrue(listed)
        self.assertEqual([], [p for p in listed if not os.path.isfile(os.path.join(ROOT, p))])

    def test_the_fixture_tree_is_exactly_the_closure_of_the_evals(self):
        tree = fixture_files(ROOT)
        self.assertTrue(tree)
        self.assertEqual(tree, fixture_closure(eval_listed_files(ROOT), ROOT))

    def test_the_webhooks_example_is_a_seed_of_the_revision_eval(self):
        listed = eval_listed_files(ROOT)
        for name in ("plans/KING-22304-webhooks-test-plan.md",
                     "reports/KING-22304-webhooks-test-report-20260916-0944.md"):
            with self.subTest(name=name):
                self.assertIn(FIXTURE_TREE + "/" + name, listed)

    def test_no_eval_names_the_old_folders(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, *FIXTURE_TREE.split("/"), "files")))
        for name, rel_path in sorted(EVALS.items()):
            text = read(rel_path)
            for old in ("evals/files", "docs/plans", "docs/reports"):
                with self.subTest(skill=name, old=old):
                    self.assertNotIn(old, text)

    def test_every_eval_copies_the_fixture_tree_into_a_scratch_home(self):
        for name, rel_path in sorted(EVALS.items()):
            cases = json.loads(read(rel_path))["evals"]
            self.assertTrue(cases, name)
            for case in cases:
                with self.subTest(skill=name, eval=case["id"]):
                    setup = case.get("setup", "")
                    self.assertIn("run the skill with HOME=<scratch home>", setup)
                    self.assertIn("The real ~/.kinoa-qa/mcp/ must be unchanged afterwards", setup)
                    for folder in FIXTURE_FOLDERS:
                        self.assertIn("<plugin>/skills/mcp-run/evals/" + folder + "/", setup)
                        self.assertIn(SCRATCH_DATA + folder + "/", setup)

    def test_no_eval_writes_into_an_outputs_folder_or_the_skill_tree(self):
        for name, rel_path in sorted(EVALS.items()):
            text = read(rel_path)
            for old in ("outputs/", "skill tree", "in place of ~/.kinoa-qa/mcp/",
                        "scratch data folder"):
                with self.subTest(skill=name, old=old):
                    self.assertNotIn(old, text)

    def test_fixtures_name_the_skills_and_the_data_folder_of_the_plugin(self):
        for rel_path in fixture_files(ROOT):
            text = read(rel_path)
            for old in ("mcp-qa-plan", "mcp-qa-execute", "docs/plans", "docs/reports",
                        "of the skill tree"):
                with self.subTest(fixture=rel_path, old=old):
                    self.assertNotIn(old, text)


class NoZipCopy(TempTree):
    def test_flags_an_archive_and_the_words_of_the_copy(self):
        self.write("skills/mcp-x/pack" + ZIP_SUFFIXES[0], "x")
        self.write("skills/mcp-x/notes.md", "built by " + ZIP_WORDS[0] + ".sh into " + ZIP_WORDS[1]
                   + "/\nscan every *" + ZIP_SUFFIXES[1] + " too\n")
        self.write("skills/other/mime.mjs", "'" + ZIP_SUFFIXES[1] + "': 'application/zip'\n")
        self.assertEqual(sorted([("skills/mcp-x/notes.md", ZIP_WORDS[0]),
                                 ("skills/mcp-x/notes.md", ZIP_WORDS[1]),
                                 ("skills/mcp-x/notes.md", "archive suffix"),
                                 ("skills/mcp-x/pack" + ZIP_SUFFIXES[0], "archive file")]),
                         sorted(zip_copy_hits(self.root)))

    def test_nothing_under_skills_describes_or_builds_the_copy(self):
        self.assertEqual([], zip_copy_hits(ROOT))

    def test_no_mcp_skill_names_the_shared_copy(self):
        for rel_path in mcp_skill_files(ROOT):
            with self.subTest(path=rel_path):
                self.assertNotIn("shared copy", read(rel_path).lower())

    def test_fixed_data_lists_the_fictional_values(self):
        fictional = section(read_flat(REFERENCES + "/fixed-data.md"), "Fictional values")
        for value in (FICTIONAL_GAME, "7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c",
                      "7d3e1c2c-7d86-4ba2-9c3d-4e5f6a7b8c9d", "99999999-9999-4999-8999-999999999999",
                      "`7d3e1c2…`", "`00000000-0000-4000-8000-…`"):
            with self.subTest(value=value):
                self.assertIn(value, fictional)

    def test_background_keeps_the_history_only(self):
        background = read(REFERENCES + "/background.md")
        for heading in ("Fictional values", "Redacted files", "The shared copy"):
            with self.subTest(heading=heading):
                self.assertNotIn("## " + heading, background)
        self.assertIn("## The runs behind the rules", background)


class NoReferenceInTwoCopies(TempTree):
    def test_flags_a_run_references_folder_and_a_byte_identical_copy(self):
        self.write("skills/mcp-plan/references/rules.md", "# Rules\n")
        self.write("skills/mcp-plan/references/language.md", "# Language\n")
        self.write("skills/mcp-run/references/rules.md", "# Rules\n")
        self.write("skills/other/notes.md", "# Language\n")
        self.assertEqual([("skills/mcp-run/references", "a references folder of its own"),
                          ("skills/mcp-run/references/rules.md", "skills/mcp-plan/references/rules.md"),
                          ("skills/other/notes.md", "skills/mcp-plan/references/language.md")],
                         duplicated_references(self.root))

    def test_a_single_copy_and_a_near_copy_pass(self):
        self.write("skills/mcp-plan/references/rules.md", "# Rules\n")
        self.write("skills/mcp-run/SKILL.md", "# Rules\n\nmore\n")
        self.assertEqual([], duplicated_references(self.root))

    def test_every_reference_exists_once(self):
        self.assertTrue(glob.glob(os.path.join(ROOT, *REFERENCES.split("/"), "*.md")))
        self.assertEqual([], duplicated_references(ROOT))


class NoOldSkillNames(TempTree):
    def test_flags_an_old_folder_name_in_any_file_of_an_mcp_skill(self):
        self.write("skills/mcp-x/evals/evals.json", '{"prompt": "read mcp-qa-execute/SKILL.md"}\n')
        self.write("skills/mcp-x/scripts/check.sh", "ok\nls mcp-qa-plan/docs\n")
        self.write("skills/testplan/SKILL.md", "mcp-qa-plan\n")
        self.assertEqual([("skills/mcp-x/evals/evals.json", 1, "mcp-qa-execute"),
                          ("skills/mcp-x/scripts/check.sh", 2, "mcp-qa-plan")],
                         old_skill_name_hits(self.root))

    def test_the_new_names_pass(self):
        self.write("skills/mcp-x/SKILL.md", "mcp-plan and mcp-run, in <plugin>/skills/mcp-plan/\n")
        self.assertEqual([], old_skill_name_hits(self.root))

    def test_no_file_of_either_skill_names_an_old_folder(self):
        files = mcp_skill_files(ROOT)
        for name in MCP_SKILLS:
            for kind in ("/SKILL.md", "/evals/evals.json"):
                self.assertIn("skills/" + name + kind, files)
        self.assertTrue(any(f.startswith("skills/mcp-plan/references/") for f in files))
        self.assertTrue(any(f.startswith("skills/mcp-plan/scripts/") for f in files))
        self.assertTrue(any(f.startswith(FIXTURE_TREE + "/plans/") for f in files))
        self.assertEqual([], old_skill_name_hits(ROOT))


class DistributionScan(TempTree):
    """check-distribution.sh <folder>...: every file, the eval fixtures included, carries no e-mail
    outside the example domains and no non-fictional uuid in a fixture position, also inside a
    confirm token; the fictional values are read from fixed-data.md."""

    def scan(self, *folders, cwd=ROOT, script=CHECK_DISTRIBUTION):
        return run_bash(script, *folders, cwd=cwd)

    def planted(self, text):
        self.write("planted/plans/KING-99001-widgets-test-plan.md", "# plan\n\n" + text + "\n")
        return os.path.join(self.root, "planted")

    @staticmethod
    def token(payload):
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        assert raw.startswith("eyJ")
        return raw

    def test_the_real_skill_folders_pass(self):
        folders = sorted(glob.glob(os.path.join(ROOT, "skills", "mcp-*")))
        self.assertTrue(folders)
        result = self.scan(*[os.path.relpath(f, ROOT) for f in folders])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_flags_an_e_mail_outside_the_example_domains(self):
        result = self.scan(self.planted("Account: qa.tester@kinoa-games.io"))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PERSONAL DATA: e-mail in") for l in result.stdout.splitlines()),
                        result.stdout)

    def test_flags_a_real_looking_game_id(self):
        result = self.scan(self.planted('`{"game_id": "' + REAL_LOOKING_GAME + '"}`'))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PERSONAL DATA: uuid in a fixture position in")
                            for l in result.stdout.splitlines()), result.stdout)

    def test_flags_the_same_game_id_inside_a_confirm_token(self):
        token = self.token({"tool": "kinoa_widget_create", "game_id": REAL_LOOKING_GAME})
        result = self.scan(self.planted("confirm_token: " + token))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PERSONAL DATA: uuid in a decoded confirm token in")
                            for l in result.stdout.splitlines()), result.stdout)

    def test_a_fictional_game_id_passes(self):
        token = self.token({"game_id": FICTIONAL_GAME})
        result = self.scan(self.planted('`{"game_id": "' + FICTIONAL_GAME + '"}` ' + token))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def copied_plan_skill(self, fixed_data):
        """A copy of mcp-plan's scripts with `fixed_data` as its references/fixed-data.md."""
        shutil.copytree(os.path.join(ROOT, "skills", "mcp-plan", "scripts"),
                        os.path.join(self.root, "skills", "mcp-plan", "scripts"))
        self.write("skills/mcp-plan/references/fixed-data.md", fixed_data)
        return os.path.join(self.root, *CHECK_DISTRIBUTION.split("/"))

    def test_reads_the_fictional_values_from_fixed_data(self):
        script = self.copied_plan_skill("# Fixed test data\n\n## Fictional values\n\n"
                                        "Only `00000000-0000-4000-8000-…` here.\n")
        folder = self.planted('`{"game_id": "' + FICTIONAL_GAME + '"}`')
        result = self.scan(folder, script=script, cwd=self.root)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PERSONAL DATA: uuid in a fixture position in")
                            for l in result.stdout.splitlines()), result.stdout)

    def test_fails_when_fixed_data_lists_no_fictional_values(self):
        script = self.copied_plan_skill("# Fixed test data\n\nNo such section.\n")
        result = self.scan(self.planted("nothing to find"), script=script, cwd=self.root)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PROBLEM: no fictional values") for l in result.stdout.splitlines()),
                        result.stdout)

    def test_the_header_names_the_plugin_path_and_ci(self):
        header = read(CHECK_DISTRIBUTION).split("\nset -u")[0]
        self.assertIn("bash <plugin>/skills/mcp-plan/scripts/check-distribution.sh <folder>...", header)
        self.assertIn("CI runs it on <plugin>/skills/mcp-plan and <plugin>/skills/mcp-run", header)
        self.assertIn("fixed-data.md", header)
        self.assertNotIn("check-layout.sh calls it", header)


if __name__ == "__main__":
    unittest.main()
