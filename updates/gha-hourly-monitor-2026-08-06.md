# GHA Hourly Health Monitor — 2026-08-06

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failing since:** 2026-08-04T22:29Z — continuous RED for ~38+ hours (30/30 consecutive failures in sample)

**Failing tests (run 31100546392, 2026-08-06T12:14Z):** 23 failed, 6211 passed, 61 skipped

```
test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist
  — AssertionError: 'kimi_signal_tracking' not found in BLOCKED_SOURCE_SYSTEMS

test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source
  — AssertionError: False is not true (baseline fixture fails; kimi not blacklisted)

test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n
  — AssertionError: kimi_signal_tracking leaked into top-2

test_phase1_active_gates.py::Phase1DeadZoneGateTests (8 tests) — AssertionError: False is not true
test_phase1_active_gates.py::Phase1TimeOfDayGateTests (10 tests) — AssertionError: False is not true
test_phase1_active_gates.py::Phase1CombinedTests (2 tests) — AssertionError: False is not true
```

Side note: `alpha_engine/backtest_quant_algorithms.py` has `invalid syntax` at line 1 (coverage step warning).

**Failure run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31100546392

**Chronic workflows:** none — all sampled workflows healthy

- `Sports endpoint smoke + Playwright`: 14 success / 1 cancelled in last 15 — NOT chronic (single cancel, 14 successes)
- `actions-failure-guardian`: 15/15 success
- `ALPHA ENGINE - Live Autonomous Scanner`: 14/15 success, 1 in-progress

**Open PRs RED (CI Tests `test` jobs failing):**

| PR | Title | CI Failure | Action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | test (3.11) + (3.12) failure | AUTHOR_FIX |
| #666 | fix(resolver): B1 backfill price guard | test (3.11) + (3.12) failure | AUTHOR_FIX |
| #665 | audit(stalled-producer-detector) v2.0+2 | test (3.11) + (3.12) failure | AUTHOR_FIX |
| #600 | feat(edge): money-ready hunt | test (3.11) + (3.12) failure | AUTHOR_FIX |

PR #657 — no check runs recorded. PR #595, #581, #564, #562 — not checked this pass.

**Root cause analysis:**

Two distinct failure clusters:

1. **`kimi_signal_tracking` not blacklisted (3 tests):** Tests assert `kimi_signal_tracking` is in `BLOCKED_SOURCE_SYSTEMS` / passes the exec gate blacklist, but the source system is absent from the list. A PR that was supposed to add `kimi_signal_tracking` to the blocklist either never merged or was reverted.

2. **Phase1 active gates returning False (20 tests):** `Phase1DeadZoneGateTests` and `Phase1TimeOfDayGateTests` all return `False is not true` — the gate functions are blocking picks that should pass. Likely a regression in `alpha_engine/passes_active_gate` or the Phase1 gate configuration (deadzone thresholds, time-of-day window, or env-flag defaults changed).

**Action required:** Author fix needed on main. Recommend:
- Add `kimi_signal_tracking` to `BLOCKED_SOURCE_SYSTEMS` in the active-gate / blacklist config (or update the tests to match current intent)
- Investigate Phase1 gate function regression — check recent changes to deadzone/time-of-day gate logic in `alpha_engine/`
