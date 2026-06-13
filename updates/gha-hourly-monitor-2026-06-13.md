# GHA Hourly Health Monitor — 2026-06-13

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** `alpha-engine-live.yml` — 30/30 runs today all `failure` (continuously failing since ≥10:37 UTC; no successes in any of the last 30 runs). Not a cancellation pattern — all conclusive failures with 0 completed jobs returned per run (possible workflow-level config error preventing jobs from registering).

**Failure diagnosis — CI Tests:**

Two distinct failure modes in the most recent run (run_id 27467278522, created 2026-06-13T12:51Z):

1. **AUTHOR_FIX** — `tests/test_wf_verdict_null_block.py`: **92 tests failing** with `AssertionError: assert False is True` on `passes_active_gate()`. The gate is returning `False` for CRYPTO LONG picks that should pass. This is a logic regression, not a flake. Result: `92 failed, 6062 passed, 62 skipped` (exit code 1).

2. **RERUN candidate** — `tests/test_money_ready_verdict.py::test_shadow_mode_stamps_quarantine_fields`: FRED API timeout in `bond_data_fred.py:_fetch_via_fredgraph_csv` (external HTTPS call to fredgraph.fred.stlouisfed.org hit 60s timeout). This fires in the "known-drift" quarantine phase and already suppressed to a `::warning` — not the primary failure driver.

3. **Side issue** — `alpha_engine/backtest_quant_algorithms.py` has **invalid Python syntax at line 1** (coverage parse error in post-step; does not block the test run but indicates a broken file in the repo).

Failing tests (sample):
- `test_wf_verdict_null_block.py::test_viable_passes_with_flag_off`
- `test_wf_verdict_null_block.py::test_viable_passes_with_flag_on`
- `test_wf_verdict_null_block.py::test_strong_passes_with_flag_off`
- `test_wf_verdict_null_block.py::test_strong_passes_with_flag_on`
- `test_wf_verdict_null_block.py::test_marginal_passes_with_flag_off`
- `test_wf_verdict_null_block.py::test_marginal_passes_with_flag_on`
- `test_wf_verdict_null_block.py::test_elite_passes_with_flag_on`
- `test_wf_verdict_null_block.py::test_env_flag_default_is_off`
- … (92 total)

**Other workflows (spot check):**
- `sports-smoke-and-e2e`: GREEN — 30/30 successes, last run 2026-06-13T12:53Z
- `Conflict Marker Check`: GREEN (success)
- `MySQL Trading Picks Sync`: GREEN (success)
- `ML Feedback Retrain`, `ML Forward Test 1745 Models`: GREEN

**Open PRs RED:** No CI status data available via REST endpoint for the 21 open PRs (PRs #563–#598). Manual check of CI Tests required per PR if needed.

**Action required:**
- **AUTHOR_FIX #1 (P0)**: Fix `passes_active_gate()` regression — 92 tests in `tests/test_wf_verdict_null_block.py` fail with `assert False is True`. The gate logic changed and now blocks picks it should pass. Likely introduced by one of the P0/P1 batches merged today (last merge: PR #572 "feat(p1): intrabar sym×dir FWD WR, FOREX F1 gate, progress tracker", merged 2026-06-13T05:53Z). Suspect the M-038 FOREX F1 gate (PR #572) or intrabar sizing gate (PR #580) inadvertently affected CRYPTO gate logic.
- **AUTHOR_FIX #2**: Fix or quarantine `alpha_engine/backtest_quant_algorithms.py` — invalid Python syntax at line 1 is preventing coverage parsing.
- **INVESTIGATE**: `alpha-engine-live.yml` sustained failure loop — 30 consecutive failures today with 0 jobs completing. Likely a workflow-level error (bad secret, missing env var, or yml syntax introduced recently). Operator should inspect the workflow run page directly.
- **INFO**: FRED network timeout in `test_shadow_mode_stamps_quarantine_fields` is a known-drift item (external API unreliable in CI). Already suppressed to warning — no action unless it starts blocking the main suite.

**Run details:**
- CI Tests failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27467278522
- Most recently merged PR: #572 (merged 2026-06-13T05:53Z)
- CI has been RED continuously since at least 06:31 UTC (5 consecutive failures spanning ~6.5 hours)
