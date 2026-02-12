#!/usr/bin/env python3
"""
Signal Quality Checker — Measures signal calibration quality using proper metrics.
Compares lm_signals strength predictions vs lm_trades actual outcomes.

Metrics (academic standard):
  - Brier Score: mean((forecast - outcome)^2) — strictly proper scoring rule
  - ECE (Expected Calibration Error): weighted avg |bucket_accuracy - bucket_confidence|
  - Gap: |avg_signal_strength - win_rate| (legacy, simple aggregate check)
  - Grade: A/B/C/D/F based on gap

Sample size gating:
  - n >= 20 required for reliable Brier/ECE/grade
  - Below that, results marked INSUFFICIENT with warning

References:
  - Brier (1950) — "Verification of forecasts expressed in terms of probability"
  - Naeini et al. (2015) — "Obtaining Well Calibrated Probabilities Using Bayesian Binning"

Usage:
  python signal_quality_checker.py              # Analyze from DB
  python signal_quality_checker.py --csv FILE   # Analyze from CSV export
  python signal_quality_checker.py --min-n 30   # Override minimum sample size
"""
import os
import sys
import json
import csv
import math
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Minimum sample sizes for reliable calibration metrics
MIN_SAMPLES_DEFAULT = 20     # Below this, Brier/ECE are too noisy to trust
MIN_SAMPLES_PER_BUCKET = 5   # ECE buckets need at least this many signals

# ECE bucket configuration
ECE_NUM_BUCKETS = 10         # 10 equal-width bins: [0-10, 10-20, ..., 90-100]


def fetch_from_db():
    """Fetch signal and trade data from DB for gap analysis."""
    import mysql.connector
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)

    # Get signal stats: avg strength per algorithm
    cursor.execute("""
        SELECT algorithm_name, asset_class,
               COUNT(*) as total_signals,
               AVG(signal_strength) as avg_signal_strength,
               MIN(signal_strength) as min_strength,
               MAX(signal_strength) as max_strength
        FROM lm_signals
        WHERE algorithm_name != ''
        GROUP BY algorithm_name, asset_class
    """)
    signals = cursor.fetchall()

    # Get trade outcomes: win rate per algorithm
    cursor.execute("""
        SELECT algorithm_name, asset_class,
               COUNT(*) as total_trades,
               SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
               AVG(realized_pct) as avg_return_pct,
               AVG(realized_pnl_usd) as avg_pnl_usd
        FROM lm_trades
        WHERE status = 'closed' AND algorithm_name != ''
        GROUP BY algorithm_name, asset_class
    """)
    trades = cursor.fetchall()

    # Also try to fetch per-signal data for Brier/ECE (signal-level, not aggregated)
    per_signal = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.algorithm_name, s.asset_class, s.signal_strength,
                   CASE WHEN t.realized_pnl_usd > 0 THEN 1 ELSE 0 END as outcome
            FROM lm_signals s
            LEFT JOIN lm_trades t
                ON s.algorithm_name = t.algorithm_name
                AND s.asset_class = t.asset_class
                AND s.symbol = t.symbol
            WHERE s.algorithm_name != '' AND t.status = 'closed'
        """)
        per_signal = cursor.fetchall()
        cursor.close()
    except Exception:
        pass  # Graceful fallback — per_signal remains empty

    conn.close()
    return signals, trades, per_signal


def fetch_from_csv(csv_path):
    """Load combined signal+trade data from CSV."""
    signals = []
    trades = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row.get('algorithm_name', '')
            asset = row.get('asset_class', 'unknown')
            if 'signal_strength' in row:
                signals.append({
                    'algorithm_name': algo,
                    'asset_class': asset,
                    'total_signals': int(row.get('total_signals', 1)),
                    'avg_signal_strength': float(row.get('signal_strength', 0)),
                    'min_strength': float(row.get('signal_strength', 0)),
                    'max_strength': float(row.get('signal_strength', 0)),
                })
            if 'realized_pnl_usd' in row:
                trades.append({
                    'algorithm_name': algo,
                    'asset_class': asset,
                    'total_trades': int(row.get('total_trades', 1)),
                    'wins': int(row.get('wins', 0)),
                    'avg_return_pct': float(row.get('realized_pct', 0)),
                    'avg_pnl_usd': float(row.get('realized_pnl_usd', 0)),
                })
    return signals, trades, []  # No per-signal data from CSV


def calc_brier_score(forecasts, outcomes):
    """
    Brier Score — mean((forecast_probability - outcome)^2).
    Forecasts in [0, 1], outcomes in {0, 1}.
    Perfect calibration = 0.0, worst = 1.0, random = 0.25.
    Strictly proper scoring rule (Brier 1950).
    """
    if not forecasts:
        return None
    n = len(forecasts)
    return sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / n


def calc_brier_decomposition(forecasts, outcomes):
    """
    Brier score decomposition: Reliability (calibration) + Resolution + Uncertainty.

    Reliability = (1/N) * sum_k(n_k * (f_k - o_k_bar)^2)  — lower is better calibrated
    Resolution  = (1/N) * sum_k(n_k * (o_k_bar - o_bar)^2) — higher is more skillful
    Uncertainty = o_bar * (1 - o_bar)                       — fixed for dataset

    Brier = Reliability - Resolution + Uncertainty
    """
    if not forecasts:
        return None, None, None

    n = len(forecasts)
    o_bar = sum(outcomes) / n

    # Bucket by forecast decile
    buckets = {}
    for f, o in zip(forecasts, outcomes):
        bucket = min(int(f * ECE_NUM_BUCKETS), ECE_NUM_BUCKETS - 1)
        if bucket not in buckets:
            buckets[bucket] = {'forecasts': [], 'outcomes': []}
        buckets[bucket]['forecasts'].append(f)
        buckets[bucket]['outcomes'].append(o)

    reliability = 0.0
    resolution = 0.0
    for bk, bv in buckets.items():
        n_k = len(bv['outcomes'])
        f_k = sum(bv['forecasts']) / n_k
        o_k_bar = sum(bv['outcomes']) / n_k
        reliability += n_k * (f_k - o_k_bar) ** 2
        resolution += n_k * (o_k_bar - o_bar) ** 2

    reliability /= n
    resolution /= n
    uncertainty = o_bar * (1 - o_bar)

    return reliability, resolution, uncertainty


def calc_ece(forecasts, outcomes, num_buckets=ECE_NUM_BUCKETS):
    """
    Expected Calibration Error — weighted average of |accuracy - confidence| per bucket.
    Lower is better. 0.0 = perfect calibration.

    Uses equal-width bins (0-10%, 10-20%, ..., 90-100%) with min sample filter.
    Returns (ece, bucket_details).
    """
    if not forecasts:
        return None, []

    n = len(forecasts)
    bucket_width = 1.0 / num_buckets

    buckets = {}
    for f, o in zip(forecasts, outcomes):
        bucket = min(int(f / bucket_width), num_buckets - 1)
        if bucket not in buckets:
            buckets[bucket] = {'forecasts': [], 'outcomes': []}
        buckets[bucket]['forecasts'].append(f)
        buckets[bucket]['outcomes'].append(o)

    ece = 0.0
    details = []
    for b in range(num_buckets):
        if b not in buckets or len(buckets[b]['outcomes']) < MIN_SAMPLES_PER_BUCKET:
            details.append({
                'bucket': f"{b*10}-{(b+1)*10}%",
                'count': len(buckets[b]['outcomes']) if b in buckets else 0,
                'avg_confidence': None,
                'accuracy': None,
                'gap': None,
            })
            continue

        bv = buckets[b]
        n_b = len(bv['outcomes'])
        avg_conf = sum(bv['forecasts']) / n_b
        accuracy = sum(bv['outcomes']) / n_b
        gap = abs(accuracy - avg_conf)

        ece += (n_b / n) * gap

        details.append({
            'bucket': f"{b*10}-{(b+1)*10}%",
            'count': n_b,
            'avg_confidence': round(avg_conf * 100, 1),
            'accuracy': round(accuracy * 100, 1),
            'gap': round(gap * 100, 1),
        })

    return round(ece, 4), details


def grade_gap(gap):
    """Assign letter grade based on signal-to-outcome gap."""
    if gap < 10:
        return 'A'
    elif gap < 25:
        return 'B'
    elif gap < 50:
        return 'C'
    elif gap < 75:
        return 'D'
    else:
        return 'F'


def analyze(signals, trades, per_signal=None, min_samples=MIN_SAMPLES_DEFAULT):
    """
    Compare signal strength predictions vs actual trade outcomes.

    Computes:
      1. Legacy gap + grade (aggregate level)
      2. Brier score (per-signal level if data available, otherwise approximate)
      3. Brier decomposition (reliability, resolution, uncertainty)
      4. ECE with bucketed calibration analysis
      5. Sample-size gating with INSUFFICIENT warning
    """
    if per_signal is None:
        per_signal = []

    # Build trade lookup: algo|asset -> stats
    trade_map = {}
    for t in trades:
        key = f"{t['algorithm_name']}|{t['asset_class']}"
        trade_map[key] = t

    # Build per-signal lookup: algo|asset -> [(forecast, outcome), ...]
    signal_map = {}
    for ps in per_signal:
        algo = ps.get('algorithm_name', '')
        asset = ps.get('asset_class', 'unknown')
        key = f"{algo}|{asset}"
        if key not in signal_map:
            signal_map[key] = {'forecasts': [], 'outcomes': []}
        # signal_strength is 0-100, normalize to 0-1 for Brier
        strength = float(ps.get('signal_strength', 0)) / 100.0
        outcome = int(ps.get('outcome', 0))
        signal_map[key]['forecasts'].append(strength)
        signal_map[key]['outcomes'].append(outcome)

    results = []
    for s in signals:
        algo = s['algorithm_name']
        asset = s['asset_class']
        key = f"{algo}|{asset}"

        avg_strength = float(s.get('avg_signal_strength', 0))
        total_signals = int(s.get('total_signals', 0))

        # Match with trade outcomes
        t = trade_map.get(key)
        if t:
            total_trades = int(t.get('total_trades', 0))
            wins = int(t.get('wins', 0))
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            avg_return = float(t.get('avg_return_pct', 0))
            avg_pnl = float(t.get('avg_pnl_usd', 0))
            execution_rate = (total_trades / total_signals * 100) if total_signals > 0 else 0
        else:
            total_trades = 0
            wins = 0
            win_rate = 0
            avg_return = 0
            avg_pnl = 0
            execution_rate = 0

        # Gap = |signal_strength - actual_win_rate| (legacy)
        gap = abs(avg_strength - win_rate)
        grade = grade_gap(gap)

        # Sample size check
        effective_n = total_trades  # Use trade count as effective sample
        sample_sufficient = effective_n >= min_samples

        # --- Brier Score & ECE ---
        brier = None
        reliability = None
        resolution = None
        uncertainty = None
        ece = None
        ece_buckets = []

        if key in signal_map and len(signal_map[key]['forecasts']) >= min_samples:
            # We have per-signal data — compute exact Brier/ECE
            forecasts = signal_map[key]['forecasts']
            outcomes = signal_map[key]['outcomes']

            brier = calc_brier_score(forecasts, outcomes)
            reliability, resolution, uncertainty = calc_brier_decomposition(forecasts, outcomes)
            ece, ece_buckets = calc_ece(forecasts, outcomes)

        elif sample_sufficient and total_trades > 0:
            # Fallback: approximate Brier from aggregate data
            # Treat avg signal strength as uniform forecast, win_rate as observed frequency
            # Brier_approx = (avg_strength/100 - win_rate/100)^2 + WR*(1-WR)/n (noise term)
            f = avg_strength / 100.0
            o_rate = win_rate / 100.0
            brier = (f - o_rate) ** 2 + o_rate * (1 - o_rate) / total_trades
            # Can't compute decomposition or ECE from aggregates
            reliability = (f - o_rate) ** 2
            resolution = None
            uncertainty = o_rate * (1 - o_rate)

        result = {
            'algorithm': algo,
            'asset_class': asset,
            'total_signals': total_signals,
            'avg_signal_strength': round(avg_strength, 1),
            'total_trades': total_trades,
            'wins': wins,
            'win_rate_pct': round(win_rate, 1),
            'avg_return_pct': round(avg_return, 2),
            'avg_pnl_usd': round(avg_pnl, 2),
            'execution_rate_pct': round(execution_rate, 1),
            'gap': round(gap, 1),
            'grade': grade,
            'sample_sufficient': sample_sufficient,
            'brier_score': round(brier, 4) if brier is not None else None,
            'brier_decomposition': {
                'reliability': round(reliability, 4) if reliability is not None else None,
                'resolution': round(resolution, 4) if resolution is not None else None,
                'uncertainty': round(uncertainty, 4) if uncertainty is not None else None,
            },
            'ece': round(ece, 4) if ece is not None else None,
            'ece_buckets': ece_buckets if ece_buckets else None,
        }
        results.append(result)

    # Sort by grade (A first), then by gap ascending
    grade_order = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}
    results.sort(key=lambda x: (grade_order.get(x['grade'], 5), x['gap']))

    return results


def save_results(results, min_samples):
    """Save to JSON with calibration metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    json_path = os.path.join(OUTPUT_DIR, 'signal_quality.json')
    with open(json_path, 'w') as f:
        json.dump({
            'generated': ts,
            'methodology': {
                'min_samples': min_samples,
                'ece_buckets': ECE_NUM_BUCKETS,
                'min_per_bucket': MIN_SAMPLES_PER_BUCKET,
                'metrics': {
                    'brier_score': 'mean((forecast - outcome)^2), 0=perfect, 0.25=random, 1=worst',
                    'reliability': 'Calibration loss — how well forecasts match actual frequencies',
                    'resolution': 'Signal discrimination — ability to separate wins from losses',
                    'uncertainty': 'Base rate entropy — fixed for the dataset',
                    'ece': 'Expected Calibration Error — weighted |accuracy - confidence| per bucket',
                },
            },
            'total_algorithms': len(results),
            'quality_report': results
        }, f, indent=2)

    return json_path


def main():
    parser = argparse.ArgumentParser(description='Signal Quality Checker')
    parser.add_argument('--csv', help='Path to CSV export (skip DB)')
    parser.add_argument('--min-n', type=int, default=MIN_SAMPLES_DEFAULT,
                        help=f'Minimum samples for reliable metrics (default {MIN_SAMPLES_DEFAULT})')
    args = parser.parse_args()

    min_samples = args.min_n

    print("=== Signal Quality Checker (Brier + ECE) ===")
    print(f"Min samples for metrics: {min_samples}")

    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        signals, trades, per_signal = fetch_from_csv(args.csv)
    else:
        print("Fetching from database...")
        signals, trades, per_signal = fetch_from_db()

    print(f"Loaded {len(signals)} signal groups, {len(trades)} trade groups")
    if per_signal:
        print(f"  Per-signal data: {len(per_signal)} rows (exact Brier/ECE available)")
    else:
        print("  No per-signal data — using aggregate approximation for Brier")

    if not signals:
        print("No signal data found. Nothing to analyze.")
        return

    results = analyze(signals, trades, per_signal, min_samples)

    # --- Main table ---
    print(f"\n{'Algorithm':28s} | {'Asset':7s} | {'N':>5} | {'Str%':>5} | {'WR%':>5} | "
          f"{'Gap':>5} | {'Grade':>5} | {'Brier':>7} | {'ECE':>7} | {'OK':>4}")
    print("-" * 110)
    for r in results:
        brier_str = f"{r['brier_score']:.3f}" if r['brier_score'] is not None else "  --"
        ece_str = f"{r['ece']:.3f}" if r['ece'] is not None else "  --"
        ok_str = "Y" if r['sample_sufficient'] else "N"
        print(f"{r['algorithm']:28s} | {r['asset_class']:7s} | {r['total_trades']:>5} | "
              f"{r['avg_signal_strength']:>4.0f}% | {r['win_rate_pct']:>4.1f}% | "
              f"{r['gap']:>5.1f} | {r['grade']:>5} | {brier_str:>7} | {ece_str:>7} | {ok_str:>4}")

    # --- Brier decomposition for top algorithms ---
    has_brier = [r for r in results if r['brier_score'] is not None]
    if has_brier:
        print(f"\n  Brier Decomposition (lower reliability = better calibrated):")
        print(f"  {'Algorithm':28s} | {'Brier':>7} | {'Reliab':>7} | {'Resol':>7} | {'Uncert':>7}")
        print(f"  {'-'*70}")
        for r in has_brier:
            bd = r['brier_decomposition']
            rel_str = f"{bd['reliability']:.4f}" if bd['reliability'] is not None else "  --"
            res_str = f"{bd['resolution']:.4f}" if bd['resolution'] is not None else "  --"
            unc_str = f"{bd['uncertainty']:.4f}" if bd['uncertainty'] is not None else "  --"
            print(f"  {r['algorithm']:28s} | {r['brier_score']:>7.4f} | {rel_str:>7} | "
                  f"{res_str:>7} | {unc_str:>7}")

    # --- ECE bucket detail for algorithms that have it ---
    has_ece = [r for r in results if r['ece_buckets']]
    if has_ece:
        print(f"\n  ECE Bucket Detail (first algorithm with data):")
        r = has_ece[0]
        print(f"  Algorithm: {r['algorithm']} (ECE = {r['ece']:.4f})")
        print(f"  {'Bucket':>10} | {'Count':>6} | {'Conf%':>6} | {'Acc%':>6} | {'Gap%':>6}")
        print(f"  {'-'*50}")
        for b in r['ece_buckets']:
            if b['avg_confidence'] is not None:
                print(f"  {b['bucket']:>10} | {b['count']:>6} | {b['avg_confidence']:>5.1f}% | "
                      f"{b['accuracy']:>5.1f}% | {b['gap']:>5.1f}%")
            else:
                print(f"  {b['bucket']:>10} | {b['count']:>6} |    --  |    --  |    -- ")

    json_path = save_results(results, min_samples)
    print(f"\nSaved: {json_path}")

    # --- Summary ---
    grades = [r['grade'] for r in results]
    print(f"\n  Grade distribution:")
    for g in ['A', 'B', 'C', 'D', 'F']:
        count = grades.count(g)
        if count > 0:
            print(f"    Grade {g}: {count} algorithm(s)")

    insufficient = [r for r in results if not r['sample_sufficient']]
    if insufficient:
        print(f"\n  WARNING: {len(insufficient)} algorithm(s) have INSUFFICIENT data (n < {min_samples}):")
        for r in insufficient:
            print(f"    ! {r['algorithm']}: n={r['total_trades']} — grade/Brier unreliable")


if __name__ == '__main__':
    main()
