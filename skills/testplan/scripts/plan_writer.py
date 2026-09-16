#!/usr/bin/env python3
"""Pure writers for kinoa-qa test-plan.md: carry assigned `allure-id:` values forward
across a regeneration, and write a newly assigned id back. Text in, text out — no file
I/O in the functions, no network, stdlib only. The CLI at the bottom reads two plan
files and prints the merged plan on stdout and the report on stderr."""
import argparse
import json
import re
import sys

from plan_parser import CASE_HEADING_RE, parse_cases

# Source of truth for the id shape is `ALLURE_ID_RE` in validate_test_plan.py (Gate 0a):
# a positive integer with no sign, separator, decimal point or leading zero. Duplicated
# here so this pure writer does not import the validator CLI module; the two must agree,
# or an id written back after a create fails the next run's validation.
ALLURE_ID_RE = re.compile(r"^[1-9][0-9]*$")


def _norm(title):
    """Match key for a case title: whitespace runs collapse and case is ignored.

    Nothing else is normalised — anything beyond that is a judgement call the
    generation subagent and the human gate own, not this module.
    """
    return " ".join(title.split()).casefold()


def _valid_id(value):
    text = str(value).strip()
    return text if ALLURE_ID_RE.match(text) else None


def _newline_of(text):
    """The dominant line terminator of a plan file, so a CRLF plan stays CRLF.

    Mixed input is normalised to the majority terminator rather than left mixed.
    """
    crlf = text.count("\r\n")
    return "\r\n" if crlf and crlf >= (text.count("\n") - crlf) else "\n"


def merge_allure_ids(previous_plan_text, new_plan_text):
    """Carry `allure-id:` from the previous plan into the regenerated one by exact title.

    Returns (merged_text, report). A title present exactly once on each side and carrying
    an id in the previous plan has that id inserted as the case's first field; every other
    case is REPORTED — never guessed — because a wrong id overwrites the wrong TestOps case.
    report: carried / retained (new plan already had an id the previous plan confirms under
    the same title) / suspect (new plan carries an id the previous plan does not corroborate)
    / unmatched (new case with no id) / orphaned (previous id no merged case carries).
    """
    previous_text = previous_plan_text or ""
    newline = _newline_of(new_plan_text)
    new_plan_text = new_plan_text.replace("\r\n", "\n")

    # Every previous title counts towards ambiguity, id or not: a duplicated title whose
    # first occurrence has no id is still a title this module cannot resolve.
    previous_by_title = {}
    previous_with_id = []
    ambiguous = set()
    seen_titles = set()
    for case in parse_cases(previous_text):
        key = _norm(case["title"])
        allure_id = _valid_id(case["tags"].get("allure-id", ""))
        entry = {"id": case["id"], "title": case["title"], "allure_id": allure_id}
        if allure_id:
            previous_with_id.append(entry)
        if key in seen_titles:
            ambiguous.add(key)
            previous_by_title.pop(key, None)
        seen_titles.add(key)
        if key not in ambiguous and allure_id:
            previous_by_title[key] = entry

    previous_titles_by_id = {}
    for entry in previous_with_id:
        previous_titles_by_id.setdefault(entry["allure_id"], set()).add(_norm(entry["title"]))

    new_cases = parse_cases(new_plan_text)
    new_id_by_case = {c["id"]: _valid_id(c["tags"].get("allure-id", "")) for c in new_cases}
    # A title occurring more than once on the new side carries nothing either: both cases
    # would otherwise receive the same id and one TestOps case would be written twice.
    new_title_counts = {}
    for case in new_cases:
        key = _norm(case["title"])
        new_title_counts[key] = new_title_counts.get(key, 0) + 1

    report = {"carried": [], "retained": [], "suspect": [], "unmatched": [], "orphaned": []}
    out = []
    for line in new_plan_text.split("\n"):
        out.append(line)
        m = CASE_HEADING_RE.match(line)
        if not m:
            continue
        case_id, title = m.group(1), m.group(2).strip()
        key = _norm(title)
        existing = new_id_by_case.get(case_id)
        if existing:
            known = previous_titles_by_id.get(existing)
            if known is None:
                report["suspect"].append({"id": case_id, "title": title,
                                          "allure_id": existing,
                                          "reason": "id not in the previous plan"})
            elif key not in known:
                report["suspect"].append({"id": case_id, "title": title,
                                          "allure_id": existing,
                                          "reason": "previous plan has this id under a "
                                                    "different title"})
            else:
                report["retained"].append({"id": case_id, "title": title,
                                           "allure_id": existing})
            continue
        match = previous_by_title.get(key) if new_title_counts.get(key, 0) == 1 else None
        if match:
            out.append("- allure-id: %s" % match["allure_id"])
            report["carried"].append({"id": case_id, "title": title,
                                      "allure_id": match["allure_id"]})
        else:
            report["unmatched"].append({"id": case_id, "title": title})

    merged = newline.join(out)
    # An orphan is a previous id no merged case carries — by presence in the merged plan,
    # not by which report list claimed it, so an id retained under a different title
    # cannot suppress the orphan report.
    merged_ids = {i for i in (_valid_id(c["tags"].get("allure-id", ""))
                              for c in parse_cases(merged)) if i}
    reported = set()
    for entry in previous_with_id:
        if entry["allure_id"] not in merged_ids and entry["allure_id"] not in reported:
            reported.add(entry["allure_id"])
            report["orphaned"].append(entry)
    return merged, report


def insert_allure_id(plan_text, case_id, allure_id):
    """Write a newly assigned id back as the first field under `### <case_id> · …`.

    Every other byte of the plan is left untouched. Raises ValueError for an id that is
    not a positive integer, an unknown case, a case that already carries an id, or a
    `TC-n` handle used by more than one heading — each would re-point a real case.
    """
    valid = _valid_id(allure_id)
    if not valid:
        raise ValueError("allure-id must be a positive integer, got %r" % (allure_id,))
    newline = _newline_of(plan_text)
    plan_text = plan_text.replace("\r\n", "\n")
    for case in parse_cases(plan_text):
        if case["id"] == case_id and case["tags"].get("allure-id"):
            raise ValueError("%s already carries allure-id %s"
                             % (case_id, case["tags"]["allure-id"]))

    out = []
    found = 0
    for line in plan_text.split("\n"):
        out.append(line)
        m = CASE_HEADING_RE.match(line)
        if m and m.group(1) == case_id:
            out.append("- allure-id: %s" % valid)
            found += 1
    if not found:
        raise ValueError("no case %s in this plan" % case_id)
    if found > 1:
        raise ValueError("%s names %d headings in this plan; case handles must be unique"
                         % (case_id, found))
    return newline.join(out)


def print_report(report, stream=None):
    """The Step D gate view of a merge: one line per case, suspects and orphans last."""
    out = stream or sys.stdout
    for entry in report["carried"]:
        print("carried   %s → %s · %s"
              % (entry["id"], entry["allure_id"], entry["title"]), file=out)
    for entry in report["retained"]:
        print("retained  %s → %s · %s"
              % (entry["id"], entry["allure_id"], entry["title"]), file=out)
    for entry in report["unmatched"]:
        print("unmatched %s · %s" % (entry["id"], entry["title"]), file=out)
    for entry in report["suspect"]:
        print("SUSPECT   %s → %s · %s — %s"
              % (entry["id"], entry["allure_id"], entry["title"], entry["reason"]), file=out)
    for entry in report["orphaned"]:
        print("orphaned  %s · %s" % (entry["allure_id"], entry["title"]), file=out)


def build_arg_parser():
    """The CLI surface, built separately so the accepted flags are unit-testable."""
    ap = argparse.ArgumentParser(
        description="kinoa-qa mechanical allure-id merge: previous plan + regenerated "
                    "plan → merged plan on stdout, report on stderr")
    ap.add_argument("--previous", required=True,
                    help="path to the previous plan at the stable path (may be missing "
                         "on a first run)")
    ap.add_argument("--new", required=True, dest="new",
                    help="path to the regenerated plan returned by Step B")
    ap.add_argument("--json", action="store_true",
                    help="emit the report as JSON instead of one line per case")
    return ap


def main():
    args = build_arg_parser().parse_args()
    try:
        with open(args.previous, encoding="utf-8") as fh:
            previous = fh.read()
    except FileNotFoundError:
        previous = ""
    try:
        with open(args.new, encoding="utf-8") as fh:
            new = fh.read()
    except OSError as exc:
        # A merged plan is all-or-nothing: exit non-zero with nothing on stdout, so a
        # caller that branches on the exit code never writes an unmerged plan.
        print(f"plan_writer: cannot read --new {args.new}: {exc.strerror}", file=sys.stderr)
        sys.exit(1)
    merged, report = merge_allure_ids(previous, new)
    sys.stdout.write(merged)
    if args.json:
        print(json.dumps(report, indent=2), file=sys.stderr)
    else:
        print_report(report, sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
