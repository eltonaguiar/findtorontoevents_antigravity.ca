# AMENDMENT 1 to ETF_TREND_FORWARD_2026-11-23 — **PROPOSED, NOT IN FORCE**

**Status:** PROPOSED by buffy (freebuff), 2026-11-23. **Not ratified. The original pre-registration
stands in full until this is registered in `reports/hypothesis_registry.json` and agreed before the
first record on 2026-11-30.** If it is not ratified, nothing changes and the report behind it is
advisory only.

**Why:** `reports/r4b_power_2026-11-23.md` computes what the §7 checkpoints can actually detect.
With a top-5 equal-weight book σ of 3.49%/month, the standard error of the mean monthly excess at
n=60 is **45.0 bp**, so the frozen CONFIRM test (one-sided 95% lower bound > 4.32%) requires a point
estimate of **110 bp/month = 13.2%/yr**. Power to confirm a hurdle-sized 36 bp/month edge is **5.0%**
— the same as the false-positive rate. A plausible 3–6%/yr momentum premium **cannot** confirm at
60 months, or at 736 months for the 36 bp case.

## A1. Replace the §7 checkpoint row

| old | new |
|---|---|
| `Earliest possible CONFIRM` ~**60 months** — the interval can finally be tight enough | **60 months is when SE falls to ≈ the hurdle, not when the hurdle becomes detectable.** At n=60 CONFIRM requires ≥110 bp/month net (13.2%/yr); KILL requires a point estimate ≤ −38 bp/month. Both thresholds are listed in the table below and are unchanged from §5 — this amendment documents them, it does not move them. |

## A2. Add §9 — what this clock can and cannot say

| n (months) | SE | point needed to CONFIRM | point needed to KILL |
|---:|---:|---:|---:|
| 12 | 100.7 bp | 201.7 bp/mo | −129.7 bp/mo |
| 36 | 58.2 bp | 131.7 bp/mo | −59.7 bp/mo |
| 60 | 45.0 bp | 110.0 bp/mo | −38.0 bp/mo |
| 120 | 31.8 bp | 88.4 bp/mo | −16.4 bp/mo |

Power to REFUTE at n=60: 48.2% for a −36 bp/month edge, 60.5% at −50, 91.6% at −100.

**The deliverable is therefore: (a) a refutation test, (b) a point estimate with an interval that
tightens every month, (c) a rule that stays at trial count 1.** It is not a confirmation instrument,
and no downstream document may describe it as one.

## A3. Explicitly unchanged

Universe (20 ETFs, frozen), signal (12-month absolute momentum, top 5), monthly cadence, cash rule,
the 4.32% hurdle, the §5 kill/confirm conditions, and trial count 1. **No number in §5 moves.**

## A4. What this amendment refuses to do

It does not lower the hurdle, relax the CONFIRM bar, shorten the observation window, or authorise a
backtest to produce a larger effect size. The bar is high; that is a fact about the bar, not licence
to lower it.

## A5. Effect if unratified

Zero. The clock runs exactly as written and the power table is advisory. The only cost of leaving it
unratified is that a reader may still believe 60 months produces a verdict.
