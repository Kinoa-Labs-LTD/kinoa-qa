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
