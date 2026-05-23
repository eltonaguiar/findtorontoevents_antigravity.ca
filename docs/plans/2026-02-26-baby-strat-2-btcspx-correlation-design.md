# Baby Strat #2: BTC-SPX Correlation Breakdown Detector

> **Strategy Registry:** See [ALL_STRATEGIES.md](../ALL_STRATEGIES.md) for the full crypto strategy inventory across all systems.

**Date:** 2026-02-26
**Agent:** claude_code_01
**File:** `incubator/agents/claude_code_01/crossasset_btcspx_corrbreakdown_v1.py`
**Category:** Cross-Asset (white space — zero existing strategies in ecosystem)

## Strategy Summary

Detects when the rolling 30-day Pearson correlation between BTC and SPX daily returns drops below 0.15 (historically ~0.5-0.7). When BTC is underperforming SPX during a correlation breakdown, this is a mean-reversion BUY opportunity. When BTC is vastly outperforming during a breakdown, it's a SELL.

## Entry Conditions

**BUY:**
1. Rolling 30d BTC-SPX correlation < 0.15
2. BTC 10d cumulative return < SPX 10d cumulative return (BTC is lagging)
3. BTC RSI < 45 (not already overbought)

**SELL:**
1. Rolling 30d BTC-SPX correlation < 0.15
2. BTC 10d cumulative return > SPX 10d return + 5% (BTC overextended)
3. BTC RSI > 55

## Exit Conditions

- Take Profit: 2.5x ATR
- Stop Loss: 1.5x ATR

## Parameters (5)

| Param | Default | Description |
|-------|---------|-------------|
| corr_window | 30 | Rolling correlation period |
| corr_threshold | 0.15 | Below = breakdown |
| return_window | 10 | BTC vs SPX comparison period |
| tp_atr_mult | 2.5 | TP in ATR multiples |
| sl_atr_mult | 1.5 | SL in ATR multiples |

## Test Results

- 300 synthetic daily bars, 250 scanned iterations
- 13 signals fired (12 BUY, 1 SELL) — ~5% signal rate
- Confidence range: 12.8% to 77.0%
- All validation checks PASS

## Academic Backing

- Bouri et al. (2020): BTC-equity correlation regime shifts
- Conlon & McGee (2020): Cross-asset correlation dynamics in crypto

## Uniqueness

First cross-asset strategy in the ecosystem. All existing systems (A-E, Mercury 2) are single-asset. Signals are structurally uncorrelated with everything else because the primary signal source (cross-asset correlation) is not used anywhere.
