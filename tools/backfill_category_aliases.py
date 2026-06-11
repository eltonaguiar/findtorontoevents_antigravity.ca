#!/usr/bin/env python3
"""One-shot backfill: normalize trading_picks.category aliases to canonical.

INCIDENT_OVERALL#88 (2026-06-11) — the category case-mess was actively
regrowing: 129 new 'stocks' rows since 2026-06-01 plus 'stock' / 'penny' /
'pennystock' variants, all invisible to every LOWER(category)='equity'
filter, gate, and per-class PF/WR recompute. The writer-side fix lives in
alpha_engine/mysql_trading_sync.py (_CATEGORY_CANONICAL_MAP at the ingest
chokepoint); this script is the companion one-shot backfill for the rows
that already leaked through.

CANONICAL form is UPPERCASE — matches the majority consumer convention
(tools/backfill_unknown_category.py::_CATEGORY_MAP,
audit_trail/dashboard_generator.py::_ASSET_CLASS_HINTS / _CANONICAL,
quality_gates `.upper()` comparisons, and mysql_trading_sync's own
Canonical-CRYPTO bucket). Only TRUE aliases are rewritten (e.g.
'stocks' -> 'EQUITY'); casing-only variants ('equity' vs 'EQUITY') are
left alone because the table collation is case-insensitive and every SQL
consumer uses LOWER(category) — rewriting them would churn ~23k rows for
zero read-side benefit.

NULL/empty/UNKNOWN rows are NOT handled here — that is
tools/backfill_unknown_category.py's job (symbol-pattern auto-tag).
'meme' and 'index' are intentionally preserved: downstream normalizers map
them with env-configurable policy (ASSET_CLASS_MAP_MEME_TO_CRYPTO,
index->FUTURES in dashboard_generator).

Safety:
  * Dry-run by DEFAULT — prints the per-alias plan and exits without writing.
  * --apply first snapshots every affected row to a timestamped backup table
    in ejaguiar1_backups (tools.db_env.get_backups_creds — mandatory target
    before mutating ejaguiar1_stocks per project safety rule), then applies
    chunked UPDATE transactions (commit per chunk) keyed by primary key `id`
    with a category guard so concurrent writers are never clobbered.
  * --limit caps total rows touched per run.

Usage:
  python3 tools/backfill_category_aliases.py                 # dry-run (default)
  python3 tools/backfill_category_aliases.py --apply         # backup + UPDATE
  python3 tools/backfill_category_aliases.py --apply --chunk-size 200
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymysql

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.db_env import get_backups_creds, get_stocks_creds  # noqa: E402

# Alias (lowercase) -> canonical. Mirrors the TRUE-alias subset of
# alpha_engine/mysql_trading_sync.py::_CATEGORY_CANONICAL_MAP — i.e. only
# keys whose lowercase form differs from the canonical's lowercase form.
# Casing-only variants are deliberately excluded (see module docstring).
ALIAS_TO_CANONICAL: dict[str, str] = {
    # EQUITY aliases — the active regrowth (incident's 144-row core).
    "stock": "EQUITY",
    "stocks": "EQUITY",
    "share": "EQUITY",
    "shares": "EQUITY",
    "penny": "EQUITY",
    "pennystock": "EQUITY",
    "pennystocks": "EQUITY",
    # Other known aliases, same map as the writer-side fix.
    "cryptocurrency": "CRYPTO",
    "fx": "FOREX",
    "currency": "FOREX",
    "currencies": "FOREX",
    "bonds": "BOND",
    "future": "FUTURES",
    "commodities": "COMMODITY",
}

BACKUP_TABLE_PREFIX = "trading_picks_category_alias_backup"
DEFAULT_CHUNK = 500


def _connect(creds: dict) -> pymysql.connections.Connection:
    kwargs = {
        k: v
        for k, v in creds.items()
        if k in ("host", "user", "password", "database", "port", "connect_timeout")
    }
    return pymysql.connect(**kwargs, cursorclass=pymysql.cursors.DictCursor)


def fetch_affected_rows(cur, limit: int) -> list[dict]:
    placeholders = ",".join(["%s"] * len(ALIAS_TO_CANONICAL))
    cur.execute(
        f"""
        SELECT id, symbol, category, source_system, strategy, created_at
        FROM trading_picks
        WHERE LOWER(TRIM(category)) IN ({placeholders})
        ORDER BY created_at
        LIMIT %s
        """,
        (*ALIAS_TO_CANONICAL.keys(), limit),
    )
    return list(cur.fetchall())


def plan_updates(rows: list[dict]) -> list[tuple[str, str, str]]:
    """Returns (new_category, id, old_category_exact) triples."""
    out: list[tuple[str, str, str]] = []
    for row in rows:
        old = str(row.get("category") or "")
        key = old.strip().lower()
        new = ALIAS_TO_CANONICAL.get(key)
        if new and new != old:
            out.append((new, str(row["id"]), old))
    return out


def print_plan(rows: list[dict]) -> None:
    by_alias: dict[tuple[str, str], int] = {}
    for row in rows:
        old = str(row.get("category") or "")
        key = old.strip().lower()
        new = ALIAS_TO_CANONICAL.get(key, "?")
        by_alias[(old, new)] = by_alias.get((old, new), 0) + 1
    print(f"plan: {len(rows)} rows across {len(by_alias)} alias buckets")
    for (old, new), n in sorted(by_alias.items(), key=lambda kv: -kv[1]):
        print(f"  {old!r:16} -> {new!r:12} {n:6d} rows")


def backup_rows(rows: list[dict], updates: list[tuple[str, str, str]],
                chunk_size: int) -> str:
    """Snapshot affected rows to a timestamped table in ejaguiar1_backups."""
    new_by_id = {pid: new for (new, pid, _old) in updates}
    table = (
        f"{BACKUP_TABLE_PREFIX}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    bconn = _connect(get_backups_creds())
    try:
        bcur = bconn.cursor()
        bcur.execute(
            f"""
            CREATE TABLE {table} (
                id VARCHAR(100) NOT NULL,
                symbol VARCHAR(20),
                old_category VARCHAR(20),
                new_category VARCHAR(20),
                source_system VARCHAR(50),
                strategy VARCHAR(100),
                created_at DATETIME,
                backed_up_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
            """
        )
        payload = [
            (
                str(r["id"]),
                r.get("symbol"),
                r.get("category"),
                new_by_id.get(str(r["id"])),
                r.get("source_system"),
                r.get("strategy"),
                r.get("created_at"),
            )
            for r in rows
            if str(r["id"]) in new_by_id
        ]
        for i in range(0, len(payload), chunk_size):
            bcur.executemany(
                f"INSERT INTO {table} (id, symbol, old_category, new_category,"
                " source_system, strategy, created_at)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                payload[i:i + chunk_size],
            )
            bconn.commit()
        print(f"backup: {len(payload)} rows -> ejaguiar1_backups.{table}")
    finally:
        bconn.close()
    return table


def apply_updates(conn, cur, updates: list[tuple[str, str, str]],
                  chunk_size: int) -> int:
    """Chunked UPDATE transactions. The WHERE clause re-checks the exact old
    category so a row mutated by a concurrent writer between SELECT and
    UPDATE is skipped, never clobbered."""
    touched = 0
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i + chunk_size]
        cur.executemany(
            "UPDATE trading_picks SET category = %s "
            "WHERE id = %s AND category = %s",
            chunk,
        )
        conn.commit()
        touched += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        print(f"  chunk {i // chunk_size + 1}: "
              f"{min(i + chunk_size, len(updates))}/{len(updates)} submitted")
    return touched


def verify_remaining(cur) -> int:
    placeholders = ",".join(["%s"] * len(ALIAS_TO_CANONICAL))
    cur.execute(
        f"SELECT COUNT(*) AS n FROM trading_picks "
        f"WHERE LOWER(TRIM(category)) IN ({placeholders})",
        tuple(ALIAS_TO_CANONICAL.keys()),
    )
    return int(cur.fetchone()["n"])


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Normalize trading_picks.category aliases to canonical "
                    "(INCIDENT_OVERALL#88). Dry-run by default.")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (backup table + chunked UPDATEs); "
                         "default is dry-run")
    ap.add_argument("--limit", type=int, default=10000,
                    help="max rows per run (default 10000)")
    ap.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK,
                    help=f"rows per transaction (default {DEFAULT_CHUNK})")
    args = ap.parse_args()

    conn = _connect(get_stocks_creds())
    try:
        cur = conn.cursor()
        rows = fetch_affected_rows(cur, args.limit)
        if not rows:
            print("nothing to do: 0 alias rows found")
            return 0

        print_plan(rows)
        updates = plan_updates(rows)

        if not args.apply:
            print(f"\nDRY-RUN (default): {len(updates)} rows would be updated."
                  " Re-run with --apply to write.")
            return 0

        if not updates:
            print("nothing to do: plan resolved to 0 updates")
            return 0

        # Mandatory backup snapshot BEFORE any mutation.
        backup_rows(rows, updates, args.chunk_size)

        touched = apply_updates(conn, cur, updates, args.chunk_size)
        remaining = verify_remaining(cur)
        print(f"\napply: {touched} rows updated; {remaining} alias rows remain"
              f" (concurrent inserts or rows beyond --limit)")
        if remaining:
            print("re-run to sweep the remainder (writer-side fix in "
                  "mysql_trading_sync.py prevents new regrowth)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
