#!/usr/bin/env python3
"""Token usage of the current Claude Code session, as a Markdown table on stdout: grouped
skill run -> agent (main session or subagent) -> model, with an estimated USD cost from
../prices.json. Stdlib only; reads the transcript files under $CLAUDE_CONFIG_DIR/projects/
(default ~/.claude/projects/)."""
import argparse
import bisect
import datetime
import glob
import json
import os
import re
import sys

NO_SKILL = "no skill"
NO_RUN = (0, 0, NO_SKILL)
MAIN = "main"
USAGE_KEYS = ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read")
SYNTHETIC_MODEL = "<synthetic>"
COMMAND_NAME = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
SKILL_EXPANSION = "Base directory for this skill"
AGENT_TOOLS = ("Agent", "Task")
TAIL_BYTES = 64 * 1024


def json_lines(path):
    """Every parseable JSON object of a JSON-lines file; broken lines are skipped."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict):
                yield entry


def read_json(path):
    """The JSON object in `path`, or {} when the file is missing, unreadable or not an object."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            value = json.load(f)
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def find_transcript(projects_dir, session_id):
    """The main transcript `<projects_dir>/*/<session_id>.jsonl` (the most recently modified one
    when several projects hold it), or None."""
    hits = glob.glob(os.path.join(projects_dir, "*", session_id + ".jsonl"))
    return max(sorted(hits), key=os.path.getmtime) if hits else None


def projects_root():
    """`<config dir>/projects`: the config dir is $CLAUDE_CONFIG_DIR when set, else ~/.claude."""
    base = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip() or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def parse_time(value):
    """An ISO-8601 `timestamp` as an aware datetime, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        moment = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=datetime.timezone.utc)


def normalize_model(model):
    """A model id without a `[1m]` tag or a trailing `-YYYYMMDD` date."""
    model = model.split("[", 1)[0]
    head, _, tail = model.rpartition("-")
    if head and len(tail) == 8 and tail.isdigit():
        return head
    return model


def usage_of(raw):
    """The five priced token counts of an API usage block; cache writes without a 5m/1h split
    count as 5-minute writes."""
    split = raw.get("cache_creation") or {}
    if "ephemeral_5m_input_tokens" in split or "ephemeral_1h_input_tokens" in split:
        write_5m = split.get("ephemeral_5m_input_tokens") or 0
        write_1h = split.get("ephemeral_1h_input_tokens") or 0
    else:
        write_5m, write_1h = raw.get("cache_creation_input_tokens") or 0, 0
    return {"input": raw.get("input_tokens") or 0, "output": raw.get("output_tokens") or 0,
            "cache_write_5m": write_5m, "cache_write_1h": write_1h,
            "cache_read": raw.get("cache_read_input_tokens") or 0}


def requests_of(path):
    """[(request id, normalized model, usage)] of one transcript file in file order, one entry per
    API request: lines sharing a requestId (or message.id) are one request."""
    seen, out = set(), []
    for entry in json_lines(path):
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        rid = entry.get("requestId") or message.get("id")
        raw = message.get("usage")
        model = message.get("model") or "?"
        if not rid or not raw or model == SYNTHETIC_MODEL or rid in seen:
            continue
        seen.add(rid)
        out.append((rid, normalize_model(model), usage_of(raw)))
    return out


def message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text") or "" for c in content or [] if isinstance(c, dict) and c.get("type") == "text")


def tool_uses(message):
    content = message.get("content")
    return [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"] if isinstance(content, list) else []


def is_tool_result(message):
    content = message.get("content")
    return isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content)


def new_state():
    """Run bookkeeping shared by every file of one session chain: the next run ordinal and the run
    each start (Skill tool_use id or user line uuid) opened, so a start copied into a resumed file
    reopens the same run instead of a new one."""
    return {"next": 1, "starts": {}}


def skill_timeline(path, state, fork_tools=()):
    """({request id: run}, {tool_use id: run}, [(time, run)]) of one main transcript. A run is
    (ordinal, 0, skill name); before the first run it is NO_RUN. A run starts at a slash command
    whose skill expansion follows on the same or the next user line, or at a Skill tool call that
    is the first tool call since the last genuine user prompt (not a tool_result, not isMeta); a
    Skill call made mid-task, or one that runs as a forked agent (`fork_tools`), keeps the run that
    was active. A run lasts until the next one starts."""
    current, pending, tool_since_prompt = NO_RUN, None, False
    request_run, tool_run, timeline = {}, {}, []

    def start(name, identity):
        if identity and identity in state["starts"]:
            return state["starts"][identity]
        run = (state["next"], 0, name)
        state["next"] += 1
        if identity:
            state["starts"][identity] = run
        return run

    for entry in json_lines(path):
        message = entry.get("message") or {}
        if entry.get("type") == "user":
            if not entry.get("isMeta") and not is_tool_result(message):
                tool_since_prompt = False
            text = message_text(message)
            hit = COMMAND_NAME.search(text)
            if SKILL_EXPANSION in text and (hit or pending):
                current, pending = start(hit.group(1) if hit else pending, entry.get("uuid")), None
            else:
                pending = hit.group(1) if hit else None
        elif entry.get("type") == "assistant":
            rid = entry.get("requestId") or message.get("id")
            for item in tool_uses(message):
                skill = (item.get("input") or {}).get("skill") if item.get("name") == "Skill" else None
                if skill and not tool_since_prompt and item.get("id") not in fork_tools:
                    current = start(skill, item.get("id"))
                    if rid:
                        request_run[rid] = current
                tool_since_prompt = True
                tool_run.setdefault(item.get("id"), current)
            if rid:
                request_run.setdefault(rid, current)
        moment = parse_time(entry.get("timestamp"))
        if moment is not None:
            timeline.append((moment, current))
    return request_run, tool_run, timeline


def subagent_files(session_path):
    """{agent id: agent-<id>.jsonl path} of one session's subagents/ folder and every folder below
    it (workflow subagents live under subagents/workflows/<workflow id>/)."""
    folder = os.path.join(session_path[:-len(".jsonl")], "subagents")
    out = {}
    for path in sorted(glob.glob(os.path.join(folder, "**", "agent-*.jsonl"), recursive=True)):
        agent_id = os.path.basename(path)[len("agent-"):-len(".jsonl")]
        if agent_id in out:
            agent_id = os.path.relpath(path, folder)[:-len(".jsonl")]
        out[agent_id] = path
    return out


def first_time(path):
    """The timestamp of the first line of a transcript that carries one, or None."""
    for entry in json_lines(path):
        moment = parse_time(entry.get("timestamp"))
        if moment is not None:
            return moment
    return None


def tail_entries(path, size=TAIL_BYTES):
    """The JSON objects on the complete lines of the last `size` bytes of a JSON-lines file."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            offset = max(0, f.tell() - size)
            f.seek(offset)
            data = f.read()
    except OSError:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    if offset and lines:
        lines = lines[1:]
    out = []
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def continued_in(path):
    """The session id a transcript says it was resumed into, or None. `continued-in` is the last
    record of a resumed file, so only the file's tail is read."""
    target = None
    for entry in tail_entries(path):
        if entry.get("type") == "continued-in":
            target = entry.get("continuedInSessionId") or target
    return target


def session_chain(path):
    """The main transcripts of one conversation, oldest first, ending with `path`: each earlier
    file is a sibling whose `continued-in` line names the next file's session id."""
    siblings = sorted(glob.glob(os.path.join(os.path.dirname(path), "*.jsonl")))
    resumed_into = {}
    for sibling in siblings:
        target = continued_in(sibling)
        if target:
            resumed_into.setdefault(target, sibling)
    chain = [path]
    while True:
        previous = resumed_into.get(os.path.basename(chain[0])[:-len(".jsonl")])
        if previous is None or previous in chain:
            return chain
        chain.insert(0, previous)


def read_session(path):
    """Every API request of the session whose main transcript is `path`, counted once:
    {"session_id", "resumed_from", "agents": {id: {"type", "description"}},
     "requests": [{"agent", "model", "skill", "run", "usage"}]}. The main session's agent id is
    "main"; `run` is the skill run key (see skill_timeline; a forked skill agent gets
    (ordinal of the run it was started in, n, its skill name)) and `skill` its skill name."""
    chain = session_chain(path)
    agents = {MAIN: {"type": "main session", "description": ""}}
    requests, seen = [], set()

    def add(agent, rid, model, usage, run):
        if rid in seen:
            return
        seen.add(rid)
        requests.append({"agent": agent, "model": model, "skill": run[2], "run": run, "usage": usage})

    files, metas, tool_owner = {}, {}, {}
    for session_path in chain:
        for agent_id, agent_path in subagent_files(session_path).items():
            stem = agent_path[:-len(".jsonl")]
            files[agent_id] = agent_path
            metas[agent_id] = read_json(stem + ".meta.json")
            metas[agent_id]["forkedSkill"] = read_json(stem + ".forked-skill.json").get("skillName")
            for entry in json_lines(agent_path):
                for item in tool_uses(entry.get("message") or {}):
                    tool_owner.setdefault(item.get("id"), agent_id)
    fork_tools = {meta.get("toolUseId") for meta in metas.values() if meta.get("forkedSkill") and meta.get("toolUseId")}
    state, request_run, tool_run, timeline = new_state(), {}, {}, []
    for session_path in chain:
        by_request, by_tool, times = skill_timeline(session_path, state, fork_tools)
        for rid, run in by_request.items():
            request_run.setdefault(rid, run)
        for tid, run in by_tool.items():
            tool_run.setdefault(tid, run)
        timeline.extend(times)
        for rid, model, usage in requests_of(session_path):
            add(MAIN, rid, model, usage, request_run.get(rid, NO_RUN))
    timeline.sort(key=lambda pair: pair[0])
    moments = [moment for moment, _ in timeline]

    def run_at(moment):
        index = bisect.bisect_right(moments, moment) if moment is not None else 0
        return timeline[index - 1][1] if index else NO_RUN

    resolved, forks = {}, {}

    def run_of(agent_id, visited):
        if agent_id in resolved:
            return resolved[agent_id]
        meta = metas[agent_id]
        tid = meta.get("toolUseId")
        parent = tool_owner.get(tid)
        if tid in tool_run:
            run = tool_run[tid]
        elif parent in metas and parent not in visited:
            run = run_of(parent, visited | {parent})
        else:
            run = run_at(first_time(files[agent_id]))
        if meta.get("forkedSkill"):
            forks[run[0]] = forks.get(run[0], 0) + 1
            run = (run[0], forks[run[0]], meta["forkedSkill"])
        resolved[agent_id] = run
        return run

    for agent_id, agent_path in files.items():
        meta = metas[agent_id]
        agents[agent_id] = {"type": meta.get("agentType") or "?", "description": meta.get("description") or ""}
        run = run_of(agent_id, {agent_id})
        for rid, model, usage in requests_of(agent_path):
            add(agent_id, rid, model, usage, run)
    return {"session_id": os.path.basename(path)[:-len(".jsonl")], "resumed_from": len(chain) - 1,
            "agents": agents, "requests": requests}


def run_labels(session):
    """{run key: label} in time order: a skill's first run is its name, a later one
    "<name> (run N)"; everything before the first run is "no skill"."""
    labels, counts = {}, {}
    for run in sorted({request["run"] for request in session["requests"]}):
        counts[run[2]] = counts.get(run[2], 0) + 1
        labels[run] = run[2] if counts[run[2]] == 1 else "{} (run {})".format(run[2], counts[run[2]])
    return labels


def add_usage(total, usage):
    for key in USAGE_KEYS:
        total[key] += usage[key]


def totals(session, *keys):
    """Summed usage per tuple of request fields, e.g. totals(s, "agent", "model")."""
    out = {}
    for request in session["requests"]:
        key = tuple(request[k] for k in keys)
        add_usage(out.setdefault(key, dict.fromkeys(USAGE_KEYS, 0)), request["usage"])
    return out


PRICES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prices.json")


def load_prices(path=None):
    """The plugin's price file: {"as_of", "source", "models": {model id: USD per million tokens
    for each of the five usage keys}}."""
    with open(path or PRICES, encoding="utf-8") as f:
        return json.load(f)


def request_cost(model, usage, prices):
    """Estimated USD cost of `usage` on `model`, or None when the model has no price."""
    rates = prices.get("models", {}).get(normalize_model(model))
    if rates is None:
        return None
    return sum(usage[key] * rates[key] for key in USAGE_KEYS) / 1000000


TABLE_HEAD = ("| Skill run | Agent | Model | Input | Output | Cache write | Cache read | Cost |\n"
              "|---|---|---|--:|--:|--:|--:|--:|")
CURRENT_TURN_NOTE = "The current turn's tokens may be missing or partial: its requests are still being written."


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def agent_label(session, agent_id):
    if agent_id == MAIN:
        return "main session"
    agent = session["agents"].get(agent_id) or {}
    kind, description = agent.get("type") or "?", agent.get("description") or ""
    return "{}: {}".format(kind, description) if description else kind


def money(cost):
    """`no price` for None; 4 decimals below one cent so a small run does not read as $0.00."""
    if cost is None:
        return "no price"
    return "${:.4f}".format(cost) if 0 < cost < 0.01 else "${:.2f}".format(cost)


def table_line(first, agent, model, usage, cost):
    numbers = [usage["input"], usage["output"], usage["cache_write_5m"] + usage["cache_write_1h"], usage["cache_read"]]
    return "| " + " | ".join([first, agent, model] + ["{:,}".format(n) for n in numbers] + [money(cost)]) + " |"


def render_markdown(session, prices):
    """The report: a header, one table grouped skill run -> agent -> model with a subtotal per
    skill run and a session total, then the notes that apply."""
    groups, labels = {}, run_labels(session)
    for request in session["requests"]:
        agents = groups.setdefault(request["run"], {})
        models = agents.setdefault(request["agent"], {})
        models.setdefault(request["model"], []).append(request)
    unpriced, lines = [], [TABLE_HEAD]
    total, total_cost = dict.fromkeys(USAGE_KEYS, 0), None
    for run in sorted(groups):
        label = cell(labels[run])
        subtotal, subtotal_cost = dict.fromkeys(USAGE_KEYS, 0), None
        for agent_id, models in groups[run].items():
            for model, requests in models.items():
                usage = dict.fromkeys(USAGE_KEYS, 0)
                cost = 0.0
                for request in requests:
                    add_usage(usage, request["usage"])
                    one = request_cost(model, request["usage"], prices)
                    cost = None if one is None or cost is None else cost + one
                if cost is None and model not in unpriced:
                    unpriced.append(model)
                lines.append(table_line(label, cell(agent_label(session, agent_id)), cell(model), usage, cost))
                add_usage(subtotal, usage)
                if cost is not None:
                    subtotal_cost = (subtotal_cost or 0.0) + cost
        lines.append(table_line("**{} subtotal**".format(label), "", "", subtotal, subtotal_cost))
        add_usage(total, subtotal)
        if subtotal_cost is not None:
            total_cost = (total_cost or 0.0) + subtotal_cost
    lines.append(table_line("**Session total**", "", "", total, total_cost))
    header = "Session `{}`".format(session["session_id"])
    if session["resumed_from"]:
        header += " · resumed from {} earlier session(s)".format(session["resumed_from"])
    header += " · prices as of {} (estimate)".format(prices.get("as_of") or "?")
    notes = []
    if not any(agent_id != MAIN for agent_id in session["agents"]):
        notes.append("No subagents in this session.")
    if all(request["skill"] == NO_SKILL for request in session["requests"]):
        notes.append("No skill runs in this session.")
    if unpriced:
        notes.append("The cost total excludes {} (no price).".format(", ".join(unpriced)))
    notes.append(CURRENT_TURN_NOTE)
    return "# Token report\n\n{}\n\n{}\n\n{}\n".format(header, "\n".join(lines), "\n".join(notes))


def main(argv=None):
    """Print the report for $CLAUDE_CODE_SESSION_ID; exit 1 with a message on stderr and no
    report when the variable is unset or its transcript is missing."""
    argparse.ArgumentParser(description="Token usage of the current Claude Code session.").parse_args(argv)
    session_id = (os.environ.get("CLAUDE_CODE_SESSION_ID") or "").strip()
    if not session_id:
        print("token-report: CLAUDE_CODE_SESSION_ID is not set; run this from inside a Claude Code session.",
              file=sys.stderr)
        return 1
    projects_dir = projects_root()
    looked_for = os.path.join(projects_dir, "*", session_id + ".jsonl")
    path = find_transcript(projects_dir, session_id) if os.path.basename(session_id) == session_id else None
    if path is None:
        print("token-report: no transcript for session {}; looked for {}".format(session_id, looked_for),
              file=sys.stderr)
        return 1
    sys.stdout.write(render_markdown(read_session(path), load_prices()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
