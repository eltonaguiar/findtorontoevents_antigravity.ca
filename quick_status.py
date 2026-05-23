#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('battleground/data/bundle_babies.db')
cursor = conn.cursor()

print('BUNDLE FORWARD STATUS:')
print('-'*60)
cursor.execute('SELECT name, forward_trades, forward_realized_pnl, forward_status FROM bundle_babies ORDER BY backtest_sharpe DESC')
for row in cursor.fetchall():
    print(f"{row[0][:45]:<45} | Trades: {row[1]:>3} | PnL: {row[2]:>8.2f}% | {row[3]}")

print('\n' + '='*60)
print('LATEST TRADE:')
cursor.execute('SELECT strategy_name, entry_time_est, entry_price, take_profit, stop_loss, status FROM bundle_trades ORDER BY entry_time_utc DESC LIMIT 1')
row = cursor.fetchone()
if row:
    print(f"  Strategy: {row[0]}")
    print(f"  Entry (EST): {row[1]}")
    print(f"  Entry Price: ${row[2]:.2f}")
    print(f"  Take Profit: ${row[3]:.2f}")
    print(f"  Stop Loss: ${row[4]:.2f}")
    print(f"  Status: {row[5]}")

conn.close()
