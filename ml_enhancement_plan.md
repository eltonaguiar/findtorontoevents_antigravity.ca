# Machine Learning Enhancement Plan for Leverage Crypto Trading Prediction System

## Overview
This document outlines a comprehensive plan to address the current shortcomings of our machine learning (ML) pipeline for leveraged crypto trading predictions. The goal is to improve model performance, robustness, and adaptability by incorporating time‑of‑day context, volatility regime awareness, entry‑timing optimization, dynamic stop‑loss calibration, and feature completeness.

---

## 1. Identified Gaps
| Gap | Description |
|-----|-------------|
| **No time‑of‑day learning** | Model ignores diurnal patterns (e.g., "BNB at 23:00 UTC is risky"). |
| **No volatility‑regime context** | Model does not differentiate low‑volatility periods (e.g., Sunday night chop) from high‑volatility regimes. |
| **No entry‑timing optimization** | Model cannot learn that a specific entry was $2 too high, leading to sub‑optimal execution. |
| **No stop‑loss calibration** | Fixed SL distance does not adapt to recent outcomes or market conditions. |
| **Sparse feature usage** | 26 of 39 engineered features are always zero, limiting the model’s informational richness. |

---

## 2. Proposed Enhancements
### 2.1 Time‑of‑Day Features
- Add **hour‑of‑day** (0‑23) and **day‑of‑week** (0‑6) as categorical embeddings.
- Create interaction terms with asset‑specific volatility (e.g., `hour * vol_24h`).
- Encode as sinusoidal features (`sin(2π*hour/24)`, `cos(2π*hour/24)`) to capture periodicity.

### 2.2 Volatility‑Regime Context
- Compute rolling volatility windows (5 min, 30 min, 4 h) and classify regimes:
  - **Low**: vol < 25th percentile
  - **Medium**: 25‑75th percentile
  - **High**: > 75th percentile
- Add regime as a one‑hot vector and as a scaling factor for risk‑adjusted features.

### 2.3 Entry‑Timing Optimization
- Record **execution slippage** (`entry_price - mid_price_at_signal`).
- Include slippage as a target for a secondary regression model that predicts optimal entry offset.
- Use reinforcement‑learning (RL) style reward shaping: penalize high slippage.

### 2.4 Dynamic Stop‑Loss Calibration
- Implement a **SL‑distance predictor** that takes recent trade outcomes, volatility regime, and position size as inputs.
- Update SL distance per‑trade using an exponential moving average of realized loss magnitude.
- Optionally, train a classifier to decide between **fixed‑ratio** vs **ATR‑based** SL.

### 2.5 Feature Completion & Engineering
- Audit the 39 features: identify why 26 are zero (e.g., missing data, incorrect preprocessing).
- Introduce **order‑book depth** metrics, **sentiment scores**, **funding rate**, **open‑interest**, and **macro‑economic indicators** (e.g., USD index).
- Apply **feature imputation** (median or model‑based) for sparse columns.
- Normalize all numeric features using robust scaling (median & IQR).

---

## 3. Implementation Roadmap
1. **Data Pipeline Extension**
   - Update `alpha_engine/data_ingestion.py` to compute time‑of‑day, volatility regime, and new market‑microstructure metrics.
   - Store additional columns in the feature store (`features.parquet`).
2. **Feature Engineering Module**
   - Create `alpha_engine/feature_engineering.py` with functions:
     - `add_time_features(df)`
     - `add_vol_regime(df)`
     - `add_slippage_target(df)`
     - `add_dynamic_sl(df(df,
n. **Model Retraining**
   - Extend training script (`alpha_engine/train_model.py`) to include new features and a multi‑task loss (prediction + slippage).
   - Use **XGBoost** or **LightGBM** with categorical handling for hour/day embeddings.
   - Perform hyper‑parameter search focusing on `max_depth`, `learning_rate`, and `reg_alpha`.
4. **Evaluation Framework**
   - Add back‑testing scenarios in `alpha_engine/backtest_v2.py` that compare:
     - Baseline vs. enhanced model.
     - Metrics: Sharpe, max‑drawdown, win‑rate, average slippage, SL hit‑rate.
   - Visualize regime‑specific performance.
5. **Deployment & Monitoring**
   - Update the inference service (`alpha_engine/api.py`) to compute real‑time regime and time‑of‑day features.
   - Add health‑checks for feature completeness (alert if >5% of rows have zeroed new features).
   - Log SL distance predictions for post‑trade analysis.
6. **Documentation & Knowledge Transfer**
   - Write a **README** (`docs/ml_enhancement_plan.md`) summarizing changes.
   - Add inline code comments and type hints.
   - Conduct a short walkthrough with the team.

---

## 4. Timeline (2‑Week Sprint)
| Day | Milestone |
|-----|-----------|
| **1** | Extend data pipeline; compute time‑of‑day & volatility regime.
| **2** | Implement new feature engineering functions; unit‑test.
| **3** | Audit existing features; fix zero‑value issues.
| **4** | Add slippage target and dynamic SL predictors.
| **5** | Retrain baseline model with new features; baseline comparison.
| **6** | Hyper‑parameter tuning; select best model.
| **7** | Back‑test across regimes; generate performance report.
| **8** | Update inference API; add real‑time feature computation.
| **9** | Deploy to staging; monitor feature completeness.
| **10** | Final review, documentation, and hand‑off.

---

## 5. Success Criteria
- **Feature Utilization**: > 90% of engineered features have non‑zero variance.
- **Performance Gains**: ≥ 15% increase in Sharpe ratio on out‑of‑sample data.
- **Slippage Reduction**: Average entry slippage ↓ 20%.
- **Dynamic SL**: Stop‑loss hit‑rate aligns with target risk level (e.g., 1‑2% per trade).
- **Regime Awareness**: Model exhibits distinct behavior in low vs. high volatility periods (validated via per‑regime metrics).

---

## 6. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Data leakage from future regime labels | Compute regime using only past data windows; enforce strict temporal ordering. |
| Over‑fitting to time‑of‑day patterns | Use cross‑validation that respects time series (e.g., rolling windows). |
| Increased latency from additional features | Profile feature computation; cache rolling volatility; pre‑compute hour embeddings. |
| Sparse new features (e.g., sentiment) | Apply fallback defaults; monitor feature presence in production. |

---

## 7. Next Steps
- Assign owners for each module (data, feature engineering, model, deployment).
- Set up a dedicated branch `ml‑enhancement‑plan`.
- Begin implementation according to the timeline.

---

*Prepared by Kilo Code — leveraging the **Content Research Writer** skill to produce a structured, actionable plan.*

---

[ml_enhancement_plan.md](ml_enhancement_plan.md)