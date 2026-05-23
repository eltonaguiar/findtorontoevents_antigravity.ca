import os

import pymysql, json
conn = pymysql.connect(host='mysql.50webs.com', database='ejaguiar1_backtests', user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""), cursorclass=pymysql.cursors.DictCursor, read_timeout=30)
c = conn.cursor()
c.execute("SELECT asset_class, COUNT(*) as cnt, COUNT(DISTINCT symbol) as sym_cnt FROM bt_backtest_trades GROUP BY asset_class ORDER BY cnt DESC")
results = {'asset_class': c.fetchall()}
c.close()
conn.close()
with open('/mnt/agents/output/micro_2.json','w') as f:
    json.dump(results, f, default=str, indent=2)
print("OK")
