# GHA Hourly Health Monitor — 2026-07-25

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**CI Tests extended history (last 15):** 0 success, 15 failure — continuous failures since 2026-07-24T17:33Z (~18h red streak). Run IDs: 30157348671, 30154888607, 30152484104, 30149940433, 30147156537, 30145461834, 30143004674, 30140497673, 30137610753, 30134428399, 30131132638, 30127311154, 30122875719, 30118619121, 30113484084.

**Failing tests (24 FAILED — AUTHOR_FIX, not infra flakes):**

_Source: run 30157348671, job `test (3.11)`, 2026-07-25T12:04–12:53Z_

| # | Test file | Tests | Root cause |
|---|---|---|---|
| 18 | `test_phase1_active_gates.py` | Phase1DeadZoneGateTests (×9), Phase1TimeOfDayGateTests (×8), Phase1CombinedTests (×2) | All return `AssertionError: False is not true` — Phase1 gate functions broken or removed in production code (`alpha_engine/active_gates.py` likely) |
| 3 | `test_blacklist_exec_gate_enforcement.py` (2) + `test_blacklist_leaderboard_filter.py` (1) | `test_kimi_in_intake_blacklist`, `test_passes_active_gate_rejects_kimi_source`, `test_ranking_excludes_blacklisted_from_top_n` | `kimi_signal_tracking` expected in `BLOCKED_SOURCE_SYSTEMS` but absent; tests were added, production blacklist not updated |
| 1 | `test_tpsl_policy.py` | `test_get_optimal_tp_sl_uses_policy_defaults_for_commodity` | COMMODITY TP/SL default mismatch: got `100.5`, expected `106.25` |

**Additional coverage warning:** `alpha_engine/backtest_quant_algorithms.py` reports `invalid syntax at line 1` during coverage pass — possible conflict markers in that file.

**Failing run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30157348671

**Chronic workflows:** none detected in 60-run global sample (pages 1–2 of all-branches history). Full per-workflow chronic scan skipped — 362 active workflows; sampled runs from pages 1+2 showed no cancellations.

**Open PRs CI snapshot (9 open PRs, all on same main SHA 69c8ff54):**

All open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562) are based on main SHA `69c8ff54ec74c1bc80c020ad46a5ae63bb262cac`. Since main CI is RED, any CI run on these branches will also fail with the same 24 failures (or a superset). Classification: **AUTHOR_FIX** (the failures are real test-logic breakage, not infra flake).

**Action required:**
- **AUTHOR_FIX main**: Three issues need fixing before main turns green:
  1. `alpha_engine/active_gates.py` (or equivalent) — Phase1 DeadZone + TimeOfDay gate functions broken; 18 tests assert `False` where `True` is required
  2. `BLOCKED_SOURCE_SYSTEMS` or equivalent blacklist — add `kimi_signal_tracking` to match 3 failing blacklist tests
  3. `alpha_engine/tpsl_policy.py` COMMODITY default — expected `106.25`, currently computes `100.5`
- **Inspect** `alpha_engine/backtest_quant_algorithms.py` line 1 for conflict markers / invalid syntax
- All 9 open PRs will remain red until main is fixed

**Status change vs previous hourly run (2026-05-22 06:00 UTC):** GREEN → RED (verdict changed — this is the first monitor run since 2026-05-22; continuous failures detected since 2026-07-24T17:33Z).

---
