#!/usr/bin/env python3
"""
SAFE orphan resolver — dry-run preview. NO DB writes.

Per Hermes 2026-05-09 rules + corrected scope from PR #892:
  TRUE orphans = closed_at IS NULL AND status IN <terminal-statuses>
  Count: 1,366 (NOT 38,129 Hermes-claimed; NOT 57,710 raw-NULL — 56,190
  of those are legitimately OPEN/active positions, not bugs)

These rows have pnl_pct populated (917 negative + 449 positive) but
NULL closed_at — they came from sources that emit `exit_time` instead
of `closed_at` (PR #891 writer fix solves the GO-FORWARD case via
fallback chain; this script handles the BACKLOG of 1,366 historic rows).

STRATEGY
========
Since pnl_pct is ALREADY set, we don't need price-fetch. Estimate
closed_at deterministically:
  closed_at = created_at + asset_class_hold_estimate

Where asset_class_hold_estimate uses the same MAX_HOLD_HOURS_BY_CLASS
table as alpha_engine/outcome_resolver.py:
  CRYPTO    24h    (most picks resolve same-day)
  EQUITY    96h
  ETF       96h
  COMMODITY 96h
  FUTURES   96h
  FOREX    120h
  BOND     120h

For midpoint estimate use 50% of MAX (conservative — real average
resolution is around half the cap).

OUTPUT
======
reports/orphan_resolver_dryrun_<TS>/preview.csv with columns:
  id, symbol, source_system, strategy, category, status,
  created_at, proposed_closed_at, hold_hours_used, pnl_pct, would_apply

NO DB writes. NO price fetches. NO API calls. Pure metadata estimation.

To turn into an apply-mode update later, must:
  1. Run safe_db_archive.py first (Hermes rule #1)
  2. Review CSV
  3. UPDATE in batches of 1,000 (Hermes rule #3)
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymysql

if sys.platform == "win32":
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

REPO = Path(__file__).resolve().parent.parent
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO / "reports" / f"orphan_resolver_dryrun_{TS}"
OUT.mkdir(parents=True, exist_ok=True)

# Mirror alpha_engine/outcome_resolver.py NON_CRYPTO_MAX_HOLD_HOURS_BY_CLASS
HOLD_HOURS_BY_CLASS = {
    "CRYPTO":    24,
    "EQUITY":    96,
    "ETF":       96,
    "COMMODITY": 96,
    "FUTURES":   96,
    "STOCK":     96,
    "INDEX":     96,
    "FOREX":    120,
    "BOND":     120,
}
DEFAULT_HOLD_HOURS = 48


def estimate_hold_hours(category: str) -> int:
    cat = (category or "").upper().strip()
    full = HOLD_HOURS_BY_CLASS.get(cat, DEFAULT_HOLD_HOURS)
    # midpoint estimate — real average resolution is ~half the cap
    return max(1, full // 2)


def main():
    print("=== SAFE ORPHAN RESOLVER (dry-run) ===")
    conn = pymysql.connect(
        host="mysql.50webs.com", user="ejaguiar1_stocks",
        password=os.environ.get("DB_PASS_STOCKS", ""), db="ejaguiar1_stocks",
        connect_timeout=15, read_timeout=180,
    )
    cur = conn.cursor()

    # Pull all 1,366 orphans (terminal-status + NULL closed_at)
    cur.execute("""
        SELECT id, symbol, source_system, strategy, category, status,
               created_at, pnl_pct, exit_reason, direction
        FROM trading_picks
        WHERE closed_at IS NULL
          AND status IN ('WON','LOST','TP_HIT','SL_HIT','CLOSED_TP',
                         'CLOSED_SL','EXPIRED','TIME_EXIT','FLAT','CLOSED',
                         'WIN','LOSS','STALE')
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    print(f"  matching orphans: {len(rows):,}")

    out_rows = []
    no_created_at = 0
    by_category = {}
    for r in rows:
        (id_, symbol, source, strategy, category, status,
         created_at, pnl_pct, exit_reason, direction) = r

        if created_at is None:
            no_created_at += 1
            would_apply = False
            proposed_closed_at = ""
            hold_h = 0
        else:
            hold_h = estimate_hold_hours(category)
            proposed_closed_at = (created_at + timedelta(hours=hold_h)).strftime("%Y-%m-%d %H:%M:%S")
            would_apply = True

        by_category[category or "NULL"] = by_category.get(category or "NULL", 0) + 1
        out_rows.append({
            "id": (id_ or "")[:60],
            "symbol": symbol or "",
            "source_system": source or "",
            "strategy": (strategy or "")[:40],
            "category": category or "",
            "status": status,
            "created_at": str(created_at) if created_at else "",
            "proposed_closed_at": proposed_closed_at,
            "hold_hours_used": hold_h,
            "pnl_pct": float(pnl_pct) if pnl_pct is not None else "",
            "exit_reason": exit_reason or "",
            "direction": direction or "",
            "would_apply": "YES" if would_apply else "NO_no_created_at",
        })

    csv_path = OUT / "preview.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        cols = list(out_rows[0].keys())
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    apply_count = sum(1 for r in out_rows if r["would_apply"] == "YES")

    print(f"\n  WOULD_APPLY: {apply_count:,} of {len(out_rows):,}")
    print(f"  no_created_at (skipped): {no_created_at:,}")
    print(f"\n  by category:")
    for cat, n in sorted(by_category.items(), key=lambda x: -x[1]):
        hold_h = estimate_hold_hours(cat) if cat != "NULL" else "—"
        print(f"    {cat:12s} n={n:>4} hold_h={hold_h}")

    print(f"\n  preview written: {csv_path}")
    print(f"\n  NO DB writes. NO API calls. Pure metadata estimation.")
    print(f"\n  NEXT STEPS (for future --apply pass, NOT this PR):")
    print(f"    1. python tools/safe_db_archive.py --source-table trading_picks \\")
    print(f"         --where \"closed_at IS NULL AND status IN ('WON',...)\" \\")
    print(f"         --purpose orphan_resolver_apply --apply")
    print(f"    2. Review reports/db_archives_log.md")
    print(f"    3. UPDATE in 1000-row batches with proposed_closed_at values")
    print(f"    4. Verify dashboard tile counts before/after")

    conn.close()


if __name__ == "__main__":
    main()
