# Residual mean-reversion book — built, first pass, no verdict yet (2026-11-20)

## What was built

[`tools/residual_mean_reversion.py`](tools/residual_mean_reversion.py) — market-neutral
residual mean reversion in the Avellaneda–Lee shape:

- [`ols()`](tools/residual_mean_reversion.py:70) solves the normal equations with partial
  pivoting and returns `None` on a singular system rather than garbage coefficients. No
  numpy, so the tool runs anywhere the rest of `tools/` does.
- [`ou_fit()`](tools/residual_mean_reversion.py:102) fits AR(1) to the residual: `rho` from
  the lag-1 regression, `kappa = 1 - rho`, `mu`, half-life `ln2/kappa`, and `sigma_eq`.
  `kappa <= 0` returns `None` — an honest "no mean reversion", not a tiny positive number
  manufactured from noise.
- [`simulate()`](tools/residual_mean_reversion.py:170) is walk-forward: every fit at bar
  `t` uses only `[t-window:t]`, the hedge is beta-weighted by the fitted loadings, and a
  position is skipped when the fitted half-life exceeds half the window.
- [`summarize()`](tools/residual_mean_reversion.py:210) reports `profit_factor: None`
  when there are no losses, instead of dividing by zero or printing infinity.

## The caveat I refused to drop

AR(1) on a finite sample is biased **downward** in `rho` (the Dickey–Fuller bias), so a
pure random walk yields `kappa > 0` and a short-looking half-life even when nothing
mean-reverts. One of my own tests hit this: a random walk fitted a 6.01-day half-life. I
did not relax the test to make it green — I documented the bias in `ou_fit`'s docstring and
pinned the biased behaviour as *known*, because a half-life can only ever **exclude** a
candidate. It is a filter, never a verdict.

## First pass on real bars

`python3 tools/residual_mean_reversion.py --fetch --symbol SPY --factors QQQ IWM TLT`
— 2,514 daily bars, window 60, 5 bps/leg:

| metric | value |
|---|---|
| trades | 153 |
| mean net | +0.1997% |
| win rate | 49.0% |
| profit factor | 1.279 |
| mean hold | 7.24 days |
| exits | 54 revert / 0 stop / **99 time** |

## Why this is not a "supported" result

The pre-registered statistic for H-2026-11-20-01 is the **walk-forward net Sharpe over 5
purged folds with a paired-block CI**. Neither was computed here, so neither the
`min_sharpe: 0.5` bar nor the "CI excludes 0" test has been evaluated. A positive mean on
one configuration is not evidence.

Two structural facts are already negative, though:

1. **99 of 153 trades (65%) exited on the time cap, never on reversion.** The residual
   did not snap back within the holding period for two thirds of entries. That is exactly
   the failure mode the hypothesis's own operator note warned about — a trend bet wearing
   a mean-reversion label.
2. **A full-sample OU fit of the SPY residual returns `None`** — `rho >= 1`, `kappa <= 0`.
   Over ten years the residual shows no estimated mean reversion at all. Only rolling
   60-day fits produce tradeable half-lives, which is more consistent with the
   Dickey–Fuller bias than with a stable OU process.

A 49% win rate at PF 1.28 also means the mean is carried by a few large winners, not by
consistency — the opposite of what a mean-reversion book should look like.

## Verification

- `python3 -m pytest tests/test_residual_mean_reversion.py -q` → **12 passed**
- Run artifact: [`reports/residual_mr_2026-11-20.json`](reports/residual_mr_2026-11-20.json)
- Registry: H-2026-11-20-01 updated with the numbers, the two negative structural facts,
  and an explicit statement that the primary statistic was *not* computed.

## Next

Fold-level Sharpe and the paired-block CI on the same signal set — not a bigger sample.
More configurations before the pre-registered test would be trial inflation.
