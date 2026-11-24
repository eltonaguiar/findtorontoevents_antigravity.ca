# Hours-scale skyrocket patterns — 2026-11-15

Label: forward 4-hour move >= 1.5x the ATR% at the signal bar. Hourly bars, ~2 years. Base rate over all bars: **14.52%**.

Feature sources live this run: VIX regime **yes**, SEC filing recency **29 tickers**. Options flow is live-only (see below).

## Base rates by class

| class | bars | tickers | base rate | median ATR% | median spike size |
|---|---|---|---|---|---|
| CRYPTO | 137073 | 8 | 13.68% | 0.835% | 1.25% |
| EQUITY | 143099 | 29 | 14.59% | 1.802% | 2.7% |
| ETF | 44409 | 9 | 16.90% | 0.778% | 1.17% |

## Which feature orders the spikes

| feature | AUC | top-decile rate | bottom-decile | lift | coverage |
|---|---|---|---|---|---|
| atr_comp | 0.462 | 17.39% | 11.80% | 1.2x | 100% |
| bb_z | 0.476 | 16.78% | 12.68% | 1.16x | 100% |
| donch_break | 0.520 | 16.56% | 13.36% | 1.14x | 100% |
| vix_r1 | 0.480 | 16.02% | 12.05% | 1.1x | 82% |
| vol_surge | 0.519 | 16.34% | 12.78% | 1.13x | 100% |
| vix_level | 0.512 | 16.98% | 12.71% | 1.17x | 82% |
| filing_24h | 0.508 | 14.52% | 14.52% | 1.0x | 100% |
| range_exp | 0.494 | 15.47% | 13.72% | 1.07x | 100% |
| rsi | 0.506 | 16.38% | 13.62% | 1.13x | 100% |
| sma_dist | 0.506 | 15.18% | 13.87% | 1.05x | 100% |
| r4 | 0.505 | 15.44% | 12.89% | 1.06x | 100% |
| gap | 0.497 | 16.24% | 11.57% | 1.12x | 100% |
| log_hrs_filing | 0.502 | 16.33% | 13.42% | 1.12x | 44% |
| r24 | 0.501 | 14.92% | 14.01% | 1.03x | 100% |
| streak | 0.501 | 15.16% | 14.12% | 1.04x | 100% |
| r1 | 0.500 | 15.12% | 13.12% | 1.04x | 100% |

## Named patterns (train = first 70% of time, test = last 30%)

| pattern | signals | train precision | test precision | test lift | avg fwd test |
|---|---|---|---|---|---|
| filing in last 24h + breakout | 142 | 18.81% | 19.51% | 1.45x | -0.301% |
| VIX > 25 (stressed regime) | 17182 | 15.26% | 18.61% | 1.39x | 0.41% |
| breakout + squeeze | 4205 | 17.34% | 17.92% | 1.33x | 0.131% |
| oversold snap (RSI<30) | 19415 | 15.17% | 17.66% | 1.32x | 0.412% |
| 20-bar breakout | 8962 | 17.62% | 17.16% | 1.28x | 0.112% |
| squeeze + volume surge | 15091 | 16.80% | 16.43% | 1.22x | 0.04% |
| breakout + vol >1.5x | 3064 | 19.88% | 16.36% | 1.22x | 0.161% |
| volatility squeeze (atr_comp<0.8) | 72741 | 17.01% | 16.22% | 1.21x | 0.011% |
| squeeze + breakout + RSI<70 | 5459 | 17.55% | 16.07% | 1.2x | 0.091% |
| VIX falling (r1<0) + squeeze | 48150 | 16.44% | 16.08% | 1.2x | 0.035% |
| vol surge >2x | 39976 | 16.18% | 14.72% | 1.1x | 0.044% |
| filing in last 24h | 8272 | 16.93% | 14.79% | 1.1x | -0.161% |
| range expansion >2x ATR | 20654 | 15.18% | 14.32% | 1.07x | 0.065% |
| 3+ up bars in a row | 38532 | 15.84% | 13.40% | 1.0x | 0.021% |
| RSI 50-70 trend | 138439 | 14.85% | 12.82% | 0.95x | -0.012% |
| pullback in uptrend (r24>0, r1<-1%) | 13019 | 13.37% | 10.64% | 0.79x | -0.026% |
| gap up >1% | 7273 | 9.23% | 8.89% | 0.66x | 0.084% |

## Model ceiling (chronological split)

- all features: test AUC **0.5549**, base 13.43%, top-1% precision **14.37%** (1.07x lift)
- candle-only model: test AUC **0.5423** → catalyst/regime features +0.013 AUC
- rows: 227172 train / 97409 test

weights: `r1` -0.05, `r4` -0.01, `r24` -0.04, `vol_surge` +0.08, `range_exp` -0.05, `atr_comp` -0.13, `donch_break` +0.10, `rsi` -0.01, `sma_dist` +0.02, `bb_z` +0.02, `gap` +0.03, `streak` +0.00, `vix_level` +0.08, `vix_r1` -0.08, `log_hrs_filing` -0.03, `filing_24h` +0.03

## Live watchlist (latest bar scored by that model)

| ticker | class | score | 1h | 24h | vol surge | ATR comp | RSI | vs 20h high | VIX | hrs since filing |
|---|---|---|---|---|---|---|---|---|---|---|
| XLE | ETF | 0.196 | +0.1% | +4.1% | 0.43x | 0.71 | 66 | -0.70% | 19.7 | — |
| IWM | ETF | 0.182 | -0.0% | -2.1% | 0.65x | 0.96 | 38 | -2.50% | 19.7 | — |
| AFRM | EQUITY | 0.180 | -0.4% | -4.1% | 1.50x | 0.86 | 37 | -5.70% | 19.7 | 192 |
| GDX | ETF | 0.177 | -0.2% | -10.4% | 0.29x | 0.94 | 32 | -6.20% | 19.7 | — |
| SHOP | EQUITY | 0.176 | +0.6% | -3.4% | 0.52x | 0.77 | 46 | -2.50% | 19.7 | 240 |
| CVNA | EQUITY | 0.175 | +0.1% | -5.9% | 0.35x | 0.88 | 46 | -3.70% | 19.7 | 384 |
| PLTR | EQUITY | 0.174 | +0.2% | -0.7% | 0.51x | 0.79 | 45 | -4.20% | 19.7 | 240 |
| QQQ | ETF | 0.174 | +0.3% | -0.2% | 0.91x | 1.05 | 43 | -2.60% | 19.7 | — |
| ABNB | EQUITY | 0.173 | +0.4% | -2.2% | 0.70x | 1.01 | 58 | -0.80% | 19.7 | 192 |
| GME | EQUITY | 0.173 | -0.2% | +1.6% | 1.01x | 0.91 | 62 | -1.60% | 19.7 | 600 |
| SNAP | EQUITY | 0.171 | -0.3% | +4.2% | 0.52x | 0.92 | 53 | -3.20% | 19.7 | 192 |
| ARKK | ETF | 0.170 | +0.4% | -5.3% | 2.08x | 1.11 | 37 | -6.30% | 19.7 | — |

## Options flow — CURRENT SNAPSHOT ONLY (not backtested)

yfinance exposes the live chain, not its history, so these columns cannot enter the label stats above.

| ticker | expiry | put/call vol | put/call OI | ATM IV skew (put-call) | call vol | put vol |
|---|---|---|---|---|---|---|
| ABNB | 2026-11-20 | 1.19 | 0.92 | -0.0767 | 1017 | 1214 |
| AFRM | 2026-11-20 | 2.13 | 1.02 | 0.1265 | 1403 | 2986 |
| CVNA | 2026-11-20 | 0.68 | 1.0 | 2.644 | 8597 | 5824 |
| GDX | 2026-11-16 | 1.59 | 0.88 | 0.0249 | 1242 | 1974 |
| GME | 2026-11-20 | 0.18 | 0.23 | -0.0098 | 61812 | 10854 |
| IWM | 2026-11-16 | 1.22 | 1.37 | 0.0713 | 48626 | 59555 |
| PLTR | 2026-11-20 | 0.57 | 0.99 | 0.0007 | 71348 | 40516 |
| QQQ | 2026-11-16 | 1.17 | 1.3 | 0.1166 | 398321 | 465386 |
| SHOP | 2026-11-20 | 0.37 | 1.0 | -0.0679 | 5386 | 1987 |
| XLE | 2026-11-16 | 0.54 | 0.79 | -0.3271 | 1606 | 866 |

---
Read the test column only. Catalyst recency is a *filing timestamp*, not the news content:
an 8-K at 16:00 is knowable, its effect is not. Options flow stays snapshot-only until a historical
chain source exists — treating a live ratio as if it were backtested is how false edges get shipped.
