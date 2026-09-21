# Step A ImageReader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Step A of the `testplan` plugin read a Jira Story's image attachments, so what an image shows becomes an acceptance criterion instead of a `⚠️ GAP`.

**Architecture:** A new `ImageReader` adds `images[]` to the authoritative tier of the SoT bundle. Retrieval is an authenticated Jira REST fetch using environment credentials; provenance rides on a new optional case field `image-ref:`, validated offline by syntax and source pairing only, exactly as `design-ref:` is.

**Tech Stack:** Python 3 standard library only (no third-party imports anywhere in `skills/testplan/scripts/`), `unittest`, Markdown reference files that the agent executes.

**Spec:** `docs/superpowers/specs/2026-09-21-testplan-image-reader-design.md`

## Global Constraints

- **stdlib only.** No third-party imports in any script under `skills/testplan/scripts/`.
- **Every test file ends with `if __name__ == "__main__": unittest.main()` and defines nothing after that block.** A class appended below it runs under `discover` but not on a direct run, reporting a false green.
- **The validator is offline.** No check may perform a network call, read an environment variable, or touch Jira.
- **Reference Markdown under `skills/testplan/` is implementation, not documentation.** A reference file that misdescribes the validator is a defect, not a typo.
- **Never split a delimited line where the value may contain the delimiter.** `image-ref` is matched with a regex, never `split("—")`; a filename containing an em dash must survive intact, proven by a test.
- Credentials: `JIRA_EMAIL`, `JIRA_API_TOKEN`. Base URL: the existing `jira_base_url` key in `config.json`. Endpoint: `<jira_base_url>/rest/api/3/attachment/content/<id>`.
- Size cap: `10 * 1024 * 1024` bytes per image, skipped with a reason above it.
- Working directory for all test commands: `skills/testplan/scripts/`.
- Baseline before any change: `python3 -m unittest discover -p "test_*.py"` reports **225 tests, OK**.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/testplan/scripts/jira_attachments.py` (create) | Pure selection of image attachments from an issue JSON, plus the one network call that fetches their bytes. |
| `skills/testplan/scripts/test_jira_attachments.py` (create) | Unit tests for the above; the fetch is exercised through an injected opener, never a real request. |
| `skills/testplan/scripts/validate_test_plan.py` (modify) | New `image-ref-valid` check; `image` added to `CONFLICT_SOURCES`; header docstring check-list updated. |
| `skills/testplan/scripts/test_validate_test_plan.py` (modify) | Cases for the new check and the new conflict source. |
| `skills/testplan/references/test-plan-format.md` (modify) | The `images:` header line, the `image-ref:` field, the conflict-source vocabulary, the TestOps mapping row. |
| `skills/testplan/references/generation.md` (modify) | How ACs are derived from images; no-fabrication; image conflicts. |
| `skills/testplan/references/sot-assembly.md` (modify) | The ImageReader itself: extraction, credentials, endpoint, header line, degradation. |
| `skills/testplan/SKILL.md` (modify) | Step A mention, reference-table row, degradation rows. |
| `README.md` (modify) | The two environment variables and a dependency-table row. |

---

### Task 1: `jira_attachments.py` — selection and retrieval

**Files:**
- Create: `skills/testplan/scripts/jira_attachments.py`
- Test: `skills/testplan/scripts/test_jira_attachments.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `MAX_BYTES`, `EMAIL_ENV`, `TOKEN_ENV`, `AttachmentError`,
  `content_url(base_url, attachment_id) -> str`,
  `select_image_attachments(issue_json, *, base_url, max_bytes=MAX_BYTES) -> (kept, skipped)` where each record is
  `{"id": str, "filename": str, "mimeType": str, "size": int, "content_url": str}` and a skipped record additionally carries `"reason": str`,
  `credentials(env=None) -> (email, token) | None`,
  `fetch_attachment(url, *, email, token, opener=None) -> bytes`.

- [ ] **Step 1: Write the failing test**

Create `skills/testplan/scripts/test_jira_attachments.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd skills/testplan/scripts && python3 -m unittest test_jira_attachments -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'jira_attachments'`.

- [ ] **Step 3: Write the minimal implementation**

Create `skills/testplan/scripts/jira_attachments.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd skills/testplan/scripts && python3 -m unittest test_jira_attachments -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Run the whole suite**

Run: `cd skills/testplan/scripts && python3 -m unittest discover -p "test_*.py"`
Expected: OK, 235 tests (225 baseline + 10).

- [ ] **Step 6: Commit**

```bash
git add skills/testplan/scripts/jira_attachments.py skills/testplan/scripts/test_jira_attachments.py
git commit -m "Add the ImageReader's attachment selection and retrieval"
```

---

### Task 2: `image-ref-valid` in the validator

**Files:**
- Modify: `skills/testplan/scripts/validate_test_plan.py` (header docstring check list; `CONFLICT_SOURCES` at line 65; new check after `design-ref-valid`, which ends at line 206)
- Test: `skills/testplan/scripts/test_validate_test_plan.py`

**Interfaces:**
- Consumes: nothing from Task 1 — the validator is offline and must not import `jira_attachments`.
- Produces: a check named `image-ref-valid` in the report's `checks` list; `IMAGE_REF_RE`; `"image"` in `CONFLICT_SOURCES`.

- [ ] **Step 1: Write the failing test**

Append these classes to `skills/testplan/scripts/test_validate_test_plan.py` — **above** the
closing `if __name__ == "__main__": unittest.main()` block, which must remain the last thing
in the file. The file already provides the helpers used below: `_write(tmp, text)` writes a
plan to a temp path and returns it, `_checks(report)` maps check names to check dicts, and
`validate(plan_path, None)` runs a business-mode validation. Do not add new helpers.

```python
PLAN_IMAGE_REF = """# QA Test Plan — KING-1 · svc / cap
story: KING-1 · title: T · generated: 2026-09-21
images: 1 read

## Acceptance Criteria

- AC-1: The eligibility checkbox is disabled while a progression is active.

## Cases

### TC-1 · Eligibility checkbox is disabled during a progression
- type: functional
- priority: P1
- purpose: Verify that the checkbox is disabled while a progression is active.
- source: ac: AC-1
- image-ref: 10231 — milestone-eligibility.png
- preconditions: An operator is on the in-app configuration screen.
- steps:
  1. Open the in-app configuration screen.
     → expected: The eligibility checkbox is visible and disabled.
- expected: The checkbox cannot be toggled during a progression.

## Conflicts

## Gaps
"""


class ImageRefValid(unittest.TestCase):
    def _run(self, plan_text):
        with tempfile.TemporaryDirectory() as tmp:
            return validate(_write(tmp, plan_text), None)

    def test_well_formed_image_ref_passes(self):
        r = self._run(PLAN_IMAGE_REF)
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])

    def test_filename_containing_an_em_dash_is_not_truncated(self):
        r = self._run(PLAN_IMAGE_REF.replace("milestone-eligibility.png",
                                             "milestone — eligibility.png"))
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])

    def test_malformed_image_ref_fails_naming_the_case(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "- image-ref: 10231 — milestone-eligibility.png",
            "- image-ref: milestone-eligibility.png"))
        self.assertEqual(1, r["exit_code"])
        self.assertIn("TC-1", _checks(r)["image-ref-valid"]["detail"])

    def test_non_numeric_attachment_id_fails(self):
        r = self._run(PLAN_IMAGE_REF.replace("10231 —", "abc —"))
        self.assertEqual(1, r["exit_code"])
        self.assertFalse(_checks(r)["image-ref-valid"]["ok"])

    def test_image_ref_requires_an_ac_source(self):
        r = self._run(PLAN_IMAGE_REF
                      .replace("- source: ac: AC-1",
                               "- source: QA-added: operator sanity check")
                      .replace("- AC-1: The eligibility checkbox is disabled while a "
                               "progression is active.\n", ""))
        self.assertEqual(1, r["exit_code"])
        self.assertIn("ac:", _checks(r)["image-ref-valid"]["detail"])

    def test_absent_image_ref_is_valid(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "- image-ref: 10231 — milestone-eligibility.png\n", ""))
        self.assertEqual(0, r["exit_code"], r["checks"])
        self.assertTrue(_checks(r)["image-ref-valid"]["ok"])


class ImageConflictSource(unittest.TestCase):
    def _run(self, plan_text):
        with tempfile.TemporaryDirectory() as tmp:
            return validate(_write(tmp, plan_text), None)

    def test_image_is_an_accepted_conflict_source(self):
        plan = PLAN_IMAGE_REF.replace(
            "- AC-1: The eligibility checkbox is disabled while a progression is active.",
            "- AC-1: The eligibility checkbox is disabled while a progression is active.\n"
            "- AC-2: The eligibility checkbox is required.").replace(
            "## Conflicts\n",
            "## Conflicts\n\n- ⚠️ CONFLICT: AC-2 · story: the checkbox is optional vs "
            "image: the frame shows it required — no case was generated for AC-2\n")
        r = self._run(plan)
        # An unannotated conflict is HOLD, not FAIL: the source vocabulary accepted `image`.
        self.assertEqual(2, r["exit_code"], r["checks"])

    def test_unknown_conflict_source_is_still_rejected(self):
        r = self._run(PLAN_IMAGE_REF.replace(
            "## Conflicts\n",
            "## Conflicts\n\n- ⚠️ CONFLICT: AC-1 · story: a vs screenshot: b — none\n"))
        self.assertEqual(1, r["exit_code"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd skills/testplan/scripts && python3 -m unittest test_validate_test_plan.ImageRefValid -v`
Expected: FAIL — no check named `image-ref-valid` in the report (a `KeyError`/`StopIteration`
from the helper, or an assertion on `ok`).

- [ ] **Step 3: Write the minimal implementation**

In `validate_test_plan.py`, beside `DESIGN_REF_RE` (line 61), add:

```python
# `<attachment-id> — <filename>`. Matched, never split: a filename may legitimately contain
# an em dash, and splitting on it would truncate the value silently.
IMAGE_REF_RE = re.compile(r"^\d+\s+—\s+\S.*$")
```

Extend the conflict vocabulary at line 65:

```python
CONFLICT_SOURCES = ("story", "prd", "design", "openspec", "image")
```

Immediately after the `design-ref-valid` check block (which appends at line 205-206), add:

```python
    # 5. image-ref-valid — syntax and source pairing only; never a Jira call
    bad = []
    for c in cases:
        ref = (c["tags"].get("image-ref") or "").strip()
        if not ref:
            continue
        if not IMAGE_REF_RE.match(ref):
            bad.append(f"{c['id']}: malformed image-ref '{ref}' "
                       f"(expected '<attachment-id> — <filename>')")
        if not c["tags"].get("source", "").startswith("ac:"):
            bad.append(f"{c['id']}: image-ref requires an 'ac:' source — an image enters "
                       f"through the acceptance criteria, not as a source kind")
    checks.append({"name": "image-ref-valid", "ok": not bad,
                   "detail": "ok" if not bad else "; ".join(bad)})
```

Renumber the comment numbering of the checks that follow it (`allure-id-valid` onwards) so
the numbered comments stay sequential, and update the numbered check list in the module
docstring at the top of the file to include `image-ref-valid` in its new position.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/testplan/scripts && python3 -m unittest test_validate_test_plan -v`
Expected: PASS, including the eight new cases.

- [ ] **Step 5: Confirm no shipped fixture regressed**

Run:
```bash
cd skills/testplan/scripts && for f in ../evals/fixtures/*/test-plan*.md; do
  python3 validate_test_plan.py "$f" >/dev/null 2>&1; echo "$? $f"; done
```
Expected: the same exit code per fixture as before the change (`image-ref` is optional, so
no existing plan changes outcome). Investigate any fixture whose code moved.

- [ ] **Step 6: Run the whole suite**

Run: `cd skills/testplan/scripts && python3 -m unittest discover -p "test_*.py"`
Expected: OK, 243 tests.

- [ ] **Step 7: Commit**

```bash
git add skills/testplan/scripts/validate_test_plan.py skills/testplan/scripts/test_validate_test_plan.py
git commit -m "Validate image-ref and accept image as a conflict source"
```

---

### Task 3: the generator's contract — format and generation references

**Files:**
- Modify: `skills/testplan/references/test-plan-format.md`
- Modify: `skills/testplan/references/generation.md`

**Interfaces:**
- Consumes: the check name `image-ref-valid`, the grammar `<attachment-id> — <filename>`, and the `image` conflict source from Task 2. These files must describe the validator exactly as Task 2 implemented it.
- Produces: the contract the Step B subagent reads.

- [ ] **Step 1: Add the header line to `test-plan-format.md`**

In the Header block, after the `design:` line, add `images: <<n> read | none | none (<reason>)>`
and, in the prose under the block, one sentence: the line is informational like `openspec:`
and `design:`; `images: none` is the ordinary path for a Story with no image attachment, and
only an attempted-and-failed retrieval carries a `(<reason>)` and warns at the gate.

- [ ] **Step 2: Add the field to the `## Cases` grammar**

In the case field block add `- image-ref: <attachment-id> — <filename>   # optional, authoritative traceability`
directly after the `design-ref:` line, update the sentence that lists the fixed field order to
`allure-id`, `type`, `priority`, `purpose`, `source`, `openspec-ref`, `design-ref`,
`image-ref`, `preconditions`, `steps`, `expected`, and add `image-ref` to the sentence naming
the optional fields. Then add a bullet describing it, modelled on the `design-ref:` bullet:

- it points at the Story image attachment behind an image-derived AC;
- like a mockup and unlike a spec, an image **may ground an `expected:`**;
- it is validated **syntactically only** — the validator never calls Jira — and may only
  accompany an `ac:` source;
- the attachment id is a positive integer and the filename may itself contain an em dash,
  so the value is matched, never split.

- [ ] **Step 3: Add `image` to the conflict vocabulary and the TestOps mapping**

In the `## Conflicts` section, change the sentence "Each `<source>` is one of `story` / `prd` /
`design` / `openspec`" to include `image`. In the Field → Allure TestOps V2 mapping table, add
a row for `image-ref` stating it is not pushed as a field and rides the `Provenance:` line on
`description`, exactly as `design-ref` does, and extend the existing `purpose` row's
provenance-suffix mention to name `image-ref:` alongside `openspec-ref:` / `design-ref:`.

- [ ] **Step 4: Add the image rules to `generation.md`**

Add a section "Images — deriving ACs from `images[]`", modelled on the existing mockup section:

- each bundle entry `images[{ id, filename, mimeType, bytes }]` is a **business requirement**,
  equal to the Story, the PRD and a mockup;
- write what the image *shows* into `## Acceptance Criteria` like any other criterion;
- the case stays `source: ac: AC-<n>` and additionally carries `image-ref: <id> — <filename>`,
  taken verbatim from the bundle entry;
- an image showing detail the Story omits is an **additional AC**, not a conflict;
- an image that **contradicts** the Story, the PRD or a mockup is a `## Conflicts` line with
  `image` as one side, and that AC yields no case until it is annotated;
- **no fabrication still applies**: an image with no testable state — a logo, a colour study,
  an unreadable screenshot — produces a `- ⚠️ GAP:` line, never an invented case, and pixel
  values, spacing and colours are never asserted;
- `images: none (<reason>)` simply means no image-derived ACs; it is not licence to guess.

Also update the Precedence section's bundle line and the authoritative-tier sentence to include
`images[]`, and add `image` to the list of conflict `<source>` keywords in the Conflicts
section of this file.

- [ ] **Step 5: Verify the references match the validator**

Run:
```bash
cd skills/testplan/scripts && python3 - <<'PY'
import re, pathlib
v = pathlib.Path("validate_test_plan.py").read_text()
fmt = pathlib.Path("../references/test-plan-format.md").read_text()
gen = pathlib.Path("../references/generation.md").read_text()
assert "image" in re.search(r"CONFLICT_SOURCES = \(([^)]*)\)", v).group(1)
for doc, name in ((fmt, "test-plan-format.md"), (gen, "generation.md")):
    assert "image-ref" in doc, name
    assert "image" in doc, name
print("references mention image-ref and the image conflict source")
PY
```
Expected: the confirmation line, no AssertionError.

- [ ] **Step 6: Commit**

```bash
git add skills/testplan/references/test-plan-format.md skills/testplan/references/generation.md
git commit -m "Teach the plan format and generation rules about Story images"
```

---

### Task 4: Step A itself — `sot-assembly.md`, `SKILL.md`, `README.md`

**Files:**
- Modify: `skills/testplan/references/sot-assembly.md`
- Modify: `skills/testplan/SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: from Task 1 — the module name `jira_attachments.py`, the env var names `JIRA_EMAIL` / `JIRA_API_TOKEN`, the endpoint `<jira_base_url>/rest/api/3/attachment/content/<id>`, the 10 MB cap; from Task 3 — the `images:` header line values.
- Produces: the Step A instructions the orchestrating agent executes.

- [ ] **Step 1: Add the ImageReader section to `sot-assembly.md`**

Insert a section "## 4. ImageReader — Story image attachments (Jira REST, authoritative)"
between the DesignReader and the OpenSpecReader, renumbering OpenSpecReader to 5. It states:

- an image attached to the Story is a **business requirement**, in the authoritative tier with
  Story, PRD and mockups;
- selection and retrieval are implemented in `scripts/jira_attachments.py`:
  `select_image_attachments(issue_json, base_url=...)` then `fetch_attachment(...)` per kept
  record;
- **every** image attachment is read, not only those the description embeds, because an inline
  media placeholder's id does not map onto an attachment id;
- credentials are `JIRA_EMAIL` + `JIRA_API_TOKEN` from the environment and the base URL is
  `jira_base_url` from `config.json`; the plugin owns no credentials, exactly as it owns no
  MCP configuration;
- images above 10 MB are skipped with their reason;
- each image enters the bundle as `images[{ id, filename, mimeType, bytes }]` and is handed to
  the Step B subagent as an actual image, not a description of one;
- the `images:` header line records `<n> read`, `none`, or `none (<reason>)`.

Add the degradation table from the spec verbatim (no image attachment → `images: none`, no
warning; credentials unset → `images: none (jira credentials not set)`, warn; a fetch that
404s or is rejected → that file's reason, others continue, warn; oversized → skipped with
reason, warn; non-image attachment → ignored silently). Close with: never a hard stop — images
degrade exactly like the PRD and Figma.

Also update the tier table at the top of the file to list `{ story, acceptance, prd?,
designs[], images[] }`.

- [ ] **Step 2: Update `SKILL.md`**

- Step A's sentence: the bundle is authoritative `{ story, acceptance, prd?, designs[], images[] }`.
- The reference table: add a row — "Story image attachments (ImageReader)" → `references/sot-assembly.md`.
- The Degradation table: add the rows for credentials unset, a fetch failure, and an oversized
  image, each "Continue; header `images: none (<reason>)`; warn at the gate; never a hard stop",
  and one row for "Story has no image attachment" → "Ordinary path, not a degradation; header
  `images: none`; **no** gate warning".
- The `## Source of truth` section: name the image alongside the Story, PRD and mockup as a
  source with no precedence between them.

- [ ] **Step 3: Update `README.md`**

In the dependency table add a row: **Jira REST (attachments)** | Optional, Step A | Reading
image attachments on the Story | Without `JIRA_EMAIL` + `JIRA_API_TOKEN` the run continues and
the header records `images: none (jira credentials not set)`. Document both variables where the
README describes environment setup, naming the Jira API token page as where the token comes
from, and state the 10 MB per-image cap.

- [ ] **Step 4: Verify every fenced command in the touched docs has a `__main__`**

Run:
```bash
cd /Users/dmytrokapeliukh/Projects/kinoa-qa/.claude/worktrees/testplan-image-reader && \
grep -rn "python3 .*scripts/" skills/testplan/SKILL.md skills/testplan/references/*.md README.md \
| grep -o "scripts/[a-z_]*\.py" | sort -u | while read -r s; do
  grep -q '__main__' "skills/testplan/$s" && echo "OK   $s" || echo "NO MAIN $s"; done
```
Expected: every line reads `OK`. A doc that tells an agent to run a module with no `__main__`
entry point would exit 0 and do nothing — the step would silently never happen. If a `NO MAIN`
appears, remove that fenced command or add the entry point rather than shipping it.

- [ ] **Step 5: Run the whole suite one last time**

Run: `cd skills/testplan/scripts && python3 -m unittest discover -p "test_*.py"`
Expected: OK, 243 tests.

- [ ] **Step 6: Commit**

```bash
git add skills/testplan/references/sot-assembly.md skills/testplan/SKILL.md README.md
git commit -m "Add the ImageReader to Step A, its degradations and its credentials"
```

---

## Self-review notes

- **Spec coverage:** retrieval → Task 1; `image-ref` field and `images:` header → Tasks 2-3;
  validator check and conflict source → Task 2; generation rules → Task 3; Step A wiring,
  degradation table, README credentials → Task 4. Every spec section maps to a task.
- **Out of scope, as the spec states:** re-running KING-18454 through the new path, Confluence
  image embeds, OCR.
- **Type consistency:** `select_image_attachments` returns `(kept, skipped)` in Task 1 and is
  referenced with that shape in Task 4; record keys `id`/`filename`/`mimeType`/`size`/
  `content_url` are used identically in both; the check is named `image-ref-valid` in Tasks 2
  and 3; the grammar `<attachment-id> — <filename>` is identical in the regex, the tests and
  the format doc.
