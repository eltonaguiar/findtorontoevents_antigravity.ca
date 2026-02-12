#!/usr/bin/env python3
"""
mutualfund_ml_optimizer.py — Mutual Funds ML Parameter Optimizer with Walk-Forward Validation.

The PHP learning engine (learning.php) does basic grid search optimizing raw return only.
This script adds:
  1. Walk-forward validation (train/validation/test splits) to detect overfitting
  2. Sharpe ratio optimization (risk-adjusted, not raw return)
  3. Expense ratio drag in all calculations
  4. Cross-algorithm correlation analysis
  5. ML status tracking integration (lm_ml_status, lm_walk_forward)
  6. Regime-aware optimization (bull/bear detection from NAV trends)
  7. Comprehensive reporting for GitHub Actions logs

Database: ejaguiar1_stocks (same MySQL server as stocks)
Tables used:
  - mf2_fund_picks       — algorithm fund selections with entry_nav
  - mf2_nav_history      — daily NAV prices per fund
  - mf2_funds            — fund metadata (expense_ratio, category)
  - mf2_algo_performance — stores optimized params + metrics
  - mf2_backtest_results — stores walk-forward validation results
  - mf2_backtest_trades  — individual trade records from backtests
  - lm_ml_status         — ML readiness per algo (asset_class='MUTUALFUND')
  - lm_walk_forward      — walk-forward train/test split results

10 Algorithms:
  MF Momentum, MF Value Tilt, MF Sector Rotation, MF Risk Parity,
  MF Expense Optimizer, MF Trend Following, MF Mean Reversion,
  MF Quality Growth, MF Diversified Income, MF Balanced Composite

Requires: pip install mysql-connector-python numpy pandas requests
Usage:    python scripts/mutualfund_ml_optimizer.py [--dry-run]
"""

import os
import sys
import json
import math
import argparse
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
import mysql.connector
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

MF_LEARNING_URL = "https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/learning.php"

# Grid search ranges
TP_GRID = [3, 5, 7, 8, 10, 12, 15, 20, 25, 30]        # Target return %
SL_GRID = [2, 3, 5, 7, 8, 10, 12, 15]                  # Stop loss %
HOLD_GRID = [7, 14, 21, 30, 42, 63, 90, 126, 180, 252] # Max hold days

# Walk-forward split ratios
TRAIN_RATIO = 0.60
VAL_RATIO = 0.20
TEST_RATIO = 0.20

# Backtesting defaults
INITIAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 20.0  # 20% of capital per position

# Risk-free rate for Sharpe (annualized, approx T-bill)
RISK_FREE_RATE = 0.05

# Minimum data thresholds
MIN_PICKS_FOR_OPTIMIZATION = 10
MIN_PICKS_FOR_WALKFORWARD = 20

ALL_ALGORITHMS = [
    'MF Momentum', 'MF Value Tilt', 'MF Sector Rotation', 'MF Risk Parity',
    'MF Expense Optimizer', 'MF Trend Following', 'MF Mean Reversion',
    'MF Quality Growth', 'MF Diversified Income', 'MF Balanced Composite'
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('mutualfund_ml_optimizer')


# ---------------------------------------------------------------------------
# Database Connection
# ---------------------------------------------------------------------------

def connect_db():
    """Connect to MySQL database."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=30
    )


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_fund_picks(conn, algorithm=None):
    """
    Fetch fund picks with NAV history joined.
    Returns a list of dicts sorted by pick_date ASC.
    """
    cursor = conn.cursor(dictionary=True)
    where = ""
    params = []
    if algorithm:
        where = " AND fp.algorithm_name = %s"
        params = [algorithm]

    query = """
        SELECT fp.id, fp.symbol, fp.algorithm_name, fp.pick_date, fp.entry_nav,
               fp.score, fp.rating, fp.risk_level, fp.timeframe,
               f.fund_name, f.category, f.expense_ratio, f.fund_family
        FROM mf2_fund_picks fp
        LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
        WHERE fp.entry_nav > 0 {where}
        ORDER BY fp.pick_date ASC
    """.format(where=where)

    cursor.execute(query, params)
    picks = cursor.fetchall()
    cursor.close()
    return picks


def fetch_nav_history(conn, symbol, start_date, limit=260):
    """
    Fetch NAV history for a symbol starting from a given date.
    Returns list of (nav_date, nav) tuples sorted ASC.
    """
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT nav_date, nav
        FROM mf2_nav_history
        WHERE symbol = %s AND nav_date >= %s
        ORDER BY nav_date ASC
        LIMIT %s
    """
    cursor.execute(query, [symbol, start_date, limit])
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_all_nav_history(conn):
    """
    Fetch all NAV history into a dict of symbol -> list of (date, nav).
    More efficient than per-pick queries for large datasets.
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT symbol, nav_date, nav
        FROM mf2_nav_history
        ORDER BY symbol ASC, nav_date ASC
    """)
    rows = cursor.fetchall()
    cursor.close()

    nav_map = defaultdict(list)
    for row in rows:
        nav_map[row['symbol']].append((str(row['nav_date']), float(row['nav'])))

    logger.info("  Loaded NAV history for %d symbols (%d total records)", len(nav_map), len(rows))
    return nav_map


def fetch_algorithm_list(conn):
    """Get list of algorithms that have picks."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT algorithm_name, COUNT(*) as pick_count
        FROM mf2_fund_picks
        WHERE entry_nav > 0
        GROUP BY algorithm_name
        ORDER BY algorithm_name
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


# ---------------------------------------------------------------------------
# Backtesting Engine (replicates PHP mf2_quick_backtest logic in Python)
# ---------------------------------------------------------------------------

def backtest_picks(picks, nav_map, tp_pct, sl_pct, max_hold_days, capital=None):
    """
    Run a backtest on a list of picks with given parameters.

    Replicates the PHP `mf2_quick_backtest` logic:
    - For each pick, look up subsequent NAV prices
    - Apply TP/SL/MaxHold exit conditions
    - Track PnL with expense ratio drag
    - 20% position sizing

    Returns dict with: trades (list), metrics (dict).
    """
    if capital is None:
        capital = INITIAL_CAPITAL

    initial_capital = capital
    peak_capital = capital
    max_drawdown = 0.0
    trades = []
    trade_returns = []

    for pick in picks:
        symbol = pick['symbol']
        entry_nav = float(pick['entry_nav'])
        pick_date = str(pick['pick_date'])
        expense = float(pick.get('expense_ratio') or 0)

        if entry_nav <= 0:
            continue

        # Position sizing: 20% of current capital
        position_value = capital * (POSITION_SIZE_PCT / 100.0)
        if position_value < entry_nav:
            continue
        units = position_value / entry_nav

        # Look up NAV history from pick date
        navs = nav_map.get(symbol, [])
        if not navs:
            continue

        # Find NAVs on or after pick_date
        relevant_navs = [(d, n) for d, n in navs if d >= pick_date]
        if not relevant_navs:
            continue

        # Simulate holding period
        day_count = 0
        exit_nav = entry_nav
        exit_date = pick_date
        exit_reason = 'end_of_data'
        sold = False

        for nav_date, nav_price in relevant_navs:
            day_count += 1
            change_pct = ((nav_price - entry_nav) / entry_nav) * 100.0

            # Target return hit
            if change_pct >= tp_pct and tp_pct < 999:
                exit_nav = nav_price
                exit_date = nav_date
                exit_reason = 'target_hit'
                sold = True
                break

            # Stop loss hit
            if change_pct <= -sl_pct and sl_pct < 999:
                exit_nav = nav_price
                exit_date = nav_date
                exit_reason = 'stop_loss'
                sold = True
                break

            # Max hold days reached
            if day_count >= max_hold_days:
                exit_nav = nav_price
                exit_date = nav_date
                exit_reason = 'max_hold'
                sold = True
                break

        if not sold and day_count > 0:
            exit_reason = 'end_of_data'

        # Calculate PnL with expense ratio drag
        gross_profit = (exit_nav - entry_nav) * units
        expense_drag = (expense / 100.0) * (day_count / 365.25) * (entry_nav * units)
        net_profit = gross_profit - expense_drag
        return_pct = (net_profit / (entry_nav * units)) * 100.0 if (entry_nav * units) > 0 else 0.0

        trade = {
            'symbol': symbol,
            'algorithm': pick.get('algorithm_name', ''),
            'entry_date': pick_date,
            'entry_nav': round(entry_nav, 4),
            'exit_date': exit_date,
            'exit_nav': round(exit_nav, 4),
            'units': round(units, 4),
            'gross_profit': round(gross_profit, 2),
            'expense_drag': round(expense_drag, 2),
            'net_profit': round(net_profit, 2),
            'return_pct': round(return_pct, 4),
            'exit_reason': exit_reason,
            'hold_days': day_count,
        }
        trades.append(trade)
        trade_returns.append(return_pct / 100.0)

        capital += net_profit
        if capital > peak_capital:
            peak_capital = capital
        drawdown = ((peak_capital - capital) / peak_capital) * 100.0 if peak_capital > 0 else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Compute aggregate metrics
    n_trades = len(trades)
    wins = sum(1 for t in trades if t['net_profit'] > 0)
    losses = n_trades - wins
    win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0
    total_return = ((capital - initial_capital) / initial_capital) * 100.0 if initial_capital > 0 else 0.0

    # Sharpe ratio
    sharpe = compute_sharpe(trade_returns)

    # Sortino ratio
    sortino = compute_sortino(trade_returns)

    # Profit factor
    gross_wins = sum(t['net_profit'] for t in trades if t['net_profit'] > 0)
    gross_losses = sum(abs(t['net_profit']) for t in trades if t['net_profit'] <= 0)
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (999 if gross_wins > 0 else 0)

    # Avg win/loss
    win_returns = [t['return_pct'] for t in trades if t['net_profit'] > 0]
    loss_returns = [abs(t['return_pct']) for t in trades if t['net_profit'] <= 0]
    avg_win = np.mean(win_returns) if win_returns else 0
    avg_loss = np.mean(loss_returns) if loss_returns else 0

    # Expectancy
    win_rate_dec = wins / n_trades if n_trades > 0 else 0
    loss_rate_dec = 1 - win_rate_dec
    expectancy = (win_rate_dec * avg_win) - (loss_rate_dec * avg_loss)

    # Avg hold days
    avg_hold = np.mean([t['hold_days'] for t in trades]) if trades else 0

    # Total expense drag
    total_expense_drag = sum(t['expense_drag'] for t in trades)

    metrics = {
        'trades': n_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 2),
        'total_return_pct': round(total_return, 4),
        'sharpe': round(sharpe, 4),
        'sortino': round(sortino, 4),
        'max_drawdown_pct': round(max_drawdown, 4),
        'profit_factor': round(profit_factor, 4),
        'expectancy': round(expectancy, 4),
        'avg_win_pct': round(avg_win, 4),
        'avg_loss_pct': round(avg_loss, 4),
        'avg_hold_days': round(avg_hold, 2),
        'total_pnl': round(capital - initial_capital, 2),
        'final_capital': round(capital, 2),
        'total_expense_drag': round(total_expense_drag, 2),
    }

    return {'trades': trades, 'metrics': metrics}


def compute_sharpe(returns, periods_per_year=252):
    """Compute annualized Sharpe ratio from a list of per-trade returns."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    excess = arr - RISK_FREE_RATE / periods_per_year
    mean_r = np.mean(excess)
    std_r = np.std(arr, ddof=1)
    if std_r < 1e-10:
        return 0.0
    return float(mean_r / std_r * np.sqrt(periods_per_year))


def compute_sortino(returns, periods_per_year=252):
    """Compute annualized Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    excess = arr - RISK_FREE_RATE / periods_per_year
    mean_r = np.mean(excess)
    downside = arr[arr < 0]
    if len(downside) < 2:
        return float(mean_r * np.sqrt(periods_per_year)) if mean_r > 0 else 0.0
    downside_std = np.std(downside, ddof=1)
    if downside_std < 1e-10:
        return 0.0
    return float(mean_r / downside_std * np.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# Regime Detection (bull/bear from NAV trend)
# ---------------------------------------------------------------------------

def detect_regime(nav_map):
    """
    Simple regime detection based on broad NAV trends.
    Returns 'bull', 'bear', or 'neutral' and a confidence score.

    Uses the median 60-day return across all funds as a broad market indicator.
    """
    recent_returns = []
    for symbol, navs in nav_map.items():
        if len(navs) < 60:
            continue
        recent = navs[-60:]
        first_nav = recent[0][1]
        last_nav = recent[-1][1]
        if first_nav > 0:
            ret = ((last_nav - first_nav) / first_nav) * 100.0
            recent_returns.append(ret)

    if not recent_returns:
        return 'neutral', 0.0

    median_return = np.median(recent_returns)
    if median_return > 3.0:
        return 'bull', min(abs(median_return) / 10.0, 1.0)
    elif median_return < -3.0:
        return 'bear', min(abs(median_return) / 10.0, 1.0)
    else:
        return 'neutral', 0.3


# ---------------------------------------------------------------------------
# Walk-Forward Grid Search
# ---------------------------------------------------------------------------

def walk_forward_optimize(picks, nav_map, algorithm_name):
    """
    Per-algorithm walk-forward grid search.

    Split picks chronologically:
      - First 60%: training (find best params by Sharpe)
      - Next 20%:  validation (confirm params generalize)
      - Final 20%: test (final unbiased estimate)

    Objective: maximize Sharpe ratio (risk-adjusted return with expense drag).

    Returns dict with best params, train/val/test metrics, overfitting analysis.
    """
    n = len(picks)
    if n < MIN_PICKS_FOR_OPTIMIZATION:
        return None

    # Walk-forward split
    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    train_picks = picks[:train_end]
    val_picks = picks[train_end:val_end]
    test_picks = picks[val_end:]

    if len(train_picks) < 5 or len(val_picks) < 3:
        return None

    logger.info("    Split: train=%d, val=%d, test=%d picks", len(train_picks), len(val_picks), len(test_picks))

    # Get date ranges for reporting
    train_start_date = str(train_picks[0]['pick_date'])
    train_end_date = str(train_picks[-1]['pick_date'])
    val_start_date = str(val_picks[0]['pick_date']) if val_picks else train_end_date
    val_end_date = str(val_picks[-1]['pick_date']) if val_picks else val_start_date
    test_start_date = str(test_picks[0]['pick_date']) if test_picks else val_end_date
    test_end_date = str(test_picks[-1]['pick_date']) if test_picks else test_start_date

    # Phase 1: Grid search on TRAINING data
    best_sharpe = -9999
    best_params = {'tp': 10, 'sl': 8, 'hold': 90}
    all_results = []
    profitable_combos = 0
    total_combos = 0

    for tp in TP_GRID:
        for sl in SL_GRID:
            for hold in HOLD_GRID:
                total_combos += 1
                result = backtest_picks(train_picks, nav_map, tp, sl, hold)
                m = result['metrics']

                if m['trades'] == 0:
                    continue

                all_results.append({
                    'tp': tp, 'sl': sl, 'hold': hold,
                    'sharpe': m['sharpe'],
                    'return_pct': m['total_return_pct'],
                    'win_rate': m['win_rate'],
                    'trades': m['trades'],
                    'profit_factor': m['profit_factor'],
                })

                if m['total_return_pct'] > 0:
                    profitable_combos += 1

                if m['sharpe'] > best_sharpe:
                    best_sharpe = m['sharpe']
                    best_params = {'tp': tp, 'sl': sl, 'hold': hold}

    if not all_results:
        return None

    logger.info("    Grid: %d combos tested, %d profitable (%.1f%%)",
                total_combos, profitable_combos,
                profitable_combos / max(len(all_results), 1) * 100)
    logger.info("    Best train params: TP=%d%% SL=%d%% Hold=%dd (Sharpe=%.3f)",
                best_params['tp'], best_params['sl'], best_params['hold'], best_sharpe)

    # Phase 2: Validate on VALIDATION data
    val_result = backtest_picks(val_picks, nav_map, best_params['tp'], best_params['sl'], best_params['hold'])
    val_metrics = val_result['metrics']

    # Also run default params on validation for comparison
    default_val_result = backtest_picks(val_picks, nav_map, 10, 8, 90)
    default_val_metrics = default_val_result['metrics']

    # Phase 3: Test on TEST data (final unbiased estimate)
    test_result = None
    test_metrics = {'trades': 0, 'sharpe': 0, 'win_rate': 0, 'total_return_pct': 0}
    if test_picks:
        test_result = backtest_picks(test_picks, nav_map, best_params['tp'], best_params['sl'], best_params['hold'])
        test_metrics = test_result['metrics']

    # Phase 4: Run best params on FULL dataset for overall metrics
    full_result = backtest_picks(picks, nav_map, best_params['tp'], best_params['sl'], best_params['hold'])
    full_metrics = full_result['metrics']

    # Also run default params on full dataset
    default_full = backtest_picks(picks, nav_map, 10, 8, 90)
    default_metrics = default_full['metrics']

    # Overfitting analysis
    train_result = backtest_picks(train_picks, nav_map, best_params['tp'], best_params['sl'], best_params['hold'])
    train_metrics = train_result['metrics']

    sharpe_decay = 0.0
    if train_metrics['sharpe'] != 0:
        sharpe_decay = (1.0 - val_metrics['sharpe'] / train_metrics['sharpe']) * 100.0 if train_metrics['sharpe'] > 0 else 0.0

    is_overfit = False
    overfit_warnings = []

    # Overfitting signals
    if sharpe_decay > 50:
        is_overfit = True
        overfit_warnings.append("Sharpe decayed %.0f%% from train to validation" % sharpe_decay)
    if train_metrics['sharpe'] > 0 and val_metrics['sharpe'] < 0:
        is_overfit = True
        overfit_warnings.append("Train Sharpe positive but validation Sharpe negative")
    if train_metrics['win_rate'] > 0 and val_metrics['win_rate'] > 0:
        wr_decay = ((train_metrics['win_rate'] - val_metrics['win_rate']) / train_metrics['win_rate']) * 100
        if wr_decay > 30:
            overfit_warnings.append("Win rate dropped %.0f%% from train to val" % wr_decay)

    # Improvement over default
    improvement_sharpe = full_metrics['sharpe'] - default_metrics['sharpe']
    improvement_return = full_metrics['total_return_pct'] - default_metrics['total_return_pct']

    # Top 5 alternative param combos (by Sharpe)
    sorted_results = sorted(all_results, key=lambda x: x['sharpe'], reverse=True)
    top_alternatives = sorted_results[:5]

    return {
        'algorithm': algorithm_name,
        'total_picks': n,
        'best_params': best_params,
        'best_train_sharpe': round(best_sharpe, 4),

        # Split results
        'train': {
            'picks': len(train_picks),
            'start_date': train_start_date,
            'end_date': train_end_date,
            'metrics': train_metrics,
        },
        'validation': {
            'picks': len(val_picks),
            'start_date': val_start_date,
            'end_date': val_end_date,
            'metrics': val_metrics,
            'default_metrics': default_val_metrics,
        },
        'test': {
            'picks': len(test_picks),
            'start_date': test_start_date,
            'end_date': test_end_date,
            'metrics': test_metrics,
        },
        'full': {
            'metrics': full_metrics,
            'default_metrics': default_metrics,
        },

        # Overfitting analysis
        'overfitting': {
            'sharpe_decay_pct': round(sharpe_decay, 2),
            'is_overfit': is_overfit,
            'warnings': overfit_warnings,
        },

        # Improvement over default (TP=10, SL=8, Hold=90)
        'improvement': {
            'sharpe_delta': round(improvement_sharpe, 4),
            'return_delta': round(improvement_return, 4),
        },

        # Grid search summary
        'grid_search': {
            'total_combos': total_combos,
            'combos_with_trades': len(all_results),
            'profitable_combos': profitable_combos,
            'profitability_rate': round(profitable_combos / max(len(all_results), 1) * 100, 1),
            'top_alternatives': top_alternatives,
        },
    }


# ---------------------------------------------------------------------------
# Cross-Algorithm Correlation Analysis
# ---------------------------------------------------------------------------

def compute_correlation_matrix(picks_by_algo, nav_map):
    """
    Compute correlation between algorithm picks.

    For each pair of algorithms:
    - Find overlapping time periods where both had picks
    - Check if they picked the same funds
    - Compute return correlation for shared picks

    Returns correlation matrix and recommendations.
    """
    algo_names = sorted(picks_by_algo.keys())
    n_algos = len(algo_names)

    if n_algos < 2:
        return {'matrix': {}, 'recommendations': [], 'overlap_analysis': {}}

    # Build per-algo symbol sets per date
    algo_symbols = {}
    algo_returns = {}
    for algo, picks in picks_by_algo.items():
        symbols_set = set()
        returns_list = []
        for pick in picks:
            symbols_set.add(pick['symbol'])
            # Quick return calc using nav_map
            sym = pick['symbol']
            navs = nav_map.get(sym, [])
            entry_nav = float(pick['entry_nav'])
            pick_date = str(pick['pick_date'])
            relevant = [(d, n) for d, n in navs if d >= pick_date]
            if relevant and entry_nav > 0:
                exit_nav = relevant[min(29, len(relevant) - 1)][1]  # 30-day return
                ret = ((exit_nav - entry_nav) / entry_nav) * 100.0
                returns_list.append(ret)
        algo_symbols[algo] = symbols_set
        algo_returns[algo] = returns_list

    # Symbol overlap matrix
    overlap_matrix = {}
    for i, algo_a in enumerate(algo_names):
        overlap_matrix[algo_a] = {}
        for j, algo_b in enumerate(algo_names):
            syms_a = algo_symbols.get(algo_a, set())
            syms_b = algo_symbols.get(algo_b, set())
            if not syms_a or not syms_b:
                overlap_matrix[algo_a][algo_b] = 0.0
                continue
            intersection = len(syms_a & syms_b)
            union = len(syms_a | syms_b)
            jaccard = intersection / union if union > 0 else 0
            overlap_matrix[algo_a][algo_b] = round(jaccard, 4)

    # Return correlation matrix
    corr_matrix = {}
    for i, algo_a in enumerate(algo_names):
        corr_matrix[algo_a] = {}
        for j, algo_b in enumerate(algo_names):
            if algo_a == algo_b:
                corr_matrix[algo_a][algo_b] = 1.0
                continue
            ret_a = algo_returns.get(algo_a, [])
            ret_b = algo_returns.get(algo_b, [])
            min_len = min(len(ret_a), len(ret_b))
            if min_len < 5:
                corr_matrix[algo_a][algo_b] = None
                continue
            corr = np.corrcoef(ret_a[:min_len], ret_b[:min_len])[0, 1]
            corr_matrix[algo_a][algo_b] = round(float(corr), 4) if not np.isnan(corr) else None

    # Recommendations
    recommendations = []
    highly_correlated_pairs = []

    for i in range(n_algos):
        for j in range(i + 1, n_algos):
            algo_a = algo_names[i]
            algo_b = algo_names[j]

            corr = corr_matrix.get(algo_a, {}).get(algo_b)
            overlap = overlap_matrix.get(algo_a, {}).get(algo_b, 0)

            if corr is not None and corr > 0.7:
                highly_correlated_pairs.append((algo_a, algo_b, corr, overlap))

    if highly_correlated_pairs:
        for pair in sorted(highly_correlated_pairs, key=lambda x: x[2], reverse=True):
            recommendations.append(
                "HIGH CORRELATION (%.2f): '%s' and '%s' (symbol overlap: %.1f%%). "
                "Consider merging or dropping one." % (pair[2], pair[0], pair[1], pair[3] * 100)
            )

    # Identify unique algorithms (low correlation with all others)
    unique_algos = []
    for algo in algo_names:
        max_corr_with_others = 0
        for other in algo_names:
            if algo == other:
                continue
            c = corr_matrix.get(algo, {}).get(other)
            if c is not None and abs(c) > max_corr_with_others:
                max_corr_with_others = abs(c)
        if max_corr_with_others < 0.4:
            unique_algos.append(algo)

    if unique_algos:
        recommendations.append(
            "UNIQUE STRATEGIES (low correlation with all others): %s" % ', '.join(unique_algos)
        )

    return {
        'correlation_matrix': corr_matrix,
        'symbol_overlap_matrix': overlap_matrix,
        'highly_correlated_pairs': [
            {'algo_a': p[0], 'algo_b': p[1], 'correlation': p[2], 'symbol_overlap': p[3]}
            for p in highly_correlated_pairs
        ],
        'unique_algorithms': unique_algos,
        'recommendations': recommendations,
    }


# ---------------------------------------------------------------------------
# Database Updates
# ---------------------------------------------------------------------------

def update_algo_performance(conn, algo_result, dry_run=False):
    """Update mf2_algo_performance with optimized params."""
    if dry_run:
        return

    algo = algo_result['algorithm']
    full_m = algo_result['full']['metrics']
    params = algo_result['best_params']
    overfit = algo_result['overfitting']
    default_m = algo_result['full']['default_metrics']

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    best_for = "Optimized: TP:%d%% SL:%d%% Hold:%dd Sharpe:%.2f" % (
        params['tp'], params['sl'], params['hold'], full_m['sharpe']
    )
    if overfit['is_overfit']:
        best_for += " [OVERFIT WARNING]"

    worst_for = "Default(10/8/90): Return:%.2f%% WR:%.1f%%" % (
        default_m['total_return_pct'], default_m['win_rate']
    )

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mf2_algo_performance
            (algorithm_name, strategy_type, total_picks, total_trades, win_rate,
             avg_return_pct, best_for, worst_for, updated_at)
        VALUES (%s, 'ml_optimizer', %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            total_trades = %s, win_rate = %s, avg_return_pct = %s,
            best_for = %s, worst_for = %s, updated_at = %s
    """, [
        algo, algo_result['total_picks'], full_m['trades'], full_m['win_rate'],
        full_m['total_return_pct'], best_for, worst_for, now,
        full_m['trades'], full_m['win_rate'], full_m['total_return_pct'],
        best_for, worst_for, now,
    ])
    conn.commit()
    cursor.close()


def update_backtest_results(conn, algo_result, dry_run=False):
    """Store walk-forward validation results in mf2_backtest_results."""
    if dry_run:
        return

    algo = algo_result['algorithm']
    params = algo_result['best_params']
    train_m = algo_result['train']['metrics']
    val_m = algo_result['validation']['metrics']
    test_m = algo_result['test']['metrics']
    full_m = algo_result['full']['metrics']

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    run_name = "wf_ml_%s_tp%d_sl%d_%dd" % (
        algo.replace(' ', '_').lower(),
        params['tp'], params['sl'], params['hold']
    )

    start_date = algo_result['train']['start_date']
    end_date = algo_result['test']['end_date'] or algo_result['validation']['end_date']

    params_json = json.dumps({
        'target_return_pct': params['tp'],
        'stop_loss_pct': params['sl'],
        'max_hold_days': params['hold'],
        'method': 'walk_forward_sharpe',
        'train_sharpe': train_m['sharpe'],
        'val_sharpe': val_m['sharpe'],
        'test_sharpe': test_m['sharpe'],
        'is_overfit': algo_result['overfitting']['is_overfit'],
    })

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mf2_backtest_results
            (portfolio_id, run_name, algorithm_filter, strategy_type,
             start_date, end_date, initial_capital, final_value,
             total_return_pct, total_trades, winning_trades, losing_trades,
             win_rate, avg_win_pct, avg_loss_pct,
             best_trade_pct, worst_trade_pct,
             max_drawdown_pct, total_fees, sharpe_ratio, sortino_ratio,
             profit_factor, expectancy, avg_hold_days, fee_drag_pct,
             params_json, created_at)
        VALUES (0, %s, %s, 'ml_walkforward',
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                0, 0,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s)
    """, [
        run_name, algo, start_date, end_date,
        INITIAL_CAPITAL, full_m['final_capital'],
        full_m['total_return_pct'], full_m['trades'],
        full_m['wins'], full_m['losses'],
        full_m['win_rate'], full_m['avg_win_pct'], full_m['avg_loss_pct'],
        full_m['max_drawdown_pct'], full_m['total_expense_drag'],
        full_m['sharpe'], full_m['sortino'],
        full_m['profit_factor'], full_m['expectancy'],
        full_m['avg_hold_days'],
        round(full_m['total_expense_drag'] / max(INITIAL_CAPITAL, 1) * 100, 4),
        params_json, now,
    ])
    conn.commit()
    cursor.close()


def update_ml_status(conn, algo_result, dry_run=False):
    """
    Update lm_ml_status table with mutual fund algo entries.
    asset_class = 'MUTUALFUND'
    """
    if dry_run:
        return

    algo = algo_result['algorithm']
    params = algo_result['best_params']
    full_m = algo_result['full']['metrics']
    overfit = algo_result['overfitting']

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    ml_ready = 1 if (
        full_m['trades'] >= MIN_PICKS_FOR_OPTIMIZATION
        and not overfit['is_overfit']
        and full_m['sharpe'] > 0
    ) else 0

    # Determine status
    if full_m['trades'] < MIN_PICKS_FOR_OPTIMIZATION:
        status = 'collecting_data'
        status_reason = 'Need %d+ trades, have %d' % (MIN_PICKS_FOR_OPTIMIZATION, full_m['trades'])
    elif overfit['is_overfit']:
        status = 'overfit_detected'
        status_reason = '; '.join(overfit['warnings'])
    elif full_m['sharpe'] <= 0:
        status = 'underperforming'
        status_reason = 'Negative Sharpe (%.3f) with optimized params' % full_m['sharpe']
    else:
        status = 'optimized'
        status_reason = 'Sharpe %.3f, WR %.1f%%, PF %.2f' % (
            full_m['sharpe'], full_m['win_rate'], full_m['profit_factor']
        )

    # Determine param source
    param_source = 'ml_walkforward'
    if overfit['is_overfit']:
        param_source = 'default'  # Don't deploy overfit params

    # Backtest grade
    if full_m['sharpe'] >= 1.5:
        grade = 'A+'
    elif full_m['sharpe'] >= 1.0:
        grade = 'A'
    elif full_m['sharpe'] >= 0.5:
        grade = 'B'
    elif full_m['sharpe'] >= 0:
        grade = 'C'
    else:
        grade = 'D'

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lm_ml_status
            (algorithm_name, asset_class, closed_trades, min_trades_needed,
             ml_ready, current_tp, current_sl, current_hold,
             param_source, current_win_rate, current_sharpe, current_pf,
             total_pnl, last_optimization, optimization_count,
             best_sharpe_ever, backtest_sharpe, backtest_grade, backtest_trades,
             status, status_reason, updated_at, created_at)
        VALUES (%s, 'MUTUALFUND', %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, 1,
                %s, %s, %s, %s,
                %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            closed_trades = %s, ml_ready = %s,
            current_tp = %s, current_sl = %s, current_hold = %s,
            param_source = %s, current_win_rate = %s, current_sharpe = %s,
            current_pf = %s, total_pnl = %s, last_optimization = %s,
            optimization_count = optimization_count + 1,
            best_sharpe_ever = GREATEST(COALESCE(best_sharpe_ever, 0), %s),
            backtest_sharpe = %s, backtest_grade = %s, backtest_trades = %s,
            status = %s, status_reason = %s, updated_at = %s
    """, [
        # INSERT values
        algo, full_m['trades'], MIN_PICKS_FOR_OPTIMIZATION,
        ml_ready, params['tp'], params['sl'], params['hold'],
        param_source, full_m['win_rate'], full_m['sharpe'], full_m['profit_factor'],
        full_m['total_pnl'], now,
        full_m['sharpe'], full_m['sharpe'], grade, full_m['trades'],
        status, status_reason, now, now,
        # UPDATE values
        full_m['trades'], ml_ready,
        params['tp'], params['sl'], params['hold'],
        param_source, full_m['win_rate'], full_m['sharpe'],
        full_m['profit_factor'], full_m['total_pnl'], now,
        full_m['sharpe'],
        full_m['sharpe'], grade, full_m['trades'],
        status, status_reason, now,
    ])
    conn.commit()
    cursor.close()


def update_walk_forward(conn, algo_result, dry_run=False):
    """Store walk-forward train/test split results in lm_walk_forward."""
    if dry_run:
        return

    algo = algo_result['algorithm']
    params = algo_result['best_params']
    train = algo_result['train']
    test = algo_result['test']
    val = algo_result['validation']
    overfit = algo_result['overfitting']

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # Store train vs validation split
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO lm_walk_forward
            (algorithm_name, asset_class,
             train_start, train_end, test_start, test_end,
             train_sharpe, train_win_rate, train_trades,
             test_sharpe, test_win_rate, test_trades, test_pnl,
             tp_pct, sl_pct, max_hold_hours,
             sharpe_decay_pct, is_overfit, created_at)
        VALUES (%s, 'MUTUALFUND',
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s)
    """, [
        algo,
        train['start_date'], train['end_date'],
        val['start_date'], val['end_date'],
        train['metrics']['sharpe'], train['metrics']['win_rate'], train['metrics']['trades'],
        val['metrics']['sharpe'], val['metrics']['win_rate'], val['metrics']['trades'],
        val['metrics']['total_pnl'],
        params['tp'], params['sl'], params['hold'] * 24,  # Convert days to hours for schema compat
        overfit['sharpe_decay_pct'], 1 if overfit['is_overfit'] else 0, now,
    ])

    # Also store train vs test split if we have test data
    if test['metrics']['trades'] > 0:
        cursor.execute("""
            INSERT INTO lm_walk_forward
                (algorithm_name, asset_class,
                 train_start, train_end, test_start, test_end,
                 train_sharpe, train_win_rate, train_trades,
                 test_sharpe, test_win_rate, test_trades, test_pnl,
                 tp_pct, sl_pct, max_hold_hours,
                 sharpe_decay_pct, is_overfit, created_at)
            VALUES (%s, 'MUTUALFUND',
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s)
        """, [
            algo,
            train['start_date'], val['end_date'],
            test['start_date'], test['end_date'],
            train['metrics']['sharpe'], train['metrics']['win_rate'],
            train['metrics']['trades'] + val['metrics']['trades'],
            test['metrics']['sharpe'], test['metrics']['win_rate'], test['metrics']['trades'],
            test['metrics']['total_pnl'],
            params['tp'], params['sl'], params['hold'] * 24,
            overfit['sharpe_decay_pct'], 1 if overfit['is_overfit'] else 0, now,
        ])

    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# PHP API Integration
# ---------------------------------------------------------------------------

def trigger_php_learning():
    """
    Trigger the PHP learning endpoint for comparison.
    The PHP engine does basic grid search on raw return — we compare results.
    """
    logger.info("Triggering PHP learning engine for comparison...")
    try:
        response = requests.get(
            MF_LEARNING_URL,
            params={"action": "analyze_and_adjust"},
            headers=API_HEADERS,
            timeout=120
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                n_algos = data.get('total_algorithms', 0)
                logger.info("  PHP learning completed: %d algorithms analyzed", n_algos)
                return data
            else:
                logger.warning("  PHP learning returned error: %s", data.get('error', 'unknown'))
        else:
            logger.warning("  PHP learning HTTP %d", response.status_code)
    except requests.RequestException as e:
        logger.warning("  PHP learning request failed: %s", e)
    except (ValueError, KeyError) as e:
        logger.warning("  PHP learning response parse error: %s", e)
    return None


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results, correlation_analysis, regime, php_comparison):
    """Print comprehensive report for GitHub Actions logs."""
    print("")
    print("=" * 80)
    print("  MUTUAL FUNDS ML PARAMETER OPTIMIZER — RESULTS REPORT")
    print("  Generated: %s UTC" % datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 80)

    # Regime
    regime_name, regime_conf = regime
    print("\n  Market Regime: %s (confidence: %.0f%%)" % (regime_name.upper(), regime_conf * 100))

    # Summary table
    print("\n" + "-" * 80)
    print("  PER-ALGORITHM RESULTS")
    print("-" * 80)
    print("  %-25s %5s %5s %5s %7s %7s %7s %7s %8s" % (
        "Algorithm", "TP%", "SL%", "Hold", "Sharpe", "Return", "WinRt", "PF", "Status"
    ))
    print("  " + "-" * 78)

    algo_summary = []
    for r in results:
        algo = r['algorithm']
        params = r['best_params']
        full_m = r['full']['metrics']
        overfit = r['overfitting']

        status = "OK"
        if overfit['is_overfit']:
            status = "OVERFIT"
        elif full_m['sharpe'] <= 0:
            status = "WEAK"
        elif full_m['sharpe'] >= 1.0:
            status = "STRONG"

        print("  %-25s %5d %5d %5d %7.3f %6.1f%% %5.1f%% %7.2f %8s" % (
            algo[:25], params['tp'], params['sl'], params['hold'],
            full_m['sharpe'], full_m['total_return_pct'],
            full_m['win_rate'], full_m['profit_factor'], status
        ))

        algo_summary.append({
            'algorithm': algo,
            'sharpe': full_m['sharpe'],
            'return_pct': full_m['total_return_pct'],
            'status': status,
        })

    # Train vs Validation vs Test breakdown
    print("\n" + "-" * 80)
    print("  WALK-FORWARD VALIDATION (Train 60% | Validation 20% | Test 20%)")
    print("-" * 80)
    print("  %-25s  Train-SR  Val-SR  Test-SR  Decay%%  Overfit?" % "Algorithm")
    print("  " + "-" * 73)

    for r in results:
        algo = r['algorithm']
        t_sr = r['train']['metrics']['sharpe']
        v_sr = r['validation']['metrics']['sharpe']
        te_sr = r['test']['metrics']['sharpe']
        decay = r['overfitting']['sharpe_decay_pct']
        overfit = "YES" if r['overfitting']['is_overfit'] else "no"

        print("  %-25s  %8.3f %7.3f %8.3f %6.1f%% %8s" % (
            algo[:25], t_sr, v_sr, te_sr, decay, overfit
        ))

    # Overfitting warnings
    overfit_algos = [r for r in results if r['overfitting']['is_overfit']]
    if overfit_algos:
        print("\n  *** OVERFITTING WARNINGS ***")
        for r in overfit_algos:
            for w in r['overfitting']['warnings']:
                print("  [%s] %s" % (r['algorithm'], w))

    # Improvement over defaults
    print("\n" + "-" * 80)
    print("  IMPROVEMENT OVER DEFAULT PARAMS (TP=10%%, SL=8%%, Hold=90d)")
    print("-" * 80)
    print("  %-25s  Sharpe-Delta  Return-Delta  Default-SR  Optimized-SR" % "Algorithm")
    print("  " + "-" * 73)

    for r in results:
        algo = r['algorithm']
        imp = r['improvement']
        def_sr = r['full']['default_metrics']['sharpe']
        opt_sr = r['full']['metrics']['sharpe']
        marker = " <-- WORSE" if imp['sharpe_delta'] < 0 else ""

        print("  %-25s  %+12.3f  %+11.2f%%  %10.3f  %12.3f%s" % (
            algo[:25], imp['sharpe_delta'], imp['return_delta'], def_sr, opt_sr, marker
        ))

    # Correlation analysis
    if correlation_analysis.get('recommendations'):
        print("\n" + "-" * 80)
        print("  CROSS-ALGORITHM CORRELATION ANALYSIS")
        print("-" * 80)
        for rec in correlation_analysis['recommendations']:
            print("  %s" % rec)

    if correlation_analysis.get('highly_correlated_pairs'):
        print("\n  Highly Correlated Pairs:")
        for pair in correlation_analysis['highly_correlated_pairs']:
            print("    %s <-> %s : corr=%.3f, symbol_overlap=%.1f%%" % (
                pair['algo_a'], pair['algo_b'],
                pair['correlation'], pair['symbol_overlap'] * 100
            ))

    if correlation_analysis.get('unique_algorithms'):
        print("\n  Unique/Orthogonal Algorithms (low correlation with all others):")
        for algo in correlation_analysis['unique_algorithms']:
            print("    - %s" % algo)

    # Profitability analysis across all param combos
    print("\n" + "-" * 80)
    print("  CROSS-PARAMETER PROFITABILITY")
    print("-" * 80)
    for r in results:
        gs = r['grid_search']
        print("  %-25s  %d/%d combos profitable (%.1f%%)" % (
            r['algorithm'][:25],
            gs['profitable_combos'], gs['combos_with_trades'],
            gs['profitability_rate']
        ))

    # Identify universally unprofitable algos
    unprofitable = [r for r in results if r['grid_search']['profitability_rate'] < 10]
    if unprofitable:
        print("\n  *** UNIVERSALLY UNPROFITABLE (< 10%% of combos profitable) ***")
        for r in unprofitable:
            print("  [%s] Only %.1f%% of parameter combos are profitable — consider retiring." % (
                r['algorithm'], r['grid_search']['profitability_rate']
            ))

    # PHP comparison
    if php_comparison:
        print("\n" + "-" * 80)
        print("  PHP LEARNING ENGINE COMPARISON")
        print("-" * 80)
        php_recs = php_comparison.get('recommendations', [])
        for rec in php_recs:
            algo_name = rec.get('algorithm', '?')
            php_best = rec.get('best_return_pct', 0)
            php_verdict = rec.get('verdict', '?')
            php_params = rec.get('best_params', {})

            # Find our result for this algo
            our_result = None
            for r in results:
                if r['algorithm'] == algo_name:
                    our_result = r
                    break

            if our_result:
                our_sharpe = our_result['full']['metrics']['sharpe']
                our_return = our_result['full']['metrics']['total_return_pct']
                print("  %-25s PHP: %.2f%% return (%s) | ML: Sharpe=%.3f Return=%.2f%%" % (
                    algo_name[:25], php_best, php_verdict, our_sharpe, our_return
                ))

    # Final scoreboard
    strong = len([r for r in results if r['full']['metrics']['sharpe'] >= 1.0 and not r['overfitting']['is_overfit']])
    decent = len([r for r in results if 0 < r['full']['metrics']['sharpe'] < 1.0 and not r['overfitting']['is_overfit']])
    weak = len([r for r in results if r['full']['metrics']['sharpe'] <= 0])
    overfit_count = len(overfit_algos)

    print("\n" + "=" * 80)
    print("  FINAL SCOREBOARD")
    print("  Strong (Sharpe >= 1.0): %d" % strong)
    print("  Decent (0 < Sharpe < 1): %d" % decent)
    print("  Weak (Sharpe <= 0):     %d" % weak)
    print("  Overfit warnings:       %d" % overfit_count)
    print("  Total algorithms:       %d" % len(results))
    print("=" * 80)
    print("")


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_optimization(dry_run=False):
    """
    Full optimization pipeline:
    1. Connect to DB and fetch all fund picks + NAV history
    2. Detect market regime
    3. Per-algorithm walk-forward grid search
    4. Cross-algorithm correlation analysis
    5. Update DB tables (mf2_algo_performance, mf2_backtest_results, lm_ml_status, lm_walk_forward)
    6. Trigger PHP learning for comparison
    7. Print comprehensive report
    """
    logger.info("=" * 60)
    logger.info("MUTUAL FUNDS ML PARAMETER OPTIMIZER — Starting")
    logger.info("  Method: Walk-forward grid search (Sharpe optimization)")
    logger.info("  Splits: Train=%.0f%% Val=%.0f%% Test=%.0f%%",
                TRAIN_RATIO * 100, VAL_RATIO * 100, TEST_RATIO * 100)
    logger.info("  Grid:   TP=%s  SL=%s  Hold=%s", TP_GRID, SL_GRID, HOLD_GRID)
    logger.info("  Combos: %d per algorithm", len(TP_GRID) * len(SL_GRID) * len(HOLD_GRID))
    logger.info("  Dry run: %s", dry_run)
    logger.info("=" * 60)

    # Connect to database
    try:
        conn = connect_db()
        logger.info("Connected to database: %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
    except mysql.connector.Error as e:
        logger.error("Database connection failed: %s", e)
        return None

    # Fetch all NAV history (bulk load for efficiency)
    logger.info("\nStep 1: Loading data...")
    nav_map = fetch_all_nav_history(conn)
    if not nav_map:
        logger.error("No NAV history found. Run fetch_prices.php first.")
        conn.close()
        return None

    # Fetch algorithm list
    algo_list = fetch_algorithm_list(conn)
    logger.info("  Found %d algorithms with picks", len(algo_list))
    for a in algo_list:
        logger.info("    %-25s %d picks", a['algorithm_name'], a['pick_count'])

    # Detect regime
    logger.info("\nStep 2: Detecting market regime...")
    regime = detect_regime(nav_map)
    logger.info("  Regime: %s (confidence: %.0f%%)", regime[0].upper(), regime[1] * 100)

    # Per-algorithm optimization
    logger.info("\nStep 3: Walk-forward optimization per algorithm...")
    results = []
    picks_by_algo = {}

    for algo_info in algo_list:
        algo_name = algo_info['algorithm_name']
        pick_count = int(algo_info['pick_count'])

        logger.info("\n  --- %s (%d picks) ---", algo_name, pick_count)

        if pick_count < MIN_PICKS_FOR_OPTIMIZATION:
            logger.info("    SKIP: Need %d+ picks, have %d", MIN_PICKS_FOR_OPTIMIZATION, pick_count)
            continue

        picks = fetch_fund_picks(conn, algorithm=algo_name)
        picks_by_algo[algo_name] = picks

        result = walk_forward_optimize(picks, nav_map, algo_name)
        if result is None:
            logger.info("    SKIP: Insufficient data after splitting")
            continue

        results.append(result)

        # Log key results
        full_m = result['full']['metrics']
        params = result['best_params']
        overfit = result['overfitting']

        logger.info("    Optimized: TP=%d%% SL=%d%% Hold=%dd", params['tp'], params['sl'], params['hold'])
        logger.info("    Full: Sharpe=%.3f Return=%.2f%% WR=%.1f%% PF=%.2f",
                    full_m['sharpe'], full_m['total_return_pct'], full_m['win_rate'], full_m['profit_factor'])
        if overfit['is_overfit']:
            logger.warning("    *** OVERFIT DETECTED: %s", '; '.join(overfit['warnings']))

        # Update database tables
        try:
            update_algo_performance(conn, result, dry_run)
            update_backtest_results(conn, result, dry_run)
            update_ml_status(conn, result, dry_run)
            update_walk_forward(conn, result, dry_run)
            if not dry_run:
                logger.info("    DB updated: mf2_algo_performance, mf2_backtest_results, lm_ml_status, lm_walk_forward")
        except mysql.connector.Error as e:
            logger.warning("    DB update failed: %s", e)

    if not results:
        logger.warning("No algorithms had sufficient data for optimization.")
        conn.close()
        return None

    # Correlation analysis
    logger.info("\nStep 4: Cross-algorithm correlation analysis...")
    correlation_analysis = compute_correlation_matrix(picks_by_algo, nav_map)
    if correlation_analysis['recommendations']:
        for rec in correlation_analysis['recommendations']:
            logger.info("  %s", rec)
    else:
        logger.info("  No significant correlations detected.")

    # Trigger PHP learning for comparison
    logger.info("\nStep 5: PHP learning engine comparison...")
    php_comparison = trigger_php_learning()

    # Close DB connection
    conn.close()
    logger.info("\nDatabase connection closed.")

    # Print comprehensive report
    print_report(results, correlation_analysis, regime, php_comparison)

    # Also output JSON summary for programmatic consumption
    summary = {
        'ok': True,
        'timestamp': datetime.utcnow().isoformat(),
        'regime': {'name': regime[0], 'confidence': round(regime[1], 2)},
        'dry_run': dry_run,
        'algorithms_analyzed': len(results),
        'total_combos_per_algo': len(TP_GRID) * len(SL_GRID) * len(HOLD_GRID),
        'results': [
            {
                'algorithm': r['algorithm'],
                'best_params': r['best_params'],
                'sharpe': r['full']['metrics']['sharpe'],
                'return_pct': r['full']['metrics']['total_return_pct'],
                'win_rate': r['full']['metrics']['win_rate'],
                'profit_factor': r['full']['metrics']['profit_factor'],
                'is_overfit': r['overfitting']['is_overfit'],
                'sharpe_decay_pct': r['overfitting']['sharpe_decay_pct'],
                'improvement_sharpe': r['improvement']['sharpe_delta'],
                'improvement_return': r['improvement']['return_delta'],
            }
            for r in results
        ],
        'correlation': {
            'highly_correlated': len(correlation_analysis.get('highly_correlated_pairs', [])),
            'unique_algorithms': correlation_analysis.get('unique_algorithms', []),
        },
        'scoreboard': {
            'strong': len([r for r in results if r['full']['metrics']['sharpe'] >= 1.0 and not r['overfitting']['is_overfit']]),
            'decent': len([r for r in results if 0 < r['full']['metrics']['sharpe'] < 1.0 and not r['overfitting']['is_overfit']]),
            'weak': len([r for r in results if r['full']['metrics']['sharpe'] <= 0]),
            'overfit': len([r for r in results if r['overfitting']['is_overfit']]),
        }
    }

    print("\n--- JSON SUMMARY ---")
    print(json.dumps(summary, indent=2, default=str))

    return summary


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Mutual Funds ML Parameter Optimizer with Walk-Forward Validation'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Run optimization but do not update database tables')
    args = parser.parse_args()

    run_optimization(dry_run=args.dry_run)
