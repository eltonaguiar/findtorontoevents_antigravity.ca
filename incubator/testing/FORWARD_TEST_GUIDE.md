# Forward Testing System Guide

**Status:** ✅ Active  
**Location:** `incubator/testing/`  
**Database:** `incubator/forward_test.db`

---

## Overview

Comprehensive system for tracking strategies from **paper trading → forward testing → graduation → live deployment**.

This ensures we know what **REALLY** works in live markets, not just what backtests well.

---

## Key Components

### 1. ForwardTestTracker (`forward_test_tracker.py`)
SQLite-based tracking system for strategy lifecycle.

```python
from incubator.testing import register_strategy_for_forward_test, update_forward_performance

# When strategy passes Tier 1/2
register_strategy_for_forward_test('my_strategy', 'web_ai', {
    'sharpe': 1.5,
    'win_rate': 0.55,
    'max_drawdown': 0.15,
    'expectancy': 0.65
})

# Daily/hourly updates from paper trading
update_forward_performance('my_strategy', {
    'sharpe': 1.2,
    'win_rate': 0.52,
    'max_drawdown': 0.18,
    'pnl_pct': 5.2,
    'trades_count': 25,
    'days_in_test': 15
}, trades=[...])
```

### 2. Graduation Criteria

Strategies must meet ALL criteria to graduate to live:

| Criteria | Minimum | Ideal |
|----------|---------|-------|
| Forward Days | 30 | 45+ |
| Trade Count | 20 | 30+ |
| Win Rate | 45% | 50%+ |
| Sharpe | 0.8 | 1.0+ |
| Max Drawdown | 25% | <20% |
| P&L | Positive | >5% |

**Graduation Score:** 0-100 calculated from performance metrics
- 80+ = Tier S (Full allocation)
- 60-79 = Tier A (Reduced allocation)
- 40-59 = Continue testing
- <40 = Review/eliminate

### 3. ForwardTestDashboard (`forward_dashboard.py`)

Generate comprehensive reports:

```python
from incubator.testing import generate_forward_report, get_graduation_candidates

# Full JSON + Markdown report
report_path = generate_forward_report()

# Get candidates ready for graduation
candidates = get_graduation_candidates()
```

### 4. ForwardTestCoordinator (`forward_test_coordinator.py`)

Parallel coordination of forward testing across workers:

```bash
# Discover strategies needing forward test
python -m incubator.testing.forward_test_coordinator --discover

# Run forward tests with 4 workers
python -m incubator.testing.forward_test_coordinator --run --workers 4

# Auto-graduate ready strategies (dry run)
python -m incubator.testing.forward_test_coordinator --graduate --min-score 75

# Actually graduate
python -m incubator.testing.forward_test_coordinator --graduate --min-score 75 --execute
```

---

## Database Schema

### strategies table
```sql
- strategy_name (PRIMARY KEY)
- agent_id (codex_gpt5, cursor_ai, web_ai, etc.)
- status (paper_trading, forward_testing, graduated, failed)
- backtest_* metrics
- forward_* metrics
- graduation_score
- created_at, graduated_at
```

### daily_performance table
```sql
- strategy_name
- date
- pnl_pct, cumulative_pnl_pct
- trades_count, drawdown_pct
```

### forward_trades table
```sql
- strategy_name
- entry_time, exit_time
- direction, entry_price, exit_price
- pnl_pct, exit_reason, bars_held
```

---

## Workflow

```
┌─────────────────┐
│ Strategy Created│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Tier 1 Pass?   │────▶│  Asset-Specific  │
│ (BTC/ETH/SOL)   │ Fail│  Test Other Pairs│
└────────┬────────┘     └──────────────────┘
         │ Pass
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Tier 2 Pass?   │────▶│  Partial Pass    │
│ (Multi-TF)      │ Fail│  (1-2 timeframes)│
└────────┬────────┘     └──────────────────┘
         │ Pass
         ▼
┌─────────────────────────┐
│ Register for Forward    │
│ (Paper Trading Start)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 30+ Days Forward Test   │
│ Track: Sharpe, WR, DD   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐     ┌──────────────┐
│ Graduation Criteria Met?│────▶│ Continue     │
│ Score ≥ 75              │ Fail│ Paper Trading│
└────────┬────────────────┘     └──────────────┘
         │ Pass
         ▼
┌─────────────────────────┐
│ 🎓 GRADUATED TO LIVE    │
│ Allocation: 5-10%       │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Live Performance Track  │
│ Monthly Review          │
└─────────────────────────┘
```

---

## GitHub URLs for Web AIs

Testing Utilities:  
`https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/incubator/testing/__init__.py`

Forward Test Tracker:  
`https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/incubator/testing/forward_test_tracker.py`

Forward Dashboard:  
`https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/incubator/testing/forward_dashboard.py`

---

## Key Insights from Forward Testing

From `FORWARD_TEST_VALIDATION_REPORT.md`:

- **Only 22% of backtested strategies proved viable** in forward testing
- **Backtest/Forward correlation: 0.34** (significant overfitting)
- **Strategies that survived:**
  - Funding Rate Arbitrage (score: 88)
  - Pairs Trading (score: 79)
  - Betting Against Beta (score: 77)
  - Flash Crash Reversal (score: 71)
  - Quality Minus Junk (score: 75)

**Rule:** Deploy capital ONLY to strategies with forward-test validation.

---

## Files

| File | Purpose |
|------|---------|
| `forward_test_tracker.py` | Core tracking logic, SQLite database |
| `forward_dashboard.py` | Report generation, graduation candidates |
| `forward_test_coordinator.py` | Parallel worker coordination |
| `__init__.py` | Public API exports |

---

*Last Updated: 2026-02-27*  
*System Status: Ready for production use*
