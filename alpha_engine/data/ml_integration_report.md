# Mercury/Inception ML Algorithm Integration Assessment
## Alpha Engine — March 18, 2026

### Current System Baseline
- **Model:** XGBoost primary + LightGBM secondary + RF fallback (stacked ensemble)
- **Features:** 41 engineered features (Phase 8: OBI velocity, funding, microstructure)
- **Training data:** 365 live closed picks + ~1,408 augmented (backtest bridge)
- **Current AUC:** 0.70 (CV), validation varies
- **Inference constraint:** <2 min in GitHub Actions, CPU-only, no GPU
- **Existing advanced components:** HMM regime detection (3-state), isotonic calibration, champion/challenger, incremental training, feature drift detection
- **Dependencies available:** scikit-learn, xgboost, lightgbm, numpy, pandas, scipy, shap, hmmlearn
- **NOT available:** PyTorch, TensorFlow, darts, pytorch-forecasting (not in requirements.txt)

---

## Algorithm-by-Algorithm Assessment

### 1. LSTM/GRU Recurrent Networks
**Can we use it NOW?** NO — requires PyTorch or TensorFlow (not installed).
**Data needed:** Sequential OHLCV windows (30-60 bars per sample). We have OHLCV via Binance API.
**Implementation time:** 2-3 weeks (install PyTorch, build train pipeline, handle sequence creation)
**Expected AUC improvement:** +0.02-0.05 over XGBoost IF enough data. Research (researcher_002) found GRU-Attention scored 0% WR with only ~2,500 samples. Our 365 live picks is FAR below the ~50,000 minimum for deep learning.
**GitHub Actions feasibility:** Marginal. PyTorch CPU inference is 5-20x slower than XGBoost. Training would need offline/pre-trained model.
**Verdict: NOT RECOMMENDED NOW.** Fatal data limitation (365 samples vs 50K+ needed). The existing research (researcher_002_lstm_attention.md) already documented why System C's GRU-Attention got 0% WR — insufficient data, attention on single token, sequence too long. Same problems would apply here.

### 2. Temporal Convolutional Networks (TCN)
**Can we use it NOW?** NO — requires PyTorch (tsai or pytorch-tcn library).
**Data needed:** Same as LSTM — sequential OHLCV windows.
**Implementation time:** 1-2 weeks (simpler than LSTM, fewer hyperparameters)
**Expected AUC improvement:** +0.01-0.03. TCN is computationally faster than LSTM but has same data hunger problem.
**GitHub Actions feasibility:** Better than LSTM (no recurrent state = parallelizable), but still needs PyTorch.
**Verdict: NOT RECOMMENDED NOW.** Same data bottleneck as LSTM. TCN needs 10K+ sequences minimum. Could revisit when we have 2,000+ closed picks.

### 3. Transformer-Based Models (Informer, TFT)
**Can we use it NOW?** NO — requires pytorch-forecasting or tslib (not installed).
**Data needed:** Multi-horizon time series (OHLCV + covariates). TFT needs static covariates (coin category) + known future inputs (time features) + observed inputs (price/volume).
**Implementation time:** 3-4 weeks. TFT is the most promising transformer for our use case, but setup is complex.
**Expected AUC improvement:** +0.03-0.08 IF enough data. Research (researcher_013) shows TFT outperforms LSTM/GRU on crypto with >100K samples.
**GitHub Actions feasibility:** POOR. TFT inference takes 10-30 seconds per batch on CPU. Training impossible in Actions.
**Verdict: NOT RECOMMENDED NOW.** Data and compute constraints both fatal. Revisit when: (a) 5,000+ closed picks, (b) separate GPU training pipeline.

### 4. Graph Neural Networks (GNN) on Correlation Graphs
**Can we use it NOW?** PARTIALLY — lightweight GNN possible with scikit-learn + networkx (both available or easy to add).
**Data needed:** 30-symbol correlation matrix (WE HAVE THIS — OHLCV for 30 symbols already fetched). Cross-asset return correlations, rolling windows.
**Implementation time:** 1 week for a simple spectral clustering / graph-based feature approach. Full GNN (PyTorch Geometric) would take 3-4 weeks.
**Expected AUC improvement:** +0.01-0.03 as features; +0.03-0.05 with full GNN.
**GitHub Actions feasibility:** Graph features from correlation matrix = <5 seconds. Full GNN inference = needs PyTorch.
**Verdict: PARTIAL RECOMMENDATION.** We can extract graph-based features from correlation matrices NOW without any new dependencies:
- Eigenvector centrality of each symbol in the correlation graph
- Cluster membership (spectral clustering)
- Rolling correlation regime change signals
- Network density as a systemic risk indicator
These are just new FEATURES for our existing XGBoost, not a new model. ~3-5 days to implement.

### 5. Ensemble/Stacking Models
**Can we use it NOW?** YES — WE ALREADY HAVE THIS. Our ml_ranker.py uses XGBoost + secondary RF stacking with LogisticRegression meta-learner candidate.
**Data needed:** Already have it.
**Implementation time:** 0 — already implemented. Improvement opportunities: 1-3 days.
**Expected AUC improvement:** +0.02-0.04 from better ensemble diversity.
**GitHub Actions feasibility:** Already running fine.
**Verdict: HIGHEST PRIORITY IMPROVEMENT.** Our current stacking is basic. Concrete improvements:
1. **Add CatBoost** as a third base learner (pip install catboost, CPU-friendly, handles categoricals natively) — different gradient boosting algorithm = more diversity.
2. **Logistic Regression meta-learner** using out-of-fold predictions from all base models (proper stacking, not just blending).
3. **Dynamic weighting** based on rolling 30-trade performance per base model (regime-aware stacking).
4. **Negative correlation learning** — optimize ensemble to minimize prediction correlation between base learners.
Estimated AUC: 0.70 -> 0.73-0.75 with proper stacking + CatBoost diversity.

### 6. Reinforcement Learning (PPO, SAC)
**Can we use it NOW?** NO — requires stable-baselines3 + gym (not installed). Also needs simulation environment.
**Data needed:** OHLCV for environment simulation. Need to build custom Gym environment with realistic slippage/fees.
**Implementation time:** 3-5 weeks for PPO agent + environment + training.
**Expected AUC improvement:** N/A (RL produces actions, not probabilities). Could improve PORTFOLIO performance but not individual signal ranking.
**GitHub Actions feasibility:** TERRIBLE. RL training needs millions of steps. Inference could work (pre-trained policy forward pass is fast), but training is impossible in 2 min.
**Verdict: NOT RECOMMENDED NOW.** Research (researcher_012) is blunt: "In live trading, rarely and consistently [profitable]." RL excels at portfolio allocation (position sizing), not signal classification. Our existing regime allocator + Kelly criterion already handles this. The finrl-crypto repo (2.2K stars) is impressive but its PPO agent needs >1M training steps and a GPU. It could NOT work in our GitHub Actions pipeline. Revisit only for offline portfolio optimization.

### 7. Probabilistic/Bayesian Models (Gaussian Processes)
**Can we use it NOW?** YES — sklearn.gaussian_process is available out of the box.
**Data needed:** Same 41 features we already have. GP works on ANY feature matrix.
**Implementation time:** 3-5 days.
**Expected AUC improvement:** +0.01-0.03 as a stacking member; main value is UNCERTAINTY QUANTIFICATION.
**GitHub Actions feasibility:** POOR for >500 samples. GP scales O(n^3) — with 365 picks OK (~0.5s), with 1,770 augmented BAD (~60s). Sparse GP (sklearn) helps.
**Verdict: RECOMMENDED AS CALIBRATOR, NOT PRIMARY MODEL.** GP's real value is producing well-calibrated prediction intervals. Use it to REPLACE our isotonic regression calibrator with a GP that outputs (mean_prediction, uncertainty_band). High-uncertainty predictions get filtered more aggressively. Implementation:
- Use `GaussianProcessClassifier` with RBF kernel on the TOP 10 features (dimensionality reduction)
- Train on recent 200 picks only (computational tractability)
- Output: calibrated probability + uncertainty width
- Estimated time: 3 days. Estimated improvement: +0.01-0.02 AUC but significantly better calibration (reducing false positives in the 0.50-0.60 ML score range where we have 69% WR vs 32% in the 0.60-0.70 range — the non-monotonicity problem).

### 8. Hybrid Classical-ML + Deep Learning
**Can we use it NOW?** PARTIALLY — the "classical ML" part YES.
**Data needed:** Current features + time-series features.
**Implementation time:** Depends on which DL component. Feature extraction from pre-trained models = 1-2 weeks.
**Expected AUC improvement:** +0.03-0.05 if deep features are informative.
**GitHub Actions feasibility:** If DL is pre-computed offline, hybrid inference is fast.
**Verdict: FUTURE PHASE.** The right approach is: (1) build a solid classical ML ensemble first (stacking), (2) later add DL features as inputs to that ensemble. Our current architecture already supports this pattern via the feature injection mechanism (Phase 7-8).

---

## RANKED RECOMMENDATIONS (Implement Next)

### Priority 1: Enhanced Stacking Ensemble (1 week, AUC +0.03-0.05)
**What:** Add CatBoost as third base learner + proper out-of-fold stacking meta-learner.
**Why:** Highest ROI. Zero new infrastructure. Our current stacking is basic (XGB + secondary RF). CatBoost handles categoricals natively (strategy_encoded, category_encoded) which XGBoost/LightGBM one-hot encode less efficiently. Research (researcher_004) confirms: "Three uncorrelated models beat twenty correlated ones."
**Libraries:** `catboost` (pip install catboost, CPU-optimized, 10-50x faster than sklearn RF)
**Implementation:**
1. Add CatBoost classifier as third base learner in ml_ranker.py train()
2. Use 5-fold TimeSeriesSplit to generate out-of-fold predictions from XGB + LGB + CatBoost
3. Train LogisticRegression meta-learner on stacked OOF predictions
4. Inference: run all 3 base models + meta-learner (total ~0.3s on CPU)
**Expected result:** AUC 0.70 -> 0.73-0.75. CatBoost typically adds 1-2% AUC as a diverse ensemble member.
**Replaces or supplements:** SUPPLEMENTS current XGBoost. XGBoost remains primary, CatBoost + LGB provide diversity.

### Priority 2: Graph-Based Correlation Features (3-5 days, AUC +0.01-0.03)
**What:** Extract features from the 30-symbol rolling correlation matrix and feed them into the existing XGBoost.
**Why:** Captures cross-asset regime information that no single-asset feature can. When BTC/ETH correlation breaks down, it signals regime change. When a small-cap becomes highly correlated with BTC, it signals momentum contagion.
**Libraries:** `networkx` (pip install networkx, pure Python, no GPU) + existing numpy/scipy
**Implementation:**
1. Build 30x30 rolling correlation matrix from 30-day OHLCV returns
2. Extract per-symbol: eigenvector_centrality, clustering_coefficient, betweenness_centrality
3. Extract global: network_density, largest_eigenvalue (Marchenko-Pastur ratio for RMT), number_of_communities
4. Add 6-8 new features to MLSignalRanker.FEATURES list
5. Inject via scanner's existing feature injection pattern
**Expected result:** AUC +0.01-0.03. Small but meaningful, and these features are highly UNCORRELATED with existing features (which are all single-asset).
**Supplements:** New features for existing model, no model change needed.

### Priority 3: Gaussian Process Uncertainty Calibrator (3 days, better calibration)
**What:** Replace isotonic regression calibrator with GP-based uncertainty-aware calibrator.
**Why:** Our biggest problem is non-monotonic ML scores (0.50-0.60 range has 69% WR but 0.60-0.70 has only 32% WR). Isotonic regression fixes monotonicity but doesn't tell us WHERE the model is uncertain. GP provides (prediction, uncertainty) — we can filter high-uncertainty predictions more aggressively.
**Libraries:** `sklearn.gaussian_process` (already installed)
**Implementation:**
1. Replace `IsotonicRegression` calibrator with `GaussianProcessClassifier(kernel=RBF())`
2. Train on validation set (same as current isotonic calibrator)
3. At prediction time: get (probability, std_dev) from GP
4. If std_dev > 0.25: apply additional penalty to ML score (uncertain = conservative)
5. Use sparse approximation (n_restarts_optimizer=2, max_iter_predict=50) for speed
**Expected result:** Better calibration. AUC may not change much, but precision@20 should improve from ~0.40 to ~0.48+ by filtering uncertain predictions.
**Replaces:** Isotonic regression calibrator in ml_ranker.py (lines 660-662).

---

## Specific Question Answers

### Can finrl-crypto's PPO agent work for our use case?
**NO.** Three blockers:
1. **Training compute:** finrl-crypto's PPO needs 100K-1M environment steps (hours of GPU time). Cannot run in GitHub Actions.
2. **Task mismatch:** PPO learns BUY/HOLD/SELL actions for portfolio management. We need WIN PROBABILITY for signal ranking. Different problem entirely.
3. **Data format:** finrl-crypto expects continuous OHLCV time series in a Gym environment. Our data is discrete trade signals with features. Would need a complete rewrite.
**Alternative:** Use PPO OFFLINE to learn optimal position sizing, then export the learned sizing policy as a lookup table (regime x confidence -> position_size). This could supplement Kelly criterion. Estimated effort: 2-3 weeks (build Gym env + train + extract policy).

### Can we run a lightweight GNN on our 30-symbol correlation matrix?
**YES, but not a real GNN — use graph features instead.** A true GNN (PyTorch Geometric) needs PyTorch and is overkill for 30 nodes. Instead:
- Build a `networkx.Graph` from the correlation matrix (edge if |corr| > 0.5)
- Compute centrality metrics per node (symbol)
- Use spectral clustering to identify asset communities
- Feed these as features to XGBoost
This runs in <1 second for 30 nodes. A full GNN would add ~10s (CPU) for minimal benefit on such a small graph.

### Is TCN worth trying as an alternative to our current approach?
**NOT NOW.** TCN's advantage is capturing long-range temporal dependencies in sequences. Our current input is a FEATURE VECTOR per trade signal (41 features), not a TIME SERIES. TCN needs sequential input (e.g., 60 bars of OHLCV). To use TCN, we'd need to:
1. Install PyTorch
2. Restructure the data pipeline from features-per-signal to sequences-per-signal
3. Have 10K+ sequence samples (we have 365)
TCN makes sense when we move to a time-series prediction model (predicting price direction from OHLCV sequences), not for our current signal ranking task.

---

## Data Gap Analysis

| Data Source | Have It? | Used By | Gap |
|---|---|---|---|
| OHLCV (1d, 4h, 1h) | YES (Binance API) | XGBoost features, HMM | None |
| Order book depth | PARTIAL (OBI injected) | Phase 7-8 features | Missing: full L2 snapshots |
| Funding rates | YES (Binance fapi) | Phase 6 features | None |
| On-chain (MVRV, NVT) | PARTIAL (proxy) | onchain_strategies.py | Missing: real Glassnode/CryptoQuant data |
| Cross-asset correlations | YES (can compute) | NOT USED YET | Gap: not extracted as features |
| Social sentiment | PARTIAL (Fear & Greed) | fear_greed_norm feature | Missing: LunarCrush Galaxy Score per coin |
| Liquidation cascades | PARTIAL (estimated) | liquidation_cascade strategy | Missing: real-time liquidation feed |
| Options/IV data | NO (proxy only) | options_features.py | Missing: Deribit options data |

---

## Implementation Roadmap

| Week | Task | Expected AUC |
|---|---|---|
| Week 1 | Enhanced stacking (CatBoost + OOF meta-learner) | 0.73-0.75 |
| Week 2 | Graph correlation features (networkx) | 0.74-0.76 |
| Week 2 | GP uncertainty calibrator | 0.74-0.76 + better calibration |
| Week 3-4 | (OPTIONAL) Offline TFT/LSTM experimentation | Research only |
| Month 2+ | (FUTURE) PyTorch integration, TCN, full GNN | Requires >2K picks |

**Total estimated improvement:** AUC 0.70 -> 0.74-0.76 within 2 weeks, using only CPU-compatible libraries that work in GitHub Actions.
