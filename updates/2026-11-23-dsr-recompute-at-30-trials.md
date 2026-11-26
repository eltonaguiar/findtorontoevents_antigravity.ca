# The DSR requirement is 137 days, not 77 — and H-201 now fails even at N=28

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

C-019 recorded two margins for H-201: DSR holds to N=28 of 29 declared, and 76.7 more trading days
would close the data margin. Today's three additions (H-234, H-235, H-236) moved the declared trial
count, so both numbers needed recomputing — from the regenerated return series, not the summary.

## Series actually measured

T = 3,744 days, mean +11.521 bp/day, sd 156.5 bp, **sr_daily = 0.073603**, skew −0.050,
**kurtosis 12.254**. The kurtosis is the part C-019 did not carry: it makes the DSR denominator
1.0094 instead of 1.0.

## Results

| N trials | K(N) | sr0 (daily) | DSR today | days needed | **forward days** |
|---|---|---|---|---|---|
| 28 | 2.0448 | 0.046618 | 0.9490 | 3,786 | 42 |
| 29 | 2.0594 | 0.046950 | 0.9469 | 3,881 | **137** |
| 30 | 2.0734 | 0.047269 | 0.9448 | 3,976 | **232** |
| 31 | 2.0869 | 0.047577 | 0.9427 | 4,071 | **327** |
| 32 | 2.0999 | 0.047873 | 0.9406 | 4,165 | 421 |

## What changed versus C-019

1. **76.7 → 137 days at N=29.** The normal-returns denominator was the difference; the requirement
   scales with the square of the ratio.
2. **The one-trial margin has closed.** Corrected DSR at N=28 is **0.9490**, so the cell clears only
   at **N ≤ 27**. Declared count is 30–31. H-201 is three or four trials short, plus 137–327 days.
3. **Every test added today cost the same cell.** H-234 was worth it, but this is how a programme
   tests its best idea out of existence.

## The 20-day gate is not a significance gate

At +77 days DSR would be 0.9487 (N=29), 0.9466 (N=30), 0.9445 (N=31) — all below 0.95. Completing
the pod's 20-day sanity gate must not be reported as clearing the DSR.

## Caveats

- Forward days only count if the forward Sharpe equals 0.073603 daily; the requirement is quadratic
  in (sr − sr0), so decay makes it diverge.
- Statistical gate, not economic proof; costs modelled at 10 bp/unit.
- sqrt(var_sr)=0.02279813 is inherited from C-019's recovery, not re-estimated here.

## Verification

Artifact regenerated with `tools/per_class_edge_harness.py` `xsmom(126,3,10,21)` on the 10-name
EQUITY universe; T and sr reproduce H-234's full-sample figures exactly (3,744 days, +11.521 bp/day).
Claim C-029 appended to `reports/claim_register.json`.
