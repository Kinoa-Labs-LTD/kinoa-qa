#!/usr/bin/env python3
"""Jira Story -> affected service repos -> exact OpenSpec capability specs, via `gh`.

Prototype auto-resolver for the SpecResolver seam. Given a Jira Story key plus its
subtask keys, it uses the GitHub CLI to find the feature PRs, filters out release /
cross-referenced noise, reads each PR's changed files to pin the OpenSpec capability,
and returns the archived spec path to read. All `gh` calls go through an injected
`runner`, so the pure logic is unit-tested without a network.

Validated end-to-end against KING-20951 (webhook export, 8 repos): resolves to
webhook/webhook-export, push-notifications/push-export, and the kinoa-java-commons
export specs — while dropping "Release to *" PRs and unrelated tickets.

Boundary: this script owns the GitHub side only. The Jira side (the Story's subtask
keys) is supplied by the caller — the skill gets those from the Atlassian MCP.

stdlib-only.
"""
import argparse
import json
import re
import subprocess
import sys

# A PR title we accept starts with the key, optionally bracketed: "KING-1 ...", "[KING-1] ...".
LEADING_KEY_RE = re.compile(r"^\[?(KING-\d+)")
# openspec/specs/<cap>/spec.md  OR  openspec/changes/<change-id>/specs/<cap>/spec.md
SPEC_PATH_RE = re.compile(r"openspec/(?:changes/[^/]+/)?specs/([^/]+)/spec\.md$")


def title_leading_key(title):
    """The KING-key a PR title starts with, or None ('Release to production' -> None)."""
    m = LEADING_KEY_RE.match((title or "").strip())
    return m.group(1) if m else None


def pr_matches(pr, keys):
    """Keep a PR only if its title starts with one of our keys (story + subtasks),
    or — when a branch name is available — its branch contains one. This drops both
    aggregate 'Release to *' PRs and PRs that merely reference the key from another
    ticket."""
    tk = title_leading_key(pr.get("title", ""))
    if tk and tk in keys:
        return True
    branch = pr.get("headRefName", "") or ""
    return any(k in branch for k in keys)


def capabilities_from_files(filenames):
    """Set of OpenSpec capability names from a PR's changed-file paths."""
    caps = set()
    for f in filenames:
        m = SPEC_PATH_RE.search(f)
        if m:
            caps.add(m.group(1))
    return caps


def _run(args):
    """Default runner: invoke the real `gh` CLI."""
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=False)


def gh_search_prs(key, owner, runner=_run):
    # NOTE: `gh search prs --json` accepts repository/number/state/title/url — NOT
    # headRefName/mergeCommit (those belong to `gh pr list`). Title is our signal.
    r = runner(["search", "prs", key, "--owner", owner, "--limit", "40",
                "--json", "repository,number,state,title,url"])
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def gh_pr_files(repo, number, runner=_run):
    r = runner(["api", "--paginate", f"repos/{repo}/pulls/{number}/files",
                "--jq", ".[].filename"])
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def resolve(story_key, subtask_keys, owner, runner=_run):
    """Return a sorted list of {repo, capability, spec_path, via_pr, via_url} —
    one per (repo, capability) the Story touches that carries an OpenSpec spec.
    Repos with no OpenSpec spec change (e.g. pure-frontend) contribute nothing and
    are handled business-only downstream."""
    keys = {story_key, *subtask_keys}
    seen, prs = set(), []
    for k in keys:
        for pr in gh_search_prs(k, owner, runner):
            repo = pr["repository"]["nameWithOwner"]
            ident = (repo, pr["number"])
            if ident in seen or not pr_matches(pr, keys):
                continue
            seen.add(ident)
            prs.append(pr)
    results = {}
    for pr in prs:
        repo = pr["repository"]["nameWithOwner"]
        for cap in capabilities_from_files(gh_pr_files(repo, pr["number"], runner)):
            results.setdefault((repo, cap), {
                "repo": repo,
                "capability": cap,
                "spec_path": f"openspec/specs/{cap}/spec.md",
                "via_pr": f"{repo}#{pr['number']}",
                "via_url": pr.get("url", ""),
            })
    return sorted(results.values(), key=lambda r: (r["repo"], r["capability"]))


def main():
    ap = argparse.ArgumentParser(
        description="Resolve a Jira Story to service-repo OpenSpec capability specs via gh")
    ap.add_argument("story", help="Jira Story key, e.g. KING-20951")
    ap.add_argument("--subtask", action="append", default=[],
                    help="a subtask key (repeatable); supply the Story's subtasks for full recall")
    ap.add_argument("--owner", default="Kinoa-Labs-LTD")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()
    results = resolve(args.story, args.subtask, args.owner)
    if args.json:
        print(json.dumps(results, indent=2))
        return
    if not results:
        print("no spec-grounded capabilities resolved — business-only for this Story")
        return
    for r in results:
        print(f"{r['repo']}\t{r['capability']}\t{r['spec_path']}\t(via {r['via_pr']})")


if __name__ == "__main__":
    main()
