#!/usr/bin/env python3
"""pick_flow_funnel.py — per-asset-class pick funnel for a date range.

Prints, per asset class: raw picks emitted, gate rejections (top reason),
consensus survivors, closed picks, win-rate and profit factor. This is the
data behind a /audit pick-flow case study.

Reads the at_pick_flow_daily rollup table when present (fast); otherwise
computes the funnel live from at_raw_picks + at_filter_log + at_consensus_picks.

Usage:
    python pick_flow_funnel.py                 # last 7 days, from rollup
    python pick_flow_funnel.py --days 14
    python pick_flow_funnel.py --live          # bypass rollup, compute live
    python pick_flow_funnel.py --since 2026-05-11 --until 2026-05-18

Credentials: env AUDIT_DB_HOST/AUDIT_DB_USER/AUDIT_DB_PASS, or --pw.
"""
import argparse
import datetime as dt
import os
import sys

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    sys.exit("pip install pymysql")


def connect(args):
    return pymysql.connect(
        host=os.getenv("AUDIT_DB_HOST", "mysql.50webs.com"),
        user=os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"),
        password=args.pw or os.getenv("AUDIT_DB_PASS", ""),
        database=os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks"),
        connect_timeout=20, cursorclass=DictCursor)


HEAD = (f"{'CLASS':10} {'EMIT':>7} {'REJECT':>7} {'CONSENS':>8} "
        f"{'CLOSED':>7} {'WR%':>6} {'PF':>6}  TOP-REJECT")


def from_rollup(cur, since, until):
    cur.execute(
        "SELECT asset_class, SUM(raw_emitted) emit, SUM(rejected_total) rej, "
        "SUM(consensus_count) cons, SUM(closed_count) closed, SUM(wins) wins, "
        "SUM(gross_win_pct) gw, SUM(gross_loss_pct) gl, "
        "SUBSTRING_INDEX(GROUP_CONCAT(reject_top_reason ORDER BY rejected_total DESC),"
        "',',1) top_reason "
        "FROM at_pick_flow_daily WHERE flow_date BETWEEN %s AND %s "
        "GROUP BY asset_class ORDER BY emit DESC", (since, until))
    return cur.fetchall()


def live(cur, since, until):
    """Compute the funnel directly (rollup-independent)."""
    rows = {}
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n "
        "FROM at_raw_picks WHERE DATE(recorded_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until))
    for r in cur.fetchall():
        rows.setdefault(r["ac"], {})["emit"] = r["n"]
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n, "
        "SUBSTRING_INDEX(GROUP_CONCAT(filter_reason ORDER BY 1),',',1) tr "
        "FROM at_filter_log WHERE DATE(created_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until))
    for r in cur.fetchall():
        d = rows.setdefault(r["ac"], {})
        d["rej"], d["top_reason"] = r["n"], r["tr"]
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n "
        "FROM at_consensus_picks WHERE DATE(generated_at) BETWEEN %s AND %s GROUP BY ac",
        (since, until))
    for r in cur.fetchall():
        rows.setdefault(r["ac"], {})["cons"] = r["n"]
    cur.execute(
        "SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac, COUNT(*) n, "
        "SUM(pnl_pct>0) wins, "
        "SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END) gw, "
        "ABS(SUM(CASE WHEN pnl_pct<=0 THEN pnl_pct ELSE 0 END)) gl "
        "FROM at_raw_picks WHERE DATE(closed_at) BETWEEN %s AND %s "
        "AND pnl_pct IS NOT NULL GROUP BY ac", (since, until))
    for r in cur.fetchall():
        d = rows.setdefault(r["ac"], {})
        d.update(closed=r["n"], wins=r["wins"], gw=r["gw"], gl=r["gl"])
    return [dict(asset_class=k, **v) for k, v in rows.items()]


def show(rows):
    print(HEAD)
    print("-" * len(HEAD))
    for r in sorted(rows, key=lambda x: -(x.get("emit") or 0)):
        closed = r.get("closed") or 0
        wins = r.get("wins") or 0
        gw, gl = float(r.get("gw") or 0), float(r.get("gl") or 0)
        wr = f"{100*wins/closed:.1f}" if closed else "-"
        pf = f"{gw/gl:.2f}" if gl > 0 else ("inf" if gw > 0 else "-")
        print(f"{r['asset_class']:10} {r.get('emit') or 0:7} "
              f"{r.get('rej') or 0:7} {r.get('cons') or 0:8} "
              f"{closed:7} {wr:>6} {pf:>6}  {r.get('top_reason') or '-'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--live", action="store_true", help="compute live, skip rollup")
    ap.add_argument("--pw")
    args = ap.parse_args()

    until = dt.date.fromisoformat(args.until) if args.until else dt.date.today()
    since = (dt.date.fromisoformat(args.since) if args.since
             else until - dt.timedelta(days=args.days))

    conn = connect(args)
    cur = conn.cursor()
    print(f"\nPick-flow funnel  {since} .. {until}  "
          f"({'live' if args.live else 'rollup'})\n")
    rows = live(cur, since, until) if args.live else from_rollup(cur, since, until)
    if not rows and not args.live:
        print("(at_pick_flow_daily empty for range — retry with --live)")
        rows = live(cur, since, until)
    show(rows)
    conn.close()
    print("\nNote: WR/PF use closed_at-dated rows. Picks whose status is terminal "
          "but closed_at is NULL are not counted — see the skill's data-quality "
          "section. Use trace_pick.py to inspect any single pick.")


if __name__ == "__main__":
    main()
