# James-Stein shrinkage — implemented per the operator's recommendation; it compresses noise but creates no edge

**Date:** 2026-11-23T06:44Z · **Author:** Kilo · Paper only.
Responds to the top-gainers brief: *"symbol-level ranking is noise … escape route is hierarchical modelling WITH SHRINKAGE."*

## What was run
`tools/shrinkage_estimator.py` on **real dated trades only** (`entry_date` set), James-Stein toward a common grand mean.

| dimension | k | grand mean | shrink factor B | raw top5 survive shrink |
|---|---:|---:|---:|---:|
| strategy | 16 | +0.0031%/trade | **22.1%** | 5/5 (order unchanged) |
| symbol | 25 | +0.0020%/trade | **45.5%** | 5/5 (order unchanged) |

## Two findings
1. **Shrinkage compresses magnitudes (22–46%) but does NOT reorder.** James-Stein toward a single grand mean is
   monotone, so it pulls every estimate toward the pool by the same fraction — the ranking is preserved. So "shrinkage"
   alone cannot fix a selection problem; **grouping / hierarchy** (different priors per group) is what changes ordering.
2. **Even the shrunk winners are net-negative after cost.** Best shrunk strategy `cta_commodity_momentum_term`
   = **+0.049%/trade** vs a **0.20%** commodity round trip → **−0.15% net**. Best shrunk symbol `SOLUSDT`
   = +0.012% vs 0.52% crypto cost → **−0.51% net**. **0 of 6 top strategies and 0 of 6 top symbols are net-positive.**

## Verdict
The operator's shrinkage recommendation is **correct and now implemented**, but it is a *honesty* fix, not an edge:
it stops small-sample winners from being overstated, and it confirms they were never big enough to clear cost. This
reinforces the programme conclusion — the binding constraints are **cost and data coverage**, not model sophistication.

*Paper only. Not investment advice.*
