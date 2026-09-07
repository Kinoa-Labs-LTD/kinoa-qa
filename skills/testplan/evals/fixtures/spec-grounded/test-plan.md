# QA Test Plan — kinoa-client-support-tool / admin-authentication
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · target: kinoa-client-support-tool/admin-authentication@main · generated: 2026-09-07 · spec-sha: a1b2c3d4e5f6
specs: resolved

## Cases

### TC-1 · A tenant token creates an Author account
- type: functional
- priority: P1
- source: scenario: Google Workspace sign-in/A tenant token creates an Author account
- preconditions: no account row exists for anna@kinoa.io
- steps:
  1. present an OIDC user request (email=anna@kinoa.io, hd=kinoa.io, email_verified=true)
  2. invoke the OIDC user service to load that user
- expected: a principal for anna@kinoa.io is returned and exactly one AUTHOR account row exists

### TC-2 · The break-glass credentials grant Super admin
- type: functional
- priority: P1
- source: scenario: Break-glass sign-in/The break-glass credentials grant Super admin
- preconditions: break-glass credentials configured; approver list empty
- steps:
  1. post a form sign-in with valid break-glass credentials and a valid CSRF token
- expected: the session is redirected to /admin/incidents with Super admin access

## Gaps
- ⚠️ GAP: Token rate limiting — spec states no observable behavior to assert
