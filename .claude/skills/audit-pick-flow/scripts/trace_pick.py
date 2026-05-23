#!/usr/bin/env python3
"""trace_pick.py — reconstruct the full pipeline flow of one /audit pick.

Given a symbol, raw-pick id, or dedup_hash, this prints the pick's journey:
emitter -> at_raw_picks -> at_filter_log gate decisions -> at_consensus_picks
-> outcome (at_signal_outcomes / status+pnl_pct) -> at_pick_audit_trail (if the
opt-in gate-trace writer is wired). Read-only.

Usage:
    python trace_pick.py --symbol BTCUSDT
    python trace_pick.py --pick-id 145879
    python trace_pick.py --dedup-hash <sha256>
    python trace_pick.py --symbol SPY --asset-class EQUITY --limit 5

Credentials: env AUDIT_DB_HOST/AUDIT_DB_USER/AUDIT_DB_PASS, or pass --pw.
Default host mysql.50webs.com, db ejaguiar1_stocks.
"""
import argparse
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


def hr(title):
    print("\n" + "=" * 72 + f"\n  {title}\n" + "=" * 72)


def trace_one(cur, rp):
    """Print the flow for one at_raw_picks row dict `rp`."""
    pid, dh = rp["id"], rp.get("dedup_hash")
    hr(f"PICK #{pid}  {rp['symbol']} {rp.get('direction','')}  "
       f"[{rp.get('asset_class') or '(null)'}]")
    print(f"  source_system : {rp.get('source_system')}")
    print(f"  strategy      : {rp.get('strategy')}")
    print(f"  confidence    : {rp.get('confidence')}   R:R {rp.get('risk_reward')}")
    print(f"  entry/tp/sl   : {rp.get('entry_price')} / "
          f"{rp.get('take_profit')} / {rp.get('stop_loss')}")
    print(f"  recorded_at   : {rp.get('recorded_at')}")
    print(f"  flags         : stale={rp.get('was_stale')} banned={rp.get('was_banned')} "
          f"demoted={rp.get('was_demoted')} wr_suppressed={rp.get('was_wr_suppressed')}")
    print(f"  STATUS        : {rp.get('status')}   pnl_pct={rp.get('pnl_pct')}   "
          f"exit_reason={rp.get('exit_reason')}   closed_at={rp.get('closed_at')}")

    # gate rejections
    cur.execute("SELECT filter_reason, details, created_at FROM at_filter_log "
                "WHERE raw_pick_id=%s ORDER BY created_at", (pid,))
    fl = cur.fetchall()
    print(f"\n  -- at_filter_log: {len(fl)} gate rejection(s) --")
    for r in fl:
        print(f"     [{r['created_at']}] {r['filter_reason']}: "
              f"{(r['details'] or '')[:90]}")

    # fine-grained gate trace (new opt-in table)
    cur.execute("SELECT pipeline_stage, gate_name, gate_order, decision, reason "
                "FROM at_pick_audit_trail WHERE raw_pick_id=%s OR dedup_hash=%s "
                "ORDER BY gate_order, evaluated_at", (pid, dh))
    at = cur.fetchall()
    if at:
        print(f"\n  -- at_pick_audit_trail: {len(at)} gate evaluation(s) --")
        for r in at:
            mark = {"PASS": "+", "REJECT": "X", "SKIP": ".", "WARN": "!"}.get(
                r["decision"], "?")
            print(f"     {mark} [{r['pipeline_stage']}] {r['gate_name']}"
                  f" -> {r['decision']}  {r.get('reason') or ''}")
    else:
        print("\n  -- at_pick_audit_trail: empty (opt-in gate-trace writer not wired) --")

    # consensus survival
    if dh:
        cur.execute("SELECT id, consensus_tier, classification, agreement_count, "
                    "status, pnl_pct FROM at_consensus_picks "
                    "WHERE symbol=%s AND direction=%s "
                    "ORDER BY ABS(TIMESTAMPDIFF(MINUTE, generated_at, %s)) LIMIT 1",
                    (rp["symbol"], rp.get("direction"), rp.get("recorded_at")))
        cp = cur.fetchone()
        if cp:
            print(f"\n  -- at_consensus_picks: SURVIVED to consensus --")
            print(f"     tier={cp['consensus_tier']} class={cp['classification']} "
                  f"agreement={cp['agreement_count']} status={cp['status']}")
        else:
            print("\n  -- at_consensus_picks: did NOT reach consensus "
                  "(filtered or no agreement) --")

    # resolved outcome
    cur.execute("SELECT outcome, entry_price, exit_price, pnl_pct, closed_at "
                "FROM at_signal_outcomes WHERE symbol=%s ORDER BY closed_at DESC LIMIT 1",
                (rp["symbol"],))
    so = cur.fetchone()
    if so:
        print(f"\n  -- at_signal_outcomes: {so['outcome']} pnl={so['pnl_pct']}% "
              f"@ {so['closed_at']} --")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol")
    ap.add_argument("--pick-id", type=int)
    ap.add_argument("--dedup-hash")
    ap.add_argument("--asset-class")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--pw", help="DB password (else env AUDIT_DB_PASS)")
    args = ap.parse_args()
    if not (args.symbol or args.pick_id or args.dedup_hash):
        ap.error("give one of --symbol / --pick-id / --dedup-hash")

    conn = connect(args)
    cur = conn.cursor()
    if args.pick_id:
        cur.execute("SELECT * FROM at_raw_picks WHERE id=%s", (args.pick_id,))
    elif args.dedup_hash:
        cur.execute("SELECT * FROM at_raw_picks WHERE dedup_hash=%s", (args.dedup_hash,))
    else:
        q = "SELECT * FROM at_raw_picks WHERE symbol=%s"
        p = [args.symbol]
        if args.asset_class:
            q += " AND asset_class=%s"
            p.append(args.asset_class)
        q += " ORDER BY recorded_at DESC LIMIT %s"
        p.append(args.limit)
        cur.execute(q, p)
    rows = cur.fetchall()
    if not rows:
        sys.exit("no matching picks in at_raw_picks")
    for rp in rows:
        trace_one(cur, rp)
    conn.close()


if __name__ == "__main__":
    main()
