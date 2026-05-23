#!/usr/bin/env python3
"""Debug script for strategy signal generation."""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load strategy
import importlib.util
spec = importlib.util.spec_from_file_location('strat', '../agents/cursor_ai/crypto_rsi_whaleconfirmed_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

strategy = module.WhaleConfirmedRSIStrategy()

# Generate data with extreme moves
np.random.seed(42)
n = 200
returns = np.random.normal(0.0001, 0.02, n)
# Add some extreme moves for RSI signals
for i in [50, 51, 52, 100, 101, 150, 151]:
    returns[i] = np.random.choice([-0.08, 0.08])

prices = 50000 * np.exp(np.cumsum(returns))

data = pd.DataFrame({
    'open': prices * (1 + np.random.normal(0, 0.001, n)),
    'high': prices * (1 + abs(np.random.normal(0, 0.015, n))),
    'low': prices * (1 - abs(np.random.normal(0, 0.015, n))),
    'close': prices,
    'volume': np.random.uniform(100, 1000, n)
})

# Count signals
all_signals = []
for end_idx in range(50, len(data)):
    window = data.iloc[:end_idx + 1]
    sigs = strategy.generate_signals(window, symbol='BTCUSDT')
    all_signals.extend(sigs)

print(f'Total signals: {len(all_signals)}')

if all_signals:
    for s in all_signals[:5]:
        print(f'  {s.direction} @ {s.entry_price:,.0f} - {s.reason[:60]}...')
else:
    # Check why no signals
    window = data.iloc[:100]
    rsi = strategy._calculate_rsi(window['close'])
    print(f'RSI range: {rsi.min():.1f} - {rsi.max():.1f}')
    print(f'RSI last: {rsi.iloc[-1]:.1f}')
    
    # Check whale data
    whale = strategy._analyze_whale_activity('BTCUSDT')
    print(f'Whale accumulation: {whale["accumulation"]}')
    print(f'Whale confidence: {whale["confidence"]:.2f}')
    
    # Multiple whale checks
    print('\nMultiple whale data calls:')
    for i in range(5):
        w = strategy._analyze_whale_activity('BTCUSDT')
        print(f'  Call {i+1}: acc={w["accumulation"]}, conf={w["confidence"]:.2f}')
