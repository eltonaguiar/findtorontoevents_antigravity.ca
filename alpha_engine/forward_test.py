#!/usr/bin/env python3
"""
Forward Test Entry Point (Layer 6)
====================================
Minimal forward-test harness entry point.

Background (wbkz389ek finding, 2026-06-01):
    The forensic audit (`sync_forward_test_picks.py` header line:
    "This fixes the broken Layer 6 pipeline") noted that the actual
    `forward_test.py` module the harness imports did NOT exist —
    Layer 6 picks were sourced from a sync table with no upstream
    generator. This module provides the missing entry point so the
    harness can call `run_forward_test()` and get a structured
    snapshot of currently-open picks within a horizon window.

This is intentionally minimal: it does NOT re-implement forward
testing logic. It queries `trading_picks` for OPEN picks inside the
window and returns counts + a sample. Resolution/scoring stays in
the existing resolver pipeline.

Usage:
    python -m alpha_engine.forward_test
    python -m alpha_engine.forward_test --strategy claude_gainer_st --horizon 30
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

try:
    import pymysql
except ImportError:  # pragma: no cover
    pymysql = None  # type: ignore

# Optional re-export so harness callers can also reach the sync helper.
try:
    from alpha_engine import sync_forward_test_picks  # noqa: F401
except Exception:  # pragma: no cover
    sync_forward_test_picks = None  # type: ignore


DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_NAME = "ejaguiar1_stocks"
DBPASSES_PATH = Path("/home/eaguiar2015/dbpasses.txt")


def _resolve_password() -> Optional[str]:
    """Resolve DB password from env first, then dbpasses.txt convention."""
    env_pw = os.environ.get("DB_PASS_STOCKS")
    if env_pw:
        return env_pw
    # Convention per /reference-db-password-convention: <name>1234560
    # Confirmed by /home/eaguiar2015/dbpasses.txt: <gitignored convention>
    if DBPASSES_PATH.exists():
        try:
            text = DBPASSES_PATH.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("stocks") and len(line) == 13 and line.endswith("0"):  # convention shape, not literal
                    return line
        except Exception:
            pass
    return os.environ.get("DB_PASS_STOCKS", "")  # 2026-06-04 INCIDENT #89 scrub: was literal fallback


def run_forward_test(
    strategy_id: Optional[str] = None,
    horizon_days: int = 30,
) -> dict:
    """Snapshot open picks for a forward-test horizon window.

    Args:
        strategy_id: Optional source_system filter. If None, all strategies.
        horizon_days: Look back this many days from NOW().

    Returns:
        dict with keys: strategy_id, horizon_days, open_count,
        resolved_count, open_picks (up to 50 sample rows), error (optional).
    """
    result: dict = {
        "strategy_id": strategy_id,
        "horizon_days": horizon_days,
        "open_count": 0,
        "resolved_count": 0,
        "open_picks": [],
    }

    if pymysql is None:
        result["error"] = "pymysql not installed"
        return result

    pw = _resolve_password()
    if not pw:
        result["error"] = "no DB password resolved"
        return result

    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=pw,
            database=DB_NAME,
            connect_timeout=10,
            read_timeout=20,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception as e:
        result["error"] = f"connect failed: {e!s}"
        return result

    try:
        with conn.cursor() as cur:
            # Open count
            where = ["status = 'OPEN'", "created_at >= NOW() - INTERVAL %s DAY"]
            params: list = [int(horizon_days)]
            if strategy_id:
                where.append("source_system = %s")
                params.append(strategy_id)
            where_sql = " AND ".join(where)

            cur.execute(
                f"SELECT COUNT(*) AS c FROM trading_picks WHERE {where_sql}",
                params,
            )
            row = cur.fetchone() or {}
            result["open_count"] = int(row.get("c", 0))

            # Resolved (non-OPEN) count in same window
            res_where = ["status <> 'OPEN'", "created_at >= NOW() - INTERVAL %s DAY"]
            res_params: list = [int(horizon_days)]
            if strategy_id:
                res_where.append("source_system = %s")
                res_params.append(strategy_id)
            cur.execute(
                "SELECT COUNT(*) AS c FROM trading_picks WHERE "
                + " AND ".join(res_where),
                res_params,
            )
            row = cur.fetchone() or {}
            result["resolved_count"] = int(row.get("c", 0))

            # Sample of open picks
            cur.execute(
                f"""
                SELECT id, symbol, source_system, category, status,
                       direction, created_at, entry_price, take_profit, stop_loss
                FROM trading_picks
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT 50
                """,
                params,
            )
            rows = cur.fetchall() or []
            for r in rows:
                # Stringify datetimes for JSON safety
                if r.get("created_at") is not None:
                    r["created_at"] = str(r["created_at"])
            result["open_picks"] = list(rows)
    except Exception as e:
        result["error"] = f"query failed: {e!s}"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return result


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Layer 6 forward-test snapshot")
    p.add_argument("--strategy", "--strategy-id", dest="strategy_id", default=None)
    p.add_argument("--horizon", "--horizon-days", dest="horizon_days",
                   type=int, default=30)
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv)
    out = run_forward_test(
        strategy_id=args.strategy_id,
        horizon_days=args.horizon_days,
    )
    print(json.dumps(out, indent=2, default=str))
    return 0 if "error" not in out else 1


if __name__ == "__main__":
    sys.exit(main())
