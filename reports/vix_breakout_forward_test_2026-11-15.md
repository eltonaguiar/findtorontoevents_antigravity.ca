# VIX>25 + breakout — recency / forward test (2026-11-15)

Rule: `vix_level > 25` AND `donch_break >= -0.001` → spike label `fwd_4h >= 1.5x ATR`. Pooled hourly bars: **265,991**, VIX coverage 100%, newest bar 2026-11-14 00:00:00+00:00.

## Read this before the table

The discovery run happened today on data ending today, so **every slice below is inside
its own sample**. This is a *recency stability* test, not an out-of-sample test — saying
otherwise would be exactly the kind of overclaim this repo has been burned by. The rule
also has no fitted parameters, so the risk being measured is regime decay, not overfit.

| window | bars | signals | base rate | precision | lift | avg fwd |
|---|---|---|---|---|---|---|
| all bars | 265,991 | 246 | 14.68% | **19.92%** ✅ | 1.36x | +0.582% |
| discovery (before last 90d) | 238,774 | 245 | 14.88% | **19.59%** ✅ | 1.32x | +0.546% |
| last 90d | 27,217 | 1 | 12.95% | **100.00%** ✅ | 7.72x | +9.368% |
| last 30d | 9,214 | 1 | 12.01% | **100.00%** ✅ | 8.32x | +9.368% |
| last 14d | 4,106 | 1 | 11.69% | **100.00%** ✅ | 8.55x | +9.368% |
| last 7d | 1,985 | 0 | — | — | — | — |

✅ = Wilson 95% lower bound still above that window's base rate.

## Last 30 days by asset class

| class | bars | signals | base rate | precision | lift | avg fwd |
|---|---|---|---|---|---|---|
| CRYPTO | 3,514 | 0 | — | — | — | — |
| EQUITY | 4,350 | 1 | 13.93% | **100.00%** ✅ | 7.18x | +9.368% |
| ETF | 1,350 | 0 | — | — | — | — |

## Verdict

Read the lift column against the base rate in the same row — a base rate that rises with
the precision means VIX stress lifted the whole tape, not the rule. Windows with n below
~30 carry Wilson intervals wide enough to be uninformative; they are shown rather than
hidden so nobody mistakes a quiet week for confirmation.

Snapshot JSON: `reports/vix_breakout_forward_test_2026-11-15.json`. Log the rule forward with a fixed entry/exit before any
sizing decision; a second run of this script on later data is the actual out-of-sample check.
