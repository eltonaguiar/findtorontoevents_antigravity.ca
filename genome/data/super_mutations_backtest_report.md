# Super Mutations Backtest Report

Generated: 2026-03-14 02:45 UTC

## Configuration
- **Symbols:** 21 pairs
- **Data:** 500 bars of 1h OHLCV from Binance
- **Walk-forward window:** bars 200-500 (300 evaluation bars)
- **Max hold:** 24 bars (24h)
- **TP/SL:** From strategy signals (ATR-based defaults if missing)
- **Fear & Greed context:** Fixed at 25 (moderate fear) for consistency

## Overall Ranking

| Rank | Strategy | Trades | WR% | Total PnL% | Profit Factor | Sharpe | Max DD% |
|------|----------|--------|-----|------------|---------------|--------|---------|
| 1 | genesis_momentum_blend | 467 | 43.7 | +20.90 | 1.04 | 0.02 | 29.75 |
| 2 | multi_system_conviction_filter | 793 | 40.0 | -21.73 | 0.97 | -0.02 | 60.78 |
| 3 | ml_keltner_adaptive | 264 | 34.8 | -8.76 | 0.96 | -0.02 | 21.28 |
| 4 | keltner_rsi_confluence_v2 | 3 | 33.3 | -0.12 | 0.96 | -0.02 | 1.95 |
| - | consensus_deep_value_hybrid | 0 | - | - | - | - | - |

---

## keltner_rsi_confluence_v2
*Keltner squeeze + dual RSI oversold confluence*

**Parents:** keltner_compression_expansion (72.9% WR), multi_period_rsi_confluence (64% WR, Sharpe 10.86)

**Expected WR:** 70%+ | **R:R:** 2.0:1

### Aggregate Stats
- **Trades:** 3 (1W / 2L)
- **Win Rate:** 33.3%
- **Total PnL:** -0.12%
- **Avg PnL/trade:** -0.0417%
- **Profit Factor:** 0.96
- **Sharpe Ratio:** -0.02
- **Max Drawdown:** 1.95%
- **Avg Hold:** 5.0 bars
- **Exits:** TP=1 | SL=2 | Timeout=0
- **Symbols Traded:** 3/21

### Best Symbols
- **SEIUSDT:** +2.76% PnL, 100.0% WR

### Worst Symbols
- **INJUSDT:** -0.94% PnL, 0.0% WR
- **FILUSDT:** -1.95% PnL, 0.0% WR

### Per-Symbol Breakdown
| Symbol | Trades | WR% | PnL% | PF | Avg Hold | TP | SL | TO |
|--------|--------|-----|------|----|----------|----|----|-----|
| FILUSDT | 1 | 0.0 | -1.95 | 0.00 | 3.0 | 0 | 1 | 0 |
| INJUSDT | 1 | 0.0 | -0.94 | 0.00 | 4.0 | 0 | 1 | 0 |
| SEIUSDT | 1 | 100.0 | +2.76 | INF | 8.0 | 1 | 0 | 0 |

---

## consensus_deep_value_hybrid
*Cross-system consensus + RSI capitulation + F&G filter*

**Parents:** rsi_capitulation_sniper (+2.51%, 7.12 PF), cross_aggregation (58.3% WR, +71.4%), fear_greed_contrarian

**Expected WR:** 60%+ | **R:R:** 1.875:1

**No trades generated during backtest period.**
This strategy has very strict entry conditions that were not met.

---

## genesis_momentum_blend
*GENESIS-style multi-indicator scoring + momentum confirmation*

**Parents:** GENESIS genome (+442% PnL), battleground EMA stack, supertrend, ADX

**Expected WR:** 62%+ | **R:R:** 1.33:1

### Aggregate Stats
- **Trades:** 467 (204W / 263L)
- **Win Rate:** 43.7%
- **Total PnL:** +20.90%
- **Avg PnL/trade:** +0.0447%
- **Profit Factor:** 1.04
- **Sharpe Ratio:** 0.02
- **Max Drawdown:** 29.75%
- **Avg Hold:** 7.3 bars
- **Exits:** TP=190 | SL=256 | Timeout=21
- **Symbols Traded:** 21/21

### Best Symbols
- **TAOUSDT:** +21.40% PnL, 58.6% WR
- **FETUSDT:** +15.06% PnL, 57.1% WR
- **SEIUSDT:** +9.27% PnL, 50.0% WR
- **NEARUSDT:** +8.23% PnL, 44.0% WR
- **ETHUSDT:** +3.06% PnL, 45.5% WR

### Worst Symbols
- **FILUSDT:** -5.94% PnL, 36.8% WR
- **SOLUSDT:** -7.04% PnL, 37.5% WR
- **AVAXUSDT:** -7.96% PnL, 36.4% WR

### Per-Symbol Breakdown
| Symbol | Trades | WR% | PnL% | PF | Avg Hold | TP | SL | TO |
|--------|--------|-----|------|----|----------|----|----|-----|
| ADAUSDT | 22 | 40.9 | -1.43 | 0.94 | 5.7 | 9 | 12 | 1 |
| APTUSDT | 20 | 45.0 | +2.70 | 1.12 | 8.2 | 8 | 10 | 2 |
| ARBUSDT | 20 | 45.0 | -0.51 | 0.98 | 8.3 | 8 | 11 | 1 |
| AVAXUSDT | 22 | 36.4 | -7.96 | 0.68 | 8.2 | 7 | 14 | 1 |
| BNBUSDT | 25 | 36.0 | -4.05 | 0.78 | 7.3 | 9 | 16 | 0 |
| BTCUSDT | 23 | 43.5 | +0.98 | 1.05 | 8.0 | 10 | 12 | 1 |
| DOGEUSDT | 24 | 45.8 | +1.46 | 1.06 | 5.8 | 11 | 13 | 0 |
| ETHUSDT | 22 | 45.5 | +3.06 | 1.15 | 7.5 | 9 | 12 | 1 |
| FETUSDT | 21 | 57.1 | +15.06 | 1.73 | 8.4 | 11 | 9 | 1 |
| FILUSDT | 19 | 36.8 | -5.94 | 0.76 | 8.4 | 6 | 12 | 1 |
| INJUSDT | 22 | 36.4 | -5.05 | 0.78 | 7.2 | 8 | 13 | 1 |
| LINKUSDT | 22 | 40.9 | -2.72 | 0.89 | 7.1 | 8 | 13 | 1 |
| LTCUSDT | 18 | 44.4 | +1.21 | 1.09 | 8.4 | 7 | 9 | 2 |
| NEARUSDT | 25 | 44.0 | +8.23 | 1.27 | 6.6 | 11 | 13 | 1 |
| OPUSDT | 19 | 42.1 | -2.40 | 0.90 | 7.9 | 8 | 11 | 0 |
| SEIUSDT | 20 | 50.0 | +9.27 | 1.54 | 7.8 | 10 | 9 | 1 |
| SOLUSDT | 24 | 37.5 | -7.04 | 0.76 | 6.8 | 8 | 15 | 1 |
| SUIUSDT | 24 | 50.0 | +2.70 | 1.09 | 6.6 | 11 | 12 | 1 |
| TAOUSDT | 29 | 58.6 | +21.40 | 1.66 | 7.0 | 14 | 12 | 3 |
| TIAUSDT | 24 | 41.7 | -3.13 | 0.90 | 6.9 | 9 | 14 | 1 |
| XRPUSDT | 22 | 36.4 | -4.95 | 0.77 | 6.1 | 8 | 14 | 0 |

---

## ml_keltner_adaptive
*Claude Gainer ML features + adaptive Keltner channels*

**Parents:** claude_gainer_ml (56.2% WR, +99.5% PnL), keltner_channel_breakout (72.9% WR), atr_volatility_regime (crash protection)

**Expected WR:** 65%+ | **R:R:** adaptive (1.5-2.5:1)

### Aggregate Stats
- **Trades:** 264 (92W / 172L)
- **Win Rate:** 34.8%
- **Total PnL:** -8.76%
- **Avg PnL/trade:** -0.0332%
- **Profit Factor:** 0.96
- **Sharpe Ratio:** -0.02
- **Max Drawdown:** 21.28%
- **Avg Hold:** 5.8 bars
- **Exits:** TP=89 | SL=165 | Timeout=10
- **Symbols Traded:** 21/21

### Best Symbols
- **DOGEUSDT:** +8.86% PnL, 53.8% WR
- **LINKUSDT:** +4.47% PnL, 45.5% WR
- **FETUSDT:** +3.70% PnL, 41.7% WR
- **SEIUSDT:** +3.02% PnL, 40.0% WR
- **ETHUSDT:** +2.29% PnL, 45.5% WR

### Worst Symbols
- **ADAUSDT:** -3.67% PnL, 27.3% WR
- **BTCUSDT:** -4.11% PnL, 25.0% WR
- **INJUSDT:** -7.41% PnL, 25.0% WR

### Per-Symbol Breakdown
| Symbol | Trades | WR% | PnL% | PF | Avg Hold | TP | SL | TO |
|--------|--------|-----|------|----|----------|----|----|-----|
| ADAUSDT | 11 | 27.3 | -3.67 | 0.62 | 5.8 | 3 | 8 | 0 |
| APTUSDT | 13 | 38.5 | +1.35 | 1.12 | 5.9 | 5 | 8 | 0 |
| ARBUSDT | 12 | 25.0 | -3.23 | 0.72 | 4.6 | 3 | 9 | 0 |
| AVAXUSDT | 11 | 27.3 | -3.32 | 0.61 | 5.8 | 3 | 7 | 1 |
| BNBUSDT | 14 | 35.7 | +0.26 | 1.04 | 5.8 | 5 | 8 | 1 |
| BTCUSDT | 16 | 25.0 | -4.11 | 0.62 | 5.9 | 4 | 12 | 0 |
| DOGEUSDT | 13 | 53.8 | +8.86 | 2.27 | 5.5 | 7 | 5 | 1 |
| ETHUSDT | 11 | 45.5 | +2.29 | 1.34 | 7.6 | 5 | 5 | 1 |
| FETUSDT | 12 | 41.7 | +3.70 | 1.39 | 4.9 | 5 | 7 | 0 |
| FILUSDT | 14 | 28.6 | -2.18 | 0.83 | 4.1 | 4 | 10 | 0 |
| INJUSDT | 12 | 25.0 | -7.41 | 0.33 | 7.3 | 2 | 9 | 1 |
| LINKUSDT | 11 | 45.5 | +4.47 | 1.63 | 7.1 | 5 | 5 | 1 |
| LTCUSDT | 10 | 30.0 | -3.27 | 0.54 | 7.6 | 2 | 7 | 1 |
| NEARUSDT | 7 | 28.6 | -2.74 | 0.66 | 5.1 | 2 | 5 | 0 |
| OPUSDT | 12 | 33.3 | -0.60 | 0.94 | 4.7 | 4 | 8 | 0 |
| SEIUSDT | 20 | 40.0 | +3.02 | 1.21 | 5.8 | 8 | 11 | 1 |
| SOLUSDT | 16 | 37.5 | -0.15 | 0.99 | 7.2 | 6 | 10 | 0 |
| SUIUSDT | 14 | 35.7 | +0.77 | 1.06 | 5.9 | 5 | 8 | 1 |
| TAOUSDT | 13 | 30.8 | -2.61 | 0.83 | 4.2 | 4 | 9 | 0 |
| TIAUSDT | 9 | 33.3 | -0.12 | 0.99 | 3.8 | 3 | 6 | 0 |
| XRPUSDT | 13 | 38.5 | -0.10 | 0.99 | 5.7 | 4 | 8 | 1 |

---

## multi_system_conviction_filter
*Meta-strategy requiring 3+ system layers to agree*

**Parents:** battleground (61.7% WR, +158%), rsi_capitulation_sniper (60% WR, 7.12 PF), claude_gainer_ml (56.2% WR, +99.5%), cross_aggregation (58.3% WR, +71.4%), fear_greed_contrarian

**Expected WR:** 65%+ | **R:R:** adaptive (1.5-2.5:1)

### Aggregate Stats
- **Trades:** 793 (317W / 476L)
- **Win Rate:** 40.0%
- **Total PnL:** -21.73%
- **Avg PnL/trade:** -0.0274%
- **Profit Factor:** 0.97
- **Sharpe Ratio:** -0.02
- **Max Drawdown:** 60.78%
- **Avg Hold:** 5.1 bars
- **Exits:** TP=305 | SL=454 | Timeout=34
- **Symbols Traded:** 21/21

### Best Symbols
- **TAOUSDT:** +11.99% PnL, 46.2% WR
- **LINKUSDT:** +5.77% PnL, 42.4% WR
- **ETHUSDT:** +5.20% PnL, 47.1% WR
- **LTCUSDT:** +3.88% PnL, 51.7% WR
- **AVAXUSDT:** +3.48% PnL, 45.0% WR

### Worst Symbols
- **SEIUSDT:** -10.84% PnL, 28.9% WR
- **OPUSDT:** -11.14% PnL, 33.3% WR
- **DOGEUSDT:** -11.94% PnL, 34.0% WR

### Per-Symbol Breakdown
| Symbol | Trades | WR% | PnL% | PF | Avg Hold | TP | SL | TO |
|--------|--------|-----|------|----|----------|----|----|-----|
| ADAUSDT | 35 | 40.0 | +0.30 | 1.01 | 5.5 | 14 | 20 | 1 |
| APTUSDT | 20 | 40.0 | +1.92 | 1.12 | 7.0 | 8 | 10 | 2 |
| ARBUSDT | 35 | 34.3 | -5.22 | 0.85 | 5.5 | 12 | 22 | 1 |
| AVAXUSDT | 40 | 45.0 | +3.48 | 1.14 | 4.8 | 17 | 21 | 2 |
| BNBUSDT | 41 | 43.9 | +1.35 | 1.07 | 4.9 | 17 | 22 | 2 |
| BTCUSDT | 47 | 42.6 | +2.75 | 1.10 | 4.9 | 20 | 26 | 1 |
| DOGEUSDT | 47 | 34.0 | -11.94 | 0.72 | 5.1 | 16 | 29 | 2 |
| ETHUSDT | 34 | 47.1 | +5.20 | 1.26 | 5.0 | 15 | 17 | 2 |
| FETUSDT | 30 | 36.7 | -5.61 | 0.81 | 5.7 | 10 | 18 | 2 |
| FILUSDT | 37 | 37.8 | -3.93 | 0.88 | 5.4 | 13 | 22 | 2 |
| INJUSDT | 43 | 37.2 | -4.57 | 0.87 | 6.0 | 15 | 25 | 3 |
| LINKUSDT | 33 | 42.4 | +5.77 | 1.26 | 5.5 | 14 | 17 | 2 |
| LTCUSDT | 29 | 51.7 | +3.88 | 1.27 | 7.2 | 13 | 14 | 2 |
| NEARUSDT | 37 | 40.5 | +1.23 | 1.03 | 4.9 | 15 | 22 | 0 |
| OPUSDT | 42 | 33.3 | -11.14 | 0.72 | 4.5 | 14 | 28 | 0 |
| SEIUSDT | 38 | 28.9 | -10.84 | 0.66 | 5.8 | 11 | 24 | 3 |
| SOLUSDT | 40 | 40.0 | +2.86 | 1.09 | 4.9 | 16 | 22 | 2 |
| SUIUSDT | 44 | 40.9 | -0.27 | 0.99 | 4.5 | 17 | 25 | 2 |
| TAOUSDT | 52 | 46.2 | +11.99 | 1.23 | 3.7 | 24 | 28 | 0 |
| TIAUSDT | 37 | 40.5 | +0.07 | 1.00 | 4.0 | 15 | 22 | 0 |
| XRPUSDT | 32 | 37.5 | -9.00 | 0.59 | 5.5 | 9 | 20 | 3 |

---

## Summary & Conclusions

- **Total trades across all strategies:** 1527
- **Combined PnL:** -9.71%
- **Best strategy by Sharpe:** genesis_momentum_blend (Sharpe=0.02, WR=43.7%)

**Strategies with 0 trades:** consensus_deep_value_hybrid
These strategies have extremely selective entry conditions (deep RSI oversold, 
Keltner squeeze, multi-layer conviction). This is BY DESIGN -- they wait for 
high-probability setups which may not occur in a 500-bar (21-day) window.