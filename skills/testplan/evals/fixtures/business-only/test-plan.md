# QA Test Plan — KING-22737 (business-only)
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · title: [AQA][AI] QA Plugin · target: (none) · generated: 2026-09-07
prd: resolved
openspec: none (no service repo resolved)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: Authorized Workspace users get an Author account on first sign-in
- AC-2: Break-glass access is limited and audited

## Cases

### TC-1 · First Workspace sign-in provisions an Author account
- type: functional
- priority: P1
- purpose: Verify that an authorized Workspace user is provisioned an Author account on first sign-in.
- source: ac: AC-1
- preconditions: The user has no existing account.
  The user's Workspace domain is authorized.
- steps:
  1. Sign in with an authorized Workspace account for the first time.
     → expected: The sign-in succeeds and an Author account is created for the user.
- expected: an Author account is created for the user

### TC-2 · Break-glass access is refused past the limit
- type: negative
- priority: P1
- purpose: Verify that break-glass access is refused and audited once the attempt limit is exceeded.
- source: ac: AC-2
- preconditions: Break-glass access is configured with a small attempt limit.
  The audit log is reachable.
- steps:
  1. Exceed the allowed number of break-glass attempts.
     → expected: Access is refused and the rejected attempt is written to the audit log.
- expected: access is refused and the attempt is audited

## Conflicts

## Gaps
