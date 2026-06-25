# GHA Hourly Health Monitor — 2026-06-25

## 13:00 UTC

**Verdict:** DEGRADED

**Note:** No workflow named "CI Tests" exists in this repository. The canonical PR/push test suite is two separate surfaces:
- **Scheduled smoke CI** → "Sports endpoint smoke + Playwright" (`sports-smoke-and-e2e.yml`)
- **PR test matrix** → `test (3.11)` / `test (3.12)` jobs (runs on PR pushes only, not on main directly)

**Main CI — Sports endpoint smoke + Playwright (last 15 runs on main):** 15 success, 0 failure, 0 in_progress
- All runs 2026-06-24T17:54Z → 2026-06-25T13:04Z: `success`
- Latest run id=28172161863, created 2026-06-25T13:04:42Z: `success`

**Main CI — Unified Audit Dashboard (last 15 completed):** 14 success, 0 failure, 1 in_progress
- Latest completed: id=28168765738 created 2026-06-25T12:04:37Z: `success`
- Currently in_progress: id=28172075782 created 2026-06-25T13:03:16Z

**Main CI — ALPHA ENGINE - Live Autonomous Scanner (last 15):** 14 success, 0 failure, 1 in_progress
- Latest completed: id=28165628670 created 2026-06-25T11:04:23Z: `success`
- Currently in_progress: id=28171957749 created 2026-06-25T13:01:19Z

**Chronic workflows (sampled: 3 key workflows):** none
- Sports endpoint smoke + Playwright: 0 cancellations / 15 runs
- ALPHA ENGINE - Live Autonomous Scanner: 0 cancellations / 14 completed runs
- Unified Audit Dashboard: 0 cancellations / 14 completed runs

**Open PRs RED:**

| PR | Title | Failing checks | Cause | Action |
|---|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | `test (3.11)` FAIL, `test (3.12)` FAIL | `alpha_engine/backtest_quant_algorithms.py` invalid syntax at line 1 | AUTHOR_FIX |
| #666 | fix(resolver): B1 backfill price guard | `test (3.11)` FAIL, `test (3.12)` FAIL | Same — `backtest_quant_algorithms.py` invalid syntax at line 1 | AUTHOR_FIX |
| #665 | audit(stalled-producer-detector): v2.0+2 | `test (3.11)` FAIL, `test (3.12)` FAIL | Same — `backtest_quant_algorithms.py` invalid syntax at line 1 | AUTHOR_FIX |
| #657 | feat(contract-test): cold-merge atomic | No checks run | `[skip ci]` in commit message — intentional | IGNORE |

**Root cause detail:** `alpha_engine/backtest_quant_algorithms.py` starts with binary/garbage content (`IsADirectoryErrorCHATWITHIT.mdmd atTH..D`) instead of valid Python. This causes the CI `py_compile` / import scan step to abort with `'invalid syntax' at line 1` on both Python 3.11 and 3.12. The file has been broken across at least 3 PRs opened at different base commits of main (2026-06-24 01:13Z, 15:12Z, 15:30Z), confirming this is a **pre-existing defect on main**, not introduced by these PRs.

**PRs not yet checked for CI:** #600, #595, #581, #564, #562 — likely same test failure pattern if they were opened after the file was corrupted on main.

**Action required:** Author should fix `alpha_engine/backtest_quant_algorithms.py` — replace the corrupted file content with valid Python (or restore from a known-good commit). A single fix commit on main will unblock all 3 open PRs once they rebase/re-run CI.

Run URL (PR #667 failing test): https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28109985534
