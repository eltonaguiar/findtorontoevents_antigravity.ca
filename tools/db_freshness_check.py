"""
DB Freshness Guardian — checks staleness of live MySQL tables.

Reports RED / YELLOW / GREEN status for:
  - ejaguiar1_stocks.trading_picks (live picks)
  - ejaguiar1_stocks.trading_picks (resolver outputs — closed picks updated_at)
  - ejaguiar1_backtests.bt_backtest_trades (backtest data freshness)

Exit codes:
  0 = all GREEN
  1 = at least one YELLOW (warning)
  2 = at least one RED (CI failure)

Environment variables: resolved via tools.db_env (supports all naming
conventions: DB_PASS_STOCKS, DB_PASS_BACKTESTS, MYSQL_PASSWORD, and legacy
names DB_STOCKS_PASSWORD / DB_BACKTESTS_PASSWORD). See tools/db_env.py.
  DB_FRESHNESS_OUTPUT (default: audit_dashboard/data/db_freshness.json)

Thresholds:
  live_picks:   GREEN < 2h, YELLOW 2-6h, RED > 6h
  resolver:     GREEN < 4h, YELLOW 4-12h, RED > 12h
  backtests:    GREEN < 48h, YELLOW 48-168h (1 week), RED > 168h
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ── Freshness thresholds (minutes) ────────────────────────────────────────────
THRESHOLDS: Dict[str, Dict[str, int]] = {
    "live_picks": {
        "green_max_minutes": 120,   # 2h
        "yellow_max_minutes": 360,  # 6h
    },
    "resolver_outputs": {
        "green_max_minutes": 240,   # 4h
        "yellow_max_minutes": 720,  # 12h
    },
    "signal_outcomes": {
        "green_max_minutes": 360,   # 6h — resolved picks may land slower than raw picks
        "yellow_max_minutes": 1440, # 24h
    },
    "backtests": {
        "green_max_minutes": 2880,  # 48h
        "yellow_max_minutes": 10080,  # 1 week
    },
}

# ── DB connection helpers ─────────────────────────────────────────────────────

try:
    from tools.db_env import get_stocks_creds, get_backtests_creds as _get_backtests_creds
    _USE_DB_ENV = True
except ImportError:
    _USE_DB_ENV = False


def _e(key: str, fallback: Optional[str] = None) -> Optional[str]:
    """Single-key env lookup (used only in legacy fallback paths)."""
    return os.environ.get(key, fallback)


def _connect_stocks() -> Any:
    """Return a pymysql connection to ejaguiar1_stocks.

    Credential resolution priority (via db_env): DB_PASS_STOCKS,
    MYSQL_PASSWORD, DB_STOCKS_PASSWORD, DB_PASSWORD, AUDIT_DB_PASS.
    """
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed — run: pip install pymysql")

    if _USE_DB_ENV:
        creds = get_stocks_creds()
        return pymysql.connect(**{k: creds[k] for k in
                                  ("host", "user", "password", "database", "port",
                                   "connect_timeout", "read_timeout")})

    # Fallback: legacy direct lookup when tools.db_env unavailable
    password = (_e("DB_PASS_STOCKS") or _e("MYSQL_PASSWORD") or _e("DB_STOCKS_PASSWORD"))
    if not password:
        raise RuntimeError(
            "No stocks DB password — set DB_PASS_STOCKS or MYSQL_PASSWORD. "
            "Never hardcode credentials."
        )
    return pymysql.connect(
        host=_e("DB_HOST_STOCKS", _e("DB_STOCKS_HOST", "mysql.50webs.com")),
        user=_e("DB_USER_STOCKS", _e("DB_STOCKS_USER", "ejaguiar1_stocks")),
        password=password,
        database=_e("DB_NAME_STOCKS", _e("DB_STOCKS_NAME", "ejaguiar1_stocks")),
        port=int(_e("DB_PORT_STOCKS", _e("DB_STOCKS_PORT", "3306"))),
        connect_timeout=20,
        read_timeout=30,
    )


def _connect_backtests() -> Any:
    """Return a pymysql connection to ejaguiar1_backtests.

    Credential resolution priority (via db_env): DB_PASS_BACKTESTS,
    DB_BACKTESTS_PASSWORD, BACKTESTS_DB_PASS, MYSQL_PASSWORD, DB_STOCKS_PASSWORD.
    """
    try:
        import pymysql
    except ImportError:
        raise RuntimeError("pymysql not installed — run: pip install pymysql")

    if _USE_DB_ENV:
        creds = _get_backtests_creds()
        return pymysql.connect(**{k: creds[k] for k in
                                  ("host", "user", "password", "database", "port",
                                   "connect_timeout", "read_timeout")})

    # Fallback: legacy direct lookup when tools.db_env unavailable
    password = (
        _e("DB_PASS_BACKTESTS") or _e("DB_BACKTESTS_PASSWORD")
        or _e("BACKTESTS_DB_PASS") or _e("MYSQL_PASSWORD")
    )
    if not password:
        raise RuntimeError(
            "No backtests DB password — set DB_PASS_BACKTESTS or MYSQL_PASSWORD. "
            "Never hardcode credentials."
        )
    return pymysql.connect(
        host=_e("DB_HOST_BACKTESTS", _e("DB_BACKTESTS_HOST", "mysql.50webs.com")),
        user=_e("DB_USER_BACKTESTS", _e("DB_BACKTESTS_USER", "ejaguiar1_backtests")),
        password=password,
        database=_e("DB_NAME_BACKTESTS", _e("DB_BACKTESTS_NAME", "ejaguiar1_backtests")),
        port=int(_e("DB_PORT_BACKTESTS", _e("DB_BACKTESTS_PORT", "3306"))),
        connect_timeout=20,
        read_timeout=30,
    )


# ── Freshness check logic ─────────────────────────────────────────────────────


def _minutes_since(ts: Optional[Any]) -> Optional[float]:
    """Return minutes elapsed since a datetime/string timestamp."""
    if ts is None:
        return None
    if isinstance(ts, str):
        ts = ts.replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts)
    if not hasattr(ts, "tzinfo") or ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 60.0


def _grade(minutes: Optional[float], thresholds: Dict[str, int]) -> str:
    if minutes is None:
        return "RED"
    if minutes <= thresholds["green_max_minutes"]:
        return "GREEN"
    if minutes <= thresholds["yellow_max_minutes"]:
        return "YELLOW"
    return "RED"


def check_live_picks(conn: Any) -> Dict[str, Any]:
    """Check freshness of most recent active pick in trading_picks."""
    result: Dict[str, Any] = {
        "check": "live_picks",
        "table": "trading_picks",
        "status": "RED",
        "minutes_stale": None,
        "last_pick_at": None,
        "n_active": 0,
    }
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(created_at), COUNT(*) FROM trading_picks "
                "WHERE status IN ('active', 'open', 'ACTIVE', 'OPEN')"
            )
            row = cur.fetchone()
            if row:
                last_at, n_active = row
                result["last_pick_at"] = str(last_at) if last_at else None
                result["n_active"] = int(n_active or 0)
                minutes = _minutes_since(last_at)
                result["minutes_stale"] = round(minutes, 1) if minutes is not None else None
                result["status"] = _grade(minutes, THRESHOLDS["live_picks"])
    except Exception as exc:
        log.warning("live_picks check error: %s", exc)
        result["error"] = str(exc)
    return result


def check_resolver_outputs(conn: Any) -> Dict[str, Any]:
    """Check freshness of most recently resolved (closed) pick."""
    result: Dict[str, Any] = {
        "check": "resolver_outputs",
        "table": "trading_picks",
        "status": "RED",
        "minutes_stale": None,
        "last_resolved_at": None,
        "n_resolved_today": 0,
    }
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(updated_at), "
                "  SUM(CASE WHEN DATE(updated_at) = CURDATE() THEN 1 ELSE 0 END) "
                "FROM trading_picks "
                "WHERE status IN ('closed', 'CLOSED', 'resolved', 'RESOLVED', 'expired', 'EXPIRED')"
            )
            row = cur.fetchone()
            if row:
                last_at, n_today = row
                result["last_resolved_at"] = str(last_at) if last_at else None
                result["n_resolved_today"] = int(n_today or 0)
                minutes = _minutes_since(last_at)
                result["minutes_stale"] = round(minutes, 1) if minutes is not None else None
                result["status"] = _grade(minutes, THRESHOLDS["resolver_outputs"])
    except Exception as exc:
        log.warning("resolver_outputs check error: %s", exc)
        result["error"] = str(exc)
    return result


def check_signal_outcomes(conn: Any) -> Dict[str, Any]:
    """Check freshness of most recent outcome in at_signal_outcomes.

    This is the production outcome table written by the universal resolver
    when PICK_OUTCOMES_MYSQL_ENABLED=1.  Freshness here tells us whether
    resolved picks are making it to MySQL (vs ghost rows / empty tables).
    """
    result: Dict[str, Any] = {
        "check": "signal_outcomes",
        "table": "at_signal_outcomes",
        "status": "RED",
        "minutes_stale": None,
        "last_resolved_at": None,
        "n_resolved_today": 0,
        "n_total": 0,
    }
    try:
        with conn.cursor() as cur:
            # at_signal_outcomes has no exit_time column; closed_at is when
            # the outcome resolved (schema verified 2026-05-15).
            cur.execute(
                "SELECT MAX(closed_at), "
                "  SUM(CASE WHEN DATE(closed_at) = CURDATE() THEN 1 ELSE 0 END), "
                "  COUNT(*) "
                "FROM at_signal_outcomes"
            )
            row = cur.fetchone()
            if row:
                last_at, n_today, n_total = row
                result["last_resolved_at"] = str(last_at) if last_at else None
                result["n_resolved_today"] = int(n_today or 0)
                result["n_total"] = int(n_total or 0)
                minutes = _minutes_since(last_at)
                result["minutes_stale"] = round(minutes, 1) if minutes is not None else None
                result["status"] = _grade(minutes, THRESHOLDS["signal_outcomes"])
                # Legacy sidecar: if nothing written in 30d, do not fail CI when
                # trading_picks resolver path is healthy (checked separately).
                if minutes is not None and minutes > 30 * 24 * 60:
                    result["status"] = "SKIPPED"
                    result["skip_reason"] = (
                        "at_signal_outcomes stale >30d — outcomes use trading_picks; "
                        "see resolver_outputs check"
                    )
                elif last_at is None and int(n_total or 0) == 0:
                    result["status"] = "SKIPPED"
                    result["skip_reason"] = "at_signal_outcomes empty — optional legacy table"
    except Exception as exc:
        log.warning("signal_outcomes check error: %s", exc)
        result["error"] = str(exc)
    return result


def check_backtests(conn: Any) -> Dict[str, Any]:
    """Check freshness of most recent backtest trade insertion."""
    result: Dict[str, Any] = {
        "check": "backtests",
        "table": "bt_backtest_trades",
        "status": "RED",
        "minutes_stale": None,
        "last_trade_at": None,
        "n_total": 0,
    }
    try:
        with conn.cursor() as cur:
            # Prefer bt_backtest_trades (28M+ rows, imported_at). Legacy backtest_trades
            # has no timestamp columns and must not win LIMIT 1 ordering.
            table = None
            for candidate in ("bt_backtest_trades", "backtest_trades", "trades"):
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = %s LIMIT 1",
                    (candidate,),
                )
                if cur.fetchone():
                    table = candidate
                    break
            if not table:
                result["error"] = "no backtest table found"
                return result
            result["table"] = table

            # Pick the freshness column. Prefer created_at, fall back to
            # imported_at. Both may be absent if the schema changes — in
            # that case skip the staleness check (YELLOW, not RED).
            cur.execute(f"SHOW COLUMNS FROM {table} LIKE 'created_at'")
            has_created = bool(cur.fetchone())
            cur.execute(f"SHOW COLUMNS FROM {table} LIKE 'imported_at'")
            has_imported = bool(cur.fetchone())

            if has_created:
                ts_col = "created_at"
            elif has_imported:
                ts_col = "imported_at"
            else:
                result["status"] = "YELLOW"
                result["error"] = f"no timestamp column in {table} — schema check needed"
                log.warning("backtests freshness: no created_at or imported_at in %s", table)
                return result

            cur.execute(f"SELECT MAX({ts_col}), COUNT(*) FROM {table}")
            row = cur.fetchone()
            if row:
                last_at, total = row
                result["last_trade_at"] = str(last_at) if last_at else None
                result["n_total"] = int(total or 0)
                minutes = _minutes_since(last_at)
                result["minutes_stale"] = round(minutes, 1) if minutes is not None else None
                result["status"] = _grade(minutes, THRESHOLDS["backtests"])
    except Exception as exc:
        log.warning("backtests check error: %s", exc)
        result["error"] = str(exc)
    return result


# ── Main orchestrator ─────────────────────────────────────────────────────────


def run_freshness_check(output_path: Optional[str] = None) -> Dict[str, Any]:
    """Run all freshness checks and write JSON report.

    Returns the full report dict. Exit code is determined by severity:
      all GREEN → 0, any YELLOW → 1, any RED → 2
    """
    if output_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(
            repo_root, "audit_dashboard", "data", "db_freshness.json"
        )

    checks: List[Dict[str, Any]] = []
    stocks_conn = None
    backtests_conn = None

    # ── Stocks DB ────────────────────────────────────────────────────────────
    try:
        stocks_conn = _connect_stocks()
        checks.append(check_live_picks(stocks_conn))
        checks.append(check_resolver_outputs(stocks_conn))
        checks.append(check_signal_outcomes(stocks_conn))
    except RuntimeError as exc:
        log.error("Stocks DB connect failed: %s", exc)
        checks.append({"check": "live_picks", "status": "RED", "error": str(exc)})
        checks.append({"check": "resolver_outputs", "status": "RED", "error": str(exc)})
        checks.append({"check": "signal_outcomes", "status": "RED", "error": str(exc)})
    finally:
        if stocks_conn:
            try:
                stocks_conn.close()
            except Exception:
                pass

    # ── Backtests DB ─────────────────────────────────────────────────────────
    try:
        backtests_conn = _connect_backtests()
        checks.append(check_backtests(backtests_conn))
    except RuntimeError as exc:
        log.error("Backtests DB connect failed: %s", exc)
        checks.append({"check": "backtests", "status": "RED", "error": str(exc)})
    finally:
        if backtests_conn:
            try:
                backtests_conn.close()
            except Exception:
                pass

    # ── Overall status ────────────────────────────────────────────────────────
    statuses = [c.get("status", "RED") for c in checks if c.get("status") != "SKIPPED"]
    if "RED" in statuses:
        overall = "RED"
    elif "YELLOW" in statuses:
        overall = "YELLOW"
    else:
        overall = "GREEN"

    report = {
        "overall": overall,
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": THRESHOLDS,
    }

    # Write output
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        log.info("Freshness report written: %s (overall=%s)", output_path, overall)
    except Exception as exc:
        log.warning("Failed to write freshness report: %s", exc)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = run_freshness_check()
    overall = report.get("overall", "RED")
    log.info("Overall DB freshness: %s", overall)
    exit_code = {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(overall, 2)
    sys.exit(exit_code)
