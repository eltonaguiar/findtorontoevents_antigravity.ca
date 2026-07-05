# GHA Hourly Health Monitor — 2026-07-05

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last run):** 0 success, 1 failure (run ID 28741315243, sha 2155f73d0c, triggered 12:49 UTC)

**Chronic workflows:** none (0 cancellations in 100-run scan; 25/28 workflows green, 2 in_progress, 1 failure)

**Open PRs RED:** Open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562) not individually re-checked — all are based on pre-2026-07-05 main commits; the CI failure is on the current main HEAD.

**Failing tests — 23 FAILED across 2 test modules (Python 3.11 + 3.12, same failures both):**

| Module | Tests | Classification |
|---|---|---|
| `test_blacklist_exec_gate_enforcement.py` | 2 failures | AUTHOR_FIX |
| `test_blacklist_leaderboard_filter.py` | 1 failure | AUTHOR_FIX |
| `test_phase1_active_gates.py` | 20 failures | AUTHOR_FIX |

**Root causes:**
- `kimi_signal_tracking` is missing from the blacklist (intake + exec gate both fail to find it)
- `test_phase1_active_gates` — `passes_active_gate()` returns `False` across all DeadZone and TimeOfDay gate tests; gate function is broken or the test fixture assumptions changed
- Additional coverage note: `alpha_engine/backtest_quant_algorithms.py` has an invalid syntax at line 1 (non-blocking, caught by coverage step only)

**Run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28741315243

**Action required:** Author fix on main — add `kimi_signal_tracking` to the production blacklist and investigate `passes_active_gate()` regression (likely a signature/import change since last green run).
