# QA Test Plan — KING-22737 (business-only)
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: (none) · generated: 2026-09-07
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
- source: ac: AC-1
- preconditions: the user has no existing account
- steps:
  1. sign in with an authorized Workspace account for the first time
- expected: an Author account is created for the user

### TC-2 · Break-glass access is refused past the limit
- type: negative
- priority: P1
- source: ac: AC-2
- preconditions: break-glass configured with a small attempt limit
- steps:
  1. exceed the allowed number of break-glass attempts
- expected: access is refused and the attempt is audited

## Conflicts

## Gaps
