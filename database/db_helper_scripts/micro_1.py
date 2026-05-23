import os

import pymysql, json
conn = pymysql.connect(host='mysql.50webs.com', database='ejaguiar1_backtests', user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""), cursorclass=pymysql.cursors.DictCursor, read_timeout=30)
c = conn.cursor()
results = {}
# Single query per connection
c.execute("SELECT status, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY status ORDER BY cnt DESC")
results['status'] = c.fetchall()
c.close()
conn.close()
with open('/mnt/agents/output/micro_1.json','w') as f:
    json.dump(results, f, default=str, indent=2)
print("OK")
