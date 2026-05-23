#!/usr/bin/env python3
"""
Migrate backtest-heavy tables from ejaguiar1_stocks -> ejaguiar1_backtests.

Credentials are read from environment variables (GitHub Secrets / server .env):
  MYSQL_HOST                 (default: mysql.50webs.com)
  MYSQL_PORT                 (default: 3306)
  SOURCE_DB_NAME             (default: ejaguiar1_stocks)
  TARGET_DB_NAME             (default: ejaguiar1_backtests)
  SOURCE_DB_USER             (default: AUDIT_DB_USER or ejaguiar1_stocks)
  SOURCE_DB_PASS             (default: AUDIT_DB_PASS or stocks)
  TARGET_DB_USER             (default: BACKTESTS_DB_USER or SOURCE_DB_USER)
  TARGET_DB_PASS             (default: BACKTESTS_DB_PASS or SOURCE_DB_PASS)

Default tables:
  - bt_backtest_trades
  - bt_backtest_runs
  - backtest_trades
  - backtest_results
  - at_large_backtest_results
  - at_incubator_backtest_results

Example:
  python tools/migrate_backtests_to_backtests_db.py --dry-run
  python tools/migrate_backtests_to_backtests_db.py --tables bt_backtest_trades bt_backtest_runs
  python tools/migrate_backtests_to_backtests_db.py --truncate-target
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Iterable, List


DEFAULT_TABLES = [
    "bt_backtest_trades",
    "bt_backtest_runs",
    "backtest_trades",
    "backtest_results",
    "at_large_backtest_results",
    "at_incubator_backtest_results",
]


@dataclass
class Config:
    host: str
    port: int
    source_db: str
    target_db: str
    source_user: str
    source_pass: str
    target_user: str
    target_pass: str
    tables: List[str]
    dry_run: bool
    truncate_target: bool
    stop_on_error: bool


def _ensure_pymysql():
    try:
        import pymysql  # type: ignore
        return pymysql
    except ImportError:
        raise RuntimeError(
            "pymysql is required. Install with: python -m pip install pymysql"
        )


def _safe_table_name(name: str) -> str:
    if not name:
        raise ValueError("Empty table name")
    for ch in name:
        if not (ch.isalnum() or ch == "_"):
            raise ValueError(f"Invalid table name: {name}")
    return name


def _quote_ident(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def load_config(args: argparse.Namespace) -> Config:
    source_user = os.getenv("SOURCE_DB_USER", os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"))
    source_pass = os.getenv("SOURCE_DB_PASS", os.getenv("AUDIT_DB_PASS", "stocks"))
    target_user = os.getenv("TARGET_DB_USER", os.getenv("BACKTESTS_DB_USER", source_user))
    target_pass = os.getenv("TARGET_DB_PASS", os.getenv("BACKTESTS_DB_PASS", source_pass))

    raw_tables: Iterable[str] = args.tables or DEFAULT_TABLES
    tables = [_safe_table_name(t.strip()) for t in raw_tables if t and t.strip()]
    if not tables:
        raise ValueError("No tables specified")

    return Config(
        host=os.getenv("MYSQL_HOST", "mysql.50webs.com"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        source_db=os.getenv("SOURCE_DB_NAME", "ejaguiar1_stocks"),
        target_db=os.getenv("TARGET_DB_NAME", "ejaguiar1_backtests"),
        source_user=source_user,
        source_pass=source_pass,
        target_user=target_user,
        target_pass=target_pass,
        tables=tables,
        dry_run=bool(args.dry_run),
        truncate_target=bool(args.truncate_target),
        stop_on_error=bool(args.stop_on_error),
    )


def _connect(pymysql, host: str, port: int, user: str, password: str):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset="utf8mb4",
        autocommit=False,
        connect_timeout=20,
        read_timeout=120,
        write_timeout=120,
    )


def _count_rows(cur, db: str, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {_quote_ident(db)}.{_quote_ident(table)}")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _table_exists(cur, db: str, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s LIMIT 1",
        (db, table),
    )
    return cur.fetchone() is not None


def migrate_table(cur, cfg: Config, table: str) -> dict:
    src = f"{_quote_ident(cfg.source_db)}.{_quote_ident(table)}"
    dst = f"{_quote_ident(cfg.target_db)}.{_quote_ident(table)}"
    result = {"table": table, "source_count": 0, "target_before": 0, "target_after": 0}

    if not _table_exists(cur, cfg.source_db, table):
        raise RuntimeError(f"Source table missing: {cfg.source_db}.{table}")

    result["source_count"] = _count_rows(cur, cfg.source_db, table)
    result["target_before"] = _count_rows(cur, cfg.target_db, table) if _table_exists(cur, cfg.target_db, table) else 0

    if cfg.dry_run:
        return result

    cur.execute(f"CREATE TABLE IF NOT EXISTS {dst} LIKE {src}")
    if cfg.truncate_target:
        cur.execute(f"TRUNCATE TABLE {dst}")

    cur.execute(f"INSERT INTO {dst} SELECT * FROM {src}")
    result["inserted_rows"] = int(cur.rowcount) if cur.rowcount is not None else -1

    result["target_after"] = _count_rows(cur, cfg.target_db, table)
    return result


def run(cfg: Config) -> int:
    pymysql = _ensure_pymysql()
    conn = _connect(
        pymysql,
        host=cfg.host,
        port=cfg.port,
        user=cfg.target_user,
        password=cfg.target_pass,
    )
    cur = conn.cursor()
    exit_code = 0

    try:
        print(f"Host: {cfg.host}:{cfg.port}")
        print(f"Source: {cfg.source_db} (user={cfg.source_user})")
        print(f"Target: {cfg.target_db} (user={cfg.target_user})")
        print(f"Mode: {'DRY RUN' if cfg.dry_run else 'LIVE COPY'}")
        print(f"Tables: {', '.join(cfg.tables)}")
        print("")

        # Verify visibility of source/target DBs from this connection.
        cur.execute("SELECT DATABASE()")
        _ = cur.fetchone()

        for table in cfg.tables:
            try:
                res = migrate_table(cur, cfg, table)
                print(
                    f"[OK] {table}: source={res['source_count']}, "
                    f"target_before={res['target_before']}, target_after={res['target_after']}"
                )
            except Exception as exc:
                exit_code = 1
                print(f"[ERROR] {table}: {exc}")
                if cfg.stop_on_error:
                    raise

        if not cfg.dry_run and exit_code == 0:
            conn.commit()
            print("\nCommitted migration transaction.")
        elif not cfg.dry_run:
            conn.rollback()
            print("\nRolled back migration due to errors.")
    except Exception:
        if not cfg.dry_run:
            conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return exit_code


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Copy backtest tables from stocks DB to backtests DB.")
    p.add_argument(
        "--tables",
        nargs="+",
        help="Override table list (space-separated)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Read counts and validate table presence without copying data",
    )
    p.add_argument(
        "--truncate-target",
        action="store_true",
        help="TRUNCATE target tables before copy (useful for reruns)",
    )
    p.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately if one table fails",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args)
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
