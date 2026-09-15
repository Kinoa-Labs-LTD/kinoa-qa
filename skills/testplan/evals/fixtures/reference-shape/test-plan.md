# QA Test Plan — kinoa-in-app / milestones-eligibility
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-18454 · title: As an operator I want to have Eligibility checkboxes for Milestones in-app · target: kinoa-in-app/milestones-eligibility@main · generated: 2026-09-15
prd: resolved
openspec: none (no OpenSpec file in the service repo)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: Eligibility is decremented only when the final milestone of an in-app is collected; collecting an intermediate milestone leaves the counter, the instance and the progression untouched

## Cases

### TC-1 · Collecting a non-final milestone does not change the eligibility counter
- type: functional
- priority: P1
- purpose: Verify eligibility is untouched while the player progresses through milestones before the last one.
- source: ac: AC-1
- preconditions: Published Milestone in-app with 3 milestones and Max Eligibility = 2.
  Test player has an active in-app instance with actual_eligibility = 2 and no milestones collected.
- steps:
  1. Reach and collect milestone 1 via the collect-milestones endpoint.
     → expected: Request succeeds; the reward of milestone 1 is granted.
  2. Inspect the collect-milestones response body.
     → expected: The response contains no in_app key — the claim did not engage.
  3. Fetch the player's in-app instance.
     → expected: actual_eligibility is still 2; the instance ID is unchanged; progression reflects milestone 1 as collected.
  4. Reach and collect milestone 2 (still not the final one).
     → expected: Request succeeds, no in_app key in the response, actual_eligibility is still 2, progression is not reset.
- expected: Eligibility is decremented only at the final milestone; intermediate collects leave actual_eligibility, the instance ID and the progression intact.

## Conflicts

## Gaps
