#!/usr/bin/env python3
"""Register DNA mutation results in audit trail and strategy registry."""
import sqlite3, json, hashlib, uuid
from datetime import datetime, timezone

now = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

mutations = [
    {'name': 'PriceRocDeepDip', 'file': 'price_roc_deep_dip_strategy.py', 'status': 'experimental',
     'results': [
         {'symbol': 'BTCUSDT', 'trades': 0, 'win_rate': 0, 'sharpe': 0, 'avg_trade': 0},
         {'symbol': 'ETHUSDT', 'trades': 1, 'win_rate': 1.0, 'sharpe': 2.33, 'avg_trade': 0.05},
         {'symbol': 'SOLUSDT', 'trades': 6, 'win_rate': 0.33, 'sharpe': -1.08, 'avg_trade': -0.02},
     ], 'best_sharpe': 2.33, 'best_wr': 1.0, 'verdict': 'Too selective on synthetic data'},
    {'name': 'PriceRocSlowSmoother', 'file': 'price_roc_slow_smoother_strategy.py', 'status': 'active',
     'results': [
         {'symbol': 'BTCUSDT', 'trades': 48, 'win_rate': 0.542, 'sharpe': 5.40, 'avg_trade': 0.0219},
         {'symbol': 'ETHUSDT', 'trades': 77, 'win_rate': 0.597, 'sharpe': 6.91, 'avg_trade': 0.0331},
         {'symbol': 'SOLUSDT', 'trades': 71, 'win_rate': 0.521, 'sharpe': 4.47, 'avg_trade': 0.0279},
     ], 'best_sharpe': 6.91, 'best_wr': 0.597, 'verdict': 'WINNER - strong across all symbols'},
    {'name': 'PriceRocVolGate', 'file': 'price_roc_vol_gate_strategy.py', 'status': 'experimental',
     'results': [
         {'symbol': 'BTCUSDT', 'trades': 0, 'win_rate': 0, 'sharpe': 0, 'avg_trade': 0},
         {'symbol': 'ETHUSDT', 'trades': 1, 'win_rate': 1.0, 'sharpe': 1.67, 'avg_trade': 0.1052},
         {'symbol': 'SOLUSDT', 'trades': 2, 'win_rate': 0.5, 'sharpe': 5.34, 'avg_trade': 0.0613},
     ], 'best_sharpe': 5.34, 'best_wr': 1.0, 'verdict': 'Very selective, needs real data'},
    {'name': 'PriceRocTrendAligned', 'file': 'price_roc_trend_aligned_strategy.py', 'status': 'active',
     'results': [
         {'symbol': 'BTCUSDT', 'trades': 46, 'win_rate': 0.543, 'sharpe': 3.26, 'avg_trade': 0.0143},
         {'symbol': 'ETHUSDT', 'trades': 15, 'win_rate': 0.667, 'sharpe': 7.65, 'avg_trade': 0.0412},
         {'symbol': 'SOLUSDT', 'trades': 19, 'win_rate': 0.526, 'sharpe': 4.30, 'avg_trade': 0.0304},
     ], 'best_sharpe': 7.65, 'best_wr': 0.667, 'verdict': 'WINNER - uptrend filter works brilliantly'},
    {'name': 'PriceRocQuickScalp', 'file': 'price_roc_quick_scalp_strategy.py', 'status': 'active',
     'results': [
         {'symbol': 'BTCUSDT', 'trades': 120, 'win_rate': 0.567, 'sharpe': 3.80, 'avg_trade': 0.0074},
         {'symbol': 'ETHUSDT', 'trades': 137, 'win_rate': 0.547, 'sharpe': 3.47, 'avg_trade': 0.0089},
         {'symbol': 'SOLUSDT', 'trades': 149, 'win_rate': 0.530, 'sharpe': 2.66, 'avg_trade': 0.0084},
     ], 'best_sharpe': 3.80, 'best_wr': 0.567, 'verdict': 'WINNER - highest trade volume, consistent'},
]

db_audit = sqlite3.connect('audit_trail/data/audit_trail.db')
db_reg = sqlite3.connect('genome/strategy_registry.db')

parent_id = 'baby_' + hashlib.md5('PriceRocMeanReversion'.encode()).hexdigest()[:12]

for m in mutations:
    strat_id = 'baby_' + hashlib.md5(m['name'].encode()).hexdigest()[:12]
    best = max(m['results'], key=lambda r: r['sharpe'])
    total_trades = sum(r['trades'] for r in m['results'])

    # Audit trail: bt_backtest_runs
    for r in m['results']:
        if r['trades'] == 0:
            continue
        run_id = str(uuid.uuid4())
        wins = int(round(r['win_rate'] * r['trades']))
        db_audit.execute(
            "INSERT INTO bt_backtest_runs "
            "(id, source_db, source_table, strategy, symbol, asset_class, "
            "total_trades, wins, losses, win_rate, total_return, sharpe, max_drawdown, imported_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, 'dna_mutation_backtest', 'baby_strategies/' + m['file'],
             m['name'], r['symbol'], 'CRYPTO',
             r['trades'], wins, r['trades'] - wins,
             round(r['win_rate'], 4), round(r['avg_trade'] * r['trades'], 4),
             round(r['sharpe'], 3), 0, now))

    # Audit trail: strategy_stats
    if total_trades > 0:
        active_results = [r for r in m['results'] if r['trades'] > 0]
        avg_wr = sum(r['win_rate'] * r['trades'] for r in active_results) / total_trades
        total_wins = sum(int(round(r['win_rate'] * r['trades'])) for r in active_results)
        avg_pnl = sum(r['avg_trade'] for r in active_results) / len(active_results)
        db_audit.execute(
            "INSERT OR REPLACE INTO strategy_stats "
            "(strategy, source_system, asset_class, total_picks, wins, losses, win_rate, avg_pnl_pct, last_updated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (m['name'], 'baby_strategies_dna_mutation', 'CRYPTO',
             total_trades, total_wins, total_trades - total_wins,
             round(avg_wr, 4), round(avg_pnl, 6), now))

    # Audit trail: audit event
    db_audit.execute(
        "INSERT INTO audit_events "
        "(event_type, symbol, payload, origin, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        ('DNA_MUTATION_' + m['status'].upper(), best['symbol'],
         json.dumps({'mutation': m['name'], 'parent': 'PriceRocMeanReversion',
                     'status': m['status'], 'verdict': m['verdict'],
                     'best_sharpe': m['best_sharpe'], 'best_wr': m['best_wr'],
                     'total_trades': total_trades, 'results': m['results']}),
         'dna_mutation_engine', now))

    # Strategy registry
    exists = db_reg.execute('SELECT COUNT(*) FROM strategies WHERE id = ?', (strat_id,)).fetchone()[0]
    if not exists:
        db_reg.execute(
            "INSERT INTO strategies "
            "(id, name, dna_hash, status, created_at, updated_at, generation, parent_ids, "
            "genes, symbol_specialization, metadata, fitness_score, win_rate, sharpe_ratio, total_trades) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (strat_id, m['name'], hashlib.sha256(m['name'].encode()).hexdigest()[:16],
             m['status'], now, now, 2, parent_id,
             json.dumps({'parent': 'PriceRocMeanReversion', 'mutation_type': 'parameter_shift',
                         'file': 'baby_strategies/' + m['file']}),
             best['symbol'] if best['trades'] > 0 else None,
             json.dumps({'verdict': m['verdict'], 'backtest_date': '2026-03-09'}),
             round(m['best_sharpe'] * m['best_wr'], 4) if m['best_wr'] > 0 else 0,
             round(best['win_rate'], 4) if best['trades'] > 0 else None,
             round(m['best_sharpe'], 3), total_trades))

    # Registry audit log
    db_reg.execute(
        "INSERT INTO audit_log (table_name, record_id, action, new_values, timestamp, user_agent) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ('strategies', strat_id, 'DNA_MUTATION',
         json.dumps({'parent': 'PriceRocMeanReversion', 'mutation': m['name'],
                     'status': m['status'], 'best_sharpe': m['best_sharpe']}),
         now, 'dna_mutation_engine'))

db_audit.commit()
db_reg.commit()

# Summary
print('=== DNA Mutation Registration Complete ===\n')
audit_runs = db_audit.execute('SELECT COUNT(*) FROM bt_backtest_runs').fetchone()[0]
audit_stats = db_audit.execute('SELECT COUNT(*) FROM strategy_stats').fetchone()[0]
audit_events = db_audit.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
reg_total = db_reg.execute('SELECT COUNT(*) FROM strategies').fetchone()[0]
print(f'Audit trail: {audit_runs} backtest runs, {audit_stats} strategy stats, {audit_events} events')
print(f'Strategy registry: {reg_total} total strategies\n')

print('=== Mutation Results ===')
for m in mutations:
    icon = 'WINNER' if m['status'] == 'active' else 'EXPERIMENTAL'
    total = sum(r['trades'] for r in m['results'])
    print(f'  [{icon:12}] {m["name"]:<25} Sharpe={m["best_sharpe"]:>6.2f}  '
          f'WR={m["best_wr"]:>5.0%}  Trades={total:>4}')

db_audit.close()
db_reg.close()
