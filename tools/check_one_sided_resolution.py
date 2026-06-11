#!/usr/bin/env python3
"""One-sided resolution checker (FINDING_OVERALL#12) — READ-ONLY CI assertion.

Flags strategies in at_raw_picks whose resolved (WON/LOST) outcomes are 100%
one-sided — every resolved row WON or every resolved row LOST — with at least
MIN_RESOLVED resolved rows. A strategy that only ever resolves to one side is
the signature of a resolver/close-path bug (e.g. only one transition branch
fires), not of genuine edge: the artifact grew 41 -> 57 strategies between
2026-05-31 and 2026-06-11 while unguarded, silently biasing every raw
at_raw_picks WR computation that feeds /audit drill-downs.

This script is a tripwire, not a fixer: it performs ONLY a SELECT (no writes)
and reports. Wire it as a non-blocking warning step in a daily data-quality
workflow (see .github/workflows/daily-scrutiny-engine.yml).

Exit codes:
    0 — no one-sided strategies at or above the threshold
    1 — one-sided strategies found (listed on stdout)
    2 — infrastructure error (no creds / cannot connect / query failed)

Usage:
    python3 tools/check_one_sided_resolution.py [--min-resolved 20] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

QUERY = """
    SELECT strategy,
           SUM(status = 'WON')  AS won,
           SUM(status = 'LOST') AS lost,
           COUNT(*)             AS total_rows
    FROM at_raw_picks
    GROUP BY strategy
    HAVING (won + lost) >= %s
       AND (won = 0 OR lost = 0)
    ORDER BY (won + lost) DESC
"""


def fetch_one_sided(min_resolved: int) -> list[dict]:
    """Return strategies with >= min_resolved WON+LOST rows, all on one side."""
    import pymysql
    import pymysql.cursors
    from tools.db_env import get_stocks_creds

    conn = pymysql.connect(
        **get_stocks_creds(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY, (min_resolved,))
            rows = cur.fetchall()
    finally:
        conn.close()

    out = []
    for r in rows:
        won = int(r["won"] or 0)
        lost = int(r["lost"] or 0)
        out.append({
            "strategy": r["strategy"],
            "won": won,
            "lost": lost,
            "resolved": won + lost,
            "total_rows": int(r["total_rows"] or 0),
            "side": "WON-only" if lost == 0 else "LOST-only",
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FINDING#12: flag 100% one-sided WON-only/LOST-only "
                    "resolution per strategy in at_raw_picks (read-only)")
    parser.add_argument("--min-resolved", type=int, default=20,
                        help="minimum WON+LOST rows for a strategy to be "
                             "eligible (default: 20)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit machine-readable JSON instead of text")
    args = parser.parse_args()

    try:
        offenders = fetch_one_sided(args.min_resolved)
    except Exception as exc:  # creds missing / connect refused / bad query
        print(f"INFRA_ERROR: one-sided check could not run: {exc}",
              file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps({
            "min_resolved": args.min_resolved,
            "one_sided_count": len(offenders),
            "ok": not offenders,
            "strategies": offenders,
        }, indent=2, default=str))
    elif offenders:
        print(f"FAIL: {len(offenders)} strategies with >= {args.min_resolved} "
              f"resolved rows are 100% one-sided (FINDING#12):")
        for o in offenders:
            print(f"  {o['side']:<10} won={o['won']:<6} lost={o['lost']:<6} "
                  f"resolved={o['resolved']:<6} total={o['total_rows']:<6} "
                  f"{o['strategy']}")
    else:
        print(f"OK: no strategy with >= {args.min_resolved} resolved rows is "
              f"100% one-sided.")

    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main())
