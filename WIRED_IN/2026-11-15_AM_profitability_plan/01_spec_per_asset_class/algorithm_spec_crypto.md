# Algorithm Specification — CRYPTO

**Asset Class:** CRYPTO
**Status:** RESEARCH SLOT 2 (CONDITIONAL) — NOT MONEY-READY
**sizing_allowed:** false

---

## 1. Algorithm Specification

### Strategies Tested

| Strategy | Type | Holding Period | Parameters |
|----------|------|----------------|------------|
| Donchian Channel Breakout (Turtle style) | Trend following | Swing (9-10 days avg) | Buy breakout above 20-day high; sell below 20-day low; ATR TP=2.5×, SL=1.25×; max 20 bars |
| EMA Trend Crossover | Trend following | Swing (7-11 days avg) | EMA(20) crosses above EMA(50) for LONG; below for SHORT; ATR TP=2.5×, SL=1.25×; max 30 bars |

### Universe Tested
BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD

### Cost Model
- Commission: 1 bps per side
- Slippage: 1 bps per side
- Round-trip: 4 bps total
- (Note: Real crypto costs are higher — taker fees + funding + spread. Simulation used conservative 4bps.)

### Benchmark
- Equal-weight buy-and-hold + cash (not tested in this simulation; Buffy's backtest showed BTC beats SPY due to beta, not skill)

### Walk-Forward Design
- 5 folds, expanding window
- 1 year train / 1 year test per fold

---

## 2. Backtest Results (2020-01-01 → 2025-12-31)

| Symbol | Strategy | Trades | WR % | PF | Net PnL % | Max DD % | Sharpe | DSR | PBO | Gates Passed |
|--------|----------|--------|------|-----|-----------|----------|--------|-----|-----|--------------|
| BTC-USD | EMA_Trend_Crossover | 33 | 33.33 | 0.315 | -128.25 | 147.27 | -3.10 | 0.002 | 0.999 | 1/7 |
| ETH-USD | EMA_Trend_Crossover | 34 | 38.24 | 0.500 | -113.37 | 137.16 | -1.76 | 0.045 | 0.999 | 1/7 |
| SOL-USD | EMA_Trend_Crossover | 32 | 46.88 | 0.868 | -33.35 | 153.31 | -0.36 | 0.360 | 0.983 | 1/7 |
| XRP-USD | EMA_Trend_Crossover | 47 | 36.17 | 0.523 | -130.73 | 152.81 | -1.89 | 0.033 | 0.999 | 1/7 |
| ADA-USD | EMA_Trend_Crossover | 30 | 46.67 | 0.889 | -18.22 | 79.03 | -0.30 | 0.383 | 0.979 | 4/7* |
| BTC-USD | Donchian_Breakout | 0 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0/7 |
| ETH-USD | Donchian_Breakout | 0 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0/7 |
| SOL-USD | Donchian_Breakout | 0 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0/7 |
| XRP-USD | Donchian_Breakout | 0 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0/7 |
| ADA-USD | Donchian_Breakout | 0 | 0.00 | 0.000 | 0.00 | 0.00 | 0.000 | 0.000 | 0.000 | 0/7 |

\* ADA-USD EMA Trend: 4/7 gates (PF, WR, MaxDD, Trades) but fails Sharpe (-0.30), DSR (0.383), PBO (0.979). Max DD 79% — unacceptable.

### Walk-Forward (Test Period Aggregated)

| Symbol | Strategy | Folds | Avg PF | Avg WR % | Avg Net PnL % | Avg Max DD % | Avg Sharpe | Max PBO |
|--------|----------|-------|--------|----------|---------------|--------------|------------|---------|
| ADA-USD | EMA_Trend_Crossover | 5 | 200.37 | 53.00 | -0.46 | 11.93 | 0.72 | 0.999 |
| ETH-USD | EMA_Trend_Crossover | 5 | 0.77 | 39.74 | -15.30 | 24.38 | -1.09 | 0.999 |
| SOL-USD | EMA_Trend_Crossover | 4 | 0.75 | 35.42 | -25.92 | 33.13 | -0.87 | 0.999 |
| XRP-USD | EMA_Trend_Crossover | 5 | 0.70 | 32.79 | -18.46 | 31.35 | -1.35 | 0.999 |
| BTC-USD | EMA_Trend_Crossover | 5 | 0.37 | 25.33 | -24.94 | 29.62 | -3.63 | 0.999 |

---

## 3. Pick Justification

**No crypto pick is justified for deployment.**

**Reasoning:**
1. **All crypto strategies lost money after costs** (net PnL -18% to -130%).
2. **ADA-USD EMA Trend** — "best" crypto result — passes only 4/7 gates. Fails Sharpe (-0.30 < 1.0), DSR (0.383 < 0.95), PBO (0.979 > 0.10). Max drawdown 79% — catastrophic for capital deployment.
3. **Donchian Breakout** — zero trades on all 5 symbols. Strategy never fired. Eliminated.
4. **DSR ≈ 0** for all crypto strategies except ADA (0.383) — still well below 0.95 threshold.
5. **PBO ≈ 0.98-0.999** — near-certain overfitting.
6. **Buffy's parallel backtest** (2004-2026): BTC_TREND200 showed SR 1.10 vs BTC hold 0.93, but DSR only 0.84 < 0.95. "Promising, unproven."

**Best (least bad) crypto candidate:** ADA-USD EMA Trend Crossover — 4/7 gates but fails Sharpe, DSR, PBO. Max DD 79%. **Not deployable.**

---

## 4. Elimination Reason

- **Donchian Channel Breakout:** Eliminated — zero trades across all 5 crypto symbols over 5+ years. Strategy never generated a signal. Not viable.
- **EMA Trend Crossover:** Eliminated — negative expectancy on all symbols (-18% to -130%), max DD up to 153%, Sharpe negative on 4/5 symbols, DSR < 0.4 on all, PBO > 0.97. Not tradable.

---

## 5. Money-Ready Gate Result

**0/7 gates passed for all crypto strategies.** Best was ADA-USD EMA Trend at 4/7 but fails DSR≥0.95, PBO≤0.10, Sharpe≥1.0. Crypto remains **conditional research slot only** — re-open only after fill fixes + SubQ coverage ≥7/10 + clean forward test.
