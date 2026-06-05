"""
Canonical DB credential resolver for all ejaguiar1_stocks connections.

Priority order: env vars → hardcoded default (dev/CI only).
All production Python files MUST import from here instead of inlining passwords.

Usage:
    from alpha_engine.db_credentials import get_stocks_db_config
    conn = pymysql.connect(**get_stocks_db_config())
"""

from __future__ import annotations
import os


_HOST_DEFAULT = "mysql.50webs.com"
_USER_DEFAULT = "ejaguiar1_stocks"
_DB_DEFAULT = "ejaguiar1_stocks"
# No password literal — the canonical resolver is tools.db_env.get_stocks_creds()
# (handles DB_PASSWORDS_JSON + legacy env var fallbacks). This file is the
# lightweight in-tree fallback; require an env var to be set.
_PASS_DEFAULT = ""


def get_stocks_db_config(db: str | None = None) -> dict:
    """Return a pymysql.connect()-compatible kwargs dict for ejaguiar1_stocks."""
    return {
        "host": os.environ.get("DB_HOST", _HOST_DEFAULT),
        "user": os.environ.get("DB_USER", _USER_DEFAULT),
        "password": _get_password(),
        "database": db or os.environ.get("DB_NAME", _DB_DEFAULT),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "15")),
        "charset": "utf8mb4",
    }


def get_backtests_db_config() -> dict:
    """Return config for ejaguiar1_backtests (separate DB, same host/user)."""
    cfg = get_stocks_db_config()
    cfg["database"] = os.environ.get("DB_NAME_BACKTESTS", "ejaguiar1_backtests")
    cfg["password"] = os.environ.get(
        "DB_PASS_BACKTESTS",
        os.environ.get("DB_PASS_STOCKS", _PASS_DEFAULT),
    )
    return cfg


def _get_password() -> str:
    for var in ("DB_PASS", "DB_PASS_STOCKS", "AUDIT_DB_PASS", "MYSQL_PASSWORD"):
        val = os.environ.get(var)
        if val:
            return val
    return _PASS_DEFAULT
