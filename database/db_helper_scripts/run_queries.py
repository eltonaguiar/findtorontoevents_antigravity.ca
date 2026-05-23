import os

import pymysql
import json

def q(sql, params=()):
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=15, connect_timeout=10
    )
    try:
        c = conn.cursor()
        c.execute("SET SESSION wait_timeout=30, net_read_timeout=30")
        c.execute(sql, params)
        r = c.fetchall()
        c.close()
        return r
    except Exception as e:
        return [{'error': str(e)}]
    finally:
        conn.close()

results = {}

# 1B: Status
results['1b_status'] = q("SELECT status, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY status ORDER BY cnt DESC")

# 1C: Direction - individual counts (WHERE is faster than GROUP BY on unindexed)
results['1c_long'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='LONG'")
results['1c_short'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='SHORT'")
results['1c_null_dir'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction IS NULL")

# 1D: Date ranges
results['1d_min_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id LIMIT 1")
results['1d_max_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id DESC LIMIT 1")
results['1d_min_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id LIMIT 1")
results['1d_max_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id DESC LIMIT 1")
results['1d_future_entry'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE entry_time > NOW()")
results['1d_future_exit'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_time > NOW()")

# 1E: Top 20 symbols
results['1e_top_symbols'] = q("SELECT symbol, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY symbol ORDER BY cnt DESC LIMIT 20")

# 1F: Top 20 strategies
results['1f_top_strategies'] = q("SELECT strategy, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY strategy ORDER BY cnt DESC LIMIT 20")

# 1G: NULL exit_price with exit_time
results['1g'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_time IS NOT NULL AND exit_price IS NULL")

# 1H: exit_price without exit_time
results['1h'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_time IS NULL AND exit_price IS NOT NULL")

with open('/mnt/agents/output/query_results_s1.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print("Section 1 queries done!")
for k, v in results.items():
    print(f"  {k}: {v}")
