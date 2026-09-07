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
