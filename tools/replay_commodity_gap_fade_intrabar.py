#!/usr/bin/env python3
"""replay_commodity_gap_fade_intrabar.py — P1-4 intrabar replay for gold_overnight_gap_fade.

READ-ONLY DB query against at_signal_outcomes.intrabar_* (deduped sym+dir+day).
Compares to backtest proxy claim (PF 1.92, n=108 BT) from action plan.

Usage:
  python3 tools/replay_commodity_gap_fade_intrabar.py
  python3 tools/replay_commodity_gap_fade_intrabar.py --json reports/commodity_gap_fade_intrabar_latest.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")
STRATEGY = "gold_overnight_gap_fade"
BT_PROXY = {"n": 108, "pf": 1.92, "source": "strategy backtest proxy (action plan P1-4)"}


def _stats(rows: list[dict]) -> dict:
    n = len(rows)
    wins = sum(1 for r in rows if r.get("intrabar_status") == "TP_HIT")
    gw = sum(float(r.get("intrabar_pnl_pct") or 0) for r in rows if float(r.get("intrabar_pnl_pct") or 0) > 0)
    gl = sum(-float(r.get("intrabar_pnl_pct") or 0) for r in rows if float(r.get("intrabar_pnl_pct") or 0) < 0)
    wr = round(100.0 * wins / n, 1) if n else 0.0
    pf = round(gw / gl, 3) if gl > 0 else None
    return {"n": n, "wins": wins, "wr_pct": wr, "pf": pf, "avg_pnl_pct": round(sum(float(r.get("intrabar_pnl_pct") or 0) for r in rows) / n, 4) if n else 0.0}


def build() -> dict:
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.symbol, UPPER(o.direction) AS direction, o.strategy, o.asset_class,
               o.intrabar_status, o.intrabar_pnl_pct, o.opened_at
        FROM at_signal_outcomes o
        JOIN (
            SELECT MIN(id) AS id
            FROM at_signal_outcomes
            WHERE intrabar_resolved_at IS NOT NULL
              AND intrabar_status IN ('TP_HIT', 'SL_HIT')
              AND opened_at IS NOT NULL
            GROUP BY symbol, UPPER(direction), DATE(opened_at)
        ) d ON d.id = o.id
        WHERE o.strategy LIKE %s
        ORDER BY o.opened_at DESC
        """,
        (f"%{STRATEGY}%",),
    )
    rows = list(cur.fetchall())
    conn.close()

    all_stats = _stats(rows)
    comm = [r for r in rows if (r.get("asset_class") or "").upper() == "COMMODITY"]
    comm_stats = _stats(comm)

    verdict = "INSUFFICIENT_N"
    if comm_stats["n"] >= 100 and comm_stats["wr_pct"] >= 50 and (comm_stats["pf"] or 0) >= 1.5:
        verdict = "T2_CANDIDATE"
    elif comm_stats["n"] >= 30 and comm_stats["wr_pct"] >= 48 and (comm_stats["pf"] or 0) >= 1.2:
        verdict = "T3_CANDIDATE"
    elif comm_stats["n"] >= 10:
        verdict = "PROXY_UNCONFIRMED" if (comm_stats["pf"] or 0) < (BT_PROXY["pf"] or 0) * 0.75 else "PROXY_ALIGNED"

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": STRATEGY,
        "source": "at_signal_outcomes.intrabar_* deduped (symbol,direction,day)",
        "bt_proxy_claim": BT_PROXY,
        "all_asset_classes": all_stats,
        "commodity_only": comm_stats,
        "verdict": verdict,
        "note": "P1-4 measurement — compare intrabar COMMODITY stats to BT proxy before sizing.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    payload = build()
    if args.stdout or not args.json:
        print(json.dumps(payload, indent=2))
    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
