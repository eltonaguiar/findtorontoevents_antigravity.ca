# Permutation Portfolio Testing System

This system creates paper trading portfolios to test which **systems** (alone or together) and **strategies** (alone or together) can be trusted to generate profit.

## Overview

### System Permutation Portfolios
Test which trading systems produce better results when:
- Running **solo** (individual system)
- Running in **pairs** (2 systems must agree)
- Running in **triplets** (3 systems must agree)
- Running with **flexible consensus** (2 of 3, 2 of 4, 3 of 5, etc.)

### Strategy Combination Portfolios  
Test which strategies produce better results when:
- Running **solo** (individual strategy)
- Running with **confluence** (multiple strategies must agree)
- Running by **category** (trend + mean reversion, breakout + ML, etc.)
- Running by **performance tier** (proven only, strong only, etc.)

## Quick Start

### 1. Initialize Portfolios
```bash
cd paper_trading
python -m permutation_portfolio_manager --mode all
```

### 2. Run Analysis
```bash
# Generate full report
python -m permutation_analyzer --report full --export-html

# View specific analysis
python -m permutation_analyzer --report systems
python -m permutation_analyzer --report strategies
python -m permutation_analyzer --report trust
```

### 3. View Results
Open `paper_trading/data/permutation_report.html` in your browser.

## Portfolio Categories

### System Permutation Portfolios

| Category | Description | Count |
|----------|-------------|-------|
| **Solo Systems** | Individual system baseline | 7 |
| **Pair Combinations** | 2-system agreement | 9 |
| **Triplet Combinations** | 3-system agreement | 6 |
| **Flexible Consensus** | 2/3, 2/4, 3/5 agreement | 4 |
| **High Performance** | Systems with WR > 50% | 5 |
| **ML Focused** | ML-based systems only | 6 |
| **Rapid Fire Variants** | RF + other systems | 6 |

**Total: 43 system permutation portfolios**

### Strategy Combination Portfolios

| Category | Description | Count |
|----------|-------------|-------|
| **Solo Strategies** | Individual strategy baseline | 9 |
| **Category Combinations** | Cross-category mixing | 5 |
| **Tier Combinations** | By performance tier | 4 |
| **Confluence Portfolios** | Multi-strategy agreement | 5 |
| **Champion Focused** | Competition winners | 3 |
| **Hoffman Family** | IRB variations | 5 |
| **Prop Firm Focused** | Battle-tested classics | 5 |
| **KIMI ML Focused** | Academic ML strategies | 4 |
| **Anti-Correlation** | Hedging combinations | 2 |

**Total: 42 strategy combination portfolios**

## Configuration Files

### `system_permutation_config.json`
Defines all system portfolios with parameters:
- `systems`: Which systems to include
- `min_agreement`: Minimum systems that must agree
- `max_agreement`: Maximum systems that can agree
- `filter`: Optional filters (e.g., WR threshold)

### `strategy_combination_config.json`
Defines all strategy portfolios with parameters:
- `strategies`: Which strategies to include
- `min_strategies`: Minimum strategies that must agree
- `require_same_direction`: All must be LONG or all SHORT
- `allow_opposing_directions`: Allow hedging

## Database Schema

### Tables
- `permutation_portfolios`: Portfolio definitions and performance
- `permutation_positions`: Individual trades per portfolio
- `permutation_equity_snapshots`: Historical equity tracking

### Key Metrics Tracked
- Total trades, wins, losses
- Win rate, PnL %
- Max drawdown
- Profit factor
- Expectancy
- Trust score (composite metric)

## Trust Score Calculation

The trust score (0-100) is calculated as:
- Win rate component: up to 40 points
- PnL component: up to 30 points  
- Sample size component: up to 20 points
- Drawdown penalty: subtracts up to 20 points

**Interpretation:**
- **70+**: Highly trusted - allocate significant capital
- **50-69**: Trusted - allocate moderate capital
- **30-49**: Promising - monitor and small allocation
- **< 30**: Unproven - avoid or paper trade only

## Running the System

### Manual Execution
```bash
# Process new picks and update portfolios
python -m permutation_portfolio_manager --mode systems
python -m permutation_portfolio_manager --mode strategies
python -m permutation_portfolio_manager --mode all

# Generate reports
python -m permutation_analyzer --report full --export-html
```

### Automated (Cron)
```bash
# Add to crontab to run every hour
0 * * * * cd /path/to/paper_trading && python -m permutation_portfolio_manager --mode all
0 * * * * cd /path/to/paper_trading && python -m permutation_analyzer --report full --export-html
```

## Interpreting Results

### What to Look For

1. **Best Solo Systems**: Which individual systems are profitable?
2. **Combination Boost**: Do combinations outperform solo systems?
3. **Optimal Agreement Level**: Is 2/3, 3/5, or full consensus best?
4. **Strategy Confluence**: Do multiple strategies agreeing improve results?
5. **Category Synergy**: Which strategy categories work well together?

### Red Flags

- Win rate < 45% (losing strategy)
- Negative expectancy (loses money over time)
- High drawdown > 20% (too risky)
- Low sample size < 10 trades (insufficient data)

## Extending the System

### Adding New Systems
1. Edit `system_permutation_config.json`
2. Add system definition to `systems` section
3. Add portfolio definitions to appropriate category
4. Run `permutation_portfolio_manager` to initialize

### Adding New Strategies
1. Edit `strategy_combination_config.json`
2. Add strategy to appropriate category
3. Add portfolio definitions
4. Run `permutation_portfolio_manager` to initialize

### Custom Analysis
```python
from paper_trading.permutation_analyzer import PermutationAnalyzer

analyzer = PermutationAnalyzer()
analyzer.load_stats()

# Custom filtering
for pf_id, stats in analyzer.system_stats.items():
    if stats.win_rate > 60 and stats.total_trades > 20:
        print(f"{stats.name}: {stats.win_rate}% WR, {stats.pnl_pct}% PnL")
```

## Files

| File | Purpose |
|------|---------|
| `permutation_portfolio_manager.py` | Main execution engine |
| `permutation_analyzer.py` | Analysis and reporting |
| `system_permutation_config.json` | System portfolio definitions |
| `strategy_combination_config.json` | Strategy portfolio definitions |
| `PERMUTATION_README.md` | This file |

## Integration with Existing Paper Trading

This system extends the existing paper trading infrastructure:
- Uses same database (`paper.db`)
- Uses same position sizing (2% risk)
- Uses same TP/SL logic
- Separate tables to avoid conflicts

## Future Enhancements

- [ ] Dynamic position sizing based on trust score
- [ ] Auto-promotion of high-trust combinations to live trading
- [ ] Machine learning to predict which combinations will work
- [ ] Correlation analysis between portfolios
- [ ] Monte Carlo simulation for robustness testing
