# GHA Hourly Health Monitor — 2026-07-21

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failing run:** [29829552398](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29829552398) — 2026-07-21T12:18:26Z (most recent completed)

**Duration of RED:** All 30 sampled completed runs on main are `failure`, spanning 2026-07-20T16:04Z → 2026-07-21T12:18Z (≥ 20 hours continuous failures).

**Failing tests (24 failed, 6210 passed, 61 skipped — Python 3.11 + 3.12 both affected):**

| Test file | Failures | Root cause |
|---|---|---|
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` not in blacklist (`BLOCKED_SOURCE_SYSTEMS`) — missing entry |
| `tests/test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaking into top-N ranking — same missing blacklist entry |
| `tests/test_phase1_active_gates.py` | 20 | `Phase1DeadZoneGateTests` + `Phase1TimeOfDayGateTests` + `Phase1CombinedTests` all return `False is not true` — Phase 1 gate function broken or never wired |
| `tests/test_tpsl_policy.py` | 1 | `test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` → `assert 100.5 == 106.25` (commodity TP/SL default mismatch) |

**Coverage note:** `alpha_engine/backtest_quant_algorithms.py` has `invalid syntax` at line 1 (flagged in coverage step — not the pytest failure cause, but a separate bug).

**Chronic workflows:** none — Claude Gainer ML Live Scanner: 30/30 success (last 30 runs). No chronic cancellation pattern detected via per-workflow query.

**Open PRs RED:** 7 open PRs (#667, #666, #665, #657, #600, #595, #581, #564) — all share `base.sha = 69c8ff54ec74c1bc80c020ad46a5ae63bb262cac`. CI Tests will fail on any of these that touch `alpha_engine/**`, `paper_trading/**`, or `tests/**` paths due to the 24 gating test failures. PR-level CI status not individually fetched (statusCheckRollup unavailable via list endpoint); failure root cause is the same 24 failures on main HEAD.

**Action required:** AUTHOR_FIX — the 4 root causes must be fixed on main:
1. **CRITICAL**: Add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS` in `alpha_engine/emitter_discipline.py` (or equivalent blacklist constant) — 3 tests failing
2. **CRITICAL**: Fix `Phase1DeadZoneGate` and `Phase1TimeOfDayGate` functions — all 20 `test_phase1_active_gates.py` tests return `False is not true`, suggesting these gate functions were removed or renamed after the tests were written
3. **LOW**: Fix TPSL commodity default — `test_tpsl_policy.py` expects `106.25` but got `100.5`
4. **LOW**: Fix syntax error in `alpha_engine/backtest_quant_algorithms.py` line 1

**Status change vs previous baseline (2026-05-22 — GREEN):** GREEN → RED. First detection. This is a new daily file; no prior 2026-07-21 entry exists.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29829552398
