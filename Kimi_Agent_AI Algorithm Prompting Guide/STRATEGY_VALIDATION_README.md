# Strategy Validation and Kill Switch System

## Overview

This is a production-ready Python module for validating trading strategies before they go live. It provides comprehensive performance tracking, automated kill switches, a promotion pipeline, Monte Carlo simulation for robustness testing, and statistical significance testing.

## Key Features

### 1. Strategy Promotion Pipeline
```
INCUBATOR (0-50 trades) → SANDBOX (50-100 trades) → FRESH_PICKS (100-200 trades) → LIVE (200+ trades)
```

### 2. Kill Switch System
Automatically disables strategies that fail performance thresholds:
- Win Rate < 45% after 50 trades
- Sharpe Ratio < 1.0 after 50 trades
- Max Drawdown > 15%
- Profit Factor < 1.0
- 10+ consecutive losses
- Statistically invalid performance

### 3. Performance Metrics
- **Basic**: Total trades, Win Rate, P&L
- **Risk-Adjusted**: Sharpe, Sortino, Calmar ratios
- **Drawdown**: Max drawdown, current drawdown
- **Statistical**: P-value for win rate significance

### 4. Monte Carlo Simulation
Tests strategy robustness through bootstrap resampling:
- Probability of profitability
- Win rate confidence intervals
- Sharpe ratio distribution
- Robustness score calculation

### 5. False Discovery Rate Control
Implements multiple testing corrections:
- Benjamini-Hochberg procedure
- Benjamini-Yekutieli procedure
- Bonferroni correction

### 6. Walk-Forward Analysis
Validates out-of-sample performance with rolling windows.

## Quick Start

```python
from strategy_validation import (
    StrategyValidator, KillSwitchConfig, PromotionCriteria,
    Trade, StrategyStage
)
from datetime import datetime
import numpy as np

# Configure kill switches
kill_config = KillSwitchConfig(
    wr_threshold=0.45,          # Kill if WR < 45%
    sharpe_threshold=1.0,       # Kill if Sharpe < 1.0
    max_drawdown_pct=-0.15,     # Kill if DD > 15%
    min_trades_for_kill=50      # Minimum trades before kill
)

# Configure promotion criteria
promotion_criteria = PromotionCriteria(
    live_min_trades=200,        # 200+ trades for LIVE
    live_min_wr=0.52,           # 52% WR for LIVE
    live_min_sharpe=1.0         # Sharpe >= 1.0 for LIVE
)

# Initialize validator
validator = StrategyValidator(
    db_path="strategy_validation.db",
    kill_config=kill_config,
    promotion_criteria=promotion_criteria
)

# Register a strategy
validator.register_strategy("my_strategy", metadata={
    "type": "momentum",
    "timeframe": "1h"
})

# Record trades
for i in range(250):
    pnl = np.random.normal(15, 40)  # Simulate trade P&L
    
    trade = Trade(
        trade_id=f"trade_{i}",
        strategy_id="my_strategy",
        timestamp=datetime.now(),
        pnl=pnl,
        pnl_pct=pnl / 1000,
        direction="long",
        entry_price=100,
        exit_price=100 + pnl,
        holding_period=60
    )
    
    metrics, kill_reason = validator.record_trade(trade)
    
    if kill_reason:
        print(f"Strategy KILLED: {kill_reason.value}")
        break

# Check final metrics
final_metrics = validator.get_metrics("my_strategy")
print(f"Stage: {validator.get_strategy_info('my_strategy')['stage'].value}")
print(f"Win Rate: {final_metrics.win_rate:.2%}")
print(f"Sharpe: {final_metrics.sharpe_ratio:.2f}")

# Run Monte Carlo simulation
mc_results = validator.monte_carlo_sim("my_strategy", num_simulations=1000)
print(f"Is Robust: {mc_results['is_robust']}")
print(f"Robustness Score: {mc_results['robustness_score']:.2%}")
```

## Configuration

### KillSwitchConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_trades_for_kill` | 20 | Minimum trades before kill switch activates |
| `wr_threshold` | 0.45 | Kill if win rate falls below this |
| `wr_min_trades` | 50 | Minimum trades for WR kill switch |
| `sharpe_threshold` | 1.0 | Kill if Sharpe falls below this |
| `sharpe_min_trades` | 50 | Minimum trades for Sharpe kill switch |
| `max_drawdown_pct` | -0.15 | Kill if max drawdown exceeds this |
| `max_consecutive_losses` | 10 | Kill after this many consecutive losses |
| `significance_level` | 0.05 | P-value threshold for statistical tests |

### PromotionCriteria

| Stage | Min Trades | Min WR | Min Sharpe | Max DD |
|-------|------------|--------|------------|--------|
| SANDBOX | 50 | 48% | - | -10% |
| FRESH_PICKS | 100 | 50% | 0.8 | -12% |
| LIVE | 200 | 52% | 1.0 | -15% |

## Database Schema

The system uses SQLite for persistence with the following tables:

- **strategies**: Strategy metadata and current stage
- **trades**: Individual trade records
- **metrics_history**: Historical metrics snapshots
- **kill_events**: Kill switch activation log
- **promotion_events**: Promotion pipeline log
- **monte_carlo_results**: MC simulation results

## API Reference

### StrategyValidator

#### `register_strategy(strategy_id, metadata=None)`
Register a new strategy in the INCUBATOR stage.

#### `record_trade(trade)`
Record a trade and update metrics. Returns `(metrics, kill_reason)`.

#### `calculate_metrics(strategy_id)`
Calculate comprehensive metrics for a strategy.

#### `check_kill_conditions(strategy_id, metrics)`
Check if kill switch should be triggered.

#### `monte_carlo_sim(strategy_id, num_simulations=1000, confidence_level=0.95)`
Run Monte Carlo simulation for robustness testing.

#### `get_metrics(strategy_id)`
Get cached metrics for a strategy.

#### `manual_disable(strategy_id, reason)`
Manually disable a strategy.

#### `manual_promote(strategy_id, to_stage)`
Manually promote a strategy.

### FalseDiscoveryRateControl

#### `benjamini_hochberg(p_values, alpha=0.05)`
Apply BH procedure for FDR control.

#### `benjamini_yekutieli(p_values, alpha=0.05)`
Apply BY procedure (works under arbitrary dependence).

#### `bonferroni(p_values, alpha=0.05)`
Apply Bonferroni correction (controls FWER).

### WalkForwardAnalysis

#### `perform_wfa(strategy_id, train_size=50, test_size=20, step_size=10)`
Perform walk-forward analysis.

### StrategyDashboard

#### `get_pipeline_summary()`
Get summary of strategies in each pipeline stage.

#### `get_kill_switch_summary()`
Get summary of kill switch events.

#### `get_strategies_ready_for_promotion()`
Get strategies meeting promotion criteria.

## Statistical Significance Testing

The system uses binomial tests to determine if a strategy's win rate is statistically significantly different from 50%:

```python
# P-value < 0.05 indicates statistical significance
if metrics.wr_p_value < 0.05:
    print("Win rate is statistically significant")
```

## Best Practices

### 1. Sample Size Requirements
- Minimum 50 trades before kill switches activate
- Minimum 200 trades before promotion to LIVE
- More trades = more reliable statistics

### 2. Kill Switch Configuration
- Set thresholds based on historical strategy performance
- Use more lenient thresholds during volatile markets
- Consider strategy type (trend-following vs mean-reversion)

### 3. Monte Carlo Simulation
- Run with at least 1000 simulations
- Require robustness score > 80% for LIVE promotion
- Check probability of profit > 70%

### 4. Multiple Strategy Testing
- Always use FDR control when testing many strategies
- Benjamini-Hochberg is appropriate for independent strategies
- Benjamini-Yekutieli for correlated strategies

## Integration Example

```python
# Daily strategy monitoring
def monitor_strategies(validator):
    dashboard = StrategyDashboard(validator)
    
    # Get pipeline summary
    summary = dashboard.get_pipeline_summary()
    
    # Check for strategies ready to promote
    ready = dashboard.get_strategies_ready_for_promotion()
    
    # Review kill switch events
    kills = dashboard.get_kill_switch_summary()
    
    # Generate report
    report = {
        'incubator_count': summary['incubator']['count'],
        'sandbox_count': summary['sandbox']['count'],
        'fresh_picks_count': summary['fresh_picks']['count'],
        'live_count': summary['live']['count'],
        'disabled_count': summary['disabled']['count'],
        'ready_for_live': len(ready['to_live']),
        'recent_kills': kills['recent_kills']
    }
    
    return report
```

## Performance Considerations

- Metrics are cached after calculation
- Database writes are batched where possible
- Monte Carlo simulations can be run asynchronously
- Use appropriate indexes for large trade histories

## Troubleshooting

### Strategy gets killed too early
- Increase `min_trades_for_kill`
- Adjust `max_drawdown_pct` for higher tolerance
- Check if strategy is suitable for current market regime

### Strategy never promotes to LIVE
- Verify promotion criteria are achievable
- Check if statistical significance is required
- Review Sharpe and Sortino thresholds

### Database performance issues
- Archive old strategies
- Limit metrics history retention
- Use connection pooling for high throughput

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please follow the existing code style and add tests for new features.

## Support

For questions or issues, please open a GitHub issue or contact the quantitative finance research team.
