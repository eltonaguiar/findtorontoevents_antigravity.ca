#!/usr/bin/env python3
"""Export strategy_perf_by_class -> audit_dashboard/data JSON for the dashboard.

Reads the per-asset-class strategy tracker (built by rebuild_strategy_stats_all_classes.py,
ENHANCEMENT #121) and writes a compact static JSON the /audit surface (the standalone
strategy_perf_by_class.html viewer) reads. Read-only on the DB; writes one JSON file.

Usage: DB_PASS_STOCKS=... python tools/export_strategy_perf_by_class.py
"""
from __future__ import annotations

import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "audit_dashboard", "data", "strategy_perf_by_class.json")


def export() -> dict:
    import pymysql
    c = pymysql.connect(host="mysql.50webs.com", user="ejaguiar1_stocks",
                        password=os.environ["DB_PASS_STOCKS"],
                        database="ejaguiar1_stocks", connect_timeout=20,
                        cursorclass=pymysql.cursors.DictCursor)
    cur = c.cursor()
    cur.execute("""SELECT asset_class, strategy, n, wins, losses, win_rate_pct,
                          profit_factor, avg_pnl_pct, total_pnl_pct, rebuilt_utc
                   FROM strategy_perf_by_class ORDER BY asset_class, n DESC""")
    rows = cur.fetchall()
    c.close()
    by_class: dict = {}
    for r in rows:
        r["rebuilt_utc"] = str(r.get("rebuilt_utc") or "")
        by_class.setdefault(r["asset_class"], []).append(r)
    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "ejaguiar1_stocks.strategy_perf_by_class (ENHANCEMENT #121)",
        "note": ("Raw per-(asset_class, strategy) tracking from resolved WON/LOST picks "
                 "(at_pick_outcomes). NOT edge-proven — apply the #111 attribution gate "
                 "(alpha vs beta) + n>=30 + DSR before any money-ready claim."),
        "n_classes": len(by_class),
        "n_cells": len(rows),
        "by_class": by_class,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)
    return {"written": OUT, "n_classes": len(by_class), "n_cells": len(rows)}


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(export(), indent=2, default=str))
