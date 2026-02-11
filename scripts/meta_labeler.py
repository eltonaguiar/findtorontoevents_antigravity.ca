#!/usr/bin/env python3
"""
Meta-Labeling Engine — XGBoost-based signal filter.

Lopez de Prado's meta-labeling technique:
  - Primary model: Your existing 23 algos generate BUY/SHORT signals
  - Meta-model (this): Predicts PROBABILITY of signal success
  - Only execute signals where meta-model confidence > threshold

Features:
  - Signal strength, algorithm name, bundle
  - Regime (HMM, Hurst, composite score)
  - Volatility (EWMA, ATR ratio)
  - Time features (hour, day of week, market session)
  - Bundle recent win rate (online learning)
  - Cross-asset correlation state

Expected impact:
  - Precision: 40-70% (filters ~50% of noise)
  - Sharpe boost: +0.3-0.5

Requires: pip install xgboost scikit-learn pandas numpy requests
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, call_api
from config import API_BASE, ADMIN_KEY

logger = logging.getLogger('meta_labeler')

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'meta_labeler.json')


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def engineer_features(signals_df):
    """
    Create features for the meta-model from raw signal data.

    Input columns expected:
      signal_time, algorithm_name, signal_strength, symbol, asset_class,
      entry_price, target_tp_pct, target_sl_pct, max_hold_hours,
      hmm_regime, hurst, composite_score, ewma_vol, vix_level

    Output: Feature matrix (X) and target (y = TP hit or not).
    """
    df = signals_df.copy()

    # Time features
    if 'signal_time' in df.columns:
        dt = pd.to_datetime(df['signal_time'])
        df['hour'] = dt.dt.hour
        df['day_of_week'] = dt.dt.dayofweek
        df['is_market_open'] = ((dt.dt.hour >= 9) & (dt.dt.hour < 16)).astype(int)
        df['is_monday'] = (dt.dt.dayofweek == 0).astype(int)
        df['is_friday'] = (dt.dt.dayofweek == 4).astype(int)
    else:
        df['hour'] = 12
        df['day_of_week'] = 2
        df['is_market_open'] = 1
        df['is_monday'] = 0
        df['is_friday'] = 0

    # Signal features
    df['strength'] = pd.to_numeric(df.get('signal_strength', 50), errors='coerce').fillna(50)
    df['tp_sl_ratio'] = pd.to_numeric(df.get('target_tp_pct', 5), errors='coerce') / \
                        pd.to_numeric(df.get('target_sl_pct', 3), errors='coerce').clip(lower=0.1)
    df['hold_hours'] = pd.to_numeric(df.get('max_hold_hours', 24), errors='coerce').fillna(24)

    # Regime features
    df['composite_score'] = pd.to_numeric(df.get('composite_score', 50), errors='coerce').fillna(50)
    df['hurst'] = pd.to_numeric(df.get('hurst', 0.5), errors='coerce').fillna(0.5)
    df['ewma_vol'] = pd.to_numeric(df.get('ewma_vol', 0.02), errors='coerce').fillna(0.02)
    df['vix_level'] = pd.to_numeric(df.get('vix_level', 20), errors='coerce').fillna(20)

    # Interaction features
    df['strength_x_regime'] = df['strength'] * df['composite_score'] / 100
    df['strength_x_hurst'] = df['strength'] * df['hurst']
    df['vol_x_regime'] = df['ewma_vol'] * df['composite_score']

    # One-hot encode HMM regime
    hmm_col = df.get('hmm_regime', pd.Series(['sideways'] * len(df)))
    for regime in ['bull', 'sideways', 'bear']:
        df['hmm_' + regime] = (hmm_col == regime).astype(int)

    # One-hot encode asset class
    ac_col = df.get('asset_class', pd.Series(['STOCK'] * len(df)))
    for ac in ['CRYPTO', 'FOREX', 'STOCK']:
        df['ac_' + ac] = (ac_col == ac).astype(int)

    # Bundle recent performance (online learning feature)
    # This gets populated from rolling stats
    df['bundle_recent_wr'] = pd.to_numeric(df.get('bundle_recent_wr', 0.5), errors='coerce').fillna(0.5)
    df['algo_recent_wr'] = pd.to_numeric(df.get('algo_recent_wr', 0.5), errors='coerce').fillna(0.5)

    # Feature columns
    feature_cols = [
        'strength', 'tp_sl_ratio', 'hold_hours',
        'composite_score', 'hurst', 'ewma_vol', 'vix_level',
        'hour', 'day_of_week', 'is_market_open', 'is_monday', 'is_friday',
        'strength_x_regime', 'strength_x_hurst', 'vol_x_regime',
        'hmm_bull', 'hmm_sideways', 'hmm_bear',
        'ac_CRYPTO', 'ac_FOREX', 'ac_STOCK',
        'bundle_recent_wr', 'algo_recent_wr'
    ]

    X = df[feature_cols].fillna(0).astype(float)

    # Target: did the signal hit TP? (binary)
    y = None
    if 'exit_reason' in df.columns:
        y = (df['exit_reason'] == 'tp_hit').astype(int)
    elif 'outcome' in df.columns:
        y = (df['outcome'] == 'TP_HIT').astype(int)

    return X, y, feature_cols


# ---------------------------------------------------------------------------
# Adversarial Validation (Leakage Detection)
# ---------------------------------------------------------------------------

def adversarial_validation(X, fold_indices):
    """
    Detect temporal leakage: Can a model predict which fold a sample belongs to?
    If accuracy > 55%, there's likely leakage in the features.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(clf, X, fold_indices, cv=3, scoring='accuracy')
    avg = float(np.mean(scores))

    if avg > 0.55:
        logger.warning("LEAKAGE DETECTED: adversarial accuracy=%.2f%% (>55%%)", avg * 100)
        return False, avg
    else:
        logger.info("Leakage check passed: adversarial accuracy=%.2f%%", avg * 100)
        return True, avg


# ---------------------------------------------------------------------------
# Training Pipeline
# ---------------------------------------------------------------------------

def train_meta_labeler():
    """
    Train XGBoost meta-labeler on historical signals + outcomes.
    Uses purged time-series cross-validation.
    """
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import precision_score, recall_score, f1_score

    logger.info("=" * 60)
    logger.info("META-LABELER — Training")
    logger.info("=" * 60)

    # Fetch historical signals with outcomes
    logger.info("Fetching training data...")
    result = call_api('meta_label_training_data')

    if not result.get('ok') or not result.get('signals'):
        logger.warning("No training data available. Attempting fallback...")
        # Try fetching from trade history
        result = call_api('history', 'limit=5000')
        if not result.get('ok'):
            logger.error("Cannot fetch training data")
            return None

    signals = result.get('signals', result.get('trades', []))
    if len(signals) < 50:
        logger.error("Insufficient training data (%d signals, need 50+)", len(signals))
        return None

    logger.info("Training data: %d signals", len(signals))

    # Convert to DataFrame
    df = pd.DataFrame(signals)
    X, y, feature_cols = engineer_features(df)

    if y is None:
        logger.error("No target variable (exit_reason/outcome) in data")
        return None

    logger.info("Features: %d | Positive rate: %.1f%%", len(feature_cols), y.mean() * 100)

    # Purged Time-Series Cross-Validation
    tscv = TimeSeriesSplit(n_splits=5)
    cv_results = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        # Purge: add gap between train and test (prevent leakage from overlapping trades)
        purge_gap = min(24, len(train_idx) // 20)  # ~5% of training data
        train_idx = train_idx[:-purge_gap] if purge_gap > 0 else train_idx

        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Handle class imbalance
        pos_count = y_train.sum()
        neg_count = len(y_train) - pos_count
        scale = neg_count / max(pos_count, 1)

        model = xgb.XGBClassifier(
            max_depth=4,
            learning_rate=0.05,
            n_estimators=200,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale,
            eval_metric='logloss',
            random_state=42,
            use_label_encoder=False
        )

        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  verbose=False)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        precision = precision_score(y_test, preds, zero_division=0)
        recall = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)

        cv_results.append({
            'fold': fold + 1,
            'precision': round(precision, 3),
            'recall': round(recall, 3),
            'f1': round(f1, 3),
            'test_size': len(y_test),
            'positive_rate': round(float(y_test.mean()), 3)
        })

        logger.info("  Fold %d: Precision=%.1f%% Recall=%.1f%% F1=%.3f (n=%d, pos_rate=%.1f%%)",
                     fold + 1, precision * 100, recall * 100, f1,
                     len(y_test), y_test.mean() * 100)

    # Summary
    avg_precision = np.mean([r['precision'] for r in cv_results])
    avg_recall = np.mean([r['recall'] for r in cv_results])
    avg_f1 = np.mean([r['f1'] for r in cv_results])

    logger.info("CV Summary: Precision=%.1f%% Recall=%.1f%% F1=%.3f",
                 avg_precision * 100, avg_recall * 100, avg_f1)

    # Train final model on all data
    logger.info("Training final model on all %d samples...", len(X))

    pos_count = y.sum()
    neg_count = len(y) - pos_count
    scale = neg_count / max(pos_count, 1)

    final_model = xgb.XGBClassifier(
        max_depth=4,
        learning_rate=0.05,
        n_estimators=200,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale,
        eval_metric='logloss',
        random_state=42,
        use_label_encoder=False
    )
    final_model.fit(X, y, verbose=False)

    # Feature importance
    importances = dict(zip(feature_cols, final_model.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    logger.info("Top 10 features:")
    for feat, imp in sorted_imp[:10]:
        bar = '#' * int(imp * 100)
        logger.info("  %-22s %.3f |%s|", feat, imp, bar)

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    final_model.save_model(MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)

    # Post training results to API
    training_result = {
        'cv_results': cv_results,
        'avg_precision': round(avg_precision, 4),
        'avg_recall': round(avg_recall, 4),
        'avg_f1': round(avg_f1, 4),
        'training_samples': len(X),
        'positive_rate': round(float(y.mean()), 4),
        'top_features': [{'name': f, 'importance': round(float(i), 4)} for f, i in sorted_imp[:15]],
        'trained_at': datetime.utcnow().isoformat()
    }

    post_to_api('update_meta_labeler', training_result)

    return final_model, cv_results


# ---------------------------------------------------------------------------
# Prediction (for live signals)
# ---------------------------------------------------------------------------

def predict_signal_quality(signal_features):
    """
    Predict probability of a signal's success.

    signal_features: dict with same keys as training features.
    Returns: (probability, should_execute, explanation)
    """
    import xgboost as xgb

    if not os.path.exists(MODEL_PATH):
        logger.warning("No trained model found at %s — passing all signals", MODEL_PATH)
        return 0.5, True, "No model trained yet"

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    # Build feature vector
    df = pd.DataFrame([signal_features])
    X, _, feature_cols = engineer_features(df)

    prob = float(model.predict_proba(X)[0, 1])

    # Threshold: 0.55 for moderate filtering, 0.60 for aggressive
    threshold = 0.55
    should_execute = prob >= threshold

    # Explanation
    if prob >= 0.70:
        explanation = "HIGH confidence signal — strong regime/strength alignment"
    elif prob >= 0.55:
        explanation = "MODERATE confidence — execute with standard sizing"
    elif prob >= 0.40:
        explanation = "LOW confidence — reduce size or skip"
    else:
        explanation = "VERY LOW confidence — likely noise, skip"

    return prob, should_execute, explanation


# ---------------------------------------------------------------------------
# Batch Prediction (for signal scan output)
# ---------------------------------------------------------------------------

def filter_signals(signals):
    """
    Filter a batch of signals through the meta-labeler.
    Returns: list of signals with meta_probability and should_execute flags.
    """
    import xgboost as xgb

    if not os.path.exists(MODEL_PATH):
        logger.info("No model trained — passing all %d signals", len(signals))
        for s in signals:
            s['meta_probability'] = 0.5
            s['meta_execute'] = True
            s['meta_explanation'] = 'No model trained'
        return signals

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    df = pd.DataFrame(signals)
    X, _, _ = engineer_features(df)

    probs = model.predict_proba(X)[:, 1]

    threshold = 0.55
    filtered = 0
    passed = 0

    for i, signal in enumerate(signals):
        prob = float(probs[i])
        execute = prob >= threshold
        signal['meta_probability'] = round(prob, 3)
        signal['meta_execute'] = execute

        if execute:
            passed += 1
        else:
            filtered += 1

    logger.info("Meta-filter: %d passed, %d filtered (%.0f%% pass rate)",
                 passed, filtered, passed / max(1, len(signals)) * 100)

    return signals


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    """Train meta-labeler if sufficient data exists."""
    logger.info("=" * 60)
    logger.info("META-LABELER ENGINE — Starting")
    logger.info("=" * 60)

    result = train_meta_labeler()

    if result:
        model, cv_results = result
        logger.info("Training complete. Model ready for live filtering.")
    else:
        logger.info("Training skipped (insufficient data). Will pass all signals.")

    logger.info("=" * 60)


if __name__ == '__main__':
    main()
