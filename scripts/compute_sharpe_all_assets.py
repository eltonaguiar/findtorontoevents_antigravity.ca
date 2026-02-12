#!/usr/bin/env python3
"""
Multi-Asset Sharpe Ratio Calculator
====================================
Backtests all signals (stocks, crypto, forex) against actual price data
and computes exact Sharpe ratios per algorithm, per asset class, and portfolio-wide.

Compares against 2026 industry benchmarks:
  - S&P 500 buy-and-hold: ~0.9 Sharpe
  - Renaissance Medallion: ~2.5-6.0 Sharpe
  - Two Sigma: ~1.5-2.5 Sharpe
  - AQR: ~1.0-1.5 Sharpe
  - Good algo: 1.0+ | Very good: 2.0+ | Elite: 3.0+

Usage:
  python scripts/compute_sharpe_all_assets.py
  python scripts/compute_sharpe_all_assets.py --min-n 5

Requirements: pip install mysql-connector-python
"""
import os
import sys
import json
import math
import argparse
from datetime import datetime

# DB config from env vars
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Default backtest params (matches PHP backtest defaults)
STOCK_TP = 10       # Take profit %
STOCK_SL = 5        # Stop loss %
STOCK_HOLD = 7      # Max hold days
CRYPTO_TP = 10
CRYPTO_SL = 5
CRYPTO_HOLD = 30
FOREX_TP = 2
FOREX_SL = 1
FOREX_HOLD = 14

# Industry benchmarks (2026)
BENCHMARKS = {
    'stocks': {
        'sp500_buy_hold': 0.9,
        'good_algo': 1.0,
        'very_good': 2.0,
        'elite': 3.0,
        'renaissance': 2.5,
    },
    'crypto': {
        'btc_buy_hold': 1.1,
        'good_algo': 1.0,
        'very_good': 2.0,
        'market_neutral': 2.5,
        'elite': 3.0,
    },
    'forex': {
        'eur_usd_carry': 0.3,
        'good_algo': 0.8,
        'very_good': 1.5,
        'elite': 2.5,
    },
    'portfolio': {
        'sp500': 0.9,
        'aqr': 1.2,
        'two_sigma': 1.5,
        'renaissance': 2.5,
    },
}


def connect_db():
    import mysql.connector
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
    )


# ────────────────────────────────────────────────────────
#  STOCKS: stock_picks + daily_prices
# ────────────────────────────────────────────────────────
def backtest_stocks(conn, tp=STOCK_TP, sl=STOCK_SL, max_hold=STOCK_HOLD):
    """Backtest all stock picks against daily_prices."""
    cur = conn.cursor(dictionary=True)

    # Load all picks
    cur.execute("""
        SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, sp.score
        FROM stock_picks sp
        WHERE sp.entry_price > 0
        ORDER BY sp.pick_date ASC
    """)
    picks = cur.fetchall()

    if not picks:
        return []

    # Load all prices into memory (ticker -> date -> OHLC)
    tickers_needed = set(p['ticker'] for p in picks)
    prices = {}  # ticker -> [{date, o, h, l, c}, ...]

    for tk in tickers_needed:
        cur.execute("""
            SELECT trade_date, open_price, high_price, low_price, close_price
            FROM daily_prices WHERE ticker = %s ORDER BY trade_date ASC
        """, (tk,))
        rows = cur.fetchall()
        prices[tk] = rows

    # Simulate trades
    trades = []
    for pick in picks:
        tk = pick['ticker']
        ep = float(pick['entry_price'])
        pd_date = pick['pick_date']
        algo = pick['algorithm_name']

        if tk not in prices or not prices[tk]:
            continue

        # Find index of pick date
        price_list = prices[tk]
        start_idx = None
        for i, pr in enumerate(price_list):
            if pr['trade_date'] >= pd_date:
                start_idx = i
                break
        if start_idx is None:
            continue

        # Simulate
        tp_price = ep * (1 + tp / 100.0)
        sl_price = ep * (1 - sl / 100.0)
        exit_price = 0
        exit_reason = ''
        hold_days = 0

        for j in range(start_idx, min(start_idx + max_hold + 2, len(price_list))):
            bar = price_list[j]
            hold_days += 1
            h = float(bar['high_price'])
            l = float(bar['low_price'])
            c = float(bar['close_price'])

            if l <= sl_price:
                exit_price = sl_price
                exit_reason = 'stop_loss'
                break
            if h >= tp_price:
                exit_price = tp_price
                exit_reason = 'take_profit'
                break
            if hold_days >= max_hold:
                exit_price = c
                exit_reason = 'max_hold'
                break

        if exit_price <= 0:
            continue

        ret_pct = ((exit_price - ep) / ep) * 100.0
        trades.append({
            'asset_class': 'stocks',
            'algorithm': algo,
            'symbol': tk,
            'return_pct': ret_pct,
            'pnl_usd': ret_pct * 100,  # Assuming $10k position at 10%
            'hold_days': hold_days,
            'exit_reason': exit_reason,
        })

    return trades


# ────────────────────────────────────────────────────────
#  CRYPTO: cp_signals + cp_prices
# ────────────────────────────────────────────────────────
def backtest_crypto(conn, tp=CRYPTO_TP, sl=CRYPTO_SL, max_hold=CRYPTO_HOLD):
    """Backtest all crypto signals against cp_prices."""
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT pair, strategy_name, signal_date, entry_price, direction
        FROM cp_signals WHERE entry_price > 0
        ORDER BY signal_date ASC
    """)
    signals = cur.fetchall()
    if not signals:
        return []

    # Load all prices
    cur.execute("""
        SELECT pair, trade_date, open_price, high_price, low_price, close_price
        FROM cp_prices ORDER BY pair, trade_date ASC
    """)
    prices_raw = cur.fetchall()
    prices = {}  # pair -> list of bars
    for pr in prices_raw:
        pair = pr['pair']
        if pair not in prices:
            prices[pair] = []
        prices[pair].append(pr)

    trades = []
    for sig in signals:
        pair = sig['pair']
        ep = float(sig['entry_price'])
        sd = sig['signal_date']
        algo = sig['strategy_name']

        if pair not in prices or ep <= 0:
            continue

        price_list = prices[pair]
        start_idx = None
        for i, pr in enumerate(price_list):
            if pr['trade_date'] >= sd:
                start_idx = i
                break
        if start_idx is None:
            continue

        tp_price = ep * (1 + tp / 100.0)
        sl_price = ep * (1 - sl / 100.0)
        exit_price = 0
        exit_reason = ''
        hold_days = 0

        for j in range(start_idx, min(start_idx + max_hold + 2, len(price_list))):
            bar = price_list[j]
            hold_days += 1
            h = float(bar['high_price'])
            l = float(bar['low_price'])
            c = float(bar['close_price'])

            if l <= sl_price:
                exit_price = sl_price
                exit_reason = 'stop_loss'
                break
            if h >= tp_price:
                exit_price = tp_price
                exit_reason = 'take_profit'
                break
            if hold_days >= max_hold:
                exit_price = c
                exit_reason = 'max_hold'
                break

        if exit_price <= 0:
            continue

        ret_pct = ((exit_price - ep) / ep) * 100.0
        trades.append({
            'asset_class': 'crypto',
            'algorithm': algo,
            'symbol': pair,
            'return_pct': ret_pct,
            'pnl_usd': ret_pct * 100,
            'hold_days': hold_days,
            'exit_reason': exit_reason,
        })

    return trades


# ────────────────────────────────────────────────────────
#  FOREX: fx_signals + fx_prices
# ────────────────────────────────────────────────────────
def backtest_forex(conn, tp=FOREX_TP, sl=FOREX_SL, max_hold=FOREX_HOLD):
    """Backtest all forex signals against fx_prices."""
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT pair, strategy_name, signal_date, entry_price, direction
        FROM fx_signals WHERE entry_price > 0
        ORDER BY signal_date ASC
    """)
    signals = cur.fetchall()
    if not signals:
        return []

    # Load all prices
    cur.execute("""
        SELECT pair, trade_date, open_price, high_price, low_price, close_price
        FROM fx_prices ORDER BY pair, trade_date ASC
    """)
    prices_raw = cur.fetchall()
    prices = {}
    for pr in prices_raw:
        pair = pr['pair']
        if pair not in prices:
            prices[pair] = []
        prices[pair].append(pr)

    trades = []
    for sig in signals:
        pair = sig['pair']
        ep = float(sig['entry_price'])
        sd = sig['signal_date']
        algo = sig['strategy_name']

        if pair not in prices or ep <= 0:
            continue

        price_list = prices[pair]
        start_idx = None
        for i, pr in enumerate(price_list):
            if pr['trade_date'] >= sd:
                start_idx = i
                break
        if start_idx is None:
            continue

        tp_price = ep * (1 + tp / 100.0)
        sl_price = ep * (1 - sl / 100.0)
        exit_price = 0
        exit_reason = ''
        hold_days = 0

        for j in range(start_idx, min(start_idx + max_hold + 2, len(price_list))):
            bar = price_list[j]
            hold_days += 1
            h = float(bar['high_price'])
            l = float(bar['low_price'])
            c = float(bar['close_price'])

            if l <= sl_price:
                exit_price = sl_price
                exit_reason = 'stop_loss'
                break
            if h >= tp_price:
                exit_price = tp_price
                exit_reason = 'take_profit'
                break
            if hold_days >= max_hold:
                exit_price = c
                exit_reason = 'max_hold'
                break

        if exit_price <= 0:
            continue

        ret_pct = ((exit_price - ep) / ep) * 100.0
        trades.append({
            'asset_class': 'forex',
            'algorithm': algo,
            'symbol': pair,
            'return_pct': ret_pct,
            'pnl_usd': ret_pct * 100,
            'hold_days': hold_days,
            'exit_reason': exit_reason,
        })

    return trades


# ────────────────────────────────────────────────────────
#  METRICS COMPUTATION
# ────────────────────────────────────────────────────────
def calc_sharpe(returns, annualize_factor=252):
    """Annualized Sharpe ratio = mean/std * sqrt(annualize_factor)."""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std = math.sqrt(var) if var > 0 else 0
    if std == 0:
        return float('inf') if mean_r > 0 else 0.0
    return (mean_r / std) * math.sqrt(annualize_factor)


def calc_sortino(returns, annualize_factor=252):
    """Annualized Sortino ratio = mean / downside_deviation * sqrt(factor)."""
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    dvar = sum(min(0, r) ** 2 for r in returns) / len(returns)
    dstd = math.sqrt(dvar) if dvar > 0 else 0
    if dstd == 0:
        return float('inf') if mean_r > 0 else 0.0
    return (mean_r / dstd) * math.sqrt(annualize_factor)


def calc_max_drawdown(pnls):
    """Max drawdown from cumulative PnL series."""
    if not pnls:
        return 0.0
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
    return mdd


def compute_metrics(trades, label=''):
    """Compute comprehensive metrics for a list of trades."""
    n = len(trades)
    if n == 0:
        return None

    rets = [t['return_pct'] for t in trades]
    pnls = [t['pnl_usd'] for t in trades]

    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    wr = len(wins) / n if n > 0 else 0
    mean_ret = sum(rets) / n
    total_pnl = sum(pnls)

    # Avg win/loss
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0

    # Expectancy
    exp = (wr * avg_win) - ((1 - wr) * avg_loss)

    # Profit factor
    gw = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p <= 0))
    pf = gw / gl if gl > 0 else (999 if gw > 0 else 0)

    # Sharpe & Sortino (annualized)
    sharpe = calc_sharpe(rets)
    sortino = calc_sortino(rets)

    # Max drawdown
    mdd = calc_max_drawdown(pnls)

    # Volatility
    var = sum((r - mean_ret) ** 2 for r in rets) / n if n > 0 else 0
    vol = math.sqrt(var)

    # VaR 95%
    var95 = 0
    if n >= 20:
        sorted_r = sorted(rets)
        var95 = sorted_r[int(n * 0.05)]

    return {
        'label': label,
        'total_trades': n,
        'win_rate_pct': round(wr * 100, 2),
        'mean_return_pct': round(mean_ret, 4),
        'total_pnl_usd': round(total_pnl, 2),
        'avg_win_pct': round(avg_win, 2),
        'avg_loss_pct': round(avg_loss, 2),
        'expectancy_pct': round(exp, 4),
        'profit_factor': round(min(pf, 999), 3),
        'sharpe_ratio': round(sharpe, 4),
        'sortino_ratio': round(sortino, 4),
        'max_drawdown_usd': round(mdd, 2),
        'volatility_pct': round(vol, 4),
        'var_95_pct': round(var95, 2),
    }


def grade_sharpe(sharpe, asset_class='stocks'):
    """Grade a Sharpe ratio against industry benchmarks."""
    bm = BENCHMARKS.get(asset_class, BENCHMARKS['stocks'])
    if sharpe >= bm.get('elite', 3.0):
        return 'A+'
    elif sharpe >= bm.get('very_good', 2.0):
        return 'A'
    elif sharpe >= bm.get('good_algo', 1.0):
        return 'B'
    elif sharpe >= 0.5:
        return 'C'
    else:
        return 'D'


# ────────────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Multi-Asset Sharpe Calculator')
    parser.add_argument('--min-n', type=int, default=5,
                        help='Min trades to include algorithm (default 5)')
    args = parser.parse_args()

    print("=" * 100)
    print("  MULTI-ASSET SHARPE RATIO CALCULATOR")
    print("  Backtests all signals against actual price data")
    print("=" * 100)

    conn = connect_db()

    # ── Backtest all three asset classes ──
    print("\n[1/3] Backtesting stocks (stock_picks + daily_prices)...")
    stock_trades = backtest_stocks(conn)
    print(f"       {len(stock_trades)} stock trades simulated")

    print("[2/3] Backtesting crypto (cp_signals + cp_prices)...")
    crypto_trades = backtest_crypto(conn)
    print(f"       {len(crypto_trades)} crypto trades simulated")

    print("[3/3] Backtesting forex (fx_signals + fx_prices)...")
    forex_trades = backtest_forex(conn)
    print(f"       {len(forex_trades)} forex trades simulated")

    conn.close()

    all_trades = stock_trades + crypto_trades + forex_trades
    print(f"\nTotal: {len(all_trades)} trades across all asset classes")

    if not all_trades:
        print("No trades to analyze. Check database.")
        return

    # ── Per-Algorithm Metrics ──
    algo_groups = {}
    for t in all_trades:
        key = f"{t['algorithm']}|{t['asset_class']}"
        if key not in algo_groups:
            algo_groups[key] = []
        algo_groups[key].append(t)

    algo_results = []
    for key, trades in algo_groups.items():
        algo, ac = key.split('|')
        if len(trades) < args.min_n:
            continue
        m = compute_metrics(trades, f"{algo} ({ac})")
        if m:
            m['algorithm'] = algo
            m['asset_class'] = ac
            m['grade'] = grade_sharpe(m['sharpe_ratio'], ac)
            algo_results.append(m)

    algo_results.sort(key=lambda x: x['sharpe_ratio'], reverse=True)

    # Print per-algorithm table
    print("\n" + "=" * 120)
    print("  PER-ALGORITHM SHARPE RATIOS")
    print("=" * 120)
    print(f"  {'#':>3} | {'Algorithm':30s} | {'Asset':7s} | {'N':>5} | {'WR%':>6} | "
          f"{'Sharpe':>8} | {'Sortino':>8} | {'PF':>6} | {'Exp%':>7} | {'Grade':>5}")
    print("  " + "-" * 110)

    for i, r in enumerate(algo_results):
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "INF"
        print(f"  {i+1:>3} | {r['algorithm']:30s} | {r['asset_class']:7s} | {r['total_trades']:>5} | "
              f"{r['win_rate_pct']:>5.1f}% | {r['sharpe_ratio']:>+8.3f} | "
              f"{r['sortino_ratio']:>+8.3f} | {pf_str:>6} | {r['expectancy_pct']:>+6.3f}% | "
              f"{r['grade']:>5}")

    # ── Per-Asset-Class Metrics ──
    print("\n" + "=" * 100)
    print("  ASSET CLASS SHARPE RATIOS vs. INDUSTRY BENCHMARKS")
    print("=" * 100)

    ac_results = {}
    for ac_name, ac_trades in [('stocks', stock_trades), ('crypto', crypto_trades), ('forex', forex_trades)]:
        if not ac_trades:
            continue
        m = compute_metrics(ac_trades, ac_name.title())
        if m:
            m['grade'] = grade_sharpe(m['sharpe_ratio'], ac_name)
            m['benchmarks'] = BENCHMARKS.get(ac_name, {})
            ac_results[ac_name] = m

    # Portfolio-wide
    port_m = compute_metrics(all_trades, 'Portfolio (All Assets)')
    if port_m:
        port_m['grade'] = grade_sharpe(port_m['sharpe_ratio'], 'portfolio')
        port_m['benchmarks'] = BENCHMARKS['portfolio']
        ac_results['portfolio'] = port_m

    for key in ['stocks', 'crypto', 'forex', 'portfolio']:
        m = ac_results.get(key)
        if not m:
            continue

        is_port = key == 'portfolio'
        if is_port:
            print("\n  " + "-" * 80)

        print(f"\n  {m['label']}")
        print(f"  {'=' * 55}")
        print(f"    Trades:       {m['total_trades']:>8,}")
        print(f"    Win Rate:     {m['win_rate_pct']:>7.1f}%")
        print(f"    Mean Return:  {m['mean_return_pct']:>+7.3f}%")
        print(f"    Volatility:   {m['volatility_pct']:>7.3f}%")
        print(f"    VaR (95%):    {m['var_95_pct']:>+7.2f}%")
        print(f"    Avg Win:      {m['avg_win_pct']:>+7.2f}%")
        print(f"    Avg Loss:     {m['avg_loss_pct']:>7.2f}%")
        print()
        print(f"    SHARPE RATIO: {m['sharpe_ratio']:>+8.4f}  [{m['grade']}]")
        print(f"    Sortino:      {m['sortino_ratio']:>+8.4f}")
        print(f"    Profit Factor:{m['profit_factor']:>8.2f}")
        print(f"    Expectancy:   {m['expectancy_pct']:>+7.3f}%")

        bm = m.get('benchmarks', {})
        if bm:
            print(f"\n    vs. Industry Benchmarks:")
            for bk, bv in sorted(bm.items(), key=lambda x: x[1]):
                delta = m['sharpe_ratio'] - bv
                sign = '+' if delta >= 0 else ''
                status = 'BEATING' if delta >= 0 else 'BELOW'
                print(f"      {bk:20s}: {bv:>5.1f}  (ours {sign}{delta:>.2f}) [{status}]")

    # ── Summary ──
    print("\n" + "=" * 100)
    print("  SUMMARY & INDUSTRY COMPARISON")
    print("=" * 100)
    print(f"""
    Our Portfolio Sharpe:   {ac_results.get('portfolio', {}).get('sharpe_ratio', 'N/A')}
    
    Industry Reference Points:
      S&P 500 Buy-and-Hold:    0.7 - 1.1
      Average Hedge Fund:      0.5 - 1.0
      AQR Capital:             1.0 - 1.5
      Two Sigma:               1.5 - 2.5
      Renaissance Medallion:   2.5 - 6.0

    Grading Scale:
      A+ = 3.0+   (Elite - top 1% of funds)
      A  = 2.0+   (Excellent - institutional quality)
      B  = 1.0+   (Good - beats most passive strategies)
      C  = 0.5+   (Below average - needs improvement)
      D  = <0.5   (Poor - losing risk-adjusted)
    """)

    # ── Save to JSON ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = {
        'generated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'backtest_params': {
            'stocks': {'tp': STOCK_TP, 'sl': STOCK_SL, 'max_hold': STOCK_HOLD},
            'crypto': {'tp': CRYPTO_TP, 'sl': CRYPTO_SL, 'max_hold': CRYPTO_HOLD},
            'forex': {'tp': FOREX_TP, 'sl': FOREX_SL, 'max_hold': FOREX_HOLD},
        },
        'industry_benchmarks': BENCHMARKS,
        'per_algorithm': algo_results,
        'per_asset_class': ac_results,
    }

    report_path = os.path.join(OUTPUT_DIR, 'sharpe_ratio_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report saved: {report_path}")

    # Also update the goldmine stats with Sharpe data
    stats_path = os.path.join(OUTPUT_DIR, 'goldmine', 'sharpe_stats.json')
    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    with open(stats_path, 'w') as f:
        json.dump({
            'generated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'asset_classes': {k: {
                'sharpe': v.get('sharpe_ratio'), 'sortino': v.get('sortino_ratio'),
                'win_rate': v.get('win_rate_pct'), 'grade': v.get('grade'),
                'trades': v.get('total_trades'),
            } for k, v in ac_results.items()},
            'top_algorithms': [
                {'name': r['algorithm'], 'asset': r['asset_class'],
                 'sharpe': r['sharpe_ratio'], 'grade': r['grade']}
                for r in algo_results[:10]
            ],
        }, f, indent=2)
    print(f"  Stats saved:  {stats_path}")

    return ac_results, algo_results


if __name__ == '__main__':
    main()
