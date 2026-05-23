import sys
sys.path.insert(0, '.')

from alpha_engine.justin_bravo_strategies_v2 import JUSTIN_BRAVO_STRATEGIES_V2
from alpha_engine.backtest_justin_bravo import JustinBravoBacktester

# Available pairs
symbols = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOT/USDT',
    'DOGE/USDT', 'SHIB/USDT', 'ALGO/USDT', 'TRX/USDT',
    'APE/USDT', 'ARB/USDT', 'DYDX/USDT', 'FET/USDT', 'INJ/USDT'
]

print("Re-running backtest to save to audit DB...")

# Initialize backtester with V2 strategies
bt = JustinBravoBacktester(data_source='crypto_data.db')

# Run backtest
results = bt.run_full_backtest(symbols, strategies=JUSTIN_BRAVO_STRATEGIES_V2)

# Save to audit database
bt.save_to_audit_db()

print("\nDone! Results saved to data/audit_trail.db")
