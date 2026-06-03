#!/usr/bin/env python3
"""
tools/resolve_stale_open_picks.py — Batch-resolve stale live picks in MySQL
=============================================================================

Connects to the ejaguiar1_stocks MySQL database, finds OPEN and ACTIVE picks
whose age exceeds the per-category MAX_HOLD_HOURS threshold, and batch-resolves
them as TIME_EXIT with flat PnL.

Hold windows match audit_trail/universal_pick_resolver.py:
  CRYPTO            48h
  EQUITY / ETF / COMMODITY / FUTURES   96h
  FOREX / BOND     120h

Usage
-----
    # Preview only (default) — ALWAYS use --max-batches for dry-run; full scan
    # over 3k+ live picks can run for hours on remote MySQL.
    python tools/resolve_stale_open_picks.py --batch-size 500 --max-batches 10

    # Execute updates (daily hygiene uses --max-batches 30)
    python tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 30

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
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.pick_hold_windows import LIVE_PICK_STATUSES, is_past_max_hold

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
        for i, line in enumerate(lines):
            if line.strip() == "ejaguiar1_stocks" and i + 1 < len(lines):
                return lines[i + 1].strip()
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

_LIVE_STATUS_SQL = ", ".join("'%s'" % s for s in LIVE_PICK_STATUSES)

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


# ---------------------------------------------------------------------------
# Core resolution logic
# ---------------------------------------------------------------------------

def count_live_picks(conn) -> int:
    """Return total OPEN + ACTIVE picks count."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM trading_picks "
            f"WHERE status IN ({_LIVE_STATUS_SQL})"
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0


def find_live_picks_batch(
    conn, batch_size: int, offset: int = 0
) -> list[dict[str, Any]]:
    """Fetch live picks (OPEN or ACTIVE) oldest-first with OFFSET pagination."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, symbol, category, strategy, direction, status, "
            "entry_price, take_profit, stop_loss, created_at "
            f"FROM trading_picks WHERE status IN ({_LIVE_STATUS_SQL}) "
            "ORDER BY created_at ASC LIMIT %s OFFSET %s",
            (batch_size, offset),
        )
        return cur.fetchall()


def is_stale(pick: dict) -> bool:
    """Check if a pick is past its category max-hold window."""
    return is_past_max_hold(pick)


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
    Find and batch-resolve stale OPEN/ACTIVE picks.

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
        "total_live_picks": 0,
        "total_open_picks": 0,  # alias for dashboards expecting this key
        "by_status": defaultdict(lambda: {"stale": 0, "resolved": 0}),
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
        summary["total_live_picks"] = count_live_picks(conn)
        summary["total_open_picks"] = summary["total_live_picks"]
        log.info(
            "Total live picks (OPEN+ACTIVE): %d  statuses=%s",
            summary["total_live_picks"],
            LIVE_PICK_STATUSES,
        )

        if summary["total_live_picks"] == 0:
            log.info("No OPEN/ACTIVE picks -- nothing to resolve.")
            summary["completed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            return summary

        batches_done = 0
        scan_offset = 0  # paginate through full live set (fix: don't stop at oldest 500 only)

        while True:
            picks = find_live_picks_batch(conn, batch_size, scan_offset)
            if not picks:
                log.info("No more OPEN/ACTIVE picks to check (offset=%d).", scan_offset)
                break

            batches_done += 1
            if max_batches and batches_done > max_batches:
                log.info("Max batches limit reached (%d).", max_batches)
                break

            stale_picks = [p for p in picks if is_stale(p)]
            summary["total_stale_found"] += len(stale_picks)

            # Accumulate stats by asset class and strategy
            for p in stale_picks:
                ac = (p.get("category") or "UNKNOWN").upper()
                strat = (p.get("strategy") or "unknown")[:100]
                st = (p.get("status") or "UNKNOWN").upper()
                summary["by_asset_class"][ac]["stale"] += 1
                summary["by_strategy"][strat]["stale"] += 1
                summary["by_status"][st]["stale"] += 1

            if not stale_picks:
                scan_offset += len(picks)
                if scan_offset >= summary["total_live_picks"]:
                    log.info(
                        "Full live set scanned (%d picks); 0 stale in final window.",
                        summary["total_live_picks"],
                    )
                    break
                log.info(
                    "Batch %d: %d live picks checked, 0 stale (offset now %d / %d).",
                    batches_done,
                    len(picks),
                    scan_offset,
                    summary["total_live_picks"],
                )
                continue

            log.info(
                "Batch %d: %d live picks, %d stale (>%d categories).",
                batches_done, len(picks), len(stale_picks),
                len({(p.get("category") or "UNKNOWN").upper() for p in stale_picks}),
            )

            if execute:
                # Bulk update using WHERE id IN (...). Chunk into groups of 1000
                # to avoid oversized queries over slow network connections.
                all_ids = [p["id"] for p in stale_picks]
                chunk_size = 1000
                total_updated = 0

                with conn.cursor() as cur:
                    for i in range(0, len(all_ids), chunk_size):
                        chunk = all_ids[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        bulk_sql = (
                            "UPDATE trading_picks SET "
                            "status='TIME_EXIT', "
                            "exit_reason='TIME_EXIT_MAX_HOLD', "
                            "exit_price=entry_price, pnl_pct=0.0 "
                            f"WHERE id IN ({placeholders})"
                        )
                        cur.execute(bulk_sql, chunk)
                        total_updated += cur.rowcount

                conn.commit()
                summary["total_resolved"] += total_updated
                # Also set by_asset_class/by_strategy resolved counts
                for p in stale_picks:
                    ac = (p.get("category") or "UNKNOWN").upper()
                    strat = (p.get("strategy") or "unknown")[:100]
                    st = (p.get("status") or "UNKNOWN").upper()
                    summary["by_asset_class"][ac]["resolved"] += 1
                    summary["by_strategy"][strat]["resolved"] += 1
                    summary["by_status"][st]["resolved"] += 1

                log.info(
                    "Batch %d: %d picks resolved via bulk update (cumulative: %d).",
                    batches_done, total_updated, summary["total_resolved"],
                )
                # Re-scan from oldest after removals (counts/shape changed).
                scan_offset = 0
            else:
                # DRY_RUN: just count
                for p in stale_picks:
                    ac = (p.get("category") or "UNKNOWN").upper()
                    strat = (p.get("strategy") or "unknown")[:100]
                    st = (p.get("status") or "UNKNOWN").upper()
                    summary["by_asset_class"][ac]["resolved"] += 1
                    summary["by_strategy"][strat]["resolved"] += 1
                    summary["by_status"][st]["resolved"] += 1

                log.info(
                    "Batch %d [DRY_RUN]: %d stale picks would be resolved.",
                    batches_done, len(stale_picks),
                )
                scan_offset = 0

        summary["batches_processed"] = batches_done
        summary["scan_offset_final"] = scan_offset

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
    print("STALE LIVE PICKS RESOLVER (OPEN+ACTIVE) -- Summary")
    print("=" * 70)
    print(f"  Mode:             {summary['mode']}")
    print(f"  Started:          {summary['started_at']}")
    print(f"  Completed:        {summary['completed_at']}")
    print(f"  Batch size:       {summary['batch_size']}")
    print(f"  Total live picks: {summary.get('total_live_picks', summary['total_open_picks'])}")
    print(f"  Batches:          {summary['batches_processed']}")
    print(f"  Stale found:      {summary['total_stale_found']}")
    print(f"  Resolved:         {summary['total_resolved']}")
    print(f"  Errors:           {summary['errors']}")

    by_st = dict(summary.get("by_status") or {})
    if by_st:
        print("\n  By Status:")
        for st in sorted(by_st):
            s = by_st[st]
            print(f"    {st:12s}  stale={s['stale']:>8d}  resolved={s['resolved']:>8d}")

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
        description="Resolve stale OPEN/ACTIVE picks in MySQL trading_picks table",
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

    log.info("=== Stale Live Picks Resolver (OPEN+ACTIVE) ===")
    log.info("Mode: %s | batch_size=%d | max_batches=%s",
             "EXECUTE" if args.execute else "DRY_RUN",
             args.batch_size, args.max_batches)
    log.info("DB: %s@%s:%s/%s", DB_USER, DB_HOST, DB_PORT, DB_NAME)
    log.info("Hold windows module: tools.pick_hold_windows")

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
        out["by_status"] = dict(out.get("by_status") or {})
        print(json.dumps(out, indent=2, default=str))
    else:
        print_summary(summary)

    if summary["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
