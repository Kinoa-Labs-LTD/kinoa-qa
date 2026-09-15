# QA Test Plan — kinoa-client-support-tool / admin-lockout
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22901 · target: kinoa-client-support-tool/admin-lockout@main · generated: 2026-09-14
prd: resolved
openspec: admin-lockout@0f1e2d3c4b5a
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: After 5 consecutive failed sign-in attempts the admin account is locked
- AC-2: While an account is locked, a sign-in with the correct password is still refused (HTTP 423) and the account stays locked until an operator unlock

## Cases

### TC-1 · Five consecutive failures lock the admin account
- type: functional
- priority: P1
- source: ac: AC-1
- openspec-ref: Admin sign-in lockout/Five failed attempts lock the account
- preconditions: admin account is ACTIVE with 0 recorded failures
- steps:
  1. post 5 sign-ins with an incorrect password
  2. read the account state
- expected: the account state is LOCKED

### TC-2 · A correct password while locked is still refused
- type: negative
- priority: P1
- source: ac: AC-2
- preconditions: the admin account is LOCKED after 5 failed attempts
- steps:
  1. post a sign-in with the CORRECT password while the account is LOCKED
  2. read the account state
- expected: the sign-in is refused with HTTP 423 and the account state is still LOCKED

## Conflicts
- ⚠️ CONFLICT: AC-2 · story: a correct password while LOCKED is refused with 423 and the account stays locked vs openspec: a correct password while LOCKED clears the lock and grants the session — no case was generated for AC-2; the plugin picks no winner
  → resolved: business wins

## Gaps
- ⚠️ GAP: Lockout telemetry — spec states no observable behavior to assert
- ⚠️ GAP: Admin sign-in lockout/A correct password clears the lock — contradicted by AC-2; no case until the conflict is resolved
