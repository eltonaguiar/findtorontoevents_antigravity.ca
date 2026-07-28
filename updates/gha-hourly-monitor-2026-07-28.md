# GHA Hourly Health Monitor — 2026-07-28

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress (run in_progress at 12:01Z is attempt 3 of latest, still running)

**Failing tests (23 total — both py3.11 and py3.12, run 30353103762, completed 11:01–11:21Z):**
- `tests/test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist` — `kimi_signal_tracking` no longer found in the live blacklist list (production blacklist changed)
- `tests/test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source` — baseline fixture fails (gate returns False when it should pass)
- `tests/test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n` — `kimi_signal_tracking` leaked into top-2
- `tests/test_phase1_active_gates.py` — **20 failures** across `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests`; all assert `False is not true` — the active-gate function now returns False in every scenario where the test expects True (regression: gate logic inverted or broken)

**Secondary issue:** `alpha_engine/backtest_quant_algorithms.py` has `invalid syntax at line 1` (coverage parse error — not a direct test failure driver but indicates a broken file in `alpha_engine/`).

**Failure streak:** 29 consecutive failures from 2026-07-26T18:58Z through 2026-07-28T11:01Z (~42 hours). Currently in_progress run (id 30357186616) is attempt 3 — repeated manual retries confirm this is not infra flake.

**Failure run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30353103762

**Sports smoke & e2e (last 15):** 14 success, 1 cancelled (2026-07-27T18:46Z), 0 failure — GREEN, running hourly at normal cadence.

**Chronic workflows:** none — no workflow meets the chronic-cancellation threshold (≥4 cancellations in 15 runs, 0 successes, none in 48h).

**Open PRs CI snapshot:** 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562). None of these PRs touch CI-path files (`alpha_engine/**`, `tests/**`, etc.) — they are all feature/research branches that predated the failure streak and did not trigger CI Tests on main. No current PR has an actionable failing CI check that warrants author attention (all open PRs are waiting on operator review, not CI fixes).

**Open PRs RED:** none — the RED verdict is on main itself, not on a specific open PR.

**Action required:** **AUTHOR_FIX required on main.**
1. **Primary (blocker):** Fix `tests/test_phase1_active_gates.py` — 20 gate logic failures. The Phase 1 active-gate functions (`passes_deadzone_gate`, `passes_time_of_day_gate`, `passes_active_gate`) are returning `False` in all test scenarios. Either the gate was accidentally broken by a recent merge to main, or a constant/config threshold was changed. Bisect from ~2026-07-26T18:58Z (first failure) to find the culprit commit.
2. **Secondary (blocker):** Fix the `kimi_signal_tracking` blacklist — 3 tests expect it to be present in the production blacklist but it was removed. Add it back or update the tests to match the new intended blacklist.
3. **Tertiary (non-blocking):** Fix `alpha_engine/backtest_quant_algorithms.py` syntax error at line 1 — breaks coverage parsing. File was last modified in the 2026-05-23 history-cleanup commit; may need to be regenerated or the syntax issue corrected.

**Status change vs 2026-05-22 (last monitor entry):** GREEN → **RED** (status changed). First monitor entry for 2026-07-28. Previous last-confirmed-green run was PR #1292 merged 2026-05-21T19:15Z; CI Tests have been failing continuously since at least 2026-07-26T18:58Z (~42 hours at time of writing).
