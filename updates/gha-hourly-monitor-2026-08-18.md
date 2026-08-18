# GHA Hourly Health Monitor — 2026-08-18

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Status note:** CI Tests has not been triggered on main since 2026-08-11T21:16Z (7 days ago). All recent main commits (active since 2026-08-11) are `[skip ci]` bot pushes (live-monitor, gainer-capture, alpha-engine, prediction-updates). The last code-triggering push caused failures that persist across 30+ consecutive runs (all failure, no success).

**Last CI Tests run:** 2026-08-11T21:16Z — run ID 31537099985 — FAILED (both `test(3.11)` and `test(3.12)`)  
**Run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985

**Failing tests (AUTHOR_FIX — real assertion errors, not infra flake):**

| Test | Failure |
|------|---------|
| `tests/test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n` | `kimi_signal_tracking` leaking into top-N (not filtered by blacklist) |
| `tests/test_blacklist_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source` | baseline fixture fails — `passes_active_gate` returning False when it should return True |
| `tests/test_phase1_active_gates.py::Phase1DeadZoneGateTests` (7 tests) | `AssertionError: False is not true` — gate returning False on expected-pass inputs |
| `tests/test_phase1_active_gates.py::Phase1TimeOfDayGateTests` (9 tests) | `AssertionError: False is not true` — gate returning False on expected-pass inputs |
| `tests/test_phase1_active_gates.py::Phase1CombinedTests` (2 tests) | `AssertionError: False is not true` |
| `tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` | `assert 100.5 == 106.25` — TP/SL commodity policy defaults mismatch |
| `tests/test_audit_metric_invariants.py::test_headline_total_pnl_is_the_compounded_value` | `ERROR: found no collectors` — import or collection error |
| `tests/test_confidence_calibrator.py::CalibratorContractTests::test_no_op_when_flag_unset` | `ERROR: not found` — collector failure |

**Root cause cluster:** `passes_active_gate` is the common denominator. Phase-1 gate failures across DeadZone, TimeOfDay, and Combined tests all report `False is not true` — likely a regression in `alpha_engine/active_gates.py` where `passes_active_gate` was tightened and now rejects inputs that should pass. The blacklist baseline fixture failing independently suggests `kimi_signal_tracking` is no longer in the blacklist or the filter path is broken.

**Chronic workflows:** Not fully scanned (362 workflows — scope limited by API response size). No immediately visible chronic pattern from the last 100-run sample; all recent bot workflows show `success` conclusions.

**Open PRs RED (CI status not retrieved — statusCheckRollup not queried this run):**

Open PRs as of 13:00 UTC: #667, #666, #665, #657, #600, #595, #581, #564, #562

**Action required:** AUTHOR/OPERATOR should fix `alpha_engine/active_gates.py` — `passes_active_gate` regression blocking all Phase-1 gate tests. Also fix blacklist filter path (kimi_signal_tracking leak) and TP/SL commodity policy defaults. CI Tests has been red for 7+ days on main.

**Status change vs last monitor (2026-05-22 06:00 UTC):** GREEN → RED — committing and pushing.
