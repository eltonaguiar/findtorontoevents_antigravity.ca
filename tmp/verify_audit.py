import sqlite3

conn = sqlite3.connect('data/audit_trail.db')
cursor = conn.cursor()

print("=== JUSTIN/BRAVO STRATEGIES IN AUDIT DB ===\n")

# Check bt_backtest_runs
cursor.execute("""
    SELECT strategy, symbol, total_trades, win_rate, profit_factor, total_return, sharpe
    FROM bt_backtest_runs
    WHERE strategy LIKE '%justin%' OR strategy LIKE '%bravo%'
    ORDER BY win_rate DESC, profit_factor DESC
""")

print("Backtest Runs (Justin/Bravo Strategies):")
print("-" * 100)
for row in cursor.fetchall():
    print(f"{row[0]:35} | {row[1]:12} | Trades: {row[2]:3} | WR: {row[3]*100:5.1f}% | PF: {row[4]:5.2f} | Return: {row[5]:8.2f}% | Sharpe: {row[6]:5.2f}")

# Count total
cursor.execute("""
    SELECT COUNT(*), SUM(total_trades)
    FROM bt_backtest_runs
    WHERE strategy LIKE '%justin%' OR strategy LIKE '%bravo%'
""")
count, total_trades = cursor.fetchone()
print(f"\nTotal: {count} strategy-pair combinations, {total_trades} trades")

# Check bt_backtest_trades
cursor.execute("""
    SELECT COUNT(*), 
           SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN status='LOST' THEN 1 ELSE 0 END) as losses
    FROM bt_backtest_trades
    WHERE strategy LIKE '%justin%' OR strategy LIKE '%bravo%'
""")

row = cursor.fetchone()
print(f"\nIndividual trades: {row[0]} total, {row[1]} wins, {row[2]} losses")

conn.close()
