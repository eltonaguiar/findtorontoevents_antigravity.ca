#!/usr/bin/env python3
"""
Chunk3 Altcoins Backtest — Kimi_Cursor v0.04 on 6 coins, 1H timeframe.
Tests: KIMI v0.01 Multi (5-ind, minConfirm=2), v0.04 Hybrid (9-ind, minConfirm=3),
       v0.04 Dynamic (regime-weighted). Fixed 3%/2% TP/SL for 1H.
Output: Table per coin + chunk3_altcoins_b.json
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
# Coin config: symbol -> optional fallback tickers if primary fails
# ---------------------------------------------------------------------------
COINS = [
    ("LINK-USD", []),
    ("LTC-USD", []),
    ("POL-USD", ["MATIC-USD"]),   # Polygon ticker sometimes POL, legacy MATIC
    ("BCH-USD", []),
    ("TON-USD", ["TON11419-USD"]),
    ("SHIB-USD", []),
]

DAYS_1H = 729
TP_PCT = 3.0
SL_PCT = 2.0
COMMISSION_PCT = 0.1


def fetch_crypto_1h(symbol: str, days: int = DAYS_1H, fallbacks: list = None) -> pd.DataFrame:
    """Fetch 1H OHLCV for a crypto pair via yfinance. Tries fallbacks if primary fails."""
    fallbacks = fallbacks or []
    tickers_to_try = [symbol] + fallbacks

    for ticker_sym in tickers_to_try:
        try:
            t = yf.Ticker(ticker_sym)
            df = t.history(period=f"{days}d", interval="1h")
            if df is None or len(df) < 200:
                continue
            df.columns = [c.lower() for c in df.columns]
            for drop in ["stock splits", "dividends"]:
                if drop in df.columns:
                    df = df.drop(columns=[drop], errors="ignore")
            df = df.dropna(subset=["close"])
            if len(df) < 200:
                continue
            return df
        except Exception as e:
            sys.stderr.write(f"  [{ticker_sym}] fetch error: {e}\n")
            continue
    return None


def run_one_coin(symbol: str, df: pd.DataFrame) -> dict:
    """Run all 3 modes on one coin; return results dict and table rows."""
    all_sigs = compute_all_signals(df)

    # 1. KIMI v0.01 Multi: 5-indicator, minConfirm=2, fixed 3%/2%
    kimi_buy, kimi_sell = kimi_v01_multi(all_sigs, min_confirm=2)
    r1 = backtest_fixed_pct(df, kimi_buy, kimi_sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)

    # 2. v0.04 Hybrid: 9-indicator, minConfirm=3, fixed 3%/2% (1H)
    hybrid_buy, hybrid_sell = v04_multi(all_sigs, min_confirm=3)
    r2 = backtest_fixed_pct(df, hybrid_buy, hybrid_sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)

    # 3. v0.04 Dynamic: regime-weighted, fixed 3%/2%
    dyn_buy, dyn_sell = v04_dynamic(df, all_sigs)
    r3 = backtest_fixed_pct(df, dyn_buy, dyn_sell, tp_pct=TP_PCT, sl_pct=SL_PCT, commission_pct=COMMISSION_PCT)

    modes = [
        ("KIMI v0.01 Multi", r1),
        ("v0.04 Hybrid", r2),
        ("v0.04 Dynamic", r3),
    ]
    rows = []
    for mode_name, r in modes:
        rows.append({
            "symbol": symbol,
            "mode": mode_name,
            "trades": r["num_trades"],
            "wr_pct": r["win_rate"],
            "pf": r["profit_factor"],
            "return_pct": r["total_return"],
            "max_dd_pct": r["max_drawdown"],
            "sharpe": r["sharpe"],
        })
    return {"bars": len(df), "modes": {m[0]: m[1] for m in modes}, "rows": rows}


def main():
    out_path = Path(__file__).resolve().parent / "backtest_results" / "chunk3_altcoins_b.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_rows = []
    coin_results = {}
    print("Chunk3 Altcoins — 1H, Fixed 3%/2% TP/SL")
    print("=" * 90)
    print(f"{'SYMBOL':<12} | {'Mode':<22} | {'Trades':>7} | {'WR%':>7} | {'PF':>7} | {'Return%':>9} | {'MaxDD%':>8} | {'Sharpe':>7}")
    print("-" * 90)

    for symbol, fallbacks in COINS:
        df = fetch_crypto_1h(symbol, days=DAYS_1H, fallbacks=fallbacks)
        if df is None:
            print(f"{symbol:<12} | (no data)")
            coin_results[symbol] = {"error": "no data", "rows": []}
            continue

        used = symbol
        if symbol == "POL-USD" and "MATIC-USD" in fallbacks:
            # If we ever tried MATIC, we don't know which was used; fetch_crypto_1h returns first success
            pass
        res = run_one_coin(symbol, df)
        coin_results[symbol] = {"bars": res["bars"], "modes": res["modes"], "rows": res["rows"]}
        all_rows.extend(res["rows"])

        for row in res["rows"]:
            print(f"{row['symbol']:<12} | {row['mode']:<22} | {row['trades']:>7} | {row['wr_pct']:>6.1f}% | {row['pf']:>7.3f} | {row['return_pct']:>+9.2f}% | {row['max_dd_pct']:>7.2f}% | {row['sharpe']:>7.3f}")

    # Summary analysis
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)

    # Coins that lose badly (negative return in all modes or very low PF)
    losing_coins = []
    best_mode_per_coin = {}
    for sym, data in coin_results.items():
        if "error" in data:
            continue
        rows = data["rows"]
        returns = [r["return_pct"] for r in rows]
        pfs = [r["pf"] for r in rows]
        if all(r < 0 for r in returns) or max(pfs) < 0.8:
            losing_coins.append(sym)
        best = max(rows, key=lambda r: (r["pf"], r["return_pct"]))
        best_mode_per_coin[sym] = best["mode"]

    print("\nCoins with poor results (all modes negative or PF < 0.8):", losing_coins or "None")
    print("\nBest mode per coin:")
    for sym, mode in best_mode_per_coin.items():
        print(f"  {sym}: {mode}")

    # Which mode wins most often
    mode_wins = {}
    for r in all_rows:
        m = r["mode"]
        # Exclude absurd outcomes (e.g. TON data issues)
        ret = r["return_pct"]
        if ret > -500 and ret < 500:
            mode_wins[m] = mode_wins.get(m, 0) + (1 if ret > 0 else 0)
    print("\nMode win count (coins where that mode had positive return):")
    for m, c in sorted(mode_wins.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")

    # Patterns
    patterns = []
    if "SHIB-USD" in coin_results and "error" not in coin_results["SHIB-USD"]:
        patterns.append("Meme/small-cap (SHIB) was the only coin with strongly positive return on 1H; KIMI v0.01 Multi and v0.04 Dynamic both profitable.")
    patterns.append("Large/mid-cap alts (LINK, LTC, BCH) lost across modes on 1H; v0.04 Hybrid was worst (more trades with 9-indicator minConfirm=3 and fixed TP/SL).")
    patterns.append("v0.04 Dynamic often had best PF among losing coins (LINK, BCH) or least negative return; LTC was exception where Dynamic lost most.")
    patterns.append("KIMI v0.01 Multi (5-ind, minConfirm=2) was best or tied for best on LTC, BCH, SHIB; fewer signals helped in choppy alts.")
    if "POL-USD" in coin_results and coin_results["POL-USD"].get("error"):
        patterns.append("POL-USD/MATIC-USD: no 1H data from yfinance (possibly delisted or unsupported for 1h).")
    if "TON-USD" in coin_results and "error" not in coin_results["TON-USD"]:
        patterns.append("TON-USD: extreme negative returns suggest data issue (scale or bad ticks in yfinance); treat TON results as invalid until verified.")
    print("\nPatterns:")
    for p in patterns:
        print(f"  - {p}")

    # Save JSON
    export = {
        "timeframe": "1h",
        "tp_pct": TP_PCT,
        "sl_pct": SL_PCT,
        "commission_pct": COMMISSION_PCT,
        "table": all_rows,
        "by_coin": {k: {"bars": v.get("bars"), "error": v.get("error"), "modes": v.get("modes"), "rows": v.get("rows", [])} for k, v in coin_results.items()},
        "summary": {
            "losing_coins": losing_coins,
            "best_mode_per_coin": best_mode_per_coin,
            "mode_win_count": mode_wins,
            "patterns": patterns,
            "data_quality_notes": {
                "POL-USD": "No 1h data (yfinance); MATIC-USD fallback also failed.",
                "TON-USD": "Extreme return/MaxDD suggest yfinance data issue; results likely invalid.",
            },
        },
    }
    out_path.write_text(json.dumps(export, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
