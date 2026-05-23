# Backtest Framework for Trading Strategies

A production-ready Python backtest engine for evaluating trading strategies on historical data.

## Features

- **Multiple Data Sources**: Yahoo Finance, Kraken crypto exchange, CSV files
- **Comprehensive Metrics**: Total Return, Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate, Profit Factor, Calmar Ratio
- **Multiple Assets**: Support for stocks, crypto, forex
- **Position Sizing**: Fixed, percent risk, and Kelly criterion sizing
- **Batch Testing**: Run 100+ strategies with parameter optimization
- **Trade Logging**: Complete trade history with PnL analysis
- **Equity Curve Tracking**: Visualize portfolio performance over time

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from backtest_framework import (
    BacktestEngine, BacktestConfig,
    MovingAverageCrossover, DataLoader
)

# Load data
data = DataLoader.from_yahoo(
    symbol="AAPL",
    start_date="2020-01-01",
    end_date="2025-01-01"
)

# Configure backtest
config = BacktestConfig(
    initial_capital=100000.0,
    commission_rate=0.001,
    slippage=0.0005
)

# Create strategy
strategy = MovingAverageCrossover(fast_period=20, slow_period=50)

# Run backtest
engine = BacktestEngine(config)
engine.set_data(data)
engine.set_strategy(strategy)
result = engine.run()

# View results
print(result)
```

## Data Loading

### Yahoo Finance
```python
data = DataLoader.from_yahoo(
    symbol="BTC-USD",
    start_date="2020-01-01",
    end_date="2025-01-01",
    interval="1d"  # 1d, 1h, 15m, etc.
)
```

### Kraken Crypto Exchange
```python
data = DataLoader.from_kraken(
    symbol="BTCUSD",
    start_date="2020-01-01",
    end_date="2025-01-01",
    interval=1440  # minutes
)
```

### CSV File
```python
data = DataLoader.from_csv(
    path="data.csv",
    date_col="date",
    symbol="AAPL"
)
```

## Creating Custom Strategies

```python
from backtest_framework import Strategy, Signal

class MyStrategy(Strategy):
    def __init__(self, param1=20):
        super().__init__("My Strategy")
        self.param1 = param1
    
    def _calculate_indicators(self):
        # Calculate indicators
        self.indicators['sma'] = self.data['close'].rolling(self.param1).mean()
    
    def on_bar(self, idx, bar):
        # Generate signals
        if idx < self.param1:
            return None
        
        sma = self.get_indicator('sma', idx)
        
        if bar['close'] > sma:
            return Signal.BUY
        elif bar['close'] < sma:
            return Signal.SELL
        
        return Signal.HOLD
```

## Batch Testing & Optimization

```python
from backtest_framework import BatchBacktester

# Create batch tester
batch = BatchBacktester(data, config)

# Parameter grid
param_grid = {
    'fast_period': [10, 20, 30],
    'slow_period': [50, 100, 200]
}

# Run optimization
results = batch.run_param_grid(
    MovingAverageCrossover,
    param_grid,
    base_name="MA_Optimization"
)

# Get best strategy
best_strategy, best_result = batch.get_best_strategy('sharpe_ratio')

# Save results
batch.save_results("./backtest_results")
```

## Performance Metrics

| Metric | Description |
|--------|-------------|
| Total Return | Overall strategy return |
| Annualized Return | Return normalized to yearly |
| Sharpe Ratio | Risk-adjusted return (higher is better) |
| Sortino Ratio | Downside risk-adjusted return |
| Max Drawdown | Largest peak-to-trough decline |
| Calmar Ratio | Annualized return / Max drawdown |
| Win Rate | Percentage of winning trades |
| Profit Factor | Gross profit / Gross loss |
| Number of Trades | Total trades executed |

## Configuration Options

```python
config = BacktestConfig(
    initial_capital=100000.0,    # Starting capital
    commission_rate=0.001,        # 0.1% per trade
    slippage=0.0005,             # 0.05% slippage
    max_position_pct=1.0,        # Max 100% in one position
    allow_short=False,           # No short selling
    position_sizing="fixed",     # fixed, percent_risk, kelly
    risk_per_trade=0.02,         # 2% risk per trade
    stop_loss_pct=0.05,          # 5% stop loss
    take_profit_pct=0.10         # 10% take profit
)
```

## Included Strategies

1. **MovingAverageCrossover**: Classic dual MA crossover
2. **RSIStrategy**: Mean reversion using RSI
3. **BollingerBandsStrategy**: Mean reversion using Bollinger Bands

## Example Output

```
Backtest Results
================
Total Return:        457.20%
Annualized Return:   40.97%
Sharpe Ratio:        1.06
Sortino Ratio:       1.49
Max Drawdown:        -26.07%
Calmar Ratio:        1.57
Win Rate:            56.25%
Profit Factor:       8.08
Number of Trades:    16
Avg Trade Return:    14.69%
```

## Running the Example

```bash
python backtest_framework.py
```

This will run the example with synthetic data and demonstrate all features.

## License

MIT License
