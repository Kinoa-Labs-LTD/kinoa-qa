> **Superseded — historical record (2026-09-07).** Vocabulary here (e.g. `source: scenario:`) no longer matches the plugin and now fails validation. Current authority: `skills/testplan/references/`.

# kinoa-qa Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone `kinoa-qa` Claude Code plugin that turns a Jira Story (+ optional Confluence PRD + optional service-repo OpenSpec specs) into a validator-checked Test Plan and, after a human gate, idempotently upserts Test Cases into Allure TestOps.

**Architecture:** A single orchestrator skill (`testplan`) drives five steps — assemble SoT → generate (fresh-context subagent, QA lens) → deterministic validate (Python) → human gate → idempotent TestOps upsert. Every external system sits behind a thin adapter (`SpecResolver` via `gh`/filesystem, `RequirementsReader` via Atlassian MCP, `TestOpsWriter` via Allure MCP). Deterministic logic lives in three small, tested, stdlib-only Python modules; everything else is skill/reference prose the agent follows.

**Tech Stack:** Claude Code plugin (`.claude-plugin/plugin.json` + `marketplace.json`, mirroring kinoa-dev); Python 3 (stdlib only) for the validator/parser/payload modules + `unittest`/`pytest`; Atlassian MCP (Jira + Confluence); Allure TestOps MCP (V2 create/update/find testcase, AQL); GitHub `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-09-04-kinoa-qa-plugin-design.md` (in this same repo)

## Global Constraints

- **Python scripts are stdlib-only** — no third-party imports (`argparse`, `json`, `os`, `re`, `sys`, `unittest`). Every `open()` uses `encoding="utf-8"`.
- **Plugin packaging mirrors kinoa-dev exactly:** `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`, plugin `source: "./"`.
- **The slash command derives from the skill NAME.** Skill dir `skills/testplan/` → command `/kinoa-qa:testplan`. (Lesson carried from flow-test-plan — do not advertise any other command name.)
- **Service repos are READ-ONLY.** The plugin never writes to a service repo. It writes only to Allure TestOps (after the human gate) and to a local `test-plan.md` working file.
- **TestOps is the system of record.** `test-plan.md` is a reviewable intermediate. TestOps V2 create/update expose `name`, `description`, `precondition`, `expectedResult`, `scenario.steps[{type:"body",body}]`, `tags[str]`, `links[{name,url}]` — **there is no first-class severity field**, so `priority` maps to a `priority-<p>` tag (a Severity custom field is optional, only if `testops_get_project` confirms one exists).
- **Idempotency key = a unique tag** `tp-<slug>` on each case; re-runs find via AQL `tags = "tp-<slug>"` → update if found, else create. Never match on the (editable) title.
- **`source:` grammar (machine-readable, validator-enforced):** exactly one of `scenario: <Requirement>/<Scenario>` | `ac: AC-<n>` | `QA-added: <reason>`. (This supersedes the human-prose `source` line shown illustratively in design-doc §8.)
- **No fabrication.** An untestable/scenario-less requirement gets a `## Gaps` `- ⚠️ GAP: <Requirement> — <reason>` line (em dash U+2014), never an invented case.
- **Jira base URL:** `https://kinoadev.atlassian.net`. **TestOps project:** `KINOA` (numeric `project_id` resolved at run time / from `config.json`).
- **Only the Jira Story is a required input.** PRD and specs each degrade independently; a Story-only or Story+PRD run is a first-class mode.

---

## File Structure

```
kinoa-qa/
├─ .claude-plugin/plugin.json          # T1 — manifest (mirror kinoa-dev)
├─ .claude-plugin/marketplace.json     # T1 — install source, plugin source "./"
├─ .gitignore                          # T1 — __pycache__, *.pyc, workspace dir
├─ README.md                           # T1 — overwrite the seed readme
├─ config.json                         # T1 — { testops.project_name, testops.project_id, jira_base_url }
├─ services.json                       # T7 — optional service→repo override registry
├─ skills/testplan/
│  ├─ SKILL.md                         # T8 — orchestrator, Steps A–E
│  ├─ references/
│  │  ├─ sot-assembly.md               # T7 — RequirementsReader + SpecResolver mechanics
│  │  ├─ generation.md                 # T6 — QA-lens derivation rules, no-fabrication
│  │  ├─ test-plan-format.md           # T5 — exact format + TestOps field mapping + 2 goldens
│  │  └─ testops-sync.md               # T7 — TestOpsWriter: AQL find→update|create, dry-run
│  ├─ scripts/
│  │  ├─ plan_parser.py                # T2 — pure parsers (cases/spec/gaps/acs)
│  │  ├─ validate_test_plan.py         # T3 — deterministic checks, --spec optional
│  │  ├─ testops_payload.py            # T4 — case→TestOps payload + traceability tag
│  │  ├─ test_plan_parser.py           # T2
│  │  ├─ test_validate_test_plan.py    # T3
│  │  └─ test_testops_payload.py       # T4
│  └─ evals/
│     ├─ evals.json                    # T9 — mirror flow-test-plan harness format
│     └─ fixtures/                     # T5/T9 — spec.md + golden test-plan.md fixtures
└─ docs/superpowers/{specs,plans}/…    # already present
```

---

### Task 1: Repo scaffold & plugin packaging

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `.gitignore`
- Create: `config.json`
- Modify: `README.md` (overwrite seed)
- Create: `skills/testplan/scripts/` and `skills/testplan/references/` and `skills/testplan/evals/fixtures/` (via a `.gitkeep` in each empty dir)
- Test: `scripts/check_packaging.py` (throwaway assertion run, not shipped) — or inline `python3 -c`

**Interfaces:**
- Produces: the plugin skeleton every later task writes into; `config.json` shape `{"testops":{"project_name":"KINOA","project_id":null},"jira_base_url":"https://kinoadev.atlassian.net"}` consumed by SKILL.md (T8) and testops-sync.md (T7).

- [ ] **Step 1: Write `.claude-plugin/plugin.json`**

```json
{
  "name": "kinoa-qa",
  "description": "QA plugin: builds Allure TestOps test cases from Jira Story + PRD + OpenSpec specs. Standalone, decoupled from kinoa-dev.",
  "version": "0.1.0",
  "author": {
    "name": "Dmytro Kapeliukh",
    "email": "d.kapeliukh@kinoa.io"
  },
  "homepage": "https://github.com/Kinoa-Labs-LTD/kinoa-qa",
  "repository": "https://github.com/Kinoa-Labs-LTD/kinoa-qa.git",
  "keywords": ["jira", "confluence", "openspec", "allure-testops", "qa", "test-plan", "kinoa"]
}
```

- [ ] **Step 2: Write `.claude-plugin/marketplace.json`**

```json
{
  "name": "kinoa-qa",
  "description": "QA plugin: Jira Story + PRD + OpenSpec specs -> Allure TestOps test cases",
  "owner": { "name": "Dmytro Kapeliukh", "email": "d.kapeliukh@kinoa.io" },
  "plugins": [
    {
      "name": "kinoa-qa",
      "source": "./",
      "version": "0.1.0",
      "description": "QA test-plan + TestOps case generator: the /kinoa-qa:testplan orchestrator skill",
      "homepage": "https://github.com/Kinoa-Labs-LTD/kinoa-qa",
      "author": { "name": "Dmytro Kapeliukh", "email": "d.kapeliukh@kinoa.io" }
    }
  ]
}
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.DS_Store
skills/testplan/evals/_runs/
```

- [ ] **Step 4: Write `config.json`**

```json
{
  "testops": { "project_name": "KINOA", "project_id": null },
  "jira_base_url": "https://kinoadev.atlassian.net"
}
```

- [ ] **Step 5: Overwrite `README.md`**

```markdown
# kinoa-qa

QA plugin for Claude Code. Turns a Jira Story (+ optional Confluence PRD + optional
service-repo OpenSpec specs) into a validator-checked QA **Test Plan**, then — after a
human review gate — idempotently upserts **Test Cases into Allure TestOps** (project KINOA).

Standalone and decoupled from `kinoa-dev`: it depends only on the artifacts kinoa-dev
produces (OpenSpec `spec.md` files in service repos) and the Jira/[AQA] conventions.

## Usage

```
/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>] [--spec-path <dir>] [--dry-run]
```

See `docs/superpowers/specs/` for the design and `skills/testplan/SKILL.md` for the flow.
```

- [ ] **Step 6: Create empty dirs with `.gitkeep`**

Run:
```bash
mkdir -p skills/testplan/scripts skills/testplan/references skills/testplan/evals/fixtures
touch skills/testplan/references/.gitkeep skills/testplan/evals/fixtures/.gitkeep
```

- [ ] **Step 7: Verify packaging JSON parses and has required keys**

Run:
```bash
python3 -c "import json; p=json.load(open('.claude-plugin/plugin.json')); m=json.load(open('.claude-plugin/marketplace.json')); c=json.load(open('config.json')); assert p['name']=='kinoa-qa'; assert m['plugins'][0]['source']=='./'; assert c['testops']['project_name']=='KINOA'; print('packaging OK')"
```
Expected: prints `packaging OK`, exit 0.

- [ ] **Step 8: Commit**

```bash
git add .claude-plugin config.json .gitignore README.md skills/testplan
git commit -m "feat: scaffold kinoa-qa plugin packaging + skill skeleton"
```

---

### Task 2: `plan_parser.py` — pure parsers

**Files:**
- Create: `skills/testplan/scripts/plan_parser.py`
- Test: `skills/testplan/scripts/test_plan_parser.py`

**Interfaces:**
- Produces (consumed by T3, T4):
  - `parse_spec(spec_text) -> (scenarios:set[str "Req/Scn"], reqs_without:set[str "Req"])`
  - `parse_cases(plan_text) -> list[dict{"id","title","tags":dict,"steps":list[str]}]`
  - `parse_gaps(plan_text) -> set[str "Req"]`
  - `parse_acs(plan_text) -> dict{"AC-<n>": "text"}`

- [ ] **Step 1: Write the failing test**

```python
# test_plan_parser.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from plan_parser import parse_spec, parse_cases, parse_gaps, parse_acs

SPEC = """## capability
### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
#### Scenario: Bad password
- WHEN y
### Requirement: Rate limiting
"""

PLAN = """# QA Test Plan — svc / cap
story: KING-1 · target: svc/cap@main · generated: 2026-09-07 · spec-sha: abc

## Acceptance Criteria
- AC-1: Users can sign in
- AC-2: Bad passwords are rejected

## Cases

### TC-1 · Happy path sign-in
- type: functional
- priority: P1
- source: scenario: Sign-in/Happy path
- preconditions: a user exists
- steps:
  1. enter valid credentials
  2. submit
- expected: the user is signed in

## Gaps
- ⚠️ GAP: Rate limiting — spec states no observable behavior to assert
"""

class TestParsers(unittest.TestCase):
    def test_parse_spec_scenarios_and_scenarioless_reqs(self):
        scenarios, reqs_without = parse_spec(SPEC)
        self.assertEqual(scenarios, {"Sign-in/Happy path", "Sign-in/Bad password"})
        self.assertEqual(reqs_without, {"Rate limiting"})

    def test_parse_cases_fields_and_steps(self):
        cases = parse_cases(PLAN)
        self.assertEqual(len(cases), 1)
        c = cases[0]
        self.assertEqual(c["id"], "TC-1")
        self.assertEqual(c["title"], "Happy path sign-in")
        self.assertEqual(c["tags"]["type"], "functional")
        self.assertEqual(c["tags"]["source"], "scenario: Sign-in/Happy path")
        self.assertEqual(c["tags"]["preconditions"], "a user exists")
        self.assertEqual(c["tags"]["expected"], "the user is signed in")
        self.assertEqual(len(c["steps"]), 2)

    def test_parse_gaps(self):
        self.assertEqual(parse_gaps(PLAN), {"Rate limiting"})

    def test_parse_acs(self):
        self.assertEqual(parse_acs(PLAN), {"AC-1": "Users can sign in", "AC-2": "Bad passwords are rejected"})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/testplan/scripts && python3 -m pytest test_plan_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'plan_parser'`.

- [ ] **Step 3: Write minimal implementation**

```python
# plan_parser.py
"""Pure parsers for kinoa-qa test-plan.md and OpenSpec spec.md. stdlib-only."""
import re


def parse_spec(spec_text):
    """Return (scenarios:set['Req/Scn'], reqs_without_scenarios:set['Req'])."""
    scenarios = set()
    req_scn = {}
    current_req = None
    for line in spec_text.splitlines():
        m = re.match(r"^###\s+Requirement:\s+(.*\S)\s*$", line)
        if m:
            current_req = m.group(1).strip()
            req_scn.setdefault(current_req, 0)
            continue
        m = re.match(r"^####\s+Scenario:\s+(.*\S)\s*$", line)
        if m and current_req is not None:
            scenarios.add(f"{current_req}/{m.group(1).strip()}")
            req_scn[current_req] += 1
    reqs_without = {r for r, n in req_scn.items() if n == 0}
    return scenarios, reqs_without


def parse_cases(plan_text):
    """Return list of dicts: {id, title, tags:{k:v}, steps:[...]}."""
    cases = []
    cur = None
    in_steps = False
    for line in plan_text.splitlines():
        m = re.match(r"^###\s+(TC-\S+)\s+·\s+(.*\S)\s*$", line)
        if m:
            if cur:
                cases.append(cur)
            cur = {"id": m.group(1), "title": m.group(2).strip(), "tags": {}, "steps": []}
            in_steps = False
            continue
        if cur is None:
            continue
        if line.startswith("### ") or line.startswith("## "):
            cases.append(cur)
            cur = None
            in_steps = False
            continue
        m = re.match(r"^-\s+([a-z]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            cur["tags"][key] = val
            in_steps = (key == "steps")
            continue
        if in_steps and re.match(r"^\s+\d+\.\s+\S", line):
            cur["steps"].append(line.strip())
    if cur:
        cases.append(cur)
    return cases


def parse_gaps(plan_text):
    """Return set of requirement names named in `## Gaps` GAP lines."""
    gaps = set()
    in_gaps = False
    for line in plan_text.splitlines():
        if re.match(r"^##\s+Gaps\s*$", line):
            in_gaps = True
            continue
        if in_gaps and line.startswith("## "):
            in_gaps = False
        if in_gaps:
            m = re.match(r"^-\s+⚠️\s+GAP:\s+(.*?)\s+—", line)
            if m:
                gaps.add(m.group(1).strip())
    return gaps


def parse_acs(plan_text):
    """Return {AC-<n>: text} from the `## Acceptance Criteria` section."""
    acs = {}
    in_ac = False
    for line in plan_text.splitlines():
        if re.match(r"^##\s+Acceptance Criteria\s*$", line):
            in_ac = True
            continue
        if in_ac and line.startswith("## "):
            in_ac = False
        if in_ac:
            m = re.match(r"^-\s+(AC-\d+):\s+(.*\S)\s*$", line)
            if m:
                acs[m.group(1)] = m.group(2).strip()
    return acs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/testplan/scripts && python3 -m pytest test_plan_parser.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/testplan/scripts/plan_parser.py skills/testplan/scripts/test_plan_parser.py
git commit -m "feat: plan_parser — pure parsers for spec/cases/gaps/acceptance-criteria"
```

---

### Task 3: `validate_test_plan.py` — deterministic checks (both modes)

**Files:**
- Create: `skills/testplan/scripts/validate_test_plan.py`
- Test: `skills/testplan/scripts/test_validate_test_plan.py`

**Interfaces:**
- Consumes: `plan_parser.parse_spec/parse_cases/parse_gaps/parse_acs` (T2).
- Produces (consumed by SKILL Step C, evals): `validate(plan_path, spec_path=None) -> report:dict` with `report["ok"]:bool` and `report["checks"]:list[{name,ok,detail}]`; CLI `validate_test_plan.py <plan> [--spec <spec>] [--json]`, exit 0 pass / 1 fail. Check names: `required-fields`, `source-valid`, `scenario-coverage`, `ac-coverage`, `gap-honesty`.

- [ ] **Step 1: Write the failing test**

```python
# test_validate_test_plan.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest, tempfile
from validate_test_plan import validate

SPEC = """### Requirement: Sign-in
#### Scenario: Happy path
- WHEN x
### Requirement: Rate limiting
"""

PLAN_SPEC_MODE = """# QA Test Plan — svc / cap
## Cases
### TC-1 · Happy path
- type: functional
- priority: P1
- source: scenario: Sign-in/Happy path
- preconditions: a user exists
- steps:
  1. enter valid credentials
- expected: signed in
## Gaps
- ⚠️ GAP: Rate limiting — no observable behavior to assert
"""

PLAN_BUSINESS_MODE = """# QA Test Plan — KING-1 (business-only)
## Acceptance Criteria
- AC-1: Users can sign in
- AC-2: Bad passwords rejected
## Cases
### TC-1 · Sign in
- type: functional
- priority: P1
- source: ac: AC-1
- preconditions: a user exists
- steps:
  1. sign in
- expected: signed in
### TC-2 · Reject bad password
- type: negative
- priority: P1
- source: ac: AC-2
- preconditions: a user exists
- steps:
  1. sign in with wrong password
- expected: rejected
## Gaps
"""

def _write(tmp, text):
    p = os.path.join(tmp, "f.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p

class TestValidate(unittest.TestCase):
    def test_spec_mode_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            spec = os.path.join(tmp, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            r = validate(plan, spec)
            self.assertTrue(r["ok"], r["checks"])

    def test_business_mode_pass_without_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE)
            r = validate(plan, None)
            self.assertTrue(r["ok"], r["checks"])
            names = {c["name"]: c for c in r["checks"]}
            self.assertIn("n/a", names["scenario-coverage"]["detail"])

    def test_unmarked_scenarioless_req_fails_gap_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE.replace("## Gaps\n- ⚠️ GAP: Rate limiting — no observable behavior to assert\n", "## Gaps\n"))
            spec = os.path.join(tmp, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            r = validate(plan, spec)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["gap-honesty"])

    def test_uncovered_ac_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace("### TC-2 · Reject bad password\n- type: negative\n- priority: P1\n- source: ac: AC-2\n- preconditions: a user exists\n- steps:\n  1. sign in with wrong password\n- expected: rejected\n", ""))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["ac-coverage"])

    def test_scenario_source_without_spec_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_SPEC_MODE)
            r = validate(plan, None)  # scenario: source but no spec
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["source-valid"])

    def test_missing_required_field_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = _write(tmp, PLAN_BUSINESS_MODE.replace("- preconditions: a user exists\n", "", 1))
            r = validate(plan, None)
            self.assertFalse(r["ok"])
            self.assertFalse({c["name"]: c["ok"] for c in r["checks"]}["required-fields"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/testplan/scripts && python3 -m pytest test_validate_test_plan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate_test_plan'`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""kinoa-qa deterministic validator.

Checks a generated QA test-plan.md. `--spec` is OPTIONAL: with a spec, spec-grounded
checks run; without one (business-only mode), those checks report n/a and the plan is
graded against its own `## Acceptance Criteria`. Checks:

  1. required-fields — every `### TC-` case has type, priority, source, preconditions,
     non-empty steps, non-empty expected;
  2. source-valid — every `source:` is `scenario: <Req>/<Scn>` (spec must be present and
     the scenario must exist), `ac: AC-<n>` (must exist in `## Acceptance Criteria`), or
     `QA-added: <reason>`;
  3. scenario-coverage — (spec mode only) every spec scenario referenced by >=1 case;
  4. ac-coverage — every AC listed in `## Acceptance Criteria` referenced by >=1 case;
  5. gap-honesty — (spec mode only) every scenario-less requirement named in a
     `## Gaps` `- ⚠️ GAP:` line.

Exit 0 = pass, 1 = fail.
"""
import argparse
import json
import os
import sys

from plan_parser import parse_spec, parse_cases, parse_gaps, parse_acs


def validate(plan_path, spec_path=None):
    with open(plan_path, encoding="utf-8") as f:
        plan_text = f.read()
    if spec_path:
        with open(spec_path, encoding="utf-8") as f:
            spec_text = f.read()
        scenarios, reqs_without = parse_spec(spec_text)
    else:
        scenarios, reqs_without = set(), set()

    cases = parse_cases(plan_text)
    gaps = parse_gaps(plan_text)
    acs = parse_acs(plan_text)
    checks = []

    # 1. required-fields
    bad = []
    for c in cases:
        missing = [k for k in ("type", "priority", "source", "preconditions") if not c["tags"].get(k)]
        if not c["tags"].get("expected"):
            missing.append("expected")
        if not c["steps"]:
            missing.append("steps")
        if missing:
            bad.append(f"{c['id']}: missing {', '.join(missing)}")
    checks.append({"name": "required-fields", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 2. source-valid
    covered_scn, covered_ac, bad = set(), set(), []
    for c in cases:
        src = c["tags"].get("source", "")
        if src.startswith("scenario:"):
            ref = src[len("scenario:"):].strip()
            if spec_path is None:
                bad.append(f"{c['id']}: scenario source but no --spec provided")
            elif ref in scenarios:
                covered_scn.add(ref)
            else:
                bad.append(f"{c['id']}: unknown scenario '{ref}'")
        elif src.startswith("ac:"):
            ref = src[len("ac:"):].strip()
            if ref in acs:
                covered_ac.add(ref)
            else:
                bad.append(f"{c['id']}: unknown acceptance-criterion '{ref}'")
        elif src.startswith("QA-added:"):
            pass
        else:
            bad.append(f"{c['id']}: source must be 'scenario:', 'ac:' or 'QA-added:'")
    checks.append({"name": "source-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 3. scenario-coverage (spec mode only)
    if spec_path:
        uncovered = sorted(scenarios - covered_scn)
        checks.append({"name": "scenario-coverage", "ok": not uncovered,
                       "detail": "ok" if not uncovered else "uncovered: " + "; ".join(uncovered)})
    else:
        checks.append({"name": "scenario-coverage", "ok": True,
                       "detail": "n/a (no spec — business-only mode)"})

    # 4. ac-coverage
    if acs:
        uncovered_ac = sorted(set(acs) - covered_ac)
        checks.append({"name": "ac-coverage", "ok": not uncovered_ac,
                       "detail": "ok" if not uncovered_ac else "uncovered: " + "; ".join(uncovered_ac)})
    else:
        checks.append({"name": "ac-coverage", "ok": True,
                       "detail": "n/a (no acceptance criteria listed)"})

    # 5. gap-honesty (spec mode only)
    if spec_path:
        unmarked = sorted(reqs_without - gaps)
        checks.append({"name": "gap-honesty", "ok": not unmarked,
                       "detail": "ok" if not unmarked else "scenarioless & unmarked: " + "; ".join(unmarked)})
    else:
        checks.append({"name": "gap-honesty", "ok": True, "detail": "n/a (no spec)"})

    report = {
        "plan": plan_path, "spec": spec_path,
        "counts": {"scenarios": len(scenarios), "cases": len(cases), "acs": len(acs), "gaps": len(gaps)},
        "checks": checks,
    }
    report["ok"] = all(c["ok"] for c in checks)
    return report


def print_report(report):
    print(f"kinoa-qa validator — {os.path.basename(report['plan'])}")
    print("=" * 60)
    for c in report["checks"]:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['name']}")
        if not c["ok"] or c["detail"].startswith("n/a"):
            print(f"       {c['detail']}")
    cnt = report["counts"]
    print("=" * 60)
    print(f"scenarios={cnt['scenarios']} cases={cnt['cases']} acs={cnt['acs']} gaps={cnt['gaps']}")
    print("RESULT:", "PASS" if report["ok"] else "FAIL — fix before the human gate / TestOps upsert")


def main():
    ap = argparse.ArgumentParser(description="kinoa-qa deterministic validator")
    ap.add_argument("plan", help="path to the generated test-plan.md")
    ap.add_argument("--spec", default=None, help="optional path to the capability spec.md")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args()
    spec = os.path.abspath(args.spec) if args.spec else None
    report = validate(os.path.abspath(args.plan), spec)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/testplan/scripts && python3 -m pytest test_validate_test_plan.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/testplan/scripts/validate_test_plan.py skills/testplan/scripts/test_validate_test_plan.py
git commit -m "feat: validator — spec-grounded + business-only modes, ac-coverage check"
```

---

### Task 4: `testops_payload.py` — case → TestOps payload + idempotency tag

**Files:**
- Create: `skills/testplan/scripts/testops_payload.py`
- Test: `skills/testplan/scripts/test_testops_payload.py`

**Interfaces:**
- Consumes: a parsed case dict from `plan_parser.parse_cases` (T2).
- Produces (consumed by SKILL Step E / testops-sync.md T7):
  - `slugify(text) -> str` (lowercase, non-alnum runs → single `-`, trimmed);
  - `traceability_tag(story, service, capability, source, title="") -> str` (`tp-<slug>`, deterministic, AQL-safe `[a-z0-9-]`; `title` included so cases sharing one `source` scenario don't collide);
  - `case_to_payload(case, *, story, service, capability, jira_base_url) -> dict` — the shared TestOps V2 create/update body (`name, description, precondition, expectedResult, scenario.steps[], tags[], links[]`); the caller adds `projectId` (create) or `id` (update).

- [ ] **Step 1: Write the failing test**

```python
# test_testops_payload.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/testplan/scripts && python3 -m pytest test_testops_payload.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'testops_payload'`.

- [ ] **Step 3: Write minimal implementation**

```python
# testops_payload.py
"""Pure mapping: a parsed test-plan case -> an Allure TestOps V2 payload body, plus the
deterministic traceability tag used as the idempotency key. stdlib-only, no network."""
import re

PRIORITY_TAG = {"P1": "priority-p1", "P2": "priority-p2", "P3": "priority-p3"}


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def traceability_tag(story, service, capability, source):
    """Deterministic, AQL-matchable tag identifying one case across re-runs."""
    parts = [p for p in (story, service, capability, source) if p]
    return "tp-" + slugify("-".join(parts))


def _strip_num(step):
    return re.sub(r"^\d+\.\s*", "", step).strip()


def _dedupe(items):
    out = []
    for i in items:
        if i and i not in out:
            out.append(i)
    return out


def case_to_payload(case, *, story, service, capability, jira_base_url):
    """Shared TestOps create/update body. Caller adds projectId (create) or id (update)."""
    tags = case["tags"]
    ttag = traceability_tag(story, service or "", capability or "", tags.get("source", ""))
    return {
        "name": f"{case['id']} · {case['title']}",
        "description": f"source: {tags.get('source', '')}\ntraceability: {ttag}\nstory: {story}",
        "precondition": tags.get("preconditions", ""),
        "expectedResult": tags.get("expected", ""),
        "scenario": {"steps": [{"type": "body", "body": _strip_num(s)} for s in case["steps"]]},
        "tags": _dedupe([
            "spec-derived",
            f"type-{slugify(tags.get('type', ''))}",
            PRIORITY_TAG.get(tags.get("priority", ""), "priority-unset"),
            ttag,
        ]),
        "links": [{"name": story, "url": f"{jira_base_url.rstrip('/')}/browse/{story}"}],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/testplan/scripts && python3 -m pytest test_testops_payload.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the whole script suite together**

Run: `cd skills/testplan/scripts && python3 -m pytest -v`
Expected: PASS (14 tests total across the three modules).

- [ ] **Step 6: Commit**

```bash
git add skills/testplan/scripts/testops_payload.py skills/testplan/scripts/test_testops_payload.py
git commit -m "feat: testops_payload — case->TestOps body + deterministic traceability tag"
```

---

### Task 5: `test-plan-format.md` reference + two golden fixtures

**Files:**
- Create: `skills/testplan/references/test-plan-format.md`
- Create: `skills/testplan/evals/fixtures/spec-grounded/spec.md`
- Create: `skills/testplan/evals/fixtures/spec-grounded/test-plan.md`
- Create: `skills/testplan/evals/fixtures/business-only/test-plan.md`
- Test: run the validator against both goldens.

**Interfaces:**
- Consumes: the validator (T3) as the acceptance gate.
- Produces: the canonical format the generation subagent (T6) must emit; the two goldens reused by evals (T9).

- [ ] **Step 1: Write `references/test-plan-format.md`**

Content (the exact grammar the validator parses — keep the `·` U+00B7, `—` U+2014, `⚠️` verbatim):

````markdown
# test-plan.md format

A `test-plan.md` is the reviewable intermediate. One file → N `### TC-<n>` cases → N
Allure TestOps cases (1:1). The deterministic validator
(`scripts/validate_test_plan.py`) parses this exact shape — do not deviate.

## Header (required)

```
# QA Test Plan — <service> / <capability>          (or "— <STORY-KEY> (business-only)")
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: <STORY-KEY> · target: <service>/<capability>@<ref> · generated: <YYYY-MM-DD> · spec-sha: <sha12 | none>
specs: <resolved | none (<reason>)>
```

## `## Acceptance Criteria` (required in business-only mode; optional in spec mode)

```
- AC-1: <one acceptance criterion, one line>
- AC-2: <…>
```
Every listed AC MUST be cited by ≥1 case `source: ac: AC-<n>` (validator `ac-coverage`).
Omit the whole section in spec-grounded mode unless you intend to cover the ACs too.

## `## Cases` (required)

```
### TC-<n> · <title>
- type: functional            # functional | negative | edge | regression | e2e | nonfunctional
- priority: P1                # P1 | P2 | P3
- source: scenario: <Requirement>/<Scenario>   # OR  ac: AC-<n>   OR  QA-added: <reason>
- preconditions: <state that must hold>
- steps:
  1. <action>
  2. <action>
- expected: <observable outcome>
```
Field order is fixed. `steps` are `  N. ` numbered lines. All six fields are required
(validator `required-fields`).

## `## Gaps` (required section header; may be empty)

```
- ⚠️ GAP: <Requirement> — <why no case>      # em dash U+2014
```
In spec mode, every requirement with no scenario MUST appear here (validator `gap-honesty`).

## Field → Allure TestOps V2 mapping (Step E)

| test-plan.md | TestOps create/update field |
|---|---|
| `### TC-n · <title>` | `name` = `"TC-n · <title>"` |
| `type` | tag `type-<type>` |
| `priority` | tag `priority-<p>` (no first-class severity field in V2; a Severity custom field is optional, only if `testops_get_project` confirms one) |
| `source` | `description` (+ the `tp-…` traceability tag) |
| `preconditions` | `precondition` |
| `steps` | `scenario.steps[{type:"body", body}]` (numbering stripped) |
| `expected` | `expectedResult` |
| — | tags always include `spec-derived` + the `tp-<slug>` traceability tag; `links[0]` → the Jira Story |

`## Gaps` lines are never pushed to TestOps.
````

- [ ] **Step 2: Write `fixtures/spec-grounded/spec.md`**

```markdown
### Requirement: Google Workspace sign-in
#### Scenario: A tenant token creates an Author account
- WHEN an authorized Workspace user signs in for the first time
- THEN an Author account is provisioned

### Requirement: Break-glass sign-in
#### Scenario: The break-glass credentials grant Super admin
- WHEN valid break-glass credentials are posted
- THEN the session is granted Super admin

### Requirement: Token rate limiting
```

- [ ] **Step 3: Write `fixtures/spec-grounded/test-plan.md`**

```markdown
# QA Test Plan — kinoa-client-support-tool / admin-authentication
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: kinoa-client-support-tool/admin-authentication@main · generated: 2026-09-07 · spec-sha: a1b2c3d4e5f6
specs: resolved

## Cases

### TC-1 · A tenant token creates an Author account
- type: functional
- priority: P1
- source: scenario: Google Workspace sign-in/A tenant token creates an Author account
- preconditions: no account row exists for anna@kinoa.io
- steps:
  1. present an OIDC user request (email=anna@kinoa.io, hd=kinoa.io, email_verified=true)
  2. invoke the OIDC user service to load that user
- expected: a principal for anna@kinoa.io is returned and exactly one AUTHOR account row exists

### TC-2 · The break-glass credentials grant Super admin
- type: functional
- priority: P1
- source: scenario: Break-glass sign-in/The break-glass credentials grant Super admin
- preconditions: break-glass credentials configured; approver list empty
- steps:
  1. post a form sign-in with valid break-glass credentials and a valid CSRF token
- expected: the session is redirected to /admin/incidents with Super admin access

## Gaps
- ⚠️ GAP: Token rate limiting — spec states no observable behavior to assert
```

- [ ] **Step 4: Write `fixtures/business-only/test-plan.md`**

```markdown
# QA Test Plan — KING-22737 (business-only)
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: (none) · generated: 2026-09-07 · spec-sha: none
specs: none (no service repo resolved)

## Acceptance Criteria
- AC-1: Authorized Workspace users get an Author account on first sign-in
- AC-2: Break-glass access is limited and audited

## Cases

### TC-1 · First Workspace sign-in provisions an Author account
- type: functional
- priority: P1
- source: ac: AC-1
- preconditions: the user has no existing account
- steps:
  1. sign in with an authorized Workspace account for the first time
- expected: an Author account is created for the user

### TC-2 · Break-glass access is refused past the limit
- type: negative
- priority: P1
- source: ac: AC-2
- preconditions: break-glass configured with a small attempt limit
- steps:
  1. exceed the allowed number of break-glass attempts
- expected: access is refused and the attempt is audited

## Gaps
```

- [ ] **Step 5: Validate both goldens**

Run:
```bash
cd skills/testplan
python3 scripts/validate_test_plan.py evals/fixtures/spec-grounded/test-plan.md --spec evals/fixtures/spec-grounded/spec.md
python3 scripts/validate_test_plan.py evals/fixtures/business-only/test-plan.md
```
Expected: both print `RESULT: PASS` and exit 0.

- [ ] **Step 6: Commit**

```bash
git add skills/testplan/references/test-plan-format.md skills/testplan/evals/fixtures
git commit -m "docs: test-plan.md format reference + spec-grounded & business-only goldens"
```

---

### Task 6: `generation.md` reference — the QA-lens contract

**Files:**
- Create: `skills/testplan/references/generation.md`

**Interfaces:**
- Consumes: `test-plan-format.md` (T5, the output shape).
- Produces: the derivation rules the Step B subagent follows; verified by evals (T9).

- [ ] **Step 1: Write `references/generation.md`**

Content — adapt flow-test-plan's five QA-lens rules to the new SoT (Story + PRD + optional spec) and the two source modes. Include verbatim:

````markdown
# generation.md — deriving cases from the SoT bundle

Input: the SoT bundle `{ story, acceptance, prd?, specs[] }` assembled in Step A.
Output: exactly one `test-plan.md` (per `references/test-plan-format.md`) + nothing else.

## Source discipline (which `source:` to use)
- A case grounded in a **spec scenario** → `source: scenario: <Requirement>/<Scenario>`
  (the heading text, verbatim). Only when a spec was resolved.
- A case grounded only in a **business requirement** → `source: ac: AC-<n>`, and that
  `AC-<n>` MUST be listed in `## Acceptance Criteria` (derive the AC list from the Story
  description/acceptance-criteria + PRD).
- A genuinely QA-motivated case with no direct scenario/AC → `source: QA-added: <reason>`
  (use sparingly; it is not an escape hatch for laziness).

## The five QA-lens rules
1. **Functional (happy path):** one case per spec scenario / per acceptance criterion,
   asserting the stated behavior.
2. **Negative / edge:** where a scenario or AC implies a boundary or invalid input
   (a limit, a required field, an auth failure), add a `type: negative` or `type: edge`
   case — the boundary must be implied by the source text, never invented.
3. **Regression (contract):** if a resolved spec/PRD indicates a shared contract change
   (an API payload, an event schema, a shared response), add a `type: regression` case
   asserting backward compatibility. (Spec mode; skip if no contract signal.)
4. **End-to-end:** only when the SoT describes a cross-component flow the Story spans;
   otherwise omit. (Business-only runs rarely warrant e2e — prefer functional/negative.)
5. **Nonfunctional:** only when the source text states an observable nonfunctional
   requirement (a timeout, a rate limit with an asserted response). Never infer silently.

## No fabrication (hard rule)
An untestable or scenario-less requirement is NOT turned into a case. In spec mode, name
each scenario-less requirement in a `## Gaps` `- ⚠️ GAP: <Requirement> — <reason>` line.
Do not invent an `expected` you cannot ground in the source.

## Degradation
- **No spec resolved:** run in business-only mode — derive `## Acceptance Criteria` from
  Story + PRD, source every case with `ac:`; set header `specs: none (<reason>)`; expect
  coarser cases. Rules 3–5 apply only where the PRD explicitly states the behavior.
- **No PRD:** proceed on the Story alone; the acceptance criteria come from the Story's
  own acceptance-criteria/description fields.

## Self-check (before returning)
State that you expect `python3 scripts/validate_test_plan.py <plan> [--spec <spec>]` to
report `RESULT: PASS` on your output. This is a self-check, not a substitute for Step C
actually running the validator.
````

- [ ] **Step 2: Sanity-check the reference against the goldens**

Confirm (by reading) that both T5 goldens obey every rule in this file (functional cases present; spec-grounded uses `scenario:`, business-only uses `ac:`; the scenario-less `Token rate limiting` requirement is a GAP). No command; a read-through.

- [ ] **Step 3: Commit**

```bash
git add skills/testplan/references/generation.md
git commit -m "docs: generation.md — QA-lens derivation rules + no-fabrication + degradation"
```

---

### Task 7: Adapter references (`sot-assembly.md`, `testops-sync.md`) + `services.json`

**Files:**
- Create: `skills/testplan/references/sot-assembly.md`
- Create: `skills/testplan/references/testops-sync.md`
- Create: `services.json`

**Interfaces:**
- Consumes: `config.json` (T1); `testops_payload.py` (T4).
- Produces: the exact vendor mechanics SKILL.md (T8) points at for Steps A and E.

- [ ] **Step 1: Write `services.json`**

```json
{
  "kinoa-client-support-tool": {
    "owner": "Kinoa-Labs-LTD",
    "repo": "kinoa-client-support-tool",
    "specs_root": "openspec/specs",
    "default_ref": "main"
  }
}
```

- [ ] **Step 2: Write `references/sot-assembly.md`**

````markdown
# sot-assembly.md — Step A (read-only)

Assemble the SoT bundle `{ story, acceptance, prd?, specs[] }`. Only the Story is
required; PRD and specs each degrade independently.

## RequirementsReader (Atlassian MCP)
1. `getJiraIssue(<STORY-KEY>)` → description + acceptance criteria + subtasks.
   Missing Story / MCP down → HARD STOP (the one required input).
2. **Affected-repo references** — extract in priority order (convention not yet locked):
   a. Jira **dev-status** linked PRs/branches → `(owner, repo, ref)` (most precise);
   b. **remote/issue links** to `github.com/<owner>/<repo>` → `(owner, repo, default_ref)`;
   c. a **structured field / labels / components** mapped via `services.json`;
   d. otherwise use the CLI overrides `--repo` / `--target` / `--spec-path`.
3. PRD: for each Confluence link on the Story, `getConfluencePage(id)`. Absent → skip,
   set `specs`/`prd` degradation notes in the header. Never a hard stop.

## SpecResolver (GitHub `gh` default; local override)
Interface: `(service, capability[, ref]) -> spec text`. Backends:
- **Default — `gh` remote:**
  ```bash
  gh api "repos/<owner>/<repo>/contents/<specs_root>/<capability>/spec.md?ref=<ref>" --jq '.content' | base64 -d
  ```
  `<specs_root>` defaults to `openspec/specs` (from `services.json` or convention).
- **Override — local:** `--spec-path <dir>` reads `<dir>/openspec/specs/<capability>/spec.md`.

Any resolution failure (not found / unregistered / `gh` unauthed / one target fails) is
NON-fatal: continue in business-only mode, record `specs: none (<reason>)` in the header,
and surface the error at the human gate. `--continue-on-missing` opts into partial
multi-target runs; the default aborts a multi-target run only if the QA engineer asks.

## spec-sha
When a spec is resolved, record `spec-sha: <first 12 of sha256(spec text)>` in the header
for traceability; `none` in business-only mode.
````

- [ ] **Step 3: Write `references/testops-sync.md`**

````markdown
# testops-sync.md — Step E (writes; only after the human gate)

Uses the Allure TestOps MCP. `project_id` from `config.json` (resolve once via
`testops_find_projects`/`testops_get_project` on `project_name` "KINOA" and cache it).

For each `### TC-<n>` case, build the body with `scripts/testops_payload.py`
`case_to_payload(case, story=…, service=…, capability=…, jira_base_url=…)` — this yields
`name, description, precondition, expectedResult, scenario.steps[], tags[], links[]`, and
the `tp-<slug>` traceability tag inside `tags`.

## Idempotent upsert (per case)
1. `ttag = testops_payload.traceability_tag(story, service, capability, source, title)` — `title` = the case's TC title; required so two cases citing the same `source` scenario (functional + negative) don't collide onto one TestOps case.
2. `testops_find_testcases(projectId, aql='tags = "<ttag>"', expand=["tags"])`.
3. **Found (≥1):** `testops_update_testcase(id=<first hit id>, **payload)`.
   **None:** `testops_create_testcase(projectId=<pid>, **payload)`.
4. Take the returned case id → write `@allure.id=<id>` back into the `test-plan.md` case
   header comment (so the file records the TestOps link).

Because the key is a stable tag (not the title), re-running a Story updates in place —
0 duplicates. A partial failure needs no rollback: re-run resumes (found→update the
landed ones, create the rest).

## `--dry-run`
Do NOT call create/update. Instead print, per case: the intended action
(create|update), the `ttag`, and the payload `name` — the QA preview of Step E.

## Degradation
- TestOps unreachable → the reviewed `test-plan.md` is already on disk; stop and tell the
  QA engineer to re-run Step E later. Nothing is lost.
- `priority` has no first-class TestOps field → it rides as a `priority-<p>` tag. If
  `testops_get_project(expand=["custom_fields"])` shows a Severity custom field, ALSO set
  it via `customFields:[{name:"Severity", value:<critical|normal|minor>}]` (P1→critical,
  P2→normal, P3→minor).
````

- [ ] **Step 4: Verify `services.json` parses**

Run: `python3 -c "import json; json.load(open('services.json')); print('services.json OK')"`
Expected: prints `services.json OK`.

- [ ] **Step 5: Commit**

```bash
git add skills/testplan/references/sot-assembly.md skills/testplan/references/testops-sync.md services.json
git commit -m "docs: SoT-assembly + TestOps-sync adapter references + services.json registry"
```

---

### Task 8: `SKILL.md` — the orchestrator

**Files:**
- Create: `skills/testplan/SKILL.md`

**Interfaces:**
- Consumes: all four references (T5–T7) + the three scripts (T2–T4) + `config.json` (T1).
- Produces: the `/kinoa-qa:testplan` entry point tying Steps A–E together.

- [ ] **Step 1: Write `skills/testplan/SKILL.md`**

Content — the orchestrator. Include the YAML frontmatter (name `testplan`, a
description), the two-mode note, Steps A–E, the degradation table, and the invariants:

````markdown
---
name: testplan
description: Build a validator-checked QA test plan from a Jira Story (+ optional Confluence PRD + optional service-repo OpenSpec specs) and, after a human gate, idempotently upsert the cases into Allure TestOps. Invoke for `/kinoa-qa:testplan <STORY-KEY>`.
---

# testplan — Jira Story → Allure TestOps cases

`/kinoa-qa:testplan <STORY-KEY> [--target <service>/<capability>] [--repo <owner>/<name>] [--spec-path <dir>] [--dry-run]`

The main agent orchestrates, validates, gates, and upserts. **Heavy reading (Story/PRD/
spec → cases) happens in a fresh-context subagent (Step B)** — the main agent does not
read the whole spec/PRD itself.

| What | Reference |
|---|---|
| Assemble the SoT; adapters (Jira, Confluence, `gh`) | `references/sot-assembly.md` |
| QA-lens derivation rules, no-fabrication | `references/generation.md` |
| Exact `test-plan.md` shape + TestOps mapping | `references/test-plan-format.md` |
| Idempotent TestOps upsert, `--dry-run` | `references/testops-sync.md` |
| Deterministic validator (script, not an LLM) | `scripts/validate_test_plan.py` |

## Step A — Assemble the SoT (read-only)
Follow `references/sot-assembly.md`. Result: the SoT bundle `{ story, acceptance, prd?,
specs[] }`. Only the Story is required; PRD and specs degrade independently. Never write.

## Step B — Generate (fresh-context subagent)
Dispatch a subagent with the SoT bundle + `references/generation.md` +
`references/test-plan-format.md`. It returns exactly one artifact: the `test-plan.md`
content. Write it to a local working file `./<STORY-KEY>-<service>-<capability>.test-plan.md`.

## Step C — Validate (deterministic, gates the run)
```bash
python3 <plugin>/skills/testplan/scripts/validate_test_plan.py <plan> [--spec <spec>]
```
(Pass `--spec` only when a spec was resolved.) FAIL → one regeneration retry with the
validator detail → still FAIL → STOP before the human gate and surface the failing
checks. A failing plan never reaches TestOps.

## Step D — Human gate
Present the validated `test-plan.md` to the QA engineer. **Nothing has touched TestOps
yet.** If specs degraded, warn that the plan is business-only. On edits, re-run Step C.
Proceed to Step E only on explicit approval.

## Step E — TestOps upsert
Follow `references/testops-sync.md`: per case, AQL-find by the `tp-<slug>` tag →
`update` or `create` in project KINOA (id from `config.json`), then write `@allure.id`
back into the `.md`. With `--dry-run`, print intended actions instead.

## Degradation
| Failure | Behavior |
|---|---|
| Jira Story missing / Atlassian down | HARD STOP at Step A (only required input). |
| Confluence PRD absent/unreachable | Proceed Story-only; header `prd: none`. |
| Spec unresolved / `gh` unauthed / target fails | Continue business-only; header `specs: none (<reason>)`; warn at the gate. |
| Thin spec (requirement, no scenario) | `⚠️ GAP` line, no invented case. |
| Generation fails | One retry, then stop and surface. |
| Validator FAIL | One retry → stop before the gate; never ships. |
| QA rejects at the gate | Nothing pushed; edits re-validated. |
| TestOps write fails mid-batch | No rollback — keyed upsert; re-run resumes. |
| TestOps unreachable | `test-plan.md` is on disk; re-run Step E later. |

## Invariants
- Service repos are READ-ONLY.
- TestOps is written ONLY after the Step D human gate.
- Upserts are idempotent, keyed by the `tp-<slug>` tag — no duplicates on re-run.
- No fabrication — untestable/scenario-less → `⚠️ GAP`, never an invented case.
- The deterministic validator gates before the human sees the plan.
- Standalone — zero code dependency on kinoa-dev.
````

- [ ] **Step 2: Verify the skill frontmatter parses and the command name is correct**

Run:
```bash
python3 -c "import re,io; t=open('skills/testplan/SKILL.md',encoding='utf-8').read(); fm=t.split('---')[1]; assert 'name: testplan' in fm; assert '/kinoa-qa:testplan' in t; print('SKILL.md OK — command /kinoa-qa:testplan')"
```
Expected: prints `SKILL.md OK — command /kinoa-qa:testplan`.

- [ ] **Step 3: Commit**

```bash
git add skills/testplan/SKILL.md
git commit -m "feat: testplan SKILL.md — orchestrator Steps A–E, degradation, invariants"
```

---

### Task 9: `evals/evals.json` — the eval harness

**Files:**
- Create: `skills/testplan/evals/evals.json`
- (Fixtures from T5 are reused; add any extra fixture files referenced below.)

**Interfaces:**
- Consumes: the goldens (T5), the validator (T3), the generation/format/sync references.
- Produces: the property-based eval suite (mirrors the flow-test-plan harness schema:
  top-level `skill_name`, `notes`, `evals:[{id,name,fixture,prompt,expected_output,files,assertions:[{text,passed,evidence}]}]`).

- [ ] **Step 1: Write `evals/evals.json`**

```json
{
  "skill_name": "kinoa-qa:testplan",
  "notes": "Fixtures live in ./fixtures/. Subagents can't nest in the eval harness, so the generation subagent's work (Step B) runs INLINE by the eval-running agent. Atlassian, gh (SpecResolver) and Allure TestOps are SIMULATED (no reachable MCP/repo in the eval env) — but skills/testplan/scripts/validate_test_plan.py runs for REAL against the generated test-plan.md and fixture spec.md, and its real exit code/output is what assertions are checked against.",
  "evals": [
    {
      "id": 0,
      "name": "spec-grounded-every-scenario-covered",
      "fixture": "spec-grounded",
      "prompt": "Given fixtures/spec-grounded/spec.md (two scenario'd requirements + one scenario-less 'Token rate limiting'), generate test-plan.md per generation.md + test-plan-format.md (generation inline), then run validate_test_plan.py against the spec.",
      "expected_output": "Every #### Scenario is covered by >=1 case with source: scenario: <Req>/<Scenario> matching the headings; the scenario-less requirement appears as a ## Gaps line; validate_test_plan.py exits 0 with RESULT: PASS.",
      "files": [],
      "assertions": [
        { "text": "Each spec scenario is referenced by >=1 case's source: scenario: <Req>/<Scenario>, exact string match", "passed": false, "evidence": "" },
        { "text": "The scenario-less 'Token rate limiting' requirement is named in a ## Gaps ⚠️ GAP line (not silently dropped)", "passed": false, "evidence": "" },
        { "text": "validate_test_plan.py was actually executed against the generated plan and fixture spec (not self-checked only)", "passed": false, "evidence": "" },
        { "text": "validate_test_plan.py exits 0 and prints RESULT: PASS (all five checks PASS or n/a)", "passed": false, "evidence": "" }
      ]
    },
    {
      "id": 1,
      "name": "business-only-ac-coverage",
      "fixture": "business-only",
      "prompt": "No service repo resolves. Using only a Jira Story + PRD (acceptance criteria AC-1, AC-2), generate a business-only test-plan.md and validate WITHOUT --spec.",
      "expected_output": "The plan has a ## Acceptance Criteria section; every AC is covered by >=1 case with source: ac: AC-<n>; header records specs: none; validate_test_plan.py (no --spec) exits 0, scenario-coverage and gap-honesty report n/a.",
      "files": [],
      "assertions": [
        { "text": "Every AC-<n> in ## Acceptance Criteria is cited by >=1 case source: ac: AC-<n>", "passed": false, "evidence": "" },
        { "text": "No case uses source: scenario: (there is no spec) — sources are ac: or QA-added:", "passed": false, "evidence": "" },
        { "text": "Header records specs: none (<reason>)", "passed": false, "evidence": "" },
        { "text": "validate_test_plan.py without --spec exits 0; scenario-coverage and gap-honesty show n/a", "passed": false, "evidence": "" }
      ]
    },
    {
      "id": 2,
      "name": "qa-lens-adds-negative",
      "fixture": "spec-grounded",
      "prompt": "For a scenario implying a boundary/auth failure (break-glass), apply generation.md rule 2 and add a negative/edge case, then validate.",
      "expected_output": "Beyond the base functional case, >=1 case tagged type: negative or type: edge exists, its boundary implied by the source scenario's WHEN/THEN, still using a valid source: reference. Validator passes.",
      "files": [],
      "assertions": [
        { "text": "A type: negative or type: edge case exists beyond the happy-path case", "passed": false, "evidence": "" },
        { "text": "Its boundary/invalid input is implied by the source scenario text, not fabricated", "passed": false, "evidence": "" },
        { "text": "It uses a valid source: (scenario: or ac:), not QA-added: as an escape hatch", "passed": false, "evidence": "" },
        { "text": "validate_test_plan.py exits 0", "passed": false, "evidence": "" }
      ]
    },
    {
      "id": 3,
      "name": "no-fabrication-gap-honesty",
      "fixture": "spec-grounded",
      "prompt": "The spec has a scenario-less requirement ('Token rate limiting'). Confirm no case is invented for it and it is marked as a gap; validate.",
      "expected_output": "No case cites 'Token rate limiting'; it appears once as a ## Gaps ⚠️ GAP line with an em dash and a reason; validate_test_plan.py gap-honesty PASS.",
      "files": [],
      "assertions": [
        { "text": "No ### TC- case is invented for the scenario-less requirement", "passed": false, "evidence": "" },
        { "text": "'Token rate limiting' appears as a ## Gaps ⚠️ GAP: <req> — <reason> line (em dash U+2014)", "passed": false, "evidence": "" },
        { "text": "validate_test_plan.py gap-honesty check PASS", "passed": false, "evidence": "" }
      ]
    },
    {
      "id": 4,
      "name": "idempotent-upsert-key-stable",
      "fixture": "spec-grounded",
      "prompt": "Simulate two Step E runs over the SAME approved plan via testops_payload.traceability_tag + a simulated testops_find_testcases. Show the second run updates, not duplicates.",
      "expected_output": "For each case, traceability_tag(story, service, capability, source) is identical across both runs; run 1 (find returns none) => create; run 2 (find returns the id) => update; no case is created twice.",
      "files": [],
      "assertions": [
        { "text": "traceability_tag is byte-identical for the same case across the two runs", "passed": false, "evidence": "" },
        { "text": "Run 2's find (aql tags = the same tp- tag) matches run 1's created case, so the action is update", "passed": false, "evidence": "" },
        { "text": "No case results in two create calls (0 duplicates)", "passed": false, "evidence": "" },
        { "text": "The tp- tag is AQL-safe ([a-z0-9-]+) and present in the payload tags", "passed": false, "evidence": "" }
      ]
    },
    {
      "id": 5,
      "name": "dry-run-writes-nothing",
      "fixture": "spec-grounded",
      "prompt": "Run Step E with --dry-run over the approved plan. Confirm no create/update is issued and a per-case preview is printed.",
      "expected_output": "Per testops-sync.md --dry-run: for each case, print intended action (create|update), its tp- tag, and payload name; issue ZERO testops_create_testcase / testops_update_testcase calls.",
      "files": [],
      "assertions": [
        { "text": "Zero create/update TestOps calls are issued under --dry-run", "passed": false, "evidence": "" },
        { "text": "A per-case line prints the intended action, the tp- tag, and the payload name", "passed": false, "evidence": "" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Verify evals.json parses and references real fixtures**

Run:
```bash
cd skills/testplan
python3 -c "import json,os; e=json.load(open('evals/evals.json')); [os.path.isdir(f'evals/fixtures/{ev[\"fixture\"]}') or (_ for _ in ()).throw(AssertionError(ev['fixture'])) for ev in e['evals']]; print(f'{len(e[\"evals\"])} evals OK')"
```
Expected: prints `6 evals OK`.

- [ ] **Step 3: Commit**

```bash
git add skills/testplan/evals/evals.json
git commit -m "test: eval suite — spec/business modes, QA-lens, no-fabrication, idempotency, dry-run"
```

---

### Task 10: End-to-end dry-run acceptance (real story)

**Files:**
- Create: `skills/testplan/evals/_runs/` output (gitignored) — a real generated plan, kept only for inspection.

**Interfaces:**
- Consumes: the whole plugin (T1–T9).
- Produces: a confirmed working end-to-end pass on real vendors, in `--dry-run` (no TestOps writes).

- [ ] **Step 1: Run the full scripts test suite once more**

Run: `cd skills/testplan/scripts && python3 -m pytest -v`
Expected: PASS (14 tests).

- [ ] **Step 2: Validate both goldens once more (regression guard)**

Run:
```bash
cd skills/testplan
python3 scripts/validate_test_plan.py evals/fixtures/spec-grounded/test-plan.md --spec evals/fixtures/spec-grounded/spec.md
python3 scripts/validate_test_plan.py evals/fixtures/business-only/test-plan.md
```
Expected: both `RESULT: PASS`.

- [ ] **Step 3: Real end-to-end dry-run against a chosen Story**

Using the installed plugin, run `/kinoa-qa:testplan <STORY-KEY> --dry-run` for a real
Story that has a resolvable service-repo spec (e.g. one covering
`kinoa-client-support-tool/admin-authentication`, which is in `services.json`). Verify by
inspection:
- Step A resolved the Story via Atlassian and read the spec via `gh` (or degraded to
  business-only with a `specs: none` header + a warning — either is a valid pass);
- Step C printed `RESULT: PASS`;
- Step D presented the plan and paused for approval;
- Step E under `--dry-run` printed per-case create/update intentions with `tp-` tags and
  issued NO TestOps writes.

- [ ] **Step 4: Record the acceptance result**

Write a one-paragraph note of what happened (mode taken, case count, validator result,
dry-run actions) into the PR description or a scratch note. No commit required (the
`_runs/` output is gitignored).

- [ ] **Step 5: Bump version & tag the milestone (optional, on request)**

```bash
git commit --allow-empty -m "chore: kinoa-qa v0.1.0 — end-to-end dry-run acceptance passed"
```

---

## Self-Review

**1. Spec coverage.** Design-doc sections → tasks: §4 architecture/packaging → T1; §5
pipeline Steps A–E → T8 (orchestration) + T2–T4 (deterministic parts) + T6/T7 (prose);
§6 adapters → T7 (SpecResolver, RequirementsReader, TestOpsWriter) + T4 (payload/key);
§7 SoT hardness tiers → T3 (business-only validation) + T6/T7/T8 (degradation) ; §8
format + TestOps mapping + idempotency key → T5 (format) + T4 (payload/tag) + T7 (sync);
§9 error handling → T8 degradation table + non-fatal paths in T3/T7; §10 testing → T2–T4
(unit), T5 (golden gate), T9 (evals), T10 (e2e dry-run). All covered.

**2. Placeholder scan.** No "TBD"/"handle appropriately"/"similar to Task N": every code
step carries real code; every prose file carries its full text; every check step carries
a runnable command with an expected result. `config.json`'s `project_id: null` is an
intentional runtime-resolved value (T7 Step 3 documents resolving it), not a placeholder.

**3. Type consistency.** `parse_cases` returns `{"id","title","tags","steps"}` (T2) and is
consumed unchanged by `validate` (T3) and `case_to_payload` (T4). `traceability_tag(story,
service, capability, source)` and `case_to_payload(case, *, story, service, capability,
jira_base_url)` signatures match between T4 impl, its tests, and testops-sync.md (T7).
Check names (`required-fields`, `source-valid`, `scenario-coverage`, `ac-coverage`,
`gap-honesty`) are identical across T3 impl, its tests, and the evals (T9). Command name
`/kinoa-qa:testplan` is identical across README (T1), SKILL (T8), and design doc.
```
