# QA Test Plan — kinoa-admin-shell / notifications
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22954 · target: kinoa-admin-shell/notifications@main · generated: 2026-09-14
prd: resolved
openspec: none
design: remote (simulated)

## Acceptance Criteria
- AC-1: Opening the bell icon shows the notifications panel with the newest notification first
- AC-2: With no notifications the panel shows the empty state — "You're all caught up" over "New notifications will appear here." — and no "Mark all as read" action

## Cases

### TC-1 · The notifications panel lists the newest notification first
- type: functional
- priority: P1
- source: ac: AC-1
- design-ref: aBcD1234EfGh/1205:3312 — Notifications · Default
- preconditions: the signed-in admin has 3 unread notifications with distinct timestamps
- steps:
  1. open the admin shell
  2. click the bell icon
- expected: the notifications panel opens and the most recent notification is the first row

### TC-2 · The empty state is shown when there are no notifications
- type: edge
- priority: P2
- source: ac: AC-2
- design-ref: aBcD1234EfGh/1205:3390 — Notifications · Empty state
- preconditions: the signed-in admin has zero notifications
- steps:
  1. open the admin shell
  2. click the bell icon
- expected: the panel shows "You're all caught up" above "New notifications will appear here." with no notification rows and no "Mark all as read" action

## Conflicts

## Gaps
