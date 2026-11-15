# Metrics Addendum — Benchmark-Relative Bars by Perspective

**Date:** 2026-11-15 · **Author:** Buffy
Extends `2026-11-15_1227AM_profitability/buffy/06_metrics/METRICS_BY_PERSPECTIVE.md`, which covered
absolute metrics (Sharpe, PF, CVaR, Kelly). This adds the comparison layer you flagged: **beat the
S&P 500, beat buy-and-hold.**

---

## 1. The four numbers that decide "is it better than doing nothing"

| Metric | What it answers | Fail signal |
|---|---|---|
| **Excess return** (matched exposure, net) | Did you beat the index? | ≤ 0 → you are an expensive index fund |
| **Information ratio** | Is the outperformance consistent? | < 0.5 → it's noise |
| **Down-capture** | Do you lose less when the market falls? | ≥ 100 → no risk benefit |
| **Capture ratio** (up ÷ down) | Are you asymmetric? | ≤ 1.0 → no |

Everything else (PF, Sharpe, WR) is secondary: they describe the shape of returns, not whether the
strategy deserves capital over a 3-bps index fund.

---

## 2. Bars by audience

### 2.1 Bank prop desk / senior trader
| Metric | Bar |
|---|---|
| Excess vs desk benchmark | > 0 after funding cost |
| Sharpe (net) | ≥ 1.5 |
| Information ratio | ≥ 0.75 |
| Down-capture | < 90 |
| Daily VaR 99% | < 1% NAV |

They are judged on P&L against a hurdle, not against SPY — but the *hurdle* is still a benchmark.

### 2.2 Mutual fund manager (long-only, benchmarked)
| Metric | Bar |
|---|---|
| **Information ratio vs index** | **≥ 0.5** |
| **Tracking error** | **2–6%** (mandate) |
| Up-capture / down-capture | > 100 / < 100 |
| R² vs index | report (high R² = closet indexer) |
| Excess over 3/5/10y | positive net of fees |
| Max drawdown | < 15–20% |

**The harsh reality:** SPIVA shows 85.59% of large-cap funds trailed the S&P 500 over 10 years and
92.89% over 20. The typical manager fails their own benchmark. Being in the surviving 7% is the job.

### 2.3 Hedge fund allocator (institutional LP)
| Metric | Bar |
|---|---|
| Jensen's alpha | > 0 with **t-stat > 3.0** |
| Deflated Sharpe | ≥ 0.95 at true trial count |
| PBO | < 0.5 |
| Information ratio | ≥ 0.5 vs a *strategy-appropriate* benchmark (not SPY for a market-neutral book) |
| Capacity | stated |
| Fee-adjusted (2/20) | still positive |

Note the benchmark trap: judging a market-neutral book against SPY is meaningless. Match the benchmark
to the exposure — for market-neutral, cash is the benchmark.

### 2.4 Chief risk officer
| Metric | Bar |
|---|---|
| Down-capture | < 100 |
| Capture ratio | > 1.0 |
| Stress loss (worst 5 days) | < 20% NAV |
| CVaR95 | within limit |
| HHI | < 0.25 |
| Max drawdown (compounded) | < 15% at sleeve level |

A strategy that beats SPY but has 100% down-capture has not reduced risk — it has added leverage.

### 2.5 Retail / prop challenge
| Metric | Bar |
|---|---|
| Max daily loss | 5% (hard) |
| Max total loss | 10% (hard) |
| Profit target | 8–10% |
| Anything benchmark-relative | **secondary** |

In a prop challenge, survival outranks benchmark beating. But note: the *reason* most challenge accounts
fail is not signal quality — it is sizing and drawdown, which is why the risk overlay is separate from
the edge question.

### 2.6 Academic / replication
| Metric | Bar |
|---|---|
| Alpha t-stat | **> 3.0** (Harvey–Liu–Zhu) |
| OOS | ≥ 2 disjoint periods, both positive |
| Sharpe after costs | reported, not gross |
| Trial count | fully disclosed |
| PBO | < 0.5 |

---

## 3. Deriving the bars from this ledger

| Class | Annualised excess vs benchmark | IR | Down-capture | Verdict |
|---|---|---|---|---|
| EQUITY | **not computed** | — | — | unknown |
| ETF | **not computed** (SPY hold = 8.71% CAGR, Sharpe 0.64) | — | — | likely negative after costs |
| CRYPTO | **not computed** (BTC hold is the bar) | — | — | unknown |
| FOREX | **not computed** (cash is the bar) | — | — | unknown |
| BOND | **not computed** (AGG) | — | — | PF 0.59 suggests negative |
| PREDICTION | **not computed** (fee-inclusive breakeven) | — | — | structurally negative as taker |

**Five classes, zero benchmarked.** This is the largest single gap in the whole measurement stack: the
contamination problem makes numbers *wrong*, but the missing benchmark makes the question *unasked*.

---

## 4. Two metrics people forget

**M² (Modigliani–Modigliani)** — rescales the strategy's Sharpe to the benchmark's volatility, so you can
say "this strategy would have returned X% at the index's risk level." It converts a risk-adjusted
statistic into a return number a non-quant can act on. Include it on every card.

**Captured upside vs captured downside in money terms**, not percentages. "We captured 92% of SPY's
upside and 71% of its downside" is the sentence that actually convinces an allocator.

---

## 5. The minimum dashboard card

```
Strategy: stocks_rsi2_pullback        Class: EQUITY       Benchmark: SPY TR
Excess (matched, net): +1.9%/yr       IR: 0.62            Beta: 0.58
Up-capture: 104%   Down-capture: 88%  Capture ratio: 1.18
Sharpe (ann): 0.91   DSR: 0.83 (N=361)   MaxDD: −18.4%
Verdict: CANDIDATE — fails DSR gate
```

If a card cannot fill those fields, it is not ready to be shown — and it is certainly not ready to be
funded. That is the standard this repo has been missing.
