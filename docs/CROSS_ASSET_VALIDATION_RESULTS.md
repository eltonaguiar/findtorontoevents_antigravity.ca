# Cross-Asset Strategy Validation Results

**Date:** June 2025  
**Scope:** 20 crypto pairs × 8 strategies (+ 8 inverses) × 6 months 1H candles  
**Tool:** `tools/cross_asset_backtester.py`

## Executive Summary

Across 20 symbols and ~80,000 trades, **only 2 strategies show a genuine cross-asset edge**:

| Strategy | Trades | WR% | PF | Avg PnL | Edge Symbols |
|----------|--------|-----|------|---------|-------------|
| **INV_zscore_mr** (inverse z-score MR) | 1,761 | 46.8% | 1.13 | +0.098% | 10/20 |
| **cci_divergence** | 5,147 | 41.5% | 1.05 | +0.053% | 4/20 |

### Key Findings

1. **Inverse strategies consistently outperform originals.** Supertrend, HMA, LuxAlgo breakout — all generate stronger edge when direction is flipped. This means the original signal logic is reliably wrong, making the inverse predictive.

2. **Inverse Z-Score MR is the standout.** PF 1.13 with 46.8% WR across 1,761 trades on 20 symbols, with edge in 10/20 pairs. This is the most robust cross-asset signal found.

3. **CCI Divergence is the only non-inverse winner.** PF 1.05, WR 41.5% across 5,147 trades. Modest but consistent.

4. **Three strategies are fundamentally broken on crypto:**
   - Supertrend: PF 0.88, -1,194% total → **retire or invert**
   - HMA Trend: PF 0.88, -624% total → **retire or invert**
   - LuxAlgo Breakout: PF 0.91, -800% total → **retire or invert**

5. **SL Width matters massively.** "Tight" stops (1.0x ATR) show 60-68% SL hit rates. "Wide" stops (2.0x ATR) drop SL rates to 45-55% but with fewer trades. Optimal is symbol-dependent:
   - BTC/majors: 1.5x ATR SL works well
   - Volatile alts (SOL, SUI, PEPE): need 2.0x+ ATR

## Strategy Rankings (Full 20-Symbol Results)

### Profitable (PF > 1.0)
| # | Strategy | Cat | Trades | WR | PF | Avg PnL | Total PnL | Edge/20 |
|---|----------|-----|--------|-----|------|---------|-----------|---------|
| 1 | INV_zscore_mr | inverse | 1,761 | 46.8% | 1.13 | +0.098% | +172.8% | 10/20 |
| 2 | INV_supertrend | inverse | 7,940 | 40.4% | 1.12 | +0.137% | +1,085.6% | 1/20 |
| 3 | INV_luxalgo_breakout | inverse | 8,004 | 41.1% | 1.09 | +0.097% | +774.0% | 3/20 |
| 4 | INV_bb_squeeze | inverse | 389 | 42.4% | 1.09 | +0.080% | +31.0% | 8/20 |
| 5 | INV_volume_breakout | inverse | 4,004 | 41.0% | 1.08 | +0.082% | +326.6% | 4/20 |
| 6 | INV_hma_trend | inverse | 4,396 | 41.9% | 1.07 | +0.072% | +317.5% | 5/20 |
| 7 | cci_divergence | passer | 5,147 | 41.5% | 1.05 | +0.053% | +274.1% | 4/20 |

### Unprofitable (PF < 1.0)
| # | Strategy | Cat | Trades | WR | PF | Avg PnL | Total PnL |
|---|----------|-----|--------|-----|------|---------|-----------|
| 8 | volume_breakout | passer | 3,796 | 38.5% | 0.95 | -0.055% | -209.9% |
| 9 | zscore_mr | winner* | 1,871 | 43.5% | 0.92 | -0.065% | -121.7% |
| 10 | luxalgo_breakout | winner* | 8,235 | 38.0% | 0.91 | -0.097% | -800.1% |
| 11 | supertrend | component | 8,047 | 35.9% | 0.88 | -0.148% | -1,193.9% |
| 12 | hma_trend | component | 4,751 | 38.2% | 0.88 | -0.131% | -624.1% |
| 13 | INV_cci_divergence | inverse | 5,017 | 37.2% | 0.86 | -0.157% | -789.1% |
| 14 | bb_squeeze_breakout | passer | 389 | 36.2% | 0.85 | -0.148% | -57.4% |

*Note: "winner" label was from forward test on limited assets; cross-asset validation shows these don't generalize.

## DNA Mutation Recommendations

### 1. Immediate Inversions (high confidence)
- **Supertrend → INV_supertrend**: PF 0.88 → 1.12 (+1,085% total). The trend-following logic is reliably wrong on crypto 1H. Invert it.
- **HMA Trend → INV_hma_trend**: PF 0.88 → 1.07. Same pattern — trend inflection points are noise on crypto.
- **LuxAlgo Breakout → INV_luxalgo_breakout**: PF 0.91 → 1.09.

### 2. Strategy Refinements
- **Z-Score MR**: Original loses money (PF 0.92) but inverse wins (PF 1.13). The MR signal logic is backwards — z-score extremes in ranging markets actually predict continuation, not reversion, in crypto.
- **CCI Divergence**: Only strategy that works both ways — the original wins (PF 1.05) and inverse loses (PF 0.86). This signal has genuine predictive value. Focus on parameter optimization.

### 3. SL Width Fix
Current default SL mult = 1.0x ATR causes 60-68% SL hit rate. Recommended:
- **Majors (BTC, ETH)**: SL = 1.5x ATR, TP = 2.5x ATR
- **Mid-cap (SOL, AVAX, DOT)**: SL = 2.0x ATR, TP = 3.0x ATR
- **Small/volatile (PEPE, SUI, ARB)**: SL = 2.5x ATR, TP = 4.0x ATR

## Implementation Plan

1. **Deploy inverse_wrapper.py** for supertrend, hma_trend, luxalgo_breakout, zscore_mr in QuanEngine strategy pool
2. **Promote cci_divergence** to TRENDING pool (it's currently in passers)
3. **Implement per-asset SL width tiers** based on symbol volatility class
4. **Re-run forward test** with inverse strategies for 2 weeks minimum before trusting

## Raw Data

Full per-symbol results saved in: `backtest_results/cross_asset_validation.json`
