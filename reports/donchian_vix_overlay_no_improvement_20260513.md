# Donchian 52w + VIX regime overlay — NO IMPROVEMENT

**Date:** 2026-05-13
**Tool:** `tools/backtest_donchian_vix_regime.py`
**Baseline:** Donchian 52w + Volume on 30 large-cap (2010-2026): n=491, WR 48.9%, PF 2.36, Sharpe 0.46, MDD 49.2%

## Result

| VIX threshold | n | WR% | PF | Sharpe | MDD% | Mean% | Skipped |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline (no filter) | **491** | 48.9 | **2.36** | 0.46 | 49.2 | +3.31 | 0 |
| VIX<18 | 408 | 46.8 | 2.26 | 0.42 | 39.5 | +3.00 | 194 |
| VIX<20 | 427 | 48.0 | 2.36 | 0.45 | 39.5 | +3.21 | 139 |
| VIX<22 | 457 | 48.1 | 2.19 | 0.43 | 46.2 | +2.95 | 85 |
| VIX<25 | 475 | 48.0 | 2.13 | 0.42 | 46.0 | +2.83 | 49 |
| VIX<30 | 489 | 48.9 | 2.30 | 0.45 | 49.2 | +3.15 | 11 |

**VIX filter does NOT improve Donchian.** PF stays in 2.13-2.36 range; Sharpe 0.42-0.46; MDD only marginally compresses; mean return decreases at lower thresholds (worse risk-adjusted).

## Why pattern transfer fails here

EQUITY + ETF VIX-overlays work because:
- **Monthly-rebalance momentum**: enters every month if signal exists, gets caught in high-vol regimes
- VIX filter = "don't enter momentum during bad regime" → MDD compresses dramatically
- Skipping ~22-28% of months OK because momentum still works in remaining 70%

Donchian 52w breakout fails the same overlay because:
- **Event-based entry**: only fires on confirmed 52w high + volume — itself already an implicit "strength" signal
- Many 52w breakouts happen DURING vol recovery rallies (early 2021 post-COVID, late 2024)
- Filtering those out = miss the upside, no MDD benefit
- Donchian's own signal IS the regime filter

## Generalizable pattern (refined)

**VIX-regime overlay HELPS:**
- Monthly-rebalance momentum (EQUITY top-5 → TIER-1)
- Monthly-rebalance sector rotation (ETF top-3 → TIER-1)
- Strategies that enter regardless of present-bar conditions

**VIX-regime overlay does NOT help:**
- Event-based breakouts (Donchian)
- Strategies whose entry signal ALREADY captures regime info

**Why:** signals that fire only on bullish confirmation (breakout, volume surge) self-select for risk-on conditions. Adding VIX filter on top removes some real edge with no MDD benefit.

## Updated swarm-projection track record

| Strategy | Verdict |
|---|---|
| EQUITY VIX<20/22 | EXCEEDED (TIER-1) |
| ETF VIX<22/25 | EXCEEDED (TIER-1) |
| WTI-Brent event-based | PARTIAL WIN (PF 2.26, claim wrong) |
| **Donchian + VIX** | **NO IMPROVEMENT (this run)** |
| BOND credit-spread overlay | FALSIFIED |
| BOND duration rotation | FALSIFIED |
| Gasoline → XLP rotation | FALSIFIED |

7 of 10 strategies tested have meaningful outcome. Updated regime-gate hit rate:
- 4 of 5 regime-gate variants work (EQUITY×2, ETF×2; Donchian fails)
- 80% hit rate on regime-gate proposals
- 0% on lead-lag-correlation proposals

## Recommendation

DO NOT wire VIX overlay on top of Donchian. The strategy already implicitly handles regime.

For future regime-gate tests: check whether the underlying signal already captures regime context. If yes (breakouts, strength-confirmed entries), VIX overlay won't help.

## Files

- `tools/backtest_donchian_vix_regime.py`
- `audit_dashboard/data/donchian_vix_regime_backtest.json`

NFA. No production change.
