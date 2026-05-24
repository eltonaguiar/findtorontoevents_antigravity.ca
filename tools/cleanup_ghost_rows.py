#!/usr/bin/env python3
"""
Ghost row cleanup for MySQL database.

Identifies cohorts of duplicate rows sharing the same (symbol, strategy, direction, entry_price)
and deletes all but the row with the lowest id. DRY_RUN mode is default.

Ghost cohorts from db_health.json (2026-05-24):
  - MATICUSDT / quan_engine / LONG  @ 150000: 20,474 rows
  - DOGEUSDT / meta_strategy / LONG @ 500000: 5,661 rows
  - WIFUSDT  / meta_strategy / SHORT @ 500000: 4,644 rows
  ... and 9 more cohorts, 56,559 total ghost rows.

Usage:
  python tools/cleanup_ghost_rows.py             # dry run, shows what would be deleted
  python tools/cleanup_ghost_rows.py --execute    # actually delete
  python tools/cleanup_ghost_rows.py --no-limit   # remove 1000-row safety cap
  python tools/cleanup_ghost_rows.py --min-size 10  # only process cohorts with >= N rows (default: 5)

Safety:
  - DRY_RUN mode is the default; nothing is deleted without --execute
  - Max 1000 deletes per run unless --no-limit
  - All deletes wrapped in a single transaction (rolled back on error)
  - Reports before/after counts and per-cohort summaries
  - Requires confirmation prompt before --execute (unless --yes)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── DB connection ─────────────────────────────────────────────────────────────

try:
    from tools.db_env import get_stocks_creds
    _USE_DB_ENV = True
except ImportError:
    _USE_DB_ENV = False


def _read_db_password() -> str:
    """Read DB password from /home/eaguiar2015/dbpasses.txt if available."""
    try:
        lines = open("/home/eaguiar2015/dbpasses.txt").read().strip().splitlines()
        for line in lines:
            if "stocks" in line.lower():
                return line.strip()
        return lines[0] if lines else ""
    except FileNotFoundError:
        return ""


def _connect() -> Any:
    """Return a pymysql connection to ejaguiar1_stocks."""
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed — run: pip install pymysql")

    if _USE_DB_ENV:
        creds = get_stocks_creds()
        return pymysql.connect(**creds)

    password = (os.environ.get("DB_PASS_STOCKS") or 
                os.environ.get("MYSQL_PASSWORD") or 
                _read_db_password())
    if not password:
        raise RuntimeError(
            "No DB password — set DB_PASS_STOCKS, MYSQL_PASSWORD, or create /home/eaguiar2015/dbpasses.txt"
        )
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=password,
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=int(os.environ.get("DB_PORT_STOCKS", "3306")),
        connect_timeout=30,
        read_timeout=60,
        autocommit=False,
    )


# ── Constants ─────────────────────────────────────────────────────────────────

# Target table where ghost rows live (verified via ghost_sweep_2026_05_08.py)
TARGET_TABLE = "bt_backtest_trades"

# Column names for cohort grouping (validated against ghost_sweep patterns)
COHORT_COLS = ["strategy", "symbol", "direction"]
ENTRY_PRICE_COL = "entry_price"
PNL_COL = "pnl_pct"
PK_COL = "id"

DEFAULT_MIN_COHORT_SIZE = 5
DEFAULT_MAX_DELETES = 1000


# ── Cohort detection ─────────────────────────────────────────────────────────

def discover_ghost_cohorts(conn: Any, min_size: int = DEFAULT_MIN_COHORT_SIZE) -> List[Dict[str, Any]]:
    """Find cohorts of (symbol, strategy, direction, entry_price) with count > min_size.

    Returns list of cohort dicts with keys: strategy, symbol, direction,
    entry_price, count, min_id, max_id, pnl_sample.
    """
    cohort_select = ", ".join(f"`{c}`" for c in COHORT_COLS)
    entry_col = ENTRY_PRICE_COL

    sql = f"""
        SELECT {cohort_select},
               `{entry_col}`,
               COUNT(*) AS cnt,
               MIN(`{PK_COL}`) AS min_id,
               MAX(`{PK_COL}`) AS max_id
        FROM `{TARGET_TABLE}`
        GROUP BY {cohort_select}, `{entry_col}`
        HAVING COUNT(*) > %s
        ORDER BY cnt DESC
    """

    cohorts = []
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (min_size,))
            for row in cur.fetchall():
                cohorts.append({
                    "strategy": row[0],
                    "symbol": row[1],
                    "direction": row[2],
                    "entry_price": row[3],
                    "count": int(row[4]),
                    "min_id": int(row[5]),
                    "max_id": int(row[6]),
                })
    except Exception as exc:
        log.error("Error discovering cohorts: %s", exc)
        raise

    return cohorts


def _sample_pnl(conn: Any, cohort: Dict[str, Any]) -> Optional[float]:
    """Get a representative pnl_pct for the cohort (from the oldest row)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT `{PNL_COL}` FROM `{TARGET_TABLE}` WHERE `{PK_COL}` = %s",
                (cohort["min_id"],),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                return float(row[0])
    except Exception:
        pass
    return None


# ── Deletion logic ────────────────────────────────────────────────────────────

def build_delete_sql(cohort: Dict[str, Any], limit: Optional[int] = None) -> Tuple[str, List[Any]]:
    """Build SQL that deletes ghost rows in a cohort, keeping the one with lowest id.

    Returns (sql, params) tuple.
    """
    # Strategy: delete all rows in the cohort EXCEPT the one with min_id
    conditions = []
    params: List[Any] = []

    for col in COHORT_COLS:
        conditions.append(f"`{col}` = %s")
        params.append(cohort[col])

    conditions.append(f"`{ENTRY_PRICE_COL}` = %s")
    params.append(cohort["entry_price"])

    conditions.append(f"`{PK_COL}` != %s")
    params.append(cohort["min_id"])

    where_clause = " AND ".join(conditions)
    limit_clause = f" LIMIT {limit}" if limit else ""

    sql = f"DELETE FROM `{TARGET_TABLE}` WHERE {where_clause}{limit_clause}"
    return sql, params


def run_cleanup(
    conn: Any,
    cohorts: List[Dict[str, Any]],
    execute: bool = False,
    max_deletes: int = DEFAULT_MAX_DELETES,
) -> Dict[str, Any]:
    """Process cohorts, deleting ghost rows.

    Args:
        conn: pymysql connection (autocommit=False for transaction support)
        cohorts: list of cohort dicts from discover_ghost_cohorts
        execute: if False, only report what would be deleted
        max_deletes: safety cap on total deletions per run

    Returns:
        Report dict with summary and per-cohort details.
    """
    report: Dict[str, Any] = {
        "mode": "EXECUTE" if execute else "DRY_RUN",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cohorts_found": len(cohorts),
        "cohorts_processed": 0,
        "total_deletable": 0,
        "total_deleted": 0,
        "max_deletes_reached": False,
        "remaining_deletable": 0,
        "per_cohort": [],
        "errors": [],
    }

    deletes_remaining = max_deletes if max_deletes is not None else float("inf")
    cap_is_active = max_deletes is not None

    # Pre-compute total deletable across ALL cohorts (before any cap logic)
    for cohort in cohorts:
        report["total_deletable"] += cohort["count"] - 1

    for i, cohort in enumerate(cohorts):
        deletable = cohort["count"] - 1  # keep 1, delete the rest

        # Apply safety cap
        to_delete = deletable
        capped = False
        if cap_is_active and to_delete > deletes_remaining:
            to_delete = int(deletes_remaining)
            capped = True
            report["max_deletes_reached"] = True

        if to_delete <= 0 and cap_is_active:
            # Cap exhausted, skip this cohort
            report["remaining_deletable"] += deletable
            report["per_cohort"].append({
                "strategy": cohort["strategy"],
                "symbol": cohort["symbol"],
                "direction": cohort["direction"],
                "entry_price": cohort["entry_price"],
                "count": cohort["count"],
                "would_delete": 0,
                "capped": True,
            })
            continue

        sql, params = build_delete_sql(cohort, limit=to_delete if capped else None)

        cohort_detail = {
            "strategy": cohort["strategy"],
            "symbol": cohort["symbol"],
            "direction": cohort["direction"],
            "entry_price": cohort["entry_price"],
            "count": cohort["count"],
            "min_id": cohort["min_id"],
            "max_id": cohort["max_id"],
            "would_delete": to_delete,
            "capped": capped,
        }

        if execute:
            try:
                with conn.cursor() as cur:
                    affected = cur.execute(sql, params)
                    cohort_detail["deleted"] = int(affected)
                    log.info(
                        "[%d/%d] DELETED %d rows: %s %s %s @ entry=%s (kept id=%d)",
                        i + 1, len(cohorts), affected,
                        cohort["strategy"], cohort["symbol"], cohort["direction"],
                        cohort["entry_price"], cohort["min_id"],
                    )
                    report["total_deleted"] += int(affected)
                    deletes_remaining -= int(affected)
            except Exception as exc:
                error_msg = f"Cohort {i+1} ({cohort['symbol']}/{cohort['strategy']}): {exc}"
                log.error(error_msg)
                report["errors"].append(error_msg)
                cohort_detail["error"] = str(exc)
        else:
            log.info(
                "[%d/%d] WOULD DELETE %d rows: %s %s %s @ entry=%s (keep id=%d, %d total in cohort)",
                i + 1, len(cohorts), to_delete,
                cohort["strategy"], cohort["symbol"], cohort["direction"],
                cohort["entry_price"], cohort["min_id"], cohort["count"],
            )

        report["per_cohort"].append(cohort_detail)
        report["cohorts_processed"] += 1

        # In execute mode, stop processing once cap is reached.
        # In dry run, continue through all cohorts to show full scope.
        if execute and report["max_deletes_reached"]:
            log.warning("Max deletes cap reached (%d). %d more rows eligible.", max_deletes, report["remaining_deletable"])
            break

    # Transaction handling
    if execute:
        if report["errors"]:
            log.warning("Rolling back transaction due to errors")
            conn.rollback()
            report["total_deleted"] = 0  # reset since rolled back
        else:
            conn.commit()
            log.info("Transaction committed")

    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    return report


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Clean up ghost rows (duplicate entries) from MySQL database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="Actually delete ghost rows. Default is dry run.",
    )
    parser.add_argument(
        "--no-limit", action="store_true",
        help="Remove the 1000-row safety cap on deletions.",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_MAX_DELETES,
        help=f"Max rows to delete per run (default: {DEFAULT_MAX_DELETES}). Ignored if --no-limit.",
    )
    parser.add_argument(
        "--min-size", type=int, default=DEFAULT_MIN_COHORT_SIZE,
        help=f"Minimum cohort size to consider (default: {DEFAULT_MIN_COHORT_SIZE}).",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip confirmation prompt when using --execute.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to write JSON report (default: tools/ghost_cleanup_report.json).",
    )
    parser.add_argument(
        "--cohort-only", type=str, default=None,
        help="Filter to a single cohort by symbol (e.g. 'MATICUSDT').",
    )

    args = parser.parse_args()

    max_deletes = None if args.no_limit else args.limit

    # Connect to DB
    log.info("Connecting to MySQL...")
    try:
        conn = _connect()
    except Exception as exc:
        log.error("Connection failed: %s", exc)
        sys.exit(1)

    try:
        # Discover ghost cohorts
        log.info("Discovering ghost cohorts (min_size=%d)...", args.min_size)
        cohorts = discover_ghost_cohorts(conn, min_size=args.min_size)
        log.info("Found %d ghost cohorts", len(cohorts))

        if not cohorts:
            log.info("No ghost cohorts found. Nothing to do.")
            return

        # Print summary
        total_ghost = sum(c["count"] - 1 for c in cohorts)
        log.info("Total ghost rows across all cohorts: %d", total_ghost)
        log.info("")
        log.info("Top cohorts:")
        for i, c in enumerate(cohorts[:10]):
            log.info(
                "  %d. %s / %s / %s @ entry=%s: %d rows (delete %d)",
                i + 1, c["strategy"], c["symbol"], c["direction"],
                c["entry_price"], c["count"], c["count"] - 1,
            )

        # Filter by symbol if requested
        if args.cohort_only:
            cohorts = [c for c in cohorts if c["symbol"] == args.cohort_only]
            log.info("Filtered to %d cohorts matching symbol '%s'", len(cohorts), args.cohort_only)
            if not cohorts:
                log.info("No cohorts match. Nothing to do.")
                return

        # Confirmation prompt
        if args.execute and not args.yes:
            mode_label = "EXECUTE" if args.execute else "DRY_RUN"
            confirm = input(
                f"\nMode: {mode_label}\n"
                f"Cohorts: {len(cohorts)}\n"
                f"Rows to delete: {min(total_ghost, max_deletes) if max_deletes else total_ghost}\n"
                f"Max deletes cap: {'off' if args.no_limit else max_deletes}\n"
                f"Proceed? (yes/no): "
            )
            if confirm.lower() not in ("yes", "y"):
                log.info("Aborted by user.")
                return

        # Run cleanup
        mode_label = "DRY RUN" if not args.execute else "EXECUTE"
        log.info("=" * 60)
        log.info("Starting cleanup (%s mode)...", mode_label)
        log.info("=" * 60)

        report = run_cleanup(conn, cohorts, execute=args.execute, max_deletes=max_deletes)

        # Print summary
        log.info("")
        log.info("=" * 60)
        log.info("CLEANUP REPORT")
        log.info("=" * 60)
        log.info("Mode: %s", report["mode"])
        log.info("Cohorts found: %d", report["cohorts_found"])
        log.info("Cohorts processed: %d", report["cohorts_processed"])
        log.info("Total deletable: %d", report["total_deletable"])
        if args.execute:
            log.info("Total deleted: %d", report["total_deleted"])
        else:
            log.info("Would delete: %d rows", report["total_deletable"])
        if report["max_deletes_reached"]:
            log.info("Remaining (capped): %d rows", report["remaining_deletable"])
        if report["errors"]:
            log.info("Errors: %d", len(report["errors"]))
            for err in report["errors"]:
                log.error("  - %s", err)

        # Write report
        output_path = args.output or "tools/ghost_cleanup_report.json"
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        log.info("Report written to %s", output_path)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
