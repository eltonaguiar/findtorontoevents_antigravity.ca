#!/usr/bin/env python3
"""
Algorithm Consolidator — Redundancy, Correlation & Orthogonality Analyzer
==========================================================================
Analyzes all 23 trading algorithms for signal correlation, return stream
correlation, orthogonality, and performance — then recommends which to
keep, merge, or remove.

Thesis (from research):
  "You don't have 91 alphas. You have 6 ideas with parameter tweaks."
  "Cut 60% of algorithms. Edge scales when capital isn't diluted
   across correlated bets."
  "You need 3-5 orthogonal, high-quality, capital-efficient strategies."

Data sources:
  - lm_signals: signal history (algorithm_name, signal_type, signal_time)
  - lm_trades:  closed trade outcomes (algorithm_name, realized_pct, exit_time)
  - lm_algo_performance: rolling performance stats (if available)

Output:
  - data/algorithm_consolidation_report.json
  - Stdout: detailed analysis with recommendations

Usage:
  python scripts/algorithm_consolidator.py
  python scripts/algorithm_consolidator.py --days 60 --min-trades 5
  python scripts/algorithm_consolidator.py --dry-run

Requirements: pip install mysql-connector-python pandas numpy requests
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────

DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'data')

# ─────────────────────────────────────────────────
#  THE 23 ALGORITHMS & CATEGORY GROUPS
# ─────────────────────────────────────────────────

ALL_ALGORITHMS = [
    'Momentum Burst', 'Breakout 24h', 'Volatility Breakout', 'Trend Sniper',
    'VAM', 'ADX Trend Strength',
    'RSI Reversal', 'DCA Dip', 'Dip Recovery', 'Mean Reversion Sniper', 'RSI(2) Scalp',
    'Bollinger Squeeze', 'MACD Crossover', 'StochRSI Crossover', 'Awesome Oscillator',
    'Ichimoku Cloud',
    'Insider Cluster Buy', '13F New Position', 'Sentiment Divergence', 'Contrarian Fear/Greed',
    'Consensus', 'Alpha Predator', 'Volume Spike',
]

CATEGORY_GROUPS = {
    'MOMENTUM': ['Momentum Burst', 'Breakout 24h', 'Volatility Breakout',
                 'Trend Sniper', 'VAM', 'ADX Trend Strength'],
    'REVERSION': ['RSI Reversal', 'DCA Dip', 'Dip Recovery',
                  'Mean Reversion Sniper', 'RSI(2) Scalp'],
    'TECHNICAL': ['Bollinger Squeeze', 'MACD Crossover', 'StochRSI Crossover',
                  'Awesome Oscillator', 'Ichimoku Cloud'],
    'FUNDAMENTAL': ['Insider Cluster Buy', '13F New Position',
                    'Sentiment Divergence', 'Contrarian Fear/Greed'],
    'META': ['Consensus', 'Alpha Predator', 'Volume Spike'],
}

# Reverse lookup: algorithm -> category
ALGO_TO_CATEGORY = {}
for cat, algos in CATEGORY_GROUPS.items():
    for algo in algos:
        ALGO_TO_CATEGORY[algo] = cat

# Composite score weights
COMPOSITE_WEIGHTS = {
    'sharpe': 0.30,
    'win_rate': 0.30,
    'profit_factor': 0.20,
    'orthogonality': 0.20,
}

# Correlation threshold: pairs above this are flagged REDUNDANT
CORR_THRESHOLD = 0.70


# ─────────────────────────────────────────────────
#  DATABASE CONNECTION
# ─────────────────────────────────────────────────

def connect_db():
    """Connect to MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


# ─────────────────────────────────────────────────
#  DATA FETCHING
# ─────────────────────────────────────────────────

def fetch_signals(conn, lookback_days=90):
    """
    Fetch all signals from lm_signals for the analysis period.

    Returns list of dicts with keys:
        algorithm_name, signal_type, signal_time, symbol, asset_class, signal_strength
    """
    import mysql.connector
    print(f"  Fetching signals from last {lookback_days} days...")
    cursor = conn.cursor(dictionary=True)
    cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT algorithm_name, signal_type, signal_time, symbol,
               asset_class, signal_strength
        FROM lm_signals
        WHERE algorithm_name != ''
          AND signal_time >= %s
        ORDER BY signal_time ASC
    """, (cutoff,))
    rows = cursor.fetchall()
    cursor.close()
    print(f"  -> {len(rows)} signals fetched")
    return rows


def fetch_closed_trades(conn, lookback_days=90):
    """
    Fetch all closed trades from lm_trades for the analysis period.

    Returns list of dicts with keys:
        algorithm_name, symbol, asset_class, realized_pnl_usd, realized_pct,
        entry_time, exit_time, position_value_usd, direction, exit_reason
    """
    print(f"  Fetching closed trades from last {lookback_days} days...")
    cursor = conn.cursor(dictionary=True)
    cutoff = (datetime.utcnow() - timedelta(days=lookback_days)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT algorithm_name, symbol, asset_class,
               realized_pnl_usd, realized_pct,
               entry_time, exit_time,
               position_value_usd, direction, exit_reason
        FROM lm_trades
        WHERE status = 'closed'
          AND algorithm_name != ''
          AND exit_time >= %s
        ORDER BY exit_time ASC
    """, (cutoff,))
    rows = cursor.fetchall()
    cursor.close()
    print(f"  -> {len(rows)} closed trades fetched")
    return rows


def fetch_algo_performance(conn):
    """
    Fetch rolling performance stats from lm_algo_performance (if table exists).
    Returns list of dicts or empty list if table does not exist.
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT algorithm_name, calc_date, win_rate, avg_return_pct,
                   total_trades, sharpe_ratio
            FROM lm_algo_performance
            ORDER BY calc_date DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Exception:
        return []


# ─────────────────────────────────────────────────
#  1. SIGNAL CORRELATION ANALYSIS
# ─────────────────────────────────────────────────

def encode_signal_direction(signal_type):
    """Map signal_type string to numeric direction."""
    st = (signal_type or '').upper().strip()
    if st in ('BUY', 'STRONG_BUY', 'STRONG BUY'):
        return 1
    elif st in ('SHORT', 'SELL', 'STRONG_SELL', 'STRONG SELL'):
        return -1
    return 0


def build_signal_matrix(signals):
    """
    Build a date x algorithm matrix of signal directions.

    For each day and algorithm, aggregate:
      +1 if net BUY signals, -1 if net SHORT signals, 0 otherwise.

    Returns (matrix_dict, sorted_dates, sorted_algos) where
    matrix_dict[date][algo] = encoded_value.
    """
    import numpy as np

    daily_signals = defaultdict(lambda: defaultdict(int))
    algo_set = set()

    for sig in signals:
        algo = sig['algorithm_name']
        algo_set.add(algo)
        # Normalize to date string
        st = sig['signal_time']
        if isinstance(st, datetime):
            date_str = st.strftime('%Y-%m-%d')
        else:
            date_str = str(st)[:10]
        direction = encode_signal_direction(sig['signal_type'])
        daily_signals[date_str][algo] += direction

    sorted_dates = sorted(daily_signals.keys())
    sorted_algos = sorted(algo_set)

    if not sorted_dates or not sorted_algos:
        return np.array([]), sorted_dates, sorted_algos

    # Build numpy matrix: rows=dates, cols=algos
    matrix = np.zeros((len(sorted_dates), len(sorted_algos)))
    algo_idx = {a: i for i, a in enumerate(sorted_algos)}
    for d_i, date in enumerate(sorted_dates):
        for algo, val in daily_signals[date].items():
            matrix[d_i, algo_idx[algo]] = np.sign(val)  # Clip to -1/0/+1

    return matrix, sorted_dates, sorted_algos


def compute_signal_correlation(signals):
    """
    Build correlation matrix of algorithm signals.

    Returns (corr_matrix as dict-of-dicts, algo_list) or (None, [])
    if insufficient data.
    """
    import numpy as np

    matrix, dates, algos = build_signal_matrix(signals)
    if len(algos) < 2 or len(dates) < 5:
        print("  WARNING: Insufficient signal data for correlation analysis")
        return None, algos

    print(f"  Signal matrix: {len(dates)} days x {len(algos)} algorithms")

    # Remove algorithms with zero variance (never fired)
    variances = np.var(matrix, axis=0)
    active_mask = variances > 0
    active_algos = [a for a, m in zip(algos, active_mask) if m]
    active_matrix = matrix[:, active_mask]

    if len(active_algos) < 2:
        print("  WARNING: Fewer than 2 algorithms with signal variance")
        return None, active_algos

    # Pearson correlation
    corr = np.corrcoef(active_matrix, rowvar=False)
    np.fill_diagonal(corr, 1.0)

    # Convert to dict-of-dicts for easier access
    corr_dict = {}
    for i, a1 in enumerate(active_algos):
        corr_dict[a1] = {}
        for j, a2 in enumerate(active_algos):
            val = corr[i, j]
            # Handle NaN from constant columns
            corr_dict[a1][a2] = round(float(val), 4) if not math.isnan(val) else 0.0

    return corr_dict, active_algos


# ─────────────────────────────────────────────────
#  2. RETURN STREAM CORRELATION
# ─────────────────────────────────────────────────

def compute_return_correlation(trades):
    """
    Correlate actual PnL streams between algorithms.
    Builds a daily PnL time series per algorithm from closed trades,
    then computes Pearson correlation.

    Returns (corr_dict, algo_list) or (None, []) if insufficient data.
    """
    import numpy as np

    # Group trades by algo and exit date
    daily_pnl = defaultdict(lambda: defaultdict(float))
    algo_set = set()
    date_set = set()

    for trade in trades:
        algo = trade['algorithm_name']
        algo_set.add(algo)
        et = trade['exit_time']
        if isinstance(et, datetime):
            date_str = et.strftime('%Y-%m-%d')
        else:
            date_str = str(et)[:10]
        date_set.add(date_str)

        pct = float(trade['realized_pct'] or 0)
        daily_pnl[date_str][algo] += pct

    sorted_dates = sorted(date_set)
    sorted_algos = sorted(algo_set)

    if len(sorted_algos) < 2 or len(sorted_dates) < 5:
        print("  WARNING: Insufficient trade data for return correlation analysis")
        return None, sorted_algos

    print(f"  Return matrix: {len(sorted_dates)} days x {len(sorted_algos)} algorithms")

    # Build numpy matrix
    matrix = np.zeros((len(sorted_dates), len(sorted_algos)))
    algo_idx = {a: i for i, a in enumerate(sorted_algos)}
    for d_i, date in enumerate(sorted_dates):
        for algo, pnl in daily_pnl[date].items():
            matrix[d_i, algo_idx[algo]] = pnl

    # Remove algos with zero variance
    variances = np.var(matrix, axis=0)
    active_mask = variances > 0
    active_algos = [a for a, m in zip(sorted_algos, active_mask) if m]
    active_matrix = matrix[:, active_mask]

    if len(active_algos) < 2:
        print("  WARNING: Fewer than 2 algorithms with return variance")
        return None, active_algos

    corr = np.corrcoef(active_matrix, rowvar=False)
    np.fill_diagonal(corr, 1.0)

    corr_dict = {}
    for i, a1 in enumerate(active_algos):
        corr_dict[a1] = {}
        for j, a2 in enumerate(active_algos):
            val = corr[i, j]
            corr_dict[a1][a2] = round(float(val), 4) if not math.isnan(val) else 0.0

    return corr_dict, active_algos


# ─────────────────────────────────────────────────
#  3. ORTHOGONALITY SCORING
# ─────────────────────────────────────────────────

def compute_orthogonality_scores(signal_corr, return_corr):
    """
    For each algorithm, compute orthogonality score:
        orthogonality = 1 - avg(abs(correlation)) with all other algos

    Blends signal and return correlations (60% return, 40% signal)
    since return correlation is more important for capital allocation.

    Returns dict of algo -> orthogonality score (0-1, higher = more unique).
    """
    scores = {}

    # Collect all algorithms across both matrices
    all_algos = set()
    if signal_corr:
        all_algos.update(signal_corr.keys())
    if return_corr:
        all_algos.update(return_corr.keys())

    for algo in all_algos:
        sig_orth = None
        ret_orth = None

        # Signal orthogonality
        if signal_corr and algo in signal_corr:
            other_corrs = [abs(v) for k, v in signal_corr[algo].items() if k != algo]
            if other_corrs:
                sig_orth = 1.0 - (sum(other_corrs) / len(other_corrs))

        # Return orthogonality
        if return_corr and algo in return_corr:
            other_corrs = [abs(v) for k, v in return_corr[algo].items() if k != algo]
            if other_corrs:
                ret_orth = 1.0 - (sum(other_corrs) / len(other_corrs))

        # Blend: 60% return correlation, 40% signal correlation
        if ret_orth is not None and sig_orth is not None:
            scores[algo] = round(0.6 * ret_orth + 0.4 * sig_orth, 4)
        elif ret_orth is not None:
            scores[algo] = round(ret_orth, 4)
        elif sig_orth is not None:
            scores[algo] = round(sig_orth, 4)
        else:
            scores[algo] = 0.5  # Default: neutral

    return scores


# ─────────────────────────────────────────────────
#  4. PERFORMANCE RANKING
# ─────────────────────────────────────────────────

def compute_algo_rankings(trades, orthogonality_scores, min_trades=10):
    """
    Rank algorithms by composite performance + uniqueness.

    For each algorithm, computes:
      - Win rate
      - Average PnL per trade (%)
      - Sharpe ratio (mean/stdev of per-trade returns)
      - Profit factor (sum of wins / abs(sum of losses))
      - Trade count (sample size)
      - Orthogonality score (from correlation analysis)

    Composite = 0.30*Sharpe_norm + 0.30*WinRate + 0.20*PF_norm + 0.20*Orthogonality

    Returns sorted list of dicts (highest composite first).
    """
    import numpy as np

    algo_trades = defaultdict(list)
    for t in trades:
        algo_trades[t['algorithm_name']].append(float(t['realized_pct'] or 0))

    rankings = []
    for algo, returns in algo_trades.items():
        n = len(returns)
        returns_arr = np.array(returns)

        wins = returns_arr[returns_arr > 0]
        losses = returns_arr[returns_arr <= 0]

        win_rate = len(wins) / n if n > 0 else 0
        avg_pnl = float(np.mean(returns_arr))
        std_pnl = float(np.std(returns_arr))

        # Sharpe ratio (per-trade, not annualized — we don't know trade frequency)
        sharpe = avg_pnl / std_pnl if std_pnl > 0 else 0.0

        # Profit factor
        total_wins = float(np.sum(wins)) if len(wins) > 0 else 0.0
        total_losses = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else (
            float('inf') if total_wins > 0 else 0.0
        )

        # Max drawdown of cumulative PnL series
        cum_pnl = np.cumsum(returns_arr)
        running_max = np.maximum.accumulate(cum_pnl)
        drawdowns = cum_pnl - running_max
        max_dd = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Expectancy: (WR * avg_win) - (LR * avg_loss)
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        avg_loss = float(np.abs(np.mean(losses))) if len(losses) > 0 else 0.0
        loss_rate = 1.0 - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

        orth = orthogonality_scores.get(algo, 0.5)
        category = ALGO_TO_CATEGORY.get(algo, 'UNKNOWN')

        # Composite score (normalize each component to 0-1 range)
        sharpe_norm = min(2.0, max(-1.0, sharpe)) / 2.0  # [-1,2] -> [0,1]
        sharpe_norm = (sharpe_norm + 0.5) / 1.5  # Shift to keep positive range
        pf_norm = min(3.0, profit_factor) / 3.0  # [0,3] -> [0,1]

        composite = (
            COMPOSITE_WEIGHTS['sharpe'] * sharpe_norm +
            COMPOSITE_WEIGHTS['win_rate'] * win_rate +
            COMPOSITE_WEIGHTS['profit_factor'] * pf_norm +
            COMPOSITE_WEIGHTS['orthogonality'] * max(0, orth)
        )

        rankings.append({
            'algorithm': algo,
            'category': category,
            'trades': n,
            'win_rate': round(win_rate * 100, 1),
            'avg_pnl_pct': round(avg_pnl, 4),
            'sharpe': round(sharpe, 4),
            'profit_factor': round(min(99.99, profit_factor), 2),
            'max_drawdown_pct': round(max_dd, 2),
            'expectancy': round(expectancy, 4),
            'avg_win_pct': round(avg_win, 4),
            'avg_loss_pct': round(avg_loss, 4),
            'orthogonality': round(orth, 4),
            'composite_score': round(composite, 4),
            'sufficient_data': n >= min_trades,
        })

    return sorted(rankings, key=lambda x: x['composite_score'], reverse=True)


# ─────────────────────────────────────────────────
#  5. REDUNDANCY DETECTION
# ─────────────────────────────────────────────────

def find_redundant_pairs(signal_corr, return_corr, threshold=None):
    """
    Find all algorithm pairs with correlation above threshold.
    Uses return correlation primarily (more relevant for capital allocation),
    with signal correlation as supplementary evidence.

    Returns list of (algo1, algo2, return_corr, signal_corr, source).
    """
    if threshold is None:
        threshold = CORR_THRESHOLD
    pairs = []
    seen = set()

    # Return correlation pairs (primary)
    if return_corr:
        for a1 in return_corr:
            for a2 in return_corr[a1]:
                if a1 >= a2:
                    continue
                pair_key = tuple(sorted([a1, a2]))
                if pair_key in seen:
                    continue
                r_corr = return_corr[a1][a2]
                s_corr = signal_corr.get(a1, {}).get(a2, 0.0) if signal_corr else 0.0
                if abs(r_corr) > threshold:
                    pairs.append((a1, a2, round(r_corr, 4), round(s_corr, 4), 'return'))
                    seen.add(pair_key)

    # Signal correlation pairs (catch cases not in return data)
    if signal_corr:
        for a1 in signal_corr:
            for a2 in signal_corr[a1]:
                if a1 >= a2:
                    continue
                pair_key = tuple(sorted([a1, a2]))
                if pair_key in seen:
                    continue
                s_corr = signal_corr[a1][a2]
                r_corr = return_corr.get(a1, {}).get(a2, 0.0) if return_corr else 0.0
                if abs(s_corr) > threshold:
                    pairs.append((a1, a2, round(r_corr, 4), round(s_corr, 4), 'signal'))
                    seen.add(pair_key)

    # Sort by highest absolute correlation
    pairs.sort(key=lambda x: max(abs(x[2]), abs(x[3])), reverse=True)
    return pairs


# ─────────────────────────────────────────────────
#  6. CONSOLIDATION RECOMMENDATIONS
# ─────────────────────────────────────────────────

def generate_recommendations(rankings, signal_corr, return_corr,
                             redundant_pairs, min_trades=10,
                             max_keep=8):
    """
    Generate keep/merge/remove recommendations based on:
      - Performance data (rankings)
      - Redundancy (correlated pairs)
      - Insufficient data
      - Category diversity (ensure at least one from each category)

    Returns dict with 'keep', 'merge', 'remove', 'pause' lists.
    """
    rankings_by_name = {r['algorithm']: r for r in rankings}

    remove = []
    merge = []
    pause = []
    keep_candidates = []

    # ── Phase 1: Remove clearly poor algorithms ──
    for algo_info in rankings:
        algo = algo_info['algorithm']

        if algo_info['trades'] < min_trades:
            remove.append({
                'algorithm': algo,
                'reason': f"insufficient_data ({algo_info['trades']} trades < {min_trades})",
                'category': algo_info['category'],
            })
            continue

        if algo_info['win_rate'] < 30.0:
            remove.append({
                'algorithm': algo,
                'reason': f"poor_win_rate ({algo_info['win_rate']}%)",
                'category': algo_info['category'],
            })
            continue

        if algo_info['sharpe'] < -0.5:
            remove.append({
                'algorithm': algo,
                'reason': f"negative_sharpe ({algo_info['sharpe']})",
                'category': algo_info['category'],
            })
            continue

        if algo_info['expectancy'] < -1.0:
            remove.append({
                'algorithm': algo,
                'reason': f"negative_expectancy ({algo_info['expectancy']}%)",
                'category': algo_info['category'],
            })
            continue

        keep_candidates.append(algo_info)

    removed_names = set(r['algorithm'] for r in remove)

    # ── Phase 2: Handle correlated pairs among remaining ──
    merged_names = set()
    for a1, a2, r_corr, s_corr, source in redundant_pairs:
        if a1 in removed_names or a2 in removed_names:
            continue
        if a1 in merged_names or a2 in merged_names:
            continue

        r1 = rankings_by_name.get(a1)
        r2 = rankings_by_name.get(a2)
        if not r1 or not r2:
            continue

        # Keep the one with higher composite score
        corr_val = r_corr if source == 'return' else s_corr
        if r1['composite_score'] >= r2['composite_score']:
            loser = a2
            winner = a1
        else:
            loser = a1
            winner = a2

        merge.append({
            'algorithm': loser,
            'merge_into': winner,
            'reason': f"correlated_with_{winner} (r={abs(corr_val):.2f}, source={source})",
            'return_corr': r_corr,
            'signal_corr': s_corr,
            'category': rankings_by_name[loser]['category'],
        })
        merged_names.add(loser)

    # ── Phase 3: Build final KEEP list ──
    final_keep = []
    categories_represented = set()

    for algo_info in keep_candidates:
        algo = algo_info['algorithm']
        if algo in merged_names:
            continue
        final_keep.append(algo_info)
        categories_represented.add(algo_info['category'])

    # ── Phase 4: Ensure category diversity ──
    # If a category has zero representation, find the best from merge list
    for cat in CATEGORY_GROUPS:
        if cat not in categories_represented:
            # Find the best merged algo from this category
            cat_merged = [m for m in merge if m['category'] == cat]
            if cat_merged:
                # Rescue the best one
                rescued_name = cat_merged[0]['algorithm']
                rescued_info = rankings_by_name.get(rescued_name)
                if rescued_info:
                    final_keep.append(rescued_info)
                    merge = [m for m in merge if m['algorithm'] != rescued_name]
                    categories_represented.add(cat)
                    print(f"  Rescued '{rescued_name}' to ensure {cat} category represented")

    # ── Phase 5: Cap at max_keep — move excess to PAUSE ──
    if len(final_keep) > max_keep:
        # Sort by composite, keep top N
        final_keep.sort(key=lambda x: x['composite_score'], reverse=True)
        excess = final_keep[max_keep:]
        final_keep = final_keep[:max_keep]
        for ex in excess:
            pause.append({
                'algorithm': ex['algorithm'],
                'reason': f"exceeded_max_keep ({max_keep}), composite={ex['composite_score']}",
                'category': ex['category'],
                'composite_score': ex['composite_score'],
            })

    # Algorithms with no data at all (never appeared in signals/trades)
    seen_algos = set()
    for r in rankings:
        seen_algos.add(r['algorithm'])
    for algo in ALL_ALGORITHMS:
        if algo not in seen_algos:
            remove.append({
                'algorithm': algo,
                'reason': 'no_data (zero signals and zero trades in period)',
                'category': ALGO_TO_CATEGORY.get(algo, 'UNKNOWN'),
            })

    return {
        'keep': final_keep,
        'merge': merge,
        'remove': remove,
        'pause': pause,
    }


# ─────────────────────────────────────────────────
#  7. INTRA-GROUP ANALYSIS
# ─────────────────────────────────────────────────

def analyze_category_groups(rankings, signal_corr, return_corr):
    """
    For each category group, analyze internal correlation and
    identify which algorithm is the "representative" (best composite).

    Returns dict of category -> analysis.
    """
    rankings_by_name = {r['algorithm']: r for r in rankings}
    analysis = {}

    for cat, algos in CATEGORY_GROUPS.items():
        active_algos = [a for a in algos if a in rankings_by_name]
        if not active_algos:
            analysis[cat] = {
                'algorithms': algos,
                'active_count': 0,
                'representative': None,
                'avg_intra_corr': None,
                'note': 'No algorithms with trade data',
            }
            continue

        # Find intra-group correlation
        intra_corrs = []
        corr_source = return_corr if return_corr else signal_corr
        if corr_source:
            for i, a1 in enumerate(active_algos):
                for a2 in active_algos[i + 1:]:
                    if a1 in corr_source and a2 in corr_source.get(a1, {}):
                        intra_corrs.append(abs(corr_source[a1][a2]))

        avg_intra = round(sum(intra_corrs) / len(intra_corrs), 4) if intra_corrs else None

        # Best algorithm in group
        group_rankings = [rankings_by_name[a] for a in active_algos]
        group_rankings.sort(key=lambda x: x['composite_score'], reverse=True)
        best = group_rankings[0]

        analysis[cat] = {
            'algorithms': algos,
            'active_count': len(active_algos),
            'representative': best['algorithm'],
            'representative_composite': best['composite_score'],
            'avg_intra_correlation': avg_intra,
            'highly_correlated': avg_intra is not None and avg_intra > CORR_THRESHOLD,
            'rankings': [
                {
                    'algorithm': r['algorithm'],
                    'composite': r['composite_score'],
                    'win_rate': r['win_rate'],
                    'sharpe': r['sharpe'],
                    'trades': r['trades'],
                }
                for r in group_rankings
            ],
        }

    return analysis


# ─────────────────────────────────────────────────
#  8. REPORT GENERATION
# ─────────────────────────────────────────────────

def build_report(signal_corr, return_corr, orthogonality_scores,
                 rankings, recommendations, group_analysis,
                 redundant_pairs, lookback_days):
    """Build comprehensive JSON report."""
    optimal_core = [r['algorithm'] for r in recommendations['keep']]

    # Estimate improvements
    total_algos = len(ALL_ALGORITHMS)
    kept = len(recommendations['keep'])
    removed = len(recommendations['remove'])
    merged = len(recommendations['merge'])
    paused = len(recommendations['pause'])
    reduction_pct = round(100 * (1 - kept / total_algos), 1) if total_algos > 0 else 0

    report = {
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'analysis_period_days': lookback_days,
        'total_algorithms_analyzed': total_algos,

        'signal_correlation_matrix': signal_corr or {},
        'return_correlation_matrix': return_corr or {},
        'orthogonality_scores': orthogonality_scores,

        'redundant_pairs': [
            {
                'algo1': p[0], 'algo2': p[1],
                'return_corr': p[2], 'signal_corr': p[3],
                'detected_via': p[4],
            }
            for p in redundant_pairs
        ],

        'performance_rankings': rankings,
        'category_group_analysis': group_analysis,

        'recommendations': {
            'keep': [
                {
                    'algorithm': r['algorithm'],
                    'category': r['category'],
                    'composite_score': r['composite_score'],
                    'win_rate': r['win_rate'],
                    'sharpe': r['sharpe'],
                    'orthogonality': r['orthogonality'],
                    'trades': r['trades'],
                }
                for r in recommendations['keep']
            ],
            'merge': recommendations['merge'],
            'remove': recommendations['remove'],
            'pause': recommendations['pause'],
        },

        'optimal_core_set': optimal_core,

        'summary': {
            'total': total_algos,
            'keep': kept,
            'merge': merged,
            'remove': removed,
            'pause': paused,
            'algorithm_reduction_pct': reduction_pct,
        },

        'estimated_improvement': {
            'capital_efficiency': f"+{min(60, max(20, reduction_pct))}%",
            'description': (
                f"Consolidating from {total_algos} to {kept} algorithms "
                f"({reduction_pct}% reduction) concentrates capital on "
                f"orthogonal, proven strategies."
            ),
        },
    }

    return report


def print_report(report, recommendations, rankings, redundant_pairs,
                 orthogonality_scores, group_analysis, corr_threshold=CORR_THRESHOLD):
    """Print human-readable report to stdout."""
    print()
    print("=" * 72)
    print("  ALGORITHM CONSOLIDATION REPORT")
    print(f"  Generated: {report['timestamp']}")
    print(f"  Analysis period: {report['analysis_period_days']} days")
    print("=" * 72)

    # Summary
    s = report['summary']
    print(f"\n  Total algorithms: {s['total']}")
    print(f"  KEEP:   {s['keep']}")
    print(f"  MERGE:  {s['merge']}")
    print(f"  REMOVE: {s['remove']}")
    print(f"  PAUSE:  {s['pause']}")
    print(f"  Reduction: {s['algorithm_reduction_pct']}%")

    # Performance rankings
    print("\n" + "-" * 72)
    print("  PERFORMANCE RANKINGS (by composite score)")
    print("-" * 72)
    header = f"  {'#':>3} {'Algorithm':25s} {'Cat':10s} {'Trades':>6} {'WR%':>6} " \
             f"{'Sharpe':>7} {'PF':>6} {'Orth':>6} {'Comp':>6}"
    print(header)
    print("  " + "-" * 70)

    for i, r in enumerate(rankings, 1):
        flag = " *" if not r['sufficient_data'] else "  "
        print(f"  {i:3d} {r['algorithm']:25s} {r['category']:10s} "
              f"{r['trades']:6d} {r['win_rate']:5.1f}% "
              f"{r['sharpe']:7.3f} {r['profit_factor']:6.2f} "
              f"{r['orthogonality']:6.3f} {r['composite_score']:6.3f}{flag}")

    if any(not r['sufficient_data'] for r in rankings):
        print("  (* = insufficient data, below min trades threshold)")

    # Redundant pairs
    if redundant_pairs:
        print("\n" + "-" * 72)
        print("  REDUNDANT PAIRS (correlation > {:.0f}%)".format(corr_threshold * 100))
        print("-" * 72)
        for a1, a2, r_corr, s_corr, source in redundant_pairs:
            print(f"  {a1:25s} <-> {a2:25s}")
            print(f"    Return corr: {r_corr:+.3f}  |  Signal corr: {s_corr:+.3f}  "
                  f"|  Detected via: {source}")
    else:
        print("\n  No redundant pairs detected above threshold.")

    # Category group analysis
    print("\n" + "-" * 72)
    print("  CATEGORY GROUP ANALYSIS")
    print("-" * 72)
    for cat, info in group_analysis.items():
        corr_str = f"{info['avg_intra_correlation']:.3f}" if info['avg_intra_correlation'] is not None else "N/A"
        rep = info.get('representative', 'None')
        flag = " ** HIGH INTRA-CORR" if info.get('highly_correlated') else ""
        print(f"\n  {cat} ({info['active_count']}/{len(info['algorithms'])} active)")
        print(f"    Best representative: {rep}")
        print(f"    Avg intra-group corr: {corr_str}{flag}")
        if info.get('rankings'):
            for r in info['rankings']:
                print(f"      {r['algorithm']:25s} comp={r['composite']:.3f} "
                      f"WR={r['win_rate']:.1f}% sharpe={r['sharpe']:.3f} "
                      f"n={r['trades']}")

    # Recommendations
    print("\n" + "-" * 72)
    print("  RECOMMENDATIONS")
    print("-" * 72)

    print("\n  KEEP (core set):")
    for r in recommendations['keep']:
        print(f"    + {r['algorithm']:25s} [{r['category']:10s}] "
              f"composite={r['composite_score']:.3f}")

    if recommendations['merge']:
        print("\n  MERGE (redundant, absorb into higher-performer):")
        for m in recommendations['merge']:
            print(f"    ~ {m['algorithm']:25s} -> {m['merge_into']}")
            print(f"      Reason: {m['reason']}")

    if recommendations['remove']:
        print("\n  REMOVE (poor performance or no data):")
        for r in recommendations['remove']:
            print(f"    - {r['algorithm']:25s} [{r['category']:10s}]")
            print(f"      Reason: {r['reason']}")

    if recommendations['pause']:
        print("\n  PAUSE (decent but exceeds core set limit):")
        for p in recommendations['pause']:
            print(f"    || {p['algorithm']:25s} [{p['category']:10s}] "
                  f"composite={p.get('composite_score', 'N/A')}")

    # Optimal core
    print("\n" + "-" * 72)
    print("  OPTIMAL CORE SET")
    print("-" * 72)
    for i, algo in enumerate(report['optimal_core_set'], 1):
        cat = ALGO_TO_CATEGORY.get(algo, '?')
        print(f"    {i}. {algo} [{cat}]")

    print(f"\n  Estimated capital efficiency improvement: "
          f"{report['estimated_improvement']['capital_efficiency']}")
    print(f"  {report['estimated_improvement']['description']}")

    print("\n" + "=" * 72)
    print("  END OF REPORT")
    print("=" * 72)


# ─────────────────────────────────────────────────
#  9. API UPLOAD (optional)
# ─────────────────────────────────────────────────

def upload_to_api(report):
    """
    Upload consolidation report to the live-monitor API
    for dashboard consumption (optional, best-effort).
    """
    import requests

    url = f"{API_BASE}/smart_money.php?action=update_consolidation&key={ADMIN_KEY}"
    try:
        resp = requests.post(url, json=report, headers=API_HEADERS, timeout=30)
        result = resp.json()
        if result.get('ok'):
            print("  Uploaded consolidation report to API")
        else:
            print(f"  API upload skipped: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"  API upload failed (non-critical): {e}")


# ─────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Algorithm Consolidator: analyze redundancy and recommend pruning'
    )
    parser.add_argument('--days', type=int, default=90,
                        help='Lookback period in days (default: 90)')
    parser.add_argument('--min-trades', type=int, default=10,
                        help='Minimum trades for reliable metrics (default: 10)')
    parser.add_argument('--max-keep', type=int, default=8,
                        help='Maximum algorithms to keep (default: 8)')
    parser.add_argument('--corr-threshold', type=float, default=CORR_THRESHOLD,
                        help=f'Correlation threshold for redundancy (default: {CORR_THRESHOLD})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Analyze only, do not upload results to API')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON path (default: data/algorithm_consolidation_report.json)')
    args = parser.parse_args()

    corr_threshold = args.corr_threshold

    print("=" * 72)
    print("  Algorithm Consolidator")
    print(f"  Lookback: {args.days} days | Min trades: {args.min_trades} | "
          f"Max keep: {args.max_keep} | Corr threshold: {corr_threshold}")
    print("=" * 72)

    # ── Step 1: Connect to DB and fetch data ──
    print("\n[1/7] Fetching data from database...")
    try:
        conn = connect_db()
    except Exception as e:
        print(f"  ERROR: Could not connect to database: {e}")
        print("  Make sure DB_HOST, DB_USER, DB_PASS, DB_NAME env vars are set correctly.")
        sys.exit(1)

    signals = fetch_signals(conn, lookback_days=args.days)
    trades = fetch_closed_trades(conn, lookback_days=args.days)
    _perf_data = fetch_algo_performance(conn)
    conn.close()

    if not signals and not trades:
        print("\n  FATAL: No signals or trades found in the analysis period.")
        print("  Check that lm_signals and lm_trades tables have data.")
        sys.exit(1)

    # ── Step 2: Signal correlation ──
    print("\n[2/7] Computing signal correlation matrix...")
    signal_corr, signal_algos = compute_signal_correlation(signals)
    if signal_corr:
        print(f"  Signal correlation computed for {len(signal_algos)} algorithms")
    else:
        print("  Signal correlation: SKIPPED (insufficient data)")

    # ── Step 3: Return stream correlation ──
    print("\n[3/7] Computing return stream correlation matrix...")
    return_corr, return_algos = compute_return_correlation(trades)
    if return_corr:
        print(f"  Return correlation computed for {len(return_algos)} algorithms")
    else:
        print("  Return correlation: SKIPPED (insufficient data)")

    # ── Step 4: Orthogonality scores ──
    print("\n[4/7] Computing orthogonality scores...")
    orthogonality_scores = compute_orthogonality_scores(signal_corr, return_corr)
    if orthogonality_scores:
        best_orth = max(orthogonality_scores.items(), key=lambda x: x[1])
        worst_orth = min(orthogonality_scores.items(), key=lambda x: x[1])
        print(f"  Most orthogonal:  {best_orth[0]} ({best_orth[1]:.3f})")
        print(f"  Least orthogonal: {worst_orth[0]} ({worst_orth[1]:.3f})")
    else:
        print("  No orthogonality scores computed (no correlation data)")

    # ── Step 5: Performance ranking ──
    print("\n[5/7] Computing performance rankings...")
    rankings = compute_algo_rankings(trades, orthogonality_scores,
                                     min_trades=args.min_trades)
    if rankings:
        print(f"  Ranked {len(rankings)} algorithms with trade data")
        top = rankings[0]
        print(f"  Top algorithm: {top['algorithm']} (composite={top['composite_score']:.3f})")
    else:
        print("  WARNING: No algorithms with trade data to rank")
        print("  Building report with signal-only analysis...")

    # ── Step 6: Find redundant pairs ──
    print("\n[6/7] Detecting redundant pairs...")
    redundant_pairs = find_redundant_pairs(signal_corr, return_corr,
                                           threshold=corr_threshold)
    print(f"  Found {len(redundant_pairs)} redundant pairs "
          f"(correlation > {corr_threshold:.0%})")

    # ── Step 7: Generate recommendations ──
    print("\n[7/7] Generating consolidation recommendations...")
    group_analysis = analyze_category_groups(rankings, signal_corr, return_corr)
    recommendations = generate_recommendations(
        rankings, signal_corr, return_corr, redundant_pairs,
        min_trades=args.min_trades, max_keep=args.max_keep
    )

    # ── Build and save report ──
    report = build_report(
        signal_corr, return_corr, orthogonality_scores,
        rankings, recommendations, group_analysis,
        redundant_pairs, args.days
    )

    # Save to file
    output_path = args.output
    if not output_path:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, 'algorithm_consolidation_report.json')

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved to: {output_path}")

    # Print human-readable report
    print_report(report, recommendations, rankings, redundant_pairs,
                 orthogonality_scores, group_analysis,
                 corr_threshold=corr_threshold)

    # Upload to API (unless dry-run)
    if not args.dry_run:
        upload_to_api(report)
    else:
        print("\n  (dry-run: skipping API upload)")

    return report


if __name__ == '__main__':
    main()
