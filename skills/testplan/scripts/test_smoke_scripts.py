# test_smoke_scripts.py
"""smoke-run's two Jira scripts are Node, run through `node` from the repo root with every
JIRA_* variable removed: a dry run and a usage message must need no credentials and no
network, and the usage line must name the plugin path an agent is told to run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shutil, subprocess, unittest

# repo root: skills/testplan/scripts/ -> ../../..
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SCRIPTS_REL = "skills/smoke-run/scripts"
FIXTURE_REL = SCRIPTS_REL + "/fixtures/dry-run-report.json"


def run_node(*args):
    """Run `node <args>` from the repo root with no JIRA_* variable in the environment."""
    node = shutil.which("node")
    env = {k: v for k, v in os.environ.items() if not k.startswith("JIRA_")}
    return subprocess.run([node] + list(args), cwd=ROOT, env=env, capture_output=True,
                          text=True, timeout=60)


class NodeScriptTest(unittest.TestCase):
    def setUp(self):
        if shutil.which("node") is None:
            self.fail("node (>= 18) is required to test skills/smoke-run/scripts; install it")


class JiraReportDryRun(NodeScriptTest):
    def test_dry_run_exits_0_and_prints_the_computed_verdict(self):
        result = run_node(SCRIPTS_REL + "/jiraReport.mjs", FIXTURE_REL, "--dry-run")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("feature: partially live   conformance: failed (computed)", result.stdout)
        self.assertIn("3 steps · 1 pass / 1 fail / 1 blocked", result.stdout)
        self.assertIn("--dry-run: nothing posted.", result.stdout)

    def test_the_fixture_supplies_no_conformance_verdict(self):
        path = os.path.join(ROOT, FIXTURE_REL)
        self.assertTrue(os.path.isfile(path), FIXTURE_REL)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn('"conformance"', text)


class UsageNamesThePluginPath(NodeScriptTest):
    def test_no_args_prints_the_plugin_usage_line_on_stderr(self):
        for name in ("jiraReport", "jiraAttach"):
            with self.subTest(script=name):
                result = run_node("{}/{}.mjs".format(SCRIPTS_REL, name))
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertIn("Usage: node <plugin>/skills/smoke-run/scripts/{}.mjs".format(name),
                              result.stderr)


if __name__ == "__main__":
    unittest.main()
