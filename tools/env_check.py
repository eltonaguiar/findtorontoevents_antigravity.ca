#!/usr/bin/env python3
"""Validate required MySQL env vars before sync. Exit 1 with clear message if missing."""
import os, sys

def check():
    errors = []

    stocks_pass = os.environ.get("DB_PASS_STOCKS") or os.environ.get("MYSQL_PASSWORD") or os.environ.get("AUDIT_DB_PASS")
    if not stocks_pass:
        errors.append("Stocks DB password missing: set DB_PASS_STOCKS, MYSQL_PASSWORD, or AUDIT_DB_PASS")
    else:
        print(f"[env_check] Stocks DB credential: resolved via {'DB_PASS_STOCKS' if os.environ.get('DB_PASS_STOCKS') else 'MYSQL_PASSWORD/AUDIT_DB_PASS'}")

    bt_pass = os.environ.get("DB_PASS_BACKTESTS") or os.environ.get("MYSQL_PASSWORD")
    if not bt_pass:
        errors.append("Backtests DB password missing: set DB_PASS_BACKTESTS or MYSQL_PASSWORD")
    else:
        print(f"[env_check] Backtests DB credential: resolved via {'DB_PASS_BACKTESTS' if os.environ.get('DB_PASS_BACKTESTS') else 'MYSQL_PASSWORD'}")

    host = os.environ.get("MYSQL_HOST", "mysql.50webs.com")
    print(f"[env_check] MySQL host: {host}")

    if errors:
        print("\n[env_check] ERRORS:")
        for e in errors:
            print(f"  - {e}")
        print("\nSee docs/MYSQL_ENV_SETUP.md for setup instructions.")
        sys.exit(1)

    print("[env_check] All required env vars present.")

if __name__ == "__main__":
    check()
