#!/usr/bin/env python3
"""
Chunk1 Majors 1H Backtest — Kimi_Cursor v0.04 multi-coin, multi-mode.
Tests BTC-USD, ETH-USD, SOL-USD, BNB-USD on 1H with:
- KIMI v0.01 Multi (5-indicator, minConfirm=2)
- v0.04 Hybrid (9-indicator, minConfirm=3)
- v0.04 Dynamic (regime-weighted)
Fixed 3%/2% TP/SL for 1H (tf_secs <= 3600). Saves to backtest_results/chunk1_majors.json.
"""

import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Reuse backtester logic
from backtest_kimi_cursor_v04 import (
    compute_all_signals,
    kimi_v01_multi,
    v04_multi,
    v04_dynamic,
    backtest_fixed_pct,
)

SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
MODES = [
    ("KIMI v0.01 Multi", lambda all_sigs, df: kimi_v01_multi(all_sigs, min_confirm=2)),
    ("v0.04 Hybrid", lambda all_sigs, df: v04_multi(all_sigs, min_confirm=3)),
    ("v0.04 Dynamic", lambda all_sigs, df: v04_dynamic(df, all_sigs)),
]
TF = "1h"
MAX_DAYS_1H = 729
TP_PCT = 3.0
SL_PCT = 2.0
COMMISSION_PCT = 0.1


def fetch_ohlc(symbol: str, interval: str = "1h", days: int = 729) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from yfinance. 1h supports max 729 days."""
    limit = min(days, MAX_DAYS_1H) if interval == "1h" else min(days, 3650)
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{limit}d", interval=interval)
    if df is None or len(df) < 200:
        return None
    df.columns = [c.lower() for c in df.columns]
    for col in ["stock splits", "dividends"]:
        if col in df.columns:
            df.drop(columns=[col], errors="ignore", inplace=True)
    df = df.dropna(subset=["close"])
    return df


def run_one(symbol: str) -> List[Dict]:
    """Run all 3 modes for one symbol on 1H; fixed 3%/2% TP/SL."""
    df = fetch_ohlc(symbol, interval="1h", days=MAX_DAYS_1H)
    if df is None or len(df) < 200:
        return []
    all_sigs = compute_all_signals(df)
    rows = []
    for mode_name, vote_fn in MODES:
        buy_sig, sell_sig = vote_fn(all_sigs, df)
        res = backtest_fixed_pct(df, buy_sig, sell_sig, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)
        rows.append({
            "symbol": symbol,
            "mode": mode_name,
            "trades": res["num_trades"],
            "wr_pct": res["win_rate"],
            "pf": res["profit_factor"],
            "return_pct": res["total_return"],
            "max_dd_pct": res["max_drawdown"],
            "sharpe": res["sharpe"],
            "bars": len(df),
            "tp_sl": "Fixed 3%/2%",
        })
    return rows


def main():
    out_path = Path("backtest_results/chunk1_majors.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict] = []
    print("SYMBOL | Mode                | Trades | WR%   | PF    | Return% | MaxDD% | Sharpe")
    print("-" * 95)

    for symbol in SYMBOLS:
        rows = run_one(symbol)
        if not rows:
            print(f"{symbol} | (insufficient data)")
            continue
        for r in rows:
            all_rows.append(r)
            ret_str = f"+{r['return_pct']:.2f}%" if r["return_pct"] >= 0 else f"{r['return_pct']:.2f}%"
            print(f"{r['symbol']:<6} | {r['mode']:<20} | {r['trades']:>6} | {r['wr_pct']:>5.1f}% | {r['pf']:>5.3f} | {ret_str:>7} | {r['max_dd_pct']:>5.2f}% | {r['sharpe']:>6.3f}")

    # Summary analysis
    print("\n" + "=" * 95)
    print("ANALYSIS")
    print("=" * 95)

    by_symbol: Dict[str, List[Dict]] = {}
    for r in all_rows:
        by_symbol.setdefault(r["symbol"], []).append(r)

    losers = []
    best_per_coin = {}
    for sym, rows in by_symbol.items():
        best = max(rows, key=lambda x: (x["pf"], x["return_pct"]))
        best_per_coin[sym] = best["mode"]
        for r in rows:
            if r["return_pct"] < -20 or r["pf"] < 0.5:
                losers.append((r["symbol"], r["mode"], r["return_pct"], r["pf"]))

    print("\nCoins/modes that lose badly (Return% < -20 or PF < 0.5):")
    if losers:
        for sym, mode, ret, pf in losers:
            print(f"  - {sym} {mode}: Return%={ret:.2f}, PF={pf:.3f}")
    else:
        print("  (none)")

    print("\nBest mode per coin:")
    for sym, mode in best_per_coin.items():
        print(f"  {sym}: {mode}")

    # Pattern: which mode wins most often
    mode_wins = {}
    for sym, rows in by_symbol.items():
        best_mode = max(rows, key=lambda x: (x["pf"], x["return_pct"]))["mode"]
        mode_wins[best_mode] = mode_wins.get(best_mode, 0) + 1
    print("\nMode wins (best PF/return per coin):")
    for mode, count in sorted(mode_wins.items(), key=lambda x: -x[1]):
        print(f"  {mode}: {count}/4 coins")

    # Patterns
    patterns = []
    if any(r["symbol"] in ("SOL-USD", "BNB-USD") and r["return_pct"] < -25 for r in all_rows):
        patterns.append("High-beta alts (SOL, BNB) lose badly with fixed 3%/2% on 1H; consider wider stops or lower size.")
    if best_per_coin.get("BTC-USD") == "v0.04 Dynamic" and best_per_coin.get("SOL-USD") == "v0.04 Dynamic":
        patterns.append("Regime-weighted (v0.04 Dynamic) works best for BTC and SOL on 1H.")
    if best_per_coin.get("ETH-USD") == "KIMI v0.01 Multi" or best_per_coin.get("BNB-USD") == "KIMI v0.01 Multi":
        patterns.append("Simpler 5-indicator baseline (KIMI v0.01) wins for ETH and BNB; mean-reversion / fewer signals may suit range-bound behaviour.")
    if mode_wins.get("v0.04 Hybrid", 0) == 0:
        patterns.append("v0.04 Hybrid (9-indicator, minConfirm=3) never best; fixed 3%/2% with more confirmations hurts alts.")
    print("\nPatterns:")
    for p in patterns:
        print(f"  - {p}")

    # Save
    payload = {
        "timeframe": TF,
        "tp_pct": TP_PCT,
        "sl_pct": SL_PCT,
        "commission_pct": COMMISSION_PCT,
        "max_days": MAX_DAYS_1H,
        "results": all_rows,
        "analysis": {
            "losers": [{"symbol": s, "mode": m, "return_pct": r, "pf": p} for s, m, r, p in losers],
            "best_per_coin": best_per_coin,
            "mode_wins": mode_wins,
            "patterns": patterns,
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
