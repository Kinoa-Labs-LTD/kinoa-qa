#!/usr/bin/env python3
"""kinoa-qa deterministic validator.

Checks a generated QA test-plan.md. The Jira Story, the PRD and any linked mockup are the
source of truth; OpenSpec files (`--openspec`, optional) are context only. Checks:

  1. required-fields — every `### TC-` case has type, priority, purpose, source,
     preconditions, non-empty steps, non-empty expected, and every step carries an
     `\u2192 expected:` result — exactly one under `scope: smoke`, one or more under
     `scope: e2e` or with the scope absent (the offending step is named by number);
  2. source-valid — every `source:` is `ac: AC-<n>[, AC-<m>…]` (a comma-separated list;
     each id must exist in `## Acceptance Criteria`, and a part that does not start a new
     `AC-<n>` is read as part of the id before it) or `QA-added: <reason>`; there is no
     `scenario:` source;
  3. openspec-ref-valid — every `openspec-ref:` names a real scenario of a supplied
     OpenSpec file, qualified `<capability>#<Requirement>/<Scenario>` when more than one
     file is supplied;
  4. design-ref-valid — every `design-ref:` reads `<fileKey>/<nodeId> — <frame name>` and
     accompanies an `ac:` source; checked syntactically, the validator never calls Figma;
  5. image-ref-valid — every `image-ref:` reads `<attachment-id> — <filename>` and
     accompanies an `ac:` source; checked syntactically, the validator never calls Jira;
  6. allure-id-valid — a present `allure-id:` is a positive integer and no two cases carry
     the same one (shape and uniqueness only; the validator is offline and never asks
     TestOps whether the id exists). The field is optional: its absence is the ordinary
     first-run state;
  7. scenario-coverage — advisory only: how many OpenSpec scenarios a case enriches;
  8. ac-coverage — `## Acceptance Criteria` is required and every AC listed there is cited
     by >=1 case, each id of an `ac:` list counting as cited. Under `scope: smoke` an
     uncovered AC is advisory (`ok`, detail `advisory: uncovered: …`); a missing section
     still FAILs in both formats;
  9. conflict-resolution — `## Conflicts` header present, no unrecognised line in the
     section, every side of each conflict (two or more) named with a known artifact, and no
     case citing (anywhere in its `ac:` list) an AC a still-unresolved conflict
     contradicts, and every `→ resolved:`
     annotation written in the documented grammar;
 10. gap-honesty — every scenario-less requirement AND every OpenSpec scenario no case
     enriches is named in a `## Gaps` line, unless an unresolved `## Conflicts` line already
     names it; spec coverage is advisory, dishonesty is not;
 11. scope-valid — the header's optional `scope:` is `e2e` or `smoke`, compared
     case-sensitively. Absent passes and means `e2e`; any other value, `story` included,
     FAILs naming the value and the allowed set;
 12. type-valid — every present `type:` is one of `functional`, `negative`, `edge`,
     `regression`, `nonfunctional`; any other value FAILs naming the case and the value,
     and `type: e2e` FAILs pointing at `scope: e2e` (a format, not a case type);
 13. smoke-shape — under `scope: smoke` the plan has exactly one case and it is
     `type: functional`; n/a for an e2e plan, the scope absent included. The smoke rules
     (here, in required-fields and in ac-coverage) apply only when `scope:` is exactly
     `smoke`, the comparison scope-valid makes; any other value runs the e2e rules;
 14. sections-present — the `## Cases` and `## Gaps` section headers are present (`## Gaps`
     may be empty); a missing one FAILs naming it. `## Acceptance Criteria` is ac-coverage's
     and `## Conflicts` is conflict-resolution's.

Exit 0 = PASS, 1 = FAIL, 2 = HOLD (structurally valid, but an unresolved conflict blocks
the TestOps upsert until the QA engineer annotates `→ resolved: …`).
"""
import argparse
import json
import os
import re
import sys

from plan_parser import (SCOPES, E2E_SCOPE, SMOKE_SCOPE,
                         parse_spec, parse_cases, parse_gaps, parse_acs, parse_conflicts,
                         parse_header, parse_ac_source)

def _capability_of(spec_path):
    """The capability a spec file belongs to: its parent directory, per the OpenSpec layout
    `openspec/specs/<capability>/spec.md`, falling back to the file's own stem."""
    head, tail = os.path.split(os.path.abspath(spec_path))
    return os.path.basename(head) if tail == "spec.md" else os.path.splitext(tail)[0]


AC_SECTION_RE = re.compile(r"^##\s+Acceptance Criteria\s*$", re.M)
# The required section headers no other check owns, in plan order. `## Gaps` may be empty.
REQUIRED_SECTIONS = ("Cases", "Gaps")
# `allure-id:` is assigned by Allure TestOps, so a valid one is a positive integer with no
# sign, separator or decimal point. Shape only: the validator is offline and never asks
# TestOps whether the id exists.
ALLURE_ID_RE = re.compile(r"^[1-9][0-9]*$")
DESIGN_REF_RE = re.compile(r"^[^/\s]+/[^/\s]+\s+—\s+\S.*$")
# `<attachment-id> — <filename>`. Matched, never split: a filename may legitimately contain
# an em dash, and splitting on it would truncate the value silently.
IMAGE_REF_RE = re.compile(r"^[0-9]+\s+—\s+\S.*$")
# The case types a plan may use. `e2e` is a format (the header's `scope:`), not a type.
CASE_TYPES = ("functional", "negative", "edge", "regression", "nonfunctional")
SMOKE_CASE_TYPE = "functional"
CONFLICT_SOURCES = ("story", "prd", "design", "openspec", "image")
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


def _step_problems(steps, smoke):
    """Every step must carry at least one `\u2192 expected:` result in both formats, smoke and
    e2e. Only under smoke is a step limited to exactly one; an e2e step may carry several,
    each becoming its own expected_body. Returns one message per offending step, naming its 1-based number so the QA engineer knows which
    line to fix. A blank `\u2192 expected:` counts as missing, matching the payload builder,
    which omits an empty expected result entirely."""
    problems = []
    for n, step in enumerate(steps, 1):
        if not step.get("expected"):
            problems.append(f"step {n} has no expected result")
        elif step.get("extra_expected") and smoke:
            problems.append(f"step {n} has {1 + len(step['extra_expected'])} expected results "
                            f"(exactly one is allowed)")
    return problems


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
    header = parse_header(plan_text)
    # The one definition of "the smoke rules apply": exactly the value scope-valid accepts
    # as smoke. Absent, `e2e` or an invalid value runs the e2e rules, and scope-valid alone
    # reports an invalid value. The default lives here, never in the parser.
    smoke = header.get("scope") == SMOKE_SCOPE
    checks = []

    # 1. required-fields
    bad = []
    for c in cases:
        missing = [k for k in ("type", "priority", "purpose", "source", "preconditions")
                   if not c["tags"].get(k)]
        if not c["tags"].get("expected"):
            missing.append("expected")
        if not c["steps"]:
            missing.append("steps")
        problems = [f"missing {', '.join(missing)}"] if missing else []
        problems += _step_problems(c["steps"], smoke)
        if problems:
            bad.append(f"{c['id']}: {'; '.join(problems)}")
    checks.append({"name": "required-fields", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 2. source-valid — business grounding only
    covered_ac, bad = set(), []
    for c in cases:
        src = c["tags"].get("source", "")
        if src.startswith("ac:"):
            refs = parse_ac_source(src)
            if not refs:
                bad.append(f"{c['id']}: 'ac:' source names no acceptance criterion")
            for ref in refs:
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

    # 5. image-ref-valid — syntax and source pairing only; never a Jira call
    bad = []
    for c in cases:
        ref = (c["tags"].get("image-ref") or "").strip()
        if not ref:
            continue
        if not IMAGE_REF_RE.match(ref):
            bad.append(f"{c['id']}: malformed image-ref '{ref}' "
                       f"(expected '<attachment-id> — <filename>')")
        if not c["tags"].get("source", "").startswith("ac:"):
            bad.append(f"{c['id']}: image-ref requires an 'ac:' source — an image enters "
                       f"through the acceptance criteria, not as a source kind")
    checks.append({"name": "image-ref-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 6. allure-id-valid — shape, plus uniqueness across the plan; existence in TestOps is
    # Step E's business. Two cases sharing an id would make Step E update one TestOps case
    # twice and never create the other, so a duplicate is a failure here, before any write.
    bad, present = [], 0
    by_id = {}
    for c in cases:
        if "allure-id" not in c["tags"]:
            continue
        present += 1
        raw = (c["tags"].get("allure-id") or "").strip()
        if not ALLURE_ID_RE.match(raw):
            bad.append(f"{c['id']}: malformed allure-id '{raw}' "
                       f"(expected a positive integer assigned by Step E)")
            continue
        by_id.setdefault(raw, []).append(c["id"])
    for raw, owners in by_id.items():
        if len(owners) > 1:
            bad.append(f"duplicate allure-id '{raw}' carried by " + ", ".join(owners) +
                       " — one TestOps case cannot be two plan cases")
    checks.append({"name": "allure-id-valid", "ok": not bad,
                   "detail": ("; ".join(bad) if bad else
                              f"ok: {present}/{len(cases)} cases carry an allure-id"
                              if present else
                              "ok: no case carries an allure-id (the first-run state)")})

    # 7. scenario-coverage — advisory, never a failure
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

    # 8. ac-coverage — the section is required in both formats; an uncovered AC fails an
    # e2e plan and is advisory under smoke.
    if not has_ac_section or not acs:
        checks.append({"name": "ac-coverage", "ok": False,
                       "detail": "missing '## Acceptance Criteria' — every case must be "
                                 "grounded in a business acceptance criterion"})
    else:
        uncovered_ac = sorted(set(acs) - covered_ac - contradicted)
        if not uncovered_ac:
            checks.append({"name": "ac-coverage", "ok": True, "detail": "ok"})
        elif smoke:
            checks.append({"name": "ac-coverage", "ok": True,
                           "detail": "advisory: uncovered: " + "; ".join(uncovered_ac)})
        else:
            checks.append({"name": "ac-coverage", "ok": False,
                           "detail": "uncovered: " + "; ".join(uncovered_ac)})

    # 9. conflict-resolution
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
        for ref in parse_ac_source(case["tags"].get("source", "")):
            if ref in contradicted:
                bad.append(f"{case['id']}: cites {ref}, contradicted by an unresolved "
                           f"conflict — a contradicted AC must yield no case")
    checks.append({"name": "conflict-resolution", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 10. gap-honesty
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

    # 11. scope-valid — the declared format, value only. Absent passes and means e2e;
    # anything but `e2e` or `smoke` fails naming the value.
    if "scope" not in header:
        scope_detail, scope_ok = f"ok: no scope declared ({E2E_SCOPE})", True
    elif header["scope"] in SCOPES:
        scope_detail, scope_ok = f"ok: scope '{header['scope']}'", True
    else:
        scope_ok = False
        scope_detail = (f"unrecognised scope '{header['scope']}' — allowed: "
                        + ", ".join(SCOPES) + f" (or omit the field for {E2E_SCOPE})")
    checks.append({"name": "scope-valid", "ok": scope_ok, "detail": scope_detail})

    # 12. type-valid — a present `type:` is one of CASE_TYPES; its absence is
    # required-fields' failure, not this one's.
    bad = []
    for c in cases:
        case_type = c["tags"].get("type")
        if not case_type or case_type in CASE_TYPES:
            continue
        if case_type == E2E_SCOPE:
            bad.append(f"{c['id']}: type '{case_type}' is a format, not a case type — "
                       f"declare it in the header as 'scope: {E2E_SCOPE}'")
        else:
            bad.append(f"{c['id']}: unknown type '{case_type}' — allowed: "
                       + ", ".join(CASE_TYPES))
    checks.append({"name": "type-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})

    # 13. smoke-shape — a smoke plan is exactly one `functional` case; n/a otherwise.
    if smoke:
        bad = []
        if len(cases) != 1:
            bad.append(f"a smoke plan has exactly one case, found {len(cases)}")
        for c in cases:
            if c["tags"].get("type") != SMOKE_CASE_TYPE:
                bad.append(f"{c['id']}: type '{c['tags'].get('type', '')}' — a smoke case "
                           f"is '{SMOKE_CASE_TYPE}'")
        checks.append({"name": "smoke-shape", "ok": not bad,
                       "detail": "ok" if not bad else "; ".join(bad)})
    else:
        checks.append({"name": "smoke-shape", "ok": True,
                       "detail": f"n/a (scope {header.get('scope') or E2E_SCOPE})"})

    # 14. sections-present — the required headers no other check owns, each named when
    # missing; a present-but-empty `## Gaps` passes.
    missing = [name for name in REQUIRED_SECTIONS
               if not re.search(rf"^##\s+{name}\s*$", plan_text, re.M)]
    checks.append({"name": "sections-present", "ok": not missing,
                   "detail": "ok" if not missing else "; ".join(
                       f"missing '## {name}' section header"
                       + (" (may be empty, but it is required)" if name == "Gaps"
                          else " (required)")
                       for name in missing)})

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
