#!/usr/bin/env python3
"""Audit confidence schema for mixed-scale data quality bug.

Discovered 2026-05-11 in SUPREME EDGE P0 #9 verify: some `confidence` values
in trading_picks are on 0-1 scale (modern writers) and others on 0-10 scale
(legacy writer, observed value=10.000). Same column. Same table. Causes
HIGH_CONVICTION gate to misfire and calibration measurements to compound.

This script enumerates writers + scale distribution and produces a report
to feed the follow-up fix PR.

Usage:
    python tools/audit_confidence_schema.py           # full audit
    python tools/audit_confidence_schema.py --table trading_picks   # one table

Read-only. Safe to run in production.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

try:
    import pymysql
except ImportError:
    print("ERROR: pymysql not installed. Run: pip install pymysql", file=sys.stderr)
    sys.exit(2)


def connect():
    return pymysql.connect(
        host=os.environ.get("DB_STOCKS_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_STOCKS_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_STOCKS_PASSWORD", "stocks"),
        database=os.environ.get("DB_STOCKS_NAME", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_STOCKS_PORT", "3306")),
        connect_timeout=30,
        read_timeout=60,
    )


def audit_table(cur, table: str) -> dict:
    """Return scale-distribution summary for one table's confidence column."""
    out = {"table": table, "has_column": False, "scales": {}, "writers": [],
           "min": None, "max": None, "n": 0}
    try:
        cur.execute(f"SHOW COLUMNS FROM {table} LIKE 'confidence'")
        if not cur.fetchone():
            return out
        out["has_column"] = True

        cur.execute(f"""
            SELECT
                COUNT(*) AS n,
                MIN(confidence) AS min_c,
                MAX(confidence) AS max_c,
                SUM(CASE WHEN confidence BETWEEN 0 AND 1 THEN 1 ELSE 0 END) AS n_0_1,
                SUM(CASE WHEN confidence > 1 AND confidence <= 10 THEN 1 ELSE 0 END) AS n_1_10,
                SUM(CASE WHEN confidence > 10 AND confidence <= 100 THEN 1 ELSE 0 END) AS n_10_100,
                SUM(CASE WHEN confidence > 100 THEN 1 ELSE 0 END) AS n_gt_100,
                SUM(CASE WHEN confidence IS NULL THEN 1 ELSE 0 END) AS n_null
            FROM {table}
        """)
        r = cur.fetchone()
        out["n"] = int(r["n"] or 0)
        out["min"] = float(r["min_c"]) if r["min_c"] is not None else None
        out["max"] = float(r["max_c"]) if r["max_c"] is not None else None
        out["scales"] = {
            "0_1": int(r["n_0_1"] or 0),
            "1_10": int(r["n_1_10"] or 0),
            "10_100": int(r["n_10_100"] or 0),
            "gt_100": int(r["n_gt_100"] or 0),
            "null": int(r["n_null"] or 0),
        }

        # Probe writers — group by strategy and check scale per group
        try:
            cur.execute(f"""
                SELECT strategy,
                    MIN(confidence) AS min_c,
                    MAX(confidence) AS max_c,
                    COUNT(*) AS n
                FROM {table}
                WHERE confidence IS NOT NULL
                GROUP BY strategy
                HAVING (MAX(confidence) > 1 AND MIN(confidence) >= 1) OR
                       (MAX(confidence) <= 1 AND MIN(confidence) < 1)
                ORDER BY n DESC
                LIMIT 25
            """)
            for row in cur.fetchall():
                scale = "0_10" if (row["max_c"] or 0) > 1 else "0_1"
                out["writers"].append({
                    "strategy": row["strategy"],
                    "scale": scale,
                    "min": float(row["min_c"] or 0),
                    "max": float(row["max_c"] or 0),
                    "n": int(row["n"] or 0),
                })
        except Exception as e:
            out["writers_error"] = str(e)[:120]
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--table", default=None, help="Single table to audit")
    args = p.parse_args()

    tables = [args.table] if args.table else [
        "trading_picks",
        "at_raw_picks",
        "at_local_picks",
        "at_consensus_picks",
    ]

    try:
        conn = connect()
    except Exception as e:
        print(f"DB connect failed: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(pymysql.cursors.DictCursor)
    print(f"# Confidence schema audit — {os.environ.get('DB_STOCKS_HOST', 'mysql.50webs.com')}")
    print()

    bad_tables = []
    for t in tables:
        r = audit_table(cur, t)
        print(f"## {t}")
        if not r["has_column"]:
            print("  (no `confidence` column)")
            print()
            continue
        print(f"  n={r['n']}  min={r['min']}  max={r['max']}")
        print(f"  buckets: " + ", ".join(f"{k}={v}" for k, v in r["scales"].items()))
        mixed = (r["scales"]["0_1"] > 0) and (r["scales"]["1_10"] + r["scales"]["10_100"] + r["scales"]["gt_100"] > 0)
        if mixed:
            print(f"  [WARN] MIXED-SCALE DETECTED — 0-1 rows: {r['scales']['0_1']}, >1 rows: {r['scales']['1_10'] + r['scales']['10_100'] + r['scales']['gt_100']}")
            bad_tables.append(t)
        if r["writers"]:
            print(f"  Top-25 writers by scale (n>=1):")
            for w in r["writers"]:
                print(f"    {w['strategy'][:40]:40} scale={w['scale']:5} min={w['min']:.3f}  max={w['max']:.3f}  n={w['n']}")
        print()

    cur.close()
    conn.close()

    print(f"## Verdict")
    if bad_tables:
        print(f"  Mixed-scale bug confirmed in: {', '.join(bad_tables)}")
        print(f"  Action: normalize on read in audit_trail/quality_gates.py (9 callsites)")
        print(f"          + open issue against writers emitting >1 values")
        sys.exit(1)
    else:
        print("  No mixed-scale bug detected.")


if __name__ == "__main__":
    main()
