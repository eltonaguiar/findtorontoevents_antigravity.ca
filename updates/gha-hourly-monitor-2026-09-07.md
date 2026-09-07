# GHA Hourly Health Monitor — 2026-09-07

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> Last CI Tests run on main: 2026-08-31T02:20Z (run #2249, attempt 7).
> No new CI-triggering pushes to main since then — all recent main commits are `[skip ci]` automated scheduler commits.

**Chronic workflows:** none detected (per-workflow scan skipped — main RED is the blocking signal)

**Open PRs RED:**
- PR #665 (`fix/ci-tests-drift-reconciliation`) — branch has no CI check rollup visible yet; this PR appears to be the active fix attempt for the test failures below.
- PRs #666, #667 — CI status unknown (no status check rollup in open PR list).

**Failing tests (run #2249 — 2026-08-31T02:20Z):**
- `tests/test_phase1_active_gates.py::Phase1TimeOfDayGateTests::*` — 7 failures; `AssertionError: False is not true` (gate logic regression)
- `tests/test_phase1_active_gates.py::Phase1CombinedTests::*` — 2 failures; same error
- `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` — `assert 100.5 == 106.25` (COMMODITY TP/SL policy mismatch)
- 14 additional failures (counted in total: **24 failed**, 6210 passed, 61 skipped)
- Secondary: `alpha_engine/backtest_quant_algorithms.py` line 1 — **invalid syntax** (caught by coverage parser, not pytest gate)

**Likely cause:** AUTHOR_FIX — test logic failures in `alpha_engine` active-gate and TP/SL policy modules. Not infra flake; failures are consistent across 5 consecutive runs (each with 3–7 re-attempts) on both Python 3.11 and 3.12. Pattern matches code regression rather than environment issue.

**Action required:**
- Author should fix `tests/test_phase1_active_gates.py` regression (Phase1TimeOfDayGateTests — gates returning False when True expected)
- Author should fix `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` (COMMODITY TP/SL default mismatch: got 100.5, expected 106.25)
- Author should fix syntax error in `alpha_engine/backtest_quant_algorithms.py` line 1
- PR #665 (`fix/ci-tests-drift-reconciliation`) is the likely active fix branch — verify it addresses all 24 failures before merging

**Run links:**
- Latest failure: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33339421177 (2026-08-31T02:20Z)
- Previous failures: runs 33335405566 / 33332081242 / 33328677219 / 33324694550 (all 2026-08-30)
