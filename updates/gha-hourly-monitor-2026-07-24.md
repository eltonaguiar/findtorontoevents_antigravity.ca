# GHA Hourly Health Monitor — 2026-07-24

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 1 in_progress

Failing run sampled: [run 30091753921](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30091753921) (2026-07-24T12:04Z)

**Failure summary (both Python 3.11 and 3.12 — identical):**
```
24 failed, 6210 passed, 61 skipped in ~130s
```

**Top failing tests (AUTHOR_FIX — real assertion errors, not infra flakes):**
- `tests/test_phase1_active_gates.py::Phase1TimeOfDayGateTests::*` — 7 tests, all `AssertionError: False is not true`
- `tests/test_phase1_active_gates.py::Phase1CombinedTests::*` — 2 tests, all `AssertionError: False is not true`
- `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` — `assert 100.5 == 106.25`

Secondary note: `alpha_engine/backtest_quant_algorithms.py` has `invalid syntax` at line 1 (flagged during coverage step — not a direct test gate but indicates a broken file on main).

All 29 completed CI Tests runs on main today (01:32 UTC → 12:04 UTC) are `failure`. Failure appears persistent across the full day.

**Chronic workflows:** none detected — sports-smoke-and-e2e (15/15 success in last 15 runs, all today). No cancellation pattern in the 30-run sample of other workflows.

**Open PRs RED:**
- PRs #667, #666, #665, #657, #600, #595, #581, #564, #562 are all open against a stale base SHA (`69c8ff54`) from June 2026 — their CI checks pre-date today's failures. No new PR-level CI data available.
- **Classification:** AUTHOR_FIX — the Phase1TimeOfDayGate and tpsl_policy failures are logic regressions on main, not infra flakes.

**Action required:** Author fix needed on main for:
1. `alpha_engine/phase1_active_gates.py` (or equivalent) — Phase1TimeOfDayGateTests expecting `True`, getting `False`; likely a logic inversion or missing import after a recent refactor
2. `alpha_engine/tpsl_policy.py` — commodity TP/SL policy returns `100.5` instead of expected `106.25`
3. `alpha_engine/backtest_quant_algorithms.py` — syntax error at line 1 should be fixed to restore coverage

**Status change vs 2026-05-22 00:00 UTC:** GREEN → RED (first entry for 2026-07-24; no prior monitor entry today). Committing and notifying.
