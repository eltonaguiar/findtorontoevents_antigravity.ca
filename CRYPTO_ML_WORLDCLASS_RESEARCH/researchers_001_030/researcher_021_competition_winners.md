# Researcher Profile: Dr. Lucas Dubois

## Persona
- **Title:** Kaggle Grandmaster and Competition Specialist
- **Expertise:** Winning solutions, ensemble stacking, feature engineering tricks
- **Years Experience:** 9
- **Background:** Kaggle Grandmaster (top 0.1%), former data scientist at H2O.ai, now analyzes competition strategies for crypto.

## Research Scope
**Primary Question:** What techniques do Kaggle competition winners use for crypto price prediction and how can they be adapted for production?

**Target Systems/Areas:**
- `crypto_ml_edge/` (LightGBM pipeline with walk-forward validation)
- `ml_battleground/` (multi-system architecture: Systems A/B/C + pilots)
- `alpha_engine/ensemble/` (meta-learner + signal combiner)
- `scripts/ensemble_stacker.py`, `scripts/xgboost_stacker.py` (stacking systems)
- `scripts/meta_labeler.py` (Lopez de Prado meta-labeling)
- `claude_gainer_ml/train_model.py` (RF + XGBoost with calibration)
- `ml_crypto_predictor/production_engine.py` (production ensemble)

## Methodology
1. **Sources:** Full codebase grep for ensemble/stacking, LightGBM/XGBoost configs, validation strategies, calibration, feature engineering.
2. **Extraction:** Mapped actual class hierarchies, hyperparameter configurations, feature counts, and validation protocols across all ML subsystems.
3. **Analysis:** Compared implementations against competition-winning patterns (G-Research Crypto 2021, Numerai, Binance AI).
4. **Validation:** Assessed whether implementations enforce hard gates or merely log metrics.

---

## Key Findings (REAL CODEBASE AUDIT)

### Finding 1: Ensemble/Stacking Architecture — PARTIALLY IMPLEMENTED

**What exists:**

| System | File | Models | Method |
|--------|------|--------|--------|
| EnsembleStacker | `scripts/ensemble_stacker.py` | RF + GBM + Ridge + LR | 2-level stacking with meta-features (mean, std, min, max, range of base predictions) |
| XGBoost Stacker | `scripts/xgboost_stacker.py` | XGBClassifier (n_est=200, lr=0.02, depth=4) | Single-model stacker over multi-algo signal features |
| Alpha Engine Meta-Learner | `alpha_engine/ensemble/meta_learner.py` | Regime-aware weighted combiner | Performance-weighted, rank-average, or equal-weight signal combination |
| Signal Combiner | `alpha_engine/ensemble/signal_combiner.py` | N/A (rule-based) | 3 modes: equal_weight, performance_weighted, rank_average |
| PerformanceWeightedBlender | `scripts/ensemble_stacker.py` | N/A | Inverse-MSE weighted blending |

**Strengths:**
- `EnsembleStacker` implements proper 2-level stacking: base models predict on validation, meta-model (LinearRegression) trains on those predictions + statistical meta-features
- `SignalCombiner` has rank-average mode -- robust to outlier scores (matches competition best practice)
- `MetaLearner` integrates regime allocation, signal combination, and alternative data multipliers (insider, sentiment, earnings) into a single arbitrator

**Gaps vs. Competition Winners:**
- NO LightGBM + LSTM heterogeneous stacking found anywhere as a single ensemble (System C GRU and crypto_ml_edge LightGBM exist separately but are never combined)
- `EnsembleStacker` uses `train_test_split` with random split (line 55) -- not time-series aware, which is a data leakage risk for financial data
- Meta-model is LinearRegression -- competition winners typically use Ridge or a shallow GBM to avoid negative coefficients
- No diversity-weighted ensemble (the method is mentioned in `SignalCombiner` docstring but only `compute_strategy_diversity` correlation matrix exists, never used in combination logic)
- Stacking is "method 4" listed in `SignalCombiner` docstring but never implemented in the combine() dispatch

### Finding 2: Feature Engineering — SOLID BUT NOT EXTREME

**crypto_ml_edge Feature Engine** (`crypto_ml_edge/features/engine.py`):
- **16 features** across 5 categories: Momentum (4), Funding Rate (3), Volume (2), Volatility (2), S/R (2), Oscillators (3)
- All features are stationary: returns, ratios, z-scores, percentiles, bounded oscillators
- Zero-lookahead guarantees enforced via explicit `.shift(1)` and causal rolling windows
- `WARMUP_BARS = 200` properly documented
- **Design philosophy explicitly limits to 10-20 features** per config.py comment: "Everything else is overfitting waiting to happen"

**ml_battleground System A Filter** (`ml_battleground/system_a_filter/ml_filter.py`):
- **36 features**: 26 numeric + 11 strategy one-hot flags
- Includes interaction features implicitly (S/R distances, BTC correlation, hour encoding)
- Hurst exponent included (useful for regime detection -- competition pattern)

**ml_battleground TA Ensemble** (`ml_battleground/pilots/ta_ensemble.py`):
- **22 features**: Returns(5), RSI variants(3), MACD(2), Bollinger(2), Volume(2), Volatility(2), Trend(2), ADX(1), Mean-reversion(1), OBV(1)
- Multi-pair training: 10 pairs concatenated for cross-asset learning

**ml_battleground Regime Classifier** (`ml_battleground/system_b_regime/regime_classifier.py`):
- **20 features** for 4-class regime classification (trending_up, trending_down, range_bound, high_volatility)
- Rule-based fallback with confidence estimation when no trained model exists

**scripts/meta_labeler.py** (Meta-Labeling Features):
- **23 features**: Signal strength, TP/SL ratio, regime indicators (HMM, Hurst, composite), time features (hour, DoW, session), volatility, interaction features (strength*regime, strength*hurst, vol*regime), one-hot asset class

**Assessment:** Feature counts (16-36) are intentionally conservative vs. competition winners (200-500+). This is a deliberate design choice documented in config.py. The trade-off: less overfitting risk, but potentially missing non-linear feature interactions that competition stacking would capture. All features are hand-crafted with domain knowledge -- no automated feature generation (e.g., tsfresh, featuretools) found.

### Finding 3: Validation Strategy — WORLD-CLASS IMPLEMENTATION

**crypto_ml_edge Validation** (`crypto_ml_edge/validation.py`) -- **The crown jewel of this codebase:**

| Component | Implementation | Quality |
|-----------|---------------|---------|
| Walk-Forward Split | `WalkForwardSplit` class: expanding or rolling window, configurable folds (default 5) | EXCELLENT |
| Purge Gap | `PURGE_GAP_BARS = 20` bars removed between train end and test start | CORRECT |
| Embargo | `EMBARGO_PCT = 0.01` (1%) of test window trailing edge removed | CORRECT |
| Regime Coverage | `verify_regime_coverage()` asserts 2022 bear market appears in at least one test fold | EXCELLENT -- most competition entries lack this |
| Chronology Validation | `Fold.validate_chronology()` eagerly checks for temporal inconsistencies at construction | GOOD |
| DSR Gate | Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio with full math: expected max Sharpe under null, non-normal SE correction, hard gate at P>0.95 | EXCELLENT -- textbook implementation |
| Multiple Testing Cap | `MAX_MODEL_VARIANTS = 10` caps n_trials to prevent inflation | CORRECT |
| Cost-Adjusted Sharpe | `cost_adjusted_sharpe()` deducts Binance fees + per-pair slippage before any validation | CORRECT |
| Combined Gate | `validate_model()` enforces all gates as HARD FAIL: non-positive net Sharpe OR DSR<0.95 = FAIL | EXCELLENT |

**scripts/walk_forward_validator.py** -- Second implementation:
- `PurgedTimeSeriesSplit`: purge_pct=0.02, embargo_pct=0.01
- Monte Carlo simulation (1000 paths) with Sharpe CI
- DSR implementation (independent from crypto_ml_edge)
- Alpha decay analysis per algorithm
- Adversarial validation for leakage detection (in meta_labeler.py)

**alpha_engine/validation/purged_cv.py** -- Third implementation:
- `PurgedKFoldCV`: purge_days=5, embargo_days=5
- IC and Rank IC metrics per fold
- IC Information Ratio (IC_IR) -- key quant metric

**Assessment:** Three independent purged-CV implementations exist. The `crypto_ml_edge/validation.py` implementation is competition-grade with its integrated DSR gate, cost adjustment, regime coverage check, and chronological validation. The hard-gate philosophy (FAIL unless P>0.95) is superior to competition practice where overfitting on leaderboard is rewarded.

### Finding 4: Post-Processing — CALIBRATION EXISTS, CLIPPING ABSENT

**Probability Calibration Found:**
- `claude_gainer_ml/train_model.py`: Isotonic calibration via `CalibratedClassifierCV(method="isotonic", cv=3)` on both RF and XGBoost
- `ml_crypto_predictor/production_engine.py`: Platt scaling (sigmoid) for RF + Isotonic for GBT
- `ml_crypto_predictor/enhanced_models/model_trainer.py`: Isotonic calibration
- `ml_crypto_predictor/enhanced_models/meta_labeler.py`: Isotonic on secondary model
- `ml_crypto_predictor/enhanced_models/world_class_transformer_v2.py`: Learnable Platt scaling parameters (temperature + bias) in PyTorch -- most sophisticated implementation

**Prediction Clipping:**
- `MetaLearner._apply_insider_multiplier()`: Clips scores to `min(score * 1.5, 1.0)` and confidence to `min(conf * 1.3, 0.99)`
- `MetaLearner._apply_sentiment_filter()`: Clips to `min(score * 1.2, 1.0)`
- `ml_filter._heuristic_score()`: `max(0.0, min(1.0, score))` bounding
- **No systematic prediction clipping** (e.g., clip to [5th, 95th] percentile) found in regression output

**Missing:**
- No prediction clipping at distribution tails for continuous outputs
- No Venn-Abers or conformal prediction for uncertainty quantification
- Calibration is only in `claude_gainer_ml` and `ml_crypto_predictor` -- NOT in the newer `crypto_ml_edge` pipeline (which uses raw LightGBM probabilities)

### Finding 5: Target Encoding and Categorical Encoding — MINIMAL

**What exists:**
- `scripts/xgboost_stacker.py`: `pd.get_dummies()` for algo_name and asset_class (one-hot encoding)
- `scripts/meta_labeler.py`: Manual one-hot for HMM regime (bull/sideways/bear) and asset class (CRYPTO/FOREX/STOCK)
- `ml_battleground/system_a_filter/ml_filter.py`: Manual strategy one-hot flags (11 binary features)
- `crypto_ml_edge/trainer.py`: LightGBM with `class_weight="balanced"` for label imbalance
- `scripts/meta_labeler.py`: `scale_pos_weight` computed from class ratio for XGBoost

**Missing:**
- **No target encoding** (e.g., encoding coin_id or regime by average target value -- a competition staple)
- **No CatBoost or category_encoders** library usage
- **No frequency encoding, WOE encoding, or leave-one-out encoding**
- **No feature hashing** for high-cardinality categoricals

### Finding 6: Hyperparameter Tuning — OPTUNA + FALLBACK GRID

**crypto_ml_edge/trainer.py** (`EdgeTrainer`):
- **Optuna TPE sampler** with n_trials=20, inner 3-fold TimeSeriesCV
- Search space: n_estimators [100,600], max_depth [3,8], num_leaves [8,64], learning_rate [0.01,0.15] (log), min_child_samples [10,60], subsample [0.6,1.0], colsample_bytree [0.6,1.0], reg_lambda [0.01,10.0] (log)
- **5-candidate fallback grid** when Optuna not installed (conservative to deep+regularized)
- Early stopping: 30 rounds
- LightGBM fixed params: multiclass (3 classes), balanced class weights, verbose=-1

**ml_battleground/pilots/ta_ensemble.py**:
- **Fixed hyperparameters** (no tuning): n_estimators=300, lr=0.05, max_depth=6, num_leaves=31, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0
- Early stopping: 50 rounds via `lgb.early_stopping`

**scripts/xgboost_stacker.py**:
- **Fixed hyperparameters**: n_estimators=200, lr=0.02, max_depth=4

**Assessment:** Only `crypto_ml_edge/trainer.py` has proper HPO. The Optuna implementation is solid (TPE sampler, inner CV, time-series split) but limited to 20 trials (for CI speed). Competition winners typically run 200-500 trials. Other subsystems use fixed params -- acceptable for production stability but not competition-grade.

### Finding 7: Deep Learning Architecture — GRU-ATTENTION (Not LSTM)

**ml_battleground/system_c_deeplearn/model_arch.py**:
- `GRUAttentionModel`: Dual-timeframe GRU (15m + 1h), 2 layers, hidden_size=128, dropout=0.3
- Multi-head self-attention (4 heads) on concatenated hidden states
- 3 output heads: entry probability (sigmoid), TP distance (ReLU+0.5), SL distance (ReLU+0.5)
- Layer norm + residual connection

**ml_crypto_predictor/enhanced_models/world_class_transformer_v2.py**:
- Full Transformer architecture with multi-timeframe fusion
- Learnable Platt scaling for confidence calibration
- Documented as "World-Class" with 8 architectural components

**Gap:** GRU and Transformer exist but are never stacked with LightGBM in a single ensemble. Competition winners typically use tree model + neural model + linear model stacking.

### Finding 8: Meta-Labeling — IMPLEMENTED (Lopez de Prado Pattern)

**scripts/meta_labeler.py**: XGBoost meta-labeler that:
1. Takes primary model signals as input
2. Engineers 23 features including interaction terms
3. Predicts P(signal success) with threshold=0.55
4. Uses purged time-series CV with explicit purge gap
5. Includes adversarial validation for leakage detection

**crypto_ml_edge/labeler.py**: Triple-barrier labeling:
- Correct implementation: TP hit first = +1, SL hit first = -1, timeout = 0
- Cost-based thresholds: minimum gross move must exceed round-trip fees + slippage
- Embargo function properly masks labels near train/test boundaries

This is textbook Lopez de Prado (2018) and matches competition-grade practice.

---

## Competition-Readiness Scorecard

| Dimension | Score | Competition Baseline | Notes |
|-----------|-------|---------------------|-------|
| Ensemble Stacking | 6/10 | 9/10 | Base infrastructure exists (EnsembleStacker, XGBoost stacker, MetaLearner) but no heterogeneous tree+neural stacking |
| Feature Engineering | 7/10 | 8/10 | Hand-crafted, stationary, no-lookahead guaranteed. Intentionally limited (16-36 features) vs competition (200+). Missing: auto-feature generation |
| Validation Strategy | 9/10 | 8/10 | SUPERIOR to most competition entries. Purged walk-forward + DSR hard gate + cost-adjusted Sharpe + regime coverage. Three independent implementations |
| Post-Processing | 5/10 | 8/10 | Isotonic/Platt calibration exists in 3 subsystems but NOT in the main pipeline (crypto_ml_edge). No systematic tail clipping |
| Target Encoding | 2/10 | 7/10 | Only basic one-hot. No target encoding, frequency encoding, or CatBoost |
| Hyperparameter Tuning | 6/10 | 8/10 | Optuna (20 trials) in one pipeline. Fixed params elsewhere. Competition winners run 200+ trials |
| Meta-Labeling | 8/10 | 7/10 | Full Lopez de Prado implementation with adversarial validation |
| Deep Learning | 6/10 | 7/10 | GRU-Attention + Transformer exist but isolated from tree models |
| **Overall** | **6.1/10** | **7.8/10** | Strong foundations, especially validation. Main gap: heterogeneous model stacking |

---

## Actionable Insights (Priority-Ordered)

1. **[HIGH] Implement heterogeneous stacking in crypto_ml_edge:** Stack LightGBM (tree) + GRU (temporal) + Ridge (linear) predictions as features for a meta-model. The individual components already exist -- they just need to be wired together.

2. **[HIGH] Add calibration to crypto_ml_edge pipeline:** The `EdgeTrainer` outputs raw LightGBM probabilities. Add `CalibratedClassifierCV(method="isotonic", cv=3)` after the LightGBM step in `_create_pipeline()`. The pattern already exists in `claude_gainer_ml/train_model.py`.

3. **[MEDIUM] Add target encoding for pair/regime:** Encode `pair` and `regime` categoricals by their historical mean target value using leave-one-out encoding within each training fold. This captures pair-specific alpha patterns that one-hot encoding misses.

4. **[MEDIUM] Increase Optuna trials to 50-100 for overnight runs:** Keep 20 for CI but add a `--full-tune` flag that increases to 100 trials for weekend training runs. The search space is well-defined.

5. **[MEDIUM] Add prediction tail clipping:** After ensemble output, clip predictions to [2nd, 98th] percentile of training-set predictions. This reduces variance from extreme outlier predictions without biasing the center.

6. **[LOW] Add automated feature generation:** Use `tsfresh` or rolling statistics generator to create 200+ candidate features, then apply SHAP pruning (already implemented) to select the top 30-50. The SHAP pruning infrastructure in `EdgeTrainer._prune_features()` is already competition-grade.

7. **[LOW] Fix EnsembleStacker random split:** Replace `train_test_split` in `ensemble_stacker.py` line 55 with `TimeSeriesSplit` to prevent data leakage in the stacking validation.

## References
- Bailey & Lopez de Prado (2014) -- Deflated Sharpe Ratio: implemented in `crypto_ml_edge/validation.py`
- Lopez de Prado (2018) -- Purged CV, Embargo, Triple-Barrier: implemented across 3 modules
- Lundberg & Lee (2017) -- SHAP TreeExplainer: implemented in `crypto_ml_edge/trainer.py`
- Hamilton (1989) -- HMM Regime Switching: implemented in `ml_battleground/pilots/hmm_regime_gate.py`

---
*Researcher ID: 021* | *Status: Complete*
