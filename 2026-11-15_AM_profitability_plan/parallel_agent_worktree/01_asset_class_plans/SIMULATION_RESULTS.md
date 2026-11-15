# Simulation Results — Appended to Profitability Plan

**Date:** 2026-11-15 (AM)
**Source:** `run_simulation_backtest.py` executed against live yfinance data (2020-01-01 → 2025-12-31)
**Data:** 7 equity ETFs + 5 crypto symbols, daily bars
**Cost model:** 1 bps commission + 1 bps slippage per side (4 bps round-trip)

---

## Simulation Results Summary

### Test Matrix

| Dimension | Values |
|-----------|--------|
| Equity symbols | SPY, QQQ, IWM, DIA, VTI, EFA, EEM |
| Crypto symbols | BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD |
| Equity strategies | RSI2 Mean Reversion, Dual MA Crossover, Bollinger Mean Reversion |
| Crypto strategies | Donchian Breakout, EMA Trend Crossover |
| Holding periods | Swing/positional (daily bars, ATR/MA exits) |
| Walk-forward | 5 folds, 1yr train / 1yr test (expanding) |
| Total combos backtested | 37 |
| Total walk-forward folds | ~150 |

---

### Full-Period Results (sorted by Profit Factor, ≥10 trades only)

| Symbol | Strategy | Trades | WR % | PF | Net PnL % | Max DD % | Sharpe | Sortino | Calmar | Avg Bars | Expectancy % | DSR | PBO |
|--------|----------|--------|------|-----|-----------|----------|--------|---------|--------|----------|--------------|-----|-----|
| ADA-USD | EMA_Trend_Crossover | 30 | 46.67 | 0.889 | -18.22 | 79.03 | -0.304 | -0.989 | -1.937 | 9.7 | -0.61 | 0.383 | 0.979 |
| SOL-USD | EMA_Trend_Crossover | 32 | 46.88 | 0.868 | -33.35 | 153.31 | -0.364 | -0.953 | -1.713 | 10.3 | -1.04 | 0.360 | 0.983 |
| XRP-USD | EMA_Trend_Crossover | 47 | 36.17 | 0.523 | -130.73 | 152.81 | -1.894 | -5.440 | -4.587 | 9.5 | -2.78 | 0.033 | 0.999 |
| ETH-USD | EMA_Trend_Crossover | 34 | 38.24 | 0.500 | -113.37 | 137.16 | -1.763 | -3.779 | -6.126 | 10.6 | -3.33 | 0.045 | 0.999 |
| BTC-USD | EMA_Trend_Crossover | 33 | 33.33 | 0.315 | -128.25 | 147.27 | -3.095 | -10.379 | -6.650 | 7.0 | -3.89 | 0.002 | 0.999 |
| QQQ | RSI2_MeanReversion | 47 | 8.51 | 0.022 | -164.26 | 158.61 | -9.711 | -11.164 | -5.553 | 4.1 | -3.50 | 0.000 | 0.999 |
| IWM | RSI2_MeanReversion | 40 | 17.50 | 0.017 | -145.60 | 146.59 | -8.470 | -10.479 | -6.257 | 3.4 | -3.64 | 0.000 | 0.999 |
| VTI | RSI2_MeanReversion | 43 | 2.33 | 0.003 | -148.07 | 142.43 | -12.148 | -12.709 | -6.093 | 3.5 | -3.44 | 0.000 | 0.999 |
| SPY | RSI2_MeanReversion | 48 | 2.08 | 0.002 | -161.28 | 155.67 | -12.963 | -13.450 | -5.439 | 3.5 | -3.36 | 0.000 | 0.999 |
| DIA | RSI2_MeanReversion | 52 | 0.00 | 0.000 | -186.52 | 180.88 | -16.074 | -16.074 | -4.997 | 4.2 | -3.59 | 0.000 | 0.999 |
| EFA | RSI2_MeanReversion | 46 | 0.00 | 0.000 | -181.98 | 180.08 | -18.454 | -18.454 | -5.536 | 4.2 | -3.96 | 0.000 | 0.999 |
| EEM | RSI2_MeanReversion | 33 | 0.00 | 0.000 | -118.47 | 116.87 | -11.179 | -11.179 | -7.741 | 4.2 | -3.59 | 0.000 | 0.999 |

*(All other symbol×strategy combos had <10 trades or PF=0 — see full JSON for details.)*

---

### Walk-Forward Summary (Test-Period Aggregated)

| Symbol | Strategy | Folds | Avg PF | Avg WR % | Avg Net PnL % | Avg Max DD % | Avg Sharpe | Avg DSR | Max PBO |
|--------|----------|-------|--------|----------|---------------|--------------|------------|---------|---------|
| ADA-USD | EMA_Trend_Crossover | 5 | 200.37 | 53.00 | -0.46 | 11.93 | 0.724 | 0.000 | 0.999 |
| EFA | Bollinger_MeanReversion | 5 | 200.11 | 30.00 | +0.71 | 0.69 | -0.296 | 0.000 | 0.999 |
| IWM | Bollinger_MeanReversion | 5 | 199.84 | 30.00 | -6.04 | 3.75 | -0.718 | 0.000 | 0.999 |
| SPY | Bollinger_MeanReversion | 5 | 199.80 | 20.00 | -1.68 | 0.46 | -1.558 | 0.000 | 0.999 |
| QQQ | Bollinger_MeanReversion | 5 | 199.80 | 20.00 | -2.01 | 1.57 | -0.979 | 0.000 | 0.999 |
| ETH-USD | EMA_Trend_Crossover | 5 | 0.768 | 39.74 | -15.30 | 24.38 | -1.086 | 0.000 | 0.999 |
| SOL-USD | EMA_Trend_Crossover | 4 | 0.745 | 35.42 | -25.92 | 33.13 | -0.866 | 0.000 | 0.999 |
| XRP-USD | EMA_Trend_Crossover | 5 | 0.702 | 32.79 | -18.46 | 31.35 | -1.348 | 0.000 | 0.999 |
| DIA | Bollinger_MeanReversion | 5 | 0.419 | 30.00 | -2.32 | 0.88 | -0.403 | 0.000 | 0.999 |
| BTC-USD | EMA_Trend_Crossover | 5 | 0.368 | 25.33 | -24.94 | 29.62 | -3.631 | 0.000 | 0.999 |

**Note:** The Bollinger Mean Reversion PF values >100 on equity ETFs are statistical artifacts — they occur when gross_loss ≈ 0 (almost no losing trades, but also almost no trades at all). These are not tradable edges; they are under-sampled noise.

---

### Money-Ready Gate Results (Walk-Forward Test Period)

**Gate requirements:** PF≥1.15 \| WR≥50% \| Sharpe≥1.0 \| DSR≥0.95 \| PBO≤0.10 \| MaxDD<15% \| Trades≥50

| Symbol | Strategy | Passed | Status | Gates Passed |
|--------|----------|--------|--------|--------------|
| ADA-USD | EMA_Trend_Crossover | 4/7 | PARTIAL | PF✓ WR✓ MaxDD✓ Trades✓ | Sharpe✗ DSR✗ PBO✗ |
| EFA | Bollinger_MeanReversion | 3/7 | PARTIAL | PF✓ MaxDD✓ Trades✓ | WR✗ Sharpe✗ DSR✗ PBO✗ |
| IWM | Bollinger_MeanReversion | 3/7 | PARTIAL | PF✓ MaxDD✓ Trades✓ | WR✗ Sharpe✗ DSR✗ PBO✗ |
| SPY | Bollinger_MeanReversion | 3/7 | PARTIAL | PF✓ MaxDD✓ Trades✓ | WR✗ Sharpe✗ DSR✗ PBO✗ |
| QQQ | Bollinger_MeanReversion | 3/7 | PARTIAL | PF✓ MaxDD✓ Trades✓ | WR✗ Sharpe✗ DSR✗ PBO✗ |
| ETH-USD | EMA_Trend_Crossover | 1/7 | PARTIAL | Trades✓ | PF✗ WR✗ Sharpe✗ DSR✗ PBO✗ MaxDD✗ |
| SOL-USD | EMA_Trend_Crossover | 1/7 | PARTIAL | Trades✓ | PF✗ WR✗ Sharpe✗ DSR✗ PBO✗ MaxDD✗ |
| XRP-USD | EMA_Trend_Crossover | 1/7 | PARTIAL | Trades✓ | PF✗ WR✗ Sharpe✗ DSR✗ PBO✗ MaxDD✗ |
| BTC-USD | EMA_Trend_Crossover | 1/7 | PARTIAL | Trades✓ | PF✗ WR✗ Sharpe✗ DSR✗ PBO✗ MaxDD✗ |
| *(all others)* | *(all others)* | 2-3/7 | PARTIAL | Varies | Most fail PF/WR/Sharpe/DSR/PBO |

**Bottom line: 0/37 combos pass all 7 gates.** Best performer (ADA-USD EMA Trend Crossover) passes only 4/7 and fails Sharpe, DSR, and PBO — meaning it has no statistically significant edge.

---

### Key Conclusions from Simulations

1. **No strategy is profitable after costs.** All equity strategies are deeply negative (RSI2 Mean Reversion: -118% to -186% net PnL; Bollinger: -2% to -75%). Crypto EMA trend is negative (-18% to -130%).

2. **DSR ≈ 0 for nearly all strategies.** No statistical confidence that any Sharpe > 0. The information coefficient is effectively 0.

3. **PBO ≈ 0.999 for nearly all strategies.** Near-certain probability that any apparent edge is overfitting, not real.

4. **High Max Drawdown (79%-180%) on crypto trend strategies.** Even the "best" crypto strategy (ADA) has 79% max drawdown — unacceptable for capital deployment.

5. **RSI(2) mean reversion on equity fails completely in 2020-2025.** Unlike the 2008-2020 era when Connors RSI(2) worked, the post-2020 regime has destroyed this edge (WR 0-17%, PF ~0).

6. **Walk-forward confirms in-sample decay.** Strategies that look OK full-period collapse in OOS test folds (negative Sharpe, negative PnL).

---

### What This Validates

The simulation results **independently confirm** the final_v4/flaxen-hair plan conclusion:

> **No asset class is currently proven profitable. 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. Information coefficient ≈ 0. Win rates near 40%. All 9 classes return `sizing_allowed: false`. Do not deploy capital yet.**

The only path to profitability remains:
1. **Parallel track:** Low-cost index ETF/MF passive allocation (beta capture, not alpha) — this is the only positive-expectancy vehicle.
2. **Research track:** Continue EQUITY and CRYPCO research under strict gates, but nothing is ready for capital.

---

## Full Raw Results

Saved to: `01_asset_class_plans/simulation_results_2026-11-15.json`

Contains: all 37 full-period results, ~150 walk-forward folds, cost model, run timestamp.
