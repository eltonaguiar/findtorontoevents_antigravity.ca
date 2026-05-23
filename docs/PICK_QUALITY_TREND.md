# Pick Quality Trend Analysis

*Generated: 2026-03-16 | Diagnostic report -- read-only analysis*

---

## Analysis 1: Alpha Engine Pick Quality Over Time

**Total closed picks: 281**

| Quartile | Picks | Win Rate | Avg PnL % | Profit Factor | Avg ML Score | Date Range |
|----------|-------|----------|-----------|---------------|--------------|------------|
| Q1 (oldest) | 70 | 40.0% | 0.0034 | 1.216 | 0.772 | 03/11 - 03/14 |
| Q2 | 70 | 48.6% | 0.0133 | 1.497 | 0.647 | 03/14 - 03/16 |
| Q3 | 70 | 44.3% | -0.0142 | 0.750 | 0.543 | 03/16 - 03/16 |
| Q4 (newest) | 71 | 50.7% | 0.0524 | 2.270 | 0.732 | 03/16 - 03/16 |

**Win Rate Trend:** IMPROVING (Q1=40.0% -> Q4=50.7%)
**Avg PnL Trend:** IMPROVING (Q1=0.0034 -> Q4=0.0524)

---

## Analysis 2: Consensus Pick Quality Over Time

**Total closed consensus picks: 200**

| Quartile | Picks | Win Rate | Avg PnL % | Avg Agreement | Date Range |
|----------|-------|----------|-----------|---------------|------------|
| Q1 (oldest) | 50 | 38.0% | 0.05% | 2.2 | 03/14 - 03/15 |
| Q2 | 50 | 48.0% | 0.20% | 2.4 | 03/15 - 03/15 |
| Q3 | 50 | 66.0% | 1.06% | 2.8 | 03/15 - 03/16 |
| Q4 (newest) | 50 | 86.0% | 2.26% | 2.7 | 03/16 - 03/16 |

**Consensus Trend:** IMPROVING (Q1=38.0% -> Q4=86.0%, PnL: 0.05% -> 2.26%)

---

## Analysis 3: Claude Gainer Pick Quality Over Time

**Total Claude Gainer picks: 39**

| Half | Picks | Win Rate | Avg PnL % | TP2 Hit Rate | Avg Pump Prob |
|------|-------|----------|-----------|--------------|---------------|
| First Half | 19 | 57.9% | 4.09% | 42.1% | 0.396 |
| Second Half | 20 | 65.0% | 6.37% | 40.0% | 0.385 |

### Re-picked Symbols Performance

| Symbol | Times Picked | Avg PnL % | First Pick PnL | Last Pick PnL | Improving? |
|--------|-------------|-----------|----------------|---------------|------------|
| H | 2 | -8.15% | -5.13% | -11.17% | No |
| INJ | 2 | -5.58% | -5.87% | -5.30% | Yes |
| VVV | 2 | 3.22% | -7.20% | 13.63% | Yes |
| RIVER | 2 | 36.95% | 14.73% | 59.16% | Yes |
| TAO | 2 | 13.52% | 11.27% | 15.77% | Yes |
| ZEC | 2 | -6.00% | -5.25% | -6.74% | No |
| FET | 2 | 1.71% | -5.53% | 8.95% | Yes |
| RENDER | 2 | -1.81% | -6.38% | 2.75% | Yes |

**Claude Gainer Trend:** IMPROVING (WR: 58% -> 65%, PnL: 4.1% -> 6.4%)

---

## Analysis 4: Per-Strategy Improvement Trends

Strategies with 5+ picks, comparing first 3 vs last 3 picks:

| Strategy | Total | First 3 WR | Last 3 WR | First 3 Avg PnL | Last 3 Avg PnL | Trend |
|----------|-------|------------|-----------|-----------------|----------------|-------|
| fractal_sr_bounce | 22 | 67% | 33% | 0.0028 | -0.0020 | v Degrading |
| seasonal_factor_rotation | 11 | 0% | 0% | -0.0100 | -0.0160 | ~ Flat |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 10 | 100% | 100% | 0.1046 | 0.0520 | v Degrading |
| ml_enhanced_BTCUSDT_15m_D_ensemble_stack | 10 | 0% | 0% | -0.1030 | -0.0945 | ~ Flat |
| ml_enhanced_ADAUSDT_15m_D_ensemble_stack | 10 | 0% | 0% | -0.1518 | -0.0798 | ^ Improving |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 8 | 100% | 100% | 0.3382 | 0.0505 | v Degrading |
| widened_tp_momentum_carry | 7 | 100% | 0% | 0.0600 | -0.0272 | v Degrading |
| hurst_regime_adaptive | 6 | 33% | 0% | -0.0088 | -0.0398 | v Degrading |
| adaptive_vr_confluence | 6 | 33% | 0% | 0.0018 | -0.0355 | v Degrading |
| community_london_breakout_v2_forex | 6 | 0% | 0% | -0.0091 | -0.0094 | ~ Flat |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 5 | 100% | 100% | 0.4049 | 0.4042 | ~ Flat |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 5 | 100% | 100% | 0.2296 | 0.1105 | v Degrading |

**Improving strategies (1):**
  - ml_enhanced_ADAUSDT_15m_D_ensemble_stack
**Degrading strategies (7):**
  - fractal_sr_bounce
  - ml_enhanced_BNBUSDT_15m_B_lightgbm
  - ml_enhanced_RENDERUSDT_1h_D_ensemble_stack
  - widened_tp_momentum_carry
  - hurst_regime_adaptive
  - adaptive_vr_confluence
  - ml_enhanced_RENDERUSDT_4h_D_ensemble_stack

---

## Analysis 5: ML Score Calibration Check

| ML Score Range | Picks | Wins | Win Rate | Avg PnL % | Calibration |
|----------------|-------|------|----------|-----------|-------------|
| 0.50-0.60 | 55 | 38 | 69.1% | 0.0579 | baseline |
| 0.60-0.70 | 66 | 21 | 31.8% | -0.0053 | INVERTED |
| 0.70-0.80 | 59 | 24 | 40.7% | -0.0055 | OK |
| 0.80-0.90 | 50 | 28 | 56.0% | 0.0579 | OK |
| 0.90-1.00 | 13 | 11 | 84.6% | 0.1220 | OK |

**ML Score Calibration:** MISCALIBRATED -- higher ml_score does NOT consistently predict better outcomes.

Picks with ML score: 281 | Without: 0

---

## Summary Verdict

| System | Verdict | Key Evidence |
|--------|---------|--------------|
| Alpha Engine | IMPROVING | WR: 40% -> 51%, PnL: 0.0034 -> 0.0524 |
| Consensus Aggregator | IMPROVING | WR: 38% -> 86%, PnL: 0.05% -> 2.26% |
| Claude Gainer | IMPROVING | WR: 58% -> 65%, PnL: 4.1% -> 6.4% |
| Per-Strategy | Mixed | 1 improving, 7 degrading |
| ML Score | MISCALIBRATED | See calibration table above |

### Interpretation Notes

- **Quartile analysis** divides all picks into 4 equal time-ordered groups to detect trends.
- **Profit Factor** = gross profit / gross loss. Values > 1.0 indicate net profitability.
- **ML Calibration** checks if the model's confidence scores actually predict outcomes.
- **Per-strategy trends** compare the first 3 and last 3 picks to detect learning or decay.
- A strategy is marked 'improving' if its recent picks have higher win rate OR higher avg PnL.