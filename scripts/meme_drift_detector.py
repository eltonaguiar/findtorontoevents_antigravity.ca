#!/usr/bin/env python3
"""
Meme Coin Concept Drift Detector -- Monitors mc_winners for indicator
distribution shifts and win rate degradation, triggering retrain alerts.

Monitors:
  1. PSI on each of the 7 indicator scores (rolling 7-day vs 30-day baseline)
  2. Win rate degradation vs historical baseline
  3. Signal volume changes (are we generating more/fewer signals?)

Connects to ejaguiar1_memecoin database (same as meme_scanner.php).

Usage:
  python scripts/meme_drift_detector.py
  python scripts/meme_drift_detector.py --dry-run
  python scripts/meme_drift_detector.py --ref-days 30 --recent-days 7
"""
import os
import sys
import math
import json
import argparse
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MEME_DB_HOST = os.getenv('MEME_DB_HOST', 'mysql.50webs.com')
MEME_DB_USER = os.getenv('MEME_DB_USER', 'ejaguiar1_memecoin')
MEME_DB_PASS = os.getenv('MEME_DB_PASS', 'testing123')
MEME_DB_NAME = os.getenv('MEME_DB_NAME', 'ejaguiar1_memecoin')

# PSI thresholds
PSI_OK = 0.10
PSI_MODERATE = 0.25

# Win rate degradation threshold (percentage points)
WR_DEGRADATION_PP = 15.0

# Volume change threshold
VOLUME_CHANGE_PCT = 50.0

# Minimum samples
MIN_SIGNALS_FOR_PSI = 15
MIN_RESOLVED_FOR_WR = 10

# Factor keys and their max scores for normalization
FACTOR_KEYS = [
    ('explosive_volume', 25),
    ('parabolic_momentum', 20),
    ('rsi_hype_zone', 15),
    ('social_proxy', 15),
    ('volume_concentration', 10),
    ('breakout_4h', 10),
    ('low_cap_bonus', 5),
]

DEFAULT_REF_DAYS = 30
DEFAULT_RECENT_DAYS = 7


def connect_meme_db():
    """Connect to the meme coin MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=MEME_DB_HOST,
        user=MEME_DB_USER,
        password=MEME_DB_PASS,
        database=MEME_DB_NAME,
        connect_timeout=15,
    )


def compute_psi(reference, recent, buckets=10):
    """Compute Population Stability Index between two distributions."""
    if not reference or not recent:
        return None
    if len(reference) < 5 or len(recent) < 5:
        return None

    min_val = min(reference)
    max_val = max(reference)

    if max_val == min_val:
        if min(recent) == max(recent) == min_val:
            return 0.0
        return 1.0

    bin_width = (max_val - min_val) / buckets
    edges = [min_val + i * bin_width for i in range(buckets + 1)]
    edges[-1] = max_val + 1e-10

    def bin_proportions(values):
        n = len(values)
        counts = [0] * buckets
        for v in values:
            placed = False
            for i in range(buckets):
                if edges[i] <= v < edges[i + 1]:
                    counts[i] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1
        epsilon = 1e-6
        props = [(c / n) + epsilon for c in counts]
        total = sum(props)
        return [p / total for p in props]

    ref_props = bin_proportions(reference)
    rec_props = bin_proportions(recent)

    psi = 0.0
    for r_ref, r_rec in zip(ref_props, rec_props):
        psi += (r_rec - r_ref) * math.log(r_rec / r_ref)

    return round(max(0.0, psi), 6)


def classify_psi(psi_value):
    if psi_value is None:
        return 'INSUFFICIENT_DATA'
    if psi_value < PSI_OK:
        return 'OK'
    elif psi_value < PSI_MODERATE:
        return 'MONITOR'
    return 'RETRAIN_NEEDED'


def extract_factor_score(factors_json, key):
    """Extract a factor score from the factors_json dict."""
    if not factors_json:
        return None
    f = factors_json.get(key)
    if f is None:
        return None
    if isinstance(f, dict):
        return f.get('score', 0)
    if isinstance(f, (int, float)):
        return f
    return None


# ---------------------------------------------------------------------------
# 1. Feature Drift Detection
# ---------------------------------------------------------------------------
def detect_meme_feature_drift(conn, ref_days, recent_days):
    """Detect feature distribution drift on mc_winners using PSI."""
    print("\n" + "=" * 60)
    print("  1. MEME FEATURE DRIFT (PSI)")
    print("=" * 60)

    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    ref_start = now - timedelta(days=ref_days)
    ref_end = now - timedelta(days=recent_days)
    recent_start = ref_end

    # Fetch reference period signals
    cursor.execute(
        "SELECT factors_json, score FROM mc_winners "
        "WHERE created_at >= %s AND created_at < %s AND factors_json IS NOT NULL",
        (ref_start.strftime('%Y-%m-%d'), ref_end.strftime('%Y-%m-%d'))
    )
    ref_rows = cursor.fetchall()

    # Fetch recent period signals
    cursor.execute(
        "SELECT factors_json, score FROM mc_winners "
        "WHERE created_at >= %s AND factors_json IS NOT NULL",
        (recent_start.strftime('%Y-%m-%d'),)
    )
    recent_rows = cursor.fetchall()

    cursor.close()

    print(f"  Reference: {len(ref_rows)} signals ({ref_days}d window)")
    print(f"  Recent:    {len(recent_rows)} signals ({recent_days}d window)")

    results = {}

    for key, max_val in FACTOR_KEYS:
        ref_values = []
        for r in ref_rows:
            fj = r['factors_json']
            if isinstance(fj, str):
                try:
                    fj = json.loads(fj)
                except Exception:
                    continue
            val = extract_factor_score(fj, key)
            if val is not None:
                ref_values.append(val / max_val if max_val > 0 else val)

        rec_values = []
        for r in recent_rows:
            fj = r['factors_json']
            if isinstance(fj, str):
                try:
                    fj = json.loads(fj)
                except Exception:
                    continue
            val = extract_factor_score(fj, key)
            if val is not None:
                rec_values.append(val / max_val if max_val > 0 else val)

        psi = compute_psi(ref_values, rec_values)
        status = classify_psi(psi)

        results[key] = {
            'psi': psi,
            'status': status,
            'ref_count': len(ref_values),
            'recent_count': len(rec_values),
            'ref_mean': round(sum(ref_values) / len(ref_values), 4) if ref_values else None,
            'recent_mean': round(sum(rec_values) / len(rec_values), 4) if rec_values else None,
        }

        symbol = {'OK': '+', 'MONITOR': '!', 'RETRAIN_NEEDED': 'X', 'INSUFFICIENT_DATA': '?'}[status]
        psi_str = f"{psi:.4f}" if psi is not None else "N/A"
        print(f"  [{symbol}] {key:25s}  PSI={psi_str:8s}  {status}")

    # Also check total score distribution
    ref_scores = [r['score'] for r in ref_rows if r['score'] is not None]
    rec_scores = [r['score'] for r in recent_rows if r['score'] is not None]
    score_psi = compute_psi(ref_scores, rec_scores)
    score_status = classify_psi(score_psi)
    results['total_score'] = {
        'psi': score_psi,
        'status': score_status,
        'ref_mean': round(sum(ref_scores) / len(ref_scores), 1) if ref_scores else None,
        'recent_mean': round(sum(rec_scores) / len(rec_scores), 1) if rec_scores else None,
    }
    symbol = {'OK': '+', 'MONITOR': '!', 'RETRAIN_NEEDED': 'X', 'INSUFFICIENT_DATA': '?'}[score_status]
    psi_str = f"{score_psi:.4f}" if score_psi is not None else "N/A"
    print(f"  [{symbol}] {'total_score':25s}  PSI={psi_str:8s}  {score_status}")

    return results


# ---------------------------------------------------------------------------
# 2. Win Rate Degradation
# ---------------------------------------------------------------------------
def detect_meme_wr_drift(conn, ref_days, recent_days):
    """Detect win rate degradation in meme signals."""
    print("\n" + "=" * 60)
    print("  2. MEME WIN RATE DRIFT")
    print("=" * 60)

    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    ref_end = now - timedelta(days=recent_days)
    ref_start = now - timedelta(days=ref_days)

    # Reference win rate
    cursor.execute(
        "SELECT outcome FROM mc_winners "
        "WHERE outcome IS NOT NULL AND created_at >= %s AND created_at < %s",
        (ref_start.strftime('%Y-%m-%d'), ref_end.strftime('%Y-%m-%d'))
    )
    ref_outcomes = cursor.fetchall()
    ref_wins = sum(1 for r in ref_outcomes if r['outcome'] in ('win', 'partial_win'))
    ref_total = len(ref_outcomes)
    ref_wr = (ref_wins / ref_total * 100) if ref_total > 0 else None

    # Recent win rate
    cursor.execute(
        "SELECT outcome FROM mc_winners "
        "WHERE outcome IS NOT NULL AND created_at >= %s",
        (ref_end.strftime('%Y-%m-%d'),)
    )
    recent_outcomes = cursor.fetchall()
    rec_wins = sum(1 for r in recent_outcomes if r['outcome'] in ('win', 'partial_win'))
    rec_total = len(recent_outcomes)
    rec_wr = (rec_wins / rec_total * 100) if rec_total > 0 else None

    cursor.close()

    wr_drop = 0
    status = 'OK'

    if ref_wr is not None and rec_wr is not None:
        wr_drop = ref_wr - rec_wr
        if wr_drop > WR_DEGRADATION_PP:
            status = 'RETRAIN_NEEDED'
        elif wr_drop > WR_DEGRADATION_PP / 2:
            status = 'MONITOR'

    if ref_total < MIN_RESOLVED_FOR_WR or rec_total < MIN_RESOLVED_FOR_WR:
        status = 'INSUFFICIENT_DATA'

    result = {
        'ref_wr': round(ref_wr, 1) if ref_wr is not None else None,
        'ref_total': ref_total,
        'recent_wr': round(rec_wr, 1) if rec_wr is not None else None,
        'recent_total': rec_total,
        'wr_drop_pp': round(wr_drop, 1),
        'status': status,
    }

    print(f"  Reference WR: {result['ref_wr']}% ({ref_total} signals)")
    print(f"  Recent WR:    {result['recent_wr']}% ({rec_total} signals)")
    print(f"  WR Drop:      {result['wr_drop_pp']} pp  [{status}]")

    return result


# ---------------------------------------------------------------------------
# 3. Signal Volume Drift
# ---------------------------------------------------------------------------
def detect_meme_volume_drift(conn, ref_days, recent_days):
    """Detect changes in signal generation frequency."""
    print("\n" + "=" * 60)
    print("  3. MEME SIGNAL VOLUME DRIFT")
    print("=" * 60)

    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    ref_start = now - timedelta(days=ref_days)
    ref_end = now - timedelta(days=recent_days)

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM mc_winners WHERE created_at >= %s AND created_at < %s",
        (ref_start.strftime('%Y-%m-%d'), ref_end.strftime('%Y-%m-%d'))
    )
    ref_count = cursor.fetchone()['cnt']

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM mc_winners WHERE created_at >= %s",
        (ref_end.strftime('%Y-%m-%d'),)
    )
    rec_count = cursor.fetchone()['cnt']

    cursor.close()

    # Normalize to daily average
    ref_daily = ref_count / max(1, ref_days - recent_days)
    rec_daily = rec_count / max(1, recent_days)
    pct_change = ((rec_daily - ref_daily) / ref_daily * 100) if ref_daily > 0 else 0

    status = 'OK'
    if abs(pct_change) > VOLUME_CHANGE_PCT:
        status = 'VOLUME_SURGE' if pct_change > 0 else 'VOLUME_DROP'
    elif abs(pct_change) > VOLUME_CHANGE_PCT / 2:
        status = 'MONITOR'

    result = {
        'ref_daily_avg': round(ref_daily, 1),
        'recent_daily_avg': round(rec_daily, 1),
        'pct_change': round(pct_change, 1),
        'status': status,
    }

    print(f"  Ref daily avg:    {result['ref_daily_avg']} signals/day")
    print(f"  Recent daily avg: {result['recent_daily_avg']} signals/day")
    print(f"  Change:           {result['pct_change']}%  [{status}]")

    return result


# ---------------------------------------------------------------------------
# Summary and Alerts
# ---------------------------------------------------------------------------
def print_summary(feature_drift, wr_drift, vol_drift):
    print("\n" + "=" * 60)
    print("  MEME DRIFT SUMMARY")
    print("=" * 60)

    alerts = []

    # Feature drift alerts
    for key, info in feature_drift.items():
        if info['status'] == 'RETRAIN_NEEDED':
            alerts.append(f"RETRAIN: {key} PSI={info['psi']}")
        elif info['status'] == 'MONITOR':
            alerts.append(f"MONITOR: {key} PSI={info['psi']}")

    # Win rate drift
    if wr_drift['status'] == 'RETRAIN_NEEDED':
        alerts.append(f"RETRAIN: Win rate dropped {wr_drift['wr_drop_pp']}pp")
    elif wr_drift['status'] == 'MONITOR':
        alerts.append(f"MONITOR: Win rate dropping {wr_drift['wr_drop_pp']}pp")

    # Volume drift
    if vol_drift['status'] in ('VOLUME_SURGE', 'VOLUME_DROP'):
        alerts.append(f"ALERT: Signal volume {vol_drift['status']} ({vol_drift['pct_change']}%)")

    if not alerts:
        print("  All clear -- no significant drift detected")
    else:
        for a in alerts:
            print(f"  >> {a}")

    needs_retrain = any('RETRAIN' in a for a in alerts)
    print(f"\n  Recommendation: {'RETRAIN MODEL' if needs_retrain else 'Continue monitoring'}")

    return {
        'alerts': alerts,
        'needs_retrain': needs_retrain,
        'timestamp': datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Save results to mc_adaptive_weights table as a drift record
# ---------------------------------------------------------------------------
def save_drift_alert(conn, summary, feature_drift, wr_drift, vol_drift, dry_run=False):
    """Save drift detection results to the database."""
    if dry_run:
        print("\n  [DRY RUN] Skipping DB write")
        return

    try:
        cursor = conn.cursor()
        # Ensure drift log table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mc_drift_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                drift_json TEXT NOT NULL,
                needs_retrain TINYINT DEFAULT 0,
                alert_count INT DEFAULT 0,
                created_at DATETIME NOT NULL,
                INDEX idx_drift_created (created_at)
            ) ENGINE=MyISAM DEFAULT CHARSET=utf8
        """)

        drift_data = json.dumps({
            'feature_drift': feature_drift,
            'wr_drift': wr_drift,
            'vol_drift': vol_drift,
            'summary': summary,
        })

        cursor.execute(
            "INSERT INTO mc_drift_log (drift_json, needs_retrain, alert_count, created_at) "
            "VALUES (%s, %s, %s, NOW())",
            (drift_data, 1 if summary['needs_retrain'] else 0, len(summary['alerts']))
        )
        conn.commit()
        cursor.close()
        print(f"\n  Drift results saved to mc_drift_log")
    except Exception as e:
        print(f"\n  WARNING: Could not save drift results: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Meme Coin Concept Drift Detector'
    )
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--ref-days', type=int, default=DEFAULT_REF_DAYS)
    parser.add_argument('--recent-days', type=int, default=DEFAULT_RECENT_DAYS)
    args = parser.parse_args()

    print("=" * 60)
    print("  MEME COIN CONCEPT DRIFT DETECTOR")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Ref: {args.ref_days}d | Recent: {args.recent_days}d")
    if args.dry_run:
        print("  MODE: DRY RUN")
    print("=" * 60)

    conn = None
    try:
        conn = connect_meme_db()
        print(f"\n  Connected to {MEME_DB_NAME}")

        feature_drift = detect_meme_feature_drift(conn, args.ref_days, args.recent_days)
        wr_drift = detect_meme_wr_drift(conn, args.ref_days, args.recent_days)
        vol_drift = detect_meme_volume_drift(conn, args.ref_days, args.recent_days)
        summary = print_summary(feature_drift, wr_drift, vol_drift)

        save_drift_alert(conn, summary, feature_drift, wr_drift, vol_drift,
                         dry_run=args.dry_run)

        print("\n" + "=" * 60)
        retrain_flag = "YES" if summary['needs_retrain'] else "NO"
        print(f"  DONE -- Retrain needed: {retrain_flag} | Alerts: {len(summary['alerts'])}")
        print("=" * 60)

        if summary['needs_retrain']:
            sys.exit(1)

    except Exception as e:
        print(f"\n  FATAL: {e}")
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
