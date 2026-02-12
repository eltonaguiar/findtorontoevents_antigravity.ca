#!/usr/bin/env python3
"""
Cross-Asset ML Intelligence System
====================================
Identifies improvements across ALL asset classes (STOCK, CRYPTO, FOREX, SPORTS)
by filling the empty ML tracking tables with actionable data.

Modules:
  1. Cross-Asset Signal Correlation Analysis   -> lm_cross_correlation
  2. Ensemble Weight Optimization              -> lm_ensemble_weights
  3. Prediction Calibration Check              -> lm_prediction_calibration
  4. Feature Importance Analysis               -> lm_feature_importance
  5. ML Readiness Assessment                   -> lm_ml_status
  6. Alpha Decay Detection                     -> console report + lm_ml_status flags

Usage:
  python scripts/cross_asset_ml_intelligence.py
  python scripts/cross_asset_ml_intelligence.py --dry-run
  python scripts/cross_asset_ml_intelligence.py --module correlation
  python scripts/cross_asset_ml_intelligence.py --module ensemble --dry-run

Requirements: pip install mysql-connector-python numpy requests
"""
import os
import sys
import json
import math
import argparse
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cross_asset_ml')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')
API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# Thresholds
CORRELATION_HIGH = 0.7      # Algorithms above this are redundant
CORRELATION_LOW = 0.3       # Algorithms below this are orthogonal (good)
MIN_TRADES_ML_READY = 20    # Minimum closed trades for ML readiness
ALPHA_DECAY_TRADES = 30     # Minimum trades for alpha decay detection
ALPHA_DECAY_THRESHOLD = 15  # Recent WR must be >15% below historical to flag
CALIBRATION_BUCKETS = [
    (0, 20, '0-20'),
    (20, 40, '20-40'),
    (40, 60, '40-60'),
    (60, 80, '60-80'),
    (80, 101, '80-100'),
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')


def connect_db():
    """Connect to MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


def ensure_schema(conn):
    """
    Ensure all ML intelligence tables exist.
    Calls the PHP API to create tables, with DB fallback.
    """
    import requests
    try:
        url = f"{API_BASE}/ml_intelligence.php?action=schema&key={ADMIN_KEY}"
        resp = requests.get(url, headers=API_HEADERS, timeout=30)
        data = resp.json()
        if data.get('ok'):
            logger.info("Schema ensured via API")
            return True
    except Exception as e:
        logger.warning("API schema call failed: %s — using DB fallback", e)

    # Fallback: create tables directly
    cursor = conn.cursor()
    tables = [
        """CREATE TABLE IF NOT EXISTS lm_cross_correlation (
            id INT AUTO_INCREMENT PRIMARY KEY,
            algo_a VARCHAR(100) NOT NULL,
            asset_a VARCHAR(20) NOT NULL,
            algo_b VARCHAR(100) NOT NULL,
            asset_b VARCHAR(20) NOT NULL,
            correlation DECIMAL(5,4) DEFAULT NULL,
            sample_size INT DEFAULT 0,
            calc_date DATE NOT NULL,
            created_at DATETIME,
            INDEX idx_date (calc_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""",
        """CREATE TABLE IF NOT EXISTS lm_ensemble_weights (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asset_class VARCHAR(20) NOT NULL,
            algorithm_name VARCHAR(100) NOT NULL,
            ensemble_weight DECIMAL(5,4) DEFAULT 0,
            rolling_sharpe_30d DECIMAL(8,4) DEFAULT NULL,
            rolling_win_rate_30d DECIMAL(5,2) DEFAULT NULL,
            correlation_to_portfolio DECIMAL(5,4) DEFAULT NULL,
            information_ratio DECIMAL(8,4) DEFAULT NULL,
            calc_date DATE NOT NULL,
            created_at DATETIME,
            UNIQUE KEY uq_ensemble (asset_class, algorithm_name, calc_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""",
        """CREATE TABLE IF NOT EXISTS lm_prediction_calibration (
            id INT AUTO_INCREMENT PRIMARY KEY,
            algorithm_name VARCHAR(100) NOT NULL,
            asset_class VARCHAR(20) NOT NULL,
            confidence_bucket VARCHAR(20) NOT NULL,
            total_predictions INT DEFAULT 0,
            correct_predictions INT DEFAULT 0,
            actual_accuracy DECIMAL(5,2) DEFAULT NULL,
            calibration_error DECIMAL(5,4) DEFAULT NULL,
            calc_date DATE NOT NULL,
            created_at DATETIME,
            INDEX idx_algo_date (algorithm_name, asset_class, calc_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""",
        """CREATE TABLE IF NOT EXISTS lm_feature_importance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            algorithm_name VARCHAR(100) NOT NULL,
            asset_class VARCHAR(20) NOT NULL,
            feature_name VARCHAR(100) NOT NULL,
            importance_score DECIMAL(8,4) DEFAULT 0,
            importance_rank INT DEFAULT 0,
            calc_date DATE NOT NULL,
            sample_size INT DEFAULT 0,
            created_at DATETIME,
            INDEX idx_algo_date (algorithm_name, asset_class, calc_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""",
        """CREATE TABLE IF NOT EXISTS lm_ml_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            algorithm_name VARCHAR(100) NOT NULL,
            asset_class VARCHAR(20) NOT NULL,
            closed_trades INT DEFAULT 0,
            min_trades_needed INT DEFAULT 20,
            ml_ready TINYINT DEFAULT 0,
            current_tp DECIMAL(5,2) DEFAULT NULL,
            current_sl DECIMAL(5,2) DEFAULT NULL,
            current_hold INT DEFAULT NULL,
            param_source VARCHAR(20) DEFAULT 'default',
            current_win_rate DECIMAL(5,2) DEFAULT NULL,
            current_sharpe DECIMAL(8,4) DEFAULT NULL,
            current_pf DECIMAL(5,3) DEFAULT NULL,
            total_pnl DECIMAL(10,2) DEFAULT 0,
            last_optimization DATETIME DEFAULT NULL,
            optimization_count INT DEFAULT 0,
            best_sharpe_ever DECIMAL(8,4) DEFAULT NULL,
            backtest_sharpe DECIMAL(8,4) DEFAULT NULL,
            backtest_grade VARCHAR(5) DEFAULT NULL,
            backtest_trades INT DEFAULT 0,
            forward_backtest_overlap TINYINT DEFAULT 0,
            status VARCHAR(30) DEFAULT 'collecting_data',
            status_reason TEXT,
            updated_at DATETIME,
            created_at DATETIME,
            UNIQUE KEY uq_algo_asset (algorithm_name, asset_class)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8""",
    ]
    for sql in tables:
        try:
            cursor.execute(sql)
        except Exception as e:
            logger.warning("Table create warning: %s", e)
    conn.commit()
    cursor.close()
    logger.info("Schema ensured via direct DB")
    return True


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------

def fetch_signals(conn):
    """Fetch all signals from lm_signals."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, asset_class, symbol, algorithm_name, signal_type,
               signal_strength, entry_price, target_tp_pct, target_sl_pct,
               max_hold_hours, signal_time, status
        FROM lm_signals
        ORDER BY signal_time ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    logger.info("Fetched %d signals from lm_signals", len(rows))
    return rows


def fetch_closed_trades(conn):
    """Fetch all closed trades from lm_trades."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, asset_class, symbol, algorithm_name, signal_id,
               direction, entry_time, entry_price, position_value_usd,
               target_tp_pct, target_sl_pct, max_hold_hours,
               exit_time, exit_price, exit_reason,
               realized_pnl_usd, realized_pct, hold_hours, status
        FROM lm_trades
        WHERE status = 'closed'
          AND algorithm_name != ''
        ORDER BY entry_time ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    logger.info("Fetched %d closed trades from lm_trades", len(rows))
    return rows


def fetch_regime(conn):
    """Fetch latest market regime data."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT date, hmm_regime, hmm_confidence, composite_score,
                   vix_level, vix_regime
            FROM lm_market_regime
            ORDER BY date DESC
            LIMIT 90
        """)
        rows = cursor.fetchall()
    except Exception:
        rows = []
    cursor.close()
    logger.info("Fetched %d regime records", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def calc_sharpe(returns, annualize_factor=252):
    """Annualized Sharpe ratio from a list of returns (as decimals, e.g. 0.05 for 5%)."""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance) if variance > 0 else 0
    if std < 1e-10:
        return 0.0
    return (mean_r / std) * math.sqrt(annualize_factor)


def calc_rolling_sharpe(returns, window=30):
    """Rolling Sharpe over last `window` returns."""
    if len(returns) < window:
        return calc_sharpe(returns)
    recent = returns[-window:]
    return calc_sharpe(recent)


def calc_win_rate(trades):
    """Win rate from trades list (each must have 'realized_pnl_usd' key)."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if float(t.get('realized_pnl_usd', 0)) > 0)
    return round(wins / len(trades) * 100, 2)


def group_by(items, key_fn):
    """Group items into dict of lists by key function."""
    groups = defaultdict(list)
    for item in items:
        groups[key_fn(item)] = groups.get(key_fn(item), [])
        groups[key_fn(item)].append(item)
    return dict(groups)


def safe_float(val, default=0.0):
    """Safely convert to float."""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 1: Cross-Asset Signal Correlation Analysis
# ═══════════════════════════════════════════════════════════════════════════

def run_correlation_analysis(conn, signals, dry_run=False):
    """
    Compute pairwise correlation between algorithm signal patterns.

    For each pair of algorithms, we build a binary vector:
    for each (symbol, date), did the algorithm fire a signal?
    Then compute Pearson correlation between these vectors.
    """
    print("\n" + "=" * 80)
    print("  MODULE 1: CROSS-ASSET SIGNAL CORRELATION ANALYSIS")
    print("=" * 80)

    if not signals:
        print("  [SKIP] No signals found in lm_signals")
        return {'pairs_analyzed': 0, 'redundant': [], 'orthogonal': []}

    # Build signal matrix: for each algorithm, record (symbol, date) combos
    algo_signals = defaultdict(set)
    all_points = set()

    for sig in signals:
        algo = sig['algorithm_name']
        asset = sig['asset_class']
        sym = sig['symbol']
        sig_time = sig.get('signal_time')
        if not sig_time or not algo:
            continue

        # Normalize to date string
        if hasattr(sig_time, 'strftime'):
            date_str = sig_time.strftime('%Y-%m-%d')
        else:
            date_str = str(sig_time)[:10]

        point = (sym, date_str)
        key = (algo, asset)
        algo_signals[key].add(point)
        all_points.add(point)

    all_points_list = sorted(all_points)
    algo_keys = sorted(algo_signals.keys())

    if len(algo_keys) < 2:
        print("  [SKIP] Need at least 2 algorithms with signals for correlation")
        return {'pairs_analyzed': 0, 'redundant': [], 'orthogonal': []}

    if len(all_points_list) < 5:
        print("  [SKIP] Need at least 5 unique signal points for meaningful correlation")
        return {'pairs_analyzed': 0, 'redundant': [], 'orthogonal': []}

    print(f"  Algorithms: {len(algo_keys)}")
    print(f"  Unique signal points: {len(all_points_list)}")

    # Build binary vectors
    point_to_idx = {p: i for i, p in enumerate(all_points_list)}
    n_points = len(all_points_list)

    algo_vectors = {}
    for key in algo_keys:
        vec = [0] * n_points
        for point in algo_signals[key]:
            vec[point_to_idx[point]] = 1
        algo_vectors[key] = vec

    # Compute pairwise Pearson correlation
    def pearson_corr(v1, v2):
        n = len(v1)
        if n < 5:
            return None
        s1 = sum(v1)
        s2 = sum(v2)
        # If either vector is all-zero or all-one, correlation is undefined
        if s1 == 0 or s1 == n or s2 == 0 or s2 == n:
            return None
        mean1 = s1 / n
        mean2 = s2 / n
        cov = sum((v1[i] - mean1) * (v2[i] - mean2) for i in range(n)) / n
        std1 = math.sqrt(sum((v1[i] - mean1) ** 2 for i in range(n)) / n)
        std2 = math.sqrt(sum((v2[i] - mean2) ** 2 for i in range(n)) / n)
        if std1 < 1e-10 or std2 < 1e-10:
            return None
        return cov / (std1 * std2)

    pairs = []
    redundant = []
    orthogonal = []
    today = datetime.utcnow().strftime('%Y-%m-%d')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for i in range(len(algo_keys)):
        for j in range(i + 1, len(algo_keys)):
            key_a = algo_keys[i]
            key_b = algo_keys[j]
            corr = pearson_corr(algo_vectors[key_a], algo_vectors[key_b])
            if corr is None:
                continue

            sample_size = n_points
            pair = {
                'algo_a': key_a[0], 'asset_a': key_a[1],
                'algo_b': key_b[0], 'asset_b': key_b[1],
                'correlation': round(corr, 4),
                'sample_size': sample_size,
            }
            pairs.append(pair)

            if abs(corr) > CORRELATION_HIGH:
                redundant.append(pair)
            elif abs(corr) < CORRELATION_LOW:
                orthogonal.append(pair)

    print(f"\n  Pairs analyzed: {len(pairs)}")
    print(f"  Redundant (|corr| > {CORRELATION_HIGH}): {len(redundant)}")
    print(f"  Orthogonal (|corr| < {CORRELATION_LOW}): {len(orthogonal)}")

    if redundant:
        print("\n  REDUNDANT PAIRS (consider merging):")
        for p in sorted(redundant, key=lambda x: abs(x['correlation']), reverse=True):
            print(f"    {p['algo_a']} ({p['asset_a']}) <-> {p['algo_b']} ({p['asset_b']}): "
                  f"corr={p['correlation']:+.4f}")

    if orthogonal:
        print("\n  ORTHOGONAL PAIRS (good diversification):")
        for p in sorted(orthogonal, key=lambda x: abs(x['correlation']))[:10]:
            print(f"    {p['algo_a']} ({p['asset_a']}) <-> {p['algo_b']} ({p['asset_b']}): "
                  f"corr={p['correlation']:+.4f}")

    # Store in DB
    if not dry_run and pairs:
        cursor = conn.cursor()
        # Clear today's entries first
        cursor.execute("DELETE FROM lm_cross_correlation WHERE calc_date = %s", (today,))

        insert_sql = """INSERT INTO lm_cross_correlation
            (algo_a, asset_a, algo_b, asset_b, correlation, sample_size, calc_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

        insert_count = 0
        for p in pairs:
            try:
                cursor.execute(insert_sql, (
                    p['algo_a'], p['asset_a'],
                    p['algo_b'], p['asset_b'],
                    p['correlation'], p['sample_size'],
                    today, now
                ))
                insert_count += 1
            except Exception as e:
                logger.warning("Insert correlation failed: %s", e)

        conn.commit()
        cursor.close()
        print(f"\n  Stored {insert_count} correlation pairs in lm_cross_correlation")
    elif dry_run:
        print(f"\n  [DRY RUN] Would store {len(pairs)} correlation pairs")

    return {
        'pairs_analyzed': len(pairs),
        'redundant': redundant,
        'orthogonal': orthogonal,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 2: Ensemble Weight Optimization
# ═══════════════════════════════════════════════════════════════════════════

def run_ensemble_weights(conn, trades, dry_run=False):
    """
    Compute optimal ensemble weights for each asset class.

    Weight formula: inverse_volatility * rolling_sharpe * (1 - abs(corr_to_portfolio))
    Weights are normalized to sum to 1.0 per asset class.
    """
    print("\n" + "=" * 80)
    print("  MODULE 2: ENSEMBLE WEIGHT OPTIMIZATION")
    print("=" * 80)

    if not trades:
        print("  [SKIP] No closed trades found")
        return {'asset_classes': {}}

    # Group trades by asset class -> algorithm
    ac_algo_trades = defaultdict(lambda: defaultdict(list))
    all_trades_by_ac = defaultdict(list)

    for t in trades:
        ac = t['asset_class']
        algo = t['algorithm_name']
        ac_algo_trades[ac][algo].append(t)
        all_trades_by_ac[ac].append(t)

    today = datetime.utcnow().strftime('%Y-%m-%d')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    results = {}

    for ac in sorted(ac_algo_trades.keys()):
        print(f"\n  --- {ac} ---")
        algo_trades = ac_algo_trades[ac]

        # Portfolio returns for this asset class (all trades combined, chronological)
        portfolio_returns = [safe_float(t.get('realized_pct', 0)) / 100.0
                            for t in sorted(all_trades_by_ac[ac],
                                            key=lambda x: x.get('entry_time', ''))]

        algo_weights = {}
        for algo, atrades in sorted(algo_trades.items()):
            if len(atrades) < 3:
                continue

            # Per-trade returns
            returns = [safe_float(t.get('realized_pct', 0)) / 100.0 for t in atrades]

            # Rolling 30-day Sharpe (using last 30 trades as proxy)
            rolling_sharpe = calc_rolling_sharpe(returns, window=30)

            # Rolling win rate (last 30 trades)
            recent_trades = atrades[-30:] if len(atrades) >= 30 else atrades
            rolling_wr = calc_win_rate(recent_trades)

            # Correlation to portfolio returns
            # Align by index: use overlap
            min_len = min(len(returns), len(portfolio_returns))
            if min_len >= 5:
                algo_r = returns[-min_len:]
                port_r = portfolio_returns[-min_len:]
                # Pearson correlation
                mean_a = sum(algo_r) / min_len
                mean_p = sum(port_r) / min_len
                cov = sum((algo_r[i] - mean_a) * (port_r[i] - mean_p)
                          for i in range(min_len)) / min_len
                std_a = math.sqrt(sum((r - mean_a) ** 2 for r in algo_r) / min_len)
                std_p = math.sqrt(sum((r - mean_p) ** 2 for r in port_r) / min_len)
                if std_a > 1e-10 and std_p > 1e-10:
                    corr_to_port = cov / (std_a * std_p)
                else:
                    corr_to_port = 0.0
            else:
                corr_to_port = 0.0

            # Inverse volatility
            if len(returns) >= 2:
                mean_r = sum(returns) / len(returns)
                variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
                vol = math.sqrt(variance) if variance > 0 else 1.0
                inv_vol = 1.0 / max(vol, 0.001)
            else:
                inv_vol = 1.0

            # Information ratio (excess return / tracking error vs portfolio)
            if min_len >= 5:
                excess = [algo_r[i] - port_r[i] for i in range(min_len)]
                mean_excess = sum(excess) / min_len
                te_var = sum((e - mean_excess) ** 2 for e in excess) / min_len
                te = math.sqrt(te_var) if te_var > 0 else 1.0
                info_ratio = mean_excess / max(te, 0.001)
            else:
                info_ratio = 0.0

            # Weight formula: inverse_vol * rolling_sharpe * (1 - |corr_to_portfolio|)
            raw_weight = inv_vol * max(rolling_sharpe, 0.01) * (1 - abs(corr_to_port))
            raw_weight = max(raw_weight, 0.0)  # Ensure non-negative

            algo_weights[algo] = {
                'raw_weight': raw_weight,
                'rolling_sharpe': round(rolling_sharpe, 4),
                'rolling_wr': round(rolling_wr, 2),
                'corr_to_port': round(corr_to_port, 4),
                'info_ratio': round(info_ratio, 4),
                'trades': len(atrades),
            }

        # Normalize weights
        total_raw = sum(w['raw_weight'] for w in algo_weights.values())
        if total_raw > 0:
            for algo in algo_weights:
                algo_weights[algo]['weight'] = round(algo_weights[algo]['raw_weight'] / total_raw, 4)
        else:
            # Equal weight fallback
            n = len(algo_weights)
            for algo in algo_weights:
                algo_weights[algo]['weight'] = round(1.0 / n, 4) if n > 0 else 0

        # Print
        sorted_algos = sorted(algo_weights.items(), key=lambda x: x[1]['weight'], reverse=True)
        print(f"  {'Algorithm':30s} | {'Weight':>7s} | {'Sharpe':>7s} | "
              f"{'WR%':>6s} | {'Corr':>6s} | {'IR':>6s} | {'N':>4s}")
        print(f"  {'-'*30}-+-{'-'*7}-+-{'-'*7}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*4}")
        for algo, w in sorted_algos:
            print(f"  {algo:30s} | {w['weight']:>7.4f} | {w['rolling_sharpe']:>+7.3f} | "
                  f"{w['rolling_wr']:>5.1f}% | {w['corr_to_port']:>+6.3f} | "
                  f"{w['info_ratio']:>+6.3f} | {w['trades']:>4d}")

        results[ac] = algo_weights

    # Store in DB
    if not dry_run:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lm_ensemble_weights WHERE calc_date = %s", (today,))

        insert_sql = """INSERT INTO lm_ensemble_weights
            (asset_class, algorithm_name, ensemble_weight, rolling_sharpe_30d,
             rolling_win_rate_30d, correlation_to_portfolio, information_ratio,
             calc_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                ensemble_weight = VALUES(ensemble_weight),
                rolling_sharpe_30d = VALUES(rolling_sharpe_30d),
                rolling_win_rate_30d = VALUES(rolling_win_rate_30d),
                correlation_to_portfolio = VALUES(correlation_to_portfolio),
                information_ratio = VALUES(information_ratio),
                created_at = VALUES(created_at)"""

        insert_count = 0
        for ac, algo_weights in results.items():
            for algo, w in algo_weights.items():
                try:
                    cursor.execute(insert_sql, (
                        ac, algo, w['weight'], w['rolling_sharpe'],
                        w['rolling_wr'], w['corr_to_port'], w['info_ratio'],
                        today, now
                    ))
                    insert_count += 1
                except Exception as e:
                    logger.warning("Insert ensemble weight failed: %s", e)

        conn.commit()
        cursor.close()
        print(f"\n  Stored {insert_count} ensemble weights in lm_ensemble_weights")
    else:
        total = sum(len(v) for v in results.values())
        print(f"\n  [DRY RUN] Would store {total} ensemble weights")

    return {'asset_classes': results}


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 3: Prediction Calibration Check
# ═══════════════════════════════════════════════════════════════════════════

def run_calibration_check(conn, signals, trades, dry_run=False):
    """
    Check if signal_strength (confidence) is well-calibrated against actual outcomes.

    For each algorithm: bucket signals by strength -> compare to actual win rate.
    Brier score = mean((predicted_probability - actual_outcome)^2)
    """
    print("\n" + "=" * 80)
    print("  MODULE 3: PREDICTION CALIBRATION CHECK")
    print("=" * 80)

    if not signals or not trades:
        print("  [SKIP] Need both signals and trades for calibration")
        return {'algorithms': {}}

    # Build signal_id -> outcome map from trades
    signal_outcomes = {}
    for t in trades:
        sig_id = t.get('signal_id')
        if sig_id:
            won = 1 if safe_float(t.get('realized_pnl_usd', 0)) > 0 else 0
            signal_outcomes[int(sig_id)] = won

    # Group signals by (algorithm, asset_class) and bucket by strength
    algo_buckets = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins': 0}))

    matched = 0
    for sig in signals:
        sig_id = sig.get('id')
        if sig_id is None or int(sig_id) not in signal_outcomes:
            continue

        matched += 1
        algo = sig['algorithm_name']
        ac = sig['asset_class']
        strength = safe_float(sig.get('signal_strength', 50))
        outcome = signal_outcomes[int(sig_id)]

        # Find bucket
        for low, high, label in CALIBRATION_BUCKETS:
            if low <= strength < high:
                key = (algo, ac)
                algo_buckets[key][label]['total'] += 1
                algo_buckets[key][label]['wins'] += outcome
                break

    print(f"  Matched signals to trades: {matched}")

    if not algo_buckets:
        print("  [SKIP] No signal-trade matches found for calibration")
        return {'algorithms': {}}

    today = datetime.utcnow().strftime('%Y-%m-%d')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    results = {}
    poorly_calibrated = []

    print(f"\n  {'Algorithm':30s} | {'Asset':7s} | {'Bucket':>8s} | "
          f"{'N':>5s} | {'Predicted':>9s} | {'Actual':>7s} | {'Error':>7s}")
    print(f"  {'-'*30}-+-{'-'*7}-+-{'-'*8}-+-{'-'*5}-+-{'-'*9}-+-{'-'*7}-+-{'-'*7}")

    for (algo, ac), buckets in sorted(algo_buckets.items()):
        algo_result = {}
        total_brier = 0.0
        total_n = 0

        for label in ['0-20', '20-40', '40-60', '60-80', '80-100']:
            data = buckets.get(label)
            if not data or data['total'] == 0:
                continue

            n = data['total']
            actual_wr = data['wins'] / n

            # Expected probability = midpoint of bucket / 100
            low_val = int(label.split('-')[0])
            high_val = int(label.split('-')[1])
            expected_prob = (low_val + high_val) / 200.0

            # Calibration error
            cal_error = abs(expected_prob - actual_wr)

            # Brier score contribution
            brier_contrib = (expected_prob - actual_wr) ** 2
            total_brier += brier_contrib * n
            total_n += n

            bucket_result = {
                'total': n,
                'wins': data['wins'],
                'actual_accuracy': round(actual_wr * 100, 2),
                'calibration_error': round(cal_error, 4),
            }
            algo_result[label] = bucket_result

            print(f"  {algo:30s} | {ac:7s} | {label:>8s} | {n:>5d} | "
                  f"{expected_prob:>8.1%} | {actual_wr:>6.1%} | {cal_error:>6.3f}")

        # Overall Brier score for this algo
        if total_n > 0:
            brier = total_brier / total_n
            algo_result['brier_score'] = round(brier, 4)
            algo_result['total_predictions'] = total_n

            if brier > 0.1:
                poorly_calibrated.append({
                    'algorithm': algo, 'asset': ac,
                    'brier_score': round(brier, 4),
                    'predictions': total_n
                })

        results[(algo, ac)] = algo_result

    # Report poorly calibrated
    if poorly_calibrated:
        print(f"\n  POORLY CALIBRATED (Brier > 0.10):")
        for p in sorted(poorly_calibrated, key=lambda x: x['brier_score'], reverse=True):
            print(f"    {p['algorithm']} ({p['asset']}): Brier={p['brier_score']:.4f} "
                  f"(n={p['predictions']})")
    else:
        print(f"\n  All algorithms are reasonably calibrated (Brier <= 0.10)")

    # Store in DB
    if not dry_run:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lm_prediction_calibration WHERE calc_date = %s", (today,))

        insert_sql = """INSERT INTO lm_prediction_calibration
            (algorithm_name, asset_class, confidence_bucket, total_predictions,
             correct_predictions, actual_accuracy, calibration_error,
             calc_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        insert_count = 0
        for (algo, ac), algo_result in results.items():
            for bucket_label in ['0-20', '20-40', '40-60', '60-80', '80-100']:
                data = algo_result.get(bucket_label)
                if not data:
                    continue
                try:
                    cursor.execute(insert_sql, (
                        algo, ac, bucket_label,
                        data['total'], data['wins'],
                        data['actual_accuracy'], data['calibration_error'],
                        today, now
                    ))
                    insert_count += 1
                except Exception as e:
                    logger.warning("Insert calibration failed: %s", e)

        conn.commit()
        cursor.close()
        print(f"\n  Stored {insert_count} calibration entries in lm_prediction_calibration")
    else:
        total = sum(len([k for k in v if k not in ('brier_score', 'total_predictions')])
                    for v in results.values())
        print(f"\n  [DRY RUN] Would store {total} calibration entries")

    return {
        'algorithms': {f"{k[0]}|{k[1]}": v for k, v in results.items()},
        'poorly_calibrated': poorly_calibrated,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 4: Feature Importance Analysis
# ═══════════════════════════════════════════════════════════════════════════

def run_feature_importance(conn, signals, trades, regime_data, dry_run=False):
    """
    Analyze which market features predict wins vs losses for each algorithm.

    Features analyzed:
      - Regime (bull/bear/sideways)
      - Day of week (signal_time)
      - Hour of day (signal_time)
      - Signal strength bucket
      - Recent momentum (inferred from signal_type)
      - Volatility proxy (ATR percentile via spread between TP and SL)
    """
    print("\n" + "=" * 80)
    print("  MODULE 4: FEATURE IMPORTANCE ANALYSIS")
    print("=" * 80)

    if not signals or not trades:
        print("  [SKIP] Need both signals and trades")
        return {'algorithms': {}}

    # Build signal_id -> outcome + trade info
    trade_by_signal = {}
    for t in trades:
        sig_id = t.get('signal_id')
        if sig_id:
            trade_by_signal[int(sig_id)] = t

    # Build date -> regime map
    regime_map = {}
    for r in regime_data:
        d = r.get('date')
        if d:
            if hasattr(d, 'strftime'):
                date_str = d.strftime('%Y-%m-%d')
            else:
                date_str = str(d)[:10]
            regime_map[date_str] = r.get('hmm_regime', 'unknown')

    # Build feature vectors per algorithm
    algo_features = defaultdict(list)

    for sig in signals:
        sig_id = sig.get('id')
        if sig_id is None or int(sig_id) not in trade_by_signal:
            continue

        trade = trade_by_signal[int(sig_id)]
        algo = sig['algorithm_name']
        ac = sig['asset_class']
        won = 1 if safe_float(trade.get('realized_pnl_usd', 0)) > 0 else 0

        sig_time = sig.get('signal_time')
        if not sig_time:
            continue

        # Extract features
        if hasattr(sig_time, 'hour'):
            hour = sig_time.hour
            dow = sig_time.weekday()
            date_str = sig_time.strftime('%Y-%m-%d')
        else:
            # Parse string
            try:
                dt = datetime.strptime(str(sig_time)[:19], '%Y-%m-%d %H:%M:%S')
                hour = dt.hour
                dow = dt.weekday()
                date_str = dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue

        # Regime
        regime = regime_map.get(date_str, 'unknown')

        # Signal strength bucket
        strength = safe_float(sig.get('signal_strength', 50))
        if strength < 30:
            strength_bucket = 'low'
        elif strength < 70:
            strength_bucket = 'medium'
        else:
            strength_bucket = 'high'

        # Volatility proxy: TP/SL ratio as indicator
        tp = safe_float(sig.get('target_tp_pct', 3))
        sl = safe_float(sig.get('target_sl_pct', 2))
        vol_proxy = tp + sl  # Higher = more volatile expected move

        # Signal type
        sig_type = sig.get('signal_type', 'BUY').upper()

        features = {
            'won': won,
            'regime': regime,
            'hour': hour,
            'dow': dow,
            'strength_bucket': strength_bucket,
            'signal_type': sig_type,
            'vol_proxy': vol_proxy,
        }
        algo_features[(algo, ac)].append(features)

    if not algo_features:
        print("  [SKIP] No signal-trade matches with features")
        return {'algorithms': {}}

    today = datetime.utcnow().strftime('%Y-%m-%d')
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    results = {}

    for (algo, ac), feature_list in sorted(algo_features.items()):
        n = len(feature_list)
        if n < 5:
            continue

        print(f"\n  {algo} ({ac}) — {n} trades")
        importance = {}

        # 1. Regime importance: win rate per regime
        regime_groups = defaultdict(lambda: {'wins': 0, 'total': 0})
        for f in feature_list:
            r = f['regime']
            regime_groups[r]['total'] += 1
            regime_groups[r]['wins'] += f['won']

        overall_wr = sum(f['won'] for f in feature_list) / n
        regime_spread = 0.0
        for r, data in regime_groups.items():
            if data['total'] >= 2:
                rwr = data['wins'] / data['total']
                regime_spread = max(regime_spread, abs(rwr - overall_wr))
        importance['regime'] = round(regime_spread, 4)

        # 2. Day of week importance
        dow_groups = defaultdict(lambda: {'wins': 0, 'total': 0})
        for f in feature_list:
            dow_groups[f['dow']]['total'] += 1
            dow_groups[f['dow']]['wins'] += f['won']

        dow_spread = 0.0
        for d, data in dow_groups.items():
            if data['total'] >= 2:
                dwr = data['wins'] / data['total']
                dow_spread = max(dow_spread, abs(dwr - overall_wr))
        importance['day_of_week'] = round(dow_spread, 4)

        # 3. Hour of day importance (bucket: morning/afternoon/evening/night)
        hour_buckets = defaultdict(lambda: {'wins': 0, 'total': 0})
        for f in feature_list:
            h = f['hour']
            if h < 6:
                bucket = 'night'
            elif h < 12:
                bucket = 'morning'
            elif h < 18:
                bucket = 'afternoon'
            else:
                bucket = 'evening'
            hour_buckets[bucket]['total'] += 1
            hour_buckets[bucket]['wins'] += f['won']

        hour_spread = 0.0
        for b, data in hour_buckets.items():
            if data['total'] >= 2:
                hwr = data['wins'] / data['total']
                hour_spread = max(hour_spread, abs(hwr - overall_wr))
        importance['time_of_day'] = round(hour_spread, 4)

        # 4. Signal strength importance
        str_groups = defaultdict(lambda: {'wins': 0, 'total': 0})
        for f in feature_list:
            str_groups[f['strength_bucket']]['total'] += 1
            str_groups[f['strength_bucket']]['wins'] += f['won']

        str_spread = 0.0
        for s, data in str_groups.items():
            if data['total'] >= 2:
                swr = data['wins'] / data['total']
                str_spread = max(str_spread, abs(swr - overall_wr))
        importance['signal_strength'] = round(str_spread, 4)

        # 5. Signal type importance (BUY vs SHORT/SELL)
        type_groups = defaultdict(lambda: {'wins': 0, 'total': 0})
        for f in feature_list:
            type_groups[f['signal_type']]['total'] += 1
            type_groups[f['signal_type']]['wins'] += f['won']

        type_spread = 0.0
        for t, data in type_groups.items():
            if data['total'] >= 2:
                twr = data['wins'] / data['total']
                type_spread = max(type_spread, abs(twr - overall_wr))
        importance['signal_direction'] = round(type_spread, 4)

        # 6. Volatility proxy importance (high vs low vol)
        vol_values = [f['vol_proxy'] for f in feature_list]
        median_vol = sorted(vol_values)[len(vol_values) // 2]
        vol_groups = {'low': {'wins': 0, 'total': 0}, 'high': {'wins': 0, 'total': 0}}
        for f in feature_list:
            bucket = 'high' if f['vol_proxy'] > median_vol else 'low'
            vol_groups[bucket]['total'] += 1
            vol_groups[bucket]['wins'] += f['won']

        vol_spread = 0.0
        for v, data in vol_groups.items():
            if data['total'] >= 2:
                vwr = data['wins'] / data['total']
                vol_spread = max(vol_spread, abs(vwr - overall_wr))
        importance['volatility_proxy'] = round(vol_spread, 4)

        # Rank features by importance
        ranked = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        for rank, (feat, score) in enumerate(ranked, 1):
            print(f"    {rank}. {feat:25s}: {score:.4f}")

        results[(algo, ac)] = {
            'n_trades': n,
            'overall_wr': round(overall_wr * 100, 2),
            'features': ranked,
        }

    # Store in DB
    if not dry_run and results:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lm_feature_importance WHERE calc_date = %s", (today,))

        insert_sql = """INSERT INTO lm_feature_importance
            (algorithm_name, asset_class, feature_name, importance_score,
             importance_rank, calc_date, sample_size, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

        insert_count = 0
        for (algo, ac), data in results.items():
            for rank, (feat, score) in enumerate(data['features'], 1):
                try:
                    cursor.execute(insert_sql, (
                        algo, ac, feat, score, rank,
                        today, data['n_trades'], now
                    ))
                    insert_count += 1
                except Exception as e:
                    logger.warning("Insert feature importance failed: %s", e)

        conn.commit()
        cursor.close()
        print(f"\n  Stored {insert_count} feature importance entries in lm_feature_importance")
    elif dry_run:
        total = sum(len(v['features']) for v in results.values())
        print(f"\n  [DRY RUN] Would store {total} feature importance entries")

    return {'algorithms': {f"{k[0]}|{k[1]}": v for k, v in results.items()}}


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 5: ML Readiness Assessment
# ═══════════════════════════════════════════════════════════════════════════

def run_ml_readiness(conn, trades, dry_run=False):
    """
    Update lm_ml_status for ALL asset classes with:
    - closed_trades count
    - current params (TP/SL/Hold)
    - ml_ready flag (requires 20+ trades)
    - status: collecting_data / ml_ready / optimized / degraded
    - status_reason with actionable detail
    """
    print("\n" + "=" * 80)
    print("  MODULE 5: ML READINESS ASSESSMENT")
    print("=" * 80)

    if not trades:
        print("  [SKIP] No closed trades found")
        return {'algorithms': {}}

    # Group by (algorithm, asset_class)
    algo_ac_trades = defaultdict(list)
    for t in trades:
        key = (t['algorithm_name'], t['asset_class'])
        algo_ac_trades[key].append(t)

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    results = {}

    print(f"\n  {'Algorithm':30s} | {'Asset':7s} | {'Trades':>6s} | {'WR%':>6s} | "
          f"{'PnL':>8s} | {'Status':>16s}")
    print(f"  {'-'*30}-+-{'-'*7}-+-{'-'*6}-+-{'-'*6}-+-{'-'*8}-+-{'-'*16}")

    for (algo, ac), atrades in sorted(algo_ac_trades.items()):
        n = len(atrades)
        wins = sum(1 for t in atrades if safe_float(t.get('realized_pnl_usd', 0)) > 0)
        wr = round(wins / n * 100, 2) if n > 0 else 0
        total_pnl = round(sum(safe_float(t.get('realized_pnl_usd', 0)) for t in atrades), 2)

        # Current params: average from trades
        avg_tp = round(sum(safe_float(t.get('target_tp_pct', 0)) for t in atrades) / n, 2)
        avg_sl = round(sum(safe_float(t.get('target_sl_pct', 0)) for t in atrades) / n, 2)
        avg_hold = int(sum(safe_float(t.get('max_hold_hours', 0)) for t in atrades) / n)

        # Sharpe ratio
        returns = [safe_float(t.get('realized_pct', 0)) / 100.0 for t in atrades]
        sharpe = round(calc_sharpe(returns), 4) if len(returns) >= 2 else 0.0

        # Profit factor
        gross_wins = sum(safe_float(t.get('realized_pnl_usd', 0))
                         for t in atrades if safe_float(t.get('realized_pnl_usd', 0)) > 0)
        gross_losses = abs(sum(safe_float(t.get('realized_pnl_usd', 0))
                               for t in atrades if safe_float(t.get('realized_pnl_usd', 0)) < 0))
        pf = round(gross_wins / gross_losses, 3) if gross_losses > 0 else 0.0

        # ML readiness
        ml_ready = 1 if n >= MIN_TRADES_ML_READY else 0

        # Status determination
        if n < MIN_TRADES_ML_READY:
            status = 'collecting_data'
            remaining = MIN_TRADES_ML_READY - n
            reason = f"Need {remaining} more closed trades for grid search optimization. " \
                     f"Current: {n}/{MIN_TRADES_ML_READY}."
        elif wr >= 55 and total_pnl > 0:
            status = 'optimized'
            reason = f"Profitable with {wr:.1f}% WR and ${total_pnl:.2f} PnL. " \
                     f"Sharpe: {sharpe:.3f}. Consider walk-forward validation."
        elif wr >= 45:
            status = 'ml_ready'
            reason = f"Sufficient data ({n} trades). WR={wr:.1f}%, Sharpe={sharpe:.3f}. " \
                     f"Ready for parameter optimization."
        else:
            status = 'degraded'
            reason = f"Underperforming: WR={wr:.1f}%, PnL=${total_pnl:.2f}. " \
                     f"Consider re-tuning TP/SL or pausing this algorithm for {ac}."

        print(f"  {algo:30s} | {ac:7s} | {n:>6d} | {wr:>5.1f}% | "
              f"${total_pnl:>+7.2f} | {status:>16s}")

        results[(algo, ac)] = {
            'closed_trades': n,
            'ml_ready': ml_ready,
            'win_rate': wr,
            'total_pnl': total_pnl,
            'sharpe': sharpe,
            'profit_factor': pf,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl,
            'avg_hold': avg_hold,
            'status': status,
            'reason': reason,
        }

    # Store in DB
    if not dry_run and results:
        cursor = conn.cursor()

        upsert_sql = """INSERT INTO lm_ml_status
            (algorithm_name, asset_class, closed_trades, ml_ready,
             current_tp, current_sl, current_hold, param_source,
             current_win_rate, current_sharpe, current_pf, total_pnl,
             status, status_reason, updated_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                closed_trades = VALUES(closed_trades),
                ml_ready = VALUES(ml_ready),
                current_tp = VALUES(current_tp),
                current_sl = VALUES(current_sl),
                current_hold = VALUES(current_hold),
                current_win_rate = VALUES(current_win_rate),
                current_sharpe = VALUES(current_sharpe),
                current_pf = VALUES(current_pf),
                total_pnl = VALUES(total_pnl),
                status = VALUES(status),
                status_reason = VALUES(status_reason),
                updated_at = VALUES(updated_at)"""

        upsert_count = 0
        for (algo, ac), data in results.items():
            try:
                cursor.execute(upsert_sql, (
                    algo, ac, data['closed_trades'], data['ml_ready'],
                    data['avg_tp'], data['avg_sl'], data['avg_hold'], 'live',
                    data['win_rate'], data['sharpe'], data['profit_factor'],
                    data['total_pnl'],
                    data['status'], data['reason'],
                    now, now
                ))
                upsert_count += 1
            except Exception as e:
                logger.warning("Upsert ml_status failed for %s/%s: %s", algo, ac, e)

        conn.commit()
        cursor.close()
        print(f"\n  Upserted {upsert_count} entries in lm_ml_status")
    elif dry_run:
        print(f"\n  [DRY RUN] Would upsert {len(results)} lm_ml_status entries")

    # Summary
    statuses = defaultdict(int)
    for data in results.values():
        statuses[data['status']] += 1
    print(f"\n  Summary: {dict(statuses)}")

    return {'algorithms': {f"{k[0]}|{k[1]}": v for k, v in results.items()}}


# ═══════════════════════════════════════════════════════════════════════════
# MODULE 6: Alpha Decay Detection
# ═══════════════════════════════════════════════════════════════════════════

def run_alpha_decay(conn, trades, dry_run=False):
    """
    For algorithms with 30+ trades, check if recent performance
    (last 10 trades) is significantly worse than historical (first 20).

    Flag algorithms where recent WR < historical WR by >15%.
    """
    print("\n" + "=" * 80)
    print("  MODULE 6: ALPHA DECAY DETECTION")
    print("=" * 80)

    if not trades:
        print("  [SKIP] No closed trades found")
        return {'decaying': [], 'healthy': [], 'insufficient': []}

    # Group by (algorithm, asset_class), preserve time order
    algo_ac_trades = defaultdict(list)
    for t in trades:
        key = (t['algorithm_name'], t['asset_class'])
        algo_ac_trades[key].append(t)

    decaying = []
    healthy = []
    insufficient = []

    print(f"\n  {'Algorithm':30s} | {'Asset':7s} | {'N':>4s} | "
          f"{'Hist WR%':>8s} | {'Recent WR%':>10s} | {'Delta':>7s} | {'Status':>10s}")
    print(f"  {'-'*30}-+-{'-'*7}-+-{'-'*4}-+-{'-'*8}-+-{'-'*10}-+-{'-'*7}-+-{'-'*10}")

    for (algo, ac), atrades in sorted(algo_ac_trades.items()):
        n = len(atrades)

        if n < ALPHA_DECAY_TRADES:
            insufficient.append({
                'algorithm': algo, 'asset': ac, 'trades': n,
                'needed': ALPHA_DECAY_TRADES
            })
            print(f"  {algo:30s} | {ac:7s} | {n:>4d} | {'N/A':>8s} | "
                  f"{'N/A':>10s} | {'N/A':>7s} | {'too_few':>10s}")
            continue

        # Sort by entry_time to ensure chronological order
        sorted_trades = sorted(atrades, key=lambda x: x.get('entry_time', ''))

        # Historical = first (n-10) trades, Recent = last 10 trades
        split_point = max(n - 10, 20)  # Ensure at least 20 in historical
        historical = sorted_trades[:split_point]
        recent = sorted_trades[split_point:]

        if len(recent) < 5:
            # Not enough recent trades
            recent = sorted_trades[-10:]
            historical = sorted_trades[:-10]

        hist_wins = sum(1 for t in historical if safe_float(t.get('realized_pnl_usd', 0)) > 0)
        hist_wr = hist_wins / len(historical) * 100 if historical else 0

        recent_wins = sum(1 for t in recent if safe_float(t.get('realized_pnl_usd', 0)) > 0)
        recent_wr = recent_wins / len(recent) * 100 if recent else 0

        delta = recent_wr - hist_wr

        entry = {
            'algorithm': algo,
            'asset': ac,
            'total_trades': n,
            'historical_wr': round(hist_wr, 1),
            'historical_n': len(historical),
            'recent_wr': round(recent_wr, 1),
            'recent_n': len(recent),
            'delta': round(delta, 1),
        }

        if delta < -ALPHA_DECAY_THRESHOLD:
            status = 'DECAYING'
            entry['recommendation'] = f"Recent WR ({recent_wr:.1f}%) is {abs(delta):.1f}pp " \
                                       f"below historical ({hist_wr:.1f}%). " \
                                       f"Consider retraining or pausing."
            decaying.append(entry)
        else:
            status = 'HEALTHY'
            entry['recommendation'] = 'Performance is stable.'
            healthy.append(entry)

        print(f"  {algo:30s} | {ac:7s} | {n:>4d} | {hist_wr:>7.1f}% | "
              f"{recent_wr:>9.1f}% | {delta:>+6.1f}% | {status:>10s}")

    # Summary
    print(f"\n  Healthy: {len(healthy)}")
    print(f"  Decaying (WR drop > {ALPHA_DECAY_THRESHOLD}%): {len(decaying)}")
    print(f"  Insufficient data (< {ALPHA_DECAY_TRADES} trades): {len(insufficient)}")

    if decaying:
        print(f"\n  ALPHA DECAY ALERTS:")
        for d in sorted(decaying, key=lambda x: x['delta']):
            print(f"    {d['algorithm']} ({d['asset']}): "
                  f"{d['historical_wr']:.1f}% -> {d['recent_wr']:.1f}% "
                  f"(delta {d['delta']:+.1f}%)")
            print(f"      Recommendation: {d['recommendation']}")

    # Update lm_ml_status with decay flags (mark degraded algos)
    if not dry_run and decaying:
        cursor = conn.cursor()
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        for d in decaying:
            reason = f"ALPHA DECAY: Recent WR {d['recent_wr']:.1f}% vs historical " \
                     f"{d['historical_wr']:.1f}% (delta {d['delta']:+.1f}%). " \
                     f"Last {d['recent_n']} trades underperforming."
            try:
                cursor.execute("""
                    UPDATE lm_ml_status
                    SET status = 'degraded',
                        status_reason = %s,
                        updated_at = %s
                    WHERE algorithm_name = %s AND asset_class = %s
                      AND status != 'collecting_data'
                """, (reason, now, d['algorithm'], d['asset']))
            except Exception as e:
                logger.warning("Update decay status failed: %s", e)

        conn.commit()
        cursor.close()
        print(f"\n  Updated {len(decaying)} algorithms as 'degraded' in lm_ml_status")
    elif dry_run and decaying:
        print(f"\n  [DRY RUN] Would mark {len(decaying)} algorithms as 'degraded'")

    return {
        'decaying': decaying,
        'healthy': healthy,
        'insufficient': insufficient,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Cross-Asset ML Intelligence System')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print analysis without writing to DB')
    parser.add_argument('--module', type=str, default='all',
                        choices=['all', 'correlation', 'ensemble', 'calibration',
                                 'features', 'readiness', 'decay'],
                        help='Run specific module only (default: all)')
    args = parser.parse_args()

    print("=" * 80)
    print("  CROSS-ASSET ML INTELLIGENCE SYSTEM")
    print(f"  Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Module: {args.module.upper()}")
    print("=" * 80)

    # Connect and ensure schema
    try:
        conn = connect_db()
        logger.info("Connected to database: %s@%s/%s", DB_USER, DB_HOST, DB_NAME)
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        print(f"\n  FATAL: Cannot connect to database: {e}")
        sys.exit(1)

    try:
        ensure_schema(conn)
    except Exception as e:
        logger.warning("Schema ensure warning: %s", e)

    # Fetch data once, share across modules
    print("\n  Fetching data...")
    signals = fetch_signals(conn)
    trades = fetch_closed_trades(conn)
    regime_data = fetch_regime(conn)

    print(f"  Signals: {len(signals)}")
    print(f"  Closed trades: {len(trades)}")
    print(f"  Regime records: {len(regime_data)}")

    # Track results
    all_results = {}
    run = args.module

    # Module 1: Correlation
    if run in ('all', 'correlation'):
        try:
            all_results['correlation'] = run_correlation_analysis(
                conn, signals, dry_run=args.dry_run)
        except Exception as e:
            logger.error("Correlation analysis failed: %s", e)
            all_results['correlation'] = {'error': str(e)}

    # Module 2: Ensemble weights
    if run in ('all', 'ensemble'):
        try:
            all_results['ensemble'] = run_ensemble_weights(
                conn, trades, dry_run=args.dry_run)
        except Exception as e:
            logger.error("Ensemble weight optimization failed: %s", e)
            all_results['ensemble'] = {'error': str(e)}

    # Module 3: Calibration
    if run in ('all', 'calibration'):
        try:
            all_results['calibration'] = run_calibration_check(
                conn, signals, trades, dry_run=args.dry_run)
        except Exception as e:
            logger.error("Calibration check failed: %s", e)
            all_results['calibration'] = {'error': str(e)}

    # Module 4: Feature importance
    if run in ('all', 'features'):
        try:
            all_results['features'] = run_feature_importance(
                conn, signals, trades, regime_data, dry_run=args.dry_run)
        except Exception as e:
            logger.error("Feature importance analysis failed: %s", e)
            all_results['features'] = {'error': str(e)}

    # Module 5: ML readiness
    if run in ('all', 'readiness'):
        try:
            all_results['readiness'] = run_ml_readiness(
                conn, trades, dry_run=args.dry_run)
        except Exception as e:
            logger.error("ML readiness assessment failed: %s", e)
            all_results['readiness'] = {'error': str(e)}

    # Module 6: Alpha decay (run AFTER readiness so it can override status)
    if run in ('all', 'decay'):
        try:
            all_results['decay'] = run_alpha_decay(
                conn, trades, dry_run=args.dry_run)
        except Exception as e:
            logger.error("Alpha decay detection failed: %s", e)
            all_results['decay'] = {'error': str(e)}

    # Close DB
    conn.close()

    # ── Final Summary ──
    print("\n" + "=" * 80)
    print("  CROSS-ASSET ML INTELLIGENCE — FINAL SUMMARY")
    print("=" * 80)

    # Correlation summary
    corr = all_results.get('correlation', {})
    if 'error' not in corr:
        print(f"\n  1. Signal Correlation:")
        print(f"     Pairs analyzed: {corr.get('pairs_analyzed', 0)}")
        print(f"     Redundant (corr > {CORRELATION_HIGH}): "
              f"{len(corr.get('redundant', []))}")
        print(f"     Orthogonal (corr < {CORRELATION_LOW}): "
              f"{len(corr.get('orthogonal', []))}")
        if corr.get('redundant'):
            print(f"     ACTION: Consider merging these {len(corr['redundant'])} "
                  f"redundant algorithm pairs")

    # Ensemble summary
    ens = all_results.get('ensemble', {})
    if 'error' not in ens:
        n_ac = len(ens.get('asset_classes', {}))
        n_algos = sum(len(v) for v in ens.get('asset_classes', {}).values())
        print(f"\n  2. Ensemble Weights:")
        print(f"     Asset classes: {n_ac}")
        print(f"     Algorithms weighted: {n_algos}")

    # Calibration summary
    cal = all_results.get('calibration', {})
    if 'error' not in cal:
        poorly = cal.get('poorly_calibrated', [])
        print(f"\n  3. Prediction Calibration:")
        print(f"     Algorithms checked: {len(cal.get('algorithms', {}))}")
        print(f"     Poorly calibrated (Brier > 0.10): {len(poorly)}")
        if poorly:
            print(f"     ACTION: Recalibrate confidence scores for "
                  f"{', '.join(p['algorithm'] for p in poorly)}")

    # Feature importance summary
    feat = all_results.get('features', {})
    if 'error' not in feat:
        print(f"\n  4. Feature Importance:")
        print(f"     Algorithms analyzed: {len(feat.get('algorithms', {}))}")

    # ML readiness summary
    ready = all_results.get('readiness', {})
    if 'error' not in ready:
        algos = ready.get('algorithms', {})
        statuses = defaultdict(int)
        for v in algos.values():
            statuses[v['status']] += 1
        print(f"\n  5. ML Readiness:")
        print(f"     Total algorithm-asset pairs: {len(algos)}")
        for s, c in sorted(statuses.items()):
            print(f"     {s}: {c}")

    # Alpha decay summary
    decay = all_results.get('decay', {})
    if 'error' not in decay:
        print(f"\n  6. Alpha Decay:")
        print(f"     Healthy: {len(decay.get('healthy', []))}")
        print(f"     Decaying: {len(decay.get('decaying', []))}")
        print(f"     Insufficient data: {len(decay.get('insufficient', []))}")
        if decay.get('decaying'):
            print(f"     ACTION: Retrain or pause these decaying algorithms: "
                  f"{', '.join(d['algorithm'] for d in decay['decaying'])}")

    # Save report to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, 'cross_asset_ml_report.json')
    try:
        # Serialize results (handle non-serializable types)
        serializable = json.loads(json.dumps(all_results, default=str))
        serializable['generated'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        serializable['dry_run'] = args.dry_run
        serializable['module'] = args.module
        with open(report_path, 'w') as f:
            json.dump(serializable, f, indent=2)
        print(f"\n  Report saved: {report_path}")
    except Exception as e:
        logger.warning("Failed to save report: %s", e)

    print("\n" + "=" * 80)
    print("  COMPLETE")
    print("=" * 80)

    return all_results


if __name__ == '__main__':
    main()
