# GHA Hourly Health Monitor — 2026-07-07

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Root cause:** `alpha_engine/backtest_quant_algorithms.py` has been overwritten with garbage content. Line 1 reads `IsADirectoryErrorCHATWITHIT.mdmd atTH..D` — not valid Python. Both `test (3.11)` and `test (3.12)` jobs fail with `coverage.py` reporting: `Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1`. The streak spans at least 30 consecutive CI Tests failures on main from 2026-07-05T18:29Z through 2026-07-07T12:02Z (~41.5 hours). PR check runs on PRs #667 and #666 (both opened 2026-06-24) also show `test (3.11)` FAILURE and `test (3.12)` FAILURE, suggesting the breakage may predate July 5.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28864612505

**Chronic workflows:** none — no workflow meets the chronic-cancellation threshold (latest-cancelled + ≥4 cancels in last 15 + 0 successes in last 48h). The 30-run snapshot (most recent run per workflow) shows 16 successes and 14 in_progress; 0 cancelled, 0 failed outside CI Tests.

**Open PRs CI snapshot (9 open PRs):**

| PR | Title | CI Tests | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | ❌ test(3.11) FAIL, test(3.12) FAIL | AUTHOR_FIX (blocked by main breakage; fix `backtest_quant_algorithms.py` on main first) |
| #666 | fix(resolver): B1 backfill price guard | ❌ test(3.11) FAIL, test(3.12) FAIL | AUTHOR_FIX (blocked by main breakage; fix `backtest_quant_algorithms.py` on main first) |
| #665 | audit(stalled-producer-detector): v2.0+2 | not re-checked (opened 2026-06-24, likely same failure pattern) | BLOCKED by main |
| #657 | feat(contract-test): cold-merge atomic contract-test gate | `[skip ci]` in PR body — CI may not have triggered | Review |
| #600, #595, #581, #564, #562 | Various feat/research PRs (opened 2026-06-12/13) | Not re-checked; all predate breakage onset | BLOCKED by main |

**Open PRs RED (CI Tests):** #667, #666 confirmed. All other open PRs likely RED for the same reason (same source file in scope).

**Action required:** **OPERATOR MUST FIX `alpha_engine/backtest_quant_algorithms.py` on main.**

The file has been overwritten with non-Python garbage (`IsADirectoryErrorCHATWITHIT.mdmd atTH..D`). Fix options:
1. `git log --all -- alpha_engine/backtest_quant_algorithms.py` to find the last good commit, then `git checkout <commit>^1 -- alpha_engine/backtest_quant_algorithms.py` and push directly to main.
2. Or restore from the last clean version in git history and open a hotfix PR.

**Sports endpoint smoke + Playwright:** GREEN — 30/30 success in last 30 runs (latest 2026-07-07T13:03Z). No action needed.

**Status change vs 2026-05-22 00:00 UTC (last monitor run):** GREEN → RED. First entry for 2026-07-07 — committing to record verdict change.
