#!/usr/bin/env python3
"""Verify GitHub Actions can authenticate to all 10 MySQL databases.

Reads the consolidated `DB_PASSWORDS_JSON` secret (one JSON object mapping
db-suffix -> password) and opens a real connection to each
`ejaguiar1_<db>` database on the 50webs host. Reports pass/fail per
database and the runner's outbound IP (needed for the 50webs Remote-MySQL
allowlist). NEVER prints a password value.

Run by .github/workflows/db-credentials-test.yml (workflow_dispatch).
Locally: DB_PASSWORDS_JSON='{"stocks":"...",...}' python3 tools/test_db_credentials.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

HOST = os.environ.get("DB_HOST", "mysql.50webs.com")
DBS = ["backtests", "backups", "deals", "events", "favcreators",
       "memecoin", "news", "sportsbet", "stocks", "tvmoviestrailers"]


def main() -> int:
    raw = (os.environ.get("DB_PASSWORDS_JSON") or "").strip()
    if not raw:
        print("::error::DB_PASSWORDS_JSON secret is empty or not set on this repo")
        return 1
    try:
        creds = json.loads(raw)
    except Exception as exc:
        print(f"::error::DB_PASSWORDS_JSON is not valid JSON ({type(exc).__name__})")
        return 1
    try:
        import pymysql  # noqa: F401
    except ImportError:
        print("::error::pymysql not installed — add `pip install pymysql` to the workflow")
        return 1
    import pymysql

    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode()
    except Exception:
        ip = "unknown"
    print(f"GitHub runner outbound IP: {ip}")
    print("  -> this IP must be in the 50webs Remote-MySQL allowlist for each DB user")
    print(f"  -> host: {HOST}")
    print()
    print(f"{'DATABASE':<28} {'RESULT':<8} DETAIL")
    print("-" * 72)

    failures = 0
    for db in DBS:
        name = f"ejaguiar1_{db}"
        pw = creds.get(db)
        if not pw:
            print(f"{name:<28} {'SKIP':<8} no entry for '{db}' in DB_PASSWORDS_JSON")
            failures += 1
            continue
        t0 = time.time()
        try:
            conn = pymysql.connect(
                host=HOST, user=name, password=pw, database=name,
                connect_timeout=15, read_timeout=15,
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s",
                (name,),
            )
            ntab = cur.fetchone()[0]
            conn.close()
            print(f"{name:<28} {'OK':<8} {ntab} tables  ({time.time() - t0:.1f}s)")
        except Exception as exc:
            # print only the numeric error code, never the exception body
            # (it cannot contain the password, but stay conservative).
            code = exc.args[0] if getattr(exc, "args", None) else type(exc).__name__
            hint = {
                1045: "access denied — wrong password OR runner IP not in allowlist",
                2003: "cannot reach host — network / IP block",
                2013: "lost connection",
            }.get(code, "")
            print(f"{name:<28} {'FAIL':<8} [{code}] {hint}  ({time.time() - t0:.1f}s)")
            failures += 1

    print("-" * 72)
    ok = len(DBS) - failures
    print(f"{ok}/{len(DBS)} databases authenticated from GitHub Actions")
    if failures:
        print(f"::error::{failures} database connection(s) failed — see table above")
        return 1
    print("::notice::All 10 DB credentials verified working from GitHub Actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
