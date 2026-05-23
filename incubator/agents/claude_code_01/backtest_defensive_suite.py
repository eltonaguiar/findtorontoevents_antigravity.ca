"""
Backtest runner for the Defensive Strategy Suite (crypto_defensive_suite_v1.py).

Tests 8 defensive strategy classes against REAL Binance OHLCV data using
a walk-forward approach across multiple symbols and timeframes.

Strategies tested:
  1. TrendGuard_Long_v1       - Trend-following long entries
  2. TrendGuard_Short_v1      - Trend-following short entries
  3. VolRegime_Filter_v1      - Volatility regime filtering
  4. MTF_Trend_v1             - Multi-timeframe trend alignment
  5. MeanRev_Timing_v1        - Mean reversion timing
  6. Adaptive_Regime_v1       - Adaptive regime switching
  7. Cascade_Recovery_v1      - Cascade sell recovery
  8. Divergence_Entry_v1      - Divergence-based entries

Dependencies: numpy, requests, json (NO pandas)

Usage: python backtest_defensive_suite.py
"""

import sys
import os

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import math
import time
import importlib.util
import traceback
import numpy as np
import requests
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STRATEGIES = {
    "TrendGuard_Long": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "TrendGuardLongStrategy",
        "strategy_name": "TrendGuard_Long_v1",
    },
    "TrendGuard_Short": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "TrendGuardShortStrategy",
        "strategy_name": "TrendGuard_Short_v1",
    },
    "VolRegime_Filter": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "VolatilityRegimeFilterStrategy",
        "strategy_name": "VolRegime_Filter_v1",
    },
    "MTF_Trend": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "MultiTimeframeTrendStrategy",
        "strategy_name": "MTF_Trend_v1",
    },
    "MeanRev_Timing": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "MeanReversionTimingStrategy",
        "strategy_name": "MeanRev_Timing_v1",
    },
    "Adaptive_Regime": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "AdaptiveRegimeStrategy",
        "strategy_name": "Adaptive_Regime_v1",
    },
    "Cascade_Recovery": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "CascadeSellRecoveryStrategy",
        "strategy_name": "Cascade_Recovery_v1",
    },
    "Divergence_Entry": {
        "file": "crypto_defensive_suite_v1.py",
        "class": "DivergenceEntryStrategy",
        "strategy_name": "Divergence_Entry_v1",
    },
}

# Symbols split by tier for timeframe coverage
ALL_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
               "BNBUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
TOP4_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]

# Timeframe plan:
#   1h  -> all 8 symbols
#   4h  -> top 4 symbols
#   1d  -> top 4 symbols
TIMEFRAME_PLAN = [
    ("1h", ALL_SYMBOLS),
    ("4h", TOP4_SYMBOLS),
    ("1d", TOP4_SYMBOLS),
]

KLINE_LIMIT = 500
MAX_HOLD_BARS = 50   # max bars to hold a trade before timeout
MIN_BARS_START = 200  # need enough history for indicators

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"


# ---------------------------------------------------------------------------
# DataFrame-like wrapper so strategies can use data['close'].values.astype(float)
# ---------------------------------------------------------------------------

class _NpColumn:
    """Wraps a numpy array to support .values.astype(float) chaining."""
    def __init__(self, arr: np.ndarray):
        self._arr = arr
        self.values = arr

    def astype(self, dtype):
        return self._arr.astype(dtype)


class NpDataFrame:
    """Minimal dict-of-arrays wrapper that mimics pd.DataFrame access patterns.

    Supports:
      - data['close']           -> _NpColumn (has .values)
      - data['close'].values    -> np.ndarray
      - len(data)               -> number of rows
      - Slicing is done externally by building a new NpDataFrame from sliced arrays.
    """

    def __init__(self, columns: dict):
        self._columns = {k: np.asarray(v, dtype=float) for k, v in columns.items()}
        # All columns must have same length
        lengths = {len(v) for v in self._columns.values()}
        if lengths:
            self._len = max(lengths)
        else:
            self._len = 0

    def __getitem__(self, key: str) -> _NpColumn:
        return _NpColumn(self._columns[key])

    def __len__(self) -> int:
        return self._len

    def slice_to(self, end: int) -> "NpDataFrame":
        """Return a new NpDataFrame with columns sliced to [:end]."""
        return NpDataFrame({k: v[:end] for k, v in self._columns.items()})


# ---------------------------------------------------------------------------
# Binance data fetcher  (returns dict of numpy arrays)
# ---------------------------------------------------------------------------

def fetch_binance_data(symbol: str, interval: str, limit: int = KLINE_LIMIT) -> dict:
    """Fetch OHLCV klines from Binance public API.

    Returns dict with keys: open, high, low, close, volume  (numpy arrays).
    Returns empty dict on failure.
    """
    url = (f"https://api.binance.com/api/v3/klines"
           f"?symbol={symbol}&interval={interval}&limit={limit}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        klines = r.json()
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {symbol} {interval}: {e}")
        return {}

    if not klines:
        return {}

    data = {
        "open": np.array([float(k[1]) for k in klines]),
        "high": np.array([float(k[2]) for k in klines]),
        "low": np.array([float(k[3]) for k in klines]),
        "close": np.array([float(k[4]) for k in klines]),
        "volume": np.array([float(k[5]) for k in klines]),
    }
    return data


# ---------------------------------------------------------------------------
# Strategy loader
# ---------------------------------------------------------------------------

def load_strategy_class(file_name: str, class_name: str):
    """Dynamically load a strategy class from a .py file."""
    file_path = SCRIPT_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Strategy file not found: {file_path}")
    spec = importlib.util.spec_from_file_location(class_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


# ---------------------------------------------------------------------------
# Walk-forward backtester  (pure numpy, no pandas)
# ---------------------------------------------------------------------------

def walk_forward_backtest(strategy, data: dict, symbol: str, interval: str):
    """
    Walk-forward backtest: for each bar from MIN_BARS_START to end,
    pass data[:i] to generate_signals. If a signal fires, simulate
    the trade using subsequent bars (check TP/SL hit order via high/low).

    data: dict with keys open, high, low, close, volume (numpy arrays).
    Returns dict with full stats and list of individual trades.
    """
    n = len(data["close"])
    start_bar = min(MIN_BARS_START, n - 20)
    if start_bar < 50:
        return None  # not enough data

    # Build a full NpDataFrame once; slicing creates lightweight views
    full_frame = NpDataFrame(data)

    # Keep raw arrays for fast future-bar lookups
    highs = data["high"]
    lows = data["low"]
    closes = data["close"]

    trades = []
    active_trade_end = 0  # prevents overlapping trades

    for i in range(start_bar, n):
        if i <= active_trade_end:
            continue  # still in a trade, skip

        window = full_frame.slice_to(i + 1)
        try:
            signals = strategy.generate_signals(window, symbol)
        except Exception:
            continue

        if not signals:
            continue

        sig = signals[-1]  # take the latest signal

        entry = sig.entry_price
        tp = sig.take_profit
        sl = sig.stop_loss
        direction = sig.direction
        confidence = getattr(sig, 'confidence', 0.5)

        if entry <= 0 or tp <= 0 or sl <= 0:
            continue

        # Simulate trade forward
        outcome = None
        exit_price = entry
        bars_held = 0

        for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
            bars_held += 1

            if direction == "BUY":
                # Check SL first on same bar (conservative)
                if lows[j] <= sl:
                    outcome = "LOSS"
                    exit_price = sl
                    break
                if highs[j] >= tp:
                    outcome = "WIN"
                    exit_price = tp
                    break
            else:  # SELL / SHORT
                if highs[j] >= sl:
                    outcome = "LOSS"
                    exit_price = sl
                    break
                if lows[j] <= tp:
                    outcome = "WIN"
                    exit_price = tp
                    break

        if outcome is None:
            # Timeout: close at last reachable bar's close
            last_idx = min(i + MAX_HOLD_BARS, n - 1)
            exit_price = closes[last_idx]
            bars_held = last_idx - i
            if direction == "BUY":
                outcome = "WIN" if exit_price > entry else "LOSS"
            else:
                outcome = "WIN" if exit_price < entry else "LOSS"

        # PnL calculation
        if direction == "BUY":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        trades.append({
            "bar_index": i,
            "direction": direction,
            "entry": entry,
            "exit": exit_price,
            "tp": tp,
            "sl": sl,
            "outcome": outcome,
            "pnl_pct": pnl_pct,
            "bars_held": bars_held,
            "confidence": confidence,
        })

        active_trade_end = i + bars_held  # block overlapping trades

    return _compute_stats(trades)


def _compute_stats(trades: list) -> dict:
    """Compute comprehensive stats from a list of trade dicts."""
    if not trades:
        return {
            "total_trades": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "total_pnl_pct": 0.0, "max_drawdown_pct": 0.0,
            "sharpe": 0.0, "profit_factor": 0.0, "avg_bars_held": 0.0,
            "long_wins": 0, "long_total": 0, "short_wins": 0, "short_total": 0,
            "trades": [],
        }

    total = len(trades)
    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    losses = total - wins
    pnls = np.array([t["pnl_pct"] for t in trades])
    total_pnl = float(np.sum(pnls))
    win_rate = wins / total * 100 if total > 0 else 0.0

    # Long/Short breakdown
    long_trades = [t for t in trades if t["direction"] == "BUY"]
    short_trades = [t for t in trades if t["direction"] == "SELL"]
    long_wins = sum(1 for t in long_trades if t["outcome"] == "WIN")
    short_wins = sum(1 for t in short_trades if t["outcome"] == "WIN")

    # Max drawdown (cumulative PnL curve)
    cumulative = np.cumsum(pnls)
    running_peak = np.maximum.accumulate(cumulative)
    drawdowns = running_peak - cumulative
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Sharpe ratio (per-trade, annualized roughly)
    if total >= 2:
        mean_pnl = float(np.mean(pnls))
        std_pnl = float(np.std(pnls, ddof=1))
        if std_pnl < 0.001:
            std_pnl = 0.001
        sharpe_per_trade = mean_pnl / std_pnl
        # Rough annualization: assume ~250 trading days / avg_bars_held
        avg_bars = sum(t["bars_held"] for t in trades) / total
        trades_per_year = max(250 / max(avg_bars, 1), 1)
        sharpe = sharpe_per_trade * math.sqrt(trades_per_year)
        sharpe = max(-99.99, min(99.99, sharpe))
    else:
        sharpe = 0.0

    # Profit factor
    gross_wins = float(np.sum(pnls[pnls > 0])) if np.any(pnls > 0) else 0.0
    gross_losses = float(np.abs(np.sum(pnls[pnls < 0]))) if np.any(pnls < 0) else 0.0
    if gross_losses > 0:
        profit_factor = gross_wins / gross_losses
    elif gross_wins > 0:
        profit_factor = 999.0
    else:
        profit_factor = 0.0

    # Average bars held
    avg_bars_held = sum(t["bars_held"] for t in trades) / total if total > 0 else 0.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_bars_held": round(avg_bars_held, 1),
        "long_wins": long_wins,
        "long_total": len(long_trades),
        "short_wins": short_wins,
        "short_total": len(short_trades),
        "trades": trades,  # kept for JSON export
    }


# ---------------------------------------------------------------------------
# Aggregate rankings
# ---------------------------------------------------------------------------

def compute_aggregate_rankings(results: list) -> list:
    """Aggregate results per strategy across all symbols and timeframes."""
    strat_groups = defaultdict(list)
    for r in results:
        strat_groups[r["strategy"]].append(r)

    rankings = []
    for strat_name, entries in strat_groups.items():
        total_trades = sum(e["total_trades"] for e in entries)
        if total_trades == 0:
            continue

        # Weighted averages by trade count
        avg_wr = sum(e["win_rate"] * e["total_trades"] for e in entries) / total_trades
        avg_pnl = sum(e["total_pnl_pct"] for e in entries)
        avg_sharpe = sum(e["sharpe"] * e["total_trades"] for e in entries) / total_trades
        avg_pf = sum(e["profit_factor"] * e["total_trades"] for e in entries) / total_trades

        # Best / worst by PnL
        best = max(entries, key=lambda e: e["total_pnl_pct"])
        worst = min(entries, key=lambda e: e["total_pnl_pct"])

        rankings.append({
            "strategy": strat_name,
            "total_trades": total_trades,
            "avg_win_rate": round(avg_wr, 1),
            "total_pnl_pct": round(avg_pnl, 2),
            "avg_sharpe": round(avg_sharpe, 2),
            "avg_profit_factor": round(avg_pf, 2),
            "best_symbol": f"{best['symbol']}_{best['timeframe']}",
            "best_pnl": round(best["total_pnl_pct"], 2),
            "worst_symbol": f"{worst['symbol']}_{worst['timeframe']}",
            "worst_pnl": round(worst["total_pnl_pct"], 2),
            "num_configs": len(entries),
        })

    rankings.sort(key=lambda x: x["total_pnl_pct"], reverse=True)
    return rankings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    run_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    print(f"\n{'=' * 100}")
    print(f"  DEFENSIVE SUITE BACKTEST -- {run_ts}")
    print(f"{'=' * 100}")
    print(f"  Strategies : {len(STRATEGIES)}")
    print(f"  Symbols    : {', '.join(ALL_SYMBOLS)}")
    print(f"  Timeframes : 1h (all), 4h (top4), 1d (top4)")
    print(f"  Kline bars : {KLINE_LIMIT}")
    print(f"  Max hold   : {MAX_HOLD_BARS} bars")
    print(f"{'=' * 100}\n")

    # ------------------------------------------------------------------
    # Phase 1: Fetch all market data
    # ------------------------------------------------------------------
    print("[Phase 1] Fetching market data from Binance...\n")

    market_data = {}  # key = (symbol, interval) -> dict of numpy arrays
    fetch_count = 0

    for interval, symbols in TIMEFRAME_PLAN:
        for sym in symbols:
            key = (sym, interval)
            if key in market_data:
                continue
            print(f"  Fetching {sym} {interval}...", end=" ", flush=True)
            data = fetch_binance_data(sym, interval, KLINE_LIMIT)
            if data:
                market_data[key] = data
                print(f"{len(data['close'])} bars OK")
            else:
                print("FAILED")
            fetch_count += 1
            time.sleep(0.5)  # rate limit

    print(f"\n  Total data sets fetched: {len(market_data)} / {fetch_count} attempted\n")

    if not market_data:
        print("No market data fetched. Exiting.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 2: Load strategies
    # ------------------------------------------------------------------
    print("[Phase 2] Loading strategy classes...\n")

    loaded_strategies = {}
    for strat_key, strat_info in STRATEGIES.items():
        try:
            StratClass = load_strategy_class(strat_info["file"], strat_info["class"])
            loaded_strategies[strat_key] = StratClass()
            print(f"  {strat_key}: {strat_info['class']} loaded OK")
        except Exception as e:
            print(f"  {strat_key}: FAILED to load - {e}")
            traceback.print_exc()

    if not loaded_strategies:
        print("\nNo strategies loaded. Exiting.")
        sys.exit(1)

    print(f"\n  Loaded: {len(loaded_strategies)}/{len(STRATEGIES)} strategies\n")

    # ------------------------------------------------------------------
    # Phase 3: Walk-forward backtest
    # ------------------------------------------------------------------
    print(f"[Phase 3] Running walk-forward backtests...\n")

    results = []
    total_combos = sum(
        len(syms) for _, syms in TIMEFRAME_PLAN
    ) * len(loaded_strategies)
    combo_count = 0

    for strat_key, strategy in loaded_strategies.items():
        print(f"\n{'---' * 34}")
        print(f"  Strategy: {strat_key}  ({STRATEGIES[strat_key]['strategy_name']})")
        print(f"{'---' * 34}")

        for interval, symbols in TIMEFRAME_PLAN:
            for sym in symbols:
                combo_count += 1
                key = (sym, interval)
                if key not in market_data:
                    continue

                data = market_data[key]
                pct = combo_count / total_combos * 100

                print(f"  [{combo_count}/{total_combos} {pct:4.0f}%] "
                      f"{strat_key} x {sym} x {interval}...", end=" ", flush=True)

                try:
                    stats = walk_forward_backtest(strategy, data, sym, interval)
                except Exception as e:
                    print(f"ERROR: {e}")
                    traceback.print_exc()
                    continue

                if stats is None or stats["total_trades"] == 0:
                    print("0 trades")
                    continue

                # Strip raw trades for summary print (keep in results)
                trade_list = stats.pop("trades", [])

                print(f"{stats['total_trades']:>3} trades | "
                      f"WR {stats['win_rate']:>5.1f}% | "
                      f"PnL {stats['total_pnl_pct']:>+8.2f}% | "
                      f"DD {stats['max_drawdown_pct']:>5.2f}% | "
                      f"Sharpe {stats['sharpe']:>6.2f} | "
                      f"PF {stats['profit_factor']:>5.2f} | "
                      f"AvgBars {stats['avg_bars_held']:>4.1f} | "
                      f"L:{stats['long_wins']}/{stats['long_total']} "
                      f"S:{stats['short_wins']}/{stats['short_total']}")

                result_entry = {
                    "strategy": strat_key,
                    "strategy_name": STRATEGIES[strat_key]["strategy_name"],
                    "symbol": sym,
                    "timeframe": interval,
                    **stats,
                    "trades_detail": trade_list,
                }
                results.append(result_entry)

    # ------------------------------------------------------------------
    # Phase 4: Summary tables
    # ------------------------------------------------------------------
    print(f"\n\n{'=' * 120}")
    print("  DETAILED RESULTS TABLE")
    print(f"{'=' * 120}")

    header = (f"{'Strategy':<22} | {'Symbol':<10} | {'TF':<4} | "
              f"{'Trades':>6} | {'WR%':>6} | {'PnL%':>9} | "
              f"{'MaxDD%':>7} | {'Sharpe':>7} | {'PF':>6} | "
              f"{'AvgBars':>7} | {'L W/T':>7} | {'S W/T':>7}")
    print(header)
    print("-" * 120)

    # Sort by strategy name, then symbol, then timeframe
    results_sorted = sorted(results, key=lambda r: (r["strategy"], r["symbol"], r["timeframe"]))
    for r in results_sorted:
        line = (f"{r['strategy']:<22} | {r['symbol']:<10} | {r['timeframe']:<4} | "
                f"{r['total_trades']:>6} | {r['win_rate']:>5.1f}% | "
                f"{r['total_pnl_pct']:>+8.2f}% | {r['max_drawdown_pct']:>6.2f}% | "
                f"{r['sharpe']:>7.2f} | {r['profit_factor']:>5.2f} | "
                f"{r['avg_bars_held']:>6.1f} | "
                f"{r['long_wins']}/{r['long_total']:>3} | "
                f"{r['short_wins']}/{r['short_total']:>3}")
        print(line)

    # Aggregate rankings
    print(f"\n\n{'=' * 120}")
    print("  STRATEGY RANKINGS (All Symbols Combined)")
    print(f"{'=' * 120}")

    rankings = compute_aggregate_rankings(results)

    rank_header = (f"{'#':>2} {'Strategy':<22} | {'Total Trades':>12} | "
                   f"{'Avg WR%':>8} | {'Total PnL%':>11} | "
                   f"{'Avg Sharpe':>10} | {'Avg PF':>7} | "
                   f"{'Best Config':>20} | {'Worst Config':>20}")
    print(rank_header)
    print("-" * 120)

    for idx, rk in enumerate(rankings, 1):
        line = (f"{idx:>2} {rk['strategy']:<22} | {rk['total_trades']:>12} | "
                f"{rk['avg_win_rate']:>7.1f}% | {rk['total_pnl_pct']:>+10.2f}% | "
                f"{rk['avg_sharpe']:>10.2f} | {rk['avg_profit_factor']:>6.2f} | "
                f"{rk['best_symbol']:>15} {rk['best_pnl']:>+.1f}% | "
                f"{rk['worst_symbol']:>15} {rk['worst_pnl']:>+.1f}%")
        print(line)

    # Grade strategies
    print(f"\n\n{'=' * 80}")
    print("  STRATEGY GRADES")
    print(f"{'=' * 80}")

    for rk in rankings:
        grade = "F"
        if rk["avg_win_rate"] >= 60 and rk["avg_sharpe"] >= 2.0 and rk["total_pnl_pct"] > 0:
            grade = "A"
        elif rk["avg_win_rate"] >= 55 and rk["avg_sharpe"] >= 1.5 and rk["total_pnl_pct"] > 0:
            grade = "B"
        elif rk["avg_win_rate"] >= 50 and rk["avg_sharpe"] >= 1.0 and rk["total_pnl_pct"] > 0:
            grade = "C"
        elif rk["avg_win_rate"] >= 45 and rk["total_pnl_pct"] > -5:
            grade = "D"

        stars = {"A": " *** PROVEN ***", "B": " ** STRONG **", "C": " * VIABLE *",
                 "D": "", "F": " (needs work)"}

        print(f"  [{grade}] {rk['strategy']:<22} "
              f"WR {rk['avg_win_rate']:.1f}% | "
              f"Sharpe {rk['avg_sharpe']:.2f} | "
              f"PnL {rk['total_pnl_pct']:+.1f}% | "
              f"Trades {rk['total_trades']}{stars.get(grade, '')}")

    print(f"\n{'=' * 80}\n")

    # ------------------------------------------------------------------
    # Phase 5: Save to JSON
    # ------------------------------------------------------------------
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "defensive_suite_backtest.json"

    # Strip trade details for JSON to keep file manageable
    results_export = []
    for r in results:
        r_copy = {k: v for k, v in r.items() if k != "trades_detail"}
        # Include trade summary (count per direction)
        r_copy["trade_count_long"] = r.get("long_total", 0)
        r_copy["trade_count_short"] = r.get("short_total", 0)
        results_export.append(r_copy)

    export_data = {
        "meta": {
            "run_timestamp": run_ts,
            "kline_limit": KLINE_LIMIT,
            "max_hold_bars": MAX_HOLD_BARS,
            "min_bars_start": MIN_BARS_START,
            "symbols_1h": ALL_SYMBOLS,
            "symbols_4h_1d": TOP4_SYMBOLS,
            "strategies_tested": len(STRATEGIES),
            "total_results": len(results_export),
        },
        "individual_results": results_export,
        "aggregate_rankings": rankings,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"Results saved to: {output_path}")
    print(f"Total strategy-symbol-timeframe combos with trades: {len(results)}")
    print(f"Done.\n")

    return results


if __name__ == "__main__":
    main()
