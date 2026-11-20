#!/usr/bin/env python3
"""Equity/ETF Donchian breakout candidates — DRY RUN only.

Why: POD-EQUITY-BREAKOUT has no live emitter. Its four registered names exist in no
emission table, and the same-named "real" strategies emit CRYPTO/FUTURES/COMMODITY
only (docs/B1_POD_STRATEGY_NAMES_FINDING_2026-11-20.md §2b). This tool produces the
signal the pod was supposed to test, from real bars, without writing to any table.

Rules (pre-registered in this docstring before the first run):
  * daily bars aggregated from stock_ohlcv 1h;
  * LONG when today's close > the highest high of the prior 20 days;
  * stop = lowest low of the prior 10 days; target = entry + 2 x (entry - stop);
  * no signal if fewer than 21 daily bars or a degenerate stop.

Output is a candidates JSON for human review. Wiring it into the pick pipeline is a
separate, owner-approved step.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "EFA", "EEM", "GLD", "SLV", "TLT",
                    "XLE", "XLK", "XLV", "XLF", "XLP", "XLI"]
ENTRY_LOOKBACK = 20
STOP_LOOKBACK = 10


def daily_bars(rows: list[dict]) -> list[dict]:
    """Aggregate (likely hourly) rows into UTC daily OHLCV."""
    by_day: dict[str, dict] = {}
    for r in rows:
        day = datetime.fromtimestamp(int(r["timestamp"]) / 1000, timezone.utc).strftime("%Y-%m-%d")
        b = by_day.get(day)
        if b is None:
            by_day[day] = {"date": day, "open": float(r["open"]), "high": float(r["high"]),
                           "low": float(r["low"]), "close": float(r["close"]),
                           "volume": float(r.get("volume") or 0)}
        else:
            b["high"] = max(b["high"], float(r["high"]))
            b["low"] = min(b["low"], float(r["low"]))
            b["close"] = float(r["close"])
            b["volume"] += float(r.get("volume") or 0)
    return [by_day[d] for d in sorted(by_day)]


def donchian_signal(bars: list[dict], entry_lookback: int = ENTRY_LOOKBACK,
                    stop_lookback: int = STOP_LOOKBACK) -> dict | None:
    """LONG breakout of the prior-N-day high, with a prior-M-day stop."""
    if len(bars) < entry_lookback + 1:
        return None
    today, prior = bars[-1], bars[-(entry_lookback + 1):-1]
    entry = today["close"]
    channel_high = max(b["high"] for b in prior)
    if entry <= channel_high:
        return None
    stop_window = bars[-stop_lookback:]
    stop = min(b["low"] for b in stop_window)
    if stop <= 0 or stop >= entry:
        return None
    return {"entry": round(entry, 4), "stop": round(stop, 4),
            "target": round(entry + 2.0 * (entry - stop), 4),
            "channel_high": round(channel_high, 4),
            "breakout_pct": round((entry / channel_high - 1.0) * 100.0, 3)}


def _fetch(symbols: list[str]) -> dict[str, list[dict]]:
    import pymysql
    from tools.db_env import get_stocks_creds
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    conn = pymysql.connect(cursorclass=pymysql.cursors.DictCursor,
                           **{k: v for k, v in get_stocks_creds().items() if k in keep})
    cur = conn.cursor()
    out = {}
    try:
        for s in symbols:
            cur.execute("SELECT timestamp, open, high, low, close, volume FROM stock_ohlcv "
                        "WHERE symbol=%s ORDER BY timestamp", (s,))
            out[s] = cur.fetchall()
    finally:
        conn.close()
    return out


def scan(symbols: list[str], rows_by_symbol: dict[str, list[dict]]) -> list[dict]:
    picked = []
    for s in symbols:
        bars = daily_bars(rows_by_symbol.get(s) or [])
        sig = donchian_signal(bars)
        if not sig:
            continue
        picked.append({
            "symbol": s,
            "asset_class": "ETF" if s in DEFAULT_UNIVERSE else "EQUITY",
            "strategy": "donchian_breakout_scalp",
            "direction": "LONG",
            "as_of": bars[-1]["date"],
            "bars": len(bars),
            **sig,
        })
    return picked


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="equity/ETF Donchian candidates (dry run)")
    ap.add_argument("--universe", nargs="+", default=DEFAULT_UNIVERSE)
    ap.add_argument("--out", default=str(REPO / "reports" / "equity_breakout_candidates.json"))
    ap.add_argument("--rows-json", help="offline {symbol: [rows]} override")
    args = ap.parse_args(argv)

    rows = json.loads(Path(args.rows_json).read_text()) if args.rows_json \
        else _fetch(args.universe)
    picks = scan(args.universe, rows)
    rep = {"schema": "equity_breakout_candidates.v1",
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "universe": args.universe, "n_candidates": len(picks), "candidates": picks,
           "note": "DRY RUN — nothing is written to trading_picks or at_signal_outcomes."}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{len(picks)} candidate(s) of {len(args.universe)} symbols -> {args.out}")
    for p in picks:
        print(f"  {p['symbol']:5} entry {p['entry']:.2f} stop {p['stop']:.2f} "
              f"target {p['target']:.2f} breakout {p['breakout_pct']:+.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
