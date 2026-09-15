# QA Test Plan — kinoa-reports / export-progress
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22989 · target: kinoa-reports/export-progress@main · generated: 2026-09-14
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
- source: ac: AC-1
- design-ref: Zx9QwErTy012/880:1510 — Export · In progress
- preconditions: an operator is signed in and an export job for a scheduled report is running
- steps:
  1. open the Reports screen while the export job is still running
- expected: the "Download CSV" action is not rendered and an in-progress indicator is shown in its place

### TC-2 · The in-progress state offers a cancel action
- type: edge
- priority: P2
- source: ac: AC-2
- design-ref: Zx9QwErTy012/880:1510 — Export · In progress
- preconditions: an operator is signed in and an export job for a scheduled report is running
- steps:
  1. open the Reports screen while the export job is still running
  2. read the progress row
- expected: a spinner labelled "Preparing your export…" is shown beside a "Cancel export" action, with no success banner and no helper text

## Conflicts

## Gaps
