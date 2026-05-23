#!/usr/bin/env python3
"""Unified DB credential resolution across multiple env-var naming schemes.

2026-05-12 DB credentials rotated by user. Local env now uses:
  DB_PASS_STOCKS / DB_NAME_STOCKS / DB_PASS_BACKTESTS / DB_NAME_BACKTESTS

Repo code historically used at least 4 distinct naming conventions:
  - AUDIT_DB_HOST/USER/PASS/NAME             (audit_trail/mysql_client.py)
  - DB_STOCKS_HOST/USER/PASSWORD/NAME        (alpha_engine/active_picks_sync.py
                                              and most tools/* additions)
  - MYSQL_PASSWORD (GH secret)               (GitHub Actions workflow steps)
  - DB_BACKTESTS_PASSWORD                    (older backtest-DB callers)
  - BACKTESTS_DB_USER/PASS/NAME              (mysql_client.py backtests path)

This module centralizes resolution. Callers do:

    from tools.db_env import get_stocks_creds, get_backtests_creds
    creds = get_stocks_creds()
    conn = pymysql.connect(**creds)

Each helper returns a kwargs dict suitable for pymysql.connect() (or
mysql.connector.connect() — same keyword shape). Raises ValueError if
no password can be resolved.

Resolution priority for password (first match wins):
  1. New names: DB_PASS_STOCKS (or DB_PASS_BACKTESTS for backtests DB)
  2. Common GH-secret name: MYSQL_PASSWORD
  3. Legacy: DB_STOCKS_PASSWORD / DB_BACKTESTS_PASSWORD
  4. Older audit alias: AUDIT_DB_PASS / DB_PASSWORD

Same priority pattern for HOST/USER/NAME.
"""
from __future__ import annotations

import os
from typing import Optional


_DEFAULT_HOST = "mysql.50webs.com"
_DEFAULT_PORT = 3306
_DEFAULT_STOCKS_USER = "ejaguiar1_stocks"
_DEFAULT_STOCKS_NAME = "ejaguiar1_stocks"
_DEFAULT_BACKTESTS_NAME = "ejaguiar1_backtests"


def _first_set(*names: str, default: Optional[str] = None) -> Optional[str]:
    """Return first env var in `names` that resolves to a non-empty string."""
    for n in names:
        v = os.environ.get(n)
        if v:
            v = str(v).strip()
            if v:
                return v
    return default


def get_stocks_creds(*, raise_on_missing: bool = True) -> dict:
    """Build pymysql.connect() kwargs for the ejaguiar1_stocks DB.

    Args:
        raise_on_missing: if True, raise ValueError when password absent.

    Returns:
        dict with keys: host, user, password, database, port,
        connect_timeout, read_timeout.
    """
    pw = _first_set(
        "DB_PASS_STOCKS",        # new (2026-05-12 rotation)
        "MYSQL_PASSWORD",        # GH secret convention
        "DB_STOCKS_PASSWORD",    # legacy
        "DB_PASSWORD",           # older
        "AUDIT_DB_PASS",         # mysql_client.py alias
    )
    if not pw and raise_on_missing:
        raise ValueError(
            "no DB password found in any of: DB_PASS_STOCKS, "
            "MYSQL_PASSWORD, DB_STOCKS_PASSWORD, DB_PASSWORD, AUDIT_DB_PASS"
        )
    return {
        "host": _first_set("DB_HOST_STOCKS", "DB_STOCKS_HOST", "AUDIT_DB_HOST",
                            default=_DEFAULT_HOST),
        "user": _first_set("DB_USER_STOCKS", "DB_STOCKS_USER", "AUDIT_DB_USER",
                            default=_DEFAULT_STOCKS_USER),
        "password": pw,
        "database": _first_set("DB_NAME_STOCKS", "DB_STOCKS_NAME", "AUDIT_DB_NAME",
                                default=_DEFAULT_STOCKS_NAME),
        "port": int(_first_set("DB_PORT_STOCKS", "DB_STOCKS_PORT", "AUDIT_DB_PORT",
                                default=str(_DEFAULT_PORT))),
        "connect_timeout": 30,
        "read_timeout": 60,
    }


def get_backtests_creds(*, raise_on_missing: bool = True) -> dict:
    """Build pymysql.connect() kwargs for the ejaguiar1_backtests DB.

    Falls back to stocks-DB password if backtests-specific not set, since
    many environments use the same credential for both.
    """
    pw = _first_set(
        "DB_PASS_BACKTESTS",     # new
        "DB_BACKTESTS_PASSWORD", # legacy
        "BACKTESTS_DB_PASS",     # mysql_client alias
        "MYSQL_PASSWORD",        # GH secret fallback
        "DB_STOCKS_PASSWORD",    # last-resort same-creds fallback
    )
    if not pw and raise_on_missing:
        raise ValueError(
            "no DB password found in any of: DB_PASS_BACKTESTS, "
            "DB_BACKTESTS_PASSWORD, BACKTESTS_DB_PASS, MYSQL_PASSWORD, "
            "DB_STOCKS_PASSWORD"
        )
    return {
        "host": _first_set("DB_HOST_BACKTESTS", "DB_BACKTESTS_HOST",
                            "BACKTESTS_DB_HOST", "AUDIT_DB_HOST",
                            default=_DEFAULT_HOST),
        "user": _first_set("DB_USER_BACKTESTS", "DB_BACKTESTS_USER",
                            "BACKTESTS_DB_USER", "AUDIT_DB_USER",
                            default=_DEFAULT_STOCKS_USER),
        "password": pw,
        "database": _first_set("DB_NAME_BACKTESTS", "DB_BACKTESTS_NAME",
                                "BACKTESTS_DB_NAME",
                                default=_DEFAULT_BACKTESTS_NAME),
        "port": int(_first_set("DB_PORT_BACKTESTS", "DB_BACKTESTS_PORT",
                                "AUDIT_DB_PORT",
                                default=str(_DEFAULT_PORT))),
        "connect_timeout": 30,
        "read_timeout": 60,
    }


def diagnose() -> dict:
    """Diagnostic: which env vars are set, redacted. Returns names+lengths only."""
    relevant = [
        "DB_PASS_STOCKS", "DB_NAME_STOCKS", "DB_USER_STOCKS", "DB_HOST_STOCKS",
        "DB_PASS_BACKTESTS", "DB_NAME_BACKTESTS",
        "MYSQL_PASSWORD",
        "DB_STOCKS_PASSWORD", "DB_STOCKS_USER", "DB_STOCKS_HOST", "DB_STOCKS_NAME",
        "DB_BACKTESTS_PASSWORD",
        "AUDIT_DB_PASS", "AUDIT_DB_HOST", "AUDIT_DB_USER", "AUDIT_DB_NAME",
        "DB_PASSWORD", "DB_USER", "DB_HOST", "DB_NAME",
    ]
    out = {}
    for n in relevant:
        v = os.environ.get(n)
        if v:
            out[n] = f"SET (len={len(v)})"
        else:
            out[n] = "UNSET"
    return out


if __name__ == "__main__":
    import json
    print("# DB env diagnostic — checks all known naming conventions")
    print(json.dumps(diagnose(), indent=2))
    try:
        s = get_stocks_creds()
        print(f"\n# get_stocks_creds() -> resolved: host={s['host']} "
              f"user={s['user']} db={s['database']} port={s['port']} "
              f"pass=*** (len={len(s['password'])})")
    except ValueError as e:
        print(f"\n# get_stocks_creds() FAILED: {e}")
    try:
        b = get_backtests_creds()
        print(f"# get_backtests_creds() -> resolved: host={b['host']} "
              f"user={b['user']} db={b['database']} port={b['port']} "
              f"pass=*** (len={len(b['password'])})")
    except ValueError as e:
        print(f"# get_backtests_creds() FAILED: {e}")
