#!/usr/bin/env python3
"""
Standardize ALL non-canonical statuses in trading_picks to canonical values.

Canonical terminal statuses: TP_HIT, SL_HIT, LOST, EXPIRED, TIME_EXIT

Mapping rules:
  WIN       → TP_HIT (pnl>0) / LOST (pnl<=0)
  WON       → TP_HIT (pnl>0) / LOST (pnl<=0)
  LOSS      → LOST  (pnl<0)  / TP_HIT (pnl>=0, contradiction — trust PnL)
  closed    → TP_HIT (pnl>0) / LOST (pnl<0) / TIME_EXIT (pnl=0/NULL)
  CLOSED_SL → SL_HIT
  CLOSED_TP → TP_HIT
  SIGNAL    → EXPIRED (no PnL data, no meaningful outcome)
  FLAT      → TIME_EXIT
  STALE     → EXPIRED

Active statuses (active, OPEN, ACTIVE) are NOT touched — they're not terminal.

Usage:
  python3 tools/standardize_statuses.py           # dry-run preview
  python3 tools/standardize_statuses.py --apply   # execute changes
"""

import argparse
import os
import sys

import pymysql

DB_HOST = "mysql.50webs.com"
DB_USER = "ejaguiar1_stocks"
DB_PASS = os.getenv("DB_PASS_STOCKS", "")
DB_NAME = "ejaguiar1_stocks"

# ── Mapping table ───────────────────────────────────────────────────────────
# Each entry: (from_status, condition_sql, to_status, exit_reason_override)
# condition_sql is a WHERE fragment applied per-row (uses pnl_pct column)
# exit_reason_override: None = preserve existing exit_reason, else set this

STATUS_MAPPINGS = [
    # WIN: all positive in practice, but safety-handle non-positive and NULL
    ("WIN",        "pnl_pct > 0",      "TP_HIT",    "STATUS_STANDARDIZED"),
    ("WIN",        "pnl_pct <= 0 OR pnl_pct IS NULL", "LOST", "STATUS_STANDARDIZED"),
    # WON: mostly positive (317/328), 11 had negative
    ("WON",        "pnl_pct > 0",      "TP_HIT",    "STATUS_STANDARDIZED"),
    ("WON",        "pnl_pct <= 0 OR pnl_pct IS NULL", "LOST", "STATUS_STANDARDIZED"),
    # LOSS: mostly negative (182/185), 2 had positive → contradiction, trust PnL
    ("LOSS",       "pnl_pct < 0",      "LOST",      "STATUS_STANDARDIZED"),
    ("LOSS",       "pnl_pct >= 0 OR pnl_pct IS NULL", "TP_HIT", "STATUS_STANDARDIZED"),
    # closed: mixed — PnL determines outcome
    ("closed",     "pnl_pct > 0",      "TP_HIT",    "STATUS_STANDARDIZED"),
    ("closed",     "pnl_pct < 0",      "LOST",      "STATUS_STANDARDIZED"),
    ("closed",     "pnl_pct = 0 OR pnl_pct IS NULL", "TIME_EXIT", "STATUS_STANDARDIZED"),
    # CLOSED_SL: stop-loss exits, all negative
    ("CLOSED_SL",  "1=1",              "SL_HIT",    "STATUS_STANDARDIZED"),
    # CLOSED_TP: take-profit exits, all positive
    ("CLOSED_TP",  "1=1",              "TP_HIT",    "STATUS_STANDARDIZED"),
    # SIGNAL: never had PnL — treat as expired
    ("SIGNAL",     "1=1",              "EXPIRED",   "STATUS_STANDARDIZED"),
    # FLAT: breakeven / forced close → TIME_EXIT
    ("FLAT",       "1=1",              "TIME_EXIT", "STATUS_STANDARDIZED"),
    # STALE: aged out → EXPIRED
    ("STALE",      "1=1",              "EXPIRED",   "STATUS_STANDARDIZED"),
    # 2026-06-09: FORCE_CLOSED_TOXIC leaked into the status column (3,504 rows) —
    # it's a legitimate exit_reason (kill-switch / crypto_risk_gates force-close a
    # toxic-source position) but NOT a canonical status. Honest canonical mapping:
    # a forced early close is NOT a take-profit, so pnl<0 -> LOST (real loss),
    # pnl>=0/NULL -> TIME_EXIT (non-TP exit; PnL preserved, but not counted a win).
    # Original intent retained in exit_reason.
    ("FORCE_CLOSED_TOXIC", "pnl_pct < 0",                    "LOST",      "FORCE_CLOSED_TOXIC"),
    ("FORCE_CLOSED_TOXIC", "pnl_pct >= 0 OR pnl_pct IS NULL", "TIME_EXIT", "FORCE_CLOSED_TOXIC"),
    # DISPUTED (1 row): same pnl-driven canonicalization.
    ("DISPUTED",           "pnl_pct < 0",                    "LOST",      "DISPUTED_STANDARDIZED"),
    ("DISPUTED",           "pnl_pct >= 0 OR pnl_pct IS NULL", "TIME_EXIT", "DISPUTED_STANDARDIZED"),
]


def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        connect_timeout=15,
        charset="utf8mb4",
        autocommit=False,
    )


def preview(conn) -> list[dict]:
    """Dry-run: show what each mapping rule would affect."""
    cur = conn.cursor()
    results = []
    total = 0
    for from_status, condition, to_status, exit_reason in STATUS_MAPPINGS:
        sql = f"""
            SELECT COUNT(*) FROM trading_picks
            WHERE status = %s AND ({condition})
        """
        cur.execute(sql, (from_status,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            results.append({
                "from": from_status,
                "condition": condition,
                "to": to_status,
                "exit_reason": exit_reason,
                "count": cnt,
            })
            total += cnt

    results.append({"from": "TOTAL", "condition": "", "to": "", "exit_reason": "", "count": total})
    return results


def sample_changes(conn, limit: int = 5) -> list[dict]:
    """Show sample rows that would be changed by each mapping."""
    cur = conn.cursor()
    samples = []
    for from_status, condition, to_status, exit_reason in STATUS_MAPPINGS:
        sql = f"""
            SELECT id, symbol, direction, pnl_pct, status, exit_reason, strategy
            FROM trading_picks
            WHERE status = %s AND ({condition})
            LIMIT {limit}
        """
        cur.execute(sql, (from_status,))
        rows = cur.fetchall()
        for row in rows:
            samples.append({
                "id": row[0],
                "symbol": row[1],
                "direction": row[2],
                "pnl_pct": float(row[3]) if row[3] is not None else None,
                "from_status": row[4],
                "old_exit_reason": row[5],
                "strategy": row[6],
                "to_status": to_status,
                "new_exit_reason": exit_reason,
            })
    return samples


def apply(conn) -> dict:
    """Execute all status standardizations in a single transaction."""
    cur = conn.cursor()
    stats = {"total": 0, "by_rule": []}

    for from_status, condition, to_status, exit_reason in STATUS_MAPPINGS:
        # Preserve existing exit_reason if it exists and is meaningful.
        # Idempotency: skip rows already tagged with STATUS_STANDARDIZED.
        sql = f"""
            UPDATE trading_picks
            SET status = %s,
                exit_reason = CASE
                    WHEN exit_reason IS NULL OR exit_reason = '' OR exit_reason = %s
                        THEN %s
                    ELSE CONCAT(exit_reason, ' (', %s, ')')
                END,
                updated_at = NOW()
            WHERE status = %s AND ({condition})
              AND (exit_reason IS NULL OR exit_reason NOT LIKE %s)
        """
        cur.execute(sql, (to_status, from_status, exit_reason, exit_reason, from_status, '%STATUS_STANDARDIZED%'))
        affected = cur.rowcount
        if affected > 0:
            stats["by_rule"].append({
                "from": from_status,
                "condition": condition,
                "to": to_status,
                "affected": affected,
            })
        stats["total"] += affected

    return stats


CANONICAL_STATUSES = {"TP_HIT", "SL_HIT", "LOST", "EXPIRED", "TIME_EXIT", "ACTIVE", "OPEN"}


def verify(conn) -> dict:
    """Post-standardization: confirm no non-canonical statuses remain."""
    cur = conn.cursor()
    # Use NOT IN canonical list instead of hardcoding non-canonical — catches new outliers
    placeholders = ",".join(["%s"] * len(CANONICAL_STATUSES))
    cur.execute(f"""
        SELECT status, COUNT(*) FROM trading_picks
        WHERE status NOT IN ({placeholders})
        GROUP BY status
    """, tuple(CANONICAL_STATUSES))
    remaining = {row[0]: row[1] for row in cur.fetchall()}

    # Show final status distribution
    cur.execute("""
        SELECT status, COUNT(*) FROM trading_picks
        GROUP BY status ORDER BY COUNT(*) DESC
    """)
    distribution = {row[0]: row[1] for row in cur.fetchall()}

    return {"remaining_non_canonical": remaining, "distribution": distribution}


def main():
    ap = argparse.ArgumentParser(description="Standardize trading_picks statuses")
    ap.add_argument("--apply", action="store_true", help="Execute changes (default: dry-run)")
    args = ap.parse_args()

    if not DB_PASS:
        print("ERROR: DB_PASS_STOCKS not set")
        sys.exit(1)

    conn = get_conn()
    try:
        print("=" * 70)
        print("STATUS STANDARDIZATION — trading_picks")
        print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
        print("=" * 70)

        # ── Preview ──
        print("\n📊 Rows to be changed:\n")
        results = preview(conn)
        for r in results:
            if r["from"] == "TOTAL":
                print(f"  {'─' * 50}")
                print(f"  TOTAL: {r['count']:,} rows")
            else:
                print(f"  {r['from']:12s} → {r['to']:10s}  ({r['condition']:30s})  {r['count']:6,d} rows")

        # ── Samples ──
        print(f"\n📋 Sample changes (5 per rule):\n")
        samples = sample_changes(conn)
        seen_rules = set()
        for s in samples:
            rule_key = (s["from_status"], s["to_status"])
            if rule_key not in seen_rules:
                seen_rules.add(rule_key)
                print(f"  {s['from_status']:12s} → {s['to_status']:10s}:")
            pnl_str = f"{s['pnl_pct']:.2f}" if s['pnl_pct'] is not None else "NULL"
            print(f"    {s['symbol']:10s} {s['direction']:6s} pnl={pnl_str:>8s}  "
                  f"id={str(s['id'])[:20]:20s}  strat={s['strategy'] or '?':25s}")

        if args.apply:
            # ── Apply ──
            print("\n⚡ Applying changes...")
            stats = apply(conn)
            conn.commit()
            print(f"\n  ✅ {stats['total']:,} rows updated across {len(stats['by_rule'])} rules")

            # ── Verify ──
            print("\n🔍 Verifying post-standardization state...")
            v = verify(conn)

            if v["remaining_non_canonical"]:
                print("  ❌ NON-CANONICAL STATUSES REMAIN:")
                for st, cnt in v["remaining_non_canonical"].items():
                    print(f"     {st}: {cnt}")
            else:
                print("  ✅ All statuses are now canonical!")

            print("\n📊 Final status distribution:")
            for status, cnt in sorted(v["distribution"].items(), key=lambda x: -x[1]):
                print(f"  {status:12s}: {cnt:>8,d}")
        else:
            print(f"\n💡 Dry-run complete. Re-run with --apply to execute changes.")
            print(f"   python3 tools/standardize_statuses.py --apply")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
