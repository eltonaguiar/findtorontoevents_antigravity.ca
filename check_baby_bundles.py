#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('battleground/data/bundle_babies.db')
cursor = conn.cursor()

print('='*70)
print('BABY BUNDLES - CURRENT STATUS')
print('='*70)

cursor.execute('SELECT bundle_id, name, symbol_scope, timeframe_scope, direction_bias, backtest_sharpe, forward_trades, forward_status, strategy_names FROM bundle_babies ORDER BY backtest_sharpe DESC')
for row in cursor.fetchall():
    print(f"\n[Bundle] {row[1]}")
    print(f"  ID: {row[0]}")
    print(f"  Classification: {row[2]} | {row[3]} | {row[4]}")
    print(f"  Backtest Sharpe: {row[5]:.2f}")
    print(f"  Forward Trades: {row[6]}")
    print(f"  Status: {row[7]}")
    strategies = json.loads(row[8]) if row[8] else []
    print(f"  Strategies ({len(strategies)}): {', '.join(strategies)}")

print('\n' + '='*70)
print('FORWARD TRADES - AUDIT TRAIL')
print('='*70)

cursor.execute('SELECT * FROM bundle_trades ORDER BY entry_time_utc DESC')
columns = [desc[0] for desc in cursor.description]
rows = cursor.fetchall()

if rows:
    for row in rows:
        print(f"\n--- Trade: {row[0]} ---")
        data = dict(zip(columns, row))
        print(f"  Bundle: {data['bundle_id']}")
        print(f"  Strategy: {data['strategy_name']}")
        print(f"  Symbol: {data['symbol']}")
        print(f"  Side: {data['side']}")
        print(f"  Entry Time (EST): {data['entry_time_est']}")
        print(f"  Entry Price: ${data['entry_price']:.2f}")
        print(f"  Take Profit: ${data['take_profit']:.2f}")
        print(f"  Stop Loss: ${data['stop_loss']:.2f}")
        print(f"  TP Distance Remaining: {data['tp_distance_remaining_pct']:.2f}%")
        print(f"  SL Distance Remaining: {data['sl_distance_remaining_pct']:.2f}%")
        print(f"  Realized PnL: {data['realized_pnl_pct']:.2f}%")
        print(f"  Unrealized PnL: {data['unrealized_pnl_pct']:.2f}%")
        print(f"  Max Profit: {data['max_profit_pct']:.2f}%")
        print(f"  Max Loss: {data['max_loss_pct']:.2f}%")
        print(f"  Status: {data['status']}")
        if data['exit_time_est']:
            print(f"  Exit Time (EST): {data['exit_time_est']}")
            print(f"  Exit Price: ${data['exit_price']:.2f}")
            print(f"  Exit Reason: {data['exit_reason']}")
        print(f"  Bars Held: {data['bars_held']}")
        print(f"  Time in Trade: {data['time_in_trade_minutes']} minutes")
else:
    print('No trades recorded yet.')

conn.close()
