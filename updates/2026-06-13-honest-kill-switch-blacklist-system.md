# Honest Kill Switch & Automated Blacklist System

**Date:** 2026-06-13  
**Author:** Buffy (Codebuff)  
**Status:** Implemented & Verified

---

## Problem

The portfolio had 19 strategies with WR < 45% or PF < 1.0 after 30+ closed trades in the honest ledger (`at_signal_outcomes`). These strategies were dragging down portfolio performance by:
- -326.41% in total PnL damage
- -5.21 percentage points of win rate
- -0.43 profit factor points

## Solution

### 1. Honest Kill Switch (`alpha_engine/honest_kill_switch.py`)

A data-driven strategy killer that queries the honest ledger and applies statistical gates:

- **Gate 1:** WR < 45% → KILL
- **Gate 2:** PF < 1.0 → KILL
- **Minimum:** 30+ closed trades before evaluation
- **Protected:** Core strategies exempt from auto-kill

**CLI:**
```bash
python3 alpha_engine/honest_kill_switch.py              # dry-run report
python3 alpha_engine/honest_kill_switch.py --apply       # write kills to pipeline
python3 alpha_engine/honest_kill_switch.py --check <name> # test one strategy
```

### 2. Blacklist Impact Simulation (`tools/blacklist_impact_simulation.py`)

Measures the portfolio-level improvement after removing killed strategies:

| Metric | Baseline | Post-Blacklist | Delta |
|--------|----------|----------------|-------|
| Trades | 17,329 | 12,280 | -29.1% |
| Win Rate | 53.28% | 58.49% | **+5.21 pp** |
| Profit Factor | 1.5020 | 1.9351 | **+0.4331** |
| Total PnL | 3,303.45% | 3,629.86% | **+326.41%** |

### 3. Suppression Pipeline Integration

Killed strategies are written to `alpha_engine/strategy_kill_list.json` which feeds:
- `strategy_suppression.py::load_kill_list()` → consumed by `forward_validator.py` and `smart_picks_engine.py`
- `alpha_engine/config.py::BLACKLISTED_STRATEGIES` → intake-side blacklist
- `audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS` → source-system block

### 4. Automated GitHub Actions Workflow

`.github/workflows/honest-kill-switch.yml` runs every 12 hours:
- Re-evaluates all strategies against the honest ledger
- Applies new kills to the suppression pipeline
- Runs the blacklist impact simulation
- Commits results with `[skip ci]`

### 5. Unit Tests (`alpha_engine/tests/test_honest_kill_switch.py`)

Tests cover:
- Kill logic: WR < 45% → KILL, PF < 1.0 → KILL, both pass → SURVIVOR
- Insufficient data: < 30 trades → not evaluated
- Protected strategies: exempt from auto-kill
- PF edge cases: zero losses → high PF, zero wins+losses → PF=0
- Custom thresholds: stricter WR/trades kill more
- Cache invalidation: proper reset between runs
- Boundary conditions: exactly at threshold survives, just below kills

---

## Files Changed

| File | Change |
|------|--------|
| `alpha_engine/honest_kill_switch.py` | **New** — core kill switch module |
| `alpha_engine/config.py` | Added `goldmine_6x_consensus`, `commodity_momentum`, `cta_cross_asset_tsmom` to `BLACKLISTED_STRATEGIES` |
| `audit_trail/quality_gates.py` | Added `quan_engine` to `BLOCKED_SOURCE_SYSTEMS` |
| `tools/blacklist_impact_simulation.py` | **New** — portfolio simulation tool |
| `.github/workflows/honest-kill-switch.yml` | **New** — automated 12-hour evaluation |
| `alpha_engine/tests/test_honest_kill_switch.py` | **New** — unit tests |
| `alpha_engine/data/honest_kill_switch.json` | **Generated** — kill switch report |
| `alpha_engine/strategy_kill_list.json` | **Updated** — suppression pipeline input |
| `reports/blacklist_impact_simulation.json` | **Generated** — simulation results |

---

## Verification

1. **Kill switch runs cleanly:** `python3 alpha_engine/honest_kill_switch.py` — 19 killed, 6 survivors
2. **Simulation confirms impact:** +5.21 pp WR, +0.4331 PF, -326% PnL damage removed
3. **Suppression pipeline wired:** All 19 killed strategies confirmed in `strategy_suppression.py::load_kill_list()`
4. **Unit tests pass:** All kill logic, edge cases, and cache tests verified
5. **GitHub Actions workflow:** Configured for every-12-hour re-evaluation

---

## Next Steps

- Monitor the kill switch's GitHub Actions runs for reliability
- Track whether newly-appearing strategies get killed promptly (the 45-strategy "insufficient" pool)
- Consider adding asset-class-specific WR thresholds (FOREX may need different gates than CRYPTO)
- Wire blacklist impact metrics into the audit dashboard for live visibility
