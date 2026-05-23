import sqlite3

conn = sqlite3.connect('data/audit_trail.db')
cursor = conn.cursor()

# Strategy performance - check consensus_picks which has status
print("=== CONSENSUS_PICKS PERFORMANCE (with status) ===")
cursor.execute("SELECT status, COUNT(*) FROM consensus_picks GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check bt_backtest_trades for strategy performance
print("\n=== BACKTEST STRATEGY PERFORMANCE (10+ trades) ===")
cursor.execute("""
    SELECT strategy, asset_class,
           COUNT(*) as total_trades,
           SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN status='LOST' THEN 1 ELSE 0 END) as losses,
           ROUND(AVG(pnl_pct), 2) as avg_pnl,
           ROUND(SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) * 100.0 / 
                 NULLIF(COUNT(*), 0), 1) as win_rate,
           ROUND(SUM(CASE WHEN status='WON' THEN ABS(pnl_pct) ELSE 0 END) /
                 NULLIF(SUM(CASE WHEN status='LOST' THEN ABS(pnl_pct) ELSE 0 END), 0), 2) as profit_factor
    FROM bt_backtest_trades
    WHERE status IN ('WON', 'LOST') AND pnl_pct IS NOT NULL
    GROUP BY strategy, asset_class
    HAVING total_trades >= 10
    ORDER BY win_rate DESC, profit_factor DESC
    LIMIT 30
""")

for row in cursor.fetchall():
    print(f"{row[0]:40} | {row[1]:8} | Trades: {row[2]:4} | WR: {row[6]}% | PF: {row[7]} | Avg: {row[5]}%")

# Check for any existing Justin strategies
print("\n=== EXISTING JUSTIN STRATEGIES ===")
cursor.execute("""
    SELECT strategy, COUNT(*) 
    FROM bt_backtest_trades 
    WHERE strategy LIKE '%justin%' OR strategy LIKE '%ema9%' OR strategy LIKE '%bravo%'
    GROUP BY strategy
""")
justin_strats = cursor.fetchall()
if justin_strats:
    for row in justin_strats:
        print(f"  {row[0]}: {row[1]} trades")
else:
    print("  No existing Justin/EMA9/Bravo strategies found")

# Check strategy_stats table
print("\n=== STRATEGY_STATS TABLE ===")
cursor.execute("SELECT * FROM strategy_stats LIMIT 5")
for row in cursor.fetchall():
    print(row)

conn.close()
