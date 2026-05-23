# Signal Quality Scoring System

A hedge fund-quality signal validation system for crypto trading predictions.

## Overview

This system provides comprehensive multi-dimensional scoring of trading signals to ensure only high-quality signals are executed. Signals are scored on a 0-100 scale across 6 dimensions and assigned grades from A+ to F.

## Grade Thresholds

| Grade | Score | Status | Action |
|-------|-------|--------|--------|
| A+ | 95-100 | Exceptional | Full position size |
| A | 90-94 | Excellent | Full position size |
| A- | 85-89 | Very Good | Standard size |
| B+ | 80-84 | Good | Standard size |
| B | 75-79 | Above Average | Standard size |
| B- | 70-74 | Acceptable | **Min. for live trading** |
| C+ | 65-69 | Marginal | Paper trade only |
| C | 60-64 | Weak | Paper trade only |
| D/F | < 60 | Poor | Reject |

## File Structure

```
genome/
├── __init__.py                  - Module initialization
├── quality_engine.py            - Core quality scoring (SignalQualityEngine)
├── tp_sl_calculator.py          - TP/SL calculations (TPSLCalculator)
├── signal_validator.py          - Pre-trade validation (SignalValidator)
├── picks_generator.py           - Picks orchestrator (PicksGenerator)
├── run_quality_system.py        - CLI runner
├── test_quality_system.py       - Unit tests
├── active_picks.json            - Generated picks output
├── grades_explained.md          - Detailed grading documentation
└── README.md                    - This file
```

## Quick Start

### Run Demo
```bash
python genome/run_quality_system.py demo
```

### Run Tests
```bash
python genome/run_quality_system.py test
```

### Generate Daily Picks
```bash
python genome/run_quality_system.py generate
```

### Validate Signal File
```bash
python genome/run_quality_system.py validate signal.json
```

## Usage Example

```python
from genome import SignalQualityEngine, TPSLCalculator, SignalValidator

# 1. Score a signal
engine = SignalQualityEngine()
quality = engine.calculate_quality_score(signal)
print(f"Score: {quality.total_score}, Grade: {quality.grade}")

# 2. Validate
validator = SignalValidator()
validation = validator.validate(signal)
if validation.approved:
    # 3. Calculate TP/SL
    calc = TPSLCalculator()
    levels = calc.calculate_levels(
        symbol="BTCUSDT",
        entry_price=85000.0,
        direction="LONG",
        strategy_dna={'risk_profile': 'medium', 'win_rate': 0.65}
    )
    print(f"TP: ${levels['take_profit']}, SL: ${levels['stop_loss']}")
```

## Scoring Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Backtest Validity | 25% | Sharpe ratio, win rate, profit factor |
| Statistical Significance | 20% | Sample size, trade count |
| Regime Alignment | 15% | Current market regime fit |
| Risk-Adjusted Return | 20% | Sortino, Calmar ratios |
| Consensus Strength | 10% | Multi-system agreement |
| Market Structure | 10% | Liquidity, spread, volume |

## Validation Checks

- Sufficient backtest data (30+ trades, 180+ days)
- No recent similar signals (4-hour cooldown)
- Market hours OK
- Liquidity sufficient ($10M+ daily volume)
- Portfolio correlation within limits
- Daily loss limit not exceeded
- Spread acceptable (< 1%)
- Volatility normal (< 15% daily)
- Not blacklisted

## Output Format

```json
{
  "id": "pick_btc_20260302_001",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry_price": 85000.00,
  "take_profit": 93500.00,
  "stop_loss": 80750.00,
  "risk_reward": 2.0,
  "quality_score": 87.5,
  "grade": "A-",
  "verdict": "STRONG_BUY",
  "position_size_pct": 3.5
}
```

## Testing

Run all unit tests:
```bash
python -m pytest genome/test_quality_system.py -v
```

Or via the runner:
```bash
python genome/run_quality_system.py test
```

## License

Part of the crypto trading system.
