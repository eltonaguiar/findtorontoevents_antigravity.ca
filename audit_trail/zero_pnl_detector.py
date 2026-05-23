#!/usr/bin/env python3
"""Zero-PnL resolver-bug detector (per Grok PR #917 spec 2026-05-12).

Companion to tools/data_audit/etl_checksum.py — that script does broad
classification across 4 causes; THIS script targets the narrowest most-
actionable cause: trades where exit_price clearly differs from
entry_price BUT pnl_pct is recorded as zero. That's a writer-side
resolver bug (lost the (exit-entry)/entry computation).

Uses pymysql (repo convention) + DB_STOCKS_* env vars per
audit_trail/mysql_client.py. NO hardcoded credentials.

Reads from `trading_picks` (the live ledger). The Grok spec's `trades`
table doesn't exist in this repo; substituting the actual table here.

Outputs:
  audit_trail/data/zero_pnl_report.json

Usage:
  DB_STOCKS_PASSWORD=... python audit_trail/zero_pnl_detector.py
  python audit_trail/zero_pnl_detector.py --limit 500
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "audit_trail" / "data" / "zero_pnl_report.json"

TERMINAL_STATUSES = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT",
                     "EXPIRED", "closed_win", "closed_loss")


def connect():
    pw = os.environ.get("DB_STOCKS_PASSWORD") or os.environ.get("DB_PASSWORD")
    if not pw:
        raise RuntimeError(
            "DB_STOCKS_PASSWORD (or DB_PASSWORD) environment variable required"
        )
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=pw,
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=500,
                   help="Max suspect rows to return (default 500)")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    out_path = Path(args.out) if args.out else REPORT_PATH

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    placeholders = ",".join(["%s"] * len(TERMINAL_STATUSES))
    sql = f"""
        SELECT id, strategy, symbol, asset_class, direction,
               entry_price, exit_price, pnl_pct, status, exit_reason,
               created_at, closed_at
        FROM trading_picks
        WHERE ABS(COALESCE(pnl_pct, 0)) < 0.0001
          AND exit_price IS NOT NULL
          AND entry_price IS NOT NULL
          AND ABS(entry_price - exit_price) > 0.01
          AND status IN ({placeholders})
        ORDER BY created_at DESC
        LIMIT %s
    """
    cur.execute(sql, TERMINAL_STATUSES + (args.limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Compute the "what pnl_pct SHOULD have been" per row (helps the
    # backfill Option A SQL pass at reports/zero_pnl_backfill_sql_2026-05-12.md)
    enriched = []
    for r in rows:
        try:
            entry = float(r["entry_price"])
            exit_p = float(r["exit_price"])
            direction = str(r.get("direction", "")).upper()
            if entry > 0:
                if direction in ("LONG", "BUY"):
                    correct = (exit_p - entry) / entry * 100
                elif direction in ("SHORT", "SELL"):
                    correct = (entry - exit_p) / entry * 100
                else:
                    correct = None
            else:
                correct = None
        except (TypeError, ValueError):
            correct = None
        enriched.append({
            "id": str(r.get("id", "")),
            "strategy": r.get("strategy"),
            "symbol": r.get("symbol"),
            "asset_class": r.get("asset_class"),
            "direction": r.get("direction"),
            "entry_price": float(r["entry_price"]) if r.get("entry_price") is not None else None,
            "exit_price": float(r["exit_price"]) if r.get("exit_price") is not None else None,
            "stored_pnl_pct": float(r.get("pnl_pct") or 0),
            "correct_pnl_pct": round(correct, 4) if correct is not None else None,
            "status": r.get("status"),
            "exit_reason": r.get("exit_reason"),
            "created_at": str(r.get("created_at") or ""),
            "closed_at": str(r.get("closed_at") or ""),
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": (
            "Filter: terminal status + non-null entry + non-null exit + "
            "|entry-exit|>0.01 + |pnl_pct|<0.0001. Every match is a "
            "writer-side resolver bug — the (exit-entry)/entry math was "
            "never recorded."
        ),
        "limit_requested": args.limit,
        "zero_pnl_bug_count": len(enriched),
        "trades": enriched,
        "remediation": (
            "See reports/zero_pnl_backfill_sql_2026-05-12.md Option A — "
            "UPDATE trading_picks SET pnl_pct = (exit-entry)/entry... "
            "Each row in this report is a candidate for that backfill."
        ),
        "nfa": "Read-only diagnostic. Does not modify the DB.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str),
                        encoding="utf-8")
    print(f"# Found {len(enriched)} zero-PnL resolver-bug candidates",
          file=sys.stderr)
    print(f"# wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
