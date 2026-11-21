# H-149 factor regression, and H-150 pre-registered

**Date:** 2026-11-21
**Files:** `tools/h149_midcap_gross_profitability.py`,
`reports/h149_midcap_gross_profitability_2026-11-21.{md,json}`,
`reports/hypothesis_registry.json`
**Status:** regression answers the open question (alpha zero); literal spec filed as H-150

## What was missing

The H-149 acceptance criteria declared MKT/SMB/HML/RMW as the factor benchmark
before the run, but nothing ever regressed them out. The artifact said so in its
own `limits` list: "a strong factor tilt could masquerade as a signal." With the
book showing +2.04%/40d on the top decile and the harness rejecting anyway, that
gap was the one remaining explanation worth ruling out.

## What changed

**1. Factor regression in the tool.** New `_ff_monthly()` (Ken French 5-factor
monthly file, cached at `tools/cache/ff5_monthly.csv`, untracked), `_ols()`
(intercept + four factors, classical standard errors), and
`factor_regression()`, which builds the top-quintile equal-weight book at each
formation, restates the 40-trading-day net return as a monthly equivalent at
21/40, assigns it to the month the position is held, and subtracts RF. Both an
overlapping fit and an every-second-month fit (which breaks the ~10-day overlap
between consecutive formations) are reported. `--no-factors` skips the fetch.

**2. H-150 pre-registered.** The four deviations that made H-149 a test of
something other than what was filed are now their own hypothesis, so H-149's
rejection cannot be read as a verdict on the filed spec.

## Result

| fit | n | alpha | alpha t | MKT | SMB | HML | RMW | R² |
|---|---|---|---|---|---|---|---|---|
| overlapping | 77 | +0.033%/mo | **0.04** | 0.48 | **+1.33** | **−0.73** | −0.41 | 0.415 |
| every 2nd month | 39 | −0.901%/mo | **−0.78** | — | — | — | — | — |

Alpha is zero on both fits. R² = 0.415 with SMB +1.33 and HML −0.73: the book's
return is a small-cap, low-book-to-market tilt inside a $2B–$10B band, not a
gross-profitability premium. This is the measurement that was missing, and it
agrees with the harness (11 strong negative windows vs 4 positive).

## Verification

- `--self-check` → `unmodified=True`; the harness is still imported unmodified.
- Factor file parses 759 months (196307..202609).
- `_ols` recovers a known synthetic fit exactly: alpha 1.0%/mo, MKT 1.5, HML 0.2,
  R² = 1.0 — so the estimator and the t-stat plumbing are correct before any real
  number is trusted.
- `factor_regression()` on a synthetic 24-formation book returns 24 observations
  and a 12-observation overlap-free fit.
- Full re-run at `--sample-n 2600` reproduced the committed economics exactly
  (10,230 records, 71 windows ≥80, 66 scored, 4+/11−, net +0.9598%) before the
  artifact was replaced — the regression did not perturb the backtest.
- `pytest tests/test_hypothesis_status.py` → 7 passed; `H-150`
  `PRE-REGISTERED` normalises to `PRE_REGISTERED`, and the registry has no
  duplicate keys (strict `object_pairs_hook` audit).

## Limitations

- Overlapping monthly fits have autocorrelated residuals; classical OLS t-stats
  are optimistic, which is why the overlap-free fit is reported alongside and is
  the number to trust.
- The regression covers the top quintile (what the tool holds), not the decile
  reported in §5 of the report.
- H-150 is registered only: quarterly XBRL framing, next-open entry, a 20–60
  calendar-day exit and a top-quintile book are all still unbuilt.
