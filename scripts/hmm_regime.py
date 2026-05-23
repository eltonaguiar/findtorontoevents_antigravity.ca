# hmm_regime.py - Detect market regime using HMM on SPY/VIX data
# Run daily via cron/batch or GitHub Actions
# Requirements: pip install yfinance numpy hmmlearn requests
#
# NOTE: The lm_market_regime table already exists with a RICHER schema
# managed by the worldclass regime detection system. This script UPDATES
# the existing row via API (ingest_regime) rather than direct DB.
# Columns: date, hmm_regime, hmm_confidence, vix_level, created_at

import yfinance as yf
import numpy as np
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import post_to_api
from config import API_BASE, ADMIN_KEY

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
    """Send HMM results to API (ingest_regime)."""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = post_to_api('ingest_regime', {
        'date': now,
        'hmm_regime': regime,
        'hmm_confidence': confidence,
        'vix_level': vix_value,
        'created_at': now,
    })
    return result

if __name__ == '__main__':
    regime, spy_ret, vix_value, confidence = detect_regime()
    insert_regime(regime, spy_ret, vix_value, confidence)
    print(f'Detected regime: {regime} (confidence: {confidence:.2f}, VIX: {vix_value:.1f})')
