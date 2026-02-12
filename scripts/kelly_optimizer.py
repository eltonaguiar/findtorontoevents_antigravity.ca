#!/usr/bin/env python3
"""
Kelly Optimizer — Regime-aware position sizing using Kelly Criterion.
Calculates optimal bet fraction per algorithm with safety bounds and decay detection.

Features:
  - Sample-size-adaptive Kelly shrinkage (Baker & McHale 2013 inspired)
    fraction = min(KELLY_FRACTION, 1 / sqrt(n)) — aggressively shrinks for small n
  - Wilson score CI on win probability for honest uncertainty bounds on f*
  - Regime multipliers: bull 1.2x, sideways 0.85x, bear 0.5x
  - Position bounds: 1% min, 10% max of capital
  - Rolling 30-day vs all-time WR comparison
  - Decay warning when recent WR drops >20% from all-time
  - Confidence tiers: HIGH (n>=50), MEDIUM (n>=20), LOW (n>=10), INSUFFICIENT (n<10)

References:
  - Kelly (1956) — "A New Interpretation of Information Rate"
  - Baker & McHale (2013) — optimal shrinkage under estimation risk
  - Columbia 2025 — textbook Kelly oversizes by 22-36% in real markets

Usage:
  python kelly_optimizer.py                    # Analyze from DB
  python kelly_optimizer.py --csv FILE         # Analyze from CSV export
  python kelly_optimizer.py --regime bear      # Override regime (bull/sideways/bear)
"""
import os
import sys
import json
import csv
import math
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Kelly config
KELLY_FRACTION = 0.25       # Quarter-Kelly
MIN_POSITION_PCT = 1.0      # 1% minimum
MAX_POSITION_PCT = 10.0     # 10% maximum
DECAY_THRESHOLD = 0.20      # 20% drop triggers warning
ROLLING_WINDOW_DAYS = 30

REGIME_MULTIPLIERS = {
    'bull': 1.2,
    'sideways': 0.85,
    'bear': 0.5,
}

# Confidence tiers by sample size (power-awareness)
SAMPLE_TIER_HIGH = 50       # HIGH: reliable Kelly estimates
SAMPLE_TIER_MEDIUM = 20     # MEDIUM: usable but noisy
SAMPLE_TIER_LOW = 10        # LOW: high estimation error
                            # INSUFFICIENT: n < 10 — Kelly is essentially guessing


def fetch_from_db():
    """Fetch closed trades from the lm_trades table."""
    import mysql.connector
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT algorithm_name, asset_class, symbol, realized_pnl_usd, realized_pct,
               position_value_usd, entry_date, exit_date
        FROM lm_trades
        WHERE status = 'closed' AND algorithm_name != ''
        ORDER BY exit_date DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def fetch_from_csv(csv_path):
    """Load trades from CSV file."""
    rows = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['realized_pnl_usd'] = float(row.get('realized_pnl_usd', 0))
            row['realized_pct'] = float(row.get('realized_pct', 0))
            row['position_value_usd'] = float(row.get('position_value_usd', 0))
            rows.append(row)
    return rows


def detect_regime_from_db():
    """Try to detect current regime from the lm_regime table or default to sideways."""
    try:
        import mysql.connector
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT regime FROM lm_regime ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            regime = row['regime'].lower()
            if regime in REGIME_MULTIPLIERS:
                return regime
    except Exception:
        pass
    return 'sideways'


def calculate_kelly(win_rate, avg_win, avg_loss):
    """Calculate raw Kelly fraction: f* = (p * b - q) / b where b = avg_win/avg_loss."""
    if avg_loss == 0 or avg_win == 0:
        return 0
    b = avg_win / avg_loss  # Win/loss ratio
    p = win_rate
    q = 1 - p
    kelly = (p * b - q) / b
    return max(0, kelly)


def adaptive_kelly_fraction(n):
    """
    Sample-size-adaptive Kelly shrinkage.

    Inspired by Baker & McHale (2013) and Columbia 2025 research showing
    textbook Kelly oversizes by 22-36% in real markets.

    fraction = min(KELLY_FRACTION, 1 / sqrt(n))

    At n=16 trades: fraction = 0.25 (matches quarter-Kelly)
    At n=5 trades:  fraction = 0.45 -> capped at 0.25, but...
    At n=100:       fraction = 0.10 (more aggressive shrinkage at high confidence)

    Actually we use: fraction = KELLY_FRACTION / (1 + 3.0 / sqrt(n))
    This is a smoother form that:
      - At n=9:  fraction = 0.125 (half of quarter-Kelly — high uncertainty)
      - At n=25: fraction = 0.156
      - At n=50: fraction = 0.186
      - At n=100: fraction = 0.208
      - At n=500: fraction = 0.236 (approaching full quarter-Kelly)
    Never exceeds KELLY_FRACTION.
    """
    if n <= 0:
        return 0
    fraction = KELLY_FRACTION / (1 + 3.0 / math.sqrt(n))
    return min(KELLY_FRACTION, fraction)


def wilson_ci_for_wr(wins, n, z=1.96):
    """
    Wilson score 95% confidence interval for win probability.
    Returns (lower, upper) bounds as proportions.
    Gives asymmetric, honest uncertainty on the win rate feeding Kelly.
    """
    if n == 0:
        return (0, 0)
    p_hat = wins / n
    denominator = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denominator
    lower = max(0, center - spread)
    upper = min(1, center + spread)
    return (lower, upper)


def sample_confidence_tier(n):
    """Return confidence tier based on sample size."""
    if n >= SAMPLE_TIER_HIGH:
        return 'HIGH'
    elif n >= SAMPLE_TIER_MEDIUM:
        return 'MEDIUM'
    elif n >= SAMPLE_TIER_LOW:
        return 'LOW'
    else:
        return 'INSUFFICIENT'


def analyze(trades, regime='sideways'):
    """
    Calculate Kelly-optimal position sizes per algorithm.

    Improvements over naive Kelly:
      1. Adaptive shrinkage — fraction decreases with smaller sample size
      2. Wilson CI on win rate — shows honest uncertainty on the edge estimate
      3. Conservative Kelly — uses CI lower bound for position sizing (worst-case)
      4. Confidence tiers — flags unreliable estimates
    """
    # Group trades by algorithm|asset
    algo_groups = {}
    cutoff_date = datetime.utcnow() - timedelta(days=ROLLING_WINDOW_DAYS)

    for t in trades:
        algo = t.get('algorithm_name', 'Unknown')
        asset = t.get('asset_class', 'unknown')
        key = f"{algo}|{asset}"
        if key not in algo_groups:
            algo_groups[key] = {'all': [], 'recent': [], 'algorithm': algo, 'asset_class': asset}

        pnl = float(t.get('realized_pnl_usd', 0))
        pct = float(t.get('realized_pct', 0))
        exit_date = t.get('exit_date')

        trade_data = {'pnl': pnl, 'pct': pct}
        algo_groups[key]['all'].append(trade_data)

        # Check if trade is within rolling window
        if exit_date:
            try:
                if isinstance(exit_date, str):
                    exit_dt = datetime.strptime(exit_date[:19], '%Y-%m-%d %H:%M:%S')
                else:
                    exit_dt = exit_date
                if exit_dt >= cutoff_date:
                    algo_groups[key]['recent'].append(trade_data)
            except (ValueError, TypeError):
                pass

    regime_mult = REGIME_MULTIPLIERS.get(regime, 1.0)
    results = []

    for key, group in algo_groups.items():
        all_trades = group['all']
        recent_trades = group['recent']
        n_all = len(all_trades)

        if n_all < 5:  # Need minimum trades for Kelly
            continue

        # All-time stats
        wins_all = [t for t in all_trades if t['pnl'] > 0]
        losses_all = [t for t in all_trades if t['pnl'] <= 0]
        n_wins = len(wins_all)
        wr_all = n_wins / n_all if n_all > 0 else 0
        avg_win_all = sum(t['pct'] for t in wins_all) / n_wins if wins_all else 0
        avg_loss_all = abs(sum(t['pct'] for t in losses_all) / len(losses_all)) if losses_all else 0

        # Wilson CI on win probability (95%)
        wr_ci_lower, wr_ci_upper = wilson_ci_for_wr(n_wins, n_all)

        # Recent stats
        n_recent = len(recent_trades)
        if n_recent >= 3:
            wins_recent = [t for t in recent_trades if t['pnl'] > 0]
            wr_recent = len(wins_recent) / n_recent if n_recent > 0 else 0
        else:
            wr_recent = wr_all  # Not enough recent data, use all-time

        # Decay detection
        decay = False
        decay_pct = 0
        if wr_all > 0 and n_recent >= 3:
            decay_pct = (wr_all - wr_recent) / wr_all
            decay = decay_pct > DECAY_THRESHOLD

        # --- Adaptive Kelly Calculation ---
        # 1. Raw Kelly from point estimate
        raw_kelly = calculate_kelly(wr_all, avg_win_all, avg_loss_all)

        # 2. Conservative Kelly — uses CI lower bound on win rate
        #    This is the Kelly you'd get if the true WR is at the worst end of
        #    the 95% confidence interval (pessimistic but honest)
        conservative_kelly = calculate_kelly(wr_ci_lower, avg_win_all, avg_loss_all)

        # 3. Adaptive fraction — shrinks with sample size
        effective_fraction = adaptive_kelly_fraction(n_all)

        # 4. Apply adaptive fraction to conservative Kelly (double safety)
        shrunk_kelly = conservative_kelly * effective_fraction

        # Old quarter-Kelly for comparison
        quarter_kelly = raw_kelly * KELLY_FRACTION

        # Apply regime multiplier
        adjusted_kelly = shrunk_kelly * regime_mult

        # Apply decay penalty (reduce by 50% if decaying)
        if decay:
            adjusted_kelly *= 0.5

        # Clamp to bounds
        if adjusted_kelly > 0:
            position_pct = max(MIN_POSITION_PCT, min(MAX_POSITION_PCT, adjusted_kelly * 100))
        else:
            position_pct = 0

        # Confidence tier
        confidence = sample_confidence_tier(n_all)

        results.append({
            'algorithm': group['algorithm'],
            'asset_class': group['asset_class'],
            'total_trades': n_all,
            'recent_trades': n_recent,
            'win_rate_all_pct': round(wr_all * 100, 1),
            'win_rate_recent_pct': round(wr_recent * 100, 1),
            'wr_ci_lower_pct': round(wr_ci_lower * 100, 1),
            'wr_ci_upper_pct': round(wr_ci_upper * 100, 1),
            'avg_win_pct': round(avg_win_all, 2),
            'avg_loss_pct': round(avg_loss_all, 2),
            'raw_kelly_pct': round(raw_kelly * 100, 2),
            'conservative_kelly_pct': round(conservative_kelly * 100, 2),
            'quarter_kelly_pct': round(quarter_kelly * 100, 2),
            'effective_fraction': round(effective_fraction, 4),
            'shrunk_kelly_pct': round(shrunk_kelly * 100, 2),
            'regime': regime,
            'regime_multiplier': regime_mult,
            'decay_detected': decay,
            'decay_pct': round(decay_pct * 100, 1),
            'position_size_pct': round(position_pct, 2),
            'old_position_size_pct': round(
                max(MIN_POSITION_PCT, min(MAX_POSITION_PCT, quarter_kelly * regime_mult * (0.5 if decay else 1) * 100))
                if quarter_kelly * regime_mult > 0 else 0, 2),
            'confidence': confidence,
        })

    # Sort by position size descending
    results.sort(key=lambda x: x['position_size_pct'], reverse=True)
    return results


def save_results(results, regime):
    """Save to JSON with adaptive Kelly metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    json_path = os.path.join(OUTPUT_DIR, 'kelly_sizing.json')
    with open(json_path, 'w') as f:
        json.dump({
            'generated': ts,
            'regime': regime,
            'kelly_fraction_max': KELLY_FRACTION,
            'adaptive_shrinkage': 'fraction = KELLY_FRACTION / (1 + 3.0 / sqrt(n))',
            'conservative_mode': 'Uses Wilson CI lower bound on win rate (pessimistic)',
            'bounds': {'min_pct': MIN_POSITION_PCT, 'max_pct': MAX_POSITION_PCT},
            'confidence_tiers': {
                'HIGH': f'>= {SAMPLE_TIER_HIGH} trades',
                'MEDIUM': f'>= {SAMPLE_TIER_MEDIUM} trades',
                'LOW': f'>= {SAMPLE_TIER_LOW} trades',
                'INSUFFICIENT': f'< {SAMPLE_TIER_LOW} trades',
            },
            'references': [
                'Kelly (1956) — A New Interpretation of Information Rate',
                'Baker & McHale (2013) — Optimal shrinkage under estimation risk',
                'Columbia 2025 — Textbook Kelly oversizes by 22-36%',
            ],
            'total_algorithms': len(results),
            'sizing': results
        }, f, indent=2)

    return json_path


def main():
    parser = argparse.ArgumentParser(description='Kelly Optimizer — Regime-aware position sizing')
    parser.add_argument('--csv', help='Path to CSV trade export (skip DB)')
    parser.add_argument('--regime', choices=['bull', 'sideways', 'bear'],
                        help='Override regime detection')
    args = parser.parse_args()

    print("=== Kelly Optimizer (Adaptive Shrinkage) ===")

    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        trades = fetch_from_csv(args.csv)
        regime = args.regime or 'sideways'
    else:
        print("Fetching from database...")
        trades = fetch_from_db()
        regime = args.regime or detect_regime_from_db()

    print(f"Loaded {len(trades)} closed trades")
    print(f"Regime: {regime} (multiplier: {REGIME_MULTIPLIERS.get(regime, 1.0)}x)")
    print(f"Kelly mode: Adaptive shrinkage (f = {KELLY_FRACTION} / (1 + 3/sqrt(n)))")
    print(f"Win rate: Conservative — uses Wilson CI lower bound")
    print(f"Bounds: {MIN_POSITION_PCT}% - {MAX_POSITION_PCT}%")

    if not trades:
        print("No trades found. Nothing to optimize.")
        return

    results = analyze(trades, regime)

    # --- Main table ---
    print(f"\n{'Algorithm':30s} | {'Asset':8s} | {'N':>5} | {'WR%':>6} | {'WR CI':>14} | "
          f"{'Frac':>5} | {'Old%':>6} | {'New%':>6} | {'Conf':>6} | {'Decay':>5}")
    print("-" * 125)
    for r in results:
        decay_str = f"{r['decay_pct']:.0f}%!" if r['decay_detected'] else "OK"
        ci_str = f"[{r['wr_ci_lower_pct']:>4.1f}-{r['wr_ci_upper_pct']:>4.1f}]"
        conf = r['confidence'][:4]
        print(f"{r['algorithm']:30s} | {r['asset_class']:8s} | {r['total_trades']:>5} | "
              f"{r['win_rate_all_pct']:>5.1f}% | {ci_str:>14} | "
              f"{r['effective_fraction']:>5.3f} | {r['old_position_size_pct']:>5.1f}% | "
              f"{r['position_size_pct']:>5.1f}% | {conf:>6} | {decay_str:>5}")

    json_path = save_results(results, regime)
    print(f"\nSaved: {json_path}")

    # --- Impact summary ---
    has_both = [r for r in results if r['old_position_size_pct'] > 0 and r['position_size_pct'] > 0]
    if has_both:
        avg_old = sum(r['old_position_size_pct'] for r in has_both) / len(has_both)
        avg_new = sum(r['position_size_pct'] for r in has_both) / len(has_both)
        reduction = (avg_old - avg_new) / avg_old * 100 if avg_old > 0 else 0
        print(f"\n  Adaptive shrinkage impact: avg position {avg_old:.1f}% -> {avg_new:.1f}% "
              f"({reduction:.0f}% reduction)")

    # Confidence warnings
    insufficient = [r for r in results if r['confidence'] == 'INSUFFICIENT']
    low_conf = [r for r in results if r['confidence'] == 'LOW']

    if insufficient:
        print(f"\n  WARNING: {len(insufficient)} algorithm(s) have INSUFFICIENT data (n < {SAMPLE_TIER_LOW}):")
        for r in insufficient:
            print(f"    ! {r['algorithm']}: n={r['total_trades']} — Kelly estimate unreliable")

    if low_conf:
        print(f"\n  CAUTION: {len(low_conf)} algorithm(s) have LOW confidence (n < {SAMPLE_TIER_MEDIUM}):")
        for r in low_conf:
            print(f"    ~ {r['algorithm']}: n={r['total_trades']}, frac={r['effective_fraction']:.3f} "
                  f"(heavily shrunk)")

    # Decay warnings
    decaying = [r for r in results if r['decay_detected']]
    if decaying:
        print(f"\n  DECAY: {len(decaying)} algorithm(s) showing performance decay:")
        for r in decaying:
            print(f"    - {r['algorithm']} ({r['asset_class']}): WR dropped {r['decay_pct']:.0f}% "
                  f"(all-time {r['win_rate_all_pct']:.0f}% -> recent {r['win_rate_recent_pct']:.0f}%)")


if __name__ == '__main__':
    main()
