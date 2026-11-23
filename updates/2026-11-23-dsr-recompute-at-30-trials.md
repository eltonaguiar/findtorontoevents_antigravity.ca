# The DSR requirement is 137 days, not 77 — and H-201 now fails even at N=28

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

C-019 recorded two margins for H-201: DSR holds to N=28 of 29 declared, and 76.7 more trading days
would close the data margin. Today's three additions (H-234, H-235, H-236) moved the declared trial
count, so both numbers needed recomputing. Recomputed from the regenerated return series rather than
the stored summary, using the family scale sqrt(var_sr)=0.02279813/day that C-019 recovered, the
closed-form K(N), and the series' own higher moments.

## Series actually measured

T = 3,744 days, mean +11.521 bp/day, sd 156.5 bp, **sr_daily = 0.073603**, skew −0.050,
**kurtosis 12.254**. That kurtosis is the part C-019 did not carry: it makes the DSR denominator
1.0094 instead of 1.0, which widens every interval slightly and moves the requirement.

## Results

| N trials | K(N) | sr0 (daily) | DSR today | days needed | **forward days** |
|---|---|---|---|---|---|
| 28 | 2.0448 | 0.046618 | 0.9490 | 3,786 | 42 |
| 29 | 2.0594 | 0.046950 | 0.9469 | 3,881 | **137** |
| 30 | 2.0734 | 0.047269 | 0.9448 | 3,976 | **232** |
| 31 | 2.0869 | 0.047577 | 0.9427 | 4,071 | **327** |
| 32 | 2.0999 | 0.047873 | 0.9406 | 4,165 | 421 |
| 35 | 2.1362 | 0.048702 | 0.9344 | 4,447 | 703 |
| 40 | 2.1895 | 0.049916 | 0.9245 | 4,914 | 1,170 |

## What changed versus C-019

1. **76.7 days → 137 days at N=29.** C-019 used a normal-returns denominator; the measured kurtosis
   of 12.25 widens it to 1.0094, and the requirement scales with the square of that factor.
2. **The one-trial margin has closed.** C-019 said the DSR held to N=28. With the corrected
   denominator it is **0.9490 at N=28**, so the cell now clears only at **N ≤ 27**. The trial count
   in force today is 30–31. So H-201 is no longer "one trial short"; it is three or four short, plus
   137–327 forward days.
3. **Every test added today cost the same cell.** H-234, H-235 and H-236 each raised N. H-234 was
   worth it (it converted a near-miss into a period-stable result), but this is the mechanism by
   which a research programme can test its best idea out of existence.

## What the pod's 20-day gate does *not* do

At +77 days the DSR would be 0.9487 (N=29), 0.9466 (N=30), 0.9445 (N=31) — all below 0.95. The
20-day gate is a sanity check on the forward clock, **not** a significance gate, and completing it
must not be reported as clearing the DSR.

## Caveats

- Forward days only count if the forward Sharpe equals the in-sample 0.073603 daily. If it decays
  even slightly, the requirement diverges; the relationship is quadratic in (sr − sr0).
- This is a statistical gate, not economic proof. Costs are still modelled at 10 bp/unit turnover.
- The family scale sqrt(var_sr) is inherited from C-019's recovery against the original artifact;
  it is not re-estimated here, so the N-sensitivity is exact only if that scale is right.

## Verification

`reports/dsr_recompute_2026-11-23.json` regenerated from `tools/per_class_edge_harness.py`
(`xsmom(126, 3, 10, 21)` on the 10-name EQUITY universe), T and sr reproduced exactly against
H-234's full-sample figures (3,744 days, +11.521 bp/day). Claim C-029 appended.
