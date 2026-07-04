# GHA Hourly Health Monitor — 2026-07-04

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

> Runs #1404–#1400 (SHA 3bc820c → 963ac80c), all `failure`, spanning 2026-07-04T07:55Z–12:53Z.
> Continuous failure streak: ≥20 consecutive failures traced back to at least 2026-07-03T15:11Z (run #1385).

**Chronic workflows:** none detected — no cancellation-only pattern observed in sampled data (28 unique workflows on main, 0 cancelled runs in the 30-run snapshot).

**Open PRs RED:** CI status not individually queried (9 open PRs: #562, #564, #581, #595, #600, #657, #665, #666, #667). Main CI is RED; any PR that touches CI-gated paths (`alpha_engine/`, `tests/`, `paper_trading/`) will likely fail.

**Failing test breakdown (run #1404 — Python 3.11 & 3.12 both fail identically):**

`23 failed, 6211 passed, 61 skipped, 2 xfailed in 156s`

| Test file | Failures | Root cause |
|---|---|---|
| `tests/test_blacklist_exec_gate_enforcement.py` | 2 | `kimi_signal_tracking` not in `BLOCKED_SOURCE_SYSTEMS` / active gate baseline fixture returns False |
| `tests/test_blacklist_leaderboard_filter.py` | 1 | `kimi_signal_tracking` leaks into top-2 ranking — should be filtered |
| `tests/test_phase1_active_gates.py` | 20 | All `Phase1DeadZoneGateTests` (8), `Phase1TimeOfDayGateTests` (10), `Phase1CombinedTests` (2) return `False is not true` — passes_active_gate() blocking everything |

**Classification:** AUTHOR_FIX — assertion failures indicating real logic regressions, not infra flakes.

**Secondary issue:** `alpha_engine/backtest_quant_algorithms.py` has invalid Python syntax at line 1 (file appears corrupted with binary garbage `"IsADirectoryErrorCHATWITHIT.mdmd atTH..D"`). This causes `coverage` to fail to parse it (non-blocking warning visible in CI logs, does not cause pytest failures directly).

**Likely root causes:**
1. **`kimi_signal_tracking` blacklist gap** — tests in `test_blacklist_exec_gate_enforcement.py` and `test_blacklist_leaderboard_filter.py` expect this source name in `BLOCKED_SOURCE_SYSTEMS` (likely `alpha_engine/emitter_discipline.py`). Either a new test was written expecting a kill that was never applied, or a code change removed the entry.
2. **`phase1_active_gates` broken** — 20 gate tests all return `False is not true`. The `passes_active_gate()` or underlying `check_deadzone()` / `check_time_of_day()` functions appear to be returning False unconditionally. Possible causes: gate config was tightened to always-reject, an import broke silently, or a refactor changed function signatures/return types.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28706851361

**Action required:**
1. **Author should fix:** Add `kimi_signal_tracking` to the blacklist source in `alpha_engine/emitter_discipline.py::BLOCKED_SOURCE_SYSTEMS` (or equivalent), and investigate `alpha_engine/quality_gates.py` (or wherever `Phase1DeadZoneGate`/`Phase1TimeOfDayGate` live) — the gate functions are returning False on all inputs.
2. **Author should fix:** Investigate `alpha_engine/backtest_quant_algorithms.py` — file has corrupted content at line 1; replace with valid Python or restore from git history.

**Status change vs last monitor (2026-05-22 00:00 UTC):** GREEN → RED. This is the first monitor run since 2026-05-22. CI failure streak is at least 21h long as of this writing (≥20 consecutive hourly runs all failing). The regression window is unknown — it could have been introduced any time between 2026-05-22 and 2026-07-03T15:11Z.
