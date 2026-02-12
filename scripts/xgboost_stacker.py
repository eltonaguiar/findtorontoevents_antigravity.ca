# xgboost_stacker.py - Full XGBoost stacking for multi-asset signals
# Requirements: pip install xgboost pandas numpy mysql-connector-python scikit-learn

import os
import mysql.connector
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import xgboost as xgb
import numpy as np

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

MODEL_PATH = 'models/xgb_stacker.json'

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_signals(asset_class=None):
    conn = connect_db()
    query = """
    SELECT s.*, t.return_pct, m.regime
    FROM lm_signals s
    LEFT JOIN lm_trades t ON s.id = t.signal_id
    LEFT JOIN lm_market_regime m ON DATE(s.signal_date) = m.regime_date
    """
    if asset_class:
        query += f" WHERE s.asset_class = '{asset_class}'"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def prepare_stacking_data(df):
    # One-hot algos and assets
    df = pd.get_dummies(df, columns=['algo_name', 'asset_class'], prefix=['algo', 'asset'])
    
    # Features: confidence, regime dummy, signal_type, etc.
    df['is_buy'] = (df['signal_type'] == 'buy').astype(int)
    df['regime_bull'] = (df['regime'] == 'bull').astype(int)
    df['regime_bear'] = (df['regime'] == 'bear').astype(int)
    
    # Label: successful if return > 0
    df['success'] = (df['return_pct'] > 0).astype(int)
    
    features = [col for col in df.columns if col.startswith('algo_') or col.startswith('asset_') or col in ['confidence', 'is_buy', 'regime_bull', 'regime_bear']]
    X = df[features].fillna(0)
    y = df['success']
    return X, y, features

def train_stacker(asset_class=None):
    df = fetch_signals(asset_class)
    if len(df) < 100:
        print(f"Insufficient data for {asset_class or 'all'}")
        return None
        
    X, y, features = prepare_stacking_data(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        learning_rate=0.02,
        max_depth=4,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Stacker Accuracy: {acc:.2f}")
    
    model.save_model(MODEL_PATH)
    return model

def stack_predict(new_signals_df, alphas_df):
    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    X, _, _ = prepare_stacking_data(new_signals_df.fillna(0))
    
    # Blend in alphas
    for i in range(len(new_signals_df)):
        ticker = new_signals_df.iloc[i]['ticker']
        if ticker in alphas_df.index:
            alpha_scores = alphas_df.loc[ticker]
            X.loc[i, 'avg_alpha'] = np.mean(list(alpha_scores.values()))
    
    probs = model.predict_proba(X)[:, 1]
    return probs
    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    X, _, _ = prepare_stacking_data(new_signals_df.fillna(0))
    probs = model.predict_proba(X)[:, 1]
    return probs

if __name__ == '__main__':
    train_stacker()