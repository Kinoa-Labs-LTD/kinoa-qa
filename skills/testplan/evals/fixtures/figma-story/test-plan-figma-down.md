# QA Test Plan — kinoa-admin-shell / notifications
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22954 · target: kinoa-admin-shell/notifications@main · generated: 2026-09-14
prd: resolved
openspec: none
design: none (Figma MCP unreachable — simulated outage)

## Acceptance Criteria
- AC-1: Opening the bell icon shows the notifications panel with the newest notification first

## Cases

### TC-1 · The notifications panel lists the newest notification first
- type: functional
- priority: P1
- source: ac: AC-1
- preconditions: the signed-in admin has 3 unread notifications with distinct timestamps
- steps:
  1. open the admin shell
  2. click the bell icon
- expected: the notifications panel opens and the most recent notification is the first row

## Conflicts

## Gaps
