# meta_label.py - XGBoost meta-labeler for signal quality prediction
# Requirements: pip install xgboost pandas numpy mysql-connector-python scikit-learn

import os
import mysql.connector
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score
import xgboost as xgb

# DB config from env vars
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_trade_data():
    conn = connect_db()
    query = """
    SELECT t.*, s.confidence, s.algo_name, s.signal_type,
           m.regime, m.spy_ret, m.vix_value
    FROM lm_trades t
    JOIN lm_signals s ON t.signal_id = s.id
    LEFT JOIN lm_market_regime m ON DATE(t.entry_date) = m.regime_date
    WHERE t.status = 'closed' AND t.return_pct IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def engineer_features(df):
    # Binary label: good (positive return) vs bad
    df['label'] = (df['return_pct'] > 0).astype(int)
    
    # Features
    df['win_rate_rolling'] = df.groupby('algo_name')['label'].transform(lambda x: x.rolling(20).mean())
    df['regime_bull'] = (df['regime'] == 'bull').astype(int)
    df['regime_bear'] = (df['regime'] == 'bear').astype(int)
    df['is_buy'] = (df['signal_type'] == 'buy').astype(int)
    df['hold_hours'] = (pd.to_datetime(df['exit_date']) - pd.to_datetime(df['entry_date'])).dt.total_seconds() / 3600
    
    features = ['confidence', 'spy_ret', 'vix_value', 'win_rate_rolling',
                'regime_bull', 'regime_bear', 'is_buy', 'hold_hours']
    X = df[features].fillna(0)
    y = df['label']
    return X, y, features

def train_model():
    df = fetch_trade_data()
    if len(df) < 50:
        print("Insufficient data for training")
        return None
        
    X, y, feature_cols = engineer_features(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
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
    prec = precision_score(y_test, preds)
    print(f"Accuracy: {acc:.2f}, Precision: {prec:.2f}")
    
    model.save_model('models/meta_label_model.json')
    return model

def predict_signal(features_dict):
    import xgboost as xgb
    model = xgb.XGBClassifier()
    try:
        model.load_model('models/meta_label_model.json')
    except:
        print("No model found")
        return 0.5, True, "No model available"
    
    # Match training features
    df = pd.DataFrame([features_dict])
    X, _, _ = engineer_features(df.fillna(0))
    
    prob = model.predict_proba(X)[0, 1]
    should_execute = prob >= 0.6
    explanation = f"Predicted success prob: {prob:.2f}"
    return prob, should_execute, explanation

if __name__ == '__main__':
    train_model()