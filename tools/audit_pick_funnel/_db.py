"""Shared DB connection helper for the audit pick-funnel automation.

Uses pymysql against ejaguiar1_stocks @ mysql.50webs.com. Credentials are
resolved via tools.db_env (preferred) or DB_PASS_STOCKS env fallback.
Read-only: this module never ALTERs existing tables.
"""
from __future__ import annotations

import os
from typing import Any


def connect_stocks() -> Any:
    """Return a pymysql DictCursor connection to ejaguiar1_stocks."""
    import pymysql
    try:
        from tools.db_env import get_stocks_creds  # type: ignore
        c = get_stocks_creds()
        return pymysql.connect(
            host=c["host"], user=c["user"], password=c["password"],
            database=c["database"], port=int(c.get("port", 3306)),
            connect_timeout=15, read_timeout=60,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception:
        pwd = os.environ.get("DB_PASS_STOCKS") or os.environ.get("MYSQL_PASSWORD")
        if not pwd:
            raise RuntimeError("DB_PASS_STOCKS not set")
        return pymysql.connect(
            host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
            user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
            password=pwd,
            database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
            port=int(os.environ.get("DB_PORT_STOCKS", "3306")),
            connect_timeout=15, read_timeout=60,
            cursorclass=__import__("pymysql").cursors.DictCursor,
        )
