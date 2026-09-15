# QA Test Plan — kinoa-reports / scheduled-export
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22988 · target: kinoa-reports/scheduled-export@main · generated: 2026-09-14
prd: resolved
openspec: none
design: remote (simulated)

## Acceptance Criteria
- AC-1: Requesting an export queues the job and emails the operator a download link when the CSV is ready
- AC-2: A download link stays valid for a retention window, after which the file is purged and the link returns HTTP 410

## Cases

### TC-1 · A requested export is queued and its download link is emailed
- type: functional
- priority: P1
- source: ac: AC-1
- design-ref: Zx9QwErTy012/880:1420 — Export · Ready
- preconditions: an operator is signed in and a scheduled report with at least one row exists
- steps:
  1. request an export of the scheduled report
  2. wait for the export job to finish
  3. open the operator's mailbox
- expected: the job is queued, and when the CSV is ready the operator receives an email containing a download link, and the Reports screen shows "Your export is ready." with a "Download CSV" action

## Conflicts
- ⚠️ CONFLICT: AC-2 · story: a download link is valid for 7 days vs prd: an export file is retained for 24 hours vs design: the "Export · Ready" frame reads "This link expires in 30 days." — no case was generated for AC-2; Story, PRD and mockup are equal business sources and the plugin picks no winner

## Gaps
