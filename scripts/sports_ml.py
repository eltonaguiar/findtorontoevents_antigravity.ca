# sports_ml.py - ML models for sports betting
# Requirements: pip install scikit-learn pandas numpy mysql-connector-python requests

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import mysql.connector
import requests

# DB config (sports DB)
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_sportsbet')
DB_PASS = os.getenv('DB_PASS', 'eltonsportsbets')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_sportsbet')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_historical_bets():
    conn = connect_db()
    query = """
    SELECT * FROM lm_sports_bets 
    WHERE result IN ('win', 'loss')
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def train_sports_model():
    df = fetch_historical_bets()
    if len(df) < 50:
        print("Insufficient data")
        return None
        
    # Features: ev_pct, confidence, odds, etc.
    features = ['ev_pct', 'confidence_score', 'odds', 'win_prob']
    X = df[features].fillna(0)
    y = (df['result'] == 'win').astype(int)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Sports Model Accuracy: {acc:.2f}")
    
    # Save or use model
    return model

def predict_bet_outcome(features_dict):
    model = train_sports_model()  # Or load saved
    if model is None:
        return 0.5
        
    df = pd.DataFrame([features_dict])
    prob = model.predict_proba(df)[0,1]
    return prob

if __name__ == '__main__':
    train_sports_model()