#!/usr/bin/env python3
"""
Backtest: volume_price_confirmation_reversal
=============================================
Runs the strategy across 21 symbols (crypto + equity + forex),
simulates TP/SL/max-hold exits, and applies anti-overfitting checks.
"""

import json
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats as sp_stats

warnings.filterwarnings("ignore")

# Import the strategy
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from baby_strategies.volume_price_confirmation_reversal import (
    VolumePriceConfirmationReversalStrategy,
)

# ── Symbols ──────────────────────────────────────────────────────────────
CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD",
          "AVAX-USD", "LINK-USD", "NEAR-USD", "ATOM-USD"]
EQUITY = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN"]
FOREX  = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
ALL_SYMBOLS = CRYPTO + EQUITY + FOREX


def fetch_data(symbols, period="5y"):
    """Fetch OHLCV data from yfinance."""
    data = {}
    for sym in symbols:
        try:
            df = yf.download(sym, period=period, progress=False, auto_adjust=True)
            if df is not None and len(df) >= 100:
                # Normalize columns to lowercase
                df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
                data[sym] = df
                print(f"  {sym}: {len(df)} bars")
            else:
                print(f"  {sym}: skipped (insufficient data)")
        except Exception as e:
            print(f"  {sym}: error - {e}")
    return data


def simulate_trades(signals, df):
    """
    Simulate TP/SL/max-hold exits using actual price data.
    Returns list of trade results with PnL.
    """
    trades = []

    for sig in signals:
        # Support both dict and dataclass signals
        def _get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        entry = _get(sig, "entry_price")
        tp = _get(sig, "take_profit")
        sl = _get(sig, "stop_loss")
        side = _get(sig, "direction", _get(sig, "side", "BUY"))
        # Map direction names for TP/SL simulation
        if side == "BUY":
            side = "LONG"
        elif side == "SELL":
            side = "SHORT"
        max_hold = _get(sig, "max_hold_days", 15)

        # Find entry bar index
        entry_idx = None
        for idx in range(len(df)):
            if abs(float(df.iloc[idx]["open"]) - entry) / max(entry, 1e-8) < 0.001:
                entry_idx = idx
                break

        if entry_idx is None:
            # Fallback: find closest open price
            opens = df["open"].values.astype(float)
            diffs = np.abs(opens - entry)
            entry_idx = int(np.argmin(diffs))

        # Simulate forward from entry
        exit_price = None
        exit_reason = "max_hold"

        for j in range(entry_idx + 1, min(entry_idx + max_hold + 1, len(df))):
            high = float(df.iloc[j]["high"])
            low = float(df.iloc[j]["low"])

            if side == "LONG":
                if low <= sl:
                    exit_price = sl
                    exit_reason = "stop_loss"
                    break
                if high >= tp:
                    exit_price = tp
                    exit_reason = "take_profit"
                    break
            else:  # SHORT
                if high >= sl:
                    exit_price = sl
                    exit_reason = "stop_loss"
                    break
                if low <= tp:
                    exit_price = tp
                    exit_reason = "take_profit"
                    break

        if exit_price is None:
            # Max hold exit at close of last bar
            last_idx = min(entry_idx + max_hold, len(df) - 1)
            exit_price = float(df.iloc[last_idx]["close"])

        # Calculate PnL
        if side == "LONG":
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - exit_price) / entry) * 100

        # Determine in-sample vs OOS (60/40 split)
        total_bars = len(df)
        split_idx = int(total_bars * 0.6)
        in_sample = entry_idx < split_idx

        trades.append({
            "entry": entry,
            "exit": exit_price,
            "side": side,
            "pnl_pct": pnl_pct,
            "exit_reason": exit_reason,
            "in_sample": in_sample,
            "entry_idx": entry_idx,
        })

    return trades


def analyze_results(all_trades, symbol_trades):
    """Run 8-point anti-overfitting analysis."""
    n = len(all_trades)
    if n < 5:
        return {"verdict": "INSUFFICIENT", "total_trades": n, "checks": {}}

    wins = sum(1 for t in all_trades if t["pnl_pct"] > 0)
    losses = n - wins
    wr = wins / n * 100

    pnls = [t["pnl_pct"] for t in all_trades]
    avg_pnl = np.mean(pnls)
    sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0

    gross_win = sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] > 0)
    gross_loss = abs(sum(t["pnl_pct"] for t in all_trades if t["pnl_pct"] <= 0))
    pf = gross_win / gross_loss if gross_loss > 0 else 99.99

    # P-value (binomial)
    p_val = float(sp_stats.binomtest(wins, n, 0.5, alternative="greater").pvalue)

    # In-sample / OOS split
    is_trades = [t for t in all_trades if t["in_sample"]]
    oos_trades = [t for t in all_trades if not t["in_sample"]]
    is_wr = sum(1 for t in is_trades if t["pnl_pct"] > 0) / len(is_trades) * 100 if is_trades else 0
    oos_wr = sum(1 for t in oos_trades if t["pnl_pct"] > 0) / len(oos_trades) * 100 if oos_trades else 0
    oos_avg = np.mean([t["pnl_pct"] for t in oos_trades]) if oos_trades else 0

    # Multi-asset check
    sym_profitable = 0
    sym_tested = len(symbol_trades)
    for sym, trades in symbol_trades.items():
        if trades and np.mean([t["pnl_pct"] for t in trades]) > 0:
            sym_profitable += 1

    # Consistency: first half vs second half
    mid = n // 2
    first_half = pnls[:mid]
    second_half = pnls[mid:]
    first_avg = np.mean(first_half) if first_half else 0
    second_avg = np.mean(second_half) if second_half else 0

    # Exit reason breakdown
    tp_count = sum(1 for t in all_trades if t["exit_reason"] == "take_profit")
    sl_count = sum(1 for t in all_trades if t["exit_reason"] == "stop_loss")
    mh_count = sum(1 for t in all_trades if t["exit_reason"] == "max_hold")

    # 8 anti-overfit checks
    checks = {
        "min_30_trades": n >= 30,
        "wr_above_50": wr > 50,
        "p_value_lt_05": p_val < 0.05,
        "profit_factor_gt_1_2": pf > 1.2,
        "oos_profitable": oos_avg > 0,
        "multi_asset_3plus": sym_profitable >= 3,
        "both_halves_profitable": first_avg > 0 and second_avg > 0,
        "sharpe_gt_0_5": sharpe > 0.5,
    }
    passes = sum(1 for v in checks.values() if v)

    if passes >= 7:
        verdict = "SURVIVOR"
    elif passes >= 5:
        verdict = "PROMISING"
    elif passes >= 3:
        verdict = "MARGINAL"
    else:
        verdict = "ELIMINATED"

    return {
        "verdict": verdict,
        "total_trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wr, 1),
        "avg_pnl_pct": round(avg_pnl, 3),
        "sharpe": round(sharpe, 2),
        "profit_factor": round(pf, 2),
        "p_value": round(p_val, 4),
        "in_sample_trades": len(is_trades),
        "in_sample_wr": round(is_wr, 1),
        "oos_trades": len(oos_trades),
        "oos_wr": round(oos_wr, 1),
        "oos_avg_pnl_pct": round(oos_avg, 3),
        "symbols_profitable": sym_profitable,
        "symbols_tested": sym_tested,
        "first_half_avg_pnl": round(first_avg, 3),
        "second_half_avg_pnl": round(second_avg, 3),
        "tp_exits": tp_count,
        "sl_exits": sl_count,
        "max_hold_exits": mh_count,
        "checks": checks,
        "checks_passed": passes,
    }


def main():
    t0 = time.time()

    print("=" * 70)
    print("  BACKTEST: volume_price_confirmation_reversal")
    print("  BB false breakout + volume exhaustion + next-bar reversal")
    print("  TP: 3x ATR | SL: 2x ATR | Max Hold: 15 days")
    print("=" * 70)

    strat = VolumePriceConfirmationReversalStrategy()

    print("\n[1/3] Fetching 5 years of daily OHLCV data...")
    data = fetch_data(ALL_SYMBOLS, period="5y")

    if not data:
        print("FATAL: No data fetched")
        sys.exit(1)

    print(f"\n[2/3] Generating signals and simulating trades on {len(data)} symbols...")
    all_trades = []
    symbol_trades = {}
    symbol_signals = {}

    for sym, df in data.items():
        signals = strat.generate_signals(df, symbol=sym)
        symbol_signals[sym] = len(signals)

        if signals:
            trades = simulate_trades(signals, df)
            symbol_trades[sym] = trades
            all_trades.extend(trades)

            wins = sum(1 for t in trades if t["pnl_pct"] > 0)
            wr = wins / len(trades) * 100
            avg = np.mean([t["pnl_pct"] for t in trades])
            print(f"  {sym:>10}: {len(signals):3d} signals -> {len(trades):3d} trades | WR={wr:.1f}% | avg={avg:+.3f}%")
        else:
            symbol_trades[sym] = []
            print(f"  {sym:>10}: 0 signals")

    print(f"\n  TOTAL: {len(all_trades)} trades across {sum(1 for v in symbol_trades.values() if v)} symbols")

    print(f"\n[3/3] Anti-overfitting analysis (8 checks)...")
    results = analyze_results(all_trades, symbol_trades)

    # Print report
    print("\n" + "=" * 70)
    print(f"  VERDICT: {results['verdict']}")
    print("=" * 70)

    if results["total_trades"] < 5:
        print("  Insufficient trades for analysis")
    else:
        print(f"  Trades: {results['total_trades']} | Wins: {results['wins']} | Losses: {results['losses']}")
        print(f"  Win Rate: {results['win_rate_pct']}% | Avg PnL: {results['avg_pnl_pct']}%")
        print(f"  Sharpe: {results['sharpe']} | Profit Factor: {results['profit_factor']} | p-value: {results['p_value']}")
        print(f"  In-Sample: {results['in_sample_trades']}T {results['in_sample_wr']}% WR")
        print(f"  Out-of-Sample: {results['oos_trades']}T {results['oos_wr']}% WR (avg {results['oos_avg_pnl_pct']}%)")
        print(f"  Multi-Asset: {results['symbols_profitable']}/{results['symbols_tested']} profitable")
        print(f"  Consistency: 1st half {results['first_half_avg_pnl']}% | 2nd half {results['second_half_avg_pnl']}%")
        print(f"  Exits: TP={results['tp_exits']} | SL={results['sl_exits']} | MaxHold={results['max_hold_exits']}")

        print(f"\n  Anti-Overfit Checks ({results['checks_passed']}/8):")
        for check, passed in results["checks"].items():
            icon = "PASS" if passed else "FAIL"
            print(f"    [{icon}] {check}")

    # Save results
    save_path = Path("baby_strategies/data")
    save_path.mkdir(parents=True, exist_ok=True)
    out_file = save_path / "vpcr_backtest_results.json"

    with open(out_file, "w") as f:
        json.dump({
            "strategy": strat.NAME,
            "test_date": datetime.now(timezone.utc).isoformat(),
            "symbols_tested": len(data),
            "period": "5y",
            "results": results,
            "per_symbol_signals": symbol_signals,
        }, f, indent=2, default=str)

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.1f}s | Saved: {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
