import os

"""Run indexed-column queries on bt_backtest_trades"""
import pymysql
import json

def q(sql, params=(), fetch='all'):
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor, read_timeout=20, connect_timeout=10
    )
    try:
        c = conn.cursor()
        c.execute(sql, params)
        r = c.fetchone() if fetch == 'one' else c.fetchall()
        c.close()
        return {'ok': True, 'data': r}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    finally:
        conn.close()

results = {}

# Status counts (use index)
results['status'] = q("SELECT status, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY status ORDER BY cnt DESC")

# Asset class distribution
results['asset_class'] = q("SELECT asset_class, COUNT(*) as cnt, COUNT(DISTINCT symbol) as sym_cnt FROM bt_backtest_trades GROUP BY asset_class ORDER BY cnt DESC")

# Top symbols (use index)
results['top_symbols'] = q("SELECT symbol, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY symbol ORDER BY cnt DESC LIMIT 20")

# Top strategies (use index)
results['top_strategies'] = q("SELECT strategy, COUNT(*) as cnt FROM bt_backtest_trades GROUP BY strategy ORDER BY cnt DESC LIMIT 20")

# Per-asset-class top symbols
for ac in ['CRYPTO', 'FOREX', 'EQUITY', 'PENNY_STOCK', 'MEMECOIN', 'FUTURES', 'ETF', 'COMMODITY']:
    results[f'symbols_{ac}'] = q(
        "SELECT symbol, COUNT(*) as cnt FROM bt_backtest_trades WHERE asset_class=%s GROUP BY symbol ORDER BY cnt DESC LIMIT 10",
        (ac,)
    )

# Date range via PK
results['min_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id LIMIT 1", fetch='one')
results['max_entry'] = q("SELECT entry_time as t FROM bt_backtest_trades ORDER BY id DESC LIMIT 1", fetch='one')
results['min_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id LIMIT 1", fetch='one')
results['max_exit'] = q("SELECT exit_time as t FROM bt_backtest_trades WHERE exit_time IS NOT NULL ORDER BY id DESC LIMIT 1", fetch='one')

# PnL stats via sampling (5 samples of 1000)
for i in range(5):
    offset = i * 5000000
    results[f'pnl_sample_{i}'] = q(
        "SELECT MIN(pnl_pct) as mn, MAX(pnl_pct) as mx, AVG(pnl_pct) as av FROM bt_backtest_trades WHERE id BETWEEN %s AND %s",
        (offset + 1, offset + 5000000), fetch='one'
    )

# Entry/exit price anomalies
results['zero_entry'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE entry_price=0", fetch='one')
results['zero_exit_closed'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_price=0 AND status='CLOSED'", fetch='one')

# NULL exit_price with exit_time
results['null_exitprice'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_time IS NOT NULL AND exit_price IS NULL", fetch='one')

# exit_price without exit_time
results['exitprice_no_time'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE exit_time IS NULL AND exit_price IS NOT NULL", fetch='one')

# Direction counts
results['long'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='LONG'", fetch='one')
results['short'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction='SHORT'", fetch='one')
results['null_dir'] = q("SELECT COUNT(*) as cnt FROM bt_backtest_trades WHERE direction IS NULL", fetch='one')

# Confidence
results['conf_stats'] = q("SELECT MIN(confidence) as mn, MAX(confidence) as mx, AVG(confidence) as av FROM bt_backtest_trades", fetch='one')

with open('/mnt/agents/output/indexed_results.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print("Done!")
for k, v in results.items():
    print(f"  {k}: {'OK' if v['ok'] else v.get('error','')[:60]}")
