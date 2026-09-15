# KING-22988 — Download a scheduled report export

(Fixture: a simulated Jira Story body. No Atlassian MCP runs in the eval env.)

## Description
An operator can export a scheduled report as CSV. The export runs in the background and the
operator is emailed a download link when it is ready. Design:
https://www.figma.com/design/Zx9QwErTy012/Reports?node-id=880-1420

The download link stays valid for **7 days**, after which the file is purged and the link
returns HTTP 410.

## Acceptance criteria
- AC-1: Requesting an export queues the job and emails the operator a download link when the
  CSV is ready.
- AC-2: A download link is valid for 7 days; after that the file is purged and the link
  returns HTTP 410.
