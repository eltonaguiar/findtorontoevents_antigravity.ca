# monte_carlo_paths.py - Monte Carlo simulation for risk paths
# Requirements: pip install numpy pandas yfinance mysql-connector-python

import os
import numpy as np
import pandas as pd
import yfinance as yf
import mysql.connector

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )

def fetch_returns(ticker, period='5y'):
    data = yf.download(ticker, period=period)['Adj Close']
    returns = data.pct_change().dropna()
    return returns

def monte_carlo_sim(returns, num_sim=1000, horizon=252):
    mu = returns.mean()
    sigma = returns.std()
    
    simulations = np.zeros((horizon, num_sim))
    simulations[0] = 1.0  # Start at 1
    
    for t in range(1, horizon):
        simulations[t] = simulations[t-1] * (1 + np.random.normal(mu, sigma, num_sim))
    
    return simulations

def compute_risk_metrics(simulations):
    final = simulations[-1]
    var_95 = np.percentile(final, 5)
    cvar_95 = final[final <= var_95].mean()
    max_dd = np.min(simulations / np.maximum.accumulate(simulations) - 1, axis=0).mean()
    return {
        'var_95': var_95,
        'cvar_95': cvar_95,
        'avg_max_dd': max_dd
    }

def run_mc_for_portfolio():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    # Get current portfolio tickers from lm_trades
    cursor.execute("SELECT DISTINCT ticker FROM lm_trades WHERE status = 'open'")
    tickers = [row['ticker'] for row in cursor.fetchall()]
    
    if not tickers:
        print("No open positions")
        return
        
    portfolio_returns = pd.DataFrame()
    for t in tickers:
        rets = fetch_returns(t)
        portfolio_returns[t] = rets
    
    # Equal weight
    avg_returns = portfolio_returns.mean(axis=1)
    
    sims = monte_carlo_sim(avg_returns)
    metrics = compute_risk_metrics(sims)
    
    # Store in DB (add table if needed)
    print(metrics)
    
    conn.close()

if __name__ == '__main__':
    run_mc_for_portfolio()