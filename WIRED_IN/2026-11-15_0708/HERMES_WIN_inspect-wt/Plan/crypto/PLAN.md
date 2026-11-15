# PLAN — Crypto (BTC, ETH, major alts)

**Status:** Conditional, blocked on data/fill fixes. **Gap filled:** F9 (breakout+carry shuffle FAIL), F11 (token unlock, N too small), F30 (transformer, insufficient data).

## Hypothesis
After fixing the fill/data bugs that caused the shuffle-control failure (F9), a **cross-sectional carry + trend** strategy (long top-quartile funding-positive alts, short bottom-quartile funding-negative, 7-day trend filter, weekly rebalance) can beat BTC buy-and-hold after realistic costs on forward data.

## Gap it fills
- F9 died on **shuffle control** (a pipeline leak — best failure). The plan mandates a leakage audit first.
- F30 (transformer) failed on insufficient N — this plan uses weekly (not daily) to grow trade count.
- Existing crypto work is **directional**; cross-sectional is untested.

## Method
- **Signal:** rank alts by 7-day funding rate + 30-day price trend; long top quartile, short bottom quartile
- **Universe:** top 20 alts by market cap, liquidity ≥ $5M/day
- **Timeframe:** 8h bars, 2021-01-01 → 2026-11-15
- **Rebalance:** Weekly (Thursdays), equal risk-weighted
- **Cost model:** taker fee 0.10%, maker 0.02%, slippage 0.05%, funding paid/received at actual rate
- **Benchmark:** BTC buy-and-hold total return

## Proof tests it will pass (§6)
1. ✅ Temporal: train 2021-2024, test 2025-2026 (locked)
2. ✅ Walk-forward: 4-quarter rolling, report efficiency + param stability
3. ✅ Multiple testing: state total configs (1 — this single configuration)
4. ✅ Monte Carlo: block bootstrap (arch), % positive paths + 5th percentile
5. ✅ Friction: full funding/taker/maker/slippage model
6. ✅ Significance: bootstrap CI for excess return vs BTC-hold, t-stat, p-values
7. ✅ Regime: bull/bear/sideways (crypto regimes), high/low vol
8. ✅ Shuffle control: permuted prices must NOT reproduce (this is the gate F9 failed)
9. ✅ Forward: 6-month paper-trading protocol
10. ✅ Reproducibility: fixed seed, versioned data, documented formulas

## Expected outcome
If the shuffle control still fails after the leak audit, the crypto class is dead. If it passes but friction kills it, the honest verdict is "edge exists but untradeable at retail cost". Do not re-test with tweaked parameters.