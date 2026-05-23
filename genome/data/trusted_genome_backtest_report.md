# Trusted Genome Mutations -- Backtest Report

**Run:** 2026-03-14T03:24:42.578864+00:00
**Universe:** 21 symbols | 1h interval | 500 bars
**Window:** Bar 200..500
**Costs:** 0.1% commission + 0.05% slippage per side

---

## Summary Table

| Strategy | Trades | Win Rate | Avg PnL | Total Ret | PF | MaxDD | Sharpe | Gate |
|----------|--------|----------|---------|-----------|-----|-------|--------|------|
| regime_switch_mut | 372 | 33.1% | -0.550% | -18.58% | 0.56 | 18.9% | -5.22 | FAIL |
| basket_corr_gate_mut | 412 | 35.4% | -0.623% | -22.72% | 0.56 | 22.7% | -5.33 | FAIL |
| vol_scaler_size_mut | 340 | 35.0% | -0.657% | -20.08% | 0.53 | 20.2% | -5.87 | FAIL |
| mtf_align_mut | 325 | 39.7% | -0.290% | -9.10% | 0.78 | 9.5% | -2.20 | FAIL |
| vol_adaptive_thresh_mut | 9 | 22.2% | -0.899% | -0.81% | 0.31 | 0.8% | -11.24 | FAIL |

---

## Per-Strategy Detail

### regime_switch_mut
> Trend-follow in high-vol regime, mean-revert in low-vol regime

- **Trades:** 372 (123W / 249L)
- **Win Rate:** 33.1%
- **Avg PnL:** -0.5505%
- **Total Return:** -18.58%
- **Profit Factor:** 0.56
- **Max Drawdown:** 18.9%
- **Sharpe Ratio:** -5.22
- **Avg Hold:** 8.1 bars
- **Exit Mix:** TP=110 | SL=236 | TIME=26
- **Best Trade:** +4.896% | Worst: -3.529%

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 63 | 21 | 38% | -0.50% | 0.75 |
| ETHUSDT | 43 | 15 | 33% | -0.85% | 0.52 |
| BNBUSDT | 60 | 19 | 21% | -1.09% | 0.34 |
| SOLUSDT | 51 | 15 | 27% | -0.90% | 0.54 |
| XRPUSDT | 39 | 19 | 26% | -1.73% | 0.25 |
| LTCUSDT | 45 | 18 | 39% | -0.67% | 0.58 |
| ADAUSDT | 35 | 15 | 27% | -1.55% | 0.35 |
| TAOUSDT | 54 | 21 | 48% | +0.77% | 1.31 |
| AVAXUSDT | 59 | 17 | 47% | -0.35% | 0.80 |
| LINKUSDT | 38 | 18 | 39% | -0.88% | 0.58 |
| NEARUSDT | 29 | 10 | 40% | -0.36% | 0.76 |
| SUIUSDT | 48 | 19 | 37% | -0.77% | 0.71 |
| APTUSDT | 43 | 16 | 38% | -0.34% | 0.80 |
| DOGEUSDT | 47 | 22 | 14% | -2.91% | 0.18 |
| ARBUSDT | 50 | 18 | 33% | -1.48% | 0.45 |
| OPUSDT | 59 | 19 | 37% | -0.60% | 0.71 |
| INJUSDT | 47 | 17 | 47% | -0.10% | 0.94 |
| FETUSDT | 52 | 15 | 27% | -1.15% | 0.43 |
| TIAUSDT | 45 | 19 | 32% | -1.42% | 0.50 |
| SEIUSDT | 77 | 27 | 26% | -2.38% | 0.36 |
| FILUSDT | 31 | 12 | 25% | -1.14% | 0.40 |

### basket_corr_gate_mut
> BTC correlation gate: only trade alts correlated > 0.4 with BTC

- **Trades:** 412 (146W / 266L)
- **Win Rate:** 35.4%
- **Avg PnL:** -0.6228%
- **Total Return:** -22.72%
- **Profit Factor:** 0.56
- **Max Drawdown:** 22.7%
- **Sharpe Ratio:** -5.33
- **Avg Hold:** 8.7 bars
- **Exit Mix:** TP=133 | SL=257 | TIME=22
- **Best Trade:** +4.341% | Worst: -3.500%

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| ETHUSDT | 110 | 19 | 32% | -1.60% | 0.42 |
| BNBUSDT | 94 | 16 | 31% | -0.89% | 0.44 |
| SOLUSDT | 112 | 24 | 29% | -2.00% | 0.45 |
| XRPUSDT | 115 | 24 | 25% | -2.13% | 0.32 |
| LTCUSDT | 113 | 21 | 38% | -0.86% | 0.60 |
| ADAUSDT | 106 | 21 | 33% | -1.34% | 0.55 |
| TAOUSDT | 82 | 17 | 35% | -0.94% | 0.68 |
| AVAXUSDT | 111 | 20 | 45% | -0.46% | 0.81 |
| LINKUSDT | 115 | 24 | 21% | -2.89% | 0.26 |
| NEARUSDT | 93 | 19 | 58% | +0.67% | 1.33 |
| SUIUSDT | 78 | 23 | 39% | -1.15% | 0.66 |
| APTUSDT | 99 | 26 | 35% | -1.73% | 0.58 |
| DOGEUSDT | 105 | 17 | 35% | -1.22% | 0.50 |
| ARBUSDT | 114 | 25 | 32% | -2.43% | 0.43 |
| OPUSDT | 104 | 21 | 33% | -1.82% | 0.46 |
| INJUSDT | 73 | 17 | 35% | -0.82% | 0.62 |
| FETUSDT | 90 | 17 | 53% | +0.20% | 1.11 |
| TIAUSDT | 107 | 24 | 38% | -1.72% | 0.56 |
| SEIUSDT | 78 | 21 | 38% | -0.79% | 0.71 |
| FILUSDT | 115 | 16 | 31% | -1.61% | 0.40 |

### vol_scaler_size_mut
> Inverse volatility-scaled confidence/position sizing

- **Trades:** 340 (119W / 221L)
- **Win Rate:** 35.0%
- **Avg PnL:** -0.6566%
- **Total Return:** -20.08%
- **Profit Factor:** 0.53
- **Max Drawdown:** 20.2%
- **Sharpe Ratio:** -5.87
- **Avg Hold:** 8.3 bars
- **Exit Mix:** TP=109 | SL=214 | TIME=17
- **Best Trade:** +3.756% | Worst: -3.500%

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 64 | 15 | 33% | -0.95% | 0.44 |
| ETHUSDT | 68 | 17 | 29% | -1.85% | 0.28 |
| BNBUSDT | 46 | 13 | 38% | -0.43% | 0.60 |
| SOLUSDT | 62 | 17 | 41% | -0.45% | 0.79 |
| XRPUSDT | 71 | 23 | 30% | -1.92% | 0.34 |
| LTCUSDT | 62 | 16 | 38% | -0.84% | 0.52 |
| ADAUSDT | 76 | 16 | 31% | -1.38% | 0.43 |
| TAOUSDT | 59 | 16 | 38% | -0.82% | 0.70 |
| AVAXUSDT | 68 | 19 | 37% | -1.21% | 0.51 |
| LINKUSDT | 63 | 17 | 12% | -2.77% | 0.12 |
| NEARUSDT | 55 | 15 | 53% | +0.28% | 1.16 |
| SUIUSDT | 46 | 16 | 38% | -1.28% | 0.48 |
| APTUSDT | 60 | 18 | 28% | -1.74% | 0.41 |
| DOGEUSDT | 73 | 16 | 25% | -1.75% | 0.34 |
| ARBUSDT | 72 | 19 | 37% | -1.35% | 0.56 |
| OPUSDT | 62 | 13 | 38% | -0.45% | 0.73 |
| INJUSDT | 51 | 14 | 29% | -1.18% | 0.41 |
| FETUSDT | 46 | 15 | 73% | +1.99% | 3.64 |
| TIAUSDT | 69 | 17 | 35% | -1.45% | 0.48 |
| SEIUSDT | 53 | 16 | 19% | -2.03% | 0.24 |
| FILUSDT | 71 | 12 | 42% | -0.63% | 0.63 |

### mtf_align_mut
> 3-timeframe confluence: 1h + 4h + daily must all agree

- **Trades:** 325 (129W / 196L)
- **Win Rate:** 39.7%
- **Avg PnL:** -0.2903%
- **Total Return:** -9.10%
- **Profit Factor:** 0.78
- **Max Drawdown:** 9.5%
- **Sharpe Ratio:** -2.20
- **Avg Hold:** 9.6 bars
- **Exit Mix:** TP=108 | SL=186 | TIME=31
- **Best Trade:** +6.392% | Worst: -3.628%

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 139 | 21 | 38% | -0.62% | 0.73 |
| ETHUSDT | 135 | 17 | 35% | -0.91% | 0.61 |
| BNBUSDT | 158 | 20 | 40% | -0.28% | 0.84 |
| SOLUSDT | 125 | 15 | 27% | -1.42% | 0.49 |
| XRPUSDT | 97 | 17 | 29% | -1.47% | 0.39 |
| LTCUSDT | 111 | 11 | 36% | -0.53% | 0.55 |
| ADAUSDT | 63 | 8 | 38% | -0.61% | 0.45 |
| TAOUSDT | 167 | 21 | 48% | +0.70% | 1.24 |
| AVAXUSDT | 152 | 16 | 44% | -0.33% | 0.84 |
| LINKUSDT | 125 | 16 | 31% | -0.85% | 0.57 |
| NEARUSDT | 146 | 16 | 50% | +0.97% | 1.48 |
| SUIUSDT | 148 | 18 | 44% | -0.14% | 0.95 |
| APTUSDT | 94 | 8 | 38% | -0.64% | 0.53 |
| DOGEUSDT | 145 | 20 | 50% | +0.34% | 1.15 |
| ARBUSDT | 133 | 17 | 29% | -1.74% | 0.46 |
| OPUSDT | 125 | 11 | 36% | -0.75% | 0.58 |
| INJUSDT | 132 | 13 | 38% | -0.25% | 0.83 |
| FETUSDT | 141 | 16 | 62% | +0.95% | 1.70 |
| TIAUSDT | 146 | 18 | 39% | -0.52% | 0.81 |
| SEIUSDT | 150 | 16 | 31% | -1.04% | 0.51 |
| FILUSDT | 145 | 10 | 40% | -0.33% | 0.78 |

### vol_adaptive_thresh_mut
> ATR-scaled RSI thresholds: widen in high-vol, tighten in low-vol

- **Trades:** 9 (2W / 7L)
- **Win Rate:** 22.2%
- **Avg PnL:** -0.8994%
- **Total Return:** -0.81%
- **Profit Factor:** 0.31
- **Max Drawdown:** 0.8%
- **Sharpe Ratio:** -11.24
- **Avg Hold:** 4.6 bars
- **Exit Mix:** TP=2 | SL=7 | TIME=0
- **Best Trade:** +2.489% | Worst: -2.247%

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 2 | 2 | 0% | -0.28% | 0.00 |
| TAOUSDT | 1 | 1 | 100% | +0.25% | 10.00 |
| AVAXUSDT | 1 | 1 | 0% | -0.13% | 0.00 |
| NEARUSDT | 1 | 1 | 0% | -0.22% | 0.00 |
| DOGEUSDT | 2 | 2 | 50% | -0.10% | 0.55 |
| INJUSDT | 1 | 1 | 0% | -0.15% | 0.00 |
| SEIUSDT | 1 | 1 | 0% | -0.18% | 0.00 |
