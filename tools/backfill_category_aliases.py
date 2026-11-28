#!/usr/bin/env python3
"""Normalize every trading_picks.category label to ONE canonical enum.

2026-11-28 — a live survey found 20 distinct raw values for 11 canonical
classes: case forks ('crypto' 16,113 + 'CRYPTO' 27,818), plus 'index',
'meme', 'managed_futures' and 'prediction_market' as separate lowercase
buckets. Any consumer that string-compares a category — rather than
LOWER()-ing it — sees two different equities, two different cryptos, and
silently drops whichever fork it did not expect.

CANONICAL enum (`.claude/skills/db-schema/SKILL.md` +
`tools/asset_class_audit_checks.py::CANONICAL` + `CANONICAL_ASSET_CLASSES`):

    CRYPTO EQUITY FOREX ETF BOND COMMODITY FUTURES
    INDEX PREDICTION_MARKET MEMECOIN PENNY_STOCK

UPPERCASE is the majority consumer convention (dashboard_generator
_ASSET_CLASS_HINTS / _CANONICAL, quality_gates `.upper()` compares,
mysql_trading_sync's Canonical-CRYPTO bucket). The pre-2026-11-28 version of
this script deliberately skipped casing-only variants as "zero read-side
benefit" — that was wrong: it left 45,236 rows in a second fork that every
exact-match consumer misses.

Empty/NULL category is NOT handled here (it is a missing label, not a
label): `tools/backfill_unknown_category.py` owns symbol-pattern auto-tag.
This script reports those rows and leaves them alone.

Safety:
  * Dry-run by DEFAULT — prints the per-label plan and exits without writing.
  * --apply first snapshots the affected rows to a timestamped table in
    ejaguiar1_backups (tools.db_env.get_backups_creds — mandatory target
    before mutating ejaguiar1_stocks per project safety rule), then applies
    one set-based UPDATE per raw label inside its own transaction.
  * Updates are keyed on the EXACT byte value (CAST(category AS BINARY)) so
    the case-insensitive collation can never widen a rewrite beyond the
    bucket being normalized, and a concurrent writer is reported
    (rowcount delta) rather than clobbered.
  * --limit caps rows touched per label per run.

Companion row-level snapshot (all columns, restorable):
  python3 tools/safe_db_archive.py --source-table trading_picks \\
      --purpose category_enum --where "<same predicate>"

Usage:
  python3 tools/backfill_category_aliases.py                 # dry-run (default)
  python3 tools/backfill_category_aliases.py --apply         # backup + UPDATE
  python3 tools/backfill_category_aliases.py --apply --limit 5000
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

# The one canonical enum. Must stay in sync with
# tools/asset_class_audit_checks.py::CANONICAL.
CANONICAL_ENUM: tuple[str, ...] = (
    "CRYPTO",
    "EQUITY",
    "FOREX",
    "ETF",
    "BOND",
    "COMMODITY",
    "FUTURES",
    "INDEX",
    "PREDICTION_MARKET",
    "MEMECOIN",
    "PENNY_STOCK",
)

# Alias (lowercase) -> canonical. Seeded with `canonical.lower() -> canonical`
# so casing forks are normalized too, then extended with true synonyms.
# Mirrors alpha_engine/mysql_trading_sync.py::_CATEGORY_CANONICAL_MAP — the
# ingest chokepoint that stops the drift regrowing.
ALIAS_TO_CANONICAL: dict[str, str] = {c.lower(): c for c in CANONICAL_ENUM}
ALIAS_TO_CANONICAL.update({
    # EQUITY aliases
    "stock": "EQUITY",
    "stocks": "EQUITY",
    "share": "EQUITY",
    "shares": "EQUITY",
    "penny": "EQUITY",
    "pennystock": "EQUITY",
    "pennystocks": "EQUITY",
    # CRYPTO
    "cryptocurrency": "CRYPTO",
    "meme": "MEMECOIN",
    "meme_coin": "MEMECOIN",
    "memecoin": "MEMECOIN",
    # FOREX
    "fx": "FOREX",
    "currency": "FOREX",
    "currencies": "FOREX",
    # BOND / FUTURES / COMMODITY
    "bonds": "BOND",
    "future": "FUTURES",
    "managed_futures": "FUTURES",
    "commodities": "COMMODITY",
    # INDEX / PREDICTION_MARKET
    "index": "INDEX",
    "prediction_markets": "PREDICTION_MARKET",
})

BACKUP_TABLE_PREFIX = "trading_picks_category_alias_backup"
DEFAULT_CHUNK = 500


def _connect(creds: dict) -> pymysql.connections.Connection:
    kwargs = {
        k: v
        for k, v in creds.items()
        if k in ("host", "user", "password", "database", "port",
                 "connect_timeout", "read_timeout")
    }
    return pymysql.connect(**kwargs, cursorclass=pymysql.cursors.DictCursor)


def survey(cur) -> list[tuple[str, int]]:
    """Exact (case-sensitive) label -> row count. BINARY keeps the forks

    distinct — the column collation is utf8mb4_unicode_ci, so a plain
    GROUP BY would merge 'crypto' and 'CRYPTO'.
    """
    cur.execute(
        """
        SELECT CAST(category AS BINARY) AS raw, COUNT(*) AS n
        FROM trading_picks
        GROUP BY CAST(category AS BINARY)
        ORDER BY n DESC
        """
    )
    return [(r["raw"].decode("utf-8", "replace"), int(r["n"])) for r in cur.fetchall()]


def plan(raw_survey: list[tuple[str, int]]):
    """Split the survey into (to_rewrite, already_canonical, empty, unmapped)."""
    to_rewrite: list[tuple[str, str, int]] = []
    canonical: list[tuple[str, int]] = []
    empty: list[tuple[str, int]] = []
    unmapped: list[tuple[str, int]] = []
    for raw, n in raw_survey:
        if raw.strip() == "":
            empty.append((raw, n))
            continue
        if raw in CANONICAL_ENUM:
            canonical.append((raw, n))
            continue
        target = ALIAS_TO_CANONICAL.get(raw.strip().lower())
        if target:
            to_rewrite.append((raw, target, n))
        else:
            unmapped.append((raw, n))
    return to_rewrite, canonical, empty, unmapped


def print_plan(to_rewrite, canonical, empty, unmapped) -> None:
    print(f"plan: {len(to_rewrite)} label(s), "
          f"{sum(n for _, _, n in to_rewrite):,} rows to rewrite")
    for raw, target, n in to_rewrite:
        print(f"  {raw!r:20} -> {target!r:20} {n:>7,} rows")
    if canonical:
        print(f"already canonical: {len(canonical)} label(s), "
              f"{sum(n for _, n in canonical):,} rows")
        for raw, n in canonical:
            print(f"  {raw!r:20} {'(unchanged)':<20} {n:>7,} rows")
    if empty:
        print(f"EMPTY label (not normalised — tools/backfill_unknown_category.py "
              f"owns these): {sum(n for _, n in empty):,} rows")
    if unmapped:
        print(f"UNMAPPED ({len(unmapped)}) — add to ALIAS_TO_CANONICAL if legit:")
        for raw, n in unmapped:
            print(f"  {raw!r:20} {'???':<20} {n:>7,} rows")


def backup_rows(conn, cur, to_rewrite, chunk_size: int) -> str:
    """Snapshot every affected row (id + old/new label) into ejaguiar1_backups."""
    target_by_raw = {raw: target for raw, target, _n in to_rewrite}
    table = (
        f"{BACKUP_TABLE_PREFIX}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    bconn = _connect(get_backups_creds())
    copied = 0
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
        for raw, _target, _n in to_rewrite:
            cur.execute(
                """
                SELECT id, symbol, category, source_system, strategy, created_at
                FROM trading_picks
                WHERE CAST(category AS BINARY) = %s
                """,
                (raw.encode("utf-8"),),
            )
            while True:
                batch = cur.fetchmany(chunk_size)
                if not batch:
                    break
                payload = [
                    (
                        str(r["id"]),
                        r.get("symbol"),
                        r.get("category"),
                        target_by_raw.get(raw),
                        r.get("source_system"),
                        r.get("strategy"),
                        r.get("created_at"),
                    )
                    for r in batch
                ]
                bcur.executemany(
                    f"INSERT INTO {table} (id, symbol, old_category, new_category,"
                    " source_system, strategy, created_at)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    payload,
                )
                bconn.commit()
                copied += len(payload)
                print(f"  backup {copied:,} rows ({raw!r})")
        print(f"backup: {copied:,} rows -> ejaguiar1_backups.{table}")
    finally:
        bconn.close()
    return table


def apply_updates(conn, cur, to_rewrite, limit: int) -> int:
    """One set-based UPDATE per raw label, keyed on the exact byte value.

    The BINARY predicate is what keeps the case-insensitive collation from
    widening the rewrite: 'crypto' and 'CRYPTO' are separate statements.
    """
    touched = 0
    for raw, target, expected in to_rewrite:
        sql = (
            "UPDATE trading_picks SET category = %s "
            "WHERE CAST(category AS BINARY) = %s"
        )
        params: tuple = (target, raw.encode("utf-8"))
        if limit:
            sql += " LIMIT %s"
            params = (target, raw.encode("utf-8"), limit)
        cur.execute(sql, params)
        conn.commit()
        n = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        touched += n
        delta = "" if not limit else f" (capped at {limit})"
        flag = "" if n == expected or limit else f"  DELTA vs plan {expected:,}"
        print(f"  {raw!r:20} -> {target!r:20} {n:>7,} rows{delta}{flag}")
    return touched


def verify(cur) -> list[tuple[str, int]]:
    return survey(cur)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Normalize every trading_picks.category label to the one "
                    "canonical uppercase enum. Dry-run by default.")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (backup table + set-based UPDATEs); "
                         "default is dry-run")
    ap.add_argument("--limit", type=int, default=0,
                    help="max rows per label per run (0 = no cap)")
    ap.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK,
                    help=f"rows per backup insert batch (default {DEFAULT_CHUNK})")
    args = ap.parse_args()

    conn = _connect(get_stocks_creds())
    try:
        cur = conn.cursor()
        raw_survey = survey(cur)
        to_rewrite, canonical, empty, unmapped = plan(raw_survey)
        print_plan(to_rewrite, canonical, empty, unmapped)

        if not to_rewrite:
            print("\nnothing to do: every non-empty category is already canonical")
            return 0

        if not args.apply:
            print(f"\nDRY-RUN (default): "
                  f"{sum(n for _, _, n in to_rewrite):,} rows would be updated."
                  " Re-run with --apply to write.")
            return 0

        # Mandatory backup snapshot BEFORE any mutation.
        table = backup_rows(conn, cur, to_rewrite, args.chunk_size)

        print("\napply:")
        touched = apply_updates(conn, cur, to_rewrite, args.limit)

        after = verify(cur)
        drift = [(r, n) for r, n in after if r.strip() and r not in CANONICAL_ENUM]
        print(f"\napply: {touched:,} rows updated")
        print(f"rollback: ejaguiar1_backups.{table} "
              f"(UPDATE trading_picks p JOIN {table} b ON p.id=b.id "
              f"SET p.category=b.old_category)")
        print(f"\npost-state: {len(after)} distinct labels")
        for r, n in after:
            mark = "" if (r in CANONICAL_ENUM or not r.strip()) else "   <-- still off-enum"
            print(f"  {r!r:24} {n:>7,}{mark}")
        if drift:
            print(f"\nWARNING: {len(drift)} label(s) still off-enum "
                  f"(concurrent writers or --limit cap) — re-run to sweep")
            return 0
        print("\nOK: every non-empty label is now a member of the canonical enum")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
