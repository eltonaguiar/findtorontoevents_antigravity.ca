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
    'expectancy': 0.25,     # Most actionable — dollars/trade edge
    'sharpe': 0.20,         # Industry-standard risk-adjusted return (annualized)
    'sortino': 0.20,        # Risk-adjusted return (downside-only vol)
    'profit_factor': 0.15,  # Gross win/loss ratio
    'win_rate': 0.10,       # Win frequency
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
                   position_value_usd, entry_time AS entry_date, exit_time AS exit_date
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


def calc_sharpe(returns, annualize=True):
    """
    Sharpe Ratio — mean return / standard deviation of returns.
    Annualized by default: * sqrt(252) for daily, or * sqrt(n) for per-trade.
    Industry standard metric per HFR, AQR, etc.

    For per-trade returns (not daily), we use sqrt(trades_per_year_estimate).
    Since we don't know trade frequency, we report the raw (non-annualized)
    Sharpe and let the caller decide on annualization context.
    """
    if not returns or len(returns) < 2:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std_ret = math.sqrt(variance)
    if std_ret == 0:
        return float('inf') if mean_ret > 0 else 0.0
    sharpe = mean_ret / std_ret
    if annualize:
        # For per-trade returns, approximate annualization assuming ~252 trades/year
        # This is an approximation — true annualization requires knowing trade frequency
        sharpe *= math.sqrt(252)
    return sharpe


def calc_sortino(returns, target=0.0, annualize=True):
    """
    Sortino Ratio — mean excess return / downside deviation.
    Only penalizes negative returns (unlike Sharpe which penalizes all volatility).
    Standard in institutional quant evaluation.
    Annualized by default with sqrt(252).
    """
    if not returns:
        return 0.0
    mean_ret = sum(returns) / len(returns)
    downside = [min(0, r - target) ** 2 for r in returns]
    dd_variance = sum(downside) / len(downside)
    dd_std = math.sqrt(dd_variance)
    if dd_std == 0:
        return float('inf') if mean_ret > 0 else 0.0
    sortino = mean_ret / dd_std
    if annualize:
        sortino *= math.sqrt(252)
    return sortino


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

        # Sharpe ratio — annualized (on % returns)
        sharpe = calc_sharpe(pcts, annualize=True)
        sharpe_capped = min(max(sharpe, -10.0), 10.0)  # Cap both ends for normalization

        # Sortino ratio — annualized (on % returns)
        sortino = calc_sortino(pcts, annualize=True)
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
            'sharpe_ratio': round(sharpe, 3),
            'sortino_ratio': round(sortino, 3),
            'max_drawdown_usd': round(max_dd, 2),
            'max_win_pct': round(max_win_pct, 2),
            'max_loss_pct': round(max_loss_pct, 2),
            # Raw values for z-scoring (capped to prevent inf)
            '_wr': win_rate * 100,
            '_exp': expectancy_pct,
            '_pf': pf_capped,
            '_sharpe': sharpe_capped,
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
    sharpe_z = z_score_normalize([r['_sharpe'] for r in raw_results])
    sort_z = z_score_normalize([r['_sortino'] for r in raw_results])
    dd_z = z_score_normalize([r['_dd'] for r in raw_results])  # Higher = less drawdown = better

    for i, r in enumerate(raw_results):
        composite = (
            COMPOSITE_WEIGHTS['win_rate'] * wr_z[i] +
            COMPOSITE_WEIGHTS['expectancy'] * exp_z[i] +
            COMPOSITE_WEIGHTS['profit_factor'] * pf_z[i] +
            COMPOSITE_WEIGHTS['sharpe'] * sharpe_z[i] +
            COMPOSITE_WEIGHTS['sortino'] * sort_z[i] +
            COMPOSITE_WEIGHTS['max_dd'] * dd_z[i]
        )
        r['composite_score'] = round(composite, 4)
        r['z_scores'] = {
            'win_rate': round(wr_z[i], 3),
            'expectancy': round(exp_z[i], 3),
            'profit_factor': round(pf_z[i], 3),
            'sharpe': round(sharpe_z[i], 3),
            'sortino': round(sort_z[i], 3),
            'max_dd': round(dd_z[i], 3),
        }
        # Remove internal fields
        for k in ('_wr', '_exp', '_pf', '_sharpe', '_sortino', '_dd'):
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


def compute_asset_class_metrics(trades, min_trades=5):
    """
    Compute aggregate Sharpe ratios and performance metrics per asset class
    (stocks, crypto, forex, sports) and for the entire portfolio.

    Returns dict: { 'stocks': {...}, 'crypto': {...}, ..., 'portfolio': {...} }
    """
    # Group trades by asset class
    asset_groups = {}
    all_pcts = []

    for t in trades:
        ac = t.get('asset_class', 'unknown').lower()
        if ac not in asset_groups:
            asset_groups[ac] = {'pcts': [], 'pnls': []}
        pct = float(t.get('realized_pct', 0))
        pnl = float(t.get('realized_pnl_usd', 0))
        asset_groups[ac]['pcts'].append(pct)
        asset_groups[ac]['pnls'].append(pnl)
        all_pcts.append(pct)

    # Industry benchmarks (2026) for comparison
    benchmarks = {
        'stocks':  {'sp500_sharpe': 0.9, 'good': 1.0, 'very_good': 2.0, 'elite': 3.0},
        'crypto':  {'btc_sharpe': 1.1, 'good': 1.0, 'very_good': 2.0, 'elite': 3.0},
        'forex':   {'eur_usd_sharpe': 0.3, 'good': 0.8, 'very_good': 1.5, 'elite': 2.5},
        'sports':  {'good': 0.5, 'very_good': 1.0, 'elite': 2.0},
    }
    # Reference: Renaissance Medallion ~2.5-6.0, Two Sigma ~1.5-2.5, AQR ~1.0-1.5

    results = {}

    def _metrics_for(pcts, pnls, label):
        n = len(pcts)
        if n < min_trades:
            return None
        wins = [p for p in pcts if p > 0]
        losses = [p for p in pcts if p <= 0]
        wr = len(wins) / n
        mean_ret = sum(pcts) / n
        total_pnl = sum(pnls)

        # Variance (population) and std
        var = sum((r - mean_ret) ** 2 for r in pcts) / n
        std = math.sqrt(var) if var > 0 else 0

        # Downside deviation
        dvar = sum(min(0, r) ** 2 for r in pcts) / n
        dstd = math.sqrt(dvar) if dvar > 0 else 0

        # Sharpe (annualized per-trade with sqrt(252) approximation)
        sharpe = (mean_ret / std * math.sqrt(252)) if std > 0 else 0
        sortino = (mean_ret / dstd * math.sqrt(252)) if dstd > 0 else 0

        # Profit factor
        gw = sum(p for p in pnls if p > 0)
        gl = abs(sum(p for p in pnls if p <= 0))
        pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)

        # Max drawdown (from cumulative PnL)
        cum = 0
        peak = 0
        mdd = 0
        for p in pnls:
            cum += p
            if cum > peak:
                peak = cum
            dd = cum - peak
            if dd < mdd:
                mdd = dd

        # Calmar ratio (annualized return / max drawdown)
        ann_return = mean_ret * 252
        calmar = ann_return / abs(mdd) if mdd < 0 else 0

        # VaR 95% (historical)
        var95 = 0
        if n >= 20:
            sorted_p = sorted(pcts)
            idx5 = int(n * 0.05)
            var95 = sorted_p[idx5]

        # Expectancy
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        exp = (wr * avg_win) - ((1 - wr) * avg_loss)

        return {
            'label': label,
            'total_trades': n,
            'win_rate_pct': round(wr * 100, 2),
            'mean_return_pct': round(mean_ret, 4),
            'total_pnl_usd': round(total_pnl, 2),
            'sharpe_ratio': round(sharpe, 4),
            'sortino_ratio': round(sortino, 4),
            'calmar_ratio': round(calmar, 4),
            'profit_factor': round(min(pf, 999), 3),
            'max_drawdown_usd': round(mdd, 2),
            'volatility_pct': round(std, 4),
            'downside_deviation': round(dstd, 4),
            'var_95_pct': round(var95, 2),
            'expectancy_pct': round(exp, 4),
            'avg_win_pct': round(avg_win, 2),
            'avg_loss_pct': round(avg_loss, 2),
        }

    # Per asset class
    for ac, data in asset_groups.items():
        m = _metrics_for(data['pcts'], data['pnls'], ac.title())
        if m:
            bm = benchmarks.get(ac, {})
            grade = 'D'
            s = m['sharpe_ratio']
            if s >= bm.get('elite', 3.0):
                grade = 'A+'
            elif s >= bm.get('very_good', 2.0):
                grade = 'A'
            elif s >= bm.get('good', 1.0):
                grade = 'B'
            elif s >= 0.5:
                grade = 'C'
            m['grade'] = grade
            m['benchmark'] = bm
            results[ac] = m

    # Portfolio-level (all trades)
    all_pnls = []
    for ac, data in asset_groups.items():
        all_pnls.extend(data['pnls'])
    port = _metrics_for(all_pcts, all_pnls, 'Portfolio (All Assets)')
    if port:
        port['grade'] = 'A+' if port['sharpe_ratio'] >= 3.0 else ('A' if port['sharpe_ratio'] >= 2.0 else ('B' if port['sharpe_ratio'] >= 1.0 else ('C' if port['sharpe_ratio'] >= 0.5 else 'D')))
        port['benchmark'] = {'renaissance': 2.5, 'two_sigma': 1.5, 'aqr': 1.2, 'sp500': 0.9}
        results['portfolio'] = port

    return results


def print_asset_class_report(ac_metrics):
    """Print a comprehensive asset-class-level Sharpe ratio report."""
    print("\n" + "=" * 100)
    print("  ASSET CLASS PERFORMANCE REPORT — vs. Industry Benchmarks")
    print("=" * 100)

    for key in ['stocks', 'crypto', 'forex', 'sports', 'portfolio']:
        m = ac_metrics.get(key)
        if not m:
            continue

        is_port = key == 'portfolio'
        header = f"  {m['label']}"
        if is_port:
            print("\n" + "-" * 100)
        print(f"\n{header}")
        print(f"  {'─' * 60}")
        print(f"    Trades:     {m['total_trades']:>8,}")
        print(f"    Win Rate:   {m['win_rate_pct']:>7.1f}%")
        print(f"    Mean Ret:   {m['mean_return_pct']:>+7.3f}%")
        print(f"    Total PnL:  ${m['total_pnl_usd']:>10,.2f}")
        print(f"    Volatility: {m['volatility_pct']:>7.3f}%")
        print(f"    VaR (95%):  {m['var_95_pct']:>+7.2f}%")
        print(f"    Max DD:     ${m['max_drawdown_usd']:>10,.2f}")
        print()
        print(f"    SHARPE:     {m['sharpe_ratio']:>+7.3f}  [Grade: {m['grade']}]")
        print(f"    Sortino:    {m['sortino_ratio']:>+7.3f}")
        print(f"    Calmar:     {m['calmar_ratio']:>+7.3f}")
        print(f"    Profit F:   {m['profit_factor']:>7.2f}")
        print(f"    Expectancy: {m['expectancy_pct']:>+7.3f}%")

        bm = m.get('benchmark', {})
        if bm:
            print(f"\n    Benchmarks:")
            for bk, bv in bm.items():
                delta = m['sharpe_ratio'] - bv
                indicator = '+' if delta >= 0 else ''
                print(f"      vs {bk:20s}: {bv:>5.1f}  (ours {indicator}{delta:.2f})")

    print("\n" + "=" * 100)
    print("  Industry Reference: Renaissance ~2.5-6.0 | Two Sigma ~1.5-2.5 | "
          "AQR ~1.0-1.5 | S&P500 ~0.9")
    print("  Grading: A+=3.0+ | A=2.0+ | B=1.0+ | C=0.5+ | D=<0.5")
    print("=" * 100)


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
          f"{'PF':>6} | {'Sharpe':>7} | {'Sorti':>7} | {'MaxDD$':>8} | {'Score':>7}")
    print("-" * 130)
    for r in results:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "INF"
        sharpe_str = f"{r['sharpe_ratio']:>+7.2f}" if abs(r['sharpe_ratio']) < 100 else "INF"
        sort_str = f"{r['sortino_ratio']:.2f}" if r['sortino_ratio'] < 100 else "INF"
        print(f"{r['rank']:>3} | {r['algorithm']:28s} | {r['asset_class']:7s} | {r['total_trades']:>5} | "
              f"{r['win_rate_pct']:>5.1f}% | {r['expectancy_pct']:>6.2f}% | "
              f"{pf_str:>6} | {sharpe_str:>7} | {sort_str:>7} | ${r['max_drawdown_usd']:>7.0f} | "
              f"{r['composite_score']:>+7.3f}")

    # --- Z-score breakdown for top 5 ---
    top_n = min(5, len(results))
    print(f"\n  Z-Score Breakdown (top {top_n}):")
    print(f"  {'Algorithm':28s} | {'z_WR':>6} | {'z_Exp':>6} | {'z_PF':>6} | {'z_Shp':>6} | {'z_Srt':>6} | {'z_DD':>6}")
    print(f"  {'-'*85}")
    for r in results[:top_n]:
        z = r['z_scores']
        print(f"  {r['algorithm']:28s} | {z['win_rate']:>+6.2f} | {z['expectancy']:>+6.2f} | "
              f"{z['profit_factor']:>+6.2f} | {z['sharpe']:>+6.2f} | {z['sortino']:>+6.2f} | {z['max_dd']:>+6.2f}")

    # --- Asset Class Sharpe Report (NEW) ---
    ac_metrics = compute_asset_class_metrics(trades, min_trades=5)
    print_asset_class_report(ac_metrics)

    # --- Save results (including asset class metrics) ---
    json_path, csv_path = save_results(results, min_trades)

    # Save asset-class report to JSON
    ac_json_path = os.path.join(OUTPUT_DIR, 'asset_class_sharpe_report.json')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(ac_json_path, 'w') as f:
        json.dump({
            'generated': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),
            'description': 'Asset-class and portfolio-level Sharpe ratios with industry benchmarks',
            'benchmarks_reference': {
                'renaissance_medallion': '2.5-6.0 Sharpe (best hedge fund ever)',
                'two_sigma': '1.5-2.5 Sharpe (ML-driven quant)',
                'aqr': '1.0-1.5 Sharpe (systematic factor)',
                'sp500_buy_hold': '0.7-1.1 Sharpe (passive benchmark)',
                'grading': 'A+=3.0+ | A=2.0+ | B=1.0+ | C=0.5+ | D=<0.5',
            },
            'asset_classes': ac_metrics
        }, f, indent=2)

    print(f"\nSaved: {json_path}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {ac_json_path}")


if __name__ == '__main__':
    main()
