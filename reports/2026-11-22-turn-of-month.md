# Turn-of-month seasonality: a real gross effect that cost is nearly 3× too big to pay

**Date:** 2026-11-22 · **Owner:** buffy · **Item:** B13
**Tool:** `tools/turn_of_month_check.py` · **Raw:** `reports/turn_of_month_2026-11-22.json`
**Window:** SPY 1993-01-29 → 2026-11-20, **8,491 days** (33 years)
**Signal:** calendar only — no price information whatsoever. This is the cheapest family
left untested, so it deserved one clean run and then a decision.

## Pre-registered gate (written before the run)

Pass requires **all three**: bootstrap CI-LB on mean daily excess > 0, **both halves**
positive, and the observed mean ≥ the **95th percentile** of a random-window null holding
the **same number of days**. Anything less is a refutation.

Three variants are reported so the headline is not a choice among them: the classic
**L→+3** (last trading day through the 3rd of the next month), **L only**, and **+1→+3**
only.

## Results (5 bp per unit of turnover)

| variant | held | round trips | gross bp/day | cost drag bp/day | **net bp/day** | net %/yr | Sharpe | 90% CI (net) | null pct (gross) |
|---|---|---|---|---|---|---|---|---|---|
| L→+3 | 19.14% | 812 | **+0.345** | **0.957** | **−0.612** | −1.54 | −0.194 | [−1.492, +0.287] | 23.2 |
| L only | 4.79% | 406 | −0.305 | 0.479 | −0.784 | −1.98 | −0.531 | [−1.204, **−0.363**] | 3.1 |
| +1→+3 | 14.34% | 406 | +0.650 | 0.478 | +0.172 | +0.43 | +0.062 | [−0.612, +0.945] | 62.5 |

Halves on the classic variant: **[−0.841, −0.382]** — negative in both, so no regime story
rescues it. At 10 bp/side the classic variant is **−3.95%/yr**.

## The finding, stated precisely

**The turn-of-month effect is real gross and unpayable net.** The classic window earns
**+0.345 bp/day gross (≈ +0.87%/yr)** over T-bills, which is roughly what the literature
says the effect is worth. It costs **0.957 bp/day to harvest** — 812 round trips a year
across 33 years — so net is **−0.612 bp/day (−1.54%/yr)**.

**Cost is 2.8× the entire gross effect.** This is the sharpest cost-to-signal ratio found
anywhere in the programme: for comparison, funding carry's fee was 94% of its round trip,
but its *gross* premium at least exceeded the fee. Here the effect never had a chance.

**And cost is not even the only problem.** The gross mean sits at the **23.2nd percentile**
of random same-size windows — i.e. a randomly chosen 19% of days usually does better than
the turn-of-month days do. So the effect is not merely unpayable, it is **indistinguishable
from a random window** at this sample size even before cost. Both facts are reported
because they are independent grounds for the same verdict.

## Verdict

**REFUTED** — 0 of 3 variants pass. The equity seasonality family is closed, and the
programme should stop spending attention on calendar rules at daily granularity.

One caveat that keeps this honest: 33 years is one history, and a calendar effect that has
been arbitraged down since the 1990s would show exactly this pattern (gross small, cost
fixed). The finding is "not harvestable at 5 bp", not "the effect never existed".
