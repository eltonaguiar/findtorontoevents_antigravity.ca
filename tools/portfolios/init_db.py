"""Apply the AI-model-portfolios Phase 1 schema to ejaguiar1_stocks.

Reads tools/portfolios/schema.sql and executes each CREATE TABLE statement.
Idempotent (every statement is CREATE TABLE IF NOT EXISTS).

SAFETY: defaults to --dry-run. The live DB is ONLY touched when --apply is
passed explicitly, so this script can never accidentally write to production.

Usage:
    python tools/portfolios/init_db.py            # dry-run (default): print statements
    python tools/portfolios/init_db.py --dry-run  # explicit dry-run
    python tools/portfolios/init_db.py --apply     # connect + execute (live)

Environment (same convention as tools/ai_tournament/ingest_to_db.py):
    DB_HOST_STOCKS    MySQL host     (default: mysql.50webs.com)
    DB_USER_STOCKS    Username       (default: ejaguiar1_stocks)
    DB_PASS_STOCKS    MySQL password (default: stocks1234560)
    DB_NAME_STOCKS    Database name  (default: ejaguiar1_stocks)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def load_statements(path: Path = SCHEMA_PATH) -> list[str]:
    """Split schema.sql into individual executable statements.

    Strips line comments (-- ...) and blank lines, then splits on ';'.
    """
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    text = path.read_text()
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    statements = []
    for chunk in cleaned.split(";"):
        chunk = chunk.strip()
        if chunk:
            statements.append(chunk)
    return statements


def summarize(stmt: str) -> str:
    m = re.search(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", stmt, re.IGNORECASE)
    return m.group(1) if m else stmt.split("\n", 1)[0][:60]


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    # Default to dry-run unless --apply is explicitly passed.
    dry_run = not apply

    statements = load_statements()
    print(f"[init_db] loaded {len(statements)} statement(s) from {SCHEMA_PATH}")

    if dry_run:
        print("[init_db] DRY-RUN (no DB connection). Pass --apply to execute.")
        for i, stmt in enumerate(statements, 1):
            print(f"\n--- statement {i}/{len(statements)} ({summarize(stmt)}) ---")
            print(stmt + ";")
        print(f"\n[init_db] dry-run complete: {len(statements)} CREATE TABLE statement(s).")
        return 0

    db_host = os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com")
    db_user = os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks")
    db_pass = os.environ.get("DB_PASS_STOCKS", "") or os.environ.get("MYSQL_PASSWORD", "")
    db_name = os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks")

    print(f"[init_db] APPLY: connecting to {db_host}/{db_name} as {db_user}")
    try:
        import pymysql
    except ImportError:
        print("[init_db] ERROR: pymysql not installed — cannot --apply", file=sys.stderr)
        return 1

    conn = pymysql.connect(
        host=db_host, user=db_user, password=db_pass, database=db_name,
        port=3306, connect_timeout=20, autocommit=False)
    try:
        with conn.cursor() as cur:
            for i, stmt in enumerate(statements, 1):
                name = summarize(stmt)
                print(f"[init_db] [{i}/{len(statements)}] {name} ...")
                cur.execute(stmt)
        conn.commit()
        print(f"[init_db] applied {len(statements)} statement(s); committed.")
    except Exception:
        conn.rollback()
        print("[init_db] ERROR — rolled back", file=sys.stderr)
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
