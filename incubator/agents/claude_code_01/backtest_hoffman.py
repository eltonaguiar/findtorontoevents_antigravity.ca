"""
Hoffman Family v1 — Multi-Symbol Multi-Timeframe Backtest
==========================================================

Tests all 7 Hoffman variations across 6 symbols on both 1h and 1d timeframes.

Usage:
    python backtest_hoffman.py

Symbols: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, ADAUSDT
Timeframes: 1h (500 bars), 1d (500 bars)
"""

import json
import sys
import time
import math
from datetime import datetime, timezone
from typing import List, Dict, Any

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))

from incubator.agents.claude_code_01.crypto_hoffman_family_v1 import (
    ALL_STRATEGIES, Signal
)

# ── Configuration ─────────────────────────────────────────────────────

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "ADAUSDT"]
TIMEFRAMES = ["1h", "1d"]
KLINE_LIMIT = 500

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]


# ── Data Fetching ─────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    """Fetch klines from Binance API with retries."""
    import requests

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=KLINE_COLUMNS)
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            if attempt == 2:
                print(f"    WARN: Failed to fetch {symbol} {interval}: {e}")
                return pd.DataFrame()
            time.sleep(1)
    return pd.DataFrame()


# ── Backtest Engine ───────────────────────────────────────────────────

def backtest_strategy_on_data(strategy_cls, df: pd.DataFrame, symbol: str,
                               max_hold_bars: int = 20) -> Dict[str, Any]:
    """
    Walk-forward backtest: slide through data, generate signals at each bar,
    simulate trades with TP/SL/time-stop.

    Returns metrics dict.
    """
    n = len(df)
    if n < 100:
        return _empty_metrics()

    trades = []
    open_trades = []

    # Walk forward from bar 60 to end, checking signals every bar
    for bar_idx in range(60, n):
        # Slice data up to current bar (no lookahead)
        data_slice = df.iloc[:bar_idx + 1].copy()

        # Check/close open trades first
        curr_high = float(df["high"].iloc[bar_idx])
        curr_low = float(df["low"].iloc[bar_idx])
        curr_close = float(df["close"].iloc[bar_idx])

        closed_indices = []
        for t_idx, trade in enumerate(open_trades):
            bars_held = bar_idx - trade["entry_bar"]

            # Check stop loss
            if trade["direction"] == "BUY":
                if curr_low <= trade["sl"]:
                    pnl_pct = (trade["sl"] - trade["entry"]) / trade["entry"] * 100
                    trades.append({**trade, "exit": trade["sl"], "pnl_pct": pnl_pct,
                                   "exit_type": "SL", "bars_held": bars_held})
                    closed_indices.append(t_idx)
                    continue
                if curr_high >= trade["tp"]:
                    pnl_pct = (trade["tp"] - trade["entry"]) / trade["entry"] * 100
                    trades.append({**trade, "exit": trade["tp"], "pnl_pct": pnl_pct,
                                   "exit_type": "TP", "bars_held": bars_held})
                    closed_indices.append(t_idx)
                    continue
            else:  # SELL/SHORT
                if curr_high >= trade["sl"]:
                    pnl_pct = (trade["entry"] - trade["sl"]) / trade["entry"] * 100
                    trades.append({**trade, "exit": trade["sl"], "pnl_pct": pnl_pct,
                                   "exit_type": "SL", "bars_held": bars_held})
                    closed_indices.append(t_idx)
                    continue
                if curr_low <= trade["tp"]:
                    pnl_pct = (trade["entry"] - trade["tp"]) / trade["entry"] * 100
                    trades.append({**trade, "exit": trade["tp"], "pnl_pct": pnl_pct,
                                   "exit_type": "TP", "bars_held": bars_held})
                    closed_indices.append(t_idx)
                    continue

            # Time stop
            if bars_held >= max_hold_bars:
                if trade["direction"] == "BUY":
                    pnl_pct = (curr_close - trade["entry"]) / trade["entry"] * 100
                else:
                    pnl_pct = (trade["entry"] - curr_close) / trade["entry"] * 100
                trades.append({**trade, "exit": curr_close, "pnl_pct": pnl_pct,
                               "exit_type": "TIME", "bars_held": bars_held})
                closed_indices.append(t_idx)

        # Remove closed trades (reverse order to maintain indices)
        for ci in sorted(closed_indices, reverse=True):
            open_trades.pop(ci)

        # Skip signal generation on most bars (every 3rd bar for speed)
        if bar_idx % 3 != 0:
            continue

        # Don't open new trades if we already have one open for this symbol
        if open_trades:
            continue

        # Generate signals
        try:
            signals = strategy_cls.generate_signals(data_slice, symbol)
        except Exception:
            continue

        for sig in signals:
            # Only take BUY signals (direction normalization)
            direction = sig.direction.upper()
            if direction not in ("BUY", "SELL"):
                continue

            open_trades.append({
                "direction": direction,
                "entry": sig.entry_price,
                "tp": sig.take_profit,
                "sl": sig.stop_loss,
                "entry_bar": bar_idx,
                "confidence": sig.confidence,
            })
            break  # One trade at a time

    # Close any remaining open trades at last bar price
    if open_trades:
        last_close = float(df["close"].iloc[-1])
        for trade in open_trades:
            bars_held = n - 1 - trade["entry_bar"]
            if trade["direction"] == "BUY":
                pnl_pct = (last_close - trade["entry"]) / trade["entry"] * 100
            else:
                pnl_pct = (trade["entry"] - last_close) / trade["entry"] * 100
            trades.append({**trade, "exit": last_close, "pnl_pct": pnl_pct,
                           "exit_type": "EOD", "bars_held": bars_held})

    return _compute_metrics(trades)


def _empty_metrics() -> Dict[str, Any]:
    return {
        "total_trades": 0, "wins": 0, "losses": 0,
        "win_rate": 0.0, "total_pnl_pct": 0.0, "avg_pnl_pct": 0.0,
        "sharpe": 0.0, "max_drawdown_pct": 0.0,
        "profit_factor": 0.0,
        "tp_exits": 0, "sl_exits": 0, "time_exits": 0,
        "avg_bars_held": 0.0,
    }


def _compute_metrics(trades: List[Dict]) -> Dict[str, Any]:
    if not trades:
        return _empty_metrics()

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total = len(pnls)

    total_pnl = sum(pnls)
    avg_pnl = total_pnl / total if total > 0 else 0

    # Sharpe (annualized approximation)
    if len(pnls) > 1:
        std = np.std(pnls)
        sharpe = (avg_pnl / std * math.sqrt(252)) if std > 0 else 0
    else:
        sharpe = 0

    # Max drawdown
    equity = [100.0]
    for p in pnls:
        equity.append(equity[-1] * (1 + p / 100))
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Profit factor
    gross_wins = sum(wins) if wins else 0
    gross_losses = abs(sum(losses)) if losses else 0
    pf = gross_wins / gross_losses if gross_losses > 0 else (
        float("inf") if gross_wins > 0 else 0
    )

    # Exit type counts
    tp_exits = sum(1 for t in trades if t.get("exit_type") == "TP")
    sl_exits = sum(1 for t in trades if t.get("exit_type") == "SL")
    time_exits = sum(1 for t in trades if t.get("exit_type") in ("TIME", "EOD"))
    avg_bars = np.mean([t.get("bars_held", 0) for t in trades])

    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0,
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 3),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else 999.0,
        "tp_exits": tp_exits,
        "sl_exits": sl_exits,
        "time_exits": time_exits,
        "avg_bars_held": round(avg_bars, 1),
    }


# ── Main Runner ───────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("HOFFMAN FAMILY v1 — MULTI-SYMBOL MULTI-TIMEFRAME BACKTEST")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"Bars per symbol: {KLINE_LIMIT}")
    print("=" * 80)

    # Fetch all data first
    print("\n[1/3] Fetching market data...")
    all_data: Dict[str, Dict[str, pd.DataFrame]] = {}  # {tf: {sym: df}}

    for tf in TIMEFRAMES:
        all_data[tf] = {}
        for sym in SYMBOLS:
            print(f"  Fetching {sym} {tf}...", end=" ", flush=True)
            df = fetch_klines(sym, tf, KLINE_LIMIT)
            all_data[tf][sym] = df
            print(f"{len(df)} bars")
            time.sleep(0.15)  # Rate limit

    # Run backtests
    print("\n[2/3] Running backtests...")
    results = []
    strategy_summaries = {}  # For final ranking

    for strategy_cls in ALL_STRATEGIES:
        strat_name = strategy_cls.NAME
        print(f"\n{'-' * 70}")
        print(f"  Strategy: {strat_name}")
        print(f"  {strategy_cls.DESCRIPTION}")
        print(f"{'-' * 70}")

        strat_total_trades = 0
        strat_total_wins = 0
        strat_total_pnl = 0.0
        strat_all_pnls = []

        for tf in TIMEFRAMES:
            max_hold = 20 if tf == "1h" else 10  # Adjust hold for daily

            for sym in SYMBOLS:
                df = all_data[tf][sym]
                if df.empty or len(df) < 100:
                    print(f"    {sym} {tf}: SKIP (insufficient data)")
                    continue

                metrics = backtest_strategy_on_data(
                    strategy_cls, df, sym, max_hold_bars=max_hold
                )

                result_entry = {
                    "strategy": strat_name,
                    "symbol": sym,
                    "timeframe": tf,
                    "bars": len(df),
                    **metrics,
                }
                results.append(result_entry)

                strat_total_trades += metrics["total_trades"]
                strat_total_wins += metrics["wins"]
                strat_total_pnl += metrics["total_pnl_pct"]

                # Color code win rate
                wr = metrics["win_rate"]
                wr_indicator = "+++" if wr >= 55 else ("++" if wr >= 45 else ("+" if wr >= 35 else "-"))

                print(f"    {sym:8s} {tf:3s} | "
                      f"trades={metrics['total_trades']:3d} "
                      f"WR={wr:5.1f}% [{wr_indicator}] "
                      f"PnL={metrics['total_pnl_pct']:+7.2f}% "
                      f"Sharpe={metrics['sharpe']:+5.2f} "
                      f"MDD={metrics['max_drawdown_pct']:5.2f}% "
                      f"PF={metrics['profit_factor']:5.2f} "
                      f"TP/SL/T={metrics['tp_exits']}/{metrics['sl_exits']}/{metrics['time_exits']}")

        overall_wr = (strat_total_wins / strat_total_trades * 100
                      if strat_total_trades > 0 else 0)
        strategy_summaries[strat_name] = {
            "total_trades": strat_total_trades,
            "overall_win_rate": round(overall_wr, 1),
            "total_pnl": round(strat_total_pnl, 2),
        }
        print(f"\n    TOTAL: {strat_total_trades} trades, "
              f"WR={overall_wr:.1f}%, PnL={strat_total_pnl:+.2f}%")

    # ── Summary & Rankings ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SUMMARY & RANKINGS")
    print("=" * 80)

    # Rank strategies by total PnL
    print("\n[A] Strategy Rankings by Total PnL%:")
    sorted_strats = sorted(strategy_summaries.items(),
                           key=lambda x: x[1]["total_pnl"], reverse=True)
    for rank, (name, s) in enumerate(sorted_strats, 1):
        print(f"  #{rank} {name:30s} | trades={s['total_trades']:4d} "
              f"WR={s['overall_win_rate']:5.1f}% "
              f"PnL={s['total_pnl']:+8.2f}%")

    # Best strategy per symbol per timeframe
    print("\n[B] Best Strategy per Symbol per Timeframe:")
    for tf in TIMEFRAMES:
        print(f"\n  --- {tf} ---")
        for sym in SYMBOLS:
            sym_results = [r for r in results
                           if r["symbol"] == sym and r["timeframe"] == tf
                           and r["total_trades"] > 0]
            if not sym_results:
                print(f"    {sym}: No trades")
                continue
            best = max(sym_results, key=lambda r: r["total_pnl_pct"])
            print(f"    {sym:8s}: {best['strategy']:30s} "
                  f"WR={best['win_rate']:5.1f}% "
                  f"PnL={best['total_pnl_pct']:+7.2f}% "
                  f"Sharpe={best['sharpe']:+5.2f} "
                  f"({best['total_trades']} trades)")

    # Strategies that beat 50% WR threshold
    print("\n[C] Strategies with WR > 50% (viable for paper trading):")
    viable = [r for r in results if r["win_rate"] > 50 and r["total_trades"] >= 3]
    if viable:
        viable.sort(key=lambda r: r["total_pnl_pct"], reverse=True)
        for r in viable[:20]:
            print(f"    {r['strategy']:30s} {r['symbol']:8s} {r['timeframe']:3s} | "
                  f"WR={r['win_rate']:5.1f}% PnL={r['total_pnl_pct']:+7.2f}% "
                  f"Sharpe={r['sharpe']:+5.2f} ({r['total_trades']} trades)")
    else:
        print("    None found. Consider relaxing parameters.")

    # Highest Sharpe
    print("\n[D] Top 10 by Sharpe Ratio:")
    sharpe_sorted = sorted(
        [r for r in results if r["total_trades"] >= 3],
        key=lambda r: r["sharpe"], reverse=True
    )
    for r in sharpe_sorted[:10]:
        print(f"    {r['strategy']:30s} {r['symbol']:8s} {r['timeframe']:3s} | "
              f"Sharpe={r['sharpe']:+5.2f} WR={r['win_rate']:5.1f}% "
              f"PnL={r['total_pnl_pct']:+7.2f}% MDD={r['max_drawdown_pct']:5.2f}%")

    # Save results to JSON
    output_path = str(__import__("pathlib").Path(__file__).parent / "backtest_hoffman_results.json")
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "symbols": SYMBOLS,
            "timeframes": TIMEFRAMES,
            "bars_per_symbol": KLINE_LIMIT,
        },
        "strategy_rankings": sorted_strats,
        "all_results": results,
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
