"""
Backtest runner for 8 Unorthodox Event-Driven Crypto Strategies
================================================================
Fetches 500 daily klines from Binance, runs each strategy on a sliding window,
and evaluates TP/SL outcomes on subsequent bars.

Results: summary table + JSON export.
"""

import os
import sys

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import time
import math
import datetime
import urllib.request
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd

# --- Import strategies from sibling module ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crypto_unorthodox_event_v1 import (
    ATHBreakoutStrategy,
    ATLBounceStrategy,
    BTCATHAltRotationStrategy,
    WeekendDipBuyStrategy,
    PostCrashRecoveryStrategy,
    LongWickReversalStrategy,
    GapFillStrategy,
    ThreeWhiteSoldiersStrategy,
    Signal,
)

# -------------------------------------------------------------------------
# Config
# -------------------------------------------------------------------------
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
KLINE_LIMIT = 500
INTERVAL = "1d"
MAX_HOLD_BARS = 30  # max bars to wait for TP/SL hit

STRATEGY_CLASSES = [
    ATHBreakoutStrategy,
    ATLBounceStrategy,
    BTCATHAltRotationStrategy,
    WeekendDipBuyStrategy,
    PostCrashRecoveryStrategy,
    LongWickReversalStrategy,
    GapFillStrategy,
    ThreeWhiteSoldiersStrategy,
]

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = DATA_DIR / "unorthodox_backtest_results.json"


# -------------------------------------------------------------------------
# Binance kline fetcher
# -------------------------------------------------------------------------
def fetch_binance_klines(symbol: str, interval: str = "1d", limit: int = 500) -> pd.DataFrame:
    """Fetch klines from Binance public API (no key required)."""
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    print(f"  Fetching {symbol} {interval} x{limit} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode())

    rows = []
    for k in raw:
        rows.append({
            "open_time": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": int(k[6]),
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


# -------------------------------------------------------------------------
# Backtest engine
# -------------------------------------------------------------------------
def backtest_signal(signal: Signal, data: pd.DataFrame, bar_idx: int) -> Dict[str, Any]:
    """
    Given a signal generated at bar_idx, check subsequent bars for TP/SL.
    Returns trade result dict.
    """
    entry = signal.entry_price
    tp = signal.take_profit
    sl = signal.stop_loss
    direction = signal.direction

    # Calculate risk/reward for PnL computation
    risk = abs(entry - sl) if abs(entry - sl) > 0 else entry * 0.01
    reward = abs(tp - entry) if abs(tp - entry) > 0 else entry * 0.01

    high = data["high"].values.astype(float)
    low = data["low"].values.astype(float)
    close = data["close"].values.astype(float)

    for j in range(bar_idx + 1, min(bar_idx + 1 + MAX_HOLD_BARS, len(data))):
        if direction == "BUY":
            # Check SL first (conservative)
            if low[j] <= sl:
                return {"outcome": "loss", "pnl_pct": -abs(entry - sl) / entry * 100,
                        "bars_held": j - bar_idx}
            if high[j] >= tp:
                return {"outcome": "win", "pnl_pct": abs(tp - entry) / entry * 100,
                        "bars_held": j - bar_idx}
        else:  # SELL
            if high[j] >= sl:
                return {"outcome": "loss", "pnl_pct": -abs(sl - entry) / entry * 100,
                        "bars_held": j - bar_idx}
            if low[j] <= tp:
                return {"outcome": "win", "pnl_pct": abs(entry - tp) / entry * 100,
                        "bars_held": j - bar_idx}

    # Timeout: close at last available bar
    last_idx = min(bar_idx + MAX_HOLD_BARS, len(data) - 1)
    exit_price = close[last_idx]
    if direction == "BUY":
        pnl_pct = (exit_price - entry) / entry * 100
    else:
        pnl_pct = (entry - exit_price) / entry * 100

    return {"outcome": "timeout", "pnl_pct": pnl_pct, "bars_held": last_idx - bar_idx}


def run_backtest(strategy_cls, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Run a strategy across the full dataset using a sliding window."""
    strat = strategy_cls()
    min_bars = strat.min_bars
    name = strat.NAME

    trades = []
    # Slide from min_bars to len(data) - 1 (need at least 1 bar after for evaluation)
    for end_idx in range(min_bars, len(data) - 1):
        window = data.iloc[:end_idx + 1].copy().reset_index(drop=True)
        signals = strat.generate_signals(window, symbol)
        for sig in signals:
            result = backtest_signal(sig, data, end_idx)
            trades.append({
                "bar_idx": end_idx,
                "direction": sig.direction,
                "entry": sig.entry_price,
                "tp": sig.take_profit,
                "sl": sig.stop_loss,
                "confidence": sig.confidence,
                **result,
            })

    # Compute metrics
    n_trades = len(trades)
    if n_trades == 0:
        return {
            "strategy": name,
            "symbol": symbol,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "win_rate": 0.0,
            "total_pnl_pct": 0.0,
            "avg_pnl_pct": 0.0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "avg_bars_held": 0.0,
        }

    wins = sum(1 for t in trades if t["outcome"] == "win")
    losses = sum(1 for t in trades if t["outcome"] == "loss")
    timeouts = sum(1 for t in trades if t["outcome"] == "timeout")
    pnls = [t["pnl_pct"] for t in trades]
    bars_held = [t["bars_held"] for t in trades]

    total_pnl = sum(pnls)
    avg_pnl = total_pnl / n_trades
    win_rate = wins / n_trades * 100

    # Sharpe ratio (annualized, assuming daily)
    if len(pnls) > 1:
        std = np.std(pnls, ddof=1)
        sharpe = (avg_pnl / std) * math.sqrt(252) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown from cumulative PnL
    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    drawdowns = running_max - cum_pnl
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    return {
        "strategy": name,
        "symbol": symbol,
        "trades": n_trades,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": round(win_rate, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_bars_held": round(sum(bars_held) / n_trades, 1),
    }


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main():
    print("=" * 80)
    print("  UNORTHODOX EVENT-DRIVEN STRATEGIES -- BACKTEST")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Interval: {INTERVAL}  |  Bars: {KLINE_LIMIT}  |  Max hold: {MAX_HOLD_BARS} bars")
    print(f"  Strategies: {len(STRATEGY_CLASSES)}")
    print("=" * 80)
    print()

    # --- Fetch data ---
    print("[1/3] Fetching Binance kline data...")
    market_data: Dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        market_data[sym] = fetch_binance_klines(sym, INTERVAL, KLINE_LIMIT)
        time.sleep(0.3)  # polite rate limit
    print(f"  Fetched {sum(len(v) for v in market_data.values())} total bars.\n")

    # --- Run backtests ---
    print("[2/3] Running backtests...")
    all_results: List[Dict[str, Any]] = []
    total_combos = len(STRATEGY_CLASSES) * len(SYMBOLS)
    done = 0

    for strat_cls in STRATEGY_CLASSES:
        strat_name = strat_cls().NAME
        for sym in SYMBOLS:
            done += 1
            print(f"  [{done}/{total_combos}] {strat_name} x {sym} ...", end=" ", flush=True)
            result = run_backtest(strat_cls, market_data[sym], sym)
            all_results.append(result)
            print(f"-> {result['trades']} trades, WR={result['win_rate']:.1f}%, PnL={result['total_pnl_pct']:+.2f}%")

    print()

    # --- Summary table ---
    print("[3/3] Results Summary")
    print("=" * 120)
    header = f"{'Strategy':<25} {'Symbol':<10} {'Trades':>6} {'Wins':>5} {'Loss':>5} {'T/O':>4} {'WR%':>7} {'TotalPnL%':>10} {'AvgPnL%':>9} {'Sharpe':>7} {'MaxDD%':>8} {'AvgBars':>8}"
    print(header)
    print("-" * 120)

    for r in all_results:
        line = (
            f"{r['strategy']:<25} {r['symbol']:<10} {r['trades']:>6} "
            f"{r['wins']:>5} {r['losses']:>5} {r['timeouts']:>4} "
            f"{r['win_rate']:>6.1f}% {r['total_pnl_pct']:>+9.2f}% "
            f"{r['avg_pnl_pct']:>+8.2f}% {r['sharpe']:>7.2f} "
            f"{r['max_drawdown_pct']:>7.2f}% {r['avg_bars_held']:>7.1f}"
        )
        print(line)

    print("-" * 120)

    # Aggregate per strategy
    print("\n--- Aggregate by Strategy ---")
    print(f"{'Strategy':<25} {'Trades':>6} {'WR%':>7} {'TotalPnL%':>10} {'Sharpe':>7}")
    print("-" * 60)
    strat_names_seen = []
    for strat_cls in STRATEGY_CLASSES:
        sname = strat_cls().NAME
        strat_results = [r for r in all_results if r["strategy"] == sname]
        total_trades = sum(r["trades"] for r in strat_results)
        total_wins = sum(r["wins"] for r in strat_results)
        total_pnl = sum(r["total_pnl_pct"] for r in strat_results)
        all_pnls_flat = []
        for r in strat_results:
            if r["trades"] > 0:
                all_pnls_flat.append(r["avg_pnl_pct"])
        wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
        avg_sharpe = np.mean([r["sharpe"] for r in strat_results]) if strat_results else 0
        print(f"{sname:<25} {total_trades:>6} {wr:>6.1f}% {total_pnl:>+9.2f}% {avg_sharpe:>7.2f}")

    print("=" * 60)

    # --- Save results ---
    output = {
        "backtest_date": datetime.datetime.utcnow().isoformat() + "Z",
        "config": {
            "symbols": SYMBOLS,
            "interval": INTERVAL,
            "kline_limit": KLINE_LIMIT,
            "max_hold_bars": MAX_HOLD_BARS,
        },
        "results": all_results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {RESULTS_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
