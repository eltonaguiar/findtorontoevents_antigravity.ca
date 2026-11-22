#!/usr/bin/env python3
"""
invalid_row_forensics.py — decompose the undifferentiated `invalid_row` exclusion.

`alpha_engine/resolved_closed_view.build_view` labels every row that its coarse
classifier cannot name as `invalid_row` (resolved_closed_view.py:207-245, :309-311).
The rows were dropped by the stricter `_is_valid_resolved_pick` predicate
(audit_trail/dashboard_generator.py:4924), which has many branches. This tool
approximates those branches in SQL against `trading_picks` so the single label
becomes a measurable split, and it also measures the intrabar-vs-daily gap on
the same rows.

It is an APPROXIMATION, not the predicate itself: the real predicate also reads
`_is_historical_blocked_pick`, quality-gate files and per-pick heuristics that do
not live in the table. Every bucket is therefore a lower bound, and `unexplained`
is the honest remainder.

Read-only. Usage:
    python3 tools/invalid_row_forensics.py
    python3 tools/invalid_row_forensics.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MIN_HOLD_SECONDS = 60  # conservative stand-in for dashboard_generator._MIN_HOLD_SECONDS

# The same population the scrutiny engine scores, so the split is comparable.
POP = (
    "closed_at IS NOT NULL AND pnl_pct IS NOT NULL "
    "AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') "
    "AND closed_at > '2026-01-01' AND DATE(closed_at) != '2026-06-04'"
)

# Each branch is mutually exclusive by construction: evaluated in order, a row is
# attributed to the first branch that fires. Mirrors the predicate's order.
BRANCHES: list[tuple[str, str]] = [
    ("auto_expired", "exit_reason IS NOT NULL AND (UPPER(exit_reason) LIKE 'STALE%' OR UPPER(exit_reason)='INVALID_ENTRY')"),
    ("resolver_breakeven_fallback", "exit_reason IS NOT NULL AND UPPER(exit_reason) LIKE 'RESOLVE_FAILED%'"),
    ("placeholder_exit", "exit_price IS NOT NULL AND exit_price <= 0"),
    ("price_magnitude_gt_100x",
     "entry_price > 0 AND exit_price > 0 AND "
     "(entry_price / exit_price > 100 OR exit_price / entry_price > 100)"),
    ("non_crypto_move_gt_50pct",
     "entry_price > 0 AND exit_price > 0 AND LOWER(category) != 'crypto' AND "
     "(entry_price / exit_price > 1.5 OR exit_price / entry_price > 1.5)"),
    ("micro_hold_lt_60s",
     f"created_at IS NOT NULL AND closed_at IS NOT NULL AND TIMESTAMPDIFF(SECOND, created_at, closed_at) < {MIN_HOLD_SECONDS}"),
    ("non_performance_status", "status IS NOT NULL AND UPPER(status) IN ('ABANDONED','FLAT','FORCE_CLOSED_TOXIC','OPEN')"),
    ("unknown_exit_no_close_marker",
     "(exit_reason IS NULL OR UPPER(exit_reason) IN ('','UNKNOWN')) AND closed_at IS NULL "
     "AND UPPER(status) NOT IN ('WON','LOST','EXPIRED','CLOSED')"),
]

CASE_SQL = "CASE " + " ".join(
    f"WHEN {cond} THEN '{name}'" for name, cond in BRANCHES
) + " ELSE 'unexplained' END"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output only")
    args = ap.parse_args(argv)

    import pymysql
    from tools.db_env import get_stocks_creds

    creds = get_stocks_creds()
    creds["connect_timeout"] = 10
    creds["read_timeout"] = 120
    conn = pymysql.connect(**creds)
    out: dict = {"generated_at": datetime.now(timezone.utc).isoformat(),
                 "population": POP, "min_hold_seconds": MIN_HOLD_SECONDS,
                 "branches": {}, "by_class": [], "intrabar_gap": []}
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT {CASE_SQL} branch, COUNT(*) n, "
            f"ROUND(AVG(pnl_pct),4) mean_pnl, "
            f"ROUND(SUM(IF(pnl_pct>0,1,0))/COUNT(*),4) wr "
            f"FROM trading_picks WHERE {POP} GROUP BY branch ORDER BY n DESC"
        )
        for branch, n, mean_pnl, wr in cur.fetchall():
            out["branches"][branch] = {"n": int(n),
                                      "mean_pnl_pct": float(mean_pnl) if mean_pnl is not None else None,
                                      "wr": float(wr) if wr is not None else None}

        cur.execute(
            f"SELECT LOWER(TRIM(category)) cls, {CASE_SQL} branch, COUNT(*) n, "
            f"ROUND(SUM(IF(pnl_pct>0,1,0))/COUNT(*),4) wr, ROUND(AVG(pnl_pct),4) mean_pnl "
            f"FROM trading_picks WHERE {POP} GROUP BY cls, branch HAVING n >= 20 ORDER BY cls, n DESC"
        )
        out["by_class"] = [{"class": r[0], "branch": r[1], "n": int(r[2]),
                            "wr": float(r[3] or 0), "mean_pnl_pct": float(r[4] or 0)}
                           for r in cur.fetchall()]

        # Intrabar vs daily. A handful of rows carry corrupt intrabar values
        # (one INJUSDT row: entry 3.384 -> exit 3.456, daily +2.13%, intrabar
        # 1,706,212%). A mean is hijacked by them, so this uses the MEDIAN and
        # reports the corrupt count separately.
        cur.execute(
            f"SELECT LOWER(TRIM(category)) cls, COUNT(*) n, "
            f"ROUND(SUM(IF(pnl_pct>0,1,0))/COUNT(*),4) daily_wr, "
            f"ROUND(SUM(IF(intrabar_pnl_pct>0,1,0))/COUNT(*),4) intrabar_wr, "
            f"SUM(IF(intrabar_ambiguous=1,1,0)) ambiguous "
            f"FROM trading_picks WHERE {POP} AND intrabar_pnl_pct IS NOT NULL "
            f"AND intrabar_pnl_pct BETWEEN -100 AND 100 GROUP BY cls ORDER BY n DESC"
        )
        for (cls, n, dwr, iwr, amb) in cur.fetchall():
            out["intrabar_gap"].append({
                "class": cls, "n": int(n),
                "daily_wr": float(dwr or 0), "intrabar_wr": float(iwr or 0),
                "wr_gap_pp": round(((float(dwr or 0) - float(iwr or 0)) * 100), 2),
                "ambiguous": int(amb or 0),
            })
        cur.execute(
            f"SELECT COUNT(*) FROM trading_picks WHERE {POP} "
            f"AND intrabar_pnl_pct IS NOT NULL AND NOT (intrabar_pnl_pct BETWEEN -100 AND 100)"
        )
        out["intrabar_corrupt_rows"] = int(cur.fetchone()[0] or 0)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"invalid_row forensics  ({out['generated_at']})")
    print(f"population: scrutiny filter, min hold {MIN_HOLD_SECONDS}s\n")
    print(f"{'branch':<30}{'n':>8}{'wr':>8}{'mean%':>10}")
    for branch, b in out["branches"].items():
        print(f"{branch:<30}{b['n']:>8}{b['wr'] if b['wr'] is not None else '-':>8}"
              f"{b['mean_pnl_pct'] if b['mean_pnl_pct'] is not None else '-':>10}")
    total = sum(b["n"] for b in out["branches"].values())
    unexplained = out["branches"].get("unexplained", {}).get("n", 0)
    print(f"\ntotal rows {total}; explained {total - unexplained} "
          f"({round(100*(total-unexplained)/total, 2) if total else 0}%); unexplained {unexplained}")
    print("\nintrabar vs daily WR (sane subset, intrabar in [-100,100]):")
    print(f"{'class':<14}{'n':>7}{'daily wr':>10}{'intr wr':>9}{'gap pp':>8}{'ambig':>7}")
    for g in out["intrabar_gap"]:
        print(f"{g['class']:<14}{g['n']:>7}{g['daily_wr']:>10}{g['intrabar_wr']:>9}"
              f"{g['wr_gap_pp']:>8}{g['ambiguous']:>7}")
    print(f"corrupt intrabar rows excluded: {out.get('intrabar_corrupt_rows', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
