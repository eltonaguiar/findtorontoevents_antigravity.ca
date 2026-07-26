# GHA Hourly Health Monitor — 2026-07-26

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 30 most-recent CI Tests runs on `main` (covering 2026-07-26 02:31–12:52 UTC) are `failure`. CI has been continuously failing all day with no successful run in the visible window. The workflow appears to run hourly (scheduled). Most recent failing run: [30202918096](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30202918096) (2026-07-26T12:52Z, both `test (3.11)` and `test (3.12)` failed, 23 failed / 6211 passed / 61 skipped).

**Chronic workflows:** none detected in sampled window (0 cancellations across 30 most-recent cross-workflow runs; no workflow meets the chronic-cancel threshold).

**Open PRs RED:** 9 open PRs exist (#667, #666, #665, #657, #600, #595, #581, #564, #562 — all opened June 2026, predating the CI breakage). No statusCheckRollup data available for these PRs via the current API scope. All open PRs target `main`; given main CI is continuously failing, any PR that triggers CI Tests will also fail.

**Action required:** AUTHOR_FIX — main is RED. 23 tests failing across 3 test files. All failures are real assertion errors (not infra flake). Root causes:

### Failing tests (23 total, both py3.11 and py3.12)

**`tests/test_blacklist_exec_gate_enforcement.py` (2 tests)**
- `test_kimi_in_intake_blacklist` — `kimi_signal_tracking` not found in intake blacklist source list
- `test_passes_active_gate_rejects_kimi_source` — baseline fixture fails (`passes_active_gate` baseline broken)

**`tests/test_blacklist_leaderboard_filter.py` (1 test)**
- `test_ranking_excludes_blacklisted_from_top_n` — `kimi_signal_tracking` leaked into top-2 ranking (blacklist not enforced)

**`tests/test_phase1_active_gates.py` (20 tests)**
- `Phase1DeadZoneGateTests` (8 tests) — all return `False is not true` on positive/pass cases
- `Phase1TimeOfDayGateTests` (10 tests) — all return `False is not true` on positive/pass cases
- `Phase1CombinedTests` (2 tests) — both `False is not true`

**Likely root cause:** A code change to `alpha_engine/passes_active_gate.py` or the Phase1 gate implementation (dead-zone + time-of-day) broke the gate logic so that positive cases universally return `False`. Also, `kimi_signal_tracking` is missing from the intake blacklist registration. This is consistent with a single refactor commit that touched the gate and blacklist systems simultaneously.

**Recommended operator action:** `git log --oneline alpha_engine/passes_active_gate.py tests/test_phase1_active_gates.py` to identify the breaking commit, revert or patch the gate logic, add `kimi_signal_tracking` to the intake blacklist source registration.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30202918096

**Status change vs last known state:** Last recorded verdict was GREEN (2026-05-22 00:00 UTC, run by previous monitor session). Current verdict is RED — significant regression since May.
