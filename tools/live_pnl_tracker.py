#!/usr/bin/env python3
"""live_pnl_tracker.py — mark-to-market PnL for unresolved picks-now entries.

Reads all unresolved picks from picks_now_tracker (exit_pnl_pct IS NULL), fetches
current prices via yfinance (equities/ETFs/commodities) and Binance (crypto),
computes unrealized PnL from entry_price to current close, and writes a JSON
snapshot to audit_dashboard/data/picks_now_live_pnl.json for the /audit/picks-now.html
"Live PnL" panel.

Also updates picks_now_tracker.current_price + current_pnl_pct so the DB keeps
a running mark-to-market trail (idempotent — safe to re-run).

Usage:
    python3 tools/live_pnl_tracker.py                 # dry-run (print summary)
    python3 tools/live_pnl_tracker.py --apply         # write DB + JSON
    python3 tools/live_pnl_tracker.py --summary       # print only (no writes)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

try:
    import pymysql
    import yfinance as yf
except ImportError as e:
    print(f"Missing dependency: {e}", file=sys.stderr)
    sys.exit(1)

from tools.db_env import get_stocks_creds  # noqa: E402

OUT_JSON = REPO / "audit_dashboard" / "data" / "picks_now_live_pnl.json"
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")


def _connect():
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    return pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)


def ensure_columns(conn):
    """Add current_price + current_pnl_pct columns if missing (idempotent)."""
    cur = conn.cursor()
    for col, dtype in [("current_price", "DECIMAL(12,4)"),
                        ("current_pnl_pct", "DECIMAL(8,4)")]:
        try:
            cur.execute(
                f"ALTER TABLE picks_now_tracker ADD COLUMN {col} {dtype} NULL")
            print(f"[live_pnl] added column {col}")
        except Exception:
            pass  # already exists
    conn.commit()


def fetch_price(symbol: str, asset_class: str) -> tuple[float | None, str]:
    """Return (price, source) or (None, error_reason)."""
    ac = (asset_class or "").upper()
    sym = symbol.strip()

    # ── Crypto: Binance first, CoinGecko fallback ──
    if ac in ("CRYPTO",):
        try:
            import requests
            resp = requests.get(
                f"https://api3.binance.com/api/v3/ticker/price?symbol={sym}",
                timeout=8)
            if resp.status_code == 200:
                px = float(resp.json()["price"])
                if px > 0:
                    return (px, "binance")
        except Exception:
            pass
            return (None, "no crypto price source")

    # ── Equities / ETFs / Commodities / Forex: yfinance ──
    yf_sym = sym
    if ac == "FOREX":
        yf_sym = f"{sym}=X" if not sym.endswith("=X") else sym
    try:
        tkr = yf.Ticker(yf_sym)
        # fast_info works when .history() returns NaN (common for today's date).
        px = (tkr.fast_info.get("lastPrice")
              or tkr.fast_info.get("regularMarketPrice")
              or tkr.fast_info.get("previousClose"))
        if px and float(px) > 0:
            return (float(px), "yfinance")
        # Fallback: info dict (slower but more complete).
        info = tkr.info or {}
        px = (info.get("currentPrice")
              or info.get("regularMarketPrice")
              or info.get("previousClose")
              or info.get("regularMarketPreviousClose"))
        if px and float(px) > 0:
            return (float(px), "yfinance")
    except Exception:
        pass
    return (None, "yfinance failed")


def compute_pnl(entry: float, current: float, direction: str) -> float:
    """Point-to-point PnL in %."""
    if not entry or not current or entry <= 0:
        return 0.0
    raw = (current - entry) / entry * 100.0
    d = str(direction or "LONG").upper()
    if d in ("SHORT", "SELL", "STRONG_SELL"):
        return -raw
    return raw


def build(apply_db: bool = False) -> dict:
    conn = _connect()
    cur = conn.cursor()

    if apply_db:
        ensure_columns(conn)

    # Get unresolved picks with valid entry_price
    cur.execute(
        "SELECT id, symbol, asset_class, direction, entry_price, generated_at, "
        "suggested_tp, suggested_sl, score "
        "FROM picks_now_tracker "
        "WHERE exit_pnl_pct IS NULL AND entry_price > 0 "
        "ORDER BY generated_at DESC")
    picks = cur.fetchall()

    print(f"[live_pnl] {len(picks)} unresolved picks to mark")
    if not picks:
        conn.close()
        return {"generated_at": datetime.now(timezone.utc).isoformat(),
                "n_open": 0, "n_priced": 0, "picks": [],
                "by_class": [], "summary": {"avg_pnl_pct": None, "n_positive": 0, "n_negative": 0}}

    results = []
    priced = 0
    for i, p in enumerate(picks):
        if i > 0 and i % 20 == 0:
            time.sleep(0.3)  # rate-limit yfinance
        price, source = fetch_price(p["symbol"], p["asset_class"])
        if price is None:
            results.append({
                "symbol": p["symbol"],
                "asset_class": p["asset_class"],
                "direction": p["direction"],
                "entry_price": float(p["entry_price"]) if p["entry_price"] else None,
                "generated_at": str(p["generated_at"]),
                "current_price": None,
                "pnl_pct": None,
                "tp_pct": (float(p["suggested_tp"]) / float(p["entry_price"]) - 1) * 100
                    if p["entry_price"] and p["suggested_tp"] else None,
                "sl_pct": (float(p["suggested_sl"]) / float(p["entry_price"]) - 1) * 100
                    if p["entry_price"] and p["suggested_sl"] else None,
                "score": float(p["score"]) if p["score"] else None,
                "error": source,
            })
            continue

        entry = float(p["entry_price"])
        pnl = round(compute_pnl(entry, price, p["direction"]), 2)
        priced += 1

        results.append({
            "symbol": p["symbol"],
            "asset_class": p["asset_class"],
            "direction": p["direction"],
            "entry_price": entry,
            "generated_at": str(p["generated_at"]),
            "current_price": round(price, 4),
            "pnl_pct": pnl,
            "tp_pct": round((float(p["suggested_tp"]) / entry - 1) * 100, 1)
                if p["suggested_tp"] else None,
            "sl_pct": round((float(p["suggested_sl"]) / entry - 1) * 100, 1)
                if p["suggested_sl"] else None,
            "score": float(p["score"]) if p["score"] else None,
            "price_source": source,
        })

        if apply_db:
            cur.execute(
                "UPDATE picks_now_tracker SET current_price=%s, current_pnl_pct=%s "
                "WHERE id=%s",
                (round(price, 4), pnl, p["id"]))

    if apply_db:
        conn.commit()
        print(f"[live_pnl] wrote {priced} current_price/current_pnl_pct rows to DB")

    conn.close()

    # Summary stats
    pnls = [r["pnl_pct"] for r in results if r["pnl_pct"] is not None]
    n_pos = sum(1 for x in pnls if x > 0)
    n_neg = sum(1 for x in pnls if x < 0)
    avg = round(sum(pnls) / len(pnls), 2) if pnls else None

    # Per-class
    by_class: dict = {}
    for r in results:
        ac = r["asset_class"]
        if ac not in by_class:
            by_class[ac] = {"n": 0, "n_priced": 0, "pnls": []}
        by_class[ac]["n"] += 1
        if r["pnl_pct"] is not None:
            by_class[ac]["n_priced"] += 1
            by_class[ac]["pnls"].append(r["pnl_pct"])
    by_class_out = []
    for ac, d in sorted(by_class.items()):
        avg_ac = round(sum(d["pnls"]) / len(d["pnls"]), 2) if d["pnls"] else None
        by_class_out.append({
            "asset_class": ac, "n": d["n"], "n_priced": d["n_priced"],
            "avg_pnl_pct": avg_ac,
            "n_pos": sum(1 for x in d["pnls"] if x > 0),
            "n_neg": sum(1 for x in d["pnls"] if x < 0),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "picks_now_tracker (ejaguiar1_stocks), prices via yfinance/Binance",
        "n_open": len(picks),
        "n_priced": priced,
        "summary": {
            "avg_pnl_pct": avg,
            "n_positive": n_pos,
            "n_negative": n_neg,
            "n_no_price": len(picks) - priced,
        },
        "by_class": by_class_out,
        "picks": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Mark-to-market PnL for picks_now_tracker")
    ap.add_argument("--apply", action="store_true", help="write to DB + JSON")
    ap.add_argument("--summary", action="store_true", help="print summary only, no writes")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    payload = build(apply_db=args.apply)

    if args.summary:
        s = payload["summary"]
        print(f"\n=== LIVE PNL SUMMARY ===")
        print(f"  Open picks: {payload['n_open']}")
        print(f"  Priced: {payload['n_priced']}")
        print(f"  Avg PnL: {s['avg_pnl_pct']}%")
        print(f"  Positive: {s['n_positive']}  Negative: {s['n_negative']}")
        print(f"\n  By class:")
        for c in payload["by_class"]:
            print(f"    {c['asset_class']:12s} n={c['n']} avg={c['avg_pnl_pct']}% "
                  f"(+{c['n_pos']}/-{c['n_neg']})")
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    s = payload["summary"]
    print(f"[live_pnl] wrote {out_path}: {payload['n_priced']} priced, "
          f"avg={s['avg_pnl_pct']}% (+{s['n_positive']}/-{s['n_negative']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
