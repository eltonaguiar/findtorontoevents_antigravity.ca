# Weekly winner reverse-engineer — 2026-11-15

Features are as-of each Friday close; the target is the *next* week's return. Nothing is fitted on the week it scores.

## Crypto: this week's top gainers (CoinGecko, top-250 mcap universe)

| # | Coin | 7d % | Mcap $M |
|---|---|---|---|
| 1 | AKE (Akedo) | +78.3 | 237 |
| 2 | OZO (Ozone Chain) | +65.0 | 208 |
| 3 | PIEVERSE (Pieverse) | +26.6 | 515 |
| 4 | KITE (Kite) | +24.2 | 330 |
| 5 | NIGHT (Midnight) | +24.0 | 834 |
| 6 | FF (Falcon Finance) | +11.4 | 341 |
| 7 | JUP (Jupiter) | +10.3 | 884 |
| 8 | CAP (Cap) | +5.5 | 167 |
| 9 | M (MemeCore) | +3.7 | 1923 |
| 10 | BDX (Beldex) | +3.6 | 576 |
| 11 | APEPE (Ape and Pepe) | +2.9 | 254 |
| 12 | WLFI (World Liberty Financia) | +2.5 | 1510 |
| 13 | SPCXB (SpaceX (bStocks Tokeni) | +2.4 | 170 |
| 14 | UB (Unibase) | +2.3 | 267 |
| 15 | JST (JUST) | +1.7 | 1163 |

## Per asset class

### CRYPTO  (37 symbols, 105 weeks, 105 scored)

**This week's actual winners:** ICP-USD +2.8%, FET-USD +0.7%, ARB-USD +0.0%, ATOM-USD -1.2%, AVAX-USD -1.3%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| dollar_vol | +0.103 | +4.67 | 0.276 |
| vol1m | -0.120 | -4.04 | 0.243 |
| dist52 | +0.059 | +1.95 | 0.3 |
| sma50_dist | -0.028 | -1.15 | 0.261 |
| rsi14 | -0.027 | -1.13 | 0.267 |
| volratio | -0.027 | -1.10 | 0.244 |

**Holdout model** (z-sum of `dollar_vol` + `vol1m`, fitted on 52 weeks, tested on 53 unseen weeks): top-5 precision **0.215** vs base rate **0.216** → **1.0x** lift. (train IC -0.0724)

**Next week, by that model:**

| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |
|---|---|---|---|---|---|---|
| BTC-USD | +4.73 | -8.5% | -15.8% | -21.2% | 25 | 1.35 |
| OP-USD | +2.22 | -4.7% | -19.8% | -46.4% | 35 | 0.57 |
| TIA-USD | +1.80 | -6.3% | -28.4% | -44.1% | 36 | 0.92 |
| NEAR-USD | +1.51 | -3.8% | -26.7% | -41.5% | 36 | 0.51 |
| FET-USD | +0.91 | +7.8% | -17.4% | -46.9% | 39 | 0.83 |

Baseline share of names in the top quintile of any week: 0.215.

### EQUITY  (79 symbols, 104 weeks, 104 scored)

**This week's actual winners:** ABNB +15.6%, JD +13.4%, RIVN +11.9%, BABA +11.6%, AMZN +7.9%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| dollar_vol | +0.026 | +1.16 | 0.242 |
| volratio | +0.016 | +1.01 | 0.185 |
| dist52 | +0.021 | +0.90 | 0.198 |
| sma200_dist | +0.017 | +0.66 | 0.308 |
| sma50_dist | +0.014 | +0.63 | 0.298 |
| ret3m | +0.015 | +0.60 | 0.287 |

**Holdout model** (z-sum of `dollar_vol` + `volratio`, fitted on 52 weeks, tested on 52 unseen weeks): top-5 precision **0.219** vs base rate **0.203** → **1.08x** lift. (train IC 0.0072)

**Next week, by that model:**

| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |
|---|---|---|---|---|---|---|
| MU | +5.42 | -22.0% | -33.4% | -43.1% | 31 | 1.73 |
| NVDA | +4.28 | -8.8% | -19.0% | -22.0% | 31 | 1.47 |
| GOOGL | +3.55 | +1.8% | -18.2% | -29.2% | 30 | 2.02 |
| AMD | +3.38 | -11.0% | -27.7% | -30.9% | 38 | 1.83 |
| AAPL | +3.16 | -0.7% | +0.6% | -2.0% | 51 | 1.58 |

Baseline share of names in the top quintile of any week: 0.203.

### ETF  (37 symbols, 104 weeks, 104 scored)

**This week's actual winners:** GDX +13.6%, GDXJ +13.5%, TAN +13.4%, KWEB +9.4%, ICLN +7.4%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| sma200_dist | +0.081 | +2.28 | 0.389 |
| ret3m | +0.067 | +2.08 | 0.356 |
| vol1m | +0.059 | +1.74 | 0.378 |
| sma50_dist | +0.045 | +1.51 | 0.342 |
| volratio | +0.030 | +1.37 | 0.229 |
| ret1m | +0.026 | +0.88 | 0.337 |

**Holdout model** (z-sum of `sma200_dist` + `ret3m`, fitted on 52 weeks, tested on 52 unseen weeks): top-5 precision **0.388** vs base rate **0.216** → **1.8x** lift. (train IC 0.0755)

**Next week, by that model:**

| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |
|---|---|---|---|---|---|---|
| USO | +4.85 | -12.1% | +0.6% | -12.5% | 42 | 1.32 |
| XLV | +3.86 | -0.0% | +9.9% | -2.6% | 63 | 1.26 |
| IBIT | +3.33 | -1.1% | -7.3% | -28.8% | 39 | 1.03 |
| XLP | +2.45 | +0.7% | +8.0% | -2.0% | 60 | 1.44 |
| XLE | +1.78 | -12.0% | -5.5% | -12.0% | 34 | 1.43 |

Baseline share of names in the top quintile of any week: 0.216.

### COMMODITY  (21 symbols, 104 weeks, 104 scored)

**This week's actual winners:** PL=F +7.0%, SI=F +5.5%, GC=F +4.5%, NG=F +3.5%, PA=F +3.0%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| vol1m | -0.050 | -1.96 | 0.309 |
| dist52 | +0.055 | +1.87 | 0.233 |
| volratio | +0.059 | +1.86 | 0.288 |
| rsi14 | -0.025 | -0.77 | 0.241 |
| ret1w | -0.015 | -0.44 | 0.25 |
| sma200_dist | +0.015 | +0.43 | 0.277 |

**Holdout model** (z-sum of `vol1m` + `dist52`, fitted on 52 weeks, tested on 52 unseen weeks): top-5 precision **0.296** vs base rate **0.238** → **1.24x** lift. (train IC -0.0016)

**Next week, by that model:**

| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |
|---|---|---|---|---|---|---|
| BZ=F | +2.28 | -16.4% | -5.7% | -16.9% | 39 | 1.63 |
| CL=F | +1.81 | -12.8% | -0.7% | -19.6% | 42 | 1.36 |
| HO=F | +1.69 | -9.6% | -11.3% | -17.7% | 39 | 1.28 |
| RB=F | +1.49 | -16.2% | -16.3% | -26.4% | 33 | 1.62 |
| SB=F | +0.63 | -5.8% | -9.5% | -13.7% | 37 | 0.99 |

Baseline share of names in the top quintile of any week: 0.238.

### FOREX  (11 symbols, 105 weeks, 104 scored)

**This week's actual winners:** USDCHF=X +2.5%, USDCAD=X +1.7%, USDJPY=X +1.5%, EURGBP=X +0.1%, EURJPY=X -0.1%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| ret1m | -0.084 | -1.76 | 0.25 |
| ret1w | -0.077 | -1.38 | 0.233 |
| vol1m | +0.040 | +1.23 | 0.31 |
| sma50_dist | -0.059 | -1.16 | 0.25 |
| rsi14 | -0.047 | -0.98 | 0.26 |
| volratio | +0.026 | +0.76 | 0.291 |

**Holdout model** (z-sum of `ret1m` + `ret1w`, fitted on 52 weeks, tested on 52 unseen weeks): top-5 precision **0.25** vs base rate **0.273** → **0.92x** lift. (train IC -0.1519)

Baseline share of names in the top quintile of any week: 0.273.

### BOND  (13 symbols, 104 weeks, 104 scored)

**This week's actual winners:** MUB +1.0%, ZB=F +0.8%, BNDX +0.7%, LQD +0.6%, AGG +0.5%

| feature | mean rank-IC | t | top-5 precision |
|---|---|---|---|
| dollar_vol | +0.107 | +3.71 | 0.24 |
| sma200_dist | +0.052 | +1.06 | 0.242 |
| rsi14 | +0.040 | +0.89 | 0.254 |
| vol1m | +0.051 | +0.83 | 0.299 |
| sma50_dist | +0.025 | +0.50 | 0.246 |
| dist52 | +0.019 | +0.32 | 0.231 |

**Holdout model** (z-sum of `dollar_vol` + `sma200_dist`, fitted on 52 weeks, tested on 52 unseen weeks): top-5 precision **0.296** vs base rate **0.231** → **1.28x** lift. (train IC 0.0846)

**Next week, by that model:**

| symbol | z | 1w | 1m | vs 52w high | RSI | vol ratio |
|---|---|---|---|---|---|---|
| HYG | +2.26 | +0.3% | +0.6% | -1.9% | 55 | 1.32 |
| LQD | +1.46 | +0.6% | +2.4% | -3.1% | 65 | 0.69 |
| MUB | +1.06 | +1.0% | +4.4% | -1.4% | 78 | 0.58 |
| SHY | +0.83 | +0.2% | +0.8% | -0.0% | 73 | 1.00 |
| TLT | +0.78 | +0.5% | +5.6% | -6.6% | 64 | 0.77 |

Baseline share of names in the top quintile of any week: 0.231.

---
Sample-size warning: a 5-name top-5 is 5 observations per week; the holdout column is the only
number worth trusting, and even it needs ~30+ weeks before it separates from luck.
