# test_token_report.py
"""token-report's script, read on the synthetic sessions under its fixtures/ folder, each laid
out as a fake HOME: per-request dedupe, the per-agent and per-skill split, cost from the
plugin's prices.json, resumed sessions, and the CLI run with HOME (or CLAUDE_CONFIG_DIR) pointed
at a fixture home. Damaged files are built in a temp dir, never kept under fixtures/."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, shutil, subprocess, tempfile, unittest

# repo root: skills/testplan/scripts/ -> ../../..
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SCRIPTS = os.path.join(ROOT, "skills", "token-report", "scripts")
SCRIPT = os.path.join(SCRIPTS, "token_report.py")
PRICES = os.path.join(ROOT, "skills", "token-report", "prices.json")
FIXTURES = os.path.join(SCRIPTS, "fixtures")
sys.path.insert(0, SCRIPTS)
import token_report  # noqa: E402

NO_SKILL = "no skill"
NO_USAGE = {"input": 0, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}


def home(case):
    return os.path.join(FIXTURES, case)


def transcript(case, session_id):
    return os.path.join(home(case), ".claude", "projects", "-fake-project", session_id + ".jsonl")


def four(usage):
    """(input, output, cache write, cache read) of one usage dict."""
    return (usage["input"], usage["output"], usage["cache_write_5m"] + usage["cache_write_1h"],
            usage["cache_read"])


def run_script(case, session_id, config_dir=None, home_dir=None):
    """Run the script with HOME at the fixture home `case` (or `home_dir`), CLAUDE_CONFIG_DIR unset
    unless `config_dir` is given, and the session id in the env (or unset when None), so no real
    transcript is ever read."""
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CONFIG_DIR")}
    env["HOME"] = home_dir or home(case)
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    if session_id is not None:
        env["CLAUDE_CODE_SESSION_ID"] = session_id
    return subprocess.run([sys.executable, "-I", SCRIPT], cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=60)


def table_cells(stdout, column, value):
    """The cells of the first table line whose cell `column` is `value`, or [] when none is. Cells
    split on unescaped pipes only, so an escaped `\\|` inside a value stays in its cell."""
    for line in stdout.splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip()[1:-1])]
        if line.startswith("|") and len(cells) > column and cells[column] == value:
            return cells
    return []


def table_row(stdout, first_cell):
    return table_cells(stdout, 0, first_cell)


def table_row_for_model(stdout, model):
    return table_cells(stdout, 2, model)


def labelled(session, *keys):
    """totals() keyed by agent and run label instead of the run key, input tokens only."""
    labels = token_report.run_labels(session)
    out = {}
    for request in session["requests"]:
        key = tuple(labels[request["run"]] if k == "run" else request[k] for k in keys)
        out[key] = out.get(key, 0) + request["usage"]["input"]
    return out


def temp_projects(test):
    """A fresh `<tmp>/projects` folder removed after the test."""
    folder = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, folder)
    projects = os.path.join(folder, "projects")
    os.makedirs(projects)
    return projects


def fixture_files():
    """Every file under fixtures/, hidden folders (the fake `.claude`) included."""
    for folder, _, files in os.walk(FIXTURES):
        for f in sorted(files):
            yield os.path.join(folder, f)


class ReadSession(unittest.TestCase):
    def setUp(self):
        self.session = token_report.read_session(transcript("basic", "basic-session"))

    def test_a_request_written_on_three_lines_counts_once(self):
        main = token_report.totals(self.session, "agent").get(("main",), NO_USAGE)
        self.assertEqual((15, 150, 1000, 5000), four(main))

    def test_main_and_each_subagent_report_their_own_totals_per_model(self):
        got = {k: four(v) for k, v in token_report.totals(self.session, "agent", "model").items()}
        self.assertEqual({("main", "claude-opus-5-5"): (15, 150, 1000, 5000),
                          ("ba1", "claude-sonnet-5-5"): (7, 70, 300, 600),
                          ("ba2", "claude-haiku-4-5"): (1, 20, 200, 400),
                          ("ba2", "claude-sonnet-5-5"): (2, 10, 0, 100)}, got)

    def test_subagents_carry_their_type_and_description(self):
        agents = self.session["agents"]
        self.assertEqual({"type": "general-purpose", "description": "Review the diff"}, agents.get("ba1"))
        self.assertEqual({"type": "Explore", "description": "Find the parser"}, agents.get("ba2"))

    def test_the_synthetic_placeholder_model_is_ignored(self):
        models = {r["model"] for r in self.session["requests"]}
        self.assertEqual({"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5"}, models)

    def test_a_session_without_subagents_still_gives_the_main_total(self):
        session = token_report.read_session(transcript("basic", "solo-session"))
        got = {k: four(v) for k, v in token_report.totals(session, "agent").items()}
        self.assertEqual({("main",): (1, 2, 3, 4)}, got)


class SkillRuns(unittest.TestCase):
    def setUp(self):
        self.session = token_report.read_session(transcript("skills", "skills-session"))
        self.by_skill = labelled(self.session, "agent", "run")

    def test_pre_skill_work_and_mcp_turns_are_no_skill(self):
        self.assertEqual(1 + 2, self.by_skill.get(("main", NO_SKILL)))

    def test_a_skill_tool_call_starts_a_run_and_follow_up_turns_stay_in_it(self):
        self.assertEqual(4 + 8 + 16, self.by_skill.get(("main", "kinoa-aqa:failure-triage")))

    def test_a_slash_command_with_its_expansion_on_the_next_line_starts_a_run(self):
        self.assertEqual(32 + 128 + 256 + 512, self.by_skill.get(("main", "kinoa-dev:ticket")))

    def test_a_slash_command_with_its_expansion_on_the_same_line_starts_a_run(self):
        self.assertEqual(64, self.by_skill.get(("main", "kinoa-qa:testplan")))

    def test_subagents_count_under_the_skill_active_when_they_started(self):
        self.assertEqual(100, self.by_skill.get(("kpre", NO_SKILL)))
        self.assertEqual(200, self.by_skill.get(("ka1", "kinoa-aqa:failure-triage")))

    def test_a_nested_subagent_stays_under_the_skill_of_its_parent(self):
        self.assertEqual(400, self.by_skill.get(("kn1", "kinoa-aqa:failure-triage")))

    def test_a_forked_skill_agent_counts_under_its_own_skill_name(self):
        self.assertEqual(800, self.by_skill.get(("kf1", "code-review")))

    def test_a_second_run_of_a_skill_is_its_own_group_and_keeps_its_tokens_out_of_the_first(self):
        self.assertEqual(1024 + 2048 + 4096, self.by_skill.get(("main", "kinoa-aqa:failure-triage (run 2)")))
        self.assertEqual(4 + 8 + 16, self.by_skill.get(("main", "kinoa-aqa:failure-triage")))
        self.assertEqual(200, self.by_skill.get(("ka1", "kinoa-aqa:failure-triage")))
        self.assertEqual([NO_SKILL, "kinoa-aqa:failure-triage", "kinoa-dev:ticket", "code-review",
                          "kinoa-aqa:failure-triage (run 2)", "kinoa-qa:testplan"],
                         [label for _, label in sorted(token_report.run_labels(self.session).items())])

    def test_a_skill_loaded_mid_task_keeps_the_work_and_its_subagents_in_the_outer_run(self):
        self.assertEqual(1600, self.by_skill.get(("kmid", "kinoa-dev:ticket")))
        self.assertEqual([], [key for key in self.by_skill if "claude-api" in key[1]])

    def test_a_workflow_subagent_counts_under_the_run_active_when_it_started(self):
        self.assertEqual(3200, self.by_skill.get(("kw1", "kinoa-aqa:failure-triage (run 2)")))
        self.assertEqual({"type": "workflow-subagent", "description": "Lint | format"}, self.session["agents"].get("kw1"))

    def test_every_request_is_attributed_exactly_once(self):
        self.assertEqual(1 + 2 + 4 + 8 + 16 + 32 + 64 + 100 + 200 + 400 + 800
                         + 128 + 256 + 512 + 1600 + 1024 + 2048 + 4096 + 3200, sum(self.by_skill.values()))


class DamagedFiles(unittest.TestCase):
    def test_a_truncated_multibyte_last_line_is_skipped_and_the_rest_reports(self):
        projects = temp_projects(self)
        folder = os.path.join(projects, "-fake-project")
        os.makedirs(folder)
        target = os.path.join(folder, "cut-session.jsonl")
        shutil.copy(transcript("basic", "solo-session"), target)
        with open(target, "ab") as f:
            f.write(b'{"type": "user", "message": {"content": "caf\xc3')
        session = token_report.read_session(target)
        self.assertEqual({("main",): (1, 2, 3, 4)}, {k: four(v) for k, v in token_report.totals(session, "agent").items()})
        result = run_script("basic", "cut-session", config_dir=os.path.dirname(projects))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["1"], table_row(result.stdout, "**Session total**")[3:4])

    def test_a_corrupt_or_non_object_meta_file_still_reports_the_agent(self):
        projects = temp_projects(self)
        folder = os.path.join(projects, "-fake-project")
        shutil.copytree(os.path.dirname(transcript("basic", "basic-session")), folder)
        subagents = os.path.join(folder, "basic-session", "subagents")
        for name, text in (("agent-ba1.meta.json", '{"agentType": '), ("agent-ba2.meta.json", "[1, 2]")):
            with open(os.path.join(subagents, name), "w", encoding="utf-8") as f:
                f.write(text)
        session = token_report.read_session(os.path.join(folder, "basic-session.jsonl"))
        got = {k: v["input"] for k, v in token_report.totals(session, "agent").items()}
        self.assertEqual({("main",): 15, ("ba1",): 7, ("ba2",): 3}, got)
        self.assertEqual({"type": "?", "description": ""}, session["agents"].get("ba1"))
        self.assertEqual({}, token_report.read_json(os.path.join(subagents, "agent-ba2.meta.json")))

    def test_the_continued_in_record_is_found_at_the_end_of_a_long_file(self):
        projects = temp_projects(self)
        folder = os.path.join(projects, "-fake-project")
        shutil.copytree(os.path.dirname(transcript("resumed", "new-session")), folder)
        old = os.path.join(folder, "old-session.jsonl")
        with open(old, encoding="utf-8") as f:
            lines = f.read().splitlines(True)
        padding = json.dumps({"type": "progress", "text": "x" * 1000}) + "\n"
        with open(old, "w", encoding="utf-8") as f:
            f.writelines(lines[:-1] + [padding] * 200 + lines[-1:])
        self.assertGreater(os.path.getsize(old), 2 * token_report.TAIL_BYTES)
        new = os.path.join(folder, "new-session.jsonl")
        self.assertEqual([old, new], token_report.session_chain(new))


class FindTranscript(unittest.TestCase):
    def test_the_most_recently_modified_of_two_projects_wins(self):
        projects = temp_projects(self)
        paths = []
        for project, mtime in (("-a-project", 1000000000), ("-b-project", 2000000000)):
            os.makedirs(os.path.join(projects, project))
            path = os.path.join(projects, project, "twin-session.jsonl")
            shutil.copy(transcript("basic", "solo-session"), path)
            os.utime(path, (mtime, mtime))
            paths.append(path)
        self.assertEqual(paths[1], token_report.find_transcript(projects, "twin-session"))
        os.utime(paths[0], (3000000000, 3000000000))
        self.assertEqual(paths[0], token_report.find_transcript(projects, "twin-session"))


class Cost(unittest.TestCase):
    def setUp(self):
        self.prices = token_report.load_prices()

    def test_the_price_file_holds_the_approved_rates(self):
        self.assertTrue(os.path.isfile(PRICES), PRICES)
        with open(PRICES, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual("2026-10-06", data["as_of"])
        self.assertIn("estimate", data["source"])
        self.assertEqual({"input": 4, "output": 20, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2},
                         data["models"]["claude-opus-5-5"])
        self.assertEqual({"input": 0.1, "output": 0.5, "cache_write_5m": 0.125, "cache_write_1h": 0.2,
                          "cache_read": 0.01}, data["models"]["claude-haiku-5-5"])
        self.assertEqual(12, len(data["models"]))
        self.assertEqual(data, self.prices)

    def test_each_of_the_five_rates_is_applied_per_million_tokens(self):
        usage = {"input": 1000000, "output": 1000000, "cache_write_5m": 1000000, "cache_write_1h": 1000000,
                 "cache_read": 1000000}
        self.assertAlmostEqual(4 + 20 + 5 + 8 + 0.2, token_report.request_cost("claude-opus-5-5", usage, self.prices))

    def test_cache_writes_without_a_split_are_priced_at_the_5_minute_rate(self):
        session = token_report.read_session(transcript("basic", "basic-session"))
        ba1 = token_report.totals(session, "agent").get(("ba1",), NO_USAGE)
        self.assertEqual((300, 0), (ba1["cache_write_5m"], ba1["cache_write_1h"]))

    def test_a_date_suffix_or_1m_tag_is_stripped_before_lookup(self):
        usage = {"input": 1000000, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}
        for model in ("claude-opus-5-5-20261001", "claude-opus-5-5[1m]"):
            with self.subTest(model=model):
                self.assertAlmostEqual(4.0, token_report.request_cost(model, usage, self.prices))

    def test_an_unknown_model_shows_its_tokens_and_no_price_and_the_total_excludes_it(self):
        session = token_report.read_session(transcript("basic", "unpriced-session"))
        out = token_report.render_markdown(session, self.prices)
        self.assertEqual(["no skill", "main session", "claude-mystery-9", "500", "500", "0", "0", "no price"],
                         table_row_for_model(out, "claude-mystery-9"))
        self.assertEqual(["$4.00"], table_row_for_model(out, "claude-opus-5-5")[-1:])
        self.assertEqual(["$4.00"], table_row(out, "**Session total**")[-1:])
        self.assertIn("excludes claude-mystery-9", out)
        self.assertIsNone(token_report.request_cost("claude-mystery-9", {"input": 1, "output": 1, "cache_write_5m": 0,
                                                                         "cache_write_1h": 0, "cache_read": 0},
                                                    self.prices))

    def test_an_all_unpriced_group_says_no_price_and_a_sub_cent_amount_shows_4_decimals(self):
        def request(run, model, tokens):
            return {"agent": "main", "model": model, "skill": run[2], "run": run,
                    "usage": dict(NO_USAGE, input=tokens)}
        session = {"session_id": "made-up", "resumed_from": 0, "agents": {"main": {"type": "main session", "description": ""}},
                   "requests": [request((0, 0, NO_SKILL), "claude-opus-5-5", 1000),
                                request((1, 0, "fake-skill"), "claude-mystery-9", 500)]}
        out = token_report.render_markdown(session, self.prices)
        self.assertEqual(["$0.0040"], table_row_for_model(out, "claude-opus-5-5")[-1:])
        self.assertEqual(["$0.0040"], table_row(out, "**no skill subtotal**")[-1:])
        self.assertEqual(["500", "no price"], table_row(out, "**fake-skill subtotal**")[3:4] + table_row(out, "**fake-skill subtotal**")[-1:])
        self.assertEqual(["$0.0040"], table_row(out, "**Session total**")[-1:])
        session["requests"] = session["requests"][1:]
        out = token_report.render_markdown(session, self.prices)
        self.assertEqual(["no price"], table_row(out, "**Session total**")[-1:])
        self.assertEqual("$0.01", token_report.money(0.01))
        self.assertEqual("$4.00", token_report.money(4.0))


class Resumed(unittest.TestCase):
    def setUp(self):
        self.path = transcript("resumed", "new-session")
        self.session = token_report.read_session(self.path)

    def test_the_continued_in_chain_is_followed_back_to_the_first_session(self):
        self.assertEqual([transcript("resumed", "old-session"), self.path], token_report.session_chain(self.path))
        self.assertEqual(1, self.session["resumed_from"])

    def test_main_requests_copied_into_the_new_file_count_once(self):
        self.assertEqual(1 + 2 + 4 + 8 + 16 + 32, token_report.totals(self.session, "agent").get(("main",), NO_USAGE)["input"])

    def test_the_old_sessions_subagents_are_included(self):
        got = {k: v["input"] for k, v in token_report.totals(self.session, "agent").items()}
        self.assertEqual({("main",): 63, ("ro1",): 10, ("rn1",): 20}, got)

    def test_skill_runs_copied_into_the_new_file_stay_one_run_each_and_new_work_joins_the_last(self):
        self.assertEqual([NO_SKILL, "kinoa-qa:testplan", "kinoa-aqa:failure-triage"],
                         [label for _, label in sorted(token_report.run_labels(self.session).items())])
        by_skill = labelled(self.session, "agent", "run")
        self.assertEqual({("main", NO_SKILL): 1 + 2, ("ro1", NO_SKILL): 10, ("main", "kinoa-qa:testplan"): 8,
                          ("main", "kinoa-aqa:failure-triage"): 16 + 32 + 4, ("rn1", "kinoa-aqa:failure-triage"): 20},
                         by_skill)

    def test_the_header_says_the_session_was_resumed(self):
        out = token_report.render_markdown(self.session, token_report.load_prices())
        self.assertIn("resumed from 1 earlier session(s)", out)


class ForkedSkillCall(unittest.TestCase):
    def setUp(self):
        self.session = token_report.read_session(transcript("forked", "forked-session"))

    def test_a_forked_skill_started_by_a_skill_call_opens_no_main_run_and_its_agent_follows_the_active_run(self):
        self.assertEqual([((1, 0, "kinoa-dev:ticket"), "kinoa-dev:ticket"), ((1, 1, "code-review"), "code-review")],
                         sorted(token_report.run_labels(self.session).items()))
        self.assertEqual({("main", "kinoa-dev:ticket"): 1 + 2 + 4, ("ff1", "code-review"): 8},
                         labelled(self.session, "agent", "run"))


class Cli(unittest.TestCase):
    def test_the_report_is_one_grouped_table_with_subtotals_and_a_total(self):
        result = run_script("skills", "skills-session")
        self.assertEqual(0, result.returncode, result.stderr)
        out = result.stdout
        self.assertIn("| Skill run | Agent | Model | Input | Output | Cache write | Cache read | Cost |", out)
        self.assertIn("skills-session", out)
        self.assertIn("prices as of 2026-10-06", out)
        subtotals = ((NO_SKILL, "103"), ("kinoa-aqa:failure-triage", "628"), ("kinoa-dev:ticket", "2,528"),
                     ("code-review", "800"), ("kinoa-aqa:failure-triage (run 2)", "10,368"), ("kinoa-qa:testplan", "64"))
        for skill, tokens in subtotals:
            with self.subTest(skill=skill):
                row = table_row(out, "**{} subtotal**".format(skill))
                self.assertEqual(8, len(row), out)
                self.assertEqual(tokens, row[3], out)
        firsts = [line.split(" | ", 1)[0][2:] for line in out.splitlines() if line.startswith("| **") and " subtotal** | " in line]
        self.assertEqual(["**{} subtotal**".format(skill) for skill, _ in subtotals], firsts)
        self.assertEqual(["14,491"], table_row(out, "**Session total**")[3:4])
        self.assertIn("| kinoa-aqa:failure-triage | Explore: Read the trace file | claude-sonnet-5-5 | 400 |", out)
        self.assertNotIn("claude-api", out)
        workflow = table_cells(out, 1, "workflow-subagent: Lint \\| format")
        self.assertEqual(["kinoa-aqa:failure-triage (run 2)", "workflow-subagent: Lint \\| format", "claude-sonnet-5-5",
                          "3,200", "1", "0", "0"], workflow[:7], out)
        self.assertEqual(8, len(workflow), out)
        self.assertIn("current turn", out)
        self.assertNotIn("No subagents in this session.", out)
        self.assertNotIn("No skill runs in this session.", out)

    def test_a_session_without_subagents_or_skill_runs_says_so(self):
        result = run_script("basic", "solo-session")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("No subagents in this session.", result.stdout)
        self.assertIn("No skill runs in this session.", result.stdout)
        self.assertEqual(["1"], table_row(result.stdout, "**Session total**")[3:4])

    def test_subagents_without_skill_runs_say_only_that_there_are_no_skill_runs(self):
        result = run_script("basic", "basic-session")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("No skill runs in this session.", result.stdout)
        self.assertNotIn("No subagents in this session.", result.stdout)

    def test_an_unset_session_id_exits_1_naming_the_variable_with_no_report(self):
        result = run_script("basic", None)
        self.assertEqual(1, result.returncode)
        self.assertIn("CLAUDE_CODE_SESSION_ID", result.stderr)
        self.assertEqual("", result.stdout)

    def test_a_missing_transcript_exits_1_naming_the_path_looked_for_with_no_report(self):
        result = run_script("basic", "nope-session")
        self.assertEqual(1, result.returncode)
        self.assertIn(os.path.join(home("basic"), ".claude", "projects", "*", "nope-session.jsonl"), result.stderr)
        self.assertEqual("", result.stdout)

    def test_claude_config_dir_replaces_home_dot_claude(self):
        empty_home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty_home)
        config = os.path.join(home("basic"), ".claude")
        result = run_script("basic", "solo-session", config_dir=config, home_dir=empty_home)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["1"], table_row(result.stdout, "**Session total**")[3:4])
        missing = run_script("basic", "nope-session", config_dir=config, home_dir=empty_home)
        self.assertEqual(1, missing.returncode)
        self.assertIn(os.path.join(config, "projects", "*", "nope-session.jsonl"), missing.stderr)
        self.assertEqual("", missing.stdout)

    def test_the_report_reads_only_the_synthetic_fixture_home(self):
        result = run_script("resumed", "new-session")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("new-session", result.stdout)
        paths = list(fixture_files())
        self.assertGreater(len(paths), 20)
        for path in paths:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            with self.subTest(path=os.path.relpath(path, FIXTURES)):
                self.assertNotIn("/Users/", text)
                self.assertNotIn("/home/", text)


if __name__ == "__main__":
    unittest.main()
