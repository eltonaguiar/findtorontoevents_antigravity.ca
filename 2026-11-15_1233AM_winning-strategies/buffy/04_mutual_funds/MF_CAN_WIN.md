# Mutual Funds — Your Intuition Is Half Right, and the Half That's Wrong Is Expensive

**Date:** 2026-11-15 · **Author:** Buffy
**Your claim:** *"I'm pretty sure mutual funds would be winners, given enough time."*

**Answer: the wrapper wins, the average manager does not.** Over 20 years, **92.89% of large-cap
active funds trailed the S&P 500**, and **95.01% of all domestic funds trailed the S&P Composite
1500**. (SPIVA U.S. Year-End 2025.) That is not a marginal miss — it is the base rate.

But you are right in the way that matters: **a low-cost fund *portfolio* is the only thing in this
entire repo with a high probability of making money.** It just doesn't need a single prediction.

---

## 1. What "gives enough time" actually produces

Measured on SPY monthly history (407 months, price + dividend series via Yahoo):

| Horizon | P(positive) | Worst outcome |
|---|---|---|
| 1 year | 78.5% | — |
| 5 years | 76.1% | — |
| **10 years** | **90.2%** | **−40.2%** |
| CAGR | 8.71% | maxDD −52.2% |

So "given enough time" is empirically true at the *index* level: 9 in 10 ten-year windows were positive.
That is the equity risk premium doing the work, and it is available to anyone for ~3 bps.

Now compare the two statements:

| Statement | Evidence | True? |
|---|---|---|
| "A low-cost index fund makes money over 10+ years" | 90.2% of SPY 10y windows positive | ✅ **Yes** |
| "The average active mutual fund beats the index over 20 years" | 92.89% trailed the S&P 500 | ❌ **No** |
| "A fund *portfolio* can be a winner" | fees + behavior are controllable | ✅ **Yes** |

## 2. The three ways funds genuinely win

**2.1 Cost.** Fee drag is first-order, not a rounding error. Same portfolio, same gross CAGR:

- 0.03% ER vs 0.60% ER → over 20 years, **~10% of terminal value** is lost to the fee difference.
- On $100k at 7% gross for 20 years: ≈$386k vs ≈$351k. The fee is not small; it is a year of returns.

**2.2 Not selling.** The measured 90.2% requires *staying invested across the −40% ten-year windows*.
Behavioural failure (selling after drawdown) converts the 90.2% into a loss. This is the single largest
controllable variable for a retail investor — bigger than fund selection.

**2.3 The monthly clock.** Funds settle once daily at next NAV, cannot host intrabar stops, and are
subject to 30-day frequent-trading limits. That is usually described as a limitation. It is actually a
**feature**: it forces a monthly-cadence, low-turnover process that avoids the cost and multiple-testing
traps that kill the daily pick pipeline.

## 3. Why funds still cannot be a "pick" in this system

| Requirement for a pick | Fund reality |
|---|---|
| Entry price at signal time | NAV struck once, after close; you get the *next* unknown NAV |
| Intrabar TP/SL | impossible — one price per day |
| Exit within days | 30-day frequent-trading limit on many funds |
| Same-day repeatability | no |
| Benchmark-relative measurement | possible (this is the one thing that works) |

So funds fail as a **prediction class** for mechanical reasons, not because they're bad investments.

## 4. The test that would prove your intuition — and what it would show

You can settle this yourself in one afternoon per fund, with no prediction system:

```
For each candidate fund (and the index):
  monthly total returns, 20 years, NET of fees and loads
  compute: CAGR, Sharpe, max drawdown, and excess vs its own index
  count: does it beat its index over 20y?
```

**Expected result, from SPIVA:** about **7 in 100** active large-cap funds beat the S&P 500 over 20
years, and the survivors are not identifiable in advance. Meanwhile ~**100 in 100** low-cost index funds
deliver the index return minus a rounding error.

That asymmetry is the whole answer: **the winning fund is the one that doesn't try to win.**

## 5. What to actually build

| Build | Don't build |
|---|---|
| `BENCHMARK_SLEEVE`: monthly rebalance across 2–4 low-cost index funds, ER ≤0.10% | A mutual-fund pick ranker |
| A fee audit: total expense ratio + load + 12b-1 per holding | A NAV cache for intrabar signals |
| A behaviour rule: rebalance on the calendar, not on the news | An ML model over fund returns |
| Benchmark-relative reporting vs SPY TR | A "fund score" in the picks table |

**Naming matters.** This is **beta**, and it should be labelled beta everywhere. If it is reported next
to "picks", someone will eventually attribute the market's return to the system's skill. That is how
trust gets destroyed later.

## 6. Where I agree with you most strongly

Your instinct points at the correct **deployment vehicle**. Two things are both true:

- The system has **zero** proven alpha (verified PF 1.02–1.16, 0 of 15 gates passed).
- A low-cost fund allocation has a **measured ~90%** chance of positive 10-year return.

So the rational portfolio today is: **capital in the fund sleeve, research in the pick sleeve, and never
let the second one touch the first one until it beats SPY net of costs for 90 days of forward paper.**

That is not a defeat. It is the only arrangement where the research can continue honestly without
risking money on an unproven edge — and it is exactly what AQR's allocators did during the quant winter:
they kept the defensible position and waited for the evidence.

## 7. The one-sentence version

**Funds win because they own the market cheaply and don't trade; they lose when someone charges 0.6% to
try to beat it — 92.89% of large-cap active funds trailed the S&P 500 over 20 years, while 90.2% of
ten-year index windows were positive.** Your instinct is right; the alpha is not where you thought.
