# QA Test Plan — kinoa-in-app / rewards-claim
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22797 · title: As a player I want my claimed reward to reach my balance · target: kinoa-in-app/rewards-claim@main · generated: 2026-09-17
scope: smoke
prd: none (no PRD link on the Story)
openspec: none (no OpenSpec file in the service repo)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: Claiming a completed in-app reward credits the player's balance once and closes the in-app instance
- AC-2: A second claim of the same in-app instance is refused and leaves the balance unchanged

## Cases

### TC-1 · Claiming a completed in-app credits the balance and closes the instance
- type: functional
- priority: P1
- purpose: Verify that claiming a completed in-app reward works end to end.
- source: ac: AC-1
- preconditions: Published in-app with a single coin reward.
  Test player has a completed in-app instance and a starting balance of 0 coins.
- steps:
  1. Open the completed in-app as the test player.
     → expected: The in-app shows its reward with an enabled Claim button.
  2. Click Claim.
     → expected: The reward is granted and the in-app closes.
  3. Open the player's balance.
     → expected: The balance equals the reward amount.
- expected: The claim credits the balance and closes the in-app instance.

## Conflicts

## Gaps
