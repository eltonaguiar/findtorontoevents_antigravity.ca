#!/usr/bin/env python3
"""
Investigation script for at_pick_outcomes TP_HIT vs SL_HIT bug.
Avoids cross-table joins due to collation mismatches.
"""
import sys
import pymysql
from datetime import datetime, timedelta
from decimal import Decimal

DB_HOST = 'mysql.50webs.com'
DB_USER = 'ejaguiar1_stocks'
DB_PASS = 'stocks1234560'
DB_NAME = 'ejaguiar1_stocks'

AT_PO_COLS = ['pick_id', 'symbol', 'strategy', 'asset_class', 'status',
              'resolution_method', 'pnl_pct', 'resolved_at', 'resolver_version']

def connect():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
        read_timeout=120,
        write_timeout=60,
    )

def run_query(conn, title, sql, params=None, limit=25):
    print(f"\n{'='*100}")
    print(f"QUERY: {title}")
    print(f"{'='*100}")
    print(f"SQL: {sql.strip()}")
    if params:
        print(f"PARAMS: {params}")
    print("-" * 100)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            print("(no rows returned)")
            return rows
        headers = list(rows[0].keys())
        print(" | ".join(headers))
        print("-" * (len(" | ".join(headers)) + 10))
        for i, row in enumerate(rows):
            if i >= limit:
                print(f"... ({len(rows) - limit} more rows)")
                break
            vals = []
            for h in headers:
                v = row[h]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, float):
                    vals.append(f"{v:.4f}")
                elif isinstance(v, Decimal):
                    vals.append(f"{float(v):.4f}")
                else:
                    vals.append(str(v))
            print(" | ".join(vals))
        print(f"TOTAL ROWS: {len(rows)}")
        return rows

def main():
    print(f"Investigation started: {datetime.now().isoformat()}")
    conn = connect()
    print(f"Connected to {DB_HOST} / {DB_NAME}")

    # ==================================================================
    # 1. at_pick_outcomes — core misclassification analysis
    # ==================================================================

    run_query(conn, "at_pick_outcomes: resolution_method x status breakdown (all time)", """
        SELECT
            resolution_method,
            status,
            COUNT(*) AS total,
            ROUND(AVG(pnl_pct), 4) AS avg_pnl,
            MIN(pnl_pct) AS min_pnl,
            MAX(pnl_pct) AS max_pnl
        FROM at_pick_outcomes
        GROUP BY resolution_method, status
        ORDER BY resolution_method, status
    """)

    run_query(conn, "at_pick_outcomes: TP_HIT picks with NEGATIVE pnl_pct (misclassified)", """
        SELECT
            pick_id, symbol, strategy, asset_class, status,
            pnl_pct, resolution_method, resolver_version, resolved_at
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT'
          AND pnl_pct < 0
        ORDER BY pnl_pct ASC
        LIMIT 20
    """)

    run_query(conn, "at_pick_outcomes: SL_HIT picks with POSITIVE pnl_pct (misclassified)", """
        SELECT
            pick_id, symbol, strategy, asset_class, status,
            pnl_pct, resolution_method, resolver_version, resolved_at
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT'
          AND pnl_pct > 0
        ORDER BY pnl_pct DESC
        LIMIT 20
    """)

    run_query(conn, "at_pick_outcomes: pnl_pct distribution for TP_HIT", """
        SELECT
            CASE
                WHEN pnl_pct < -10 THEN '< -10%'
                WHEN pnl_pct < -5  THEN '-10% to -5%'
                WHEN pnl_pct < -2  THEN '-5% to -2%'
                WHEN pnl_pct < 0   THEN '-2% to 0%'
                WHEN pnl_pct = 0   THEN '0%'
                WHEN pnl_pct <= 2  THEN '0% to 2%'
                WHEN pnl_pct <= 5  THEN '2% to 5%'
                WHEN pnl_pct <= 10 THEN '5% to 10%'
                ELSE '> 10%'
            END AS pnl_bucket,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT'
        GROUP BY pnl_bucket
        ORDER BY MIN(pnl_pct)
    """)

    run_query(conn, "at_pick_outcomes: pnl_pct distribution for SL_HIT", """
        SELECT
            CASE
                WHEN pnl_pct < -10 THEN '< -10%'
                WHEN pnl_pct < -5  THEN '-10% to -5%'
                WHEN pnl_pct < -2  THEN '-5% to -2%'
                WHEN pnl_pct < 0   THEN '-2% to 0%'
                WHEN pnl_pct = 0   THEN '0%'
                WHEN pnl_pct <= 2  THEN '0% to 2%'
                WHEN pnl_pct <= 5  THEN '2% to 5%'
                WHEN pnl_pct <= 10 THEN '5% to 10%'
                ELSE '> 10%'
            END AS pnl_bucket,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT'
        GROUP BY pnl_bucket
        ORDER BY MIN(pnl_pct)
    """)

    run_query(conn, "at_pick_outcomes: misclassified counts by resolver_version", """
        SELECT
            COALESCE(resolver_version, 'NULL') AS resolver_version,
            COUNT(*) AS total,
            SUM(CASE WHEN resolution_method = 'TP_HIT' AND pnl_pct < 0 THEN 1 ELSE 0 END) AS tp_hit_negative,
            SUM(CASE WHEN resolution_method = 'SL_HIT' AND pnl_pct > 0 THEN 1 ELSE 0 END) AS sl_hit_positive,
            ROUND(100.0 * SUM(CASE WHEN resolution_method = 'TP_HIT' AND pnl_pct < 0 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN resolution_method = 'TP_HIT' THEN 1 ELSE 0 END), 0), 2) AS tp_misclass_rate,
            ROUND(100.0 * SUM(CASE WHEN resolution_method = 'SL_HIT' AND pnl_pct > 0 THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN resolution_method = 'SL_HIT' THEN 1 ELSE 0 END), 0), 2) AS sl_misclass_rate
        FROM at_pick_outcomes
        WHERE resolution_method IN ('TP_HIT', 'SL_HIT')
        GROUP BY resolver_version
        ORDER BY total DESC
    """)

    run_query(conn, "at_pick_outcomes: asset class breakdown for TP_HIT / SL_HIT", """
        SELECT
            COALESCE(asset_class, 'NULL') AS asset_class,
            resolution_method,
            COUNT(*) AS total,
            ROUND(AVG(pnl_pct), 4) AS avg_pnl,
            ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate
        FROM at_pick_outcomes
        WHERE resolution_method IN ('TP_HIT', 'SL_HIT')
        GROUP BY asset_class, resolution_method
        ORDER BY asset_class, resolution_method
    """)

    # ==================================================================
    # 2. picks table — R:R analysis (independent query)
    # ==================================================================

    run_query(conn, "picks table: TP vs SL distance from entry (R:R ratio)", """
        SELECT
            direction,
            COUNT(*) AS total,
            ROUND(AVG(ABS(take_profit - entry_price) / NULLIF(entry_price, 0) * 100), 4) AS avg_tp_distance_pct,
            ROUND(AVG(ABS(stop_loss - entry_price) / NULLIF(entry_price, 0) * 100), 4) AS avg_sl_distance_pct,
            ROUND(AVG(ABS(take_profit - entry_price) / NULLIF(ABS(stop_loss - entry_price), 0)), 4) AS avg_rr_ratio
        FROM picks
        WHERE take_profit IS NOT NULL
          AND stop_loss IS NOT NULL
          AND entry_price IS NOT NULL
          AND take_profit > 0
          AND stop_loss > 0
          AND entry_price > 0
        GROUP BY direction
    """)

    run_query(conn, "picks table: picks where TP is CLOSER to entry than SL (bad R:R)", """
        SELECT
            direction,
            COUNT(*) AS total,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
        FROM picks
        WHERE take_profit IS NOT NULL
          AND stop_loss IS NOT NULL
          AND entry_price IS NOT NULL
          AND take_profit > 0
          AND stop_loss > 0
          AND entry_price > 0
          AND ABS(take_profit - entry_price) < ABS(stop_loss - entry_price)
        GROUP BY direction
    """)

    # ==================================================================
    # 3. at_raw_picks — exit_reason distribution (independent query)
    # ==================================================================

    run_query(conn, "at_raw_picks: exit_reason distribution", """
        SELECT
            COALESCE(exit_reason, 'NULL') AS exit_reason,
            COUNT(*) AS total,
            ROUND(AVG(pnl_pct), 4) AS avg_pnl,
            ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate
        FROM at_raw_picks
        WHERE status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
        GROUP BY exit_reason
        ORDER BY total DESC
    """)

    run_query(conn, "at_raw_picks: exit_reason x status cross-tab", """
        SELECT
            COALESCE(exit_reason, 'NULL') AS exit_reason,
            status,
            COUNT(*) AS total,
            ROUND(AVG(pnl_pct), 4) AS avg_pnl
        FROM at_raw_picks
        WHERE status IN ('WON', 'LOST', 'EXPIRED', 'CLOSED')
        GROUP BY exit_reason, status
        ORDER BY exit_reason, status
    """)

    # ==================================================================
    # 4. crypto_ohlcv verification for specific misclassified picks
    # ==================================================================

    misclassified = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT symbol, pnl_pct, resolution_method, resolved_at, resolver_version
            FROM at_pick_outcomes
            WHERE (
                (resolution_method = 'TP_HIT' AND pnl_pct < -2)
                OR
                (resolution_method = 'SL_HIT' AND pnl_pct > 2)
            )
            AND resolved_at >= '2026-05-01'
            ORDER BY ABS(pnl_pct) DESC
            LIMIT 10
        """)
        misclassified = cur.fetchall()

    print(f"\n{'='*100}")
    print(f"OHLCV VERIFICATION: {len(misclassified)} severe misclassified picks since 2026-05-01")
    print(f"{'='*100}")

    for row in misclassified:
        sym = row['symbol']
        pnl = row['pnl_pct']
        method = row['resolution_method']
        resolved = row['resolved_at']
        version = row['resolver_version']

        date_start = (resolved - timedelta(days=3)).strftime('%Y-%m-%d')
        date_end = (resolved + timedelta(days=1)).strftime('%Y-%m-%d')

        print(f"\n--- {sym} | {method} | pnl={pnl}% | resolved={resolved} | version={version} ---")

        with conn.cursor() as cur2:
            cur2.execute("""
                SELECT
                    FROM_UNIXTIME(timestamp/1000) AS dt,
                    open, high, low, close, volume
                FROM crypto_ohlcv
                WHERE symbol = %s
                  AND timeframe = '1h'
                  AND timestamp >= UNIX_TIMESTAMP(%s) * 1000
                  AND timestamp <= UNIX_TIMESTAMP(%s) * 1000
                ORDER BY timestamp
                LIMIT 50
            """, (sym, date_start, date_end))
            ohlcv = cur2.fetchall()
            if not ohlcv:
                print(f"  No 1h OHLCV data for {sym} between {date_start} and {date_end}")
                cur2.execute("""
                    SELECT timeframe, COUNT(*) AS c
                    FROM crypto_ohlcv
                    WHERE symbol = %s
                    GROUP BY timeframe
                """, (sym,))
                tfs = cur2.fetchall()
                if tfs:
                    print(f"  Available timeframes for {sym}: {tfs}")
                else:
                    print(f"  No OHLCV data at all for {sym}")
            else:
                print(f"  Found {len(ohlcv)} 1h candles. First 5:")
                for i, c in enumerate(ohlcv[:5]):
                    print(f"    {c['dt']}: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")
                print(f"  Last 3:")
                for c in ohlcv[-3:]:
                    print(f"    {c['dt']}: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")

    # ==================================================================
    # 5. Summary counts
    # ==================================================================

    run_query(conn, "SUMMARY: overall misclassification rates", """
        SELECT
            'TP_HIT with negative PnL' AS issue,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM at_pick_outcomes WHERE resolution_method = 'TP_HIT'), 2) AS pct_of_tp_hit
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT' AND pnl_pct < 0
        UNION ALL
        SELECT
            'SL_HIT with positive PnL' AS issue,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM at_pick_outcomes WHERE resolution_method = 'SL_HIT'), 2) AS pct_of_sl_hit
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT' AND pnl_pct > 0
        UNION ALL
        SELECT
            'TP_HIT total' AS issue,
            COUNT(*) AS count,
            100.0 AS pct_of_tp_hit
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT'
        UNION ALL
        SELECT
            'SL_HIT total' AS issue,
            COUNT(*) AS count,
            100.0 AS pct_of_sl_hit
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT'
    """)

    run_query(conn, "June 2026+ misclassification rates", """
        SELECT
            'TP_HIT with negative PnL (June+)' AS issue,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM at_pick_outcomes WHERE resolution_method = 'TP_HIT' AND resolved_at >= '2026-06-01'), 0), 2) AS pct
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT' AND pnl_pct < 0 AND resolved_at >= '2026-06-01'
        UNION ALL
        SELECT
            'SL_HIT with positive PnL (June+)' AS issue,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM at_pick_outcomes WHERE resolution_method = 'SL_HIT' AND resolved_at >= '2026-06-01'), 0), 2) AS pct
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT' AND pnl_pct > 0 AND resolved_at >= '2026-06-01'
        UNION ALL
        SELECT
            'TP_HIT total (June+)' AS issue,
            COUNT(*) AS count,
            100.0 AS pct
        FROM at_pick_outcomes
        WHERE resolution_method = 'TP_HIT' AND resolved_at >= '2026-06-01'
        UNION ALL
        SELECT
            'SL_HIT total (June+)' AS issue,
            COUNT(*) AS count,
            100.0 AS pct
        FROM at_pick_outcomes
        WHERE resolution_method = 'SL_HIT' AND resolved_at >= '2026-06-01'
    """)

    conn.close()
    print(f"\nInvestigation complete: {datetime.now().isoformat()}")

if __name__ == '__main__':
    main()
