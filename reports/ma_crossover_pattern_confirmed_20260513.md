# SPY 50/200 MA crossover + VIX overlay — pattern confirmed (event signals self-regulate)

**Date:** 2026-05-13
**Tool:** `tools/backtest_ma_crossover_vix_regime.py`
**Source:** Cerebras unique pick from next-harvest swarm (rank 2)

## Baseline (no VIX gate) — surprise TIER-1 metrics

| Metric | Value | TIER-1 target | Pass |
|---|---:|---:|:---:|
| **PF** | **15.55** | ≥ 2.0 | ✓✓ |
| **WR** | **80%** | ≥ 55% | ✓✓ |
| **MDD%** | **7.99** | ≤ 10 | ✓ |
| n | 10 | ≥ 200 | ✗ (huge shortfall — golden crosses are rare) |
| Sharpe | 0.79 | (exceptional) | ok |
| Total% | +484 | — | — |
| avg days/trade | 387 | — | — |

vs SPY B&H benchmark: SPY +807% / Sharpe 0.64 / MDD 55.2% (~60% of upside with 7× less MDD)

## VIX overlay variants — DOES NOT HELP

| VIX threshold | n | WR% | PF | Sharpe | MDD% | Total% | Skipped |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 10 | 80.0 | 15.55 | 0.79 | 8.0 | +484 | 0 |
| VIX<18 | 4 | 75.0 | 10.82 | 0.80 | 6.4 | +74 | 6 |
| VIX<20 | 8 | 75.0 | 11.51 | 0.66 | 8.0 | +253 | 2 |
| VIX<22 | 8 | 75.0 | 11.51 | 0.66 | 8.0 | +253 | 2 |
| VIX<25 | 8 | 75.0 | 11.51 | 0.66 | 8.0 | +253 | 2 |
| VIX<30 | 9 | 77.8 | 14.30 | 0.75 | 8.0 | +395 | 1 |

**Every VIX variant produces LOWER total return AND lower Sharpe.** MDD already at 8% baseline (TIER-1 PASSES); filter can't compress further.

## Pattern confirmation (2nd event-signal data point)

| Strategy | Baseline | VIX overlay effect |
|---|---|---|
| EQUITY top-5 momentum | PF 2.82, Sharpe 1.34 | EXCEEDS (PF 5.37, Sharpe 2.19) |
| ETF sector top-3 | PF 2.05, Sharpe 0.97 | EXCEEDS (PF 3.32, Sharpe 1.68) |
| Donchian 52w + Volume | PF 2.36, Sharpe 0.46 | NO IMPROVEMENT |
| **SPY 50/200 crossover** | **PF 15.55, Sharpe 0.79** | **NO IMPROVEMENT (worse)** |

**Confirmed pattern:** VIX overlay helps **monthly-rebalance** momentum (which enters EVERY month regardless of immediate conditions) but does NOT help **event-based** signals (Donchian breakout, MA crossover).

Why: event signals (52w high + volume / golden cross) only fire on confirmed bullish conditions — they SELF-REGULATE for regime. Adding VIX filter on top removes some valid entries with no MDD benefit.

## Cumulative regime-overlay hit rate (now 7 tests)

| Strategy | Type | VIX overlay verdict |
|---|---|---|
| EQUITY VIX | monthly-rebal momentum | ✓ TIER-1 |
| EQUITY VIX+YC | monthly-rebal momentum | ✓✓ SUPER-BREAKTHROUGH |
| EQUITY YC-only | monthly-rebal momentum | ✓ TIER-1 PF |
| ETF VIX | monthly-rebal momentum | ✓ TIER-1 |
| WTI-Brent event | event-based | partial (event-based threshold works without VIX) |
| Donchian + VIX | event-based | ✗ no improvement |
| **MA crossover + VIX** | **event-based** | **✗ no improvement** |

**Type-aware refinement: regime-gate helps 4/4 monthly-rebalance, 0/2 event-based.**

## Strategy candidate (no overlay needed)

SPY 50/200 crossover by itself is a TIER-1-criteria-passing strategy on PF/WR/MDD. Only n=10 blocks formal cert. As a **trend-following position-management framework**, it could be the simplest regime gate around — own SPY when 50d > 200d, cash otherwise.

This is essentially Faber 2007's tactical asset allocation rule. Confirmed in our 20-year backtest.

## Recommendation

**Do NOT wire VIX overlay onto event-based signals.** Use VIX overlay only for monthly-rebalance momentum strategies.

**Standalone use case:** SPY 50/200 crossover could be a position-level macro filter (own EQUITY exposure when crossover is positive; cash otherwise). Different abstraction layer than per-pick gate — would live in portfolio manager not exec gate.

## Files

- `tools/backtest_ma_crossover_vix_regime.py`
- `audit_dashboard/data/ma_crossover_vix_regime_backtest.json`

NFA. No production change.
