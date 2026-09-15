# QA Test Plan — kinoa-admin-shell / notifications
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22954 · title: Notifications empty state · target: kinoa-admin-shell/notifications@main · generated: 2026-09-14
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
- purpose: Verify that the notifications panel lists the newest notification first.
- source: ac: AC-1
- design-ref: aBcD1234EfGh/1205:3312 — Notifications · Default
- preconditions: An admin is signed in to the admin shell.
  The admin has 3 unread notifications with distinct timestamps.
- steps:
  1. Open the admin shell.
     → expected: The shell header renders with the bell icon showing the unread count.
  2. Click the bell icon.
     → expected: The notifications panel opens and the most recent notification is the first row.
- expected: the notifications panel opens and the most recent notification is the first row

### TC-2 · The empty state is shown when there are no notifications
- type: edge
- priority: P2
- purpose: Verify that the notifications panel shows the empty state when the admin has no notifications.
- source: ac: AC-2
- design-ref: aBcD1234EfGh/1205:3390 — Notifications · Empty state
- preconditions: An admin is signed in to the admin shell.
  The admin has zero notifications.
- steps:
  1. Open the admin shell.
     → expected: The shell header renders with the bell icon showing no unread count.
  2. Click the bell icon.
     → expected: The panel shows "You're all caught up" above "New notifications will appear here." with no notification rows and no "Mark all as read" action.
- expected: the panel shows "You're all caught up" above "New notifications will appear here." with no notification rows and no "Mark all as read" action

## Conflicts

## Gaps
