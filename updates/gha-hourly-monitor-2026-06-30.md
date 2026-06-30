# GHA Hourly Health Monitor — 2026-06-30

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 5 most-recent runs on `main` failed. Oldest sampled failure: 2026-06-28T15:57Z — CI has been continuously RED for **2+ days** (30/30 scanned runs all `failure`).

**Failing run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/28442500949

**Failing tests (24 total — all AUTHOR_FIX):**

| Group | Tests | Symptom |
|---|---|---|
| Blacklist enforcement | 3 | `kimi_signal_tracking` not found in `BLOCKED_SOURCE_SYSTEMS`; passes active gate when it shouldn't; leaks into leaderboard top-N |
| Phase1 active gates | 19 | `Phase1DeadZoneGateTests`, `Phase1TimeOfDayGateTests`, `Phase1CombinedTests` — all returning `False is not true`; gate functions broken |
| TPSL policy | 1 | `test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` — expected 106.25 got 100.5 |
| Syntax error (secondary) | — | `alpha_engine/backtest_quant_algorithms.py` fails coverage parse: `invalid syntax at line 1` (file appears corrupted/non-Python content) |

**Sports smoke (last 15):** 15 success — GREEN

**Chronic workflows:** No CHRONIC pattern detected in sampled workflows (sports-smoke-and-e2e 15/15 success; Unified Audit Dashboard, DNA Strategy Pipeline, Baby Strat Real Forward Monitor, Copy Trader Forward Test, Outcome Resolver in_progress as of scan time — normal operational state).

**Open PRs RED:**
- **#667** (feat/b5-forward-track-cell-selector) — `test(3.11)` + `test(3.12)` FAILURE — AUTHOR_FIX (inherits pre-existing main failures; cannot merge until main is fixed)
- **#666** (fix/resolver-b1-backfill-price-guard) — `test(3.11)` + `test(3.12)` FAILURE — AUTHOR_FIX (same; inherits main failures)

**Action required:** Author should fix main's 24 failing tests before merging any open PRs.

Priority order:
1. **`kimi_signal_tracking` blacklist** — add to `BLOCKED_SOURCE_SYSTEMS` or equivalent gate list; check `alpha_engine/emitter_discipline.py` or `alpha_engine/quality_gates.py`
2. **Phase1 gate functions** — `passes_active_gate` or equivalent is returning `False` across all Phase1 test cases; likely a gate logic regression in a recent commit
3. **TPSL policy commodity** — check `alpha_engine/tpsl_policy.py` (or equivalent); commodity default changed from 106.25 to 100.5 unexpectedly
4. **`alpha_engine/backtest_quant_algorithms.py`** — file contains non-Python content at line 1; needs replacement with valid Python or deletion if deprecated
