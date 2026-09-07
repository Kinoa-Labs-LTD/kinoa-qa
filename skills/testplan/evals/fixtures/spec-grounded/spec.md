### Requirement: Google Workspace sign-in
#### Scenario: A tenant token creates an Author account
- WHEN an authorized Workspace user signs in for the first time
- THEN an Author account is provisioned

### Requirement: Break-glass sign-in
#### Scenario: The break-glass credentials grant Super admin
- WHEN valid break-glass credentials are posted
- THEN the session is granted Super admin

### Requirement: Token rate limiting
