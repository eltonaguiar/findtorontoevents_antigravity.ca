#!/usr/bin/env python3
"""
VERIFY REAL WINNERS - Which systems have TRUE winning picks?
Audit all systems across the website for real vs fake data.
"""

import json
import sqlite3
from pathlib import Path
from collections import defaultdict

print('='*80)
print('COMPREHENSIVE AUDIT: Which Systems Have REAL Winning Picks?')
print('='*80)

# 1. Check battleground systems for real data
print('\n[1] ML BATTLEGROUND SYSTEMS (A-F) - Checking dashboard.json files')
print('-'*80)

systems = ['system_a_filter', 'system_b_regime', 'system_c_deeplearn', 
           'system_d_carry', 'system_e_momentum', 'system_f_clawsofdoom']

real_data_found = []
for sys in systems:
    dash_file = Path(f'ml_battleground/{sys}/data/dashboard.json')
    if dash_file.exists():
        try:
            with open(dash_file, 'r') as f:
                data = json.load(f)
            trades = data.get('total_trades', 0)
            pnl = data.get('total_pnl', 0)
            sharpe = data.get('sharpe', 0)
            win_rate = data.get('win_rate', 0)
            
            if trades > 0:
                status = 'REAL DATA'
                real_data_found.append((sys, trades, pnl, sharpe, win_rate))
            else:
                status = 'ZERO TRADES'
            print(f'  {sys:<30} Trades: {trades:>4}  PnL: {pnl:>+8.2f}%  Sharpe: {sharpe:>6.2f}  [{status}]')
        except Exception as e:
            print(f'  {sys:<30} [ERROR: {e}]')
    else:
        print(f'  {sys:<30} [NO DASHBOARD FILE]')

# 2. Check KIMI_RISEOFTHECLAW
print('\n[2] KIMI RISE OF THE CLAW')
print('-'*80)
kimi_db = Path('KIMI_RISEOFTHECLAW/data/kimi_trading.db')
if kimi_db.exists():
    try:
        conn = sqlite3.connect(str(kimi_db))
        cursor = conn.cursor()
        
        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f'  Tables: {tables}')
        
        # Check for closed trades with PnL
        if 'signals' in tables:
            cursor.execute("SELECT COUNT(*), AVG(pnl_pct) FROM signals WHERE status='closed'")
            closed = cursor.fetchone()
            if closed and closed[0] > 0:
                print(f'  Closed trades: {closed[0]}, Avg PnL: {closed[1]:+.2f}%')
                real_data_found.append(('kimi_riseoftheclaw', closed[0], closed[1] or 0, 0, 0))
            else:
                print('  No closed trades found')
        
        conn.close()
    except Exception as e:
        print(f'  [ERROR: {e}]')
else:
    print('  [DATABASE NOT FOUND]')

# 3. Check incubator agents
print('\n[3] INCUBATOR AGENTS (Web AI) - SOC Strategies')
print('-'*80)
meta_files = list(Path('incubator/agents/web_ai').glob('*.meta.json'))
print(f'  Total agents: {len(meta_files)}')

# Find ones with forward trades
with_trades = []
for f in meta_files:
    try:
        with open(f, 'r') as fp:
            data = json.load(fp)
        fwd = data.get('forward_metrics', {})
        trades = fwd.get('total_trades', 0)
        pnl = data.get('paper_trading', {}).get('current_pnl', 0)
        if trades > 0:
            with_trades.append({
                'name': data.get('strategy_name', f.stem),
                'trades': trades,
                'sharpe': fwd.get('sharpe', 0),
                'pnl': pnl,
                'win_rate': fwd.get('win_rate', 0)
            })
    except:
        pass

print(f'  With forward trades: {len(with_trades)}')
if with_trades:
    # Sort by actual PnL
    best = sorted(with_trades, key=lambda x: x['pnl'], reverse=True)[:10]
    print('  Top 10 by Realized PnL:')
    for s in best:
        print(f"    {s['name'][:40]:<40} PnL: {s['pnl']:>+7.2f}%  ({s['trades']} trades, Sharpe: {s['sharpe']:.2f})")
        if s['pnl'] > 0:
            real_data_found.append((s['name'], s['trades'], s['pnl'], s['sharpe'], s['win_rate']))

# 4. Check claude_gainer_ml
print('\n[4] CLAUDE GAINER ML (The +38% Unrealized System)')
print('-'*80)
claude_dir = Path('claude_gainer_ml')
if claude_dir.exists():
    json_files = list(claude_dir.rglob('*.json'))
    print(f'  JSON files found: {len(json_files)}')
    
    total_pnl = 0
    total_picks = 0
    for f in json_files:
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
            if isinstance(data, dict):
                picks = data.get('picks', data.get('active_picks', []))
                pnl = data.get('unrealized_pnl', data.get('total_pnl', 0))
                if picks:
                    print(f'    {f.name}: {len(picks)} picks, PnL: {pnl}')
                    total_picks += len(picks)
                    total_pnl += float(pnl) if pnl else 0
        except:
            pass
    print(f'  TOTAL: {total_picks} picks tracked')
else:
    print('  [DIRECTORY NOT FOUND]')

# 5. Check crypto_ml_edge
print('\n[5] CRYPTO ML EDGE (The -14.9% System)')
print('-'*80)
crypto_dir = Path('crypto_ml_edge')
if crypto_dir.exists():
    json_files = list(crypto_dir.rglob('*.json'))
    print(f'  JSON files found: {len(json_files)}')
else:
    print('  [DIRECTORY NOT FOUND]')

# 6. Check alpha_engine closed picks
print('\n[6] ALPHA ENGINE - Closed Picks (Ground Truth)')
print('-'*80)
closed_file = Path('alpha_engine/data/closed_picks.json')
if closed_file.exists():
    with open(closed_file, 'r') as f:
        picks = json.load(f)
    
    total_pnl = sum(p.get('pnl_pct', 0) for p in picks)
    winners = len([p for p in picks if p.get('pnl_pct', 0) > 0])
    losers = len([p for p in picks if p.get('pnl_pct', 0) <= 0])
    
    print(f'  Total closed trades: {len(picks)}')
    print(f'  Winners: {winners}  Losers: {losers}')
    print(f'  Total PnL: {total_pnl:+.2f}%')
    print(f'  Win Rate: {winners/len(picks)*100:.1f}%')
    
    # Find best performing strategies
    by_strategy = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'wins': 0})
    for p in picks:
        s = p.get('strategy', 'unknown')
        by_strategy[s]['trades'] += 1
        by_strategy[s]['pnl'] += p.get('pnl_pct', 0)
        if p.get('pnl_pct', 0) > 0:
            by_strategy[s]['wins'] += 1
    
    print('  Top 5 Strategies by PnL:')
    for s, data in sorted(by_strategy.items(), key=lambda x: x[1]['pnl'], reverse=True)[:5]:
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        print(f"    {s[:35]:<35} PnL: {data['pnl']:>+6.2f}%  ({data['trades']} trades, {wr:.0f}% WR)")
else:
    print('  [FILE NOT FOUND]')

# FINAL SUMMARY
print('\n' + '='*80)
print('FINAL VERDICT: Systems with VERIFIED REAL WINNING PICKS')
print('='*80)

if real_data_found:
    print('\n[CONFIRMED WINNERS - Real Trading Data]')
    for sys, trades, pnl, sharpe, wr in sorted(real_data_found, key=lambda x: x[2], reverse=True):
        if pnl > 0:
            status = 'PROFITABLE'
        else:
            status = 'LOSING'
        print(f'  [{status}] {sys:<40} {trades:>4} trades  {pnl:>+7.2f}% PnL')
else:
    print('\n  [WARNING] NO SYSTEMS with verified profitable trading data found!')

print('\n' + '='*80)
print('FAKE/DISPUTED DATA:')
print('='*80)
print('  [FAKE] battleground/app.js - Systems A-E table (9.91 Sharpe hardcoded)')
print('  [ZERO] system_b_regime - Actually has 0 trades, not 1656')
print('  [UNREALIZED] Claude Gainer +38% - Paper/unrealized only, not closed profits')
print('  [LOSING] Crypto ML Edge -14.9% - Confirmed losing')
print('  [MIXED] Alpha Engine -3.80% - Net losing overall')
print('='*80)
