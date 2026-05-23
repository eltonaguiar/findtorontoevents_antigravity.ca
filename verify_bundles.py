import sqlite3
conn = sqlite3.connect('battleground/data/bundle_babies.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM bundle_babies')
count = cursor.fetchone()[0]
print(f'Total bundles: {count}')
cursor.execute('SELECT name, backtest_sharpe FROM bundle_babies WHERE name LIKE "%Breakout%" OR name LIKE "%Regime%" OR name LIKE "%Liquidation%" OR name LIKE "%Momentum%" ORDER BY backtest_sharpe DESC')
new_bundles = cursor.fetchall()
print('New high-performance bundles:')
for name, sharpe in new_bundles:
    print(f'  {name}: Sharpe {sharpe:.1f}')
conn.close()