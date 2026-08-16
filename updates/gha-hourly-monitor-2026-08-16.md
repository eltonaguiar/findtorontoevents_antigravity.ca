# GHA Hourly Health Monitor — 2026-08-16

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 scanned):** 0 success, 30 failure, 0 in_progress

> NOTE: CI Tests last ran on main on 2026-08-11 (5 days ago, run_attempt=8). No new pushes to main since then — the red state is stale but persistent.

**Failing jobs:** `test (3.11)` and `test (3.12)` — both fail at step 8 "Run all tests (gating — known-drift quarantined)".

**Failing tests (24 total, identical on 3.11 and 3.12):**

| Test file | Count | Root cause |
|---|---|---|
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` missing from `BLOCKED_SOURCE_SYSTEMS` (intake blacklist) |
| `tests/test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaks into top-N ranking (same missing-blacklist root) |
| `tests/test_phase1_active_gates.py` | 20 | All `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests` return `False` where `True` expected — likely gate function signature/return-value drift |
| `tests/test_tpsl_policy.py` | 1 | Commodity TP/SL policy default mismatch: got `100.5`, expected `106.25` |

**Latest failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985

**Chronic workflows:** none — `ALPHA ENGINE - Live Autonomous Scanner` (30/30 success, last run 2026-08-16T12:08Z) and `sports-smoke-and-e2e` (30/30 success, last run 2026-08-16T12:25Z) are healthy.

**Open PRs:** 9 open PRs. CI status from latest scanned runs:

| PR | Branch | CI Tests status |
|---|---|---|
| #665 | fix/ci-tests-drift-reconciliation | FAILURE (latest commit 2026-06-24; earlier commit passed) |
| #667, #666, #657, #600, #595, #581, #564, #562 | various | No CI Tests runs found in scanned history |

**Context on PR #665:** An earlier commit on this branch (`764b656b`) passed CI (fixing 107 drift failures). The latest commit (`1cc7c8ea`, 2026-06-24) introduced 24 new failures — the 3 test files above. The PR is currently in FAILURE state and needs an author fix before merging.

**Action required:** AUTHOR_FIX — three distinct failures need code fixes in production:

1. **Blacklist gap:** Add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS` (or equivalent blacklist list in the production config/constants file). Fixes 3 test failures.
2. **Phase1 gates regression:** `test_phase1_active_gates.py` — all 20 tests return `False is not true`; the gate functions (`check_dead_zone`, `check_time_of_day`, combined) appear to be returning `False` unconditionally or have wrong signatures. Likely caused by a recent refactor that changed the return type or gate-enable logic. Check the Phase1 gate module for a recent boolean inversion or early-return bug.
3. **TP/SL commodity default:** `test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` expects `106.25` but gets `100.5`. A policy constant was changed without updating the test, or vice versa.

All three are **AUTHOR_FIX** (not flake). No rerun will help.
