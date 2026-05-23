# Machine Learning Blueprint -- Updated 2026-03-23

> **Purpose:** Complete technical specification of every ML system, scoring pipeline, gating logic,
> and research technique in the Antigravity trading platform.
>
> **Audience:** Other AI systems (Claude, Grok, Gemini, Mercury) modifying this codebase.
> **Goal:** Beat the market -- generate winning crypto/forex/equity signals that improve over time.

---

## Table of Contents

1. [System Architecture](#section-1-system-architecture)
2. [ML Model Inventory (9 Models)](#section-2-ml-model-inventory)
3. [Research Techniques Implemented (8/10)](#section-3-research-techniques-implemented)
4. [Scoring System](#section-4-scoring-system)
5. [Gating Pipeline (6 Production + 12 JSON + 11 Forward Validator = 29 Gates)](#section-5-gating-pipeline)
6. [New Modules (March 2026)](#section-6-new-modules)
7. [Data Files Reference](#section-7-data-files-reference)
8. [KPI Dashboard](#section-8-kpi-dashboard)
9. [Known Issues and Roadmap](#section-9-known-issues-and-roadmap)
10. [How to Tweak (For Other AIs)](#section-10-how-to-tweak)

---

## Section 1: System Architecture

### Pipeline Flow

```
[200+ Strategies]
    |
    v
scanner.py  --->  raw signals (BUY/SELL per symbol)
    |
    v
production_scanner.py::apply_quality_gates()
    |  6 data-driven quality gates (confidence, ML, forex, SHORT, volume, unvalidated)
    v
ml_ranker.py  --->  ML scoring (XGBoost + RF + CatBoost ensemble, purged CV)
    |                Boruta feature selection (46 -> ~15-20 features)
    |                Meta-label probability gate at 0.55
    v
forward_validator.py  (16 wired modules + 11+ gates)
    |  Applies elite_scorer, Thompson bonus, HMM regime adj, BOCPD, etc.
    |  Also evaluates 12 JSON-driven gates from gates_config.json
    v
elite_scorer.py  --->  composite score (0-183 pts) + grade (S/A/B/C/D/F)
    |  Copy trader confidence deflation applied
    |  ML replacement score (0-18 pts, halved from 35 per Method 4 backtest)
    v
active_picks.json  (published -- consumed by dashboards, Discord, audit)
    |
    v
forward_validator.py::validate_open_picks()
    |  Fetches live prices (yfinance), tracks MFE/MAE, checks TP/SL/trailing/expiry
    v
closed_picks.json  (outcome WON/LOST -- feeds ML retraining)
    |
    v
[Feedback Loop: Thompson update, Online learner update, Bandit TP/SL update,
 SL recalibration, Adaptive Trust Tuner, Missed Opportunity Analyzer]
```

### 16 Wired Modules in forward_validator.py

Each module is imported inside a `try/except` block so failure of any single module does not crash the pipeline.

| # | Module | File Path | What It Does |
|---|--------|-----------|-------------|
| 1 | **VPIN Detector** | `alpha_engine/vpin_detector.py` | Volume-synced Probability of Informed Trading. Blocks picks when VPIN > 0.55 (toxic flow). Routes mean-reversion in noise regimes (VPIN < 0.3). |
| 2 | **Cooldown Gate** | `alpha_engine/enhanced_strategies.py` | Blocks signals from strategies with 2+ consecutive losses on the same symbol. Prevents chasing losers. |
| 3 | **Deflated Sharpe** | `alpha_engine/deflated_sharpe.py` | Bailey & Lopez de Prado (2014) multiple-testing correction. Penalizes elite_score by -15 if strategy Sharpe is not statistically significant (DSR < 0.95). |
| 4 | **Monte Carlo Validator** | `alpha_engine/validation/monte_carlo.py` | 1000 bootstrap simulations + White's Reality Check. Determines if strategy alpha is real or data-snooped. Grades: PROVEN / LIKELY_VALID / INCONCLUSIVE / LIKELY_RANDOM. |
| 5 | **GARCH Volatility** | `alpha_engine/garch_volatility.py` | GARCH(1,1) forecast for conditional volatility. Used for regime-adaptive TP/SL sizing. |
| 6 | **SL Calibrator** | `alpha_engine/sl_calibrator.py` | Groups trades by (asset_class, strategy_type, session). Computes optimal SL from MAE p90 and TP from MFE p75 per group. |
| 7 | **Entry Optimizer** | `alpha_engine/entry_optimizer.py` | Computes entry timing score based on support/resistance proximity, volume profile, and candle pattern. Score 0-100 feeds into signal_quality component. |
| 8 | **Smart Entry** | `alpha_engine/smart_entry.py` | SmartEntryDetector class -- identifies optimal entry zones using order flow analysis. Feeds entry_zone_score into elite scorer. |
| 9 | **Execution Cost** | `alpha_engine/execution_cost.py` | Computes net edge after fees (taker 0.04%, maker 0.02%). net_edge_bps >= 20 earns +2 pts in signal_quality. |
| 10 | **Pattern Predictor** | `alpha_engine/pattern_predictor.py` | Multi-dimensional pattern matching (RSI x regime x vol x direction x category x confidence x ml x timeframe x day). Golden (>=80% WR, 2+ trades) = +5 pts, Danger (<=20%) = -5 pts. |
| 11 | **Thompson Sampler** | `alpha_engine/thompson_sampler.py` | Beta-distribution per strategy. Bayesian allocation -- winners get +10, losers get -10. Decay factor 0.95/week for regime adaptation. |
| 12 | **Online Learner** | `alpha_engine/online_learner.py` | Single-layer perceptron updated after every closed trade. 9 features, learning rate 0.01. |
| 13 | **HMM Regime** | `alpha_engine/hmm_regime.py` | 3-state Hidden Markov Model (BULL/BEAR/CHOP). Adjusts elite_score +/- based on signal-regime compatibility. |
| 14 | **BOCPD** | `alpha_engine/bocpd.py` | Bayesian Online Changepoint Detection. When P(changepoint) is high, penalizes elite_score by -8 as a warning that the current regime may be ending. |
| 15 | **Bandit TP/SL** | `alpha_engine/bandit_tp_sl.py` | Multi-armed bandit for TP/SL selection. Multiple (TP_mult, SL_mult) arms compete; Thompson sampling picks the best. Updates after each trade outcome. |
| 16 | **Meta-Labeler** | `alpha_engine/meta_labeler.py` | Lopez de Prado (2018) meta-labeling. Secondary ML model asks "Should we ACT on this signal?" P(profitable) > 0.7 = +3 pts, < 0.3 = -5 pts. Falls back to heuristic with < 100 picks. |

Additionally these modules are called at **trade close** (feedback loop):
- `thompson_sampler.update_after_trade()` -- updates Beta posteriors
- `online_learner.online_update()` -- gradient step on perceptron
- `bandit_tp_sl.update_bandit()` -- updates arm rewards
- `adaptive_trust_tuner.apply_trust_adjustments()` -- rolling WR-based confidence boosts

---

## Section 2: ML Model Inventory

### Model 1: Alpha Engine ML Ranker (CURRENT FOCUS)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/ml_ranker.py` |
| **Algorithm** | Heterogeneous stacking ensemble: XGBoost (primary) + RandomForest (secondary) + CatBoost (secondary, optional, has_time=True for ordered boosting). LightGBM as alternative primary. RF-only fallback. |
| **Training data** | ~1,118 samples (closed picks + backtest bridge augmented data, 0.3x weight) |
| **AUC/Accuracy** | **AUC = 1.0 PERSISTS** -- known overfitting artifact (see Known Issues). Champion model is INCOMPATIBLE (feature mismatch). |
| **Status** | **BROKEN** -- `model_comparison.json` (2026-03-22): `champion_incompatible`, 296 val samples. Cannot score validation data. |
| **Feature count** | **46 declared features** (see breakdown below). After auto-drop of 80%+ zero features and Boruta selection, typically ~15-20 remain. |
| **Leaky features removed (Phase 11)** | 4 features excluded: `entry_vs_optimal`, `hold_duration_hours`, `mfe_pct`, `mae_pct` -- these leaked future information, caused AUC=1.0. |
| **Regime interactions removed (Phase 12)** | 7 features removed: `rsi_x_regime`, `vol_ratio_x_regime`, `momentum_x_regime`, `bb_x_regime`, `hour_x_regime`, `atr_x_regime`, `direction_x_regime` -- always-zero (multiplied two mostly-zero features). |
| **Phase 12 additions** | 4 features: `close_to_vwap`, `garman_klass_vol`, `fng_gradient`, `risk_reward_raw` |
| **Phase 13 additions** | 7 chi-squared validated technical features: `mom30`, `rsi30`, `macd_hist_norm`, `stoch_k30`, `stoch_d30`, `cci20_norm`, `williams_r` (92.4% XGBoost accuracy in isolation) |
| **Strategy encoding** | Hash-based: `hash(name) % 100 / 100` (deterministic, no label encoding leak) |
| **Cross-validation** | Purged time-series CV with 2% embargo (Lopez de Prado, AFML Ch.7) -- prevents temporal leakage at fold boundaries |
| **Sample weighting** | Triple-barrier asymmetric weights (win=1.0, loss=1.2, expired=0.5) x recency decay (half-life=30) |
| **Feature selection** | Boruta (Kursa & Rudnicki, 2010) -- reduces 46 to ~15-20. Cached in `data/boruta_selected_features.json`. Reruns weekly. |
| **Incremental training** | Warm-start XGBoost (adds 10 trees on new picks). Drift detection: accuracy < 45% on last 50 triggers full retrain. |
| **Meta-label gate** | `META_LABEL_PROBABILITY_GATE = 0.55` (lowered from 0.65 -- ML not yet predictive enough) |
| **Feature health (CRISIS)** | Only **1 truly alive feature** out of 46. 25+ features are "dead" (80%+ zero/default). See Section 9. |
| **Learning rate** | NOT IMPROVING. Precision@20 stuck near 0. Score-to-WR correlation near 0. Both KPIs RED. |
| **Time to useful** | Needs feature pipeline fix (populate real OHLCV values) + retrain. 1-3 days if pipeline fixed. |

#### Feature List (46 features, grouped by phase)

| # | Feature | Phase | Default | Population Rate | Notes |
|---|---------|-------|---------|-----------------|-------|
| 1 | `strategy_encoded` | Core | - | 100% | hash(name) % 100 / 100 |
| 2 | `category_encoded` | Core | 0 | 100% | crypto=0, forex=1, stock=2, penny=3, meme=4 |
| 3 | `confidence` | Core | 0 | 100% | Strategy raw confidence |
| 4 | `rsi_at_entry` | Core | 50 | 17% (58/342) | Rest imputed to 50 -- nearly dead |
| 5 | `volume_ratio` | Core | 1.0 | 6% (22/342) | Rest imputed to 1.0 -- nearly dead |
| 6 | `risk_reward` | Core | 1.5 | 100% | TP/SL ratio |
| 7 | `atr_at_entry` | Core | 0 | 5% (18/342) | Rest imputed to 0 -- nearly dead |
| 8 | `regime_encoded` | Core | 0 | ~5% | bull=1, neutral=0, bear=-1 -- nearly dead |
| 9 | `direction_encoded` | Core | 1 | 100% | LONG=1, SHORT=-1 |
| 10 | `strategy_win_rate` | Core | 0 | ~80% (via audit dashboard fallback) | Strategy historical WR |
| 11 | `strategy_sharpe` | Core | 0 | ~80% | Strategy historical Sharpe |
| 12 | `strategy_closed_picks` | Core | 0 | ~80% | Strategy trade count |
| 13-18 | `hour_utc`, `hour_sin`, `hour_cos`, `day_of_week`, `is_weekend`, `hour_x_vol` | Phase 5 | time-based | 100% | Time-of-day cyclic features |
| 19-21 | `sl_distance_pct`, `tp_distance_pct`, `rr_asymmetry` | Phase 5 | 0 | 100% | Trade structure features |
| 22-24 | `funding_rate_raw`, `funding_z_30d`, `funding_persistence` | Phase 6 | 0 | <5% | Binance fapi -- rarely populated |
| 25-27 | `orderbook_imbalance`, `vpin_toxicity`, `funding_rate_norm` | Phase 7 | 0/0.5/0 | <5% | Scanner injection -- rarely populated |
| 28-30 | `obi_delta_5`, `obi_delta_15`, `obi_acceleration` | Phase 8 | 0 | <5% | OBI velocity -- rarely populated |
| 31 | `fear_greed_norm` | Phase 8 | 0.5 | <5% | F&G index -- rarely injected |
| 32-35 | `cs_momentum_rank`, `cs_relative_strength`, `cs_dispersion`, `cs_leader_lag` | Phase 10 | 0.5/0/0/0 | <5% | Cross-sectional features |
| 36-39 | `close_to_vwap`, `garman_klass_vol`, `fng_gradient`, `risk_reward_raw` | Phase 12 | 0/0/0/1.5 | <10% | OHLCV-derived, new |
| 40-46 | `mom30`, `rsi30`, `macd_hist_norm`, `stoch_k30`, `stoch_d30`, `cci20_norm`, `williams_r` | Phase 13 | 0.5 defaults | <5% | Chi-squared validated. Computed in `technical_features.py`. |

**Feature health summary:** Of 46 declared features, approximately **1 is truly alive** (non-zero/non-default in >20% of picks). ~25 are "dead" (80%+ at their default value). The model auto-drops features with 80%+ zero/NaN during training, but the underlying data pipeline is not populating them. This is the **#1 critical issue**.

### Model 2: KIMI ML Signal Ranker

| Attribute | Value |
|-----------|-------|
| **File** | `KIMI_RISEOFTHECLAW/ml_signal_ranker.py` |
| **Algorithm** | RandomForest (200 trees, max_depth=8) |
| **Training data** | 305 samples (109 wins, 196 losses = 35.7% base WR) |
| **AUC** | **0.7518** (std 0.0585) -- BEST ML model in the entire platform |
| **Status** | **TRAINED, ACTIVE** -- last trained 2026-03-18 03:51 UTC |
| **Features (15)** | algo_wr (21.6%), algo_sharpe (14.8%), hour_of_day (14.6%), risk_reward (13.6%), symbol_enc (9.8%), algo_closed (6.1%), algo_drought (6.1%), algo_id_enc (5.3%), algo_kelly (4.1%), category_enc (2.3%), tier_enc (1.8%), rsi_at_entry (0.0), volume_ratio (0.0), fear_greed (0.0), btc_24h_change (0.0) |
| **Dead features** | 4 at 0.0: rsi_at_entry, volume_ratio, fear_greed, btc_24h_change |
| **Flaws** | (1) 4 dead features placeholder. (2) 305 samples thin for 15 features. (3) algo_wr dominates at 21.6% -- may just replicate WR lookup. |
| **Learning rate** | AUC improved from ~0.50 (heuristic mode) to 0.7518 after RF activation. Genuine progress. |
| **Time to useful** | Already useful. Populate the 4 dead features + expand to 500+ samples for next gain. |

### Model 3: Claude Gainer ML

| Attribute | Value |
|-----------|-------|
| **File** | `claude_gainer_ml/models/training_meta.json` |
| **Algorithm** | RF (45%) + XGBoost (55%) ensemble |
| **Training data** | 15,046 total (12,036 train + 3,010 test + 46 online samples) |
| **AUC** | **0.40** -- BELOW random (worse than coin flip) |
| **Status** | **DEGRADED** -- AUC stuck at 0.40 across 7 versions (v1.0.1 to v1.0.7) |
| **Flaws** | (1) AUC=0.40 means model is ANTI-predictive. (2) Positive rate 0.97% = extreme imbalance. (3) 7 retraining cycles with ZERO improvement. |
| **Learning rate** | NOT IMPROVING. Flatlined. |
| **Time to useful** | Unclear. Consider reframing as anomaly detection or disabling ML layer. |

### Model 4: Quick Guess (Parallel Agent)

| Attribute | Value |
|-----------|-------|
| **File** | `parallel_agent/data/guess_stats.json` |
| **Algorithm** | Directional prediction model (BTC/ETH/SOL at 5/15/60 min horizons) |
| **Training data** | **4,784 guesses** across 3 symbols x 3 horizons (up from 2,100) |
| **Accuracy** | **49.2% overall** (2352/4784) -- essentially a **coin flip** |
| **Status** | **ACTIVE but AT coin flip** |
| **By symbol** | BTC: 48.6% (774/1593), ETH: 47.7% (761/1595), SOL: 51.2% (817/1596) |
| **By horizon** | 5min: 49.0% (811/1654), 15min: 50.3% (819/1628), 60min: 48.1% (722/1502) |
| **TP/SL wins** | 0.5x TP: 40.4% (1931/4784), 1.0x TP: 33.7% (1612/4784), 1.5x TP: 27.4% (1312/4784). SL setting makes NO difference (identical at all SL levels). |
| **Flaws** | (1) At coin flip on all horizons. (2) TP/SL settings do not affect outcome -- confirms no directional edge. (3) SOL slightly above 50% may be noise. |
| **Learning rate** | Improved from 39.2% (2,100 guesses) to 49.2% (4,784 guesses) -- converging to 50% = pure noise. |
| **Time to useful** | Low priority. This is fundamentally a random walk on short timeframes. |

### Model 5: Thompson Sampling

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/thompson_sampler.py` + `alpha_engine/data/thompson_state.json` |
| **Algorithm** | Beta-Bernoulli Thompson Sampling with temporal decay |
| **Tracking** | **183+ strategies** with Beta(alpha, beta) posteriors |
| **Status** | **ACTIVE, HEALTHY** |
| **Flaws** | (1) Top strategies are ml_enhanced with inflated PnL from FET/RENDER duplication. (2) Small alpha+beta for many strategies means very uncertain posteriors. |
| **Learning rate** | Updates after every trade. Adapts with 0.95/week decay. Working as designed. |

### Model 6: Online Learner

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/online_learner.py` + `alpha_engine/data/online_learner_state.json` |
| **Algorithm** | Single-layer perceptron, SGD with lr=0.01 |
| **Training** | **1 step** (1 trade processed) |
| **Status** | **EMBRYONIC** -- effectively untrained |
| **Flaws** | Only 1 gradient step -- no learned representation yet. Likely a wiring issue preventing updates. |
| **Time to useful** | Weeks. Needs fix to ensure update is called on every trade close. |

### Model 7: HMM Regime

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/hmm_regime.py` + `alpha_engine/data/hmm_regime_state.json` |
| **Algorithm** | 3-state Hidden Markov Model (BULL / BEAR / CHOP) |
| **Status** | **ACTIVE, HEALTHY** |
| **Flaws** | (1) BULL/BEAR probabilities often close -- low confidence regime. (2) Only 3 states may be insufficient. |
| **Learning rate** | Updates each cycle from BTC price data. Working as designed. |

### Model 8: Pattern Predictor

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/pattern_predictor.py` + `alpha_engine/data/pattern_stats.json` |
| **Algorithm** | Multi-dimensional pattern matching with hierarchical fallback (L0-L5) |
| **Status** | **ACTIVE, GROWING** |
| **Key insight** | LONG ml_enhanced crypto = 82% WR. SHORT ml_enhanced crypto = 13% WR. Confirms the SHORT problem at pattern level. |
| **Flaws** | (1) Most patterns at L0 have only 1-2 trades. (2) "rsi_unknown" and "regime_unknown" dominate -- feature population failure. |

### Model 9: SL Calibrator

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/sl_calibrator.py` + `alpha_engine/data/sl_calibration.json` |
| **Algorithm** | MAE/MFE percentile analysis per (asset_class, strategy_type, session) group |
| **Status** | **ACTIVE but mostly insufficient data** |
| **Flaws** | Requires much more data before it can meaningfully override default TP/SL. Consider reducing bucket granularity. |

---

## Section 3: Research Techniques Implemented (8/10)

### Technique 1: Thompson Sampling (#1 ranked)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/thompson_sampler.py` |
| **What it does** | Bayesian strategy allocation via Beta-Bernoulli posteriors. Winners get concentrated capital; losers get starved. |
| **Where wired** | `forward_validator.py`: `get_strategy_score_bonus(strategy)` adjusts elite_score +/-10. Also called at trade close via `update_after_trade()`. |
| **Actual impact** | Active, 183+ strategies tracked. Score adjustments being applied. |

### Technique 2: Online Learning (#2)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/online_learner.py` |
| **What it does** | Single-layer perceptron updated after every trade. Learns which features predict wins in real-time without full retraining. |
| **Actual impact** | Only 1 step processed. Effectively dormant. Wiring issue suspected. |

### Technique 3: Stacked Ensemble (via ML Ranker)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/ml_ranker.py` |
| **What it does** | Heterogeneous stacking: XGBoost (primary) + RF (secondary) + CatBoost (secondary, optional). CatBoost uses ordered boosting (`has_time=True`) for time-series awareness. |
| **Where wired** | `forward_validator.py`: `MLSignalRanker` scores all signals before gating. |
| **Actual impact** | Champion model is INCOMPATIBLE (feature mismatch). Falling back to heuristic scoring. CatBoost is trained when installed but cannot score due to same champion incompatibility. |

### Technique 4: HMM Regime Detection (#3)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/hmm_regime.py` |
| **What it does** | 3-state HMM classifies market regime (BULL/BEAR/CHOP). Regime-compatible signals get boosted; incompatible get penalized. |
| **Actual impact** | Active. Adjustments being applied but often marginal due to regime uncertainty. |

### Technique 5: BOCPD Changepoint Detection (#4)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/bocpd.py` |
| **What it does** | Bayesian Online Changepoint Detection on BTC daily returns. -8 elite_score penalty during changepoints. |
| **Actual impact** | Active. Prevents entries during regime transitions. |

### Technique 6: Bandit TP/SL (#7)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/bandit_tp_sl.py` |
| **What it does** | Multi-armed bandit selects optimal (TP_mult, SL_mult) pair for each signal. Arms compete via Thompson sampling. |
| **Actual impact** | Active. Recommending TP/SL via `bandit_tp`, `bandit_sl`, `bandit_arm_index` fields. |

### Technique 7: Feature-Weighted Linear Stacking (FWLS, #6)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/fwls_stacker.py` |
| **What it does** | Context-weighted meta-learner: `final = (w_base + w_ctx * context) * predictions`. |
| **Actual impact** | Available but not confirmed wired into main pipeline. |

### Technique 8: Backtest Bridge (#8)

| Attribute | Value |
|-----------|-------|
| **File** | `alpha_engine/backtest_bridge.py` |
| **What it does** | Converts 55,000+ backtest results into pseudo-closed-picks for ML training data augmentation. Backtest data weighted 0.3x. Capped at 3:1 ratio vs live picks. |
| **Actual impact** | Active. augmented_training.json has ~1,118 samples. Quality concern: look-ahead bias. |

### NOT YET IMPLEMENTED

| # | Technique | Status |
|---|-----------|--------|
| 5 | **Temporal Fusion Transformer (TFT)** | Deferred -- requires PyTorch, GPU, 10,000+ data points. |
| 10 | **Momentum Transformer** | Deferred -- same constraints as TFT. |

---

## Section 4: Scoring System

### Elite Score Components (max theoretical: ~183 pts)

Weights recalibrated from Method 4 backtest (2026-03-22). Major changes:
- ML replacement halved from 35 to 18 pts (was over-weighted vs track record)
- Confluence is now a PENALTY (anti-predictive: 34% WR, herding effect)
- Monte Carlo DISABLED (anti-predictive: 10% WR)
- Leverage safety is BEST PREDICTOR (67% WR, +1.21% P/L)
- Copy trader confidence deflation caps copy picks at 0.60 confidence
- Strategy track record doubled from 10 to 20 pts

| Component | Max Pts | Source | Notes |
|-----------|---------|--------|-------|
| **ML Replacement** | 18 | Confidence + Kelly + strategy reputation | Halved from 35 per Method 4 backtest. Confidence >=0.70 = 80% WR = up to 8 pts. Kelly >=0.35 = 5 pts. Strategy WR >=0.65 = 5 pts. |
| **Forward WR** | 30 | strategy_performance.json | 10+ trades at 55%+ WR = full marks. Unvalidated (<10 trades) capped. Profit factor >= 2.0 gives 15% boost. Copy trader forward credit capped at 8 pts. |
| **Source System** | 20 | system-level WR tier | New in current version. |
| **Confluence** | -3 to 0 | confluence_strategies count | ANTI-PREDICTIVE (34% WR). Now a herding penalty. |
| **Position** | 10 | unrealized_pnl_pct + tp_progress | +5% unrealized = 10 pts. TP progress >= 80% = +3 pts. |
| **Leverage Safety** | 10 | stop distance + ML confidence + forward WR | **BEST PREDICTOR** (67% WR, +1.21% P/L). Tight stop (1.5%) = 5 pts. High ML (0.80+) = +3. |
| **Risk:Reward** | 5 | TP/SL ratio | RR >= 3.0 = 5 pts, >= 2.0 = 3, >= 1.5 = 2, >= 1.0 = 1. |
| **Monte Carlo** | 0 | DISABLED | ANTI-PREDICTIVE (10% WR). Always returns 0. |
| **Signal Quality** | 10 (or -5) | pattern_predictor + entry_optimizer + execution_cost | Golden pattern = +5, danger = -5. Strong entry zone = +3. Net edge >= 20bps = +2. |
| **Meta-Label** | 3 (or -5) | meta_labeler P(profitable) | P > 0.7 = +3 pts (boost). P < 0.3 = -5 pts (penalize). |
| **Volume** | -20 to 5 | volume_ratio | Penalize vol_ratio > 5.0 (17.4% WR). Reward 1.5-3.0x. |
| **Regime** | -30 to 15 | direction + regime | Ranging=+15, SELL in bull=-30, direction-aware. Regime+misalignment cap: 65 max. |
| **Proven Strategy** | 10 | academically-backed OOS strategies | |
| **Strategy Track Record** | -5 to 20 | actual closed-pick WR | Doubled from 10 per Method 4 backtest. |
| **Hindsight Winner** | 3 | winner_patterns.json | |
| **Skyrocket Potential** | 5 | skyrocket_detector alerts | |
| **Super Signal Cap** | cap at 70 | unproven "super" strategies | |
| **Directional Concentration** | -5 | ALL picks same direction | |

### Copy Trader Confidence Deflation (2026-03-19)

Copy trader scrapers set confidence based on trader profile quality (PnL, account size, trade count) -- NOT signal quality. A 0.95 confidence from copy_hl means "good trader", not "strong signal". The 80% WR correlation for conf>=0.70 was calibrated on non-copy picks.

**Fix:** Copy trader confidence is capped at 0.60 before scoring. Copy trader forward_wr is reset to 0 and only uses actual system-verified closed picks for forward credit.

### Score Modifiers (applied after elite_score, in forward_validator gates)

| Modifier | Range | Source |
|----------|-------|--------|
| Thompson bonus | +/- 10 | thompson_sampler: strong posterior WR = +10, weak = -10 |
| HMM regime adjustment | +/- variable | hmm_regime: regime-compatible signals boosted |
| BOCPD changepoint | -8 | bocpd: changepoint detected = warning |
| DSR penalty | -15 | deflated_sharpe: Sharpe not significant |
| WRC penalty | -10 | White's Reality Check: alpha not significant (p > 0.05) |
| Hot streak bonus | +5 or +10 | 5+ trades at 75%+ WR = +5, 90%+ = +10 |
| Momentum alignment | -8 | SMA5/SMA20 misalignment penalty |
| Daily trend bonus | +5 or -5 | SMA50/SMA200 uptrend (+5 for longs) or downtrend (-5) |
| Volume confirmation | +5/+3/-3 | Volume >= 2x avg = +5, >= 1.5x = +3, < 0.5x = -3 |
| VPIN noise boost | +5 | VPIN < 0.3 noise regime: mean-reversion strategies get +5 |
| LDS warning | -15 | Liquidation Density Score > 3: cascade risk |
| OBI velocity | +3/-3 | Order book imbalance velocity alignment with direction |
| GRU deep learning | +5/-5 | Local GPU-trained direction model alignment |
| Adaptive trust | +/- 0.20 | adaptive_trust_tuner: rolling WR-based confidence adjustment |

### Grade Thresholds

| Grade | Score | Meaning |
|-------|-------|---------|
| **S** | >= 95 | Elite -- highest conviction |
| **A** | >= 80 | Strong -- high quality signal |
| **B** | >= 65 | Good -- worth taking |
| **C** | >= 50 | Average -- acceptable |
| **D** | >= 35 | Weak -- marginal |
| **F** | < 35 | Fail -- suppressed by quality gate at score < 30 |

---

## Section 5: Gating Pipeline (29 Total Gates)

### Layer 1: Production Scanner Quality Gates (6 gates in `production_scanner.py::apply_quality_gates()`)

Applied BEFORE forward_validator. Data-driven gates based on 788 forward-tested closed picks analysis.

| # | Gate | Type | Condition | Action |
|---|------|------|-----------|--------|
| 1 | **Confidence Cliff** | HARD | conf < 0.70 | BLOCKS (10.2% WR below threshold vs 80% WR above) |
| 2 | **ML Score Floor** | HARD | ml_score < 0.50 | BLOCKS (23.5% WR below threshold) |
| 3 | **Forex Block** | HARD | category == forex | BLOCKS (0% WR on 17+ trades) |
| 4 | **SHORT Quality Gate** | HARD | SELL/SHORT direction | Uses `short_trade_validator.py`: proven strategies pass, toxic blocked, others need conf >= 0.80 + bearish regime |
| 5 | **Volume Spike** | HARD | vol_ratio > 5.0 | BLOCKS (17.4% WR) |
| 6 | **Unvalidated Strategy** | HARD | forward_validated=false AND forward_trades=0 AND conf < 0.80 | BLOCKS |

Additional production_scanner filters (not numbered gates):
- **Bad Symbol Filter**: removes known bad symbols (Hyperliquid k-prefix, delisted, stablecoins)
- **Stale Pick Closer**: closes picks open >48h with no price updates
- **TP Cap**: crypto max 12%, forex max 1.0% from entry
- **Symbol Sanitizer**: strips CoinGecko numeric IDs
- **Deduplicator**: keeps highest-confidence per symbol+direction, resolves BUY/SELL conflicts
- **Regime Gate**: suppresses low-score crypto LONGs in bearish regime

### Layer 2: JSON-Driven Gates (12 gates in `gates_config.json`)

Declarative rule engine for forward_validator. Each gate has id, type (hard/soft/hard_soft), condition, action, and params. Fully configurable without code changes.

| # | Gate ID | Type | Description | Action |
|---|---------|------|-------------|--------|
| 1 | `price_sanity` | Hard | Entry price suspiciously low for USD pair (catches yfinance BTC-denominated bugs). Per-symbol price floors (BTC>$1000, ETH>$100, etc.) | BLOCKS |
| 2 | `rr_gate` | Hard | R:R < 1.5 (or < 1.0 for mean-reversion). Mercury data: RR>=1.5 lifts WR 39%->68%. | BLOCKS |
| 3 | `direction_gate_long` | Hard | System-wide long WR < 30% across 10+ trades | BLOCKS longs |
| 4 | `enhanced_short_gate` | Hard (4-layer) | Layer 1: system SHORT WR >= 40%. Layer 2: conf >= 0.80. Layer 3: ml >= 0.80. Layer 4: price < SMA50 (downtrend confirmation). ALL must pass. | BLOCKS if any fails |
| 5 | `forex_gate` | Hard | Forex WR < 30% (currently 0% on 0/9 trades) | BLOCKS all forex |
| 6 | `meme_short_gate` | Hard | Meme coin + SHORT (25% WR category) | BLOCKS |
| 7 | `vpin_toxicity` | Hard/Soft | VPIN > 0.55: BLOCK. 0.3-0.55: allow only elite (score >= 60). < 0.3: +5 for mean-reversion. | Variable |
| 8 | `lds_risk` | Hard/Soft | LDS > 5: BLOCK (cascade imminent). LDS 3-5: -15 score penalty. | Variable |
| 9 | `cooldown_gate` | Hard | 2+ consecutive losses on same symbol+strategy | BLOCKS |
| 10 | `dsr_penalty` | Soft | DSR < 0.95: Sharpe not significant. -15 elite_score. | -15 penalty |
| 11 | `wrc_penalty` | Soft | White's Reality Check p > 0.05: alpha not significant. -10 score. | -10 penalty |
| 12 | `quality_gate` | Hard | elite_score < 30 after all adjustments. Bottom ~20% net-negative expectancy. | BLOCKS |

### Layer 3: Forward Validator Inline Gates (11 gates in code)

| # | Gate | Type | What It Checks | Action |
|---|------|------|---------------|--------|
| 1 | **Structural Strategy Gate** | HARD | Kill list, max 2 structural per symbol, net edge > 5 bps, volume > 0.3 | BLOCKS |
| 2 | **R:R Gate** | HARD | risk_reward < 1.5 (1.0 for mean-reversion) | BLOCKS |
| 3 | **Direction Gate (Long)** | HARD | System-wide long WR >= 30% on 10+ trades | BLOCKS if WR too low |
| 4 | **Enhanced SHORT Gate** | HARD (4 layers) | system SHORT WR >= 40%, conf >= 0.80, ml >= 0.80, price < 50-SMA | BLOCKS |
| 5 | **Category Gates (Forex + Meme SHORT)** | HARD | Forex WR < 30%, meme SHORT | BLOCKS |
| 6 | **VPIN Toxicity + Regime Routing** | HARD/SOFT | Same as JSON gate 7 | BLOCKS or adjusts |
| 7 | **LDS Risk Filter** | HARD/SOFT | Same as JSON gate 8 | BLOCKS or -15 |
| 8 | **Cooldown Gate** | HARD | 2+ consecutive losses | BLOCKS |
| 9 | **DSR + WRC Penalties** | SOFT | DSR < 0.95: -15. WRC p > 0.05: -10 | Penalties |
| 10 | **Momentum Confirmation** | SOFT | SMA5/SMA20 misalignment: -8. SMA50/SMA200 daily trend: +/-5 | Adjustments |
| 11 | **Quality Gate** | HARD | elite_score < 30 | BLOCKS |
| 12 | **Winner Filter** | HARD | Research-backed quality gate based on 8,457 closed pick analysis | BLOCKS |

**Note:** Some gates overlap between JSON config and inline code. The JSON config (`gates_config.json`) is the declarative version intended to eventually replace inline gate code.

---

## Section 6: New Modules (March 2026)

### 6.1 Adaptive Trust Tuner (`alpha_engine/adaptive_trust_tuner.py`)

**Purpose:** Automatically adjusts strategy trust weights based on forward performance. Strategies that consistently hit TP get higher confidence; strategies that consistently hit SL get lower confidence.

**How it works:**
- Loads `closed_picks.json` and groups by strategy + symbol
- Computes rolling metrics: WR last 10/20/50, profit factor, avg PnL
- Strategy-level boosts: +0.15 (70%+ WR), +0.10 (60%+), +0.05 (50%+), -0.10 (<40%), -0.15 (<30%)
- Smart detection: WR looks good but PF < 1.0 and avg_pnl < 0 = NEGATIVE boost (winning often but losing more per loss)
- Symbol-level boosts: +0.08 (70%+ WR on specific symbol), -0.10 (<30%)
- Total adjustment capped at +/- 0.20
- 1-hour in-memory cache for performance
- Writes `data/trust_adjustments.json`

**Integration:** `apply_trust_adjustments(pick)` returns a float adjustment applied to confidence in the pipeline. Respects "mutate before kill" rule -- NEVER deletes strategies.

### 6.2 HTF Confirmation Filter (`alpha_engine/htf_confirmation.py`)

**Purpose:** Higher Timeframe (daily) confirmation for Alpha Engine signals. Prevents taking trades against the dominant daily trend.

**Indicators computed:**
- Daily EMA 9/21/50/200 alignment
- Daily RSI(14)
- Daily Bollinger %B (20,2)
- Daily MACD histogram direction
- Daily Williams %R(14)
- Weekly trend proxy (last 5 daily closes)

**Scoring:** 0-5 bullish indicators (EMA alignment, RSI > 50, BB > 0.5, MACD positive+rising, weekly UP). Bias: BULLISH (4+), BEARISH (4+ bear), NEUTRAL.

**Integration:**
- `apply_htf_filter(picks)` -- annotates picks with htf_bias, htf_score, htf_aligned
- Misaligned picks: confidence -= 0.10
- Strongly aligned picks (score >= 4): confidence += 0.05
- Pure Python + numpy, no pandas/scipy
- Binance 4-mirror API failover, 1-hour cache, 500ms rate limiting

### 6.3 Indicator Correlation Tracker (`alpha_engine/indicator_correlation_tracker.py`)

**Purpose:** Monitors 14 technical indicators alongside active picks to discover which indicators actually predict profitability.

**14 tracked indicators:** rsi_14, rsi_2, macd_histogram, bollinger_pct_b, volume_ratio, atr_pct, ema_alignment, stoch_k, stoch_d, obv_trend, adx, vwap_deviation_pct, consecutive_candles, dist_from_200sma_pct.

**How it works:**
- Runs as standalone CLI or library import
- Fetches OHLCV from Binance (4-mirror failover + CoinGecko fallback)
- Logs observations to `data/indicator_correlation_log.json` (rolling 7-day retention)
- Computes per-indicator predictive power statistics
- Writes ranked results to `data/indicator_predictive_power.json`
- Exports `get_indicator_filter_recommendations()` for scanner integration

### 6.4 Missed Opportunity Analyzer (`alpha_engine/missed_opportunity_analyzer.py`)

**Purpose:** Self-improving feedback loop that identifies gaps and failures.

**What it does (hourly):**
1. Identifies top Binance gainers we did NOT have picks on
2. Identifies wrong guesses (SL_HIT picks) and analyzes why
3. Detects recurring patterns in misses and failures
4. Generates actionable recommendations for the scanner
5. Provides `get_universe_additions()` for dynamic symbol rotation

**Thresholds:**
- MIN_GAIN_PCT = 10% (minimum gain to count as "missed")
- MIN_VOLUME_USD = $2M
- UNIVERSE_ADD_THRESHOLD = 3 (missed 3+ times in 7 days = recommend add)
- STRATEGY_BAD_SL_RATE = 0.60 (>60% SL rate = flag strategy)

**Output files:**
- `data/missed_gainers_log.json` (30-day rolling log)
- `data/wrong_guesses_log.json` (failure analysis)
- `data/hourly_improvement_report.json` (actionable recommendations)
- `data/dynamic_universe.json` (suggested symbol additions)

**Integration:** `production_scanner.py` imports `get_universe_additions()` to add missed symbols to scanning universe.

### 6.5 Mercury 2 RSI Guard (`mercury2/risk_engine.py`)

**Added:** Guard 8 -- RSI overbought guard. Audit found: LONGs with RSI >= 70 had 3.8% WR vs 90% WR when blocked. Blocks LONG entries when RSI >= 70.

Mercury 2 now has 8 guards total:
0. Symbol blacklist (0% WR symbols)
1. Confidence >= 0.55 (no fear discount)
2. Probability >= 2x total cost
3. Trend: price > 200 SMA OR F&G < 20
4. Funding z-score within +/-2
5. ATR-edge > 2x cost
6. Minimum R:R >= MIN_RR
7. High-ATR guard: reduce size 50% when ATR > 1.5x avg
8. **RSI overbought guard: block LONG when RSI >= 70** (NEW)

---

## Section 7: Data Files Reference

### Core Pipeline Data

| File | Path | Contents |
|------|------|----------|
| `active_picks.json` | `alpha_engine/data/active_picks.json` | All open positions with TP/SL, MFE/MAE, elite_score, forward gate status |
| `active_picks_fast.json` | `alpha_engine/data/active_picks_fast.json` | Fast-mode variant (30-min cycle) |
| `closed_picks.json` | `alpha_engine/data/closed_picks.json` | All historical outcomes (WON/LOST). ~800+ picks. |
| `strategy_performance.json` | `alpha_engine/data/strategy_performance.json` | Per-strategy stats: WR, Sharpe, PnL, closed count. Auto-rebuilt hourly. |
| `validation_log.json` | `alpha_engine/data/validation_log.json` | Chronological log of all pick closures |
| `core_whitelist.json` | `alpha_engine/data/core_whitelist.json` | Kill list of permanently disabled strategies |
| `strategy_tweaks.json` | `alpha_engine/data/strategy_tweaks.json` | Auto-adjusted strategy parameters from tweaker |
| `premium_signals.json` | `alpha_engine/data/premium_signals.json` | Production scanner output (consumed by dashboards) |
| `trust_adjustments.json` | `alpha_engine/data/trust_adjustments.json` | Adaptive trust tuner output (strategy + symbol boosts) |
| `gates_config.json` | `alpha_engine/gates_config.json` | JSON-driven gate rules (12 gates, declarative config) |

### ML Model Data

| File | Path | Contents |
|------|------|----------|
| `model_comparison.json` | `alpha_engine/data/model_comparison.json` | Champion selection result (2026-03-22: `champion_incompatible`, 296 val samples) |
| `feature_importance.json` | `alpha_engine/data/feature_importance.json` | Feature importances, dead features, drop candidates |
| `kpi_report.json` | `alpha_engine/data/kpi_report.json` | Precision@k, score-to-WR correlation |
| `ml_weights.json` | `alpha_engine/data/ml_weights.json` | ML model weights for strategies |
| `augmented_training.json` | `alpha_engine/data/augmented_training.json` | Backtest bridge output (~1,118 samples) |
| `ml_challenger.joblib` | `alpha_engine/data/ml_challenger.joblib` | Serialized challenger model |
| `boruta_selected_features.json` | `alpha_engine/data/boruta_selected_features.json` | Boruta feature selection cache (weekly) |
| `prediction_history.json` | `alpha_engine/data/prediction_history.json` | Last 500 predictions for drift detection |
| `obi_history.json` | `alpha_engine/data/obi_history.json` | 100 snapshots per symbol for OBI velocity |

### New Module Data

| File | Path | Contents |
|------|------|----------|
| `indicator_correlation_log.json` | `alpha_engine/data/indicator_correlation_log.json` | Rolling 7-day indicator observation log |
| `indicator_predictive_power.json` | `alpha_engine/data/indicator_predictive_power.json` | Ranked indicator statistics |
| `missed_gainers_log.json` | `alpha_engine/data/missed_gainers_log.json` | 30-day missed gainer log |
| `wrong_guesses_log.json` | `alpha_engine/data/wrong_guesses_log.json` | Wrong guess failure analysis |
| `hourly_improvement_report.json` | `alpha_engine/data/hourly_improvement_report.json` | Actionable recommendations |
| `dynamic_universe.json` | `alpha_engine/data/dynamic_universe.json` | Missed opportunity symbol additions |
| `regime_report.json` | `alpha_engine/data/regime_report.json` | Regime detection production report |

### Research Module State

| File | Path | Contents |
|------|------|----------|
| `thompson_state.json` | `alpha_engine/data/thompson_state.json` | Beta(alpha, beta) per strategy. 183+ strategies. |
| `online_learner_state.json` | `alpha_engine/data/online_learner_state.json` | Perceptron weights. 1 step, 9 features. |
| `hmm_regime_state.json` | `alpha_engine/data/hmm_regime_state.json` | Current regime probabilities. |
| `pattern_stats.json` | `alpha_engine/data/pattern_stats.json` | Pattern WR tracking. |
| `sl_calibration.json` | `alpha_engine/data/sl_calibration.json` | SL calibration groups. |
| `monte_carlo_results.json` | `alpha_engine/data/monte_carlo_results.json` | Per-strategy Monte Carlo verdicts |

### External System Data

| File | Path | Contents |
|------|------|----------|
| `training_meta.json` | `claude_gainer_ml/models/training_meta.json` | Claude Gainer model metadata (v1.0.7, AUC 0.40) |
| `guess_stats.json` | `parallel_agent/data/guess_stats.json` | Quick Guess results (49.2% accuracy, 4,784 guesses) |

---

## Section 8: KPI Dashboard

### Current Values (as of 2026-03-23)

| # | KPI | Current Value | Target | Status |
|---|-----|---------------|--------|--------|
| 1 | Precision@10 (top 10 scored picks WR) | **~0%** | >= 60% | RED |
| 2 | Precision@20 | **~0%** | >= 52% | RED |
| 3 | Score-to-WR correlation | **~0.0** | > 0 (positive) | RED |
| 4 | Recent 50 picks WR | **59.2%** | >= 55% | GREEN |
| 5 | Total closed picks | **800+** (est.) | >= 200 | GREEN |
| 6 | Alpha Engine overall WR | **41.5%** | >= 50% | RED |
| 7 | KIMI ML AUC | **0.7518** | >= 0.65 | GREEN |
| 8 | Claude Gainer AUC | **0.40** | >= 0.55 | RED |
| 9 | Quick Guess accuracy | **49.2%** (4784 guesses) | >= 55% | RED (coin flip) |
| 10 | Thompson strategies tracked | **183+** | >= 50 | GREEN |
| 11 | Pattern predictor | growing | >= 20 golden | GREEN |
| 12 | Model champion status | **INCOMPATIBLE** | ACTIVE | RED |
| 13 | Feature health | **1/46 alive (~2%)** | >= 70% | RED (CRISIS) |
| 14 | Online learner steps | **1** | >= 50 | RED |

**Summary: 4 GREEN, 0 YELLOW, 10 RED.**

### Performance Snapshot (2026-03-23)

| Metric | Value | Notes |
|--------|-------|-------|
| **Recent 50 picks** | **59.2% WR** | Encouraging -- gates are working |
| **Overall (all time)** | **41.5% WR** | Dragged down by early poor picks |
| **SHORT WR** | **~20%** | Still terrible. Enhanced SHORT gate mitigating. |
| **Forex WR** | **0%** | Gate blocks all forex. |
| **Copy trader picks** | Deflated | Confidence capped at 0.60, forward credit reset. |

**The critical finding persists:** The ML ranker champion model cannot score picks (feature mismatch since model_comparison.json 2026-03-22), which means ML precision metrics are all 0 -- the ML layer is effectively disabled. Everything runs on heuristic scoring. The recent 50-pick WR of 59.2% is driven by quality gates, NOT by ML.

---

## Section 9: Known Issues and Roadmap

### CRITICAL: Feature Population Crisis

**The #1 problem in the entire system.** Of 46 declared ML features, approximately 25 are "dead" (80%+ at default value) and only ~1 feature has meaningful non-zero values in >20% of closed picks. Root cause: the scanner and strategy modules do not populate most features at signal generation time.

| Feature Group | Count | Population Rate | Notes |
|---------------|-------|-----------------|-------|
| Core (strategy_encoded, confidence, risk_reward, direction) | 5 | 100% | Working |
| Strategy perf (win_rate, sharpe, closed_picks) | 3 | ~80% | Via audit dashboard fallback |
| Time-of-day (hour_utc, hour_sin, etc.) | 6 | 100% | Working |
| Trade structure (sl_distance, tp_distance, rr_asymmetry) | 3 | 100% | Working |
| RSI/ATR/volume/regime at entry | 4 | 5-17% | Mostly imputed defaults |
| Funding/microstructure (OBI, VPIN, funding) | 9 | <5% | Scanner rarely injects these |
| Cross-sectional (cs_momentum, cs_relative_strength) | 4 | <5% | cross_sectional.py rarely called |
| Phase 12 (close_to_vwap, garman_klass_vol) | 4 | <10% | New, not fully wired |
| Phase 13 chi-squared (mom30, rsi30, stoch_k30, etc.) | 7 | <5% | technical_features.py not fully wired |

**Impact:** The model trains on mostly-zero data, learns nothing, and falls back to heuristic scoring. AUC=1.0 is an artifact of the few non-zero features perfectly separating the tiny subset of populated samples.

**Fix priority:** Wire `technical_features.py` and `cross_sectional.py` into the scanner signal generation loop so every pick has real OHLCV-derived values at creation time. This alone would raise alive features from 1 to ~20+.

### Critical (Fix This Week)

| Issue | Impact | Fix |
|-------|--------|-----|
| **Feature population crisis (25 dead features)** | Model learns nothing. ML scoring disabled. | Wire technical_features.py and cross_sectional.py into scanner. Populate OHLCV features at signal generation time. |
| **ML champion model incompatible** | ML scoring completely disabled. All picks scored by heuristic fallback. | Retrain with matching feature set after feature pipeline fix. |
| **AUC=1.0 persists** | Training metrics are meaningless. | Root cause: even after removing 4 leaky features + purged CV, the few populated features perfectly separate the tiny non-zero subset. Fix requires populating more features. |
| **Online learner stuck at 1 step** | Continuous learning not happening. | Debug why `online_update()` is not called on trade close. |
| **Overall WR 41.5%** | Below coin flip on aggregate. | Recent 50 at 59.2% suggests gates are working. Need time for poor early picks to age out. |

### Degraded (Monitor)

| Issue | Impact | Status |
|-------|--------|--------|
| **Quick Guess at 49.2% = exact coin flip** | No directional edge on any horizon. | Converging to 50% with more data. Consider removing. |
| Claude Gainer AUC 0.40 | Model is anti-predictive. | Stuck across 7 retraining cycles. Consider disabling. |
| SHORT WR ~20% | Every short position is likely a loss. | Enhanced SHORT gate (4-layer) mitigating. |
| Forex WR 0% | All forex positions lose. | Gate blocks all forex. Consider removing forex strategies. |
| SL Calibrator insufficient data | Default TP/SL for 97% of groups. | Slow improvement as trades accumulate. |
| Pattern predictor "unknown" features | Most patterns have "rsi_unknown" / "regime_unknown". | Same root cause as feature population crisis. |

### Roadmap Priorities (Ordered)

| Priority | Task | Expected Impact | Effort |
|----------|------|-----------------|--------|
| **P0** | Fix feature pipeline: wire technical_features.py into scanner | Raises alive features from 1 to 20+. Enables real ML training. | 1-2 days |
| **P0** | Retrain ML model after feature fix | New champion model with real features. May finally get AUC < 1.0 (realistic). | 1 day |
| **P1** | Add BTC correlation feature | BTC correlation is the strongest missing predictor. Most alts move with BTC. | 0.5 days |
| **P1** | Fix online learner wiring | Enable continuous adaptation without full retrain. | 0.5 days |
| **P2** | Increase production scanner TP from 3% to adaptive | Current BUY_ONLY + TP 3% + SL 2% = 56.25% WR (rank 3 config). Adaptive TP could improve. | 1 day |
| **P2** | Clean FET/RENDER duplicate data | Fixes Thompson sampling inflation on top strategies. | 0.5 days |
| **P3** | Reduce SL calibrator bucket granularity | Faster calibration with fewer groups. | 0.5 days |
| **P3** | Deploy GRU model from local_gpu_trainer | A/B test showed GRU > RF > XGB. Never deployed. | 1-2 days |

### Deferred Items

| # | Technique | Why Deferred |
|---|-----------|-------------|
| 5 | **Temporal Fusion Transformer (TFT)** | Requires PyTorch + GPU + 10,000+ data points. Current data: ~800 picks. |
| 10 | **Momentum Transformer** | Same constraints as TFT. |
| -- | **GRU deployment** | ML Crypto Predictor A/B test showed GRU (0.413) > RF (0.373) > XGB (0.365), but never deployed to production. |

---

## Section 10: How to Tweak (For Other AIs)

### Where to Adjust Scoring Weights

**File:** `alpha_engine/elite_scorer.py`

The `compute_elite_score()` function has clearly labeled sections. Key components with their Method 4 backtest calibration:
- ML replacement score: 0-18 pts (halved from 35) -- `compute_ml_replacement_score()`
- Forward WR: 0-30 pts -- copy trader deflation resets forward_wr to 0 for unverified copy picks
- Confluence: -3 to 0 pts (ANTI-PREDICTIVE penalty)
- Leverage Safety: 0-10 pts (BEST PREDICTOR)
- Monte Carlo: DISABLED (always 0)
- Track record: -5 to 20 pts (doubled from 10)

**Grade thresholds:** `S>=95, A>=80, B>=65, C>=50, D>=35, F<35`

### Where to Add/Remove Gates

Three locations:

1. **Production scanner gates** (`production_scanner.py::apply_quality_gates()`): Data-driven pre-filtering. Edit constants at top: `QUALITY_GATE_MIN_CONFIDENCE`, `QUALITY_GATE_MIN_ML_SCORE`, `QUALITY_GATE_MAX_VOL_RATIO`, `QUALITY_GATE_BLOCKED_CATEGORIES`.

2. **JSON gate config** (`gates_config.json`): Declarative gate rules. Add a new object to the `gates` array. Each gate needs: id, name, type, description, condition, action, params. No code changes needed.

3. **Forward validator inline gates** (`forward_validator.py`): Each gate follows this pattern:
```python
# --- Gate N: Name ---
try:
    if <condition_to_block>:
        print(f"  [GATE_NAME] BLOCK {signal['symbol']} ...")
        continue  # hard block
    # OR for soft gate:
    signal["elite_score"] = signal.get("elite_score", 50) - PENALTY
except Exception:
    pass  # Gate failure must not block picks
```

### Where to Add New Features to ML

**File:** `alpha_engine/ml_ranker.py`

1. Add the feature name to `MLSignalRanker.FEATURES` list
2. Add feature extraction logic in `_build_features()` method
3. Ensure the feature is populated by the scanner at signal generation time
4. Retrain (auto-triggers when closed_picks accumulate)

**CRITICAL:** After adding features, the champion model becomes INCOMPATIBLE. This is the current bug. The retraining pipeline must run with the updated feature set.

### Where to Add New Strategies

**File:** `alpha_engine/crypto_strategies.py` (bottom)

Pattern:
```python
try:
    from your_strategy_module import YOUR_STRATEGIES
    CRYPTO_STRATEGIES.update(YOUR_STRATEGIES)
except ImportError:
    pass
```

The strategy will automatically be scanned, ML-scored, gated, elite-scored, Thompson-tracked, and pattern-matched.

### How Online Learning Systems Update

All three online systems update at trade close in `forward_validator.py::validate_open_picks()`:
- Thompson: `update_after_trade(strategy, won=True/False)`
- Online learner: `online_update(pick_features, won=True/False)` (BROKEN -- only 1 step)
- Bandit: `update_bandit(arm_index, reward)`
- Adaptive trust tuner: `compute_trust_adjustments()` (runs standalone, writes JSON)

---

*Document version: 4.0 | Last updated: 2026-03-23 | Next review: 2026-03-30*
*Comprehensive update: CatBoost ensemble, 46 features (25 dead), 29 gates across 3 layers, 4 new modules, feature population crisis documented, performance data updated.*
