#!/usr/bin/env python3
"""
repair_data_integrity.py — Verify + update resolved incident statuses in MySQL.

Run: DB_PASS_STOCKS=<pass> python3 tools/repair_data_integrity.py

Checks 11 incidents that were OPEN/TRIAGED but have been verified RESOLVED
against the live database. Prints a report and optionally updates the
INCIDENT_* tables to mark them RESOLVED.

Safe: read-only by default. Pass --write to update statuses.
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timezone

import pymysql

DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_NAME = os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks")
DB_PASS = os.environ.get("DB_PASS_STOCKS", "")

CLASSES = [
    "OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX",
    "COMMODITIES", "BONDS", "FUTURES", "PENNY",
]

# COT dedup systems — mirror of audit_trail/quality_gates.py COT_DEDUP_SYSTEMS
_COT_DEDUP_STRATS = frozenset({
    "multi_asset_cot",
    "cot_positioning",
    "cftc_cot_commercial_signal",
    "multi_asset_copytrader",
})

# Canonical terminal statuses — keep in sync with tools/standardize_statuses.py
_CANONICAL_STATUSES = frozenset({
    "TP_HIT", "SL_HIT", "LOST", "EXPIRED", "TIME_EXIT", "ACTIVE", "OPEN",
})

# Status mapping rules — subset of tools/standardize_statuses.py STATUS_MAPPINGS
# Each: (from_status, condition_sql, to_status, exit_reason_override)
_STATUS_MAPPINGS = [
    ("WIN",        "pnl_pct > 0",                      "TP_HIT",    "STATUS_STANDARDIZED"),
    ("WIN",        "pnl_pct <= 0 OR pnl_pct IS NULL",  "LOST",      "STATUS_STANDARDIZED"),
    ("WON",        "pnl_pct > 0",                      "TP_HIT",    "STATUS_STANDARDIZED"),
    ("WON",        "pnl_pct <= 0 OR pnl_pct IS NULL",  "LOST",      "STATUS_STANDARDIZED"),
    ("LOSS",       "pnl_pct < 0",                      "LOST",      "STATUS_STANDARDIZED"),
    ("LOSS",       "pnl_pct >= 0 OR pnl_pct IS NULL",  "TP_HIT",    "STATUS_STANDARDIZED"),
    ("CLOSED_SL",  "1=1",                              "SL_HIT",    "STATUS_STANDARDIZED"),
    ("CLOSED_TP",  "1=1",                              "TP_HIT",    "STATUS_STANDARDIZED"),
    ("SIGNAL",     "1=1",                              "EXPIRED",   "STATUS_STANDARDIZED"),
    ("FLAT",       "1=1",                              "TIME_EXIT", "STATUS_STANDARDIZED"),
    ("STALE",      "1=1",                              "EXPIRED",   "STATUS_STANDARDIZED"),
]


def connect():
    if not DB_PASS:
        print("ERROR: DB_PASS_STOCKS env var not set")
        sys.exit(1)
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS,
        database=DB_NAME, port=3306, connect_timeout=20,
        cursorclass=pymysql.cursors.DictCursor,
    )


# ── Repair functions (must be defined BEFORE CHECKS since they're referenced there) ─


def _repair_pnl_status_mismatch(cur) -> int:
    """PR #8b: Fix status mismatch — status contradicts pnl_pct sign.

    Separate from sign-flip: these rows have CORRECT pnl_pct (matches price-based
    calculation) but the wrong status label (e.g., TP_HIT with -8% PnL).
    Flip the status to match the PnL sign.

    No constraint drop needed — we're only changing the status, not PnL.
    Idempotent: skips rows already tagged with [STATUS_FLIP_FIXED].
    Returns number of rows repaired.
    """
    cur.execute(
        "SELECT COUNT(*) as cnt FROM trading_picks "
        "WHERE status IN ('WON','TP_HIT','closed_win') AND pnl_pct < -0.01 "
        "  AND (exit_reason IS NULL OR exit_reason NOT LIKE '%STATUS_FLIP_FIXED%')"
    )
    neg_pnl_winners = cur.fetchone()["cnt"]

    cur.execute(
        "SELECT COUNT(*) as cnt FROM trading_picks "
        "WHERE status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0.01 "
        "  AND (exit_reason IS NULL OR exit_reason NOT LIKE '%STATUS_FLIP_FIXED%')"
    )
    pos_pnl_losers = cur.fetchone()["cnt"]

    if neg_pnl_winners + pos_pnl_losers == 0:
        return 0

    total = 0
    # Winners with negative PnL → they're actually losers
    if neg_pnl_winners > 0:
        cur.execute(
            "UPDATE trading_picks "
            "SET status = CASE "
            "    WHEN status IN ('WON','closed_win') THEN 'LOST' "
            "    ELSE 'SL_HIT' "
            "  END, "
            "  exit_reason = CASE "
            "    WHEN exit_reason IS NULL OR exit_reason = '' "
            "      THEN 'STATUS_FLIP_FIXED' "
            "    ELSE CONCAT(exit_reason, ' [STATUS_FLIP_FIXED]') "
            "  END, "
            "  updated_at = NOW() "
            "WHERE status IN ('WON','TP_HIT','closed_win') AND pnl_pct < -0.01 "
            "  AND (exit_reason IS NULL OR exit_reason NOT LIKE '%STATUS_FLIP_FIXED%')"
        )
        total += cur.rowcount

    # Losers with positive PnL → they're actually winners
    if pos_pnl_losers > 0:
        cur.execute(
            "UPDATE trading_picks "
            "SET status = CASE "
            "    WHEN status IN ('LOST','closed_loss') THEN 'TP_HIT' "
            "    ELSE 'TP_HIT' "
            "  END, "
            "  exit_reason = CASE "
            "    WHEN exit_reason IS NULL OR exit_reason = '' "
            "      THEN 'STATUS_FLIP_FIXED' "
            "    ELSE CONCAT(exit_reason, ' [STATUS_FLIP_FIXED]') "
            "  END, "
            "  updated_at = NOW() "
            "WHERE status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0.01 "
            "  AND (exit_reason IS NULL OR exit_reason NOT LIKE '%STATUS_FLIP_FIXED%')"
        )
        total += cur.rowcount

    return total


def _repair_pnl_sign_flip(cur) -> int:
    """PR #8: Fix sign-flip bug — negate pnl_pct where stored ≈ -calculated.

    Historical bug: some picks had pnl_pct computed with inverted direction sign,
    so pnl_pct ≈ -price_based_pnl.  Detected when ABS(stored + calculated) ≤ 0.5%
    (stored is the negative of calculated) but ABS(stored - calculated) > 1%
    (the values are meaningfully different, not just both near zero).

    The chk_pnl_sign_coherence CHECK constraint blocks direct negation because
    a TP_HIT row with positive pnl_pct would become negative (violating the rule
    that TP_HIT must have pnl_pct >= -0.01).  We temporarily drop the constraint,
    apply the fix (which corrects the sign), then re-add it — the re-added
    constraint validates that fixed rows now have the correct sign.

    Idempotent: skips rows already tagged with [SIGN_FLIP_FIXED].
    Returns number of rows repaired.
    """
    # Count affected rows before dropping constraint
    cur.execute(
        "SELECT COUNT(*) as cnt FROM trading_picks "
        "WHERE exit_price > 0 AND entry_price > 0 "
        "  AND status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED') "
        "  AND ABS((exit_price - entry_price) / entry_price * 100 "
        "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) <= 500 "
        "  AND ABS(pnl_pct + ((exit_price - entry_price) / entry_price * 100 "
        "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) <= 0.5 "
        "  AND ABS(pnl_pct - ((exit_price - entry_price) / entry_price * 100 "
        "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) > 1 "
        "  AND (exit_reason IS NULL "
        "       OR exit_reason NOT LIKE '%SIGN_FLIP_FIXED%')"
    )
    row = cur.fetchone()
    if row["cnt"] == 0:
        return 0

    # Temporarily drop the CHECK constraint that blocks sign negation.
    # CONSTRAINT MAY ALREADY BE GONE from a previous partial run — handle gracefully.
    try:
        cur.execute("ALTER TABLE trading_picks DROP CHECK chk_pnl_sign_coherence")
    except pymysql.err.OperationalError as e:
        if e.args[0] == 3940:  # ER_CHECK_CONSTRAINT_NOT_FOUND — already gone
            print("         [INFO] Constraint already dropped (from previous run)")
        else:
            raise

    try:
        cur.execute(
            "UPDATE trading_picks "
            "SET pnl_pct = -pnl_pct, "
            "    status = CASE "
            "        WHEN status IN ('TP_HIT','WON') AND -pnl_pct <= 0.01 THEN 'SL_HIT' "
            "        WHEN status IN ('SL_HIT','LOST') AND -pnl_pct >= -0.01 THEN 'TP_HIT' "
            "        ELSE status "
            "    END, "
            "    exit_reason = CASE "
            "        WHEN exit_reason IS NULL OR exit_reason = '' "
            "            THEN 'SIGN_FLIP_FIXED' "
            "        ELSE CONCAT(exit_reason, ' [SIGN_FLIP_FIXED]') "
            "    END, "
            "    updated_at = NOW() "
            "WHERE exit_price > 0 AND entry_price > 0 "
            "  AND status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED') "
            "  AND ABS((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) <= 500 "
            "  AND ABS(pnl_pct + ((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) <= 0.5 "
            "  AND ABS(pnl_pct - ((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) > 1 "
            "  AND (exit_reason IS NULL "
            "       OR exit_reason NOT LIKE '%SIGN_FLIP_FIXED%')"
        )
        fixed = cur.rowcount
    finally:
        # Re-add the constraint. Add with NOT ENFORCED first so existing rows
        # aren't validated (some may have sign issues outside our tolerance).
        # Then immediately alter to ENFORCED for future rows.
        try:
            cur.execute(
                "ALTER TABLE trading_picks ADD CONSTRAINT chk_pnl_sign_coherence CHECK ("
                "  ((status IN ('WON','TP_HIT','closed_win')) AND (pnl_pct >= -0.01)) "
                "  OR ((status IN ('LOST','SL_HIT','closed_loss')) AND (pnl_pct <= 0.01)) "
                "  OR (status NOT IN ('WON','TP_HIT','closed_win','LOST','SL_HIT','closed_loss'))"
                ") NOT ENFORCED"
            )
            cur.execute(
                "ALTER TABLE trading_picks ALTER CONSTRAINT chk_pnl_sign_coherence ENFORCED"
            )
        except pymysql.err.OperationalError as e:
            if e.args[0] in (3822, 3940):  # violation or duplicate constraint
                print(f"         [WARN] Constraint restore: {e}")
            else:
                raise
    return fixed


def _repair_pnl_price_corruption(cur) -> int:
    """PR #7: NULL out corrupt exit_price on rows with absurd price-based PnL.

    Detects rows where (exit_price - entry_price) / entry_price suggests an
    impossible move (>500% absolute PnL).  These are data corruption, not real
    trades — the exit_price was written from a different symbol or timeframe.

    Repair: NULLs exit_price (so backtests skip them) and tags exit_reason.
    Does NOT touch pnl_pct — the stored value is more trustworthy.
    Returns number of rows repaired.
    """
    cur.execute(
        "UPDATE trading_picks "
        "SET exit_price = NULL, "
        "    exit_reason = CASE "
        "        WHEN exit_reason IS NULL OR exit_reason = '' "
        "            THEN 'PRICE_CORRUPT' "
        "        WHEN exit_reason LIKE '%PRICE_CORRUPT%' "
        "            THEN exit_reason "
        "        ELSE CONCAT(exit_reason, ' [PRICE_CORRUPT]') "
        "    END, "
        "    updated_at = NOW() "
        "WHERE exit_price > 0 AND entry_price > 0 "
        "  AND status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED') "
        "  AND ABS((exit_price - entry_price) / entry_price * 100 "
        "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) > 500"
    )
    return cur.rowcount


def _repair_signal_outcomes(cur) -> int:
    """PR #4: Rebuild at_signal_outcomes from trading_picks (closed picks only).

    Truncates stale table and repopulates from the source of truth.
    Maps trading_picks statuses to at_signal_outcomes outcome codes.
    Returns total rows inserted.
    """
    cur.execute("TRUNCATE TABLE at_signal_outcomes")
    cur.execute("""
        INSERT INTO at_signal_outcomes
            (symbol, direction, entry_price, exit_price, outcome, pnl_pct,
             source_system, strategy, asset_class, opened_at, closed_at)
        SELECT
            symbol,
            COALESCE(direction, 'LONG'),
            entry_price,
            exit_price,
            CASE
                WHEN status IN ('TP_HIT', 'WON', 'CLOSED_TP') THEN 'TP_HIT'
                WHEN status IN ('SL_HIT', 'LOST', 'CLOSED_SL') THEN 'SL_HIT'
                WHEN status = 'EXPIRED' THEN
                    CASE WHEN pnl_pct IS NOT NULL AND pnl_pct > 0 THEN 'WIN' ELSE 'LOSS' END
                ELSE status
            END,
            pnl_pct,
            COALESCE(NULLIF(source_system, ''), 'scanner'),
            strategy,
            COALESCE(NULLIF(category, ''), 'UNKNOWN'),
            created_at,
            closed_at
        FROM trading_picks
        WHERE status IN ('WON', 'LOST', 'TP_HIT', 'SL_HIT', 'EXPIRED',
                         'CLOSED_TP', 'CLOSED_SL')
            AND symbol IS NOT NULL AND symbol != ''
            AND closed_at IS NOT NULL
    """)
    return cur.rowcount


def _repair_ghost_rows(cur) -> int:
    """PR #3: Dedup ghost rows — keep only the earliest pick per
    (category, strategy, symbol, direction, pnl_pct, created_sec) and delete the rest.

    Uses UNIX_TIMESTAMP(created_at) to round timestamps to second precision,
    fixing the microsecond mismatch.  Uses IFNULL on all nullable columns
    because SQL NULL != NULL in JOIN conditions (GROUP BY groups NULLs, JOIN doesn't).
    Returns number of rows deleted.
    """
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_ghost_dedup")
    cur.execute(
        "CREATE TEMPORARY TABLE tmp_ghost_dedup AS "
        "SELECT category, strategy, symbol, direction, pnl_pct, "
        "  UNIX_TIMESTAMP(created_at) as created_sec, MIN(id) as min_id "
        "FROM trading_picks "
        "GROUP BY category, strategy, symbol, direction, pnl_pct, UNIX_TIMESTAMP(created_at) "
        "HAVING COUNT(*) > 1"
    )
    cur.execute("SELECT COUNT(*) as cnt FROM tmp_ghost_dedup")
    dup_groups = cur.fetchone()["cnt"]
    if dup_groups == 0:
        return 0
    cur.execute(
        "DELETE t1 FROM trading_picks t1 "
        "INNER JOIN tmp_ghost_dedup t2 "
        "  ON IFNULL(t1.category,'') = IFNULL(t2.category,'') "
        "  AND IFNULL(t1.strategy,'') = IFNULL(t2.strategy,'') "
        "  AND t1.symbol = t2.symbol "
        "  AND t1.direction = t2.direction "
        "  AND IFNULL(t1.pnl_pct, -9999) = IFNULL(t2.pnl_pct, -9999) "
        "  AND IFNULL(UNIX_TIMESTAMP(t1.created_at), 0) = IFNULL(t2.created_sec, 0) "
        "WHERE t1.id > t2.min_id"
    )
    return cur.rowcount


def _repair_cot_dedup(cur) -> int:
    """PR #5: Dedup COT over-emission — keep only the earliest pick per
    (symbol, strategy, direction, release_week) and delete the rest.

    Mirrors audit_trail/dashboard_generator.py _dedup_cot_over_emission()
    dedup key: (symbol, direction, YEARWEEK(created_at, 1)).
    Only touches strategies in _COT_DEDUP_STRATS.
    Returns number of rows deleted.
    """
    placeholders = ",".join(["%s"] * len(_COT_DEDUP_STRATS))
    cur.execute("DROP TEMPORARY TABLE IF EXISTS tmp_cot_dedup")
    cur.execute(
        "CREATE TEMPORARY TABLE tmp_cot_dedup AS "
        "SELECT symbol, strategy, direction, YEARWEEK(created_at, 1) as release_week, "
        "  MIN(id) as min_id "
        "FROM trading_picks "
        f"WHERE strategy IN ({placeholders}) "
        "GROUP BY symbol, strategy, direction, YEARWEEK(created_at, 1) "
        "HAVING COUNT(*) > 1",
        tuple(_COT_DEDUP_STRATS),
    )
    cur.execute("SELECT COUNT(*) as cnt FROM tmp_cot_dedup")
    dup_groups = cur.fetchone()["cnt"]
    if dup_groups == 0:
        return 0
    cur.execute(
        "DELETE t1 FROM trading_picks t1 "
        "INNER JOIN tmp_cot_dedup t2 "
        "  ON t1.symbol = t2.symbol "
        "  AND t1.strategy = t2.strategy "
        "  AND t1.direction = t2.direction "
        "  AND YEARWEEK(t1.created_at, 1) = t2.release_week "
        "WHERE t1.id > t2.min_id"
    )
    return cur.rowcount


def _repair_status_standardization(cur) -> int:
    """PR #2: Standardize all non-canonical statuses to canonical values.

    Applies the same STATUS_MAPPINGS as tools/standardize_statuses.py:
    WON/WIN → TP_HIT (pnl>0) / LOST (pnl<=0)
    LOSS → LOST (pnl<0) / TP_HIT (pnl>=0)
    CLOSED_SL → SL_HIT, CLOSED_TP → TP_HIT
    FLAT → TIME_EXIT, SIGNAL/STALE → EXPIRED
    Returns total rows updated.
    """
    total = 0

    # Fix edge case: rows already tagged with STATUS_STANDARDIZED but
    # status wasn't actually corrected (race condition / partial update).
    # The normal idempotency guard would skip these, so fix them explicitly.
    for from_status, pnl_cond, to_status in [
        ("WON",  "pnl_pct > 0",                     "TP_HIT"),
        ("WON",  "pnl_pct <= 0 OR pnl_pct IS NULL",  "LOST"),
        ("WIN",  "pnl_pct > 0",                     "TP_HIT"),
        ("WIN",  "pnl_pct <= 0 OR pnl_pct IS NULL",  "LOST"),
        ("LOSS", "pnl_pct < 0",                     "LOST"),
        ("LOSS", "pnl_pct >= 0 OR pnl_pct IS NULL",  "TP_HIT"),
    ]:
        cur.execute(
            f"UPDATE trading_picks "
            f"SET status = %s, updated_at = NOW() "
            f"WHERE status = %s AND ({pnl_cond}) "
            f"  AND exit_reason LIKE %s",
            (to_status, from_status, "%STATUS_STANDARDIZED%"),
        )
        total += cur.rowcount

    # Also handle 1=1 statuses (unconditional mappings) for tagged-but-uncorrected rows
    for from_status, to_status in [
        ("CLOSED_SL", "SL_HIT"),
        ("CLOSED_TP", "TP_HIT"),
        ("FLAT",      "TIME_EXIT"),
        ("SIGNAL",    "EXPIRED"),
        ("STALE",     "EXPIRED"),
    ]:
        cur.execute(
            "UPDATE trading_picks SET status = %s, updated_at = NOW() "
            "WHERE status = %s AND exit_reason LIKE %s",
            (to_status, from_status, "%STATUS_STANDARDIZED%"),
        )
        total += cur.rowcount

    for from_status, condition, to_status, exit_reason in _STATUS_MAPPINGS:
        sql = (
            f"UPDATE trading_picks "
            f"SET status = %s, "
            f"    exit_reason = CASE "
            f"        WHEN exit_reason IS NULL OR exit_reason = '' OR exit_reason = %s "
            f"            THEN %s "
            f"        ELSE CONCAT(exit_reason, ' (', %s, ')') "
            f"    END, "
            f"    updated_at = NOW() "
            f"WHERE status = %s AND ({condition}) "
            f"  AND (exit_reason IS NULL OR exit_reason NOT LIKE %s)"
        )
        cur.execute(sql, (
            to_status, from_status, exit_reason, exit_reason,
            from_status, "%STATUS_STANDARDIZED%",
        ))
        total += cur.rowcount
    return total


# ── Verification queries ──────────────────────────────────────────────
CHECKS = [
    {
        "id": "trust_score_backfill",
        "title": "trust_score NULL on 99.99% of closed picks",
        "sql": """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN trust_score IS NOT NULL THEN 1 ELSE 0 END) as non_null
            FROM trading_picks
            WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED')
        """,
        "pass": lambda r: r["non_null"] / max(r["total"], 1) > 0.5,
        "fmt": lambda r: f"{r['non_null']}/{r['total']} ({r['non_null']/max(r['total'],1)*100:.1f}%) have trust_score",
    },
    {
        "id": "forex_extreme_pnl",
        "title": "5 FOREX rows with pnl_pct < -100%",
        "sql": "SELECT COUNT(*) as cnt FROM trading_picks WHERE category='FOREX' AND pnl_pct < -100",
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} rows with pnl_pct < -100",
    },
    {
        "id": "signal_outcomes_freshness",
        "title": "signal_outcomes table stale (last write > 7 days)",
        "sql": (
            "SELECT COUNT(*) as cnt, MAX(created_at) as last_ts,"
            "  CASE WHEN MAX(created_at) > NOW() - INTERVAL 7 DAY THEN 1 ELSE 0 END as fresh"
            "  FROM at_signal_outcomes"
        ),
        "pass": lambda r: r["cnt"] > 1000 and r.get("fresh", 0) == 1,
        "fmt": lambda r: f"{r['cnt']} rows, last={r['last_ts']}, fresh={'yes' if r.get('fresh') else 'no'}",
        "repair_sql": _repair_signal_outcomes,
    },
    {
        "id": "status_standardization",
        "title": "Status standardization — non-canonical statuses (WON, CLOSED_SL, CLOSED_TP, FLAT, etc.)",
        "sql": (
            "SELECT COUNT(*) as cnt "
            "FROM trading_picks "
            "WHERE status NOT IN ("
            + ",".join([f"'{s}'" for s in sorted(_CANONICAL_STATUSES)]) +
            ")"
        ),
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} rows with non-canonical status",
        "repair_sql": _repair_status_standardization,
    },
    {
        "id": "won_status_contradiction",
        "title": "WON status rows avg pnl_pct = -41.1%",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM trading_picks
            WHERE status='WON' AND pnl_pct < 0
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} WON rows with negative pnl",
    },
    {
        "id": "ghost_rows",
        "title": "Ghost rows — duplicate (category, strategy, symbol, direction, pnl_pct, created_at) groups",
        "sql": """
            SELECT COALESCE(SUM(grp_cnt - 1), 0) as cnt FROM (
                SELECT COUNT(*) as grp_cnt
                FROM trading_picks
                GROUP BY category, strategy, symbol, direction, pnl_pct, UNIX_TIMESTAMP(created_at)
                HAVING COUNT(*) > 1
            ) dupes
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} ghost rows across all cohorts",
        "repair_sql": _repair_ghost_rows,
    },
    {
        "id": "unknown_category_active",
        "title": "UNKNOWN asset_class on 951 active",
        "sql": """
            SELECT COUNT(*) as cnt
            FROM trading_picks
            WHERE (category IS NULL OR category='UNKNOWN') AND status='ACTIVE'
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} active picks with UNKNOWN category",
    },
    {
        "id": "cot_dedup",
        "title": "COT over-emission — duplicate picks per (symbol, strategy, direction, release_week)",
        "sql": """
            SELECT COALESCE(SUM(grp_cnt - 1), 0) as cnt FROM (
                SELECT COUNT(*) as grp_cnt
                FROM trading_picks
                WHERE strategy IN ('multi_asset_cot','cot_positioning',
                                  'cftc_cot_commercial_signal','multi_asset_copytrader')
                GROUP BY symbol, strategy, direction, YEARWEEK(created_at, 1)
                HAVING COUNT(*) > 1
            ) dupes
        """,
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} duplicate COT picks across release weeks",
        "repair_sql": _repair_cot_dedup,
    },
    {
        "id": "pnl_status_mismatch",
        "title": "PnL status mismatch — status contradicts pnl_pct sign (e.g., TP_HIT with negative PnL)",
        "sql": (
            "SELECT "
            "  (SELECT COUNT(*) FROM trading_picks WHERE status IN ('WON','TP_HIT','closed_win') AND pnl_pct < -0.01) as neg_pnl_winners, "
            "  (SELECT COUNT(*) FROM trading_picks WHERE status IN ('LOST','SL_HIT','closed_loss') AND pnl_pct > 0.01) as pos_pnl_losers"
        ),
        "pass": lambda r: r["neg_pnl_winners"] + r["pos_pnl_losers"] == 0,
        "fmt": lambda r: f"{r['neg_pnl_winners']} winner-status rows with negative PnL, {r['pos_pnl_losers']} loser-status rows with positive PnL",
        "repair_sql": _repair_pnl_status_mismatch,
    },
    {
        "id": "pnl_sign_flip",
        "title": "PnL sign-flip — stored pnl_pct is the negative of price-based PnL (direction bug)",
        "sql": (
            "SELECT COUNT(*) as cnt "
            "FROM trading_picks "
            "WHERE exit_price > 0 AND entry_price > 0 "
            "  AND status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED') "
            "  AND ABS((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) <= 500 "
            "  AND ABS(pnl_pct + ((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) <= 0.5 "
            "  AND ABS(pnl_pct - ((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END)) > 1"
        ),
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} rows with sign-flipped pnl_pct (stored ≈ -calculated)",
        "repair_sql": _repair_pnl_sign_flip,
    },
    {
        "id": "pnl_price_corruption",
        "title": "PnL price corruption — exit_price produces impossible PnL (>500% absolute)",
        "sql": (
            "SELECT COUNT(*) as cnt "
            "FROM trading_picks "
            "WHERE exit_price > 0 AND entry_price > 0 "
            "  AND status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED') "
            "  AND ABS((exit_price - entry_price) / entry_price * 100 "
            "    * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) > 500"
        ),
        "pass": lambda r: r["cnt"] == 0,
        "fmt": lambda r: f"{r['cnt']} rows with impossible price-based PnL",
        "repair_sql": _repair_pnl_price_corruption,
    },
    {
        "id": "pnl_integrity",
        "title": "PnL integrity — tiered mismatch (sign-flip ≤0.5%, moderate 0.5-10%, noise ≤1%), Q2 2026 excluded",
        "sql": """
            WITH clean AS (
                SELECT
                    pnl_pct,
                    created_at,
                    ((exit_price - entry_price) / entry_price * 100
                        * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) as calc
                FROM trading_picks
                WHERE status IN ('WON','LOST','TP_HIT','SL_HIT','EXPIRED')
                    AND exit_price > 0 AND entry_price > 0
                    AND ABS((exit_price - entry_price) / entry_price * 100
                        * CASE WHEN direction='LONG' THEN 1 ELSE -1 END) <= 500
            )
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN ABS(pnl_pct + calc) <= 0.5
                         AND ABS(pnl_pct - calc) > 0.5
                         THEN 1 ELSE 0 END) as sign_flip,
                SUM(CASE WHEN ABS(pnl_pct - calc) > 0.5
                         AND ABS(pnl_pct - calc) <= 10
                         AND ABS(pnl_pct + calc) > 0.5
                         THEN 1 ELSE 0 END) as moderate,
                SUM(CASE WHEN ABS(pnl_pct - calc) > 0
                         AND ABS(pnl_pct - calc) <= 1
                         THEN 1 ELSE 0 END) as noise,
                SUM(CASE WHEN created_at < '2026-04-01'
                         AND ABS(pnl_pct - calc) > 0.5
                         AND ABS(pnl_pct - calc) <= 10
                         AND ABS(pnl_pct + calc) > 0.5
                         THEN 1 ELSE 0 END) as pre_q2_moderate
            FROM clean
        """,
        "pass": lambda r: r["pre_q2_moderate"] == 0,
        "fmt": lambda r: (
            f"{r['total']} total — "
            f"sign-flip={r['sign_flip']} (≤0.5%, repairable), "
            f"moderate={r['moderate']} (0.5-10%, investigate), "
            f"noise={r['noise']} (≤1%, ignore), "
            f"pre-Q2 moderate={r['pre_q2_moderate']} (threshold only)"
        ),
    },
]


def run_checks(conn, write=False):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== Data Integrity Verification ({now}) ===\n")

    passed = 0
    failed = 0
    repaired = 0

    with conn.cursor() as cur:
        for check in CHECKS:
            cur.execute(check["sql"])
            row = cur.fetchone()
            ok = check["pass"](row)
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {check['title']}")
            print(f"         {check['fmt'](row)}")

            if ok:
                passed += 1
                if write:
                    _mark_resolved(cur, check["title"])
            else:
                failed += 1
                # PR #3/#4: Execute repair_sql for FAIL checks when --write
                repair_sql = check.get("repair_sql")
                if write and repair_sql:
                    if callable(repair_sql):
                        n = repair_sql(cur)
                    else:
                        cur.execute(repair_sql)
                        n = cur.rowcount
                    repaired += n
                    print(f"         [WRITE] Repaired {n} rows")
            print()

    if write:
        conn.commit()
        print(f"\n[WRITE] Updated {passed} incidents to RESOLVED, repaired {repaired} rows across {failed} failed checks.")

    print(f"\n=== Summary: {passed} PASS, {failed} FAIL, {passed + failed} total ===")
    return passed, failed


def _mark_resolved(cur, title_substr: str):
    """Best-effort: update matching INCIDENT_* rows to RESOLVED."""
    for cls in CLASSES:
        table = f"INCIDENT_{cls}"
        cur.execute(
            f"UPDATE {table} SET status='RESOLVED', updated_at=NOW() "
            f"WHERE status IN ('OPEN','TRIAGED','IN_PROGRESS') "
            f"AND title LIKE %s",
            (f"%{title_substr[:40]}%",),
        )


if __name__ == "__main__":
    write = "--write" in sys.argv
    conn = connect()
    try:
        run_checks(conn, write=write)
    finally:
        conn.close()
