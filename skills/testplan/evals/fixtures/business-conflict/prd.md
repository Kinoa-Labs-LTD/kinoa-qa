# PRD extract — Reports / scheduled export retention

(Fixture: a simulated Confluence PRD extract. No Atlassian MCP runs in the eval env.)

## Retention
Generated export files are transient. An export file is retained for **24 hours** from the
moment it is generated; the purge job runs hourly and a request for a purged file returns
HTTP 410. Compliance signed off on the 24-hour window — exports may contain PII.
