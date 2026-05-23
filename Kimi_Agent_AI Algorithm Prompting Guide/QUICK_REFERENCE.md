# Strategy Validation System - Quick Reference

## Installation

```python
# Copy strategy_validation.py to your project
# No additional dependencies beyond standard scientific Python stack
import numpy as np
import pandas as pd
from scipy import stats
```

## Basic Usage

```python
from strategy_validation import StrategyValidator, Trade, KillSwitchConfig
from datetime import datetime

# 1. Create validator
validator = StrategyValidator(db_path="my_trading.db")

# 2. Register strategy
validator.register_strategy("strat_001", metadata={"type": "momentum"})

# 3. Record trades
trade = Trade(
    trade_id="t001",
    strategy_id="strat_001",
    timestamp=datetime.now(),
    pnl=150.0,           # Profit in currency
    pnl_pct=0.015,       # 1.5% return
    direction="long",
    entry_price=10000,
    exit_price=10150,
    holding_period=120   # minutes
)
metrics, kill_reason = validator.record_trade(trade)

# 4. Check if killed
if kill_reason:
    print(f"Strategy killed: {kill_reason.value}")
```

## Configuration Templates

### Conservative (Recommended for Production)
```python
config = KillSwitchConfig(
    wr_threshold=0.45,          # Kill if WR < 45%
    sharpe_threshold=1.0,       # Kill if Sharpe < 1.0
    max_drawdown_pct=-0.15,     # Kill if DD > 15%
    min_trades_for_kill=50,
    max_consecutive_losses=10
)
```

### Aggressive (For High-Frequency Strategies)
```python
config = KillSwitchConfig(
    wr_threshold=0.40,
    sharpe_threshold=0.8,
    max_drawdown_pct=-0.20,
    min_trades_for_kill=30,
    max_consecutive_losses=15
)
```

### Lenient (For Development/Testing)
```python
config = KillSwitchConfig(
    wr_threshold=0.35,
    sharpe_threshold=0.5,
    max_drawdown_pct=-0.25,
    min_trades_for_kill=20,
    max_consecutive_losses=20
)
```

## Common Operations

### Get Strategy Metrics
```python
metrics = validator.get_metrics("strat_001")
print(f"Win Rate: {metrics.win_rate:.2%}")
print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
print(f"Max DD: {metrics.max_drawdown_pct:.2%}")
print(f"P-value: {metrics.wr_p_value:.4f}")
print(f"Statistically Significant: {metrics.is_statistically_significant}")
```

### Check Pipeline Status
```python
from strategy_validation import StrategyDashboard

dashboard = StrategyDashboard(validator)
summary = dashboard.get_pipeline_summary()

for stage, data in summary.items():
    print(f"{stage}: {data['count']} strategies")
```

### Run Monte Carlo Simulation
```python
results = validator.monte_carlo_sim("strat_001", num_simulations=1000)

print(f"Robust: {results['is_robust']}")
print(f"Score: {results['robustness_score']:.2%}")
print(f"Prob Profit: {results['total_pnl']['prob_profit']:.2%}")
print(f"Prob WR>50%: {results['win_rate']['prob_above_50']:.2%}")
```

### Manual Operations
```python
from strategy_validation import StrategyStage, KillReason

# Manual disable
validator.manual_disable("strat_001")

# Manual promote
validator.manual_promote("strat_001", StrategyStage.LIVE)

# Get all live strategies
live_strats = validator.get_all_strategies(StrategyStage.LIVE)
```

## False Discovery Rate Control

```python
from strategy_validation import FalseDiscoveryRateControl

# Collect p-values from multiple strategies
p_values = {
    "strat_001": 0.01,
    "strat_002": 0.04,
    "strat_003": 0.15,
    # ... more strategies
}

# Apply FDR control
bh_results = FalseDiscoveryRateControl.benjamini_hochberg(p_values, alpha=0.05)

for strat_id, is_significant in bh_results.items():
    print(f"{strat_id}: {'Significant' if is_significant else 'Not significant'}")
```

## Walk-Forward Analysis

```python
from strategy_validation import WalkForwardAnalysis

wfa = WalkForwardAnalysis(validator)
results = wfa.perform_wfa(
    "strat_001",
    train_size=50,    # 50 trades for training
    test_size=20,     # 20 trades for testing
    step_size=10      # Slide 10 trades each time
)

print(f"Windows: {results['num_windows']}")
print(f"Consistent: {results['is_consistent']}")
print(f"Train WR: {results['win_rate']['train_mean']:.2%}")
print(f"Test WR: {results['win_rate']['test_mean']:.2%}")
```

## Database Queries

```python
import sqlite3

conn = sqlite3.connect("my_trading.db")
cursor = conn.cursor()

# Get all disabled strategies
cursor.execute("""
    SELECT strategy_id, kill_reason, disabled_at 
    FROM strategies 
    WHERE stage = 'disabled'
""")

# Get kill events by reason
cursor.execute("""
    SELECT kill_reason, COUNT(*) 
    FROM kill_events 
    GROUP BY kill_reason
""")

# Get promotion history
cursor.execute("""
    SELECT strategy_id, from_stage, to_stage, timestamp
    FROM promotion_events
    ORDER BY timestamp DESC
""")

conn.close()
```

## Integration with Trading System

```python
class TradingSystem:
    def __init__(self):
        self.validator = StrategyValidator(db_path="trading.db")
    
    def on_trade_closed(self, strategy_id, trade_data):
        """Called when a trade is closed."""
        trade = Trade(
            trade_id=trade_data['id'],
            strategy_id=strategy_id,
            timestamp=datetime.now(),
            pnl=trade_data['pnl'],
            pnl_pct=trade_data['pnl_pct'],
            direction=trade_data['direction'],
            entry_price=trade_data['entry'],
            exit_price=trade_data['exit'],
            holding_period=trade_data['duration']
        )
        
        metrics, kill_reason = self.validator.record_trade(trade)
        
        if kill_reason:
            self.disable_strategy(strategy_id, kill_reason)
        
        return metrics
    
    def disable_strategy(self, strategy_id, kill_reason):
        """Disable a strategy in the trading system."""
        # Stop trading
        # Close open positions
        # Send alert
        print(f"Strategy {strategy_id} disabled: {kill_reason.value}")
```

## Monitoring Dashboard

```python
def generate_daily_report(validator):
    """Generate daily strategy health report."""
    dashboard = StrategyDashboard(validator)
    
    report = {
        'date': datetime.now().isoformat(),
        'pipeline': dashboard.get_pipeline_summary(),
        'kills': dashboard.get_kill_switch_summary(),
        'ready_for_promotion': dashboard.get_strategies_ready_for_promotion()
    }
    
    # Count strategies by stage
    for stage in ['incubator', 'sandbox', 'fresh_picks', 'live', 'disabled']:
        count = report['pipeline'][stage]['count']
        print(f"{stage.upper()}: {count}")
    
    # Alert on recent kills
    recent_kills = report['kills']['recent_kills']
    if recent_kills:
        print(f"\n⚠️  Recent kill switches: {len(recent_kills)}")
    
    return report
```

## Troubleshooting

### Strategy killed unexpectedly
```python
# Check metrics at kill
info = validator.get_strategy_info("strat_001")
metrics = validator.get_metrics("strat_001")

print(f"Killed at: {info['disabled_at']}")
print(f"Reason: {info['kill_reason'].value}")
print(f"Trades: {metrics.total_trades}")
print(f"WR: {metrics.win_rate:.2%}")
print(f"Max DD: {metrics.max_drawdown_pct:.2%}")
```

### Strategy not promoting
```python
# Check promotion criteria
dashboard = StrategyDashboard(validator)
ready = dashboard.get_strategies_ready_for_promotion()

print(f"Ready for LIVE: {len(ready['to_live'])}")
for item in ready['to_live']:
    print(f"  {item['strategy_id']}")
```

## Performance Tips

1. **Batch trade recording** for high-frequency strategies
2. **Cache metrics** to avoid recalculation
3. **Archive old strategies** to keep database small
4. **Run MC simulations** asynchronously
5. **Use connection pooling** for high throughput

## Key Constants

```python
# Pipeline stages
StrategyStage.INCUBATOR    # 0-50 trades
StrategyStage.SANDBOX      # 50-100 trades
StrategyStage.FRESH_PICKS  # 100-200 trades
StrategyStage.LIVE         # 200+ trades
StrategyStage.DISABLED     # Kill switch triggered

# Kill reasons
KillReason.WIN_RATE_THRESHOLD
KillReason.SHARPE_THRESHOLD
KillReason.MAX_DRAWDOWN
KillReason.CONSECUTIVE_LOSSES
KillReason.STATISTICAL_INVALID
```
