#!/usr/bin/env python3
"""
Transfer Entropy Analyzer — Find true causal relationships between assets.

Unlike correlation (symmetric), transfer entropy measures DIRECTIONAL information flow:
  - "BTC price movements contain 0.15 bits of info about ETH's next move"
  - "But ETH contains only 0.02 bits about BTC"
  → BTC LEADS ETH, not the other way around

This is a core technique at Renaissance Technologies and DE Shaw.

Applications:
  1. Find which assets lead others (lead-lag relationships)
  2. Identify which of your 23 algorithms have TRUE predictive power
  3. Weight cross-asset signals by causal strength
  4. Build causal graph for GNN (Sprint 4)

Pipeline:
  1. Fetch historical returns for all tracked assets (yfinance)
  2. Compute pairwise transfer entropy
  3. Build lead-lag matrix
  4. Post causal relationships to world_class_intelligence.php

Requires: pip install numpy pandas yfinance requests
Optional: pip install pyinform (for faster computation)
Runs via: python run_all.py --entropy
"""
import sys
import os
import json
import logging
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
from itertools import combinations

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS

logger = logging.getLogger('transfer_entropy')

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

# Check for pyinform (optional, faster)
try:
    from pyinform import transfer_entropy as te_func
    PYINFORM_AVAILABLE = True
except ImportError:
    PYINFORM_AVAILABLE = False

# Cross-asset tickers to test lead-lag relationships
CROSS_ASSET_TICKERS = [
    'SPY',      # US equities
    'QQQ',      # Tech
    'IWM',      # Small cap
    'TLT',      # Long-term bonds
    'GLD',      # Gold
    'UUP',      # US Dollar
    'BTC-USD',  # Bitcoin
    'ETH-USD',  # Ethereum
    '^VIX',     # Volatility
]


# ---------------------------------------------------------------------------
# Transfer Entropy Computation
# ---------------------------------------------------------------------------

def discretize_returns(returns, n_bins=3):
    """
    Discretize continuous returns into bins for transfer entropy.
    3 bins: down (-1), flat (0), up (+1)
    """
    thresholds = np.percentile(returns, [33.33, 66.67])
    discretized = np.digitize(returns, thresholds)
    return discretized.astype(int)


def compute_transfer_entropy_numpy(source, target, k=5):
    """
    Compute transfer entropy from source → target using numpy.

    TE(X→Y) = H(Y_future | Y_past) - H(Y_future | Y_past, X_past)

    Higher TE = source contains more information about target's future.

    Args:
        source: discretized time series (array of ints)
        target: discretized time series (array of ints)
        k: history length (number of past values to consider)

    Returns: float (transfer entropy in bits)
    """
    n = len(source)
    if n < k + 2:
        return 0.0

    # Build joint and marginal distributions
    # We need: p(y_t+1, y_t:t-k, x_t:t-k) and marginals
    joint_counts = {}
    target_past_counts = {}
    target_past_source_counts = {}
    target_future_past_counts = {}

    for t in range(k, n - 1):
        y_future = target[t + 1]
        y_past = tuple(target[t - k + 1:t + 1])
        x_past = tuple(source[t - k + 1:t + 1])

        # Joint: (y_future, y_past, x_past)
        joint_key = (y_future, y_past, x_past)
        joint_counts[joint_key] = joint_counts.get(joint_key, 0) + 1

        # Marginal: (y_past, x_past)
        ypxp_key = (y_past, x_past)
        target_past_source_counts[ypxp_key] = target_past_source_counts.get(ypxp_key, 0) + 1

        # Marginal: (y_future, y_past)
        yfyp_key = (y_future, y_past)
        target_future_past_counts[yfyp_key] = target_future_past_counts.get(yfyp_key, 0) + 1

        # Marginal: (y_past)
        target_past_counts[y_past] = target_past_counts.get(y_past, 0) + 1

    total = n - k - 1
    if total <= 0:
        return 0.0

    # Compute TE = sum p(y_t+1, y_past, x_past) * log2(
    #   p(y_t+1 | y_past, x_past) / p(y_t+1 | y_past)
    # )
    te = 0.0
    for (y_f, y_p, x_p), count in joint_counts.items():
        p_joint = count / total
        p_ypxp = target_past_source_counts.get((y_p, x_p), 1) / total
        p_yfyp = target_future_past_counts.get((y_f, y_p), 1) / total
        p_yp = target_past_counts.get(y_p, 1) / total

        # TE contribution
        if p_ypxp > 0 and p_yp > 0:
            ratio = (p_joint * p_yp) / (p_ypxp * p_yfyp) if p_yfyp > 0 else 1.0
            if ratio > 0:
                te += p_joint * np.log2(ratio)

    return max(0.0, te)  # TE is non-negative


def compute_transfer_entropy(source, target, k=5):
    """Compute TE using pyinform if available, else numpy fallback."""
    if PYINFORM_AVAILABLE:
        try:
            return float(te_func.transfer_entropy(source, target, k=k))
        except Exception:
            pass
    return compute_transfer_entropy_numpy(source, target, k=k)


# ---------------------------------------------------------------------------
# Lead-Lag Analysis
# ---------------------------------------------------------------------------

def compute_lead_lag_matrix(returns_df, k=5):
    """
    Compute pairwise transfer entropy matrix for all assets.

    Returns: DataFrame where entry [i,j] = TE from asset i → asset j
    (how much asset i's past predicts asset j's future)
    """
    tickers = returns_df.columns.tolist()
    n = len(tickers)
    te_matrix = np.zeros((n, n))

    # Discretize all series
    discretized = {}
    for ticker in tickers:
        discretized[ticker] = discretize_returns(returns_df[ticker].values)

    total_pairs = n * (n - 1)
    computed = 0

    for i, source_ticker in enumerate(tickers):
        for j, target_ticker in enumerate(tickers):
            if i == j:
                continue

            te_val = compute_transfer_entropy(
                discretized[source_ticker],
                discretized[target_ticker],
                k=k
            )
            te_matrix[i, j] = te_val
            computed += 1

            if computed % 20 == 0:
                logger.info("    Computed %d/%d pairs...", computed, total_pairs)

    return pd.DataFrame(te_matrix, index=tickers, columns=tickers)


def find_leading_indicators(te_matrix):
    """
    Identify which assets are leading indicators for others.

    An asset is a "leader" if its outgoing TE (row sum) is much higher
    than its incoming TE (column sum).

    Returns: list of {ticker, outgoing_te, incoming_te, net_te, role}
    """
    results = []

    for ticker in te_matrix.index:
        outgoing = float(te_matrix.loc[ticker].sum())  # How much this predicts others
        incoming = float(te_matrix[ticker].sum())        # How much others predict this
        net = outgoing - incoming

        if net > 0.01:
            role = 'LEADER'
        elif net < -0.01:
            role = 'FOLLOWER'
        else:
            role = 'NEUTRAL'

        results.append({
            'ticker': ticker,
            'outgoing_te': round(outgoing, 6),
            'incoming_te': round(incoming, 6),
            'net_te': round(net, 6),
            'role': role,
        })

    return sorted(results, key=lambda x: x['net_te'], reverse=True)


def find_strongest_pairs(te_matrix, top_n=15):
    """Find the strongest directional relationships."""
    pairs = []

    for source in te_matrix.index:
        for target in te_matrix.columns:
            if source == target:
                continue

            te_forward = float(te_matrix.loc[source, target])
            te_backward = float(te_matrix.loc[target, source])
            asymmetry = te_forward - te_backward

            if te_forward > 0.001:  # Only meaningful relationships
                pairs.append({
                    'source': source,
                    'target': target,
                    'te': round(te_forward, 6),
                    'te_reverse': round(te_backward, 6),
                    'asymmetry': round(asymmetry, 6),
                    'description': f"{source} → {target}: {te_forward:.4f} bits"
                })

    return sorted(pairs, key=lambda x: x['asymmetry'], reverse=True)[:top_n]


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_transfer_entropy():
    """Run transfer entropy analysis on cross-asset relationships."""
    logger.info("=" * 60)
    logger.info("TRANSFER ENTROPY ANALYZER — Starting")
    logger.info("  Engine: %s", "pyinform" if PYINFORM_AVAILABLE else "numpy (slower)")
    logger.info("=" * 60)

    if not YF_AVAILABLE:
        logger.error("yfinance not installed")
        return {}

    # Fetch historical returns
    all_tickers = list(set(CROSS_ASSET_TICKERS + TRACKED_TICKERS[:6]))
    logger.info("  Fetching data for %d tickers...", len(all_tickers))

    try:
        data = yf.download(all_tickers, period='1y', progress=False)
        if data.empty:
            logger.error("No data returned")
            return {}

        if isinstance(data.columns, pd.MultiIndex):
            prices = data['Adj Close']
        else:
            prices = data

        # Drop tickers with too much missing data
        valid = prices.columns[prices.notna().sum() > len(prices) * 0.8]
        prices = prices[valid].dropna()
        returns = prices.pct_change().dropna()

        logger.info("  Got %d days of returns for %d tickers", len(returns), len(returns.columns))

    except Exception as e:
        logger.error("Data fetch failed: %s", e)
        return {}

    if len(returns.columns) < 3:
        logger.error("Need at least 3 tickers with valid data")
        return {}

    # Compute transfer entropy matrix
    logger.info("")
    logger.info("--- Computing Transfer Entropy Matrix ---")
    logger.info("  This may take 1-3 minutes for %d pairs...",
                 len(returns.columns) * (len(returns.columns) - 1))

    te_matrix = compute_lead_lag_matrix(returns, k=5)

    # Find leaders and followers
    logger.info("")
    logger.info("--- Lead-Lag Analysis ---")
    leaders = find_leading_indicators(te_matrix)

    for asset in leaders:
        emoji = {'LEADER': '>>>', 'FOLLOWER': '<<<', 'NEUTRAL': '==='}
        logger.info("  [%s] %-10s out=%.4f in=%.4f net=%+.4f",
                     emoji.get(asset['role'], '???'),
                     asset['ticker'],
                     asset['outgoing_te'],
                     asset['incoming_te'],
                     asset['net_te'])

    # Find strongest directional pairs
    logger.info("")
    logger.info("--- Strongest Directional Relationships ---")
    strongest = find_strongest_pairs(te_matrix, top_n=15)

    for pair in strongest[:10]:
        arrow = '>>>' if pair['asymmetry'] > 0.005 else ' → '
        logger.info("  %s %s %s  (TE=%.4f, reverse=%.4f, asymmetry=%+.4f)",
                     pair['source'], arrow, pair['target'],
                     pair['te'], pair['te_reverse'], pair['asymmetry'])

    # Post to API
    payload = {
        'source': 'transfer_entropy',
        'leaders': leaders,
        'strongest_pairs': strongest,
        'te_matrix': {
            row: {col: round(float(te_matrix.loc[row, col]), 6)
                  for col in te_matrix.columns if float(te_matrix.loc[row, col]) > 0.001}
            for row in te_matrix.index
        },
        'tickers_analyzed': list(returns.columns),
        'data_points': len(returns),
        'history_length_k': 5,
        'engine': 'pyinform' if PYINFORM_AVAILABLE else 'numpy',
        'computed_at': datetime.utcnow().isoformat(),
    }

    api_result = post_to_api('ingest_regime', payload)
    if api_result.get('ok'):
        logger.info("Transfer entropy data posted to API")
    else:
        logger.warning("API post error: %s", api_result.get('error', 'unknown'))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TRANSFER ENTROPY SUMMARY")
    logger.info("  Tickers analyzed: %d", len(returns.columns))
    logger.info("  Pairs computed: %d", len(returns.columns) * (len(returns.columns) - 1))

    top_leaders = [a for a in leaders if a['role'] == 'LEADER']
    top_followers = [a for a in leaders if a['role'] == 'FOLLOWER']

    if top_leaders:
        logger.info("  LEADERS (predict others): %s",
                     ', '.join(a['ticker'] for a in top_leaders[:5]))
    if top_followers:
        logger.info("  FOLLOWERS (predicted by others): %s",
                     ', '.join(a['ticker'] for a in top_followers[:5]))

    logger.info("=" * 60)

    return payload


def main():
    return run_transfer_entropy()


if __name__ == '__main__':
    main()
