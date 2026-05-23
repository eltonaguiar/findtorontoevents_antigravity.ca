import sys
sys.path.insert(0, '.')

from alpha_engine.justin_bravo_strategies_v2 import JUSTIN_BRAVO_STRATEGIES_V2
from alpha_engine.backtest_justin_bravo import JustinBravoBacktester
import os
from datetime import datetime
import json

# Available pairs
symbols = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOT/USDT',
    'DOGE/USDT', 'SHIB/USDT', 'ALGO/USDT', 'TRX/USDT',
    'APE/USDT', 'ARB/USDT', 'DYDX/USDT', 'FET/USDT', 'INJ/USDT'
]

print("="*80)
print("JUSTIN & J BRAVO STRATEGY BACKTEST - V2 (IMPROVED)")
print("="*80)
print(f"Testing {len(symbols)} crypto pairs")

# Initialize backtester with V2 strategies
bt = JustinBravoBacktester(data_source='crypto_data.db')

# Run backtest with V2 strategies
results = bt.run_full_backtest(symbols, strategies=JUSTIN_BRAVO_STRATEGIES_V2)

# Generate report
report = bt.generate_report()
print(report)

# Save report
os.makedirs('backtest_results', exist_ok=True)
report_file = f'backtest_results/justin_bravo_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report)
print(f"\n[OK] Report saved to {report_file}")

# Save to audit database
bt.save_to_audit_db()

# Get top performers
top10 = bt.get_best_performers(min_trades=3)[:10]
print("\n" + "="*80)
print("TOP 10 STRATEGY-PAIR COMBINATIONS (V2)")
print("="*80)
for i, r in enumerate(top10, 1):
    print(f"{i:2}. {r.strategy:30} | {r.symbol:12} | Trades: {r.total_trades:3} | "
          f"WR: {r.win_rate:5.1f}% | PF: {r.profit_factor:5.2f} | PnL: {r.total_pnl:8.2f}%")

# Analysis by symbol
print("\n" + "="*80)
print("ANALYSIS BY SYMBOL")
print("="*80)
symbol_analysis = bt.analyze_by_symbol()
for symbol, stats in sorted(symbol_analysis.items()):
    if stats['best_strategy']:
        print(f"{symbol:12} -> Best: {stats['best_strategy']:30} (WR: {stats['best_win_rate']:.1f}%)")

# Analysis by strategy
print("\n" + "="*80)
print("STRATEGY SUMMARY")
print("="*80)
strategy_analysis = bt.analyze_by_strategy()
for strategy, stats in sorted(strategy_analysis.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
    print(f"{strategy:30} | Trades: {stats['total_trades']:4} | "
          f"Profitable: {stats['profitable_symbols']:2}/{len(stats['symbols'])} | "
          f"Avg WR: {stats['avg_win_rate']:5.1f}% | Total PnL: {stats['total_pnl']:10.2f}%")

# Save winners
winners = []
for r in top10:
    winners.append({
        'strategy': r.strategy,
        'symbol': r.symbol,
        'win_rate': r.win_rate,
        'profit_factor': r.profit_factor,
        'total_pnl': r.total_pnl,
        'total_trades': r.total_trades,
        'sharpe': r.sharpe,
        'max_drawdown': r.max_drawdown
    })

with open(f'backtest_results/justin_bravo_v2_winners_{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
    json.dump(winners, f, indent=2)

print("\n[OK] Winners saved to JSON")
