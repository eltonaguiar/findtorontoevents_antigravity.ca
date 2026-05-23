# Infrastructure Modules v2.0

**Date:** 2026-05-02

Three new production modules to elevate the platform to institutional grade.

## 1. track_calculator.py -- Fixes TRK% vs FWD WR% Bug

**Problem:** `forward_wr` was calculated at **strategy-level only**, masking that BTC-USD LONG had 54.9% WR while ETH-USD SHORT had 28.9% under the same strategy.

**Fix:** Computes forward WR at `(strategy, symbol, direction)` granularity.

**Usage:**
```python
from alpha_engine.track_calculator import get_track_wr
result = get_track_wr("markov_zone", "BTC-USD", "LONG", min_n=5)
# {"track_key": "markov_zone:BTC-USD:LONG", "win_rate": 0.549, "n": 441, "pf": 3.14}
```

## 2. statistical_rigor.py -- PSR / DSR / Bootstrap CI

Implements institutional-grade statistical validation:
- **Bootstrap CI**: 1,000 runs, BCa accelerated
- **PSR**: Probabilistic Sharpe Ratio -- P(SR > benchmark | observed data)
- **DSR**: Deflated Sharpe Ratio -- multiple-testing correction
- **MTRL**: Minimum Track Record Length in months

**Usage:**
```python
from alpha_engine.statistical_rigor import StrategyValidator
v = StrategyValidator()
result = v.validate_strategy(returns, name="Equity_L100", n_trials_tested=50)
# result.psr > 0.95 and result.dsr > 0.95 --> genuine edge confirmed
```

**Evidence Grades:**
- A+: PSR > 0.99, DSR > 0.99
- A: PSR > 0.95, DSR > 0.95
- B: PSR > 0.90
- B-: PSR > 0.80
- C: PSR <= 0.80 (insufficient evidence)

## 3. decay_tracker.py -- Auto-Demotion Ladder

4-tier health monitoring with automatic position sizing:

| Tier | Sharpe | Action | Size |
|------|--------|--------|------|
| GREEN | > 1.5 | MAINTAIN | 1.0x |
| YELLOW | 0.8-1.5 or -20% from peak | REDUCE_SIZE | 0.5x |
| RED | < 0.8 or -40% from peak | PAPER_TRADE | 0.25x |
| BLACK | 5+ red days or PF < 0.8 | **HALT** | 0.0x |

**Usage:**
```python
from alpha_engine.decay_tracker import DecayTracker
dt = DecayTracker()
status = dt.check_strategy("Equity_L100", returns_90d)
# status.tier -> "GREEN", status.size_multiplier -> 1.0
```

## Deployment

```bash
# Install dependencies
pip install numpy

# Run validation on all strategies
python -c "
from alpha_engine.statistical_rigor import batch_validate
import numpy as np
strategies = {
    'Equity_L100': np.random.normal(0.007, 0.01, 100),
    'Crypto_S_Tier': np.random.normal(0.005, 0.008, 50),
}
results = batch_validate(strategies, n_trials_tested=50)
print(results['summary'])
"
```
