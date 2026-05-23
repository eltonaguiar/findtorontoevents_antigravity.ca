#!/usr/bin/env python3
"""Backtest COMMODITY Seasonal strategy on 5y yfinance OHLCV.

Validates expected PF 2.2 before flipping COMMODITY_SEASONAL_ENABLED=1.

Usage:
    python tools/backtest_commodity_seasonal.py
    python tools/backtest_commodity_seasonal.py --years 3 --output report.md

Writes report at reports/backtest_commodity_seasonal_<UTC>.md.
Exits 0 always (read-only).
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    from alpha_engine.commodity_seasonal import (
        ASSET_CLASS,
        ATR_SL_MULT,
        ATR_TP_MULT,
        CROP_TO_SYMBOL,
        HOLD_DAYS,
        PEAK_WEEKS,
    )
except Exception as e:
    print(f"FATAL: cannot import commodity_seasonal: {e}")
    sys.exit(0)


def _try_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        return None


def _atr(highs, lows, closes, period=14):
    """True-range ATR approximation (last `period` bars)."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period if trs else None


def _detect_window(week: int, crop: str):
    """Mirror commodity_seasonal._detect_window logic."""
    peaks = PEAK_WEEKS[crop]
    plant_lo = peaks["planting_peak"] - 2
    plant_hi = peaks["planting_peak"]
    harv_lo = peaks["harvest_peak"] - 2
    harv_hi = peaks["harvest_peak"]
    if plant_lo <= week < plant_hi:
        return "LONG"
    if harv_lo <= week < harv_hi:
        return "SHORT"
    return None


def backtest_one_symbol(yf_module, crop: str, symbol: str, years: int):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 30)
    try:
        df = yf_module.download(
            symbol, start=start.isoformat(), end=end.isoformat(),
            progress=False, auto_adjust=False, threads=False,
        )
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "trades": []}
    if df is None or df.empty:
        return {"symbol": symbol, "error": "no_data", "trades": []}

    # Normalize columns (yfinance can return MultiIndex)
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    dates = df.index.tolist()

    trades = []
    in_pos = False
    entry_i = None
    entry_price = None
    tp = sl = None
    direction = None

    for i in range(20, len(dates)):
        # Manage open position
        if in_pos:
            held = i - entry_i
            hi, lo = highs[i], lows[i]
            exit_price = None
            exit_reason = None
            if direction == "LONG":
                if hi >= tp:
                    exit_price = tp
                    exit_reason = "TP"
                elif lo <= sl:
                    exit_price = sl
                    exit_reason = "SL"
            else:  # SHORT
                if lo <= tp:
                    exit_price = tp
                    exit_reason = "TP"
                elif hi >= sl:
                    exit_price = sl
                    exit_reason = "SL"
            if exit_price is None and held >= HOLD_DAYS:
                exit_price = closes[i]
                exit_reason = "TIME"
            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                if direction == "SHORT":
                    pnl_pct = -pnl_pct
                trades.append({
                    "entry_date": dates[entry_i].isoformat()[:10],
                    "exit_date": dates[i].isoformat()[:10],
                    "direction": direction,
                    "entry": round(entry_price, 4),
                    "exit": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "held_days": held,
                })
                in_pos = False

        # Look for new entry
        if not in_pos:
            try:
                week = dates[i].isocalendar()[1]
            except Exception:
                continue
            direction_cand = _detect_window(week, crop)
            if direction_cand is None:
                continue
            atr = _atr(highs[: i + 1], lows[: i + 1], closes[: i + 1])
            if atr is None or atr <= 0:
                continue
            entry_price = closes[i]
            if direction_cand == "LONG":
                tp = entry_price + ATR_TP_MULT * atr
                sl = entry_price - ATR_SL_MULT * atr
            else:
                tp = entry_price - ATR_TP_MULT * atr
                sl = entry_price + ATR_SL_MULT * atr
            in_pos = True
            entry_i = i
            direction = direction_cand

    return {"symbol": symbol, "trades": trades}


def aggregate(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "mdd_pct": 0.0, "expectancy": 0.0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sum_wins = sum(t["pnl_pct"] for t in wins)
    sum_losses = abs(sum(t["pnl_pct"] for t in losses))
    pf = sum_wins / sum_losses if sum_losses > 0 else float("inf")
    wr = len(wins) / len(trades) * 100
    expectancy = sum(t["pnl_pct"] for t in trades) / len(trades)
    # Compute MDD on equity curve
    equity = 0.0
    peak = 0.0
    mdd = 0.0
    for t in trades:
        equity += t["pnl_pct"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > mdd:
            mdd = dd
    return {
        "n": len(trades),
        "wr_pct": round(wr, 2),
        "pf": round(pf, 3) if pf != float("inf") else "inf",
        "mdd_pct": round(mdd, 2),
        "expectancy": round(expectancy, 3),
    }


def verdict(pf) -> str:
    if pf == "inf":
        return "PASS"
    if pf >= 1.5:
        return "PASS"
    if pf >= 1.0:
        return "WARN"
    return "FAIL"


def write_report(results: list[dict], out_path: Path) -> None:
    lines = ["# Backtest — COMMODITY Seasonal Planting/Harvest", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Per-symbol results")
    lines.append("")
    lines.append("| Symbol | n | WR% | PF | MDD% | Expectancy% | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---:|:---|")
    all_trades = []
    for r in results:
        sym = r["symbol"]
        trades = r.get("trades") or []
        all_trades.extend(trades)
        if "error" in r:
            lines.append(f"| {sym} | 0 | — | — | — | — | ERROR: {r['error']} |")
            continue
        agg = aggregate(trades)
        v = verdict(agg["pf"])
        lines.append(f"| {sym} | {agg['n']} | {agg['wr_pct']} | {agg['pf']} | {agg['mdd_pct']} | {agg['expectancy']} | {v} |")
    lines.append("")
    overall = aggregate(all_trades)
    overall_v = verdict(overall["pf"])
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- **n:** {overall['n']}")
    lines.append(f"- **WR:** {overall['wr_pct']}%")
    lines.append(f"- **PF:** {overall['pf']}")
    lines.append(f"- **MDD:** {overall['mdd_pct']}%")
    lines.append(f"- **Expectancy/trade:** {overall['expectancy']}%")
    lines.append(f"- **Verdict:** {overall_v}  (PASS = PF>=1.5, WARN = 1.0-1.5, FAIL = <1.0)")
    lines.append("")
    if all_trades:
        srt = sorted(all_trades, key=lambda t: t["pnl_pct"], reverse=True)
        lines.append("## Best 5 trades")
        for t in srt[:5]:
            lines.append(f"- {t['entry_date']} -> {t['exit_date']} {t['direction']} pnl={t['pnl_pct']:+.2f}% ({t['exit_reason']})")
        lines.append("")
        lines.append("## Worst 5 trades")
        for t in srt[-5:][::-1]:
            lines.append(f"- {t['entry_date']} -> {t['exit_date']} {t['direction']} pnl={t['pnl_pct']:+.2f}% ({t['exit_reason']})")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--output", type=str)
    args = ap.parse_args()

    yf_module = _try_yfinance()
    if yf_module is None:
        print("yfinance not installed; verdict=DATA_GAP")
        out_path = REPO / "reports" / f"backtest_commodity_seasonal_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
        out_path.write_text("# Backtest COMMODITY Seasonal\n\nVerdict: DATA_GAP (yfinance not installed)\n", encoding="utf-8")
        return

    results = []
    for crop, symbol in CROP_TO_SYMBOL.items():
        print(f"  backtesting {crop} {symbol} ({args.years}y)...", flush=True)
        r = backtest_one_symbol(yf_module, crop, symbol, args.years)
        n = len(r.get("trades") or [])
        print(f"    -> {n} trades")
        results.append(r)
        time.sleep(0.5)

    out_path = Path(args.output) if args.output else (
        REPO / "reports" / f"backtest_commodity_seasonal_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(results, out_path)


if __name__ == "__main__":
    main()
