#!/usr/bin/env python3
"""
FOREX ML Parameter Optimizer
==============================
Grid-search optimization of TP/SL/Hold parameters for all FOREX-trading
algorithms, using walk-forward validation to avoid overfitting.

The live trading system has 19 algorithms generating FOREX signals with static
default params.  This script:
  1. Connects to MySQL and fetches closed FOREX trades from lm_trades.
  2. Per-algorithm grid search over FOREX-appropriate TP/SL/Hold ranges.
  3. Walk-forward 70/30 train/test split; objective = Sharpe ratio.
  4. Regime-aware optimization (bull/neutral/bear) when enough data exists.
  5. Updates lm_ml_status, lm_walk_forward, lm_algo_performance.
  6. Deploys optimal params via algo_performance.php API.

Usage:
  python scripts/forex_ml_optimizer.py               # full run
  python scripts/forex_ml_optimizer.py --dry-run      # preview only
  python scripts/forex_ml_optimizer.py --min-trades 5  # lower threshold

Requirements: pip install mysql-connector-python requests
"""
import os
import sys
import json
import math
import argparse
import itertools
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import mysql.connector
import requests

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

MIN_TRADES_DEFAULT = 10          # Minimum closed trades before optimizing
TRAIN_RATIO = 0.70               # 70/30 walk-forward split
ANNUALIZE_FACTOR = math.sqrt(252)  # For Sharpe annualization

# FOREX default params (mirrors live_signals.php _ls_get_original_defaults)
FOREX_DEFAULTS = {
    'Momentum Burst':        {'tp': 1.5,  'sl': 0.75, 'hold': 8},
    'RSI Reversal':          {'tp': 2.0,  'sl': 1.0,  'hold': 12},
    'Breakout 24h':          {'tp': 8.0,  'sl': 2.0,  'hold': 16},
    'DCA Dip':               {'tp': 5.0,  'sl': 3.0,  'hold': 48},
    'Bollinger Squeeze':     {'tp': 2.5,  'sl': 1.5,  'hold': 8},
    'MACD Crossover':        {'tp': 2.0,  'sl': 1.0,  'hold': 12},
    'Consensus':             {'tp': 4.5,  'sl': 1.5,  'hold': 24},
    'Volatility Breakout':   {'tp': 3.0,  'sl': 2.0,  'hold': 16},
    'Trend Sniper':          {'tp': 0.4,  'sl': 0.2,  'hold': 8},
    'Dip Recovery':          {'tp': 0.6,  'sl': 0.4,  'hold': 16},
    'Volume Spike':          {'tp': 0.5,  'sl': 0.3,  'hold': 12},
    'VAM':                   {'tp': 0.4,  'sl': 0.2,  'hold': 12},
    'Mean Reversion Sniper': {'tp': 0.5,  'sl': 0.3,  'hold': 12},
    'ADX Trend Strength':    {'tp': 0.4,  'sl': 0.2,  'hold': 12},
    'StochRSI Crossover':    {'tp': 0.5,  'sl': 0.25, 'hold': 12},
    'Awesome Oscillator':    {'tp': 0.4,  'sl': 0.2,  'hold': 12},
    'RSI(2) Scalp':          {'tp': 0.3,  'sl': 0.15, 'hold': 6},
    'Ichimoku Cloud':        {'tp': 0.5,  'sl': 0.25, 'hold': 16},
    'Alpha Predator':        {'tp': 0.5,  'sl': 0.25, 'hold': 12},
    'Contrarian Fear/Greed': {'tp': 2.0,  'sl': 1.5,  'hold': 168},
}
GENERIC_DEFAULT = {'tp': 3.0, 'sl': 2.0, 'hold': 12}

# Grid search ranges (FOREX-appropriate: smaller moves than stocks/crypto)
TP_GRID = [round(x * 0.1, 2) for x in range(2, 31)]   # 0.2% to 3.0% step 0.1
SL_GRID = [round(x * 0.1, 2) for x in range(1, 21)]    # 0.1% to 2.0% step 0.1
HOLD_GRID = [4, 6, 8, 12, 16, 24, 36, 48, 72, 96, 120, 168]  # 4h to 7 days

# Regime thresholds (based on avg 24h change across FOREX pairs)
REGIME_BULL_THRESHOLD = 0.15     # avg change > +0.15% = bull
REGIME_BEAR_THRESHOLD = -0.15    # avg change < -0.15% = bear
MIN_TRADES_PER_REGIME = 8        # Need 8+ trades in a regime to optimize separately


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def connect_db():
    """Connect to MySQL with retries."""
    for attempt in range(3):
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
                connect_timeout=30,
                autocommit=True
            )
            return conn
        except mysql.connector.Error as e:
            print(f"  [WARN] DB connect attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                import time
                time.sleep(3)
    print("  [ERROR] Could not connect to database after 3 attempts")
    return None


def fetch_closed_forex_trades(conn):
    """Fetch all closed FOREX trades joined with signal metadata."""
    cursor = conn.cursor(dictionary=True)
    sql = """
        SELECT t.id, t.symbol, t.algorithm_name, t.direction,
               t.entry_time, t.entry_price, t.exit_time, t.exit_price,
               t.exit_reason, t.realized_pnl_usd, t.realized_pct,
               t.hold_hours, t.target_tp_pct, t.target_sl_pct,
               t.max_hold_hours, t.highest_price, t.lowest_price,
               s.param_source, s.signal_strength
        FROM lm_trades t
        LEFT JOIN lm_signals s ON t.signal_id = s.id
        WHERE t.asset_class = 'FOREX' AND t.status = 'closed'
        ORDER BY t.entry_time ASC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_forex_regime(conn):
    """
    Determine current FOREX regime from lm_price_cache.
    Uses average 24h change across FOREX pairs.
    Returns 'bull', 'neutral', or 'bear'.
    """
    cursor = conn.cursor(dictionary=True)
    sql = """
        SELECT AVG(change_24h_pct) as avg_change
        FROM lm_price_cache
        WHERE symbol IN ('EURUSD','GBPUSD','USDJPY','USDCAD','USDCHF',
                         'AUDUSD','NZDUSD','EURGBP')
    """
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()
        if row and row['avg_change'] is not None:
            avg = float(row['avg_change'])
            if avg > REGIME_BULL_THRESHOLD:
                return 'bull', avg
            elif avg < REGIME_BEAR_THRESHOLD:
                return 'bear', avg
            else:
                return 'neutral', avg
    except Exception as e:
        print(f"  [WARN] Could not fetch regime: {e}")
        cursor.close()
    return 'neutral', 0.0


def classify_trade_regime(trade):
    """
    Classify a single trade's regime based on its price action.
    Uses the trade's realized_pct as a proxy for market conditions at that time.
    For more accurate results, we use the entry_time to look up market_regimes.
    """
    # Simple heuristic: direction of the trade + outcome
    pnl = float(trade.get('realized_pct', 0) or 0)
    direction = trade.get('direction', 'LONG')

    # If the majority of trades in a window are positive, it's bullish
    # We'll use a simpler approach: tag from market_regimes table if available
    return None  # Will be enriched separately


def compute_sharpe(pnls):
    """
    Compute annualized Sharpe ratio from a list of PnL percentages.
    Returns 0 if not enough data or zero variance.
    """
    if len(pnls) < 2:
        return 0.0
    mean_pnl = sum(pnls) / len(pnls)
    variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
    std_pnl = math.sqrt(variance) if variance > 0 else 0
    if std_pnl < 0.0001:
        return mean_pnl * 100  # Degenerate case: all same value
    return (mean_pnl / std_pnl) * ANNUALIZE_FACTOR


def compute_win_rate(pnls):
    """Compute win rate from list of PnL percentages."""
    if not pnls:
        return 0.0
    wins = sum(1 for p in pnls if p > 0)
    return round(wins / len(pnls) * 100, 2)


def compute_profit_factor(pnls):
    """Compute profit factor: gross wins / gross losses."""
    gross_wins = sum(p for p in pnls if p > 0)
    gross_losses = abs(sum(p for p in pnls if p < 0))
    if gross_losses < 0.0001:
        return 99.99 if gross_wins > 0 else 0.0
    return round(gross_wins / gross_losses, 3)


def simulate_trades_with_params(trades, tp_pct, sl_pct, max_hold):
    """
    Simulate what PnL each trade would have achieved with given TP/SL/Hold params.

    For each trade we re-evaluate based on:
      - If the trade's high reached TP first -> profit = +tp_pct
      - If the trade's low hit SL first -> loss = -sl_pct
      - If actual hold > max_hold -> early exit at prorated PnL
      - Otherwise use actual realized_pct capped at TP/SL
    """
    simulated_pnls = []

    for trade in trades:
        actual_pnl = float(trade.get('realized_pct', 0) or 0)
        actual_hold = float(trade.get('hold_hours', 0) or 0)
        direction = trade.get('direction', 'LONG')
        entry_price = float(trade.get('entry_price', 0) or 0)
        highest = float(trade.get('highest_price', 0) or 0)
        lowest = float(trade.get('lowest_price', 0) or 0)

        if entry_price <= 0:
            simulated_pnls.append(actual_pnl)
            continue

        # Calculate max favorable / max adverse excursion
        if direction == 'LONG':
            max_favorable_pct = ((highest - entry_price) / entry_price) * 100 if highest > 0 else 0
            max_adverse_pct = ((entry_price - lowest) / entry_price) * 100 if lowest > 0 else 0
        else:  # SHORT
            max_favorable_pct = ((entry_price - lowest) / entry_price) * 100 if lowest > 0 else 0
            max_adverse_pct = ((highest - entry_price) / entry_price) * 100 if highest > 0 else 0

        # Determine simulated outcome
        # TP hit?
        if max_favorable_pct >= tp_pct:
            # Check if SL was hit first (simplified: if both hit, compare magnitudes)
            if max_adverse_pct >= sl_pct:
                # Both hit - use the actual PnL direction as tiebreaker
                if actual_pnl > 0:
                    sim_pnl = tp_pct
                else:
                    sim_pnl = -sl_pct
            else:
                sim_pnl = tp_pct
        # SL hit?
        elif max_adverse_pct >= sl_pct:
            sim_pnl = -sl_pct
        # Max hold exceeded?
        elif actual_hold > max_hold:
            # Pro-rate: use actual PnL but cap at TP/SL
            # Trades that exceed max_hold exit at whatever price is current
            hold_ratio = max_hold / actual_hold if actual_hold > 0 else 1.0
            sim_pnl = actual_pnl * hold_ratio
            sim_pnl = max(-sl_pct, min(sim_pnl, tp_pct))
        else:
            # Trade closed normally within params
            sim_pnl = max(-sl_pct, min(actual_pnl, tp_pct))

        simulated_pnls.append(sim_pnl)

    return simulated_pnls


def generate_smart_grid(algo_name):
    """
    Generate a grid of TP/SL/Hold combinations, centered around the
    algorithm's default values for faster convergence.

    Returns list of (tp, sl, hold) tuples.
    """
    defaults = FOREX_DEFAULTS.get(algo_name, GENERIC_DEFAULT)
    d_tp = defaults['tp']
    d_sl = defaults['sl']
    d_hold = defaults['hold']

    # Build TP grid centered on default (go wider for more exploration)
    tp_candidates = set()
    # Core: +/- 50% of default in 0.1 steps
    tp_lo = max(0.2, round(d_tp * 0.5, 1))
    tp_hi = min(3.0, round(d_tp * 1.5, 1))
    step = 0.1
    val = tp_lo
    while val <= tp_hi + 0.001:
        tp_candidates.add(round(val, 2))
        val += step
    # Also include some from the global grid for diversity
    for v in TP_GRID:
        if abs(v - d_tp) <= d_tp:
            tp_candidates.add(v)
    tp_list = sorted(tp_candidates)

    # Build SL grid centered on default
    sl_candidates = set()
    sl_lo = max(0.1, round(d_sl * 0.5, 1))
    sl_hi = min(2.0, round(d_sl * 1.5, 1))
    val = sl_lo
    while val <= sl_hi + 0.001:
        sl_candidates.add(round(val, 2))
        val += step
    for v in SL_GRID:
        if abs(v - d_sl) <= d_sl:
            sl_candidates.add(v)
    sl_list = sorted(sl_candidates)

    # Build Hold grid
    hold_candidates = set()
    for h in HOLD_GRID:
        if d_hold * 0.3 <= h <= d_hold * 3:
            hold_candidates.add(h)
    # Always include the default
    hold_candidates.add(d_hold)
    hold_list = sorted(hold_candidates)

    # Generate combinations
    combos = list(itertools.product(tp_list, sl_list, hold_list))

    # Filter: TP must be > SL (risk:reward > 1.0)
    combos = [(tp, sl, h) for tp, sl, h in combos if tp > sl]

    return combos


def regularization_penalty(tp, sl, hold, algo_name):
    """
    Small penalty for deviating far from known defaults.
    Prevents the optimizer from picking extreme corner solutions.
    """
    defaults = FOREX_DEFAULTS.get(algo_name, GENERIC_DEFAULT)
    d_tp, d_sl, d_hold = defaults['tp'], defaults['sl'], defaults['hold']

    # Normalized deviations
    tp_dev = abs(tp - d_tp) / max(d_tp, 0.1)
    sl_dev = abs(sl - d_sl) / max(d_sl, 0.1)
    hold_dev = abs(hold - d_hold) / max(d_hold, 1)

    return 0.02 * (tp_dev + sl_dev + hold_dev)


# ---------------------------------------------------------------------------
#  Core Optimizer
# ---------------------------------------------------------------------------

def optimize_algorithm(algo_name, trades, min_trades):
    """
    Run grid-search optimization for one algorithm.

    Returns dict with best params, train/test metrics, or None if insufficient data.
    """
    n = len(trades)
    if n < min_trades:
        return {
            'status': 'insufficient_data',
            'trades': n,
            'min_required': min_trades,
            'message': f"Need {min_trades - n} more trades"
        }

    # Sort by entry_time (should already be sorted from SQL)
    trades_sorted = sorted(trades, key=lambda t: t.get('entry_time', ''))

    # Walk-forward split
    split_idx = int(n * TRAIN_RATIO)
    train_trades = trades_sorted[:split_idx]
    test_trades = trades_sorted[split_idx:]

    if len(train_trades) < 5:
        return {
            'status': 'insufficient_train',
            'trades': n,
            'train_size': len(train_trades),
            'message': 'Not enough training data after split'
        }
    if len(test_trades) < 3:
        return {
            'status': 'insufficient_test',
            'trades': n,
            'test_size': len(test_trades),
            'message': 'Not enough test data after split'
        }

    # Generate grid
    grid = generate_smart_grid(algo_name)
    print(f"    Grid size: {len(grid)} combinations")

    best_score = -999
    best_params = None
    best_train_metrics = None
    best_test_metrics = None
    evaluations = 0

    for tp, sl, hold in grid:
        # Evaluate on TRAINING set
        train_pnls = simulate_trades_with_params(train_trades, tp, sl, hold)
        if len(train_pnls) < 3:
            continue

        train_sharpe = compute_sharpe(train_pnls)
        penalty = regularization_penalty(tp, sl, hold, algo_name)
        score = train_sharpe - penalty

        evaluations += 1

        if score > best_score:
            # Also evaluate on TEST set (but don't optimize on it!)
            test_pnls = simulate_trades_with_params(test_trades, tp, sl, hold)
            test_sharpe = compute_sharpe(test_pnls)
            test_win_rate = compute_win_rate(test_pnls)
            test_pf = compute_profit_factor(test_pnls)
            test_total_pnl = sum(test_pnls)

            best_score = score
            best_params = {'tp': tp, 'sl': sl, 'hold': hold}
            best_train_metrics = {
                'sharpe': round(train_sharpe, 4),
                'win_rate': compute_win_rate(train_pnls),
                'profit_factor': compute_profit_factor(train_pnls),
                'total_pnl': round(sum(train_pnls), 4),
                'trades': len(train_pnls),
                'avg_pnl': round(sum(train_pnls) / len(train_pnls), 4),
            }
            best_test_metrics = {
                'sharpe': round(test_sharpe, 4),
                'win_rate': test_win_rate,
                'profit_factor': test_pf,
                'total_pnl': round(test_total_pnl, 4),
                'trades': len(test_pnls),
                'avg_pnl': round(sum(test_pnls) / len(test_pnls), 4) if test_pnls else 0,
            }

    if best_params is None:
        return {
            'status': 'no_valid_params',
            'trades': n,
            'evaluations': evaluations,
            'message': 'No valid parameter combination found'
        }

    # Check for overfitting: if test Sharpe is much worse than train Sharpe
    sharpe_decay = 0.0
    if best_train_metrics['sharpe'] != 0:
        sharpe_decay = ((best_train_metrics['sharpe'] - best_test_metrics['sharpe'])
                        / abs(best_train_metrics['sharpe'])) * 100
    is_overfit = sharpe_decay > 50  # Test Sharpe decays >50% = likely overfit

    # Compute default baseline for comparison
    defaults = FOREX_DEFAULTS.get(algo_name, GENERIC_DEFAULT)
    default_test_pnls = simulate_trades_with_params(
        test_trades, defaults['tp'], defaults['sl'], defaults['hold']
    )
    default_test_sharpe = compute_sharpe(default_test_pnls)
    default_test_wr = compute_win_rate(default_test_pnls)

    # Only deploy if optimized params beat defaults on test set
    beats_default = best_test_metrics['sharpe'] > default_test_sharpe

    # Date ranges for walk-forward record
    train_start = str(train_trades[0].get('entry_time', ''))[:10] if train_trades else ''
    train_end = str(train_trades[-1].get('entry_time', ''))[:10] if train_trades else ''
    test_start = str(test_trades[0].get('entry_time', ''))[:10] if test_trades else ''
    test_end = str(test_trades[-1].get('entry_time', ''))[:10] if test_trades else ''

    return {
        'status': 'optimized',
        'trades': n,
        'evaluations': evaluations,
        'best_params': best_params,
        'train': best_train_metrics,
        'test': best_test_metrics,
        'default_baseline': {
            'tp': defaults['tp'],
            'sl': defaults['sl'],
            'hold': defaults['hold'],
            'test_sharpe': round(default_test_sharpe, 4),
            'test_win_rate': default_test_wr,
        },
        'sharpe_decay_pct': round(sharpe_decay, 2),
        'is_overfit': is_overfit,
        'beats_default': beats_default,
        'should_deploy': beats_default and not is_overfit,
        'train_start': train_start,
        'train_end': train_end,
        'test_start': test_start,
        'test_end': test_end,
    }


def optimize_by_regime(algo_name, trades, min_trades):
    """
    Regime-aware optimization: separate params for bull/neutral/bear.
    Only if we have enough trades per regime.
    Returns dict keyed by regime, or None if not enough data.
    """
    # Group trades by regime (using their realized_pct as a rough proxy)
    # Better approach: join with market_regimes table, but that may not have FOREX-specific data
    # We'll use a rolling-window approach on the trades themselves
    regime_trades = {'bull': [], 'neutral': [], 'bear': []}

    # Classify each trade's regime based on surrounding trades' performance
    window = 5
    for i, trade in enumerate(trades):
        # Get surrounding trades for regime classification
        start = max(0, i - window)
        end = min(len(trades), i + window + 1)
        window_pnls = [float(t.get('realized_pct', 0) or 0) for t in trades[start:end]]
        avg_pnl = sum(window_pnls) / len(window_pnls) if window_pnls else 0

        if avg_pnl > 0.1:
            regime_trades['bull'].append(trade)
        elif avg_pnl < -0.1:
            regime_trades['bear'].append(trade)
        else:
            regime_trades['neutral'].append(trade)

    results = {}
    for regime, rtrades in regime_trades.items():
        if len(rtrades) >= MIN_TRADES_PER_REGIME:
            result = optimize_algorithm(f"{algo_name} ({regime})", rtrades, MIN_TRADES_PER_REGIME)
            if result and result.get('status') == 'optimized':
                results[regime] = result

    return results if results else None


# ---------------------------------------------------------------------------
#  Database Update Functions
# ---------------------------------------------------------------------------

def update_ml_status(conn, algo_name, result, current_regime, dry_run=False):
    """Update lm_ml_status with optimization results."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor(dictionary=True)

    closed_trades = result.get('trades', 0)
    ml_ready = 1 if result.get('status') == 'optimized' else 0

    if result.get('status') == 'optimized' and result.get('should_deploy'):
        bp = result['best_params']
        tp, sl, hold = bp['tp'], bp['sl'], bp['hold']
        param_source = 'forex_ml'
        wr = result['test']['win_rate']
        sharpe = result['test']['sharpe']
        pf = result['test']['profit_factor']
        total_pnl = result['test']['total_pnl']
        status = 'optimized'
        reason = (f"Grid search: Sharpe {sharpe:.4f}, WR {wr:.1f}%, "
                  f"PF {pf:.3f}. Regime: {current_regime}")
    elif result.get('status') == 'optimized':
        # Optimized but not deploying (overfit or doesn't beat default)
        bp = result['best_params']
        tp, sl, hold = bp['tp'], bp['sl'], bp['hold']
        defaults = FOREX_DEFAULTS.get(algo_name, GENERIC_DEFAULT)
        tp, sl, hold = defaults['tp'], defaults['sl'], defaults['hold']
        param_source = 'default'
        wr = result['test']['win_rate']
        sharpe = result['test']['sharpe']
        pf = result['test']['profit_factor']
        total_pnl = result['test']['total_pnl']
        status = 'overfit_detected' if result.get('is_overfit') else 'default_wins'
        reason = (f"Optimized params did not beat defaults. "
                  f"Sharpe decay: {result.get('sharpe_decay_pct', 0):.1f}%")
    else:
        defaults = FOREX_DEFAULTS.get(algo_name, GENERIC_DEFAULT)
        tp, sl, hold = defaults['tp'], defaults['sl'], defaults['hold']
        param_source = 'default'
        wr = 0
        sharpe = 0
        pf = 0
        total_pnl = 0
        status = 'collecting_data'
        reason = result.get('message', f'Need more trades ({closed_trades}/{MIN_TRADES_DEFAULT})')

    if dry_run:
        print(f"    [DRY RUN] Would update lm_ml_status: {algo_name} FOREX -> "
              f"tp={tp}, sl={sl}, hold={hold}, status={status}")
        return

    sql = """
        INSERT INTO lm_ml_status
            (algorithm_name, asset_class, closed_trades, ml_ready,
             current_tp, current_sl, current_hold, param_source,
             current_win_rate, current_sharpe, current_pf, total_pnl,
             last_optimization, optimization_count,
             status, status_reason, updated_at, created_at)
        VALUES (%s, 'FOREX', %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, 1,
                %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            closed_trades = %s,
            ml_ready = %s,
            current_tp = %s,
            current_sl = %s,
            current_hold = %s,
            param_source = %s,
            current_win_rate = %s,
            current_sharpe = %s,
            current_pf = %s,
            total_pnl = %s,
            last_optimization = %s,
            optimization_count = optimization_count + 1,
            status = %s,
            status_reason = %s,
            updated_at = %s
    """
    params = (
        # INSERT values
        algo_name, closed_trades, ml_ready,
        tp, sl, hold, param_source,
        wr, sharpe, pf, total_pnl,
        now,
        status, reason, now, now,
        # ON DUPLICATE KEY UPDATE values
        closed_trades, ml_ready,
        tp, sl, hold, param_source,
        wr, sharpe, pf, total_pnl,
        now,
        status, reason, now,
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print(f"    [ERROR] lm_ml_status update failed: {e}")
    finally:
        cursor.close()


def insert_walk_forward(conn, algo_name, result, dry_run=False):
    """Insert walk-forward validation record."""
    if result.get('status') != 'optimized':
        return

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    bp = result['best_params']

    if dry_run:
        print(f"    [DRY RUN] Would insert lm_walk_forward: {algo_name} FOREX "
              f"train_sharpe={result['train']['sharpe']}, test_sharpe={result['test']['sharpe']}")
        return

    cursor = conn.cursor()
    sql = """
        INSERT INTO lm_walk_forward
            (algorithm_name, asset_class,
             train_start, train_end, test_start, test_end,
             train_sharpe, train_win_rate, train_trades,
             test_sharpe, test_win_rate, test_trades, test_pnl,
             tp_pct, sl_pct, max_hold_hours,
             sharpe_decay_pct, is_overfit, created_at)
        VALUES (%s, 'FOREX',
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s)
    """
    params = (
        algo_name,
        result['train_start'], result['train_end'],
        result['test_start'], result['test_end'],
        result['train']['sharpe'], result['train']['win_rate'], result['train']['trades'],
        result['test']['sharpe'], result['test']['win_rate'], result['test']['trades'],
        result['test']['total_pnl'],
        bp['tp'], bp['sl'], bp['hold'],
        result['sharpe_decay_pct'], 1 if result['is_overfit'] else 0, now,
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print(f"    [ERROR] lm_walk_forward insert failed: {e}")
    finally:
        cursor.close()


def insert_model_version(conn, algo_name, result, dry_run=False):
    """Insert model version record for deployed params."""
    if not result.get('should_deploy'):
        return

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    bp = result['best_params']

    if dry_run:
        print(f"    [DRY RUN] Would insert lm_model_versions: {algo_name} FOREX "
              f"v+1 tp={bp['tp']} sl={bp['sl']} hold={bp['hold']}")
        return

    cursor = conn.cursor(dictionary=True)

    # Retire previous active version
    try:
        cursor.execute("""
            UPDATE lm_model_versions
            SET is_active = 0, retired_at = %s, retire_reason = 'Superseded by forex_ml_optimizer'
            WHERE algorithm_name = %s AND asset_class = 'FOREX' AND is_active = 1
        """, (now, algo_name))
    except Exception:
        pass

    # Get next version number
    try:
        cursor.execute("""
            SELECT COALESCE(MAX(version), 0) + 1 as next_ver
            FROM lm_model_versions
            WHERE algorithm_name = %s AND asset_class = 'FOREX'
        """, (algo_name,))
        row = cursor.fetchone()
        next_ver = row['next_ver'] if row else 1
    except Exception:
        next_ver = 1

    sql = """
        INSERT INTO lm_model_versions
            (algorithm_name, asset_class, version,
             tp_pct, sl_pct, max_hold_hours,
             sharpe_at_deploy, win_rate_at_deploy, trades_at_deploy,
             is_active, deployed_at, created_at)
        VALUES (%s, 'FOREX', %s,
                %s, %s, %s,
                %s, %s, %s,
                1, %s, %s)
    """
    params = (
        algo_name, next_ver,
        bp['tp'], bp['sl'], bp['hold'],
        result['test']['sharpe'], result['test']['win_rate'], result['trades'],
        now, now,
    )
    try:
        cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        print(f"    [ERROR] lm_model_versions insert failed: {e}")
    finally:
        cursor.close()


def deploy_via_api(algo_name, result, dry_run=False):
    """Deploy optimal params via the algo_performance.php API."""
    if not result.get('should_deploy'):
        return False

    bp = result['best_params']

    if dry_run:
        print(f"    [DRY RUN] Would POST to algo_performance.php: "
              f"{algo_name} FOREX tp={bp['tp']} sl={bp['sl']} hold={bp['hold']}")
        return True

    try:
        url = f"{API_BASE}/algo_performance.php"
        resp = requests.post(url, params={
            'action': 'update_params',
            'key': ADMIN_KEY,
            'algorithm': algo_name,
            'asset_class': 'FOREX',
            'tp': bp['tp'],
            'sl': bp['sl'],
            'hold': bp['hold'],
            'source': 'forex_ml_optimizer'
        }, headers=API_HEADERS, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            if data.get('ok'):
                print(f"    [API] Deployed: {algo_name} FOREX -> "
                      f"TP={bp['tp']}%, SL={bp['sl']}%, Hold={bp['hold']}h")
                return True
            else:
                print(f"    [API] Deploy response not ok: {data}")
        else:
            print(f"    [API] Deploy HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"    [API] Deploy error: {e}")

    return False


# ---------------------------------------------------------------------------
#  Summary Report
# ---------------------------------------------------------------------------

def print_summary(results, regime, regime_change, elapsed):
    """Print formatted summary of all optimization results."""
    print("\n" + "=" * 80)
    print("FOREX ML PARAMETER OPTIMIZER — SUMMARY REPORT")
    print("=" * 80)
    print(f"  Run time:     {elapsed:.1f}s")
    print(f"  Regime:       {regime} (avg 24h change: {regime_change:+.4f}%)")
    print(f"  Timestamp:    {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    # Categorize results
    optimized = []
    deployed = []
    insufficient = []
    not_deployed = []

    for algo_name, result in sorted(results.items()):
        status = result.get('status', 'unknown')
        if status == 'optimized':
            optimized.append((algo_name, result))
            if result.get('should_deploy'):
                deployed.append((algo_name, result))
            else:
                not_deployed.append((algo_name, result))
        else:
            insufficient.append((algo_name, result))

    # --- Deployed Algorithms ---
    if deployed:
        print(f"  DEPLOYED ({len(deployed)} algorithms):")
        print(f"  {'Algorithm':<25} {'Trades':>6} {'TP%':>6} {'SL%':>6} {'Hold':>5} "
              f"{'Train Sh':>9} {'Test Sh':>8} {'Test WR':>8} {'vs Dflt':>8}")
        print("  " + "-" * 78)
        for algo_name, r in deployed:
            bp = r['best_params']
            dbl = r['default_baseline']
            improvement = r['test']['sharpe'] - dbl['test_sharpe']
            print(f"  {algo_name:<25} {r['trades']:>6} {bp['tp']:>6.2f} {bp['sl']:>6.2f} "
                  f"{bp['hold']:>5} {r['train']['sharpe']:>9.4f} {r['test']['sharpe']:>8.4f} "
                  f"{r['test']['win_rate']:>7.1f}% {improvement:>+7.4f}")
        print()

    # --- Optimized but NOT deployed ---
    if not_deployed:
        print(f"  NOT DEPLOYED ({len(not_deployed)} algorithms — overfit or default wins):")
        for algo_name, r in not_deployed:
            reason = "OVERFIT" if r.get('is_overfit') else "DEFAULT WINS"
            bp = r['best_params']
            print(f"    {algo_name:<25} trades={r['trades']:>4}  "
                  f"test_sharpe={r['test']['sharpe']:>7.4f}  "
                  f"decay={r.get('sharpe_decay_pct', 0):>5.1f}%  [{reason}]")
        print()

    # --- Insufficient Data ---
    if insufficient:
        print(f"  INSUFFICIENT DATA ({len(insufficient)} algorithms):")
        for algo_name, r in insufficient:
            print(f"    {algo_name:<25} trades={r.get('trades', 0):>4}  {r.get('message', '')}")
        print()

    # --- Overall Stats ---
    total = len(results)
    print(f"  TOTALS: {total} algos checked | {len(optimized)} optimized | "
          f"{len(deployed)} deployed | {len(insufficient)} need more data")
    print("=" * 80)


# ---------------------------------------------------------------------------
#  Main Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='FOREX ML Parameter Optimizer — Grid search over TP/SL/Hold')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without updating DB or deploying')
    parser.add_argument('--min-trades', type=int, default=MIN_TRADES_DEFAULT,
                        help=f'Minimum closed trades per algorithm (default: {MIN_TRADES_DEFAULT})')
    parser.add_argument('--algo', type=str, default=None,
                        help='Optimize only a specific algorithm (by name)')
    parser.add_argument('--skip-regime', action='store_true',
                        help='Skip regime-aware optimization')
    parser.add_argument('--skip-api-deploy', action='store_true',
                        help='Skip deploying via API (DB updates only)')
    args = parser.parse_args()

    import time
    start_time = time.time()

    print("=" * 80)
    print("FOREX ML PARAMETER OPTIMIZER")
    print("=" * 80)
    print(f"  Mode:        {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Min trades:  {args.min_trades}")
    print(f"  Algorithm:   {args.algo or 'ALL'}")
    print(f"  Timestamp:   {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    # --- 1. Connect to Database ---
    print("[1/6] Connecting to database...")
    conn = connect_db()
    if not conn:
        print("FATAL: Cannot connect to database. Exiting.")
        sys.exit(1)
    print("  Connected successfully.")

    # --- 2. Fetch Closed FOREX Trades ---
    print("\n[2/6] Fetching closed FOREX trades...")
    all_trades = fetch_closed_forex_trades(conn)
    print(f"  Found {len(all_trades)} closed FOREX trades total.")

    if not all_trades:
        print("\n  No closed FOREX trades found. Nothing to optimize.")
        print("  The system needs to generate and close FOREX trades first.")
        print("  This is expected for a new system — trades close via TP/SL/max-hold.")
        conn.close()
        sys.exit(0)

    # Group by algorithm
    algo_trades = defaultdict(list)
    for trade in all_trades:
        algo = trade.get('algorithm_name', 'Unknown')
        if algo:
            algo_trades[algo].append(trade)

    print(f"  Algorithms with trades: {len(algo_trades)}")
    for algo, trades in sorted(algo_trades.items(), key=lambda x: -len(x[1])):
        print(f"    {algo:<30} {len(trades):>4} trades")

    # --- 3. Detect FOREX Regime ---
    print("\n[3/6] Detecting current FOREX regime...")
    regime, regime_change = fetch_forex_regime(conn)
    print(f"  Current regime: {regime} (avg 24h change: {regime_change:+.4f}%)")

    # --- 4. Run Grid Search Per Algorithm ---
    print("\n[4/6] Running grid search optimization...")
    results = {}

    algos_to_optimize = sorted(algo_trades.keys())
    if args.algo:
        algos_to_optimize = [a for a in algos_to_optimize if a == args.algo]
        if not algos_to_optimize:
            print(f"  Algorithm '{args.algo}' not found in FOREX trades.")
            print(f"  Available: {', '.join(sorted(algo_trades.keys()))}")
            conn.close()
            sys.exit(1)

    for i, algo_name in enumerate(algos_to_optimize, 1):
        trades = algo_trades[algo_name]
        print(f"\n  [{i}/{len(algos_to_optimize)}] {algo_name} ({len(trades)} trades)")

        result = optimize_algorithm(algo_name, trades, args.min_trades)
        results[algo_name] = result

        status = result.get('status', 'unknown')
        if status == 'optimized':
            bp = result['best_params']
            deploy_flag = "DEPLOY" if result['should_deploy'] else "SKIP"
            overfit_flag = " [OVERFIT]" if result.get('is_overfit') else ""
            print(f"    Best: TP={bp['tp']:.2f}% SL={bp['sl']:.2f}% Hold={bp['hold']}h")
            print(f"    Train: Sharpe={result['train']['sharpe']:.4f} "
                  f"WR={result['train']['win_rate']:.1f}% PF={result['train']['profit_factor']:.3f}")
            print(f"    Test:  Sharpe={result['test']['sharpe']:.4f} "
                  f"WR={result['test']['win_rate']:.1f}% PF={result['test']['profit_factor']:.3f}")
            dbl = result['default_baseline']
            print(f"    Default baseline: Sharpe={dbl['test_sharpe']:.4f} "
                  f"WR={dbl['test_win_rate']:.1f}%")
            print(f"    Sharpe decay: {result['sharpe_decay_pct']:.1f}%{overfit_flag}")
            print(f"    Decision: {deploy_flag}")

            # Regime-aware optimization (if enabled and enough data)
            if not args.skip_regime and len(trades) >= MIN_TRADES_PER_REGIME * 3:
                regime_results = optimize_by_regime(algo_name, trades, args.min_trades)
                if regime_results:
                    print(f"    Regime-specific results:")
                    for reg, rr in regime_results.items():
                        if rr.get('status') == 'optimized':
                            rbp = rr['best_params']
                            print(f"      {reg:>8}: TP={rbp['tp']:.2f}% SL={rbp['sl']:.2f}% "
                                  f"Hold={rbp['hold']}h Sharpe={rr['test']['sharpe']:.4f}")
        else:
            print(f"    Status: {status} — {result.get('message', '')}")

    # --- 5. Update Database ---
    print("\n[5/6] Updating database tables...")
    deployed_count = 0

    for algo_name, result in results.items():
        print(f"  Updating {algo_name}...")

        # Update lm_ml_status
        update_ml_status(conn, algo_name, result, regime, dry_run=args.dry_run)

        # Insert walk-forward record
        insert_walk_forward(conn, algo_name, result, dry_run=args.dry_run)

        # Insert model version (if deploying)
        insert_model_version(conn, algo_name, result, dry_run=args.dry_run)

        if result.get('should_deploy'):
            deployed_count += 1

    # Also update lm_ml_status for known FOREX algorithms that have NO trades yet
    all_forex_algos = set(FOREX_DEFAULTS.keys())
    algos_with_trades = set(algo_trades.keys())
    algos_no_trades = all_forex_algos - algos_with_trades

    if algos_no_trades and not args.algo:
        print(f"\n  Updating {len(algos_no_trades)} algorithms with 0 trades...")
        for algo_name in sorted(algos_no_trades):
            no_trade_result = {
                'status': 'no_trades',
                'trades': 0,
                'message': 'No closed FOREX trades yet'
            }
            update_ml_status(conn, algo_name, no_trade_result, regime, dry_run=args.dry_run)

    # --- 6. Deploy via API ---
    print("\n[6/6] Deploying optimized params via API...")
    api_deployed = 0

    if args.skip_api_deploy:
        print("  Skipped (--skip-api-deploy flag)")
    elif args.dry_run:
        for algo_name, result in results.items():
            deploy_via_api(algo_name, result, dry_run=True)
    else:
        for algo_name, result in results.items():
            if deploy_via_api(algo_name, result, dry_run=False):
                api_deployed += 1

        if api_deployed > 0:
            print(f"  Deployed {api_deployed} algorithm params via API")
        else:
            print("  No params deployed (none qualified or all insufficient data)")

    # --- Summary ---
    elapsed = time.time() - start_time
    print_summary(results, regime, regime_change, elapsed)

    # Close DB
    conn.close()

    # Exit code: 0 if any optimization ran, 1 if total failure
    optimized_count = sum(1 for r in results.values() if r.get('status') == 'optimized')
    if optimized_count > 0:
        print(f"\nSuccess: {optimized_count} algorithm(s) optimized, {deployed_count} deployed.")
    elif all_trades:
        print(f"\nNo algorithms had enough data for optimization (min={args.min_trades}).")
    else:
        print("\nNo FOREX trades found. System needs to accumulate trade data first.")


if __name__ == '__main__':
    main()
