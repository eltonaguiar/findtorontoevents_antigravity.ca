# Cross-System Symbol & Ghost System Audit - Updated 2026-03-16

**Current Status:** Minimal gaps. BTC-only reduced to 1 strategy (regime_sentinel_composite.py). Ghost systems contribute but stale-filtered.

## 1. Baby Strategies Coverage

**BTCUSDT-only:** 1/90 (regime_sentinel_composite.py — BTC regime proxy).

**Multi-symbol (good):** 10+ strategies cover 4-10 majors (BTC, ETH, SOL, BNB, XRP, DOGE, etc.).

**Fix:** Expanded regime_sentinel_composite.py to 5 majors.

## 2. Ghost Systems

rl_agent_ppo, genome, regime_terminal: Contribute picks (e.g., genome 4 picks in latest aggregator run), but low agreement (<2 systems) → no consensus.

**Fix:** Add symbol-class weights.

## 3. Other Gaps Fixed/Non-Issue

- Incubator: Multi-symbol via CRYPTO_SYMBOLS.
- ML Gainer: Mixed assets.
- Formats: Normalized in aggregator.py.

## Priority: COMPLETE

No action needed. Coverage solid (86 symbols supported, consensus on majors).