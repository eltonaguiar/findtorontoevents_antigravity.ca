#!/usr/bin/env python3
"""
Entry-Anchored Smart TP/SL vs Fixed 3%/2% — v0.04 Dynamic, 1H, 13 coins.
Compares:
  a) Fixed 3%/2% (baseline)
  b) Smart Anchored 1.5/1.0 — TP/SL fixed at entry from entry_atr_pct
  c) Smart Anchored 2.0/1.0 — same, TP mult 2.0

Entry-anchored: at entry bar set entry_atr_pct = atr14/entry_price*100;
tp_level = entry_price * (1 + entry_atr_pct*tp_mult/100) for long (reverse for short);
sl_level = entry_price * (1 - entry_atr_pct*sl_mult/100) for long.
Exit when price hits tp_level or sl_level (levels fixed for entire trade).

Output: table per coin, summary, backtest_results/smart_anchored_comparison.json
"""

import json
import sys
import warnings
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from backtest_kimi_cursor_v04 import (
    calc_atr,
    compute_all_signals,
    v04_dynamic,
    backtest_fixed_pct,
    fetch_ohlc,
)

SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "DOGE-USD",
    "ADA-USD",
    "AVAX-USD",
    "TRX-USD",
    "DOT-USD",
    "LINK-USD",
    "LTC-USD",
    "SHIB-USD",
]
TF = "1h"
DAYS = 729
MIN_BARS = 200
COMMISSION_PCT = 0.1


def backtest_smart_anchored(
    df: pd.DataFrame,
    buy_sig: pd.Series,
    sell_sig: pd.Series,
    tp_mult: float = 1.5,
    sl_mult: float = 1.0,
    commission_pct: float = 0.1,
) -> Dict:
    """
    Entry-anchored Smart TP/SL: at entry capture entry_atr_pct = atr14/entry_price*100,
    set fixed tp_level and sl_level for the entire trade. Exit when price hits level.
    Long: tp_level = entry*(1+entry_atr_pct*tp_mult/100), sl_level = entry*(1-entry_atr_pct*sl_mult/100).
    Short: tp_level = entry*(1-entry_atr_pct*tp_mult/100), sl_level = entry*(1+entry_atr_pct*sl_mult/100).
    Same bar: check TP first, then SL (if both hit, TP wins).
    """
    atr14 = calc_atr(df, 14)
    trades = []
    position = 0
    entry_price = 0.0
    entry_bar = 0
    entry_atr_pct = 0.0
    tp_level = 0.0
    sl_level = 0.0

    for i in range(len(df)):
        c = df["close"].iloc[i]
        h = df["high"].iloc[i]
        l = df["low"].iloc[i]
        a = atr14.iloc[i]
        if pd.isna(a) or a <= 0 or c <= 0:
            a = 0.0
        else:
            a = float(a)

        if position != 0:
            bars_held = i - entry_bar
            # Long: TP when high >= tp_level, SL when low <= sl_level
            # Short: TP when low <= tp_level, SL when high >= sl_level
            if position == 1:
                hit_tp = h >= tp_level
                hit_sl = l <= sl_level
            else:
                hit_tp = l <= tp_level
                hit_sl = h >= sl_level
            flip = (position == 1 and sell_sig.iloc[i]) or (position == -1 and buy_sig.iloc[i])

            if hit_tp or hit_sl or flip:
                if hit_tp:
                    exit_price = tp_level
                    reason = "TP"
                elif hit_sl:
                    exit_price = sl_level
                    reason = "SL"
                else:
                    exit_price = c
                    reason = "FLIP"
                pnl_pct = (exit_price / entry_price - 1) * position * 100 - commission_pct * 2
                trades.append({"pnl": pnl_pct, "bars": bars_held, "reason": reason})
                position = 0

        if position == 0:
            if buy_sig.iloc[i]:
                position = 1
                entry_price = c
                entry_bar = i
                entry_atr_pct = (a / entry_price * 100) if entry_price and a else 2.0
                tp_level = entry_price * (1 + entry_atr_pct * tp_mult / 100)
                sl_level = entry_price * (1 - entry_atr_pct * sl_mult / 100)
            elif sell_sig.iloc[i]:
                position = -1
                entry_price = c
                entry_bar = i
                entry_atr_pct = (a / entry_price * 100) if entry_price and a else 2.0
                tp_level = entry_price * (1 - entry_atr_pct * tp_mult / 100)
                sl_level = entry_price * (1 + entry_atr_pct * sl_mult / 100)

    if not trades:
        return {
            "num_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "avg_bars": 0.0,
        }
    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.001
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0
    pnl_arr = np.array(pnls)
    sharpe = (pnl_arr.mean() / pnl_arr.std() * np.sqrt(252)) if pnl_arr.std() > 0 else 0.0
    return {
        "num_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_win / gross_loss, 3),
        "total_return": round(float(sum(pnls)), 2),
        "max_drawdown": round(float(max_dd), 2),
        "sharpe": round(float(sharpe), 3),
        "avg_bars": round(float(np.mean([t["bars"] for t in trades])), 1),
    }


def run_one(symbol: str) -> tuple:
    df = fetch_ohlc(symbol, TF, days=DAYS)
    if df is None or len(df) < MIN_BARS:
        return symbol, None
    all_sigs = compute_all_signals(df)
    buy, sell = v04_dynamic(df, all_sigs)
    fixed = backtest_fixed_pct(df, buy, sell, tp_pct=3.0, sl_pct=2.0, commission_pct=COMMISSION_PCT)
    anchored_15 = backtest_smart_anchored(
        df, buy, sell, tp_mult=1.5, sl_mult=1.0, commission_pct=COMMISSION_PCT
    )
    anchored_20 = backtest_smart_anchored(
        df, buy, sell, tp_mult=2.0, sl_mult=1.0, commission_pct=COMMISSION_PCT
    )
    return symbol, {"fixed": fixed, "smart_anchored_1_5_1": anchored_15, "smart_anchored_2_0_1": anchored_20}


def main():
    out_path = Path("backtest_results/smart_anchored_comparison.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("v0.04 Dynamic 1H — Fixed 3%/2% vs Smart Anchored 1.5/1.0 vs Smart Anchored 2.0/1.0")
    print("=" * 100)
    print(f"{'SYMBOL':<10} | {'Fixed 3%/2%':^28} | {'Smart Anch 1.5/1':^28} | {'Smart Anch 2.0/1':^28}")
    print(f"{'':10} | {'Trades WR%   PF   Ret%   DD%':^28} | {'Trades WR%   PF   Ret%   DD%':^28} | {'Trades WR%   PF   Ret%   DD%':^28}")
    print("-" * 100)

    rows = []
    for symbol in SYMBOLS:
        symbol, data = run_one(symbol)
        if data is None:
            print(f"{symbol:<10} | (insufficient data)")
            rows.append({"symbol": symbol, "error": "insufficient_data", "fixed": None, "smart_anchored_1_5_1": None, "smart_anchored_2_0_1": None})
            continue
        f, s15, s20 = data["fixed"], data["smart_anchored_1_5_1"], data["smart_anchored_2_0_1"]
        print(
            f"{symbol:<10} | {f['num_trades']:>4} {f['win_rate']:>5.1f}% {f['profit_factor']:>5.3f} {f['total_return']:>+6.2f}% {f['max_drawdown']:>5.2f}% | "
            f"{s15['num_trades']:>4} {s15['win_rate']:>5.1f}% {s15['profit_factor']:>5.3f} {s15['total_return']:>+6.2f}% {s15['max_drawdown']:>5.2f}% | "
            f"{s20['num_trades']:>4} {s20['win_rate']:>5.1f}% {s20['profit_factor']:>5.3f} {s20['total_return']:>+6.2f}% {s20['max_drawdown']:>5.2f}%"
        )
        rows.append({"symbol": symbol, "fixed": f, "smart_anchored_1_5_1": s15, "smart_anchored_2_0_1": s20})

    valid = [r for r in rows if r.get("fixed") is not None]
    if not valid:
        summary = {
            "coins_smart_15_beats_fixed": 0,
            "coins_smart_20_beats_fixed": 0,
            "coins_total": 0,
            "avg_pf_delta_smart_15": 0.0,
            "avg_pf_delta_smart_20": 0.0,
            "coins_improve_most_15": [],
            "coins_improve_most_20": [],
        }
    else:
        n = len(valid)
        smart_15_beats = [r for r in valid if r["smart_anchored_1_5_1"]["profit_factor"] > r["fixed"]["profit_factor"]]
        smart_20_beats = [r for r in valid if r["smart_anchored_2_0_1"]["profit_factor"] > r["fixed"]["profit_factor"]]
        pf_deltas_15 = [r["smart_anchored_1_5_1"]["profit_factor"] - r["fixed"]["profit_factor"] for r in valid]
        pf_deltas_20 = [r["smart_anchored_2_0_1"]["profit_factor"] - r["fixed"]["profit_factor"] for r in valid]
        avg_delta_15 = sum(pf_deltas_15) / n
        avg_delta_20 = sum(pf_deltas_20) / n
        sorted_15 = sorted(valid, key=lambda r: r["smart_anchored_1_5_1"]["profit_factor"] - r["fixed"]["profit_factor"], reverse=True)
        sorted_20 = sorted(valid, key=lambda r: r["smart_anchored_2_0_1"]["profit_factor"] - r["fixed"]["profit_factor"], reverse=True)
        summary = {
            "coins_smart_15_beats_fixed": len(smart_15_beats),
            "coins_smart_20_beats_fixed": len(smart_20_beats),
            "coins_total": n,
            "avg_pf_delta_smart_15": round(avg_delta_15, 4),
            "avg_pf_delta_smart_20": round(avg_delta_20, 4),
            "coins_improve_most_15": [r["symbol"] for r in sorted_15[:5]],
            "coins_improve_most_20": [r["symbol"] for r in sorted_20[:5]],
        }

    print()
    print("--- Summary ---")
    print(f"Coins Smart Anchored 1.5/1.0 beats Fixed: {summary['coins_smart_15_beats_fixed']}/{summary['coins_total']}")
    print(f"Coins Smart Anchored 2.0/1.0 beats Fixed: {summary['coins_smart_20_beats_fixed']}/{summary['coins_total']}")
    print(f"Average PF delta (Smart 1.5/1.0 - Fixed): {summary['avg_pf_delta_smart_15']:.4f}")
    print(f"Average PF delta (Smart 2.0/1.0 - Fixed): {summary['avg_pf_delta_smart_20']:.4f}")
    print(f"Coins that improve most with 1.5/1.0: {summary['coins_improve_most_15']}")
    print(f"Coins that improve most with 2.0/1.0: {summary['coins_improve_most_20']}")

    save = {"rows": rows, "summary": summary}
    out_path.write_text(json.dumps(save, indent=2))
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
    sys.exit(0)
