# meta_label.py - XGBoost meta-labeler for signal quality prediction
# Requirements: pip install xgboost pandas numpy scikit-learn requests

import os
import sys
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score
import xgboost as xgb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import call_api, post_to_api

def fetch_trade_data():
    """Get training data from API (meta_label_training_data)."""
    data = call_api('meta_label_training_data')
    if not data or not data.get('ok'):
        return pd.DataFrame()
    rows = data.get('data', data.get('rows', data.get('trades', [])))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

def engineer_features(df):
    # Binary label: good (positive return) vs bad
    ret_col = df.get('return_pct', df.get('realized_pct', pd.Series([0] * len(df))))
    if hasattr(ret_col, 'median'):
        df['label'] = (ret_col > ret_col.median()).astype(int)
    else:
        df['label'] = 1

    # Features
    algo_col = df.get('algo_name', df.get('algorithm_name', 'algo'))
    df['win_rate_rolling'] = df.groupby(algo_col)['label'].transform(lambda x: x.rolling(20, min_periods=1).mean())
    regime = df.get('regime', df.get('hmm_regime', ''))
    df['regime_bull'] = (regime == 'bull').astype(int)
    df['regime_bear'] = (regime == 'bear').astype(int)
    sig_type = df.get('signal_type', 'buy')
    df['is_buy'] = (sig_type == 'buy').astype(int)
    entry = pd.to_datetime(df.get('entry_date', df.get('entry_time', 0)), errors='coerce')
    exit_ = pd.to_datetime(df.get('exit_date', df.get('exit_time', 0)), errors='coerce')
    df['hold_hours'] = ((exit_ - entry).dt.total_seconds() / 3600).fillna(0)
    if 'confidence' not in df.columns:
        df['confidence'] = 0
    else:
        df['confidence'] = df['confidence'].fillna(0)
    if 'spy_ret' not in df.columns:
        df['spy_ret'] = 0
    else:
        df['spy_ret'] = df['spy_ret'].fillna(0)
    if 'vix_value' not in df.columns and 'vix_level' in df.columns:
        df['vix_value'] = df['vix_level'].fillna(0)
    elif 'vix_value' not in df.columns:
        df['vix_value'] = 0
    else:
        df['vix_value'] = df['vix_value'].fillna(0)

    features = ['confidence', 'spy_ret', 'vix_value', 'win_rate_rolling',
                'regime_bull', 'regime_bear', 'is_buy', 'hold_hours']
    X = df[[c for c in features if c in df.columns]].fillna(0)
    y = df['label']
    return X, y, [c for c in features if c in df.columns]

def train_model():
    df = fetch_trade_data()
    if len(df) < 50:
        print("Insufficient data for training")
        return None

    X, y, feature_cols = engineer_features(df)
    # Temporal split: use first 80% as train, last 20% as test (preserves chronological order)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=3,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    print(f"Accuracy: {acc:.2f}, Precision: {prec:.2f}")

    os.makedirs('models', exist_ok=True)
    model.save_model('models/meta_label_model.json')

    # Post model metadata/results to API
    post_to_api('update_meta_labeler', {
        'accuracy': round(acc, 4),
        'precision': round(prec, 4),
        'feature_importance': dict(zip(feature_cols, model.feature_importances_.tolist())),
    })
    return model

def predict_signal(features_dict):
    model = xgb.XGBClassifier()
    try:
        model.load_model('models/meta_label_model.json')
    except Exception:
        print("No model found")
        return 0.5, True, "No model available"

    df = pd.DataFrame([features_dict])
    X, _, _ = engineer_features(df.fillna(0))
    prob = model.predict_proba(X)[0, 1]
    should_execute = prob >= 0.6
    explanation = f"Predicted success prob: {prob:.2f}"
    return prob, should_execute, explanation

if __name__ == '__main__':
    train_model()
