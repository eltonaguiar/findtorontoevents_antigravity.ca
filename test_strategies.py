#!/usr/bin/env python3
"""
Quick test of baby strategies
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Test one strategy
from baby_strategies.rsi_volume_mean_reversion import RSIVolumeMeanReversionStrategy

# Create synthetic data
np.random.seed(42)
n = 500
returns = np.random.normal(0.0001, 0.02, n)
prices = 50000 * np.exp(np.cumsum(returns))

test_data = pd.DataFrame({
    'open': prices * (1 + np.random.normal(0, 0.001, n)),
    'high': prices * (1 + abs(np.random.normal(0, 0.01, n))),
    'low': prices * (1 - abs(np.random.normal(0, 0.01, n))),
    'close': prices,
    'volume': np.random.uniform(100, 1000, n)
})

# Test strategy
strategy = RSIVolumeMeanReversionStrategy()
signals = strategy.generate_signals(test_data, symbol="BTCUSDT")

print(f"Generated {len(signals)} signals from {len(test_data)} bars")
for sig in signals[:3]:
    print(f"  {sig.direction} {sig.symbol} at {sig.entry_price:.2f}, TP: {sig.take_profit:.2f}, SL: {sig.stop_loss:.2f}")
    print(f"    Reason: {sig.reason}")

print("✅ Strategy test passed!")