import os

"""Run all validation queries with reconnect-per-query"""
import pymysql
import json

def q(sql, params=(), fetch='all', timeout=25):
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor,
        read_timeout=timeout, connect_timeout=10
    )
    try:
        c = conn.cursor()
        c.execute("SET SESSION wait_timeout=60, net_read_timeout=60, max_execution_time=60000")
        c.execute(sql, params)
        if fetch == 'one':
            r = c.fetchone()
        else:
            r = c.fetchall()
        c.close()
        return {'ok': True, 'data': r}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        conn.close()

results = {}

# ===== SMALL TABLES FIRST =====
print("=== bt_backtest_runs ===")
results['runs_count'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_runs", fetch='one')
results['runs_zero_trades'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_runs WHERE total_trades=0", fetch='one')
results['runs_status'] = q("SELECT strategy, symbol, total_trades, win_rate FROM bt_backtest_runs LIMIT 10")

print("=== at_incubator ===")
results['incubator_count'] = q("SELECT COUNT(*) as cnt FROM at_incubator_backtest_results", fetch='one')
results['incubator_perms'] = q("SELECT DISTINCT perm_id FROM at_incubator_backtest_results LIMIT 20", fetch='all')

print("=== at_large ===")
results['large_count'] = q("SELECT COUNT(*) as cnt FROM at_large_backtest_results", fetch='one')
results['large_perms'] = q("SELECT DISTINCT perm_id FROM at_large_backtest_results LIMIT 20", fetch='all')

print("=== backtest_results ===")
results['br_count'] = q("SELECT COUNT(*) as cnt FROM backtest_results", fetch='one')
results['br_data'] = q("SELECT * FROM backtest_results", fetch='all')

print("=== backtest_trades ===")
results['bt_count'] = q("SELECT COUNT(*) as cnt FROM backtest_trades", fetch='one')
results['bt_data'] = q("SELECT * FROM backtest_trades", fetch='all')

# ===== bt_backtest_trades: INDEXED COLUMNS =====
print("=== bt_backtest_trades: indexed columns ===")
# Status already known
results['s_status'] = [
    {'status': 'OPEN', 'cnt': 26033106}, {'status': 'closed', 'cnt': 1191988},
    {'status': 'LOST', 'cnt': 845319}, {'status': 'WON', 'cnt': 605776},
    {'status': 'expired', 'cnt': 28340}, {'status': 'WIN', 'cnt': 265},
    {'status': 'LOSS', 'cnt': 195}, {'status': 'SL_HIT', 'cnt': 158},
    {'status': 'TP_HIT', 'cnt': 25}, {'status': 'CLOSED_SL', 'cnt': 23},
    {'status': 'CLOSED_TP', 'cnt': 23}
]

# Symbol and strategy (indexed) - top 20
results['s_top_symbols'] = q("SELECT symbol, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY symbol ORDER BY cnt DESC LIMIT 20")
results['s_top_strategies'] = q("SELECT strategy, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY strategy ORDER BY cnt DESC LIMIT 20")

# Asset class (indexed)
results['s_asset_class'] = q("SELECT asset_class, COUNT(*) as cnt, COUNT(DISTINCT symbol) as sym_cnt FROM bt_backtest_trades GROUP BY asset_class ORDER BY cnt DESC")

# Top symbols per asset class
for ac in ['CRYPTO', 'FOREX', 'EQUITY']:
    results[f's_symbols_{ac}'] = q(
        "SELECT symbol, COUNT(*) as cnt FROM bt_backtest_trades WHERE asset_class=%s GROUP BY symbol ORDER BY cnt DESC LIMIT 10",
        (ac,)
    )

# ===== bt_backtest_trades: PK-based range queries =====
print("=== bt_backtest_trades: PK range queries ===")
results['s_min_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id LIMIT 1", fetch='one')
results['s_max_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id DESC LIMIT 1", fetch='one')
results['s_min_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id LIMIT 1", fetch='one')
results['s_max_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id DESC LIMIT 1", fetch='one')

# ===== PnL and numeric checks via sampling =====
print("=== bt_backtest_trades: sampling ===")
results['s_sample_1'] = q("SELECT * FROM bt_backtest_trades ORDER BY id LIMIT 5", fetch='all')
results['s_sample_2'] = q("SELECT * FROM bt_backtest_trades ORDER BY RAND() LIMIT 5", fetch='all')

# ===== Cross-table checks =====
print("=== Cross-table checks ===")
# bt_backtest_runs strategies vs bt_backtest_trades strategies
results['x_runs_strategies'] = q("SELECT DISTINCT strategy FROM bt_backtest_runs WHERE strategy IS NOT NULL")
results['x_trades_strategies'] = q("SELECT DISTINCT strategy FROM bt_backtest_trades WHERE strategy IS NOT NULL LIMIT 100")

# perm_id overlap
results['x_perm_overlap'] = q("""
    SELECT COUNT(*) as cnt FROM (
        SELECT perm_id FROM at_incubator_backtest_results
        INTERSECT
        SELECT perm_id FROM at_large_backtest_results
    ) t
""", fetch='one')

results['x_perm_incubator_only'] = q("""
    SELECT COUNT(*) as cnt FROM (
        SELECT perm_id FROM at_incubator_backtest_results
        EXCEPT
        SELECT perm_id FROM at_large_backtest_results
    ) t
""", fetch='one')

with open('/mnt/agents/output/all_results.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print("All queries done!")
for k, v in results.items():
    status = "OK" if v.get('ok') else "ERR"
    print(f"  [{status}] {k}")
