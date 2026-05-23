# HyroTrader Methodology & Enhancement Recommendations — 2026-05-15

**Current Role**: External paper-trading challenge bridge (`tools/hyro_quan_bridge.py`, `hyro_pick_performance_validator.py`, `hyro_ml_pick_optimizer.py`).

## Current State
- Used primarily for participating in HyroTrader competitions and pulling performance data.
- Functions as an external validation layer rather than a core internal production signal.
- `/audit/hyrotrader` section exists but is under-developed compared to main asset class views.

## Recommended Enhancements (90-Day)

**P0 (0-30 days)**
- Make HyroTrader paper P&L a first-class data source in the main audit (compare directly vs internal paper trading for the same strategies).
- Add automated "HyroTrader Survival Rate" metric per strategy.

**P1 (30-60 days)**
- Use consistent positive expectancy in HyroTrader challenges as a **graduation gate** for new strategies (faster path to higher sizing / trust_score).
- Build a "HyroTrader Top Performers" feed that can be used as an opt-in signal source.

**P2 (60-90 days)**
- Treat HyroTrader as a high-fidelity forward-test environment (real competition + realistic slippage).
- Create a dedicated HyroTrader tab/panel in `/audit` that shows strategy-by-strategy comparison (Internal Paper vs HyroTrader vs Live when available).

**Verdict**: HyroTrader is currently an under-leveraged external validation tool. Turning it into a proper forward-test + graduation engine would significantly improve strategy selection quality with low additional cost.