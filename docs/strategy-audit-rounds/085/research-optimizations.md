# Round 085 — Research & Optimizations for vix_term_structure_signal

**Date:** 2026-05-08T16:07:18.309267

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
