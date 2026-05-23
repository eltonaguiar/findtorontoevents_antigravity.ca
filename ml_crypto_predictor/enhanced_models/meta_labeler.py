"""
Meta-Labeling Module (López de Prado M1/M2 Pattern)
=====================================================
M1 (primary model) generates directional signals.
M2 (meta-labeler) predicts whether M1's signal will be profitable.

This filters false positives: only emit picks where M2 confidence > threshold.

References:
  - López de Prado (2018) "Advances in Financial Machine Learning", Ch. 3
  - R001 (Hedge Fund Quant) researcher finding: meta-labeling is #1 improvement

Usage:
  Training:   train_meta_model(X_train, y_train, m1_proba_train, ...)
  Inference:  apply_meta_filter(pair, timeframe, features, m1_proba, ...)
"""

import json
import numpy as np
import joblib
from pathlib import Path
from typing import Tuple, List, Optional, Dict

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import cross_val_predict, TimeSeriesSplit

from .config import MODELS_DIR, RESULTS_DIR


def train_meta_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    m1_proba_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    m1_proba_test: np.ndarray,
    feature_names: List[str],
    pair: str,
    timeframe: str,
) -> Optional[Dict]:
    """
    Train M2 meta-labeling model.

    The meta-labeler takes M1's features + M1's probability as input,
    and predicts whether M1's signal will be a TP (1) or SL (0).

    Args:
        X_train/X_test: Scaled feature arrays from M1
        y_train/y_test: True TP/SL labels
        m1_proba_train/test: M1's predicted probabilities
        feature_names: Feature column names
        pair: Trading pair
        timeframe: Timeframe string

    Returns:
        Dict with training metrics, or None if insufficient data
    """
    if len(X_train) < 100 or len(X_test) < 30:
        return None

    # FIXED: m1_proba_train should be out-of-fold predictions (not in-sample)
    # to avoid data leakage. The caller (model_trainer.py) now passes OOF
    # predictions via cross_val_predict. See model_trainer.py line ~409.
    X_train_meta = np.column_stack([X_train, m1_proba_train])
    X_test_meta = np.column_stack([X_test, m1_proba_test])

    # Only train on samples where M1 would have signaled (proba > 0.5)
    # This focuses M2 on filtering M1's actual signals
    train_mask = m1_proba_train >= 0.5
    test_mask = m1_proba_test >= 0.5

    if train_mask.sum() < 50 or test_mask.sum() < 10:
        return None

    X_train_filtered = X_train_meta[train_mask]
    y_train_filtered = y_train[train_mask]
    X_test_filtered = X_test_meta[test_mask]
    y_test_filtered = y_test[test_mask]

    # GBM for M2 (lighter than XGBoost, fewer params to overfit)
    m2 = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=10,
        random_state=42,
    )
    m2.fit(X_train_filtered, y_train_filtered)

    # Calibrate probabilities
    try:
        m2_cal = CalibratedClassifierCV(m2, method="isotonic", cv=3, ensemble=True)
        m2_cal.fit(X_train_filtered, y_train_filtered)
        m2 = m2_cal
    except Exception:
        pass  # Keep uncalibrated if calibration fails

    # Evaluate
    m2_proba = m2.predict_proba(X_test_filtered)[:, 1]
    m2_pred = (m2_proba >= 0.55).astype(int)

    # Coverage = what fraction of M1's signals pass M2
    coverage = m2_pred.mean()

    # Filtered win rate = WR among signals that pass M2
    if m2_pred.sum() > 0:
        filtered_wr = y_test_filtered[m2_pred == 1].mean()
    else:
        filtered_wr = 0.0

    # Unfiltered win rate (M1 alone)
    unfiltered_wr = y_test_filtered.mean()

    # Save M2 model
    meta_path = MODELS_DIR / f"meta_{pair}_{timeframe}.joblib"
    joblib.dump(m2, str(meta_path))

    # Save meta feature names (original + m1_proba)
    meta_info = {
        "feature_names": feature_names + ["m1_proba"],
        "pair": pair,
        "timeframe": timeframe,
        "unfiltered_win_rate": float(unfiltered_wr),
        "filtered_win_rate": float(filtered_wr),
        "coverage": float(coverage),
        "train_samples": int(train_mask.sum()),
        "test_samples": int(test_mask.sum()),
    }
    meta_info_path = MODELS_DIR / f"meta_{pair}_{timeframe}_info.json"
    with open(meta_info_path, "w") as f:
        json.dump(meta_info, f, indent=2)

    return meta_info


def apply_meta_filter(
    pair: str,
    timeframe: str,
    feature_vector: np.ndarray,
    m1_proba: float,
    feature_names: List[str],
    threshold: float = 0.55,
) -> Tuple[bool, float]:
    """
    Apply M2 meta-label filter to a single prediction.

    Args:
        pair: Trading pair
        timeframe: Timeframe string
        feature_vector: Scaled feature array (1D or 2D with 1 row)
        m1_proba: M1's predicted probability for this signal
        feature_names: Feature column names (for validation)
        threshold: Minimum M2 confidence to pass

    Returns:
        (should_trade: bool, meta_confidence: float)
        If no meta model exists, returns (True, m1_proba) — pass through
    """
    meta_path = MODELS_DIR / f"meta_{pair}_{timeframe}.joblib"

    if not meta_path.exists():
        # No meta model trained yet — pass through
        return True, float(m1_proba)

    try:
        m2 = joblib.load(str(meta_path))

        # Ensure feature_vector is 2D
        if feature_vector.ndim == 1:
            feature_vector = feature_vector.reshape(1, -1)

        # Augment with M1 probability
        X_meta = np.column_stack([feature_vector, [[m1_proba]]])

        # Predict
        meta_proba = m2.predict_proba(X_meta)[:, 1][0]
        should_trade = meta_proba >= threshold

        return bool(should_trade), float(meta_proba)

    except Exception as e:
        # Any error → pass through (don't block trading due to meta issues)
        print(f"  [META] Filter error for {pair}/{timeframe}: {e}")
        return True, float(m1_proba)
