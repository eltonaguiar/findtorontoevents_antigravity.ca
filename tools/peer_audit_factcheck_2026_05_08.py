"""
Fact-check script for peer audit findings 2026-05-08.

Read-only SELECTs against ejaguiar1_stocks. Writes results to stdout JSON
so the parent agent can transcribe into reports/peer_audit_factcheck_2026-05-08.md.
"""
import os
import json
from decimal import Decimal
from datetime import datetime, date

os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection


def _jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8', errors='replace')
        except Exception:
            return str(v)
    return v


def fetchall_dict(cur, sql, params=None):
    cur.execute(sql, params or ())
    cols = [d[0] for d in cur.description]
    return [{c: _jsonable(v) for c, v in zip(cols, row)} for row in cur.fetchall()]


def fetch_one(cur, sql, params=None):
    cur.execute(sql, params or ())
    row = cur.fetchone()
    return _jsonable(row[0]) if row else None


def main():
    conn = _create_connection()
    cur = conn.cursor()
    cur.execute("SET SESSION MAX_EXECUTION_TIME=120000")

    out = {}

    # ────────────────────────────────────────────────────────────────────
    # Finding 1: at_consensus_picks time-travel (closed_at < generated_at)
    # ────────────────────────────────────────────────────────────────────
    f1 = {}
    # Discover columns first
    f1['columns'] = fetchall_dict(cur, """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='at_consensus_picks'
        ORDER BY ORDINAL_POSITION
    """)
    cols_present = {c['COLUMN_NAME'] for c in f1['columns']}
    if 'closed_at' in cols_present and 'generated_at' in cols_present:
        f1['total_rows'] = fetch_one(cur, "SELECT COUNT(*) FROM at_consensus_picks")
        f1['rows_with_both_ts'] = fetch_one(cur, """
            SELECT COUNT(*) FROM at_consensus_picks
            WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
        """)
        f1['time_travel_count'] = fetch_one(cur, """
            SELECT COUNT(*) FROM at_consensus_picks
            WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
              AND closed_at < generated_at
        """)
        # Sample 10 rows w/ id (whichever pk col)
        pk_candidates = ['pick_id', 'id', 'consensus_id']
        pk = next((c for c in pk_candidates if c in cols_present), None)
        sample_cols = [pk] if pk else []
        for c in ('symbol', 'direction', 'generated_at', 'closed_at', 'asset_class'):
            if c in cols_present:
                sample_cols.append(c)
        f1['sample'] = fetchall_dict(cur, f"""
            SELECT {','.join(sample_cols)}
            FROM at_consensus_picks
            WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
              AND closed_at < generated_at
            ORDER BY generated_at DESC
            LIMIT 10
        """)
        # Severity slice: how bad on average
        f1['stats'] = fetchall_dict(cur, """
            SELECT
              MIN(TIMESTAMPDIFF(HOUR, closed_at, generated_at)) AS min_hrs_ahead,
              MAX(TIMESTAMPDIFF(HOUR, closed_at, generated_at)) AS max_hrs_ahead,
              AVG(TIMESTAMPDIFF(HOUR, closed_at, generated_at)) AS avg_hrs_ahead
            FROM at_consensus_picks
            WHERE closed_at IS NOT NULL AND generated_at IS NOT NULL
              AND closed_at < generated_at
        """)
    else:
        f1['error'] = f"Missing columns. cols={sorted(cols_present)}"
    out['finding_1_time_travel'] = f1

    # ────────────────────────────────────────────────────────────────────
    # Finding 2: consensus_tracked 100% synthetic
    # ────────────────────────────────────────────────────────────────────
    f2 = {}
    f2['columns'] = fetchall_dict(cur, """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='consensus_tracked'
        ORDER BY ORDINAL_POSITION
    """)
    ct_cols = {c['COLUMN_NAME'] for c in f2['columns']}
    f2['total'] = fetch_one(cur, "SELECT COUNT(*) FROM consensus_tracked")
    if 'entry_date' in ct_cols:
        f2['future_dated'] = fetch_one(cur, "SELECT COUNT(*) FROM consensus_tracked WHERE entry_date > NOW()")
    if 'entry_price' in ct_cols:
        f2['round_entry'] = fetch_one(cur, "SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = ROUND(entry_price,0)")
    if 'final_return_pct' in ct_cols:
        f2['zero_return'] = fetch_one(cur, "SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct = 0")
    elif 'pnl_pct' in ct_cols:
        f2['zero_return'] = fetch_one(cur, "SELECT COUNT(*) FROM consensus_tracked WHERE pnl_pct = 0")
    # Sample 5 rows
    f2['sample'] = fetchall_dict(cur, "SELECT * FROM consensus_tracked LIMIT 5")
    out['finding_2_synthetic_consensus_tracked'] = f2

    # ────────────────────────────────────────────────────────────────────
    # Finding 3: asset_class='' empty string across 3 tables
    # ────────────────────────────────────────────────────────────────────
    f3 = {}
    for tbl in ('at_raw_picks', 'at_audit_events', 'at_consensus_picks'):
        # Confirm column exists
        col_check = fetchall_dict(cur, """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME=%s AND COLUMN_NAME='asset_class'
        """, (tbl,))
        sub = {'col_def': col_check}
        if col_check:
            sub['empty_string'] = fetch_one(cur, f"SELECT COUNT(*) FROM {tbl} WHERE asset_class = ''")
            sub['null'] = fetch_one(cur, f"SELECT COUNT(*) FROM {tbl} WHERE asset_class IS NULL")
            sub['unknown_literal'] = fetch_one(cur, f"SELECT COUNT(*) FROM {tbl} WHERE asset_class = 'UNKNOWN'")
            sub['total'] = fetch_one(cur, f"SELECT COUNT(*) FROM {tbl}")
            sub['distinct_values'] = fetchall_dict(cur, f"""
                SELECT asset_class, COUNT(*) AS n FROM {tbl}
                GROUP BY asset_class ORDER BY n DESC LIMIT 20
            """)
        f3[tbl] = sub
    out['finding_3_asset_class_empty'] = f3

    # ────────────────────────────────────────────────────────────────────
    # Finding 4: simulation_grid 100% LONG
    # ────────────────────────────────────────────────────────────────────
    f4 = {}
    cols = fetchall_dict(cur, """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='simulation_grid'
        ORDER BY ORDINAL_POSITION
    """)
    f4['columns'] = [c['COLUMN_NAME'] for c in cols]
    sg_cols = set(f4['columns'])
    f4['total'] = fetch_one(cur, "SELECT COUNT(*) FROM simulation_grid")
    direction_col = None
    for cand in ('direction', 'side', 'trade_direction'):
        if cand in sg_cols:
            direction_col = cand
            break
    f4['direction_col'] = direction_col
    if direction_col:
        f4['distribution'] = fetchall_dict(cur,
            f"SELECT {direction_col} AS dir, COUNT(*) AS n FROM simulation_grid GROUP BY {direction_col} ORDER BY n DESC")
    out['finding_4_sim_grid_long_only'] = f4

    # ────────────────────────────────────────────────────────────────────
    # Finding 5: rapid_signals exact 50/50 win/loss
    # ────────────────────────────────────────────────────────────────────
    f5 = {}
    cols = fetchall_dict(cur, """
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='ejaguiar1_stocks' AND TABLE_NAME='rapid_signals'
        ORDER BY ORDINAL_POSITION
    """)
    f5['columns'] = cols
    rs_cols = {c['COLUMN_NAME'] for c in cols}
    f5['total'] = fetch_one(cur, "SELECT COUNT(*) FROM rapid_signals")
    if 'status' in rs_cols:
        f5['status_dist'] = fetchall_dict(cur, """
            SELECT status, COUNT(*) AS n FROM rapid_signals GROUP BY status ORDER BY n DESC
        """)
    if 'outcome' in rs_cols:
        f5['outcome_dist'] = fetchall_dict(cur, """
            SELECT outcome, COUNT(*) AS n FROM rapid_signals GROUP BY outcome ORDER BY n DESC
        """)
    if 'pnl_pct' in rs_cols:
        f5['pnl_pct_top'] = fetchall_dict(cur, """
            SELECT pnl_pct, COUNT(*) AS n FROM rapid_signals
            WHERE pnl_pct IS NOT NULL
            GROUP BY pnl_pct ORDER BY n DESC LIMIT 15
        """)
        f5['pnl_pct_summary'] = fetchall_dict(cur, """
            SELECT
              COUNT(*) AS n_total,
              SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS n_win,
              SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) AS n_loss,
              SUM(CASE WHEN pnl_pct = 0 THEN 1 ELSE 0 END) AS n_zero,
              SUM(CASE WHEN pnl_pct IS NULL THEN 1 ELSE 0 END) AS n_null,
              AVG(pnl_pct) AS avg_pnl,
              MIN(pnl_pct) AS min_pnl,
              MAX(pnl_pct) AS max_pnl
            FROM rapid_signals
        """)
    # Sample 3
    f5['sample'] = fetchall_dict(cur, "SELECT * FROM rapid_signals LIMIT 3")
    out['finding_5_rapid_signals_5050'] = f5

    print(json.dumps(out, indent=2, default=str))
    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
