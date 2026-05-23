import sqlite3

conn = sqlite3.connect('data/audit_trail.db')
cursor = conn.cursor()

# Check all tables row counts
print("=== TABLE ROW COUNTS ===")
tables = ['raw_picks', 'consensus_picks', 'bt_backtest_trades', 'bt_backtest_runs', 'strategy_stats', 'filter_log', 'audit_events']
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count}")

# Check bt_backtest_runs for strategy performance data
print("\n=== BACKTEST RUNS (Top 20) ===")
cursor.execute("""
    SELECT strategy, asset_class, total_trades, win_rate, profit_factor, sharpe, max_drawdown
    FROM bt_backtest_runs
    WHERE total_trades >= 10
    ORDER BY win_rate DESC, profit_factor DESC
    LIMIT 20
""")

for row in cursor.fetchall():
    print(f"  {row[0][:40]:40} | {row[1]:8} | Trades: {row[2]:4} | WR: {row[3]}% | PF: {row[4]} | Sharpe: {row[5]}")

# Sample some raw_picks
print("\n=== SAMPLE RAW_PICKS ===")
cursor.execute("""
    SELECT source_system, symbol, direction, strategy, asset_class
    FROM raw_picks
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
