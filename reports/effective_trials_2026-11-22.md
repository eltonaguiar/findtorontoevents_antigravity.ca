# How many independent trials is the family worth? — 2026-11-22

Family **34 cells × 3735 days** (2012-01-03 → 2026-11-20). Declared trials **29**; cross-sectional sd of daily Sharpe **0.022799**.

## 1. Correlation-matrix estimators

| estimator | value |
|---|---|
| mean pairwise correlation | 0.1903 |
| median pairwise correlation | 0.0732 |
| share of pairs above 0.5 | 0.1604 |
| N² / Σρ (variance of a sum) | **4.67** |
| N / (1+(N−1)ρ̄) (equicorrelation) | **4.67** |
| participation ratio (Σλ)²/Σλ² | **8.12** |
| Kaiser (λ > 1) | **8** |
| entropy exp(−Σp log p) | **15.71** |
| Marchenko-Pastur edge count | **6** |
| first eigenvalue share | 0.3065 |

## 2. Bootstrap calibration (the decisive one)

| quantity | t |
|---|---|
| correlated null, 95th pct | 2.729 |
| correlated null, 98.5th pct | 3.141 |
| correlated null, 99th pct | 3.266 |
| independent null, 95th pct | 2.769 |

Correlation narrows the max-tail by only **1.45%** (2.769 → 2.729). Calibrating on the same bootstrap's independent null (random subsets of the real cells) puts the equivalent count at **N_eff = 25** for the max statistic.

| n cells | independent-null p95 (t) |
|---|---|
| 5 | 2.1739 |
| 10 | 2.4361 |
| 15 | 2.5818 |
| 20 | 2.6437 |
| 25 | 2.7612 |
| 30 | 2.7518 |

Target (correlated null p95): **2.729**. The analytic order-statistic solve is reported for reference only (19) — solving it against this bootstrap's own independent null returns 19 for a 34-cell family, a ~45% compression with no principled cause, so it is not used for the verdict.

This is the crux: the **variance-of-sum** estimator says the family is worth **4.67** independent trials, but that is the effective count for an AVERAGE. Every correction used here (DSR, RC, SPA) is a MAX-type statistic, and for a maximum a common factor both synchronises the cells and widens each marginal -- the two effects nearly cancel at ρ̄ = 0.1903. So the number that applies is **25**, not 4.67.

## 3. The decision — DSR by trial count

| N trials | DSR-implied max daily SR | DSR-implied t threshold | DSR for H-201 |
|---|---|---|---|
| 1 | 0.0 | 0.0 | 1.0 |
| 3 | 0.01944 | 1.19 | 0.9995 |
| 5 | 0.02719 | 1.664 | 0.9975 |
| 8 | 0.03326 | 2.035 | 0.9928 |
| 10 | 0.0359 | 2.197 | 0.9889 |
| 15 | 0.04037 | 2.47 | 0.978 |
| 20 | 0.04333 | 2.652 | 0.9667 |
| 28 | 0.04662 | 2.853 | 0.949 |
| 29 | 0.04695 | 2.873 | 0.9469 |
| 34 | 0.04844 | 2.964 | 0.9364 |

H-201's observed t is **4.504**, sitting at the **100.0th percentile** of the correlation-preserving null. The DSR passes only while N ≤ **27**, so the whole question is whether N_eff is above or below 27.

**Verdict: N_eff(max) ≈ 25 vs a pass threshold of N ≤ 27 → `H201_PASSES_DSR_at_neff`.**
