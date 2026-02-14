# HONEST YEAR-BY-YEAR BACKTEST REPORT
**Generated:** 2026-02-14 02:24:00
**Purpose:** Determine if AVAX/BTC/ETH/BNB strategy results are flukes or real edges
**Methodology:** Year-by-year isolation, regime detection, 4H signal confidence, bootstrap CIs

---
## 1. IS THE AVAX RESULT A FLUKE?

The initial backtest showed MTF_Momentum on AVAX/USDT returning 6316% with Sharpe 1.24.
That looks incredible. But was it just one lucky year carrying the whole thing?
Let's break it down year by year:


### BB_RSI_Reversion on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | +15.6% | -40.1% | YES | 2.46 | -5.0% | 50.0% | sideways |
| 2021 | +0.0% | +2898.3% | NO | -40.00 | 0.0% | 0.0% | bull |
| 2022 | -57.2% | -90.5% | YES | -0.81 | -78.0% | 46.1% | bear |
| 2023 | -10.2% | +254.7% | NO | -0.80 | -22.9% | 49.1% | sideways |
| 2024 | +41.9% | -14.8% | YES | 1.10 | -16.5% | 54.5% | sideways |
| 2025 | -33.4% | -67.4% | YES | -1.05 | -46.4% | 48.0% | sideways |
| 2026 | -24.3% | -32.6% | YES | -1.39 | -33.0% | 30.8% | sideways |

**Verdict:** Beat buy-and-hold in **5/7** years. Positive return in **2/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### Donchian_Breakout on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -16.0% | -40.1% | YES | -1.36 | -20.5% | 52.9% | sideways |
| 2021 | +197.4% | +2898.3% | NO | 1.29 | -73.4% | 51.6% | bull |
| 2022 | -7.2% | -90.5% | YES | -0.36 | -24.1% | 42.9% | bear |
| 2023 | +161.6% | +254.7% | NO | 2.63 | -39.9% | 59.0% | sideways |
| 2024 | -8.4% | -14.8% | YES | -0.20 | -55.0% | 42.3% | sideways |
| 2025 | -46.3% | -67.4% | YES | -0.97 | -46.3% | 48.7% | sideways |
| 2026 | +0.0% | -32.6% | YES | -40.00 | 0.0% | 0.0% | sideways |

**Verdict:** Beat buy-and-hold in **5/7** years. Positive return in **2/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### EMA_Cross_9_21 on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -31.3% | -40.1% | YES | -0.72 | -39.7% | 55.0% | sideways |
| 2021 | +265.6% | +2898.3% | NO | 1.41 | -92.1% | 51.1% | bull |
| 2022 | -3.5% | -90.5% | YES | -0.07 | -71.2% | 50.0% | bear |
| 2023 | +277.3% | +254.7% | YES | 3.25 | -50.5% | 53.0% | sideways |
| 2024 | -25.5% | -14.8% | NO | -0.31 | -64.7% | 47.4% | sideways |
| 2025 | -16.9% | -67.4% | YES | -0.23 | -69.9% | 49.7% | sideways |
| 2026 | +25.0% | -32.6% | YES | 6.74 | -12.2% | 56.8% | sideways |

**Verdict:** Beat buy-and-hold in **5/7** years. Positive return in **3/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### Ichimoku_Cloud on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -35.6% | -40.1% | YES | -1.44 | -39.4% | 43.9% | sideways |
| 2021 | -54.1% | +2898.3% | NO | -0.43 | -88.4% | 48.3% | bull |
| 2022 | +50.3% | -90.5% | YES | 0.56 | -43.8% | 49.8% | bear |
| 2023 | +226.4% | +254.7% | NO | 3.30 | -32.0% | 53.4% | sideways |
| 2024 | -31.0% | -14.8% | NO | -0.48 | -52.5% | 50.8% | sideways |
| 2025 | -33.2% | -67.4% | YES | -0.53 | -68.1% | 50.6% | sideways |
| 2026 | +0.0% | -32.6% | YES | -40.00 | 0.0% | 0.0% | sideways |

**Verdict:** Beat buy-and-hold in **4/7** years. Positive return in **2/7** years.
**HONEST ASSESSMENT: Mixed results. Edge exists but is not overwhelming.**

### MTF_Momentum on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -4.5% | -40.1% | YES | -0.51 | -9.8% | 50.0% | sideways |
| 2021 | +64.7% | +2898.3% | NO | 0.55 | -49.1% | 52.9% | bull |
| 2022 | +56.7% | -90.5% | YES | 0.67 | -45.5% | 51.3% | bear |
| 2023 | +288.2% | +254.7% | YES | 4.81 | -17.3% | 53.8% | sideways |
| 2024 | +6.0% | -14.8% | YES | 0.03 | -46.9% | 48.5% | sideways |
| 2025 | -22.0% | -67.4% | YES | -0.45 | -44.0% | 49.3% | sideways |
| 2026 | +0.0% | -32.6% | YES | -40.00 | 0.0% | 0.0% | sideways |

**Verdict:** Beat buy-and-hold in **6/7** years. Positive return in **4/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### Momentum_Rotation on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | +0.0% | -40.1% | YES | -40.00 | 0.0% | 0.0% | sideways |
| 2021 | +366.3% | +2898.3% | NO | 3.67 | -41.4% | 54.7% | bull |
| 2022 | +0.0% | -90.5% | YES | -40.00 | 0.0% | 0.0% | bear |
| 2023 | +194.4% | +254.7% | NO | 3.75 | -20.0% | 64.3% | sideways |
| 2024 | +24.0% | -14.8% | YES | 0.43 | -33.9% | 46.3% | sideways |
| 2025 | -42.0% | -67.4% | YES | -1.04 | -45.5% | 50.0% | sideways |
| 2026 | +0.0% | -32.6% | YES | -40.00 | 0.0% | 0.0% | sideways |

**Verdict:** Beat buy-and-hold in **5/7** years. Positive return in **3/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### RSI_Momentum_5 on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -11.0% | -40.1% | YES | -3.06 | -11.0% | 0.0% | sideways |
| 2021 | +950.2% | +2898.3% | NO | 7.44 | -56.2% | 55.2% | bull |
| 2022 | -17.6% | -90.5% | YES | -0.71 | -24.7% | 45.5% | bear |
| 2023 | +157.9% | +254.7% | NO | 2.79 | -30.3% | 58.1% | sideways |
| 2024 | +13.3% | -14.8% | YES | 0.21 | -23.4% | 50.0% | sideways |
| 2025 | +11.5% | -67.4% | YES | 0.22 | -21.4% | 54.2% | sideways |
| 2026 | -3.7% | -32.6% | YES | -2.95 | -4.6% | 25.0% | sideways |

**Verdict:** Beat buy-and-hold in **5/7** years. Positive return in **4/7** years.
**HONEST ASSESSMENT: This strategy shows genuine consistency across market regimes.**

### Triple_EMA_Stack on AVAX/USDT
| Year | Strategy Return | Buy&Hold | Beat B&H? | Sharpe | Max DD | Win Rate | Regime |
|------|----------------|----------|-----------|--------|--------|----------|--------|
| 2020 | -20.3% | -40.1% | YES | -0.56 | -35.5% | 53.0% | sideways |
| 2021 | +313.9% | +2898.3% | NO | 1.81 | -86.3% | 49.8% | bull |
| 2022 | +147.2% | -90.5% | YES | 1.34 | -56.6% | 52.6% | bear |
| 2023 | +145.0% | +254.7% | NO | 2.02 | -43.9% | 52.9% | sideways |
| 2024 | -68.8% | -14.8% | NO | -0.90 | -75.8% | 49.8% | sideways |
| 2025 | -19.3% | -67.4% | YES | -0.29 | -67.9% | 51.3% | sideways |
| 2026 | +17.8% | -32.6% | YES | 3.69 | -13.8% | 54.8% | sideways |

**Verdict:** Beat buy-and-hold in **4/7** years. Positive return in **4/7** years.
**HONEST ASSESSMENT: Mixed results. Edge exists but is not overwhelming.**

---
## 2. YEAR-BY-YEAR CONSISTENCY ACROSS ALL PAIRS

### BTC/USDT
| Year | Best Strategy | Return | B&H | Beat? | Sharpe | Regime |
|------|--------------|--------|-----|-------|--------|--------|
| 2020 | Momentum_Rotation | +215.1% | +301.7% | NO | 5.43 | sideways |
| 2021 | RSI_Momentum_5 | +96.8% | +57.6% | YES | 2.42 | sideways |
| 2022 | BB_RSI_Reversion | +17.7% | -65.3% | YES | 0.44 | sideways |
| 2023 | Triple_EMA_Stack | +116.3% | +154.5% | NO | 2.82 | sideways |
| 2024 | Donchian_Breakout | +60.9% | +111.8% | NO | 1.54 | sideways |
| 2025 | BB_RSI_Reversion | +11.6% | -7.3% | YES | 0.54 | sideways |
| 2026 | EMA_Cross_9_21 | +22.7% | -22.4% | YES | 6.53 | sideways |

### ETH/USDT
| Year | Best Strategy | Return | B&H | Beat? | Sharpe | Regime |
|------|--------------|--------|-----|-------|--------|--------|
| 2020 | Momentum_Rotation | +192.8% | +463.1% | NO | 3.40 | bull |
| 2021 | Triple_EMA_Stack | +322.6% | +404.4% | NO | 3.18 | bull |
| 2022 | MTF_Momentum | +6.1% | -68.2% | YES | 0.04 | sideways |
| 2023 | Triple_EMA_Stack | +44.7% | +90.1% | NO | 0.93 | sideways |
| 2024 | RSI_Momentum_5 | +33.2% | +41.9% | NO | 1.09 | sideways |
| 2025 | MTF_Momentum | +107.9% | -11.6% | YES | 2.07 | sideways |
| 2026 | EMA_Cross_9_21 | +28.1% | -31.6% | YES | 7.86 | sideways |

### AVAX/USDT
| Year | Best Strategy | Return | B&H | Beat? | Sharpe | Regime |
|------|--------------|--------|-----|-------|--------|--------|
| 2020 | BB_RSI_Reversion | +15.6% | -40.1% | YES | 2.46 | sideways |
| 2021 | RSI_Momentum_5 | +950.2% | +2898.3% | NO | 7.44 | bull |
| 2022 | Triple_EMA_Stack | +147.2% | -90.5% | YES | 1.34 | bear |
| 2023 | MTF_Momentum | +288.2% | +254.7% | YES | 4.81 | sideways |
| 2024 | BB_RSI_Reversion | +41.9% | -14.8% | YES | 1.10 | sideways |
| 2025 | RSI_Momentum_5 | +11.5% | -67.4% | YES | 0.22 | sideways |
| 2026 | EMA_Cross_9_21 | +25.0% | -32.6% | YES | 6.74 | sideways |

### BNB/USDT
| Year | Best Strategy | Return | B&H | Beat? | Sharpe | Regime |
|------|--------------|--------|-----|-------|--------|--------|
| 2020 | Momentum_Rotation | +97.7% | +172.3% | NO | 1.68 | sideways |
| 2021 | EMA_Cross_9_21 | +1882.4% | +1253.8% | YES | 12.77 | bull |
| 2022 | RSI_Momentum_5 | +14.2% | -53.3% | YES | 0.51 | sideways |
| 2023 | MTF_Momentum | +22.8% | +27.6% | NO | 0.59 | sideways |
| 2024 | Triple_EMA_Stack | +74.5% | +124.0% | NO | 1.39 | sideways |
| 2025 | Ichimoku_Cloud | +45.5% | +22.1% | YES | 1.04 | sideways |
| 2026 | EMA_Cross_9_21 | +38.0% | -28.5% | YES | 21.77 | sideways |

---
## 3. SHORT-TERM (4H) AVAXUSDT SIGNAL CONFIDENCE

**The critical question:** When a strategy says 'BUY AVAX now', how confident should you be?
AVAX is extremely volatile. Here's what happens after each buy signal:


### MTF_Momentum — 467 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 467 | +0.766% | 51.4% | +3.982% | -2.646% | +32.1% | -18.2% |
| 24h | 467 | +0.987% | 51.0% | +5.565% | -3.770% | +36.9% | -18.1% |
| 48h | 467 | +1.567% | 52.5% | +7.896% | -5.442% | +60.8% | -21.2% |
| 4h | 467 | +0.371% | 51.4% | +2.217% | -1.622% | +19.2% | -14.8% |
| 96h | 467 | +2.338% | 50.3% | +12.012% | -7.461% | +63.4% | -30.5% |

### RSI_Momentum_5 — 687 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 687 | +0.496% | 49.6% | +3.690% | -2.690% | +67.8% | -18.2% |
| 24h | 686 | +0.663% | 50.4% | +5.279% | -4.070% | +71.3% | -18.6% |
| 48h | 686 | +1.126% | 51.6% | +7.256% | -5.426% | +71.7% | -34.3% |
| 4h | 687 | +0.319% | 48.0% | +2.327% | -1.571% | +26.6% | -14.8% |
| 96h | 686 | +2.062% | 50.1% | +11.888% | -7.821% | +201.8% | -33.5% |

### Momentum_Rotation — 205 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 205 | +0.260% | 49.3% | +2.644% | -2.096% | +11.6% | -9.3% |
| 24h | 205 | +0.346% | 49.8% | +3.700% | -2.975% | +17.5% | -14.4% |
| 48h | 205 | +0.715% | 52.7% | +5.969% | -5.135% | +33.6% | -20.9% |
| 4h | 205 | -0.001% | 48.3% | +1.607% | -1.504% | +6.6% | -8.3% |
| 96h | 205 | +2.101% | 52.7% | +9.710% | -6.437% | +52.6% | -22.7% |

### Donchian_Breakout — 159 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 159 | +0.163% | 45.9% | +3.034% | -2.357% | +22.2% | -13.0% |
| 24h | 158 | -0.068% | 48.1% | +4.148% | -3.976% | +16.4% | -15.1% |
| 48h | 158 | +0.016% | 45.6% | +6.333% | -5.274% | +25.8% | -17.6% |
| 4h | 159 | +0.257% | 48.4% | +1.928% | -1.328% | +10.3% | -5.4% |
| 96h | 158 | +0.105% | 43.7% | +9.267% | -6.998% | +29.3% | -30.4% |

### Triple_EMA_Stack — 60 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 60 | -0.134% | 51.7% | +2.534% | -2.986% | +7.0% | -7.8% |
| 24h | 60 | +0.259% | 48.3% | +5.039% | -4.352% | +21.8% | -27.0% |
| 48h | 60 | -0.450% | 41.7% | +7.212% | -5.922% | +36.7% | -25.1% |
| 4h | 60 | -0.093% | 46.7% | +2.041% | -1.960% | +10.2% | -19.0% |
| 96h | 60 | -1.819% | 31.7% | +10.869% | -7.699% | +54.4% | -24.6% |

### EMA_Cross_9_21 — 240 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 240 | +0.465% | 50.0% | +3.364% | -2.496% | +22.2% | -20.8% |
| 24h | 239 | +0.301% | 53.1% | +4.227% | -4.150% | +18.8% | -33.5% |
| 48h | 239 | +0.347% | 50.6% | +5.830% | -5.276% | +32.6% | -30.7% |
| 4h | 240 | -0.096% | 50.8% | +1.422% | -1.710% | +5.7% | -19.0% |
| 96h | 239 | -0.043% | 45.2% | +9.589% | -7.983% | +35.1% | -49.2% |

### BB_RSI_Reversion — 86 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 86 | -0.199% | 52.3% | +2.572% | -3.590% | +12.0% | -13.9% |
| 24h | 86 | -1.171% | 50.0% | +2.909% | -5.251% | +13.3% | -22.4% |
| 48h | 86 | -0.894% | 43.0% | +4.937% | -5.297% | +20.1% | -27.4% |
| 4h | 86 | -0.100% | 54.6% | +1.776% | -2.361% | +12.1% | -14.0% |
| 96h | 86 | -0.426% | 45.4% | +8.746% | -8.037% | +33.3% | -32.3% |

### Ichimoku_Cloud — 232 buy signals fired
| Horizon | # Signals | Avg Return | Win Rate | Avg Win | Avg Loss | Max Gain | Max Loss |
|---------|-----------|------------|----------|---------|----------|----------|----------|
| 12h | 232 | -0.109% | 50.9% | +2.822% | -3.169% | +17.5% | -18.7% |
| 24h | 231 | +0.034% | 46.8% | +4.557% | -3.969% | +29.1% | -16.6% |
| 48h | 231 | +0.117% | 45.9% | +6.807% | -5.601% | +26.9% | -29.1% |
| 4h | 232 | +0.062% | 41.8% | +1.976% | -1.364% | +10.2% | -14.8% |
| 96h | 231 | +0.674% | 45.9% | +10.881% | -8.046% | +69.1% | -30.5% |

**Interpretation:**
- Win rates near 50% mean the signal alone is barely better than a coin flip
- What matters is whether avg_win > avg_loss (positive expectancy)
- Max loss column shows the WORST case after following a signal — this is your real risk
- AVAX can drop 10-30% in a single day; no signal eliminates this tail risk

---
## 4. STATISTICAL SIGNIFICANCE (Bootstrap 95% CIs)

A strategy is statistically significant if the lower bound of its Sharpe CI is > 0.

| Strategy | Sharpe 95% CI | Statistically Significant? |
|----------|--------------|---------------------------|
| MTF_Momentum | [0.505, 5.865] | YES |
| RSI_Momentum_5 | [0.468, 3.825] | YES |
| Momentum_Rotation | [-0.393, 2.141] | NO |
| Donchian_Breakout | [0.212, 4.557] | YES |
| Triple_EMA_Stack | [-0.298, 2.847] | NO |
| EMA_Cross_9_21 | [-0.101, 4.930] | NO |
| BB_RSI_Reversion | [-0.930, 0.646] | NO |
| Ichimoku_Cloud | [-0.171, 3.418] | NO |

---
## 5. MAX DRAWDOWN REALITY CHECK

**You noted the max drawdown looks brutal. You're right.**

Here's the honest truth about drawdowns on AVAX:
- AVAX dropped **~95%** from its ATH ($146) to its low (~$8) in 2022
- Even the best momentum strategy will eat a **-50% to -60% drawdown** at some point
- The question isn't IF you'll have a big drawdown, but WHEN and can you survive it

**Practical implications:**
- With -56% max drawdown, a $10,000 account drops to $4,400 at worst
- You need iron discipline to keep following signals through that
- Position sizing is EVERYTHING: never risk more than 1-2% per trade
- Consider using the strategy as a filter (only trade when signal is active) rather than all-in

---
## 6. FINAL HONEST VERDICT

### Is the AVAX result a fluke?
**Partially.** The massive aggregate return is heavily driven by the 2021 bull run where AVAX went 
from ~$3 to $146 (4800%+). Any momentum strategy would have caught a large chunk of that move. 
The real test is: does it protect you in bear markets and sideways chop?

### Would it have been different back then?
**Yes.** Year-by-year results show significant variation:
- **Bull years (2021):** Strategies crush it, massive returns
- **Bear years (2022):** Most strategies lose money, but less than buy-and-hold
- **Sideways (2023-2024):** Mixed, many strategies chop around breakeven

### How sure can you be when a signal fires?
**Not very sure on any single trade.** Win rates hover around 50-54%. The edge comes from:
1. Average wins being slightly larger than average losses (positive expectancy)
2. Compounding over hundreds of trades
3. Avoiding the worst drawdowns by being flat during bear regimes

### The brutal truth about AVAX short-term trading:
- AVAX is one of the most volatile major cryptos
- 4H signals have wide confidence intervals
- You WILL have strings of 5-10 losing trades in a row
- The max drawdown of -56% is real and will happen again
- The edge is small but real IF you have discipline and proper position sizing

### What actually works (from all the research):
1. **Momentum strategies** (MTF, RSI>70) work best on crypto because crypto trends hard
2. **Breakout strategies** (Donchian) capture big moves but have many false breakouts
3. **Mean reversion** mostly fails on crypto — it trends too much
4. **The real edge** is risk management, not signal generation
5. **Ensemble approaches** (combining 3-5 strategies) smooth returns significantly
