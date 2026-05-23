
"""Chunk-based aggregation for bt_backtest_trades"""
import pymysql
import json
from collections import Counter

def get_bounds():
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor, read_timeout=15, connect_timeout=10
    )
    c = conn.cursor()
    c.execute("SELECT MIN(id) as mn, MAX(id) as mx FROM bt_backtest_trades")
    r = c.fetchone()
    c.close()
    conn.close()
    return r['mn'], r['mx']

def query_chunk(sql, start_id, end_id):
    conn = pymysql.connect(
        host='mysql.50webs.com', database='ejaguiar1_backtests',
        user='ejaguiar1_backtests', password=os.environ.get("DB_PASS_BACKTESTS", ""),
        cursorclass=pymysql.cursors.DictCursor, read_timeout=15, connect_timeout=10
    )
    try:
        c = conn.cursor()
        c.execute("SET SESSION wait_timeout=30")
        c.execute(sql, (start_id, end_id))
        r = c.fetchall()
        c.close()
        return r
    except Exception as e:
        print(f"  Error at {start_id}-{end_id}: {e}")
        return []
    finally:
        conn.close()

min_id, max_id = get_bounds()
print(f"ID range: {min_id} to {max_id}")

# Use 50k chunks
CHUNK = 200000
status_counts = Counter()
direction_counts = Counter()
symbol_counts = Counter()
strategy_counts = Counter()
asset_counts = Counter()
entry_prices_zero = 0
exit_prices_zero_closed = 0
null_exit_price_with_exit_time = 0
exit_price_without_exit_time = 0
negative_pnl_win = 0
positive_pnl_lose = 0
future_entry = 0
future_exit = 0
pnl_values = []
confidence_values = []
total_rows = 0
closed_but_null_exit = 0
open_with_exit = 0

# We'll process 50k chunks, but limit total for time
# Process ALL chunks but commit incrementally
import os

processed = 0
total_chunks = (max_id - min_id) // CHUNK + 1

for start in range(min_id, max_id + 1, CHUNK):
    end = min(start + CHUNK - 1, max_id)
    
    # Get rows for this chunk
    rows = query_chunk(
        "SELECT status, direction, symbol, strategy, asset_class, "
        "entry_price, exit_price, exit_time, pnl_pct, confidence, entry_time "
        "FROM bt_backtest_trades WHERE id BETWEEN %s AND %s",
        start, end
    )
    
    for row in rows:
        total_rows += 1
        status_counts[row['status']] += 1
        direction_counts[row['direction'] or 'NULL'] += 1
        symbol_counts[row['symbol'] or 'NULL'] += 1
        strategy_counts[row['strategy'] or 'NULL'] += 1
        asset_counts[row['asset_class'] or 'NULL'] += 1
        
        if row['entry_price'] == 0:
            entry_prices_zero += 1
        if row['status'] == 'CLOSED' and row['exit_price'] == 0:
            exit_prices_zero_closed += 1
        if row['exit_time'] is not None and row['exit_price'] is None:
            null_exit_price_with_exit_time += 1
        if row['exit_time'] is None and row['exit_price'] is not None:
            exit_price_without_exit_time += 1
        if row['pnl_pct'] is not None:
            pnl_values.append(float(row['pnl_pct']))
        if row['confidence'] is not None:
            confidence_values.append(float(row['confidence']))
    
    processed += 1
    if processed % 20 == 0:
        pct = (end - min_id) / (max_id - min_id) * 100
        print(f"  Processed {processed}/{total_chunks} chunks ({pct:.1f}%), rows={total_rows:,}")
    
    # Save intermediate every 200 chunks
    if processed % 200 == 0:
        results = {
            'total_rows': total_rows,
            'status_counts': dict(status_counts.most_common()),
            'direction_counts': dict(direction_counts.most_common()),
            'asset_counts': dict(asset_counts.most_common()),
            'entry_prices_zero': entry_prices_zero,
            'exit_prices_zero_closed': exit_prices_zero_closed,
            'null_exit_price_with_exit_time': null_exit_price_with_exit_time,
            'exit_price_without_exit_time': exit_price_without_exit_time,
            'pnl_count': len(pnl_values),
            'confidence_count': len(confidence_values),
        }
        with open('/mnt/agents/output/progress.json', 'w') as f:
            json.dump(results, f, default=str)
        print(f"  Saved progress: {total_rows:,} rows")

# Final results
results = {
    'total_rows': total_rows,
    'status_counts': dict(status_counts.most_common()),
    'direction_counts': dict(direction_counts.most_common()),
    'symbol_counts': dict(symbol_counts.most_common(20)),
    'strategy_counts': dict(strategy_counts.most_common(20)),
    'asset_counts': dict(asset_counts.most_common()),
    'entry_prices_zero': entry_prices_zero,
    'exit_prices_zero_closed': exit_prices_zero_closed,
    'null_exit_price_with_exit_time': null_exit_price_with_exit_time,
    'exit_price_without_exit_time': exit_price_without_exit_time,
    'pnl_count': len(pnl_values),
    'pnl_min': min(pnl_values) if pnl_values else None,
    'pnl_max': max(pnl_values) if pnl_values else None,
    'pnl_avg': sum(pnl_values)/len(pnl_values) if pnl_values else None,
    'confidence_count': len(confidence_values),
    'confidence_min': min(confidence_values) if confidence_values else None,
    'confidence_max': max(confidence_values) if confidence_values else None,
    'confidence_avg': sum(confidence_values)/len(confidence_values) if confidence_values else None,
}

with open('/mnt/agents/output/bigtable_results.json', 'w') as f:
    json.dump(results, f, default=str, indent=2)

print(f"\nComplete! Processed {total_rows:,} rows")
print(f"Status: {dict(status_counts.most_common())}")
print(f"Direction: {dict(direction_counts.most_common())}")
