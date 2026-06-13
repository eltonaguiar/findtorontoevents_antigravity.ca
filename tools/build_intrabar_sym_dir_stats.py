#!/usr/bin/env python3
"""build_intrabar_sym_dir_stats.py — symbol×direction intrabar forward WR/PF map.

WHY (P1-1): Active Picks Track/FWD columns used closed-picks ledger (sym_track_wr)
or strategy-wide leaderboard (strat_fwd_wr). Honest forward truth for sizing
decisions lives in at_signal_outcomes.intrabar_* (first-touch TP/SL replay).

READ-ONLY against DB. Writes audit_dashboard/data/intrabar_sym_dir_fwd.json.
Idempotent; safe to run hourly after intrabar reresolve.

Usage: python3 tools/build_intrabar_sym_dir_stats.py [--out PATH] [--stdout]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

OUT_DEFAULT = os.path.join(REPO_ROOT, "audit_dashboard", "data", "intrabar_sym_dir_fwd.json")
_KEEP = ("host", "user", "password", "database", "port", "connect_timeout")


def _norm_dir(direction: str) -> str:
    d = (direction or "").upper().strip()
    if d in ("BUY", "LONG"):
        return "LONG"
    if d in ("SELL", "SHORT"):
        return "SHORT"
    return d or "UNKNOWN"


def _norm_sym(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    if s.endswith("=X"):
        s = s[:-2]
    return s.replace("-", "").replace("_", "").replace("/", "")


def _row_stats(n: int, wins: int, pf_raw) -> dict:
    wr = round(100.0 * wins / n, 1) if n else 0.0
    pf = float(pf_raw) if pf_raw is not None else 0.0
    return {"n": n, "wins": wins, "wr_pct": wr, "pf": pf}


def build() -> dict:
    creds = {k: v for k, v in get_stocks_creds().items() if k in _KEEP}
    conn = pymysql.connect(**creds, cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT symbol, UPPER(direction) AS direction, strategy,
               COUNT(*) AS n, SUM(intrabar_status = 'TP_HIT') AS wins,
               ROUND(SUM(CASE WHEN intrabar_pnl_pct > 0 THEN intrabar_pnl_pct ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN intrabar_pnl_pct < 0 THEN -intrabar_pnl_pct ELSE 0 END), 0), 3) AS pf
        FROM at_signal_outcomes
        WHERE intrabar_resolved_at IS NOT NULL
          AND intrabar_status IN ('TP_HIT', 'SL_HIT')
        GROUP BY symbol, UPPER(direction), strategy
        HAVING n >= 1
        """
    )
    by_key: dict[str, dict] = {}
    sym_dir_agg: dict[str, dict] = {}

    for r in cur.fetchall():
        sym = _norm_sym(r["symbol"])
        direction = _norm_dir(r["direction"])
        strat = (r["strategy"] or "").strip()
        n = int(r["n"] or 0)
        wins = int(r["wins"] or 0)
        stats = _row_stats(n, wins, r["pf"])
        if sym and direction and strat:
            by_key[f"{sym}|{direction}|{strat}"] = stats

        sd_key = f"{sym}|{direction}"
        agg = sym_dir_agg.setdefault(sd_key, {"n": 0, "wins": 0, "pos_sum": 0.0, "neg_sum": 0.0})
        agg["n"] += n
        agg["wins"] += wins
        # PF recomputed from sums at end

    cur.execute(
        """
        SELECT symbol, UPPER(direction) AS direction,
               COUNT(*) AS n, SUM(intrabar_status = 'TP_HIT') AS wins,
               ROUND(SUM(CASE WHEN intrabar_pnl_pct > 0 THEN intrabar_pnl_pct ELSE 0 END)
                     / NULLIF(SUM(CASE WHEN intrabar_pnl_pct < 0 THEN -intrabar_pnl_pct ELSE 0 END), 0), 3) AS pf
        FROM at_signal_outcomes
        WHERE intrabar_resolved_at IS NOT NULL
          AND intrabar_status IN ('TP_HIT', 'SL_HIT')
        GROUP BY symbol, UPPER(direction)
        HAVING n >= 1
        """
    )
    for r in cur.fetchall():
        sym = _norm_sym(r["symbol"])
        direction = _norm_dir(r["direction"])
        n = int(r["n"] or 0)
        wins = int(r["wins"] or 0)
        if sym and direction:
            by_key[f"{sym}|{direction}|*"] = _row_stats(n, wins, r["pf"])

    conn.close()
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "at_signal_outcomes.intrabar_* (TP_HIT/SL_HIT, first-touch replay)",
        "note": "P1-1 honest symbol×direction forward stats. Prefer sym|dir|strategy; fallback sym|dir|*.",
        "by_key": by_key,
        "key_count": len(by_key),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    payload = build()
    if args.stdout:
        print(json.dumps(payload, indent=2))
    else:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"wrote {args.out}: {payload['key_count']} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
