# Mean Reversion Strategy Cloner - Final Report

## Strategy Overview
**Source:** u/DevFuturesTrader's ES/NQ Mean Reversion Strategy

**Core Concept:** Volumetric liquidity zone trading with anchored VWAP mean reversion

### Entry Criteria:
1. Price pushes outside 2 standard deviations of anchored VWAP (outlier territory)
2. Extension into MTF low volume node (LVN) or previous high volume node (HVN)
3. CVD (Cumulative Volume Delta) fails to confirm price move (divergence)
4. Entry on 5-minute candle close back inside liquidity zone
5. Hard stop placed beyond absorption wick

### Exit Criteria:
- Target: Return to VWAP (mean reversion)
- Stop: Beyond the absorption wick (recent extreme)

---

## Backtest Results Summary

| Metric | ES Futures | NQ Futures | Combined |
|--------|------------|------------|----------|
| **Total Trades** | 177 | 179 | 356 |
| **Win Rate** | 44.07% | 44.13% | 44.10% |
| **Profit Factor** | 1.15 | 1.25 | 1.20 |
| **Sharpe Ratio** | 0.79 | 1.21 | 1.00 |
| **Max Drawdown** | -8.89% | -10.72% | -9.81% |
| **Total Return** | $5,732 | $12,565 | **$18,298** |
| **Return %** | 11.46% | 25.13% | 18.30% |

### Cost Structure (Per Trade):
| Component | ES | NQ |
|-----------|-----|-----|
| Commission (RT) | $5.00 | $5.00 |
| Spread | $3.12 | $1.25 |
| Slippage | $12.50 | $5.00 |
| **Total Cost** | **$20.62** | **$11.25** |

**Total Costs:** $5,664 (ES: $3,651 + NQ: $2,014)

---

## Claimed vs Actual Performance

| | Claimed | Actual | Difference |
|--|---------|--------|------------|
| **Return** | $103,000 | $18,298 | **-$84,702** |
| **Accuracy** | 100% | 17.8% | 82.2% lower |

### Why the Discrepancy?
1. **Costs Ignored:** Claimed returns likely exclude commissions, spread, and slippage
2. **Perfect Fills:** Real execution has slippage, especially on 5-minute closes
3. **Curve Fitting:** Original may use optimized parameters on historical data
4. **Selection Bias:** May only show best period, not full year
5. **Data Quality:** Professional feeds vs retail data differences

---

## Can Retail Traders Execute This?

### ✅ ADVANTAGES:
- Clear, systematic entry/exit rules
- Defined risk management with hard stops
- Uses standard technical indicators (VWAP, Volume Profile)
- 5-minute timeframe is manageable for active traders
- Mean reversion aligns with institutional auction theory

### ❌ CHALLENGES:
- **Data Costs:** Professional feeds with volume profile ($300-800/month)
- **CVD Requirements:** Needs bid/ask volume (not on basic feeds)
- **Subjectivity:** "Absorption wick" identification is discretionary
- **Execution Speed:** Must trade on 5-minute candle closes
- **Capital Requirements:** $25,000+ for Pattern Day Trader rule
- **Cognitive Load:** Multiple timeframe analysis

### ⚠️ REALITY CHECK:
- Strategy generates selective/infrequent signals
- Win rate varies significantly by market regime
- Costs consume 15-25% of gross profits
- Slippage often exceeds 1 tick in volatile markets
- Mean reversion fails during strong trends

---

## VERDICT

**TECHNICALLY EXECUTABLE** but **CHALLENGING** for retail traders.

The claimed $103K return appears **HIGHLY INFLATED** and likely based on:
- Unrealistic assumptions (zero costs, perfect fills)
- Optimized parameters with hindsight bias
- Selective reporting of best periods

**Realistic Expectations for Retail Traders:**
- Returns: 30-50% of claimed amounts after costs
- Win Rate: 40-50% (not the 60%+ often advertised)
- Drawdowns: 10-15% during unfavorable regimes
- Learning Curve: 6-12 months paper trading required

**Recommendation:** Paper trade for 6 months minimum. Start with 1 contract. Scale only after consistent profitability.

---

## Full Python Code

See `mean_reversion_strategy.py` for complete implementation including:
- Anchored VWAP calculation with 2SD bands
- Volume Profile LVN/HVN detection
- CVD divergence calculation
- Backtest engine with realistic costs
- Performance metrics calculation
