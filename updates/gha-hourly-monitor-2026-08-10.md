# GHA Hourly Health Monitor — 2026-08-10

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> CI Tests has been failing on main continuously for at least 37 hours (30 consecutive failures
> visible, run IDs 31283785788 through 31386600301, from 2026-08-08 23:21Z to 2026-08-10 12:08Z).
> Previous monitor verdict (last run 2026-05-22): GREEN. **This is a GREEN → RED status change.**

**Failing run:** [31386600301](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31386600301) — 2026-08-10 12:08Z

**Test summary:** 23 failed, 6211 passed, 61 skipped in 200.50s (Python 3.11 + 3.12 both RED)

**Failing tests — Group 1 (AUTHOR_FIX — blacklist missing `kimi_signal_tracking`):**
- `tests/test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist`
  — `kimi_signal_tracking` not found in `BLOCKED_SOURCE_SYSTEMS`
- `tests/test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source`
  — baseline fixture fails; negative test is meaningless
- `tests/test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n`
  — `kimi_signal_tracking` leaks into top-2 leaderboard result

**Failing tests — Group 2 (AUTHOR_FIX — 20 Phase1 active gate tests all return `False is not true`):**
- `tests/test_phase1_active_gates.py::Phase1DeadZoneGateTests` — 8 tests
- `tests/test_phase1_active_gates.py::Phase1TimeOfDayGateTests` — 10 tests
- `tests/test_phase1_active_gates.py::Phase1CombinedTests` — 2 tests
- Root cause: `passes_active_gate` returns `False` for all inputs (likely a module-level import
  error or flag default that broke the gate)

**Chronic workflows:** none
- `robust-edge-miner`: 30/30 failures in last 30 runs, but this is an **intentional fail-LOUD
  design** — step 7 "Alert if a ROBUST candidate appeared (fail-LOUD = good news, review now)"
  triggered. Run 31390932327 at 13:03Z today confirms a robust edge candidate was found.
  Zero cancellations; does not meet chronic-cancellation criteria.

**Open PRs RED:** (CI status rollup not fetched; 9 open PRs as of 13:00Z)
- PRs #667, #666, #665, #657, #600, #595, #581, #564, #562 are open.
- Any PR that runs CI Tests will fail on the same 23 tests until main is fixed.

**Action required:**
1. **Author must fix #1 — add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS`** in
   `alpha_engine/` (likely `active_gates.py` or `smart_gate_config.py`). Tests are in
   `tests/test_blacklist_exec_gate_enforcement.py` + `test_blacklist_leaderboard_filter.py`.
2. **Author must fix #2 — diagnose `passes_active_gate` returning False** for all Phase1
   DeadZone + TimeOfDay gate tests. Check `alpha_engine/active_gates.py` or the
   Phase1 gate module for a broken default flag or import error. 23 tests failing on
   both Python 3.11 and 3.12 suggests a logic/config regression, not an env issue.
3. **Investigate whether robust-edge-miner candidate is actionable** — the fail-loud
   alert fired at 13:03Z today. Inspect the uploaded scan artifact from run 31390932327.

---
