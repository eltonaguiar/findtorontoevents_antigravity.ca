# Methods Catalogue — Statistical, Risk, ML, and Data Techniques Already Used

Harvested from the repo by Layer‑B semantic scan. Every entry has a file citation. **Rule: do not propose anything in the "Already used" column as a new experiment without explaining what is different.**

## 1. Machine learning / statistical models

| Technique | Where | Notes |
|---|---|---|
| Random forest / gradient boosting | `baby_strategies/kimi_lgbm_features.py`, `alpha_engine/advanced_statistical_strategies.py` | LightGBM (lgbm) is the dominant booster; XGBoost keyword present in imports, no production model |
| PCA | `analysis/score_calibration.py` | Used for feature decorrelation before ranking |
| Kalman filter | `alpha_engine/bayesian_regime_reference.py` | State estimation for regime/momentum only; not a standalone strategy |
| Bayesian optimisation | `alpha_engine/bayes_optimizer.py` | Hyper‑parameter search; contributes to multiple‑testing load |
| HMM / regime switching | `analysis/score_calibration.py`, `alpha_engine/regime_detector.py` | Regime labels used as a filter across classes |
| ARIMA / SARIMA / Prophet | `alpha_page_tmp.txt`, research .md only | Documented in `25_Quantitative_Trading_Algorithms.md`; no production backtest module found |
| Conformal prediction | `audit_trail/conformal_sizing.py` | Sizing intervals, not direction |
| LSTM / Transformer | research .md only (`WORLDCLASS_CRYPTO_PREDICTION_SYSTEM.md`) | **Never implemented in a runnable, seeded backtest** — a genuine gap |
| SVM / clustering | `analysis/*`, `ab_testing_agent/*` | Used for calibration/AB tests, not signals |

## 2. Backtesting & validation infrastructure

| Technique | Where | Notes |
|---|---|---|
| Walk‑forward optimisation | `analysis/walkforward_optimizer.py`, `walk_forward_validator.py` | `min_train_trades=10/20`, `min_consistency=0.5`, annualised Sharpe via `sqrt(252)` |
| Grid / parameter sweep | `alpha_engine/auto_tuner.py` | Largest source of multiple‑testing inflation |
| Block bootstrap (arch) | `tools/block_bootstrap_ci.py` | `arch>=7.0.0`: MovingBlockBootstrap, StationaryBootstrap — real, shipped |
| Per‑class cost gate (3× round‑trip) | `tools/per_class_cost_gate.py` | `REQUIRED_COST_MULTIPLE = 3.0`, output `config/per_class_cost_gate.json`, deliberately fail‑open on emission |
| Stop‑fill replay | `tools/stop_fill_replay.py` | `--truncate-at-exit`; the B4 fix; 30 crypto + 25 equity + 25 ETF replays |
| Gap‑aware fill resolver | `audit_trail/universal_pick_resolver.py` | `RESOLVER_GAP_AWARE_FILL` env, default "1"; **crypto only** |
| COT contrarian backtest | `tools/cot_contrarian_backtest.py` | **Failed 4/4** pre‑registered checks — an honest negative result |
| A/B test framework | `ab_testing_agent/` | `experiment_manager.py`, `statistics.py` |

## 3. Risk & metrics

| Technique | Where | Notes |
|---|---|---|
| Sharpe / Sortino / Calmar / Sterling | `risk_adjusted_analysis.py`, `audit_trail/mercury2_scoring.py` | Sterling implemented; Calmar underused in gates |
| Kelly sizing | `tools/per_class_cost_gate.py`, `risk_management/` | Quarter‑Kelly (2.46%/trade) adopted in final_v4 risk page |
| ATR stops / trailing stops | `adaptive_stops.py`, `alpha_engine/advanced_risk_system.py` | Multiple ATR multiples tested; none universal |
| Drawdown halt rules | `audit_trail/auto_rollback_triggers.py` | Daily/weekly/monthly halts scaffolded |
| Value‑at‑Risk / Expected Shortfall | `final_v4/inspect-wt/03_risk_management/` | VaR95 flagged small‑sample in the risk page |
| Probability of ruin | `risk_quantification_agent.py` | Bootstrap‑based |
| Bootstrap CI for mean excess return | `tools/block_bootstrap_ci.py` | Shipped |

## 4. Data & execution

| Technique | Where | Notes |
|---|---|---|
| yfinance OHLCV | 153 `alpha_engine/*` modules | Declared in `requirements.txt` (fix for the ETF/Bond zero‑pick bug) |
| FRED (fredapi) | bond modules, `bond_strategies.py` | Yield/curve data |
| Binance / ccxt | crypto scanners | Binance primary; ccxt present |
| MySQL / PyMySQL | 54 files (22 unguarded imports) | Historical pick tracking |
| Redis bus | 20 files | Agent‑to‑agent messaging |
| Slippage / commission model | `transaction_cost_model.py` | Exists but inconsistently applied across scanners |
| Paper trading | `asterdex_paper/paper_trader.py`, `*_paper*` | Multiple paper harnesses, not unified |

## 5. What has NOT been tried (genuine gaps)

1. **Seeded, runnable LSTM/Transformer** — mentioned in research docs only; no committed, reproducible backtest.
2. **White's Reality Check / deflated Sharpe automation** — discussed in plans; no shipped script that computes them over the full trial registry.
3. **Unified trial registry (total configurations tried)** — the single most important multiple‑testing input is currently *unmeasurable* because trial counts are scattered across 1,307 backtest files.
4. **Shuffle/permutation control harness** — referenced conceptually, not implemented as a standard CI gate. This is why look‑ahead bugs (F2/F29) survived so long.
5. **Regime‑conditional pre‑registration** — regime filters exist, but no strategy is pre‑registered as "trade only in regime X".
6. **Options / volatility‑surface strategies** — theta options code exists (`strategy_2_theta_options.py`) but no clean OOS test.
7. **Cross‑sectional (relative) crypto signals** — existing crypto work is directional; cross‑sectional momentum/carry is a real gap.
