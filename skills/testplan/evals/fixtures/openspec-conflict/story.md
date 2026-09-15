# KING-22901 — Lock an admin account after repeated failed sign-ins

(Fixture: a simulated Jira Story body. No Atlassian MCP runs in the eval env.)

## Description
Repeated failed sign-in attempts must lock an admin account. A locked account stays locked
until an operator unlocks it — a later sign-in with the correct password must NOT unlock it.

## Acceptance criteria
- AC-1: After 5 consecutive failed sign-in attempts the admin account is locked.
- AC-2: While an account is locked, a sign-in with the CORRECT password is still refused
  (HTTP 423) and the account remains locked; only an operator unlock clears it.
