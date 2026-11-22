"""Read-only probe: how do the two closed-row filters differ on live data?

Never prints a password. SELECT-only — no INSERT/UPDATE/DELETE/DDL.

Filter A (tribunal, alpha_engine/audit3_tribunal.py:537-540):
    status = str(r.get("status") or "").upper()
    if status in ("OPEN", "PENDING", ""): drop   -> deny-list of 3
    (plus: requires numeric pnl_pct, dedupes on id)

Filter B (canonical view, alpha_engine/resolved_closed_view.py:93-102,153-160):
    exit_reason in _NON_PERFORMANCE_EXITS or startswith("STALE") -> drop
    status in ("OPEN","PENDING","CANCELLED","CANCELED","INVALID") -> drop

NOTE: trading_picks has NO asset_class column (verified by DESCRIBE). The class
is derived from symbol at read time, so the class dimension here is the DB's
own `category` column — a proxy, labelled as such.
"""
import json
import sys
sys.path.insert(0, ".")

import pymysql
from tools.db_env import get_stocks_creds

A_DENY = {"OPEN", "PENDING", ""}
B_STATUS_DENY = {"OPEN", "PENDING", "CANCELLED", "CANCELED", "INVALID"}
B_EXIT_DENY = {"", "UNKNOWN", "MANUAL", "CANCELLED", "CANCELED",
               "INVALID_ENTRY", "NO_FILL", "NOT_FILLED"}
EXIT_IN = "('', 'UNKNOWN','MANUAL','CANCELLED','CANCELED','INVALID_ENTRY','NO_FILL','NOT_FILLED')"


def main() -> int:
    creds = get_stocks_creds()
    conn = pymysql.connect(**{k: creds[k] for k in
                              ("host", "user", "password", "database", "port")
                              if k in creds},
                           connect_timeout=20,
                           cursorclass=pymysql.cursors.DictCursor)
    print(f"connected: host={creds.get('host')} db={creds.get('database')}")
    out = {}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS total_rows, SUM(pnl_pct IS NOT NULL) AS with_pnl
            FROM trading_picks
        """)
        out["totals"] = cur.fetchone()

        cur.execute("""
            SELECT status, COUNT(*) AS n
            FROM trading_picks WHERE pnl_pct IS NOT NULL
            GROUP BY status ORDER BY n DESC
        """)
        status_rows = cur.fetchall()
        out["status_with_pnl"] = status_rows

        cur.execute("""
            SELECT exit_reason, COUNT(*) AS n
            FROM trading_picks WHERE pnl_pct IS NOT NULL
            GROUP BY exit_reason ORDER BY n DESC LIMIT 40
        """)
        out["exit_reason_with_pnl"] = cur.fetchall()

        cur.execute("""
            SELECT category, COUNT(*) AS n
            FROM trading_picks WHERE pnl_pct IS NOT NULL
            GROUP BY category ORDER BY n DESC
        """)
        out["category_with_pnl"] = cur.fetchall()

        # Contested by STATUS: A scores them (not in its deny-list), B drops them.
        all_status = {str(r["status"] or "").upper() for r in status_rows}
        contested = sorted((all_status - A_DENY) & B_STATUS_DENY)
        out["contested_status_values"] = contested
        by_cat = {}
        for st in contested:
            cur.execute("""
                SELECT category, COUNT(*) AS n
                FROM trading_picks
                WHERE pnl_pct IS NOT NULL AND UPPER(COALESCE(status,'')) = %s
                GROUP BY category ORDER BY n DESC
            """, (st,))
            by_cat[st] = cur.fetchall()
        out["contested_status_by_category"] = by_cat

        # Contested by EXIT REASON: B drops them, A never looks at exit_reason.
        cur.execute(f"""
            SELECT exit_reason, COUNT(*) AS n
            FROM trading_picks
            WHERE pnl_pct IS NOT NULL
              AND (UPPER(TRIM(COALESCE(exit_reason,''))) IN {EXIT_IN}
                   OR UPPER(TRIM(COALESCE(exit_reason,''))) LIKE 'STALE%%')
            GROUP BY exit_reason ORDER BY n DESC
        """)
        out["non_performance_exit_rows"] = cur.fetchall()
        cur.execute(f"""
            SELECT category, COUNT(*) AS n
            FROM trading_picks
            WHERE pnl_pct IS NOT NULL
              AND (UPPER(TRIM(COALESCE(exit_reason,''))) IN {EXIT_IN}
                   OR UPPER(TRIM(COALESCE(exit_reason,''))) LIKE 'STALE%%')
            GROUP BY category ORDER BY n DESC
        """)
        out["non_performance_exit_by_category"] = cur.fetchall()

        # How many rows does each filter KEEP? (the denominator each page divides by)
        cur.execute("""
            SELECT COUNT(*) AS kept_by_A
            FROM trading_picks
            WHERE pnl_pct IS NOT NULL
              AND UPPER(COALESCE(status,'')) NOT IN ('OPEN','PENDING','')
        """)
        out["kept_by_tribunal_filter_A"] = cur.fetchone()
        cur.execute(f"""
            SELECT COUNT(*) AS kept_by_B
            FROM trading_picks
            WHERE pnl_pct IS NOT NULL
              AND UPPER(COALESCE(status,'')) NOT IN ('OPEN','PENDING','CANCELLED','CANCELED','INVALID')
              AND NOT (UPPER(TRIM(COALESCE(exit_reason,''))) IN {EXIT_IN}
                       OR UPPER(TRIM(COALESCE(exit_reason,''))) LIKE 'STALE%%')
        """)
        out["kept_by_canonical_filter_B"] = cur.fetchone()

    conn.close()
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
