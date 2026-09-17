# QA Test Plan — kinoa-client-support-tool / admin-authentication
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22737 · title: [AQA][AI] QA Plugin · target: kinoa-client-support-tool/admin-authentication@main · generated: 2026-09-16
prd: resolved
openspec: none (no OpenSpec file for this capability)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: A revoked Workspace token is rejected at sign-in
- AC-2: An authorized Workspace user signing in for the first time is provisioned an Author account
- AC-3: Valid break-glass credentials grant a Super admin session
- AC-4: Break-glass sign-in is refused when the credentials are invalid

## Cases

### TC-1 · A revoked Workspace token is rejected at sign-in
- type: negative
- priority: P1
- purpose: Verify that a revoked Workspace token is rejected and no session is granted.
- source: ac: AC-1
- preconditions: The Workspace token for anna@kinoa.io has been revoked.
  No session is active for anna@kinoa.io.
- steps:
  1. Present the revoked OIDC user request for anna@kinoa.io.
     → expected: The request is rejected and no session is granted.
- expected: the revoked token is rejected and no session is granted

### TC-2 · First sign-in from an authorized Workspace domain creates an Author account
- type: functional
- priority: P1
- purpose: Verify that a first Workspace sign-in provisions exactly one Author account for the user.
- source: ac: AC-2
- preconditions: No account row exists for anna@kinoa.io.
  The kinoa.io Workspace domain is authorized.
- steps:
  1. Present an OIDC user request for anna@kinoa.io with hd=kinoa.io and email_verified=true.
     → expected: The request is accepted as an authorized Workspace identity.
  2. Invoke the OIDC user service to load that user.
     → expected: A principal for anna@kinoa.io is returned and exactly one AUTHOR account row exists.
- expected: a principal for anna@kinoa.io is returned and exactly one AUTHOR account row exists

### TC-3 · The Break-Glass credentials grant Super admin
- type: functional
- priority: P1
- purpose: Verify that valid break-glass credentials grant a Super admin session.
- source: ac: AC-3
- preconditions: Break-glass credentials are configured.
  The approver list is empty.
- steps:
  1. Sign in on the break-glass form with valid credentials and a valid CSRF token.
     → expected: The session is redirected to /admin/incidents with Super admin access.
- expected: the session is redirected to /admin/incidents with Super admin access

### TC-4 · Break-glass sign-in with invalid credentials is refused
- type: edge
- priority: P1
- purpose: Verify that a break-glass sign-in with invalid credentials is refused.
- source: ac: AC-4
- preconditions: Break-glass credentials are configured.
  No admin session is active.
- steps:
  1. Sign in on the break-glass form with an incorrect break-glass password and a valid CSRF token.
     → expected: No session is granted and the sign-in page reports invalid credentials.
- expected: no session is granted and the sign-in page reports invalid credentials

## Conflicts

## Gaps
