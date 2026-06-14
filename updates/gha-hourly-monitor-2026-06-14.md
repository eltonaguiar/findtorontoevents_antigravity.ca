# GHA Hourly Health Monitor — 2026-06-14

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

*(Note: one run (id=27499425286) was in_progress at scan time; all 29 completed runs in the last 30 are failures.)*

**Chronic workflows:** none detected in per-workflow scan (CI Tests is the critical failure; general 30-run sample shows 0 cancellations)

**Open PRs RED:** 23 open PRs — all will fail CI Tests until the syntax error in `alpha_engine/backtest_quant_algorithms.py` is fixed on main. Known fix PRs:
- **#601** (`fix/wf-verdict-crypto-block-fixtures`) — fixes ~20 of 91 test failures in `test_wf_verdict_*`
- **#599** (`fix/passes-active-gate-fixture`) — fixes `tests/test_stamp_feed_membership.py` (M-036 + CRYPTO_PRODUCTION_BLOCK_LONG fixture)
- Neither PR addresses the **root blocker**: `alpha_engine/backtest_quant_algorithms.py` invalid syntax at line 1

**Root cause:** `alpha_engine/backtest_quant_algorithms.py` — `invalid syntax` at line 1 (Python 3.11 and 3.12 both fail on parse). Both CI jobs (`test (3.11)` and `test (3.12)`) crash at the `py_compile` / import stage before any test logic runs. CI has been RED continuously since **2026-06-13T05:33Z** (29+ consecutive failures across ~30 hours). Coincides exactly with merge of PR #588 at 2026-06-13T05:33:17Z ("feat(pro-level batch2): luxalgo fallback, gap-fade replay, tribunal UI + batch1").

**Failure run IDs (5 most recent completed):**
- 27498058640 — 2026-06-14T11:56Z
- 27495583152 — 2026-06-14T10:10Z
- 27493342421 — 2026-06-14T08:32Z
- 27490717501 — 2026-06-14T06:30Z
- 27487945974 — 2026-06-14T04:10Z

**Failing CI run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27498058640

**Action required:** AUTHOR FIX — fix invalid syntax in `alpha_engine/backtest_quant_algorithms.py` (line 1). This is not infra flake. PRs #599 and #601 address test fixture issues but do NOT fix the underlying syntax error that is blocking all CI runs. Someone needs to either:
1. Fix `alpha_engine/backtest_quant_algorithms.py` so it is valid Python, OR
2. Identify if PR #588 introduced a merge artifact / conflict marker at line 1 of that file and revert it
