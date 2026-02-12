# corr_pruner.py - Prune highly correlated top picks from active signals
# Requirements: pip install yfinance numpy mysql-connector-python
#
# NOTE: Queries the ACTUAL lm_signals table schema managed by live_signals.php.
# Column names: symbol, signal_strength (not ticker/confidence).
# Writes pruned list to data/pruned_picks.json for dashboard consumption.

import yfinance as yf
import numpy as np
import mysql.connector
import os
import json

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def get_top_picks(limit=50):
    """Get top active signals by strength from lm_signals (actual schema)."""
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT symbol FROM lm_signals WHERE status = 'active' ORDER BY signal_strength DESC LIMIT %s",
        (limit,))
    picks = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return picks

def fetch_prices(tickers, period='3mo'):
    """Fetch closing prices for tickers, drop any with insufficient data."""
    prices = {}
    for t in tickers:
        try:
            data = yf.download(t, period=period, progress=False)
            closes = data['Close'].dropna()
            if hasattr(closes, 'values'):
                vals = closes.values.flatten()
            else:
                vals = np.array(closes)
            if len(vals) > 20:
                prices[t] = vals
        except Exception:
            continue

    if not prices:
        return np.array([]), []

    # Align to same length (trim to shortest)
    min_len = min(len(p) for p in prices.values())
    for t in list(prices):
        prices[t] = prices[t][-min_len:]

    return np.column_stack(list(prices.values())), list(prices.keys())

def prune_correlated(prices, tickers, threshold=0.7):
    """Remove tickers with correlation > threshold, keeping higher-ranked ones."""
    if len(tickers) < 2:
        return tickers
    corr = np.corrcoef(prices, rowvar=False)
    np.fill_diagonal(corr, 0)
    to_keep = set(range(len(tickers)))
    for i in range(len(tickers)):
        if i not in to_keep:
            continue
        correlated = np.where(np.abs(corr[i]) > threshold)[0]
        for j in correlated:
            if j > i and j in to_keep:
                to_keep.remove(j)
    return [tickers[i] for i in sorted(to_keep)]

def main():
    """Main entry point for orchestrator integration."""
    top_picks = get_top_picks(50)
    if not top_picks:
        print('No active signals found.')
        os.makedirs('data', exist_ok=True)
        with open('data/pruned_picks.json', 'w') as f:
            json.dump([], f)
        return

    prices, tickers = fetch_prices(top_picks)
    if len(tickers) < 2:
        pruned = tickers
    else:
        pruned = prune_correlated(prices, tickers)

    os.makedirs('data', exist_ok=True)
    with open('data/pruned_picks.json', 'w') as f:
        json.dump(pruned, f)
    print(f'Pruned {len(top_picks)} to {len(pruned)} picks')\n\n    # PCA Alpha Decorrelation as per roadmap\n    from sklearn.decomposition import PCA\n    if len(pruned) > 0:\n        pruned_indices = [tickers.index(t) for t in pruned]\n        pruned_prices = prices[:, pruned_indices]\n        pca = PCA(n_components=5)\n        ortho = pca.fit_transform(pruned_prices)\n        with open('data/ortho.json', 'w') as f:\n            json.dump(ortho.tolist(), f)\n        print('PCA orthogonalized signals saved to data/ortho.json')


if __name__ == '__main__':
    main()
