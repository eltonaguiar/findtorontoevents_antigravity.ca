# PLAN — Mutual Funds / Low-Cost ETFs (Core, not alpha)

**Status:** Core allocation. **Gap filled:** MF/ETF class has zero coverage; infrastructure does not exist.

## Hypothesis
A **rules-based selection + allocation** of low-cost mutual funds / ETFs (expense ratio ≤ 0.20% equity, ≤ 0.10% ETF, AUM ≥ $1B, no load) can capture the equity risk premium + bond yield with minimal active risk, over 10+ years.

## Gap it fills
This is not an alpha test — it is a *beta capture* test. The edge is cost discipline + diversification, not prediction.

## Method
- **Signal:** rank funds by 3-year Sharpe + expense ratio; select top 5; equal-weighted
- **Universe:** 100+ US mutual funds / ETFs
- **Timeframe:** Daily, 2010-2026
- **Hold:** Quarterly rebalance
- **Cost model:** expense ratio + 0.05% transaction fee
- **Benchmark:** S&P 500 total return (for equity sleeve), Bloomberg Agg (for bond sleeve)

## Proof tests
1. ✅ Temporal (2010-2018 / 2019-2026)
2. ✅ WFO (4-year)
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (bootstrap)
5. ✅ Friction (expense + transaction)
6. ✅ Significance (excess vs benchmark)
7. ✅ Regime (bull/bear/sideways)
8. ✅ Shuffle control (must NOT reproduce — this is beta, not alpha)
9. ✅ Forward (5-year paper — MF/ETF are long-horizon)
10. ✅ Reproducibility

## Expected outcome
This is the highest-probability lower-risk path. Expected: positive real returns over 10+ years, but will not consistently beat the market by large margins after costs (by construction for pure index). The honest claim is "measurable, rule-based allocation with a defined, defensible expected outcome" — not "beat the market".