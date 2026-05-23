"""
Backtest all Hoffman IRB variations against historical 15-min Binance data.

Fetches 1000 bars (~10 days of 15m data), walks forward bar-by-bar,
generates signals at each bar, simulates TP/SL hits, and records
results to the audit trail database.

Usage:
    python backtest_hoffman_variations.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from baby_strategies.hoffman_variations import VARIATIONS, hoffman_scalper_signals
from baby_strategies.hoffman_irb_ema_angle import SYMBOLS

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]

# Also add the 3 original hold-time variants
# from paper_trading.strategies.hoffman_irb_strategies import (
#     _ema, _atr, _detect_irb_at, _ema_angle_degrees, _htf_ema_trend, IRB_RETRACE_PCT,
# )


def fetch_historical(symbol: str, interval: str = "15m", limit: int = 1000) -> pd.DataFrame:
    """Fetch historical klines from Binance."""
    url = "https://api.binance.com/api/v3/klines"
    resp = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json(), columns=KLINE_COLUMNS)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


def simulate_trades(signals_by_bar, df, max_hold_bars=16):
    """Walk-forward simulation: enter on signal, exit on TP/SL/time.

    Returns list of trade dicts with PnL info. Position size is derived from the signal's confidence (treated as a Kelly‑scaled fraction of equity)."""
    trades = []
    position = None  # {entry_bar, entry_price, tp, sl, direction, reason, conf}

    for bar_idx in range(len(df)):
        price = df["close"].iloc[bar_idx]
        high = df["high"].iloc[bar_idx]
        low = df["low"].iloc[bar_idx]

        # Check if open position hits TP/SL
        if position is not None:
            entry = position["entry_price"]
            hold_bars = bar_idx - position["entry_bar"]
            conf = position["conf"]  # confidence used as position fraction (0‑1)

            if position["direction"] == "BUY":
                # Check SL first (more conservative)
                if low <= position["sl"]:
                    raw_pct = (position["sl"] - entry) / entry * 100
                    pnl_pct = raw_pct * conf
                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": bar_idx,
                        "entry_price": entry,
                        "exit_price": position["sl"],
                        "direction": "LONG",
                        "pnl_pct": pnl_pct,
                        "exit_reason": "SL",
                        "hold_bars": hold_bars,
                        "confidence": conf,
                    })
                    print("TRADE:", trades[-1])
                    position = None
                    continue
                elif high >= position["tp"]:
                    raw_pct = (position["tp"] - entry) / entry * 100
                    pnl_pct = raw_pct * conf
                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": bar_idx,
                        "entry_price": entry,
                        "exit_price": position["tp"],
                        "direction": "LONG",
                        "pnl_pct": pnl_pct,
                        "exit_reason": "TP",
                        "hold_bars": hold_bars,
                        "confidence": conf,
                    })
                    position = None
                    continue
            else:  # SELL/SHORT
                if high >= position["sl"]:
                    raw_pct = (entry - position["sl"]) / entry * 100
                    pnl_pct = raw_pct * conf
                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": bar_idx,
                        "entry_price": entry,
                        "exit_price": position["sl"],
                        "direction": "SHORT",
                        "pnl_pct": pnl_pct,
                        "exit_reason": "SL",
                        "hold_bars": hold_bars,
                        "confidence": conf,
                    })
                    position = None
                    continue
                elif low <= position["tp"]:
                    raw_pct = (entry - position["tp"]) / entry * 100
                    pnl_pct = raw_pct * conf
                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": bar_idx,
                        "entry_price": entry,
                        "exit_price": position["tp"],
                        "direction": "SHORT",
                        "pnl_pct": pnl_pct,
                        "exit_reason": "TP",
                        "hold_bars": hold_bars,
                        "confidence": conf,
                    })
                    position = None
                    continue

            # Time stop
            if hold_bars >= max_hold_bars:
                if position["direction"] == "BUY":
                    raw_pct = (price - entry) / entry * 100
                else:
                    raw_pct = (entry - price) / entry * 100
                pnl_pct = raw_pct * conf
                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": bar_idx,
                    "entry_price": entry,
                    "exit_price": price,
                    "direction": "LONG" if position["direction"] == "BUY" else "SHORT",
                    "pnl_pct": pnl_pct,
                    "exit_reason": "TIME",
                    "hold_bars": hold_bars,
                    "confidence": conf,
                })
                position = None
                continue

        # Try to enter if no position and we have a signal
        if position is None and bar_idx in signals_by_bar:
            sig = signals_by_bar[bar_idx]
            position = {
                "entry_bar": bar_idx,
                "entry_price": sig.entry_price,
                "tp": sig.take_profit,
                "sl": sig.stop_loss,
                "direction": sig.direction,
                "conf": sig.confidence,
                "reason": sig.reason,
            }

    return trades


def backtest_variation(variation_fn, df, symbol, max_hold_bars=16):
    """Run a single variation over the full DataFrame, generating signals at each bar."""
    signals_by_bar = {}
    warmup = 100  # need enough bars for indicators

    for i in range(warmup, len(df)):
        # Pass a slice of data up to bar i
        subset = df.iloc[:i + 1].reset_index(drop=True)
        try:
            sigs = variation_fn(subset, symbol)
        except Exception:
            continue

        if sigs:
            # Take the highest-confidence signal
            best = max(sigs, key=lambda s: s.confidence)
            signals_by_bar[i] = best

    trades = simulate_trades(signals_by_bar, df, max_hold_bars)
    return trades, len(signals_by_bar)


def compute_metrics(trades):
    """Compute backtest metrics from trade list."""
    if not trades:
        return {
            "total_trades": 0, "win_rate": 0, "avg_pnl_pct": 0,
            "total_pnl_pct": 0, "profit_factor": 0, "max_drawdown_pct": 0,
            "avg_hold_bars": 0, "tp_exits": 0, "sl_exits": 0, "time_exits": 0,
        }

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    total_pnl = sum(t["pnl_pct"] for t in trades)

    gross_profit = sum(t["pnl_pct"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0.001

    # Max drawdown (sequential PnL curve)
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t["pnl_pct"])
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        dd = peak - e
        max_dd = max(max_dd, dd)

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl_pct": round(total_pnl / len(trades), 3),
        "total_pnl_pct": round(total_pnl, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_hold_bars": round(sum(t["hold_bars"] for t in trades) / len(trades), 1),
        "tp_exits": sum(1 for t in trades if t["exit_reason"] == "TP"),
        "sl_exits": sum(1 for t in trades if t["exit_reason"] == "SL"),
        "time_exits": sum(1 for t in trades if t["exit_reason"] == "TIME"),
    }


def record_to_audit(results):
    """Record backtest results to the audit trail database."""
    try:
        from audit_trail import record_event, start_run, finish_run
        run_id = start_run(regime_data={
            "scanner": "hoffman_backtest",
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        for r in results:
            record_event(
                "BACKTEST_RESULT",
                run_id=run_id,
                symbol="MULTI",
                payload={
                    "strategy": r["strategy"],
                    "total_trades": r["metrics"]["total_trades"],
                    "win_rate": r["metrics"]["win_rate"],
                    "total_pnl_pct": r["metrics"]["total_pnl_pct"],
                    "profit_factor": r["metrics"]["profit_factor"],
                    "max_drawdown_pct": r["metrics"]["max_drawdown_pct"],
                    "avg_hold_bars": r["metrics"]["avg_hold_bars"],
                    "symbols_tested": r["symbols_tested"],
                    "bars_per_symbol": r["bars_per_symbol"],
                },
                origin="hoffman_backtest",
            )

        finish_run(run_id, consensus_count=len(results),
                   systems_loaded=len(results), raw_count=len(results))
        print(f"\n  Audit trail: recorded {len(results)} backtest results (run_id={run_id})")
    except Exception as e:
        print(f"\n  Audit trail recording failed: {e}")


def main():
    print("=" * 70)
    print("  Hoffman IRB Variations — Walk-Forward Backtest")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Fetch historical data for all symbols
    all_data = {}
    for sym in SYMBOLS:
        print(f"\n  Fetching {sym} 15m klines (1000 bars)...")
        try:
            all_data[sym] = fetch_historical(sym, "15m", 1000)
            print(f"    -> {len(all_data[sym])} bars")
        except Exception as e:
            print(f"    -> FAILED: {e}")
        time.sleep(0.3)  # rate limit

    if not all_data:
        print("  No data fetched — aborting")
        return

    # Build list of all strategies to test
    strategies = []

    # 8 baby strategy variations
    for var in VARIATIONS:
        strategies.append({
            "name": var["name"],
            "fn": var["generate_signals"],
            "max_hold_bars": 16,  # default ~4h for 15m bars
        })

    # Override max_hold for scalper
    for s in strategies:
        if "scalper" in s["name"]:
            s["max_hold_bars"] = 2  # ~30 min for scalper

    results = []

    print(f"\n  Running {len(strategies)} strategies × {len(all_data)} symbols...")
    print("-" * 70)

    for strat in strategies:
        all_trades = []
        total_signals = 0

        for sym, df in all_data.items():
            trades, n_signals = backtest_variation(
                strat["fn"], df, sym, strat["max_hold_bars"]
            )
            all_trades.extend(trades)
            total_signals += n_signals

        metrics = compute_metrics(all_trades)
        results.append({
            "strategy": strat["name"],
            "metrics": metrics,
            "signals_generated": total_signals,
            "symbols_tested": list(all_data.keys()),
            "bars_per_symbol": 1000,
        })

        # Print results
        m = metrics
        status = "+" if m["win_rate"] >= 50 else "o" if m["win_rate"] >= 40 else "x"
        print(f"  {status} {strat['name']:<30} "
              f"Trades: {m['total_trades']:>3} | "
              f"WR: {m['win_rate']:>5.1f}% | "
              f"PnL: {m['total_pnl_pct']:>+7.2f}% | "
              f"PF: {m['profit_factor']:>4.2f} | "
              f"DD: {m['max_drawdown_pct']:>5.2f}% | "
              f"Sigs: {total_signals}")

    print("-" * 70)

    # Save results to file
    results_dir = Path(__file__).parent / "backtest_results"
    results_dir.mkdir(exist_ok=True)
    out_file = results_dir / "hoffman_variations.json"
    with open(out_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": list(all_data.keys()),
            "bars_per_symbol": 1000,
            "interval": "15m",
            "results": results,
        }, f, indent=2)
    print(f"\n  Results saved to {out_file}")

    # Record to audit trail
    record_to_audit(results)

    # Summary
    print("\n  RANKING (by PnL):")
    ranked = sorted(results, key=lambda r: r["metrics"]["total_pnl_pct"], reverse=True)
    for i, r in enumerate(ranked, 1):
        m = r["metrics"]
        print(f"    {i}. {r['strategy']:<30} "
              f"PnL={m['total_pnl_pct']:>+7.2f}%  WR={m['win_rate']:>5.1f}%  "
              f"PF={m['profit_factor']:>4.2f}  Trades={m['total_trades']}")


if __name__ == "__main__":
    main()
