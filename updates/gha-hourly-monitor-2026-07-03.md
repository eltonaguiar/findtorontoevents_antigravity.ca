# GHA Hourly Health Monitor — 2026-07-03

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30):** 0 success, 30 failure, 0 in_progress
*(30/30 consecutive failures spanning 2026-07-01 23:11Z → 2026-07-03 12:59Z — at least 38 hours continuous)*

**Chronic workflows:** none
- Sports endpoint smoke + Playwright: 30/30 success (last 30 runs, ~hourly) ✅
- Unified Audit Dashboard: 28/30 success (2 still queued/in-progress at snapshot time) ✅

**Open PRs RED:** none of the 8 open PRs have a failing CI Tests check (PRs #667, #666, #665, #657, #600, #595, #581, #564 are feature/docs branches; CI tests only gate main)

**Failing tests (run 28662172247 — 2026-07-03 12:59Z, both Python 3.11 and 3.12):**

Result: `23 failed, 6211 passed, 61 skipped, 85 deselected, 2 xfailed in 158.56s`

*Group 1 — kimi_signal_tracking blacklist (3 tests, AUTHOR_FIX):*
- `test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist`
  — `kimi_signal_tracking` not in BLOCKED_SOURCE_SYSTEMS list
- `test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source`
  — baseline fixture fails (kimi not blocked → positive test precondition broken)
- `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n`
  — `kimi_signal_tracking` leaked into top-2 ranking

*Group 2 — Phase1 active gates returning False for all picks (20 tests, AUTHOR_FIX):*
- ALL `Phase1DeadZoneGateTests` (8 tests) — gate blocks picks it should pass
- ALL `Phase1TimeOfDayGateTests` (9 tests) — gate blocks all hours including safe hours
- ALL `Phase1CombinedTests` (3 tests) — gate blocks even when both gates disabled

Both groups affect production gating logic:
- Phase1 gate regression likely means `passes_active_gate()` now rejects ALL picks (live scanner impact)
- `kimi_signal_tracking` not in blacklist means a blocked source may be emitting picks

**Likely cause:** A commit merged to main on or around 2026-07-01 23:00Z modified either:
1. `alpha_engine/passes_active_gate.py` or phase1 gate module (breaking `passes_active_gate()` to always return False)
2. `alpha_engine/emitter_discipline.py::BLOCKED_SOURCE_SYSTEMS` (removed `kimi_signal_tracking`)

**Action required:**
- AUTHOR_FIX: Investigate commits on main since 2026-07-01 22:00Z for changes to `passes_active_gate`, phase1 gate modules, or `BLOCKED_SOURCE_SYSTEMS`
- URGENT: If Phase1 gates are returning False for all picks, the live scanner is blocking all pick emissions — check live pick count
- Fix: Add `kimi_signal_tracking` back to `BLOCKED_SOURCE_SYSTEMS` if it was accidentally removed
- Fix: Restore `passes_active_gate()` to return True for picks that should pass gates

**Run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28662172247
