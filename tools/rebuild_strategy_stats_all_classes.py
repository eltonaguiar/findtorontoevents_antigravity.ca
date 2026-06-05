#!/usr/bin/env python3
"""Per-asset-class strategy tracker rebuild (ENHANCEMENT_OVERALL #121, 2026-06-04).

The canonical at_strategy_stats covers only CRYPTO/MEMECOIN (+thin EQUITY); FUTURES,
ETF, BOND, COMMODITY, PENNY emit picks with ZERO strategy-level perf rows (review
2026-06-04). This rebuilds a per-(asset_class, strategy) perf table for ALL classes
from the resolved-outcome ledger at_pick_outcomes (39k rows, every class present).

- Resolved = status in (WON, LOST). EXPIRED is excluded (unresolved/time-out, not a
  trade outcome) — matches money_ready_verdict._resolved.
- Normalizes fragmented class labels (STOCKS/STOCK->EQUITY, MEME->MEMECOIN,
  PENNY/PENNYSTOCK->PENNY_STOCK, ''->UNKNOWN).
- WR = wins/(wins+losses); PF = gross_profit/gross_loss; avg/total pnl_pct.
- Writes to NEW table strategy_perf_by_class (additive; full rebuild each run — it's
  derived data, safe to replace). Does NOT touch at_strategy_stats or any source table.
- --dry-run: aggregate + print, no DB write.

Usage: DB_PASS_STOCKS=... python tools/rebuild_strategy_stats_all_classes.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

_CLASS_MAP = {
    "STOCKS": "EQUITY", "STOCK": "EQUITY",
    "MEME": "MEMECOIN",
    "PENNY": "PENNY_STOCK", "PENNYSTOCK": "PENNY_STOCK",
    "": "UNKNOWN",
}


def normalize_class(ac: str) -> str:
    ac = str(ac or "").upper().strip()
    return _CLASS_MAP.get(ac, ac or "UNKNOWN")


def aggregate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """rows: dicts with asset_class, strategy, status, pnl_pct. Resolved=WON/LOST."""
    buckets: Dict[tuple, Dict[str, float]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "gp": 0.0, "gl": 0.0, "sum": 0.0, "n": 0})
    for r in rows:
        status = str(r.get("status") or "").upper()
        if status not in ("WON", "LOST"):
            continue
        ac = normalize_class(r.get("asset_class"))
        strat = str(r.get("strategy") or "").strip() or "(unattributed)"
        try:
            pnl = float(r.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        b = buckets[(ac, strat)]
        b["n"] += 1
        b["sum"] += pnl
        if pnl > 0:
            b["wins"] += 1; b["gp"] += pnl
        elif pnl < 0:
            b["losses"] += 1; b["gl"] += -pnl
        else:
            # zero-pnl WON/LOST: count by status label (resolver edge case)
            if status == "WON":
                b["wins"] += 1
            else:
                b["losses"] += 1
    out = []
    for (ac, strat), b in buckets.items():
        n = b["n"]
        wl = b["wins"] + b["losses"]
        wr = round(100 * b["wins"] / wl, 2) if wl else None
        pf = round(b["gp"] / b["gl"], 4) if b["gl"] > 0 else (None if b["gp"] == 0 else 999.0)
        out.append({
            "asset_class": ac, "strategy": strat[:120], "n": n,
            "wins": b["wins"], "losses": b["losses"],
            "win_rate_pct": wr, "profit_factor": pf,
            "avg_pnl_pct": round(b["sum"] / n, 6) if n else 0.0,
            "total_pnl_pct": round(b["sum"], 4),
        })
    out.sort(key=lambda r: (r["asset_class"], -(r["n"])))
    return out


def _connect():
    import pymysql
    return pymysql.connect(host="mysql.50webs.com", user="ejaguiar1_stocks",
                           password=os.environ["DB_PASS_STOCKS"],
                           database="ejaguiar1_stocks", connect_timeout=20)


def run(dry_run: bool = False) -> Dict[str, Any]:
    import datetime
    c = _connect()
    cur = c.cursor()
    cur.execute("SELECT asset_class, strategy, status, pnl_pct FROM at_pick_outcomes "
                "WHERE status IN ('WON','LOST')")
    rows = [{"asset_class": r[0], "strategy": r[1], "status": r[2], "pnl_pct": r[3]}
            for r in cur.fetchall()]
    agg = aggregate(rows)
    by_class = defaultdict(int)
    for a in agg:
        by_class[a["asset_class"]] += 1
    summary = {"resolved_rows": len(rows), "strategy_class_cells": len(agg),
               "classes_covered": dict(sorted(by_class.items()))}
    if dry_run:
        c.close()
        summary["dry_run"] = True
        return summary
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""CREATE TABLE IF NOT EXISTS strategy_perf_by_class (
        asset_class VARCHAR(20) NOT NULL, strategy VARCHAR(120) NOT NULL,
        n INT, wins INT, losses INT, win_rate_pct DOUBLE, profit_factor DOUBLE,
        avg_pnl_pct DOUBLE, total_pnl_pct DOUBLE, rebuilt_utc DATETIME,
        PRIMARY KEY (asset_class, strategy)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    cur.execute("DELETE FROM strategy_perf_by_class")   # full rebuild (derived data)
    for a in agg:
        cur.execute("""INSERT INTO strategy_perf_by_class
            (asset_class,strategy,n,wins,losses,win_rate_pct,profit_factor,avg_pnl_pct,total_pnl_pct,rebuilt_utc)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (a["asset_class"], a["strategy"], a["n"], a["wins"], a["losses"],
             a["win_rate_pct"], a["profit_factor"], a["avg_pnl_pct"], a["total_pnl_pct"], now))
    c.commit()
    c.close()
    summary["written"] = len(agg)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    import json
    print(json.dumps(run(dry_run=args.dry_run), indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    main()
