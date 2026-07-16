# GHA Hourly Health Monitor — 2026-07-16

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 on main):** 0 success, 30 failure, 0 in_progress
*(CI Tests runs on a schedule on main AND on PR pushes; it does not appear in general main-branch run listing, queried via ci-tests.yml directly)*

**Failure duration:** Continuous since at least **2026-07-15T05:50Z** — 30+ consecutive failures spanning ~31 hours.

**Latest failing run:** [#29497031018](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29497031018) — 2026-07-16T12:08Z (run_attempt 2, still failed)

**Failing tests (24 total — AUTHOR_FIX, no infra/network indicators):**

```
FAILED tests/test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist
       AssertionError: 'kimi_signal_tracking' not found in current blacklist
FAILED tests/test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source
       AssertionError: False is not true (baseline fixture fails — kimi not in list)
FAILED tests/test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n
       AssertionError: top-2 leaked: {'kimi_signal_tracking', 'legit_a'} (kimi_signal_tracking not gated)
FAILED tests/test_phase1_active_gates.py::Phase1DeadZoneGateTests::* (8 tests)
       All "AssertionError: False is not true" — dead-zone gate returning wrong values
FAILED tests/test_phase1_active_gates.py::Phase1TimeOfDayGateTests::* (10 tests)
       All "AssertionError: False is not true" — time-of-day gate returning wrong values
FAILED tests/test_phase1_active_gates.py::Phase1CombinedTests::* (2 tests)
       All "AssertionError: False is not true"
FAILED tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity
       assert 100.5 == 106.25 (commodity TP/SL default value mismatch)
```

Full summary: **24 failed, 6210 passed, 61 skipped, 85 deselected, 2 xfailed** in 151.59s

**Root cause groups:**
1. **Blacklist regression**: `kimi_signal_tracking` was removed from the active blacklist but 3 tests still assert it must be blocked. Fix: add `kimi_signal_tracking` back to the blacklist OR quarantine these tests as known-drift.
2. **Phase1 active gates regression (20 tests)**: Both `Phase1DeadZoneGate` and `Phase1TimeOfDayGate` return wrong boolean values in every test. Likely a production code change to `alpha_engine/passes_active_gate.py` or equivalent broke the gate logic.
3. **TPSL commodity mismatch**: Commodity optimal TP/SL changed from 106.25 to 100.5 — either a policy file was updated without updating the test, or vice versa.
4. **Non-gating secondary issue**: `alpha_engine/backtest_quant_algorithms.py` has invalid Python syntax at line 1 (breaks coverage parse in the post-test step; does NOT directly cause the gating failure but is a production file problem that should be fixed).

**Chronic workflows:** none detected
*(sports-smoke-and-e2e: 29 success / 1 cancelled in last 30 runs — isolated cancel on 2026-07-15, NOT chronic)*

**Open PRs RED (CI Tests failure):**
- **#667** (feat/b5-forward-track-cell-selector) — test (3.11) + test (3.12) FAILURE — AUTHOR_FIX — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/667
- **#666** (fix/resolver/B1-backfill-price-guard) — test (3.11) + test (3.12) FAILURE — AUTHOR_FIX — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/666
- **#665** (audit/stalled-producer-detector) — test (3.11) + test (3.12) FAILURE — AUTHOR_FIX — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/665
- **#600** (feat/edge/money-ready-hunt) — test (3.11) + test (3.12) FAILURE — AUTHOR_FIX — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/600
- **#657** — [skip ci] in commit message, no CI runs to assess

**Action required:** Author (eltonaguiar) must fix main. Three independent fixes needed:
1. Add `kimi_signal_tracking` to the blacklist OR quarantine the 3 blacklist tests
2. Investigate `alpha_engine/passes_active_gate.py` (or phase1 gates module) — 20 gate tests all returning `False` where `True` expected; likely a logic inversion or import error in the gate function
3. Update the commodity TP/SL default in either the policy or the test to agree on the correct value (100.5 vs 106.25)
4. Fix `alpha_engine/backtest_quant_algorithms.py` invalid syntax at line 1 (likely a binary or conflict-marker file)

All open PRs are blocked behind the same main branch issues; they cannot pass CI until main is green.
