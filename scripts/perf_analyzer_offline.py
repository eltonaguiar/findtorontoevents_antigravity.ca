#!/usr/bin/env python3
"""
Offline Performance Analyzer — Ranks all algorithms from DB trade data.
No live API calls needed. Outputs ranked CSV + JSON for dashboard consumption.

Usage:
  python perf_analyzer_offline.py              # Analyze from DB
  python perf_analyzer_offline.py --csv FILE   # Analyze from CSV export
"""
import os
import sys
import json
import csv
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')


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


def analyze(trades):
    """Analyze and rank algorithms by composite score."""
    algo_stats = {}

    for t in trades:
        algo = t.get('algorithm_name', 'Unknown')
        asset = t.get('asset_class', 'unknown')
        key = f"{algo}|{asset}"

        if key not in algo_stats:
            algo_stats[key] = {
                'algorithm': algo,
                'asset_class': asset,
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0.0,
                'total_pct': 0.0,
                'max_win_pct': 0.0,
                'max_loss_pct': 0.0,
                'total_capital_deployed': 0.0,
            }

        s = algo_stats[key]
        s['total_trades'] += 1
        pnl = float(t.get('realized_pnl_usd', 0))
        pct = float(t.get('realized_pct', 0))
        cap = float(t.get('position_value_usd', 0))

        s['total_pnl'] += pnl
        s['total_pct'] += pct
        s['total_capital_deployed'] += cap

        if pnl > 0:
            s['wins'] += 1
            s['max_win_pct'] = max(s['max_win_pct'], pct)
        else:
            s['losses'] += 1
            s['max_loss_pct'] = min(s['max_loss_pct'], pct)

    # Calculate derived metrics and rank
    results = []
    for key, s in algo_stats.items():
        n = s['total_trades']
        if n == 0:
            continue

        win_rate = s['wins'] / n * 100
        avg_return = s['total_pct'] / n
        avg_pnl = s['total_pnl'] / n

        # Profit factor
        total_wins = sum(float(t.get('realized_pnl_usd', 0)) for t in trades
                         if f"{t.get('algorithm_name')}|{t.get('asset_class')}" == key
                         and float(t.get('realized_pnl_usd', 0)) > 0)
        total_losses = abs(sum(float(t.get('realized_pnl_usd', 0)) for t in trades
                               if f"{t.get('algorithm_name')}|{t.get('asset_class')}" == key
                               and float(t.get('realized_pnl_usd', 0)) <= 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Composite score: (win_rate * 0.4) + (avg_return * 0.3) + (profit_factor * 10 * 0.3)
        composite = (win_rate * 0.4) + (avg_return * 0.3) + (min(profit_factor, 5) * 10 * 0.3)

        results.append({
            'rank': 0,
            'algorithm': s['algorithm'],
            'asset_class': s['asset_class'],
            'total_trades': n,
            'wins': s['wins'],
            'losses': s['losses'],
            'win_rate_pct': round(win_rate, 2),
            'avg_return_pct': round(avg_return, 2),
            'avg_pnl_usd': round(avg_pnl, 2),
            'total_pnl_usd': round(s['total_pnl'], 2),
            'profit_factor': round(profit_factor, 3),
            'max_win_pct': round(s['max_win_pct'], 2),
            'max_loss_pct': round(s['max_loss_pct'], 2),
            'composite_score': round(composite, 2),
        })

    # Sort by composite score descending
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    for i, r in enumerate(results):
        r['rank'] = i + 1

    return results


def save_results(results):
    """Save to JSON and CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    json_path = os.path.join(OUTPUT_DIR, 'algo_rankings.json')
    with open(json_path, 'w') as f:
        json.dump({
            'generated': ts,
            'total_algorithms': len(results),
            'rankings': results
        }, f, indent=2)

    csv_path = os.path.join(OUTPUT_DIR, f'algo_rankings_{ts}.csv')
    if results:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description='Offline Performance Analyzer')
    parser.add_argument('--csv', help='Path to CSV trade export (skip DB)')
    args = parser.parse_args()

    print("=== Offline Performance Analyzer ===")

    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        trades = fetch_from_csv(args.csv)
    else:
        print("Fetching from database...")
        trades = fetch_from_db()

    print(f"Loaded {len(trades)} closed trades")

    if not trades:
        print("No trades found. Nothing to analyze.")
        return

    results = analyze(trades)

    print(f"\n{'Rank':>4} | {'Algorithm':30s} | {'Asset':8s} | {'Trades':>6} | {'WR%':>6} | {'AvgRet%':>8} | {'PnL$':>10} | {'PF':>6} | {'Score':>7}")
    print("-" * 105)
    for r in results:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "INF"
        print(f"{r['rank']:>4} | {r['algorithm']:30s} | {r['asset_class']:8s} | {r['total_trades']:>6} | "
              f"{r['win_rate_pct']:>5.1f}% | {r['avg_return_pct']:>7.2f}% | ${r['total_pnl_usd']:>9.2f} | "
              f"{pf_str:>6} | {r['composite_score']:>7.2f}")

    json_path, csv_path = save_results(results)
    print(f"\nSaved: {json_path}")
    print(f"Saved: {csv_path}")


if __name__ == '__main__':
    main()
