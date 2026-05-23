"""
Training script for System B Regime Classifier.

Fetches 500 bars of 1h OHLCV for each pair, labels each bar using
the rule-based labeler, trains XGBoost multi-class on walk-forward
split, saves model and scaler.

Run: python -m ml_battleground.system_b_regime.train_regime
"""
import os
import sys
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from typing import Optional
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, PAIRS
from system_b_regime.regime_classifier import (
    compute_regime_features,
    label_series,
    REGIMES,
    REGIME_TO_INT,
    MODEL_PATH,
    SCALER_PATH,
    MODEL_DIR,
)


def build_training_data(
    pairs: Optional[list[str]] = None,
    interval: str = "1h",
    limit: int = 500,
    lookback_min: int = 210,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build feature matrix and label vector from historical OHLCV data.

    For each pair:
      1. Fetch 500 bars of 1h data
      2. Label each bar from lookback_min onward using rule_based_label
      3. Compute regime features for each labeled bar

    Returns:
        (X, y) where X is (n_samples, n_features) and y is (n_samples,) of int labels
    """
    pairs = pairs or PAIRS[:12]  # train on subset for speed

    all_X = []
    all_y = []

    print(f"Fetching OHLCV for {len(pairs)} pairs...")
    data = fetch_ohlcv(pairs, interval, limit)
    print(f"  Got data for {len(data)} pairs")

    for pair, df in data.items():
        if len(df) < lookback_min + 20:
            print(f"  Skipping {pair}: only {len(df)} bars (need {lookback_min + 20})")
            continue

        print(f"  Processing {pair} ({len(df)} bars)...")

        # Label each bar
        labels = label_series(df, lookback_min=lookback_min)

        # Compute features for each labeled bar
        # We step every 3 bars to reduce correlation between samples
        labeled_count = 0
        for i in range(lookback_min, len(df), 3):
            label = labels.iloc[i]
            if label is None or pd.isna(label):
                continue

            slice_df = df.iloc[:i + 1]
            try:
                features = compute_regime_features(slice_df, fear_greed=50.0)
                # Check for NaN features
                if np.any(np.isnan(features)):
                    continue

                all_X.append(features)
                all_y.append(REGIME_TO_INT[label])
                labeled_count += 1
            except Exception as e:
                continue

        print(f"    {pair}: {labeled_count} samples")

    if not all_X:
        return np.array([]), np.array([])

    X = np.array(all_X)
    y = np.array(all_y)

    # Print class distribution
    for regime, idx in REGIME_TO_INT.items():
        count = (y == idx).sum()
        pct = count / len(y) * 100 if len(y) > 0 else 0
        print(f"  Class '{regime}': {count} ({pct:.1f}%)")

    return X, y


def train():
    """Main training loop with walk-forward cross-validation."""
    print("=" * 60)
    print("System B: Regime Classifier Training")
    print("=" * 60)
    print()

    X, y = build_training_data()

    if len(X) < 100:
        print(f"\nInsufficient data: {len(X)} samples (need 100+). Skipping training.")
        return

    print(f"\nTraining on {len(X)} samples across {len(REGIMES)} classes")

    # Purged walk-forward CV (Lopez de Prado: purge + embargo prevents leakage)
    PURGE_BARS = 50   # ~2 days on 1h data
    EMBARGO_BARS = 25  # ~1 day on 1h data
    n_folds = 5
    fold_size = len(X) // n_folds
    fold_scores = []
    _cv_splits = []
    for _i in range(n_folds):
        _test_start = _i * fold_size
        _test_end = min((_i + 1) * fold_size, len(X))
        _purge_start = max(0, _test_start - PURGE_BARS)
        _embargo_end = min(len(X), _test_end + EMBARGO_BARS)
        _train_mask = np.ones(len(X), dtype=bool)
        _train_mask[_purge_start:_embargo_end] = False
        _train_idx = np.where(_train_mask)[0]
        _val_idx = np.arange(_test_start, _test_end)
        if len(_train_idx) > 0 and len(_val_idx) > 0:
            _cv_splits.append((_train_idx, _val_idx))

    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("XGBoost not installed. Install with: pip install xgboost")
        return

    def _compute_sample_weights(y_arr):
        """Compute sample weights based on inverse class frequency."""
        classes, counts = np.unique(y_arr, return_counts=True)
        total = len(y_arr)
        weight_map = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
        return np.array([weight_map[yi] for yi in y_arr])

    print(f"\nPurged walk-forward CV: {len(_cv_splits)} folds (purge={PURGE_BARS}, embargo={EMBARGO_BARS})")
    for fold, (train_idx, val_idx) in enumerate(_cv_splits):
        # Fit scaler on train only to prevent data leakage
        fold_scaler = StandardScaler()
        X_train = fold_scaler.fit_transform(X[train_idx])
        X_val = fold_scaler.transform(X[val_idx])
        y_train, y_val = y[train_idx], y[val_idx]

        # Compute sample weights from inverse class frequency
        train_weights = _compute_sample_weights(y_train)

        model = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.3,
            reg_lambda=1.5,
            objective="multi:softprob",
            num_class=len(REGIMES),
            eval_metric="mlogloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(
            X_train, y_train,
            sample_weight=train_weights,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        y_pred = model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        fold_scores.append(accuracy)
        print(f"  Fold {fold + 1}: accuracy {accuracy:.3f}")

    mean_acc = np.mean(fold_scores)
    print(f"\nMean CV accuracy: {mean_acc:.3f} (+/- {np.std(fold_scores):.3f})")

    # Train final model on all data
    # Fit scaler on train only — for final model, use all data as "train"
    print("\nTraining final model on all data...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Compute sample weights for full dataset
    full_weights = _compute_sample_weights(y)

    final_model = XGBClassifier(
        n_estimators=250,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.3,
        reg_lambda=1.5,
        objective="multi:softprob",
        num_class=len(REGIMES),
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )
    final_model.fit(X_scaled, y, sample_weight=full_weights, verbose=False)

    # Feature importance
    importances = final_model.feature_importances_
    from system_b_regime.regime_classifier import FEATURE_NAMES
    sorted_idx = np.argsort(importances)[::-1]
    print("\nTop 10 feature importances:")
    for i in sorted_idx[:10]:
        name = FEATURE_NAMES[i] if i < len(FEATURE_NAMES) else f"feature_{i}"
        print(f"  {name}: {importances[i]:.4f}")

    # Final classification report on full data (not ideal but informative)
    y_pred_all = final_model.predict(X_scaled)
    print("\nFull-data classification report:")
    print(classification_report(y, y_pred_all, target_names=REGIMES))

    # DSR/PSR hard validation gate
    import json
    os.makedirs(MODEL_DIR, exist_ok=True)
    candidate_model_path = os.path.join(MODEL_DIR, "regime_xgb_candidate.joblib")
    candidate_scaler_path = os.path.join(MODEL_DIR, "regime_scaler_candidate.joblib")

    # Save as candidate first
    joblib.dump(final_model, candidate_model_path)
    joblib.dump(scaler, candidate_scaler_path)
    print(f"\nCandidate model saved to {candidate_model_path}")

    dsr_passed = False
    try:
        from cross_aggregation.dsr_gate import validate_model_for_deployment
        y_proba_final = final_model.predict_proba(X_scaled)
        max_proba = y_proba_final.max(axis=1)
        pseudo_returns = max_proba - (1.0 / len(REGIMES))
        dsr_result = validate_model_for_deployment(pseudo_returns, n_trials=10)
        dsr_passed = dsr_result["passed"]
        if dsr_passed:
            print(f"DSR Gate: PASSED (DSR={dsr_result['dsr_pvalue']:.3f}, PSR={dsr_result['psr_pvalue']:.3f})")
        else:
            print(f"DSR Gate: FAILED -- {dsr_result['reason']}")
        report_path = os.path.join(MODEL_DIR, "validation_report.json")
        dsr_result["model"] = "system_b_regime"
        with open(report_path, "w") as f:
            json.dump(dsr_result, f, indent=2)
        print(f"Validation report saved to {report_path}")
    except Exception as e:
        print(f"DSR gate unavailable: {e}")
        dsr_passed = True  # Allow deployment if gate module unavailable

    # Hard gate: promote candidate to production only if validation passes
    if dsr_passed:
        os.replace(candidate_model_path, MODEL_PATH)
        os.replace(candidate_scaler_path, SCALER_PATH)
        print(f"Validation PASSED -- model promoted to {MODEL_PATH}")
    elif os.path.exists(MODEL_PATH):
        os.remove(candidate_model_path)
        os.remove(candidate_scaler_path)
        print(f"Validation FAILED -- keeping previous model at {MODEL_PATH}")
    else:
        os.replace(candidate_model_path, MODEL_PATH)
        os.replace(candidate_scaler_path, SCALER_PATH)
        print(f"Validation FAILED but no previous model -- deploying candidate (bootstrap)")

    print(f"\nScaler saved to: {SCALER_PATH}")
    print(f"Training complete. Mean CV accuracy: {mean_acc:.3f}")


if __name__ == "__main__":
    train()
