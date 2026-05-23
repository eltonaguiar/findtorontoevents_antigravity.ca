"""
tools/mysql_dedup_fix.py — Deduplicate trading_picks, fix confidence scale, add UNIQUE index.
================================================================================================

Problem: multiple aggregator runs generate fresh UUIDs for identical picks
(same symbol + direction + strategy + entry_price), bloating the table and
corrupting per-strategy win-rate counts.

Operations (in order):
  1. Report COUNT(*) before any changes.
  2. Delete newer duplicate rows — keeps the oldest (smallest created_at) for
     each (symbol, direction, strategy, entry_price) group.
  3. Fix confidence > 1.0 (scale artefact):
       confidence > 1 AND <= 10  → divide by 10
       confidence > 10            → divide by 100
  4. Add UNIQUE INDEX on (symbol, direction, strategy, entry_price, created_at)
     to prevent future dupes (skipped if index already exists).
  5. Report COUNT(*) after changes.

Usage:
  python tools/mysql_dedup_fix.py            # dry-run (no changes)
  python tools/mysql_dedup_fix.py --apply    # execute changes

Env vars (all have defaults matching ejaguiar1_stocks conventions):
  AUDIT_DB_HOST   default: mysql.50webs.com
  AUDIT_DB_USER   default: ejaguiar1_stocks
  AUDIT_DB_PASS   (required for real connections)
  AUDIT_DB_NAME   default: ejaguiar1_stocks
"""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("mysql_dedup_fix")

# ── Config ────────────────────────────────────────────────────────────────────

DB_HOST = os.getenv("AUDIT_DB_HOST", "mysql.50webs.com")
DB_PORT = int(os.getenv("AUDIT_DB_PORT", "3306"))
DB_USER = os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks")
DB_PASS = os.getenv("AUDIT_DB_PASS", "")
DB_NAME = os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks")

CONNECT_TIMEOUT = 15
INDEX_NAME = "uq_trading_picks_dedup"


# ── Connection ────────────────────────────────────────────────────────────────

def _connect():
    """Create and return a pymysql connection (autocommit OFF for explicit control)."""
    try:
        import pymysql
    except ImportError:
        log.error("pymysql is not installed. Run: pip install pymysql")
        sys.exit(1)

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=CONNECT_TIMEOUT,
        read_timeout=60,
        write_timeout=60,
        charset="utf8mb4",
        autocommit=False,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_one(cur, sql, params=()):
    """Execute a SELECT and return the first row, or None on error."""
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    except Exception as exc:
        log.error("Query failed: %s | error: %s", sql.strip()[:120], exc)
        return None


def _count_rows(cur):
    """Return total row count in trading_picks."""
    row = _fetch_one(cur, "SELECT COUNT(*) FROM trading_picks")
    return row[0] if row else -1


def _count_dupe_groups(cur):
    """Return number of duplicate groups (groups with >1 row for same key)."""
    sql = """
        SELECT COUNT(*) FROM (
            SELECT symbol, direction, strategy, entry_price
            FROM trading_picks
            GROUP BY symbol, direction, strategy, entry_price
            HAVING COUNT(*) > 1
        ) AS dupes
    """
    row = _fetch_one(cur, sql)
    return row[0] if row else -1


def _count_dupe_rows(cur):
    """Return total number of extra (non-oldest) duplicate rows to be deleted."""
    sql = """
        SELECT COUNT(*) FROM trading_picks tp
        WHERE tp.id NOT IN (
            SELECT keeper FROM (
                SELECT MIN(id) AS keeper
                FROM trading_picks
                GROUP BY symbol, direction, strategy, entry_price
            ) AS keepers
        )
        AND (symbol, direction, strategy, entry_price) IN (
            SELECT symbol, direction, strategy, entry_price
            FROM trading_picks
            GROUP BY symbol, direction, strategy, entry_price
            HAVING COUNT(*) > 1
        )
    """
    row = _fetch_one(cur, sql)
    return row[0] if row else -1


def _count_confidence_bad(cur):
    """Count rows where confidence is out of [0,1] scale."""
    sql = "SELECT COUNT(*) FROM trading_picks WHERE confidence > 1"
    row = _fetch_one(cur, sql)
    return row[0] if row else -1


def _index_exists(cur):
    """Check whether the dedup UNIQUE index already exists on this table."""
    sql = """
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE table_schema = %s
          AND table_name   = 'trading_picks'
          AND index_name   = %s
    """
    row = _fetch_one(cur, sql, (DB_NAME, INDEX_NAME))
    return (row[0] if row else 0) > 0


# ── Core operations ───────────────────────────────────────────────────────────

def step_delete_dupes(cur, dry_run: bool) -> int:
    """
    Delete newer duplicate rows, keeping the oldest (MIN id) per
    (symbol, direction, strategy, entry_price) group.

    MySQL does not allow DELETE ... WHERE id NOT IN (SELECT ... FROM same table)
    directly, so we use a subquery alias trick to work around the limitation.

    Returns rows deleted (or rows that would be deleted in dry-run).
    """
    # How many would be deleted?
    dupe_count = _count_dupe_rows(cur)
    if dupe_count <= 0:
        log.info("Duplicates: none found — nothing to delete.")
        return 0

    log.info("Duplicates: %d extra rows found across %d groups.",
             dupe_count, _count_dupe_groups(cur))

    if dry_run:
        log.info("[DRY-RUN] Would delete %d duplicate rows.", dupe_count)
        return dupe_count

    # Build the list of keeper IDs using a temp-table workaround that MySQL allows.
    # We materialise the subquery as a derived table aliased as `keepers`.
    delete_sql = """
        DELETE tp FROM trading_picks tp
        INNER JOIN (
            SELECT MIN(id) AS keeper_id, symbol, direction, strategy, entry_price
            FROM trading_picks
            GROUP BY symbol, direction, strategy, entry_price
            HAVING COUNT(*) > 1
        ) AS dupes
            ON  tp.symbol       = dupes.symbol
            AND tp.direction    = dupes.direction
            AND tp.strategy     = dupes.strategy
            AND tp.entry_price  = dupes.entry_price
            AND tp.id          != dupes.keeper_id
    """
    try:
        cur.execute(delete_sql)
        deleted = cur.rowcount
        log.info("Deleted %d duplicate rows.", deleted)
        return deleted
    except Exception as exc:
        log.error("Delete duplicates failed: %s", exc)
        raise


def step_fix_confidence(cur, dry_run: bool) -> dict:
    """
    Fix confidence values that are on the wrong scale:
      - confidence > 1 AND <= 10  → divide by 10   (e.g. 8.5 → 0.85)
      - confidence > 10            → divide by 100  (e.g. 85  → 0.85)

    Returns dict with {'div10': rows_affected, 'div100': rows_affected}.
    """
    bad_count = _count_confidence_bad(cur)
    if bad_count <= 0:
        log.info("Confidence: all values are in [0,1] scale — no fix needed.")
        return {"div10": 0, "div100": 0}

    log.info("Confidence: %d rows have confidence > 1.0.", bad_count)

    if dry_run:
        # Count each band for reporting.
        r10 = _fetch_one(cur,
            "SELECT COUNT(*) FROM trading_picks WHERE confidence > 1 AND confidence <= 10")
        r100 = _fetch_one(cur,
            "SELECT COUNT(*) FROM trading_picks WHERE confidence > 10")
        n10 = r10[0] if r10 else 0
        n100 = r100[0] if r100 else 0
        log.info("[DRY-RUN] Would divide-by-10: %d rows, divide-by-100: %d rows.", n10, n100)
        return {"div10": n10, "div100": n100}

    results = {}
    for band, sql in [
        ("div10",  "UPDATE trading_picks SET confidence = confidence / 10  WHERE confidence > 1 AND confidence <= 10"),
        ("div100", "UPDATE trading_picks SET confidence = confidence / 100 WHERE confidence > 10"),
    ]:
        try:
            cur.execute(sql)
            results[band] = cur.rowcount
            log.info("Confidence fix (%s): %d rows updated.", band, cur.rowcount)
        except Exception as exc:
            log.error("Confidence fix (%s) failed: %s", band, exc)
            results[band] = 0
            # Non-fatal: log and continue.

    return results


def step_add_unique_index(cur, dry_run: bool) -> bool:
    """
    Add UNIQUE INDEX on (symbol, direction, strategy, entry_price, created_at)
    if it does not already exist.

    Note: entry_price alone would be too tight (same price, different symbol),
    and including created_at allows the same strategy to re-enter the same
    symbol at the same price on a different date, which is legitimate.

    Returns True if the index was (or would be) created, False if already present.
    """
    if _index_exists(cur):
        log.info("Index '%s' already exists — skipping CREATE.", INDEX_NAME)
        return False

    create_sql = """
        CREATE UNIQUE INDEX {name}
        ON trading_picks (symbol, direction, strategy, entry_price, created_at)
    """.format(name=INDEX_NAME)

    if dry_run:
        log.info("[DRY-RUN] Would create UNIQUE INDEX '%s' on "
                 "(symbol, direction, strategy, entry_price, created_at).", INDEX_NAME)
        return True

    try:
        cur.execute(create_sql)
        log.info("Created UNIQUE INDEX '%s'.", INDEX_NAME)
        return True
    except Exception as exc:
        # If the index creation fails (e.g. still-existing dupes prevent it),
        # log the error but do not abort — the duplicates may have been cleaned
        # already and this is best-effort hardening.
        log.error("Failed to create UNIQUE INDEX '%s': %s", INDEX_NAME, exc)
        log.error("Tip: re-run with --apply after confirming dedup succeeded.")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deduplicate trading_picks, fix confidence scale, add UNIQUE index."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute changes. Default is dry-run (report only, no writes).",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    mode_label = "DRY-RUN" if dry_run else "APPLY"
    log.info("=== mysql_dedup_fix  mode=%s ===", mode_label)
    log.info("Host: %s  DB: %s  User: %s", DB_HOST, DB_NAME, DB_USER)

    conn = None
    exit_code = 0

    try:
        conn = _connect()
        cur = conn.cursor()

        # ── Step 0: baseline count ────────────────────────────────────────────
        count_before = _count_rows(cur)
        log.info("BEFORE: trading_picks row count = %d", count_before)

        # ── Step 1: delete duplicates ─────────────────────────────────────────
        try:
            deleted = step_delete_dupes(cur, dry_run)
        except Exception as exc:
            log.error("Dedup step aborted: %s — rolling back.", exc)
            conn.rollback()
            exit_code = 1
            return

        # ── Step 2: fix confidence scale ──────────────────────────────────────
        conf_results = step_fix_confidence(cur, dry_run)

        # ── Step 3: commit data changes before DDL ────────────────────────────
        if not dry_run:
            conn.commit()
            log.info("Data changes committed.")

        # ── Step 4: add UNIQUE index (DDL — its own implicit commit in MySQL) ──
        step_add_unique_index(cur, dry_run)

        # ── Step 5: final count ───────────────────────────────────────────────
        count_after = _count_rows(cur)
        log.info("AFTER:  trading_picks row count = %d", count_after)

        # ── Summary ───────────────────────────────────────────────────────────
        log.info("=== SUMMARY (%s) ===", mode_label)
        log.info("  Rows before            : %d", count_before)
        log.info("  Duplicate rows removed  : %d", deleted if not dry_run else 0)
        log.info("  Rows after             : %d", count_after)
        log.info("  Confidence / 10 fixed  : %d rows", conf_results.get("div10", 0))
        log.info("  Confidence / 100 fixed : %d rows", conf_results.get("div100", 0))
        if dry_run:
            log.info("  (No changes applied — re-run with --apply to execute)")

    except Exception as exc:
        log.error("Unhandled error: %s", exc)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        exit_code = 1

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
