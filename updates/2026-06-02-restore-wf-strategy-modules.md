# Restore walk-forward strategy modules (2026-06-02)

## Problem
`walkforward_suite.py --only pilot` returned `SKIP` for `etf_dual_momentum` and `crypto_donchian_breakout` because `verified_strategies/strategies/*.py` were never committed with PR #438.

## Fix
- Added `etf_dual_momentum.py` — sector vs SPY dual momentum (rebalance every 10 bars, 252d lookback).
- Added `crypto_donchian_breakout.py` — 20/10 Donchian with ATR stops.
- `walkforward_suite.py` — SPY history 2000 bars for ETF sleeve.

## Verify
```bash
python3 verified_strategies/walkforward_suite.py --only pilot
python3 tools/strategy_admit.py --strategy etf_dual_momentum --asset-class ETF --write
```

Donchian OOS may FAIL (expected per lab); ETF needs sufficient closed rotations for OOS n≥10.