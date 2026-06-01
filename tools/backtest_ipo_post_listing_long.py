#!/usr/bin/env python3
"""Backtest IPO asset class: LONG post-listing momentum (T+90 entry, 60d hold).

NOT lockup-expiry short (verified FAIL PF 0.18 n=23).
Uses alpha_engine/data/ipo_calendar.json + yfinance prices.

Output: audit_dashboard/data/ipo_post_listing_long_backtest.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import pandas as pd
    import yfinance as yf
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
CAL = ROOT / "alpha_engine/data/ipo_calendar.json"
OUT = ROOT / "audit_dashboard/data/ipo_post_listing_long_backtest.json"

ENTRY_DAYS_AFTER_IPO = 90
HOLD_DAYS = 60
SLIPPAGE_PCT = 0.02
COMMISSION_PCT = 0.001
MIN_PRICE = 5.0


def _trading_days_after(start: str, offset: int) -> str:
    d = datetime.strptime(start, "%Y-%m-%d")
    added = 0
    while added < offset:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d.strftime("%Y-%m-%d")


def _price_on(hist, target: str) -> float | None:
    if hist is None or hist.empty:
        return None
    try:
        ts = pd.Timestamp(target)
    except Exception:
        return None
    idx = hist.index
    if getattr(idx, "tz", None) is not None:
        ts = ts.tz_localize(idx.tz) if ts.tzinfo is None else ts.tz_convert(idx.tz)
    sub = hist[idx <= ts]
    if sub.empty:
        return None
    col = "Close"
    if hasattr(sub.columns, "get_level_values"):
        try:
            sub.columns = sub.columns.get_level_values(0)
        except Exception:
            pass
    return float(sub[col].iloc[-1])


def run_backtest() -> dict:
    cal = json.loads(CAL.read_text(encoding="utf-8"))
    trades: list[dict] = []
    wins = losses = 0
    win_pnl = loss_pnl = 0.0

    for ipo in cal.get("ipos", []):
        sym = ipo.get("symbol")
        ipo_date = ipo.get("ipo_date")
        if not sym or not ipo_date:
            continue
        entry_date = _trading_days_after(ipo_date, ENTRY_DAYS_AFTER_IPO)
        exit_date = _trading_days_after(entry_date, HOLD_DAYS)
        try:
            hist = yf.download(sym, start=ipo_date, end="2026-06-15", progress=False, auto_adjust=True)
        except Exception:
            continue
        entry_px = _price_on(hist, entry_date)
        exit_px = _price_on(hist, exit_date)
        if entry_px is None or exit_px is None or entry_px < MIN_PRICE:
            continue
        gross = (exit_px - entry_px) / entry_px
        net = gross - 2 * SLIPPAGE_PCT - 2 * COMMISSION_PCT
        outcome = "WIN" if net > 0 else "LOSS"
        if net > 0:
            wins += 1
            win_pnl += net
        else:
            losses += 1
            loss_pnl += abs(net)
        trades.append({
            "symbol": sym,
            "ipo_date": ipo_date,
            "entry_date": entry_date,
            "exit_date": exit_date,
            "entry_price": round(entry_px, 2),
            "exit_price": round(exit_px, 2),
            "pnl_pct": round(net * 100, 2),
            "outcome": outcome,
        })

    n = len(trades)
    wr = (wins / n * 100) if n else 0.0
    pf = (win_pnl / loss_pnl) if loss_pnl > 0 else (float("inf") if win_pnl > 0 else 0.0)
    return {
        "strategy": "ipo_post_listing_momentum_long",
        "asset_class": "IPO",
        "entry_rule": f"T+{ENTRY_DAYS_AFTER_IPO}d LONG hold {HOLD_DAYS}d",
        "n_trades": n,
        "win_rate_pct": round(wr, 2),
        "profit_factor": round(pf, 4) if pf != float("inf") else 999.0,
        "total_pnl_pct": round(sum(t["pnl_pct"] for t in trades), 2),
        "trades": trades,
        "note": "n<100 — research only; lockup SHORT variant FAILED (see ipo_lockup_backtest)",
    }


def main() -> None:
    result = run_backtest()
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "trades"}, indent=2))


if __name__ == "__main__":
    main()
