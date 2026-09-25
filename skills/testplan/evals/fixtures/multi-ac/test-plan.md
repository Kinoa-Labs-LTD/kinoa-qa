# QA Test Plan — kinoa-in-app / rewards-claim
> AUTO-GENERATED DRAFT — review, then approve to sync into Allure TestOps.
> System of record: Allure TestOps · project KINOA. This file is a reviewable intermediate.

story: KING-22797 · title: As a player I want my claimed reward to reach my balance · target: kinoa-in-app/rewards-claim@main · generated: 2026-09-24
scope: e2e
prd: none (no PRD link on the Story)
openspec: none (no OpenSpec file in the service repo)
design: none (no Figma link on the Story)

## Acceptance Criteria
- AC-1: Claiming a completed in-app reward credits the player's balance once
- AC-2: After a claim, the in-app instance is closed and no longer offered
- AC-3: A second claim of the same in-app instance is refused, and the balance is unchanged

## Cases

### TC-1 · Claiming a completed in-app credits the balance and closes the instance
- type: functional
- priority: P1
- purpose: Verify that one claim both credits the balance once and closes the in-app instance.
- source: ac: AC-1, AC-2
- preconditions: Published in-app with a single coin reward.
  Test player has a completed in-app instance and a starting balance of 0 coins.
- steps:
  1. Open the completed in-app as the test player and click Claim.
     → expected: The reward is granted.
     → expected: The in-app closes.
  2. Open the player's balance and the in-app list.
     → expected: The balance equals the reward amount and the in-app is no longer offered.
- expected: The claim credits the balance exactly once and the instance stays closed.

### TC-2 · A second claim of the same in-app instance is refused
- type: negative
- priority: P2
- purpose: Verify that claiming an already claimed in-app instance is refused without changing the balance.
- source: ac: AC-3
- preconditions: Test player has already claimed the in-app instance once.
- steps:
  1. Call the claim endpoint again for the same in-app instance.
     → expected: The request is refused with an "already claimed" error.
  2. Open the player's balance.
     → expected: The balance is unchanged.
- expected: A repeated claim is refused and grants nothing.

## Conflicts

## Gaps
