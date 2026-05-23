#!/usr/bin/env python3
"""
Smart TP/SL vs Fixed 3%/2% — v0.04 Dynamic only, 1H, multiple coins.
Compares: Fixed 3%/2% vs Smart (atrPct*1.5 / atrPct*1.0).
Output: table, summary, backtest_results/smart_tpsl_comparison.json
"""

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from backtest_kimi_cursor_v04 import (
    compute_all_signals,
    v04_dynamic,
    backtest_fixed_pct,
    backtest_smart_pct,
    fetch_ohlc,
)

SYMBOLS = [
    "BTC-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD",
    "ETH-USD", "ADA-USD", "AVAX-USD", "DOT-USD", "TRX-USD",
    "LINK-USD", "LTC-USD", "SHIB-USD",
]
TF = "1h"
DAYS = 729
MIN_BARS = 200


def run_one(symbol: str):
    df = fetch_ohlc(symbol, TF, days=DAYS)
    if df is None or len(df) < MIN_BARS:
        return symbol, None, None
    all_sigs = compute_all_signals(df)
    buy, sell = v04_dynamic(df, all_sigs)
    fixed = backtest_fixed_pct(df, buy, sell, tp_pct=3.0, sl_pct=2.0)
    smart = backtest_smart_pct(df, buy, sell, tp_mult=1.5, sl_mult=1.0)
    return symbol, fixed, smart


def main():
    out_path = Path("backtest_results/smart_tpsl_comparison.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("SYMBOL | TP/SL Mode | Trades | WR% | PF | Return% | MaxDD% | Sharpe")
    print("-" * 70)

    rows = []
    for symbol in SYMBOLS:
        symbol, fixed, smart = run_one(symbol)
        if fixed is None:
            print(f"{symbol} | (insufficient data)")
            rows.append({"symbol": symbol, "error": "insufficient_data", "fixed": None, "smart": None})
            continue
        print(f"{symbol} | Fixed 3%/2% | {fixed['num_trades']} | {fixed['win_rate']} | {fixed['profit_factor']} | {fixed['total_return']}% | {fixed['max_drawdown']}% | {fixed['sharpe']}")
        print(f"{symbol} | Smart ATR%   | {smart['num_trades']} | {smart['win_rate']} | {smart['profit_factor']} | {smart['total_return']}% | {smart['max_drawdown']}% | {smart['sharpe']}")
        rows.append({"symbol": symbol, "fixed": fixed, "smart": smart})

    # Summary
    valid = [r for r in rows if r.get("fixed") is not None and r.get("smart") is not None]
    if not valid:
        print("\nNo valid results to compare.")
        save = {"rows": rows, "summary": {"coins_improved": 0, "avg_pf_improvement": 0, "still_lose_with_smart": []}}
        out_path.write_text(json.dumps(save, indent=2))
        return

    improved = [r for r in valid if r["smart"]["profit_factor"] > r["fixed"]["profit_factor"]]
    still_lose = [r["symbol"] for r in valid if r["smart"]["profit_factor"] < 1.0]
    pf_deltas = [r["smart"]["profit_factor"] - r["fixed"]["profit_factor"] for r in valid]
    avg_pf_improvement = sum(pf_deltas) / len(pf_deltas) if pf_deltas else 0

    print()
    print("--- Summary ---")
    print(f"Coins improved with Smart vs Fixed: {len(improved)}/{len(valid)}")
    print(f"Average PF improvement (Smart - Fixed): {avg_pf_improvement:.3f}")
    print(f"Coins still losing with Smart (PF<1): {still_lose}")

    save = {
        "rows": rows,
        "summary": {
            "coins_improved": len(improved),
            "coins_total": len(valid),
            "avg_pf_improvement": round(avg_pf_improvement, 4),
            "still_lose_with_smart": still_lose,
        },
    }
    out_path.write_text(json.dumps(save, indent=2))
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
    sys.exit(0)
