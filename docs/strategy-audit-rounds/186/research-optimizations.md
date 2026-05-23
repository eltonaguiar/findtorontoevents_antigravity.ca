# Round 186 — Research & Optimizations for put_call_ratio_contrarian

**Date:** 2026-05-08T16:07:20.229345

**Current Performance Issues:**
- Low Sharpe in sideways regimes
- High turnover during high-vol periods

**Proposed Optimizations:**
1. Add regime filter (ATR percentile > 70)
2. Reduce position size by 30% when VIX > 25
3. Introduce time-based exit (max 5 days for equity)

**Hedge Fund Comparison:**
Similar to DE Shaw statistical arbitrage with added macro overlay.

**Expected Impact:**
- +0.4 Sharpe
- -15% max drawdown
