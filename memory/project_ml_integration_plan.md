# Project ML Integration Plan (Extended)

## Overview
This document expands on the high‑level enhancement plan for the machine‑learning/crypto prediction pipeline. It outlines concrete implementation steps, responsible agents, timelines, and deliverables for each of the six phases.

---
## Phase 1 – Feature Truth

### 1.1 Feature Audit & Repair (Agent 1)
- **Goal**: Reduce dead/constant features from 19‑25 to < 5.
- **Tasks**:
  1. Run `audit_all_prove_winners.py` to generate `feature_audit_report.json`.
  2. Identify features with variance < 0.001 or > 99 % missing values.
  3. Update `alpha_engine/feature_defs.py` to remove or replace these features.
- **Deliverable**: Updated `feature_defs.py` and `feature_audit_report.json`.

### 1.2 Feature Contract & Health Gate (Agent 4)
- **File**: `alpha_engine/feature_contract.json`
- **Schema**:
  ```json
  {
    "feature_name": "string",
    "type": "numeric|categorical",
    "last_updated": "ISO8601",
    "status": "live|dead|stale"
  }
  ```
- **Gate Logic** (in `alpha_engine/forward_validator.py`):
  - Load contract at start.
  - Count `status == "dead"`.
  - If > 50 % dead, abort training and log to `feature_health_report.json`.

### 1.3 Dynamic Feature Registry
- **File**: `alpha_engine/features_schema.json`
- **Auto‑generation**: Add a script `alpha_engine/generate_feature_schema.py` that scans `feature_defs.py` and writes the JSON.
- **Integration**: `forward_validator.py` validates incoming feature payloads against the schema.

---
## Phase 2 – Time‑of‑Day

### 2.1 Temporal Feature Engineering
- Add the following to `alpha_engine/time_features.py`:
  - `hour_of_day = price_timestamp.hour`
  - `is_session_start = hour_of_day in [0, 8, 16]`
  - `is_session_end = hour_of_day in [7, 15, 23]`
  - `session_duration = (price_timestamp - session_start_timestamp).total_seconds() / 3600`
- Update the feature list in `feature_defs.py` to include these.

### 2.2 Seasonality Model
- Train a lightweight XGBoost (`seasonality_model.pkl`) on the temporal bins (0‑4 h, 4‑8 h, 8‑12 h, 12‑16 h, 16‑20 h, 20‑24 h).
- Output probability `seasonality_score` (0‑1) and add it as a feature.

---
## Phase 3 – Volatility Regime

### 3.1 Regime Classification
- Compute rolling volatility (`vol_1h`, `vol_4h`) in `alpha_engine/volatility_features.py`.
- Use K‑means (k=3) to label regimes: `low`, `medium`, `high`.
- Store mapping in `regime_lookup.pkl`.

### 3.2 Regime‑Specific Feature Weights
- Create `alpha_engine/regime_weights.py` that learns a linear weight vector `w_regime` for each regime using a small regression on the existing 39 features.
- Multiply each base feature by its regime weight before feeding to the main ranker.

### 3.3 Health Gate Extension
- Extend the health‑gate check to flag features that become constant *within* a regime.
- Log to `regime_feature_health.json`.

---
## Phase 4 – Entry Timing

### 4.1 Pre‑Entry Scoring Layer
- New file `alpha_engine/entry_timing_scoring.py`.
- Inputs: `elite_score`, `regime`, `hour_of_day`, `seasonality_score`.
- Model: LightGBM (`entry_quality_model.pkl`) trained on past entry outcomes.
- Output: `entry_quality` (0‑1).

### 4.2 Dynamic Threshold
- Compute rolling 30‑day 75th percentile of `entry_quality`.
- In `forward_validator.py`, only emit signals with `entry_quality >= threshold`.

### 4.3 Regime‑Interaction Matrix
- Store historical win‑rate per `(regime, signal_type)` in `regime_interactions.csv`.
- Adjust `entry_quality` by multiplying with the matrix value.

---
## Phase 5 – Stop‑Loss Calibration

### 5.1 Extend Adaptive SL Engine
- Modify `sl_calibrator.py` to accept `entry_quality` as an additional dimension.
- Update lookup table to `sl_calibration_grid.pkl` (dimensions: `symbol_family`, `strategy_type`, `vol_regime`, `entry_quality_bin`).

### 5.2 Safety Buffer
- In `forward_validator.py`, enforce a minimum SL of `0.5 * ATR_1h`.

---
## Phase 6 – Continuous Learning

### 6.1 Feature Health Monitoring
- Daily job `alpha_engine/feature_health_report.py` writes `feature_health_report.json` with:
  - dead‑feature count
  - variance stats
  - stale‑data flags

### 6.2 Auto‑Retraining Trigger
- GitHub Action `retrain_on_health.yml` reads the health report; if dead‑feature % > 30 % or variance drop > 20 %, triggers a full retraining workflow.

### 6.3 Model Drift Detection
- Weekly script `alpha_engine/detect_drift.py` computes KL‑divergence between current and previous feature importance distributions.
- If > 0.2, post a Slack alert and schedule a rebuild.

---
## Infrastructure & Ops

- **Docker**: Add `Dockerfile` at repo root to containerize the pipeline.
- **Monitoring Dashboard**: Extend `alpha_engine/grade_dashboard.html` with:
  - Feature health gauges (green/yellow/red).
  - Regime win‑rate heatmap.
  - SL calibration MAE/MFE chart.
- **Alerting**: Configure Slack webhook (`SLACK_WEBHOOK_URL` in secrets) for:
  - Gate blocks > 20 % of signals.
  - Feature health gate aborts training.

---
## Quick‑Start Timeline (Next 48 h)
1. **Add temporal features** – 2 h (Agent 1).
2. **Create feature_contract.json** and integrate health‑gate – 3 h (Agent 4).
3. **Implement entry_timing_scoring.py** – 4 h (Agent 5).
4. **Wire entry_quality into sl_calibrator.py** – 2 h.
5. **Set up daily health report & Slack alerts** – 3 h.
6. **Run end‑to‑end test on BNB** – 2 h.

---
## Ownership & Review
- **Feature Truth**: Agent 1 (owner: `dev_feature.py`)
- **Time‑of‑Day**: Agent 1 (owner: `dev_time.py`)
- **Vol Regime**: Agent 5 (owner: `dev_vol.py`)
- **Entry Timing**: Agent 5 (owner: `dev_entry.py`)
- **SL Calibration**: Agent 2 (owner: `dev_sl.py`)
- **Continuous Learning**: Agent 4 (owner: `dev_continuous.py`)

---
*End of Document*
