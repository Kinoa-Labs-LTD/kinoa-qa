# QA Test Plan — kinoa-client-support-tool / admin-authentication
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: kinoa-client-support-tool/admin-authentication@main · generated: 2026-09-07
prd: resolved
openspec: admin-authentication@a1b2c3d4e5f6
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: An authorized Workspace user signing in for the first time is provisioned an Author account
- AC-2: Valid break-glass credentials grant a Super admin session
- AC-3: Break-glass sign-in is refused when the credentials are invalid

## Cases

### TC-1 · A first Workspace sign-in provisions an Author account
- type: functional
- priority: P1
- source: ac: AC-1
- openspec-ref: Google Workspace sign-in/A tenant token creates an Author account
- preconditions: no account row exists for anna@kinoa.io
- steps:
  1. present an OIDC user request (email=anna@kinoa.io, hd=kinoa.io, email_verified=true)
  2. invoke the OIDC user service to load that user
- expected: a principal for anna@kinoa.io is returned and exactly one AUTHOR account row exists

### TC-2 · The break-glass credentials grant Super admin
- type: functional
- priority: P1
- source: ac: AC-2
- openspec-ref: Break-glass sign-in/The break-glass credentials grant Super admin
- preconditions: break-glass credentials configured; approver list empty
- steps:
  1. post a form sign-in with valid break-glass credentials and a valid CSRF token
- expected: the session is redirected to /admin/incidents with Super admin access

### TC-3 · Break-glass sign-in with invalid credentials is refused
- type: negative
- priority: P1
- source: ac: AC-3
- openspec-ref: Break-glass sign-in/The break-glass credentials grant Super admin
- preconditions: break-glass credentials configured
- steps:
  1. post a form sign-in with an incorrect break-glass password and a valid CSRF token
- expected: no session is granted and the sign-in page reports invalid credentials

## Conflicts

## Gaps
- ⚠️ GAP: Token rate limiting — spec states no observable behavior to assert
