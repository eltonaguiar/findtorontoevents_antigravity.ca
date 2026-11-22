# Item 29 — Crypto Intraday Mean-Reversion at 20bp measured cost

**Status:** §0 pre-declared and frozen BEFORE the first backtest run. Results sections
below are filled in only after the run; §0 is never edited afterwards.

## §0. Pre-declared rule (written before the run)

Everything in this section was written before `tools/crypto_meanrev_intraday.py` was first
executed. No parameter here was changed after seeing any result. If it had been, this test
would be void.

### Universe and data

- **Universe (10 crypto majors):** BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, ADAUSDT,
  DOGEUSDT, LINKUSDT, AVAXUSDT, DOTUSDT (Binance USDT spot pairs).
- **Resolution: 4h bars** (the scope's preferred interval). The local
  `data/cache/asset_class_review/` cache is daily-only and the local 1h JSONs hold 17 rows,
  so intraday bars are pulled from the venue: `GET https://api.binance.com/api/v3/klines`,
  paginated at the 1,000-row cap, with the returned first/last timestamps verified against
  the request.
- **Window:** 2021-11-22T00:00Z → 2026-11-22T00:00Z (5 years), the same span as the
  programme's daily cache, so the SPY benchmark comparison is over the same window.
- BTCUSDT_3mo_1h.csv is ignored: single symbol, ~3 months, no cross-section.

### Signal

- `z_t = (Close_t − SMA50(Close)_t) / STD50(Close)_t`, 50 bars on the 4h series
  (≈ 200h ≈ 8.3 days), population stdev, computed on closes only.
- **Enter LONG when z ≤ −2.0; enter SHORT when z ≥ +2.0.**
- **Entry fills at the OPEN of bar t+1** (1-bar lag). Entering at the signal bar's close is
  look-ahead and is explicitly forbidden.

### Exit, stop, time stop

- **Reversion exit:** for a long, when z ≥ 0; for a short, when z ≤ 0, evaluated at a bar
  close → **exit fills at the next bar's open** (same fill model as entry: signal at close,
  fill at next open).
- **Time stop:** 12 bars after the entry bar → exit at that bar's open.
- **Intrabar stop:** `2.0 × ATR14` (ATR measured at the entry bar, from entry price),
  checked **first** on every bar, before the reversion/time exit. Gap-aware: if the bar's
  open is already beyond the stop, the fill is the open (the worse price), else the stop
  price.
- **Overlap policy: one position per symbol at a time.** A signal is skipped while that
  symbol already holds a position. Positions in different symbols may run in parallel.
- A position still open at the end of the data is force-closed at the last close and
  flagged.

### Sizing, costs, statistics

- **Sizing:** each trade takes 10% (= 1/10 symbols) of current equity notional; equity is
  compounded at each trade exit in exit-time order. Daily equity curve for vol/Sharpe/maxDD.
- **Costs:** **20bp per round trip base** (measured 2026-11-22: taker fee 10bp/side
  dominates, all-in ≈ 20.0bp best venue to ≈ 52.0bp Kraken) → **stress 40bp**. Cost sweeps
  vary cost ONLY: 0, 5, 10, 20, 40, 60bp. The 0/5bp columns are optimistic comparability
  columns that do not exist in reality.
- **Random-entry null:** ≥ 500 shuffles. Each actual trade is replaced by a random entry
  bar in the same symbol, keeping the trade's direction and holding-bar count, then re-run
  through the identical stop/exit logic. Reported as the percentile of the observed total net
  return.
- **Bootstrap CI:** ≥ 10,000 block resamples (block = 5 days) of the paired daily
  (strategy, SPY) return series over the overlap window, recomputing
  `CAGR(strategy) − CAGR(SPY)` per resample.
- **Selection alpha:** per trade, `gross trade return − direction-adjusted buy-and-hold
  return over the same holding period` (long: B&H; short: −B&H). Mean selection alpha is
  reported so skill is separable from beta.

### Kill criteria (declared now)

- **KILL** if any of: (a) random-null percentile < 95; (b) break-even round-trip cost
  < 20bp; (c) mean net return/trade ≤ 0 at 20bp.
- **MARGINAL** if positive at 20bp but break-even < 40bp, or null percentile in [95, 99).
- **INVESTABLE** only if null percentile ≥ 95, break-even ≥ 40bp, and the lower bound of the
  excess-CAGR bootstrap CI > 0.
- **BLOCKED_DATA** if 4h bars cannot be obtained.

## Data window

- **Resolution actually used: 4h** (Binance USDT spot klines). 10,957 bars per symbol,
  2021-11-22 → 2026-11-22, all 10 symbols loaded, none blocked
  (`reports/crypto_meanrev_intraday_20261122.json` → `data_meta`).
- Why not the local cache: `data/cache/asset_class_review/` is **daily-only** (79 `_5y.csv`
  files, one row per day). `data/cache/BTCUSDT_3mo_1h.csv` is a single symbol over ~3
  months. Neither is a usable intraday cross-section, so 4h bars were pulled from the venue
  via `GET https://api.binance.com/api/v3/klines`, paginated at the 1,000-row cap with
  first/last timestamps verified against the request (same pattern as
  [`tools/funding_carry_backtest.py`](tools/funding_carry_backtest.py)).
- **SPY benchmark:** daily closes from `data/cache/asset_class_review/SPY_5y.csv`,
  2021-11-22 → 2026-11-19, **CAGR 11.26% over the window** (4.99y, 437.3 → 715.9).

## Cost provenance

- **20bp round trip base / 40bp stress**, from the live measurement of 2026-11-22
  (ccxt order books, `reports/cost_measurement_20261122.json`): taker fee 10bp/side
  dominates the 0.0016bp BTC top-of-book spread by ~4 orders of magnitude; all-in ≈ 20.0bp
  best venue, ≈ 52.0bp Kraken. The 0bp and 5bp columns in the sweep are **optimistic
  comparability columns that do not exist in reality.**

## Results (base case, 20bp round trip)

5400 trades, 4h bars, 2021-11-22 → 2026-11-22.

| metric | value |
|---|---|
| n trades | 5400 |
| win rate | 44.67% |
| mean net return / trade | −0.4473% |
| median net return / trade | −0.2432% |
| **PF (at 20bp RT)** | **0.691** |
| PF gross, no cost | 0.815 |
| mean gross return / trade | −0.2473% |
| mean selection alpha | +0.0223% (+2.23bp) |
| per-trade stdev | 3.47% |
| skew | +0.466 |
| worst trade | −20.00% |
| CAGR | −38.89% |
| vol (ann.) | 20.21% |
| Sharpe (rf = 4.32%) | −2.546 |
| max drawdown | −92.09% |
| worst 30-day period | −25.67% (ending 2024-12-03) |

Direction split: LONG n=3313, mean gross −0.079%, win 52.8%; SHORT n=2087, mean gross
−0.515%, win 42.1%. Exits: reversion 3081, stop 1195, time 1124. Mean bars held 3.54,
median 1. Each trade is 10% of equity, so total net return is a multiple of the per-trade
mean, not a portfolio CAGR.

The only positive number is selection alpha (+2.23bp/trade) and it is dwarfed by the 20bp
cost: even with zero cost the strategy is losing (see the sweep). The distribution is
**positively** skewed, so the loss does not come from one bad tail event - it is a
consistent bleed. Even at **0bp** the Sharpe is −1.491, nowhere near the 1.114 hurdle (or
even SPY's 0.351).

## Cost sweep (only cost varies)

| round-trip cost | mean net / trade | PF | win rate |
|---|---|---|---|
| 0bp (optimistic, unreal) | −0.2473% | 0.815 | 48.65% |
| 5bp (optimistic, unreal) | −0.2973% | 0.782 | 47.74% |
| 10bp | −0.3473% | 0.750 | 46.70% |
| **20bp (measured base)** | **−0.4473%** | **0.691** | 44.67% |
| 40bp (stress) | −0.6473% | 0.585 | 40.70% |
| 60bp | −0.8473% | 0.497 | 36.96% |

**Break-even round-trip cost: 0bp** (the mean gross return is already negative: −24.7bp, so
the edge is exactly zero only at a cost of 0 and is negative at every real cost). This is the
transferable number: there is no cost at which this rule is profitable, so no taker-fee
assumption can rescue it.

## Random-entry null

500 shuffles; each real trade replaced by a random same-direction, same-holding trade in the
same symbol through the identical stop/exit logic.

- observed total net return: −24.155
- null mean −10.930, null p95 −7.512, null p99 −5.505
- **percentile of observed result: 0.0** (below the 95th percentile)

The strategy does **not** beat random - it is worse than random entries. Per the
pre-declared rule this stops the evaluation at KILL.

## Bootstrap CI vs SPY (excess CAGR)

10,000 block-bootstrap resamples (5-day blocks) of the paired daily series, window 1815 days.

- point excess CAGR: **−50.23%**
- **95% CI: [−72.37%, −30.37%]**
- SPY CAGR over the window: 11.26%

The entire interval is negative - the strategy underperforms SPY by at least 30 points of
CAGR at the 95% level.

## Per-symbol breakdown

Every one of the 10 symbols is net-negative at 20bp; PF (at 20bp RT) ranges 0.462 (BTC) to
0.883 (DOT). Largest absolute PnL share is DOGE at **16.5%** - no single symbol dominates,
so this is not a single-name artifact. It is a broad, uniform failure of the rule.

| symbol | n | mean net / trade | PF (20bp RT) | share of PnL |
|---|---|---|---|---|
| ADAUSDT | 547 | −0.348% | 0.769 | 7.9% |
| AVAXUSDT | 539 | −0.624% | 0.644 | 13.9% |
| BNBUSDT | 531 | −0.307% | 0.709 | 6.8% |
| BTCUSDT | 517 | −0.545% | 0.462 | 11.7% |
| DOGEUSDT | 546 | −0.730% | 0.618 | 16.5% |
| DOTUSDT | 550 | −0.151% | 0.883 | 3.4% |
| ETHUSDT | 539 | −0.423% | 0.651 | 9.4% |
| LINKUSDT | 533 | −0.525% | 0.661 | 11.6% |
| SOLUSDT | 539 | −0.488% | 0.717 | 10.9% |
| XRPUSDT | 559 | −0.343% | 0.757 | 7.9% |

## Verdict

**KILL.** The single most decisive number: **the random-entry null percentile is 0.0** - the
rule's net return is worse than random entries, and even at 0bp cost the PF is 0.815 and the
Sharpe is −1.49. A 20bp measured cost turns an already-losing rule into a −0.447%/trade
bleed (PF 0.691 at 20bp RT). Crypto intraday mean-reversion at z=±2 / SMA50 / 2×ATR stop /
12-bar time stop does not survive measurement.

## What would change my mind

- Evidence that the loss is an artefact rather than an edge failure: e.g. a per-symbol
  re-run on a different, independent window that is profitable **before** cost at a null
  percentile ≥ 95. The current 0bp PF of 0.815 is far enough from 1.0 that a window effect
  is unlikely to explain it, but it is the only honest lever.
- Note what would **not** change my mind: sweeping the z-threshold, lookback, stop multiple
  or holding period to find a profitable configuration. That is fishing; this programme
  does not do it. The cost sweep above is the only sweep performed, and it shows no
  positive region.
