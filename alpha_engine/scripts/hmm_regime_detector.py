#!/usr/bin/env python3
"""
GROK_XAI HMM Regime Detector
Fetches SPY/^VIX data, fits 4-state Gaussian HMM, determines current regime,
computes Hurst exponent, updates lm_market_regime table.
Run daily via cron/task scheduler.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
from hurst import compute_Hc
import mysql.connector
from datetime import datetime
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        # Fetch 2y daily data for SPY and VIX
        tickers = ['SPY', '^VIX']
        data = yf.download(tickers, period='2y', interval='1d', progress=False)['Adj Close']
        data = data.dropna()
        
        if len(data) < 252:
            raise ValueError("Insufficient data points")
        
        logging.info(f"Fetched {len(data)} days of data")
        
        # Compute log returns (%)
        rets = np.log(data / data.shift(1)).dropna() * 100
        
        # Features: [SPY_ret, VIX_ret]
        X = np.column_stack([rets['SPY'], rets['^VIX']])
        
        # Fit 4-state Gaussian HMM (crash, bear, sideways, bull)
        model = GaussianHMM(n_components=4, covariance_type="diag", n_iter=1000, random_state=42)
        model.fit(X)
        
        # Predict regimes
        regimes = model.predict(X)
        regime_probs = model.predict_proba(X)
        
        # Current regime (latest)
        current_regime_idx = regimes[-1]
        regime_conf = np.max(regime_probs[-1])
        
        # Map states to names based on mean returns (SPY high/low, VIX low/high)
        state_means = model.means_
        # Sort states by SPY mean ret desc, VIX asc (bull: high SPY low VIX)
        state_scores = state_means[:,0] / (state_means[:,1] + 1e-6)  # SPY / VIX proxy
        regime_order = np.argsort(-state_scores)  # desc
        
        regime_names = ['crash', 'bear', 'sideways', 'bull']
        regime_name = regime_names[regime_order[current_regime_idx]]
        
        logging.info(f"Current regime: {regime_name} (state {current_regime_idx}, conf {regime_conf:.2f})")
        
        # Hurst exponent on SPY returns (trending >0.55, mean-rev <0.45)
        hc_result = compute_Hc(rets['SPY'].dropna(), kind='price', min_window=10)
        hurst_exp = hc_result[0]
        
        logging.info(f"Hurst exponent: {hurst_exp:.4f}")
        
        # Latest VIX
        latest_vix = data['^VIX'].iloc[-1]
        latest_date = data.index[-1].normalize().date()
        
        # Update DB
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'antigravity'
        }
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor()
        
        update_sql = """REPLACE INTO lm_market_regime 
            (date, hmm_regime, hmm_confidence, hurst, vix_level) 
            VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(update_sql, (latest_date, regime_name, regime_conf, hurst_exp, latest_vix))
        cnx.commit()
        cursor.close()
        cnx.close()
        
        logging.info(f"Updated lm_market_regime for {latest_date}")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
