#!/usr/bin/env python3
"""Fast Wave 0 queries -- one connection, one query each, using indexes."""
import pymysql, sys

DB = dict(host="mysql.50webs.com", port=3306, user="ejaguiar1_stocks",
          password=os.environ.get("DB_PASS_STOCKS", ""), database="ejaguiar1_stocks",
          connect_timeout=15, read_timeout=60, charset="utf8mb4")

def run(label, sql):
    try:
        c = pymysql.connect(**DB)
        cur = c.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close(); c.close()
        return label, rows, None
    except Exception as e:
        return label, None, str(e)

queries = [
    # 1. EXPLAIN to verify indexes
    ("EXPLAIN-status", "EXPLAIN SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN'"),
    ("EXPLAIN-class", "EXPLAIN SELECT asset_class, COUNT(*) FROM bt_backtest_trades WHERE status='OPEN' GROUP BY asset_class"),
    # 2. OPEN sample: first 5000 by asset_class
    ("sample-asset-class", "SELECT asset_class, COUNT(*) AS n FROM (SELECT asset_class FROM bt_backtest_trades WHERE status='OPEN' LIMIT 50000) t GROUP BY asset_class ORDER BY n DESC"),
    # 3. OPEN sample: first 5000 by strategy
    ("sample-strategy", "SELECT strategy, COUNT(*) AS n FROM (SELECT strategy FROM bt_backtest_trades WHERE status='OPEN' AND strategy IS NOT NULL AND strategy!='' LIMIT 50000) t GROUP BY strategy ORDER BY n DESC LIMIT 20"),
    # 4. Recent Open (last 7 days) -- index-friendly with entry_time
    ("recent-open", "SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN' AND entry_time > NOW() - INTERVAL 7 DAY"),
    # 5. Very old Open (>60 days)
    ("old-open", "SELECT COUNT(*) FROM bt_backtest_trades WHERE status='OPEN' AND entry_time <= NOW() - INTERVAL 60 DAY"),
    # 6. Phantom EXPIRED: use expired status directly (only 30k per status dist)
    ("phantoms", "SELECT asset_class, COUNT(*) AS total, SUM(CASE WHEN pnl_pct=0 AND exit_price=entry_price THEN 1 ELSE 0 END) AS phantoms FROM bt_backtest_trades WHERE status='expired' GROUP BY asset_class ORDER BY phantoms DESC"),
    # 7. PnL integrity: sample 100k closed rows
    ("pnl-sample", "SELECT SUM(CASE WHEN entry_price>0 AND exit_price>0 AND ABS(pnl_pct-((exit_price-entry_price)/entry_price*100))>1 THEN 1 ELSE 0 END) AS mismatches, COUNT(*) AS total FROM (SELECT entry_price,exit_price,pnl_pct FROM bt_backtest_trades WHERE status IN ('WON','LOST','closed','WIN','LOSS') AND pnl_pct IS NOT NULL LIMIT 100000) t"),
    # 8. Freeze check
    ("freeze", "SELECT MAX(imported_at), TIMESTAMPDIFF(HOUR, MAX(imported_at), NOW()) FROM bt_backtest_trades WHERE status IN ('WON','LOST')"),
    # 9. Recent writes
    ("recent-writes", "SELECT COUNT(*), MAX(imported_at) FROM bt_backtest_trades WHERE imported_at > NOW() - INTERVAL 1 HOUR"),
    # 10. NULL ratios on bt_backtest_trades key columns
    ("nulls-bt", "SELECT SUM(CASE WHEN confidence IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN pnl_pct IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN entry_price IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN exit_price IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN strategy IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN direction IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM bt_backtest_trades"),
]

for label, sql in queries:
    print(f"[{label}] ...")
    label, rows, err = run(label, sql)
    if err:
        print(f"  FAIL: {err}")
    elif rows:
        for r in rows[:25]:
            print(f"  {r}")
        if len(rows) > 25:
            print(f"  ... ({len(rows)} total rows)")
    print()
