# Is the family worth 5 trials or 29? — 2026-11-22

**Owner:** buffy · **Artifacts:** `reports/effective_trials_2026-11-22.json`,
`tools/effective_trials.py`, `tests/test_effective_trials.py`

## The question, and why it decides something

Two multiplicity corrections disagree on the same 34 cells:

| correction | result | verdict |
|---|---|---|
| single-cell DSR at 29 declared trials | 0.9469 | fails the 0.95 bar |
| family-wide Hansen SPA, correlation-preserving | p = 0.0152 | rejects |

If the family is really worth ~5 independent trials, the DSR's 29 is a four-fold over-charge
and H-201 passes. If it is worth ~29, the DSR is right and SPA's rejection is measuring a
different null. So the number matters.

## 1. Three families of estimators

Correlation matrix of the 34-cell full-history family (3735 days):

| estimator | value | what it counts |
|---|---|---|
| mean pairwise correlation ρ̄ | **0.1903** | — |
| median pairwise correlation | 0.0732 | — |
| share of pairs above 0.5 | 0.1604 | — |
| N² / Σρ (variance of a sum) | **4.67** | independent trials for an **average** |
| N / (1+(N−1)ρ̄) | 4.67 | same, equicorrelation form |
| participation ratio (Σλ)²/Σλ² | 8.12 | effective dimensions |
| Kaiser (λ > 1) | 8 | — |
| Marchenko–Pastur edge count | 6 | above the iid noise edge |
| entropy exp(−Σp log p) | 15.71 | — |
| first eigenvalue share | 0.3065 | one factor explains 31% |

The first two rows are the source of the "N_eff ≈ 5" intuition. **They are the wrong
yardstick for this question**: they count the effective sample size of a *sum*, and every
correction in this programme — DSR, White's RC, Hansen SPA — is a **maximum**-type statistic.

## 2. The measurement that applies: correlation vs the max-tail

Zero-skill null (each column recentred on zero, so the two nulls differ *only* in cross-cell
correlation), circular block bootstrap, mean block T^(1/3) ≈ 15 days, 3000 draws:

| null | 95th pct of max t |
|---|---|
| correlation-preserving (real matrix) | **2.729** |
| independent (each column resampled separately) | **2.769** |

Correlation narrows the max-tail by **1.45%**. That is the whole effect at ρ̄ = 0.19 — because a
common factor does two opposing things at once: it synchronises the cells (fewer effective
draws) and it widens each marginal (shared variance). At moderate ρ they very nearly cancel.

Calibrating against the same bootstrap's independent null, on random subsets of the real cells
(the analytic order statistic is *not* used — solving it against this bootstrap's own independent
null returns 19 for a 34-cell family, a ~45% compression with no principled cause):

| n cells | independent-null p95 (t) |
|---|---|
| 5 | 2.1739 |
| 10 | 2.4361 |
| 15 | 2.5818 |
| 20 | 2.6437 |
| 25 | 2.7612 |
| 30 | 2.7518 |

Target 2.729 is first reached at **25 cells**. The 25→30 entries are within Monte-Carlo noise
(2.7612 vs 2.7518), so the honest band is **N_eff ≈ 20–30, point estimate 25**.

**Answer to the question asked: 25 — closer to 29 than to 5.** The variance-of-sum figure of
4.67 describes the average, not the maximum, and does not transfer.

## 3. The DSR re-derived on a matched basis

`s sqrt(var_sr) = 0.02279886` reconstructed from the frozen `expected_max_sharpe_daily`, and
`sr0(N=29) = 0.04695` matches the frozen value to 5 decimals — the basis is the same or the
numbers below are a different calculation wearing the same name.

| N trials | DSR-implied max daily SR | implied t threshold | DSR for H-201 |
|---|---|---|---|
| 1 | 0.00000 | 0.000 | 1.0000 |
| 3 | 0.01948 | 1.190 | 0.9995 |
| 5 | 0.02724 | 1.664 | 0.9975 |
| 8 | 0.03331 | 2.035 | 0.9928 |
| 10 | 0.03596 | 2.197 | 0.9889 |
| 15 | 0.04043 | 2.470 | 0.9780 |
| 20 | 0.04342 | 2.652 | 0.9667 |
| 28 | 0.04670 | 2.853 | 0.9490 |
| **29** | 0.04695 | 2.873 | **0.9469** |
| 34 | 0.04850 | 2.964 | 0.9364 |

DSR is decreasing in N, so there is a single pass/fail boundary: it clears 0.95 only while
**N ≤ 27**. (An earlier run of this analysis reported 28; the difference is the 8th significant
digit of `sd_sr`. The boundary is 27–28 and H-201 sits on it — that fragility is itself the
finding, not an inconvenience.)

## 4. So does the label change?

**No.** N_eff ≈ 25 against a boundary of 27–28 means the correlation adjustment moves H-201 from
*failing by 4 trials* (29 vs 27) to *passing by 2* (25 vs 27) — and the N_eff band of 20–30
straddles the boundary. A correction whose own input is uncertain by ±5 cannot settle a question
that turns on ±2.

| trial count | H-201 | basis |
|---|---|---|
| 29 declared | 0.9469 | fails |
| 27–28 boundary | 0.95 | knife-edge |
| 25 (N_eff point estimate) | 0.949–0.967 | passes, narrowly |
| 30 (upper N_eff band) | 0.9413 | fails |

H-201 stays **`NOT_PROVEN`**, and the reason is now sharper than "fails multiplicity by one
trial": *the multiplicity correction is not resolvable at this sample size, and the cell sits
inside its uncertainty band.* That is a different statement, and it is the true one.

## 5. The SPA/DSR gap is NOT explained by N_eff

This is a correction to my own earlier reasoning. C-022 attributed the SPA-vs-DSR gap to SPA
"effectively measuring a much smaller number of independent trials". The measurement above says
that is wrong: correlation narrows the max-tail by only 1.45%, so the effective trial count for a
maximum is ~25, not ~5. The gap has a different cause:

- The DSR's null inflates by the **cross-trial dispersion of Sharpe ratios** — 1.393 in t units
  here — and then applies a small order-statistic factor.
- The bootstrap null standardises each cell by **its own sampling sd**, so every cell is ~N(0,1)
  in t units and the max-tail is ~2.7.

The DSR bar is therefore larger not because it counts more trials, but because its per-trial
scale includes real heterogeneity that a standardised bootstrap removes. Both are defensible; they
are simply different nulls, and neither is a rescaling of the other.

## 6. Limitations

1. The family is 34 cells chosen by data availability (present from 2012-01-03), not by performance.
2. All of it rests on a survivorship-contaminated universe; a bootstrap resamples time, not names.
3. N_eff is a property of *these* cells. It does not transfer to a different family, and the
   calibration's Monte-Carlo noise (±1 cell at the top of the curve) is comparable to the margin
   being judged.
4. The zero-skill null used for the tail comparison is the strict one (every cell at zero). The
   observed H-201 t of 4.504 exceeds every draw, so its p is below the 1/3000 resolution; the
   Hansen SPA p of 0.0152 from the recentred null is the appropriate single number.
