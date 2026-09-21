"""Selection and retrieval of a Jira Story's image attachments (Step A, ImageReader).

The selection half is pure and offline so it is fully unit-tested; `fetch_attachment` is
the only network call in this module, and it takes an injectable opener for the same reason.
An image is an authoritative business source: what it shows may ground an `expected:`.
"""

import base64
import os
import urllib.error
import urllib.request

MAX_BYTES = 10 * 1024 * 1024
EMAIL_ENV = "JIRA_EMAIL"
TOKEN_ENV = "JIRA_API_TOKEN"


class AttachmentError(RuntimeError):
    """A retrieval failure Step A turns into an `images: none (<reason>)` degradation."""


def content_url(base_url, attachment_id):
    """The Jira REST endpoint serving an attachment's bytes."""
    return f"{str(base_url).rstrip('/')}/rest/api/3/attachment/content/{attachment_id}"


def select_image_attachments(issue_json, *, base_url, max_bytes=MAX_BYTES):
    """Split a Story's image attachments into (kept, skipped).

    Every image attachment on the Story is selected, not only those the description embeds:
    an inline media placeholder carries a Media API id that does not map onto an attachment
    id, so filtering by embedding would silently drop images. Non-image attachments are
    ignored and are not a degradation. A missing, null or empty field yields ([], []).
    """
    fields = (issue_json or {}).get("fields") or {}
    attachments = fields.get("attachment") or []
    kept, skipped = [], []
    for item in attachments:
        mime = item.get("mimeType") or ""
        if not mime.startswith("image/"):
            continue
        size = item.get("size") or 0
        record = {
            "id": str(item.get("id")),
            "filename": item.get("filename") or "",
            "mimeType": mime,
            "size": size,
            "content_url": content_url(base_url, item.get("id")),
        }
        if size > max_bytes:
            record["reason"] = f"{size} bytes exceeds the {max_bytes}-byte cap"
            skipped.append(record)
        else:
            kept.append(record)
    return kept, skipped


def credentials(env=None):
    """The (email, token) pair from the environment, or None when either is unset."""
    env = os.environ if env is None else env
    email = (env.get(EMAIL_ENV) or "").strip()
    token = (env.get(TOKEN_ENV) or "").strip()
    return (email, token) if email and token else None


def fetch_attachment(url, *, email, token, opener=None):
    """Download one attachment's bytes over HTTP Basic auth.

    Failures are raised as AttachmentError so Step A degrades with a reason rather than
    crashing: an unreadable image is never a hard stop.
    """
    raw = base64.b64encode(f"{email}:{token}".encode()).decode()
    request = urllib.request.Request(
        url, headers={"Authorization": f"Basic {raw}", "Accept": "*/*"})
    try:
        with (opener or urllib.request.urlopen)(request) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise AttachmentError(f"HTTP {exc.code} fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise AttachmentError(f"{exc.reason} fetching {url}") from exc
