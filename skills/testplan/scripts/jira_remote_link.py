#!/usr/bin/env python3
"""Record a smoke sub-task's Allure TestOps case as one Jira remote link. stdlib-only.

The sub-task keeps exactly one link titled `Allure TestOps case <id>`, which `smoke-run` and
`smoke_to_plan.py` read back as the case id: the writer lists the sub-task's links first,
updates in place, by its link id, the first one with its own globalId or a title matching
`case_id_from_title`, and otherwise creates one with the globalId
`kinoa-qa:smoke-case:<SUBTASK>`. No other issue field is written.

Credentials are `JIRA_EMAIL` / `JIRA_API_TOKEN` (a token with the classic `write:jira-work`
scope); `JIRA_HOST` picks the host: `auto` (default: the api.atlassian.com gateway, then the
site), `gateway` or `site`.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

from jira_attachments import EMAIL_ENV, TOKEN_ENV, API_HOST, credentials, resolve_cloud_id

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "..", "config.json")
CASE_TITLE_PREFIX = "Allure TestOps case "
CASE_TITLE_RE = re.compile(r"^Allure TestOps case ([1-9]\d*)\b")
HOST_MODES = ("auto", "gateway", "site")
RETRY_ELSEWHERE = (401, 403, 404)


class LinkWriteError(RuntimeError):
    """The link could not be read or written; the message names the reason."""


def case_id_from_title(title):
    """The case id a remote-link title names — `Allure TestOps case <id>` at the start of the
    whitespace-stripped title, the id a positive integer followed by a word boundary — or None.
    The one rule both the writer and the reader use."""
    match = CASE_TITLE_RE.match(title.strip() if isinstance(title, str) else "")
    return int(match.group(1)) if match else None


def link_title(case_id):
    """The exact title `smoke-run` parses the case id from."""
    return f"{CASE_TITLE_PREFIX}{case_id}"


def global_id(issue_key):
    """The globalId that makes a POST for this sub-task idempotent on Jira's side."""
    return f"kinoa-qa:smoke-case:{issue_key}"


def case_url(testops_base_url, project_id, case_id):
    """The TestOps web URL of one test case."""
    return f"{str(testops_base_url).rstrip('/')}/project/{project_id}/test-cases/{case_id}"


def link_payload(issue_key, case_id, testops_base_url, project_id):
    """The remote-link body sent by both the POST and the PUT."""
    return {"globalId": global_id(issue_key),
            "object": {"url": case_url(testops_base_url, project_id, case_id),
                       "title": link_title(case_id)}}


def links_path(issue_key):
    return f"/rest/api/3/issue/{issue_key}/remotelink"


def find_case_link(links, issue_key):
    """The sub-task's first existing case link — ours by globalId, or any title
    `case_id_from_title` reads an id from, hand-added ones included — or None."""
    for link in links or []:
        title = ((link or {}).get("object") or {}).get("title") or ""
        if link.get("globalId") == global_id(issue_key) or case_id_from_title(title) is not None:
            return link
    return None


def jira_roots(host_mode, site_url, opener=None):
    """The Jira REST roots to try, in order, for a `JIRA_HOST` mode."""
    mode = (host_mode or "auto").lower()
    if mode not in HOST_MODES:
        raise ValueError(f"JIRA_HOST={host_mode!r} is not one of {', '.join(HOST_MODES)}")
    site = str(site_url).rstrip("/")
    if mode == "site":
        return [site]
    cloud_id = resolve_cloud_id(site, opener=opener)
    gateway = f"{API_HOST}/ex/jira/{cloud_id}" if cloud_id else None
    if mode == "gateway":
        if not gateway:
            raise LinkWriteError(f"JIRA_HOST=gateway, but the cloud id of {site} could not be "
                                 "resolved")
        return [gateway]
    return [gateway, site] if gateway else [site]


def _send(method, url, *, auth, body=None, opener=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": auth, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with (opener or urllib.request.urlopen)(request) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def _http_error(exc, method, url, issue_key):
    try:
        detail = exc.read().decode("utf-8", "replace")[:300]
    except Exception:
        detail = ""
    message = f"HTTP {exc.code} on {method} {url}"
    if detail:
        message += f": {detail}"
    if exc.code in (401, 403):
        message += (f" — Jira refused the remote link: the token needs the classic "
                    f"`write:jira-work` scope (granular scopes reject every POST), and the "
                    f"account needs the Jira \"Link issues\" permission on {issue_key}")
    return LinkWriteError(message)


def upsert_remote_link(issue_key, case_id, *, email, token, testops_base_url, project_id,
                       site_url, host_mode="auto", opener=None):
    """Create or update the sub-task's one `Allure TestOps case <id>` link.

    Returns {"method": "POST"|"PUT", "url", "title", "case_url"}; raises LinkWriteError on a
    refused or failed request, ValueError on an unknown host mode.
    """
    payload = link_payload(issue_key, case_id, testops_base_url, project_id)
    auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    roots = jira_roots(host_mode, site_url, opener=opener)
    path = links_path(issue_key)
    links = root = None
    for index, root in enumerate(roots):
        url = root + path
        try:
            links = _send("GET", url, auth=auth, opener=opener)
            break
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_ELSEWHERE and index < len(roots) - 1:
                continue
            raise _http_error(exc, "GET", url, issue_key) from exc
        except urllib.error.URLError as exc:
            raise LinkWriteError(f"{exc.reason} on GET {url}") from exc
    existing = find_case_link(links, issue_key)
    if existing:
        method, url = "PUT", f"{root}{path}/{existing['id']}"
    else:
        method, url = "POST", root + path
    try:
        _send(method, url, auth=auth, body=payload, opener=opener)
    except urllib.error.HTTPError as exc:
        raise _http_error(exc, method, url, issue_key) from exc
    except urllib.error.URLError as exc:
        raise LinkWriteError(f"{exc.reason} on {method} {url}") from exc
    return {"method": method, "url": url, "title": payload["object"]["title"],
            "case_url": payload["object"]["url"]}


def _issue_key(value):
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-[1-9][0-9]*", value):
        raise argparse.ArgumentTypeError(f"{value!r} is not an issue key (e.g. KING-22976)")
    return value


def _case_id(value):
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a positive integer case id")
    return int(value)


def build_arg_parser():
    """The CLI surface, built separately so the accepted flags are unit-testable."""
    ap = argparse.ArgumentParser(
        description="kinoa-qa: write the smoke sub-task's `Allure TestOps case <id>` remote link")
    ap.add_argument("--issue", required=True, type=_issue_key, help="the smoke sub-task key")
    ap.add_argument("--case-id", required=True, type=_case_id, help="the TestOps case id")
    ap.add_argument("--config", default=DEFAULT_CONFIG,
                    help="config.json with testops.base_url, testops.project_id, jira_base_url")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the requests without sending any")
    return ap


def read_config(path):
    """The parsed config.json; raises LinkWriteError when it is unreadable or not an object."""
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, ValueError) as exc:
        raise LinkWriteError(f"cannot read --config {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise LinkWriteError(f"cannot read --config {path}: not a JSON object")
    return config


def load_config(path, env):
    """(testops_base_url, project_id, jira site url) from config.json; `JIRA_BASE_URL` in the
    environment overrides the site. Raises LinkWriteError naming a missing key."""
    config = read_config(path)
    testops = config.get("testops") or {}
    if not isinstance(testops, dict):
        raise LinkWriteError(f"{path} has no testops.base_url")
    site = (env.get("JIRA_BASE_URL") or config.get("jira_base_url") or "").strip()
    for name, value in (("testops.base_url", testops.get("base_url")),
                        ("testops.project_id", testops.get("project_id")),
                        ("jira_base_url", site)):
        if value in (None, ""):
            raise LinkWriteError(f"{path} has no {name}")
    return testops["base_url"], testops["project_id"], site


def _by_hand(issue_key, title, url):
    lines = [f"add the link by hand on {issue_key} (Link → Web link):", f"  title: {title}"]
    if url:
        lines.append(f"  url: {url}")
    return "\n".join(lines)


def _fallback_url(path, case_id):
    """The case URL when the config at `path` still names testops.base_url and project_id,
    else None."""
    try:
        testops = read_config(path).get("testops") or {}
    except LinkWriteError:
        return None
    if not isinstance(testops, dict):
        return None
    base_url, project_id = testops.get("base_url"), testops.get("project_id")
    if base_url in (None, "") or project_id in (None, ""):
        return None
    return case_url(base_url, project_id, case_id)


def main(argv=None, env=None, opener=None):
    """Write the link and return 0. Unset credentials return 3; an unreadable or incomplete
    config, or a refused or failed write, returns 1. Each prints the reason and the link to add
    by hand on stderr (the `url:` line only when the config names the TestOps host and project).
    `--dry-run` prints the requests on stdout, sends nothing and returns 0; usage errors exit 2."""
    args = build_arg_parser().parse_args(argv)
    env = os.environ if env is None else env
    try:
        base_url, project_id, site = load_config(args.config, env)
    except LinkWriteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(_by_hand(args.issue, link_title(args.case_id),
                       _fallback_url(args.config, args.case_id)), file=sys.stderr)
        return 1
    payload = link_payload(args.issue, args.case_id, base_url, project_id)
    title, url = payload["object"]["title"], payload["object"]["url"]
    host_mode = (env.get("JIRA_HOST") or "auto").strip().lower()
    if args.dry_run:
        path = links_path(args.issue)
        body = json.dumps(payload)
        print(f"# dry run — nothing sent; JIRA_HOST={host_mode}, site {site}")
        print(f"GET {path}")
        print(f"# then, when no `{CASE_TITLE_PREFIX}…` link is listed:")
        print(f"POST {path} {body}")
        print(f"# otherwise, to that link's id:")
        print(f"PUT {path}/<link id> {body}")
        return 0
    creds = credentials(env)
    if not creds:
        print(f"error: {EMAIL_ENV} and {TOKEN_ENV} must be set (a token with the classic "
              f"`write:jira-work` scope) — the link was not written", file=sys.stderr)
        print(_by_hand(args.issue, title, url), file=sys.stderr)
        return 3
    try:
        result = upsert_remote_link(args.issue, args.case_id, email=creds[0], token=creds[1],
                                    testops_base_url=base_url, project_id=project_id,
                                    site_url=site, host_mode=host_mode, opener=opener)
    except (LinkWriteError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(_by_hand(args.issue, title, url), file=sys.stderr)
        return 1
    verb = "created" if result["method"] == "POST" else "updated"
    print(f"{verb} remote link on {args.issue}: {title} → {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
