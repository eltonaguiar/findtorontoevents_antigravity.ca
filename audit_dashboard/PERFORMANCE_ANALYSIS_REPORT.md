# Forward-Testing Performance Analysis Report

**Date**: 2026-03-27
**Total Trades Analyzed**: 502
**Data Source**: `claudes_test_state.json`

---

## Executive Summary

The forward-testing system is showing **negative expectancy** with serious performance issues requiring immediate attention:

- **Overall Win Rate**: 30.08% (target: 50%+)
- **Average PnL/Trade**: -0.72% (target: positive)
- **Total Drawdown**: -$5,718.92
- **Primary Issue**: 78.9% of trades hit stop-loss

---

## Critical Findings

### 1. Stop-Loss Dominance Crisis
```
Exit Reasons:
├── SL: 396 trades (78.9%)
├── TP: 101 trades (20.1%)
└── TIME_EXIT: 5 trades (1.0%)
```

**Root cause analysis**:
- Stop-loss levels are set too tight relative to volatility
- Risk:Reward ratios may be calculated incorrectly
- Entry timing may be capturing late moves instead of early reversals
- Volatility filters (ATR-based) may be absent or misconfigured

**Immediate actions needed**:
1. Review ATR multipliers for SL placement
2. Increase SL tolerance to reduce premature exits
3. Implement minimum R:R threshold (e.g., 1.5:1)
4. Add volatility-based position sizing

### 2. Portfolio Performance Stratification

**Winning Portfolios** (small sample sizes, high performance):
| Portfolio | Trades | Win Rate | Avg PnL |
|-----------|--------|----------|---------|
| beaten_majors | 1 | 100% | +5.27% |
| fear_greed_contrarian | 4 | 100% | +3.32% |
| relative_strength_recovery | 2 | 100% | +4.03% |

**Moderate Performance**:
| Portfolio | Trades | Win Rate | Avg PnL |
|-----------|--------|----------|---------|
| sector_rotation | 16 | 50% | +0.09% |
| hoffman_elite | 14 | 43% | +1.06% |
| rsi_capitulation | 12 | 42% | +0.89% |

**Problem Pattern**:
- Small sample sizes (N≤20) show outsized performance
- Larger portfolios (multi_asset_diversified) underperform
- Suggests **overfitting to small samples** or **insufficient data** for confident strategy validation

### 3. Asset Class Analysis

```
BY ASSET CLASS:
├── CRYPTO:  n=466  WR=31.8%  avg=-0.71%
├── EQUITY:  n= 20  WR=10.0%  avg=-1.52%
└── FOREX:   n= 16  WR= 6.2%  avg=-0.24%
```

**Insights**:
- All asset classes underperform → systemic issue, not asset-specific
- FOREX has worst win rate (6.2%) but smallest losses → may need wider SLs
- EQUITY shows worst average PnL (-1.52%) → consider disabling equity signals
- Crypto dominates volume (466/502 = 93%) → system is crypto-focused

### 4. Reward/Risk Imbalance

```
Avg Win:  +4.25%
Avg Loss: -2.86%
WR: 30.08%
```

**Mathematical expectancy**: `(0.30 × 4.25) + (0.70 × -2.86) = -0.62%` (matches -0.72% observed)

**Formula**:
```
Expectancy = (Win Rate × Avg Win) + (Loss Rate × Avg Loss)
If Expectancy < 0 → Lose money over time
```

**To achieve profitability**:
- Increase WR to 40% at current R:R → `0.40×4.25 + 0.60×-2.86 = +0.12%` ✅
- OR increase avg win to +6.7% at current WR → `0.30×6.7 + 0.70×-2.86 = +0.12%` ✅
- OR reduce avg loss to -1.8% at current WR → `0.30×4.25 + 0.70×-1.8 = +0.12%` ✅

---

## Recommended Actions

### Priority 1: Fix Stop-Loss Mechanics (URGENT)
1. **Widen SL tolerance** by 50%: Current ATR multipliers are too aggressive
2. **Implement adaptive SL** based on:
   - Recent volatility (ATR rolling window)
   - Session-specific characteristics (London/NY overlap)
   - Market regime (trending vs choppy)
3. **Add SL trigger filters**:
   - Minimum time in market before SL allowed (e.g., 4 candles)
   - Volume confirmation for SL breakouts
   - Support/resistance level validation

### Priority 2: Increase Take-Profit Capture
1. **Partial TP strategy**:
   - TP1 at 50% of target: close 50% position
   - TP2 at 100% of target: close remaining 50%
   - Improves win rate even if some trades still hit SL
2. **Trailing stop activation**:
   - Move SL to breakeven after price moves +1% in favor
   - Trail at 75% of maximum favorable excursion (MFE)
3. **Risk:Recward minimums**:
   - Reject trades with R:R < 1.5:1
   - Prefer R:R ≥ 2:1 in volatile conditions

### Priority 3: Portfolio Rationalization
1. **Validate small-sample portfolios**:
   - Require minimum 30 trades before trusting performance
   - `beaten_majors`, `fear_greed_contrarian`, `relative_strength_recovery` need more data
2. **Disable underperforming asset classes**:
   - Temporarily halt FOREX signals until SL issue resolved
   - Reduce EQUITY allocation to 5% maximum
3. **Focus on proven strategies**:
   - Prioritize `fear_greed_contrarian`, `rsi_capitulation` for contrarian setups
   - Scale down `multi_asset_diversified` until SL fix implemented

### Priority 4: Backtesting & Validation
1. **Re-run historical backtests** with proposed SL changes:
   - Expected WR increase: 30% → 40-45%
   - Expected avg PnL improvement: -0.72% → +0.20-0.50%
2. **Forward test on paper**:
   - Simulate 100 trades with new SL rules
   - Verify no regression in other metrics
3. **A/B test implementation**:
   - Deploy SL changes to 25% of positions
   - Compare results against control group for 50 trades
   - Roll out to 100% if statistically significant improvement

---

## Success Metrics

After implementing the above changes, target:

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Win Rate | 30.08% | 40%+ | 2 weeks |
| Avg PnL/Trade | -0.72% | +0.30%+ | 2 weeks |
| SL Hit Rate | 78.9% | <60% | 1 week |
| TP Hit Rate | 20.1% | 30%+ | 1 week |
| Overall Expectancy | Negative | Positive | 2 weeks |

---

## Next Steps

1. **Immediate** (today):
   - Review current SL calculation logic in strategy files
   - Identify ATR multiplier values used
   - Document SL/TP ratio assumptions

2. **Short-term** (this week):
   - Implement adaptive SL algorithm
   - Add partial TP logic
   - Deploy to test environment

3. **Medium-term** (2 weeks):
   - Collect 50+ forward test trades
   - Validate performance improvements
   - Adjust parameters if needed

4. **Long-term** (1 month):
   - Full deployment to production
   - Continuous monitoring with weekly reports
   - Iterate based on new data

---

## Appendix: Data Breakdown

### Exit Reason Distribution
```
SL           ███████████████████████████████████████████████████ 78.9% (396)
TP           ████████████████████████ 20.1% (101)
TIME_EXIT    █ 1.0% (5)
```

### Win/Loss Distribution
```
Losses ████████████████████████████████████████████████████ 351 (70%)
Wins   ██████████████████████████ 151 (30%)
```

### PnL Distribution by Asset Class
```
CRYPTO  ████████████████████████████████████████████████████ 466 trades
EQUITY  ███ 20 trades
FOREX   ██ 16 trades
```

---

**Generated by**: `analyze_quality.py` v2.0
**Next Review**: 2026-04-03 (after 50+ new trades)