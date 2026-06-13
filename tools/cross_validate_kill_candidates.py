#!/usr/bin/env python3
"""
cross_validate_kill_candidates.py — sanity-check strategy-kill decisions across
the two resolution lanes before retiring anything.

Motivation (2026-06-13 review of STRATEGY_KILL_ANALYSIS): the strategy_kill_switch
runs against `at_pick_outcomes`, whose WR column is unreliable (whole strategies
show 1-23% WR because most rows resolve near-flat) and which DISAGREES with the
live `trading_picks` book. Example caught: `forex_rsi2_mean_reversion` was killed
on at_pick_outcomes (sum -130, "total_pnl_destroyed") while in trading_picks,
DEDUPED per symbol-day, it is PF 1.53 / 52% WR — i.e. profitable in the live book.

This tool reports BOTH lanes side-by-side per strategy and raises a DISAGREE flag
when one lane says "profitable" and the other says "loser", so a human/agent does
not retire a strategy that the live pick book shows making money.

Key discipline it enforces that the kill switch skips: per-(strategy,symbol,day)
DEDUP on trading_picks (FOREX raw 15,084 -> 1,853 deduped; 88% are batch dupes),
and a 5bp percent win-threshold so near-flat TIME_EXITs are not counted as wins.

Read-only. DB creds from env / ~/dbpasses.txt — never hardcoded (Gitleaks gate).

Usage:
    python3 tools/cross_validate_kill_candidates.py --strategy forex_rsi2_mean_reversion
    python3 tools/cross_validate_kill_candidates.py --strategy luxalgo_filters --strategy ensemble
    python3 tools/cross_validate_kill_candidates.py --kill-list reports/kill_candidates.txt
    python3 tools/cross_validate_kill_candidates.py --json reports/kill_xval.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

WIN_THRESHOLD_PCT = 0.05  # 5bp; trading_picks pnl_pct is in percent units


def _load_db_password() -> str:
    pw = os.environ.get("DB_PASS_STOCKS") or os.environ.get("STOCKS_DB_PASS")
    if pw:
        return pw
    for path in (Path.home() / "dbpasses.txt", Path("/home/eaguiar2015/dbpasses.txt")):
        if path.exists():
            for line in path.read_text(errors="replace").splitlines():
                s = line.strip()
                if s.startswith("stocks") and s.endswith("1234560"):
                    return s
    raise SystemExit("No DB password: set DB_PASS_STOCKS or provide dbpasses.txt")


def _connect():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=_load_db_password(),
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        connect_timeout=20,
    )


def trading_picks_metrics(cur, strategy: str) -> dict:
    """Deduped-per-symbol-day metrics from the LIVE pick book."""
    cur.execute(
        """
        SELECT id, symbol, pnl_pct, DATE(created_at)
        FROM trading_picks
        WHERE strategy=%s AND closed_at IS NOT NULL AND pnl_pct IS NOT NULL
          AND status IN ('TP_HIT','SL_HIT','LOST','TIME_EXIT','EXPIRED','WON')
          AND created_at >= '2026-01-01'
        """,
        (strategy,),
    )
    rows = cur.fetchall()
    if not rows:
        return {"present": False}
    seen = {}
    for r in rows:
        key = (r[1], r[3])
        if key not in seen or r[0] < seen[key][0]:
            seen[key] = r
    ded = list(seen.values())
    wins = [x for x in ded if float(x[2]) > WIN_THRESHOLD_PCT]
    losses = [x for x in ded if float(x[2]) < -WIN_THRESHOLD_PCT]
    gp = sum(float(x[2]) for x in wins)
    gl = abs(sum(float(x[2]) for x in losses))
    pf = gp / gl if gl > 0 else float("inf")
    decisive = len(wins) + len(losses)
    return {
        "present": True,
        "raw_n": len(rows),
        "deduped_n": len(ded),
        "dup_pct": round((1 - len(ded) / len(rows)) * 100, 1),
        "pf": round(pf, 2),
        "decisive_wr": round(len(wins) / decisive * 100, 1) if decisive else 0.0,
        "sum_pnl": round(sum(float(x[2]) for x in ded), 1),
        "profitable": pf >= 1.0,
    }


def at_pick_outcomes_metrics(cur, strategy: str) -> dict:
    """Metrics from the standalone replay lane (what the kill switch reads)."""
    cur.execute(
        """
        SELECT COUNT(*), SUM(pnl_pct > 0), AVG(pnl_pct), SUM(pnl_pct)
        FROM at_pick_outcomes
        WHERE strategy=%s AND pnl_pct IS NOT NULL
        """,
        (strategy,),
    )
    n, wins, avg, total = cur.fetchone()
    if not n:
        return {"present": False}
    return {
        "present": True,
        "n": int(n),
        "wr": round((wins or 0) / n * 100, 1),
        "avg_pnl": round(float(avg or 0), 3),
        "sum_pnl": round(float(total or 0), 1),
        "profitable": float(total or 0) > 0,
    }


def verdict(tp: dict, apo: dict) -> str:
    if not tp.get("present") and not apo.get("present"):
        return "ABSENT_BOTH"
    if not tp.get("present"):
        return "AT_PICK_OUTCOMES_ONLY (not in live book — kill is harmless but verify intent)"
    if not apo.get("present"):
        return "LIVE_BOOK_ONLY (kill switch has no at_pick_outcomes basis here)"
    if tp["profitable"] and not apo["profitable"]:
        return "DISAGREE — live book PROFITABLE, replay lane says loser → DO NOT KILL on at_pick_outcomes alone"
    if not tp["profitable"] and apo["profitable"]:
        return "DISAGREE — replay lane profitable, live book loser → kill defensible but reasoning incoherent"
    if not tp["profitable"] and not apo["profitable"]:
        return "AGREE — loser in both lanes → kill justified"
    return "AGREE — profitable in both lanes → KEEP"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", action="append", default=[], help="strategy name (repeatable)")
    ap.add_argument("--kill-list", default="", help="file with one strategy name per line")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    strategies = list(args.strategy)
    if args.kill_list:
        strategies += [l.strip() for l in Path(args.kill_list).read_text().splitlines()
                       if l.strip() and not l.startswith("#")]
    if not strategies:
        # default to the 2026-06-12 kill list for a quick audit
        strategies = ["forex_rsi2_mean_reversion", "forex_carry_momentum", "luxalgo_filters",
                      "ensemble", "futures_momentum", "cta_cross_asset_tsmom",
                      "enhanced_ml_A_xgboost", "MomentumEMA"]

    conn = _connect()
    out = []
    try:
        cur = conn.cursor()
        for s in dict.fromkeys(strategies):  # dedup preserve order
            tp = trading_picks_metrics(cur, s)
            apo = at_pick_outcomes_metrics(cur, s)
            out.append({"strategy": s, "trading_picks": tp, "at_pick_outcomes": apo,
                        "verdict": verdict(tp, apo)})
    finally:
        conn.close()

    print("# Kill-candidate cross-validation (live trading_picks deduped vs at_pick_outcomes)\n")
    for r in out:
        tp, apo = r["trading_picks"], r["at_pick_outcomes"]
        tp_s = (f"PF {tp['pf']} / WR {tp['decisive_wr']}% / n {tp['deduped_n']}(raw {tp['raw_n']}, "
                f"{tp['dup_pct']}% dup)") if tp.get("present") else "absent"
        apo_s = (f"WR {apo['wr']}% / sum {apo['sum_pnl']} / n {apo['n']}") if apo.get("present") else "absent"
        flag = "⚠️ " if r["verdict"].startswith("DISAGREE") else ""
        print(f"{flag}{r['strategy']}")
        print(f"    live book:        {tp_s}")
        print(f"    at_pick_outcomes: {apo_s}")
        print(f"    → {r['verdict']}\n")

    disagreements = [r["strategy"] for r in out if r["verdict"].startswith("DISAGREE")]
    if disagreements:
        print(f"DISAGREEMENTS ({len(disagreements)}): {', '.join(disagreements)} — review before retiring.")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
