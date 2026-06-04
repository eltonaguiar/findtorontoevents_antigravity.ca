#!/usr/bin/env python3
"""Backfill missing source_system on trading_picks rows from strategy field.

Closes the provenance gap flagged in EAGLE-3 / zoo's EAGLE2 Phase 2 plan
(Data & Resolver Hygiene). Local sample shows 111 of 500 closed_picks
rows (22%) have no source_system tag; 93 of those (84%) DO have a
strategy value populated. The alpha_engine convention is that
source_system defaults to the strategy name when no separate emitter
identifier is set.

This script:
  1. Connects to ejaguiar1_stocks
  2. Finds trading_picks rows where source_system IS NULL OR source_system = ''
  3. For each row:
     - if strategy is non-empty -> sets source_system = strategy
     - else -> sets source_system = 'unknown_legacy' (preserves the tag
       contract so dashboard generators don't trip on NULL)
  4. Reports counts; --apply commits, default is dry-run

Idempotent: re-running after a successful --apply matches zero rows.

Why this matters
----------------
Dashboard generators (`audit_trail/dashboard_generator.py`) and the
EAGLE-3 promotion gate (`audit_trail/promotion_gate.py`) both filter by
source_system. NULL source_system rows are silently excluded from
asset-class WR/PF computation, which biases the audit page toward
emitters that happened to set the field. Backfilling lets the gate
see the full pick population.
"""
from __future__ import annotations

import argparse
import sys

import pymysql

DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.environ.get('DB_PASS_STOCKS','') or os.environ.get('MYSQL_PASSWORD','')
DB_NAME = "ejaguiar1_stocks"

UNKNOWN_LEGACY = "unknown_legacy"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Commit the UPDATEs. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap rows scanned (testing).")
    parser.add_argument("--unknown-legacy-tag", default=UNKNOWN_LEGACY,
                        help=f"Fallback tag (default: {UNKNOWN_LEGACY!r}).")
    args = parser.parse_args()

    try:
        conn = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
            charset="utf8mb4", connect_timeout=15,
        )
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        return 2

    plan_a_count = 0  # source_system <- strategy
    plan_b_count = 0  # source_system <- unknown_legacy
    plan_a_rows: list[tuple[int, str]] = []
    plan_b_rows: list[int] = []

    try:
        with conn.cursor() as cur:
            limit_clause = f"LIMIT {int(args.limit)}" if args.limit else ""
            cur.execute(
                f"SELECT id, strategy FROM trading_picks "
                f"WHERE (source_system IS NULL OR source_system = '') "
                f"{limit_clause}"
            )
            rows = cur.fetchall()
            for (rid, strat) in rows:
                strat = (strat or "").strip()
                if strat:
                    plan_a_count += 1
                    plan_a_rows.append((rid, strat))
                else:
                    plan_b_count += 1
                    plan_b_rows.append(rid)

            print(f"Scanned: {len(rows)} rows with NULL/empty source_system")
            print(f"  Plan A (source_system <- strategy): {plan_a_count}")
            print(f"  Plan B (source_system <- {args.unknown_legacy_tag!r}): {plan_b_count}")

            if not args.apply:
                print("\nDRY-RUN. Pass --apply to commit.")
                print("Sample Plan A:")
                for rid, s in plan_a_rows[:5]:
                    print(f"  id={rid}  strategy={s!r}")
                print("Sample Plan B:")
                for rid in plan_b_rows[:5]:
                    print(f"  id={rid}")
                return 0

            # Apply in chunks (50webs MySQL is brittle on large executemany)
            CHUNK = 50
            applied_a = 0
            for i in range(0, len(plan_a_rows), CHUNK):
                batch = plan_a_rows[i:i + CHUNK]
                cur.executemany(
                    "UPDATE trading_picks SET source_system=%s "
                    "WHERE id=%s AND (source_system IS NULL OR source_system='')",
                    [(s, rid) for (rid, s) in batch],
                )
                conn.commit()
                applied_a += cur.rowcount

            applied_b = 0
            for i in range(0, len(plan_b_rows), CHUNK):
                batch = plan_b_rows[i:i + CHUNK]
                cur.executemany(
                    "UPDATE trading_picks SET source_system=%s "
                    "WHERE id=%s AND (source_system IS NULL OR source_system='')",
                    [(args.unknown_legacy_tag, rid) for rid in batch],
                )
                conn.commit()
                applied_b += cur.rowcount

            print(f"\nAPPLIED: {applied_a} via Plan A, {applied_b} via Plan B")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
