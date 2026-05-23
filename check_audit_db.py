import sqlite3
import json

try:
    conn = sqlite3.connect('data/audit_trail.db')
    c = conn.cursor()
    c.execute('SELECT payload FROM events WHERE event_type = "BACKTEST_RESULT" ORDER BY timestamp DESC LIMIT 15')
    rows = c.fetchall()
    print('Recent Backtest Results from Audit Database:')
    print('=' * 60)
    for row in rows:
        payload = json.loads(row[0])
        print(f"Strategy: {payload['strategy']}")
        print(f"  Trades: {payload['total_trades']}")
        print(f"  Win Rate: {payload['win_rate']:.1f}%")
        print(f"  PnL: {payload['total_pnl_pct']:+.2f}%")
        print(f"  Profit Factor: {payload['profit_factor']:.2f}")
        print(f"  Max DD: {payload['max_drawdown_pct']:.2f}%")
        print()
    conn.close()
except Exception as e:
    print('Error:', e)