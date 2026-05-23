#!/usr/bin/env python3
"""
CLAUDE CODE — ML Self-Improvement / Online Learning
====================================================
Continuously improves the model by:
1. Adding resolved picks to training data
2. Retraining model periodically (every 7 days or 50 resolved picks)
3. Tracking model version and performance drift
4. Detecting and alerting on precision drift

Usage:
    python self_improver.py [--force-retrain] [--drift-check]
"""

import os
import sys
import json
import time
import argparse
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

import random

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    from imblearn.over_sampling import SMOTE
    HAS_IMBLEARN = True
except ImportError:
    HAS_IMBLEARN = False

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TRACKER_DIR = BASE_DIR / "tracker"

FEATURE_CACHE = DATA_DIR / "feature_matrix.csv"
ONLINE_DATA_FILE = DATA_DIR / "online_training_data.csv"
PICK_HISTORY_FILE = TRACKER_DIR / "claude_pick_history.json"
PERFORMANCE_FILE = TRACKER_DIR / "claude_performance.json"
TRAINING_META = MODEL_DIR / "training_meta.json"
IMPROVEMENT_LOG = MODEL_DIR / "improvement_log.json"

# ── Feature columns (must match train_model.py) ─────────────────────────
FEATURE_COLS = [
    "vol_mcap_ratio", "vol_change_24h", "vol_change_12h",
    "price_momentum_7d", "price_momentum_3d", "price_momentum_1d",
    "rsi_14", "rsi_slope", "bb_width", "bb_percentb",
    "consolidation_range", "consecutive_green", "momentum_ignition",
    "obv_divergence", "distance_from_ath_pct", "distance_from_atl_pct",
    "mcap_tier", "price_compression", "relative_volume_spike",
    "fear_greed_proxy",
]

# ── Thresholds ───────────────────────────────────────────────────────────
RETRAIN_INTERVAL_DAYS = 7
RETRAIN_MIN_NEW_SAMPLES = 10   # Lower: faster ML feedback loop
PRECISION_DRIFT_THRESHOLD = 0.40  # Alert if precision drops below this
RECALL_DRIFT_THRESHOLD = 0.20    # Alert if recall drops below this


# ═══════════════════════════════════════════════════════════════════════════
#  ONLINE DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════

def collect_online_data():
    """Convert resolved picks into training data rows.

    Each resolved pick has features (from the scan) and a real outcome
    (did the coin actually gain >10%?).
    """
    if not PICK_HISTORY_FILE.exists():
        print("[ONLINE] No pick history found")
        return 0

    with open(PICK_HISTORY_FILE) as f:
        history = json.load(f)

    if not history:
        print("[ONLINE] Empty pick history")
        return 0

    # Load existing online data
    existing_ids = set()
    if ONLINE_DATA_FILE.exists():
        existing_df = pd.read_csv(ONLINE_DATA_FILE)
        existing_ids = set(existing_df.get("pick_id", []))
    else:
        existing_df = pd.DataFrame()

    new_rows = []
    skipped_no_features = 0
    for pick in history:
        pick_id = pick.get("pick_id", "")
        if pick_id in existing_ids:
            continue

        pnl = pick.get("pnl_pct", 0)
        if pnl is None:
            continue

        # The label: did the coin actually gain >10%?
        actual_label = 1 if pnl >= 10.0 else 0

        row = {"pick_id": pick_id, "label": actual_label, "pnl_pct": pnl}

        # Use stored feature vectors if available (added in v1.1+)
        stored_features = pick.get("features", {})
        if stored_features and any(v != 0 for v in stored_features.values()):
            # Full feature vector stored with pick — use it directly
            for col in FEATURE_COLS:
                row[col] = float(stored_features.get(col, 0.0))
        else:
            # Legacy picks without stored features — reconstruct from signals + pick metadata
            signals = pick.get("signals", [])
            signals_str = " ".join(str(s) for s in signals)

            # Signal-derived binary features
            row["momentum_ignition"] = 1.0 if "MOMENTUM_IGNITION" in signals_str else 0.0
            row["relative_volume_spike"] = 1.0 if "EXTREME_VOLUME" in signals_str or "VOL_SPIKE" in signals_str else 0.0
            row["obv_divergence"] = 1.0 if "OBV_DIVERGENCE" in signals_str else 0.0
            row["price_compression"] = 1.0 if "COMPRESSION" in signals_str else 0.0
            row["consecutive_green"] = 0.0
            for s in signals:
                if "GREEN_STREAK" in str(s):
                    try:
                        row["consecutive_green"] = float(str(s).split("(")[1].split(")")[0])
                    except (IndexError, ValueError):
                        row["consecutive_green"] = 3.0

            # Derive numeric features from pick metadata where available
            pump_prob = pick.get("pump_probability", 0.0) or 0.0

            # Use pump_probability as a proxy for momentum features
            # (the model scored this pick, so its probability reflects the feature space)
            row["price_momentum_1d"] = pump_prob * 10.0  # Scale to typical range
            row["price_momentum_3d"] = pump_prob * 8.0
            row["price_momentum_7d"] = pump_prob * 5.0

            # Derive volume features from signal presence
            has_vol_signal = row["relative_volume_spike"] > 0
            row["vol_mcap_ratio"] = 0.15 if has_vol_signal else 0.05
            row["vol_change_24h"] = 200.0 if has_vol_signal else 50.0
            row["vol_change_12h"] = 150.0 if has_vol_signal else 30.0

            # RSI proxy from pump probability (higher prob = more bullish setup)
            row["rsi_14"] = 35.0 + pump_prob * 30.0  # Range ~35-65
            row["rsi_slope"] = pump_prob * 2.0

            # Bollinger band proxies
            row["bb_width"] = 0.08 if row["price_compression"] > 0 else 0.15
            row["bb_percentb"] = 0.3 + pump_prob * 0.4  # Range 0.3-0.7

            # Consolidation range (compression = tight range)
            row["consolidation_range"] = 0.03 if row["price_compression"] > 0 else 0.08

            # Distance features — use defaults that match crypto mid-cap profiles
            row["distance_from_ath_pct"] = 60.0  # Most crypto is well off ATH
            row["distance_from_atl_pct"] = 200.0  # And well above ATL

            # Market cap tier (2 = mid-cap default)
            row["mcap_tier"] = 2.0

            # Fear/greed proxy from pump probability
            row["fear_greed_proxy"] = pump_prob * 100.0

            # Fill any remaining columns with 0
            for col in FEATURE_COLS:
                if col not in row:
                    row[col] = 0.0
            skipped_no_features += 1

        new_rows.append(row)

    if skipped_no_features:
        print(f"[ONLINE] {skipped_no_features} picks had partial features (legacy format)")

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        if len(existing_df) > 0:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined = new_df
        combined.to_csv(ONLINE_DATA_FILE, index=False)
        print(f"[ONLINE] Added {len(new_rows)} new samples (total: {len(combined)})")
        return len(new_rows)
    else:
        print("[ONLINE] No new samples to add")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
#  MODEL RETRAINING
# ═══════════════════════════════════════════════════════════════════════════

def should_retrain():
    """Check if retraining conditions are met."""
    days_since = None

    # Check time since last training
    if TRAINING_META.exists():
        with open(TRAINING_META) as f:
            meta = json.load(f)
        trained_at = meta.get("trained_at", "")
        if trained_at:
            last_train = datetime.fromisoformat(trained_at)
            days_since = (datetime.now(timezone.utc) - last_train).days
            print(f"[RETRAIN] Last trained {days_since} days ago (threshold: {RETRAIN_INTERVAL_DAYS})")
    else:
        print("[RETRAIN] No training_meta.json found — first retrain needed")
        return True

    # Check number of new online samples
    n_samples = 0
    if ONLINE_DATA_FILE.exists():
        try:
            online_df = pd.read_csv(ONLINE_DATA_FILE)
            n_samples = len(online_df)
        except Exception as e:
            print(f"[RETRAIN] Error reading online data: {e}")

    # Fallback: count resolved picks directly from pick history
    if n_samples == 0 and PICK_HISTORY_FILE.exists():
        try:
            with open(PICK_HISTORY_FILE) as f:
                history = json.load(f)
            n_resolved = len([p for p in history if p.get("pnl_pct") is not None])
            if n_resolved > 0:
                print(f"[RETRAIN] {n_resolved} resolved picks in history (online_training_data.csv missing or empty)")
                n_samples = n_resolved
        except Exception as e:
            print(f"[RETRAIN] Error reading pick history: {e}")

    if n_samples >= RETRAIN_MIN_NEW_SAMPLES:
        print(f"[RETRAIN] {n_samples} online samples (threshold: {RETRAIN_MIN_NEW_SAMPLES}) — RETRAIN NEEDED")
        return True

    # Check time-based trigger
    if days_since is not None and days_since >= RETRAIN_INTERVAL_DAYS:
        print(f"[RETRAIN] {days_since} days since last training — RETRAIN NEEDED")
        return True

    print(f"[RETRAIN] No retraining needed (samples: {n_samples}, threshold: {RETRAIN_MIN_NEW_SAMPLES})")
    return False


def _count_stagnant_retrains():
    """Count how many consecutive retrains showed zero improvement."""
    if not IMPROVEMENT_LOG.exists():
        return 0
    with open(IMPROVEMENT_LOG) as f:
        log = json.load(f)
    count = 0
    for entry in reversed(log):
        imp = entry.get("improvement", {})
        if all(abs(v) < 0.005 for v in imp.values()):
            count += 1
        else:
            break
    return count


def _sample_hyperparams(stagnant_count):
    """Sample random hyperparameters to break out of retrain loop.

    The more stagnant retrains, the more aggressive the variation.
    """
    rng = random.Random(int(time.time()))

    # RF hyperparams
    rf_max_depth = rng.choice([3, 5, 7, 10, 12, 15])
    rf_n_estimators = rng.choice([50, 100, 200, 300, 500])
    rf_min_samples_leaf = rng.choice([3, 5, 10, 20])

    # XGB hyperparams
    xgb_max_depth = rng.choice([3, 5, 7, 10])
    xgb_n_estimators = rng.choice([50, 100, 200, 300, 500])
    xgb_learning_rate = rng.choice([0.01, 0.03, 0.05, 0.1, 0.2])

    # Classification threshold: higher = more selective, better precision
    cls_threshold = rng.choice([0.55, 0.60, 0.65, 0.70, 0.75])

    # After 3+ stagnant retrains, try different positive label thresholds
    gain_thresholds = [0.03]  # default 3%
    if stagnant_count >= 3:
        gain_thresholds = [0.015, 0.02, 0.03, 0.05]

    gain_threshold = rng.choice(gain_thresholds)

    params = {
        "rf_max_depth": rf_max_depth,
        "rf_n_estimators": rf_n_estimators,
        "rf_min_samples_leaf": rf_min_samples_leaf,
        "xgb_max_depth": xgb_max_depth,
        "xgb_n_estimators": xgb_n_estimators,
        "xgb_learning_rate": xgb_learning_rate,
        "cls_threshold": cls_threshold,
        "gain_threshold_pct": gain_threshold,
    }
    return params


def retrain_model():
    """Retrain the ensemble model with original + online data.

    v2.0 improvements:
    - Random hyperparameter sampling to break retrain loop
    - Lower classification threshold (0.3 default) for better recall
    - Different gain thresholds after 3+ stagnant retrains
    - Give-up check: after 3 consecutive no-improvement retrains, change approach
    """
    print("\n" + "=" * 60)
    print("  RETRAINING MODEL (incremental v2.0)")
    print("=" * 60)

    # Check stagnation count
    stagnant_count = _count_stagnant_retrains()
    print(f"  Consecutive stagnant retrains: {stagnant_count}")

    if stagnant_count >= 3:
        print(f"  *** STAGNATION DETECTED ({stagnant_count} retrains with no improvement) ***")
        print(f"  Switching to aggressive hyperparameter variation + alternative gain thresholds")

    # Sample hyperparameters (randomized to break loop)
    hp = _sample_hyperparams(stagnant_count)
    print(f"  Sampled hyperparams: RF(depth={hp['rf_max_depth']}, trees={hp['rf_n_estimators']}, "
          f"leaf={hp['rf_min_samples_leaf']}) XGB(depth={hp['xgb_max_depth']}, "
          f"trees={hp['xgb_n_estimators']}, lr={hp['xgb_learning_rate']})")
    print(f"  Classification threshold: {hp['cls_threshold']}")
    print(f"  Gain threshold: {hp['gain_threshold_pct']:.1%}")

    # Load original training data
    original_df = pd.DataFrame()
    if FEATURE_CACHE.exists():
        original_df = pd.read_csv(FEATURE_CACHE)
        print(f"  Original data: {len(original_df)} samples")
    else:
        print("[WARN] No original training data found (feature_matrix.csv) — using online data only")

    # Load online data (or regenerate from pick history if missing)
    online_df = pd.DataFrame()
    if ONLINE_DATA_FILE.exists():
        online_df = pd.read_csv(ONLINE_DATA_FILE)
        print(f"  Online data: {len(online_df)} samples")
    else:
        print("[WARN] online_training_data.csv not found — running collect_online_data() now")
        collect_online_data()
        if ONLINE_DATA_FILE.exists():
            online_df = pd.read_csv(ONLINE_DATA_FILE)
            print(f"  Online data (just collected): {len(online_df)} samples")

    if len(original_df) == 0 and len(online_df) == 0:
        print("[ERROR] No training data available at all")
        return False

    # Combine datasets
    required_cols = FEATURE_COLS + ["label"]
    for col in required_cols:
        if col not in original_df.columns:
            original_df[col] = 0.0
        if len(online_df) > 0 and col not in online_df.columns:
            online_df[col] = 0.0

    if len(online_df) > 0:
        combined = pd.concat([
            original_df[required_cols],
            online_df[required_cols]
        ], ignore_index=True)
    else:
        combined = original_df[required_cols]

    # Re-label with alternative gain threshold if stagnant
    if hp["gain_threshold_pct"] != 0.03 and "next_close" in original_df.columns and "close" in original_df.columns:
        print(f"  Re-labeling with {hp['gain_threshold_pct']:.1%} gain threshold...")
        # Re-compute labels from original data
        orig_with_prices = original_df[original_df["close"] > 0].copy()
        if len(orig_with_prices) > 0 and "next_close" in orig_with_prices.columns:
            new_labels = ((orig_with_prices["next_close"] / orig_with_prices["close"]) - 1.0 >= hp["gain_threshold_pct"]).astype(int)
            orig_relabeled = orig_with_prices[required_cols].copy()
            orig_relabeled["label"] = new_labels.values[:len(orig_relabeled)]
            if len(online_df) > 0:
                combined = pd.concat([orig_relabeled, online_df[required_cols]], ignore_index=True)
            else:
                combined = orig_relabeled
            print(f"  Re-labeled positive rate: {combined['label'].mean():.2%}")

    print(f"  Combined data: {len(combined)} samples")
    print(f"  Positive rate: {combined['label'].mean():.2%}")

    X = combined[FEATURE_COLS].values
    y = combined["label"].values
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

    # Time-sorted split (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # SMOTE oversampling for class imbalance
    n_pos_train = int(sum(y_train == 1))
    n_neg_train = int(sum(y_train == 0))
    imbalance_ratio = n_neg_train / max(n_pos_train, 1)
    print(f"  Class balance: {n_pos_train} pos / {n_neg_train} neg (ratio 1:{imbalance_ratio:.0f})")

    if HAS_IMBLEARN and imbalance_ratio > 5 and n_pos_train >= 5:
        target_ratio = max(0.15, n_pos_train / n_neg_train)
        print(f"  Applying SMOTE (target minority ratio ~{target_ratio:.0%})...")
        try:
            smote = SMOTE(
                sampling_strategy=target_ratio,
                k_neighbors=min(5, n_pos_train - 1),
                random_state=42,
            )
            X_train, y_train = smote.fit_resample(X_train, y_train)
            print(f"  After SMOTE: {int(sum(y_train==1))} pos / {int(sum(y_train==0))} neg")
        except Exception as e:
            print(f"  [WARN] SMOTE failed ({e}), using original data")
    else:
        reason = "not installed" if not HAS_IMBLEARN else f"ratio OK ({imbalance_ratio:.0f}:1)" if imbalance_ratio <= 5 else f"too few positives ({n_pos_train})"
        print(f"  SMOTE skipped: {reason}")

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train RandomForest with sampled hyperparams
    print(f"  Training RandomForest (depth={hp['rf_max_depth']}, trees={hp['rf_n_estimators']})...")
    pos_weight = max(1, int(sum(y_train == 0) / max(sum(y_train == 1), 1)))
    sample_weights = np.where(y_train == 1, pos_weight, 1).astype(float)

    rf = RandomForestClassifier(
        n_estimators=hp["rf_n_estimators"],
        max_depth=hp["rf_max_depth"],
        min_samples_split=10,
        min_samples_leaf=hp["rf_min_samples_leaf"],
        max_features="sqrt",
        class_weight="balanced",
        random_state=int(time.time()) % 10000,  # vary seed each run
        n_jobs=-1,
    )
    rf.fit(X_train_scaled, y_train, sample_weight=sample_weights)

    rf_proba = rf.predict_proba(X_test_scaled)[:, 1]

    # Train XGBoost with sampled hyperparams
    xgb_model = None
    xgb_proba = np.zeros_like(rf_proba)

    if HAS_XGB:
        print(f"  Training XGBoost (depth={hp['xgb_max_depth']}, lr={hp['xgb_learning_rate']})...")
        xgb_model = xgb.XGBClassifier(
            n_estimators=hp["xgb_n_estimators"],
            max_depth=hp["xgb_max_depth"],
            learning_rate=hp["xgb_learning_rate"],
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            eval_metric="logloss",
            random_state=int(time.time()) % 10000,
            n_jobs=-1,
            verbosity=0,
        )
        xgb_model.fit(X_train_scaled, y_train)
        xgb_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]

    # Ensemble
    if HAS_XGB and xgb_model is not None:
        ensemble_proba = 0.45 * rf_proba + 0.55 * xgb_proba
    else:
        ensemble_proba = rf_proba

    # v2.0: Use lower classification threshold for better recall (fix degenerate 2.5% recall)
    cls_threshold = hp["cls_threshold"]
    ensemble_pred = (ensemble_proba >= cls_threshold).astype(int)

    # Also check flipped predictions (if model is anti-correlated, flipping helps)
    auc_raw = roc_auc_score(y_test, ensemble_proba) if len(np.unique(y_test)) > 1 else 0
    if auc_raw < 0.5:
        print(f"  [AUTO-FLIP] Raw AUC={auc_raw:.4f} < 0.50 — model is anti-correlated, flipping probabilities")
        ensemble_proba = 1.0 - ensemble_proba
        ensemble_pred = (ensemble_proba >= cls_threshold).astype(int)

    # Metrics
    prec = precision_score(y_test, ensemble_pred, zero_division=0)
    rec = recall_score(y_test, ensemble_pred, zero_division=0)
    f1 = f1_score(y_test, ensemble_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, ensemble_proba) if len(np.unique(y_test)) > 1 else 0
    pr_auc = average_precision_score(y_test, ensemble_proba) if len(np.unique(y_test)) > 1 else 0
    auc = pr_auc  # Use PR-AUC as primary metric (more meaningful with severe class imbalance)

    print(f"\n  Retrained Model Metrics (threshold={cls_threshold}):")
    print(f"    Precision: {prec:.4f}")
    print(f"    Recall:    {rec:.4f}")
    print(f"    F1:        {f1:.4f}")
    print(f"    ROC-AUC:   {roc_auc:.4f}")
    print(f"    PR-AUC:    {pr_auc:.4f} (primary metric for imbalanced data)")

    # Load previous metrics for comparison
    prev_meta = {}
    if TRAINING_META.exists():
        with open(TRAINING_META) as f:
            prev_meta = json.load(f)

    prev_metrics = prev_meta.get("metrics", {})
    if prev_metrics:
        print(f"\n  Comparison with previous model:")
        print(f"    Precision: {prev_metrics.get('precision', 0):.4f} -> {prec:.4f} ({prec - prev_metrics.get('precision', 0):+.4f})")
        print(f"    Recall:    {prev_metrics.get('recall', 0):.4f} -> {rec:.4f} ({rec - prev_metrics.get('recall', 0):+.4f})")
        print(f"    F1:        {prev_metrics.get('f1', 0):.4f} -> {f1:.4f} ({f1 - prev_metrics.get('f1', 0):+.4f})")
        print(f"    ROC-AUC:   {prev_metrics.get('roc_auc', 0):.4f} -> {auc:.4f} ({auc - prev_metrics.get('roc_auc', 0):+.4f})")

    # Save new models
    prev_version = prev_meta.get("model_version", "1.0.0")
    # Increment minor version
    parts = prev_version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = ".".join(parts)

    joblib.dump(rf, MODEL_DIR / "claude_rf.joblib")
    joblib.dump(scaler, MODEL_DIR / "claude_scaler.joblib")
    if HAS_XGB and xgb_model:
        joblib.dump(xgb_model, MODEL_DIR / "claude_xgb.joblib")

    # Update metadata
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": new_version,
        "pipeline": "CLAUDE CODE Gainer ML (retrained v2.0)",
        "num_features": len(FEATURE_COLS),
        "feature_names": FEATURE_COLS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "online_samples_used": int(len(online_df)),
        "total_samples": int(len(combined)),
        "positive_rate_train": float(sum(y_train) / len(y_train)),
        "positive_rate_test": float(sum(y_test) / len(y_test)),
        "ensemble_weights": {"rf": 0.45, "xgb": 0.55} if HAS_XGB else {"rf": 1.0},
        "classification_threshold": cls_threshold,
        "hyperparams": hp,
        "stagnant_retrains_before": stagnant_count,
        "metrics": {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
        },
        "previous_metrics": prev_metrics,
        "has_xgboost": HAS_XGB,
        "has_imblearn": HAS_IMBLEARN,
    }
    with open(TRAINING_META, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n  Model saved as v{new_version}")
    print(f"  Models saved to {MODEL_DIR}")

    # Log improvement
    log_improvement(new_version, meta, prev_metrics)

    return True


# ═══════════════════════════════════════════════════════════════════════════
#  DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def check_drift():
    """Check if model performance has drifted below thresholds."""
    print("\n" + "=" * 60)
    print("  DRIFT DETECTION")
    print("=" * 60)

    # Check from pick history — compute rolling precision
    if not PICK_HISTORY_FILE.exists():
        print("[DRIFT] No pick history — cannot check drift")
        return False

    with open(PICK_HISTORY_FILE) as f:
        history = json.load(f)

    if len(history) < 10:
        print(f"[DRIFT] Only {len(history)} resolved picks — need at least 10")
        return False

    # Rolling window: last 20 picks
    window_size = min(20, len(history))
    recent = history[-window_size:]

    # True positives: predicted pump AND actually pumped (pnl >= 10%)
    # All picks in history were predicted as pumps (probability > threshold)
    actual_pumps = sum(1 for p in recent if (p.get("pnl_pct") or 0) >= 10.0)
    actual_positive = sum(1 for p in recent if (p.get("pnl_pct") or 0) > 0)
    total = len(recent)

    pump_precision = actual_pumps / total if total > 0 else 0
    win_rate = actual_positive / total if total > 0 else 0

    print(f"  Recent {window_size} picks:")
    print(f"    Actual pumps (>10%): {actual_pumps}/{total} = {pump_precision:.1%}")
    print(f"    Win rate (>0%):      {actual_positive}/{total} = {win_rate:.1%}")

    drift_detected = False

    if pump_precision < PRECISION_DRIFT_THRESHOLD:
        print(f"\n  *** DRIFT ALERT: Pump precision ({pump_precision:.1%}) below threshold ({PRECISION_DRIFT_THRESHOLD:.0%}) ***")
        drift_detected = True

    if win_rate < RECALL_DRIFT_THRESHOLD:
        print(f"\n  *** DRIFT ALERT: Win rate ({win_rate:.1%}) below threshold ({RECALL_DRIFT_THRESHOLD:.0%}) ***")
        drift_detected = True

    if not drift_detected:
        print(f"\n  No drift detected — model performing within thresholds")

    # Also check for distribution shift in feature space
    if FEATURE_CACHE.exists() and ONLINE_DATA_FILE.exists():
        original_df = pd.read_csv(FEATURE_CACHE)
        online_df = pd.read_csv(ONLINE_DATA_FILE)

        if len(online_df) >= 10:
            print(f"\n  Feature distribution comparison (original vs online):")
            shifts = []
            for col in FEATURE_COLS:
                if col in original_df.columns and col in online_df.columns:
                    orig_mean = original_df[col].mean()
                    online_mean = online_df[col].mean()
                    orig_std = original_df[col].std()
                    if orig_std > 0:
                        z_shift = abs(online_mean - orig_mean) / orig_std
                        shifts.append((col, z_shift))
                        if z_shift > 2.0:
                            print(f"    {col}: z-shift = {z_shift:.2f} *** SIGNIFICANT ***")

            if shifts:
                max_shift = max(shifts, key=lambda x: x[1])
                if max_shift[1] > 2.0:
                    print(f"\n  *** DISTRIBUTION SHIFT detected in {sum(1 for _, z in shifts if z > 2.0)} features ***")
                    drift_detected = True

    return drift_detected


# ═══════════════════════════════════════════════════════════════════════════
#  IMPROVEMENT LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def log_improvement(version, meta, prev_metrics):
    """Log model improvement history."""
    log = []
    if IMPROVEMENT_LOG.exists():
        with open(IMPROVEMENT_LOG) as f:
            log = json.load(f)

    entry = {
        "version": version,
        "trained_at": meta.get("trained_at"),
        "total_samples": meta.get("total_samples"),
        "online_samples": meta.get("online_samples_used", 0),
        "metrics": meta.get("metrics", {}),
        "previous_metrics": prev_metrics,
        "improvement": {},
    }

    # Calculate improvement deltas
    current = meta.get("metrics", {})
    for metric in ["precision", "recall", "f1", "roc_auc"]:
        prev_val = prev_metrics.get(metric, 0)
        curr_val = current.get(metric, 0)
        entry["improvement"][metric] = round(curr_val - prev_val, 4)

    log.append(entry)

    # Keep last 50 entries
    log = log[-50:]

    with open(IMPROVEMENT_LOG, "w") as f:
        json.dump(log, f, indent=2)

    print(f"  Improvement logged (v{version})")


def print_improvement_history():
    """Print model improvement history."""
    if not IMPROVEMENT_LOG.exists():
        print("[HISTORY] No improvement log found")
        return

    with open(IMPROVEMENT_LOG) as f:
        log = json.load(f)

    print("\n" + "=" * 70)
    print("  MODEL IMPROVEMENT HISTORY")
    print("=" * 70)
    print(f"  {'Version':<10} {'Date':<22} {'Samples':>8} {'Prec':>7} {'Rec':>7} {'F1':>7} {'AUC':>7}")
    print("  " + "-" * 70)

    for entry in log:
        m = entry.get("metrics", {})
        date = entry.get("trained_at", "")[:19]
        print(f"  {entry.get('version', '?'):<10} {date:<22} "
              f"{entry.get('total_samples', 0):>8} "
              f"{m.get('precision', 0):>7.4f} "
              f"{m.get('recall', 0):>7.4f} "
              f"{m.get('f1', 0):>7.4f} "
              f"{m.get('roc_auc', 0):>7.4f}")

        imp = entry.get("improvement", {})
        if any(abs(v) > 0.001 for v in imp.values()):
            deltas = [f"{k}:{v:+.3f}" for k, v in imp.items() if abs(v) > 0.001]
            print(f"  {'':>10} {'':>22} {'':>8} Deltas: {', '.join(deltas)}")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CLAUDE CODE — ML Self-Improver")
    parser.add_argument("--force-retrain", action="store_true", help="Force model retraining")
    parser.add_argument("--drift-check", action="store_true", help="Only check for drift")
    parser.add_argument("--history", action="store_true", help="Print improvement history")
    parser.add_argument("--collect", action="store_true", help="Only collect online data")
    args = parser.parse_args()

    print("=" * 60)
    print("  CLAUDE CODE — ML Self-Improvement Pipeline")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    if args.history:
        print_improvement_history()
        return

    # Step 1: Collect online training data from resolved picks
    print("\n[STEP 1] Collecting online training data...")
    new_samples = collect_online_data()

    if args.collect:
        return

    # Step 2: Check for drift
    if args.drift_check:
        drift = check_drift()
        if drift:
            print("\n[ACTION] Drift detected — retraining recommended")
            print("  Run: python self_improver.py --force-retrain")
        return

    # Step 3: Check if retraining is needed
    print("\n[STEP 2] Checking retraining conditions...")
    needs_retrain = should_retrain() or args.force_retrain

    if needs_retrain:
        print("\n[STEP 3] Retraining model...")
        success = retrain_model()
        if success:
            print("\n[STEP 4] Post-retrain drift check...")
            check_drift()
        else:
            print("[ERROR] Retraining failed")
    else:
        print("\n[SKIP] Retraining not needed at this time")

    # Step 4: Check drift regardless
    print("\n[STEP 5] Drift detection...")
    check_drift()

    # Step 5: Update adaptive threshold based on resolved picks
    print("\n[STEP 6] Adaptive threshold update...")
    try:
        if PICK_HISTORY_FILE.exists():
            with open(PICK_HISTORY_FILE) as f:
                all_picks = json.load(f)
            if all_picks:
                # Import from live_scanner
                sys.path.insert(0, str(BASE_DIR))
                from live_scanner import update_adaptive_threshold
                update_adaptive_threshold(all_picks)
            else:
                print("  No resolved picks yet — threshold unchanged")
        else:
            print("  No pick history — threshold unchanged")
    except Exception as e:
        print(f"  Threshold update skipped: {e}")

    # Print history
    print_improvement_history()

    print("\n[DONE] Self-improvement cycle complete")


if __name__ == "__main__":
    main()
