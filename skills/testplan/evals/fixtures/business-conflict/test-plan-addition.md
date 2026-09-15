# QA Test Plan — kinoa-reports / export-progress
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22989 · title: Show export progress while a report is generating · target: kinoa-reports/export-progress@main · generated: 2026-09-14
prd: resolved
openspec: none
design: remote (simulated)

## Acceptance Criteria
- AC-1: While an export job is running the Reports screen shows an in-progress indicator instead of the "Download CSV" action
- AC-2: The in-progress state shows a spinner labelled "Preparing your export…" beside a "Cancel export" action, with no banner and no helper text

## Cases

### TC-1 · A running export replaces the download action with an in-progress indicator
- type: functional
- priority: P1
- purpose: Verify that a running export job replaces the download action with an in-progress indicator.
- source: ac: AC-1
- design-ref: Zx9QwErTy012/880:1510 — Export · In progress
- preconditions: An operator is signed in.
  An export job for a scheduled report is running.
- steps:
  1. Open the Reports screen while the export job is still running.
     → expected: The report row shows an in-progress indicator and no "Download CSV" action.
- expected: the "Download CSV" action is not rendered and an in-progress indicator is shown in its place

### TC-2 · The in-progress state offers a cancel action
- type: edge
- priority: P2
- purpose: Verify that the in-progress state offers a cancel action beside the progress spinner.
- source: ac: AC-2
- design-ref: Zx9QwErTy012/880:1510 — Export · In progress
- preconditions: An operator is signed in.
  An export job for a scheduled report is running.
- steps:
  1. Open the Reports screen while the export job is still running.
     → expected: The report row shows the in-progress state instead of the download action.
  2. Read the progress row.
     → expected: A spinner labelled "Preparing your export…" is shown beside a "Cancel export" action, with no success banner and no helper text.
- expected: a spinner labelled "Preparing your export…" is shown beside a "Cancel export" action, with no success banner and no helper text

## Conflicts

## Gaps
