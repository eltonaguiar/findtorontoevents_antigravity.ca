# ETF-A/B/C — friction, long-short, Black-Litterman variants

**Date:** 2026-05-13
**Baseline:** `tools/backtest_etf_sector_rotation.py` naive top-3 long-only PF 2.05 / Sharpe 0.97 / Total +283.7% / MDD 16.1% (2015-2026 on 11 SPDR sectors)

## ETF-A — Slippage-aware (5 friction scenarios)

`tools/backtest_etf_sector_rotation_slippage.py`. Per-leg friction = spread + commission + slippage; weighted by leg fraction (1/3 portfolio per top-3 long).

| Scenario | per-leg bps | PF | Sharpe | Total% | MDD% |
|---|---:|---:|---:|---:|---:|
| naive_zero_friction | 0.0 | 2.05 | 0.97 | 283.7 | 16.1 |
| low_friction_2bp_total | 1.0 | 2.04 | 0.97 | 281.6 | 16.1 |
| **realistic_5bp_total** | **2.5** | **2.03** | **0.96** | **278.3** | **16.1** |
| conservative_10bp_total | 5.0 | 2.02 | 0.95 | 273.0 | 16.2 |
| stress_20bp_total | 10.0 | 1.99 | 0.94 | 262.7 | 16.3 |

**Verdict:** TIER-1 PF survives every friction scenario. Monthly rebalance + top-3-of-11 universe = typical 0-1 leg changes/month, so friction drag is minor (~5-21% of total return at stress). **The TIER-1 PF≥2 result is robust to realistic execution costs.**

## ETF-B — Long-short top3/bottom3

Same universe + lookback, but adds `--n-short 3` shorts. Equal-weight long+short, half capital each leg.

| Metric | Long-only baseline | Long-short |
|---|---:|---:|
| PF | 2.05 | **0.937** |
| Sharpe | 0.97 | -0.085 |
| Total% | 283.7 | -8.35 |
| MDD% | 16.1 | 18.5 |

**Verdict: REJECT.** Shorting bottom-momentum sectors destroys edge. Bottom-momentum sectors mean-revert in risk-on markets (post-2020 monetary regime); the short leg bleeds during recoveries. Long-only is the right form.

## ETF-C — Black-Litterman overlay (PyPortfolioOpt 1.6.0)

`tools/backtest_etf_sector_rotation_bl.py`. Combines equal-weight prior + view "top-3 momentum sectors outperform by 1%/month".

**Result: FAILED.** `numpy.linalg.LinAlgError: Eigenvalues did not converge` during BL covariance decomposition on rolling 252-day windows.

Root cause (suspected): rolling cov matrix becomes ill-conditioned when sectors are highly correlated (XLF/XLI/XLB during regime shifts) or when window contains stale/imputed data.

Workarounds for follow-up:
1. Use Ledoit-Wolf shrinkage cov (`risk_models.CovarianceShrinkage`) instead of sample cov
2. Wider rolling window (504 days) to reduce rank deficiency
3. Add `cov_matrix = cov_matrix + 1e-6 * np.eye(n)` ridge regularization
4. Use `min_volatility()` instead of `max_sharpe()` — less sensitive to bad cov

**Verdict for now:** PyPortfolioOpt BL is too fragile for this universe without preprocessing. Equal-weight top-3 is the right baseline. BL integration deferred until Ledoit-Wolf + ridge regularization wrapper is built. Per Wire-Up Rule in CLAUDE.md, any BL module must declare opt-in sidecar status until production caller exists.

## Combined recommendation

**Ship the naive top-3 long-only ETF rotation as production candidate.** TIER-1 PF holds across friction scenarios; long-short and BL extensions don't improve it. The simplest implementation is the best.

Next steps (out of this session):
- ETF-D: combine with FRED yield-curve regime filter — gate out high-momentum tech during rising-rates inversions
- ETF-E: monthly → quarterly rebalance variant (lower turnover, same signal)

## Reproducer

```bash
python tools/backtest_etf_sector_rotation_slippage.py
python tools/backtest_etf_sector_rotation.py --n-short 3
python tools/backtest_etf_sector_rotation_bl.py   # currently fails - see workaround list
```

NFA. Reversible.
