#!/usr/bin/env python3
"""
build_clean_ledger_v2.py
========================
Creates a deduplicated, source-banned, split-adjusted clean ledger
for analytics.

Tables produced:
  - ejaguiar1_stocks.trading_picks_v2
  - ejaguiar1_stocks.at_pick_outcomes_v2

Usage:
  python tools/build_clean_ledger_v2.py          # dry-run (default)
  python tools/build_clean_ledger_v2.py --execute  # apply changes
"""

import argparse
import hashlib
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import pymysql

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn(autocommit=False):
    from tools.db_env import get_stocks_creds
    conn = pymysql.connect(
        **get_stocks_creds(),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
        read_timeout=300,
        write_timeout=300,
    )
    conn.autocommit(autocommit)
    return conn


BANNED_SOURCES = ("Predictions", "sandbox_opposite", "rapid_fire", "incubator_gainer")

CLEAN_STATUSES = (
    "CLEAN",
    "BANNED_SOURCE",
    "BACKFILL_CORRUPT",
    "DUPLICATE",
    "SPLIT_AFFECTED",
    "STALE_RESOLVED",
)


def run_sql(cursor, sql, dry_run, label=""):
    """Execute or print a SQL statement."""
    if dry_run:
        preview = sql.strip().replace("\n", " ")[:180]
        print(f"[DRY-RUN] {label}: {preview}...")
        return 0
    cursor.execute(sql)
    return cursor.rowcount


# ---------------------------------------------------------------------------
# trading_picks_v2
# ---------------------------------------------------------------------------
def create_trading_picks_v2(cursor, dry_run):
    drop = "DROP TABLE IF EXISTS trading_picks_v2"
    run_sql(cursor, drop, dry_run, "DROP")

    create = """
    CREATE TABLE trading_picks_v2 (
      `id` char(36) NOT NULL,
      `aggregation_run_id` char(36) NOT NULL,
      `source_system` varchar(100) NOT NULL,
      `symbol` varchar(50) NOT NULL,
      `asset_class` enum('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
      `direction` enum('LONG','SHORT') NOT NULL,
      `entry_price` decimal(18,8) DEFAULT NULL,
      `take_profit` decimal(18,8) DEFAULT NULL,
      `stop_loss` decimal(18,8) DEFAULT NULL,
      `risk_reward` decimal(10,4) DEFAULT NULL,
      `confidence` decimal(5,4) DEFAULT NULL,
      `strategy` varchar(200) DEFAULT NULL,
      `raw_payload` json DEFAULT NULL,
      `signal_timestamp` datetime DEFAULT NULL,
      `recorded_at` datetime NOT NULL,
      `dedup_hash` char(64) DEFAULT NULL,
      `was_stale` tinyint(1) DEFAULT '0',
      `was_banned` tinyint(1) DEFAULT '0',
      `was_demoted` tinyint(1) DEFAULT '0',
      `was_wr_suppressed` tinyint(1) DEFAULT '0',
      `created_by` varchar(50) DEFAULT 'aggregator',
      `status` enum('OPEN','WON','LOST','EXPIRED','CLOSED','ABANDONED') DEFAULT NULL,
      `exit_price` decimal(18,8) DEFAULT NULL,
      `exit_reason` varchar(50) DEFAULT NULL,
      `pnl_pct` decimal(10,4) DEFAULT NULL,
      `closed_at` datetime DEFAULT NULL,
      `reverse_split_affected` tinyint(1) NOT NULL DEFAULT '0',
      `clean_status` enum('CLEAN','BANNED_SOURCE','BACKFILL_CORRUPT','DUPLICATE','SPLIT_AFFECTED','STALE_RESOLVED') NOT NULL DEFAULT 'CLEAN',
      `dedup_group_id` varchar(64) DEFAULT NULL,
      PRIMARY KEY (`id`),
      KEY `source_system` (`source_system`),
      KEY `symbol` (`symbol`),
      KEY `asset_class` (`asset_class`),
      KEY `signal_timestamp` (`signal_timestamp`),
      KEY `clean_status` (`clean_status`),
      KEY `recorded_at` (`recorded_at`),
      KEY `strategy` (`strategy`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    run_sql(cursor, create, dry_run, "CREATE trading_picks_v2")
    if not dry_run:
        print("Created trading_picks_v2")


def populate_trading_picks_v2(cursor, dry_run):
    sql = """
    INSERT INTO trading_picks_v2
    SELECT *, 'CLEAN', NULL
    FROM at_raw_picks
    """
    n = run_sql(cursor, sql, dry_run, "INSERT")
    if not dry_run:
        print(f"Populated trading_picks_v2: {n} rows")


def mark_banned_source(cursor, dry_run):
    sql = f"""
    UPDATE trading_picks_v2
    SET clean_status = 'BANNED_SOURCE'
    WHERE clean_status = 'CLEAN'
      AND (was_banned = 1
           OR source_system IN {BANNED_SOURCES})
    """
    n = run_sql(cursor, sql, dry_run, "BANNED_SOURCE")
    if not dry_run:
        print(f"  BANNED_SOURCE: {n} rows")


def mark_backfill_corrupt(cursor, dry_run):
    sql = """
    UPDATE trading_picks_v2
    SET clean_status = 'BACKFILL_CORRUPT'
    WHERE clean_status = 'CLEAN'
      AND (exit_reason LIKE '%BACKFILL%'
           OR ABS(pnl_pct) > 1000)
    """
    n = run_sql(cursor, sql, dry_run, "BACKFILL_CORRUPT")
    if not dry_run:
        print(f"  BACKFILL_CORRUPT: {n} rows")


def mark_split_affected(cursor, dry_run):
    sql = """
    UPDATE trading_picks_v2
    SET clean_status = 'SPLIT_AFFECTED'
    WHERE clean_status = 'CLEAN'
      AND reverse_split_affected = 1
    """
    n = run_sql(cursor, sql, dry_run, "SPLIT_AFFECTED")
    if not dry_run:
        print(f"  SPLIT_AFFECTED: {n} rows")


def mark_stale_resolved(cursor, dry_run):
    sql = """
    UPDATE trading_picks_v2
    SET clean_status = 'STALE_RESOLVED'
    WHERE clean_status = 'CLEAN'
      AND status = 'ABANDONED'
      AND exit_reason = 'STALE_TIMEOUT'
    """
    n = run_sql(cursor, sql, dry_run, "STALE_RESOLVED")
    if not dry_run:
        print(f"  STALE_RESOLVED: {n} rows")


def mark_duplicates(cursor, dry_run):
    """
    Same (symbol, direction, DATE(signal_timestamp)) within 1h window.
    Keep only the first (lowest recorded_at), mark rest as DUPLICATE.
    Done in Python for clarity and to avoid heavy self-joins on the remote DB.
    """
    if dry_run:
        print("[DRY-RUN] DUPLICATE: would fetch CLEAN rows and compute in Python")
        return 0

    cursor.execute("""
        SELECT id, symbol, direction, signal_timestamp, recorded_at
        FROM trading_picks_v2
        WHERE clean_status = 'CLEAN'
    """)
    rows = cursor.fetchall()

    def _parse_dt(val):
        if val is None:
            return None
        if isinstance(val, str):
            if val.startswith("0000-00-00"):
                return None
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        return val

    # Group by (symbol, direction, day)
    groups = defaultdict(list)
    for r in rows:
        ts = _parse_dt(r["signal_timestamp"])
        if ts is None:
            continue
        groups[(r["symbol"], r["direction"], ts.date())].append({
            "id": r["id"],
            "ts": ts,
            "recorded_at": _parse_dt(r["recorded_at"]),
        })

    duplicate_ids = []
    for key, items in groups.items():
        items.sort(key=lambda x: (x["recorded_at"], x["id"]))
        keepers = [items[0]]
        for item in items[1:]:
            is_dup = any(
                abs(item["ts"] - k["ts"]) <= timedelta(hours=1)
                for k in keepers
            )
            if is_dup:
                group_hash = hashlib.md5(
                    f"{key[0]}|{key[1]}|{key[2]}".encode()
                ).hexdigest()[:16]
                duplicate_ids.append((item["id"], group_hash))
            else:
                keepers.append(item)

    total_updated = 0
    batch_size = 500
    for i in range(0, len(duplicate_ids), batch_size):
        batch = duplicate_ids[i:i + batch_size]
        ids = [x[0] for x in batch]
        # Build a CASE mapping for dedup_group_id
        case_parts = []
        for _id, gid in batch:
            case_parts.append(f"WHEN '{_id}' THEN '{gid}'")
        case_sql = "CASE id " + " ".join(case_parts) + " END"
        fmt = ",".join(f"'{x}'" for x in ids)
        sql = f"""
        UPDATE trading_picks_v2
        SET clean_status = 'DUPLICATE',
            dedup_group_id = {case_sql}
        WHERE id IN ({fmt})
        """
        cursor.execute(sql)
        total_updated += cursor.rowcount

    print(f"  DUPLICATE: {total_updated} rows ({len(duplicate_ids)} computed)")
    return total_updated


# ---------------------------------------------------------------------------
# at_pick_outcomes_v2
# ---------------------------------------------------------------------------
def create_pick_outcomes_v2(cursor, dry_run):
    drop = "DROP TABLE IF EXISTS at_pick_outcomes_v2"
    run_sql(cursor, drop, dry_run, "DROP")

    create = """
    CREATE TABLE at_pick_outcomes_v2 (
      `pick_id` varchar(100) NOT NULL,
      `symbol` varchar(50) DEFAULT NULL,
      `strategy` varchar(200) DEFAULT NULL,
      `asset_class` varchar(20) DEFAULT NULL,
      `status` enum('OPEN','WON','LOST','EXPIRED','FLAT') NOT NULL,
      `resolution_method` enum('TP_HIT','SL_HIT','TIME_EXPIRED','MANUAL') DEFAULT NULL,
      `pnl_pct` decimal(10,4) DEFAULT NULL,
      `resolved_at` datetime DEFAULT NULL,
      `resolver_version` varchar(20) DEFAULT NULL,
      `forward_test_only` tinyint(1) DEFAULT '0',
      `forward_validated` tinyint(1) DEFAULT '0',
      `_gated_forward_test_isolated` tinyint(1) DEFAULT '0',
      PRIMARY KEY (`pick_id`),
      KEY `strategy` (`strategy`),
      KEY `asset_class` (`asset_class`),
      KEY `status` (`status`),
      KEY `resolved_at` (`resolved_at`),
      KEY `resolver_version` (`resolver_version`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    run_sql(cursor, create, dry_run, "CREATE at_pick_outcomes_v2")
    if not dry_run:
        print("Created at_pick_outcomes_v2")


def populate_pick_outcomes_v2(cursor, dry_run):
    """
    Copy from at_pick_outcomes excluding:
      1. Zero-PnL FLAT rows (1,034 known bad)
      2. Toxic resolver_version = 'signflip_purge_20260'
      3. Rows whose corresponding at_raw_picks row is not CLEAN.
    """
    # Basic exclusions
    sql = """
    INSERT INTO at_pick_outcomes_v2
    SELECT * FROM at_pick_outcomes
    WHERE NOT (pnl_pct = 0 AND status = 'FLAT')
      AND resolver_version != 'signflip_purge_20260'
    """
    n = run_sql(cursor, sql, dry_run, "INSERT outcomes")
    if not dry_run:
        print(f"Inserted {n} rows after basic exclusions")

    # Remove direct-linked dirty picks (pick_id = raw_picks.id)
    del_direct = """
    DELETE po FROM at_pick_outcomes_v2 po
    INNER JOIN trading_picks_v2 rp ON po.pick_id = rp.id
    WHERE rp.clean_status != 'CLEAN'
    """
    n1 = run_sql(cursor, del_direct, dry_run, "DELETE direct-linked dirty")
    if not dry_run:
        print(f"  Removed {n1} direct-linked dirty outcomes")

    # Remove fuzzy-linked dirty picks (symbol + strategy + same day).
    # We use a temp table of dirty keys to avoid a massive self-join.
    if dry_run:
        print("[DRY-RUN] Would build temp dirty_keys table and DELETE fuzzy-linked dirty outcomes")
        return

    cursor.execute("""
        CREATE TEMPORARY TABLE _dirty_keys (
            symbol VARCHAR(50) COLLATE utf8mb4_unicode_ci,
            strategy VARCHAR(200) COLLATE utf8mb4_unicode_ci,
            dt DATE,
            KEY(symbol, strategy, dt)
        ) ENGINE=MEMORY
    """)
    cursor.execute("""
        INSERT INTO _dirty_keys
        SELECT DISTINCT symbol, strategy, DATE(signal_timestamp)
        FROM trading_picks_v2
        WHERE clean_status != 'CLEAN'
          AND signal_timestamp IS NOT NULL
    """)
    cursor.execute("""
        DELETE po FROM at_pick_outcomes_v2 po
        INNER JOIN _dirty_keys dk
          ON po.symbol = dk.symbol
         AND po.strategy = dk.strategy
         AND DATE(po.resolved_at) = dk.dt
    """)
    n2 = cursor.rowcount
    print(f"  Removed {n2} fuzzy-linked dirty outcomes")
    # Temp table auto-drops on connection close; explicit drop can timeout
    # on flaky remote connections so we skip it.


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def print_stats(cursor, dry_run):
    if dry_run:
        # Show pre-build stats from source tables
        print("\n" + "=" * 60)
        print("SOURCE TABLE STATS (dry-run)")
        print("=" * 60)
        cursor.execute("SELECT COUNT(*) as c FROM at_raw_picks")
        print(f"at_raw_picks total: {cursor.fetchone()['c']:,}")
        cursor.execute("SELECT COUNT(*) as c FROM at_pick_outcomes")
        print(f"at_pick_outcomes total: {cursor.fetchone()['c']:,}")

        cursor.execute("""
            SELECT source_system, COUNT(*) as c
            FROM at_raw_picks
            GROUP BY source_system
            ORDER BY c DESC
            LIMIT 10
        """)
        print("\nTop sources in at_raw_picks:")
        for r in cursor.fetchall():
            print(f"  {r['source_system']}: {r['c']:,}")
        return

    print("\n" + "=" * 60)
    print("TRADING_PICKS_V2 SUMMARY")
    print("=" * 60)
    cursor.execute("SELECT COUNT(*) as c FROM trading_picks_v2")
    total = cursor.fetchone()["c"]
    print(f"Total rows: {total:,}")

    cursor.execute("""
        SELECT clean_status, COUNT(*) as c
        FROM trading_picks_v2
        GROUP BY clean_status
        ORDER BY c DESC
    """)
    for r in cursor.fetchall():
        pct = r["c"] / total * 100 if total else 0
        print(f"  {r['clean_status']}: {r['c']:,} ({pct:.1f}%)")

    cursor.execute("""
        SELECT COUNT(DISTINCT dedup_group_id) as c
        FROM trading_picks_v2
        WHERE dedup_group_id IS NOT NULL
    """)
    print(f"Duplicate groups: {cursor.fetchone()['c']:,}")

    print("\n" + "=" * 60)
    print("SOURCE DISTRIBUTION: v2 (CLEAN only) vs original")
    print("=" * 60)
    cursor.execute("""
        SELECT
            a.source_system,
            COUNT(*) as orig,
            SUM(CASE WHEN b.clean_status = 'CLEAN' THEN 1 ELSE 0 END) as clean
        FROM at_raw_picks a
        LEFT JOIN trading_picks_v2 b ON a.id = b.id
        GROUP BY a.source_system
        HAVING orig > 100
        ORDER BY orig DESC
    """)
    for r in cursor.fetchall():
        keep = r["clean"] or 0
        print(f"  {r['source_system']}: {r['orig']:,} → {keep:,} CLEAN")

    print("\n" + "=" * 60)
    print("AT_PICK_OUTCOMES_V2 SUMMARY")
    print("=" * 60)
    cursor.execute("SELECT COUNT(*) as c FROM at_pick_outcomes_v2")
    v2 = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM at_pick_outcomes")
    orig = cursor.fetchone()["c"]
    print(f"Original: {orig:,}")
    print(f"v2:       {v2:,}")
    print(f"Removed:  {orig - v2:,} ({(orig - v2) / orig * 100:.1f}%)")

    cursor.execute("""
        SELECT status, COUNT(*) as c
        FROM at_pick_outcomes_v2
        GROUP BY status
        ORDER BY c DESC
    """)
    print("\nStatus distribution:")
    for r in cursor.fetchall():
        print(f"  {r['status']}: {r['c']:,}")

    cursor.execute("""
        SELECT resolver_version, COUNT(*) as c
        FROM at_pick_outcomes_v2
        GROUP BY resolver_version
        ORDER BY c DESC
        LIMIT 6
    """)
    print("\nTop resolver_versions:")
    for r in cursor.fetchall():
        print(f"  {r['resolver_version']}: {r['c']:,}")

    print("\n" + "=" * 60)
    print("WIN RATE BY ASSET CLASS (v2)")
    print("=" * 60)
    cursor.execute("""
        SELECT
            asset_class,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as losses,
            ROUND(
                SUM(CASE WHEN status = 'WON' THEN 1 ELSE 0 END)
                / NULLIF(SUM(CASE WHEN status IN ('WON','LOST') THEN 1 ELSE 0 END), 0)
                * 100, 2
            ) as wr
        FROM at_pick_outcomes_v2
        GROUP BY asset_class
        ORDER BY total DESC
    """)
    for r in cursor.fetchall():
        wr = f"{r['wr']}%" if r["wr"] is not None else "N/A"
        print(
            f"  {r['asset_class']}: {r['total']:,} picks, "
            f"{r['wins'] or 0}W/{r['losses'] or 0}L, WR={wr}"
        )

    # Duplicate audit
    print("\n" + "=" * 60)
    print("DUPLICATE AUDIT")
    print("=" * 60)
    cursor.execute("""
        SELECT COUNT(*) as c FROM at_raw_picks
    """)
    raw_total = cursor.fetchone()["c"]
    cursor.execute("""
        SELECT COUNT(*) as c FROM trading_picks_v2 WHERE clean_status = 'DUPLICATE'
    """)
    dup_count = cursor.fetchone()["c"]
    print(f"Duplicates removed: {dup_count:,} / {raw_total:,} ({dup_count/raw_total*100:.1f}%)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build clean ledger v2")
    parser.add_argument("--execute", action="store_true", help="Apply changes to the database")
    args = parser.parse_args()

    dry_run = not args.execute
    mode = "DRY-RUN" if dry_run else "EXECUTE"
    print("=" * 60)
    print(f"build_clean_ledger_v2.py — {mode} MODE")
    if dry_run:
        print("No changes will be made. Use --execute to apply.")
    print("=" * 60)

    # Use autocommit so flaky remote connections don't lose large txns.
    conn = get_conn(autocommit=not dry_run)
    try:
        with conn.cursor() as cursor:
            # trading_picks_v2
            print("\n--- trading_picks_v2 ---")
            create_trading_picks_v2(cursor, dry_run)
            populate_trading_picks_v2(cursor, dry_run)
            mark_banned_source(cursor, dry_run)
            mark_backfill_corrupt(cursor, dry_run)
            mark_split_affected(cursor, dry_run)
            mark_stale_resolved(cursor, dry_run)
            mark_duplicates(cursor, dry_run)

            # at_pick_outcomes_v2
            print("\n--- at_pick_outcomes_v2 ---")
            create_pick_outcomes_v2(cursor, dry_run)
            populate_pick_outcomes_v2(cursor, dry_run)

            # stats
            print_stats(cursor, dry_run)

        if dry_run:
            print("\nDry-run complete. No changes committed.")
        else:
            print("\nDone.")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
