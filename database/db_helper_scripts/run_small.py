import os

import pymysql
import json

def q(sql, fetch='all'):
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor, read_timeout=20, connect_timeout=10
    )
    try:
        c = conn.cursor()
        c.execute(sql)
        r = c.fetchone() if fetch == 'one' else c.fetchall()
        c.close()
        return {'ok': True, 'data': r}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        conn.close()

results = {}

# SMALL TABLES
results['runs'] = q("SELECT * FROM bt_backtest_runs")
results['incubator'] = q("SELECT * FROM at_incubator_backtest_results")
results['large'] = q("SELECT * FROM at_large_backtest_results")
results['backtest_results'] = q("SELECT * FROM backtest_results")
results['backtest_trades'] = q("SELECT * FROM backtest_trades")

# COUNTS
results['runs_count'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_runs", fetch='one')
results['inc_count'] = q("SELECT COUNT(*) as cnt FROM at_incubator_backtest_results", fetch='one')
results['large_count'] = q("SELECT COUNT(*) as cnt FROM at_large_backtest_results", fetch='one')
results['br_count'] = q("SELECT COUNT(*) as cnt FROM backtest_results", fetch='one')
results['bt_count'] = q("SELECT COUNT(*) as cnt FROM backtest_trades", fetch='one')

with open('/mnt/agents/output/small_tables.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print("Done!")
for k, v in results.items():
    print(f"  {k}: {'OK' if v['ok'] else v.get('error','')[:60]}")
