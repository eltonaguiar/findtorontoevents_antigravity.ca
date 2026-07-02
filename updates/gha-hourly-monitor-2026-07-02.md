# GHA Hourly Health Monitor — 2026-07-02

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

Last 5 main runs (all failure):
| Run ID | Conclusion | Timestamp |
|--------|-----------|-----------|
| 28591171609 | failure | 2026-07-02T12:47:45Z |
| 28587837472 | failure | 2026-07-02T11:51:56Z |
| 28582263058 | failure | 2026-07-02T10:10:36Z |
| 28575559021 | failure | 2026-07-02T08:14:11Z |
| 28569755945 | failure | 2026-07-02T06:18:29Z |

Continuous failure streak: 30+ runs, from at least 2026-06-30T18:11Z (~43 hours).

**Failing tests (24 total — run 28591171609, job 84774838298, Python 3.11):**

| Test file | Count | Root cause |
|-----------|-------|------------|
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` missing from intake blacklist; baseline fixture failing |
| `tests/test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaking into top-N ranking |
| `tests/test_phase1_active_gates.py` | 20 | All Phase1 DeadZone + TimeOfDay + Combined gate tests `AssertionError: False is not true` — gate module likely refactored |
| `tests/test_tpsl_policy.py` | 1 | Commodity TP/SL default mismatch: `assert 100.5 == 106.25` |

Result line: `24 failed, 6210 passed, 61 skipped, 85 deselected, 2 xfailed in 154.55s`

Failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28591171609

**Chronic workflows:** none
- `Sports endpoint smoke + Playwright`: 30/30 success (hourly, no cancellations) — HEALTHY

**Open PRs RED (CI Tests failing on PR head commit):**

| PR | Title | CI Tests | Classification | Recommended action |
|----|-------|----------|----------------|--------------------|
| #667 | feat(b5): forward-track cell selector | test(3.11) ❌ test(3.12) ❌ | AUTHOR_FIX | Same root cause as main; fix main first, then rebase PR |
| #666 | fix(b1): backfill price guard at resolution-write | test(3.11) ❌ test(3.12) ❌ | AUTHOR_FIX | Same root cause as main; fix main first, then rebase PR |
| #665 | audit(stalled-producer-detector): v2.0+2 | test(3.11) ❌ test(3.12) ❌ | AUTHOR_FIX | Same root cause as main; fix main first, then rebase PR |

Older open PRs (#657, #600, #595, #581, #564, #562) were opened before the failure streak; their CI checks pre-date the regression and are stale.

**Action required:** AUTHOR_FIX — operator must fix 3 root-cause issues on main:

1. **`kimi_signal_tracking` blacklist gap** (`test_blacklist_exec_gate_enforcement.py`, `test_blacklist_leaderboard_filter.py`): `kimi_signal_tracking` is expected in the intake blacklist but is absent. Either the source was removed from the blacklist without updating tests, or a new source needs to be added. Check `alpha_engine/emitter_discipline.py` or equivalent blacklist constant.

2. **Phase1 active gates regression** (`test_phase1_active_gates.py`, 20 tests): All DeadZoneGate and TimeOfDayGate tests return `False is not true`. Gate module likely underwent a signature change or the gate helpers were moved/removed. Check `alpha_engine/phase1_active_gates.py` (or equivalent) against the test fixture imports.

3. **Commodity TP/SL policy default** (`test_tpsl_policy.py`): `get_optimal_tp_sl` returns `100.5` for COMMODITY but test expects `106.25`. A policy constant was changed without updating the test (or vice versa).

**Status change vs 2026-05-22 00:00 UTC (last monitor entry):** GREEN → RED (verdict changed). First monitor entry for 2026-07-02.

---
