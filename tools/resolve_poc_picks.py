#!/usr/bin/env python3
"""resolve_poc_picks.py — the 2-week (and beyond) checkpoint for POC picks.

Reads OPEN rows in ejaguiar1_stocks.poc_picks whose measurement_date has arrived,
fetches the current price (yfinance), computes each pick's return, updates the row
(exit_price, pnl_pct, status=RESOLVED), and prints the basket-vs-benchmark verdict:
did the strategy's picks beat the benchmark?

    python3 tools/resolve_poc_picks.py                         # resolve all due picks
    python3 tools/resolve_poc_picks.py --poc-id tactical_asset_rotation_v1
    python3 tools/resolve_poc_picks.py --force                 # resolve even if before measurement_date (interim read)
    python3 tools/resolve_poc_picks.py --stdout-only           # compute + print, do NOT write to DB
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, "/home/eaguiar2015/findtorontoevents_antigravity.ca")
from tools.db_env import get_stocks_creds  # noqa: E402
import pymysql  # noqa: E402


def _db():
    keep = ("host", "user", "password", "database", "port", "connect_timeout")
    return pymysql.connect(**{k: v for k, v in get_stocks_creds().items() if k in keep})


def _price(sym):
    import yfinance as yf
    df = yf.download(sym, period="6d", progress=False, auto_adjust=True)
    if df is None or len(df) == 0:
        return None
    cl = df["Close"].iloc[-1]
    return float(cl.iloc[0]) if hasattr(cl, "iloc") else float(cl)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poc-id", default=None)
    ap.add_argument("--force", action="store_true", help="resolve even before measurement_date (interim read)")
    ap.add_argument("--stdout-only", action="store_true", help="do not write to DB")
    args = ap.parse_args()

    conn = _db()
    cur = conn.cursor()
    where = "status='OPEN'"
    params = []
    if not args.force:
        where += " AND measurement_date <= %s"
        params.append(str(date.today()))
    if args.poc_id:
        where += " AND poc_id=%s"
        params.append(args.poc_id)
    cur.execute(f"SELECT id,poc_id,pick_symbol,is_benchmark,weight,entry_price FROM poc_picks WHERE {where}", params)
    rows = cur.fetchall()
    if not rows:
        print("no POC picks due for resolution")
        conn.close()
        return 0

    by_poc = defaultdict(list)
    for r in rows:
        pid, poc, sym, isb, w, entry = r[0], r[1], r[2], r[3], float(r[4]), float(r[5])
        px = _price(sym)
        if px is None:
            print(f"  {sym}: no price, skip")
            continue
        pnl = round((px / entry - 1.0) * 100, 4)  # LONG return %
        by_poc[poc].append({"id": pid, "sym": sym, "is_bench": isb, "w": w, "entry": entry, "exit": round(px, 4), "pnl": pnl})
        if not args.stdout_only:
            cur.execute(
                "UPDATE poc_picks SET exit_price=%s, pnl_pct=%s, status='RESOLVED', resolved_at=NOW() WHERE id=%s",
                (round(px, 4), pnl, pid),
            )
    if not args.stdout_only:
        conn.commit()
    conn.close()

    for poc, picks in by_poc.items():
        legs = [p for p in picks if not p["is_bench"]]
        bench = [p for p in picks if p["is_bench"]]
        tw = sum(p["w"] for p in legs) or 1.0
        basket = sum(p["w"] * p["pnl"] for p in legs) / tw
        print(f"\n=== POC RESOLVED: {poc} ===")
        for p in sorted(picks, key=lambda x: (x["is_bench"], x["sym"])):
            tag = "BENCH" if p["is_bench"] else f"{int(p['w']*100)}%"
            print(f"  {p['sym']:5} {tag:5} {p['entry']:>9.2f} -> {p['exit']:>9.2f}  {p['pnl']:+6.2f}%")
        if bench:
            b = bench[0]["pnl"]
            print(f"  BASKET return {basket:+.2f}%  vs  {bench[0]['sym']} {b:+.2f}%  ->  {'BEAT' if basket > b else 'LAGGED'} benchmark by {basket - b:+.2f}pp")
        print("  NOTE: 2wk is too short for a monthly TAA verdict — liveness/plumbing read only; real gate is 6-12mo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
