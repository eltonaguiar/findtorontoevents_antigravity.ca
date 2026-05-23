# corr_pruner.py - Prune highly correlated top picks from active signals
# Requirements: pip install yfinance numpy requests
#
# Uses call_api('list') to get active signals instead of direct DB.
# Keeps yfinance price fetching and correlation pruning logic.
# Output to local data/pruned_picks.json for dashboard consumption.

import yfinance as yf
import numpy as np
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import call_api

def get_top_picks(limit=50):
    """Get top active signals by strength from API (list)."""
    data = call_api('list')
    if not data or not data.get('ok'):
        return []
    items = data.get('signals', data.get('list', data.get('data', [])))
    if not items:
        return []
    # Sort by signal_strength descending, take symbols
    if isinstance(items, list):
        with_strength = [(x.get('symbol', x.get('ticker', '')), float(x.get('signal_strength', 0))) for x in items if x.get('symbol') or x.get('ticker')]
        with_strength.sort(key=lambda t: t[1], reverse=True)
        return [t[0] for t in with_strength[:limit]]
    return []

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
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, '..', 'data')
    data_dir = os.path.normpath(data_dir)
    out_path = os.path.join(data_dir, 'pruned_picks.json')

    top_picks = get_top_picks(50)
    if not top_picks:
        print('No active signals found.')
        os.makedirs(data_dir, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump([], f)
        return

    prices, tickers = fetch_prices(top_picks)
    if len(tickers) < 2:
        pruned = tickers
    else:
        pruned = prune_correlated(prices, tickers)

    os.makedirs(data_dir, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(pruned, f)
    print(f'Pruned {len(top_picks)} to {len(pruned)} picks')


if __name__ == '__main__':
    main()
