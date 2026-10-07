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
        self.assertEqual([], flagged, result.stdout + result.stderr)
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

if __name__ == "__main__":
    unittest.main()
