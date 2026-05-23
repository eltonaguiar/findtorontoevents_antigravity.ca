"""
Cross-DB Consistency Audit — compares strategy keys between ejaguiar1_stocks
and ejaguiar1_backtests to detect orphaned live picks (no backtest coverage)
and orphaned backtest strategies (no live picks).

Output: audit_dashboard/data/cross_db_audit.json

Environment variables: resolved via tools.db_env (supports all naming
conventions: DB_PASS_STOCKS, DB_PASS_BACKTESTS, MYSQL_PASSWORD, legacy names).
See tools/db_env.py for full priority chain.

Wire: called by .github/workflows/cross-db-audit.yml (daily 06:00 UTC).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

log = logging.getLogger(__name__)

# ── DB credential resolution (supports all naming conventions) ─────────────────
try:
    from tools.db_env import get_stocks_creds, get_backtests_creds as _get_backtests_creds
    _USE_DB_ENV = True
except ImportError:
    _USE_DB_ENV = False


def _connect(db_type: str) -> Any:
    """Connect to 'stocks' or 'backtests' DB via unified credential resolution."""
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed — pip install pymysql")

    if _USE_DB_ENV:
        if db_type == "stocks":
            creds = get_stocks_creds()
        elif db_type == "backtests":
            creds = _get_backtests_creds()
        else:
            raise ValueError(f"Unknown db_type: {db_type}")
        return pymysql.connect(**{k: creds[k] for k in
                                  ("host", "user", "password", "database", "port",
                                   "connect_timeout", "read_timeout")})

    # Fallback: legacy direct env lookup (used when tools.db_env unavailable)
    def _e(key: str, fallback: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, fallback)

    if db_type == "stocks":
        pw = _e("DB_PASS_STOCKS") or _e("MYSQL_PASSWORD") or _e("DB_STOCKS_PASSWORD")
        if not pw:
            raise RuntimeError(
                "No stocks DB password found — set DB_PASS_STOCKS or MYSQL_PASSWORD"
            )
        return pymysql.connect(
            host=_e("DB_HOST_STOCKS", _e("DB_STOCKS_HOST", "mysql.50webs.com")),
            user=_e("DB_USER_STOCKS", _e("DB_STOCKS_USER", "ejaguiar1_stocks")),
            password=pw,
            database=_e("DB_NAME_STOCKS", _e("DB_STOCKS_NAME", "ejaguiar1_stocks")),
            port=int(_e("DB_PORT_STOCKS", _e("DB_STOCKS_PORT", "3306"))),
            connect_timeout=20,
            read_timeout=30,
        )
    elif db_type == "backtests":
        pw = _e("DB_PASS_BACKTESTS") or _e("MYSQL_PASSWORD") or _e("DB_BACKTESTS_PASSWORD")
        if not pw:
            raise RuntimeError(
                "No backtests DB password found — set DB_PASS_BACKTESTS or MYSQL_PASSWORD"
            )
        return pymysql.connect(
            host=_e("DB_HOST_BACKTESTS", _e("DB_BACKTESTS_HOST", "mysql.50webs.com")),
            user=_e("DB_USER_BACKTESTS", _e("DB_BACKTESTS_USER", "ejaguiar1_backtests")),
            password=pw,
            database=_e("DB_NAME_BACKTESTS", _e("DB_BACKTESTS_NAME", "ejaguiar1_backtests")),
            port=int(_e("DB_PORT_BACKTESTS", _e("DB_BACKTESTS_PORT", "3306"))),
            connect_timeout=20,
            read_timeout=30,
        )
    else:
        raise ValueError(f"Unknown db_type: {db_type}")


def _fetch_strategies_stocks(conn: Any) -> Dict[str, int]:
    """Return {strategy_name: n_picks} from trading_picks."""
    result: Dict[str, int] = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT strategy, COUNT(*) FROM trading_picks "
                "GROUP BY strategy ORDER BY COUNT(*) DESC"
            )
            for row in cur.fetchall():
                if row[0]:
                    result[str(row[0])] = int(row[1])
    except Exception as exc:
        log.warning("strategies_stocks fetch error: %s", exc)
    return result


def _fetch_strategies_backtests(conn: Any) -> Dict[str, int]:
    """Return {strategy_name: n_trades} from bt_backtest_trades (or fallback table)."""
    result: Dict[str, int] = {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                "AND table_name IN ('bt_backtest_trades', 'backtest_trades', 'trades') "
                "LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                log.warning("No backtest table found in ejaguiar1_backtests")
                return result
            table = row[0]

            # Check strategy column exists
            cur.execute(f"SHOW COLUMNS FROM {table} LIKE 'strategy'")
            if not cur.fetchone():
                log.warning("No 'strategy' column in %s", table)
                return result

            cur.execute(
                f"SELECT strategy, COUNT(*) FROM {table} "
                f"GROUP BY strategy ORDER BY COUNT(*) DESC"
            )
            for row in cur.fetchall():
                if row[0]:
                    result[str(row[0])] = int(row[1])
    except Exception as exc:
        log.warning("strategies_backtests fetch error: %s", exc)
    return result


def run_cross_db_audit(output_path: Optional[str] = None) -> Dict[str, Any]:
    """Compare strategy keys across both DBs and write cross_db_audit.json."""
    if output_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(
            repo_root, "audit_dashboard", "data", "cross_db_audit.json"
        )

    stocks_strategies: Dict[str, int] = {}
    backtest_strategies: Dict[str, int] = {}
    errors: List[str] = []

    # ── Fetch from stocks DB ─────────────────────────────────────────────────
    try:
        conn = _connect("stocks")
        try:
            stocks_strategies = _fetch_strategies_stocks(conn)
        finally:
            conn.close()
    except RuntimeError as exc:
        errors.append(f"stocks: {exc}")
        log.error("Stocks connect error: %s", exc)

    # ── Fetch from backtests DB ──────────────────────────────────────────────
    try:
        conn = _connect("backtests")
        try:
            backtest_strategies = _fetch_strategies_backtests(conn)
        finally:
            conn.close()
    except RuntimeError as exc:
        errors.append(f"backtests: {exc}")
        log.error("Backtests connect error: %s", exc)

    # ── Consistency analysis ─────────────────────────────────────────────────
    live_set: Set[str] = set(stocks_strategies.keys())
    bt_set: Set[str] = set(backtest_strategies.keys())

    orphaned_live = sorted(live_set - bt_set)      # live but no backtest coverage
    orphaned_bt = sorted(bt_set - live_set)         # backtest coverage but no live picks
    matched = sorted(live_set & bt_set)             # both exist

    report = {
        "summary": {
            "n_live_strategies": len(live_set),
            "n_backtest_strategies": len(bt_set),
            "n_matched": len(matched),
            "n_orphaned_live": len(orphaned_live),
            "n_orphaned_backtest": len(orphaned_bt),
        },
        "matched": [
            {
                "strategy": s,
                "n_live_picks": stocks_strategies.get(s, 0),
                "n_backtest_trades": backtest_strategies.get(s, 0),
            }
            for s in matched
        ],
        "orphaned_live": [
            {"strategy": s, "n_live_picks": stocks_strategies.get(s, 0)}
            for s in orphaned_live
        ],
        "orphaned_backtest": [
            {"strategy": s, "n_backtest_trades": backtest_strategies.get(s, 0)}
            for s in orphaned_bt
        ],
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write report
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        log.info(
            "Cross-DB audit written: %s (matched=%d, orphaned_live=%d, orphaned_bt=%d)",
            output_path,
            len(matched),
            len(orphaned_live),
            len(orphaned_bt),
        )
    except Exception as exc:
        log.warning("Failed to write cross_db_audit.json: %s", exc)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = run_cross_db_audit()
    n_orphaned = report["summary"]["n_orphaned_live"]
    log.info("Cross-DB audit done. Orphaned live strategies: %d", n_orphaned)
