# INTERPRETATION — etfs_dual_momentum_20261115_001

**Verdict: DEAD (5/9 offline gates).** This is the honest result of a pre-registered test, and it is the most informative single number this repo has produced: dual momentum is a **drawdown-control tool, not an alpha source.**

## What the run actually found

| Metric (2019-01-01 → 2026-11-15, locked holdout) | Dual momentum | SPY buy & hold |
|---|---|---|
| CAGR | **10.93%** | 16.79% |
| Sharpe | 0.79 | 0.90 |
| Volatility | 14.4% | 19.2% |
| Max drawdown | **−25.7%** | −33.7% |
| Calmar | 0.43 | 0.50 |
| Monthly trades | 236 | — |
| Monthly hit rate | 56.8% | — |
| Monthly profit factor | 1.68 | — |

- **Excess vs SPY:** −5.96%/yr, t = −1.17, one-sided p = 0.878.
- **Bootstrap CI on excess (block bootstrap, 2,000 paths):** [−13.5%, +2.0%]; only **7.4%** of paths positive.
- **Deflated Sharpe:** 0.1382 at 1,307 project trials → fails decisively.
- **Shuffle control:** real Sharpe 0.60 vs shuffled mean 0.82, p95 1.15; the real strategy is beaten by **90% of permuted-price variants**.

## Why it failed, precisely

1. **The ranking adds nothing.** Shuffle control is the decisive evidence: randomising each ETF's daily returns produces *better* Sharpe than the real signal. With seven highly-correlated equity/bond/gold ETFs, cross-sectional ranking of 12-1 momentum is mostly noise — the strategy's return comes from its **asset mix and cash filter**, not from picking.
2. **The absolute filter did its job — for risk, not return.** Drawdown 25.7% vs 33.7% and vol 14.4% vs 19.2% confirm the 10-month SMA exits cut downside. It also means the portfolio is out of the market during early recoveries, which is exactly what cost 5.96%/yr in a period where SPY compounded at 16.8%.
3. **Regime dependence is mild but real:** uptrend +16.8%, downtrend −22.2%, high-vol −0.9%. Positive in 3/5 regimes — enough to pass the regime gate, not enough to matter.

## What this changes in the plan

- **`Plan/etfs/` is now closed as an alpha candidate.** Re-testing dual momentum with different SMA/momentum lengths is exactly the parameter-hunting the standard forbids. Any future ETF work must be a *different* hypothesis (e.g. cross-asset carry, or a drawdown-targeted allocation that claims risk control rather than outperformance).
- **The honest product claim this supports:** "a rules-based rotation that historically reduced max drawdown by ~8 points at the cost of ~6 points of annual return vs SPY." That is a defensible, measurable, sellable statement — and it is *not* "we beat the market."
- **`Plan/multi_asset/` gains an input:** the 10-month SMA overlay is a validated drawdown reducer. Use it in the core-satellite allocation as a risk overlay, benchmarked against static 60/40, not sold as alpha.

## Reproduction

```bash
cd WIRED_IN/2026-11-15_0708/HERMES_WIN_inspect-wt
python experiments/etfs_dual_momentum_20261115_001/run.py
```

Data is cached in `data_cache.csv` (yfinance adjusted close, downloaded 2026-11-15) so the run is offline-reproducible. Seed 42, 100 shuffles, 2,000 bootstrap paths.

## Trial count update

This run increments the project-wide trial count. `project_trials = 1307` in `config.json` is the *pre-existing* estimate; with this run the honest count is **1308**. The deflated-Sharpe gate should be recomputed with 1308 for the next candidate — the correction only gets harsher.
