# test_jira_attachments.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from jira_attachments import (MAX_BYTES, AttachmentError, content_url,
                              credentials, fetch_attachment, select_image_attachments)

BASE = "https://kinoadev.atlassian.net"


def issue(attachments):
    return {"fields": {"attachment": attachments}}


class SelectImageAttachments(unittest.TestCase):
    def test_keeps_only_image_mime_types(self):
        kept, skipped = select_image_attachments(issue([
            {"id": 101, "filename": "mock.png", "mimeType": "image/png", "size": 12},
            {"id": 102, "filename": "spec.pdf", "mimeType": "application/pdf", "size": 12},
        ]), base_url=BASE)
        self.assertEqual(["101"], [a["id"] for a in kept])
        self.assertEqual([], skipped)

    def test_missing_null_and_empty_attachment_field_return_empty(self):
        for payload in ({}, {"fields": {}}, {"fields": {"attachment": None}},
                        {"fields": {"attachment": []}}, None):
            kept, skipped = select_image_attachments(payload, base_url=BASE)
            self.assertEqual(([], []), (kept, skipped))

    def test_oversized_image_is_skipped_with_a_reason(self):
        kept, skipped = select_image_attachments(issue([
            {"id": 103, "filename": "huge.png", "mimeType": "image/png", "size": MAX_BYTES + 1},
        ]), base_url=BASE)
        self.assertEqual([], kept)
        self.assertEqual("103", skipped[0]["id"])
        self.assertIn("cap", skipped[0]["reason"])

    def test_size_exactly_at_the_cap_is_kept(self):
        kept, _ = select_image_attachments(issue([
            {"id": 104, "filename": "edge.png", "mimeType": "image/png", "size": MAX_BYTES},
        ]), base_url=BASE)
        self.assertEqual(["104"], [a["id"] for a in kept])

    def test_content_url_is_composed_from_base_url_and_id(self):
        self.assertEqual(f"{BASE}/rest/api/3/attachment/content/105",
                         content_url(BASE + "/", 105))

    def test_record_carries_filename_and_mime(self):
        kept, _ = select_image_attachments(issue([
            {"id": 106, "filename": "a — b.png", "mimeType": "image/png", "size": 5},
        ]), base_url=BASE)
        self.assertEqual("a — b.png", kept[0]["filename"])
        self.assertEqual("image/png", kept[0]["mimeType"])


class Credentials(unittest.TestCase):
    def test_returns_none_when_either_variable_is_missing(self):
        self.assertIsNone(credentials({}))
        self.assertIsNone(credentials({"JIRA_EMAIL": "a@b.c"}))
        self.assertIsNone(credentials({"JIRA_API_TOKEN": "t"}))
        self.assertIsNone(credentials({"JIRA_EMAIL": "", "JIRA_API_TOKEN": "t"}))

    def test_returns_the_pair_when_both_are_set(self):
        self.assertEqual(("a@b.c", "t"),
                         credentials({"JIRA_EMAIL": "a@b.c", "JIRA_API_TOKEN": "t"}))


class FetchAttachment(unittest.TestCase):
    def test_sends_basic_auth_and_returns_bytes(self):
        seen = {}

        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b"PNGDATA"

        def opener(req):
            seen["url"] = req.full_url
            seen["auth"] = req.get_header("Authorization")
            return Resp()

        data = fetch_attachment(f"{BASE}/x", email="a@b.c", token="t", opener=opener)
        self.assertEqual(b"PNGDATA", data)
        self.assertEqual(f"{BASE}/x", seen["url"])
        self.assertTrue(seen["auth"].startswith("Basic "))

    def test_http_error_becomes_attachment_error(self):
        import urllib.error

        def opener(req):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        with self.assertRaises(AttachmentError) as ctx:
            fetch_attachment(f"{BASE}/x", email="a@b.c", token="t", opener=opener)
        self.assertIn("404", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
