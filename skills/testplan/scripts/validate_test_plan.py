#!/usr/bin/env python3
"""kinoa-qa deterministic validator.

Checks a generated QA test-plan.md. The Jira Story, the PRD and any linked mockup are the
source of truth; OpenSpec files (`--openspec`, optional) are context only. Checks:

  1. required-fields — every `### TC-` case has type, priority, source, preconditions,
     non-empty steps, non-empty expected;
  2. source-valid — every `source:` is `ac: AC-<n>` (must exist in `## Acceptance
     Criteria`) or `QA-added: <reason>`; there is no `scenario:` source;
  3. openspec-ref-valid — every `openspec-ref:` names a real scenario of a supplied
     OpenSpec file, qualified `<capability>#<Requirement>/<Scenario>` when more than one
     file is supplied;
  4. design-ref-valid — every `design-ref:` reads `<fileKey>/<nodeId> — <frame name>` and
     accompanies an `ac:` source; checked syntactically, the validator never calls Figma;
  5. scenario-coverage — advisory only: how many OpenSpec scenarios a case enriches;
  6. ac-coverage — `## Acceptance Criteria` is required and every AC listed there is cited
     by >=1 case;
  7. conflict-resolution — `## Conflicts` header present, no unrecognised line in the
     section, every side of each conflict (two or more) named with a known artifact, and no
     case citing an AC a still-unresolved conflict contradicts, and every `→ resolved:`
     annotation written in the documented grammar;
  8. gap-honesty — every scenario-less requirement AND every OpenSpec scenario no case
     enriches is named in a `## Gaps` line, unless an unresolved `## Conflicts` line already
     names it; spec coverage is advisory, dishonesty is not.

Exit 0 = PASS, 1 = FAIL, 2 = HOLD (structurally valid, but an unresolved conflict blocks
the TestOps upsert until the QA engineer annotates `→ resolved: …`).
"""
import argparse
import json
import os
import re
import sys

from plan_parser import parse_spec, parse_cases, parse_gaps, parse_acs, parse_conflicts

def _capability_of(spec_path):
    """The capability a spec file belongs to: its parent directory, per the OpenSpec layout
    `openspec/specs/<capability>/spec.md`, falling back to the file's own stem."""
    head, tail = os.path.split(os.path.abspath(spec_path))
    return os.path.basename(head) if tail == "spec.md" else os.path.splitext(tail)[0]


AC_SECTION_RE = re.compile(r"^##\s+Acceptance Criteria\s*$", re.M)
DESIGN_REF_RE = re.compile(r"^[^/\s]+/[^/\s]+\s+—\s+\S.*$")
CONFLICT_SOURCES = ("story", "prd", "design", "openspec")
CONFLICT_AC_RE = re.compile(r"^(AC-\d+)\s*·")
CONFLICT_BODY_RE = re.compile(r"·\s*(.*)$")
CONFLICT_SIDE_RE = re.compile(r"^([A-Za-z-]+):\s*\S")
# The documented `→ resolved:` grammar (test-plan-format.md): one of the two recognised
# verdicts, optionally followed by free-text detail after a separator. Anything else is a
# FAIL, so a hallucinated `→ resolved: TBD` cannot turn a HOLD into a PASS.
RESOLVED_GRAMMAR_RE = re.compile(
    r"^(business wins|spec wins, AC updated)(\s*[\u2014\u2013:;,(-].*)?$", re.I | re.S)


def conflict_sides(claim):
    """The artifact keyword of every ` vs `-separated side of a conflict claim, in order.
    A conflict may name two sides or more; returns [] when the claim does not name at
    least two, each labelled `<artifact>: <text>`."""
    m = CONFLICT_BODY_RE.search(claim)
    if not m:
        return []
    body = re.split(r"\s+—\s+", m.group(1))[0]
    sides = []
    for part in re.split(r"\s+vs\s+", body):
        sm = CONFLICT_SIDE_RE.match(part.strip())
        if not sm:
            return []
        sides.append(sm.group(1))
    return sides if len(sides) >= 2 else []


def validate(plan_path, openspec_path=None):
    with open(plan_path, encoding="utf-8") as f:
        plan_text = f.read()
    spec_paths = ([openspec_path] if isinstance(openspec_path, str)
                  else list(openspec_path or []))
    scenarios, reqs_without = set(), set()
    by_capability = {}
    for path in spec_paths:
        with open(path, encoding="utf-8") as f:
            scn, without = parse_spec(f.read())
        by_capability.setdefault(_capability_of(path), set()).update(scn)
        scenarios |= scn
        reqs_without |= without

    cases = parse_cases(plan_text)
    gaps = parse_gaps(plan_text)
    acs = parse_acs(plan_text)
    has_conflicts_section, conflicts, unparsed_conflicts = parse_conflicts(plan_text)
    has_ac_section = bool(AC_SECTION_RE.search(plan_text))
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

    # 2. source-valid — business grounding only
    covered_ac, bad = set(), []
    for c in cases:
        src = c["tags"].get("source", "")
        if src.startswith("ac:"):
            ref = src[len("ac:"):].strip()
            if ref in acs:
                covered_ac.add(ref)
            else:
                bad.append(f"{c['id']}: unknown acceptance-criterion '{ref}'")
        elif src.startswith("QA-added:"):
            pass
        else:
            bad.append(f"{c['id']}: source must be 'ac:' or 'QA-added:' "
                       f"(business grounding only; an OpenSpec scenario goes in openspec-ref)")
    checks.append({"name": "source-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 3. openspec-ref-valid
    covered_scn, bad = set(), []
    for c in cases:
        ref = (c["tags"].get("openspec-ref") or "").strip()
        if not ref:
            continue
        if not spec_paths:
            bad.append(f"{c['id']}: openspec-ref '{ref}' but no --openspec provided")
        elif "#" in ref:
            cap, scn = (part.strip() for part in ref.split("#", 1))
            if cap not in by_capability:
                bad.append(f"{c['id']}: unknown capability '{cap}'")
            elif scn not in by_capability[cap]:
                bad.append(f"{c['id']}: unknown scenario '{scn}' in capability '{cap}'")
            else:
                covered_scn.add(scn)
        elif len(spec_paths) > 1:
            bad.append(f"{c['id']}: unqualified openspec-ref '{ref}' is ambiguous across "
                       f"{len(spec_paths)} OpenSpec files — qualify it as <capability>#{ref}")
        elif ref in scenarios:
            covered_scn.add(ref)
        else:
            bad.append(f"{c['id']}: unknown scenario '{ref}'")
    checks.append({"name": "openspec-ref-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 4. design-ref-valid — syntax and source pairing only; never a Figma call
    bad = []
    for c in cases:
        ref = (c["tags"].get("design-ref") or "").strip()
        if not ref:
            continue
        if not DESIGN_REF_RE.match(ref):
            bad.append(f"{c['id']}: malformed design-ref '{ref}' "
                       f"(expected '<fileKey>/<nodeId> — <frame name>')")
        if not c["tags"].get("source", "").startswith("ac:"):
            bad.append(f"{c['id']}: design-ref requires an 'ac:' source — a mockup enters "
                       f"through the acceptance criteria, not as a source kind")
    checks.append({"name": "design-ref-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 5. scenario-coverage — advisory, never a failure
    if spec_paths:
        uncovered = sorted(scenarios - covered_scn)
        detail = f"advisory: {len(scenarios) - len(uncovered)}/{len(scenarios)} scenarios enriched a case"
        if uncovered:
            detail += " — uncovered: " + "; ".join(uncovered)
        checks.append({"name": "scenario-coverage", "ok": True, "detail": detail})
    else:
        checks.append({"name": "scenario-coverage", "ok": True,
                       "detail": "n/a (no OpenSpec file)"})

    # An AC named by a still-unresolved conflict is exempt from coverage and must carry
    # no case at all: nothing half-true reaches the plan.
    unresolved = [c for c in conflicts if not c["annotated"]]
    contradicted = set()
    for c in unresolved:
        m = CONFLICT_AC_RE.match(c["claim"])
        if m:
            contradicted.add(m.group(1))

    # 6. ac-coverage — required in both modes
    if not has_ac_section or not acs:
        checks.append({"name": "ac-coverage", "ok": False,
                       "detail": "missing '## Acceptance Criteria' — every case must be "
                                 "grounded in a business acceptance criterion"})
    else:
        uncovered_ac = sorted(set(acs) - covered_ac - contradicted)
        checks.append({"name": "ac-coverage", "ok": not uncovered_ac,
                       "detail": "ok" if not uncovered_ac else "uncovered: " + "; ".join(uncovered_ac)})

    # 7. conflict-resolution
    bad = []
    if not has_conflicts_section:
        bad.append("missing '## Conflicts' section header (may be empty, but it is required)")
    for line in unparsed_conflicts:
        bad.append(f"unrecognised '## Conflicts' line (expected '- \u26a0\ufe0f CONFLICT: …'): "
                   f"{line[:60]}")
    for c in conflicts:
        if c["annotated"] and not RESOLVED_GRAMMAR_RE.match(c["annotation"] or ""):
            bad.append(f"unrecognised '\u2192 resolved:' annotation "
                       f"'{(c['annotation'] or '')[:60]}' (expected 'business wins' or "
                       f"'spec wins, AC updated', optionally followed by detail)")
        sides = conflict_sides(c["claim"])
        if not sides:
            bad.append(f"conflict line names no two sides: {c['claim'][:60]}")
        for side in sides:
            if side not in CONFLICT_SOURCES:
                bad.append(f"unknown conflict source '{side}' "
                           f"(expected one of {', '.join(CONFLICT_SOURCES)})")
    for case in cases:
        src = case["tags"].get("source", "")
        if src.startswith("ac:") and src[len("ac:"):].strip() in contradicted:
            bad.append(f"{case['id']}: cites {src[len('ac:'):].strip()}, contradicted by an "
                       f"unresolved conflict — a contradicted AC must yield no case")
    checks.append({"name": "conflict-resolution", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 8. gap-honesty
    if spec_paths:
        # An OpenSpec scenario (or requirement) named in an unresolved conflict line is
        # exempt: the contradiction is already surfaced, exactly as its AC is exempt from
        # ac-coverage. Annotating the conflict removes the exemption.
        conflict_text = "\n".join(c["claim"] for c in unresolved)
        exempt = {name for name in (reqs_without | scenarios)
                  if name in conflict_text or name.split("/")[-1] in conflict_text}
        unmarked = sorted((reqs_without | (scenarios - covered_scn)) - gaps - exempt)
        checks.append({"name": "gap-honesty", "ok": not unmarked,
                       "detail": "ok" if not unmarked else "uncovered & unmarked: " + "; ".join(unmarked)})
    else:
        checks.append({"name": "gap-honesty", "ok": True, "detail": "n/a (no OpenSpec file)"})

    report = {
        "plan": plan_path, "openspec": spec_paths or None,
        "counts": {"scenarios": len(scenarios), "cases": len(cases), "acs": len(acs), "gaps": len(gaps)},
        "checks": checks,
    }
    report["ok"] = all(c["ok"] for c in checks)
    report["unresolved_conflicts"] = unresolved
    if not report["ok"]:
        report["outcome"], report["exit_code"] = "FAIL", 1
    elif unresolved:
        report["outcome"], report["exit_code"] = "HOLD", 2
    else:
        report["outcome"], report["exit_code"] = "PASS", 0
    return report


def print_report(report):
    print(f"kinoa-qa validator — {os.path.basename(report['plan'])}")
    print("=" * 60)
    for c in report["checks"]:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['name']}")
        if not c["ok"] or c["detail"].startswith(("n/a", "advisory")):
            print(f"       {c['detail']}")
    cnt = report["counts"]
    print("=" * 60)
    print(f"scenarios={cnt['scenarios']} cases={cnt['cases']} acs={cnt['acs']} gaps={cnt['gaps']}")
    if report["outcome"] == "HOLD":
        print("RESULT: HOLD — structurally valid; annotate each conflict with "
              "'→ resolved: …', then re-run. Unresolved:")
        for c in report["unresolved_conflicts"]:
            print(f"       ⚠️ {c['claim']}")
    else:
        print("RESULT:", "PASS" if report["ok"]
              else "FAIL — fix before the human gate / TestOps upsert")


def build_arg_parser():
    """The CLI surface, built separately so the accepted flags are unit-testable."""
    ap = argparse.ArgumentParser(description="kinoa-qa deterministic validator")
    ap.add_argument("plan", help="path to the generated test-plan.md")
    ap.add_argument("--openspec", action="append", default=None,
                    help="path to an OpenSpec capability spec.md (context only); repeatable")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    return ap


def main():
    args = build_arg_parser().parse_args()
    openspec = [os.path.abspath(p) for p in (args.openspec or [])] or None
    report = validate(os.path.abspath(args.plan), openspec)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
