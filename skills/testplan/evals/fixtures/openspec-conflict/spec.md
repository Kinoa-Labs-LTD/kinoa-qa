### Requirement: Admin sign-in lockout
#### Scenario: Five failed attempts lock the account
- WHEN an admin posts a 6th sign-in after 5 consecutive failures
- THEN the account state is LOCKED

#### Scenario: A correct password clears the lock
- WHEN an admin posts the correct password while the account is LOCKED
- THEN the lock is cleared and the session is granted

### Requirement: Lockout telemetry
