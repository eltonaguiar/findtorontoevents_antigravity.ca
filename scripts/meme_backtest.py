#!/usr/bin/env python3
"""
Meme Coin Backtest Framework -- Replays historical mc_scan_log entries
to calibrate the BUY NOW threshold and evaluate signal quality.

What it does:
  1. Reads all resolved signals from mc_winners
  2. For each signal, computes what the BUY NOW rank would have been
  3. Measures precision/recall at different BUY NOW thresholds
  4. Outputs the optimal threshold for maximizing win rate
  5. Compares rule-based scores vs BUY NOW composite ranking

Usage:
  python scripts/meme_backtest.py
  python scripts/meme_backtest.py --threshold 70
  python scripts/meme_backtest.py --output results/meme_backtest.json

Requires: pip install mysql-connector-python
"""
import os
import sys
import json
import math
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MEME_DB_HOST = os.getenv('MEME_DB_HOST', 'mysql.50webs.com')
MEME_DB_USER = os.getenv('MEME_DB_USER', 'ejaguiar1_memecoin')
MEME_DB_PASS = os.getenv('MEME_DB_PASS', 'testing123')
MEME_DB_NAME = os.getenv('MEME_DB_NAME', 'ejaguiar1_memecoin')


def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host=MEME_DB_HOST,
        user=MEME_DB_USER,
        password=MEME_DB_PASS,
        database=MEME_DB_NAME,
        connect_timeout=15,
    )


def extract_factor_score(factors, key):
    if not factors:
        return 0
    f = factors.get(key)
    if f is None:
        return 0
    if isinstance(f, dict):
        return f.get('score', 0)
    if isinstance(f, (int, float)):
        return f
    return 0


def compute_buy_now_rank(signal, age_minutes=5):
    """
    Compute BUY NOW composite rank for a historical signal.
    Mirrors the frontend computeBuyNowRank() logic.
    """
    base_score = int(signal.get('score', 0))
    target_pct = float(signal.get('target_pct', 0))
    risk_pct = float(signal.get('risk_pct', 0))

    # Freshness penalty: -2 per minute, max -30
    freshness_penalty = min(30, age_minutes * 2)

    # R:R bonus (max +10)
    rr_ratio = target_pct / risk_pct if risk_pct > 0 else 0
    rr_bonus = min(10, int(rr_ratio * 3))

    # Regime adjustment from factors
    factors = signal.get('factors_parsed', {})
    btc = factors.get('btc_regime', {})
    regime_adj = int(btc.get('adjustment', 0)) if isinstance(btc, dict) else 0

    # Quality gate bonus
    qc = factors.get('quality_check', {})
    qscore = qc.get('score', 0) if isinstance(qc, dict) else 0
    quality_bonus = 5 if qscore >= 3 else (2 if qscore >= 2 else 0)

    rank = base_score - freshness_penalty + rr_bonus + regime_adj + quality_bonus
    return max(0, min(100, rank))


def main():
    parser = argparse.ArgumentParser(description='Meme Coin Backtest Framework')
    parser.add_argument('--threshold', type=int, default=None,
                        help='Test a specific BUY NOW threshold')
    parser.add_argument('--output', type=str, default=None,
                        help='Save results to JSON file')
    parser.add_argument('--age-minutes', type=int, default=5,
                        help='Assumed signal age for BUY NOW rank (default 5)')
    args = parser.parse_args()

    print("=" * 60)
    print("  MEME COIN BACKTEST FRAMEWORK")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch all resolved signals
    cursor.execute("""
        SELECT id, pair, score, factors_json, verdict, target_pct, risk_pct,
               pnl_pct, outcome, tier, vol_usd_24h, chg_24h, created_at
        FROM mc_winners
        WHERE outcome IS NOT NULL
        AND factors_json IS NOT NULL
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"\n  Loaded {len(rows)} resolved signals")

    if len(rows) < 5:
        print("  Insufficient data for backtest. Need at least 5 resolved signals.")
        sys.exit(0)

    # Parse factors and compute BUY NOW rank for each
    for r in rows:
        fj = r.get('factors_json', '{}')
        if isinstance(fj, str):
            try:
                r['factors_parsed'] = json.loads(fj)
            except Exception:
                r['factors_parsed'] = {}
        else:
            r['factors_parsed'] = fj if isinstance(fj, dict) else {}

        r['buy_now_rank'] = compute_buy_now_rank(r, age_minutes=args.age_minutes)
        r['is_win'] = r.get('outcome') in ('win', 'partial_win')

    # Baseline: All signals
    total = len(rows)
    wins = sum(1 for r in rows if r['is_win'])
    losses = total - wins
    baseline_wr = wins / total * 100 if total > 0 else 0

    print(f"\n  Baseline: {wins}W / {losses}L = {baseline_wr:.1f}% WR")

    # Test different BUY NOW thresholds
    print(f"\n  {'Threshold':>10} {'Signals':>8} {'Wins':>6} {'Losses':>6} {'WR%':>8} {'Precision':>10} {'Recall':>8} {'F1':>8}")
    print("  " + "-" * 72)

    results = []
    thresholds_to_test = list(range(40, 95, 5))
    if args.threshold and args.threshold not in thresholds_to_test:
        thresholds_to_test.append(args.threshold)
        thresholds_to_test.sort()

    for threshold in thresholds_to_test:
        selected = [r for r in rows if r['buy_now_rank'] >= threshold]
        n = len(selected)
        w = sum(1 for r in selected if r['is_win'])
        l = n - w
        wr = w / n * 100 if n > 0 else 0

        # Precision: of those we selected, how many won?
        precision = w / n if n > 0 else 0
        # Recall: of all wins, how many did we select?
        recall = w / wins if wins > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        marker = ' <---' if threshold == 70 else ''
        print(f"  {threshold:>10} {n:>8} {w:>6} {l:>6} {wr:>7.1f}% {precision:>9.3f} {recall:>7.3f} {f1:>7.3f}{marker}")

        results.append({
            'threshold': threshold,
            'signals': n,
            'wins': w,
            'losses': l,
            'win_rate': round(wr, 1),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1': round(f1, 4),
        })

    # Also test by rule-based score (original)
    print(f"\n  --- By Original Score (for comparison) ---")
    print(f"  {'Score>=':>10} {'Signals':>8} {'Wins':>6} {'Losses':>6} {'WR%':>8}")
    print("  " + "-" * 42)

    for score_thresh in [70, 75, 78, 80, 85, 90]:
        sel = [r for r in rows if int(r.get('score', 0)) >= score_thresh]
        n = len(sel)
        w = sum(1 for r in sel if r['is_win'])
        l = n - w
        wr = w / n * 100 if n > 0 else 0
        print(f"  {score_thresh:>10} {n:>8} {w:>6} {l:>6} {wr:>7.1f}%")

    # Find optimal threshold
    best = max(results, key=lambda x: x['f1']) if results else None
    if best:
        print(f"\n  OPTIMAL BUY NOW THRESHOLD: {best['threshold']}")
        print(f"    F1: {best['f1']:.4f} | WR: {best['win_rate']}% | "
              f"Precision: {best['precision']:.3f} | Recall: {best['recall']:.3f}")
        print(f"    Would select {best['signals']}/{total} signals "
              f"({best['signals'] / total * 100:.0f}%)")

    # By-verdict analysis
    print(f"\n  --- By Verdict ---")
    verdict_groups = defaultdict(list)
    for r in rows:
        verdict_groups[r.get('verdict', 'UNKNOWN')].append(r)

    for verdict in ['STRONG_BUY', 'BUY', 'LEAN_BUY']:
        group = verdict_groups.get(verdict, [])
        n = len(group)
        w = sum(1 for r in group if r['is_win'])
        wr = w / n * 100 if n > 0 else 0
        avg_rank = sum(r['buy_now_rank'] for r in group) / n if n > 0 else 0
        avg_pnl = sum(float(r.get('pnl_pct', 0) or 0) for r in group) / n if n > 0 else 0
        print(f"  {verdict:15s}  {n:>4} signals  WR: {wr:>5.1f}%  "
              f"Avg BN rank: {avg_rank:.0f}  Avg PnL: {avg_pnl:+.2f}%")

    # By-tier analysis
    print(f"\n  --- By Tier ---")
    for tier in ['tier1', 'tier2']:
        group = [r for r in rows if r.get('tier') == tier]
        n = len(group)
        w = sum(1 for r in group if r['is_win'])
        wr = w / n * 100 if n > 0 else 0
        print(f"  {tier:15s}  {n:>4} signals  WR: {wr:>5.1f}%")

    # Save results
    if args.output:
        output_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_signals': total,
            'baseline_win_rate': round(baseline_wr, 1),
            'assumed_age_minutes': args.age_minutes,
            'threshold_results': results,
            'optimal_threshold': best['threshold'] if best else 70,
            'optimal_f1': best['f1'] if best else 0,
        }
        os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n  Results saved to {args.output}")

    print("\n" + "=" * 60)
    print("  BACKTEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
