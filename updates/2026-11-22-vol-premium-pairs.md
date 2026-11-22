# Volatility risk premium + GDX/SLV pairs (2026-11-22)

Reproducer: `python3 tools/vol_premium_pairs.py`
Artifacts: `reports/vol_premium_pairs/vol_premium_pairs.json`
Closes todos **42, 43**.
Split basis named once and used everywhere: **2016-01-01**.

---

## 42 — The strongest statistic in the programme, and it is uninvestable

Variance risk premium = VIX(t−1) − realised vol over the following 21 trading days,
in bp of annualised vol. SPY + ^VIX, 2006-02-02 → 2026-11-20, n=5,192 days.

| | |
|---|---|
| mean | **+357.9 bp** |
| median | +407.8 bp |
| **t-stat** | **+46.50** |
| positive on | **84.7% of days** |
| pre-2016 (n=2,496) | +350.3 bp, t=+34.09 |
| post-2016 (n=2,696) | +364.9 bp, t=+32.10 |

This is the most robust number produced anywhere in this programme. It is *not*
a window artefact — it is stable across the split, it is significant at t=46 by a
factor of twenty over any reasonable threshold, and it has the right sign on 85%
of days. Implied vol really is systematically richer than the vol that follows.

### And here is what happens when you try to collect it

**Variant 1 — naked short VXX, monthly rebalance.** Cost 10bp/month.

```
worst period        -102.86%
mean per period      +2.298%
equity hits <= 0 at period 26/106 (2020-03)
VERDICT             ** RUINED **
```

The book is **wiped out in March 2020** at period 26 of 106. Not "drew down" —
the equity curve crosses zero and cannot be compounded. A +2.298%/month mean is
worthless against a −102.86% month.

> A defect I caught in my own first pass: it printed `gross CAGR +nan` and then
> still labelled the strategy **CANDIDATE** because `nan < 3.5%` is `False`. The
> `nan` came from `prod(1+net)` going negative. A negative equity curve is RUIN,
> and the code now detects it, refuses to print CAGR/Sharpe, and returns the
> verdict RUINED.

**Variant 2 — short VXX with a 25% monthly adverse stop, daily resolution.** Cost 5bp/side.

| | |
|---|---|
| worst period | −33.74% |
| mean per period | +0.007% |
| gross mean annualised (arithmetic, NOT a CAGR) | +14.33%/yr |
| **NET CAGR** | **−18.91%/yr** |
| Sharpe | +0.03 |
| maxDD | −85.6% |
| split-half mean | −0.03% → +0.04% per period |
| **verdict** | **REFUTED** |

The stop does prevent ruin (−33.74% worst instead of −102.86%) but it converts the
trade into a loss-maker: each stop fires on the way *up* into the spike, so you
pay the gap and then miss the recovery. Gross arithmetic +14.33%/yr becomes
**−18.91%/yr compounded**.

Caveats stated, not buried: VXX has reverse splits and a sponsor-changed index, so
long-run short-VXX returns are partly construction artefact; short-borrow fees are
**UNMEASURED**. This is directionally informative, not a deployable backtest.

**Conclusion:** the programme now contains a textbook demonstration that
statistical strength and investability are different things. t=46.50 and 84.7%
hit-rate describe a *premium*, not a *strategy*. The premium is real; the naive
harvest is a negative-expectancy lottery ticket with 35x-downside months.

---

## 43 — GDX/SLV pairs

| | |
|---|---|
| data | 2006-05-22 → 2026-11-20, n=5,159 |
| hedge ratio β (GDX→SLV) | 0.4579, **estimated on the first half only**, applied OOS |

**Cointegration was tested, not assumed:**

| sample | ADF t-stat |
|---|---:|
| full | **+0.28** |
| first half | **+0.27** |
| **second half (OOS)** | **+0.15** |

5% critical value ≈ −2.86. All three are *positive* — the spread is not
mean-reverting by any margin. The pair fails its precondition before any strategy
is even run.

I ran the strategy anyway, because "the precondition failed" is weaker evidence
than "the trade also loses money":

z-score rule, enter |z|>2.0 on a 60-day window, exit |z|<0.5 or 20 bars, next-bar
fill, 10bp per round trip (2 legs × 2 sides):

| | |
|---|---|
| days in market | 31.1% |
| position changes | 225 |
| gross | +2.778%/yr, Sharpe +0.18 |
| **net** | **+2.228%/yr, Sharpe +0.14** |
| split-half net | +2.59%/yr → **+1.87%/yr** |
| **verdict** | **REFUTED** (below 3.5% T-bill) |

n_trials = 1. One z-rule, one window, one threshold set, **chosen a priori and not
optimised.** Had I searched thresholds and found one that beat the T-bill, the
search would have been the finding, not the edge.

Positive but sub-cash is exactly what a z-score rule on a non-cointegrated spread
should produce: it is trading noise around a level that wanders. The +2.23% is
compensation for 31% market exposure, not for skill.

---

## Verdict changes

| item | label | basis |
|---|---|---|
| vol risk premium (existence) | **ESTABLISHED** | +357.9bp, t=+46.50, stable across split, n=5,192 |
| short-VXX harvest (naked) | **RUINED** | equity ≤ 0 at 2020-03, period 26/106 |
| short-VXX harvest (25% stop) | **REFUTED** | net −18.91%/yr, maxDD −85.6% |
| GDX/SLV cointegration | **REFUTED** | ADF OOS +0.15 (need < −2.86) |
| GDX/SLV z-score strategy | **REFUTED** | net +2.228%/yr < 3.5% T-bill |

## The lesson this block adds

The programme has now measured one thing with overwhelming statistical support
(VRP, t=46.50) and shown it to be the *worst* trade in the set once implemented
(ruin). Every other candidate had a weak statistic and a weak payoff.
**Statistical significance and capital survival are orthogonal**, and only the
second one decides whether money is made.
