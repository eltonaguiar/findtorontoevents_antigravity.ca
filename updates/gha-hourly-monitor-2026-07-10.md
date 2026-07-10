# GHA Hourly Health Monitor — 2026-07-10

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** none detected (all 29 unique workflows in the last 100 runs showed `success` or `in_progress`; no workflow met the chronic-cancellation threshold of ≥4 cancels + 0 successes in 15 runs)

**Open PRs RED:** Unable to fetch per-PR check status via available tools — 9 PRs open (latest #667, #666, #665, #657, #600, #595, #581, #564, #562). All are likely affected since main CI Tests is consistently RED.

**Action required:** AUTHOR_FIX — main has been RED for ≥2 days (30 consecutive failures going back to 2026-07-08T20:00Z). See failure details below.

---

### Failure Detail (run 29091236452 — 2026-07-10T12:01Z, job `test (3.12)`)

Result: `24 failed, 6210 passed, 61 skipped` in step "Run all tests (gating — known-drift quarantined)"

**Failing test files and root causes:**

| # | Test | Failure | Classification |
|---|------|---------|----------------|
| 1–2 | `test_blacklist_exec_gate_enforcement.py` | `kimi_signal_tracking` not found in intake blacklist; baseline fixture fails | AUTHOR_FIX |
| 3 | `test_blacklist_leaderboard_filter.py::test_ranking_excludes_blacklisted_from_top_n` | `kimi_signal_tracking` leaks into top-2 rankings (should be excluded) | AUTHOR_FIX |
| 4–23 | `test_phase1_active_gates.py` — 20 tests across `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests` | All assertions `False is not true` — likely Phase1 gate functions broken/removed or signature changed | AUTHOR_FIX |
| 24 | `test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` | `assert 100.5 == 106.25` — commodity TP/SL default value changed | AUTHOR_FIX |

**Secondary issue (non-blocking):** `alpha_engine/backtest_quant_algorithms.py` has a Python syntax error at line 1 — coverage parser can't parse it. Doesn't gate CI but indicates a broken file in the repo.

### Recommended fixes (all AUTHOR_FIX, no infra flakes)

1. **Blacklist**: Add `kimi_signal_tracking` to the intake blacklist in whatever module backs `test_blacklist_exec_gate_enforcement.py` and `test_blacklist_leaderboard_filter.py`.
2. **Phase1 gates**: Investigate `alpha_engine/` for the Phase1 DeadZone and TimeOfDay gate functions — they may have been removed or their calling convention changed. The 20-test sweep failing with `False is not true` points to the gate function returning a falsy value (or raising before returning) for every case, including cases that should pass. Check recent commits to the Phase1 gate module.
3. **TP/SL policy commodity default**: The test expects commodity TP to produce `106.25` but gets `100.5`. A recent commit changed the commodity default multiplier. Fix the production value or update the test to the new intended default.
4. **Syntax error in `alpha_engine/backtest_quant_algorithms.py`**: Fix or remove the invalid syntax at line 1.

### History

- First failure in this monitor window: 2026-07-08T20:00Z (oldest in 30-run page)
- Most recent success on main: unknown (beyond the 30-run history page queried; total_count=1095 runs)
- Consecutive failures as of 13:00 UTC: 30+ (full page, all failures)
- Failure URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29091236452
