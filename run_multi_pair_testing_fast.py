#!/usr/bin/env python3
"""
Fast Multi-Pair Testing Runner
"""

import numpy as np
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "baby_strategies"))

def generate_data(symbol, n=350, seed=42):
    np.random.seed(seed)
    params = {'BTC': {'drift': 0.0005, 'vol': 0.035, 'price': 45000},
              'ETH': {'drift': 0.0006, 'vol': 0.045, 'price': 3000},
              'SOL': {'drift': 0.0008, 'vol': 0.055, 'price': 100}}[symbol]
    returns = [np.random.normal(params['drift'], params['vol']) for _ in range(n)]
    prices = params['price'] * np.exp(np.cumsum(returns))
    dr = np.abs(np.array(returns)) + np.random.exponential(params['vol'] * 0.4, n)
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, params['vol'] * 0.2, n)),
        'high': prices * (1 + dr * np.random.uniform(0.4, 0.8, n)),
        'low': prices * (1 - dr * np.random.uniform(0.4, 0.8, n)),
        'close': prices,
        'volume': np.random.lognormal(20, 0.8, n)
    })
    df['high'] = df[['high', 'open', 'close']].max(axis=1) * 1.001
    df['low'] = df[['low', 'open', 'close']].min(axis=1) * 0.999
    return df

def run_bt(strategy, data, symbol, direction_filter=None):
    equity, trades, position, entry_bar = 10000, [], None, 0
    for i in range(80, len(data)):
        if position:
            bars_held, price = i - entry_bar, data['close'].iloc[i]
            if position['direction'] == 'BUY':
                pnl = (price - position['entry']) / position['entry']
                exit_now = price >= position['tp'] or price <= position['sl'] or bars_held >= 10
            else:
                pnl = (position['entry'] - price) / position['entry']
                exit_now = price <= position['tp'] or price >= position['sl'] or bars_held >= 10
            if exit_now:
                trades.append({'pnl': pnl - 0.003, 'dir': position['direction']})
                equity *= (1 + (pnl - 0.003) * 0.1)
                position = None
        if not position and i < len(data) - 1:
            try:
                sigs = strategy.generate_signals(data.iloc[:i+1].copy(), symbol)
                if sigs and (direction_filter is None or sigs[0].direction == direction_filter):
                    position = {'direction': sigs[0].direction, 'entry': sigs[0].entry_price,
                               'tp': sigs[0].take_profit, 'sl': sigs[0].stop_loss}
                    entry_bar = i
            except:
                return {'sharpe': -999, 'wr': 0, 'dd': 1, 'n': 0}
    if not trades:
        return {'sharpe': -999, 'wr': 0, 'dd': 1, 'n': 0}
    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    peak, max_dd, running = 10000, 0, 10000
    for t in trades:
        running *= (1 + t['pnl'] * 0.1)
        if running > peak: peak = running
        max_dd = max(max_dd, (peak - running) / peak)
    avg, std = np.mean(pnls), np.std(pnls) or 0.001
    return {'sharpe': (avg/std)*np.sqrt(252), 'wr': len(wins)/len(pnls), 'dd': max_dd, 'n': len(trades)}

def passes(r):
    return r['sharpe'] >= 1.0 and r['wr'] >= 0.45 and r['dd'] <= 0.25 and r['n'] >= 10

def test_strategy(name, cls, symbols):
    results = {'name': name, 'pairs': [], 'best_sharpe': -999, 'best_pair': None, 'best_dir': None}
    for symbol in symbols:
        data = generate_data(symbol, n=350, seed=hash(symbol + name) % 10000)
        try:
            s = cls()
        except:
            continue
        best = None
        for dir_name, filt in [('LONG', 'BUY'), ('SHORT', 'SELL'), ('BOTH', None)]:
            r = run_bt(s, data, symbol, filt)
            if passes(r) and (best is None or r['sharpe'] > best['sharpe']):
                best = {**r, 'direction': dir_name}
        if best:
            results['pairs'].append({'symbol': symbol, **best})
            if best['sharpe'] > results['best_sharpe']:
                results['best_sharpe'] = best['sharpe']
                results['best_pair'] = symbol
                results['best_dir'] = best['direction']
    results['verified'] = len(results['pairs']) > 0
    return results

# Import strategies
from market_structure_volume import MarketStructureVolumeStrategy
from kalman_mean_reversion import KalmanMeanReversionStrategy
from liquidity_sweep_reversal import LiquiditySweepReversalStrategy
from adaptive_momentum import AdaptiveMomentumStrategy
from volume_profile_deviation import VolumeProfileDeviationStrategy
from range_expansion_breakout import RangeExpansionBreakoutStrategy
from order_block_retest import OrderBlockRetestStrategy
from multi_timeframe_confluence import MultiTimeframeConfluenceStrategy
from relative_strength_rotation import RelativeStrengthRotationStrategy
from volatility_regime_switch import VolatilityRegimeSwitchStrategy

strategies = [
    ('MarketStructureVolume', MarketStructureVolumeStrategy),
    ('KalmanMeanReversion', KalmanMeanReversionStrategy),
    ('LiquiditySweepReversal', LiquiditySweepReversalStrategy),
    ('AdaptiveMomentum', AdaptiveMomentumStrategy),
    ('VolumeProfileDeviation', VolumeProfileDeviationStrategy),
    ('RangeExpansionBreakout', RangeExpansionBreakoutStrategy),
    ('OrderBlockRetest', OrderBlockRetestStrategy),
    ('MultiTimeframeConfluence', MultiTimeframeConfluenceStrategy),
    ('RelativeStrengthRotation', RelativeStrengthRotationStrategy),
    ('VolatilityRegimeSwitch', VolatilityRegimeSwitchStrategy),
]

print("=" * 80)
print("FAST MULTI-PAIR TESTING")
print("=" * 80)
print()

symbols = ['BTC', 'ETH', 'SOL']
all_results = {}

for name, cls in strategies:
    print(f"Testing {name}...", end=' ')
    result = test_strategy(name, cls, symbols)
    all_results[name] = result
    if result['verified']:
        print(f"[PASS] Best: {result['best_pair']} {result['best_dir']} S={result['best_sharpe']:.2f}")
    else:
        print("[FAIL]")

# Update JSON
json_path = Path("battleground/data/baby_strats_dashboard.json")
if json_path.exists():
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    verified_count = 0
    for strat in data.get('strategies', []):
        strat_name = strat.get('name', '').lower()
        for result_name, result in all_results.items():
            if result_name.lower() in strat_name or strat_name in result_name.lower():
                strat['multi_pair_verified'] = result['verified']
                strat['multi_pair_metrics'] = {
                    'tested_pairs': [p['symbol'] for p in result['pairs']],
                    'best_pair': result['best_pair'],
                    'best_sharpe': result['best_sharpe'],
                    'best_direction': result['best_dir'],
                    'verified_at': datetime.now().isoformat() if result['verified'] else None
                }
                if result['verified']:
                    verified_count += 1
                break
    
    data['multi_pair_summary'] = {
        'verified_count': verified_count,
        'pending_count': len(data.get('strategies', [])) - verified_count,
        'total_count': len(data.get('strategies', [])),
        'last_tested': datetime.now().isoformat()
    }
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n[OK] Updated JSON with {verified_count} verified strategies")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
verified = [r for r in all_results.values() if r['verified']]
failed = [r for r in all_results.values() if not r['verified']]
print(f"\nVerified ({len(verified)}):")
for r in verified:
    print(f"  + {r['name']:30s} {r['best_pair']:4s} {r['best_dir']:5s} Sharpe={r['best_sharpe']:.2f}")
print(f"\nFailed ({len(failed)}):")
for r in failed:
    print(f"  - {r['name']}")
