# KING-22989 — Export progress indicator

(Fixture: a simulated Jira Story body, the ADDITION variant of business-conflict. No
Atlassian MCP runs in the eval env.)

## Description
While a scheduled report export is being generated the Reports screen must show the
operator that work is in flight. Design:
https://www.figma.com/design/Zx9QwErTy012/Reports?node-id=880-1510

## Acceptance criteria
- AC-1: While an export job is running the Reports screen shows an in-progress indicator
  instead of the "Download CSV" action.

(The Story says nothing about what the in-progress state offers the operator; that detail
exists only in the mockup. Per the plugin's rules a mockup that merely ADDS detail the Story
omits is an extra acceptance criterion, never a conflict — nothing here contradicts the
Story, so this fixture must validate green.)
