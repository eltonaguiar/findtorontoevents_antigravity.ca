# 06 — Statistical Validation Framework

**Date:** 2026-11-14 | **Purpose:** mandatory gates to label any approach “statistically valid / profitable” (research or deployable)

## 1. Core Principles
- **Evidence hierarchy:** live net returns > paper forward > OOS backtest > in-sample. No in-sample-only claims.
- **No aggregate claims from broken data:** system-level profitability assertions are invalid until `05_data_quality_remediation` passes.
- **Reproducibility:** every reported result must be reproducible from versioned code, data window, parameters, and cost model.
- **Multiple-testing awareness:** assume many trials; require controls (PBO/DSR/holdout) to avoid luck.

## 2. Required Metrics & Gates

| Metric | Target (strict / T2) | Minimum (basic) | Notes |
|---|---|---|---|
| Profit Factor (PF) | ≥ 1.5 | > 1.2 (contextual) | Net of costs; report gross & net |
| Sharpe (annualized, strategy-appropriate) | ≥ 1.0 | > 0.5 | Use consistent bar frequency/risk-free convention |
| Max Drawdown (MDD) | < 20% (prefer < 15%) | < 25% | On equity curve with stated sizing |
| Win Rate (WR) | ≥ 50% (preferred) | strategy-dependent | Not sufficient alone; pair with payoff/PF |
| Trade/sample count (n) | ≥ 100 (≥ 500 crypto preferred, Grok) | ≥ 30–50 | Higher for intraday; per-symbol and pooled |
| PBO (Probability of Backtest Overfitting) | **< 0.3** | < 0.5 | CSCV/bootstrap; report method & trials |
| DSR / Prob(Sharpe > 0) | **> 0.95** (prefer > 0.99) | > 0.95 | Deflated Sharpe or analytical P(SR>0); handle NaN with explicit calc |
| t-stat / significance (where applicable) | p < 0.05 (contextual) | report | e.g. walk-forward/return tests; avoid p-hacking |
| Stability | positive across subperiods/symbols/regimes | no single-slice dependence | Report dispersion, not just pooled |

**Deployment rule:** candidate must pass **all strict gates** on clean OOS (or justified equivalent) **and** a paper-forward period before live capital.

## 3. Test Protocol
1. **Data integrity:** verified marks, correct PnL units, no leakage (point-in-time), survivorship/bias checks where relevant.
2. **Split:** chronological train/test (and/or walk-forward). Parameter selection on train only; freeze for OOS.
3. **Costs & realism:** include commissions, spread/slippage (e.g. 10–50bps RT stress), funding/rollover/carry as applicable; capacity/latency assumptions stated.
4. **Regime/symbol robustness:** report per-symbol and pooled; test regime filters explicitly (e.g. MR-compatible vs trending).
5. **Position sizing:** state sizing (fixed/vol-targeted/fractional); report MDD and returns under that sizing.
6. **Sensitivity:** perturb key params, costs, and universe; edge should persist directionally.
7. **Benchmark:** compare to buy-and-hold/risk-matched baseline where meaningful.

## 4. Evidence Tiers (used in final_v2)

| Tier | Meaning | Examples (this review) |
|---|---|---|
| PROVEN (research) | Strong long-horizon OOS/research stats, reproducible spec | ITERATION-005 TSMOM (7.4y, Sharpe 2.13, CI [1.25,3.25]) |
| VALIDATED (basic/conditional) | OOS positive, basic gates pass, some strict gates unmet (e.g. PBO/sample) | Kilo VWAP-MR v11/v12 (PBO ~0.48-0.49) |
| PILOT | Suggestive stats but below targets or limited scope | deepAI Variant C (PF 1.26, p<0.0013) |
| CANDIDATE | Promising but unreplicated / leakage-risk / incomplete validation | flaxen-hair mega_mutation_macd_rsi/ema_momentum |
| BUILD/UNPROVEN | No validated edge yet | Bonds, MF, Forex, Commodities (current state) |

## 5. Reporting Checklist (per strategy)
- [ ] Universe, timeframe, sample window, n (per-symbol/pooled)
- [ ] Gross & net PF/Sharpe/WR/ret/MDD, equity curve notes
- [ ] PBO method/value, DSR or P(SR>0), significance tests
- [ ] Cost model + sensitivity, sizing rule
- [ ] Train vs OOS (and walk-forward folds if used)
- [ ] Failure modes, regime dependence, excluded symbols/periods
- [ ] Code/data provenance and reproduction command

## 6. Current Gaps (from this audit)
- VWAP-MR: **PBO 0.48–0.49** (needs more history/trades), symbol selectivity matters.
- Variant C: **PF below 1.5**, needs replication/scale.
- mega_mutation: **replication & leakage audit** required.
- System-wide: **data/PnL integrity** must be fixed before trusting any aggregate/live metric.
