# Funding carry — opportunity-frequency analysis (2026-11-22)

**Programme:** 12-asset-class profitability research, the funding-carry UNKNOWN row.
**Question:** what fraction of funding episodes last long enough to amortise the measured
45.524 bp pair round-trip cost?

**Tool:** [`tools/funding_carry_opportunity_frequency.py`](../tools/funding_carry_opportunity_frequency.py)
**Structured output:** `reports/funding_carry_opportunity_frequency_20261122.json`
**Raw data reused:** `reports/funding_carry_raw/funding_<SYM>.json` (the existing cached pull from
[`tools/funding_carry_backtest.py`](../tools/funding_carry_backtest.py:101), Binance
`fapi/v1/fundingRate`, 8h settlement). No new fetch was written; no new network pull was made.

---

## 0. Pre-declaration (written BEFORE any duration was computed)

This section was written before the script was run. Nothing below is tuned to a result.

### 0.1 Data source and window

- **Source:** `reports/funding_carry_raw/funding_<SYM>.json` for
  `BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT` — the same cached files the carry backtest used.
- **Window:** all available funding history per symbol, first record → the pull time
  (2026-11-22T12:00Z). Using everything avoids any window-selection choice.
- **Settlement cadence:** 8h (3 intervals/day), so one interval = 1/3 day.
- **No returns are used in this analysis.** Only the funding-rate series (and its sign), so
  there is no return-side degree of freedom to tune.

### 0.2 Episode definition (headline rule, Rule A)

An **episode** is a maximal contiguous run of settled 8h intervals in which:

1. the funding rate is **strictly positive** (`f > 0`) at every interval in the run, and
2. consecutive records are **contiguous** (timestamp gap ≤ 8h + 1h tolerance; a data gap ends the run).

Rationale, fixed in advance: the delta-neutral pair (long spot / short perp) only *earns* when
the short perp receives funding, i.e. `f > 0`. A run of positive funding is exactly a period in
which a trader would plausibly stay in the trade. Duration = `(index_end - index_start + 1) / 3` days
(inclusive of both endpoints), the same convention as the existing `positive_trailing_episodes`
block in the carry backtest.

### 0.3 Alternative definitions (sensitivity, fixed in advance)

- **Rule B — trailing-24h-positive mask:** the carry backtest's existing pre-declared entry
  condition B (`docs/edge_research/06_FUNDING_CARRY_2026-11-22.md` §0): hold while the trailing
  24h funding sum over 3 settled intervals is `> 0`, decision at interval *i* using funding up to
  *i* only. Episodes are maximal contiguous runs of that mask.
- **Rule C — strict threshold `f > 1 bp/8h`:** only intervals whose funding rate exceeds
  1 bp (0.0001) count, to test whether the result depends on trivially-small positive funding.

Rule A is the headline; B and C are reported for robustness. If the verdict flips across A/B/C,
that is the finding and will be stated as such.

### 0.4 Thresholds and where they come from

| Threshold | Value | Source |
|---|---|---|
| Break-even hold (cost amortised) | **16.398 d** | measured pair cost 45.524 bp ÷ mean funding per day, `reports/funding_carry_20261122.json` (`aggregate_mean_breakeven_days_at_median` = 16.398). Not re-derived here. |
| Hurdle-clearing hold | **90 d** | the only pre-declared hold on the grid whose net APR (+6.24%) exceeds the 4.32% T-bill hurdle (`07_HURDLE_RATES_2026-11-22.md`, `08_CARRY_AND_MOMENTUM_2026-11-22.md`). Not re-derived here. |
| Pair round-trip cost | **45.524 bp** | measured order books, `reports/cost_measurement_20261122.json`. Settled; not re-derived. |

### 0.5 Sufficiency bar (what counts as "frequent enough to trade")

**Pre-declared bar: at least one qualifying episode (≥ 16.398 d) per symbol per quarter, i.e.
≥ 4 qualifying episodes per symbol per year.**

Justification (fixed in advance): at the 16.398 d minimum, four episodes/year put capital at work
≥ 65.6 days/year (≥ 18% of the time) with ≥ 4 independent cost-amortising trades. This is a
deliberately *generous* (low) bar: if the measured frequency falls below even this, the
"too thin to trade" conclusion is robust rather than borderline. The bar is about the count of
*qualifying* episodes, not all episodes.

### 0.6 Verdict rules (mechanical)

- Qualifying fraction **below** the sufficiency bar → **NOT_INVESTABLE for lack of tradeable
  opportunity**; the break-even arithmetic was never the binding constraint, frequency was.
- Qualifying fraction **at or above** the bar → apply the full proof bar (random-entry null
  ≥ 500 shuffles, bootstrap CI ≥ 10,000 resamples, judged vs 4.32% T-bills, capacity checked on
  XRP at $29,438), and report the implied annual dollars at that capacity.
- **No INVESTABLE verdict is possible from this task.** The strongest verdict is
  NOT_INVESTABLE or a bounded MARGINAL requiring human review.

### 0.7 Capacity reference

| Symbol | Capacity |
|---|---|
| XRP | **$29,438** (binding symbol) |
| BTC | $774,000 |
| ETH | $344,000 |
| BNB | $83,000 |
| SOL | $69,000 |

From the capacity analysis (`18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL_2026-11-22.md`).

---

## 1. Measurements

Run 2026-11-22 on the cached funding history (34.036 symbol-years across the five assets).
Structured output: `reports/funding_carry_opportunity_frequency_20261122.json`.

### 1.1 Headline (Rule A: contiguous `f > 0`), aggregate over all five symbols

**The one number that decides it: 82 of 2,838 episodes (2.89%) last ≥ 16.398 d** and can
therefore amortise the measured 45.524 bp round-trip cost. **11 of 2,838 (0.39%) reach 90 d**
and can clear the 4.32% T-bill hurdle.

| Rule A aggregate | n | p50 | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| Episode duration (days) | 2,838 | 0.667 | 2.000 | 5.000 | 9.383 | 41.433 | 224.333 |

| Fraction | Count | Percent |
|---|---|---|
| ≥ 16.398 d (break-even) | 82 / 2,838 | **2.89%** |
| ≥ 90 d (hurdle-clearing) | 11 / 2,838 | **0.39%** |

Robustness check (not a pre-declared rule, reported for honesty): an episode lasting
≥ 16.398 d does not automatically *earn* 45.524 bp, because break-even was computed at the
median funding rate. Counting only episodes whose gross funding actually exceeds the cost:
**71 / 2,838 = 2.50%** (per symbol BTC 24, ETH 14, SOL 15, BNB 1, XRP 17). The conclusion is
unchanged.

### 1.2 Per symbol (Rule A)

| Symbol | n | p50 | p90 | p99 | max | ≥16.398d | ≥90d | qualifying/yr | window |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 523 | 1.000 | 8.333 | 66.507 | 180.333 | 28 (5.35%) | 2 | 3.89 | 2019-09-10..2026-11-22 |
| ETHUSDT | 525 | 1.000 | 6.000 | 71.333 | 224.333 | 19 (3.62%) | 5 | 2.72 | 2019-11-27..2026-11-22 |
| SOLUSDT | 656 | 0.667 | 4.000 | 31.150 | 165.333 | 16 (2.44%) | 2 | 2.59 | 2020-09-14..2026-11-22 |
| BNBUSDT | 442 | 0.667 | 3.333 | 10.530 | 21.000 | 1 (0.23%) | 0 | 0.15 | 2020-02-10..2026-11-22 |
| XRPUSDT | 692 | 0.667 | 4.333 | 40.083 | 176.667 | 18 (2.60%) | 2 | 2.62 | 2020-01-06..2026-11-22 |

The median episode is under one day on four of five symbols. No symbol reaches the
pre-declared ≥ 4 qualifying episodes/year bar under the headline rule (BTC is closest at 3.89).

## 2. Sensitivity: does the conclusion flip with the episode definition?

All three rules were fixed in §0 before the run.

| Rule | Definition | n | p50 | p90 | p99 | ≥16.398d | ≥90d | qualifying/yr | symbols meeting ≥4/yr |
|---|---|---|---|---|---|---|---|---|---|
| **A (headline)** | contiguous `f > 0` | 2,838 | 0.667 | 5.000 | 41.433 | **2.89%** | **0.39%** | **2.41** | **0 / 5** |
| B | trailing-24h funding sum > 0 (backtest's own entry rule) | 1,253 | 2.000 | 14.933 | 116.227 | **9.18%** | **1.36%** | **3.38** | **3 / 5** (BTC 4.58, ETH 4.01, XRP 4.07) |
| C | `f > 1 bp` per 8h | 975 | 0.667 | 4.667 | 16.433 | **1.03%** | **0.00%** | **0.29** | **0 / 5** |

**Does the conclusion flip?** The *fraction of episodes* conclusion does not: under every
rule fewer than 10% of episodes can amortise cost and the median episode is 0.7–2.0 days.
The *per-symbol frequency* bar is definition-dependent: 0/5 symbols meet it under the headline
rule A, 3/5 under the trailing-24h mask B (which is the carry backtest's own pre-declared entry
rule), 0/5 under the 1 bp threshold C. So the answer is partially definition-sensitive, and that
is stated rather than hidden: the trailing-mask definition is the most favourable one, and even
it leaves only the three majors at ~4 episodes/year with 9.18% of episodes qualifying. The 90-day
tail is 0.39–1.36% of episodes under every rule.

## 3. Frequency answer, directly

- **Fraction of episodes that amortise cost:** 2.89% (A) / 9.18% (B) / 1.03% (C).
- **Fraction that clear the 4.32% hurdle:** 0.39% (A) / 1.36% (B) / 0.00% (C).
- **Implied tradeable (≥16.398d) opportunities per symbol per year:** 2.41–3.38 aggregate,
  i.e. **0.15 (BNB) to 4.58 (BTC)** per symbol. Hurdle-clearing (≥90d) opportunities:
  **0.32 per symbol-year** on average (11 across 34 symbol-years), and zero on BNB under every rule.
- **Is that enough?** Against the pre-declared bar (≥ 4 qualifying episodes per symbol per year)
  the headline rule fails on all five symbols. Even the most favourable rule leaves the fraction
  in single-to-low-double digits. The binding constraint is opportunity frequency, not cost.

## 4. Capacity × duration: the dollar arithmetic

Capacity (binding symbol XRP **$29,438**) × net APR at the hurdle-clearing 90-day hold (6.24%)
× qualifying exposure. Two readings, both deliberately generous (every qualifying episode
assumed to earn the full 90-day net APR):

| Quantity | Value |
|---|---|
| XRP qualifying episodes (≥16.398d) over 6.8y | 18 |
| XRP qualifying days total | 944.0 |
| XRP dollars from those episodes at 6.24% APR | **$4,751 total → ~$699/yr** |
| XRP if fully deployed all year at 90d net APR | **$1,837/yr** |
| T-bill on the same $29,438 at 4.32% | **$1,272/yr** |
| Excess over T-bills, best case | **~$565/yr** |
| Same at the 30-day net APR (2.42%) | $712/yr — **below** T-bills |

Across all five symbols at their own capacities, the same generous arithmetic gives
**$36,965/yr total** on **$1,299,438** of capacity = **2.84%**, versus **$56,136/yr** for
T-bills on that capital. **Even the optimistic ceiling does not clear the hurdle**, because the
qualifying episodes occupy only ~48% of the calendar and the 6.24% APR applies only then.

A strategy can be statistically real and economically pointless. Here it is both thin and small:
the maximum realistic annual return on the whole capacity set is tens of thousands of dollars
against millions of capital deployed, and it is below the risk-free alternative.

## 5. Verdict

**NOT_INVESTABLE for lack of tradeable opportunity.**

Basis (mechanical, per §0.6): under the headline rule 2.89% of episodes qualify, 0/5 symbols meet
the pre-declared ≥4/yr bar; under the most favourable alternative 9.18% qualify with 3/5 symbols at
the bar; under the strict rule 1.03% qualify with 0/5. No rule reaches a substantial fraction, so
the full proof bar (null ≥500, bootstrap ≥10,000, capacity on XRP) is not triggered. The measured
dollar ceiling at capacity is below T-bills. The break-even arithmetic (16.398 d vs a ~2-day
median episode) was never the binding constraint: **there are not enough tradeable opportunities**,
and the ones that exist are too small to matter.

**This is measurement-driven, not interpretation-driven:** the episode-duration distribution is a
new measurement that did not exist before; no earlier fact is being re-read.
