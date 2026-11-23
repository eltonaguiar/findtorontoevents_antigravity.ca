# σ adjudication — the two DSR bases, and what the "~25 effective trials" claim actually implies

**Filed:** 2026-11-23 · **Asked for by:** `reports/TRIAL_N_RECONCILIATION_2026-11-23.md` §7, which
flagged that SR\* = 1.259 and SR\* = 1.6176 at the same N are "not comparable" because the two σ's are
on different scales. This adjudicates it for the H-242 cell, where both σ's are computable.

## The correction first

I published a COMS note saying the SE-of-SR basis was **0.07195**. That number is **wrong** and I am
retracting it. Recomputing from the same inputs:

```
SE(SR_daily) = sqrt( (1 − skew·SR + (kurt−1)/4 · SR²) / T )
             = sqrt( 1.00723 / 2514 )
             = 0.020088
```

with SR_daily = 0.06901, T = 2514, skew = −0.090, kurtosis = 7.97 (non-excess). The `0.07195` was a
mis-transcription, not a different estimator. **The two bases are 0.022798 and 0.020088 — 13% apart,
not 3.6× apart.**

## Why that matters more than the DSR number

**Cross-trial σ = 0.022798. SE of one SR estimate = 0.020088. Ratio 0.88.**

That ratio is the whole adjudication. If the 121–362 trials were **independent zero-skill draws**, the
cross-sectional standard deviation of their daily Sharpes would equal the average standard error —
i.e. the ratio would be ≈ 1. It is **0.88**, slightly *below* 1, which is exactly what a set of
near-independent trials with mildly differing lengths looks like. It is 5× away from what heavy
cross-trial correlation would produce.

**Consequence: the "~25 effective independent trials" estimate is not supported by this ratio.** For
25 effectively-independent trials out of ~120 declared, the cross-sectional SD would have to be
roughly `0.0201 / sqrt(120/25) ≈ 0.0092`. The observed 0.0228 is **2.5× larger** than that. The
correlation story that would justify N=25 does not show up in the dispersion it must produce.

This is a *different* argument from the circularity objection in the reconciliation doc §4 (which I
agree with, but which is an argument about method). This one is arithmetic on the trial scatter: if
you want to claim 25 effective trials, you have to show the shrunk dispersion, and nobody has.

## So which σ is correct for DSR?

- **Bailey & López de Prado's `Var(SR)`** is the dispersion of Sharpes *across trials*. Canonical use
  = **0.022798**. That is the estimator the formula was derived for and the one DSR should use.
- **SE(SR)** is the sampling error of *our single* estimate. Feeding it into `E[max]` (which is what
  `alpha_engine.deflated_sharpe.deflated_sharpe_ratio` does via `sharpe_variance()`) mixes two objects:
  it asks "how surprising is this SR given the noise in one measurement" rather than "how surprising
  is it given the best of N draws". It happens to be *more permissive* here only because 0.0201 <
  0.0228; that is a coincidence of this cell, not a property of the convention.

**Recommendation:** report the canonical cross-trial value as the headline, publish the SE-convention
value beside it as a sensitivity, and never quote either without naming it. That is what H-242's
artefact now does.

## The number that actually decides anything

To clear DSR 0.95 the hurdle must satisfy `SR0* ≤ SR − 1.645·denom/√(T−1)`:

```
needed SR0*  ≤ 0.03596        (z ≤ 1.577)
breakeven    = N_eff ≈ 12     (z(12) = 1.665)
```

| N_eff | SR0* | DSR |
|---:|---:|---:|
| 25 | 0.0455 | 0.879 |
| 30 | 0.0473 | 0.860 |
| 36 | 0.0490 | 0.841 |
| **120** | **0.0591** | **0.688** |
| 362 | 0.0673 | 0.533 |

**The book would have to be the best of ~11 or fewer effectively-independent trials.** Every candidate
denominator in circulation — 25, 30, 36, 120, 362 — fails, and the most generous one (25) still lands
at 0.879. This result is robust to the σ dispute, which is the point of doing the arithmetic before
arguing about which σ to prefer.

## Limits, stated

- The 0.022798 is a **recovered** scale: it was back-solved from a published
  `expected_max_sharpe_daily` at a declared N, not computed from the trial-return matrix. The matrix
  that would allow an independent check (`reports/per_class_edge_series_2026-11-22.csv`) **is not in
  this clone**, and `reports/per_class_edge_2026-11-22.json` is absent too, so the recovery step
  cannot be re-derived here. That is a real hole: if the published `expected_max_sharpe_daily` was
  itself produced with the SE convention, then 0.022798 is not a cross-trial σ at all, and the
  independence conclusion above collapses.
- The independent corroboration that 0.022797 vs 0.022799 agree to 4 decimals across two artefacts is
  evidence the *number* is stable, **not** evidence of what it measures.
- Nothing here re-opens H-242: it fails at N_eff = 25 and at N_eff = 362 alike.
