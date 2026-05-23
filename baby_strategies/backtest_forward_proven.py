"""
Comprehensive Backtester for Forward-Proven Strategy Variations
================================================================
Tests 6 new strategies across ~20 crypto pairs on 1h data.
Outputs per-strategy AND per-symbol results.

Usage:
    python baby_strategies/backtest_forward_proven.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from baby_strategies.forward_proven_variations import ALL_FORWARD_PROVEN

try:
    import ccxt
except ImportError:
    print("ERROR: ccxt not installed. Run: pip install ccxt")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "DOGE/USDT",
    "XRP/USDT", "LTC/USDT", "ADA/USDT", "LINK/USDT", "AVAX/USDT",
    "DOT/USDT", "MATIC/USDT", "NEAR/USDT", "ATOM/USDT", "UNI/USDT",
    "FIL/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT",
]

TIMEFRAME = "1h"
LIMIT = 500          # ~21 days of 1h candles
FORWARD_BARS = 60    # simulate 60-bar (60h) TP/SL resolution
STEP = 3             # sliding window step


def fetch_ohlcv(exchange, symbol, timeframe="1h", limit=500):
    """Fetch OHLCV data from Binance."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 200:
            return None
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        print(f"  Failed to fetch {symbol}: {e}")
        return None


def simulate_trade(df, signal, entry_idx, max_bars=60):
    """Simulate a trade forward from entry_idx. Returns (outcome, pnl_pct, hold_bars)."""
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(close)

    is_long = signal.direction == "BUY"
    entry = signal.entry_price
    tp = signal.take_profit
    sl = signal.stop_loss

    for bar in range(1, min(max_bars + 1, n - entry_idx)):
        j = entry_idx + bar
        if is_long:
            if low[j] <= sl:
                pnl = (sl - entry) / entry * 100
                return "loss", pnl, bar
            if high[j] >= tp:
                pnl = (tp - entry) / entry * 100
                return "win", pnl, bar
        else:
            if high[j] >= sl:
                pnl = (entry - sl) / entry * 100
                return "loss", pnl, bar
            if low[j] <= tp:
                pnl = (entry - tp) / entry * 100
                return "win", pnl, bar

    # Timeout — close at market
    final = close[min(entry_idx + max_bars, n - 1)]
    if is_long:
        pnl = (final - entry) / entry * 100
    else:
        pnl = (entry - final) / entry * 100
    return "timeout", pnl, min(max_bars, n - entry_idx - 1)


def backtest_strategy_on_symbol(strategy_cls, df, symbol_flat, step=3, forward_bars=60):
    """Run backtest for one strategy on one symbol's data."""
    results = []
    n = len(df)
    window_size = 200

    for start in range(0, n - window_size - forward_bars, step):
        end = start + window_size
        window_df = df.iloc[start:end].reset_index(drop=True)

        try:
            signals = strategy_cls.generate_signals(window_df, symbol_flat)
        except Exception:
            continue

        for sig in signals:
            outcome, pnl, hold = simulate_trade(df, sig, end - 1, forward_bars)
            results.append({
                "outcome": outcome,
                "pnl_pct": pnl,
                "hold_bars": hold,
                "direction": sig.direction,
                "confidence": sig.confidence,
                "entry": sig.entry_price,
                "tp": sig.take_profit,
                "sl": sig.stop_loss,
            })

    return results


def compute_stats(results):
    """Compute aggregate stats from a list of trade results."""
    if not results:
        return {"trades": 0, "wr": 0, "avg_pnl": 0, "total_pnl": 0,
                "pf": 0, "avg_win": 0, "avg_loss": 0, "rr": 0,
                "max_consec_loss": 0, "avg_hold": 0}

    wins = [r for r in results if r["pnl_pct"] > 0]
    losses = [r for r in results if r["pnl_pct"] <= 0]
    total_pnl = sum(r["pnl_pct"] for r in results)
    avg_pnl = total_pnl / len(results) if results else 0
    wr = len(wins) / len(results) * 100 if results else 0

    gross_profit = sum(r["pnl_pct"] for r in wins) if wins else 0
    gross_loss = abs(sum(r["pnl_pct"] for r in losses)) if losses else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.0

    avg_win = np.mean([r["pnl_pct"] for r in wins]) if wins else 0
    avg_loss = np.mean([abs(r["pnl_pct"]) for r in losses]) if losses else 0
    rr = avg_win / avg_loss if avg_loss > 0 else 99.0

    # Max consecutive losses
    max_cl = 0
    current_cl = 0
    for r in results:
        if r["pnl_pct"] <= 0:
            current_cl += 1
            max_cl = max(max_cl, current_cl)
        else:
            current_cl = 0

    avg_hold = np.mean([r["hold_bars"] for r in results])

    return {
        "trades": len(results),
        "wr": round(wr, 1),
        "avg_pnl": round(avg_pnl, 3),
        "total_pnl": round(total_pnl, 1),
        "pf": round(pf, 2),
        "avg_win": round(avg_win, 3),
        "avg_loss": round(avg_loss, 3),
        "rr": round(rr, 2),
        "max_consec_loss": max_cl,
        "avg_hold": round(avg_hold, 1),
    }


def main():
    print("=" * 70)
    print("Forward-Proven Strategy Variations — Comprehensive Backtest")
    print(f"Symbols: {len(SYMBOLS)} | Timeframe: {TIMEFRAME} | Bars: {LIMIT}")
    print("=" * 70)

    exchange = ccxt.binance({"enableRateLimit": True})

    # Fetch all data first
    print("\nFetching market data...")
    all_data = {}
    for sym in SYMBOLS:
        df = fetch_ohlcv(exchange, sym, TIMEFRAME, LIMIT)
        if df is not None:
            sym_flat = sym.replace("/", "")
            all_data[sym_flat] = df
            print(f"  {sym}: {len(df)} bars")
        time.sleep(0.3)

    print(f"\nLoaded {len(all_data)}/{len(SYMBOLS)} symbols")

    # Run backtests
    all_results = {}
    for strat_cls in ALL_FORWARD_PROVEN:
        strat_name = strat_cls.name
        print(f"\n{'-' * 50}")
        print(f"Strategy: {strat_cls.display_name}")
        print(f"{'-' * 50}")

        per_symbol = {}
        combined = []

        for sym_flat, df in all_data.items():
            results = backtest_strategy_on_symbol(strat_cls, df, sym_flat, STEP, FORWARD_BARS)
            if results:
                per_symbol[sym_flat] = compute_stats(results)
                combined.extend(results)
                stats = per_symbol[sym_flat]
                print(f"  {sym_flat:12s} → {stats['trades']:3d} trades, "
                      f"WR={stats['wr']:5.1f}%, PnL={stats['total_pnl']:+7.1f}%, "
                      f"PF={stats['pf']:5.2f}, R:R={stats['rr']:.2f}")
            else:
                print(f"  {sym_flat:12s} → 0 trades")

        total_stats = compute_stats(combined)
        all_results[strat_name] = {
            "display_name": strat_cls.display_name,
            "overall": total_stats,
            "per_symbol": per_symbol,
        }

        print(f"\n  OVERALL: {total_stats['trades']} trades, "
              f"WR={total_stats['wr']}%, Total={total_stats['total_pnl']:+.1f}%, "
              f"PF={total_stats['pf']}, R:R={total_stats['rr']}, "
              f"MaxCL={total_stats['max_consec_loss']}")

    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY — Ranked by Profit Factor")
    print("=" * 70)
    ranked = sorted(all_results.items(),
                    key=lambda x: x[1]["overall"]["pf"], reverse=True)

    print(f"{'Strategy':<30s} {'Trades':>6s} {'WR%':>6s} {'TotalPnL':>9s} "
          f"{'PF':>6s} {'R:R':>5s} {'MaxCL':>6s} {'AvgHold':>7s}")
    print("-" * 76)

    for name, data in ranked:
        o = data["overall"]
        print(f"{data['display_name']:<30s} {o['trades']:>6d} {o['wr']:>5.1f}% "
              f"{o['total_pnl']:>+8.1f}% {o['pf']:>6.2f} {o['rr']:>5.2f} "
              f"{o['max_consec_loss']:>6d} {o['avg_hold']:>6.1f}h")

    # Best individual pair performers
    print("\n" + "=" * 70)
    print("TOP 10 INDIVIDUAL PAIR PERFORMERS (min 5 trades)")
    print("=" * 70)

    pair_results = []
    for name, data in all_results.items():
        for sym, stats in data["per_symbol"].items():
            if stats["trades"] >= 5:
                pair_results.append({
                    "strategy": data["display_name"],
                    "symbol": sym,
                    **stats
                })

    pair_results.sort(key=lambda x: x["pf"], reverse=True)
    print(f"{'Strategy':<25s} {'Symbol':>10s} {'Trades':>6s} {'WR%':>6s} "
          f"{'TotalPnL':>9s} {'PF':>6s} {'R:R':>5s}")
    print("-" * 68)
    for p in pair_results[:10]:
        print(f"{p['strategy']:<25s} {p['symbol']:>10s} {p['trades']:>6d} "
              f"{p['wr']:>5.1f}% {p['total_pnl']:>+8.1f}% {p['pf']:>6.2f} "
              f"{p['rr']:>5.2f}")

    # Save results
    output_path = Path(__file__).resolve().parent / "forward_proven_backtest_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "config": {
                "symbols": list(all_data.keys()),
                "timeframe": TIMEFRAME,
                "bars": LIMIT,
                "forward_bars": FORWARD_BARS,
                "step": STEP,
            },
            "results": all_results,
        }, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    return all_results


if __name__ == "__main__":
    main()
