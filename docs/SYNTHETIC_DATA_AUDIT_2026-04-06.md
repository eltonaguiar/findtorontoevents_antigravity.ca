# Synthetic Data Audit — 2026-04-06

## Executive Summary

Audit of all `seed=42`, `np.random.seed`, and `generate_synthetic` usage across
`alpha_engine/` to identify root causes of the r=-0.91 backtest-forward correlation.

**Key Finding:** Synthetic data generation is confined to `__main__` test/demo blocks
and is NOT directly fed into the production scoring pipeline. The production path
(`run_massive_mutations.py` -> `vectorized_backtest.py`) fetches REAL Binance candles.
However, incubator strategies (bollinger, grid, RSI momentum) that were developed
and initially validated on synthetic data could have leaked biased parameter choices
into production if their tuned parameters were copy-pasted without re-validation.

## Root Cause Analysis

The r=-0.91 backtest-forward correlation has **multiple contributing factors**:

1. **Synthetic data validation** (this audit): Strategy parameters tuned on GBM
   synthetic data (seed=42) produce artifacts that do not exist in real markets:
   - No fat tails, no regime switches, no liquidity gaps
   - GBM mean-reversion patterns that real crypto does not exhibit
   - Trend-following parameters tuned to sinusoidal synthetic trends

2. **Overfitting via grid search**: 635+ strategy parameter combinations searched
   against a small synthetic dataset will find spurious patterns with 100% certainty.

3. **Selection bias**: Only strategies that "looked good" on synthetic data were
   promoted to production, guaranteeing regression to (below) mean on real data.

## Files Using Synthetic Data

### Category A: Strategy Incubators (FLAGGED)
These files generate synthetic data and validate strategy logic against it.
Parameters derived from these tests are unreliable for live trading.

| File | Function | Seed | Production Impact |
|------|----------|------|-------------------|
| `bollinger_meanrev.py` | `generate_synthetic_data()` | 42 | LOW - `__main__` only, not imported |
| `grid_trading_incubator.py` | `generate_synthetic_data()` | 42 | LOW - `__main__` only, not imported |
| `rsi_momentum_strategy.py` | `generate_synthetic_data()` | 42 | LOW - `__main__` only, not imported |
| `vectorized_backtest.py` | `generate_synthetic_candles()` | 42 | LOW - benchmark only; production uses real data |
| `diagonal_trendline_breakout.py` | inline seed=42 | 42 | LOW - `__main__` demo only |
| `confluence_pipeline.py` | inline seed=42 | 42 | LOW - `__main__` demo only |
| `smart_entry.py` | inline seed=42 | 42 | LOW - self-test only |
| `pattern_cnn_lite.py` | inline seed=42 | 42 | LOW - fallback when yfinance unavailable |

### Category B: Monte Carlo Simulators (CORRECT usage)
These use seed=42 for **reproducible randomization** in statistical simulations.
This is standard practice and does NOT constitute synthetic price data.

- `monte_carlo.py`, `intensive_monte_carlo.py`, `levy_gaussian_monte_carlo.py`
- `hf_backtest_pipeline.py`, `advanced_risk_system.py`, `forward_validator.py`
- `vectorized_backtest.py` (bootstrap_ci function)

### Category C: Validation Test Demos (CORRECT usage)
These use seed=42 in `__main__` blocks for statistical validation examples.

- `validation/statistical_gates.py`, `validation/sharpe_metrics.py`

## Fixes Implemented

### 1. Smart Picks Engine (`smart_picks_engine.py`)
- Added `SYNTHETIC_ORIGIN_STRATEGIES` set with 5 flagged strategies
- Added `-30` score penalty for synthetic-origin strategies with <10 forward trades
- Added `-15` penalty (half) for those with 10-29 forward trades
- Penalty waived at 30+ real forward trades (proven on real data)
- Added `_synthetic_origin` flag and `data_source` field to scored picks
- Strategies must have `data_source: "real"` to qualify for Smart Picks top tier

### 2. Production Scanner (`production_scanner.py`)
- Added Gate -1 (before all other gates): synthetic origin detection
- Synthetic-origin strategies get `_synthetic_origin: true` tag
- Confidence reduced by 0.30 for strategies with <30 real forward trades
- This effectively removes them from qualifying for confidence-floor gates

### 3. Warning Markers (4 files)
Added `_SYNTHETIC_WARNING = True` module-level flag to:
- `bollinger_meanrev.py`
- `grid_trading_incubator.py`
- `rsi_momentum_strategy.py`
- `vectorized_backtest.py`

### 4. Registry
Created `alpha_engine/data/synthetic_strategies_registry.json` cataloging all
synthetic data usage with risk assessments and production impact flags.

## Strategies Affected

| Strategy | Current Status | Penalty Applied |
|----------|---------------|-----------------|
| `bb_mean_reversion` | Incubator only | -30 (no fwd data) |
| `grid_trading` | Incubator only | -30 (no fwd data) |
| `rsi_momentum` | Incubator only | -30 (no fwd data) |
| `keltner_compression_expansion` | Active via mutations | -30 until 30+ fwd trades |
| `diagonal_trendline_breakout` | Incubator only | -30 (no fwd data) |

## Recommendations

1. **Immediate**: All new strategies MUST be validated on real historical data
   (minimum 200 bars of real OHLCV) before entering production scoring.

2. **Short-term**: Replace all `generate_synthetic_data()` calls in incubators
   with a `fetch_real_candles()` function that pulls from Binance/CoinGecko.

3. **Medium-term**: Add a `data_source` field requirement to the strategy
   registration pipeline. Strategies without `data_source: "real"` cannot
   enter the Smart Picks pool.

4. **Long-term**: The r=-0.91 correlation is primarily caused by overfitting
   and selection bias, not just synthetic data. Walk-forward validation
   (`walk_forward_backtester.py`) must be the mandatory gate for all strategies.
