#!/usr/bin/env python3
"""
Mercury Strategy Suite -- Backtest Runner
Tests all 7 EMA crossover variants against real Binance 1h data.
"""
import json
import sys
import time
import urllib.request
import pathlib

import pandas as pd
import numpy as np
from datetime import datetime

# Ensure project root is on sys.path so baby_strategies imports work
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baby_strategies.simpleton_trend_reversal import SimpletonTrendReversalStrategy
from baby_strategies.mercury_vol_crossover import MercuryVolCrossoverStrategy
from baby_strategies.mercury_conservative import MercuryConservativeStrategy
from baby_strategies.mercury_aggressive import MercuryAggressiveStrategy
from baby_strategies.simpleton_mercury_hybrid import SimpletonMercuryHybridStrategy
from baby_strategies.mercury_funding_enhanced import MercuryFundingEnhancedStrategy
from baby_strategies.mercury_hma_filtered import MercuryHmaFilteredStrategy
from baby_strategies.triple_confirmation import TripleConfirmationStrategy


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV from Binance public API."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    return df


def simulate_trades(signals: list, df: pd.DataFrame, max_hold_bars: int = 168) -> list:
    """
    Simulate each signal: walk forward through bars to check if TP or SL hits first.
    Returns list of trade results.
    """
    results = []
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values

    for sig in signals:
        entry = sig['entry_price']
        tp = sig['take_profit']
        sl = sig['stop_loss']
        side = sig['side']

        # Find the bar index where entry price matches
        entry_idx = None
        for i in range(len(closes)):
            if abs(closes[i] - entry) / entry < 0.001:  # Within 0.1%
                entry_idx = i
                break

        if entry_idx is None:
            # Try matching any close within 0.5%
            for i in range(len(closes)):
                if abs(closes[i] - entry) / entry < 0.005:
                    entry_idx = i
                    break

        if entry_idx is None:
            continue

        # Walk forward from entry
        outcome = "OPEN"
        exit_price = closes[-1]  # Default: still open at last bar
        bars_held = 0

        for j in range(entry_idx + 1, min(entry_idx + max_hold_bars, len(df))):
            bars_held = j - entry_idx

            if side == "LONG":
                if highs[j] >= tp:
                    outcome = "TP"
                    exit_price = tp
                    break
                elif lows[j] <= sl:
                    outcome = "SL"
                    exit_price = sl
                    break
            else:  # SHORT
                if lows[j] <= tp:
                    outcome = "TP"
                    exit_price = tp
                    break
                elif highs[j] >= sl:
                    outcome = "SL"
                    exit_price = sl
                    break

        if side == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        results.append({
            'strategy': sig['strategy'],
            'symbol': sig.get('symbol', 'UNKNOWN'),
            'side': side,
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'exit': exit_price,
            'outcome': outcome,
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
        })

    return results


def compute_metrics(trades: list) -> dict:
    """Compute strategy performance metrics."""
    if not trades:
        return {
            'total': 0, 'wins': 0, 'losses': 0, 'open': 0,
            'win_rate': 0, 'avg_pnl': 0, 'profit_factor': 0,
            'expectancy': 0, 'best': 0, 'worst': 0,
        }

    closed = [t for t in trades if t['outcome'] in ('TP', 'SL')]
    wins = [t for t in closed if t['pnl_pct'] > 0]
    losses = [t for t in closed if t['pnl_pct'] <= 0]
    open_trades = [t for t in trades if t['outcome'] == 'OPEN']

    total_closed = len(closed)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
    avg_pnl = np.mean([t['pnl_pct'] for t in closed]) if closed else 0

    gross_profit = sum(t['pnl_pct'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_pct'] for t in losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    all_pnl = [t['pnl_pct'] for t in closed]
    best = max(all_pnl) if all_pnl else 0
    worst = min(all_pnl) if all_pnl else 0

    # Expectancy = (WR * avg_win) - ((1-WR) * avg_loss)
    avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_loss = abs(np.mean([t['pnl_pct'] for t in losses])) if losses else 0
    wr = win_count / total_closed if total_closed > 0 else 0
    expectancy = (wr * avg_win) - ((1 - wr) * avg_loss)

    return {
        'total': len(trades), 'wins': win_count, 'losses': loss_count,
        'open': len(open_trades), 'win_rate': win_rate, 'avg_pnl': avg_pnl,
        'profit_factor': profit_factor, 'expectancy': expectancy,
        'best': best, 'worst': worst,
    }


def main():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]
    timeframes = ["1h", "1d"]
    limit = 1000

    strategies = [
        SimpletonTrendReversalStrategy(),
        MercuryVolCrossoverStrategy(),
        MercuryConservativeStrategy(),
        MercuryAggressiveStrategy(),
        SimpletonMercuryHybridStrategy(),
        MercuryFundingEnhancedStrategy(),
        MercuryHmaFilteredStrategy(),
        TripleConfirmationStrategy(),
    ]

    print("=" * 80)
    print("MERCURY STRATEGY SUITE -- BACKTEST REPORT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    print(f"Bars per symbol/timeframe: {limit}")
    print("=" * 80)
    print()

    # Full report for JSON output
    full_report = {
        "generated_at": datetime.now().isoformat(),
        "symbols": symbols,
        "bars_per_symbol": limit,
        "timeframes": timeframes,
        "results_by_timeframe": {}
    }

    for tf in timeframes:
        print("=" * 80)
        print(f"  TIMEFRAME: {tf}  ({limit} bars)")
        print("=" * 80)
        print()

        # Fetch data for this timeframe
        data = {}
        for sym in symbols:
            print(f"  Fetching {sym} {tf} klines ({limit} bars)...")
            try:
                data[sym] = fetch_klines(sym, tf, limit)
            except Exception as e:
                print(f"  ERROR fetching {sym}: {e}")
            time.sleep(0.3)  # Rate limit

        print()

        # Determine max_hold_bars based on timeframe
        max_hold = 168 if tf == "1h" else 30  # 7 days for 1h, 30 days for 1d

        # Run each strategy
        all_results = {}
        for strat in strategies:
            name = strat.NAME
            all_signals = []

            for sym in symbols:
                if sym not in data:
                    continue
                df = data[sym]
                signals = strat.generate_signals(df, symbol=sym)
                all_signals.extend(signals)

            # Simulate trades
            trades = []
            for sym in symbols:
                if sym not in data:
                    continue
                sym_signals = [s for s in all_signals if s.get('symbol') == sym]
                if sym_signals:
                    sym_trades = simulate_trades(sym_signals, data[sym], max_hold_bars=max_hold)
                    trades.extend(sym_trades)

            all_results[name] = compute_metrics(trades)
            all_results[name]['raw_trades'] = trades

        # Print results table
        print(f"  {'Strategy':<30} {'Trades':>6} {'Wins':>5} {'Loss':>5} {'WR%':>7} {'AvgPnL':>8} {'PF':>6} {'EV':>8} {'Best':>8} {'Worst':>8}")
        print("  " + "-" * 103)

        for name, m in all_results.items():
            print(f"  {name:<30} {m['total']:>6} {m['wins']:>5} {m['losses']:>5} "
                  f"{m['win_rate']:>6.1f}% {m['avg_pnl']:>+7.2f}% {m['profit_factor']:>5.2f} "
                  f"{m['expectancy']:>+7.2f}% {m['best']:>+7.2f}% {m['worst']:>+7.2f}%")

        print("  " + "-" * 103)
        print()

        # Per-symbol breakdown
        print(f"  PER-SYMBOL BREAKDOWN ({tf}):")
        print(f"  {'Strategy':<30} {'Symbol':<10} {'Signals':>7} {'Closed':>7} {'WR%':>7}")
        print("  " + "-" * 63)
        for name, m in all_results.items():
            trades = m['raw_trades']
            for sym in symbols:
                sym_trades = [t for t in trades if t['symbol'] == sym]
                closed = [t for t in sym_trades if t['outcome'] in ('TP', 'SL')]
                wins = [t for t in closed if t['pnl_pct'] > 0]
                wr = len(wins) / len(closed) * 100 if closed else 0
                print(f"  {name:<30} {sym:<10} {len(sym_trades):>7} {len(closed):>7} {wr:>6.1f}%")

        print()

        # Store for JSON
        full_report["results_by_timeframe"][tf] = {}
        for name, m in all_results.items():
            full_report["results_by_timeframe"][tf][name] = {
                k: v for k, v in m.items() if k != 'raw_trades'
            }

    # Save results JSON
    out = pathlib.Path(__file__).resolve().parent / "backtest_mercury_results.json"
    out.write_text(json.dumps(full_report, indent=2))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
