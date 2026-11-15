# Verbatim Catalogue of Statistical, Risk-Management, Mathematical & ML Methods Already Used (Phase 2)

**Package:** `WIRED_IN/2026-11-15_0725_inspect-wt/harvested_ideas/02_methods_catalogue.md`  
**Purpose:** Exhaustive inventory of every statistical test, mathematical optimization, risk-management control, and machine-learning model already implemented or attempted in the repository—so Phase 3 experiments never reinvent existing code without citing it or explicitly addressing a missing validation gap.

---

## 1. Layer A Regex Scan Summary (`layer_a_stats.json`)

Across **11,821** scanned code/research files (from **44,800** tracked files on `origin/main` in `.fix-wt`), static pattern matching recorded:

| Category | Matched Files | Top Observed Keyword Hits (File Counts) |
|---|---:|---|
| **RISK** | 6,848 | `sharpe` (2,955), `sl` (2,943), `tp` (2,934), `volatility` (2,180), `atr` (2,168), `stop_loss` (1,875), `take_profit` (1,845), `max drawdown` (944), `position sizing` (864), `var` (859), `leverage` (705), `kelly` (700), `sortino` (289), `calmar` (221) |
| **EXECUTION** | 5,416 | `live` (3,688), `spread` (1,209), `execution` (1,154), `funding` (1,047), `slippage` (905), `simulate` (316), `commission` (264), `paper trade` (169) |
| **BACKTESTING** | 2,988 | `backtest` (2,911), plus `walk_forward`, `cross_validation`, `out_of_sample`, `vectorbt`, `grid_search` |
| **DATA** | 2,926 | `binance` (1,436), `yfinance` (1,332), `ohlcv` (852), `polygon` (140), `resample` (107), `ccxt` (88) |
| **ML_MODELS** | 997 | `xgboost` (267), `hmm` (257), `lightgbm` (200), `clustering` (196), `bayesian` (188), `lstm` (121), `neural` (101), `random forest`, `transformer`, `kalman`, `pca`, `svm` |

---

## 2. Dependency Manifest Triage (`dependencies_summary.json`)

**30** dependency manifests parsed (`120` unique packages). Key architectural finding: validation and portfolio-allocation libraries are explicitly split out into optional manifests (`requirements-validation.txt`, `requirements-hedge-fund.txt`) and omitted from lean production runtime paths.

| Manifest Path | Core Libraries Declared | Role & Production Status |
|---|---|---|
| `requirements.txt` | `pandas==2.1.4`, `numpy==1.26.2`, `scikit-learn>=1.3.0`, `scipy>=1.10.0`, `arch>=7.0.0`, `fredapi`, `pandas-datareader`, `yfinance>=0.2.50`, `pymysql`, `redis` | Production runtime (`yfinance` had been undeclared until fix, causing ETF/Bond 0-pick failures) |
| `requirements-validation.txt` | `arch>=6.0`, `timeseriescv>=0.1.4` | Opt-in anti-overfitting sidecar (NOT in live emit gate by default) |
| `requirements-hedge-fund.txt` | `quantstats>=0.0.81`, `PyPortfolioOpt>=1.6.0` | Opt-in HTML tearsheets + HRP/EfficientFrontier (`tools/pypfopt_allocator.py`, `tools/quantstats_tearsheets.py`) |
| `requirements-worldclass.txt` | `torch>=2.0.0`, `xgboost>=1.7.0`, `lightgbm>=4.0.0`, `catboost>=1.2.0`, `shap>=0.41.0`, `featuretools>=1.28.0`, `fastapi` | ML crypto research stack |
| `alpha_engine/validation/requirements-bayes.txt` | `pymc`, `arviz`, `mysql-connector-python` | Dockerized Bayesian hierarchical Sharpe shrinkage (`alpha_engine/validation/hierarchical_sharpe.py`) |
| `ml_battleground/requirements.txt` | `torch`, `scikit-learn`, `lightgbm`, `numpy`, `pandas` | 5-system crypto arena (GRU-Attention, RF, regime, carry, momentum) |
| `genome/requirements.txt` | `numpy`, `pandas`, `scipy` | Genetic/evolutionary strategy mutation lab |

---

## 3. Verbatim Catalogue of Implemented Methods (With File Citations)

### A. Statistical Validation & Multiple-Testing Gates
| Method / Formula | Exact Implementation File & Symbol(s) | Notes / Production Wiring |
|---|---|---|
| **Deflated Sharpe Ratio (DSR)** — Bailey & López de Prado (2014) | `alpha_engine/deflated_sharpe.py` (`returns_stats`, `filter_edge_strategies`), `alpha_engine/anti_overfit_validator.py::deflated_sharpe()`, `alpha_engine/money_ready_verdict.py` | Adjusts Sharpe for trial count $N$, skewness $\gamma_3$, excess kurtosis $\gamma_4$. Opt-in in `quality_gates.py:81` (`ANTI_OVERFIT_VALIDATOR_ENABLED=0`) |
| **Combinatorial Purged Cross-Validation (CPCV) & Probability of Backtest Overfitting (PBO)** | `alpha_engine/anti_overfit_validator.py::cpcv_pbo()`, `alpha_engine/validation/purged_cv.py::PurgedKFoldCV` | Wraps `timeseriescv.CombPurgedKFoldCV`; purges & embargoes boundaries. Opt-in sidecar |
| **White's Reality Check & Hansen's SPA Test** | `alpha_engine/anti_overfit_validator.py::reality_check_pvalue()`, `alpha_engine/money_ready_verdict.py` | Uses `arch.bootstrap.SPA` and `StationaryBootstrap` (`B=1000, block_size=10`) |
| **Moving Block & Stationary Bootstrap CIs** | `tools/block_bootstrap_ci.py` (`MovingBlockBootstrap`, `StationaryBootstrap`, `N_RESAMPLES=10_000`) | 95% CIs on PF, Sharpe, WR; block size $\lceil n^{1/3} \rceil$; group-by-strategy blocking |
| **Wilson Score Lower Bound, Exact Binomial, Bonferroni Correction** | `TESTING_PROTOCOL.MD` §0.1 (`docs/PAPER_PILOT_HARNESS.md`), `alpha_engine/validation/statistical_gates.py` | $p < 0.05/k$ ($k=7 \implies \alpha=0.00714$), Wilson 95% LB > breakeven WR |
| **Bayesian Hierarchical Normal-Means Shrinkage** | `alpha_engine/validation/hierarchical_sharpe.py` (PyMC + ArviZ) | $\mu_i \sim \mathcal{N}(\mu_{\text{global}}, \tau_{\text{global}})$ across assets within strategy family |
| **Rolling Walk-Forward Validation & Concept Drift Detector** | `alpha_engine/walkforward_validator.py::walk_forward_validate()`, `tools/walk_forward_per_strategy.py` (`--require-macro-join`, `total_pf >= 1.0`), `alpha_engine/validation/walk_forward.py` | Rolling `train_size=20, test_size=10, step=5` on trades; `hf_stats.concept_drift` ($D > 0.10$ pause trigger) |
| **Monte Carlo Simulation & Stress Testing** | `alpha_engine/validation/monte_carlo.py`, `alpha_engine/validation/stress_test.py` | Trade-order reshuffling & stress regimes |

### B. Risk Management, Sizing & Portfolio Allocation
| Method / Formula | Exact Implementation File & Symbol(s) | Notes / Production Wiring |
|---|---|---|
| **Risk-Based & Fractional Kelly Position Sizing** | `alpha_engine/config.py:67-85` (`MAX_RISK_PER_TRADE=0.02`, `KELLY_CAP=0.05`), `ml_battleground/ensemble_coordinator.py` (`KELLY_CAP=0.25`), `.claude/skills/money-maker-readyv2/SKILL.md:24` (`compute_position_size()`) | Size = `risk_amount / stop_distance` capped at `15%` per pick, `80%` total exposure, `40%` correlated class cap |
| **Hierarchical Risk Parity (HRP) — López de Prado (2016)** | `tools/hrp_allocator.py`, `tools/pypfopt_allocator.py` (`PyPortfolioOpt`) | Single-linkage clustering on $d_{ij} = \sqrt{0.5(1 - \rho_{ij})}$, quasi-diagonalization, recursive inverse-variance bisection |
| **Inverse-Volatility & Volatility Targeting** | `final_v4/inspect-wt/03_risk_management/backtest_rotation.py` (`v1`, `v2` 12% target), `ml_crypto_predictor/researchers/vol_targeting_researcher.py`, `risk_parity_researcher.py` | 12m trailing realized vol scaling (`min(1.0, 0.12 / realized_vol)`), 50% max single-asset weight |
| **Regime-Aware Directional Exposure Limits** | `alpha_engine/regime_position_sizer.py` (`REGIME_LIMITS`: `TRENDING_UP (6L,2S)`, `TRENDING_DOWN (2L,6S)`, `CHOPPY (3L,3S)`, `VOLATILE (2L,2S)`), `alpha_engine/regime_flip_detector.py` | Detects BTC 4H regime via Binance/CoinGecko/KuCoin failover |
| **Drawdown & CVaR-95% Portfolio Gates** | `alpha_engine/money_ready_verdict.py:99-110` (`MDD_GATE_THRESHOLD=0.20`, `COMMODITY=0.55`, `CVAR_GATE_THRESHOLD_PCT=10.0`) | Hard-downgrades `MONEY_READY -> NOT_READY` when rolling MDD or CVaR-95 fails |
| **Per-Class 3× Cost Gate & Gap-Aware Stop Fill Model** | `tools/per_class_cost_gate.py` (`REQUIRED_COST_MULTIPLE=3.0`, `MIN_SAMPLE=30`), `tools/stop_fill_replay.py` (`audit_trail/stop_fill.py::find_stop_fill`) | Blocks emission when mean PnL < $3\times$ round-trip cost (`tools/data/transaction_costs.json`); replays 1h intrabar open gaps |
| **Pine Script ATR/Kelly/Trailing Risk Controls** | `kimi_claw_pro.pine` (`base_atr_mult=2.0`, `trailing_activation=1.0R`, `use_kelly_sizing`, `max_position_pct=2.0`) | Client-side TradingView indicator (`63/64` plot slots) |

### C. Machine Learning, Neural Networks & Optimization Algorithms
| Method / Model | Exact Implementation File & Symbol(s) | Notes / Where Tried |
|---|---|---|
| **Tree Ensembles (Random Forest, XGBoost, LightGBM, CatBoost)** | `alpha_engine/config.py:59` (`rf_model.pkl`), `tools/hyro_ml_pick_optimizer.py` (XGBoost/RF `P(WIN)` + drift <45% retrain), `ml_gatekeeper/per_class_trainer.py::predict_quality()`, `ml_battleground/retrain_on_live.py`, `ml_crypto_predictor/train_base_models.py` | Used for binary win/loss filtering and feature ranking (`alpha_engine/features/*`: momentum, flow, options, sentiment, seasonality, valuation) |
| **Deep Sequence & Graph Neural Models (GRU-Attention, LSTM, Transformer, Informer, GNN)** | `ml_battleground/ensemble_coordinator.py` (System C GRU-Attention), `ml_crypto_predictor/enhanced_models/world_class_transformer_v2.py`, `ml_crypto_predictor/models/informer_lite.py`, `ml_crypto_predictor/models/gnn_onchain.py` | Tested primarily on hourly/daily crypto OHLCV + on-chain features |
| **Hidden Markov Models (HMM), Kalman Filters, PCA, Clustering** | `ml_crypto_predictor/researchers/hmm_regime_researcher.py`, `KIMI_STRATS*.MD`, `incubator/agents/*` (`crypto_cointegration_pairs_v1.py`, `crypto_betting_against_beta_v1.py`) | Regime classification, pairs cointegration, K-means/hierarchical clustering (`hmmlearn` in 3 manifests) |
| **Meta-Labeling (López de Prado)** | `ml_crypto_predictor/enhanced_models/meta_labeler.py`, `alpha_engine/ensemble/meta_learner.py` | Secondary classifier predicting whether primary signal hits TP before SL |
| **Tree-Parzen Estimator (TPE) Bayesian Optimizer & Genetic Evolution** | `genome/bayesian_optimizer.py::BayesianOptimizer` (`_sample_tpe`), `genome/dna_engine*.py`, `genome/contrarian_evolver.py`, `genome/audit_ensemble_evolver.py` | Hyperparameter search (`sharpe`, `win_rate`, `profit_factor`) and 6-stage mutation/crossover/inverse evolution |
| **TradingView Mathematical Microstructure & Signal Stack** | `kimi_claw_pro.pine` (KAMA, HMA, Connors RSI-2, Swing Failure Pattern, Z-Score MR `p=0.015`, CVD divergence, TTM Squeeze, BTC/ETH cointegration, Kyle's Lambda, Hurst regime switching) | Multi-factor indicator in Pine v6 |

### D. Genuine Methodological Gaps Remaining (What Was NOT Yet Done Properly)
1. **No Unified, Pre-Registered 10-Step Proof Execution Across All 8 Asset Classes** with **Permuted/Shuffled Price Controls**, **Circular Block Bootstrap on Trade/Monthly Sequences**, **Breakeven Cost Margin + Canadian Tax Treatment (TFSA/RRSP vs. Non-Registered Capital Gains/Ordinary Income)**, and **Regime-Split Expectancy (Bull/Bear/Sideways × High/Low Vol)** run under a single seeded script (`SEED=42`).
2. **Meta-Selection & Uncorrelated Sleeve Combination Tested Under Cascaded DSR:** Prior runs tested single-strategy cells (`V1`) or isolated allocations (`v1-v4`), leaving untested a formal **multi-asset risk-parity combination** pooling weakly correlated sleeves ($\rho < 0.3$) with **cascaded DSR** across both $N_{\text{new}}$ and $N_{\text{repo}} = 646$.
3. **Crypto Funding-Rate Carry + Intraday Trend Evaluated Against Honest Archive Data:** `data/funding_rate_archive/{BTC,ETH,SOL,BNB,XRP}USDT.jsonl` and `data/cache/BTCUSDT_3mo_1h.csv` sit unused by a unified 10-step proof harness with explicit maker/taker + funding friction.
4. **Actionable Negative-Result Governance & Passive Benchmark Pivot:** Live `/audit` mixes unverified active picks (`0/9` classes ready) with no unified multi-horizon tracker tying every prediction back to a pre-registered proof verdict.

