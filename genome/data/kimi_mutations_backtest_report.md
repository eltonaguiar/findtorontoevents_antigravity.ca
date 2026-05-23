# KIMI Supplemental Mutations — Backtest Report

**Run:** 2026-03-14T02:34:46.120530+00:00
**Universe:** 21 symbols | 1h interval | 500 bars
**Window:** Bar 200..500
**Costs:** 0.1% commission + 0.05% slippage per side

---

## Summary Table

| Strategy | Trades | Win Rate | Avg PnL | Total Ret | PF | MaxDD | Sharpe | Gate |
|----------|--------|----------|---------|-----------|-----|-------|--------|------|
| volume_profile_funding_snap | 247 | 36.4% | -0.441% | -10.38% | 0.68 | 10.8% | -3.47 | FAIL |
| cross_agg_battleground_hybrid | 113 | 50.4% | +0.242% | +2.74% | 1.23 | 2.0% | 1.89 | PASS |
| drawdown_volatility_expansion | 3 | 66.7% | +2.611% | +0.78% | 5.96 | 0.2% | 16.79 | FAIL |
| ema_ribbon_macd_divergence | 368 | 28.5% | -0.393% | -13.55% | 0.64 | 13.9% | -3.69 | FAIL |
| vwap_bollinger_squeeze | 402 | 38.1% | -0.361% | -13.61% | 0.70 | 14.1% | -3.19 | FAIL |

---

## Per-Strategy Detail

### volume_profile_funding_snap
> Volume Profile POC breakout + funding rate alignment

- **Trades:** 247 (90W / 157L)
- **Win Rate:** 36.4%
- **Avg PnL:** -0.4407%
- **Total Return:** -10.38%
- **Profit Factor:** 0.68
- **Max Drawdown:** 10.8%
- **Sharpe Ratio:** -3.47
- **Avg Hold:** 8.0 bars
- **Exit Mix:** TP=77 | SL=152 | TIME=18
- **Best Trade:** +5.456% | Worst: -3.550%
- **Symbols Active:** 21 / 21

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 10 | 9 | 33% | -0.30% | 0.71 |
| ETHUSDT | 14 | 14 | 36% | -0.60% | 0.65 |
| BNBUSDT | 14 | 12 | 58% | +0.43% | 1.58 |
| SOLUSDT | 16 | 13 | 31% | -0.80% | 0.61 |
| XRPUSDT | 18 | 12 | 33% | -0.46% | 0.66 |
| LTCUSDT | 22 | 13 | 31% | -0.73% | 0.49 |
| ADAUSDT | 10 | 8 | 50% | +0.08% | 1.09 |
| TAOUSDT | 21 | 14 | 29% | -1.23% | 0.57 |
| AVAXUSDT | 18 | 12 | 58% | +0.49% | 1.52 |
| LINKUSDT | 15 | 11 | 36% | -0.36% | 0.76 |
| NEARUSDT | 17 | 8 | 50% | +0.59% | 1.70 |
| SUIUSDT | 23 | 15 | 47% | +0.34% | 1.18 |
| APTUSDT | 15 | 13 | 23% | -1.43% | 0.44 |
| DOGEUSDT | 11 | 6 | 50% | +0.10% | 1.19 |
| ARBUSDT | 15 | 13 | 31% | -1.36% | 0.43 |
| OPUSDT | 18 | 10 | 50% | +0.06% | 1.05 |
| INJUSDT | 21 | 13 | 31% | -0.91% | 0.47 |
| FETUSDT | 20 | 14 | 36% | -0.99% | 0.53 |
| TIAUSDT | 19 | 13 | 23% | -1.42% | 0.43 |
| SEIUSDT | 17 | 12 | 25% | -0.96% | 0.45 |
| FILUSDT | 22 | 12 | 25% | -1.41% | 0.32 |

### cross_agg_battleground_hybrid
> Multi-system RSI consensus + volume + momentum

- **Trades:** 113 (57W / 56L)
- **Win Rate:** 50.4%
- **Avg PnL:** +0.2422%
- **Total Return:** +2.74%
- **Profit Factor:** 1.23
- **Max Drawdown:** 2.0%
- **Sharpe Ratio:** 1.89
- **Avg Hold:** 9.1 bars
- **Exit Mix:** TP=55 | SL=48 | TIME=10
- **Best Trade:** +4.519% | Worst: -3.950%
- **Symbols Active:** 21 / 21

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 3 | 3 | 67% | +0.03% | 1.16 |
| ETHUSDT | 4 | 3 | 33% | -0.28% | 0.43 |
| BNBUSDT | 8 | 6 | 33% | -0.18% | 0.60 |
| SOLUSDT | 3 | 3 | 33% | -0.20% | 0.53 |
| XRPUSDT | 5 | 5 | 40% | +0.13% | 1.36 |
| LTCUSDT | 5 | 3 | 67% | +0.21% | 2.15 |
| ADAUSDT | 6 | 6 | 33% | -0.21% | 0.75 |
| TAOUSDT | 14 | 10 | 50% | +0.40% | 1.31 |
| AVAXUSDT | 6 | 6 | 33% | -0.24% | 0.66 |
| LINKUSDT | 3 | 3 | 67% | +0.32% | 2.44 |
| NEARUSDT | 6 | 5 | 20% | -0.82% | 0.21 |
| SUIUSDT | 6 | 6 | 67% | +0.67% | 2.23 |
| APTUSDT | 6 | 6 | 67% | +0.54% | 2.07 |
| DOGEUSDT | 8 | 7 | 57% | +0.48% | 1.99 |
| ARBUSDT | 8 | 7 | 86% | +1.20% | 5.62 |
| OPUSDT | 9 | 8 | 88% | +1.59% | 7.94 |
| INJUSDT | 7 | 6 | 0% | -1.15% | 0.00 |
| FETUSDT | 9 | 9 | 33% | -0.82% | 0.44 |
| TIAUSDT | 7 | 5 | 60% | +0.42% | 1.96 |
| SEIUSDT | 3 | 2 | 100% | +0.50% | 10.00 |
| FILUSDT | 4 | 4 | 50% | +0.16% | 1.42 |

### drawdown_volatility_expansion
> Drawdown recovery with ATR expansion + RSI filter

- **Trades:** 3 (2W / 1L)
- **Win Rate:** 66.7%
- **Avg PnL:** +2.6109%
- **Total Return:** +0.78%
- **Profit Factor:** 5.96
- **Max Drawdown:** 0.2%
- **Sharpe Ratio:** 16.79
- **Avg Hold:** 20.0 bars
- **Exit Mix:** TP=2 | SL=0 | TIME=1
- **Best Trade:** +4.962% | Worst: -1.581%
- **Symbols Active:** 3 / 21

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| TAOUSDT | 1 | 1 | 100% | +0.50% | 10.00 |
| INJUSDT | 1 | 1 | 0% | -0.16% | 0.00 |
| TIAUSDT | 1 | 1 | 100% | +0.45% | 10.00 |

### ema_ribbon_macd_divergence
> EMA 9/21/50 ribbon + MACD histogram divergence

- **Trades:** 368 (105W / 263L)
- **Win Rate:** 28.5%
- **Avg PnL:** -0.3934%
- **Total Return:** -13.55%
- **Profit Factor:** 0.64
- **Max Drawdown:** 13.9%
- **Sharpe Ratio:** -3.69
- **Avg Hold:** 6.8 bars
- **Exit Mix:** TP=97 | SL=247 | TIME=24
- **Best Trade:** +6.250% | Worst: -6.696%
- **Symbols Active:** 21 / 21

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 29 | 17 | 53% | +0.38% | 1.34 |
| ETHUSDT | 30 | 18 | 22% | -1.25% | 0.38 |
| BNBUSDT | 26 | 14 | 43% | +0.21% | 1.33 |
| SOLUSDT | 27 | 13 | 46% | +0.58% | 1.61 |
| XRPUSDT | 33 | 22 | 23% | -0.85% | 0.55 |
| LTCUSDT | 27 | 19 | 26% | -0.66% | 0.56 |
| ADAUSDT | 31 | 19 | 32% | -0.86% | 0.59 |
| TAOUSDT | 28 | 18 | 33% | -0.86% | 0.75 |
| AVAXUSDT | 37 | 19 | 37% | -0.03% | 0.98 |
| LINKUSDT | 32 | 16 | 12% | -1.30% | 0.24 |
| NEARUSDT | 37 | 19 | 37% | +0.37% | 1.18 |
| SUIUSDT | 26 | 19 | 32% | -0.77% | 0.70 |
| APTUSDT | 32 | 18 | 11% | -1.70% | 0.24 |
| DOGEUSDT | 32 | 19 | 32% | -0.09% | 0.94 |
| ARBUSDT | 24 | 14 | 21% | -1.27% | 0.36 |
| OPUSDT | 26 | 14 | 14% | -1.45% | 0.22 |
| INJUSDT | 34 | 18 | 33% | -0.40% | 0.77 |
| FETUSDT | 34 | 16 | 44% | +0.44% | 1.27 |
| TIAUSDT | 31 | 18 | 17% | -2.14% | 0.29 |
| SEIUSDT | 30 | 17 | 18% | -1.85% | 0.26 |
| FILUSDT | 33 | 21 | 19% | -0.94% | 0.52 |

### vwap_bollinger_squeeze
> VWAP mean reversion during Bollinger Band squeeze

- **Trades:** 402 (153W / 249L)
- **Win Rate:** 38.1%
- **Avg PnL:** -0.3614%
- **Total Return:** -13.61%
- **Profit Factor:** 0.70
- **Max Drawdown:** 14.1%
- **Sharpe Ratio:** -3.19
- **Avg Hold:** 8.3 bars
- **Exit Mix:** TP=144 | SL=233 | TIME=25
- **Best Trade:** +4.045% | Worst: -3.695%
- **Symbols Active:** 21 / 21

| Symbol | Signals | Trades | WR | Return | PF |
|--------|---------|--------|-----|--------|-----|
| BTCUSDT | 75 | 18 | 28% | -1.29% | 0.37 |
| ETHUSDT | 66 | 20 | 45% | +0.23% | 1.12 |
| BNBUSDT | 62 | 22 | 27% | -1.42% | 0.34 |
| SOLUSDT | 70 | 22 | 45% | -0.08% | 0.97 |
| XRPUSDT | 53 | 17 | 59% | +0.42% | 1.34 |
| LTCUSDT | 44 | 16 | 31% | -0.90% | 0.48 |
| ADAUSDT | 76 | 19 | 32% | -1.14% | 0.55 |
| TAOUSDT | 76 | 23 | 52% | +0.80% | 1.28 |
| AVAXUSDT | 73 | 20 | 35% | -1.01% | 0.58 |
| LINKUSDT | 62 | 18 | 39% | -0.68% | 0.71 |
| NEARUSDT | 77 | 14 | 29% | -1.54% | 0.40 |
| SUIUSDT | 64 | 22 | 50% | -0.01% | 1.00 |
| APTUSDT | 51 | 15 | 53% | +1.06% | 1.78 |
| DOGEUSDT | 83 | 17 | 29% | -1.12% | 0.50 |
| ARBUSDT | 80 | 19 | 37% | -1.09% | 0.59 |
| OPUSDT | 73 | 18 | 39% | -0.68% | 0.70 |
| INJUSDT | 64 | 20 | 35% | -0.91% | 0.62 |
| FETUSDT | 80 | 20 | 30% | -1.67% | 0.46 |
| TIAUSDT | 59 | 20 | 35% | -1.19% | 0.60 |
| SEIUSDT | 71 | 19 | 32% | -1.10% | 0.56 |
| FILUSDT | 81 | 23 | 35% | -1.18% | 0.61 |

---

## Quality Gates

| Strategy | WR>=45% | Sharpe>=0.5 | PF>=1.0 | Trades>=5 | DD<=20% | +E[PnL] | RESULT |
|----------|---------|-------------|---------|-----------|---------|---------|--------|
| volume_profile_funding_snap | N | N | N | Y | Y | N | **FAIL** |
| cross_agg_battleground_hybrid | Y | Y | Y | Y | Y | Y | **PASS** |
| drawdown_volatility_expansion | Y | Y | Y | N | Y | Y | **FAIL** |
| ema_ribbon_macd_divergence | N | N | N | Y | Y | N | **FAIL** |
| vwap_bollinger_squeeze | N | N | N | Y | Y | N | **FAIL** |

---

## Ranking (by Total Return)

1. **cross_agg_battleground_hybrid** — Ret=+2.74% | WR=50.4% | Sharpe=1.89
2. **drawdown_volatility_expansion** — Ret=+0.78% | WR=66.7% | Sharpe=16.79
3. **volume_profile_funding_snap** — Ret=-10.38% | WR=36.4% | Sharpe=-3.47
4. **ema_ribbon_macd_divergence** — Ret=-13.55% | WR=28.5% | Sharpe=-3.69
5. **vwap_bollinger_squeeze** — Ret=-13.61% | WR=38.1% | Sharpe=-3.19

---
*Generated 2026-03-14T02:34:46.120530+00:00*
