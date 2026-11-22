# 05 — Real cost measurement, and where each strategy lives or dies

**Date:** 2026-11-22 (measurement window 11:49:49Z – 11:51:15Z)
**Scope:** items 4–8 of the profitability programme: measure the real all-in
transaction cost from live order books, then re-test the two strategies whose
verdicts hinge on it.
**Reports:**
[`reports/cost_measurement_20261122.json`](../../reports/cost_measurement_20261122.json),
[`reports/fx_meanrev_cost_sweep/sweep.json`](../../reports/fx_meanrev_cost_sweep/sweep.json),
[`reports/pod_equity_breakout/breakout_cost_sweep.json`](../../reports/pod_equity_breakout/breakout_cost_sweep.json)
**Tools:** [`tools/measure_real_cost.py`](../../tools/measure_real_cost.py),
[`tools/breakout_cost_sweep.py`](../../tools/breakout_cost_sweep.py)

---

## 1. What was measured and how

Live order books were pulled with ccxt 4.5.56 and walked by notional, so no
spread number in this document is an assumption:

```
exchange = ccxt.<venue>({'enableRateLimit': True, 'timeout': 20000})
exchange.load_markets()
exchange.fetch_order_book('<SYMBOL>/<QUOTE>', limit=1000)   # kucoin: limit=100
```

For each snapshot: best bid/ask, mid, half-spread `(ask-bid)/2/mid*1e4`, then a
VWAP walk of the ask side (buy) and bid side (sell) to a target notional, giving
`round_trip_spread_bp = (vwap_buy - vwap_sell) / mid * 1e4`. Depth is summed as
resting notional within 10bp and 50bp of mid.

**These are SNAPSHOT observations, not time-averaged.** 3 samples per symbol,
3 s apart, at ~11:50 UTC on a Sunday; min/median/max are reported rather than a
single point. Raw books are kept per snapshot under
[`reports/cost_measurement/20261122T114949Z/`](../../reports/cost_measurement/20261122T114949Z)
for reproducibility. A Sunday snapshot is thin compared to a weekday US session,
so the measured spread is more likely an over- than an under-estimate.

Fees are kept **separate** from spread, at base-tier spot **taker** rates
(Binance 10bp/side, KuCoin 10bp/side, Kraken 26bp/side; maker Binance 10bp,
KuCoin 10bp, Kraken 16bp). All-in = spread round trip + 2 × taker fee.

## 2. Measured cost table

Round-trip spread in bp, by size bucket (median over samples). Fee column is
taker, round trip.

| venue | symbol | top RT | fee RT | all-in @ top | $1k | $10k | $100k | $1M |
|---|---|---|---|---|---|---|---|---|
| binance | BTC/USDT | 0.0016 | 20.0 | **20.002** | 0.002 | 0.002 | 0.477 | 3.395 |
| binance | ETH/USDT | 0.0586 | 20.0 | **20.059** | 0.059 | 0.059 | 1.086 | 5.665 |
| binance | SOL/USDT | 1.4145 | 20.0 | **21.415** | 1.415 | 1.415 | 3.198 | 43.835 |
| binance | BNB/USDT | 0.1809 | 20.0 | **20.181** | 0.181 | 0.321 | 3.499 | 32.419 |
| binance | XRP/USDT | 1.0752 | 20.0 | **21.075** | 1.075 | 1.309 | 4.577 | 20.797 |
| binance | ADA/USDT | 6.8564 | 20.0 | **26.856** | 6.856 | 8.190 | 23.894 | 988.792 |
| binance | DOGE/USDT | 1.8033 | 20.0 | **21.803** | 1.803 | 3.515 | 9.158 | 131.587 |
| binance | AVAX/USDT | 1.4904 | 20.0 | **21.490** | 2.943 | 7.285 | 27.702 | INSUFFICIENT_DEPTH |
| kucoin | BTC/USDT | 0.0164 | 20.0 | **20.016** | 0.016 | 0.476 | 1.250 | INSUFFICIENT_DEPTH |
| kucoin | ETH/USDT | 0.0586 | 20.0 | **20.059** | 0.826 | 1.344 | 5.012 | INSUFFICIENT_DEPTH |
| kraken | BTC/USD | 0.0164 | 52.0 | **52.016** | 0.016 | 0.016 | 2.615 | 9.971 |
| kraken | ETH/USD | 0.0586 | 52.0 | **52.059** | 0.059 | 0.885 | 3.786 | 12.031 |

**The headline is the fee line, not the spread line.** On BTC/USDT the spread at
top of book is 0.0016bp and the taker fee is 20bp round trip: fees are four
orders of magnitude larger than the quoted spread. Any cost model that uses
"the spread" for a taker is wrong by ~20bp per round trip.

### Where size starts to matter

Cumulative slippage exceeds 2× top-of-book spread (the 2× criterion) at:

| symbol | first bucket over 2× top |
|---|---|
| binance BTC/USDT | $100k (0.477bp vs 0.0033bp) |
| binance ETH/USDT | $100k (1.086bp) |
| binance SOL/USDT | $100k (3.198bp) |
| binance BNB/USDT | $100k (3.499bp) |
| binance XRP/USDT | $100k (4.577bp) |
| binance ADA/USDT | $100k (23.894bp) |
| binance DOGE/USDT | $100k (9.158bp) |
| binance AVAX/USDT | $10k (7.285bp) |
| kucoin BTC/USDT | $10k (0.476bp) |
| kucoin ETH/USDT | $1k (0.826bp) |
| kraken BTC/USD | $100k (2.615bp) |
| kraken ETH/USD | $10k (0.885bp) |

So for majors the size-aware penalty stays under 5bp round trip up to $100k; the
thin alt books (ADA, AVAX, DOGE) are where it becomes material, and ADA at $1M
(988bp) is effectively untradeable.

### Capacity (depth, notional USD, median over samples)

| symbol | within 10bp (bid/ask) | within 50bp (bid/ask) |
|---|---|---|
| binance BTC/USDT | $2.98M / $3.50M | $5.70M / $7.60M |
| binance ETH/USDT | $1.86M / $2.25M | $5.66M / $5.11M |
| binance SOL/USDT | $321k / $373k | $822k / $1.17M |
| binance BNB/USDT | $265k / $347k | $1.16M / $1.26M |
| binance XRP/USDT | $389k / $702k | $1.18M / $1.30M |
| binance ADA/USDT | $8k / $25k | $324k / $242k |
| binance DOGE/USDT | $179k / $208k | $760k / $684k |
| binance AVAX/USDT | $35k / $31k | $167k / $148k |
| kucoin BTC/USDT | $126k / $415k | $126k / $415k |
| kucoin ETH/USDT | $265k / $209k | $279k / $701k |
| kraken BTC/USD | $2.52M / $654k | $2.73M / $1.79M |
| kraken ETH/USD | $966k / $1.14M | $2.05M / $4.48M |

## 3. Assumption comparison

Every assumption used in this programme, against what was measured. Crypto
spreads are applied **only** to crypto; equity and FX assumptions have no
measurement behind them.

| assumption | where used | value | vs measurement |
|---|---|---|---|
| N1 equity low-turnover backtests | base | 5bp/side | **UNMEASURED** (equity) |
| N1 stress | stress | 15bp/side | **UNMEASURED** (equity) |
| D7 breakout rule | base | 5bp/side | **UNMEASURED** (equity) |
| breakout family's own threshold | stated | ~8bp round trip | **UNMEASURED** (equity) |
| R22 FOREX mean-reversion | base | 10bp round trip | **UNMEASURED** (FX, market closed) |
| R21 FOREX carry/trend | base / 2× | 10 / 20bp round trip | **UNMEASURED** (FX, market closed) |
| pod `donchian-stock-breakout` | `emit_equity_breakout_pod.py` | 8bp round trip | **UNMEASURED** (equity) |
| pod published slippage | pod doc | 25bp/side | **UNMEASURED** (equity) |
| *crypto taker, majors* | this programme's crypto work | *implicit ~0–5bp* | **OPTIMISTIC** — measured all-in 20.0bp at top book (spread 0.002–1.4bp + 20bp fee) |
| *crypto taker, thin alts* | this programme's crypto work | *implicit ~0–5bp* | **OPTIMISTIC** — measured all-in 21–27bp, spread alone 6.9bp on ADA |

**No assumption above was validated for its own asset class.** The only
assumptions this measurement can speak to are crypto ones, and for a taker all
of them are optimistic by roughly 15–20bp per round trip.

## 4. Verdict per strategy

Cost is per instrument class. A crypto spread is not applied to an equity
backtest and vice versa.

- **POD-EQUITY-BREAKOUT (equities) — INSUFFICIENT_MEASUREMENT.**
  Measured gross edge is solid (all-history +0.492%/trade, t=4.42, n≈1,900;
  pre-2021 +0.478%, t=3.72, n=1515) and the **break-even cost is 24.6bp/side
  (49.2bp round trip)** all-history, **23.9bp/side** pre-2021. But equity cost was
  not measured, so I cannot say where real equity cost sits relative to that
  break-even. Note it survives even the pod's own 25bp/side only marginally
  (−0.008%/trade), so the break-even is close to the most pessimistic assumption
  in use.
- **R22 FOREX mean-reversion — MARGINAL.** Gross +4.3038bp/trade, so break-even
  round-trip cost is **4.30bp**. At 1bp cost it is CANDIDATE; it flips to KILL at
  2bp. The window-clustered CI at 1bp still includes zero
  ([−4.32, +11.09]), so even the 1bp result is not robust to the shared
  market move inside a window. FX cost was not measured (market closed).
- **Crypto legs of this programme (any strategy running on crypto) — DEAD at
  taker cost unless it clears ~20bp round trip.** Measured all-in is ≥20.0bp at
  top book for every symbol, and higher with size. This is a measurement, not an
  assumption.

## 5. What this changes and what it does not

**Changes:**
- For crypto, the spread is not the cost. At taker rates the fee dominates by
  ~20bp round trip on majors, and size adds 0.5–5bp up to $100k, much more
  beyond. Any crypto verdict that assumed ~2–5bp total is optimistic.
- Capacity is now bounded with numbers: BTC/ETH absorb $100k with <2bp extra
  slippage, ADA/AVAX do not.

**Does not change:**
- The equity and FX verdicts. **No equity or FX order book was measured**
  (equity: no access in this environment; FX: Sunday, market closed). Those
  numbers remain assumption-only and are **not strengthened** by this work.
  The breakout and FX results below are break-even analyses, which are durable
  properties of the strategies, not confirmations that the strategies are
  profitable at real cost.
- Nothing here suggests re-testing a KILL on crypto: measured cost is *higher*
  than the assumptions, not lower.

---

## 6. Item 7 appendix — breakout rule cost sweep (break-even is the deliverable)

[`tools/breakout_cost_sweep.py`](../../tools/breakout_cost_sweep.py) imports the
backtest from [`tools/pod_equity_breakout_backtest.py`](../../tools/pod_equity_breakout_backtest.py)
and the strategy from `baby_strategies/vt_pattern_sweep.py`. Trades are generated
**once** and only cost varies, so no parameter can drift. Entry rule, exit rule,
tie-break (stop-first) and universe are unchanged.

| cost/side | all net%/tr | all t | pre-2021 net%/tr | pre t | 2021+ net%/tr | 2021+ t |
|---|---|---|---|---|---|---|
| 0 | 0.4919 | 4.42 | 0.4783 | 3.72 | 0.5410 | 2.47 |
| 2 | 0.4519 | 4.06 | 0.4383 | 3.41 | 0.5010 | 2.29 |
| 4 | 0.4119 | 3.70 | 0.3983 | 3.10 | 0.4610 | 2.11 |
| 5 | 0.3919 | 3.52 | 0.3783 | 2.94 | 0.4410 | 2.01 |
| 8 | 0.3319 | 2.98 | 0.3183 | 2.48 | 0.3810 | 1.74 |
| 10 | 0.2919 | 2.62 | 0.2783 | 2.17 | 0.3410 | 1.56 |
| 15 | 0.1919 | 1.73 | 0.1783 | 1.39 | 0.2410 | 1.10 |
| 20 | 0.0919 | 0.83 | 0.0783 | 0.61 | 0.1410 | 0.64 |
| 25 | −0.0081 | −0.07 | −0.0217 | −0.17 | 0.0410 | 0.19 |

**Break-even cost:** all-history **24.59bp/side (49.19bp round trip)**;
pre-2021 out-of-sample **23.91bp/side (47.83bp round trip)**; 2021+ no crossing in
0–25bp. Whether measured equity cost is above or below this: **UNKNOWN** —
equity cost was not measured. If real equity cost is a few bp/side (index ETF
spread at retail is small), the strategy sits comfortably below break-even; at
the pod's 25bp/side it is at the edge.

## 7. Item 8 appendix — FOREX mean-reversion cost sweep

**FX live spread measurement: BLOCKED_LIVE_MEASUREMENT** — it is Sunday
2026-11-22 ~11:47 UTC and FX markets are closed; no executable quote exists to
sample. No FX spread is asserted here; the retail EURUSD figure is **unmeasured**
in this work.

[`tools/fx_meanrev_research.py`](../../tools/fx_meanrev_research.py) `run()` was
called once per cost with everything else fixed (`--shuffles 200`, seed 42,
55 dedup pairs, 8,866 pair-rebalances, 403 windows):

| cost RT | net bp | ci95 | window-clustered ci95 | verdict |
|---|---|---|---|---|
| 1 | +3.304 | [+0.75, +5.94] | [−4.32, +11.09] | CANDIDATE |
| 2 | +2.304 | [−0.25, +4.94] | [−5.32, +10.09] | KILL |
| 3 | +1.304 | [−1.25, +3.94] | [−6.32, +9.09] | KILL |
| 4 | +0.304 | [−2.25, +2.94] | [−7.32, +8.09] | KILL |
| **4.30** | **+0.004** | [−2.55, +2.64] | [−7.62, +7.79] | KILL |
| 5 | −0.696 | [−3.25, +1.94] | [−8.32, +7.09] | KILL |
| 10 | −5.696 | [−8.25, −3.06] | [−13.32, +2.09] | KILL |
| 20 | −15.696 | [−18.25, −13.06] | [−23.32, −7.91] | KILL |

**Break-even cost: 4.3038bp round trip.** Is that realistic for retail FX?
Unresolved here, because the spread is unmeasured, but the structural point is
that the strategy has only **4.3bp** of gross edge to spend, while the repo's own
pre-registered assumption is 10bp round trip (20bp at 2×) — i.e. under the
programme's existing assumption the strategy is **already negative** (−5.7bp at
10bp). For it to be alive, a retail participant would need round-trip FX cost
below 4.3bp, which is institutional territory more than retail. Treat it as a
KILL until an FX spread is actually measured and shown to be under 4.3bp.

---

## 8. Item 51 — reconciliation of the breakout break-even figure

**Status: resolved.** The apparent factor-of-five contradiction between the
breakout PF and the breakout gross edge is a **cost-label misattribution**, not a
units bug, a universe difference, or overlapping-entry inflation. No strategy,
parameter, rule, or universe was changed to produce this section.

### 8.1 The figures as originally published (preserved, now superseded)

- §4: *"break-even cost is 24.6bp/side (49.2bp round trip) all-history, 23.9bp/side pre-2021"*
- §6: *"all-history 24.59bp/side (49.19bp round trip); pre-2021 out-of-sample 23.91bp/side (47.83bp round trip)"*
- Report A ([`pod_equity_breakout_backtest.json`](../../reports/pod_equity_breakout/pod_equity_breakout_backtest.json)) was quoted as *"PF 0.992 all-history, 0.984 pre-2021, 1.020 in the published window, at 5bp/side"*.

These originals are kept verbatim so the record shows the error; 8.2–8.6 supersede them.

### 8.2 The contradiction was a cost label, not a unit

[`pod_equity_breakout_backtest.json`](../../reports/pod_equity_breakout/pod_equity_breakout_backtest.json) line 20 reads `"cost_bp_per_side": 25.0` (from [`COST_BP_PRIMARY = 25.0`](../../tools/pod_equity_breakout_backtest.py:51)). The run was at **25bp/side = 50bp round trip**, not 5bp. All three quoted PFs are that 25bp row:

| source | cost/side | PF all | PF pre-2021 | PF 2021+ | net %/trade (all) |
|---|---|---|---|---|---|
| Report A `pod_equity_breakout_backtest.json` | 25 | 0.99165 | 0.98398 | 1.02012 | −0.01684 |
| Report B `breakout_cost_sweep.json`, cost 25 | 25 | 0.99597 | 0.98926 | 1.02072 | −0.00811 |
| Report B `breakout_cost_sweep.json`, cost **5** | **5** | **1.22064** | 1.21188 | 1.25304 | **+0.39189** |

At 5bp/side there is no PF of 0.992 anywhere: the sweep reports **PF 1.2206, net +0.3919%/trade, t = 3.52** (all-history) and PF 1.2119, t = 2.94 pre-2021. The two reports agree with each other at 25bp to within a 6-trade data refresh (n 1941 vs 1935; runs at 10:25Z and 12:02Z on yfinance `period="max"`).

### 8.3 Population comparison of the two tools

Both reports are the **same population by construction**: [`tools/breakout_cost_sweep.py`](../../tools/breakout_cost_sweep.py:26) imports `SYMBOLS`, `fetch_daily`, `backtest_symbol` and `summarize` from [`tools/pod_equity_breakout_backtest.py`](../../tools/pod_equity_breakout_backtest.py:26), and generates the trade list once.

| property | Report A (backtest) | Report B (sweep) |
|---|---|---|
| universe | 13 symbols: SPY QQQ XLK XLF XLE XLV XLY AAPL MSFT NVDA GOOGL META AMZN ([`SYMBOLS`](../../tools/pod_equity_breakout_backtest.py:49)) | identical (imported) |
| data | yfinance daily, `period="max"`, `auto_adjust=True`, OHLC only | identical (imported) |
| date range | per-symbol max history (SPY 1993-01-29..2026-11-20 … AAPL 1980-12-12..) | identical windows (see `per_symbol`) |
| entry | next bar **open** after a LONG signal from the real strategy | identical |
| exit / stop | TP or SL from the signal, else 60-bar TIMEOUT; stop checked on the entry bar; stop wins intrabar ties (`tie_break="stop"`) | identical |
| position sizing | one unit per trade, equal weight, no leverage | identical |
| concurrency | one position at a time **per symbol** (`busy_until`, lines 89–95 and 135); symbols overlap in calendar time | identical |
| metric | arithmetic mean of simple returns `(exit−entry)/entry`, ×100 → percent ([`summarize`](../../tools/pod_equity_breakout_backtest.py:148)) | identical function |
| PF population | same `net = gross − 2·cost` array ([lines 149–151](../../tools/pod_equity_breakout_backtest.py:149)) | same array |
| n | 1941 round trips | 1935 round trips |

So: **not** cause 1 (different universes), **not** cause 2 (different windows), **not** cause 3 (overlapping-entry inflation) and **not** cause 5 (median vs mean) as a difference between the reports. The metric is a mean of simple per-trade percentage returns, not log returns and not a sum divided by n−1. `n` counts sequential round trips per symbol, not overlapping (date, symbol) rows.

### 8.4 The arithmetic reconciles exactly

```
at 5bp/side : 0.49189 − 2(5)/1e4·100  = 0.49189 − 0.10 = +0.39189  ✓
at 25bp/side: 0.49189 − 0.50          = −0.00811                    ✓
Report A 25 : 0.48316 − 0.50          = −0.01684                    ✓
break-even  : 20 + 5·0.09189/(0.09189 + 0.00811) = 20 + 5(0.918894)
            = 24.5945  ✓ (reported 24.59447177839161)
pre-2021    : 20 + 5·0.07828/(0.07828 + 0.02172) = 23.914   ✓ (reported 23.91402736768366)
```

The sweep is also internally consistent: at zero cost PF = 1.2865 with mean +0.4919% implies (to first order) an average win ≈ +5.42% and average loss ≈ −2.90% (reward/risk 1.87), matching the 777 TP / 1143 SL / 15 TIMEOUT exit mix and 40.8% win rate. Re-pricing the same two moments at 5bp/side gives PF ≈ 1.221, which matches the reported 1.2206.

The premise *"PF 0.992 at 10bp round trip implies a gross edge near +10bp"* is a valid conditional with a **false antecedent** — PF 0.992 belongs to the 50bp round-trip row, not 10bp. Likewise *"PF would be well above 1.5 at +39bp net"* is not what the distribution gives: with 40.8% WR and 1.87 reward/risk, PF at +39bp net is 1.22.

### 8.5 Which break-even is defensible

**24.59bp/side (49.19bp round trip) stands as the mean-based figure.** It is not lower than 5bp, and this correction does **not** strengthen the KILL by lowering the break-even. What it removes is the false impression that the strategy is already dead at 5bp/side.

Independent reasons to treat 24.59bp as an optimistic upper bound rather than a validation:
- **Survivorship.** The universe is 2026's mega-caps and a handful of ETFs; pre-2021 results are contaminated by selecting today's winners.
- **The t-stat overstates confidence.** t = 4.42 assumes independent trades, but 13 highly correlated US equities hold overlapping positions, so the effective sample is far below 1935.
- **Mean > median.** The edge is carried by TP winners; the median trade is not reported by `summarize` and is unmeasured here.
- The earlier D7 breakout test failed the random-entry control and the selection-alpha gate (§ [`02_DEEP_REVIEW_2026-11-22.md`](02_DEEP_REVIEW_2026-11-22.md)).

The KILL is therefore unchanged, but it rests on those grounds plus 24.6bp break-even vs ≥8bp assumed cost, not on a sub-5bp break-even.

### 8.6 FX 4.3038bp RT — same structure, same weakness

From [`reports/fx_meanrev_cost_sweep/sweep.json`](../../reports/fx_meanrev_cost_sweep/sweep.json): `n_pair_rebalances` 8866 = 403 non-overlapping 5-day windows × 22 positions/window (2 × round(0.2 × 55 dedup pairs)), 55 dedup pairs. `mean_gross_bp` is 4.3038 on **every** row (the trade list is fixed), and the break-even is exactly the mean gross by construction:

```
4.3038 − 4.30 = +0.0038   ✓ (row cost 4.3)
4.3038 − 4.31 = −0.0062   ✓ (row cost 4.31)
```

So the +4.30bp is a mean per leg on the **same population** the verdict used, and the 4.3038 zero-crossing is arithmetically correct. It shares the equity figure's weaknesses, though: it is **mean-based on a right-skewed distribution** (at 1bp cost, `median_net_bp` = +1.5915 → median gross ≈ 2.59bp, well below the 4.30 mean), the **window-clustered CI includes zero at every cost tested** ([−4.32, +11.09] at 1bp), and cost is charged per leg, so a long/short pair pays twice. It is defensible as an arithmetic break-even but statistically indistinguishable from zero, and the median trade's break-even is ~2.6bp.
