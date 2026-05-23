# ML Systems Revival: Online Learning & Feedback Loops

**Date:** 2026-03-07
**Status:** Approved
**Scope:** ML Battleground A-F, Mercury2, ml_crypto_predictor (1,745 models)
**Approach:** Full Rebuild with Online Learning (Approach C)

## Problem Statement

Three ML systems are functionally dead despite running workflows:

| System | State | Root Cause |
|--------|-------|------------|
| ML Battleground A-F | A: 10% WR; B/C/D/E: 0 picks | Overly strict thresholds, no feedback loops, models never retrain on forward data |
| Mercury2 | 0% WR, degraded mode since Feb 27 | Validation failed (DSR=0, PSR=0), no walk-forward CV, `DAILY_MA_PERIOD` missing |
| ml_crypto_predictor | 1,745 models, 0 forward tests | `live_picks_tracker.py` never called by any workflow |

**Core architectural flaw:** No system learns from its own mistakes. Models train once on historical data and degrade silently as market conditions change.

---

## Section 1: Critical Bug Fixes (COMPLETED by Kilo Code)

- [x] Fixed `features_df` NameError in `ml_crypto_predictor/enhanced_models/live_picks_tracker.py:286`
- [x] Added `DAILY_MA_PERIOD = 200` to `mercury2/config.py`
- [x] Updated `ml_battleground/system_c_deeplearn/models/arch_config.json` to match actual training config
- [x] Wired `live_picks_tracker.py` into `enhanced-ml-crypto.yml` workflow

---

## Section 2: Training Quality Improvements

### 2A: Fix Label/TP Mismatch (CRITICAL — Train-Serve Skew)

**Problem:** Training labels use fixed % thresholds but live TP uses ATR-based targets. This causes:
- Low-vol pairs: ATR-TP triggers at 0.8% but model trained on +1.5% label — model misses valid signals
- High-vol pairs: ATR-TP at 6% but model trained on +1.5% — model overpredicts

**Fix:** Unify labels to ATR-based across all systems:
- Label = "did price reach `TP_ATR_MULT x ATR(14)` within `MAX_HORIZON` bars?"
- Apply to: Battleground A (2.5x ATR), B (regime-specific ATR mults), C (2.0x ATR), Mercury2 (convert from 4h fixed horizon), ml_crypto_predictor (convert from fixed % to ATR-based)

**Files affected:**
- `ml_battleground/system_a_filter/train_filter.py` — label generation
- `ml_battleground/system_b_regime/train_regime.py` — label generation
- `ml_battleground/system_c_deeplearn/train_model.py` — label generation
- `mercury2/trainer.py` — label generation
- `ml_crypto_predictor/enhanced_models/model_trainer.py` — label generation

### 2B: Candle-Close Gate (Scan Interval Fix)

**Problem:** 30-min GitHub Actions schedule against 1h/4h candles scans mid-candle with incomplete data, generating duplicate picks.

**Fix:** Gate inference on candle close:
```python
if latest_candle_close_time > last_scan_time:
    run_inference()
```

**Files affected:** All scanner.py files (Battleground A-F, Mercury2, ml_crypto_predictor)

### 2C: Mercury2 Walk-Forward CV

**Problem:** Mercury2 uses simple 80/20 train/test split — allows look-ahead bias.

**Fix:** Replace with 5-fold `TimeSeriesSplit` with 20-bar purge gap (matching Battleground A/B pattern).

**Files affected:** `mercury2/trainer.py`

### 2D: Class Balancing

**Problem:** Positive class (TP hit) is rare (2-20%). Models are biased toward predicting "no signal."

**Fix by model type:**
- XGBoost (A, B, Mercury2): `scale_pos_weight` from actual class ratios + SMOTE on minority
- GRU-Attention (C): Focal loss (downweight easy negatives) instead of standard BCE
- RandomForest (ml_crypto_predictor): Already uses `class_weight='balanced_subsample'` — keep

**Files affected:** `train_filter.py`, `train_regime.py`, `train_model.py`, `mercury2/trainer.py`

### 2E: Hard Validation Gates

**Problem:** DSR/PSR checks are logged but not enforced — bad models deploy freely.

**Fix:**
- Models saved as `model_candidate.joblib`
- If DSR >= 0.5 AND PSR >= 0.5: promote to `model.joblib`
- If validation fails: keep previous model, log failure
- If previous model also fails: enter conservative mode (higher confidence thresholds, fewer concurrent picks)

**Files affected:** All trainer scripts, all scanner scripts (for conservative mode fallback)

### 2F: Fear & Greed as Regime Filter

**Problem:** F&G is identical across all 20 pairs per scan — can't discriminate between pairs, only acts as global bias.

**Fix:**
- Use F&G as pre-screen regime filter: skip scanning entirely if F&G < 10 (extreme fear) or BTC drops >5% in 4h
- Keep F&G in feature set but acknowledge it's a global bias term
- Remove F&G momentum/average features (they add noise, not signal)

**Files affected:** All scanner.py files

### 2G: Drift Window Fix

**Problem:** Rolling 20-pick precision at 40% threshold is statistically fragile — a true 55% WR strategy will randomly dip below 40% ~10% of the time.

**Fix:** Replace hard threshold with binomial test:
```python
from scipy.stats import binom_test
p_value = binom_test(n_losses, n_picks, 1 - training_baseline_wr)
if p_value < 0.05:
    trigger_degradation()
```
This adapts to sample size automatically — no arbitrary window size needed.

**Files affected:** `ml_battleground/shared/feedback_loop.py`, `mercury2/scanner.py`

---

## Section 3: Feedback Loops & Online Learning (PARTIALLY COMPLETED)

### 3A: Performance-Triggered Retraining (COMPLETED — `feedback_loop.py`)

Core module implemented. Refinements needed per Antigravity feedback:

**Fix 1: Consecutive loss threshold**
- Current: 5 consecutive losses triggers retrain
- Problem: (0.4)^5 = 1.02% chance per window — will fire multiple times/month for a 60% WR system
- Fix: Raise to 8 consecutive losses (0.4^8 = 0.065%) OR replace with binomial test from 2G

**Fix 2: Minimum sample gate**
- Current: Evaluates degradation on any window size
- Problem: 15% WR drop in a 10-pick window is noise
- Fix: Only evaluate degradation triggers when window has >= 30 closed picks. Below that, rely on drift detection (3B) only.

**Priority hierarchy:**
1. 3B (drift detection on residuals) = primary early-warning → triggers retrain
2. 3A (hard thresholds) = emergency circuit breaker → triggers retrain + conservative mode

**Files affected:** `ml_battleground/shared/feedback_loop.py`

### 3B: Concept Drift Detection

**Method:** ADWIN from `river` library on **prediction residuals** (predicted probability - actual outcome), NOT raw features.

**Why residuals, not features:** Crypto features (RSI, funding, volume) are inherently non-stationary — ADWIN on raw features fires constantly (noise). ADWIN on residuals detects when the model's accuracy genuinely degrades, which is actionable drift.

**Retrain cooldown:** 24-hour minimum between retrains. If ADWIN fires within 24h of a retrain, log event but don't retrain again. Prevents encoding flash-crash anomalies as the new normal.

**Implementation:**
```python
from river.drift import ADWIN

class DriftMonitor:
    def __init__(self, system_name, cooldown_hours=24):
        self.detector = ADWIN(delta=0.002)
        self.last_retrain = None
        self.cooldown = timedelta(hours=cooldown_hours)

    def update(self, predicted_prob, actual_outcome):
        residual = predicted_prob - actual_outcome
        self.detector.update(residual)
        if self.detector.drift_detected:
            if self.last_retrain and (now - self.last_retrain) < self.cooldown:
                log("Drift detected but within cooldown — suppressed")
                return False
            return True  # trigger retrain
        return False
```

**New file:** `ml_battleground/shared/drift_monitor.py`

### 3C: Incremental/Warm-Start Learning

| Model | Method | Gotcha | Mitigation |
|-------|--------|--------|------------|
| XGBoost | `xgb_model=existing` | Adds trees monotonically — model bloats | Cap at 500 trees total; prune oldest when exceeded |
| LightGBM | `init_model` | Clean, works as expected | None needed |
| RandomForest | `warm_start=True` | Only works if `n_estimators` is manually incremented first | Auto-increment by 50 before each warm fit; cap at 600 total |
| GRU-Attention | Fine-tune at lr/10 | Catastrophic forgetting | Limit to 3-5 epochs; freeze GRU layers, fine-tune attention + dense only; train on 70% historical + 30% new data mix |

**Monthly full retrain:** Schedule a complete retrain from scratch using rolling 6-12 month window. Prevents unbounded model growth and purges stale patterns.

**Files affected:** All trainer scripts + new `ml-monthly-retrain.yml` workflow

### 3D: Exposure Concentration Guard (reframed from "Correlation Guard")

**Reframing:** This is portfolio-level risk management, not a feedback loop. Moved conceptually to risk module.

**Key insight from Antigravity:** If 3+ systems agree on same direction, that's actually strong consensus — blocking it is counterproductive.

**Reframed logic:**
- Track total USD exposure per correlated cluster (returns correlation > 0.7 over 30 days)
- If cluster exposure exceeds 6% of portfolio → reduce position sizing on new picks in that cluster by 50%
- During BTC-driven selloffs (r > 0.7 on all alts), suspend the guard entirely — let contrarian systems operate

**New module:** `ml_battleground/shared/exposure_guard.py` (separate from feedback_loop.py)

### 3E: Forward-Test -> Training Data Pipeline (Crown Jewel)

Every forward-test pick must persist the **full feature vector at entry time**:

```python
pick_record = {
    "symbol": "ETHUSDT",
    "direction": "LONG",
    "confidence": 0.73,
    "entry_price": 3450.2,
    "tp": 3550.0,
    "sl": 3380.0,
    "features": {feature_name: value for all N features},  # CRITICAL
    "timestamp": "2026-03-06T23:00:00Z",
    "outcome": null  # filled when TP/SL/expiry hit
}
```

**Why full feature persistence is non-negotiable:** Re-fetching historical klines at retrain time may produce different candle boundaries, resampling artifacts, or missing data. The feature snapshot captured live is the ground truth.

On each retrain cycle:
1. Load all closed forward-test picks with features + outcomes
2. Construct labeled rows: features -> label (1 if TP hit, 0 if SL/expiry)
3. Append to training set (within rolling 6-12 month window)
4. Retrain with warm-start

**Files affected:** All scanner.py files (to persist features), all trainer scripts (to consume forward data)

### 3F: Ensemble Calibration

For ml_crypto_predictor's 4-variant ensemble:
- Apply Platt scaling (sigmoid calibration) on each variant's output probabilities
- Combine calibrated probabilities via weighted average (weights from A/B test composite scores)
- Tree ensembles are often poorly calibrated — this fixes probability outputs

**Files affected:** `ml_crypto_predictor/enhanced_models/model_trainer.py`, `live_predictor.py`

### 3G: Shadow/A-B Testing for Model Deployment (NEW — from Antigravity feedback)

**Problem:** Hard-swapping models after validation may still fail live.

**Fix:** When a new model passes validation gates:
1. Run both old and new models in parallel for 30 picks (shadow mode)
2. New model's picks are logged but not acted on
3. After 30 picks, compare: if new model WR >= old model WR - 5% AND Sharpe >= old Sharpe, swap
4. Otherwise, keep old model and log the failure

**Files affected:** All scanner.py files (dual-model inference path)

### 3H: Auto-Rollback (NEW — from Antigravity feedback)

If a newly deployed model underperforms the old one after 30 live picks:
- Auto-revert to previous model version (kept as `model_previous.joblib`)
- Log rollback event with metrics comparison
- Trigger retrain with extended data

**Files affected:** All scanner.py files, all trainer scripts (model versioning)

### 3I: Training Data Recency Window (NEW — from Antigravity feedback)

**Problem:** Without a cap, training data grows forever. Market dynamics from 2024 may be noise for 2026.

**Fix:** Rolling 6-month window for warm-start retrains. Monthly full retrain uses 12-month window. Data older than 12 months is archived but not used in training.

**Files affected:** All trainer scripts

---

## Section 4: Audit Dashboard Integration

### 4A: Mercury2 Registration

Add to `JSON_PICK_SOURCES` in `audit_trail/dashboard_generator.py`:
```python
("mercury2", "mercury2/data/active_picks.json", "mercury2/data/closed_picks.json"),
```

Add to `sysLinksMap` in `audit_dashboard/index.html`:
```javascript
'mercury2': 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/mercury2/',
```

### 4B: System Health Badges

Add `health` field to each system's `scan_summary.json`:
- `"healthy"` (green) — validation passed, picks flowing
- `"degraded"` (yellow) — validation failed, running in conservative mode
- `"retraining"` (orange) — model being retrained
- `"offline"` (red) — system not running

Dashboard renders as colored status badges on each system card.

### 4C: Forward-Test Metrics on Audit Page

New columns in Systems tab:
- Forward WR, Forward Sharpe, Forward PnL
- BT vs Forward decay % (highlights overfitting)
- Model age (days since last retrain)
- Drift status (from ADWIN monitor)

---

## Section 5: Workflow Architecture

### Modified Workflows

| Workflow | Current | Proposed Change |
|----------|---------|-----------------|
| `ml-battleground-bootstrap.yml` | Manual trigger only | Weekly Sunday 03:00 UTC + performance-triggered via `retrain_trigger.json` |
| `mercury2-retrain.yml` | Weekly Sunday 02:00 UTC | Keep schedule + add drift-triggered path |
| `enhanced-ml-crypto.yml` | Daily train, 4h predict | Daily train, 4h predict + 30min tracker (DONE by Kilo Code) |
| `ml-battleground-a.yml` through `e.yml` | Every 15-30 min | Add candle-close gate + feature persistence |
| `audit-dashboard.yml` | Periodic | Add health badge + forward metrics to payload |

### New Workflows

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `ml-feedback-loop.yml` | Every 6h | Check performance metrics, detect drift, write retrain_trigger.json |
| `ml-monthly-retrain.yml` | 1st of month 04:00 UTC | Full retrain from scratch with 12-month rolling window |

### New Files

| File | Purpose |
|------|---------|
| `ml_battleground/shared/drift_monitor.py` | ADWIN-based concept drift detection on prediction residuals |
| `ml_battleground/shared/exposure_guard.py` | Portfolio-level correlated exposure concentration limits |
| `ml_battleground/shared/model_versioning.py` | Shadow testing, auto-rollback, candidate/production model management |

---

## Implementation Priority

### Phase 1: Make Models Learn (highest value)
1. Fix label/TP mismatch (2A) — all trainers
2. Wire forward-test -> training pipeline with feature persistence (3E)
3. Fix feedback_loop.py thresholds (3A fixes)
4. Add candle-close gate (2B)

### Phase 2: Improve Training Quality
5. Mercury2 walk-forward CV (2C)
6. Class balancing (2D)
7. Hard validation gates (2E)
8. Drift window fix with binomial test (2G)

### Phase 3: Online Learning Infrastructure
9. Drift monitor with ADWIN on residuals (3B)
10. Incremental warm-start learning with model size caps (3C)
11. Shadow/A-B testing for model deployment (3G)
12. Auto-rollback (3H)

### Phase 4: Dashboard & Risk
13. Audit dashboard integration (4A-4C)
14. Exposure concentration guard (3D)
15. Ensemble calibration (3F)
16. Monthly full retrain workflow (3C)

### Phase 5: Workflow Wiring
17. New workflows (ml-feedback-loop.yml, ml-monthly-retrain.yml)
18. Modified workflow schedules
19. F&G regime filter (2F)
20. Training data recency window (3I)

---

## Dependencies

- `river` library (for ADWIN drift detection) — add to requirements.txt
- `scipy` (for binomial test) — already available
- `imbalanced-learn` (for SMOTE) — add to requirements.txt

## Success Criteria

After implementation:
- All 8 systems (Battleground A-F + Mercury2 + ml_crypto_predictor) generating forward-test picks
- Models retrain automatically when performance degrades
- Forward-test outcomes feed back into training data
- Audit dashboard shows all systems with health badges and forward metrics
- No model runs longer than 30 days without retraining
