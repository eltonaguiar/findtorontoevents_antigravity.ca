# GHA Hourly Health Monitor — 2026-07-09

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 30 most-recent CI Tests runs (ci-tests.yml) are `failure` — going back to at least 2026-07-08T23:13Z. Both `test (3.11)` and `test (3.12)` jobs fail on step 8 ("Run all tests — gating known-drift quarantined"). **24 tests failed, 6210 passed** in the latest run (29016824622, 12:02–12:07Z).

**Failing tests (24 total):**

| File | Tests | Root cause |
|---|---|---|
| `tests/test_phase1_active_gates.py` | 20 failures — all `Phase1DeadZoneGateTests` + `Phase1TimeOfDayGateTests` | `passes_active_gate()` returns `False` for every case that should pass — likely an API/signature change in `alpha_engine/production_scanner.py` or gate module |
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 failures | `kimi_signal_tracking` absent from intake blacklist; baseline fixture also fails |
| `tests/test_blacklist_leaderboard_filter.py` | 1 failure | `kimi_signal_tracking` leaks into top-2 ranking — not blocked by leaderboard filter |
| `tests/test_tpsl_policy.py` | 1 failure | Commodity TP/SL constant mismatch: `assert 100.5 == 106.25` |

**Additional finding:** `alpha_engine/backtest_quant_algorithms.py` has invalid Python syntax at line 1 (coverage parse fails; does not cause test failures directly but indicates the file is broken).

**Most likely regression source:** A commit between 2026-06-24 (last confirmed-green state, run 26245197357 on PR #1292) and 2026-07-08T23:13Z changed `passes_active_gate()` gate logic, the `kimi_signal_tracking` blacklist membership, and/or the COMMODITY TP/SL constants. All 20 Phase1 gate tests returning `False is not true` strongly suggest a gate function signature or import was silently broken.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29016824622

**Chronic workflows:** none — Sports endpoint smoke + Playwright has 27 success / 3 cancel in last 30 runs (well below chronic threshold). No other workflow meets the ≥4-cancel + 0-success criteria.

**Open PRs RED:** 8 open PRs (#667, #666, #665, #657, #600, #595, #581, #564) — all stale (last updated Jun 2026); none have been rebased since the regression. Any merge of these PRs onto the broken main would inherit the CI failure. No PR has an active `CI Tests` failure from a recent push; the main branch itself is the root cause.

**Action required:**
- **AUTHOR FIX (P0):** Investigate `alpha_engine/production_scanner.py` (or wherever `passes_active_gate` / dead-zone / time-of-day gate logic lives) — the regression caused 20 gate tests to return `False` for all inputs. Check git log between 2026-06-24 and 2026-07-08 for changes to that module.
- **AUTHOR FIX (P1):** Add `kimi_signal_tracking` to the intake blacklist and leaderboard filter in production code (or update tests if strategy was intentionally un-blacklisted).
- **AUTHOR FIX (P1):** Restore COMMODITY TP/SL constants so default returns `106.25` (tests expect this value; current code returns `100.5`).
- **AUTHOR FIX (P2):** Fix invalid syntax in `alpha_engine/backtest_quant_algorithms.py` line 1.

**Status change vs 2026-05-22:** GREEN → RED. First monitor entry for 2026-07-09.
