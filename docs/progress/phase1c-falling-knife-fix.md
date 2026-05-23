# Phase 1C: Falling Knife Filter Fix

## Status: COMPLETE

## Task
Relax the falling knife filter in `crypto_ml_edge/quick_scanner.py` to be regime-adaptive using live Fear & Greed data from the API, with three tiers:
- Normal (F&G > 30): 20% threshold (original)
- Fear (F&G 16-30): 35% threshold
- Extreme fear (F&G <= 15): 50% threshold (nearly disabled)

## Rationale
Mercury 2 proved extreme fear bounces = #1 edge (8/8 wins, +28.66%). During F&G=11, everything is 30-50% below 200 SMA, so the old 20% filter rejected ALL crypto picks.

## Changes
- [x] Replace static constants with 3-tier regime constants + dynamic function `_get_dynamic_falling_knife_threshold()`
- [x] Update `normalize_connors_signal` falling knife check to use dynamic threshold
- [x] Update `normalize_vix_signal` falling knife check to use dynamic threshold
- [x] Update `normalize_fib_pullback_signal` falling knife check to use dynamic threshold
- [x] Update `_retroactive_falling_knife_sweep` to use dynamic threshold
- [x] Added `import requests` for live F&G API call
- [x] Verify syntax - PASSED
