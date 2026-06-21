# GHA Hourly Health Monitor — 2026-06-21

## 13:09 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 4 success, 1 failure, 0 in_progress

| Run | Conclusion | Time (UTC) |
|-----|------------|------------|
| 27903792180 | ✅ success | 12:06 |
| 27901003715 | ✅ success | 10:08 |
| 27898999316 | ✅ success | 08:42 |
| 27897924638 | ✅ success | 07:56 |
| 27897497292 | ❌ **FAILURE** | 07:38 |

**Failure detail (run 27897497292):** Step "Run all tests (gating — known-drift quarantined)" failed on both Python 3.11 (job 82551639047) and 3.12 (job 82551639065). Log excerpt:
```
Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1
```
This caused pytest collection to abort. Failing run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27897497292

**Background:** CI had 6 consecutive failures on main from ~04:06 to 07:38 UTC (runs 27893027312 → 27897497292), all with the same root cause — a Python syntax error committed to `alpha_engine/backtest_quant_algorithms.py`. Fixed by the 07:56 commit; 4 consecutive passes since. CI is **recovering** but technically RED by last-5 rule.

**Chronic workflows:** none

Workflows scanned per-workflow (FIXED methodology, ≥15-run window):

| Workflow | Last 15 conclusions | Chronic? |
|----------|--------------------|---------:|
| Sports endpoint smoke + Playwright | 15/15 success | No |
| Audit Hourly Update | 15/15 success | No |
| ALPHA ENGINE - Live Autonomous Scanner | success × 4 (latest), cancelled × 2, failure × 8+ (earlier today) | No — latest completed = success |

Note: Alpha Engine Live had a significant failure run (~00:57–04:15 UTC, at least 8 consecutive failures) before recovering at 04:16 UTC. Not chronic by definition (latest run is success, successes exist in last 48h) but the overnight failure pattern is worth awareness.

**Open PRs RED:**

| PR | Branch | CI Status | Cause | Action |
|----|--------|-----------|-------|--------|
| [#622](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/622) | feat/honest-kill-switch-per-class-thresholds | ❌ FAILURE (both CI runs at 04:05 and 04:24 UTC) | Same `invalid syntax` in `backtest_quant_algorithms.py` (hit during the failure window) | AUTHOR_FIX — rebase on current main to inherit the syntax fix |
| #600, #595, #581, #564, #562 | various (9+ days old) | not recently triggered | n/a | no action |

**Most recently merged PR:** [#636](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/636) — `chore(ci): dedup CRYPTO_RSI5070_SHADOW_ENABLE` merged at 08:34 UTC (after the failure window; not the cause).

**Action required:** Author should rebase PR #622 onto current main (`git rebase origin/main`) so CI picks up the syntax fix that landed at 07:56 UTC. No production code changes needed.
