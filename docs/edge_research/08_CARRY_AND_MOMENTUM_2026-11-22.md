# 08 — Carry and momentum after the honest hurdle

**Date:** 2026-11-22
**Programme items:** 12/13 (hurdle), 16 (FX carry), 11 (cross-venue basis), 17 (commodity carry), 18 (12-1 momentum), 19 (bootstrap CI), 48 (random-rank null)
**Hurdle document:** [`07_HURDLE_RATES_2026-11-22.md`](07_HURDLE_RATES_2026-11-22.md)
**Structured output:** [`reports/fx_carry_20261122.json`](../../reports/fx_carry_20261122.json),
[`reports/cross_venue_basis_20261122.json`](../../reports/cross_venue_basis_20261122.json),
[`reports/commodity_carry_20261122.json`](../../reports/commodity_carry_20261122.json),
[`reports/momentum_12_1_20261122.json`](../../reports/momentum_12_1_20261122.json)

**The bar for this whole document** (from doc 07): cash pays 4.32% (US 3-mo T-bill),
so a strategy is judged against `rf + hurdle × vol`, not against zero. To be called
an edge it must clear **Sharpe 1.114**, the standing SPY bar.

---

## Item 16 — FX carry from actual interest-rate differentials

### Data actually obtained

| Data | Source | Range / rows |
|---|---|---|
| FX spot, 10 crosses vs USD | `data/forex_rate_cache/*.csv` (Frankfurter/ECB daily close) | 2018-12-31 → 2026-11-20, 2,022 common days |
| USD short rate | FRED `DFF` (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF`) | through 2026-11-19: 3.88% |
| EUR | FRED `ECBDFR` | 2026-11-20: 2.50% |
| GBP | FRED `IUDSOIA` | 2026-11-18: 3.98% |
| JPY | FRED `IRSTCI01JPM156N` | 2026-10-01: 1.23% |
| AUD | FRED `IR3TIB01AUM156N` | 2026-10-01: 4.80% |
| CAD | FRED `IR3TIB01CAM156N` | 2026-10-01: 2.45% |
| NZD | FRED `IR3TIB01NZM156N` | 2026-10-01: 3.25% |
| CHF | FRED `IR3TIB01CHM156N` | 2026-10-01: −0.04% |
| NOK | FRED `IR3TIB01NOM156N` | 2026-10-01: 4.78% |
| SEK | FRED `IR3TIB01SEM156N` | 2026-10-01: 2.03% |
| DKK | FRED `IR3TIB01DKM156N` | 2026-10-01: 2.59% |

That is **11 currencies** (10 tradable vs USD). The euro-area 3-month interbank series
`IR3TIB01EUM156N` could **not** be fetched (returned an HTML error page), so EUR uses the
ECB deposit facility rate instead. Every rate series is the *real* published rate, not a
proxy built from prices.

### Pre-declared rule (fixed before the run)

Monthly rebalance at month-end. Rank currencies by short rate. **Long the top quintile,
short the bottom quintile, equal weight, vs USD.** With 11 currencies the quintile is
**2 long / 2 short**. Monthly P&L is modelled as two explicit components:

`ret_i = (S_{t+1}/S_t − 1)  +  (r_i − r_usd)/12`

— spot P&L **plus** the interest differential earned *continuously* while the position is
held (not a per-trade edge). Rates are joined as-of with a **30-day publication lag** so a
print published later cannot leak into the decision.

### Results

95 monthly observations, 2018-12-31 → 2026-11-20.

| Metric | Value |
|---|---|
| CAGR | **3.38%** |
| Volatility (annualised) | 7.43% |
| **Sharpe vs rf (4.32%)** | **−0.126** |
| Mean month / median month | 0.30% / 0.63% |
| **Skewness** | **−0.633** |
| **Worst month** | **−7.55%** (2020-03-31; of which −7.74% was spot, +0.20% carry) |
| **Max drawdown** | **−11.71%** |
| % positive months | 65.3% |
| Carry component (annualised) | +3.02% |
| Spot component (annualised) | +0.58% |

**The carry crash is visible and is the whole story.** The strategy earns +3.0%/yr of carry
and gives nearly all of it back on spot moves in risk-off months (March 2020 was the single
worst). Skewness is −0.63: many small gains, occasional large losses. This is the textbook
FX-carry profile, and the mean alone would hide it.

### Cost treatment (break-even, not a point estimate)

FX spot cost is **UNMEASURED** (Sunday, markets closed). Sweep in bp per unit of turnover:

| Cost (bp/leg) | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| 0 | 3.38% | −0.126 | −11.71% |
| 1 | 3.37% | −0.127 | −11.73% |
| 2 | 3.37% | −0.128 | −11.76% |
| 3 | 3.36% | −0.129 | −11.78% |
| 5 | 3.35% | −0.131 | −11.82% |
| 10 | 3.31% | −0.136 | −11.93% |

**Break-even cost (CAGR = 0): 468 bp per unit turnover.** Cost is not what kills this
strategy — even at 10bp it barely moves. What kills it is that it earns less than cash.

### Item 48 null percentile and item 19 excess-vs-SPY CI

- **Random-rank null (500 shuffles, same 2-long/2-short sizes, ranks shuffled):**
  observed Sharpe −0.126 sits at the **98.2nd percentile** of the null. The null's own
  mean Sharpe is **−0.85** (−1.45 at p5, −0.20 at p95). So the carry signal *does* beat
  random ranking of the same currencies (98th percentile) — the ranking carries
  information. It is simply not enough information to beat cash.
- **Excess CAGR vs buy-and-hold SPY** (SPY over the same window earned 6.42%): excess
  = **−3.04%**, 95% bootstrap CI (10,000 resamples, seed 20261122) **[−8.28%, +2.29%]**.
  The CI spans zero: no evidence of beating SPY, and the point estimate is negative.

### Verdict

**KILL** (as a standalone strategy). Decisive number: **Sharpe −0.126 vs rf** (a T-bill
beats it), with **skew −0.63 and a −7.5% worst month**. The signal has real ranking
content (98th percentile vs random), so it is a genuine carry premium whose crash risk
and sub-cash mean make it uninvestable on its own.

---

## Item 11 — Cross-venue basis, delta-neutral

### Data actually obtained

Public REST 1-minute OHLC for BTC, no keys:

| Venue | Endpoint | Minutes pulled |
|---|---|---|
| Binance | `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m` | 6,000 |
| KuCoin | `https://api.kucoin.com/api/v1/market/candles?type=1min&symbol=BTC-USDT` (paged, 180 bars/req) | 720 |
| Kraken | `https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1` | 720 |

**Three-way overlap: 720 minutes, 2026-11-22 00:14 → 12:13 UTC** (12 h). This is a real
time series, not a snapshot; 12 h is what the free endpoints give cheaply, and it is
reported as such.

### Pre-declared rule

Basis for a pair `= (P_A − P_B) / mid × 1e4` bp per minute. A round trip requires entering
on one venue and exiting on the other, so the **break-even is the sum of both venues'
measured all-in round trips** from [`reports/cost_measurement_20261122.json`](../../reports/cost_measurement_20261122.json)
at $10k: Binance BTC 20.00bp, KuCoin 20.48bp, Kraken 52.02bp.

| Pair | Threshold |
|---|---|
| Binance ↔ KuCoin | 40.48 bp |
| Binance ↔ Kraken | 72.02 bp |
| KuCoin ↔ Kraken | 72.50 bp |

### Results (distribution, not just the mean)

| Pair | median | sd | min | max | p1 / p99 | skew | **frac \|basis\| > threshold** |
|---|---|---|---|---|---|---|---|
| Binance vs KuCoin | −0.24 bp | 0.96 | −4.48 | +3.32 | −2.42 / +1.83 | −0.09 | **0.00%** |
| Binance vs Kraken | +20.92 bp | 2.80 | +11.27 | +27.91 | +13.68 / +24.87 | −0.52 | **0.00%** |
| KuCoin vs Kraken | +21.20 bp | 2.84 | +12.10 | +27.73 | +13.86 / +25.23 | −0.56 | **0.00%** |

The Kraken pairs show a persistent ~21bp median — that is Kraken's USD vs the USDT quote
plus its fee structure, and it is *structural*, not a momentary dislocation to harvest.
The Binance↔KuCoin basis is a fraction of a basis point. **No pair, in any of 720 minutes,
ever exceeded its two-venue break-even.**

### Item 19 / 48

The basis is flat with no exploitable distribution tail; the decisive measurement is the
0.00% exceedance, so a bootstrap CI on an un-investable basis adds nothing. Reported as
measured: **no minute above break-even**.

### Verdict

**KILL.** Decisive number: **0.00% of 720 minutes** had a basis above the measured
two-venue round trip (best case Binance↔KuCoin: max |basis| 4.48bp vs a 40.48bp threshold
— an order of magnitude short).

---

## Item 17 — Commodity term-structure carry

### Data actually obtained

Searched `data/`, `data_lake/`, `backtest_results/`:

- `data/cache/asset_class_review/*_F_5y.csv` — 10 files (CL, GC, NG, SI, HG, ZC, ZS, ES, NQ, YM).
  Each has columns `Date,Open,High,Low,Close,Volume` and is **one continuous front-month series**.
- `data/commodity_price_cache/` — empty (`.gitkeep` only).
- `data_lake/` — feature store + ingest script, no futures curves.
- `backtest_results/futures_comparison/` — a strategy win-rate report, no price data.
- Recursive search for `*front*`, `*back*month*`, `*roll*`, `*curve*` found nothing else.

**There is no second-month contract series anywhere on disk.** Roll yield
`(front − second)/second` needs two contracts at the same date; with only one continuous
series it cannot be computed.

### What was deliberately not done

No term structure was synthesised from the single front-month series or from spot ETF
prices. Doing so would invent the very signal under test.

### Verdict

**BLOCKED_DATA.** Decisive fact: **zero second-month contract series on disk**. Cost
(UNMEASURED for commodity futures) was therefore never reached; a break-even sweep would
have been reported had the test been runnable.

---

## Item 18 — 12-1 momentum on the existing panel

### Data actually obtained

79 symbols in `data/cache/asset_class_review/*_5y.csv`, 2021-11-22 → 2026-11-19 (~5 years of
daily closes, ~4 usable years after the formation window). SPY is in the same panel for the
buy-and-hold comparison.

### Pre-declared rule

Formation return over **months t−12 … t−2, skipping the most recent month t−1** (the 12-1
form, to avoid short-term reversal). Rank across symbols each month, **long top quintile /
short bottom quintile**, equal weight, hold one month. Variants fixed in advance: long/short
at 5bp/side (base) and 15bp/side (stress), long-only at the same two costs, and long/short
excluding crypto (`*-USD`) at 5bp/side.

### Honest sample note

The window is only ~4 years, so the **12-month formation leaves just 48 rebalances** (2022-12
→ 2026-11). That is a small sample: 48 monthly observations, and the bootstrap CI below is
correspondingly wide. Flagged, not hidden.

### Results

| Variant | CAGR | Vol | Sharpe vs rf | MaxDD | Skew | **Null pct** | **Excess vs SPY [95% CI]** |
|---|---|---|---|---|---|---|---|
| Long/short, 5bp | **−25.45%** | 42.6% | −0.70 | −82.3% | −1.52 | **1.6** | −42.1% [−72.6%, −0.003%] |
| Long/short, 15bp | −25.68% | 42.6% | −0.71 | −82.5% | −1.52 | 1.6 | −42.3% [−72.7%, −0.34%] |
| Long-only, 5bp | **+12.12%** | 33.0% | +0.24 | −25.2% | +0.65 | 41.4 | −4.5% [−33.7%, +37.4%] |
| Long-only, 15bp | +11.82% | 33.0% | +0.23 | −25.3% | +0.65 | 41.4 | −4.8% [−33.9%, +37.0%] |
| L/S ex-crypto, 5bp | +2.08% | 26.7% | −0.08 | −36.1% | −0.04 | 85.4 | −14.6% [−38.2%, +16.2%] |

SPY buy-and-hold over the same window: **16.64% CAGR**.

### Reading it

- **Long/short is actively bad:** −25% CAGR, an 82% drawdown, skew −1.52, and a **null
  percentile of 1.6** — i.e. 98.4% of random-rank portfolios did *better*. The short leg
  (bottom quintile = recent losers) in a panel heavy with crypto did the damage; the CI
  excludes zero on the negative side. This is a KILL, not a "no evidence" result.
- **Long-only is the only non-negative variant**, but its 12.1% CAGR is *below* SPY's 16.6%
  and its CI on excess CAGR spans zero; null percentile 41.4 means it is indistinguishable
  from random selection. No evidence of momentum edge.
- **Ex-crypto** is flat (2.1%) and sits at the 85th null percentile — again no edge.

### Cost note

Equity/ETF cost is **unmeasured**; 5bp/side is the standing convention and 15bp/side the
stress. The 1.5pp difference between them does not change any verdict.

### Verdict

**KILL** for long/short 12-1 momentum (decisive: −25.5% CAGR, null percentile 1.6).
**No evidence** for the long-only variant (decisive: excess vs SPY −4.5%, CI spanning zero,
41st null percentile).

---

## Round summary against the hurdle

| Strategy | Verdict | Decisive number | Null pct | Excess vs SPY CI |
|---|---|---|---|---|
| FX carry (quintile) | **KILL** | Sharpe −0.126 vs rf; skew −0.63; maxDD −11.7% | 98.2 | −3.04% [−8.28%, +2.29%] |
| Cross-venue basis | **KILL** | 0.00% of 720 min above two-venue cost | n/a (deterministic) | n/a |
| Commodity term carry | **BLOCKED_DATA** | no second-month contract on disk | — | — |
| 12-1 momentum L/S | **KILL** | −25.5% CAGR; null pct 1.6 | 1.6 | −42.1% [−72.6%, −0.003%] |
| 12-1 momentum long-only | **No evidence** | −4.5% vs SPY, CI spans zero | 41.4 | −4.5% [−33.7%, +37.4%] |

Nothing in this round clears the hurdle. The one genuinely interesting signal (FX carry
ranks better than random, 98th percentile) is nonetheless beaten by T-bills once crash risk
is counted, which is exactly what the honest hurdle was introduced to expose.
