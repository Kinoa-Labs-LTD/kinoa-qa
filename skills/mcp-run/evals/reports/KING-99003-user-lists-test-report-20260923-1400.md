# KING-99003 — user lists via the AI agent: Test Report

> This file is an eval fixture of the `mcp-run` skill: the report of a run of
> `KING-99003-user-lists-test-plan.md` as it stood when the run was paused — sections 1 to 3
> started, no case of the plan's table run at that point. It is not a report of a real run. Its stamp is before
> 2026-10-06, so `check-layout.sh` check 15 does not read it; check 3 accepts its name.

## 1. Header

- **Date (UTC):** 2026-09-23
- **Stand:** the deployed test stand, through the `kinoa` connector (HTTP `/mcp`, OAuth).
- **Caller `user_id`:** not recorded. The plan excerpt has no `pre-` case that records `USER_ID`.
- **Fixed data used** (from the plan's §0):
  - `P1`: *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`)
  - `P2`: *Widget sandbox 2* (`7d3e1c2b-6c75-4a91-8b2c-3d4e5f6a7b8c`), same company as `P1`
  - players: `p_8f2a1c77` (`PLAYER1`), `p_3c9d0e14` (`PLAYER2`)
  - `CSV_URL`: `https://files.example.com/widget-qa/players-2.csv`
- **Run:** `20260923-1400`
- **Plan file:** `../plans/KING-99003-user-lists-test-plan.md`, plan version 1 (2026-09-23)
- **Run reason:** first run
- **Previous report:** none

## 2. Overall status

paused — handed over before the first case of the plan's table; no case has a status yet

## 3. What was done, per part

**Before Part A (the subjects).** The plan excerpt has no preflight section: no tool inventory,
no `USER_ID` case and no snapshot `GET` of the role rows, so `ROLES_BEFORE` is not recorded and
Part A runs under role rows this run never read. The three subjects of the §0 artifacts table
were created in *Widget sandbox* (`7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b`) at 13:58:

- `FIX` = `a1c9e0f2-7b3d-4e8a-9c1f-2d3e4f5a6b7c` (`KING99003-QA-20260923-1400-fix`, key
  `king99003_qa_20260923_1400_fix`), holding `p_8f2a1c77`.
- `IMP_URL` = `b4a1e6d0-2f3c-4c55-9e1a-7a8b9c0d1e2f` (`KING99003-QA-20260923-1400-imp-url`, key
  `king99003_qa_20260923_1400_imp_url`), empty.
- `PB` = `c7d2f1e0-3a4b-4c5d-8e6f-7a8b9c0d1e2f` (`KING99003-QA-20260923-1400-pb`, key
  `king99003_qa_20260923_1400_pb`), empty, reserved for Part B. Its execute leg, at 13:58:40:
  Request: `kinoa_user_list_create {"game_id":"7d3e1c2a-5b64-4f80-9a1b-2c3d4e5f6a7b","name":"KING99003-QA-20260923-1400-pb","key":"king99003_qa_20260923_1400_pb","confirm_token":"eyJ0…Pb1"}`
  Response: `{"ok":true,"data":{"created":true,"userList":{"id":"c7d2f1e0-3a4b-4c5d-8e6f-7a8b9c0d1e2f","name":"KING99003-QA-20260923-1400-pb","key":"king99003_qa_20260923_1400_pb","status":"active"}}}`

Write list: taken from the five tools whose input schema declares `confirm_token`; the
connector shows no annotations. Dry-run: off (`meta.dryRun: false` on the first preview).

### Case status

| Case | Status | Finding / note / blocked row |
|---|---|---|
