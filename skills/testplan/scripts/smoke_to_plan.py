#!/usr/bin/env python3
"""Convert a smoke-test Jira sub-task into a `scope: smoke` test-plan.md. stdlib-only; no
network and no LLM: the plan is built from one JSON input file and nothing else.

Input file — one JSON object holding the raw Atlassian MCP responses, unmodified:

    {"subtask":      <getJiraIssue(<SUBTASK-KEY>, responseContentFormat="markdown")>,
     "story":        <getJiraIssue(<parent STORY-KEY>, responseContentFormat="markdown")>,
     "remote_links": <getJiraIssueRemoteIssueLinks(<SUBTASK-KEY>)>}

`subtask` and `story` are either the MCP envelope `{"issues": {"nodes": [<issue>]}}` or a
bare issue object; `remote_links` is the list the MCP returns (`[]` when there are none).

Only `## Preconditions`, `## Steps` and `## Open questions` of the sub-task are read; every
other section, blockquotes, run notes and ✅/⚠️ lines are dropped, and source tags are
stripped by shape. Bad input raises SmokeRefusal naming the reason; the CLI prints it as
`refused: <reason>` on stderr and exits 1.
"""
import argparse
import json
import os
import re
import sys

from jira_remote_link import case_id_from_title
from plan_parser import parse_cases, parse_header


class SmokeRefusal(Exception):
    """The sub-task cannot become a smoke plan; the message names the reason."""


# A tag's opening, at a `[`. Fixed tags end at their own `]`; value tags (`PRD:`, `Figma:`,
# `KING-n…`) end where `_value_end` says.
TAG_HEAD_RE = re.compile(r"\[(?:GATE\]|AC-\d+\]|Story\]|live-confirmed\]"
                         r"|[^\[\]\n`]*?→\s*live-confirmed\]|PRD:|Figma:|KING-\d+)")
TAG_WHOLE_RE = re.compile(r"\[(?:GATE|AC-\d+|Story|live-confirmed|[^\[\]]*?→\s*live-confirmed"
                          r"|(?:PRD|Figma):.*|KING-\d+(?:\D.*)?)\]\Z", re.S)
AC_TAG_RE = re.compile(r"\[(AC-\d+)\]\Z")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")


def _span_tags(content):
    """The tags a code span is made of, or None when it holds anything else. The span is
    split only where `]` is followed, with or without whitespace, by the head of a new tag; a
    part that does not start a new tag is rejoined, so a value containing `]` or `,` stays one tag;
    each part must end exactly where the same tag in prose would."""
    text = content.strip()
    if not text.startswith("[") or not TAG_HEAD_RE.match(text):
        return None
    starts = [0]
    for m in re.finditer(r"\]\s*(?=\[)", text):
        if TAG_HEAD_RE.match(text, m.end()):
            starts.append(m.end())
    pieces = [text[a:b].strip() for a, b in zip(starts, starts[1:] + [len(text)])]
    whole = all(_tag_end(p, 0, TAG_HEAD_RE.match(p)) == len(p) for p in pieces)
    return pieces if whole else None


def _value_end(text, start):
    """The index past the `]` that closes the value tag whose `[` is at `start`, or None: its
    first `]` that balances the brackets, moved on to a later `]` of the line only while the
    text in between holds `, ` and none of `(`, `)`, `[` — a `]` in prose never extends it."""
    depth, end = 0, None
    for i in range(start, len(text)):
        if text[i] == "\n":
            break
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None
    for j in range(end, len(text)):
        if text[j] in "\n[":
            break
        if text[j] == "]":
            between = text[end:j]
            if ", " in between and not any(c in between for c in "()"):
                end = j + 1
    return end


def _tag_end(text, start, head):
    """The index past the tag whose head `head` matched at `start`, or None when no tag ends."""
    end = head.end() if head.group(0).endswith("]") else _value_end(text, start)
    return end if end and TAG_WHOLE_RE.match(text[start:end]) else None


def _strip_bare(text, tags):
    out, i = [], 0
    while i < len(text):
        m = TAG_HEAD_RE.match(text, i) if text[i] == "[" else None
        end = _tag_end(text, i, m) if m else None
        if end:
            tags.append(text[i:end])
            i = end
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _tidy(text):
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r" +([.,;:!?])", r"\1", text)


def strip_tags(text):
    """Return (clean text, [tag, …]) for one step, precondition or question. A code span made
    only of tags is removed whole, a code span holding anything else is kept verbatim, and a
    bare tag in prose is removed; tags are returned in the order they appear."""
    tags, out, pos = [], [], 0
    for m in CODE_SPAN_RE.finditer(text):
        out.append(_strip_bare(text[pos:m.start()], tags))
        pieces = _span_tags(m.group(1))
        if pieces:
            tags.extend(pieces)
        else:
            out.append(m.group(0))
        pos = m.end()
    out.append(_strip_bare(text[pos:], tags))
    return _tidy("".join(out)), tags


SECTION_RE = re.compile(r"^##\s+(.*?)\s*#*\s*$")


def _section(description, name):
    """The lines under `## <name>` (case-insensitive), or None when the section is absent."""
    lines, inside, found = [], False, False
    for line in (description or "").replace("\r\n", "\n").split("\n"):
        m = SECTION_RE.match(line)
        if m:
            inside = m.group(1).strip().casefold() == name.casefold() and not found
            found = found or inside
            continue
        if inside:
            lines.append(line.replace("\u200b", "").replace("\u200c", ""))
    return lines if found else None


STEP_MARK_RE = re.compile(r"^\*\*(\d+)([a-z]?)\.(.*?)\*\*(.*)$")
EXPECTED_RE = re.compile(r"^[_*]{1,2}Expected:?[_*]{1,2}:?\s*(.*)$", re.I)
RUN_NOTE_RE = re.compile(r"^[_*]{1,2}Run note:?[_*]{1,2}", re.I)


def _dropped(stripped):
    """A line the converter never reads: blockquote, run note, ✅/⚠️ mark, sub-heading."""
    return (stripped.startswith((">", "#", "✅", "⚠"))
            or bool(RUN_NOTE_RE.match(stripped)))


def _append(text, line):
    """`text` continued by one more line: a list item's text joins after `; ` (a space when
    `text` already ends in punctuation), any other line after a space."""
    m = ITEM_RE.match(line)
    if not m:
        return text + " " + line.strip()
    sep = " " if re.search(r"[.;:!?]$", text.rstrip()) else "; "
    return text.rstrip() + sep + m.group(2).strip()


def _raw_steps(lines):
    """The raw steps of `## Steps`. A part (action or expected) runs until the next step
    marker, `Expected:` marker or dropped line; a blank line does not end it."""
    steps, cur, part = [], None, None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _dropped(stripped):
            part = None
            continue
        m = STEP_MARK_RE.match(stripped)
        if m:
            cur = {"label": m.group(1) + m.group(2), "sub": bool(m.group(2)),
                   "action": (m.group(3) + " " + m.group(4)).strip(), "expected": []}
            steps.append(cur)
            part = "action"
            continue
        m = EXPECTED_RE.match(stripped)
        if m and cur is not None:
            cur["expected"].append(m.group(1))
            part = "expected"
            continue
        if cur is not None and part == "action":
            cur["action"] = _append(cur["action"], line)
        elif cur is not None and part == "expected":
            cur["expected"][-1] = _append(cur["expected"][-1], line)
    return steps


def _clean_step(raw):
    action, tags = strip_tags(raw["action"])
    expected = []
    for text in raw["expected"]:
        clean, more = strip_tags(text)
        expected.append(clean)
        tags += more
    acs = []
    for tag in tags:
        m = AC_TAG_RE.match(tag)
        if m and m.group(1) not in acs:
            acs.append(m.group(1))
    return {"label": raw["label"], "action": action,
            "expected": expected[0] if len(expected) == 1 else (None if not expected else expected),
            "gate": "[GATE]" in tags, "acs": acs}


def parse_steps(description):
    """The steps of `## Steps`, in order: [{label, action, expected, gate, acs}]. `expected`
    is the one expected result, None when the step has none, or the list when it has several.
    A sub-step (`2b`) without its own expected result folds into the step emitted just before
    it when that step is its parent or a sibling sub-step (`2` or `2a`)."""
    lines = _section(description, "Steps")
    if lines is None:
        return []
    steps = []
    for raw in _raw_steps(lines):
        step = _clean_step(raw)
        number = re.match(r"\d+", raw["label"]).group(0)
        prev = steps[-1] if steps else None
        if (raw["sub"] and step["expected"] is None and prev
                and re.match(r"\d+", prev["label"]).group(0) == number):
            parent = prev
            parent["action"] = _tidy(parent["action"] + " " + step["action"])
            parent["gate"] = parent["gate"] or step["gate"]
            parent["acs"] += [a for a in step["acs"] if a not in parent["acs"]]
            continue
        steps.append(step)
    return steps


ITEM_RE = re.compile(r"^(\s*)(?:[*+-]|\d+[.)])\s+(.*)$")


def _list_items(lines, stop_at_paragraph=True):
    """Top-level list items of `lines`, with nested items and continuation lines folded into
    their parent. Stops at a heading, a bold-only line, or a paragraph after a blank line."""
    items, blank = [], False
    for line in lines:
        if not line.strip():
            blank = True
            continue
        stripped = line.strip()
        if re.match(r"^#{1,6}\s", stripped) or (items and re.match(r"^\*\*[^*].*\*\*:?$", stripped)):
            break
        m = ITEM_RE.match(line)
        indent = len(line) - len(line.lstrip())
        if m and indent < 2:
            items.append(m.group(2).strip())
        elif items and (indent >= 2 or not blank):
            items[-1] += " " + (m.group(2).strip() if m else stripped)
        elif items and stop_at_paragraph:
            break
        blank = False
    return [_tidy(i) for i in items]


def parse_preconditions(description):
    """One statement per list item or paragraph line of `## Preconditions`, tags stripped."""
    lines = _section(description, "Preconditions")
    if lines is None:
        return []
    statements, part_of_item = [], False
    for line in lines:
        stripped = line.strip()
        if not stripped or _dropped(stripped):
            part_of_item = False
            continue
        m = ITEM_RE.match(line)
        if m and len(line) - len(line.lstrip()) < 2:
            statements.append(m.group(2))
            part_of_item = True
        elif part_of_item:
            statements[-1] += " " + (m.group(2) if m else stripped)
        else:
            statements.append(stripped)
    return [s for s in (strip_tags(s)[0] for s in statements) if s]


QUESTION_RE = re.compile(r"^(?:(\d+)[.)]\s+|[*+-]\s+|\*\*(\d+)\.\s*)(.*)$")


def parse_open_questions(description):
    """The items of `## Open questions`: [{label, text, answered}]. An item is a numbered or
    bulleted list item or a `**n. …**` paragraph; `answered` is true when it carries ✅."""
    lines = _section(description, "Open questions")
    if lines is None:
        return []
    questions, current = [], None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            current = None
            continue
        m = QUESTION_RE.match(stripped) if len(line) - len(line.lstrip()) < 2 else None
        if m:
            label = m.group(1) or m.group(2) or str(len(questions) + 1)
            # A `**n. …**` item closes its bold later in the line; drop that closing pair.
            text = m.group(3).replace("**", "", 1) if m.group(2) else m.group(3)
            current = {"label": label, "text": text}
            questions.append(current)
        elif current is not None:
            current["text"] += " " + stripped
    for q in questions:
        q["answered"] = "✅" in q["text"]
        q["text"] = strip_tags(q["text"].replace("✅", ""))[0]
    return questions


AC_HEADING_TEXTS = ("acceptance criteria", "ac", "acs")
AC_HEADING_RE = re.compile(r"^(?:#{2,3}\s+(.*?)\s*#*|\*\*(.*?)\*\*:?)\s*$")


def _is_ac_heading(line):
    m = AC_HEADING_RE.match(line.strip())
    if not m:
        return False
    text = (m.group(1) if m.group(1) is not None else m.group(2)).strip().rstrip(":").strip()
    return text.casefold() in AC_HEADING_TEXTS


def _ac_field(story):
    """The Story's acceptance-criteria field value: by the `names` map when the response
    carries one, else a field key that reads "acceptance criteria"."""
    fields = story.get("fields") or {}
    keys = [k for k, name in (story.get("names") or {}).items()
            if str(name).strip().casefold() == "acceptance criteria"]
    keys += [k for k in fields if re.sub(r"[^a-z]", "", k.casefold()) == "acceptancecriteria"]
    for key in keys:
        if isinstance(fields.get(key), str) and fields[key].strip():
            return fields[key]
    return None


def story_acceptance_criteria(story):
    """The Story's acceptance criteria, in order; `AC-n` is the n-th, counted from 1. Read
    from the top-level items under the first heading or bold line reading "Acceptance
    criteria", "AC" or "ACs" (the whole line, any case) in the description, else from the acceptance-criteria field. [] when neither
    holds a list."""
    lines = (story.get("fields", {}).get("description") or "").replace("\r\n", "\n").split("\n")
    lines = [l.replace("\u200b", "").replace("\u200c", "") for l in lines]
    for i, line in enumerate(lines):
        if _is_ac_heading(line):
            items = _list_items(lines[i + 1:])
            if items:
                return items
            break
    field = _ac_field(story)
    return _list_items(field.replace("\r\n", "\n").split("\n")) if field else []


def _issue(response, role):
    """The one issue in an MCP `getJiraIssue` response, or the bare issue object."""
    if isinstance(response, dict) and isinstance(response.get("issues"), dict):
        nodes = response["issues"].get("nodes") or []
        if len(nodes) == 1 and isinstance(nodes[0], dict):
            return nodes[0]
    elif isinstance(response, dict) and response.get("key"):
        return response
    raise SmokeRefusal(f"the input's '{role}' is not a getJiraIssue response for one issue")


def _allure_id(links):
    """The TestOps case id the sub-task's `Allure TestOps case <id>` remote link records, or
    None. Links with other titles are ignored; two links naming different ids refuse."""
    if not isinstance(links, list):
        raise SmokeRefusal("the input's 'remote_links' is not the list "
                           "getJiraIssueRemoteIssueLinks returns")
    ids = []
    for entry in links:
        title = ((entry or {}).get("object") or {}).get("title") if isinstance(entry, dict) else None
        case_id = case_id_from_title(title)
        if case_id is not None and case_id not in ids:
            ids.append(case_id)
    if len(ids) > 1:
        raise SmokeRefusal("the sub-task carries Allure TestOps case links to different cases: "
                           + ", ".join(str(i) for i in ids) + " — keep one link and re-run")
    return ids[0] if ids else None


SMOKE_PREFIX_RE = re.compile(r"^\s*smoke test:\s*", re.I)


def analyse(data):
    """Read the input file's content and refuse anything that cannot become a smoke plan.
    Returns {subtask_key, story_key, story_summary, title, acs, cited, steps, preconditions,
    questions, allure_id}."""
    if not isinstance(data, dict):
        raise SmokeRefusal("the input is not a JSON object with 'subtask', 'story' and "
                           "'remote_links'")
    if "remote_links" not in data:
        raise SmokeRefusal("the input has no 'remote_links': the sub-task's remote links are "
                           "the only durable record of its TestOps case id")
    subtask = _issue(data.get("subtask"), "subtask")
    story = _issue(data.get("story"), "story")
    key = subtask.get("key", "?")
    fields = subtask.get("fields") or {}
    issuetype = fields.get("issuetype") or {}
    parent = fields.get("parent") or {}
    parent_type = ((parent.get("fields") or {}).get("issuetype") or {}).get("name")
    if not issuetype.get("subtask"):
        raise SmokeRefusal(f"{key} is a {issuetype.get('name') or 'issue'}, not a sub-task "
                           f"of a Story")
    if not parent.get("key") or parent_type != "Story":
        raise SmokeRefusal(f"{key} is not a sub-task of a Story (its parent "
                           f"{parent.get('key') or '—'} is a {parent_type or 'missing issue'})")
    story_key = parent["key"]
    if story.get("key") != story_key:
        raise SmokeRefusal(f"the input's story is {story.get('key')}, but {key}'s parent "
                           f"Story is {story_key}")
    if ((story.get("fields") or {}).get("issuetype") or {}).get("name") != "Story":
        raise SmokeRefusal(f"{story_key} is not a Story")

    description = fields.get("description") or ""
    if _section(description, "Preconditions") is None:
        raise SmokeRefusal(f"{key} has no '## Preconditions' section; the converter never "
                           f"invents a precondition")
    preconditions = parse_preconditions(description)
    if not preconditions:
        raise SmokeRefusal(f"{key}'s '## Preconditions' section is empty; the converter never "
                           f"invents a precondition")
    if _section(description, "Steps") is None:
        raise SmokeRefusal(f"{key} has no '## Steps' section")
    steps = parse_steps(description)
    if not steps:
        raise SmokeRefusal(f"{key}'s '## Steps' section holds no numbered step")
    for step in steps:
        if step["expected"] is None:
            raise SmokeRefusal(f"step {step['label']} of {key} has no expected result")
        if isinstance(step["expected"], list):
            raise SmokeRefusal(f"step {step['label']} of {key} has {len(step['expected'])} "
                               f"expected results; a smoke step has exactly one")
    if not any(s["gate"] for s in steps):
        raise SmokeRefusal(f"{key} has no [GATE] step, so no step says the feature is live")

    acs = story_acceptance_criteria(story)
    if not acs:
        raise SmokeRefusal(f"the parent Story {story_key} has no acceptance criteria list "
                           f"(a heading or bold line reading 'Acceptance criteria', 'AC' or 'ACs' followed by "
                           f"bullets or numbered items, or an acceptance-criteria field)")
    cited = []
    for step in steps:
        for ac in step["acs"]:
            n = int(ac.split("-")[1])
            if not 1 <= n <= len(acs):
                raise SmokeRefusal(f"step {step['label']} of {key} cites {ac}, but the Story "
                                   f"{story_key} lists {len(acs)} acceptance criteria")
            if ac not in cited:
                cited.append(ac)

    summary = (fields.get("summary") or "").strip()
    return {"subtask_key": key, "story_key": story_key,
            "story_summary": ((story.get("fields") or {}).get("summary") or "").strip(),
            "title": SMOKE_PREFIX_RE.sub("", summary).strip(),
            "acs": acs, "cited": cited, "steps": steps, "preconditions": preconditions,
            "questions": parse_open_questions(description),
            "allure_id": _allure_id(data.get("remote_links"))}


QA_ADDED_SOURCE = "QA-added: smoke scenario with no AC citation"


def _sentence(text):
    return text if re.search(r"[.!?)]$", text) else text + "."


def _target_halves(target):
    """(service, capability) from `--target <service>/<capability>`, split on the first `/`
    so the capability may hold more, or None without one."""
    if target is None:
        return None
    service, sep, capability = target.partition("/")
    if not sep or not service.strip() or not capability.strip():
        raise SmokeRefusal(f"--target must read <service>/<capability>, got '{target}'")
    return service.strip(), capability.strip()


def build_plan(data, target=None):
    """The `scope: smoke` test-plan.md for the input, as text: one `functional` P1 case whose
    steps are the sub-task's, under the parent Story's header and acceptance criteria. The
    same input always yields the same text."""
    info = analyse(data)
    halves = _target_halves(target)
    if not info["title"]:
        raise SmokeRefusal(f"{info['subtask_key']} has no summary to title the case with")
    story_key, subtask_key = info["story_key"], info["subtask_key"]
    gate_results = [_sentence(s["expected"]) for s in info["steps"] if s["gate"]]

    lines = [
        f"# QA Test Plan — {story_key} (smoke)",
        f"> AUTO-GENERATED by smoke_to_plan.py from the smoke-test sub-task {subtask_key}. "
        f"Fix the sub-task and re-run; never edit this file.",
        "> System of record: Allure TestOps · project KINOA. This file is a reviewable "
        "intermediate.",
        "",
        f"story: {story_key} · target: {'/'.join(halves) if halves else 'none'} · "
        f"title: {info['story_summary']}",
        f"from-smoke: {subtask_key}",
        "prd: none (smoke plan built from the sub-task)",
        "openspec: none",
        "design: none (smoke plan built from the sub-task)",
        "images: none",
        "scope: smoke",
        "",
        "## Acceptance Criteria",
        "",
    ]
    lines += [f"- AC-{n}: {text}" for n, text in enumerate(info["acs"], 1)]
    lines += ["", "## Cases", "", f"### TC-1 · {info['title']}"]
    if info["allure_id"] is not None:
        lines.append(f"- allure-id: {info['allure_id']}")
    lines += [
        "- type: functional",
        "- priority: P1",
        f"- purpose: Verify that {_sentence(info['title'])}",
        "- source: " + ("ac: " + ", ".join(info["cited"]) if info["cited"] else QA_ADDED_SOURCE),
        "- preconditions: " + info["preconditions"][0],
    ]
    lines += ["  " + p for p in info["preconditions"][1:]]
    lines.append("- steps:")
    for n, step in enumerate(info["steps"], 1):
        lines += [f"  {n}. {step['action']}", f"     → expected: {step['expected']}"]
    lines += ["- expected: " + " ".join(gate_results), "", "## Conflicts", "", "## Gaps", ""]
    lines += [f"- ⚠️ GAP: Open question {q['label']} — {q['text']}"
              for q in info["questions"] if not q["answered"]]
    text = "\n".join(lines).rstrip("\n") + "\n"

    header = parse_header(text)
    if (header.get("story"), header.get("title"), header.get("scope")) != (
            story_key, info["story_summary"], "smoke"):
        raise SmokeRefusal(f"the Story summary '{info['story_summary']}' cannot be written as "
                           f"the plan's title: the header would read it back as "
                           f"'{header.get('title')}'")
    cases = parse_cases(text)
    if len(cases) != 1 or cases[0]["title"] != info["title"]:
        raise SmokeRefusal(f"the case title '{info['title']}' does not read back from the plan")
    return text


PLANS_DIR = os.path.join("~", ".kinoa-qa", "plans")


def _path_slug(text):
    return re.sub(r"[^a-z0-9]", "-", text.lower())


def plan_path(story_key, target=None):
    """The stable plan path: `<STORY>-<service>-<capability>-smoke.test-plan.md`, or
    `<STORY>-no-target-smoke.test-plan.md` without `--target`, under ~/.kinoa-qa/plans."""
    halves = _target_halves(target)
    middle = "-".join(_path_slug(h) for h in halves) if halves else "no-target"
    return os.path.expanduser(os.path.join(PLANS_DIR,
                                           f"{story_key}-{middle}-smoke.test-plan.md"))


def build_arg_parser():
    """The CLI surface, built separately so the accepted flags are unit-testable."""
    ap = argparse.ArgumentParser(
        description="kinoa-qa smoke sub-task → scope: smoke test-plan.md on stdout")
    ap.add_argument("--input", required=True,
                    help="JSON file holding the raw subtask, story and remote_links MCP "
                         "responses")
    ap.add_argument("--target", default=None, help="<service>/<capability> (optional)")
    ap.add_argument("--print-path", action="store_true",
                    help="print the stable plan path instead of the plan")
    return ap


def main(argv=None):
    """Print the plan (or with --print-path its stable path) on stdout and return 0; on a
    refusal print `refused: <reason>` on stderr, nothing on stdout, and return 1."""
    args = build_arg_parser().parse_args(argv)
    try:
        try:
            with open(args.input, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            raise SmokeRefusal(f"cannot read --input {args.input}: {exc}")
        if args.print_path:
            output = plan_path(analyse(data)["story_key"], args.target) + "\n"
        else:
            output = build_plan(data, args.target)
    except SmokeRefusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
