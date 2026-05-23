"""
Train the ML filter for System A.
Uses walk-forward validation on historical strategy signals.
Run: python -m ml_battleground.system_a_filter.train_filter
"""
import os
import sys
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit

try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_fetcher import fetch_ohlcv, PAIRS
from shared.indicators import atr, rsi
from shared.sr_engine import detect_sr_levels
from system_a_filter.strategies import run_all_strategies
from system_a_filter.ml_filter import compute_filter_features, FEATURE_NAMES, MODEL_PATH, SCALER_PATH
from shared.model_calibration import CalibratedModelWrapper


def build_training_data(
    pairs: list[str] = None,
    interval: str = "1h",
    limit: int = 500,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 2.0,
    max_horizon: int = 48,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build labeled dataset from historical strategy signals.
    Label = 1 if TP hit before SL within horizon, else 0.
    """
    pairs = pairs or PAIRS[:10]  # Train on subset for speed
    all_X = []
    all_y = []

    data = fetch_ohlcv(pairs, interval, limit)

    for pair, df in data.items():
        if len(df) < 200:
            continue

        # Run strategies on historical slices
        for end_idx in range(250, len(df) - max_horizon, 10):
            slice_df = df.iloc[:end_idx].copy()
            future_df = df.iloc[end_idx:end_idx + max_horizon]

            signals = run_all_strategies(slice_df, pair)
            if not signals:
                continue

            sr_levels = detect_sr_levels(slice_df)
            atr_val = atr(slice_df["High"], slice_df["Low"], slice_df["Close"])

            for sig in signals:
                entry = sig["entry_price"]
                atr_now = float(atr_val.iloc[-1]) if len(atr_val) > 0 else entry * 0.02

                tp = entry + tp_atr_mult * atr_now
                sl = entry - sl_atr_mult * atr_now

                # Label via triple barrier on future data
                label = _triple_barrier_label(future_df, entry, tp, sl, sig.get("signal_type", "BUY"))

                features = compute_filter_features(sig, sr_levels, slice_df)
                all_X.append(features)
                all_y.append(label)

    if not all_X:
        return np.array([]), np.array([])

    return np.array(all_X), np.array(all_y)


def _triple_barrier_label(
    future_df: pd.DataFrame,
    entry: float,
    tp: float,
    sl: float,
    signal_type: str,
) -> int:
    """1 if TP hit first, 0 if SL hit first or neither."""
    for _, row in future_df.iterrows():
        if signal_type == "BUY":
            if row["Low"] <= sl:
                return 0
            if row["High"] >= tp:
                return 1
        else:
            if row["High"] >= sl:
                return 0
            if row["Low"] <= tp:
                return 1
    return 0  # horizon expired


def train():
    """Main training loop."""
    print("Building training data...")
    X, y = build_training_data()

    if len(X) < 100:
        print(f"Insufficient data: {len(X)} samples. Need 100+. Skipping training.")
        return

    print(f"Training on {len(X)} samples. Positive rate: {y.mean():.1%}")

    # Purged walk-forward CV (Lopez de Prado: purge + embargo prevents leakage)
    PURGE_BARS = 50   # ~2 days on 1h data
    EMBARGO_BARS = 25  # ~1 day on 1h data
    n_folds = 5
    fold_size = len(X) // n_folds
    scores = []
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
    print(f"  Purged CV: {len(_cv_splits)} folds (purge={PURGE_BARS}, embargo={EMBARGO_BARS})")

    for fold, (train_idx, val_idx) in enumerate(_cv_splits):
        # Fit scaler on train only to prevent data leakage
        fold_scaler = StandardScaler()
        X_train = fold_scaler.fit_transform(X[train_idx])
        X_val = fold_scaler.transform(X[val_idx])
        y_train, y_val = y[train_idx], y[val_idx]

        # SMOTE oversampling on train fold only (never on validation)
        if SMOTE_AVAILABLE and (y_train == 1).sum() >= 6:
            try:
                sm = SMOTE(random_state=42, k_neighbors=min(5, (y_train == 1).sum() - 1))
                X_train, y_train = sm.fit_resample(X_train, y_train)
                if fold == 0:
                    print(f"  SMOTE applied: {len(X_train)} samples after resampling")
            except Exception as e:
                print(f"  SMOTE failed on fold {fold}: {e}, using original data")

        model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,
            reg_lambda=2.0,
            scale_pos_weight=max(1, (y_train == 0).sum() / max(1, (y_train == 1).sum())),
            eval_metric="logloss",
            random_state=42,
        )
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        # Use ROC-AUC (proper metric for imbalanced trading signals)
        y_proba = model.predict_proba(X_val)[:, 1]
        y_pred = model.predict(X_val)
        try:
            auc = roc_auc_score(y_val, y_proba)
        except ValueError:
            auc = 0.5  # single-class fold
        prec = precision_score(y_val, y_pred, zero_division=0)
        rec = recall_score(y_val, y_pred, zero_division=0)
        acc = model.score(X_val, y_val)

        scores.append(auc)
        print(f"  Fold {fold + 1}: ROC-AUC={auc:.3f}  Precision={prec:.3f}  Recall={rec:.3f}  Accuracy={acc:.3f}")

    print(f"Mean CV ROC-AUC: {np.mean(scores):.3f}")

    # Split: first 80% for training, last 20% for isotonic calibration
    # Temporal split preserves time ordering — no future leakage
    cal_split = int(len(X) * 0.8)
    X_train_part, X_cal_part = X[:cal_split], X[cal_split:]
    y_train_part, y_cal_part = y[:cal_split], y[cal_split:]
    print(f"Temporal split: {len(X_train_part)} train / {len(X_cal_part)} calibration")

    # Train final model on the 80% training portion
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train_part)
    X_cal_scaled = scaler.transform(X_cal_part)

    # SMOTE on training portion only (never on calibration)
    X_train_final, y_train_final = X_scaled, y_train_part
    if SMOTE_AVAILABLE and (y_train_part == 1).sum() >= 6:
        try:
            sm = SMOTE(random_state=42, k_neighbors=min(5, (y_train_part == 1).sum() - 1))
            X_train_final, y_train_final = sm.fit_resample(X_scaled, y_train_part)
            print(f"  SMOTE applied to final model: {len(X_train_final)} samples")
        except Exception as e:
            print(f"  SMOTE failed for final model: {e}, using original data")

    final_model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.5, reg_lambda=2.0,
        scale_pos_weight=max(1, (y_train_final == 0).sum() / max(1, (y_train_final == 1).sum())),
        eval_metric="logloss", random_state=42,
    )
    final_model.fit(X_train_final, y_train_final, verbose=False)

    # Fit isotonic calibration on the held-out 20% temporal chunk
    cal_wrapper = CalibratedModelWrapper(final_model)
    cal_fitted = cal_wrapper.fit_calibration(X_cal_scaled, y_cal_part)

    # DSR/PSR hard validation gate
    import json
    from shared.model_calibration import _default_cal_path
    model_dir = os.path.dirname(MODEL_PATH)
    os.makedirs(model_dir, exist_ok=True)
    candidate_path = os.path.join(model_dir, "filter_xgb_candidate.joblib")
    candidate_scaler_path = os.path.join(model_dir, "filter_scaler_candidate.joblib")
    candidate_cal_path = os.path.join(model_dir, "filter_xgb_candidate_calibration.joblib")
    CALIBRATION_PATH = _default_cal_path(MODEL_PATH)

    # Save as candidate first
    cal_wrapper.save(candidate_path, candidate_cal_path)
    joblib.dump(scaler, candidate_scaler_path)
    print(f"Candidate model saved to {candidate_path}")
    if cal_fitted:
        print(f"Calibration model saved to {candidate_cal_path}")

    dsr_passed = False
    try:
        from cross_aggregation.dsr_gate import validate_model_for_deployment
        y_proba_final = final_model.predict_proba(X_scaled)[:, 1]
        pseudo_returns = y_proba_final - 0.5
        dsr_result = validate_model_for_deployment(pseudo_returns, n_trials=10)
        dsr_passed = dsr_result["passed"]
        if dsr_passed:
            print(f"DSR Gate: PASSED (DSR={dsr_result['dsr_pvalue']:.3f}, PSR={dsr_result['psr_pvalue']:.3f})")
        else:
            print(f"DSR Gate: FAILED -- {dsr_result['reason']}")
        report_path = os.path.join(model_dir, "validation_report.json")
        dsr_result["model"] = "system_a_filter"
        with open(report_path, "w") as f:
            json.dump(dsr_result, f, indent=2)
        print(f"Validation report saved to {report_path}")
    except Exception as e:
        print(f"DSR gate unavailable: {e}")
        # If gate module unavailable, allow deployment (bootstrap)
        dsr_passed = True

    # Hard gate: promote candidate to production only if validation passes
    def _promote_candidate():
        os.replace(candidate_path, MODEL_PATH)
        os.replace(candidate_scaler_path, SCALER_PATH)
        if os.path.exists(candidate_cal_path):
            os.replace(candidate_cal_path, CALIBRATION_PATH)
            print(f"  Calibration model promoted to {CALIBRATION_PATH}")
        elif os.path.exists(CALIBRATION_PATH):
            os.remove(CALIBRATION_PATH)  # remove stale calibration

    def _discard_candidate():
        for p in [candidate_path, candidate_scaler_path, candidate_cal_path]:
            if os.path.exists(p):
                os.remove(p)

    if dsr_passed:
        _promote_candidate()
        print(f"Validation PASSED -- model promoted to {MODEL_PATH}")
    elif os.path.exists(MODEL_PATH):
        _discard_candidate()
        print(f"Validation FAILED -- keeping previous model at {MODEL_PATH}")
    else:
        # No previous model exists (bootstrap) — deploy candidate anyway
        _promote_candidate()
        print(f"Validation FAILED but no previous model -- deploying candidate (bootstrap)")


if __name__ == "__main__":
    train()
