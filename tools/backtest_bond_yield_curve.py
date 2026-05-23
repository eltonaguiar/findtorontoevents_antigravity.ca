#!/usr/bin/env python3
"""Backtest BOND Yield Curve Inversion strategy on 5y data.

LONG TLT/IEF when T10Y2Y spread inverts (<0) AND deepening (>5bp drop / 30d).
SHORT TLT when steepening (positive AND >10bp rise / 30d).

Spread source priority:
  1. FRED API (env FRED_API_KEY) for T10Y2Y series.
  2. yfinance ^TNX (10Y) - ^IRX (3M as 2Y proxy) — coarse fallback.
  3. TLT-relative-momentum proxy — last-resort.

Usage:
    python tools/backtest_bond_yield_curve.py
    python tools/backtest_bond_yield_curve.py --years 3 --output report.md

Writes report at reports/backtest_bond_yield_curve_<UTC>.md.
Exits 0 always (read-only).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

SYMBOLS_LONG = ["TLT", "IEF"]
SYMBOL_SHORT = "TLT"
ATR_TP_MULT = 1.2
ATR_SL_MULT = 1.0
HOLD_DAYS = 30
SPREAD_LOOKBACK = 30
DROP_BP_THRESHOLD = 5.0   # LONG entry: drop >5bp over 30d
RISE_BP_THRESHOLD = 10.0  # SHORT entry: rise >10bp over 30d


def _try_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        return None


def _try_requests():
    try:
        import requests
        return requests
    except ImportError:
        return None


def _atr(highs, lows, closes, period=14):
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


def _fetch_spread_fred(years: int):
    """Return dict[iso_date] -> spread_pp via FRED API, or None."""
    key = (os.getenv("FRED_API_KEY") or "").strip()
    if not key:
        return None
    req = _try_requests()
    if req is None:
        return None
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "T10Y2Y",
        "api_key": key,
        "file_type": "json",
        "observation_start": start.isoformat(),
        "observation_end": end.isoformat(),
    }
    try:
        r = req.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None
        obs = r.json().get("observations") or []
        out = {}
        for o in obs:
            v = o.get("value")
            d = o.get("date")
            if v in (None, "", "."):
                continue
            try:
                out[d] = float(v)
            except ValueError:
                continue
        return out or None
    except Exception:
        return None


def _fetch_spread_yfinance_proxy(yf_module, years: int):
    """Crude proxy: ^TNX (10Y yield) minus ^IRX (13W bill, 2Y not on yfinance).

    Returns dict[iso_date] -> spread_pp or None.
    Note: This is a 10Y - 3M proxy, NOT 10Y - 2Y. Flagged in the report.
    """
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    try:
        tnx = yf_module.download("^TNX", start=start.isoformat(), end=end.isoformat(),
                                 progress=False, auto_adjust=False, threads=False)
        irx = yf_module.download("^IRX", start=start.isoformat(), end=end.isoformat(),
                                 progress=False, auto_adjust=False, threads=False)
    except Exception:
        return None
    if tnx is None or irx is None or tnx.empty or irx.empty:
        return None
    if hasattr(tnx.columns, "levels"):
        tnx.columns = [c[0] if isinstance(c, tuple) else c for c in tnx.columns]
    if hasattr(irx.columns, "levels"):
        irx.columns = [c[0] if isinstance(c, tuple) else c for c in irx.columns]
    out = {}
    for d, v10 in tnx["Close"].items():
        try:
            v3 = irx["Close"].get(d)
            if v3 is None:
                continue
            out[d.date().isoformat()] = float(v10) - float(v3)
        except Exception:
            continue
    return out or None


def _fetch_spread_tlt_momentum(yf_module, years: int):
    """Last-resort proxy: invert sign of 30d TLT return.

    When TLT is rallying (long duration rallying), curve is typically inverting
    → spread falls. So spread_proxy = -1 * TLT 30d %change (relative scale).
    Returns dict[iso_date] -> proxy in pp-equivalent.
    """
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 60)
    try:
        df = yf_module.download("TLT", start=start.isoformat(), end=end.isoformat(),
                                progress=False, auto_adjust=False, threads=False)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    closes = df["Close"].tolist()
    dates = [d.date().isoformat() for d in df.index.tolist()]
    out = {}
    for i in range(30, len(closes)):
        try:
            pct = (closes[i] - closes[i - 30]) / closes[i - 30]
            out[dates[i]] = -pct * 100.0  # invert; treat as pp-ish
        except Exception:
            continue
    return out or None


def _signal_for_date(spread_map, dates_sorted, idx):
    """Return 'LONG'/'SHORT'/None for bar at idx given spread_map."""
    if idx < SPREAD_LOOKBACK:
        return None
    d_now = dates_sorted[idx]
    d_prev = dates_sorted[idx - SPREAD_LOOKBACK]
    s_now = spread_map.get(d_now)
    s_prev = spread_map.get(d_prev)
    if s_now is None or s_prev is None:
        return None
    delta_bp = (s_now - s_prev) * 100.0
    inverted = s_now < 0.0
    if inverted and delta_bp < -DROP_BP_THRESHOLD:
        return "LONG"
    if (not inverted) and delta_bp > RISE_BP_THRESHOLD:
        return "SHORT"
    return None


def backtest_symbol(yf_module, symbol, spread_map, years, allow_short=True):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * years + 30)
    try:
        df = yf_module.download(symbol, start=start.isoformat(), end=end.isoformat(),
                                progress=False, auto_adjust=False, threads=False)
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "trades": []}
    if df is None or df.empty:
        return {"symbol": symbol, "error": "no_data", "trades": []}
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    dates = [d.date().isoformat() for d in df.index.tolist()]

    trades = []
    in_pos = False
    entry_i = entry_price = tp = sl = None
    direction = None
    last_signal_i = -999

    for i in range(SPREAD_LOOKBACK + 14, len(dates)):
        if in_pos:
            held = i - entry_i
            hi, lo = highs[i], lows[i]
            exit_price = None
            exit_reason = None
            if direction == "LONG":
                if hi >= tp:
                    exit_price, exit_reason = tp, "TP"
                elif lo <= sl:
                    exit_price, exit_reason = sl, "SL"
            else:
                if lo <= tp:
                    exit_price, exit_reason = tp, "TP"
                elif hi >= sl:
                    exit_price, exit_reason = sl, "SL"
            if exit_price is None and held >= HOLD_DAYS:
                exit_price, exit_reason = closes[i], "TIME"
            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                if direction == "SHORT":
                    pnl_pct = -pnl_pct
                trades.append({
                    "entry_date": dates[entry_i],
                    "exit_date": dates[i],
                    "direction": direction,
                    "entry": round(entry_price, 4),
                    "exit": round(exit_price, 4),
                    "pnl_pct": round(pnl_pct, 3),
                    "exit_reason": exit_reason,
                    "held_days": held,
                })
                in_pos = False

        if not in_pos:
            sig = _signal_for_date(spread_map, dates, i)
            if sig is None:
                continue
            if sig == "SHORT" and not allow_short:
                continue
            # Debounce: re-arm only if 5 bars since last signal
            if i - last_signal_i < 5:
                continue
            atr = _atr(highs[: i + 1], lows[: i + 1], closes[: i + 1])
            if atr is None or atr <= 0:
                continue
            entry_price = closes[i]
            if sig == "LONG":
                tp = entry_price + ATR_TP_MULT * atr
                sl = entry_price - ATR_SL_MULT * atr
            else:
                tp = entry_price - ATR_TP_MULT * atr
                sl = entry_price + ATR_SL_MULT * atr
            in_pos = True
            entry_i = i
            direction = sig
            last_signal_i = i

    return {"symbol": symbol, "trades": trades}


def aggregate(trades):
    if not trades:
        return {"n": 0, "wr_pct": 0.0, "pf": 0.0, "mdd_pct": 0.0, "expectancy": 0.0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    sum_wins = sum(t["pnl_pct"] for t in wins)
    sum_losses = abs(sum(t["pnl_pct"] for t in losses))
    pf = sum_wins / sum_losses if sum_losses > 0 else float("inf")
    wr = len(wins) / len(trades) * 100
    expectancy = sum(t["pnl_pct"] for t in trades) / len(trades)
    equity = peak = mdd = 0.0
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


def verdict(pf):
    if pf == "inf":
        return "PASS"
    if pf >= 1.5:
        return "PASS"
    if pf >= 1.0:
        return "WARN"
    return "FAIL"


def write_report(results, spread_source, out_path):
    lines = ["# Backtest - BOND Yield Curve Inversion", ""]
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Spread source:** {spread_source}")
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
            lines.append(f"| {sym} | 0 | - | - | - | - | ERROR: {r['error']} |")
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

    out_path = Path(args.output) if args.output else (
        REPO / "reports" / f"backtest_bond_yield_curve_{datetime.now(timezone.utc).strftime('%Y_%m_%d_%H%MZ')}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    yf_module = _try_yfinance()
    if yf_module is None:
        print("yfinance not installed; verdict=DATA_GAP")
        out_path.write_text("# Backtest BOND Yield Curve Inversion\n\nVerdict: DATA_GAP (yfinance not installed)\n", encoding="utf-8")
        return

    spread_map = _fetch_spread_fred(args.years)
    spread_source = "FRED T10Y2Y"
    if spread_map is None:
        spread_map = _fetch_spread_yfinance_proxy(yf_module, args.years)
        spread_source = "yfinance ^TNX-^IRX (10Y-3M PROXY)"
    if spread_map is None:
        spread_map = _fetch_spread_tlt_momentum(yf_module, args.years)
        spread_source = "TLT 30d inverse-momentum PROXY (last-resort)"
    if spread_map is None:
        print("all spread sources failed; verdict=DATA_GAP")
        out_path.write_text("# Backtest BOND Yield Curve Inversion\n\nVerdict: DATA_GAP (no spread data available)\n", encoding="utf-8")
        return

    results = []
    for sym in SYMBOLS_LONG:
        print(f"  backtesting {sym} ({args.years}y)...", flush=True)
        r = backtest_symbol(yf_module, sym, spread_map, args.years, allow_short=True)
        print(f"    -> {len(r.get('trades') or [])} trades")
        results.append(r)
        time.sleep(0.4)

    write_report(results, spread_source, out_path)


if __name__ == "__main__":
    main()
