# Exit Management System - Documentation

A comprehensive exit management system for multi-asset algorithmic trading with ATR-based exits, partial profit-taking, time-based exits, and volatility regime adjustments.

---

## Table of Contents

1. Quick Start
2. Core Components
3. Configuration Guide
4. Usage Examples
5. Parameter Optimization
6. Backtesting
7. Best Practices

---

## 1. Quick Start

### Basic Usage

```python
from exit_manager import ExitManager, AssetClass
import pandas as pd
from datetime import datetime

# Initialize exit manager
exit_mgr = ExitManager(atr_period=14, use_volatility_regime=True)

# Prepare price data (OHLCV DataFrame)
prices_df = pd.DataFrame({
    "timestamp": [...],
    "open": [...],
    "high": [...],
    "low": [...],
    "close": [...],
    "volume": [...]
})

# Initialize position
position = exit_mgr.initialize_position(
    symbol="CL=F",
    asset_class=AssetClass.COMMODITY_FUTURES,
    entry_price=78.50,
    entry_time=datetime.now(),
    quantity=10,
    direction=1,  # Long
    prices_df=prices_df,
    vix_value=None
)

# Process each new bar
bar = {
    "timestamp": datetime.now(),
    "open": 79.0,
    "high": 80.5,
    "low": 78.8,
    "close": 80.0,
    "volume": 100000
}

signals = exit_mgr.process_bar("CL=F", bar, prices_df)

for signal in signals:
    print(f"Exit: {signal.exit_type.value} at {signal.price}")
```

---

## 2. Core Components

### ExitManager
Main class that manages all exit logic for positions.

**Key Methods:**
- `initialize_position()`: Create new position with calculated exit levels
- `process_bar()`: Process new price bar and check all exit conditions
- `check_initial_stop()`: Check if stop loss hit
- `check_take_profit()`: Check if take profit hit
- `update_trailing_stop()`: Update trailing stop and check if hit
- `check_partial_profit()`: Check partial profit levels
- `check_time_exit()`: Check if max hold period exceeded
- `check_breakeven()`: Move stop to breakeven when appropriate

### VolatilityRegimeDetector
Detects market volatility regimes and adjusts parameters.

**Regimes:**
- **COMPRESSION**: ATR < 70% of baseline (tighter stops)
- **NORMAL**: ATR 70-115% of baseline (standard stops)
- **EXPANSION**: ATR 115-140% of baseline (wider stops)
- **HIGH_VOLATILITY**: ATR > 140% of baseline (much wider stops)
- **EXHAUSTION**: Declining ATR after high volatility

### ExitBacktester
Backtesting framework for exit strategy optimization.

**Key Methods:**
- `run_backtest()`: Run backtest on historical trades
- `optimize_parameters()`: Grid search parameter optimization

---

## 3. Configuration Guide

### Default Parameters by Asset Class

#### EQUITY_ETF
```python
sl_atr_mult: 1.0           # Initial stop = Entry - 1x ATR
tp_atr_mult: 1.5           # Take profit = Entry + 1.5x ATR
trail_atr_mult: 0.5        # Trailing stop distance = 0.5x ATR
partial_tp_levels: [(1.0, 0.5)]  # Close 50% at 1x ATR profit
breakeven_atr_mult: 0.8    # Move to BE at 0.8x ATR profit
max_hold_days: 20          # Max hold period
ratchet_lock_pct: 0.50     # Lock 50% of gains
```

#### STOCK
```python
sl_atr_mult: 1.0
tp_atr_mult: 1.5
trail_atr_mult: 0.5
partial_tp_levels: [(1.0, 0.5)]
breakeven_atr_mult: 0.8
max_hold_days: 15
ratchet_lock_pct: 0.50
```

#### COMMODITY_FUTURES
```python
sl_atr_mult: 1.0
tp_atr_mult: 2.0           # Higher targets for commodities
trail_atr_mult: 0.5        # Half-ATR trailing stop
partial_tp_levels: [(1.0, 0.5), (2.0, 0.25)]  # Two partial levels
breakeven_atr_mult: 0.8
max_hold_days: 10
ratchet_lock_pct: 0.50
```

#### CRYPTO
```python
sl_atr_mult: 1.5           # Wider stops for crypto volatility
tp_atr_mult: 2.5
trail_atr_mult: 0.75
partial_tp_levels: [(1.0, 0.3), (2.0, 0.3)]
breakeven_atr_mult: 1.0
max_hold_days: 7
ratchet_lock_pct: 0.50
```

### Custom Parameters
```python
# Override defaults for specific asset class
custom_params = {
    AssetClass.COMMODITY_FUTURES: {
        "sl_atr_mult": 1.2,
        "tp_atr_mult": 2.5,
        "trail_atr_mult": 0.6,
        "partial_tp_levels": [(1.0, 0.5), (2.0, 0.25)],
        "max_hold_days": 12
    }
}

exit_mgr = ExitManager(atr_period=14, custom_params=custom_params)
```

---

## 4. Usage Examples

### Example 1: Basic Trade Management
```python
from exit_manager import ExitManager, AssetClass, ExitType
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Create mock price data
dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
prices = pd.DataFrame({
    "timestamp": dates,
    "open": np.random.randn(30).cumsum() + 100,
    "high": np.random.randn(30).cumsum() + 102,
    "low": np.random.randn(30).cumsum() + 98,
    "close": np.random.randn(30).cumsum() + 100,
    "volume": np.random.randint(1000000, 5000000, 30)
})

# Initialize exit manager
exit_mgr = ExitManager(atr_period=14, use_volatility_regime=True)

# Initialize position
position = exit_mgr.initialize_position(
    symbol="AAPL",
    asset_class=AssetClass.STOCK,
    entry_price=150.0,
    entry_time=datetime(2024, 1, 1),
    quantity=100,
    direction=1,
    prices_df=prices.iloc[:14]
)

# Simulate trade
for i in range(14, len(prices)):
    bar = {
        "timestamp": prices.iloc[i]["timestamp"],
        "open": prices.iloc[i]["open"],
        "high": prices.iloc[i]["high"],
        "low": prices.iloc[i]["low"],
        "close": prices.iloc[i]["close"],
        "volume": prices.iloc[i]["volume"]
    }
    
    signals = exit_mgr.process_bar("AAPL", bar, prices.iloc[:i+1])
    
    if signals:
        for signal in signals:
            print(f"{signal.timestamp}: {signal.exit_type.value} at ${signal.price:.2f}")
            print(f"  Reason: {signal.reason}")
            print(f"  P&L: ${signal.pnl:.2f}")
        
        # Check if position closed
        if any(s.exit_type in [ExitType.INITIAL_STOP, ExitType.TAKE_PROFIT,
                               ExitType.TRAILING_STOP, ExitType.TIME_EXIT] 
               for s in signals):
            break
```

### Example 2: Multi-Asset Portfolio
```python
# Configure different parameters for each asset class
portfolio_params = {
    AssetClass.EQUITY_ETF: {
        "sl_atr_mult": 1.0,
        "tp_atr_mult": 1.5,
        "trail_atr_mult": 0.5,
        "max_hold_days": 20
    },
    AssetClass.COMMODITY_FUTURES: {
        "sl_atr_mult": 1.0,
        "tp_atr_mult": 2.0,
        "trail_atr_mult": 0.5,
        "partial_tp_levels": [(1.0, 0.5), (2.0, 0.25)],
        "max_hold_days": 10
    },
    AssetClass.CRYPTO: {
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
        "trail_atr_mult": 1.0,
        "max_hold_days": 7
    }
}

exit_mgr = ExitManager(atr_period=14, custom_params=portfolio_params)

# Manage positions for different assets
positions = {
    "SPY": AssetClass.EQUITY_ETF,
    "CL=F": AssetClass.COMMODITY_FUTURES,
    "BTC": AssetClass.CRYPTO
}
```

### Example 3: Volatility Regime Adjustment with VIX
```python
# For equity trades, pass VIX value for regime detection
vix_value = 25.0  # Current VIX level

position = exit_mgr.initialize_position(
    symbol="SPY",
    asset_class=AssetClass.EQUITY_ETF,
    entry_price=450.0,
    entry_time=datetime.now(),
    quantity=50,
    direction=1,
    prices_df=prices_df,
    vix_value=vix_value  # Enables VIX-based regime adjustment
)

# In high VIX (>30), stops will be automatically widened
```

---

## 5. Parameter Optimization

### Grid Search Example
```python
from exit_manager import ExitBacktester, ExitManager, AssetClass

# Define parameter grid
param_grid = {
    "sl_atr_mult": [0.8, 1.0, 1.2, 1.5],
    "tp_atr_mult": [1.5, 2.0, 2.5, 3.0],
    "trail_atr_mult": [0.4, 0.5, 0.6]
}

# Create exit manager
exit_mgr = ExitManager(atr_period=14)
backtester = ExitBacktester(exit_mgr)

# Run optimization
results = backtester.optimize_parameters(
    trades=historical_trades,
    price_data=price_data_dict,
    param_grid=param_grid
)

# View top results
print(results.head(10))
```

### Walk-Forward Optimization
```python
# Split data into in-sample and out-of-sample
is_data = prices.iloc[:int(len(prices) * 0.7)]
oos_data = prices.iloc[int(len(prices) * 0.7):]

# Optimize on in-sample
is_results = backtester.optimize_parameters(trades, {"CL=F": is_data}, param_grid)
best_params = is_results.iloc[0].to_dict()

# Validate on out-of-sample
oos_results = backtester.run_backtest(trades, {"CL=F": oos_data})

# Check IS vs OOS performance ratio
is_pnl = is_results.iloc[0]["total_pnl"]
oos_pnl = oos_results["total_pnl"].sum()
ratio = is_pnl / oos_pnl if oos_pnl > 0 else float("inf")

print(f"IS/OOS Ratio: {ratio:.2f} (should be < 1.5)")
```

---

## 6. Backtesting

### Backtest Structure
```python
trades = [
    {
        "symbol": "CL=F",
        "asset_class": AssetClass.COMMODITY_FUTURES,
        "entry_time": datetime(2024, 1, 1),
        "entry_price": 75.0,
        "quantity": 10,
        "direction": 1,
        "vix_value": None
    },
    # ... more trades
]

price_data = {
    "CL=F": prices_df_clf,
    "GC=F": prices_df_gcf,
    # ... more symbols
}

exit_mgr = ExitManager(atr_period=14)
backtester = ExitBacktester(exit_mgr)
results = backtester.run_backtest(trades, price_data)

# Analyze results
print(f"Total P&L: ${results['total_pnl'].sum():.2f}")
print(f"Win Rate: {(results['total_pnl'] > 0).mean():.1%}")
print(f"Avg P&L: ${results['total_pnl'].mean():.2f}")
print(f"Exit Distribution:")
print(results["exit_type"].value_counts())
```

---

## 7. Best Practices

1. **Start with Default Parameters**
   - Default parameters are based on industry research
   - Test defaults before optimization
   - Understand why defaults work

2. **Optimize by Asset Class**
   - Different assets have different volatility characteristics
   - CL=F needs different parameters than SPY
   - Crypto needs much wider stops than equities

3. **Use Walk-Forward Analysis**
   - Always validate on out-of-sample data
   - Check IS/OOS performance ratio
   - Avoid overfitting

4. **Monitor in Production**
   - Track actual vs expected performance
   - Adjust for slippage and commissions
   - Be prepared to reduce size during drawdowns

5. **Consider Market Regimes**
   - Use volatility regime detection
   - Adjust position sizes in high volatility
   - Widen stops when VIX spikes

6. **Test Partial Profit-Taking**
   - Partial exits reduce drawdowns
   - But may reduce total returns
   - Find balance for your risk tolerance

7. **Document Everything**
   - Record all parameter changes
   - Track rationale for adjustments
   - Maintain trading journal

---

## Research References

- Kaminski and Lo (2008): Stop-loss strategy research
- Snorrason and Yusupov (2009): Trailing stop performance
- ATR methodology: Wilder, J. Welles (1978)

---

## Parameter Ranges by Asset Class

### EQUITY ETFs
- sl_atr_mult: 0.8 - 1.5 (tighter for liquid ETFs)
- tp_atr_mult: 1.5 - 2.5 (1.5x for balanced, 2.5x for trend following)
- trail_atr_mult: 0.4 - 0.7 (0.5 is standard)
- partial_tp_levels: [(1.0, 0.5)] or [(0.8, 0.3), (1.5, 0.3)]
- max_hold_days: 15 - 30

### STOCKS
- sl_atr_mult: 1.0 - 2.0 (wider for individual stocks)
- tp_atr_mult: 1.5 - 3.0
- trail_atr_mult: 0.5 - 1.0
- partial_tp_levels: [(1.0, 0.5)]
- max_hold_days: 10 - 20

### COMMODITY FUTURES (CL=F, GC=F)
- sl_atr_mult: 0.8 - 1.5
- tp_atr_mult: 1.5 - 3.0 (2.0x recommended for commodities)
- trail_atr_mult: 0.4 - 0.6 (0.5x = half-ATR works well)
- partial_tp_levels: [(1.0, 0.5), (2.0, 0.25)]
- max_hold_days: 5 - 15

### CRYPTO
- sl_atr_mult: 1.5 - 3.0 (wider due to high volatility)
- tp_atr_mult: 2.0 - 4.0
- trail_atr_mult: 0.7 - 1.5
- partial_tp_levels: [(1.0, 0.3), (2.0, 0.3), (3.0, 0.2)]
- max_hold_days: 3 - 10

---

## Volatility Regime Adjustments

### COMPRESSION (ATR < 70% baseline)
- Reduce sl_atr_mult by 15% (tighter stops)
- Reduce tp_atr_mult by 10% (more conservative targets)
- Reduce position size by 20-30%

### NORMAL (ATR 70-115% baseline)
- Use standard parameters
- Full position size

### EXPANSION (ATR 115-140% baseline)
- Increase sl_atr_mult by 15% (wider stops)
- Increase tp_atr_mult by 20% (larger targets)
- Consider reducing position size by 15%

### HIGH VOLATILITY (ATR > 140% baseline)
- Increase sl_atr_mult by 30% (much wider stops)
- Increase tp_atr_mult by 40% (capture larger moves)
- Reduce position size by 30-50%
- Consider wider trailing stops

### VIX-Based Adjustments (for equities)
- VIX < 15: Normal parameters
- VIX 15-20: Increase SL by 10%
- VIX 20-30: Increase SL by 20%, reduce size by 20%
- VIX > 30: Increase SL by 30%, reduce size by 40%
