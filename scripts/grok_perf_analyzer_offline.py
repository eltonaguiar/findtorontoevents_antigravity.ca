#!/usr/bin/env python3
"""
Offline Performance Analyzer — Ranks all algorithms from DB trade data.
No live API calls needed. Outputs ranked CSV + JSON for dashboard consumption.

Metrics (industry-standard):
  - Win Rate (%)
  - Expectancy per trade: (WR * avg_win) - (LR * avg_loss)
  - Profit Factor: gross_wins / gross_losses
  - Sortino Ratio: mean_return / downside_deviation (penalizes only bad vol)
  - Max Drawdown: worst peak-to-trough in cumulative PnL
  - Composite: z-score normalized blend of above metrics (commensurable)

Minimum trade filter: n >= 10 (below that, metrics are noise).

Usage:
  python grok_perf_analyzer_offline.py              # Analyze from DB
  python grok_perf_analyzer_offline.py --csv FILE   # Analyze from CSV export
  python grok_perf_analyzer_offline.py --min-n 20   # Override minimum trade count
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

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Minimum trades for reliable metrics (below this, metrics are noise)
MIN_TRADES_DEFAULT = 10

# Composite score weights (applied to z-scores, so units are commensurable)
COMPOSITE_WEIGHTS = {
    'expectancy': 0.30,     # Most actionable — dollars/trade edge
    'sortino': 0.25,        # Risk-adjusted return (downside-only vol)
    'profit_factor': 0.20,  # Gross win/loss ratio
    'win_rate': 0.15,       # Win frequency
    'max_dd': 0.10,         # Drawdown penalty (lower is worse)
}


def fetch_from_db():
    """Fetch closed trades from the lm_trades table."""
    import mysql.connector
    try:
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
    except mysql.connector.Error as err:
        print(f"DB Error: {err}")
        sys.exit(1)


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


def calc_sortino(returns, target=0.0):
    """
    Sortino Ratio — mean excess return / downside deviation.
    Only penalizes negative returns (unlike Sharpe which penalizes all volatility).
    Standard in institutional quant evaluation.
    """
    if not returns:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    downside = [min(0, r - target) ** 2 for r in returns]
    dd_variance = sum(downside) / len(downside)
    dd_std = math.sqrt(dd_variance)
    if dd_std == 0:
        return float('inf') if mean_ret > 0 else 0.0
    return mean_ret / dd_std


def calc_max_drawdown(pnl_series):
    """
    Max drawdown from cumulative PnL series (list of per-trade PnLs).
    Returns (max_dd_pct, max_dd_usd) as negative values.
    """
    if not pnl_series:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in pnl_series:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = cumulative - peak
        if dd < max_dd:
            max_dd = dd
    return max_dd


def calc_expectancy(win_rate, avg_win, avg_loss):
    """
    Expectancy per trade = (WR * avg_win) - (LR * avg_loss).
    This is the average expected dollar (or %) gain per trade.
    Positive = edge exists; negative = losing system.
    """
    loss_rate = 1 - win_rate
    return (win_rate * avg_win) - (loss_rate * avg_loss)


def z_score_normalize(values):
    """
    Normalize a list of values to z-scores (mean=0, std=1).
    Returns list of z-scores. If std=0, returns all zeros.
    """
    n = len(values)
    if n == 0:
        return []
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance)
    if std == 0:
        return [0.0] * n
    return [(v - mean) / std for v in values]


def analyze(trades, min_trades=MIN_TRADES_DEFAULT):
    """
    Analyze and rank algorithms by z-score normalized composite score.

    Metrics computed per algorithm:
      - Win rate (%)
      - Expectancy per trade (% and $)
      - Profit factor (gross wins / gross losses)
      - Sortino ratio (mean return / downside deviation)
      - Max drawdown (peak-to-trough in cumulative PnL)
      - Composite: weighted sum of z-scored metrics

    Algorithms with fewer than min_trades are excluded (unreliable metrics).
    """
    # --- Phase 1: Collect per-algo trade lists ---
    algo_trades = {}  # key -> list of trade dicts
    for t in trades:
        algo = t.get('algorithm_name', 'Unknown')
        asset = t.get('asset_class', 'unknown')
        key = f"{algo}|{asset}"
        if key not in algo_trades:
            algo_trades[key] = {'algorithm': algo, 'asset_class': asset, 'trades': []}
        pnl = float(t.get('realized_pnl_usd', 0))
        pct = float(t.get('realized_pct', 0))
        cap = float(t.get('position_value_usd', 0))
        algo_trades[key]['trades'].append({'pnl': pnl, 'pct': pct, 'cap': cap})

    # --- Phase 2: Compute per-algo metrics ---
    raw_results = []
    skipped = 0

    for key, group in algo_trades.items():
        tlist = group['trades']
        n = len(tlist)

        # Minimum trade filter — below this, all metrics are noise
        if n < min_trades:
            skipped += 1
            continue

        pnls = [t['pnl'] for t in tlist]
        pcts = [t['pct'] for t in tlist]

        wins = [t for t in tlist if t['pnl'] > 0]
        losses = [t for t in tlist if t['pnl'] <= 0]
        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / n

        avg_return = sum(pcts) / n
        avg_pnl = sum(pnls) / n

        # Avg win/loss (in %)
        avg_win_pct = sum(t['pct'] for t in wins) / n_wins if n_wins else 0
        avg_loss_pct = abs(sum(t['pct'] for t in losses) / n_losses) if n_losses else 0

        # Expectancy (% per trade)
        expectancy_pct = calc_expectancy(win_rate, avg_win_pct, avg_loss_pct)

        # Profit factor
        gross_wins = sum(t['pnl'] for t in wins)
        gross_losses = abs(sum(t['pnl'] for t in losses))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else float('inf')
        # Cap PF at 10 for z-scoring (inf breaks normalization)
        pf_capped = min(profit_factor, 10.0)

        # Sortino ratio (on % returns)
        sortino = calc_sortino(pcts)
        sortino_capped = min(sortino, 10.0)  # Cap for normalization

        # Max drawdown (on cumulative PnL in $)
        max_dd = calc_max_drawdown(pnls)

        # Max win/loss
        max_win_pct = max((t['pct'] for t in wins), default=0)
        max_loss_pct = min((t['pct'] for t in losses), default=0)

        raw_results.append({
            'algorithm': group['algorithm'],
            'asset_class': group['asset_class'],
            'total_trades': n,
            'wins': n_wins,
            'losses': n_losses,
            'win_rate_pct': round(win_rate * 100, 2),
            'avg_return_pct': round(avg_return, 2),
            'avg_pnl_usd': round(avg_pnl, 2),
            'total_pnl_usd': round(sum(pnls), 2),
            'expectancy_pct': round(expectancy_pct, 3),
            'profit_factor': round(profit_factor, 3),
            'sortino_ratio': round(sortino, 3),
            'max_drawdown_usd': round(max_dd, 2),
            'max_win_pct': round(max_win_pct, 2),
            'max_loss_pct': round(max_loss_pct, 2),
            # Raw values for z-scoring (capped to prevent inf)
            '_wr': win_rate * 100,
            '_exp': expectancy_pct,
            '_pf': pf_capped,
            '_sortino': sortino_capped,
            '_dd': max_dd,  # Negative; higher (less negative) is better
        })

    if skipped > 0:
        print(f"  Filtered out {skipped} algorithm(s) with fewer than {min_trades} trades")

    if not raw_results:
        return []

    # --- Phase 3: Z-score normalization for composite ---
    n_algos = len(raw_results)

    wr_z = z_score_normalize([r['_wr'] for r in raw_results])
    exp_z = z_score_normalize([r['_exp'] for r in raw_results])
    pf_z = z_score_normalize([r['_pf'] for r in raw_results])
    sort_z = z_score_normalize([r['_sortino'] for r in raw_results])
    dd_z = z_score_normalize([r['_dd'] for r in raw_results])  # Higher = less drawdown = better

    for i, r in enumerate(raw_results):
        composite = (
            COMPOSITE_WEIGHTS['win_rate'] * wr_z[i] +
            COMPOSITE_WEIGHTS['expectancy'] * exp_z[i] +
            COMPOSITE_WEIGHTS['profit_factor'] * pf_z[i] +
            COMPOSITE_WEIGHTS['sortino'] * sort_z[i] +
            COMPOSITE_WEIGHTS['max_dd'] * dd_z[i]
        )
        r['composite_score'] = round(composite, 4)
        r['z_scores'] = {
            'win_rate': round(wr_z[i], 3),
            'expectancy': round(exp_z[i], 3),
            'profit_factor': round(pf_z[i], 3),
            'sortino': round(sort_z[i], 3),
            'max_dd': round(dd_z[i], 3),
        }
        # Remove internal fields
        for k in ('_wr', '_exp', '_pf', '_sortino', '_dd'):
            del r[k]

    # --- Phase 4: Rank ---
    raw_results.sort(key=lambda x: x['composite_score'], reverse=True)
    for i, r in enumerate(raw_results):
        r['rank'] = i + 1

    return raw_results


def save_results(results, min_trades):
    """Save to JSON and CSV with methodology metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    # Strip z_scores from CSV (nested dicts don't CSV well)
    csv_results = []
    for r in results:
        flat = {k: v for k, v in r.items() if k != 'z_scores'}
        if 'z_scores' in r:
            for zk, zv in r['z_scores'].items():
                flat[f'z_{zk}'] = zv
        csv_results.append(flat)

    json_path = os.path.join(OUTPUT_DIR, 'algo_rankings.json')
    with open(json_path, 'w') as f:
        json.dump({
            'generated': ts,
            'methodology': {
                'min_trades': min_trades,
                'composite_weights': COMPOSITE_WEIGHTS,
                'normalization': 'z-score (mean=0, std=1) per metric',
                'metrics': [
                    'expectancy_pct: (WR * avg_win) - (LR * avg_loss) — edge per trade',
                    'sortino_ratio: mean_return / downside_deviation — risk-adjusted',
                    'profit_factor: gross_wins / gross_losses',
                    'win_rate_pct: fraction of winning trades',
                    'max_drawdown_usd: worst peak-to-trough in cumulative PnL',
                ],
            },
            'total_algorithms': len(results),
            'rankings': results
        }, f, indent=2)

    csv_path = os.path.join(OUTPUT_DIR, f'algo_rankings_{ts}.csv')
    if csv_results:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_results[0].keys())
            writer.writeheader()
            writer.writerows(csv_results)

    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description='Offline Performance Analyzer')
    parser.add_argument('--csv', help='Path to CSV trade export (skip DB)')
    parser.add_argument('--min-n', type=int, default=MIN_TRADES_DEFAULT,
                        help=f'Minimum trades to include algorithm (default {MIN_TRADES_DEFAULT})')
    args = parser.parse_args()

    min_trades = args.min_n

    print("=== Offline Performance Analyzer (z-score composite) ===")
    print(f"Min trades: {min_trades} | Composite weights: {COMPOSITE_WEIGHTS}")

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

    results = analyze(trades, min_trades)

    if not results:
        print("No algorithms met the minimum trade threshold.")
        return

    # --- Main table ---
    print(f"\n{'Rk':>3} | {'Algorithm':28s} | {'Asset':7s} | {'N':>5} | {'WR%':>6} | {'Exp%':>7} | "
          f"{'PF':>6} | {'Sorti':>6} | {'MaxDD$':>8} | {'Score':>7}")
    print("-" * 115)
    for r in results:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "INF"
        sort_str = f"{r['sortino_ratio']:.2f}" if r['sortino_ratio'] < 100 else "INF"
        print(f"{r['rank']:>3} | {r['algorithm']:28s} | {r['asset_class']:7s} | {r['total_trades']:>5} | "
              f"{r['win_rate_pct']:>5.1f}% | {r['expectancy_pct']:>6.2f}% | "
              f"{pf_str:>6} | {sort_str:>6} | ${r['max_drawdown_usd']:>7.0f} | "
              f"{r['composite_score']:>+7.3f}")

    # --- Z-score breakdown for top 5 ---
    top_n = min(5, len(results))
    print(f"\n  Z-Score Breakdown (top {top_n}):")
    print(f"  {'Algorithm':28s} | {'z_WR':>6} | {'z_Exp':>6} | {'z_PF':>6} | {'z_Sort':>6} | {'z_DD':>6}")
    print(f"  {'-'*75}")
    for r in results[:top_n]:
        z = r['z_scores']
        print(f"  {r['algorithm']:28s} | {z['win_rate']:>+6.2f} | {z['expectancy']:>+6.2f} | "
              f"{z['profit_factor']:>+6.2f} | {z['sortino']:>+6.2f} | {z['max_dd']:>+6.2f}")

    json_path, csv_path = save_results(results, min_trades)
    print(f"\nSaved: {json_path}")
    print(f"Saved: {csv_path}")


if __name__ == '__main__':
    main()
