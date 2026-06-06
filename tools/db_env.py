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

import json
import os
from typing import Optional


_DEFAULT_HOST = "mysql.50webs.com"
_DEFAULT_PORT = 3306
_DEFAULT_STOCKS_USER = "ejaguiar1_stocks"
_DEFAULT_STOCKS_NAME = "ejaguiar1_stocks"
_DEFAULT_BACKTESTS_NAME = "ejaguiar1_backtests"
_DEFAULT_BACKUPS_USER = "ejaguiar1_backups"
_DEFAULT_BACKUPS_NAME = "ejaguiar1_backups"


# 2026-05-25 — the canonical source of truth for DB credentials is the
# `DB_PASSWORDS_JSON` env var (or, locally, the gitignored `.env.dbpw`
# file). It holds `{"stocks": "...", "backtests": "...", ...}` for all 10
# DBs. The legacy individual env vars (DB_PASS_STOCKS, MYSQL_PASS_EVENTS,
# DB_SERVER_EVENTS_PASSWORD, DBPASS_MOVIES, etc.) that show up in some
# harness/Windows-backup environments are STALE — they don't match the
# verified passwords and burned a host-block when scripts pulled them.
# Always prefer DB_PASSWORDS_JSON; fall through to the legacy names only
# as a last resort so existing scripts don't break entirely.
_PW_JSON_CACHE: Optional[dict] = None


def _passwords_json() -> dict:
    """Load the consolidated DB_PASSWORDS_JSON env or .env.dbpw file once.

    Returns empty dict if neither is present (so callers fall through to
    the legacy per-DB env names).
    """
    global _PW_JSON_CACHE
    if _PW_JSON_CACHE is not None:
        return _PW_JSON_CACHE
    raw = (os.environ.get("DB_PASSWORDS_JSON") or "").strip()
    if not raw:
        for path in (".env.dbpw", os.path.expanduser("~/.env.dbpw")):
            try:
                with open(path) as fh:
                    raw = fh.read().strip()
                    if raw:
                        break
            except OSError:
                continue
    if not raw:
        _PW_JSON_CACHE = {}
        return _PW_JSON_CACHE
    try:
        parsed = json.loads(raw)
        _PW_JSON_CACHE = parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        _PW_JSON_CACHE = {}
    return _PW_JSON_CACHE


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
    # Priority: DB_PASSWORDS_JSON["stocks"] is canonical (see _passwords_json
    # docstring). Legacy env vars are checked only as last resort because in
    # several environments they hold stale values from earlier rotations.
    pw = _passwords_json().get("stocks") or _first_set(
        "MYSQL_PASSWORD",        # GH secret convention
        "DB_STOCKS_PASSWORD",    # legacy
        "DB_PASS_STOCKS",        # individual env (may be stale)
        "DB_PASSWORD",           # older
        "AUDIT_DB_PASS",         # mysql_client.py alias
    )
    if not pw and raise_on_missing:
        raise ValueError(
            "no DB password found — set DB_PASSWORDS_JSON (canonical) or "
            "any of: MYSQL_PASSWORD, DB_STOCKS_PASSWORD, DB_PASS_STOCKS, "
            "DB_PASSWORD, AUDIT_DB_PASS"
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
    pw = _passwords_json().get("backtests") or _first_set(
        "DB_BACKTESTS_PASSWORD", # legacy
        "BACKTESTS_DB_PASS",     # mysql_client alias
        "DB_PASS_BACKTESTS",     # individual env (may be stale)
        "MYSQL_PASSWORD",        # GH secret fallback
        "DB_STOCKS_PASSWORD",    # last-resort same-creds fallback
    )
    if not pw and raise_on_missing:
        raise ValueError(
            "no DB password found — set DB_PASSWORDS_JSON (canonical) or "
            "any of: DB_BACKTESTS_PASSWORD, BACKTESTS_DB_PASS, "
            "DB_PASS_BACKTESTS, MYSQL_PASSWORD, DB_STOCKS_PASSWORD"
        )
    return {
        "host": _first_set("DB_HOST_BACKTESTS", "DB_BACKTESTS_HOST",
                            "BACKTESTS_DB_HOST", "AUDIT_DB_HOST",
                            default=_DEFAULT_HOST),
        "user": _first_set("DB_USER_BACKTESTS", "DB_BACKTESTS_USER",
                            "BACKTESTS_DB_USER",
                            default="ejaguiar1_backtests"),
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


def get_backups_creds(*, raise_on_missing: bool = True) -> dict:
    """Build pymysql.connect() kwargs for ejaguiar1_backups (archive DB).

    Mandatory target before mutating ejaguiar1_stocks tables per project safety rule.
    """
    pw = _passwords_json().get("backups") or _first_set(
        "DB_PASS_BACKUPS",
        "DB_BACKUPS_PASSWORD",
        "BACKUPS_DB_PASS",
        "MYSQL_PASSWORD",
    )
    if not pw and raise_on_missing:
        raise ValueError(
            "no backups DB password found — set DB_PASSWORDS_JSON['backups'] or "
            "DB_PASS_BACKUPS / DB_BACKUPS_PASSWORD"
        )
    return {
        "host": _first_set(
            "DB_HOST_BACKUPS", "DB_BACKUPS_HOST", "AUDIT_DB_HOST", default=_DEFAULT_HOST
        ),
        "user": _first_set(
            "DB_USER_BACKUPS", "DB_BACKUPS_USER", default=_DEFAULT_BACKUPS_USER
        ),
        "password": pw,
        "database": _first_set(
            "DB_NAME_BACKUPS", "DB_BACKUPS_NAME", default=_DEFAULT_BACKUPS_NAME
        ),
        "port": int(
            _first_set("DB_PORT_BACKUPS", "DB_BACKUPS_PORT", "AUDIT_DB_PORT",
                       default=str(_DEFAULT_PORT))
        ),
        "connect_timeout": 30,
        "read_timeout": 120,
    }


def diagnose() -> dict:
    """Diagnostic: which credential sources are set, redacted. Names+lengths only."""
    relevant = [
        # Canonical source first
        "DB_PASSWORDS_JSON",
        # Per-DB names db_env.py uses
        "DB_PASS_STOCKS", "DB_NAME_STOCKS", "DB_USER_STOCKS", "DB_HOST_STOCKS",
        "DB_PASS_BACKTESTS", "DB_NAME_BACKTESTS",
        "DB_PASS_BACKUPS", "DB_NAME_BACKUPS",
        "MYSQL_PASSWORD",
        "DB_STOCKS_PASSWORD", "DB_STOCKS_USER", "DB_STOCKS_HOST", "DB_STOCKS_NAME",
        "DB_BACKTESTS_PASSWORD",
        "AUDIT_DB_PASS", "AUDIT_DB_HOST", "AUDIT_DB_USER", "AUDIT_DB_NAME",
        "DB_PASSWORD", "DB_USER", "DB_HOST", "DB_NAME",
    ]
    out = {}
    for n in relevant:
        v = os.environ.get(n)
        out[n] = f"SET (len={len(v)})" if v else "UNSET"
    pj = _passwords_json()
    out["_DB_PASSWORDS_JSON_keys"] = sorted(pj.keys()) if pj else []
    out["_env_dbpw_file"] = "PRESENT" if os.path.exists(".env.dbpw") else "absent"
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
    try:
        bk = get_backups_creds()
        print(f"# get_backups_creds() -> resolved: host={bk['host']} "
              f"user={bk['user']} db={bk['database']} port={bk['port']} "
              f"pass=*** (len={len(bk['password'])})")
    except ValueError as e:
        print(f"# get_backups_creds() FAILED: {e}")
