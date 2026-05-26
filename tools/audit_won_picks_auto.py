#!/usr/bin/env python3
"""
audit_won_picks_auto.py — Non-interactive WON→LOST correction.

Run via CI with:
    python tools/audit_won_picks_auto.py --apply

Or dry-run only (report):
    python tools/audit_won_picks_auto.py
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def get_db_connection():
    import pymysql
    host = os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com")
    user = os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks")
    password = os.environ.get("DB_STOCKS_PASSWORD", os.environ.get("DB_PASS_STOCKS", ""))
    database = os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks")
    port = int(os.environ.get("DB_STOCKS_PORT", "3306"))
    if not password:
        password = os.environ.get("DB_PASS_STOCKS", "")
    return pymysql.connect(host=host, port=int(port), user=user, password=password, database=database, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)


def run(conn, apply=False, report_path=None):
    cur = conn.cursor()

    # Count bad rows
    cur.execute("SELECT COUNT(*) as cnt FROM trading_picks WHERE status='WON' AND pnl_pct < 0")
    count = cur.fetchone()["cnt"]
    print(f"WON picks with negative PnL: {count}")

    if count == 0:
        print("Database is clean — no corrections needed.")
        return 0

    # Sample for reporting
    cur.execute("SELECT id, symbol, direction, pnl_pct, exit_reason, strategy, source_system FROM trading_picks WHERE status='WON' AND pnl_pct < 0 ORDER BY pnl_pct ASC LIMIT 20")
    rows = cur.fetchall()

    avg_pnl = sum(float(r["pnl_pct"]) for r in rows) / len(rows) if rows else 0
    print(f"Sample ({len(rows)} rows): avg_pnl={avg_pnl:.2f}%, min_pnl={rows[-1]['pnl_pct']}%, max_pnl={rows[0]['pnl_pct']}%")
    print()
    for r in rows[:10]:
        print(f"  id={r['id']:>6} sym={str(r['symbol']):<15} dir={str(r['direction']):<5} pnl={float(r['pnl_pct']):7.2f}% reason={str(r['exit_reason']):<20} strat={str(r['strategy']):<15} src={str(r['source_system'])[:12]}")
    print()

    # Report to JSON
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bad_rows": count,
        "sample": [{"id": r["id"], "symbol": r["symbol"], "direction": r["direction"], "pnl_pct": float(r["pnl_pct"]), "exit_reason": r["exit_reason"], "strategy": r["strategy"], "source_system": r["source_system"]} for r in rows],
        "avg_pnl": round(avg_pnl, 2),
    }
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"Report written to {report_path}")

    if not apply:
        print(f"\nDRY-RUN: {count} records would be corrected (WON -> LOST).")
        print("To apply: run with --apply flag.")
        return count

    # Apply corrections
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    updated = 0
    ids = [r["id"] for r in rows]
    placeholders = ",".join(["%s"] * len(ids))
    cur.execute(f"UPDATE trading_picks SET status='LOST', exit_reason=CONCAT('AUTO_CORRECTED_FROM_WON:', COALESCE(exit_reason,'UNKNOWN')), closed_at='{now}' WHERE id IN ({placeholders})", ids)
    updated = cur.rowcount
    conn.commit()
    print(f"Applied: corrected {updated}/{count} picks (WON -> LOST).")
    return updated


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Apply corrections (WON -> LOST)")
    p.add_argument("--report", default=str(ROOT / f"reports/won_pnl_contradiction_dryrun_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}Z.json"), help="JSON report path")
    args = p.parse_args()

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = run(conn, apply=args.apply, report_path=args.report)
        sys.exit(0 if result <= 1 else 1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
