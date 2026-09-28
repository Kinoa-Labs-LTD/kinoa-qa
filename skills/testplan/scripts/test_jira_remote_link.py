# test_jira_remote_link.py
import io
import json
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subprocess
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout

from jira_remote_link import (DEFAULT_CONFIG, LinkWriteError, case_id_from_title, case_url,
                              global_id, link_title, main, upsert_remote_link)

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "jira_remote_link.py")
SITE = "https://kinoadev.atlassian.net"
GATEWAY = "https://api.atlassian.com/ex/jira/CID"
TESTOPS = "https://kinoa.testops.cloud"
ISSUE = "KING-22976"
LINKS_PATH = f"/rest/api/3/issue/{ISSUE}/remotelink"
CASE_URL = f"{TESTOPS}/project/1/test-cases/4321"
PAYLOAD = {"globalId": f"kinoa-qa:smoke-case:{ISSUE}",
           "object": {"url": CASE_URL, "title": "Allure TestOps case 4321"}}
CREDS = {"JIRA_EMAIL": "qa@kinoa.io", "JIRA_API_TOKEN": "t"}


class Resp:
    def __init__(self, body=b"", status=200):
        self.body, self.status = body, status

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body


class FakeJira:
    """An in-memory remote-link store answering the Jira REST calls the writer makes."""

    def __init__(self, links=None, deny=None, cloud_id="CID"):
        self.links = [dict(link) for link in (links or [])]
        self.deny = deny or {}
        self.cloud_id = cloud_id
        self.requests = []
        self.next_id = 20000

    def __call__(self, req):
        url, method = req.full_url, req.get_method()
        if url.endswith("/_edge/tenant_info"):
            if self.cloud_id is None:
                raise urllib.error.URLError("unreachable")
            return Resp(json.dumps({"cloudId": self.cloud_id}).encode())
        body = json.loads(req.data) if req.data else None
        self.requests.append((method, url, body, req.get_header("Authorization")))
        root = GATEWAY if url.startswith(GATEWAY) else SITE
        status = self.deny.get((root, method)) or self.deny.get(root)
        if status:
            raise urllib.error.HTTPError(url, status, "Denied", {},
                                         io.BytesIO(b'{"errorMessages":["denied"]}'))
        path = url[len(root):]
        if method == "GET" and path == LINKS_PATH:
            return Resp(json.dumps(self.links).encode())
        if method == "POST" and path == LINKS_PATH:
            for link in self.links:
                if link.get("globalId") == body["globalId"]:
                    link["object"] = body["object"]
                    return Resp(json.dumps({"id": link["id"]}).encode())
            self.next_id += 1
            self.links.append({"id": self.next_id, **body})
            return Resp(json.dumps({"id": self.next_id}).encode(), 201)
        if method == "PUT" and path.startswith(LINKS_PATH + "/"):
            link_id = int(path.rsplit("/", 1)[1])
            for link in self.links:
                if link["id"] == link_id:
                    link["globalId"], link["object"] = body["globalId"], body["object"]
                    return Resp(b"", 204)
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))
        raise AssertionError(f"unexpected request {method} {url}")

    def writes(self):
        return [r for r in self.requests if r[0] != "GET"]

    def case_links(self):
        return [l for l in self.links
                if l["object"]["title"].startswith("Allure TestOps case ")]


def upsert(fake, case_id=4321, host_mode="auto", base_url=TESTOPS):
    return upsert_remote_link(ISSUE, case_id, email="qa@kinoa.io", token="t",
                              testops_base_url=base_url, project_id=1, site_url=SITE,
                              host_mode=host_mode, opener=fake)


class Upsert(unittest.TestCase):
    def test_title_global_id_and_url_are_the_contract_smoke_run_reads(self):
        self.assertEqual("Allure TestOps case 4321", link_title(4321))
        self.assertEqual("kinoa-qa:smoke-case:KING-22976", global_id(ISSUE))
        self.assertEqual(CASE_URL, case_url(TESTOPS, 1, 4321))
        self.assertEqual(CASE_URL, case_url(TESTOPS + "/", 1, 4321))

    def test_the_links_are_read_before_anything_is_written(self):
        fake = FakeJira()
        upsert(fake)
        self.assertEqual(["GET", "POST"], [r[0] for r in fake.requests])
        self.assertEqual(GATEWAY + LINKS_PATH, fake.requests[0][1])

    def test_no_matching_link_posts_one(self):
        fake = FakeJira()
        result = upsert(fake)
        self.assertEqual([("POST", GATEWAY + LINKS_PATH, PAYLOAD)],
                         [r[:3] for r in fake.writes()])
        self.assertEqual("POST", result["method"])

    def test_a_hand_added_case_link_is_updated_in_place_by_its_id(self):
        fake = FakeJira(links=[{"id": 10001,
                                "object": {"url": "https://x/1", "title": "Allure TestOps case 999"}}])
        result = upsert(fake)
        self.assertEqual([("PUT", f"{GATEWAY}{LINKS_PATH}/10001", PAYLOAD)],
                         [r[:3] for r in fake.writes()])
        self.assertEqual("PUT", result["method"])
        self.assertEqual([{"id": 10001, **PAYLOAD}], fake.links)

    def test_case_id_from_title_reads_the_id_at_the_start_of_the_title(self):
        for title, expected in (("Allure TestOps case 4711", 4711),
                                ("Allure TestOps case 4711 (smoke)", 4711),
                                ("Allure TestOps case x", None),
                                ("Allure TestOps case 4711x", None),
                                ("Allure TestOps case ", None),
                                ("Allure TestOps case 0", None),
                                ("Allure TestOps case 05", None),
                                ("  Allure TestOps case 4711 ", 4711),
                                ("See Allure TestOps case 4711", None),
                                ("", None), (None, None)):
            with self.subTest(title=title):
                self.assertEqual(expected, case_id_from_title(title))

    def test_a_case_link_with_a_suffix_is_updated_in_place(self):
        fake = FakeJira(links=[{"id": 10002, "object": {
            "url": "https://x/1", "title": "Allure TestOps case 4711 (smoke)"}}])
        result = upsert(fake)
        self.assertEqual([("PUT", f"{GATEWAY}{LINKS_PATH}/10002", PAYLOAD)],
                         [r[:3] for r in fake.writes()])
        self.assertEqual("PUT", result["method"])
        self.assertEqual([{"id": 10002, **PAYLOAD}], fake.links)

    def test_a_title_naming_no_case_id_is_not_a_case_link(self):
        other = {"id": 6, "object": {"url": "https://x/2", "title": "Allure TestOps case x"}}
        fake = FakeJira(links=[other])
        upsert(fake)
        self.assertEqual(["POST"], [r[0] for r in fake.writes()])
        self.assertIn(other, fake.links)

    def test_a_case_link_title_with_surrounding_whitespace_is_updated_in_place(self):
        fake = FakeJira(links=[{"id": 10004, "object": {
            "url": "https://x/5", "title": " Allure TestOps case 5"}}])
        upsert(fake)
        self.assertEqual([("PUT", f"{GATEWAY}{LINKS_PATH}/10004", PAYLOAD)],
                         [r[:3] for r in fake.writes()])
        self.assertEqual([{"id": 10004, **PAYLOAD}], fake.links)

    def test_case_id_zero_is_not_a_case_link(self):
        other = {"id": 7, "object": {"url": "https://x/0", "title": "Allure TestOps case 0"}}
        fake = FakeJira(links=[other])
        upsert(fake)
        self.assertEqual(["POST"], [r[0] for r in fake.writes()])
        self.assertIn(other, fake.links)

    def test_our_global_id_is_updated_whatever_its_title(self):
        fake = FakeJira(links=[{"id": 10003, "globalId": f"kinoa-qa:smoke-case:{ISSUE}",
                                "object": {"url": "https://x/3", "title": "renamed by hand"}}])
        upsert(fake)
        self.assertEqual([("PUT", f"{GATEWAY}{LINKS_PATH}/10003", PAYLOAD)],
                         [r[:3] for r in fake.writes()])

    def test_an_unrelated_link_is_left_alone(self):
        other = {"id": 5, "object": {"url": "https://wiki/x", "title": "Confluence page"}}
        fake = FakeJira(links=[other])
        upsert(fake)
        self.assertEqual(["POST"], [r[0] for r in fake.writes()])
        self.assertIn(other, fake.links)

    def test_any_number_of_pushes_leaves_exactly_one_case_link(self):
        fake = FakeJira()
        for case_id in (4321, 4321, 4400):
            upsert(fake, case_id=case_id)
        self.assertEqual(1, len(fake.case_links()))
        self.assertEqual("Allure TestOps case 4400", fake.case_links()[0]["object"]["title"])

    def test_only_the_remote_link_resource_is_written(self):
        for links in ([], [{"id": 7, "object": {"url": "u", "title": "Allure TestOps case 1"}}]):
            with self.subTest(links=links):
                fake = FakeJira(links=links)
                upsert(fake)
                self.assertEqual(1, len(fake.writes()))
                for method, url, body, _ in fake.writes():
                    self.assertIn(method, ("POST", "PUT"))
                    self.assertIn(f"/rest/api/3/issue/{ISSUE}/remotelink", url)
                    self.assertEqual({"globalId", "object"}, set(body))
                    self.assertEqual({"url", "title"}, set(body["object"]))

    def test_every_request_carries_basic_auth(self):
        fake = FakeJira()
        upsert(fake)
        self.assertEqual(2, len(fake.requests))
        for request in fake.requests:
            self.assertTrue(request[3].startswith("Basic "), request)

    def test_auto_falls_back_from_gateway_to_site(self):
        fake = FakeJira(deny={GATEWAY: 401})
        upsert(fake, host_mode="auto")
        self.assertEqual([("GET", GATEWAY + LINKS_PATH), ("GET", SITE + LINKS_PATH),
                          ("POST", SITE + LINKS_PATH)], [r[:2] for r in fake.requests])

    def test_auto_uses_the_site_when_the_cloud_id_cannot_be_resolved(self):
        fake = FakeJira(cloud_id=None)
        upsert(fake, host_mode="auto")
        self.assertEqual([SITE + LINKS_PATH] * 2, [r[1] for r in fake.requests])

    def test_gateway_mode_never_touches_the_site(self):
        fake = FakeJira(deny={GATEWAY: 401})
        with self.assertRaises(LinkWriteError):
            upsert(fake, host_mode="gateway")
        self.assertTrue(all(r[1].startswith(GATEWAY) for r in fake.requests), fake.requests)

    def test_site_mode_never_touches_the_gateway(self):
        fake = FakeJira()
        upsert(fake, host_mode="site")
        self.assertEqual([("GET", SITE + LINKS_PATH), ("POST", SITE + LINKS_PATH)],
                         [r[:2] for r in fake.requests])

    def test_an_unknown_host_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            upsert(FakeJira(), host_mode="proxy")

    def test_a_rejected_write_names_the_classic_scope_and_the_link_permission(self):
        for status in (401, 403):
            with self.subTest(status=status):
                fake = FakeJira(deny={(GATEWAY, "POST"): status})
                with self.assertRaises(LinkWriteError) as ctx:
                    upsert(fake, host_mode="gateway")
                message = str(ctx.exception)
                self.assertIn(str(status), message)
                self.assertIn("write:jira-work", message)
                self.assertIn("Link issues", message)

    def test_a_network_failure_is_a_link_write_error(self):
        def opener(req):
            raise urllib.error.URLError("no route")

        with self.assertRaises(LinkWriteError) as ctx:
            upsert(opener, host_mode="site")
        self.assertIn("no route", str(ctx.exception))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = os.path.join(self.tmp.name, "config.json")
        with open(self.config, "w", encoding="utf-8") as fh:
            json.dump({"testops": {"project_id": 1, "base_url": TESTOPS},
                       "jira_base_url": SITE}, fh)

    def run_main(self, extra, env, opener=None):
        argv = ["--issue", ISSUE, "--case-id", "4321", "--config", self.config] + extra
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv, env=env, opener=opener)
        return code, out.getvalue(), err.getvalue()

    def test_the_shipped_config_names_the_testops_host(self):
        with open(DEFAULT_CONFIG, encoding="utf-8") as fh:
            config = json.load(fh)
        self.assertEqual(TESTOPS, config["testops"].get("base_url"))
        self.assertEqual(1, config["testops"]["project_id"])

    def test_dry_run_prints_the_requests_without_sending(self):
        def opener(req):
            raise AssertionError(f"sent {req.get_method()} {req.full_url}")

        code, out, err = self.run_main(["--dry-run"], env=dict(CREDS), opener=opener)
        self.assertEqual(0, code, err)
        self.assertIn(f"GET {LINKS_PATH}", out)
        self.assertIn(f"POST {LINKS_PATH}", out)
        self.assertIn(f"PUT {LINKS_PATH}/<", out)
        self.assertIn(json.dumps(PAYLOAD), out)

    def test_dry_run_needs_no_credentials(self):
        code, out, _ = self.run_main(["--dry-run"], env={})
        self.assertEqual(0, code)
        self.assertIn("Allure TestOps case 4321", out)

    def test_missing_credentials_exit_3_with_the_link_to_add_by_hand(self):
        for env in ({}, {"JIRA_EMAIL": "qa@kinoa.io"}, {"JIRA_API_TOKEN": "t"}):
            with self.subTest(env=env):
                fake = FakeJira()
                code, out, err = self.run_main([], env=env, opener=fake)
                self.assertEqual(3, code)
                self.assertEqual([], fake.requests)
                self.assertIn("JIRA_EMAIL", err)
                self.assertIn("title: Allure TestOps case 4321", err)
                self.assertIn(f"url: {CASE_URL}", err)

    def test_a_rejected_write_exits_1_with_the_link_to_add_by_hand(self):
        fake = FakeJira(deny={(GATEWAY, "POST"): 403})
        code, out, err = self.run_main([], env={**CREDS, "JIRA_HOST": "gateway"}, opener=fake)
        self.assertEqual(1, code)
        self.assertIn("write:jira-work", err)
        self.assertIn("Link issues", err)
        self.assertIn("title: Allure TestOps case 4321", err)
        self.assertIn(f"url: {CASE_URL}", err)

    def write_config(self, config):
        with open(self.config, "w", encoding="utf-8") as fh:
            json.dump(config, fh)

    def test_an_unreadable_config_exits_1_with_the_title_and_no_url(self):
        for content in (None, "{not json", "[]"):
            with self.subTest(content=content):
                if content is None:
                    os.remove(self.config)
                else:
                    with open(self.config, "w", encoding="utf-8") as fh:
                        fh.write(content)
                fake = FakeJira()
                code, out, err = self.run_main([], env=dict(CREDS), opener=fake)
                self.assertEqual(1, code)
                self.assertEqual([], fake.requests)
                self.assertIn("cannot read --config", err)
                self.assertIn("title: Allure TestOps case 4321", err)
                self.assertNotIn("url:", err)

    def test_a_config_without_the_jira_site_exits_1_with_the_title_and_the_url(self):
        self.write_config({"testops": {"project_id": 1, "base_url": TESTOPS}})
        fake = FakeJira()
        code, out, err = self.run_main([], env=dict(CREDS), opener=fake)
        self.assertEqual(1, code)
        self.assertEqual([], fake.requests)
        self.assertIn("has no jira_base_url", err)
        self.assertIn("title: Allure TestOps case 4321", err)
        self.assertIn(f"url: {CASE_URL}", err)

    def test_a_config_without_the_testops_project_exits_1_with_the_title_and_no_url(self):
        self.write_config({"testops": {"base_url": TESTOPS}, "jira_base_url": SITE})
        code, out, err = self.run_main([], env=dict(CREDS), opener=FakeJira())
        self.assertEqual(1, code)
        self.assertIn("has no testops.project_id", err)
        self.assertIn("title: Allure TestOps case 4321", err)
        self.assertNotIn("url:", err)

    def test_a_written_link_exits_0_and_names_it(self):
        fake = FakeJira()
        code, out, err = self.run_main([], env=dict(CREDS), opener=fake)
        self.assertEqual(0, code, err)
        self.assertIn("Allure TestOps case 4321", out)
        self.assertIn(CASE_URL, out)
        self.assertEqual(1, len(fake.case_links()))

    def test_jira_host_selects_the_host(self):
        fake = FakeJira()
        code, _, err = self.run_main([], env={**CREDS, "JIRA_HOST": "site"}, opener=fake)
        self.assertEqual(0, code, err)
        self.assertTrue(all(r[1].startswith(SITE) for r in fake.requests), fake.requests)

    def test_a_case_id_that_is_not_a_positive_integer_is_a_usage_error(self):
        for bad in ("abc", "0", "-3"):
            with self.subTest(bad=bad):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                    main(["--issue", ISSUE, "--case-id", bad, "--dry-run"], env={})
                self.assertEqual(2, ctx.exception.code)

    def test_an_issue_that_is_not_a_key_is_a_usage_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            main(["--issue", "king 1", "--case-id", "4321", "--dry-run"], env={})
        self.assertEqual(2, ctx.exception.code)

    def test_the_script_runs_as_a_program(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("JIRA_EMAIL", "JIRA_API_TOKEN")}
        proc = subprocess.run([sys.executable, SCRIPT, "--issue", ISSUE, "--case-id", "4321",
                               "--dry-run"], capture_output=True, text=True, env=env)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("Allure TestOps case 4321", proc.stdout)


if __name__ == "__main__":
    unittest.main()
