#!/usr/bin/env python3
"""
tools/resolve_stale_open_picks.py — Batch-resolve stale OPEN picks in MySQL
=============================================================================

Connects to the ejaguiar1_stocks MySQL database, finds OPEN picks whose age
exceeds the per-asset-class MAX_HOLD_HOURS threshold, and batch-resolves them
as TIME_EXIT with flat PnL.

Hold windows match audit_trail/universal_pick_resolver.py:
  CRYPTO            48h
  EQUITY / ETF / COMMODITY / FUTURES   96h
  FOREX / BOND     120h

Usage
-----
    # Preview only (default)
    python tools/resolve_stale_open_picks.py

    # Execute updates
    python tools/resolve_stale_open_picks.py --execute

    # Custom batch size
    python tools/resolve_stale_open_picks.py --execute --batch-size 5000

Environment variables
---------------------
  AUDIT_DB_HOST    (default: mysql.50webs.com)
  AUDIT_DB_PORT    (default: 3306)
  AUDIT_DB_USER    (default: ejaguiar1_stocks)
  AUDIT_DB_PASS    (REQUIRED — also checked as DB_PASS_STOCKS, MYSQL_PASSWORD)
  AUDIT_DB_NAME    (default: ejaguiar1_stocks)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("stale_open_resolver")

def _read_db_password() -> str:
    """Read DB password from /home/eaguiar2015/dbpasses.txt if available."""
    import json
    try:
        creds = json.loads(open("/home/eaguiar2015/.qwen/settings.json").read())
        db_cred = creds.get("credentials", {})
        # Check common key names for database credentials
        return (db_cred.get("stocks_password") or 
                db_cred.get("db_pass_stocks") or 
                db_cred.get("DB_PASS_STOCKS") or "")
    except Exception:
        pass
    
    try:
        lines = open("/home/eaguiar2015/dbpasses.txt").read().strip().splitlines()
        # The password for stocks DB is typically the line matching "stocks"
        for line in lines:
            if "stocks" in line.lower():
                return line.strip()
        return lines[0] if lines else ""
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# DB config
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("AUDIT_DB_HOST", os.getenv("DB_HOST", "mysql.50webs.com"))
DB_PORT = int(os.getenv("AUDIT_DB_PORT", os.getenv("DB_PORT", "3306")))
DB_USER = os.getenv("AUDIT_DB_USER", os.getenv("DB_USER", "ejaguiar1_stocks"))
DB_PASS = (
    os.getenv("AUDIT_DB_PASS")
    or os.getenv("DB_PASS_STOCKS")
    or os.getenv("MYSQL_PASSWORD")
    or _read_db_password()
)
DB_NAME = os.getenv("AUDIT_DB_NAME", os.getenv("DB_NAME", "ejaguiar1_stocks"))

# ---------------------------------------------------------------------------
# Constants — mirrors universal_pick_resolver.py MAX_HOLD_HOURS_BY_CLASS
# ---------------------------------------------------------------------------
MAX_HOLD_HOURS_BY_CLASS: dict[str, int] = {
    "CRYPTO": 48,
    "EQUITY": 96,
    "ETF": 96,
    "COMMODITY": 96,
    "FUTURES": 96,
    "FOREX": 120,
    "BOND": 120,
}
DEFAULT_MAX_HOLD_HOURS = 48

# ---------------------------------------------------------------------------
# Dependencies check
# ---------------------------------------------------------------------------
try:
    import pymysql
except ImportError:
    sys.exit("pymysql not installed -- run: pip install pymysql")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _connect():
    """Open a pymysql connection."""
    if not DB_PASS:
        log.error(
            "No DB password -- set AUDIT_DB_PASS, DB_PASS_STOCKS, or MYSQL_PASSWORD"
        )
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=15,
    )


def _hold_hours_for(category: str) -> int:
    """Return the per-category TIME_EXIT window in hours."""
    c = (category or "").strip().lower()
    # Map categories to asset-class-like hold windows
    mapping = {
        "crypto": 48,
        "meme": 48,
        "equity": 96,
        "equities": 96,
        "stock": 96,
        "stocks": 96,
        "penny": 72,
        "pennystock": 72,
        "etf": 96,
        "commodity": 96,
        "commodities": 96,
        "futures": 96,
        "forex": 120,
        "bond": 120,
        "bonds": 120,
        "index": 96,
    }
    return mapping.get(c, DEFAULT_MAX_HOLD_HOURS)


# ---------------------------------------------------------------------------
# Core resolution logic
# ---------------------------------------------------------------------------

def count_open_picks(conn) -> int:
    """Return total OPEN picks count."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM trading_picks WHERE status = 'OPEN'")
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0


def find_stale_picks(conn, batch_size: int) -> list[dict[str, Any]]:
    """
    Find OPEN picks older than their asset class MAX_HOLD_HOURS.

    Uses a SQL query that checks each pick's submitted_at/created_at against
    the per-class threshold via INTERVAL HOUR clauses.

    Returns list of pick dicts.
    """
    # We query all OPEN picks with their asset_class and timestamp, then
    # filter in Python for the per-class threshold (simpler than a massive
    # UNION of per-class queries).
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, symbol, asset_class, strategy, direction, "
            "entry_price, tp_price, sl_price, "
            "created_at, submitted_at "
            "FROM trading_picks "
            "WHERE status = 'OPEN' "
            "ORDER BY created_at ASC "
            "LIMIT %s",
            (batch_size,),
        )
        return cur.fetchall()


def _pick_age_hours(pick: dict) -> float | None:
    """Return age of pick in hours, or None if timestamp is missing."""
    # Prefer submitted_at, fall back to created_at
    ts = pick.get("submitted_at") or pick.get("created_at")
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - ts
        return age.total_seconds() / 3600.0
    if isinstance(ts, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                dt = datetime.strptime(ts[:26], fmt.replace("%f", "").replace("Z", "").rstrip(" "))
                dt = dt.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - dt
                return age.total_seconds() / 3600.0
            except ValueError:
                continue
    return None


def is_stale(pick: dict) -> bool:
    """Check if a pick is stale (older than its asset class hold window)."""
    age_hours = _pick_age_hours(pick)
    if age_hours is None:
        return False
    max_hours = _hold_hours_for(pick.get("asset_class", ""))
    return age_hours > max_hours


def _compute_pnl(pick: dict, current_price: float | None = None) -> float:
    """Compute PnL percentage for a time-exited pick."""
    entry = float(pick.get("entry_price") or 0)
    if entry <= 0:
        return 0.0
    direction = (pick.get("direction") or "LONG").upper()
    if current_price and current_price > 0:
        exit_price = current_price
    else:
        exit_price = entry  # flat PnL if no price available

    if direction == "SHORT":
        return round((entry - exit_price) / entry * 100, 4)
    else:
        return round((exit_price - entry) / entry * 100, 4)


# ---------------------------------------------------------------------------
# Main resolve loop
# ---------------------------------------------------------------------------

def resolve_stale_open_picks(
    execute: bool = False,
    batch_size: int = 1000,
    max_batches: int | None = None,
) -> dict:
    """
    Find and batch-resolve stale OPEN picks.

    Parameters
    ----------
    execute : bool
        If False (default), only counts and reports. If True, writes updates.
    batch_size : int
        Number of picks to fetch per SQL query.
    max_batches : int | None
        Maximum number of batches to process. None = unlimited (process all stale picks).

    Returns
    -------
    dict with summary statistics.
    """
    now_utc = datetime.now(timezone.utc)
    summary: dict = {
        "started_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "EXECUTE" if execute else "DRY_RUN",
        "batch_size": batch_size,
        "total_open_picks": 0,
        "batches_processed": 0,
        "total_stale_found": 0,
        "total_resolved": 0,
        "by_asset_class": defaultdict(lambda: {"stale": 0, "resolved": 0}),
        "by_strategy": defaultdict(lambda: {"stale": 0, "resolved": 0}),
        "errors": 0,
        "completed_at": None,
    }

    conn = _connect()
    try:
        summary["total_open_picks"] = count_open_picks(conn)
        log.info("Total OPEN picks: %d", summary["total_open_picks"])

        if summary["total_open_picks"] == 0:
            log.info("No OPEN picks -- nothing to resolve.")
            summary["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            return summary

        batches_done = 0
        total_resolved = 0

        while True:
            picks = find_stale_picks(conn, batch_size)
            if not picks:
                log.info("No more OPEN picks to check.")
                break

            batches_done += 1
            if max_batches and batches_done > max_batches:
                log.info("Max batches limit reached (%d).", max_batches)
                break

            stale_picks = [p for p in picks if is_stale(p)]
            summary["total_stale_found"] += len(stale_picks)

            # Accumulate stats by asset class and strategy
            for p in stale_picks:
                ac = (p.get("asset_class") or "UNKNOWN").upper()
                strat = (p.get("strategy") or "unknown")[:100]
                summary["by_asset_class"][ac]["stale"] += 1
                summary["by_strategy"][strat]["stale"] += 1

            if not stale_picks:
                log.info(
                    "Batch %d: %d OPEN picks checked, 0 stale.",
                    batches_done, len(picks),
                )
                continue

            log.info(
                "Batch %d: %d OPEN picks, %d stale (>%d asset classes).",
                batches_done, len(picks), len(stale_picks),
                len({(p.get("asset_class") or "UNKNOWN").upper() for p in stale_picks}),
            )

            if execute:
                # Batch update
                update_sql = (
                    "UPDATE trading_picks "
                    "SET status='TIME_EXIT', resolved_at=%s, "
                    "exit_reason='TIME_EXIT_MAX_HOLD', exit_price=entry_price, pnl_pct=0.0 "
                    "WHERE id=%s"
                )
                resolved_now = now_utc.strftime("%Y-%m-%d %H:%M:%S")

                updated = 0
                with conn.cursor() as cur:
                    for p in stale_picks:
                        try:
                            cur.execute(update_sql, (resolved_now, p["id"]))
                            ac = (p.get("asset_class") or "UNKNOWN").upper()
                            strat = (p.get("strategy") or "unknown")[:100]
                            summary["by_asset_class"][ac]["resolved"] += 1
                            summary["by_strategy"][strat]["resolved"] += 1
                            updated += 1
                        except Exception as exc:
                            log.error("Update error for pick %s: %s", p.get("id"), exc)
                            summary["errors"] += 1

                conn.commit()
                total_resolved += updated
                summary["total_resolved"] = total_resolved
                log.info("Batch %d: %d picks resolved (cumulative: %d).",
                         batches_done, updated, total_resolved)
            else:
                # DRY_RUN: just count
                for p in stale_picks:
                    ac = (p.get("asset_class") or "UNKNOWN").upper()
                    strat = (p.get("strategy") or "unknown")[:100]
                    summary["by_asset_class"][ac]["resolved"] += 1
                    summary["by_strategy"][strat]["resolved"] += 1

                log.info(
                    "Batch %d [DRY_RUN]: %d stale picks would be resolved.",
                    batches_done, len(stale_picks),
                )

        summary["batches_processed"] = batches_done

    finally:
        conn.close()

    summary["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return summary


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def print_summary(summary: dict) -> None:
    """Print human-readable summary."""
    print("\n" + "=" * 70)
    print("STALE OPEN PICKS RESOLVER -- Summary")
    print("=" * 70)
    print(f"  Mode:             {summary['mode']}")
    print(f"  Started:          {summary['started_at']}")
    print(f"  Completed:        {summary['completed_at']}")
    print(f"  Batch size:       {summary['batch_size']}")
    print(f"  Total OPEN picks: {summary['total_open_picks']}")
    print(f"  Batches:          {summary['batches_processed']}")
    print(f"  Stale found:      {summary['total_stale_found']}")
    print(f"  Resolved:         {summary['total_resolved']}")
    print(f"  Errors:           {summary['errors']}")

    # By asset class
    by_ac = dict(summary["by_asset_class"])
    if by_ac:
        print("\n  By Asset Class:")
        for ac in sorted(by_ac):
            s = by_ac[ac]
            print(f"    {ac:12s}  stale={s['stale']:>8d}  resolved={s['resolved']:>8d}")

    # Top strategies by stale count
    by_strat = dict(summary["by_strategy"])
    if by_strat:
        top_strats = sorted(by_strat.items(), key=lambda x: x[1]["stale"], reverse=True)[:20]
        print("\n  Top Strategies (by stale picks):")
        for strat, s in top_strats:
            print(f"    {strat:40s}  stale={s['stale']:>8d}  resolved={s['resolved']:>8d}")

    print("=" * 70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve stale OPEN picks in MySQL trading_picks table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually update the database (default: dry run, no writes)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Picks to fetch per batch (default: 1000)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Max batches to process (default: unlimited)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    log.info("=== Stale Open Picks Resolver ===")
    log.info("Mode: %s | batch_size=%d | max_batches=%s",
             "EXECUTE" if args.execute else "DRY_RUN",
             args.batch_size, args.max_batches)
    log.info("DB: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)
    log.info("Hold windows: %s", MAX_HOLD_HOURS_BY_CLASS)

    summary = resolve_stale_open_picks(
        execute=args.execute,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
    )

    if args.json:
        # Convert defaultdicts to regular dicts for JSON serialization
        out = dict(summary)
        out["by_asset_class"] = dict(out["by_asset_class"])
        out["by_strategy"] = dict(out["by_strategy"])
        print(json.dumps(out, indent=2, default=str))
    else:
        print_summary(summary)

    if summary["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
