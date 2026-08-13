# GHA Hourly Health Monitor — 2026-08-13

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 runs):** 0 success, 30 failure, 0 in_progress — every run on main since at least 2026-08-10T09:32Z is a failure. CI has been continuously RED for 3+ days.

**Failing tests (24 total, Python 3.11 + 3.12 both fail, AUTHOR_FIX):**

| Test file | Failures | Root cause |
|---|---|---|
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` not found in blacklist — source missing from `BLOCKED_SOURCE_SYSTEMS` or equivalent registry |
| `tests/test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaking into top-N ranking — same missing blacklist entry |
| `tests/test_phase1_active_gates.py` | 20 | Phase1 DeadZone + TimeOfDay gate functions all return `False is not true` — gate implementation broken or removed |
| `tests/test_tpsl_policy.py` | 1 | Commodity TP/SL policy default changed: `assert 100.5 == 106.25` |

**Key evidence from run 31537099985 (2026-08-11T21:16Z):**
```
FAILED tests/test_blacklist_exec_gate_enforcement.py::BlacklistIntakeTests::test_kimi_in_intake_blacklist
  AssertionError: 'kimi_signal_tracking' not found in [blacklist]

FAILED tests/test_phase1_active_gates.py::Phase1DeadZoneGateTests::test_deadzone_high_boundary_passes
  AssertionError: False is not true  (×18 similar failures)

FAILED tests/test_tpsl_policy.py::test_get_optimal_tp_sl_uses_policy_defaults_for_commodity
  assert 100.5 == 106.25

24 failed, 6210 passed, 61 skipped in 165.97s
```

Also noted: `Couldn't parse 'alpha_engine/backtest_quant_algorithms.py' as Python source: 'invalid syntax' at line 1` (coverage step, non-blocking).

**Chronic workflows:** none detected.
- Sports endpoint smoke + Playwright (main): 30/30 success, latest 2026-08-13T12:32Z — GREEN
- Claude Gainer ML Live Scanner (main): 30/30 success, latest 2026-08-13T12:32Z — GREEN

**Open PRs with CI Tests RED (all AUTHOR_FIX):**

| PR | Title | CI Verdict | Recommended action |
|---|---|---|---|
| #665 | audit(stalled-producer-detector): v2.0+2 | failure (2026-06-24) | AUTHOR_FIX — same root failures as main; earlier commit on this branch was green |
| #667 | feat(b5): forward-track cell selector | failure (2026-06-24) | AUTHOR_FIX — same root failures |
| #666, #657, #600, #595, #581, #564, #562 | various | not retrieved (stale/old) | investigate if merging is planned |

**Action required:**
1. **Immediate (blocker):** Author must fix 3 test categories before any merge can land:
   - Add `kimi_signal_tracking` to the blacklist (`BLOCKED_SOURCE_SYSTEMS` or equivalent) — 3 tests
   - Restore/fix Phase 1 DeadZone + TimeOfDay gate functions in `alpha_engine/` — 20 tests
   - Update commodity TP/SL policy default to match test expectation (106.25) OR update the test — 1 test
2. **Investigation:** Confirm when exactly CI turned RED — earliest visible failure is 2026-08-10T09:32Z, but the CI runs at an hourly cadence suggesting this could have started between last green run (around June 2026 on PRs) and Aug 10.

**Status change vs previous run (2026-05-22 00:00 UTC):** GREEN → **RED** (first RED detection since monitor gap May 22–Aug 13).

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985
