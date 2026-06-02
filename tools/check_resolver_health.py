#!/usr/bin/env python3
"""
tools/check_resolver_health.py — Check resolver health and open pick bloat
============================================================================

Checks the MySQL trading_picks table for:
- Total OPEN picks count
- Stale OPEN picks by asset class (beyond MAX_HOLD_HOURS thresholds)
- Last resolver run timestamp (from universal_resolved_picks.json)
- Alert if OPEN count exceeds 1M threshold

Outputs a JSON health report suitable for CI pipelines, dashboards, or
heartbeat monitoring.

Usage
-----
    python tools/check_resolver_health.py
    python tools/check_resolver_health.py --json
    python tools/check_resolver_health.py --threshold 500000

Environment variables
---------------------
  AUDIT_DB_HOST    (default: mysql.50webs.com)
  AUDIT_DB_PORT    (default: 3306)
  AUDIT_DB_USER    (default: ejaguiar1_stocks)
  AUDIT_DB_PASS    (also checked as DB_PASS_STOCKS, MYSQL_PASSWORD)
  AUDIT_DB_NAME    (default: ejaguiar1_stocks)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("resolver_health")

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
    or ""
)
DB_NAME = os.getenv("AUDIT_DB_NAME", os.getenv("DB_NAME", "ejaguiar1_stocks"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALERT_THRESHOLD_DEFAULT = 1_000_000  # Alert if OPEN picks > 1M

MAX_HOLD_HOURS_BY_CLASS: dict[str, int] = {
    "CRYPTO": 48,
    "EQUITY": 96,
    "ETF": 96,
    "COMMODITY": 96,
    "FUTURES": 96,
    "FOREX": 72,  # EAGLE2 2026-06-02: unified to 72h (was 120)
    "BOND": 120,
}

# Path to universal_resolved_picks.json for last-run timestamp
try:
    ROOT = Path(__file__).resolve().parent.parent
except NameError:
    ROOT = Path.cwd()
RESOLVED_FILE = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"

# ---------------------------------------------------------------------------
# Dependencies
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
        log.error("No DB password -- set AUDIT_DB_PASS, DB_PASS_STOCKS, or MYSQL_PASSWORD")
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
# Health checks
# ---------------------------------------------------------------------------

def check_open_picks_count(conn) -> dict:
    """Count total OPEN picks and compare against alert threshold."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM trading_picks WHERE status = 'OPEN'")
        row = cur.fetchone()
        total = int(row["cnt"]) if row else 0

    return {
        "check": "open_picks_count",
        "value": total,
        "alert_threshold": ALERT_THRESHOLD_DEFAULT,
        "status": "RED" if total > ALERT_THRESHOLD_DEFAULT else "GREEN",
        "message": f"{total:,} OPEN picks" + (f" (EXCEEDS {ALERT_THRESHOLD_DEFAULT:,} threshold)" if total > ALERT_THRESHOLD_DEFAULT else ""),
    }


def check_stale_by_category(conn) -> dict:
    """Count stale OPEN picks by category (trading_picks uses 'category' not 'asset_class')."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT category, COUNT(*) AS cnt, MIN(created_at) AS oldest, "
            "MAX(created_at) AS newest "
            "FROM trading_picks "
            "WHERE status = 'OPEN' "
            "GROUP BY category"
        )
        rows = cur.fetchall()

    now_utc = datetime.now(timezone.utc)
    stale_by_class: dict[str, dict] = {}
    total_stale = 0

    for row in rows:
        raw = row.get("category") or "UNKNOWN"
        ac = str(raw).upper() if raw else "UNKNOWN"
        cnt = int(row["cnt"])
        oldest = row.get("oldest")
        newest = row.get("newest")

        max_hours = MAX_HOLD_HOURS_BY_CLASS.get(ac, 48)
        stale_by_class[str(raw)] = {
            "total_open": cnt,
            "estimated_stale": cnt,
            "max_hold_hours": max_hours,
            "oldest_pick": str(oldest) if oldest else None,
            "newest_pick": str(newest) if newest else None,
        }
        total_stale += cnt

    return {
        "check": "stale_by_category",
        "total_stale_estimate": total_stale,
        "by_class": stale_by_class,
        "status": "RED" if total_stale > ALERT_THRESHOLD_DEFAULT else "YELLOW" if total_stale > 0 else "GREEN",
    }


def check_last_resolver_run() -> dict:
    """Check when the universal resolver last ran."""
    last_resolved_at = None
    resolved_file_exists = RESOLVED_FILE.exists()
    resolved_file_mod = None

    if resolved_file_exists:
        mtime = RESOLVED_FILE.stat().st_mtime
        resolved_file_mod = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Try to read last entry's resolved_at from the file
        try:
            data = json.loads(RESOLVED_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                # Check last few entries
                for entry in reversed(data[-100:]):
                    if isinstance(entry, dict) and entry.get("resolved_at"):
                        last_resolved_at = entry["resolved_at"]
                        break
        except Exception:
            pass

    now_utc = datetime.now(timezone.utc)
    hours_since_file = None
    if resolved_file_mod:
        try:
            file_dt = datetime.strptime(resolved_file_mod, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            hours_since_file = (now_utc - file_dt).total_seconds() / 3600.0
        except ValueError:
            pass

    hours_since_resolve = None
    if last_resolved_at:
        try:
            resolve_dt = datetime.strptime(str(last_resolved_at)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            hours_since_resolve = (now_utc - resolve_dt).total_seconds() / 3600.0
        except ValueError:
            pass

    status = "GREEN"
    message = "Resolver appears active"
    if hours_since_file is not None and hours_since_file > 48:
        status = "RED"
        message = f"Resolver file not updated in {hours_since_file:.0f}h"
    elif not resolved_file_exists:
        status = "RED"
        message = "Resolved picks file does not exist"
    elif hours_since_resolve is not None and hours_since_resolve > 72:
        status = "YELLOW"
        message = f"Last resolved pick from {hours_since_resolve:.0f}h ago"

    return {
        "check": "last_resolver_run",
        "resolved_file_exists": resolved_file_exists,
        "resolved_file_modified": resolved_file_mod,
        "last_pick_resolved_at": last_resolved_at,
        "hours_since_file_update": round(hours_since_file, 1) if hours_since_file else None,
        "hours_since_last_resolve": round(hours_since_resolve, 1) if hours_since_resolve else None,
        "status": status,
        "message": message,
    }


def check_db_connectivity() -> dict:
    """Verify DB connection works."""
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            row = cur.fetchone()
        conn.close()
        return {
            "check": "db_connectivity",
            "status": "GREEN",
            "message": f"Connected to {DB_HOST}/{DB_NAME}",
        }
    except Exception as exc:
        return {
            "check": "db_connectivity",
            "status": "RED",
            "message": f"Connection failed: {exc}",
        }


# ---------------------------------------------------------------------------
# Main health report
# ---------------------------------------------------------------------------

def run_health_check(alert_threshold: int = ALERT_THRESHOLD_DEFAULT) -> dict[str, Any]:
    """Run all health checks and return a composite report."""
    global ALERT_THRESHOLD_DEFAULT
    ALERT_THRESHOLD_DEFAULT = alert_threshold

    now_utc = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "generated_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": DB_HOST,
        "database": DB_NAME,
        "alert_threshold": alert_threshold,
        "checks": {},
        "overall": {
            "status": "GREEN",
            "checks_run": 0,
            "checks_red": 0,
            "checks_yellow": 0,
            "alerts": [],
        },
    }

    # DB connectivity
    db_check = check_db_connectivity()
    report["checks"]["db_connectivity"] = db_check

    if db_check["status"] != "GREEN":
        report["overall"]["status"] = "RED"
        report["overall"]["checks_red"] += 1
        report["overall"]["alerts"].append(db_check["message"])
        report["overall"]["checks_run"] += 1
        return report  # Can't run other checks without DB

    # Open picks count
    conn = _connect()
    try:
        count_check = check_open_picks_count(conn)
        report["checks"]["open_picks_count"] = count_check

        stale_check = check_stale_by_category(conn)
        report["checks"]["stale_by_category"] = stale_check

        tag_check = {"check": "forward_test_tag_awareness", "status": "GREEN"}
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN COALESCE(forward_test_only, 0) = 1 THEN 1 ELSE 0 END) AS ft_only_count,
                        SUM(CASE WHEN COALESCE(_gated_forward_test_isolated, 0) = 1 THEN 1 ELSE 0 END) AS gated_isolated
                    FROM at_pick_outcomes
                """)
                row = cur.fetchone() or {}
                if isinstance(row, dict):
                    total = int(row.get("total") or 0)
                    ft_only = int(row.get("ft_only_count") or 0)
                    gated = int(row.get("gated_isolated") or 0)
                else:
                    total = int(row[0] or 0)
                    ft_only = int(row[1] or 0)
                    gated = int(row[2] or 0)
                tag_check.update({
                    "total_outcomes": total,
                    "forward_test_only_count": ft_only,
                    "gated_isolated_count": gated,
                    "writer_alignment": "both universal + alpha now skip forward_test_only cohort (2026-06-01)",
                })
        except Exception as exc:
            tag_check.update({
                "status": "YELLOW",
                "error": str(exc)[:180],
                "note": "Run tools/ensure_forward_test_outcome_columns.py --execute if columns missing.",
            })
        report["checks"]["forward_test_tag_awareness"] = tag_check
        if tag_check.get("status") == "YELLOW":
            report["overall"]["checks_yellow"] += 1
    finally:
        conn.close()

    resolver_check = check_last_resolver_run()
    report["checks"]["last_resolver_run"] = resolver_check

    # Overall status
    report["overall"]["checks_run"] = len(report["checks"])
    for name, check in report["checks"].items():
        status = check.get("status", "UNKNOWN")
        if status == "RED":
            report["overall"]["checks_red"] += 1
            report["overall"]["alerts"].append(f"{name}: {check.get('message', '')}")
        elif status == "YELLOW":
            report["overall"]["checks_yellow"] += 1

    if report["overall"]["checks_red"] > 0:
        report["overall"]["status"] = "RED"
    elif report["overall"]["checks_yellow"] > 0:
        report["overall"]["status"] = "YELLOW"
    else:
        report["overall"]["status"] = "GREEN"

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check resolver health and open pick bloat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=ALERT_THRESHOLD_DEFAULT,
        help=f"Alert threshold for OPEN picks (default: {ALERT_THRESHOLD_DEFAULT:,})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output JSON, no log lines",
    )
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    log.info("=== Resolver Health Check ===")
    log.info("Alert threshold: %s", f"{args.threshold:,}")

    report = run_health_check(alert_threshold=args.threshold)

    # Print JSON
    print(json.dumps(report, indent=2, default=str))

    # Exit code
    if report["overall"]["status"] == "RED":
        sys.exit(2)
    elif report["overall"]["status"] == "YELLOW":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
