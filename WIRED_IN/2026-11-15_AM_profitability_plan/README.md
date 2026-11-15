# WIRED_IN — Specification Documentation

**Date-Time:** 2026-11-15 AM
**Worktree:** `2026-11-15_AM_profitability_plan`
**Branch:** main
**Purpose:** Formal specification of algorithms per asset class, pick justification, backtest/research evidence, and elimination log.

---

## Folder Structure

| Folder | Contents |
|--------|----------|
| `01_spec_per_asset_class/` | Algorithm specification per asset class (equity, crypto, ETF, MF, forex, commodity, bond) |
| `02_pick_justification/` | Justification for each pick / no-pick decision per asset class |
| `03_backtest_research/` | Backtest results, research methodology, what was tested |
| `04_elimination_log/` | How and why strategies/asset classes were eliminated |

---

## Executive Summary

**Zero asset classes passed money-ready gates.** This is not a recommendation to deploy capital. It is a specification of what was tested, what failed, and why.

- **0/37 strategy×symbol combos** passed all money-ready gates in my simulation (2020–2025, yfinance, 4bps round-trip).
- **0/8 pre-registered rules** beat their matched-exposure benchmark in Buffy's parallel backtest (2004–2026, DSR, 2× cost stress).
- **Both simulations agree:** low-cost beta is the only proven path; no active rule has statistical edge.
- **All 9 asset classes** return `sizing_allowed: false`.

**Deployment recommendation:** Low-cost index ETF/MF passive allocation (60% US equity, 20% international, 20% bonds/T-bills) — beta capture, not alpha.

---

## Related Files in Parent Worktree

| File | Location | Purpose |
|------|----------|---------|
| `run_simulation_backtest.py` | `../01_asset_class_plans/` | Executable backtest script |
| `simulation_results_2026-11-15.json` | `../01_asset_class_plans/` | Raw simulation output |
| `SIMULATION_RESULTS.md` | `../01_asset_class_plans/` | Human-readable results |
| `candidate_picks/simulation_candidate_picks.json` | `../01_asset_class_plans/candidate_picks/` | 3 failed-gate candidates |
| `candidate_picks/monitor_simulation_candidates.py` | `../01_asset_class_plans/candidate_picks/` | Live price monitor |
| `FORWARD_TEST_TRACKING_PROTOCOL.md` | `../08_qa_validation/` | Kill/promote decision protocol |
| `qa_protocol.md` | `../08_qa_validation/` | PnL=0%, blank-field QA |
| `plan_per_asset_class.md` | `../01_asset_class_plans/` | Per-asset-class profitability plan |
