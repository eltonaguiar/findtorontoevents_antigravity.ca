import os

import pymysql, json
conn = pymysql.connect(host='mysql.50webs.com', database='ejaguiar1_backtests', user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""), cursorclass=pymysql.cursors.DictCursor, read_timeout=30)
c = conn.cursor()
results = {}

# Direction counts (WHERE should use enum evaluation)
c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='LONG'")
results['long'] = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='SHORT'")
results['short'] = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction IS NULL")
results['null_dir'] = c.fetchone()['cnt']

# Date range via PK ordering
c.execute("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id LIMIT 1")
results['min_entry'] = str(c.fetchone()['t'])
c.execute("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id DESC LIMIT 1")
results['max_entry'] = str(c.fetchone()['t'])
c.execute("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id LIMIT 1")
results['min_exit'] = str(c.fetchone()['t'])
c.execute("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id DESC LIMIT 1")
r = c.fetchone()
results['max_exit'] = str(r['t']) if r else None

# Anomaly counts using indexed status
c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE entry_price=0")
results['zero_entry'] = c.fetchone()['cnt']
c.execute("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_price=0 AND status='CLOSED'")
results['zero_exit_closed'] = c.fetchone()['cnt']

# Confidence
c.execute("SELECT MIN(confidence) as mn, MAX(confidence) as mx, AVG(confidence) as av FROM bt_backtest_trades")
r = c.fetchone()
results['conf_min'] = float(r['mn']) if r['mn'] else None
results['conf_max'] = float(r['mx']) if r['mx'] else None
results['conf_avg'] = float(r['av']) if r['av'] else None

c.close()
conn.close()
with open('/mnt/agents/output/micro_4.json','w') as f:
    json.dump(results, f, indent=2)
print("OK")
