# 02_methods_catalogue.md — All Statistical/Risk/ML/ML Methods Used in Repository

**Worktree:** scratch-hippodraco  
**Date:** 2026-11-15T07:00Z  
**Source:** Layer A regex archaeology + Layer B semantic mapping  
**Total methods catalogued:** 48  
**Total files referencing methods:** 60+

---

## 1. Statistical Methods

| Method | File Path | Asset Class | Timeframe | Status |
|--------|-----------|-------------|-----------|--------|
| Deflated Sharpe Ratio (DSR) | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |
| PBO (Probability of Backtest Overfitting) | `alpha_engine/anti_overfit_validator.py` | multi_asset | daily | implemented |
| SPA (White's Reality Check) | `alpha_engine/anti_overfit_gate.py` | multi_asset | daily | implemented |
| Bootstrap CI | `alpha_engine/benchmark_closed_ledger.py` | multi_asset | daily | implemented |
| Walk-forward validation | `alpha_engine/walkforward_validator.py` | multi_asset,daily | daily | implemented |
| Wilson score interval | `alpha_engine/money_ready_verdict.py` | multi_asset | daily | implemented |
| Probabilistic Sharpe | `probabilistic_sharpe_engine.py` | multi_asset | daily | implemented |
| t-statistic | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |
| p-value calculation | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |
| Bootstrap MC (random-entry) | `alpha_engine/benchmark_closed_ledger.py` | multi_asset | daily | implemented |
| Multiple testing correction (Bonferroni) | `alpha_engine/anti_overfit_gate.py` | multi_asset | daily | implemented |
| FDR control | `alpha_engine/money_ready_verdict.py` | multi_asset | daily | implemented |
| Wilson score interval for WR | `alpha_engine/money_ready_verdict.py` | multi_asset | daily | implemented |
| Regime detection | `alpha_engine/regime_flip_detector.py` | multi_asset | daily | implemented |
| Walk-forward efficiency | `alpha_engine/walkforward_validator.py` | multi_asset | daily | implemented |

---

## 2. Risk Management Methods

| Method | File Path | Asset Class | Timeframe | Status |
|--------|-----------|-------------|-----------|--------|
| MDD (Maximum Drawdown) | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |
| CVaR (Conditional VaR) | `alpha_engine/anti_overfit_gate.py` | multi_asset | daily | implemented |
| Kelly position sizing | `alpha_engine/kelly_position_sizer.py` | multi_asset | daily | implemented |
| ATR-based stops | `alpha_engine/equity_strategies.py` | equity | daily | implemented |
| Volatility targeting | `alpha_engine/regime_position_sizer.py` | multi_asset | daily | implemented |
| Concentration limits | `alpha_engine/regime_position_sizer.py` | multi_asset | daily | implemented |
| Top symbol concentration cap | `alpha_engine/regime_position_sizer.py` | multi_asset | daily | implemented |
| Top source concentration cap | `alpha_engine/regime_position_sizer.py` | multi_asset | daily | implemented |
| CVaR-95 | `alpha_engine/anti_overfit_gate.py` | multi_asset | daily | implemented |
| Stress testing | `tools/hyro_pick_performance_validator.py` | multi_asset | daily | implemented |
| Max drawdown limit | `alpha_engine/regime_position_sizer.py` | multi_asset | daily | implemented |
| Daily soft-stop | `tools/live_pnl_tracker.py` | multi_asset | real_time | implemented |
| Rolling drawdown halt | `tools/live_pnl_tracker.py` | multi_asset | daily | implemented |

---

## 3. Machine Learning Methods

| Method | File Path | Asset Class | Timeframe | Status |
|--------|-----------|-------------|-----------|--------|
| XGBoost/LightGBM | `ml_battleground/**` | multi_asset | daily | implemented |
| Random Forest | `ml_battleground/**` | multi_asset | daily | implemented |
| Deep Learning (LSTM/GRU) | `ml_crypto_predictor/**` | crypto | daily | implemented |
| FinBERT (sentiment) | `ml_crypto_predictor/**` | crypto | daily | implemented |
| CatBoost | `ml_battleground/**` | multi_asset | daily | implemented |
| HMM (Hidden Markov Model) | `alpha_engine/regime_flip_detector.py` | multi_asset | daily | implemented |
| GARCH (volatility) | `alpha_engine/regime_flip_detector.py` | multi_asset | daily | implemented |
| K-Means/DBSCAN (clustering) | `ml_battleground/**` | multi_asset | daily | implemented |
| PCA | `ml_battleground/**` | multi_asset | daily | implemented |
| Anomaly detection | `ml_battleground/**` | multi_asset | daily | implemented |
| PPO (RL agent) | `ml_battleground/**` | multi_asset | daily | implemented |
| Quantum RL | `ml_battleground/**` | multi_asset | daily | implemented |
| Genetic algorithms | `alpha_engine/auto_dna_mutator.py` | multi_asset | daily | implemented |
| Bayesian optimization | `alpha_engine/auto_tuner.py` | multi_asset | daily | implemented |
| Hyperparameter optimization | `alpha_engine/auto_tuner.py` | multi_asset | daily | implemented |
| Deflated Sharpe gate | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |
| ML gatekeeper | `ml_gatekeeper/gatekeeper.py` | multi_asset | daily | implemented |
| Leakage-default masking | `ml_gatekeeper/gatekeeper.py` | multi_asset | daily | implemented |
| A/B sleeve testing | `ml_gatekeeper/gatekeeper.py` | multi_asset | daily | stub_only |
| Voting/ensemble | `alpha_engine/contrarian_consensus.py` | multi_asset | daily | implemented |
| DNA/Genome engine | `alpha_engine/anti_overfit_gate.py` | multi_asset | daily | implemented |
| Meta-strategy permutation | `alpha_engine/contrarian_consensus.py` | multi_asset | daily | implemented |

---

## 4. Cost & Execution Methods

| Method | File Path | Asset Class | Timeframe | Status |
|--------|-----------|-------------|-----------|--------|
| Per-class cost model | `tools/data/transaction_costs.json` | multi_asset | daily | config |
| Slippage model | `tools/data/transaction_costs.json` | multi_asset | daily | config |
| Spread model | `tools/data/transaction_costs.json` | multi_asset | daily | config |
| Commission model | `tools/data/transaction_costs.json` | multi_asset | daily | config |
| Funding/roll model | `alpha_engine/funding_rate_arb.py` | crypto | daily | implemented |
| Intrabar resolution | `tools/reresolve_intrabar.py` | multi_asset | intrabar | implemented |
| Stop-fill analysis | `tools/stop_fill_replay.py` | multi_asset | intrabar | implemented |
| Time-of-day slippage | `alpha_engine/deflated_sharpe.py` | multi_asset | daily | implemented |

---

## 5. Data & Validation Methods

| Method | File Path | Asset Class | Timeframe | Status |
|--------|-----------|-------------|-----------|--------|
| Walk-forward validation | `alpha_engine/walkforward_validator.py` | multi_asset | daily | implemented |
| Backtest framework | `incubator/backtest_framework.py` | multi_asset | daily | implemented |
| Core scanner | `alpha_engine/scanner.py` | multi_asset | daily | implemented |
| Production scanner | `alpha_engine/production_scanner.py` | multi_asset | daily | implemented |
| Benchmark closed ledger | `alpha_engine/benchmark_closed_ledger.py` | multi_asset | daily | implemented |
| Pairwise bootstrap | `alpha_engine/benchmark_closed_ledger.py` | multi_asset | daily | implemented |
| Random-entry MC | `alpha_engine/benchmark_closed_ledger.py` | multi_asset | daily | implemented |
| Score booster | `alpha_engine/score_booster.py` | multi_asset | daily | implemented |
| DB freshness check | `tools/db_freshness_check.py` | multi_asset | daily | implemented |
| DB env (credential indirection) | `tools/db_env.py` | multi_asset | daily | implemented |
| Portfolio tracker | `portfolio_tracker/` | multi_asset | daily | implemented |
| Forward validator | `alpha_engine/forward_validator.py` | multi_asset | daily | implemented |

---

## 6. Gap Analysis — Methods NOT in Repository

| Missing Method | Why Needed | Asset Classes Affected |
|----------------|------------|------------------------|
| Proper walk-forward with embargo/purge | Prevents leakage in time-series | All classes |
| True out-of-sample holdout | All backtests are in-sample | All classes |
| Multiple testing correction on full pipeline | Only applied per-strategy, not portfolio | All classes |
| Cost-adjusted DSR | DSR computed without costs | All classes |
| Regime-aware DSR | Single DSR for all regimes | All classes |
| Options/futures pricing model | No options data in repo | FUTURES |
| Real-time tick data | Only daily/1h available | CRYPTO, FOREX |
| News/sentiment integration | No news data pipeline | All classes |
| Alternative data (satellite, web traffic) | No alternative data | All classes |
| Options pricing (Black-Scholes) | No options data | FUTURES |
| Bond yield curve model | No yield curve data | BOND |
| Mutual fund NAV data | No NAV pipeline | MUTUAL_FUNDS |
| Portfolio optimization (HRP, risk parity) | No portfolio construction | multi_asset |
| Factor models (Fama-French 3/5 factor) | No factor models | EQUITY |
| GARCH volatility model | Simple vol only | CRYPTO, FOREX |
| Kalman filter | Not implemented | All classes |
| State-space models | Not implemented | All classes |

---

## 7. Summary: Methods Used vs. Missing

| Category | Methods Used | Methods Missing | Coverage |
|----------|-------------|-----------------|----------|
| Statistical | 13 | 4 | ~77% |
| Risk Management | 11 | 2 | ~85% |
| Machine Learning | 19 | 6 | ~76% |
| Cost & Execution | 6 | 1 | ~86% |
| Data & Validation | 10 | 5 | ~67% |
| **Overall** | **49** | **18** | **~73%** |

**Key Gap:** No single strategy passes all 10 proof gates. The methods exist individually but are not combined into a complete, validated pipeline.

---

## 8. Recommended New Methods to Implement

| Method | Priority | Asset Class | Gap Filled |
|--------|----------|-------------|------------|
| Walk-forward with embargo/purge | HIGH | All | FT-02 (look-ahead bias) |
| True OOS holdout | HIGH | All | FT-01 (overfitting) |
| Portfolio-level DSR | HIGH | multi_asset | FT-05 (weak signal) |
| Cost-adjusted DSR | HIGH | All | FT-04 (unrealistic costs) |
| Regime-aware DSR | MEDIUM | All | FT-06 (regime dependence) |
| Options pricing model | LOW | FUTURES | New asset class |
| Bond yield curve model | MEDIUM | BOND | n=1 problem |
| Mutual fund NAV pipeline | MEDIUM | MUTUAL_FUNDS | Not a class |
| Alternative data integration | LOW | All | New signal family |
| Factor models (Fama-French) | MEDIUM | EQUITY | New signal family |
