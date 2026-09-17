# QA Test Plan — kinoa-in-app / rewards-claim
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22797 · title: As a player I want my claimed reward to reach my balance · target: kinoa-in-app/rewards-claim@main · generated: 2026-09-17
scope: integration
prd: none (no PRD link on the Story)
openspec: none (no OpenSpec file in the service repo)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: Claiming a completed in-app reward credits the player's balance once and closes the in-app instance

## Cases

### TC-1 · Claiming a completed in-app credits the balance and closes the instance
- type: functional
- priority: P1
- purpose: Verify an end-to-end claim credits the balance exactly once and leaves the instance closed.
- source: ac: AC-1
- preconditions: Published in-app with a single coin reward.
  Test player has a completed in-app instance and a starting balance of 0 coins.
- steps:
  1. Call the claim endpoint for the completed in-app instance.
     → expected: Request succeeds with the granted reward in the response.
     → expected: The player's balance is credited with exactly the reward amount.
     → expected: The in-app instance is reported as closed in the same response.
  2. Fetch the player's balance and in-app instance.
     → expected: The balance is the reward amount and the instance stays closed; a second fetch changes nothing.
- expected: The claim credits the balance exactly once and closes the in-app instance.

## Conflicts

## Gaps
