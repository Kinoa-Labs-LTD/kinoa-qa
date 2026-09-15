# QA Test Plan — kinoa-admin-shell / notifications
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22954 · title: Notifications empty state · target: kinoa-admin-shell/notifications@main · generated: 2026-09-14
prd: resolved
openspec: none
design: none (Figma MCP unreachable — simulated outage)

## Acceptance Criteria
- AC-1: Opening the bell icon shows the notifications panel with the newest notification first

## Cases

### TC-1 · The notifications panel lists the newest notification first
- type: functional
- priority: P1
- purpose: Verify that the notifications panel lists the newest notification first.
- source: ac: AC-1
- preconditions: An admin is signed in to the admin shell.
  The admin has 3 unread notifications with distinct timestamps.
- steps:
  1. Open the admin shell.
     → expected: The shell header renders with the bell icon showing the unread count.
  2. Click the bell icon.
     → expected: The notifications panel opens and the most recent notification is the first row.
- expected: the notifications panel opens and the most recent notification is the first row

## Conflicts

## Gaps
