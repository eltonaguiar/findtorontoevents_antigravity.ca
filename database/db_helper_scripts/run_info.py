import os

import pymysql
import json

conn = pymysql.connect(
    host='mysql.50webs.com', database='ejaguiar1_backtests',
    user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
    cursorclass=pymysql.cursors.DictCursor, read_timeout=15, connect_timeout=10
)
c = conn.cursor()

results = {}

# Table status
c.execute("SHOW TABLE STATUS")
results['table_status'] = c.fetchall()

# Column info
c.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA='ejaguiar1_backtests'
    ORDER BY TABLE_NAME, ORDINAL_POSITION
""")
results['columns'] = c.fetchall()

# Index info
c.execute("""
    SELECT TABLE_NAME, INDEX_NAME, COLUMN_NAME, NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA='ejaguiar1_backtests'
    ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
""")
results['indexes'] = c.fetchall()

# Foreign keys
c.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA='ejaguiar1_backtests' AND REFERENCED_TABLE_NAME IS NOT NULL
""")
results['foreign_keys'] = c.fetchall()

# Table constraints
c.execute("""
    SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA='ejaguiar1_backtests'
""")
results['constraints'] = c.fetchall()

# Get row counts via COUNT (small tables only)
for tbl in ['bt_backtest_runs', 'at_incubator_backtest_results', 'at_large_backtest_results', 'backtest_results', 'backtest_trades']:
    c.execute(f"SELECT COUNT(*) as cnt FROM {tbl}")
    results[f'count_{tbl}'] = c.fetchone()

# Try quick counts on bt_backtest_trades using indexed columns
c.execute("SELECT status, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY status ORDER BY cnt DESC")
results['bt_status'] = c.fetchall()

# Get min/max id
c.execute("SELECT MIN(id) as mn, MAX(id) as mx FROM bt_backtest_trades")
results['bt_id_range'] = c.fetchone()

# Get a sample row
c.execute("SELECT * FROM bt_backtest_trades LIMIT 1")
results['bt_sample'] = c.fetchone()

# Distinct asset classes
c.execute("SELECT DISTINCT asset_class FROM bt_backtest_trades")
results['bt_asset_classes'] = c.fetchall()

# Distinct strategies in runs
c.execute("SELECT DISTINCT strategy FROM bt_backtest_runs")
results['run_strategies'] = c.fetchall()

# Distinct strategies in trades (limit to avoid timeout)
c.execute("SELECT DISTINCT strategy FROM bt_backtest_trades LIMIT 100")
results['trade_strategies'] = c.fetchall()

# Get all bt_backtest_runs
c.execute("SELECT * FROM bt_backtest_runs")
results['all_runs'] = c.fetchall()

# Get all at_incubator
c.execute("SELECT perm_id, archetype, symbol, total_trades, wins, losses, win_rate, total_return, sharpe, max_drawdown FROM at_incubator_backtest_results")
results['all_incubator'] = c.fetchall()

# Get all at_large
c.execute("SELECT perm_id, archetype, symbol, total_trades, wins, losses, win_rate, total_return, sharpe, max_drawdown FROM at_large_backtest_results")
results['all_large'] = c.fetchall()

# Cross-table: perm_id overlap
c.execute("""
    SELECT i.perm_id, i.symbol as i_sym, i.total_trades as i_trades, i.win_rate as i_wr, i.total_return as i_ret,
           l.symbol as l_sym, l.total_trades as l_trades, l.win_rate as l_wr, l.total_return as l_ret
    FROM at_incubator_backtest_results i
    LEFT JOIN at_large_backtest_results l ON i.perm_id = l.perm_id AND i.symbol = l.symbol
""")
results['incubator_large_join'] = c.fetchall()

with open('/mnt/agents/output/info_results.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print(f"Done! Wrote {len(results)} result sets.")
c.close()
conn.close()
