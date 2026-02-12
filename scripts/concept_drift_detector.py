#!/usr/bin/env python3
"""
Concept Drift Detector -- Detects when algorithm signal quality or market
feature distributions shift, triggering retraining alerts.

Monitors 3 types of drift that degrade ML model performance:

  1. Population Stability Index (PSI) for Feature Drift
     - Compares feature distributions between a reference window (last 90 days)
       and a recent window (last 14 days)
     - PSI < 0.1: No drift. PSI 0.1-0.25: Moderate drift. PSI > 0.25: Retrain!
     - Features: signal_strength, regime, price momentum, time_of_day, volatility

  2. Win Rate Degradation (Performance Drift)
     - Compares historical win rate (all trades except last 20) vs recent (last 20)
     - Flags if recent WR drops by >15 percentage points
     - Also checks Sharpe ratio degradation

  3. Signal Volume Drift
     - Compares signal generation frequency between reference and recent periods
     - Flags if volume changes by >50%

Science: Kullback (1959) PSI foundations, Adams & MacKay (2007) Bayesian changepoint

Requires: pip install mysql-connector-python numpy
Usage:
  python scripts/concept_drift_detector.py
  python scripts/concept_drift_detector.py --dry-run
  python scripts/concept_drift_detector.py --ref-days 60 --recent-days 7
"""
import os
import sys
import math
import argparse
import warnings
from datetime import datetime, timedelta
from collections import defaultdict

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

# PSI thresholds (industry standard from Siddiqi 2006, "Credit Risk Scorecards")
PSI_NO_DRIFT = 0.10
PSI_MODERATE = 0.25  # Above this = significant drift

# Win rate degradation threshold (percentage points)
WR_DEGRADATION_THRESHOLD = 15.0

# Sharpe degradation threshold (absolute decline)
SHARPE_DEGRADATION_THRESHOLD = 0.5

# Signal volume change threshold (50% increase or decrease)
VOLUME_CHANGE_THRESHOLD = 0.50

# Minimum sample sizes
MIN_TRADES_FOR_PERF_DRIFT = 25   # Need at least 25 trades total (5 hist + 20 recent)
MIN_RECENT_TRADES = 20            # Recent window size for performance drift
MIN_SIGNALS_FOR_PSI = 30          # Need at least 30 signals per window for PSI
PSI_NUM_BUCKETS = 10              # Number of bins for PSI calculation

# Default window sizes (days)
DEFAULT_REF_DAYS = 90
DEFAULT_RECENT_DAYS = 14


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
def connect_db():
    """Connect to MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=15,
    )


# ---------------------------------------------------------------------------
# 1. PSI (Population Stability Index) for Feature Drift
# ---------------------------------------------------------------------------
def compute_psi(reference, recent, buckets=PSI_NUM_BUCKETS):
    """
    Compute Population Stability Index between two distributions.

    PSI = sum_i( (recent_i - ref_i) * ln(recent_i / ref_i) )

    Where ref_i and recent_i are the proportions of observations in bucket i.
    Uses equal-width bins based on the reference distribution range.

    Args:
        reference: list of float values from reference period
        recent: list of float values from recent period
        buckets: number of equal-width bins

    Returns:
        float: PSI value. <0.1 = stable, 0.1-0.25 = moderate, >0.25 = significant
    """
    if not reference or not recent:
        return None
    if len(reference) < 5 or len(recent) < 5:
        return None

    # Determine bin edges from reference distribution
    min_val = min(reference)
    max_val = max(reference)

    # Handle edge case: all values identical
    if max_val == min_val:
        # Check if recent also has all same values
        if min(recent) == max(recent) == min_val:
            return 0.0
        else:
            return 1.0  # Complete distribution shift

    bin_width = (max_val - min_val) / buckets
    edges = [min_val + i * bin_width for i in range(buckets + 1)]
    edges[-1] = max_val + 1e-10  # Ensure max value falls in last bin

    def bin_proportions(values, edges):
        """Compute proportion of values in each bin."""
        n = len(values)
        counts = [0] * (len(edges) - 1)
        for v in values:
            for i in range(len(edges) - 1):
                if edges[i] <= v < edges[i + 1]:
                    counts[i] += 1
                    break
            else:
                # Values outside reference range go to last bin
                counts[-1] += 1

        # Convert to proportions with small epsilon to avoid log(0)
        epsilon = 1e-6
        props = [(c / n) + epsilon for c in counts]
        # Re-normalize
        total = sum(props)
        return [p / total for p in props]

    ref_props = bin_proportions(reference, edges)
    rec_props = bin_proportions(recent, edges)

    # PSI = sum( (recent_i - ref_i) * ln(recent_i / ref_i) )
    psi = 0.0
    for r_ref, r_rec in zip(ref_props, rec_props):
        psi += (r_rec - r_ref) * math.log(r_rec / r_ref)

    return round(max(0.0, psi), 6)


def classify_psi(psi_value):
    """Classify PSI drift severity."""
    if psi_value is None:
        return 'INSUFFICIENT_DATA'
    if psi_value < PSI_NO_DRIFT:
        return 'OK'
    elif psi_value < PSI_MODERATE:
        return 'MONITOR'
    else:
        return 'RETRAIN_NEEDED'


def detect_feature_drift(conn, ref_days, recent_days):
    """
    Detect feature distribution drift per algorithm using PSI.

    Features monitored:
      - signal_strength (from lm_signals)
      - regime composite_score (from lm_market_regime)
      - hour_of_day derived from signal_time (time-of-day seasonality)
      - volatility (vol_annualized from lm_market_regime)
    """
    print("\n" + "=" * 70)
    print("  1. FEATURE DRIFT DETECTION (PSI)")
    print("=" * 70)

    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    ref_start = now - timedelta(days=ref_days)
    ref_end = now - timedelta(days=recent_days)
    recent_start = ref_end

    results = {}

    # --- Signal Strength PSI per algorithm ---
    try:
        # Reference window
        cursor.execute("""
            SELECT algorithm_name, asset_class, signal_strength,
                   HOUR(signal_time) as hour_of_day
            FROM lm_signals
            WHERE signal_time >= %s AND signal_time < %s
              AND algorithm_name != ''
            ORDER BY algorithm_name, signal_time
        """, (ref_start.strftime('%Y-%m-%d %H:%M:%S'),
              ref_end.strftime('%Y-%m-%d %H:%M:%S')))
        ref_signals = cursor.fetchall()

        # Recent window
        cursor.execute("""
            SELECT algorithm_name, asset_class, signal_strength,
                   HOUR(signal_time) as hour_of_day
            FROM lm_signals
            WHERE signal_time >= %s
              AND algorithm_name != ''
            ORDER BY algorithm_name, signal_time
        """, (recent_start.strftime('%Y-%m-%d %H:%M:%S'),))
        recent_signals = cursor.fetchall()
    except Exception as e:
        print(f"  ERROR fetching signals: {e}")
        cursor.close()
        return results

    # Group by algorithm
    ref_by_algo = defaultdict(lambda: {'strength': [], 'hour': []})
    for row in ref_signals:
        algo = row['algorithm_name']
        ref_by_algo[algo]['strength'].append(float(row['signal_strength']))
        ref_by_algo[algo]['hour'].append(float(row['hour_of_day']))

    rec_by_algo = defaultdict(lambda: {'strength': [], 'hour': []})
    for row in recent_signals:
        algo = row['algorithm_name']
        rec_by_algo[algo]['strength'].append(float(row['signal_strength']))
        rec_by_algo[algo]['hour'].append(float(row['hour_of_day']))

    # --- Regime / Volatility PSI (global, not per-algo) ---
    regime_ref = []
    regime_rec = []
    vol_ref = []
    vol_rec = []
    try:
        cursor.execute("""
            SELECT composite_score, vol_annualized
            FROM lm_market_regime
            WHERE created_at >= %s AND created_at < %s
              AND composite_score IS NOT NULL
        """, (ref_start.strftime('%Y-%m-%d %H:%M:%S'),
              ref_end.strftime('%Y-%m-%d %H:%M:%S')))
        for row in cursor.fetchall():
            if row['composite_score'] is not None:
                regime_ref.append(float(row['composite_score']))
            if row['vol_annualized'] is not None:
                vol_ref.append(float(row['vol_annualized']))

        cursor.execute("""
            SELECT composite_score, vol_annualized
            FROM lm_market_regime
            WHERE created_at >= %s
              AND composite_score IS NOT NULL
        """, (recent_start.strftime('%Y-%m-%d %H:%M:%S'),))
        for row in cursor.fetchall():
            if row['composite_score'] is not None:
                regime_rec.append(float(row['composite_score']))
            if row['vol_annualized'] is not None:
                vol_rec.append(float(row['vol_annualized']))
    except Exception as e:
        print(f"  WARNING: Could not fetch regime data: {e}")

    # Compute global regime/volatility PSI
    regime_psi = compute_psi(regime_ref, regime_rec)
    vol_psi = compute_psi(vol_ref, vol_rec)

    print(f"\n  Global Market Features:")
    print(f"    Regime Composite PSI:  {_fmt_psi(regime_psi)}  "
          f"(ref={len(regime_ref)}, recent={len(regime_rec)})")
    print(f"    Volatility PSI:        {_fmt_psi(vol_psi)}  "
          f"(ref={len(vol_ref)}, recent={len(vol_rec)})")

    results['_global'] = {
        'regime_psi': regime_psi,
        'regime_status': classify_psi(regime_psi),
        'vol_psi': vol_psi,
        'vol_status': classify_psi(vol_psi),
    }

    # Compute per-algorithm PSI
    all_algos = sorted(set(list(ref_by_algo.keys()) + list(rec_by_algo.keys())))
    print(f"\n  Per-Algorithm Feature PSI ({len(all_algos)} algorithms):")
    print(f"  {'Algorithm':30s} | {'Str PSI':>8} | {'Hour PSI':>9} | {'RefN':>5} | {'RecN':>5} | {'Status':>16}")
    print(f"  {'-' * 90}")

    for algo in all_algos:
        ref_str = ref_by_algo[algo]['strength']
        rec_str = rec_by_algo[algo]['strength']
        ref_hr = ref_by_algo[algo]['hour']
        rec_hr = rec_by_algo[algo]['hour']

        str_psi = compute_psi(ref_str, rec_str)
        hr_psi = compute_psi(ref_hr, rec_hr)

        # Overall status is the worst of the two
        str_status = classify_psi(str_psi)
        hr_status = classify_psi(hr_psi)
        overall = _worst_status(str_status, hr_status)

        results[algo] = {
            'signal_strength_psi': str_psi,
            'hour_of_day_psi': hr_psi,
            'ref_count': len(ref_str),
            'recent_count': len(rec_str),
            'status': overall,
        }

        status_label = _colorize_status(overall)
        print(f"  {algo:30s} | {_fmt_psi(str_psi):>8} | {_fmt_psi(hr_psi):>9} | "
              f"{len(ref_str):>5} | {len(rec_str):>5} | {status_label:>16}")

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# 2. Win Rate & Sharpe Degradation (Performance Drift)
# ---------------------------------------------------------------------------
def detect_performance_drift(conn):
    """
    Detect win rate and Sharpe ratio degradation per algorithm + asset class.

    Compares:
      - Historical: all closed trades except the most recent 20
      - Recent: the most recent 20 closed trades
    Flags if recent WR drops by >15pp or Sharpe drops by >0.5.
    """
    print("\n" + "=" * 70)
    print("  2. PERFORMANCE DRIFT DETECTION (Win Rate & Sharpe)")
    print("=" * 70)

    cursor = conn.cursor(dictionary=True)
    results = {}

    try:
        # Fetch all closed trades ordered by exit time
        cursor.execute("""
            SELECT algorithm_name, asset_class, realized_pnl_usd, realized_pct,
                   entry_price, exit_price, exit_time
            FROM lm_trades
            WHERE status = 'closed' AND algorithm_name != ''
            ORDER BY algorithm_name, asset_class, exit_time ASC
        """)
        all_trades = cursor.fetchall()
    except Exception as e:
        print(f"  ERROR fetching trades: {e}")
        cursor.close()
        return results

    # Group by algorithm + asset_class
    grouped = defaultdict(list)
    for t in all_trades:
        key = (t['algorithm_name'], t['asset_class'])
        grouped[key].append(t)

    print(f"\n  {'Algorithm':30s} | {'Asset':7s} | {'HistWR':>7} | {'RecWR':>7} | {'WR Drop':>8} | "
          f"{'HistSh':>7} | {'RecSh':>7} | {'N':>5} | {'Status':>16}")
    print(f"  {'-' * 120}")

    for (algo, asset_class), trades in sorted(grouped.items()):
        n_total = len(trades)
        if n_total < MIN_TRADES_FOR_PERF_DRIFT:
            results[(algo, asset_class)] = {
                'status': 'INSUFFICIENT_DATA',
                'total_trades': n_total,
                'reason': f'Need {MIN_TRADES_FOR_PERF_DRIFT}+ trades, have {n_total}',
            }
            continue

        # Split into historical and recent
        recent_trades = trades[-MIN_RECENT_TRADES:]
        historical_trades = trades[:-MIN_RECENT_TRADES]

        if len(historical_trades) < 5:
            results[(algo, asset_class)] = {
                'status': 'INSUFFICIENT_DATA',
                'total_trades': n_total,
                'reason': f'Not enough historical trades after split',
            }
            continue

        # Compute win rates
        hist_wins = sum(1 for t in historical_trades
                        if float(t.get('realized_pnl_usd', 0) or 0) > 0)
        hist_wr = (hist_wins / len(historical_trades)) * 100

        rec_wins = sum(1 for t in recent_trades
                       if float(t.get('realized_pnl_usd', 0) or 0) > 0)
        rec_wr = (rec_wins / len(recent_trades)) * 100

        wr_drop = hist_wr - rec_wr

        # Compute Sharpe ratios (annualized, assuming ~252 trading days)
        hist_returns = [float(t.get('realized_pct', 0) or 0) for t in historical_trades]
        rec_returns = [float(t.get('realized_pct', 0) or 0) for t in recent_trades]

        hist_sharpe = _compute_sharpe(hist_returns)
        rec_sharpe = _compute_sharpe(rec_returns)
        sharpe_drop = hist_sharpe - rec_sharpe

        # Classify
        issues = []
        if wr_drop > WR_DEGRADATION_THRESHOLD:
            issues.append(f'WR dropped {wr_drop:.1f}pp')
        if sharpe_drop > SHARPE_DEGRADATION_THRESHOLD:
            issues.append(f'Sharpe dropped {sharpe_drop:.2f}')

        if issues:
            status = 'RETRAIN_NEEDED'
        elif wr_drop > WR_DEGRADATION_THRESHOLD * 0.6:
            status = 'MONITOR'
        elif sharpe_drop > SHARPE_DEGRADATION_THRESHOLD * 0.6:
            status = 'MONITOR'
        else:
            status = 'OK'

        results[(algo, asset_class)] = {
            'historical_wr': round(hist_wr, 1),
            'recent_wr': round(rec_wr, 1),
            'wr_drop_pp': round(wr_drop, 1),
            'historical_sharpe': round(hist_sharpe, 4),
            'recent_sharpe': round(rec_sharpe, 4),
            'sharpe_drop': round(sharpe_drop, 4),
            'total_trades': n_total,
            'historical_trades': len(historical_trades),
            'recent_trades': len(recent_trades),
            'status': status,
            'issues': issues,
        }

        status_label = _colorize_status(status)
        print(f"  {algo:30s} | {asset_class:7s} | {hist_wr:>6.1f}% | {rec_wr:>6.1f}% | "
              f"{wr_drop:>+7.1f}pp | {hist_sharpe:>7.2f} | {rec_sharpe:>7.2f} | "
              f"{n_total:>5} | {status_label:>16}")

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# 3. Signal Volume Drift
# ---------------------------------------------------------------------------
def detect_signal_volume_drift(conn, ref_days, recent_days):
    """
    Compare signal generation frequency between reference and recent periods.

    Flags if signal volume per day changes by >50% (either direction).
    A sudden increase may indicate a regime change or lowered quality bar.
    A sudden decrease may indicate data issues or algorithm failures.
    """
    print("\n" + "=" * 70)
    print("  3. SIGNAL VOLUME DRIFT")
    print("=" * 70)

    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    ref_start = now - timedelta(days=ref_days)
    ref_end = now - timedelta(days=recent_days)
    recent_start = ref_end

    results = {}

    try:
        # Reference period: signals per day per algorithm
        cursor.execute("""
            SELECT algorithm_name, COUNT(*) as total_signals
            FROM lm_signals
            WHERE signal_time >= %s AND signal_time < %s
              AND algorithm_name != ''
            GROUP BY algorithm_name
        """, (ref_start.strftime('%Y-%m-%d %H:%M:%S'),
              ref_end.strftime('%Y-%m-%d %H:%M:%S')))
        ref_counts = {row['algorithm_name']: row['total_signals'] for row in cursor.fetchall()}

        # Recent period
        cursor.execute("""
            SELECT algorithm_name, COUNT(*) as total_signals
            FROM lm_signals
            WHERE signal_time >= %s
              AND algorithm_name != ''
            GROUP BY algorithm_name
        """, (recent_start.strftime('%Y-%m-%d %H:%M:%S'),))
        rec_counts = {row['algorithm_name']: row['total_signals'] for row in cursor.fetchall()}
    except Exception as e:
        print(f"  ERROR fetching signal counts: {e}")
        cursor.close()
        return results

    # Normalize to signals/day
    ref_span = max(1, (ref_end - ref_start).days)
    rec_span = max(1, recent_days)

    all_algos = sorted(set(list(ref_counts.keys()) + list(rec_counts.keys())))

    print(f"\n  Reference: {ref_span} days | Recent: {rec_span} days")
    print(f"\n  {'Algorithm':30s} | {'Ref/day':>8} | {'Rec/day':>8} | {'Change':>8} | {'RefN':>6} | {'RecN':>6} | {'Status':>16}")
    print(f"  {'-' * 100}")

    for algo in all_algos:
        ref_total = ref_counts.get(algo, 0)
        rec_total = rec_counts.get(algo, 0)

        ref_per_day = ref_total / ref_span
        rec_per_day = rec_total / rec_span

        # Compute percentage change
        if ref_per_day > 0:
            pct_change = (rec_per_day - ref_per_day) / ref_per_day
        elif rec_per_day > 0:
            pct_change = 1.0  # New algorithm appeared (100% increase from 0)
        else:
            pct_change = 0.0  # Both zero

        # Classify
        if ref_total == 0 and rec_total == 0:
            status = 'INACTIVE'
        elif ref_total < 5:
            status = 'INSUFFICIENT_DATA'
        elif abs(pct_change) > VOLUME_CHANGE_THRESHOLD:
            if pct_change > 0:
                status = 'VOLUME_SURGE'
            else:
                status = 'VOLUME_DROP'
        elif abs(pct_change) > VOLUME_CHANGE_THRESHOLD * 0.6:
            status = 'MONITOR'
        else:
            status = 'OK'

        results[algo] = {
            'ref_total': ref_total,
            'recent_total': rec_total,
            'ref_per_day': round(ref_per_day, 2),
            'recent_per_day': round(rec_per_day, 2),
            'pct_change': round(pct_change * 100, 1),
            'status': status,
        }

        status_label = _colorize_status(status)
        change_str = f"{pct_change:>+7.0%}" if ref_total >= 5 else "    N/A"
        print(f"  {algo:30s} | {ref_per_day:>8.2f} | {rec_per_day:>8.2f} | {change_str} | "
              f"{ref_total:>6} | {rec_total:>6} | {status_label:>16}")

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# Update lm_ml_status with drift alerts
# ---------------------------------------------------------------------------
def update_ml_status(conn, feature_drift, perf_drift, volume_drift, dry_run=False):
    """
    Update lm_ml_status.status_reason with concept drift information.
    Only updates algorithms that have drift issues.
    """
    print("\n" + "=" * 70)
    print("  UPDATING lm_ml_status WITH DRIFT ALERTS")
    print("=" * 70)

    # Collect drift alerts per algorithm
    alerts_by_algo = defaultdict(list)

    # Feature drift alerts
    for algo, info in feature_drift.items():
        if algo == '_global':
            continue
        status = info.get('status', 'OK')
        if status in ('MONITOR', 'RETRAIN_NEEDED'):
            psi_str = info.get('signal_strength_psi', 'N/A')
            alerts_by_algo[algo].append(
                f"Feature drift: {status} (strength_PSI={psi_str})"
            )

    # Global regime drift affects all algorithms
    global_drift = feature_drift.get('_global', {})
    if global_drift.get('regime_status') in ('MONITOR', 'RETRAIN_NEEDED'):
        regime_alert = (f"Global regime drift: {global_drift['regime_status']} "
                        f"(PSI={global_drift.get('regime_psi', 'N/A')})")
        for algo in set(list(feature_drift.keys()) + [k[0] for k in perf_drift.keys()]):
            if algo != '_global':
                alerts_by_algo[algo].append(regime_alert)

    # Performance drift alerts
    for (algo, asset_class), info in perf_drift.items():
        status = info.get('status', 'OK')
        if status in ('MONITOR', 'RETRAIN_NEEDED'):
            issues = info.get('issues', [])
            issue_str = '; '.join(issues) if issues else status
            alerts_by_algo[algo].append(
                f"Perf drift ({asset_class}): {issue_str}"
            )

    # Volume drift alerts
    for algo, info in volume_drift.items():
        status = info.get('status', '')
        if status in ('VOLUME_SURGE', 'VOLUME_DROP'):
            pct = info.get('pct_change', 0)
            alerts_by_algo[algo].append(
                f"Volume drift: {status} ({pct:+.0f}%)"
            )

    if not alerts_by_algo:
        print("\n  No drift alerts to write -- all algorithms stable")
        return 0

    # Write to DB
    cursor = conn.cursor(dictionary=True)
    updated = 0
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for algo, alert_list in sorted(alerts_by_algo.items()):
        drift_summary = ' | '.join(alert_list)
        # Prefix with timestamp
        status_text = f"[Drift {timestamp[:10]}] {drift_summary}"
        # Truncate to fit TEXT column reasonably
        if len(status_text) > 500:
            status_text = status_text[:497] + '...'

        if dry_run:
            print(f"  [DRY RUN] Would update {algo}: {status_text}")
        else:
            try:
                # Try UPDATE first (algorithm might already have a row)
                cursor.execute("""
                    UPDATE lm_ml_status
                    SET status_reason = %s,
                        updated_at = %s
                    WHERE algorithm_name = %s
                """, (status_text, timestamp, algo))

                if cursor.rowcount > 0:
                    updated += cursor.rowcount
                    print(f"  Updated {algo}: {status_text[:80]}...")
                else:
                    # No existing row -- that is fine, don't insert blindly
                    print(f"  No lm_ml_status row for {algo} -- alert logged to console only")

            except Exception as e:
                print(f"  ERROR updating {algo}: {e}")

    if not dry_run:
        try:
            conn.commit()
        except Exception as e:
            print(f"  ERROR committing: {e}")

    cursor.close()
    print(f"\n  Updated {updated} rows in lm_ml_status")
    return updated


# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------
def print_summary(feature_drift, perf_drift, volume_drift):
    """Print a consolidated summary of all drift findings."""
    print("\n" + "=" * 70)
    print("  CONCEPT DRIFT SUMMARY")
    print("=" * 70)

    retrain = []
    monitor = []
    ok = []

    # Collect all algorithm statuses
    algo_worst = {}

    for algo, info in feature_drift.items():
        if algo == '_global':
            continue
        status = info.get('status', 'OK')
        algo_worst[algo] = _worst_status(algo_worst.get(algo, 'OK'), status)

    for (algo, asset), info in perf_drift.items():
        status = info.get('status', 'OK')
        if status not in ('INSUFFICIENT_DATA',):
            algo_worst[algo] = _worst_status(algo_worst.get(algo, 'OK'), status)

    for algo, info in volume_drift.items():
        status = info.get('status', '')
        mapped = 'RETRAIN_NEEDED' if status in ('VOLUME_SURGE', 'VOLUME_DROP') else (
            'MONITOR' if status == 'MONITOR' else 'OK')
        if status not in ('INACTIVE', 'INSUFFICIENT_DATA'):
            algo_worst[algo] = _worst_status(algo_worst.get(algo, 'OK'), mapped)

    for algo, status in sorted(algo_worst.items()):
        if status == 'RETRAIN_NEEDED':
            retrain.append(algo)
        elif status == 'MONITOR':
            monitor.append(algo)
        else:
            ok.append(algo)

    # Global regime check
    global_info = feature_drift.get('_global', {})
    if global_info.get('regime_status') in ('RETRAIN_NEEDED',):
        print(f"\n  *** GLOBAL REGIME SHIFT DETECTED *** (PSI={global_info.get('regime_psi', '?')})")
        print(f"      All algorithms should be reviewed for regime adaptation")
    if global_info.get('vol_status') in ('RETRAIN_NEEDED',):
        print(f"\n  *** GLOBAL VOLATILITY REGIME CHANGE *** (PSI={global_info.get('vol_psi', '?')})")

    print(f"\n  Total algorithms evaluated: {len(algo_worst)}")
    print()

    if retrain:
        print(f"  RETRAIN NEEDED ({len(retrain)}):")
        for algo in retrain:
            reasons = _get_reasons(algo, feature_drift, perf_drift, volume_drift)
            print(f"    [!!] {algo}")
            for r in reasons:
                print(f"         - {r}")
        print()

    if monitor:
        print(f"  MONITOR ({len(monitor)}):")
        for algo in monitor:
            reasons = _get_reasons(algo, feature_drift, perf_drift, volume_drift)
            print(f"    [??] {algo}")
            for r in reasons:
                print(f"         - {r}")
        print()

    if ok:
        print(f"  OK ({len(ok)}):")
        for algo in ok:
            print(f"    [  ] {algo}")
        print()

    return {
        'retrain_needed': retrain,
        'monitor': monitor,
        'ok': ok,
    }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def _compute_sharpe(returns, annualize_factor=252):
    """Compute annualized Sharpe ratio from a list of per-trade return percentages."""
    if not returns or len(returns) < 2:
        return 0.0
    import numpy as np
    arr = np.array(returns, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std < 1e-8:
        return 0.0
    return round(float((mean / std) * math.sqrt(annualize_factor)), 4)


def _fmt_psi(psi_value):
    """Format PSI value for display."""
    if psi_value is None:
        return "   --"
    return f"{psi_value:.4f}"


def _colorize_status(status):
    """Return status string with text marker for severity."""
    markers = {
        'OK': '[ OK ]',
        'MONITOR': '[ ?? ]',
        'RETRAIN_NEEDED': '[ !! ]',
        'VOLUME_SURGE': '[ !! ]',
        'VOLUME_DROP': '[ !! ]',
        'INSUFFICIENT_DATA': '[ -- ]',
        'INACTIVE': '[ -- ]',
    }
    return markers.get(status, f'[{status}]')


def _worst_status(a, b):
    """Return the more severe of two statuses."""
    order = {
        'OK': 0,
        'INSUFFICIENT_DATA': 0,
        'INACTIVE': 0,
        'MONITOR': 1,
        'RETRAIN_NEEDED': 2,
        'VOLUME_SURGE': 2,
        'VOLUME_DROP': 2,
    }
    if order.get(a, 0) >= order.get(b, 0):
        return a
    return b


def _get_reasons(algo, feature_drift, perf_drift, volume_drift):
    """Collect all drift reasons for a given algorithm."""
    reasons = []
    finfo = feature_drift.get(algo, {})
    if finfo.get('status') in ('MONITOR', 'RETRAIN_NEEDED'):
        psi = finfo.get('signal_strength_psi', '?')
        reasons.append(f"Feature drift: signal_strength PSI={psi}")

    for (a, ac), info in perf_drift.items():
        if a == algo and info.get('status') in ('MONITOR', 'RETRAIN_NEEDED'):
            wr_drop = info.get('wr_drop_pp', 0)
            sharpe_drop = info.get('sharpe_drop', 0)
            reasons.append(f"Perf drift ({ac}): WR drop {wr_drop:+.1f}pp, Sharpe drop {sharpe_drop:+.2f}")

    vinfo = volume_drift.get(algo, {})
    if vinfo.get('status') in ('VOLUME_SURGE', 'VOLUME_DROP', 'MONITOR'):
        pct = vinfo.get('pct_change', 0)
        reasons.append(f"Volume drift: {vinfo['status']} ({pct:+.0f}%)")

    return reasons if reasons else ['Status elevated']


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Concept Drift Detector -- monitors for feature, performance, and volume drift'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Analyze only, do not update lm_ml_status')
    parser.add_argument('--ref-days', type=int, default=DEFAULT_REF_DAYS,
                        help=f'Reference window in days (default {DEFAULT_REF_DAYS})')
    parser.add_argument('--recent-days', type=int, default=DEFAULT_RECENT_DAYS,
                        help=f'Recent window in days (default {DEFAULT_RECENT_DAYS})')
    args = parser.parse_args()

    print("=" * 70)
    print(f"  CONCEPT DRIFT DETECTOR")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Reference window: {args.ref_days} days | Recent window: {args.recent_days} days")
    if args.dry_run:
        print(f"  MODE: DRY RUN (no DB writes)")
    print("=" * 70)

    # Connect to database
    conn = None
    try:
        print(f"\n  Connecting to {DB_HOST}/{DB_NAME}...")
        conn = connect_db()
        print(f"  Database connected")
    except Exception as e:
        print(f"  FATAL: Cannot connect to database: {e}")
        sys.exit(1)

    try:
        # 1. Feature Drift (PSI)
        feature_drift = detect_feature_drift(conn, args.ref_days, args.recent_days)

        # 2. Performance Drift (Win Rate + Sharpe degradation)
        perf_drift = detect_performance_drift(conn)

        # 3. Signal Volume Drift
        volume_drift = detect_signal_volume_drift(conn, args.ref_days, args.recent_days)

        # Summary
        summary = print_summary(feature_drift, perf_drift, volume_drift)

        # Update lm_ml_status
        updated = update_ml_status(conn, feature_drift, perf_drift, volume_drift,
                                   dry_run=args.dry_run)

        # Final line
        n_retrain = len(summary.get('retrain_needed', []))
        n_monitor = len(summary.get('monitor', []))
        n_ok = len(summary.get('ok', []))

        print("=" * 70)
        print(f"  DONE -- Retrain: {n_retrain} | Monitor: {n_monitor} | OK: {n_ok} | "
              f"DB updates: {updated}")
        print("=" * 70)

        # Exit with non-zero if retraining needed (useful for CI/CD alerting)
        if n_retrain > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n  FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()
