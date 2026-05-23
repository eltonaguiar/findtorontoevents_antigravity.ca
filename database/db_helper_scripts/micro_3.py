import os

import pymysql, json
conn = pymysql.connect(host='mysql.50webs.com', database='ejaguiar1_backtests', user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""), cursorclass=pymysql.cursors.DictCursor, read_timeout=30)
c = conn.cursor()
results = {}
# Asset class - use WHERE for each value (indexed)
for ac in ['CRYPTO', 'FOREX', 'EQUITY', 'PENNY_STOCK', 'MEMECOIN', 'SPORTS', 'FUTURES', 'ETF', 'COMMODITY', 'UNKNOWN', None]:
    if ac is None:
        c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE asset_class IS NULL")
    else:
        c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE asset_class=%s", (ac,))
    r = c.fetchone()
    results[f'ac_{ac or "NULL"}'] = r['cnt']

c.close()
conn.close()
with open('/mnt/agents/output/micro_3.json','w') as f:
    json.dump(results, f, indent=2)
print("OK")
