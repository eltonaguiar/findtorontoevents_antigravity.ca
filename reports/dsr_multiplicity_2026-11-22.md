# The multiplicity verdict on H-201 is decided by one trial and 77 trading days

**Date:** 2026-11-22 · **Owner:** buffy · **Items:** D25, D28
**Tool:** `tools/dsr_multiplicity_sensitivity.py` · **Raw:** `reports/dsr_multiplicity_2026-11-22.json`
**Tests:** `tests/test_dsr_multiplicity_sensitivity.py` (6, passing)
**Input:** `reports/per_class_edge_2026-11-22.json` (40 cells, 29 declared trials)

## Why this needed doing at all

H-201 `xsmom_top3_6m` is the closest thing the programme has to an equity edge: CI-LB
7.246 bp/day, DSR **0.9469** against a 0.95 bar. It missed by **0.0031**. A number that
close invites a goalpost move ("just count 25 trials"), and the honest way to refuse that
is not to assert it — it is to measure **how large a move would be required**, so the
reader can see the size of the temptation.

## Can the DSR column even be rebuilt?

`var_sr` (the dispersion of Sharpe across trials) and each cell's daily skew/kurtosis are
not stored in the artifact, so a naive reimplementation does not reproduce it. Two things
make it rebuildable exactly:

- **the scale is recoverable.** `expected_max_sharpe_daily` = `sqrt(var_sr) · K(29)`, and
  `K(N) = (1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne))` is a closed form, so
  `sqrt(var_sr) = 0.04695 / K(29) = **0.02279813**` — exact, not fitted.
- **the denominator's non-normality term is disclosed, not hidden.** With sk=0, ku=3 the
  residual against the stored column *is* the size of that term.

Result: **H-201 reproduces to 0.0014** (0.948264 vs 0.9469 stored), and 39 of 40 cells
reproduce within 0.05. The one outlier is **H-228 at 0.1374** — the funding-carry cell whose
per-day Sharpe is smallest, exactly where the skew/kurtosis term bites hardest. The
tolerance therefore gates the cell being extrapolated, not the family, and the outlier is
reported rather than dropped.

## D25 — is `n_trials = 29` honest?

**Yes, and in the conservative direction.** 29 declared, 26 hypotheses produced a cell;
**H-202, H-203 and H-204 ran and produced no admissible cell**, so they are absent from the
table but were still searches. Counting them is right — they consumed the same researcher
degrees of freedom as the 26 that survived.

This matters more than it looks, because **at 26 trials the same data scores 0.9547 and
passes.** So the "we could just count 26" move is available and it is exactly the move that
would be wrong. The count is right; the margin is what is thin.

## D28 — how big is the margin?

| trial count N | DSR(H-201) | |
|---|---|---|
| 2 | 0.9999 | |
| 10 | 0.9894 | |
| 20 | 0.9678 | |
| **26** | **0.9547** | would pass — this is the available goalpost move |
| **28** | **≥ 0.95** | **last passing count** |
| **29 (declared)** | **0.9483** | fails by **one trial** |
| 40 | 0.9261 | |
| 100 | 0.8344 | |
| 500 | 0.5967 | |

Two independent margins, both small:

- **Bookkeeping margin: 1 trial.** H-201 holds 0.95 up to N=28 and the programme ran 29.
  One more independent search anywhere in the programme and it is further out; one fewer
  and it passes.
- **Data margin: 0.000272 of daily Sharpe**, i.e. it needed 0.073872 and observed 0.073600.
  At the observed effect size that is **3,820.7 days — 76.7 more trading days (0.30 years)
  of the same history** than the 3,744 available.

## What this changes

**The correct label for H-201 is `NOT_PROVEN`, not a clean `FAIL`.** The cell is not
refuted: its return series is unchanged and its lower bound (7.246 bp/day) is positive. It
is also not proven: significance that flips on one trial and three months of data is not
significance you can size a position on.

That is a narrower and more useful statement than `FAILS_MULTIPLICITY`, which reads as if
the data were against it. It is not. The data is **almost** for it, in a way that the
programme has already spent its search budget on.

## What would settle it, stated as a property of the data

Not a cheaper cost assumption, not a different bar, not a lower trial count. Either:

1. **77 more trading days of the identical rule at the identical effect size**, or
2. **an independent replication** on a non-overlapping universe, which adds observations
   without adding trials to *this* family.

Option 2 is the only one available offline, and it is what the forward pod for H-201
should be built to produce.

## A bug caught in this tool, on the run

The first draft's bisection searched for the **first failing** trial count in a predicate
that is true-then-false, so it walked away from the crossing and returned the cap
(100,000), printing "margin −99,971 trials". Caught on the first execution, fixed to hunt
the **last passing** count, and pinned by
`test_trials_to_clear_finds_last_passing_count` so the direction cannot silently invert
again. Recorded here because a tool that reports an absurd margin and is believed is worse
than one that crashes.
