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


# The one spelling of a case heading: `### TC-<handle> · <title>`. plan_writer inserts
# fields under the same headings this parser reads, so both must agree byte for byte.
CASE_HEADING_RE = re.compile(r"^###\s+(TC-\S+)\s+·\s+(.*\S)\s*$")

STEP_RE = re.compile(r"^\s+\d+\.\s+(\S.*?)\s*$")
STEP_EXPECTED_RE = re.compile(r"^\s+\u2192\s*expected:\s*(.*?)\s*$")


def parse_cases(plan_text):
    """Return list of dicts: {id, title, tags:{k:v}, steps:[{action, expected, extra_expected}]}.

    A step is a numbered line; its expected result is the `\u2192 expected:` line under it, and
    `expected` is None when the step has none, so an old-shape plan parses instead of crashing.
    Further expected lines for the same step land in `extra_expected`, which the validator
    rejects: the payload carries exactly one expected result per step. An indented line
    matching neither shape continues the action or expected result above it, so a wrapped
    sentence is never dropped.
    """
    cases = []
    cur = None
    in_steps = False
    last_key = None
    last_step_part = None
    for line in plan_text.splitlines():
        m = CASE_HEADING_RE.match(line)
        if m:
            if cur:
                cases.append(cur)
            cur = {"id": m.group(1), "title": m.group(2).strip(),
                   "tags": {}, "steps": []}
            in_steps = False
            last_key = None
            last_step_part = None
            continue
        if cur is None:
            continue
        if line.startswith("### ") or line.startswith("## "):
            cases.append(cur)
            cur = None
            in_steps = False
            last_step_part = None
            continue
        m = re.match(r"^-\s+([a-z-]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            cur["tags"][key] = val
            in_steps = (key == "steps")
            last_key = None if in_steps else key
            last_step_part = None
            continue
        if not in_steps and last_key and re.match(r"^\s+\S", line):
            # A continuation line extends the previous `- key: value` field, so a
            # multi-line `preconditions:` reaches TestOps newline-separated.
            prev = cur["tags"][last_key]
            cur["tags"][last_key] = (prev + "\n" + line.strip()) if prev else line.strip()
            continue
        if in_steps:
            m = STEP_RE.match(line)
            if m:
                cur["steps"].append({"action": m.group(1), "expected": None,
                                     "extra_expected": []})
                last_step_part = "action"
                continue
            m = STEP_EXPECTED_RE.match(line)
            if m and cur["steps"]:
                step = cur["steps"][-1]
                if step["expected"] is None:
                    step["expected"] = m.group(1)
                else:
                    step["extra_expected"].append(m.group(1))
                last_step_part = "expected"
                continue
            # An indented line that is neither a numbered step nor an expected result
            # continues whichever half was written last, so a wrapped sentence reaches
            # TestOps whole instead of being truncated at the line break.
            if last_step_part and cur["steps"] and re.match(r"^\s+\S", line):
                step = cur["steps"][-1]
                if last_step_part == "expected" and step["extra_expected"]:
                    prev = step["extra_expected"][-1]
                    step["extra_expected"][-1] = (prev + "\n" + line.strip()) if prev else line.strip()
                else:
                    prev = step[last_step_part] or ""
                    step[last_step_part] = (prev + "\n" + line.strip()) if prev else line.strip()
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


AC_ID_START_RE = re.compile(r"^AC-\d+")


def parse_ac_source(src):
    """Return the AC ids a `source:` value cites, in order and without duplicates; [] unless
    it is an `ac:` source. The list is comma-separated, but a part that does not start a new
    `AC-<n>` continues the part before it, so an unknown id is reported whole."""
    if not src.startswith("ac:"):
        return []
    ids = []
    for part in src[len("ac:"):].split(","):
        piece = part.strip()
        if not piece:
            continue
        if ids and not AC_ID_START_RE.match(piece):
            ids[-1] += ", " + piece
        else:
            ids.append(piece)
    return list(dict.fromkeys(ids))


RESOLVED_RE = re.compile(r"→\s*resolved:")
CONFLICT_LINE_RE = re.compile(r"^-\s+⚠️\s+CONFLICT:\s+(.*\S)\s*$")


def parse_conflicts(plan_text):
    """Return (has_section, [{claim, annotated, annotation}], unrecognised) for `## Conflicts`.

    `has_section` distinguishes a plan that omits the header (an old-shape plan) from one
    whose section is legitimately empty. A conflict is annotated when `→ resolved:` follows
    it, on the same line or on the next non-blank line before the next conflict; `claim` is
    the conflict text with that annotation stripped and `annotation` is the text that
    followed `→ resolved:` (None when the conflict is unannotated), so a caller can check
    it against the documented grammar. `unrecognised` holds every other
    non-blank line of the section, so a malformed conflict is never silently dropped.
    """
    section = []
    has_section = False
    in_conflicts = False
    for line in plan_text.splitlines():
        if re.match(r"^##\s+Conflicts\s*$", line):
            has_section = True
            in_conflicts = True
            continue
        if in_conflicts and line.startswith("## "):
            in_conflicts = False
        if in_conflicts:
            section.append(line)

    conflicts = []
    consumed = set()
    for pos, line in enumerate(section):
        m = CONFLICT_LINE_RE.match(line)
        if not m:
            continue
        body = m.group(1)
        annotation = None
        annotated = bool(RESOLVED_RE.search(body))
        if annotated:
            head, tail = RESOLVED_RE.split(body, maxsplit=1)
            body, annotation = head, tail.strip()
        else:
            for j in range(pos + 1, len(section)):
                later = section[j].strip()
                if not later:
                    continue
                if CONFLICT_LINE_RE.match(section[j]):
                    break
                if RESOLVED_RE.match(later):
                    annotated = True
                    annotation = RESOLVED_RE.split(later, maxsplit=1)[1].strip()
                    consumed.add(j)
                break
        conflicts.append({"claim": body.strip().rstrip("·—-").strip(),
                          "annotated": annotated, "annotation": annotation})

    unrecognised = [line.strip() for j, line in enumerate(section)
                    if line.strip() and j not in consumed and not CONFLICT_LINE_RE.match(line)]
    return has_section, conflicts, unrecognised


# The scope vocabulary lives here because every consumer — the validator, the payload
# builder, the field resolver and the merge — already imports this module. Four modules
# owning the same two strings is how one of them drifts.
E2E_SCOPE = "e2e"
SMOKE_SCOPE = "smoke"
SCOPES = (E2E_SCOPE, SMOKE_SCOPE)


def normalise_scope(scope):
    """One spelling of "is this e2e?" for every caller. Case and surrounding space are not
    meaningful in a scope, and `target_marker` already slugifies it, so comparing the raw
    string let a marker say `scope=e2e` while the status stayed `Draft`."""
    return (scope or "").strip().casefold()


# A header field: a lowercase key, a colon, a value. `·` separates several fields written
# on one logical line, so `story:` and `title:` parse the same way as `scope:` on its own.
HEADER_FIELD_RE = re.compile(r"^([a-z][a-z0-9-]*):\s*(.*?)\s*$")


def parse_header(plan_text):
    """Return the header fields of the prologue before the first `##` heading, as {key: value}.

    Only that prologue is the header, so a `story:`- or `scope:`-looking line inside a case
    body is never mistaken for one. An absent field is absent from the dict — never defaulted:
    the default lives in the consumer, so "the plan says nothing" stays distinguishable from
    "the plan says e2e".
    """
    header = {}
    for line in plan_text.splitlines():
        if line.startswith("## "):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue
        # `·` separates fields, but a value may legitimately contain one: a Jira summary
        # is copied into `title:` verbatim. A part that does not itself start a field is a
        # continuation of the previous value, not a new field, so it is rejoined rather than
        # dropped — Step E composes `Suite` from `title:`, and a truncation there is silent.
        pending = None
        for part in stripped.split("\u00b7"):
            piece = part.strip()
            m = HEADER_FIELD_RE.match(piece)
            if m:
                pending = m.group(1)
                header[pending] = m.group(2)
            elif piece and pending is not None:
                header[pending] = (header[pending] + " · " + piece).strip()
    return header
