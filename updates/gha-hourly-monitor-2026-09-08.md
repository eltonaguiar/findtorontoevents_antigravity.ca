# GHA Hourly Health Monitor — 2026-09-08

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** none

**Open PRs RED:** (CI status not fetched — main CI Tests workflow `ci-tests.yml` last ran 2026-08-30, 9 days stale; no pushes to main since then detected in recent run window)

**Failure detail (run #2249, 2026-08-30T22:32Z, 7 attempts):**
- Run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33339421177
- Jobs: `test (3.11)` FAILED, `test (3.12)` FAILED
- Failing step: "Run all tests (gating — known-drift quarantined)"
- **24 failed, 6210 passed, 61 skipped** (2:55 run time)

**Failing tests (AUTHOR_FIX — real assertion failures):**

| # | Test | Failure |
|---|------|---------|
| 1–3 | `test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist` + 2 others | `kimi_signal_tracking` not in blacklist registry; gate not rejecting kimi source |
| 4–22 | `test_phase1_active_gates.py::Phase1DeadZoneGateTests::*` (8) + `Phase1TimeOfDayGateTests::*` (9) + `Phase1CombinedTests::*` (2) | All `AssertionError: False is not true` — `passes_active_gate` returning False when True expected; broad Phase1 gate regression |
| 23 | `test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` | `assert 100.5 == 106.25` — commodity TP/SL default mismatch |

**Root cause assessment (AUTHOR_FIX):**
1. **Phase1 gates (19/24 failures):** `passes_active_gate` or the dead-zone/time-of-day gate helpers broke — likely a gate was removed, renamed, or threshold inverted in a recent commit. Baseline fixtures that "should pass" return False, meaning the gate now blocks everything. High-priority fix.
2. **Blacklist (3/24):** `kimi_signal_tracking` is not present in the intake blacklist (`BLOCKED_SOURCE_SYSTEMS` or equivalent registry). Either it was never added or was accidentally removed.
3. **TP/SL policy (1/24):** Commodity default TP/SL changed — expected 106.25 but got 100.5.

**Note on staleness:** CI Tests has not run on main since 2026-08-30 (9 days). The last successful CI run predates this period — no GREEN runs in the last 5. This appears to be a persistent regression, not a fresh break.

**Chronic workflow scan (100-run sample):** No workflows meet the CHRONIC threshold (≥4 cancels, 0 successes, latest=cancelled). Only 1 cancellation seen: `ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds` (1 cancel / 1 success — not chronic).

**Action required:** Author should fix `test_phase1_active_gates` regression (broadest blast radius — 19 failures), `kimi_signal_tracking` blacklist registration (3 failures), and commodity TP/SL default in `test_tpsl_policy` (1 failure).
