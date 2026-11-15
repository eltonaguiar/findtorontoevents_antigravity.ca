# PLAN — Equity (US stocks)

**Status:** Pre-registered, NOT yet run. **Gap filled:** F6/F7/F25/F27 (quality-momentum, dual momentum, intrabar resolver, VPIN reversion all failed on significance or walk-forward).

## Hypothesis
A **cross-sectional quality-momentum factor** (top decile by ROIC + 12-1 momentum, rebalanced monthly, equal-weighted) will produce a positive information ratio vs SPY total return after realistic costs, across multiple regimes, when tested with strict temporal discipline and a locked holdout.

## Gap it fills
F6 (quality-momentum, p=0.12) failed on significance vs SPY. This plan fixes that by:
1. **Pre-registration before any backtest** — no parameter hunting
2. **Cross-sectional (relative) construction** — reduces regime dependence that killed F7
3. **Explicit cost model** — commission $0.005/share + 0.03% slippage + 0.05% market impact
4. **Locked holdout** — last 24 months never touched until selection complete

## Method
- **Signal:** `score = 0.5 × z(ROIC_5yr) + 0.5 × z(momentum_12_1)` on S&P 500 constituents
- **Universe:** S&P 500 (500 names), liquid large-caps only
- **Timeframe:** Daily bars, 2010-01-01 → 2026-11-15
- **Rebalance:** Monthly, top 20 names, equal-weighted
- **Cost model:** $0.005/share commission + 0.03% slippage + 0.05% market impact per trade
- **Benchmark:** SPY total return (dividend-reinvested) over the same period

## Parameter ranges
- Momentum lookback: 12 months (fixed — not a sweep parameter)
- Quality window: 5 years (fixed)
- Rebalance frequency: monthly (fixed)
- Universe: S&P 500 (fixed)
- **No parameter sweep planned** — this is a single pre-registered configuration

## Data source
`yfinance` (declared in requirements.txt), S&P 500 constituents from Wikipedia/etfdb.com, monthly rebalance dates

## Proof tests it will pass (§6)
1. ✅ Temporal discipline: train 2010-2022, test 2023-2026 (locked, no touching)
2. ✅ Walk-forward: 4-year rolling windows, report efficiency + parameter stability
3. ✅ Multiple testing: state total configs tried (1 — this is the only one)
4. ✅ Monte Carlo: block bootstrap (arch>=7.0.0), report % positive paths + 5th percentile
5. ✅ Friction model: full cost model above
6. ✅ Significance: bootstrap CI for mean excess return, t-stat, p-values
7. ✅ Regime split: bull/bear/sideways, high/low vol — require positive expectancy in majority
8. ✅ Shuffle control: permuted prices must NOT reproduce performance
9. ✅ Forward test: pre-registered paper-trading protocol (6 months)
10. ✅ Reproducibility: fixed seeds, versioned data, documented formulas

## Expected outcome
If the pre-registered test fails, the honest verdict is "no edge found in cross-sectional quality-momentum on S&P 500" — and we pivot to a different signal family (carry, volatility, or cross-sectional crypto).