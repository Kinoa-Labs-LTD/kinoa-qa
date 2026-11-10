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

    def test_the_run_skill_fences_the_status_mode_and_the_two_greps(self):
        text = read(RUN_SKILL)
        for command in ("bash <plugin>/skills/mcp-plan/scripts/check-layout.sh status ~/.kinoa-qa/mcp/reports/<report file>",
                        "bash <plugin>/skills/mcp-plan/scripts/check-layout.sh grades ~/.kinoa-qa/mcp/reports/<report file> ~/.kinoa-qa/mcp/reports/<previous report>",
                        "grep -nE '<pattern>' ~/.kinoa-qa/mcp/plans/<plan file>",
                        "grep -nE '<pattern>' ~/.kinoa-qa/mcp/reports/<report file>",
                        "sleep <n>"):
            with self.subTest(command=command):
                self.assertTrue(fences_command(text, command), command)
        self.assertFalse(fences_command(text, "sleep 60"))


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

    def test_step_6_asks_for_the_five_permission_shapes_and_the_segment_model(self):
        steps = dict(numbered_steps(section_lines(read(RUN_SKILL), "## 1.")))
        for needle in ("curl", "`sleep <n>`", "`grep -nE`", "mcp.segment_model"):
            with self.subTest(needle=needle):
                self.assertIn(needle, steps[6])

    def test_the_run_skill_reads_segments_md_before_the_first_segment(self):
        self.assertIn("](../mcp-plan/references/segments.md)", read(RUN_SKILL))


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

    # --- the checks added by KING-23440 (B.5, B.8, B.9, B.10, C.3) ---

    def check(self, files):
        data = self.data_folder(files)
        result = run_bash(CHECK_LAYOUT, data)
        return result.returncode, result.stdout + result.stderr

    def test_a_minimal_current_plan_passes(self):
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan()})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_accepts_a_side_by_side_suffix_in_a_report_name(self):
        code, out = self.check({"reports/KING-99001-widgets-test-report-20261012-0741-opu.md": "# r\n"})
        self.assertNotIn("PROBLEM: bad report name: KING-99001-widgets-test-report-20261012-0741-opu.md",
                         out.splitlines(), out)
        self.assertEqual(0, code, out)

    def test_an_earlier_run_with_a_suffix_is_found_for_the_known_issues_check(self):
        report = "reports/KING-99001-widgets-test-report-20261012-0741-opu.md"
        plan = current_plan(
            earlier_runs="`KING-99001-widgets-test-report-20261012-0741-opu.md`",
            known_issues="### 1.2 Known issues and the cases that cover them\n\n"
                         "| Finding | Filed as | What it is | Cases |\n|---|---|---|---|\n"
                         "| F1 (0741) | — | the create loses the size | `create-ok-01` |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan,
                                report: "# r\n\n## 4. Findings\n\n### F1 — the create loses the size   [severity: minor]\n"
                                        "### F2 — the get answers 500   [severity: major]\n"})
        self.assertEqual(["PROBLEM: plans/KING-99001-widgets-test-plan.md: §1.2 has no row for F2 (0741) of "
                          "KING-99001-widgets-test-report-20261012-0741-opu.md"],
                         [l for l in flagged_lines(out) if "earlier run" in l or "§1.2" in l], out)

    def test_warns_when_a_plan_says_no_earlier_runs_but_a_report_exists(self):
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan(),
                                "reports/KING-99001-widgets-test-report-20261012-0900.md": "# r\n"})
        self.assertIn("WARN: plans/KING-99001-widgets-test-plan.md: **Earlier runs:** none, but reports/ holds "
                      "KING-99001-widgets-test-report-20261012-0900.md — a new plan version is due",
                      out.splitlines(), out)
        self.assertEqual(0, code, out)

    def test_20_does_not_warn_for_a_report_whose_run_is_paused(self):
        report = "# r\n\n## 2. Overall status\n\npaused — the run is in progress.\n\n## 3. What was done, per part\n"
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan(),
                                "reports/KING-99001-widgets-test-report-20261012-0900.md": report})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_flags_a_name_literal_missing_from_the_artifacts_table(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": "7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b", "name": "NAME-b", "size": 3}`')
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: `NAME-b` in the Call cell of `create-ok-01` "
                      "is not in the §0 artifacts table (plan-template.md, cases are data)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_flags_a_length_probe_whose_value_has_another_length(self):
        row = ('| `create-schema-01` | `kinoa_widget_create {"game_id": "7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b", '
               '"name": "len20-0123456789", "size": 3}` | `error.code` = `VALIDATION_FAILED` |\n')
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan(extra_rows=row)})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: `create-schema-01` sends a `len20-` value of "
                      "16 characters, not 20 (plan-template.md, cases are data)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_a_length_probe_is_counted_in_characters_not_bytes(self):
        row = ('| `create-schema-01` | `kinoa_widget_create {"game_id": "7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b", '
               '"name": "len8-ü01", "size": 3}` | `error.code` = `VALIDATION_FAILED` |\n')
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan(extra_rows=row)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    # check 21: research inputs and §1.3 (C.3)

    SEC13 = ("### 1.3 Research results and the cases that cover them\n\n"
             "| Source | Rule | Served contract | Cases |\n|---|---|---|---|\n")

    def test_flags_research_inputs_with_no_section_1_3(self):
        plan = current_plan(header_extra="**Research inputs:** KING-99006 — [FE] Research validations for Widgets\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: the header names research inputs, but the plan "
                      "has no ### 1.3 section (plan-template.md, the skeleton)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_flags_a_section_1_3_nobody_named(self):
        plan = current_plan(header_extra="**Research inputs:** none\n",
                            extra_sections=self.SEC13 + "| KING-99006, Form rules | `name` required | same | `create-ok-01` |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: the header says **Research inputs:** none, but "
                      "the plan has a ### 1.3 section — a research input nobody named (plan-template.md, the skeleton)",
                      out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_flags_a_section_1_3_row_with_an_empty_cases_cell(self):
        plan = current_plan(header_extra="**Research inputs:** KING-99006 — [FE] Research validations for Widgets\n",
                            extra_sections=self.SEC13 + "| KING-99006, Form rules | `name` required | same | |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: the §1.3 row `KING-99006, Form rules` has no case id "
                      "and no `not reachable:` (plan-template.md, the skeleton)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_flags_a_section_1_3_case_that_is_no_row_of_the_plan(self):
        plan = current_plan(header_extra="**Research inputs:** KING-99006 — [FE] Research validations for Widgets\n",
                            extra_sections=self.SEC13 + "| KING-99006, Form rules | `name` required | same | `create-schema-09` |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan.md: §1.3 names `create-schema-09`, which is no case "
                      "row of the plan (plan-template.md, the skeleton)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_a_backticked_not_reachable_cell_passes(self):
        plan = current_plan(header_extra="**Research inputs:** KING-99006 — [FE] Research validations for Widgets\n",
                            extra_sections=self.SEC13 +
                            "| KING-99006, UI-only limits | the add button is hidden at the limit | absent | `not reachable: a UI-only control` |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_warns_when_the_earlier_runs_none_line_carries_a_tail(self):
        plan = current_plan(earlier_runs="none — this is the first plan and the first run for this story")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan,
                                "reports/KING-99001-widgets-test-report-20261012-0900.md": "# r\n"})
        self.assertTrue(any(l.startswith("WARN: plans/KING-99001-widgets-test-plan.md: **Earlier runs:** none, but reports/ holds "
                                         "KING-99001-widgets-test-report-20261012-0900.md") for l in out.splitlines()), out)

    def test_a_covered_section_1_3_passes(self):
        plan = current_plan(header_extra="**Research inputs:** KING-99006 — [FE] Research validations for Widgets\n",
                            extra_sections=self.SEC13 +
                            "| KING-99006, Form rules | `name` required | same | `create-ok-01` |\n"
                            "| KING-99006, UI-only limits | the add button is hidden at the limit | absent | not reachable: a UI-only control |\n\n")
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    # --- the checks added after the eval run of 2026-10-16 (0.7.1): 18 reads KEY_ literals, 22-25 are new ---

    PLAN = "plans/KING-99001-widgets-test-plan.md"
    P = "PROBLEM: plans/KING-99001-widgets-test-plan.md: "

    def test_18_flags_a_key_literal_missing_from_the_artifacts_table(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", "key": "KEY_b"}`')
        code, out = self.check({self.PLAN: plan})
        self.assertIn(self.P + "`KEY_b` in the Call cell of `create-ok-01` is not in the §0 artifacts table "
                      "(plan-template.md, cases are data)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_18_reads_the_call_cells_of_part_b_too(self):
        part_b = ("# PART B — role-gated checks\n\n## B1. Checkpoint 1 — GAME Viewer on `P1`\n\n"
                  "| Id | Call | Expected |\n|---|---|---|\n"
                  '| `role-create-01` | `kinoa_widget_create {"game_id": P1, "name": "NAME-a", "key": "KEY_role_b"}` | '
                  "`error.code` = `PERMISSION_DENIED` |\n\n# REPORT")
        code, out = self.check({self.PLAN: current_plan().replace("# REPORT", part_b)})
        self.assertIn(self.P + "`KEY_role_b` in the Call cell of `role-create-01` is not in the §0 artifacts table "
                      "(plan-template.md, cases are data)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_18_a_key_inside_a_longer_token_is_not_a_key_literal(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", "ref": "CONFIRM_KEY_x"}`')
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    REPORT_V1 = "reports/KING-99001-widgets-test-report-20261010-0900.md"
    PLAN_V2 = "plans/KING-99001-widgets-test-plan-v2.md"

    def v2_pair(self, status_rows):
        plan = current_plan(earlier_runs="`KING-99001-widgets-test-report-20261010-0900.md`").replace(
            "**Plan version:** 1 (2026-10-16)", "**Plan version:** 2 (2026-10-16)")
        report = ("# r\n\n## 3. What was done, per part\n\n### Case status\n\n"
                  "| Case | Status | Finding / note / blocked row |\n|---|---|---|\n" + "\n".join(status_rows) + "\n")
        return {self.PLAN_V2: plan, self.REPORT_V1: report}

    def test_22_flags_a_graded_row_the_next_version_dropped(self):
        code, out = self.check(self.v2_pair(["| `pre-01` | `PASS` | — |", "| `create-ok-01` | `PASS` | — |",
                                             "| `create-ok-02` | `PASS` | — |", "| `list-ok-01` | `BLOCKED` | section 8 |"]))
        self.assertEqual(["PROBLEM: plans/KING-99001-widgets-test-plan-v2.md: `create-ok-02` was graded `PASS` in "
                          "KING-99001-widgets-test-report-20261010-0900.md but is no case row of this version "
                          "(plan-template.md, soundness rules)"], flagged_lines(out), out)
        self.assertEqual(1, code, out)

    def test_22_reads_a_status_cell_without_backticks(self):
        code, out = self.check(self.v2_pair(["| pre-01 | PASS | — |", "| create-ok-01 | PASS | — |",
                                             "| get-ok-01 | FAIL | F1 |"]))
        self.assertIn("PROBLEM: plans/KING-99001-widgets-test-plan-v2.md: `get-ok-01` was graded `FAIL` in "
                      "KING-99001-widgets-test-report-20261010-0900.md but is no case row of this version "
                      "(plan-template.md, soundness rules)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_23_flags_a_spread_in_an_argument_object(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", '
                                        '"params": [...SYS_R without SYS_R0, {"id": SYS_R0.id}]}`')
        code, out = self.check({self.PLAN: plan})
        self.assertTrue(any(l.startswith(self.P + "`create-ok-01` has an argument object that is not JSON once the "
                                         "handles are strings: ") and l.endswith("(plan-template.md, cases are data)")
                            for l in out.splitlines()), out)
        self.assertEqual(1, code, out)

    def test_23_accepts_handles_placeholders_and_braces_inside_strings(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", "label": "${x} }", '
                                        '"confirm_token": <token of step 1>, "q": "a\\|b", "n": null, "on": true}`')
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    ISO_ROW = '| `list-iso-03` | `kinoa_widget_list {"game_id": "not-a-game"}` | EXPECTED |\n'

    def test_24_flags_a_game_id_that_is_no_zero_value(self):
        code, out = self.check({self.PLAN: current_plan(extra_rows=self.ISO_ROW.replace("EXPECTED", "`ok: false`"))})
        self.assertIn(self.P + '`list-iso-03` sends game_id "not-a-game", which is no §0 value and not named in its '
                      "Expected cell (plan-template.md, cases are data)", out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_24_accepts_a_probe_named_in_its_expected_cell(self):
        row = self.ISO_ROW.replace("EXPECTED", "`ok: false`: the probe `not-a-game` is no uuid")
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_24_flags_a_target_game_id_handle_that_is_not_in_zero(self):
        row = '| `export-ok-01` | `kinoa_widget_export {"game_id": P1, "target_game_id": P9}` | `ok: true` |\n'
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertIn(self.P + "`export-ok-01` sends target_game_id P9, which is no §0 value and not named in its "
                      "Expected cell (plan-template.md, cases are data)", out.splitlines(), out)

    def test_25_flags_a_described_call_and_an_ellipsis_in_an_object(self):
        row = ('| `list-sem-01` | 1. `kinoa_widget_list {"game_id": P1, "page": 1}` 2. the call of step 1 with '
               '`"page": 2`, and so on: one step per page, up to the last page | `ok: true` |\n'
               '| `list-sem-02` | `kinoa_widget_list {"game_id": P1, "ids": [{"a": 1}, …]}` | `ok: true` |\n')
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        lines = out.splitlines()
        for line in (self.P + '`list-sem-01` describes calls instead of writing them: "and so on" (plan-template.md, cases are data)',
                     self.P + '`list-sem-01` describes calls instead of writing them: "up to the last page" (plan-template.md, cases are data)',
                     self.P + '`list-sem-02` describes calls instead of writing them: "…" (plan-template.md, cases are data)'):
            with self.subTest(line=line):
                self.assertIn(line, lines, out)
        self.assertEqual(1, code, out)

    # --- the fix pass after the whole-branch review (0.7.1) ---

    def test_18_a_stamp_scoped_search_prefix_of_an_artifact_is_not_an_artifact(self):
        row = '| `list-sem-01` | `kinoa_widget_list {"game_id": P1, "search": "KEY_a"}` | `ok: true` |\n'
        plan = current_plan(artifacts="| `W_A` | `NAME-a`, key `KEY_a_one` | `P1` | the widget | `create-ok-01` | exists | yes |",
                            extra_rows=row)
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_25_an_ellipsis_inside_a_json_string_is_a_value(self):
        row = ('| `create-rule-01` | `kinoa_widget_create {"game_id": P1, "name": "NAME-a", "description": "Loading…", '
               '"note": "a.....b"}` | `ok: true` |\n')
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_24_reads_the_expected_cell_of_a_row_with_trailing_spaces(self):
        row = self.ISO_ROW.replace("EXPECTED", "`ok: false`: the probe `not-a-game` is no uuid").rstrip("\n") + "   \n"
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_15_a_paused_report_is_checked_once_the_run_finishes(self):
        report = ("# r\n\n## 1. Header\n\n- Run: `20261016-0900`\n\n## 2. Overall status\n\n"
                  "paused — handed over after `create-ok-01`; the counts follow when the run finishes\n\n"
                  "## 3. What was done, per part\n\n### Case status\n\n"
                  "| Case | Status | Finding / note / blocked row |\n|---|---|---|\n| `pre-01` | `PASS` | — |\n\n"
                  "## 10. Role rows at the end of the run\n\n`ROLES_BEFORE`: `[]`. `not restored`.\n")
        code, out = self.check({"reports/KING-99001-widgets-test-report-20261016-0900.md": report})
        self.assertEqual([], flagged_lines(out), out)
        self.assertIn("PAUSED: reports/KING-99001-widgets-test-report-20261016-0900.md: the run was handed over; "
                      "it is checked once it finishes (report-spec.md, the overall status)", out.splitlines(), out)
        self.assertEqual(0, code, out)

    def test_15_and_20_a_line_that_only_mentions_paused_is_not_a_paused_report(self):
        report = "# r\n\n## 2. Overall status\n\n`RED`. The run was not paused.\n"
        code, out = self.check({"plans/KING-99001-widgets-test-plan.md": current_plan(),
                                "reports/KING-99001-widgets-test-report-20261012-0900.md": report})
        self.assertTrue(any(l.startswith("WARN: plans/KING-99001-widgets-test-plan.md: **Earlier runs:** none")
                            for l in out.splitlines()), out)

    # --- the deferred minors of the review, and check 26 (0.7.1, second fix pass) ---

    def test_24_a_quoted_part_of_a_zero_value_is_no_zero_value(self):
        row = '| `list-iso-04` | `kinoa_widget_list {"game_id": "7d3e"}` | `ok: false` |\n'
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertIn(self.P + '`list-iso-04` sends game_id "7d3e", which is no §0 value and not named in its '
                      "Expected cell (plan-template.md, cases are data)", out.splitlines(), out)

    def test_24_prints_a_placeholder_value_whole(self):
        row = '| `export-ok-01` | `kinoa_widget_export {"game_id": P1, "target_game_id": <id of step 1>}` | `ok: true` |\n'
        code, out = self.check({self.PLAN: current_plan(extra_rows=row)})
        self.assertIn(self.P + "`export-ok-01` sends target_game_id <id of step 1>, which is no §0 value and not "
                      "named in its Expected cell (plan-template.md, cases are data)", out.splitlines(), out)

    def test_23_accepts_a_placeholder_that_holds_an_arrow(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", '
                                        '"confirm_token": <token of step 1 -> preview>}`')
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)

    def test_18_a_key_after_a_hyphen_is_not_a_key_literal(self):
        plan = current_plan(create_call='`kinoa_widget_create {"game_id": P1, "name": "NAME-a", "ref": "a-KEY_q"}`')
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)

    PLAN_V1 = "plans/KING-99001-widgets-test-plan.md"

    def schema_rows(self, *numbers):
        return "".join('| `create-schema-{:02d}` | `kinoa_widget_create {{"game_id": P1, "size": {}}}` | '
                       "`error.code` = `VALIDATION_FAILED` |\n".format(n, n) for n in numbers)

    def v2(self, rows):
        return current_plan(extra_rows=rows).replace("**Plan version:** 1 (2026-10-16)", "**Plan version:** 2 (2026-10-16)")

    def test_26_flags_a_new_id_that_skips_the_next_free_number(self):
        code, out = self.check({self.PLAN_V1: current_plan(extra_rows=self.schema_rows(1, 2, 3)),
                                self.PLAN_V2: self.v2(self.schema_rows(1, 2, 3, 5))})
        self.assertEqual(["PROBLEM: plans/KING-99001-widgets-test-plan-v2.md: `create-schema-05` is not the next free "
                          "number of `create-schema`: KING-99001-widgets-test-plan.md ends the group at 03, so the "
                          "next is 04 (plan-template.md, stable case ids)"], flagged_lines(out), out)
        self.assertEqual(1, code, out)

    def test_26_a_new_group_starts_at_01_and_the_next_free_number_passes(self):
        rows = self.schema_rows(1, 2, 3, 4) + ('| `create-gap-01` | `kinoa_widget_create {"game_id": P1, "size": 0}` | '
                                               '`ok: false` |\n')
        code, out = self.check({self.PLAN_V1: current_plan(extra_rows=self.schema_rows(1, 2, 3)),
                                self.PLAN_V2: self.v2(rows)})
        self.assertEqual([], [l for l in flagged_lines(out) if "next free number" in l], out)

    def test_the_new_row_checks_skip_a_plan_dated_before_2026_10_16(self):
        row = ('| `list-sem-01` | 1. `kinoa_widget_list {"game_id": "not-a-game", "page": 1}` 2. and so on, up to the '
               'last page, with `"key": "KEY_b"` | `ok: true` |\n')
        plan = current_plan(extra_rows=row).replace("**Plan version:** 1 (2026-10-16)", "**Plan version:** 1 (2026-10-15)")
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)



def current_plan(create_call='`kinoa_widget_create {"game_id": "7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b", "name": "NAME-a", "size": 3}`',
                 artifacts="| `W_A` | `NAME-a` | `P1` | the widget | `create-ok-01` | exists | yes |",
                 earlier_runs="none", known_issues="", header_extra="", extra_rows="",
                 extra_sections="", version_date="2026-10-16"):
    """A minimal plan under the current layout (version date 2026-10-16, or `version_date`) that
    passes every check of check-layout.sh as written; a test breaks one thing in it and looks for
    the line it gets."""
    return ("# KING-99001 — widgets via the AI agent: Test Plan\n\n"
            "**Story:** https://kinoadev.atlassian.net/browse/KING-99001\n"
            "**Under test:** `kinoa_widget_create`, on the **deployed test stand**\n"
            "**Plan version:** 1 (" + version_date + ")\n"
            "**Earlier runs:** " + earlier_runs + "\n"
            "**Decisions from the interview:** artifacts are kept\n" + header_extra +
            "**Checked against:** `tools/list of 2026-10-16; server source not available`\n\n"
            "## 0. Fixed test data\n\n| Constant | Value |\n|---|---|\n"
            "| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |\n"
            "| `NAME` | `KING99001-QA-<STAMP>` |\n\n"
            "| Handle | `name` | Game | What it is | Created in | Intended end state | Expected |\n"
            "|---|---|---|---|---|---|---|\n" + artifacts + "\n\n"
            "**Name limit:** 30 — no `maxLength`; longest name 28, longest key 0\n\n"
            "## 1. Execution rules\n\n`mcp-plan references/rules.md`.\n\n"
            "### 1.1 Known deviations to confirm through the protocol\n\n"
            "| # | AC / expectation | What `tools/list` says | Cases |\n|---|---|---|---|\n\n"
            + known_issues + extra_sections +
            "# PART A — everything that needs no permission change\n\n## A0. Preflight\n\n"
            "| Id | Call | Expected |\n|---|---|---|\n"
            "| `pre-01` | `tools/list` | `kinoa_widget_create` is listed |\n"
            "| `pre-02` | `kinoa_system_ping {}` | `data.userId` present. `Record: USER_ID` |\n\n"
            "## A1. `kinoa_widget_create`\n\n| Id | Call | Expected |\n|---|---|---|\n"
            "| `create-ok-01` | 1. " + create_call + " 2. the call of step 1 plus `\"confirm_token\": <token of step 1>` "
            "| 1. `meta.confirmToken` present. 2. `data.created` = `true`. `Record: W_A` |\n" + extra_rows +
            "\n# REPORT\n\nThe report contract is `mcp-plan references/report-spec.md`.\n")

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


class RulesPass20261016(unittest.TestCase):
    """The rules the eval run of 2026-10-16 added (0.7.1): every printed command has its line in
    the closed list of rules.md, and the two SKILL files print them."""

    GIT_LINE = ("git -C <repo root> fetch --quiet && git -C <repo root> status --branch --porcelain | head -1"
                " && git -C <repo root> rev-parse --short HEAD")
    GREP_REPORT = "grep -nE '^## |^### Case status|Plan defect' ~/.kinoa-qa/mcp/reports/<report file>"
    SEEDED = FIXTURE_TREE + "/reports/KING-99003-user-lists-test-report-20260923-1400.md"

    def test_the_printed_heading_search_finds_the_headings_of_a_report(self):
        line = next(l.split(" #")[0].strip() for _, l, _ in fenced_lines(read(PLAN_SKILL))
                    if l.startswith("grep -n"))
        command = line.replace("~/.kinoa-qa/mcp/reports/<report file>", self.SEEDED)
        result = subprocess.run(["bash", "-c", command], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, command + "\n" + result.stdout + result.stderr)
        found = result.stdout.splitlines()
        self.assertTrue(any(":## 1. Header" in l for l in found), result.stdout)
        self.assertTrue(any(":### Case status" in l for l in found), result.stdout)

    def test_the_closed_list_names_the_search_with_extended_patterns(self):
        method = section(read_flat(REFERENCES + "/rules.md"), "Target and method")
        self.assertIn("`grep -nE '<pattern>' <file>`", method)
        self.assertNotIn("`grep -n '<pattern>' <file>`", method)

    def test_the_review_fixes_of_0_7_1_are_in_their_homes(self):
        template = read_flat(REFERENCES + "/plan-template.md")
        self.assertIn("check 18 reads the `NAME-`, `NAME_S-` and `KEY_` literals", template)
        self.assertIn("check 24", section(template, "Cases are data, prose is commentary"))
        self.assertIn("stays in its clause's row", template)
        self.assertIn("`paused — handed over after <case id>`",
                      section(read_flat(REFERENCES + "/report-spec.md"), "The overall status"))
        self.assertIn("its §1.2 row", section(read_flat(REFERENCES + "/file-layout.md"), "Comparing runs"))
        self.assertIn("shows no re-read", section(read_flat(REFERENCES + "/rules.md"), "Statuses"))
        plan_skill = read_flat(PLAN_SKILL)
        self.assertNotIn("the eval run of 2026-10-16", plan_skill)
        self.assertNotIn("section 8 from its first plan-defect row", plan_skill)
        self.assertIn("no command", section(read_flat(RUN_SKILL), "3. Finish"))
        for doc in (PLAN_SKILL, RUN_SKILL):
            with self.subTest(doc=doc):
                self.assertIn('"A quick `ls -la` or `echo` changes nothing"', read_flat(doc))

    def test_the_second_fix_pass_of_0_7_1_is_in_its_homes(self):
        template = read_flat(REFERENCES + "/plan-template.md")
        for check in ("check 23", "check 25"):
            with self.subTest(check=check):
                self.assertIn(check, section(template, "Cases are data, prose is commentary"))
        self.assertIn("check 26", section(template, "Stable case ids"))
        part_ab = section(read_flat(REFERENCES + "/rules.md"), "Part A / Part B")
        self.assertIn("measured as the time of a wait", part_ab)
        self.assertIn("the rows in effect are unknown", part_ab)
        run = section(read_flat(RUN_SKILL), "1. Find the files")
        self.assertIn("Each command runs at the step that names it", run)
        self.assertNotIn("no snapshot `GET` of its own before B1", run)

    def test_the_plan_skill_prints_the_sha_with_the_branch_state(self):
        self.assertTrue(fences_command(read(PLAN_SKILL), self.GIT_LINE))
        self.assertIn("`git rev-parse`", section(read_flat(REFERENCES + "/rules.md"), "Target and method"))

    def test_the_plan_skill_prints_the_heading_search_for_a_harness_with_no_file_search_tool(self):
        self.assertTrue(fences_command(read(PLAN_SKILL), self.GREP_REPORT))
        method = section(read_flat(REFERENCES + "/rules.md"), "Target and method")
        for form in ("`grep -nE '<pattern>' <file>`", "`grep -rlE '<pattern>' <folder>`",
                     "no file-search tool"):
            with self.subTest(form=form):
                self.assertIn(form, method)

    def test_the_planner_reads_the_case_status_table_and_reports_what_it_only_read(self):
        skill = read_flat(PLAN_SKILL)
        self.assertIn("`### Case status` table of section 3", section(skill, "1. Find what exists"))
        self.assertIn("`checked by reading, not verified`", section(skill, "3. Check the tree"))

    def test_the_research_rows_are_one_per_clause_and_whitespace_rules_get_two_cases(self):
        template = read_flat(REFERENCES + "/plan-template.md")
        self.assertIn("One row per clause that a case can check on its own", template)
        self.assertIn("a whitespace-only value", template)
        readers = read_flat(REFERENCES + "/story-readers.md")
        self.assertIn("about another surface", readers)

    def test_a_report_from_a_transcript_has_its_rules(self):
        run = section(read_flat(RUN_SKILL), "1. Find the files")
        for phrase in ("takes the stamp the operator gives and runs no `date`",
                       "says the file was created, not resumed",
                       "A plan with no Part B"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, run)
        self.assertIn("as `not captured`", section(read_flat(REFERENCES + "/rules.md"), "Statuses"))
        label = "`not re-checked (last seen: status <x> in <case>)`"
        self.assertIn(label, section(read_flat(REFERENCES + "/report-blocks.md"), "The artifact contract"))
        self.assertIn(label, read_flat(REFERENCES + "/language.md"))


class Segments20261109(unittest.TestCase):
    """Check 27 of check-layout.sh (KING-24108): a plan dated 2026-11-09 or later carries a
    `### 1.4 Segments` table that cuts Part A into consecutive segments, with no handle used in a
    segment before the segment that records it."""

    PLAN = "plans/KING-99001-widgets-test-plan.md"
    P = "PROBLEM: plans/KING-99001-widgets-test-plan.md: "
    TAIL = " (plan-template.md, §1.4)"
    HEAD = "### 1.4 Segments\n\n| Segment | Sections | Reads | Records | Writes | Note |\n|---|---|---|---|---|---|\n"
    TABLE_ROW = "| S1 | A1 | — | `W_A` | 1 | widgets |"
    TABLE_HEADER = "| Id | Call | Expected |\n|---|---|---|\n"

    def check(self, files):
        data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, data, ignore_errors=True)
        for folder in FIXTURE_FOLDERS:
            os.makedirs(os.path.join(data, folder))
        for rel_path, text in files.items():
            with open(os.path.join(data, rel_path), "w", encoding="utf-8") as handle:
                handle.write(text)
        result = run_bash(CHECK_LAYOUT, data)
        return result.returncode, result.stdout + result.stderr

    def segmented(self, table_rows, extra_rows="", version_date="2026-11-09", after_sections=""):
        return current_plan(version_date=version_date, extra_sections=self.HEAD + table_rows + "\n\n",
                            extra_rows=extra_rows).replace("\n# REPORT", after_sections + "\n# REPORT")

    def section(self, number, title, rows):
        return "\n## A%d. %s\n\n%s%s" % (number, title, self.TABLE_HEADER, "".join(rows))

    def update_section(self, number, call_tail='"game_id": P1', expected="`ok: true`", cid="update-ok-01"):
        return self.section(number, "`kinoa_widget_update`",
                            ["| `%s` | `kinoa_widget_update {%s}` | %s |\n" % (cid, call_tail, expected)])

    def unwired(self, out):
        """The PROBLEM lines other than the wiring of a `grey-NN` row, which these plans leave bare."""
        return [l for l in flagged_lines(out) if "is wired to no" not in l]

    def only(self, out):
        return [l for l in out.splitlines() if "§1.4" in l]

    def test_a_plan_dated_2026_11_09_without_1_4_fails(self):
        code, out = self.check({self.PLAN: current_plan(version_date="2026-11-09")})
        self.assertIn(self.P + "§1.4 Segments is missing" + self.TAIL, out.splitlines(), out)
        self.assertEqual(1, code, out)

    def test_a_1_4_heading_with_no_table_row_is_missing_too(self):
        code, out = self.check({self.PLAN: current_plan(version_date="2026-11-09",
                                                        extra_sections=self.HEAD + "\n")})
        self.assertEqual([self.P + "§1.4 Segments is missing" + self.TAIL], self.only(out), out)

    def test_a_plan_dated_before_the_gate_is_not_checked(self):
        code, out = self.check({self.PLAN: current_plan()})
        self.assertEqual([], self.only(out), out)
        self.assertEqual(0, code, out)
        code, out = self.check({self.PLAN: current_plan(version_date="2026-11-08")})
        self.assertEqual([], self.only(out), out)

    def test_one_segment_over_the_one_tool_section_passes(self):
        code, out = self.check({self.PLAN: self.segmented(self.TABLE_ROW)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_a_section_in_no_segment_and_a_section_in_two(self):
        rows = self.update_section(2)
        code, out = self.check({self.PLAN: self.segmented("| S1 | A1 | — | — | 1 | a |", extra_rows=rows)})
        self.assertIn(self.P + "section A2 is in no segment of §1.4" + self.TAIL, out.splitlines(), out)
        self.assertEqual(1, code, out)
        two = "| S1 | A1–A2 | — | — | 1 | a |\n| S2 | A2 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(two, extra_rows=rows)})
        self.assertIn(self.P + "section A2 is in two segments of §1.4: S1, S2" + self.TAIL, out.splitlines(), out)
        self.assertNotIn("not consecutive", out)

    def test_segments_that_skip_a_section_are_not_consecutive(self):
        rows = self.update_section(2) + self.update_section(3, cid="update-ok-02")
        table = "| S1 | A1 | — | — | 1 | a |\n| S2 | A3 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertIn(self.P + "the segments of §1.4 are not consecutive: S1 ends at A1, S2 starts at A3" + self.TAIL,
                      out.splitlines(), out)

    def test_a_second_segment_that_starts_before_the_first_ends_is_not_consecutive(self):
        rows = self.update_section(2)
        table = "| S1 | A2 | — | — | 1 | a |\n| S2 | A1 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertIn(self.P + "the segments of §1.4 are not consecutive: S1 ends at A2, S2 starts at A1" + self.TAIL,
                      out.splitlines(), out)

    def test_an_en_dash_and_a_hyphen_range_both_read(self):
        rows = self.update_section(2)
        for dash in ("–", "-"):
            with self.subTest(dash=dash):
                code, out = self.check({self.PLAN: self.segmented("| S1 | A1%sA2 | — | — | 1 | a |" % dash,
                                                                  extra_rows=rows)})
                self.assertEqual([], flagged_lines(out), out)
                self.assertEqual(0, code, out)

    def test_a_handle_recorded_in_a_later_segment_fails(self):
        rows = (self.update_section(2, '"game_id": P1, "ref": W_B', cid="update-ok-01")
                + self.section(3, "`kinoa_widget_create`", ["| `create-ok-02` | `kinoa_widget_create {\"game_id\": P1}` "
                                                             "| `ok: true`. `Record: W_B` |\n"]))
        table = "| S1 | A1–A2 | — | — | 1 | a |\n| S2 | A3 | — | `W_B` | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertEqual([self.P + "`W_B` is used in segment S1 (`update-ok-01`) but recorded in segment S2 "
                          "(`create-ok-02`)" + self.TAIL], self.only(out), out)
        self.assertEqual(1, code, out)
        same = "| S1 | A1–A3 | — | `W_B` | 1 | a |"
        code, out = self.check({self.PLAN: self.segmented(same, extra_rows=rows)})
        self.assertEqual([], flagged_lines(out), out)

    def test_a_zero_constant_used_as_a_handle_is_not_reported(self):
        rows = (self.update_section(2)
                + self.section(3, "`kinoa_widget_create`", ["| `create-ok-02` | `kinoa_widget_create {\"game_id\": P1}` "
                                                             "| `ok: true`. `Record: P1` |\n"]))
        table = "| S1 | A1–A2 | — | — | 1 | a |\n| S2 | A3 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertEqual([], flagged_lines(out), out)
        self.assertEqual(0, code, out)

    def test_a_handle_recorded_in_a0_counts_as_recorded_before_s1(self):
        later = self.section(3, "`kinoa_widget_create`", ["| `create-ok-02` | `kinoa_widget_create {\"game_id\": P1}` "
                                                           "| `ok: true`. `Record: USER_ID` |\n"])
        rows = self.update_section(2, '"game_id": P1, "by": USER_ID') + later
        table = "| S1 | A1–A2 | — | — | 1 | a |\n| S2 | A3 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertEqual([], flagged_lines(out), out)

    def test_a_use_of_a_handle_no_tool_section_records_is_not_reported(self):
        rows = self.update_section(2, '"game_id": P1, "ref": ROLES_BEFORE')
        code, out = self.check({self.PLAN: self.segmented("| S1 | A1–A2 | — | — | 1 | a |", extra_rows=rows)})
        self.assertEqual([], flagged_lines(out), out)

    def test_a_use_in_part_b_grey_or_hand_off_is_not_reported(self):
        grey = self.section(2, "Grey box", ["| `grey-01` | `kinoa_widget_create {\"game_id\": P1, \"ref\": W_B}` | `ok: true` |\n"])
        handoff = self.section(3, "Hand-off", ["| `handoff-01` | `kinoa_widget_get {\"game_id\": P1, \"ref\": W_B}` | `ok: true` |\n"])
        last = self.section(4, "`kinoa_widget_update`", ["| `update-ok-01` | `kinoa_widget_update {\"game_id\": P1}` "
                                                        "| `ok: true`. `Record: W_B` |\n"])
        part_b = ("# PART B — role-gated checks\n\n## B1. Checkpoint 1 — GAME Viewer on `P1`\n\n" + self.TABLE_HEADER +
                  "| `role-create-01` | `kinoa_widget_create {\"game_id\": P1, \"ref\": W_B}` | "
                  "`error.code` = `PERMISSION_DENIED` |\n\n")
        plan = self.segmented("| S1 | A1 | — | — | 1 | a |\n| S2 | A4 | — | `W_B` | 1 | b |",
                              extra_rows=grey + handoff + last, after_sections="\n" + part_b)
        plan = plan.replace("| `pre-01` | `tools/list` | `kinoa_widget_create` is listed |",
                            "| `pre-01` | `tools/list` and W_B | `kinoa_widget_create` is listed |")
        code, out = self.check({self.PLAN: plan})
        self.assertEqual([], self.only(out), out)

    def test_a_grey_row_inside_a_tool_section_must_be_named_in_the_grey_paragraph(self):
        row = ("| `grey-06` | `kinoa_widget_create {\"game_id\": P1}` | `ok: true` |\n")
        for prose, named in (("The seams of the guard; `grey-01` replays the token.", False),
                             ("The seams of the guard; `grey-06` mints the token.", True)):
            with self.subTest(named=named):
                grey = ("\n## A2. Grey box\n\n" + prose + "\n\n" + self.TABLE_HEADER
                        + "| `grey-01` | `kinoa_widget_create {\"game_id\": P1}` | `ok: true` |\n")
                code, out = self.check({self.PLAN: self.segmented("| S1 | A1 | — | — | 1 | a |",
                                                                  extra_rows=row + grey)})
                line = self.P + "`grey-06` sits in section A1 and the paragraph of §Grey does not name it" + self.TAIL
                if named:
                    self.assertEqual([], self.only(out), out)
                else:
                    self.assertEqual([line], self.only(out), out)

    def test_a_cell_with_an_escaped_pipe_still_yields_the_handle_and_the_use(self):
        use = ("| `create-ok-02` | `kinoa_widget_create {\"game_id\": P1, \"name\": \"a \\| b\", \"ref\": W_B}` "
               "| `ok: true` |\n")
        rec = self.update_section(2, expected="`x` = `a \\| b`. `Record: W_B`")
        table = "| S1 | A1 | — | — | 1 | a |\n| S2 | A2 | — | `W_B` | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=use + rec)})
        self.assertEqual([self.P + "`W_B` is used in segment S1 (`create-ok-02`) but recorded in segment S2 "
                          "(`update-ok-01`)" + self.TAIL], self.only(out), out)


    GREY_A2 = ("\n## A2. Grey box\n\nThe seams of the guard; `grey-01` replays the token.\n\n" + TABLE_HEADER
               + "| `grey-01` | `kinoa_widget_create {\"game_id\": P1}` | `ok: true` |\n")

    def test_a_grey_box_after_one_tool_section_needs_no_segment(self):
        code, out = self.check({self.PLAN: self.segmented(self.TABLE_ROW, extra_rows=self.GREY_A2)})
        self.assertEqual([], self.unwired(out), out)

    def test_a_hand_off_section_needs_no_segment_either(self):
        handoff = self.section(3, "Hand-off", ["| `handoff-01` | `kinoa_widget_get {\"game_id\": P1}` | `ok: true` |\n"])
        code, out = self.check({self.PLAN: self.segmented(self.TABLE_ROW, extra_rows=self.GREY_A2 + handoff)})
        self.assertEqual([], self.unwired(out), out)

    def test_a_row_that_names_a_section_that_is_no_tool_section_fails(self):
        table = self.TABLE_ROW + "\n| S2 | A9 | — | — | 1 | b |"
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=self.GREY_A2)})
        self.assertEqual([self.P + "segment S2 names A9, which is not a Part A tool section" + self.TAIL],
                         self.only(out), out)
        self.assertEqual(1, code, out)
        for named, shown in (("A2", "A2"), ("A1–A2", "A2"), ("A0", "A0")):
            with self.subTest(named=named):
                code, out = self.check({self.PLAN: self.segmented("| S1 | %s | — | — | 1 | a |" % named,
                                                                  extra_rows=self.GREY_A2)})
                self.assertIn(self.P + "segment S1 names %s, which is not a Part A tool section" % shown + self.TAIL,
                              out.splitlines(), out)

    def test_consecutive_is_judged_over_the_tool_sections_only(self):
        rows = self.update_section(2) + self.GREY_A2.replace("A2.", "A3.") + self.update_section(4, cid="update-ok-02")
        table = ("| S1 | A1 | — | — | 1 | a |\n| S2 | A2 | — | — | 1 | b |\n"
                 "| S3 | A4 | — | — | 1 | c |")
        code, out = self.check({self.PLAN: self.segmented(table, extra_rows=rows)})
        self.assertEqual([], self.unwired(out), out)
        skip = "| S1 | A1 | — | — | 1 | a |\n| S2 | A4 | — | — | 1 | c |"
        code, out = self.check({self.PLAN: self.segmented(skip, extra_rows=rows)})
        self.assertIn(self.P + "the segments of §1.4 are not consecutive: S1 ends at A1, S2 starts at A4" + self.TAIL,
                      out.splitlines(), out)



class ConfigNamesTheSegmentModel(unittest.TestCase):
    def test_config_names_the_segment_model(self):
        self.assertEqual("sonnet", json.loads(read("config.json"))["mcp"]["segment_model"])


class SectionWrites20261109(unittest.TestCase):
    """KING-24108 0.8.1: a segment agent writes the report per plan section, and a lost section is
    re-run. Text checks: these markdown files are the implementation the agents follow."""

    REFS = "skills/mcp-plan/references/"

    def flat(self, rel_path, heading=None):
        text = read(rel_path)
        if heading is not None:
            text = section_lines(text, heading)
        return " ".join(text.split())

    def test_capture_at_the_call_names_the_segment_agent_exception(self):
        text = self.flat(self.REFS + "rules.md", "## Capture at the call")
        self.assertIn("A segment agent writes per plan section", text)
        self.assertIn("segments.md", text)

    def test_segments_md_has_the_compaction_stop_and_the_lost_section(self):
        text = self.flat(self.REFS + "segments.md")
        self.assertIn("stopped: context compacted", text)
        self.assertIn("## A lost section", read(self.REFS + "segments.md"))
        lost = self.flat(self.REFS + "segments.md", "## A lost section")
        for word in ("re-run", "section 9", "section 8"):
            with self.subTest(word=word):
                self.assertIn(word, lost)

    def test_a_stop_mid_section_writes_what_it_holds(self):
        text = self.flat(self.REFS + "segments.md", "## Stop conditions")
        self.assertIn("the last section it ran has its rows", text)

    def test_a_lost_section_has_one_trigger_and_its_subjects_reach_section_9_at_the_finish(self):
        lost = self.flat(self.REFS + "segments.md", "## A lost section")
        self.assertIn("returned nothing or returned `stopped: context compacted`, and the section has "
                      "no row", lost)
        self.assertIn("Nothing else makes a section lost", lost)
        self.assertNotIn("the return names", lost)
        self.assertNotIn("the section is not lost", lost)
        self.assertIn("The recovery agent writes no section 9 row", lost)
        self.assertIn("name and id of every subject", lost)
        text = self.flat(self.REFS + "segments.md")
        self.assertIn("lost-section line of section 3 lists are ids the run created", text)
        run = self.flat("skills/mcp-run/SKILL.md")
        self.assertNotIn("fresh subjects", run)

    def test_fixed_data_names_the_re_run_suffix(self):
        text = self.flat(self.REFS + "fixed-data.md", "## Naming every artifact")
        self.assertIn("`r<n>`", text)

    def test_the_run_skill_no_longer_says_one_case_at_a_time_in_every_agent(self):
        text = self.flat("skills/mcp-run/SKILL.md")
        self.assertNotIn("in the main chat and in every segment agent", text)
        self.assertTrue("(segments.md, a lost section)" in text or "segments.md#a-lost-section" in text)

    def test_the_context_red_flag_names_the_segment_exception(self):
        rows = [l for l in read("skills/mcp-run/SKILL.md").splitlines()
                if l.startswith("| \"I'll write up this section's cases once it is done\"")]
        self.assertEqual(1, len(rows), rows)
        self.assertIn("segment agent", rows[0])
        answer = rows[0].strip().strip("|").split(" | ")[-1]
        self.assertLessEqual(len(answer.split()), 25, answer)


def split_table_row(line):
    """The cells of one markdown table row. A `\\|` inside a cell is part of the cell, not a
    delimiter; the cell keeps a plain `|`."""
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") and not inner.endswith("\\|") else inner
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", inner)]


class ReadingTable20261109(unittest.TestCase):
    """KING-24108 0.8.1: a segment agent reads only the reference sections its reading table
    lists, and the main chat loads only its own tool schemas."""

    REFS = "skills/mcp-plan/references/"
    READERS = {"segment", "check", "section 9"}

    def flat(self, rel_path, heading=None):
        text = read(rel_path)
        if heading is not None:
            text = section_lines(text, heading)
        return " ".join(text.split())

    def rows(self):
        """The data rows of the table under `## What a segment agent reads`, as cell lists."""
        body = section_lines(read(self.REFS + "segments.md"), "## What a segment agent reads")
        table = [l for l in body.splitlines() if l.startswith("|")]
        self.assertGreater(len(table), 3, "no table under the heading")
        self.assertEqual(["File", "Heading", "Read by"], split_table_row(table[0]))
        out = [split_table_row(l) for l in table[2:]]
        for cells in out:
            self.assertEqual(3, len(cells), cells)
        return out

    def test_the_parser_keeps_an_escaped_pipe_inside_a_cell(self):
        cells = split_table_row("| `a.md` | `## One \\| two` | segment, check |")
        self.assertEqual(["`a.md`", "`## One | two`", "segment, check"], cells)

    def test_every_heading_of_the_table_exists_in_its_file(self):
        checked = 0
        for file_name, heading, _ in self.rows():
            if not (heading.startswith("`") and heading.endswith("`")):
                continue
            heading = heading.strip("`")
            lines = [l.rstrip() for l in read(self.REFS + file_name.strip("`")).splitlines()]
            with self.subTest(file=file_name, heading=heading):
                self.assertIn(heading, lines)
            checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_read_by_holds_only_known_readers(self):
        for file_name, heading, read_by in self.rows():
            for part in read_by.split(","):
                part = re.sub(r"\s*\(.*\)\s*$", "", part).strip()
                with self.subTest(file=file_name, heading=heading, part=part):
                    self.assertIn(part, self.READERS)

    def test_pauses_is_not_read_by_a_segment_agent(self):
        for file_name, heading, read_by in self.rows():
            if heading.strip("`") == "## Pauses":
                self.assertNotIn("segment", [re.sub(r"\s*\(.*\)\s*$", "", p).strip()
                                             for p in read_by.split(",")])

    def test_the_brief_no_longer_points_at_the_whole_file_checklist(self):
        brief = " ".join(section_lines(read(self.REFS + "segments.md"), "## The brief").split())
        self.assertNotIn("step 1 of the post-compaction checklist", brief)
        self.assertIn("what-a-segment-agent-reads", brief)

    def test_segments_md_no_longer_sends_a_segment_agent_to_the_checklist(self):
        text = " ".join(read(self.REFS + "segments.md").split())
        for old in ("as steps 2 and 3 of the post-compaction", "as step 6 of the post-compaction",
                    "the post-compaction checklist, step 4", "with the references of step 1"):
            with self.subTest(old=old):
                self.assertNotIn(old, text)

    def test_no_pauses_pointer_remains_in_segments_md(self):
        for n, line in enumerate(read(self.REFS + "segments.md").splitlines(), 1):
            with self.subTest(line=n):
                self.assertNotIn("pauses", line.lower(), line)

    def test_the_connector_stop_points_at_the_connector_case_b(self):
        stops = self.flat(self.REFS + "segments.md", "## Stop conditions")
        self.assertIn("[the connector](rules.md#the-connector), case b): `stopped: connector lost`", stops)
        self.assertNotIn("sent again in place", stops)
        connector = self.flat(self.REFS + "stand-facts.md", "## Connector")
        self.assertNotIn("the lost call is sent again in place", connector)
        self.assertIn("for a lost executing leg too", connector)
        self.assertIn("`rules.md` (the connector)", connector)

    def test_the_pointer_counts_of_the_brief_agree_with_the_intro(self):
        text = read(self.REFS + "segments.md")
        intro = " ".join(text.split("Contents:")[0].split())
        intro_n = re.search(r"reads the (\w+) sections its brief points at", intro).group(1)
        brief = " ".join(section_lines(text, "## The brief").split())
        pointer_n = re.search(r"to its (\w+) sections", brief).group(1)
        self.assertEqual(intro_n, pointer_n)
        ordinal = {"three": "fourth", "four": "fifth", "five": "sixth"}[pointer_n]
        self.assertIn("and a {} pointer, to [a lost section]".format(ordinal), brief)
        self.assertIn("reads a " + ordinal, intro)

    def test_the_contents_line_and_the_intro_name_the_reading_table(self):
        text = read(self.REFS + "segments.md")
        contents = next(l for l in text.splitlines() if l.startswith("Contents:"))
        self.assertIn("(#what-a-segment-agent-reads)", contents)
        self.assertIn("## What a segment agent reads", text.splitlines())

    def test_a_segment_agent_loads_its_schemas_by_exact_name(self):
        text = " ".join(read(self.REFS + "segments.md").split())
        self.assertIn("by exact name, in one load", text)
        self.assertIn("`ToolSearch` with `select:`", text)

    def test_the_main_chat_loads_its_schemas_by_exact_name(self):
        text = " ".join(read(RUN_SKILL).split())
        self.assertIn("by exact name, in one load", text)

    def test_the_layout_doc_names_the_reading_table_in_the_segments_row(self):
        rows = [l for l in read(self.REFS + "file-layout.md").splitlines()
                if "| `segments.md`" in l or l.rstrip().endswith("`segments.md` — execution chat and its segment agents |")]
        self.assertEqual(1, len(rows), rows)
        self.assertIn("reading table", rows[0])


class CheckAgent20261109(unittest.TestCase):
    """KING-24108 0.8.1: at the finish a check agent re-reads the rows `check-layout.sh grades`
    lists and proposes corrections; the main chat applies them."""

    REFS = "skills/mcp-plan/references/"

    def flat(self, rel_path, heading=None):
        text = read(rel_path)
        if heading is not None:
            text = section_lines(text, heading)
        return " ".join(text.split())

    def test_segments_md_has_the_check_agent_and_its_return_shape(self):
        text = read(self.REFS + "segments.md")
        self.assertIn("## The check agent", text.splitlines())
        agent = section_lines(text, "## The check agent")
        for phrase in ("correct: <case id>", "unsupported:", "doubt: <case id>", "never edits",
                       "checked: <n> rows", "done | stopped: <reason>"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, agent)

    def test_the_check_agent_brief_points_at_the_reading_table_and_the_grades_lines(self):
        agent = self.flat(self.REFS + "segments.md", "## The check agent")
        self.assertIn("(#what-a-segment-agent-reads)", agent)
        self.assertIn("check-layout.sh", agent)
        self.assertIn("grades", agent)
        self.assertIn("`mcp.segment_model`", agent)
        self.assertIn("previous report", agent)

    def test_the_contents_line_and_the_intro_name_the_check_agent(self):
        text = read(self.REFS + "segments.md")
        contents = " ".join(text.split("Contents:")[1].split("\n\n")[0].split())
        self.assertIn("(#the-check-agent)", contents)
        intro = " ".join(text.split("Contents:")[0].split())
        self.assertIn("the check agent", intro)

    def test_a_check_row_of_the_reading_table_exists(self):
        body = self.flat(self.REFS + "segments.md", "## What a segment agent reads")
        self.assertRegex(body, r"\| [^|]*\bcheck\b[^|]* \|")

    def test_the_finish_runs_the_check_before_check_layout(self):
        finish = self.flat(RUN_SKILL, "## 3. Finish")
        self.assertIn("check agent", finish)
        self.assertIn("check-layout.sh", finish)
        self.assertLess(finish.index("check agent"), finish.index("check-layout.sh"))

    def test_the_finish_applies_each_correction_in_the_main_chat(self):
        finish = self.flat(RUN_SKILL, "## 3. Finish")
        for phrase in ("`correct:`", "finding block", "response not captured", "withdraw",
                       "section 8", "check line"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, finish)

    def test_the_finish_writes_the_section_9_paragraph_from_its_return(self):
        finish = self.flat(RUN_SKILL, "## 3. Finish")
        self.assertIn("section 3 paragraph of the section 9 agent", finish)
        self.assertIn("`deviations`", finish)

    def test_the_closed_list_names_three_forms(self):
        target = self.flat(self.REFS + "rules.md", "## Target and method")
        self.assertIn("`check-layout.sh` in its three forms", target)
        self.assertNotIn("both its forms", target)

    def test_report_spec_names_the_check_line(self):
        recorded = self.flat(self.REFS + "report-spec.md", "## Recorded values and segment paragraphs")
        self.assertIn("check agent", recorded)

    def test_the_layout_doc_owns_the_grades_mode_and_the_check_agent(self):
        layout = self.flat(self.REFS + "file-layout.md")
        self.assertIn("`check-layout.sh grades`", layout)
        self.assertIn("check agent", layout)

    def test_a_fail_that_becomes_any_other_status_loses_its_finding(self):
        finish = self.flat(RUN_SKILL, "## 3. Finish")
        self.assertIn("a `FAIL` that becomes any other status has its finding withdrawn", finish)
        self.assertIn("unless the block still accounts for another `FAIL` case", finish)
        self.assertIn("its id leaves the line that opens section 4", finish)
        self.assertIn("the finding ids and the finding count that the corrections left", finish)

    def test_the_segments_list_names_the_check_agent_as_a_finish_agent(self):
        used = self.flat(self.REFS + "segments.md", "## When segments are used")
        self.assertIn("the section 9 agent re-resolves the created ids at the finish", used)
        self.assertIn("the check agent re-reads the risky grades", used)
        self.assertIn("the rest of the finish stay in the main chat", used)


def subsection_lines(text, heading):
    """From the line that is `heading` up to the next heading of the same or a higher level, as the
    reading table of segments.md tells an agent to read."""
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"#{1,%d} " % level, lines[i])), len(lines))
    return "\n".join(lines[start:end])


class FinalReview20261110(unittest.TestCase):
    """KING-24108 0.8.1, the final review: a write that may have gone out without an answer has one
    home that a segment agent reads; a lost section has one trigger; a segment agent reads the plan
    header, §1 and §1.1; the fixed-label third cell is pinned."""

    REFS = "skills/mcp-plan/references/"
    WRITE = "### A write that may have gone out without an answer"
    ANCHOR = "#a-write-that-may-have-gone-out-without-an-answer"

    def flat(self, text):
        return " ".join(text.split())

    def rules(self):
        return read(self.REFS + "rules.md")

    def table_rows(self):
        body = section_lines(read(self.REFS + "segments.md"), "## What a segment agent reads")
        return [split_table_row(l) for l in body.splitlines() if l.startswith("| `")]

    def test_the_write_rule_has_one_home_under_pauses(self):
        text = self.rules()
        lines = text.splitlines()
        self.assertIn(self.WRITE, lines)
        self.assertIn("### The connector", lines)
        self.assertGreater(lines.index(self.WRITE), lines.index("## Pauses"))
        home = self.flat(subsection_lines(text, self.WRITE))
        for phrase in ("Read the subject first", "grade the case on its outcome read",
                       "Write the confirm envelope as not captured", "`BLOCKED — response not captured`",
                       "send the same confirm again with the same token",
                       "send the preview again first", "Here the server never answered the chat"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, home)
        self.assertEqual(1, self.flat(text).count("Here the server never answered the chat"))

    def test_the_reading_table_lists_both_headings_for_segment(self):
        rows = {(f.strip("`"), h.strip("`")): r for f, h, r in self.table_rows()}
        for heading in ("### The connector", self.WRITE):
            with self.subTest(heading=heading):
                self.assertIn(("rules.md", heading), rows)
                self.assertIn("segment", [p.strip() for p in rows[("rules.md", heading)].split(",")])

    def test_the_reading_rule_stops_at_a_higher_heading_too(self):
        body = self.flat(section_lines(read(self.REFS + "segments.md"), "## What a segment agent reads"))
        self.assertIn("reads to the next heading of the same or a higher level", body)

    def test_the_connector_subsection_holds_no_other_bold_section_of_pauses(self):
        connector = subsection_lines(self.rules(), "### The connector")
        self.assertNotIn("**A chat that resumes inside Part B**", connector)
        self.assertNotIn("post-compaction checklist.**", connector)

    def test_every_pointer_goes_to_the_one_home(self):
        text = self.rules()
        checklist = self.flat(text.split("**After stage — the post-compaction checklist.**")[1]
                              .split("**A checkpoint and the four ways")[0])
        step4 = checklist.split(" 4. ")[1].split(" 5. ")[0]
        step8 = checklist.split(" 8. ")[1].split(" 9. ")[0]
        for name, step in (("step 4", step4), ("step 8", step8)):
            with self.subTest(step=name):
                self.assertIn("(" + self.ANCHOR + ")", step)
        self.assertNotIn("decide the retry", step8)
        connector = self.flat(subsection_lines(text, "### The connector"))
        case_a = connector.split("(a) ")[1].split("(b) ")[0]
        case_b = connector.split("(b) ")[1]
        self.assertIn("never sent again blind", case_a)
        self.assertIn("(" + self.ANCHOR + ")", case_a)
        self.assertIn("(" + self.ANCHOR + ")", case_b)
        self.assertNotIn("Applied: grade", case_a)

    def test_the_brief_line_points_at_the_write_rule_not_the_retry_rule(self):
        brief = self.flat(section_lines(read(self.REFS + "segments.md"), "## The brief"))
        line = brief.split("**When the first case is a write that an earlier agent may have sent**")[1]
        line = line.split("- **")[0]
        self.assertIn("(rules.md" + self.ANCHOR + ")", line)
        self.assertNotIn("the retry rule", line)

    def test_a_segment_agent_never_hands_over(self):
        connector = self.flat(subsection_lines(self.rules(), "### The connector"))
        self.assertIn("A segment agent never hands over: for it, case (b) is the stop "
                      "`stopped: connector lost`", connector)

    def test_step_3_of_a_lost_section_applies_to_every_lost_section(self):
        lost = section_lines(read(self.REFS + "segments.md"), "## A lost section")
        steps = dict(numbered_steps(lost))
        self.assertIn("This step decides only the suffix", steps[1])
        self.assertIn("This step applies to every lost section", steps[3])
        self.assertIn("`**Name limit:**`", steps[2])
        self.assertNotIn("Name limit", steps[3])
        self.assertIn("a delete whose target the lost attempt already removed", steps[3])

    def test_a_segment_agent_reads_the_plan_header_and_the_preflight_paragraph(self):
        does = self.flat(section_lines(read(self.REFS + "segments.md"), "## What the agent does"))
        self.assertIn("the plan's header lines, §1 and §1.1", does)
        self.assertIn("the preflight paragraph of section 3 of the report", does)

    def test_the_check_agent_reads_the_plan_header_and_states_no_flood_rule(self):
        text = read(self.REFS + "segments.md")
        self.assertNotIn("A flood probe is", self.flat(text))
        agent = self.flat(section_lines(text, "## The check agent"))
        self.assertIn("it reads the plan's header lines by search", agent)
        self.assertIn("rate-limit rules of `stand-facts.md` (budgets)", agent)

    def test_the_section_9_agent_loads_its_schemas_by_name(self):
        body = self.flat(section_lines(read(self.REFS + "segments.md"), "## What a segment agent reads"))
        self.assertIn("The section 9 agent has no `Call` cells: it loads the `_get` and list tools "
                      "of the entities the run created, by exact name, in one load", body)

    def test_report_spec_pins_the_third_cell_of_a_fixed_label_row(self):
        table = self.flat(section_lines(read(self.REFS + "report-spec.md"), "## The case status table"))
        self.assertIn("writes the label in that cell after `section 8: `", table)
        self.assertIn("`check-layout.sh grades` finds these rows by those words", table)

    def test_a_compacted_agent_goes_straight_to_a_lost_section(self):
        run = self.flat(section_lines(read(RUN_SKILL), "## 2."))
        stops = run.split("**When an agent stops or dies.**")[1].split("**One case at a time**")[0]
        self.assertIn("returns `stopped: context compacted` leaves nothing to fix, so the operator is "
                      "not asked", stops)
        self.assertIn("segments.md#a-lost-section", stops)


class ReviewFixes20261110(unittest.TestCase):
    """The review of mcp-run of 2026-11-10: the gaps between SKILL.md and its references."""

    REFS = "skills/mcp-plan/references/"

    def flat(self, text):
        return " ".join(text.split())

    def test_a_section_writes_its_rows_last_and_a_partly_written_one_is_lost(self):
        capture = self.flat(section_lines(read(self.REFS + "rules.md"), "## Capture at the call"))
        self.assertIn("rows of the case status table go in last, all in one edit", capture)
        lost = self.flat(section_lines(read(self.REFS + "segments.md"), "## A lost section"))
        self.assertIn("and the section has no row, or only some of its rows", lost)
        self.assertIn("is removed before the re-run writes its own blocks", lost)

    def test_the_re_run_suffix_is_conditional_in_both_homes(self):
        naming = self.flat(section_lines(read(self.REFS + "fixed-data.md"), "## Naming every artifact"))
        self.assertIn("when the lost attempt left subjects on the stand", naming)
        self.assertIn("with none found, the names carry no suffix", naming)

    def test_a_segment_agent_reads_the_ten_sections(self):
        self.assertIn("## The ten sections", read(self.REFS + "report-spec.md").splitlines())
        body = section_lines(read(self.REFS + "segments.md"), "## What a segment agent reads")
        rows = {(f.strip("`"), h.strip("`")): r for f, h, r in
                (split_table_row(l) for l in body.splitlines() if l.startswith("| `"))}
        readers = [p.strip() for p in rows[("report-spec.md", "## The ten sections")].split(",")]
        self.assertEqual(["segment", "section 9"], readers)
        does = self.flat(section_lines(read(self.REFS + "segments.md"), "## What the agent does"))
        self.assertIn("get their section 8 rows in the same write", does)

    def test_no_bullet_is_glued_to_the_line_before_it(self):
        for name in sorted(os.listdir(os.path.join(ROOT, self.REFS))):
            for n, line in enumerate(read(self.REFS + name).splitlines(), 1):
                with self.subTest(file=name, line=n):
                    self.assertNotRegex(line, r"[.:;]- \*\*")

    def test_the_main_chat_loads_the_part_a_tools_in_a_run_with_no_segments(self):
        run = self.flat(read(RUN_SKILL))
        self.assertIn("in a run with no segments also those of Part A, §Grey and the section 9 re-resolve", run)
        self.assertIn("In a run with no segments, the main chat does it itself.", run)

    def test_every_stop_condition_names_its_return(self):
        stops = section_lines(read(self.REFS + "segments.md"), "## Stop conditions")
        bullets = [b for b in re.split(r"\n(?=- )", stops.split("**Context compacted.**")[0]) if b.startswith("- ")]
        self.assertEqual(4, len(bullets), bullets)
        for bullet in bullets:
            with self.subTest(bullet=bullet[:40]):
                self.assertIn("`stopped: ", bullet)

    def test_pauses_ties_the_segment_agents_to_the_threshold(self):
        pauses = self.flat(section_lines(read(self.REFS + "rules.md"), "## Pauses"))
        self.assertNotIn("handed over at every segment boundary", pauses)
        self.assertIn("In a run with more than 6 tool-section cases, Part A runs in segment agents", pauses)

    def test_every_printed_command_of_step_1_to_8_is_named_by_a_step(self):
        run = self.flat(read(RUN_SKILL))
        for phrase in ("after the `mkdir` and the `ls` of the plans folder",
                       "from the `ls` of the reports folder", "from the row count of §1",
                       "once step 8 has created the report file"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, run)


if __name__ == "__main__":
    unittest.main()
