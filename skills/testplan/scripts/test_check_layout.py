# test_check_layout.py
"""check-layout.sh on a temp data folder holding one plan and one report dated on the cut-off days
of checks 15-17, with HOME at a temp folder. Each failing case is the passing pair with one change."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shutil, subprocess, tempfile, unittest

# repo root: skills/testplan/scripts/ -> ../../..
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from test_skill_docs import CHECK_LAYOUT

PLAN_NAME = "KING-99010-widgets-test-plan.md"
REPORT_NAME = "KING-99010-widgets-test-report-20261007-0900.md"

CREATE_OK = ('| `create-ok-01` | 1. `kinoa_widget_create {"game_id": P1, "name": "NAME-a", "size": 3}` '
             '2. the call of step 1 plus `"confirm_token": <token of step 1>` | '
             '1. `meta.confirmToken` present. Also record: `ok: true`; `data.status` = `preview`. '
             '2. `data.created` = `true`. `Record: W_A` |')
CREATE_GAP = ('| `create-gap-01` | `kinoa_widget_create {"game_id": P1, "name": "NAME-z", "size": 0}` | '
              '`error.code` = `VALIDATION_FAILED`. Also record: `ok: false`; no token |')

PLAN = """# KING-99010 — widgets via the AI agent: Test Plan

**Story:** https://kinoadev.atlassian.net/browse/KING-99010
**Under test:** `kinoa_widget_create`, on the **deployed test stand**
**Plan version:** 1 (2026-10-07)
**Report to produce:** `KING-99010-widgets-test-report-<STAMP>.md` in
`~/.kinoa-qa/mcp/reports/`, one file per run
**Earlier runs:** none

## 0. Fixed test data

| Constant | Value |
|---|---|
| `P1` | `7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b` — *Widget sandbox* |
| `STAMP` | UTC `yyyyMMdd-HHmm`, captured once at the start of the run |
| `NAME` | `KING99010-QA-<STAMP>` |

**Name limit:** 30 — no `maxLength` in `tools/list`, no limit in the story; longest name 26, longest key 0

## 1. Execution rules

`mcp-plan references/rules.md`.

### 1.1 Known deviations to confirm through the protocol

| Hypothesis | What the docs say | Cases |
|---|---|---|
| H1 | create refuses a size of 0 | `create-gap-01` |

### 1.2 Known issues and the cases that cover them

None.

# PART A — everything that needs no permission change

## A0. Preflight

| Id | Call | Expected |
|---|---|---|
| `pre-01` | `tools/list` | `kinoa_widget_create` is listed |

## A1. `kinoa_widget_create`

| Id | Call | Expected |
|---|---|---|
{create_ok}
{create_gap}

# PART B — role-gated checks

None.

# REPORT

The report contract is `mcp-plan references/report-spec.md`. What only this domain knows:
- **Section 6**, one row per AC bullet: "an Operator can create widgets" — `create-ok-01`.
"""

REPORT = """# KING-99010 — widgets via the AI agent: Test Report

## 1. Header

- Date (UTC): 2026-10-07 09:00. Stand: the deployed test stand, through the `kinoa` connector.
- Run: `20261007-0900`. Plan file: `KING-99010-widgets-test-plan.md`, version 1.

## 2. Overall status

`GREEN`. Findings: 0. Notes: 0.

| PASS | FAIL | OBSERVED | BLOCKED | Total |
|---|---|---|---|---|
| 3 | 0 | 0 | 0 | 3 |

## 3. What was done, per part

Part A ran start to finish under the `COMPANY` `operator` row.

### Case status

| Case | Status | Finding / note / blocked row |
|---|---|---|
{status_rows}

## 4. Findings

None.

## 5. Notes

None.

## 6. AC traceability

| AC bullet | Cases | Verdict | Finding |
|---|---|---|---|
| an Operator can create widgets | create-ok-01 | PASS | — |

## 7. Hypothesis verdicts

H1: `CONFIRMED` by `create-gap-01`.

## 8. Not covered / blocked

None.

## 9. Artifacts left behind

None.

## 10. Role rows at the end of the run

`ROLES_BEFORE`: `[]`. The last `GET`: no row. `restored`.
"""

STATUS_ROWS = ["| `pre-01` | `PASS` | — |",
               "| `create-ok-01` | `PASS` | — |",
               "| `create-gap-01` | `PASS` | — |"]


def plan(create_ok=CREATE_OK, create_gap=CREATE_GAP):
    return PLAN.replace("{create_ok}", create_ok).replace("{create_gap}", create_gap)


def report(status_rows=STATUS_ROWS):
    return REPORT.replace("{status_rows}", "\n".join(status_rows))


def steps_call(count, escaped_at):
    """A Call cell of `count` numbered steps; step `escaped_at` holds a `\\|` inside its JSON."""
    steps = []
    for n in range(1, count + 1):
        q = "a\\|b" if n == escaped_at else "a"
        steps.append('{}. `kinoa_widget_get {{"game_id": P1, "q": "{}"}}`'.format(n, q))
    return " ".join(steps)


class CheckLayoutAfterCutOff(unittest.TestCase):
    """Checks 15-17 on a plan dated 2026-10-07 and a report stamped 20261007, and check 10 on a
    Call cell whose JSON holds an escaped `\\|`."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()
        for folder in ("plans", "reports"):
            os.makedirs(os.path.join(self.data, folder))

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, rel_path, text):
        with open(os.path.join(self.data, rel_path), "w", encoding="utf-8") as f:
            f.write(text)

    def run_check(self, plan_text=None, report_text=None):
        self.write("plans/" + PLAN_NAME, plan() if plan_text is None else plan_text)
        self.write("reports/" + REPORT_NAME, report() if report_text is None else report_text)
        env = {k: v for k, v in os.environ.items() if not k.startswith("QA_")}
        env["HOME"] = self.home
        return subprocess.run(["bash", CHECK_LAYOUT, self.data], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=300)

    def assertProblem(self, result, line):
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("PROBLEM: " + line, result.stdout.splitlines(), result.stdout)

    def test_passes_on_a_plan_and_a_report_after_the_cut_off(self):
        result = self.run_check()
        flagged = [l for l in result.stdout.splitlines() if l.startswith(("PROBLEM", "WARN", "IN PROGRESS"))]
        # The plan is version 1 and the report of its first run exists, so check 20 warns that a
        # new plan version is due (KING-23440); nothing else is flagged and the check passes.
        self.assertEqual(["WARN: plans/{}: **Earlier runs:** none, but reports/ holds {} — a new plan "
                          "version is due".format(PLAN_NAME, REPORT_NAME)], flagged,
                         result.stdout + result.stderr)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    # 15. The report sections and the case status table.
    def test_15_fails_on_a_status_table_shorter_than_the_total(self):
        result = self.run_check(report_text=report(STATUS_ROWS[:2]))
        self.assertProblem(result, "reports/{}: the case status table has 2 rows, the section 2 "
                                   "Total is 3".format(REPORT_NAME))

    def test_15_fails_on_a_missing_section(self):
        text = report().replace("## 7. Hypothesis verdicts\n\nH1: `CONFIRMED` by `create-gap-01`.\n\n", "")
        result = self.run_check(report_text=text)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertTrue(any(l.startswith("PROBLEM: reports/{}: the ## sections are not the ten of "
                                         "report-spec.md in order".format(REPORT_NAME))
                            for l in result.stdout.splitlines()), result.stdout)

    # 16. The `Also record:` label.
    def test_16_fails_on_a_label_not_written_exactly(self):
        gap = CREATE_GAP.replace("Also record:", "Also record (OBSERVED):")
        result = self.run_check(plan_text=plan(create_gap=gap))
        self.assertProblem(result, "plans/{}: create-gap-01 writes the label in another form than "
                                   "`Also record:` (1 time(s))".format(PLAN_NAME))

    def test_16_reads_a_bad_label_before_an_escaped_pipe(self):
        gap = CREATE_GAP.replace("Also record: `ok: false`", "Also record (OBSERVED): `a\\|b`")
        result = self.run_check(plan_text=plan(create_gap=gap))
        self.assertProblem(result, "plans/{}: create-gap-01 writes the label in another form than "
                                   "`Also record:` (1 time(s))".format(PLAN_NAME))

    # 17. Every gap and grey row is wired.
    def test_17_fails_on_an_unwired_gap_row(self):
        text = plan().replace("| H1 | create refuses a size of 0 | `create-gap-01` |",
                              "| H1 | create refuses a size of 0 | `create-ok-01` |")
        result = self.run_check(plan_text=text)
        self.assertProblem(result, "plans/{}: create-gap-01 is wired to no §1.1 hypothesis and no AC "
                                   "bullet of the REPORT section".format(PLAN_NAME))

    # 10. A `\|` inside a cell is part of the cell, not a column break.
    def test_10_counts_every_step_past_an_escaped_pipe(self):
        row = "| `create-ok-01` | {} | `data.created` = `true`. Also record: `ok: true` |".format(
            steps_call(7, escaped_at=6))
        result = self.run_check(plan_text=plan(create_ok=row))
        self.assertProblem(result, "plans/{}: create-ok-01 has 7 steps (at most 5)".format(PLAN_NAME))

    def test_10_flags_six_steps_with_an_escaped_pipe_in_step_five(self):
        row = "| `create-ok-01` | {} | `data.created` = `true`. Also record: `ok: true` |".format(
            steps_call(6, escaped_at=5))
        result = self.run_check(plan_text=plan(create_ok=row))
        self.assertProblem(result, "plans/{}: create-ok-01 has 6 steps (at most 5)".format(PLAN_NAME))

    # Every other row split keeps a `\|` inside its cell too.
    def test_6_prints_a_whole_zero_value_cell_with_an_escaped_pipe(self):
        text = plan().replace("| `STAMP` |", "| `P2` | TBD \\| ask the operator |\n| `STAMP` |")
        result = self.run_check(plan_text=text)
        self.assertProblem(result, "plans/{}: §0 row without a literal value — `P2`: TBD \\| ask the "
                                   "operator (fixed-data.md, empty means ask)".format(PLAN_NAME))

    def test_13_reads_every_case_of_a_known_issue_cell_with_an_escaped_pipe(self):
        text = plan().replace("### 1.2 Known issues and the cases that cover them\n\nNone.",
                              "### 1.2 Known issues and the cases that cover them\n\n"
                              "| Issue | Status | Cases |\n|---|---|---|\n"
                              "| a size of 0 | open | `bogus-01` \\| `create-gap-01` |")
        result = self.run_check(plan_text=text)
        self.assertProblem(result, "plans/{}: §1.2 names bogus-01, which is no case row of the "
                                   "plan".format(PLAN_NAME))

    def test_15_reads_a_total_cell_with_an_escaped_pipe(self):
        text = report().replace("| 3 | 0 | 0 | 0 | 3 |", "| 3 | 0 | 0 | 0 | 3 \\| all ran |")
        result = self.run_check(report_text=text)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class StatusMode(unittest.TestCase):
    """`check-layout.sh status <report>`: the counts, the last row, the cases with no row, the
    highest finding and note ids, and the recorded handles of section 3."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()
        for folder in ("plans", "reports"):
            os.makedirs(os.path.join(self.data, folder))

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, rel_path, text):
        with open(os.path.join(self.data, rel_path), "w", encoding="utf-8") as f:
            f.write(text)

    def run_bash(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("QA_")}
        env["HOME"] = self.home
        return subprocess.run(["bash", CHECK_LAYOUT, *args], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=300)

    def run_status(self, report_text, plan_text=None):
        """Writes the report and the plan (`plan_text=False`: no plan file) and runs the status mode."""
        plan_text = plan() if plan_text is None else plan_text
        if plan_text is not False:
            self.write("plans/" + PLAN_NAME, plan_text)
        self.write("reports/" + REPORT_NAME, report_text)
        result = self.run_bash("status", os.path.join(self.data, "reports", REPORT_NAME))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def test_prints_counts_last_row_and_no_missing_case(self):
        out = self.run_status(report()).stdout.splitlines()
        self.assertEqual("PASS 3 \u00b7 FAIL 0 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 3 of 3", out[0])
        self.assertEqual("last row: create-gap-01", out[1])
        self.assertEqual("no row: none", out[2])
        self.assertEqual(["highest finding: none", "highest note: none"], out[3:5])

    def test_counts_every_status_and_a_row_the_plan_does_not_have(self):
        rows = ["| `pre-01` | `PASS` | \u2014 |",
                "| `create-ok-01` | `FAIL` | F1 |",
                "| `create-gap-01` | `OBSERVED` | N1 |",
                "| `extra-01` | `BLOCKED` | row 4 |"]
        out = self.run_status(report(rows)).stdout.splitlines()
        self.assertEqual("PASS 1 \u00b7 FAIL 1 \u00b7 OBSERVED 1 \u00b7 BLOCKED 1 \u00b7 rows 4 of 3", out[0])
        self.assertEqual("last row: extra-01", out[1])

    def test_lists_the_plan_cases_with_no_row_in_plan_order(self):
        out = self.run_status(report(STATUS_ROWS[:1])).stdout.splitlines()
        self.assertEqual("PASS 1 \u00b7 FAIL 0 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 1 of 3", out[0])
        self.assertEqual("no row: create-ok-01 create-gap-01", out[2])

    def test_reads_the_highest_finding_and_note_ids(self):
        text = report().replace("## 4. Findings\n\nNone.", "## 4. Findings\n\n### F2 \u2014 x   [severity: minor]\n\n### F10 \u2014 y   [severity: minor]")
        text = text.replace("## 5. Notes\n\nNone.", "## 5. Notes\n\n### N3 \u2014 z   [impact: low]")
        out = self.run_status(text).stdout.splitlines()
        self.assertEqual(["highest finding: F10", "highest note: N3"], out[3:5])

    def test_a_fenced_finding_or_note_heading_is_not_an_id(self):
        fence = "```markdown\n### F9 — an example   [severity: minor]\n### N7 — an example   [impact: low]\n```"
        text = report().replace("## 4. Findings\n\nNone.", "## 4. Findings\n\n### F2 — x   [severity: minor]\n\n" + fence)
        out = self.run_status(text).stdout.splitlines()
        self.assertEqual(["highest finding: F2", "highest note: none"], out[3:5])

    def test_prints_every_record_of_section_3_with_its_line(self):
        text = report().replace("Part A ran start to finish under the `COMPANY` `operator` row.",
            "`Record: W_A` = `6e5d = a \\| b`. Then `Record: BASE_P1` not recorded (pre-05).")
        line = [n for n, l in enumerate(text.splitlines(), 1) if "Record: W_A" in l][0]
        self.assertEqual(18, line)
        out = self.run_status(text).stdout
        self.assertIn("record: W_A = `6e5d = a \\| b` (line {})".format(line), out)
        self.assertIn("record: BASE_P1 not recorded (line {})".format(line), out)

    def test_a_record_value_without_backticks_is_not_cut_at_a_space(self):
        text = report().replace("Part A ran start to finish under the `COMPANY` `operator` row.",
            "Record: W_A = the confirm token of step 1. Then `Record: W_B` = `x`.")
        out = self.run_status(text).stdout
        self.assertIn("record: W_A = the confirm token of step 1 (line 18)", out)
        self.assertIn("record: W_B = `x` (line 18)", out)

    def test_a_record_value_without_backticks_runs_to_the_end_of_the_line(self):
        text = report().replace("Part A ran start to finish under the `COMPANY` `operator` row.",
            "Record: W_A = the token of step 1")
        self.assertIn("record: W_A = the token of step 1 (line 18)", self.run_status(text).stdout)

    def test_a_record_outside_section_3_is_not_printed(self):
        text = report().replace("## 4. Findings\n\nNone.", "## 4. Findings\n\n`Record: W_B` = `x`")
        self.assertNotIn("record:", self.run_status(text).stdout)

    def test_resolves_the_plan_from_the_bullet_and_the_link_forms(self):
        for line in ("- **Plan file:** `../plans/{p}` \u2014 plan version 1 (2026-10-07)".format(p=PLAN_NAME),
                     "**Plan file:** [`{p}`](../plans/{p})".format(p=PLAN_NAME)):
            with self.subTest(line=line):
                text = report().replace("- Run: `20261007-0900`. Plan file: `{}`, version 1.".format(PLAN_NAME), line)
                self.assertTrue(self.run_status(text).stdout.startswith("PASS 3 \u00b7 FAIL 0 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 3 of 3"))

    def test_a_missing_report_is_a_usage_error(self):
        result = self.run_bash("status", os.path.join(self.data, "reports", "nope.md"))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout + result.stderr)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root reads a chmod 000 file")
    def test_an_unreadable_report_is_a_usage_error(self):
        path = os.path.join(self.data, "reports", REPORT_NAME)
        self.write("reports/" + REPORT_NAME, report())
        os.chmod(path, 0)
        try:
            result = self.run_bash("status", path)
        finally:
            os.chmod(path, 0o644)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("usage:", result.stdout + result.stderr)
        self.assertNotIn("PASS", result.stdout)

    def test_the_data_folder_form_and_the_dash_argument_behave_as_before(self):
        self.write("plans/" + PLAN_NAME, plan()); self.write("reports/" + REPORT_NAME, report())
        self.assertEqual(0, self.run_bash(self.data).returncode)
        self.assertEqual(2, self.run_bash("--status").returncode)

    def test_a_row_with_an_escaped_pipe_in_an_early_cell_keeps_its_status(self):
        # The Case cell holds `\\|`: split on every `|`, the status would be read from the wrong cell.
        rows = [STATUS_ROWS[0], STATUS_ROWS[1], "| `create-gap-01` \\| re-run | `FAIL` | F1 a\\|b |"]
        out = self.run_status(report(rows)).stdout.splitlines()
        self.assertEqual("PASS 2 \u00b7 FAIL 1 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 3 of 3", out[0])
        self.assertEqual("last row: create-gap-01\\|re-run", out[1])

    def test_a_record_value_that_holds_an_escaped_pipe_prints_whole(self):
        text = report().replace("Part A ran start to finish under the `COMPANY` `operator` row.",
            "`Record: W_A` = `a \\| b \\| c`.")
        self.assertIn("record: W_A = `a \\| b \\| c` (line 18)", self.run_status(text).stdout)

    def test_a_plan_that_is_not_found_prints_a_question_mark(self):
        out = self.run_status(report(), plan_text=False).stdout.splitlines()
        self.assertEqual("PASS 3 \u00b7 FAIL 0 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 3 of ?", out[0])
        self.assertEqual("no row: ? (plan not found: {}/reports/../plans/{})".format(self.data, PLAN_NAME), out[2])

    def test_an_in_progress_report_still_prints_the_five_header_lines(self):
        text = report()
        text = text[:text.index("## 4. Findings")]
        out = self.run_status(text).stdout.splitlines()
        self.assertEqual(["PASS 3 \u00b7 FAIL 0 \u00b7 OBSERVED 0 \u00b7 BLOCKED 0 \u00b7 rows 3 of 3",
                          "last row: create-gap-01", "no row: none",
                          "highest finding: none", "highest note: none"], out)

PREVIOUS_REPORT_NAME = "KING-99010-widgets-test-report-20261006-0900.md"


class GradesMode(unittest.TestCase):
    """`check-layout.sh grades <report> [<previous report>]`: the rows a check agent re-grades."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()
        for folder in ("plans", "reports"):
            os.makedirs(os.path.join(self.data, folder))

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)

    def write(self, rel_path, text):
        with open(os.path.join(self.data, rel_path), "w", encoding="utf-8") as f:
            f.write(text)

    def path(self, name):
        return os.path.join(self.data, "reports", name)

    def run_bash(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("QA_")}
        env["HOME"] = self.home
        return subprocess.run(["bash", CHECK_LAYOUT, *args], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=300)

    def run_grades(self, rows, previous_rows=None):
        """Writes the report (and the previous report) from the rows and runs the grades mode."""
        self.write("plans/" + PLAN_NAME, plan())
        self.write("reports/" + REPORT_NAME, report(rows))
        args = ["grades", self.path(REPORT_NAME)]
        if previous_rows is not None:
            self.write("reports/" + PREVIOUS_REPORT_NAME, report(previous_rows))
            args.append(self.path(PREVIOUS_REPORT_NAME))
        result = self.run_bash(*args)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result.stdout.splitlines()

    def test_without_a_previous_report_prints_every_non_pass_row(self):
        rows = ["| `pre-01` | `PASS` | \u2014 |",
                "| `create-ok-01` | `FAIL` | F1 |",
                "| `create-gap-01` | `OBSERVED` | N1 |",
                "| `extra-01` | `BLOCKED` | section 8: x |"]
        self.assertEqual(["create-ok-01 FAIL", "create-gap-01 OBSERVED", "extra-01 BLOCKED",
                          "targeted 3 of 4"], self.run_grades(rows))

    def test_a_changed_grade_names_the_previous_status(self):
        previous = ["| `pre-01` | `FAIL` | F1 |", "| `create-ok-01` | `PASS` | \u2014 |"]
        rows = ["| `pre-01` | `PASS` | \u2014 |", "| `create-ok-01` | `FAIL` | F2 |"]
        out = self.run_grades(rows, previous)
        self.assertIn("pre-01 PASS was FAIL", out)
        self.assertIn("create-ok-01 FAIL was PASS", out)

    def test_a_non_pass_case_missing_from_the_previous_report_is_new(self):
        rows = [STATUS_ROWS[0], "| `extra-01` | `BLOCKED` | section 8: x |", "| `extra-02` | `PASS` | \u2014 |"]
        out = self.run_grades(rows, [STATUS_ROWS[0]])
        self.assertIn("extra-01 BLOCKED new", out)
        self.assertFalse([l for l in out if l.startswith("extra-02")], out)

    def test_matches_by_case_id_not_by_row_order(self):
        previous = list(reversed(STATUS_ROWS))
        out = self.run_grades(STATUS_ROWS, previous)
        self.assertFalse([l for l in out if " was " in l], out)

    def test_skips_the_fixed_label_blocked_rows(self):
        rows = ["| `pre-01` | `PASS` | \u2014 |",
                "| `create-ok-01` | `BLOCKED` | section 8: excluded by the operator (2026-11-04) |",
                "| `create-gap-01` | `BLOCKED` | section 8: writes disabled server-side (dry-run) |"]
        previous = ["| `pre-01` | `PASS` | \u2014 |", "| `create-ok-01` | `PASS` | \u2014 |",
                    "| `create-gap-01` | `PASS` | \u2014 |"]
        self.assertEqual(["targeted 0 of 3"], self.run_grades(rows, previous))

    def test_a_fixed_label_previous_row_counts_as_no_previous_row(self):
        previous = ["| `pre-01` | `PASS` | — |",
                    "| `create-ok-01` | `BLOCKED` | section 8: a \\| excluded by the operator (2026-11-04) |",
                    "| `create-gap-01` | `BLOCKED` | section 8: writes disabled server-side (dry-run) |",
                    "| `extra-01` | `BLOCKED` | section 8: excluded by the operator (2026-11-04) |"]
        rows = ["| `pre-01` | `PASS` | — |", "| `create-ok-01` | `PASS` | — |",
                "| `create-gap-01` | `PASS` | — |", "| `extra-01` | `FAIL` | F1 |"]
        self.assertEqual(["extra-01 FAIL new", "targeted 1 of 4"], self.run_grades(rows, previous))

    def test_a_third_cell_with_an_escaped_pipe_keeps_the_status(self):
        rows = ["| `create-ok-01` | `FAIL` | F1 \\| N2 |"]
        self.assertIn("create-ok-01 FAIL", self.run_grades(rows))

    def test_a_fixed_label_after_an_escaped_pipe_is_still_skipped(self):
        rows = ["| `create-ok-01` | `BLOCKED` | a \\| excluded by the operator (2026-11-04) |"]
        self.assertEqual(["targeted 0 of 1"], self.run_grades(rows))

    def test_usage_errors_exit_2(self):
        self.write("reports/" + REPORT_NAME, report())
        self.write("reports/" + PREVIOUS_REPORT_NAME, report())
        rep, prev = self.path(REPORT_NAME), self.path(PREVIOUS_REPORT_NAME)
        cases = {"missing report": ["grades", self.path("nope.md")],
                 "four arguments": ["grades", rep, prev, prev],
                 "no report": ["grades"],
                 "dash argument": ["grades", "-x", rep]}
        if not (hasattr(os, "geteuid") and os.geteuid() == 0):
            cases["unreadable previous"] = ["grades", rep, prev]
        for name, args in cases.items():
            with self.subTest(name):
                if name == "unreadable previous":
                    os.chmod(prev, 0)
                try:
                    result = self.run_bash(*args)
                finally:
                    os.chmod(prev, 0o644)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn("usage:", result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
