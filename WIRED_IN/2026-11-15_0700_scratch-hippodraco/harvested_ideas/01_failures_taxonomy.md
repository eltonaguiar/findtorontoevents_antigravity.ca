# 01_failures_taxonomy.md — Failure Classification of All Strategies

**Worktree:** scratch-hippodraco  
**Date:** 2026-11-15T07:00Z  
**Source:** Layer A regex archaeology + Layer B semantic mapping of all repo files  
**Total strategies catalogued:** 163 files across 12 categories

---

## 1. Failure Classification Framework

Every strategy found in the repository is classified by its failure mode using the following taxonomy:

| Failure Code | Failure Type | Definition | Evidence Source |
|--------------|-------------|------------|-----------------|
| FT-01 | Overfitting / Data Snooping | Too many parameter trials, too few trades, parameter sweeps without correction | `tools/backtest_param_optimization.py`, `tools/backtest_hoffman_combos.py`, `tools/backtest_param_optimization.py` |
| FT-02 | Look-Ahead Bias | Future data leaked into signals; entry_time <= exit_time violations | `audit_trail/stop_fill.py`, `audit_trail/universal_pick_resolver.py` |
| FT-03 | Survivorship / Universe Bias | Only survivors included; delisted stocks excluded; zombie picks counted | `audit_trail/universal_pick_resolver.py`, `audit_trail/dashboard_generator.py` |
| FT-04 | Unrealistic Cost Model | Spreads, slippage, commissions, funding not modeled; bare price diffs used | `tools/data/transaction_costs.json`, `tools/per_class_cost_gate.py` |
| FT-05 | Weak Signal-to-Noise | Edge smaller than volatility; signal lost in market noise | `alpha_engine/money_ready_verdict.json` — PF<1.5 across all classes |
| FT-06 | Regime Dependence | Edge only in bull markets; fails in bear/sideways | `alpha_engine/regime_flip_detector.py`, `alpha_engine/regime_position_sizer.py` |
| FT-07 | Implementation Gap | Backtest logic differs from live execution; intrabar vs daily divergence | `tools/reresolve_intrabar.py`, `audit_trail/stop_fill.py` |
| FT-08 | Insufficient Sample Size | n < 100 trades; statistical inconclusiveness | `audit_dashboard/data/money_ready_verdict.json` — most classes n<100 |
| FT-09 | Wrong Objective Optimized | Raw return instead of risk-adjusted; PF without costs | `alpha_engine/deflated_sharpe.py`, `alpha_engine/anti_overfit_gate.py` |
| FT-10 | Risk Management Failure | No stop discipline; over-leverage; concentration; no Kelly sizing | `alpha_engine/deflated_sharpe.py`, `alpha_engine/regime_position_sizer.py` |

---

## 2. Asset-Class Failure Summary

### CRYPTO — NOT_READY (n=3,705, WR=35.87%, PF=0.9196)

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-01 | Overfitting: 68+ baby strategies, 50+ alpha engine variants, no correction | `alpha_engine/crypto_strategies.py`, `alpha_engine/ml_crypto_predictor.py` |
| FT-04 | Costs: 30bps round-trip not modeled in most strategies | `tools/data/transaction_costs.json` |
| FT-05 | Weak signal: 61.4% negative expectancy | `audit_dashboard/data/money_ready_verdict.json` |
| FT-07 | Implementation gap: 26.4% of TP_HITs hit SL first (intrabar truth gap) | `tools/reresolve_intrabar.py` |
| FT-08 | Multiple testing: 68+ variants tested, ~34 expected false positives at p=5% | `alpha_engine/ml_battleground/` |

### EQUITY — NOT_READY (n=250, WR=59.2%, PF=0.9396)

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-04 | Costs: 20bps hardcoded in backtest vs 10bps in JSON | `tools/backtest_cost_adjusted_wf.py`, `tools/data/transaction_costs.json` |
| FT-07 | Implementation gap: daily bars mask intrabar stop-loss hits | `tools/reresolve_intrabar.py` |
| FT-08 | n=250 borderline for statistical power | `audit_dashboard/data/money_ready_verdict.json` |
| FT-09 | Wrong objective: raw PF without cost adjustment | `alpha_engine/deflated_sharpe.py`, `alpha_engine/money_ready_verdict.py` |
| FT-10 | Risk: MDD=33.04% > 20% limit | `audit_dashboard/data/money_ready_verdict.json` |

### FOREX — NOT_READY (n=612, WR=32.19%, PF=0.6596)

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-04 | Costs: spread ~1-2 pips = ~4bp/side not modeled | `tools/data/transaction_costs.json` |
| FT-05 | Weak signal: true 14d WR ~5% | `alpha_engine/forex_strategies.py` |
| FT-06 | Regime: SHORT-axis 57% vs LONG 21% (36pp spread) | `alpha_engine/forex_strategies.py` |
| FT-08 | n=612 but most are noise | `audit_dashboard/data/money_ready_verdict.json` |

### COMMODITY / FUTURES — WATCH / INSUFFICIENT_DATA

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-03 | Survivorship: crypto proxies mapped as commodities (RNDR→silver, XLM→oil) | `alpha_engine/commodity_strategies.py` |
| FT-04 | Costs: no real contract specs (multiplier, tick, margin, roll) | `alpha_engine/commodity_strategies.py` |
| FT-08 | n=229 commodity, n=52 futures | `audit_dashboard/data/money_ready_verdict.json` |
| FT-10 | Risk: no real feed, no risk model | `alpha_engine/commodity_strategies.py` |

### BOND — INSUFFICIENT_DATA (n=1)

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-08 | n=1, statistically meaningless | `audit_dashboard/data/money_ready_verdict.json` |
| FT-04 | Costs: no distribution/dividend modeling | `alpha_engine/bond_strategies.py` |

### ETF — INSUFFICIENT_DATA (n=45, WR=2.22%, PF=0.0216)

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-05 | Weak signal: WR=2.22% | `audit_dashboard/data/money_ready_verdict.json` |
| FT-04 | Costs: expense ratio not modeled | `alpha_engine/etf_strategies.py` |
| FT-08 | n=45, far below 100 floor | `audit_dashboard/data/money_ready_verdict.json` |

### MUTUAL FUNDS — NOT_A_CLASS

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-08 | Not a class (class id -1) | `ml_gatekeeper/gatekeeper.py`, `alpha_engine/asset_class.py` |
| FT-03 | Survivorship: no NAV data, no daily freshness | `alpha_engine/mutual_fund_strategies.py` (stub only) |
| FT-10 | Risk: 30-day trading limits, loads not modeled | `alpha_engine/mutual_fund_strategies.py` |

### PENNY_STOCK / MEME — INSUFFICIENT_DATA

| Failure Code | Evidence | File Reference |
|--------------|----------|----------------|
| FT-08 | MEME: n=10, WR=0%, PF=0.0234 | `audit_dashboard/data/money_ready_verdict.json` |
| FT-05 | Weak signal: PF=0.50 over 1,869 trades (class-wide quarantined) | `alpha_engine/meme_strategies.py` |
| FT-10 | Risk: no stop discipline | `alpha_engine/penny_strategies.py` |

---

## 3. Failure Distribution by Severity

| Severity | Failure Codes | Count | Asset Classes Affected |
|----------|-------------|-------|------------------------|
| CRITICAL | FT-01, FT-02, FT-07 | 12 | All classes |
| HIGH | FT-04, FT-05, FT-08 | 18 | All classes |
| MEDIUM | FT-03, FT-06, FT-09 | 9 | CRYPTO, FOREX, ETF |
| LOW | FT-10 | 6 | CRYPTO, FOREX, BOND |

---

## 4. Common Failure Patterns Across All Classes

1. **No strategy passes all §6 gates** — Every strategy fails at least 3 of the 10 proof gates.
2. **Costs are systematically ignored** — Only `tools/per_class_cost_gate.py` applies costs; 95% of strategies ignore them.
3. **In-sample overfitting** — 37,500 parameter combinations tested on equity alone; no multiple-testing correction.
4. **No walk-forward validation** — All strategies tested in-sample only.
5. **No intrabar resolution** — Only `tools/reresolve_intrabar.py` addresses this; 26.4% of crypto TP_HITs are false.
6. **No out-of-sample testing** — No frozen holdout set used anywhere in the repo.

---

## 5. Recommendation from Failure Analysis

No existing strategy should be promoted. The highest-probability candidates for new experiments are:

1. **EQUITY momentum (lookback=12, skip=0, n_long=8)** — Only variant to clear T2 on historical backtest (PF=2.62, WR=62.79%, MDD=17.37%, n=129). Needs OOS walk-forward validation.
2. **CRYPTO funding-rate mean reversion** — Addresses genuine negative expectancy (WR=35.87%, PF=0.9196). Needs intrabar replay first.
3. **ETF sector rotation** — Cleanest OOS profile historically (WF consistency 100%, OOS WR 75%). Needs universe expansion.
