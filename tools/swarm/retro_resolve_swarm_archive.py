#!/usr/bin/env python3
"""retro_resolve_swarm_archive.py — one-shot HONEST resolution of the frozen swarm book.

Context (2026-06-12): the swarm paper-picks experiment was decommissioned with
309/340 picks never resolved because `outcome_resolver_swarm._resolve_yf_ticker`
only understood exchange-prefixed symbols; 302 open picks use bare symbols
(LINKUSDT, SPY, CL=F, ^TNX...) and were silently skipped nightly. Retiring the
book without resolving it would discard the only multi-engine attribution data
ever collected (43 underlying models).

WHY NOT just run the old resolver with a symbol fix: its fetch returns the
WINDOW max-high/min-low and checks TP before SL — whole-window aggregation with
a generous tie order is exactly the look-ahead bias class that corrupted the
main book (master loop §1). This tool resolves honestly instead:

  * daily OHLC series walk (yfinance), FIRST-TOUCH day by day
  * same-day TP+SL touch = AMBIGUOUS -> resolved as SL (conservative,
    flagged `ambiguous: true`) — house methodology (v2 spec §7)
  * past the timeframe cap: TIME_CAP at that day's real close with real pnl
    (the old resolver left TIME_CAP pnl None, which silently censored the
    slow cohort out of every leaderboard denominator)

Daily bars cannot order intra-day touches; with multi-day windows this is the
best honest granularity available for a frozen archive. Results are stamped
`retro_resolver: "first_touch_daily_v1"` so they are distinguishable from the
31 legacy resolutions.

Usage:
    python3 tools/swarm/retro_resolve_swarm_archive.py --dry-run   # report only
    python3 tools/swarm/retro_resolve_swarm_archive.py --apply     # write _OLD book
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.outcome_resolver_swarm import SYMBOL_MAP, TIMEFRAME_CAP_DAYS  # noqa: E402

STORE_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks_OLD.json"


def resolve_ticker(symbol: str) -> str | None:
    """Superset of the old mapper: handles the 302 bare symbols."""
    if symbol in SYMBOL_MAP:
        return SYMBOL_MAP[symbol]
    if ":" in symbol:
        prefix, tail = symbol.split(":", 1)
        if prefix in {"NYSE", "NASDAQ", "AMEX"}:
            return tail
        symbol = tail  # other prefixes: try the tail bare
    s = symbol.strip().upper()
    if not s:
        return None
    # bare crypto perp/spot codes -> yfinance spot pairs
    for suffix in ("USDT", "USDC", "USD"):
        if s.endswith(suffix) and len(s) > len(suffix):
            return s[: -len(suffix)] + "-USD"
    # futures (CL=F), indices (^TNX), forex (EURUSD=X), equities/ETFs: as-is
    return s


def fetch_daily(ticker: str, since: datetime, until: datetime):
    """[(date, high, low, close)] ascending, or None."""
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(
            start=since.date().isoformat(),
            end=(until + timedelta(days=1)).date().isoformat(),
            interval="1d", auto_adjust=False)
        if df.empty:
            return None
        return [(idx.to_pydatetime().replace(tzinfo=timezone.utc),
                 float(r["High"]), float(r["Low"]), float(r["Close"]))
                for idx, r in df.iterrows()]
    except Exception:
        return None


def first_touch(p: dict, bars, now: datetime) -> dict | None:
    created = datetime.fromisoformat(p["created_at"])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    cap_time = created + timedelta(days=TIMEFRAME_CAP_DAYS.get(p["timeframe"], 30))
    entry, tp, sl = float(p["entry"]), float(p["tp"]), float(p["sl"])
    is_long = p["direction"] == "LONG"
    risk = (entry - sl) if is_long else (sl - entry)
    last_close = None
    for (day, high, low, close) in bars:
        if day < created.replace(hour=0, minute=0, second=0, microsecond=0):
            continue
        if day > cap_time:
            break
        last_close = close
        tp_hit = high >= tp if is_long else low <= tp
        sl_hit = low <= sl if is_long else high >= sl
        if sl_hit:  # SL wins ties (conservative); ambiguous flagged
            pnl = (sl / entry - 1) * 100 if is_long else (entry / sl - 1) * 100
            return {"exit_reason": "SL_HIT", "exit_price": sl,
                    "exit_time": day.isoformat(), "pnl_pct": pnl, "pnl_R": -1.0,
                    "ambiguous": bool(tp_hit),
                    "retro_resolver": "first_touch_daily_v1"}
        if tp_hit:
            pnl = (tp / entry - 1) * 100 if is_long else (entry / tp - 1) * 100
            return {"exit_reason": "TP_HIT", "exit_price": tp,
                    "exit_time": day.isoformat(), "pnl_pct": pnl,
                    "pnl_R": (abs(tp - entry) / risk) if risk > 0 else None,
                    "ambiguous": False,
                    "retro_resolver": "first_touch_daily_v1"}
    if now > cap_time and last_close is not None:
        pnl = (last_close / entry - 1) * 100 if is_long \
            else (entry / last_close - 1) * 100
        return {"exit_reason": "TIME_CAP", "exit_price": last_close,
                "exit_time": cap_time.isoformat(), "pnl_pct": pnl,
                "pnl_R": ((pnl / 100) * entry / risk) if risk > 0 else None,
                "ambiguous": False,
                "retro_resolver": "first_touch_daily_v1"}
    return None  # still inside cap with no touch (shouldn't happen on a frozen book)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    picks = json.loads(STORE_PATH.read_text())
    now = datetime.now(timezone.utc)
    open_picks = [p for p in picks if p.get("outcome") is None]
    print(f"book: {len(picks)} picks, {len(open_picks)} unresolved")

    # one fetch per unique symbol
    series: dict[str, list | None] = {}
    for sym in sorted({p["symbol"] for p in open_picks}):
        tkr = resolve_ticker(sym)
        if tkr is None:
            series[sym] = None
            continue
        earliest = min(datetime.fromisoformat(p["created_at"]).replace(tzinfo=timezone.utc)
                       if datetime.fromisoformat(p["created_at"]).tzinfo is None
                       else datetime.fromisoformat(p["created_at"])
                       for p in open_picks if p["symbol"] == sym)
        series[sym] = fetch_daily(tkr, earliest, now)

    fetched = sum(1 for v in series.values() if v)
    print(f"symbols: {len(series)} unique, {fetched} with price series")

    stats = {"TP_HIT": 0, "SL_HIT": 0, "TIME_CAP": 0, "no_data": 0, "no_touch": 0,
             "ambiguous": 0}
    for p in open_picks:
        bars = series.get(p["symbol"])
        if not bars:
            stats["no_data"] += 1
            continue
        out = first_touch(p, bars, now)
        if out is None:
            stats["no_touch"] += 1
            continue
        stats[out["exit_reason"]] += 1
        if out.get("ambiguous"):
            stats["ambiguous"] += 1
        if args.apply:
            p["outcome"] = out

    print(json.dumps(stats, indent=1))
    if args.apply:
        tmp = STORE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(picks, indent=1))
        tmp.replace(STORE_PATH)
        n_res = sum(1 for p in picks if p.get("outcome"))
        print(f"wrote {STORE_PATH.name}: {n_res}/{len(picks)} now resolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
