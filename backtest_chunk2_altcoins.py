#!/usr/bin/env python3
"""
Chunk2 Altcoins Backtest — Kimi_Cursor v0.04 on 6 coins, 1H, 3 modes.
Tests: XRP-USD, DOGE-USD, ADA-USD, AVAX-USD, TRX-USD, DOT-USD.
Modes: KIMI v0.01 Multi (5-ind, minConfirm=2), v0.04 Hybrid (9-ind, minConfirm=3), v0.04 Dynamic (regime-weighted).
Fixed 3%/2% TP/SL for 1H; yfinance max 729 days for 1h interval.
Saves to backtest_results/chunk2_altcoins_a.json.
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# Import strategy and backtest from main backtester
from backtest_kimi_cursor_v04 import (
    compute_all_signals,
    kimi_v01_multi,
    v04_multi,
    v04_dynamic,
    backtest_fixed_pct,
)

SYMBOLS = ["XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD", "TRX-USD", "DOT-USD"]
TIMEFRAME = "1h"
MAX_DAYS_1H = 729
TP_PCT = 3.0
SL_PCT = 2.0
COMMISSION_PCT = 0.1

MODES = [
    ("KIMI v0.01 Multi", lambda all_sigs: kimi_v01_multi(all_sigs, min_confirm=2)),
    ("v0.04 Hybrid", lambda all_sigs: v04_multi(all_sigs, min_confirm=3)),
    ("v0.04 Dynamic", lambda df, all_sigs: v04_dynamic(df, all_sigs)),
]


def fetch_ohlcv_1h(symbol: str, days: int = MAX_DAYS_1H):
    """Fetch 1H OHLCV from yfinance (max 729 days for 1h)."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{days}d", interval="1h")
    if df is None or len(df) == 0:
        return None
    df.columns = [c.lower() for c in df.columns]
    for drop in ("stock splits", "dividends", "capital gains"):
        if drop in df.columns:
            df.drop(columns=[drop], errors="ignore", inplace=True)
    df = df.dropna(subset=["close"])
    if "open" not in df.columns:
        df["open"] = df["close"]
    if "high" not in df.columns:
        df["high"] = df[["open", "close"]].max(axis=1)
    if "low" not in df.columns:
        df["low"] = df[["open", "close"]].min(axis=1)
    return df


def run_one_symbol(symbol: str):
    """Run all 3 modes for one symbol; return list of row dicts and per-mode metrics."""
    df = fetch_ohlcv_1h(symbol)
    if df is None or len(df) < 200:
        return [], None, f"Insufficient data ({len(df) if df is not None else 0} bars)"

    all_sigs = compute_all_signals(df)
    rows = []
    results_by_mode = {}

    # 1. KIMI v0.01 Multi
    buy, sell = MODES[0][1](all_sigs)
    r = backtest_fixed_pct(df, buy, sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)
    rows.append({
        "symbol": symbol,
        "mode": "KIMI v0.01 Multi",
        "trades": r["num_trades"],
        "wr_pct": r["win_rate"],
        "pf": r["profit_factor"],
        "return_pct": r["total_return"],
        "max_dd_pct": r["max_drawdown"],
        "sharpe": r["sharpe"],
    })
    results_by_mode["KIMI v0.01 Multi"] = r

    # 2. v0.04 Hybrid
    buy, sell = MODES[1][1](all_sigs)
    r = backtest_fixed_pct(df, buy, sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)
    rows.append({
        "symbol": symbol,
        "mode": "v0.04 Hybrid",
        "trades": r["num_trades"],
        "wr_pct": r["win_rate"],
        "pf": r["profit_factor"],
        "return_pct": r["total_return"],
        "max_dd_pct": r["max_drawdown"],
        "sharpe": r["sharpe"],
    })
    results_by_mode["v0.04 Hybrid"] = r

    # 3. v0.04 Dynamic (needs df)
    buy, sell = MODES[2][1](df, all_sigs)
    r = backtest_fixed_pct(df, buy, sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)
    rows.append({
        "symbol": symbol,
        "mode": "v0.04 Dynamic",
        "trades": r["num_trades"],
        "wr_pct": r["win_rate"],
        "pf": r["profit_factor"],
        "return_pct": r["total_return"],
        "max_dd_pct": r["max_drawdown"],
        "sharpe": r["sharpe"],
    })
    results_by_mode["v0.04 Dynamic"] = r

    return rows, results_by_mode, None


def main():
    out_path = Path(__file__).resolve().parent / "backtest_results" / "chunk2_altcoins_a.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    by_symbol = {}
    errors = []

    print("Chunk2 Altcoins — Kimi_Cursor v0.04 | 1H | Fixed 3%/2% TP/SL")
    print("=" * 90)
    print(f"{'SYMBOL':<12} | {'Mode':<22} | {'Trades':>6} | {'WR%':>6} | {'PF':>6} | {'Return%':>8} | {'MaxDD%':>7} | {'Sharpe':>7}")
    print("-" * 90)

    for symbol in SYMBOLS:
        rows, res, err = run_one_symbol(symbol)
        if err:
            errors.append(f"{symbol}: {err}")
            print(f"{symbol:<12} | {err}")
            continue
        by_symbol[symbol] = {mode: res[mode] for mode in res}
        for row in rows:
            all_rows.append(row)
            print(f"{row['symbol']:<12} | {row['mode']:<22} | {row['trades']:>6} | {row['wr_pct']:>5.1f}% | {row['pf']:>6.3f} | {row['return_pct']:>+8.2f}% | {row['max_dd_pct']:>7.2f}% | {row['sharpe']:>7.3f}")

    # Summary: losers, best mode per coin, patterns
    summary = {
        "meta": {
            "timeframe": TIMEFRAME,
            "tp_pct": TP_PCT,
            "sl_pct": SL_PCT,
            "commission_pct": COMMISSION_PCT,
            "symbols": SYMBOLS,
            "modes": [m[0] for m in MODES],
        },
        "table": all_rows,
        "by_symbol": {},
        "analysis": {},
    }

    for sym in SYMBOLS:
        if sym not in by_symbol:
            continue
        summary["by_symbol"][sym] = by_symbol[sym]

    # Which coins lose badly (negative return in all modes or large drawdown)
    losing_coins = []
    for sym in SYMBOLS:
        if sym not in by_symbol:
            continue
        rets = [by_symbol[sym][m]["total_return"] for m in by_symbol[sym]]
        max_dds = [by_symbol[sym][m]["max_drawdown"] for m in by_symbol[sym]]
        if all(r < 0 for r in rets):
            losing_coins.append({"symbol": sym, "reason": "negative return in all modes", "returns": rets})
        elif max(rets) < 0 and max(max_dds) > 15:
            losing_coins.append({"symbol": sym, "reason": "negative best return and high DD", "returns": rets})

    # Best mode per coin (by profit factor, then return)
    best_per_coin = {}
    for sym in SYMBOLS:
        if sym not in by_symbol:
            continue
        best_mode = None
        best_pf = -1
        best_ret = -1e9
        for mode, r in by_symbol[sym].items():
            if r["num_trades"] < 5:
                continue
            if r["profit_factor"] > best_pf or (r["profit_factor"] == best_pf and r["total_return"] > best_ret):
                best_pf = r["profit_factor"]
                best_ret = r["total_return"]
                best_mode = mode
        if best_mode:
            best_per_coin[sym] = {
                "mode": best_mode,
                "profit_factor": float(best_pf),
                "total_return": float(best_ret),
            }

    # Mode wins (how many coins each mode wins)
    mode_wins = {"KIMI v0.01 Multi": 0, "v0.04 Hybrid": 0, "v0.04 Dynamic": 0}
    for sym, info in best_per_coin.items():
        mode_wins[info["mode"]] = mode_wins.get(info["mode"], 0) + 1

    summary["analysis"] = {
        "losing_coins": losing_coins,
        "best_mode_per_coin": best_per_coin,
        "mode_win_counts": mode_wins,
        "errors": errors,
        "notes": [
            "Lower-cap / volatile alts may need different TP/SL or thresholds.",
            "v0.04 Dynamic emphasizes trend in TREND regime and mean-reversion in RANGE.",
        ],
    }

    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("-" * 90)
    print(f"Results saved to {out_path}")
    print("\nAnalysis:")
    print("  Losing coins (negative in all modes or bad DD):", [c["symbol"] for c in losing_coins])
    print("  Best mode per coin:", best_per_coin)
    print("  Mode win counts (best PF per coin):", mode_wins)
    return 0


if __name__ == "__main__":
    sys.exit(main())
