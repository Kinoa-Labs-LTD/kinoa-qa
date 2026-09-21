# test_plugin_manifest.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re, unittest

# repo root: skills/testplan/scripts/ -> ../../..
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
PLUGIN_JSON = os.path.join(ROOT, ".claude-plugin", "plugin.json")
MARKETPLACE_JSON = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

_HEADING = re.compile(r"^##\s+(\d+\.\d+\.\d+)\b")


def top_changelog_version(text):
    """The version of the newest `## <x.y.z>` entry, or None when there is none.

    Pure so the drift case is tested with synthetic input rather than by breaking the real
    files: a test that can only prove the current tree is consistent never shows what it
    would catch.
    """
    for line in text.splitlines():
        m = _HEADING.match(line.strip())
        if m:
            return m.group(1)
    return None


class TopChangelogVersion(unittest.TestCase):
    def test_reads_the_first_version_heading(self):
        self.assertEqual("0.2.0", top_changelog_version(
            "# Changelog\n\nblurb\n\n## 0.2.0 — 2026-09-21\n\nstuff\n\n## 0.1.0\n\nolder\n"))

    def test_ignores_prose_that_mentions_a_version(self):
        self.assertEqual("1.0.0", top_changelog_version(
            "# Changelog\n\nupdate from 0.9.0 if you are stale\n\n## 1.0.0\n\nstuff\n"))

    def test_returns_none_without_any_version_heading(self):
        self.assertIsNone(top_changelog_version("# Changelog\n\nnothing released yet\n"))


class ManifestsAgree(unittest.TestCase):
    """The version is the update trigger: Claude Code refreshes an installed plugin only when
    the string in plugin.json changes. These assertions keep the three places that describe a
    release from drifting apart."""

    def setUp(self):
        with open(PLUGIN_JSON, encoding="utf-8") as f:
            self.plugin = json.load(f)
        with open(MARKETPLACE_JSON, encoding="utf-8") as f:
            self.marketplace = json.load(f)

    def test_plugin_json_declares_a_semver_version(self):
        self.assertRegex(self.plugin.get("version", ""), r"^\d+\.\d+\.\d+$")

    def test_marketplace_entry_declares_no_version(self):
        # Claude Code resolves plugin.json first and ignores the marketplace entry without
        # warning, so a version here is a silent second source of truth.
        for entry in self.marketplace["plugins"]:
            self.assertNotIn("version", entry,
                             "marketplace entry must not carry a version — plugin.json owns it")

    def test_changelog_top_entry_matches_plugin_json(self):
        with open(CHANGELOG, encoding="utf-8") as f:
            top = top_changelog_version(f.read())
        self.assertEqual(
            self.plugin["version"], top,
            "CHANGELOG's newest entry and plugin.json disagree — bump both in the same PR")


if __name__ == "__main__":
    unittest.main()
