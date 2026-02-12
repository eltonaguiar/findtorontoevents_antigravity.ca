# hmm_regime.py - Detect market regime using HMM on SPY/VIX data
# Run daily via cron/batch or GitHub Actions
# Requirements: pip install yfinance numpy hmmlearn mysql-connector-python
#
# NOTE: The lm_market_regime table already exists with a RICHER schema
# managed by the worldclass regime detection system. This script UPDATES
# the existing row rather than creating a new one, using the actual columns:
#   date, hmm_regime, hmm_confidence, vix_level, created_at
# The table also has: hurst, ewma_vol, composite_score, ticker_regimes, etc.
# Those are populated by the main regime system, not this script.

import yfinance as yf
import numpy as np
import mysql.connector
import datetime
import os
import json

# DB config - use env vars for security
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

def fetch_data(ticker, period='1y'):
    data = yf.download(ticker, period=period, progress=False)
    closes = data['Close'].dropna()
    vals = closes.values.flatten()
    returns = np.diff(vals) / vals[:-1]
    return returns.reshape(-1, 1)

def detect_regime():
    """Detect market regime using HMM on SPY returns + VIX levels."""
    try:
        from hmmlearn import hmm as hmmlearn_hmm
    except ImportError:
        print("hmmlearn not installed. pip install hmmlearn")
        return 'sideways', 0.0, 0.0, 0.5

    # Fetch data
    spy_rets = fetch_data('SPY')
    vix_data = yf.download('^VIX', period='1y', progress=False)
    vix_closes = vix_data['Close'].dropna()
    vix_vals = vix_closes.values.flatten()

    # Align lengths
    min_len = min(len(spy_rets), len(vix_vals))
    spy_rets = spy_rets[-min_len:]
    vix_vals = vix_vals[-min_len:].reshape(-1, 1)

    # Combine features: SPY returns and VIX levels
    features = np.column_stack([spy_rets, vix_vals])

    # Fit HMM (3 states: bull, bear, sideways)
    model = hmmlearn_hmm.GaussianHMM(n_components=3, covariance_type='diag', n_iter=1000)
    model.fit(features)

    # Predict current regime (last observation)
    current_features = features[-1].reshape(1, -1)
    state = model.predict(current_features)[0]

    # Map states (heuristic: lowest mean ret = bear, highest = bull, middle = sideways)
    means = model.means_[:, 0]  # SPY ret means
    state_map = {int(np.argmax(means)): 'bull', int(np.argmin(means)): 'bear'}
    regime = state_map.get(state, 'sideways')  # Default to sideways

    # Confidence: probability of the state
    probs = model.predict_proba(current_features)[0]
    confidence = float(probs[state])
    vix_current = float(vix_vals[-1][0])

    return regime, float(spy_rets[-1][0]), vix_current, confidence

def insert_regime(regime, spy_ret, vix_value, confidence):
    """Update the existing lm_market_regime row with HMM results.

    Uses the ACTUAL column names from the DB:
    - date (datetime), hmm_regime (varchar), hmm_confidence (decimal),
    - vix_level (decimal), created_at (datetime)
    """
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check if today's row exists
    cursor.execute("SELECT id FROM lm_market_regime ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    if row:
        # Update existing row with fresh HMM results
        cursor.execute("""
            UPDATE lm_market_regime
            SET hmm_regime = %s, hmm_confidence = %s, vix_level = %s, created_at = %s
            WHERE id = %s
        """, (regime, confidence, vix_value, now, row[0]))
    else:
        # Insert new row (first run)
        cursor.execute("""
            INSERT INTO lm_market_regime (date, hmm_regime, hmm_confidence, vix_level, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (now, regime, confidence, vix_value, now))

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == '__main__':
    regime, spy_ret, vix_value, confidence = detect_regime()
    insert_regime(regime, spy_ret, vix_value, confidence)
    print(f'Detected regime: {regime} (confidence: {confidence:.2f}, VIX: {vix_value:.1f})')
