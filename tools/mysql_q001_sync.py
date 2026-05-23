#!/usr/bin/env python3
"""Q-001 MySQL sync — create ejaguiar1_stocks.picks table + sync from JSON files.

Steps:
  1. Connect to ejaguiar1_stocks MySQL database
  2. Create ejaguiar1_backups database/schema if needed
  3. If ejaguiar1_stocks.picks already exists: copy to ejaguiar1_backups.picks_<UTC>
  4. Create ejaguiar1_stocks.picks with proper schema (from alpha_engine/database.py)
  5. Sync closed_picks.json → picks table (upsert by id, skip on conflict)
  6. Report row counts + sample rows

Usage (GitHub Actions):
  python tools/mysql_q001_sync.py [--dry-run] [--max-rows 5000]

Credentials via env:
  DB_PASS_STOCKS (or MYSQL_PASSWORD as fallback)
  DB_HOST_STOCKS (default: mysql.50webs.com)
  DB_NAME_STOCKS (default: ejaguiar1_stocks)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("ERROR: pymysql not installed. Run: pip install pymysql", file=sys.stderr)
    sys.exit(2)

from tools.db_env import get_stocks_creds

PICKS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `picks` (
    `id` VARCHAR(255) PRIMARY KEY,
    `strategy` VARCHAR(255),
    `source_system` VARCHAR(255),
    `symbol` VARCHAR(64) NOT NULL,
    `asset_class` VARCHAR(64),
    `category` VARCHAR(64),
    `signal_type` VARCHAR(32),
    `direction` VARCHAR(16),
    `entry_price` DOUBLE,
    `entry_date` VARCHAR(32),
    `take_profit` DOUBLE,
    `stop_loss` DOUBLE,
    `confidence` DOUBLE,
    `ml_score` DOUBLE,
    `elite_score` DOUBLE,
    `exit_price` DOUBLE,
    `exit_date` VARCHAR(32),
    `exit_reason` VARCHAR(64),
    `pnl_pct` DOUBLE,
    `pnl_dollar` DOUBLE,
    `status` VARCHAR(32) DEFAULT 'OPEN',
    `outcome` VARCHAR(32),
    `created_at` VARCHAR(64),
    `updated_at` VARCHAR(64),
    `risk_reward` DOUBLE,
    `extra_json` TEXT,
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_asset_class` (`asset_class`),
    INDEX `idx_status` (`status`),
    INDEX `idx_source_system` (`source_system`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def get_conn():
    creds = get_stocks_creds()
    return pymysql.connect(**creds, cursorclass=DictCursor)


def backup_existing_table(conn, ts: str, dry_run: bool) -> int:
    """Copy ejaguiar1_stocks.picks → ejaguiar1_backups.picks_<ts> if picks exists."""
    backup_db = "ejaguiar1_backups"
    backup_table = f"picks_{ts}"

    with conn.cursor() as cur:
        # Check if picks exists
        cur.execute("SHOW TABLES LIKE 'picks'")
        exists = cur.fetchone()
        if not exists:
            print("  picks table does not exist yet — no backup needed")
            return 0

        cur.execute("SELECT COUNT(*) as n FROM picks")
        n = cur.fetchone()["n"]
        print(f"  Found existing picks table with {n} rows")

        if dry_run:
            print(f"  [DRY-RUN] Would backup to {backup_db}.{backup_table}")
            return n

        # Create backup DB if needed
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{backup_db}` CHARACTER SET utf8mb4")
        print(f"  Creating backup {backup_db}.{backup_table} ...")
        cur.execute(
            f"CREATE TABLE `{backup_db}`.`{backup_table}` SELECT * FROM picks"
        )
        cur.execute(f"SELECT COUNT(*) as n FROM `{backup_db}`.`{backup_table}`")
        backup_n = cur.fetchone()["n"]
        conn.commit()
        print(f"  Backup done: {backup_n} rows in {backup_db}.{backup_table}")
        return backup_n


def create_picks_table(conn, dry_run: bool):
    """Create ejaguiar1_stocks.picks with proper schema."""
    if dry_run:
        print("  [DRY-RUN] Would create picks table")
        return
    with conn.cursor() as cur:
        cur.execute(PICKS_TABLE_DDL)
        conn.commit()
    print("  picks table created (or already exists)")


def sync_closed_picks(conn, max_rows: int, dry_run: bool) -> dict:
    """Load alpha_engine/data/closed_picks.json → picks table (upsert)."""
    json_path = ROOT / "alpha_engine" / "data" / "closed_picks.json"
    if not json_path.exists():
        print(f"  WARNING: {json_path} not found — skipping sync")
        return {"loaded": 0, "inserted": 0, "skipped": 0}

    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    picks = [p for p in raw if isinstance(p, dict)]
    print(f"  Loaded {len(picks)} picks from closed_picks.json")

    if max_rows and len(picks) > max_rows:
        picks = picks[:max_rows]
        print(f"  Capped to {max_rows} rows")

    if dry_run:
        print(f"  [DRY-RUN] Would upsert {len(picks)} rows")
        return {"loaded": len(picks), "inserted": 0, "skipped": 0}

    inserted = 0
    skipped = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    insert_sql = """
        INSERT INTO picks
            (id, strategy, source_system, symbol, asset_class, category,
             signal_type, direction, entry_price, entry_date, take_profit,
             stop_loss, confidence, ml_score, elite_score, exit_price,
             exit_date, exit_reason, pnl_pct, pnl_dollar, status, outcome,
             created_at, updated_at, risk_reward, extra_json)
        VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            outcome = VALUES(outcome),
            pnl_pct = VALUES(pnl_pct),
            exit_price = VALUES(exit_price),
            exit_date = VALUES(exit_date),
            exit_reason = VALUES(exit_reason),
            updated_at = VALUES(updated_at)
    """

    with conn.cursor() as cur:
        for p in picks:
            pid = p.get("id") or p.get("pick_id") or f"{p.get('source_system','?')}::{p.get('symbol','?')}::{p.get('created_at','?')}"
            extra = {k: v for k, v in p.items() if k not in {
                "id", "strategy", "source_system", "symbol", "asset_class", "category",
                "signal_type", "direction", "entry_price", "entry_date", "take_profit",
                "stop_loss", "confidence", "ml_score", "elite_score", "exit_price",
                "exit_date", "exit_reason", "pnl_pct", "pnl_dollar", "status", "outcome",
                "created_at", "risk_reward"
            }}
            try:
                cur.execute(insert_sql, (
                    pid,
                    p.get("strategy_name") or p.get("strategy"),
                    p.get("source_system"),
                    p.get("symbol"),
                    p.get("asset_class"),
                    p.get("category"),
                    p.get("signal_type"),
                    p.get("direction"),
                    p.get("entry_price"),
                    p.get("entry_date") or p.get("created_at"),
                    p.get("take_profit"),
                    p.get("stop_loss"),
                    p.get("confidence"),
                    p.get("ml_score"),
                    p.get("elite_score"),
                    p.get("exit_price"),
                    p.get("exit_date"),
                    p.get("exit_reason"),
                    p.get("pnl_pct"),
                    p.get("pnl_dollar"),
                    p.get("status", "CLOSED"),
                    p.get("outcome"),
                    p.get("created_at", now_iso),
                    now_iso,
                    p.get("risk_reward"),
                    json.dumps(extra) if extra else None,
                ))
                inserted += 1
            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"  WARN row skip: {e}")

        conn.commit()

    print(f"  Upserted: {inserted} rows, skipped: {skipped}")
    return {"loaded": len(picks), "inserted": inserted, "skipped": skipped}


def sync_active_picks(conn, max_rows: int, dry_run: bool) -> int:
    """Optionally sync active_picks.json OPEN rows to the picks table too."""
    json_path = ROOT / "alpha_engine" / "data" / "active_picks.json"
    if not json_path.exists():
        return 0

    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    picks = [p for p in raw if isinstance(p, dict) and p.get("status", "OPEN") == "OPEN"]
    if not picks:
        return 0

    print(f"  Active picks: {len(picks)} OPEN rows")
    # Reuse the same upsert logic (just OPEN rows won't update closed cols)
    if dry_run:
        print(f"  [DRY-RUN] Would upsert {len(picks)} active rows")
        return len(picks)

    now_iso = datetime.now(timezone.utc).isoformat()
    insert_sql = """
        INSERT INTO picks
            (id, strategy, source_system, symbol, asset_class, direction,
             entry_price, take_profit, stop_loss, confidence, status,
             created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            updated_at = VALUES(updated_at)
    """
    inserted = 0
    with conn.cursor() as cur:
        for p in picks[:max_rows]:
            pid = (p.get("id") or
                   f"{p.get('source_system','?')}::{p.get('symbol','?')}::{p.get('created_at','?')}")
            try:
                cur.execute(insert_sql, (
                    pid,
                    p.get("strategy_name") or p.get("strategy"),
                    p.get("source_system"),
                    p.get("symbol"),
                    p.get("asset_class"),
                    p.get("direction"),
                    p.get("entry_price"),
                    p.get("take_profit"),
                    p.get("stop_loss"),
                    p.get("confidence"),
                    "OPEN",
                    p.get("created_at", now_iso),
                    now_iso,
                ))
                inserted += 1
            except Exception:
                pass
        conn.commit()
    print(f"  Active picks upserted: {inserted}")
    return inserted


def main():
    ap = argparse.ArgumentParser(description="Q-001 MySQL picks table sync")
    ap.add_argument("--dry-run", action="store_true", help="Read-only (no writes)")
    ap.add_argument("--max-rows", type=int, default=50000, help="Max closed_picks rows to sync")
    ap.add_argument("--skip-active", action="store_true", help="Skip active_picks sync")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"=== Q-001 MySQL sync — {ts} ===")
    print(f"mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")

    try:
        conn = get_conn()
        print("MySQL connected: ejaguiar1_stocks")
    except Exception as e:
        print(f"ERROR: cannot connect to MySQL: {e}", file=sys.stderr)
        sys.exit(1)

    results = {"ts": ts, "dry_run": args.dry_run}

    print("\n[Step 1] Backup existing picks table if present ...")
    results["backup_rows"] = backup_existing_table(conn, ts, args.dry_run)

    print("\n[Step 2] Create/verify picks table schema ...")
    create_picks_table(conn, args.dry_run)

    print(f"\n[Step 3] Sync closed_picks.json (max {args.max_rows} rows) ...")
    results["closed"] = sync_closed_picks(conn, args.max_rows, args.dry_run)

    if not args.skip_active:
        print("\n[Step 4] Sync active_picks.json OPEN rows ...")
        results["active_synced"] = sync_active_picks(conn, args.max_rows, args.dry_run)

    print("\n[Step 5] Verify row count ...")
    if not args.dry_run:
        with conn.cursor() as cur:
            cur.execute("SELECT status, COUNT(*) as n FROM picks GROUP BY status ORDER BY n DESC")
            rows = cur.fetchall()
            for r in rows:
                print(f"  status={r['status']}: {r['n']} rows")
            cur.execute("SELECT COUNT(*) as total FROM picks")
            total = cur.fetchone()["total"]
            results["total_rows"] = total
            print(f"  TOTAL: {total} rows in ejaguiar1_stocks.picks")

    conn.close()

    # Write result report
    report_path = ROOT / "reports" / f"mysql_q001_sync_{ts}.json"
    report_path.write_text(json.dumps(results, indent=2))
    print(f"\nReport written: {report_path}")
    print("=== Q-001 sync complete ===")


if __name__ == "__main__":
    main()
