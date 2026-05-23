import sys
sys.path.insert(0, '.')

from alpha_engine.backtest_justin_bravo import JustinBravoBacktester, main

# Override symbols with available pairs
symbols = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOT/USDT',
    'DOGE/USDT', 'SHIB/USDT', 'ALGO/USDT', 'TRX/USDT',
    'APE/USDT', 'ARB/USDT', 'DYDX/USDT', 'FET/USDT', 'INJ/USDT'
]

print("="*80)
print("JUSTIN & J BRAVO STRATEGY BACKTEST")
print("="*80)
print(f"Testing {len(symbols)} crypto pairs")

# Initialize backtester
bt = JustinBravoBacktester(data_source='crypto_data.db')

# Run backtest
from alpha_engine.justin_bravo_strategies import JUSTIN_BRAVO_STRATEGIES
results = bt.run_full_backtest(symbols)

# Generate and print report
report = bt.generate_report()
print(report)

# Save to file
import os
from datetime import datetime
report_file = f'backtest_results/justin_bravo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
os.makedirs('backtest_results', exist_ok=True)
with open(report_file, 'w') as f:
    f.write(report)
print(f"\n✓ Report saved to {report_file}")

# Save to audit database
bt.save_to_audit_db()

# Return top 5 strategies for further analysis
top5 = bt.get_best_performers(min_trades=5)[:10]
print("\n🎯 TOP 10 STRATEGY-PAIR COMBINATIONS:")
for r in top5:
    print(f"   {r.strategy} on {r.symbol}: {r.win_rate:.1f}% WR, {r.profit_factor:.2f} PF, {r.total_pnl:.2f}% PnL")

# Save winners to JSON
winners = []
for r in top5:
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

import json
with open(f'backtest_results/justin_bravo_winners_{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
    json.dump(winners, f, indent=2)

print("\n✓ Winners saved to JSON")
