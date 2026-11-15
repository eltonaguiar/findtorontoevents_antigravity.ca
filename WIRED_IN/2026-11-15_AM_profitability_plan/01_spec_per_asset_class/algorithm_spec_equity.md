# Algorithm Specification — EQUITY (US)

**Asset Class:** EQUITY (US stocks / ETFs)
**Status:** RESEARCH SLOT 1 — NOT MONEY-READY
**sizing_allowed:** false

---

## 1. Algorithm Specification

### Strategies Tested

| Strategy | Type | Holding Period | Parameters |
|----------|------|----------------|------------|
| RSI(2) Mean Reversion | Mean reversion / swing | Short (3-5 days avg) | RSI(2)<10 & close>EMA(200) for LONG; TP=2×ATR, SL=1×ATR, max 10 bars |
| Dual MA Crossover | Trend following | Positional (30-60 days avg) | MA(50) crosses above MA(200) for entry; cross below for exit; max 60 bars |
| Bollinger Mean Reversion | Mean reversion / swing | Short (7-10 days avg) | Close < lower BB(20,2) + RSI(14)<30 for entry; close > mid BB for exit |

### Cost Model
- Commission: 1 bps per side
- Slippage: 1 bps per side
- Round-trip: 4 bps total

### Benchmark
- SPY total return (dividends adjusted)
- Must beat on risk-adjusted basis, not just raw return

### Walk-Forward Design
- 5 folds, expanding window
- 1 year train / 1 year test per fold
- Fixed start date, expanding train window
- Parameters fixed before testing (no optimization)

---

## 2. Backtest Results (2020-01-01 → 2025-12-31)

| Symbol | Strategy | Trades | WR % | PF | Net PnL % | Max DD % | Sharpe | DSR | PBO | Gates Passed |
|--------|----------|--------|------|-----|-----------|----------|--------|-----|-----|--------------|
| SPY | RSI2_MeanReversion | 48 | 2.08 | 0.002 | -161.28 | 155.67 | -12.96 | 0.000 | 0.999 | 2/7 |
| QQQ | RSI2_MeanReversion | 47 | 8.51 | 0.022 | -164.26 | 158.61 | -9.71 | 0.000 | 0.999 | 2/7 |
| IWM | RSI2_MeanReversion | 40 | 17.50 | 0.017 | -145.60 | 146.59 | -8.47 | 0.000 | 0.999 | 2/7 |
| VTI | RSI2_MeanReversion | 43 | 2.33 | 0.003 | -148.07 | 142.43 | -12.15 | 0.000 | 0.999 | 2/7 |
| DIA | RSI2_MeanReversion | 52 | 0.00 | 0.000 | -186.52 | 180.88 | -16.07 | 0.000 | 0.999 | 2/7 |
| EFA | RSI2_MeanReversion | 46 | 0.00 | 0.000 | -181.98 | 180.08 | -18.45 | 0.000 | 0.999 | 2/7 |
| EEM | RSI2_MeanReversion | 33 | 0.00 | 0.000 | -118.47 | 116.87 | -11.18 | 0.000 | 0.999 | 2/7 |
| SPY | DualMA_Crossover | 2 | 50.00 | 0.590 | -1.76 | 0.00 | -0.36 | 0.000 | 0.999 | 3/7 |
| QQQ | DualMA_Crossover | 2 | 100.00 | 999.00 | +22.29 | 0.00 | +3.25 | 0.000 | 0.999 | 4/7* |
| IWM | DualMA_Crossover | 4 | 50.00 | 0.349 | -15.71 | 13.79 | -0.93 | 0.000 | 0.999 | 3/7 |
| VTI | DualMA_Crossover | 2 | 50.00 | 0.515 | -2.91 | 0.00 | -0.45 | 0.000 | 0.999 | 3/7 |
| DIA | DualMA_Crossover | 3 | 66.67 | 0.826 | -1.62 | 0.00 | -0.15 | 0.000 | 0.999 | 2/7 |
| EFA | DualMA_Crossover | 3 | 100.00 | 999.00 | +7.32 | 0.00 | +5.47 | 0.000 | 0.999 | 4/7* |
| EEM | DualMA_Crossover | 4 | 50.00 | 0.229 | -18.38 | 10.14 | -1.24 | 0.000 | 0.999 | 3/7 |
| SPY | Bollinger_MeanReversion | 7 | 42.86 | 0.128 | -17.60 | 7.54 | -1.54 | 0.000 | 0.999 | 3/7 |
| QQQ | Bollinger_MeanReversion | 5 | 40.00 | 0.100 | -20.00 | 8.00 | -1.20 | 0.000 | 0.999 | 3/7 |
| IWM | Bollinger_MeanReversion | 8 | 25.00 | 0.084 | -22.86 | 11.36 | -1.94 | 0.000 | 0.999 | 2/7 |
| VTI | Bollinger_MeanReversion | 8 | 25.00 | 0.084 | -22.86 | 11.36 | -1.94 | 0.000 | 0.999 | 2/7 |
| DIA | Bollinger_MeanReversion | 5 | 20.00 | 0.050 | -25.00 | 10.00 | -2.00 | 0.000 | 0.999 | 2/7 |
| EFA | Bollinger_MeanReversion | 13 | 30.77 | 0.148 | -32.96 | 35.95 | -1.70 | 0.061 | 0.999 | 3/7 |
| EEM | Bollinger_MeanReversion | 10 | 20.00 | 0.103 | -27.90 | 30.22 | -1.92 | 0.000 | 0.999 | 2/7 |

\* QQQ and EFA DualMA show PF=999 on only 2-3 trades — statistical artifact, not tradable edge. DSR=0.000, PBO=0.999.

### Walk-Forward (Test Period Aggregated)

Best equity walk-forward result: SPY Bollinger Mean Reversion — avg PF 199.80 (artifact, gross_loss≈0), avg WR 20%, avg Sharpe -1.56, avg DD 0.46%. Not tradable.

---

## 3. Pick Justification

**No equity pick is justified for deployment.**

**Reasoning:**
1. **All equity strategies lost money after costs** (net PnL -1.6% to -186.5%).
2. **RSI(2) mean reversion** — previously famous (Connors, 2008-2020 era) — completely failed in 2020-2025 regime (WR 0-17%, PF ~0). The edge has decayed.
3. **Dual MA Crossover** — only 2-5 trades per symbol over 5+ years. PF=999 on 2 trades is noise. Not enough samples for statistical inference.
4. **DSR ≈ 0** for all equity strategies — no confidence any Sharpe > 0.
5. **PBO ≈ 0.999** — near-certain overfitting.
6. **Pre-registered SPY gate failed** (t=1.05, beat-SPY 45.53%, median excess -0.57%).

**Best (least bad) equity candidate:** QQQ DualMA Crossover — 4/7 gates passed (PF, WR, Sharpe, MaxDD) but only 2 trades, DSR=0, PBO=0.999. **Not deployable.**

---

## 4. Elimination Reason

- **RSI(2) Mean Reversion:** Eliminated — negative expectancy (-118% to -186%), WR 0-17%, Sharpe -8 to -18, DSR=0. Cost-dominated; regime change destroyed the edge.
- **Dual MA Crossover:** Eliminated — insufficient sample (2-5 trades per symbol over 5 years). Apparent PF=999 is statistical artifact on tiny sample. DSR=0, PBO=0.999.
- **Bollinger Mean Reversion:** Eliminated — negative expectancy (-17% to -33%), WR 20-43%, Sharpe -1.2 to -2.0. Not tradable.

---

## 5. Money-Ready Gate Result

**0/7 gates passed for all equity strategies.** Best was QQQ DualMA at 4/7 but fails DSR≥0.95, PBO≤0.10, and Trades≥50. Equity remains a **research slot only**, not a deployment vehicle.
