import os
import sys
import json
import re
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from spec_resolver import (
    title_leading_key, pr_matches, capabilities_from_files, resolve,
)


def make_runner(search_map, files_map):
    """Fake `gh` runner. search_map: key -> list[pr]; files_map: (repo, num) -> [paths]."""
    def runner(args):
        if args[:2] == ["search", "prs"]:
            key = args[2]
            return types.SimpleNamespace(returncode=0, stdout=json.dumps(search_map.get(key, [])), stderr="")
        if args and args[0] == "api":
            path = next((a for a in args if a.startswith("repos/")), "")
            m = re.match(r"repos/(.+)/pulls/(\d+)/files", path)
            if m:
                repo, num = m.group(1), int(m.group(2))
                return types.SimpleNamespace(returncode=0, stdout="\n".join(files_map.get((repo, num), [])), stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    return runner


class TestPure(unittest.TestCase):
    def test_title_leading_key(self):
        self.assertEqual(title_leading_key("KING-22039 Implement webhook export"), "KING-22039")
        self.assertEqual(title_leading_key("[KING-22041] add webhook export"), "KING-22041")
        self.assertIsNone(title_leading_key("Release to production"))
        self.assertIsNone(title_leading_key(""))

    def test_pr_matches_drops_release_and_cross_ticket(self):
        keys = {"KING-20951", "KING-22039"}
        self.assertTrue(pr_matches({"title": "KING-22039 Implement export"}, keys))
        self.assertFalse(pr_matches({"title": "Release to production", "headRefName": "release/prod"}, keys))
        self.assertFalse(pr_matches({"title": "KING-22052 Unrelated ticket"}, keys))  # not in keys
        # branch carries the key even if the title doesn't
        self.assertTrue(pr_matches({"title": "hotfix", "headRefName": "feature/KING-22039-x"}, keys))

    def test_capabilities_from_files(self):
        files = [
            "openspec/changes/add-webhook-export/specs/webhook-export/spec.md",  # delta
            "openspec/specs/push-export/spec.md",                                # archived
            "src/Foo.java",
            "openspec/changes/add-webhook-export/proposal.md",                   # not a spec.md
        ]
        self.assertEqual(capabilities_from_files(files), {"webhook-export", "push-export"})
        self.assertEqual(capabilities_from_files(["README.md"]), set())


class TestResolve(unittest.TestCase):
    def setUp(self):
        # All candidate PRs surface under the story-key search (as they did live for KING-20951).
        self.search = {
            "KING-20951": [
                {"repository": {"nameWithOwner": "Kinoa-Labs-LTD/webhook"}, "number": 3,
                 "state": "merged", "title": "KING-22039 Implement webhook export", "url": "u/webhook/3"},
                {"repository": {"nameWithOwner": "Kinoa-Labs-LTD/push-notifications"}, "number": 28,
                 "state": "merged", "title": "KING-22045 Add push export", "url": "u/push/28"},
                {"repository": {"nameWithOwner": "Kinoa-Labs-LTD/pixel-frontend-api"}, "number": 176,
                 "state": "open", "title": "Release to production", "url": "u/fe/176"},          # noise
                {"repository": {"nameWithOwner": "Kinoa-Labs-LTD/kinoa-java-commons"}, "number": 77,
                 "state": "merged", "title": "KING-22052 Unrelated flow ticket", "url": "u/commons/77"},  # cross-ticket
            ],
        }
        self.files = {
            ("Kinoa-Labs-LTD/webhook", 3): ["openspec/changes/add-webhook-export/specs/webhook-export/spec.md", "src/X.java"],
            ("Kinoa-Labs-LTD/push-notifications", 28): ["openspec/specs/push-export/spec.md"],
            ("Kinoa-Labs-LTD/pixel-frontend-api", 176): ["src/app.ts"],  # release, no spec
            ("Kinoa-Labs-LTD/kinoa-java-commons", 77): ["openspec/specs/flow-thing/spec.md"],  # excluded by pr filter
        }
        self.runner = make_runner(self.search, self.files)

    def test_resolves_backend_specs_and_drops_noise(self):
        res = resolve("KING-20951", ["KING-22039", "KING-22045"], "Kinoa-Labs-LTD", runner=self.runner)
        caps = {(r["repo"], r["capability"]) for r in res}
        self.assertIn(("Kinoa-Labs-LTD/webhook", "webhook-export"), caps)
        self.assertIn(("Kinoa-Labs-LTD/push-notifications", "push-export"), caps)
        # release PR (no leading key) and cross-ticket KING-22052 (not in keys) excluded
        self.assertNotIn("Kinoa-Labs-LTD/pixel-frontend-api", {r["repo"] for r in res})
        self.assertNotIn("flow-thing", {r["capability"] for r in res})
        self.assertEqual(len(res), 2)

    def test_spec_path_is_archived_canonical(self):
        res = resolve("KING-20951", ["KING-22039"], "Kinoa-Labs-LTD", runner=self.runner)
        wh = next(r for r in res if r["repo"].endswith("/webhook"))
        self.assertEqual(wh["spec_path"], "openspec/specs/webhook-export/spec.md")
        self.assertEqual(wh["via_pr"], "Kinoa-Labs-LTD/webhook#3")

    def test_no_specs_returns_empty(self):
        runner = make_runner(
            {"KING-1": [{"repository": {"nameWithOwner": "o/fe"}, "number": 5, "state": "merged",
                         "title": "KING-1 frontend only", "url": "u"}]},
            {("o/fe", 5): ["src/app.tsx", "package.json"]},
        )
        self.assertEqual(resolve("KING-1", [], "o", runner=runner), [])


if __name__ == "__main__":
    unittest.main()
