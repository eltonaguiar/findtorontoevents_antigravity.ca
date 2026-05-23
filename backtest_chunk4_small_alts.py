#!/usr/bin/env python3
"""
Chunk4: Backtest Kimi_Cursor v0.04 on 12 small-cap/newer alts, 1H timeframe.
Uses fixed 3%/2% TP/SL for 1H. Modes: KIMI v0.01 Multi, v0.04 Hybrid, v0.04 Dynamic.
Saves to backtest_results/chunk4_small_alts.json
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

# ---------------------------------------------------------------------------
# Coin tickers: primary and fallbacks (yfinance CMC IDs for newer coins)
# ---------------------------------------------------------------------------
COINS = [
    ("INJ", ["INJ-USD"]),
    ("FET", ["FET-USD"]),
    ("SUI", ["SUI20947-USD", "SUI-USD"]),
    ("ARB", ["ARB11841-USD", "ARB-USD"]),
    ("OP", ["OP-USD"]),
    ("SEI", ["SEI-USD", "SEI28782-USD"]),
    ("TIA", ["TIA22861-USD", "TIA-USD"]),
    ("DYDX", ["DYDX-USD", "DYDX31463-USD"]),
    ("APE", ["APE-USD"]),
    ("ALGO", ["ALGO-USD"]),
    ("HBAR", ["HBAR-USD"]),
    ("WLD", ["WLD-USD"]),
]

TF = "1h"
DAYS_1H = 729
MIN_BARS = 200
TP_PCT = 3.0
SL_PCT = 2.0
COMMISSION = 0.1


def fetch_crypto(tickers: list, tf: str = "1h", days: int = 729) -> tuple:
    """Try each ticker until we get OHLCV. Returns (df, used_ticker) or (None, None)."""
    interval_map = {"1h": "1h", "4h": "1h", "1d": "1d"}
    raw_interval = interval_map.get(tf, "1h")
    max_days = {"1h": 729, "1d": 3650}
    limit = min(days, max_days.get(raw_interval, days))

    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            df = t.history(period=f"{limit}d", interval=raw_interval)
            if df is None or len(df) < MIN_BARS:
                continue
            df.columns = [c.lower() for c in df.columns]
            df.drop(columns=["dividends", "stock splits"], errors="ignore", inplace=True)
            df = df.dropna(subset=["close"])
            if len(df) < MIN_BARS:
                continue
            if tf == "4h" and raw_interval == "1h":
                df = df.resample("4h").agg(
                    {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
                ).dropna()
            return df, sym
        except Exception as e:
            continue
    return None, None


def run_coin(symbol_label: str, df: pd.DataFrame) -> dict:
    """Run 3 modes on one coin; fixed 3%/2% TP/SL."""
    all_sigs = compute_all_signals(df)
    out = {"symbol": symbol_label, "bars": len(df), "modes": {}}

    # 1. KIMI v0.01 Multi (5-indicator, minConfirm=2)
    buy1, sell1 = kimi_v01_multi(all_sigs, min_confirm=2)
    r1 = backtest_fixed_pct(df, buy1, sell1, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION)
    out["modes"]["KIMI v0.01 Multi"] = r1

    # 2. v0.04 Hybrid (9-indicator, minConfirm=3)
    buy2, sell2 = v04_multi(all_sigs, min_confirm=3)
    r2 = backtest_fixed_pct(df, buy2, sell2, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION)
    out["modes"]["v0.04 Hybrid"] = r2

    # 3. v0.04 Dynamic (regime-weighted)
    buy3, sell3 = v04_dynamic(df, all_sigs)
    r3 = backtest_fixed_pct(df, buy3, sell3, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION)
    out["modes"]["v0.04 Dynamic"] = r3

    return out


def main():
    Path("backtest_results").mkdir(parents=True, exist_ok=True)
    all_results = []
    skipped = []

    print("=" * 90)
    print("  CHUNK4: Small Alts 1H — KIMI v0.01 Multi | v0.04 Hybrid | v0.04 Dynamic (Fixed 3%%/2%%)")
    print("=" * 90)

    for label, tickers in COINS:
        df, used_ticker = fetch_crypto(tickers, tf=TF, days=DAYS_1H)
        if df is None:
            skipped.append((label, tickers))
            print(f"  SKIP {label}: no data for {tickers}")
            continue
        print(f"\n  {label} ({used_ticker}): {len(df)} bars")
        res = run_coin(label, df)
        res["ticker_used"] = used_ticker
        all_results.append(res)

        # Table row per coin
        print(f"  {'SYMBOL':<8} | {'Mode':<22} | {'Trades':>7} | {'WR%':>6} | {'PF':>6} | {'Return%':>9} | {'MaxDD%':>7} | {'Sharpe':>7}")
        print("  " + "-" * 88)
        for mode, r in res["modes"].items():
            ret = r["total_return"]
            sign = "+" if ret > 0 else ""
            print(f"  {label:<8} | {mode:<22} | {r['num_trades']:>7} | {r['win_rate']:>5.1f}% | {r['profit_factor']:>6.3f} | {sign}{ret:>8.2f}% | {r['max_drawdown']:>6.2f}% | {r['sharpe']:>7.3f}")

    # Summary: losers, best mode per coin, patterns
    summary = {
        "timeframe": TF,
        "tp_sl": f"{TP_PCT}%/{SL_PCT}%",
        "skipped": [{"symbol": s[0], "tickers_tried": s[1]} for s in skipped],
        "coins_tested": len(all_results),
        "losers": [],
        "best_mode_per_coin": {},
        "patterns": [],
    }

    for res in all_results:
        sym = res["symbol"]
        best_mode = None
        best_pf = -999
        worst_return = 999
        for mode, r in res["modes"].items():
            if r["profit_factor"] > best_pf:
                best_pf = r["profit_factor"]
                best_mode = mode
            if r["total_return"] < worst_return:
                worst_return = r["total_return"]
        summary["best_mode_per_coin"][sym] = best_mode
        if worst_return < -15:
            summary["losers"].append({"symbol": sym, "worst_return_pct": round(worst_return, 2)})

    # Mode wins across coins
    mode_wins = {"KIMI v0.01 Multi": 0, "v0.04 Hybrid": 0, "v0.04 Dynamic": 0}
    for res in all_results:
        for mode, r in res["modes"].items():
            if r["profit_factor"] == max(m["profit_factor"] for m in res["modes"].values()):
                mode_wins[mode] += 1
                break
    summary["mode_wins"] = mode_wins

    # Pattern: newer/smaller cap often have fewer bars and more variance
    if all_results:
        avg_bars = np.mean([r["bars"] for r in all_results])
        summary["patterns"].append(
            f"Average bars per coin: {avg_bars:.0f}; newer tickers may have less history."
        )
        neg_returns = sum(1 for r in all_results for m in r["modes"].values() if m["total_return"] < 0)
        total_runs = sum(len(r["modes"]) for r in all_results)
        summary["patterns"].append(
            f"Negative return in {neg_returns}/{total_runs} mode-coin runs."
        )

    # Flat table: SYMBOL | Mode | Trades | WR% | PF | Return% | MaxDD% | Sharpe
    table = []
    for r in all_results:
        for mode, m in r["modes"].items():
            table.append({
                "symbol": r["symbol"],
                "mode": mode,
                "trades": m["num_trades"],
                "wr_pct": m["win_rate"],
                "pf": m["profit_factor"],
                "return_pct": m["total_return"],
                "max_dd_pct": m["max_drawdown"],
                "sharpe": m["sharpe"],
            })
    payload = {
        "summary": summary,
        "table": table,
        "results": [
            {
                "symbol": r["symbol"],
                "ticker_used": r.get("ticker_used"),
                "bars": r["bars"],
                "modes": r["modes"],
            }
            for r in all_results
        ],
    }
    out_path = Path("backtest_results/chunk4_small_alts.json")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n" + "=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(f"  Coins tested: {summary['coins_tested']}; Skipped: {len(skipped)}")
    print(f"  Mode wins (best PF per coin): {summary['mode_wins']}")
    print(f"  Best mode per coin: {summary['best_mode_per_coin']}")
    print(f"  Coins with large drawdown/loss: {summary['losers']}")
    print(f"  Patterns: {summary['patterns']}")
    print(f"\n  Results saved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
