# GHA Hourly Health Monitor — 2026-06-24

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failing test:** `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity`
```
assert 100.5 == 106.25
```
→ Commodity TP/SL policy default drifted. `get_optimal_tp_sl()` returns `tp=100.5` but test expects `tp=106.25`.

**Consecutive failures:** 14 runs (since 2026-06-23T18:48 UTC, SHA `3da55766`). Last green: 2026-06-23T17:44 UTC (SHA `3466e97b`).
**Failure classification:** AUTHOR_FIX — real test assertion, consistent across all 14 runs, both Python 3.11 and 3.12 matrix jobs.
**Run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28096691956

**Secondary note:** `alpha_engine/backtest_quant_algorithms.py` has invalid syntax at line 1 (coverage parse warning — not the test failure cause but warrants a look).

**Chronic workflows:** none (0 cancellations observed in 100-run main-branch sample; 30 active workflows showing success or in_progress)

**Sports endpoint smoke + Playwright:** GREEN (30/30 successes in last 30 runs, latest 2026-06-24T13:04 UTC)

**Open PRs with CI Tests RED:** All 7 open PRs (#665, #657, #622, #600, #595, #581, #564, #562) are blocked by the same main regression. PR #665 (branch: `fix/ci-tests-drift-reconciliation`) is the most recent and may already be targeting this issue.

**Action required:** Author should fix `tests/test_tpsl_policy.py:25` — update the expected value from `106.25` to `100.5` (or fix the commodity TP policy code if `100.5` is wrong). PR #665 should be checked — its branch name matches but its PR body describes a different feature (stalled-producer-detector).
