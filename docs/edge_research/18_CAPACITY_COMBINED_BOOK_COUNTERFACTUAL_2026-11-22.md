# 18 — Capacity, combined book, no-trade counterfactual

**Date:** 2026-11-22
**Programme items:** 35 (capacity at measured spread), 36 (capacity model for the survivor),
37 (combined-book Sharpe), 38 (no-trade counterfactual)
**Tool:** [`tools/capacity_model.py`](../../tools/capacity_model.py)  ·  **Tests:** [`tests/test_capacity_model.py`](../../tests/test_capacity_model.py)
**Structured output:** [`reports/capacity_20261122.json`](../../reports/capacity_20261122.json) (35+36),
[`reports/combined_book_20261122.json`](../../reports/combined_book_20261122.json) (37),
[`reports/no_trade_counterfactual_20261122.json`](../../reports/no_trade_counterfactual_20261122.json) (38)
**Reproduce:** `python3 tools/capacity_model.py --write`

**Scoreboard carried in:** 13 strategies tested, 12 KILL, 1 MARGINAL (funding carry), 0 cleared.
Hurdle T-bill **4.32%**. Every APR below is stated against that 4.32% in the same sentence.

---

## 35. Capacity at measured spread

### What was measured, and does the summary trace to the raw books?

The measured report [`reports/cost_measurement_20261122.json`](../../reports/cost_measurement_20261122.json)
was built from raw order books in `reports/cost_measurement/20261122T114949Z/` (ccxt
`fetch_order_book`, limit 1000, 3 snapshots/symbol 3s apart, captured 2026-11-22T11:49:49Z).
I re-walked every raw snapshot independently and recomputed the round-trip VWAP spread at each
reported size rather than trusting the summary:

| Size | sample/size pairs re-derived | max &#124;recomputed − report&#124; |
|---|---|---|
| $1k | 36 | 0.000e+00 bp |
| $10k | 36 | 0.000e+00 bp |
| $100k | 35 | 0.000e+00 bp |
| $1M | 27 | 0.000e+00 bp |

The summary figures trace exactly to the raw snapshots (fewer pairs at $1M because some thin
books cannot fill $1M).

### Cost as a function of size (funding-carry symbols, Binance spot, MEASURED)

Pair round-trip cost = 2 legs × (spread round trip + 2 × 10bp taker):
*this is the cost of 4 taker fills, the same construction as the 45.524bp reference.*

| Symbol | $10k | $100k | $250k | $1M |
|---|---|---|---|---|
| BTC/USDT | 40.00 | 40.95 | 42.36 | 46.79 |
| ETH/USDT | 40.12 | 42.17 | 44.60 | 51.33 |
| SOL/USDT | 42.83 | 46.40 | 54.06 | 127.67 |
| BNB/USDT | 40.64 | 47.00 | 56.97 | 104.84 |
| XRP/USDT | 42.62 | 49.15 | 53.32 | 81.59 |

(values in bp; MEASURED spread from the weekend snapshot + MEASURED 10bp/side taker fee.
Perp spread is ASSUMED equal to spot spread.)

### Notional at which pair cost reaches the 45.524bp threshold

| Symbol | Crossover ($, 1×) | Crossover ($, 2× cost) |
|---|---|---|
| BTC/USDT | 773,987 | ≤ 1,000 (already over at the floor) |
| ETH/USDT | 344,462 | ≤ 1,000 |
| BNB/USDT | 83,294 | ≤ 1,000 |
| SOL/USDT | 68,924 | ≤ 1,000 |
| **XRP/USDT (thinnest)** | **29,438** | ≤ 1,000 |

At 2× cost every symbol is already above the threshold at $1k, so the 2× crossover is only an
upper bound (`≤ $1,000`) — the honest statement, not a point estimate.

### Verdict

**Capacity ≈ $29,438 per symbol at 45.524bp pair RT, binding on XRP/USDT** (BTC tolerates
$774k, XRP only $29k), **on one 3-minute sampling window on a Sunday 2026-11-22T11:49Z, single
venue set (Binance spot), taker execution.** What would change it: a 24/7 book average rather
than 3 snapshots 3s apart; measuring perp depth directly (currently assumed = spot); maker
execution (would raise it several-fold); thinner overnight books (would lower it).

**INSUFFICIENT_MEASUREMENT** for EQUITY, ETF, FX, COMMODITY, BOND, FUTURES, MUTUAL_FUND —
cost/depth for those classes was never measured, and crypto depth is not extrapolated to them.

---

## 36. Capacity model for funding carry

### Model

```
pair_cost_bp(C)   = 2 * ( spread_rt_bp(C) + 2 * taker_bp )      # 4 taker fills
cost_apr(C, H)    = pair_cost_bp(C) / 1e4 * (365 / H)           # amortised over the hold
net_apr(C, H)     = gross_funding_apr - cost_apr(C, H)
```

`spread_rt_bp(C)` is the MEASURED depth curve above (no extrapolation past the deepest point).
`gross_funding_apr` uses the **historical MEDIAN** 8h funding rate (mandatory default):
median across symbols 7.45 bp/8h → **8.16% APR gross**. The mean is 7.93% and the last-12-month
figure is **1.75%** (funding has decayed sharply; BTC compressed from +2.80bp/8h in 2021 to
+0.30bp/8h in 2026).

### Hold assumption (the mandatory one)

The base hold is the **median positive-funding episode, 1.93 days** — not the 90-day tail.
Break-even at median funding is **16.4 days**, ~8× the median episode, so the base case is
loss-making by construction. The 30-day and 90-day numbers are shown only as labelled sensitivity.

### Net APR vs deployed capital (per symbol, gross = 8.16% median)

| Hold | Cross 0% | Cross 4.32% (T-bill) | Any grid size beats T-bill? |
|---|---|---|---|
| **1.93d (base)** | ≤ $1,000 | ≤ $1,000 | **No** |
| 7d | ≤ $1,000 | ≤ $1,000 | **No** |
| 30d | $403k (min) / $671k (median) | ≤ $1,000 | **No** |
| 90d | $1.18M (min) / $1.36M (median) | $796k (min) / $944k (median) | Yes — tail only |

"≤ $1,000" means net APR is already below the target at the smallest measured size; the true
crossing is below the measured floor, so only an upper bound is knowable.

### Verdict

**No grid size beats the T-bill at the base (median) hold** — net APR at $10k–$1M per symbol is
deeply negative (−67% to −233% APR) because 45.5bp of cost is amortised over ~2 days. At the
30-day hold the capital at which net APR crosses **0% is ~$403k–$671k per symbol**, but it never
reaches 4.32% at any size. Only the **90-day tail** beats 4.32% (at ~$800k–$944k per symbol) and
that is the favourable case the brief forbids using as the base.

**CONDITIONAL on:** measured depth from a single weekend snapshot; assumed taker execution;
funding-rate stationarity (the median is dominated by older, higher-funding regimes than the
+0.30bp/8h of 2026); perp spread assumed equal to spot spread. A model fitted to 2021 rates is
stale.

---

## 37. Combined book

**This item is NOT_APPLICABLE for a multi-strategy book.**

### Why "combine to raise Sharpe" fails on non-positive components

Equal-weight blend of a risky sleeve (mean μ, sd s) with cash at rate r_f, weight w:

```
mean_p = w·μ + (1−w)·r_f        sd_p = w·s
excess  = mean_p − r_f = w·(μ − r_f)
Sharpe_excess = w·(μ − r_f) / (w·s) = (μ − r_f) / s
```

The blend's **excess Sharpe equals the sleeve's own, independent of w**. Blending with cash
only scales expected excess return by w; it cannot raise the excess Sharpe. If the sleeve's
μ − r_f ≤ 0 then every w > 0 has non-positive expected excess return and the optimum is w = 0
(100% cash). Diversification lowers variance; it cannot lift a non-positive mean, and lower
variance around a non-positive mean is not a benefit.

### The only defensible pair: funding carry + cash

- funding-carry net APR: **2.42% at H30** and **6.24% at H90** vs **4.32%** T-bill.
- Excess Sharpe over cash: **−0.44 at H30**, **+0.23 at H90** (the reported raw Sharpe of
  0.56/0.74 is return/vol, *not* excess over cash).
- SPY measured Sharpe is **0.351**; the H90 excess of 0.23 is below it and only exists in the tail.

**Best allocation: 100% cash** at the base hold. Funding carry does **not** beat 100% cash at the
median hold; it only edges past the T-bill in the 90-day tail, and blending does not improve its
excess Sharpe.

### Verdict

**There is no viable multi-strategy book because there is only one non-negative strategy.**
No book was constructed from killed strategies. **0 pairs were searched**, so no
multiple-comparisons correction is needed and no pair statistic is reported as evidence.

---

## 38. No-trade counterfactual

### Live book

`paper_portfolio/book.json` (`purpose: plumbing_demo_not_validated_edge`): **3 open demo
positions, 0 closed trades**, realized PnL net 0.0. The gate-loader loaded nothing — **11 pods
checked, 0 eligible** ([`03_P0_...md`](03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK_2026-11-22.md)).
With zero closed trades the live-book counterfactual is **NOT_APPLICABLE** by the brief's own rule.

### Resolved closed picks (where a counterfactual *can* be computed)

From `audit_dashboard/data/resolved_closed_picks_net.json` (10,968 kept rows after 10,040
exclusions, net of the measured class cost model), **window 2026-02-17 → 2026-11-22 (278 days)**:

| Metric | Value |
|---|---|
| Trades | 10,968 |
| Win rate | 43.14% |
| Mean net per trade | **−0.1524%** |
| Median net per trade | −0.7769% |
| Sum net | −1,671.5% |
| Per-trade Sharpe | −0.037 |
| SPY, same window (yfinance) | **+1.81%** (+2.38% annualised) |
| T-bills at 4.32%, same window | **+3.29%** |

Per class the mean is negative everywhere except EQUITY (+0.19%) and FUTURES (+0.57%, n=12);
CRYPTO −0.18% (n=9,099), COMMODITY −3.47% (n=44).

### Verdict

The live paper book is **NOT_APPLICABLE** (0 closed trades). On the resolved population the
counterfactual is unambiguous: the system's mean trade returned **−0.1524%** while SPY returned
**+1.81%** and T-bills **+3.29%** over the identical window. **Has the live system done better
than doing nothing? NO** — it lost money per trade while both doing nothing (cash) and buying SPY
were positive. Machinery cost is **UNMEASURED** (API/compute not metered in-repo). Caveat: the
resolved rows are survivorship-sensitive (kept after exclusions) and the per-trade mean is not a
sized portfolio return.

---

## Test pass lines

```
python3 -m pytest tests/test_capacity_model.py -q
................                                                         [100%]
16 passed in 0.11s
```
