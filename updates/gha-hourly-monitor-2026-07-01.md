# GHA Hourly Health Monitor — 2026-07-01

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

| Run ID | Created (UTC) | SHA | Conclusion |
|---|---|---|---|
| [28516151265](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28516151265) | 2026-07-01 12:04 | 5c9f530 | ❌ failure |
| [28509780172](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28509780172) | 2026-07-01 10:06 | 858e36c | ❌ failure |
| [28504670591](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28504670591) | 2026-07-01 08:36 | 5737a99 | ❌ failure |
| [28498347225](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28498347225) | 2026-07-01 06:31 | c542bf8 | ❌ failure |
| [28492941329](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28492941329) | 2026-07-01 04:11 | f7f3e83 | ❌ failure |

**Failure duration:** Continuous failure across all 30 sampled runs back to ≥ 2026-06-29T16:06 UTC — at least **44+ hours** of unbroken RED.

**Failing tests (24 total — AUTHOR_FIX, real logic regression):**

Three distinct clusters:

1. **Blacklist / kimi_signal_tracking removed (3 tests)**
   - `test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist`
     — `'kimi_signal_tracking'` not found in blacklist array (absent from `BLOCKED_SOURCE_SYSTEMS`)
   - `test_blacklist_exec_gate_enforcement.py::BlacklistExecGateTests::test_passes_active_gate_rejects_kimi_source`
     — baseline fixture fails (`False is not true`); gate is no longer rejecting kimi source
   - `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n`
     — `kimi_signal_tracking` leaking into top-N leaderboard ranking

2. **Phase 1 gates completely broken (19 tests)**
   - All tests in `test_phase1_active_gates.py` failing: `Phase1DeadZoneGateTests` (8 tests),
     `Phase1TimeOfDayGateTests` (9 tests), `Phase1CombinedTests` (2 tests)
   - All fail with `AssertionError: False is not true` — gate functions returning `False` where
     `True` is expected, indicating the gate logic has been inverted or the gate import/wiring is broken

3. **COMMODITY TP/SL policy wrong value (1 test)**
   - `test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity`
     — `assert 100.5 == 106.25` (actual TP returned 100.5, expected 106.25)

**Coverage side-note:** `alpha_engine/backtest_quant_algorithms.py` has an `invalid syntax at line 1`
(coverage parse warning — likely a merge conflict marker or truncated file).

**Chronic workflows:** none detected (sports-smoke-and-e2e: 30/30 success; all sampled workflows clean)

**Sports smoke (sports-smoke-and-e2e):** ✅ GREEN — 30/30 consecutive successes,
most recent at 2026-07-01T11:24 UTC

**Open PRs with failing CI Tests:**

| PR | Title | Failing checks | Classification |
|---|---|---|---|
| [#667](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/667) | feat(b5): forward-track cell selector | test(3.11) ❌, test(3.12) ❌ | AUTHOR_FIX — inherits main breakage |
| [#666](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/666) | fix(resolver): B1 backfill price guard at resolution-write | test(3.11) ❌, test(3.12) ❌ | AUTHOR_FIX — inherits main breakage |

Note: All other open PRs (#665, #657, #600, #595, #581, #564, #562) were opened before the test
failure onset and/or predate this monitoring window; their CI status was not re-checked this run.

**Action required:** OPERATOR must fix 24 failing tests before any PR can merge cleanly.

Root causes to investigate (in priority order):
1. `alpha_engine/blacklist_strategy_intake.py` (or equivalent) — `kimi_signal_tracking` was
   removed from `BLOCKED_SOURCE_SYSTEMS`. Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`
   and `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, removals from the blacklist require a mutation
   analysis. Revert or re-add `kimi_signal_tracking`.
2. Phase 1 gate module (`alpha_engine/phase1_active_gates.py` or similar) — deadzone +
   time-of-day + combined gates are all returning `False`. Check for a recent refactor that
   broke the gate return-value contract, or an import alias collision.
3. `alpha_engine/tpsl_policy.py` — COMMODITY TP policy default changed from 106.25 to 100.5.
   Revert or update the test expectation if the policy change is intentional.
4. `alpha_engine/backtest_quant_algorithms.py` — invalid syntax at line 1 (possible conflict
   marker; will break coverage and any module that imports it).
