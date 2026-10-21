# Grokbot Findings: Nemotron Money Ready Strategy Evaluation

## Strategy Tested: Bond Yield Curve Slope (bond_yield_curve_slope)

### Test Overview
- **IS Period**: 2000-01-01 to 2015-12-31 (parameter selection)
- **OOS Period**: 2016-01-01 to 2026-10-20 (out-of-sample testing)
- **Initial Capital**: $10,000
- **Risk per Trade**: 2% of equity
- **Cost Assumption**: 5bp round trip (10bp for 2x cost test)
- **Timeframe**: Weekly signals with 1-week holding period

### Results Summary
| Metric | Value | Requirement | Status |
|--------|-------|-------------|--------|
| Number of Trades (n) | 1530 | ≥100 | ✅ PASS |
| Wins | 816 | - | - |
| Profit Factor (PF) | 1.115 | ≥1.5 | ❌ FAIL |
| PF 95% CI Lower Bound | 1.000 | ≥1.2 | ❌ FAIL |
| Win Rate (WR) | 53.3% | ≥50% | ✅ PASS |
| Max Drawdown (MDD) | 2.0% | ≤20% | ✅ PASS |
| Monte Carlo Percentile | 48.20% | ≥95 | ❌ FAIL |
| Deflated Sharpe Ratio (DSR) | 25.912 | >0.95 | ✅ PASS |
| PF at 2x Costs | 0.003 | ≥1.3 | ❌ FAIL |
| Top Symbol Share | 100.0% | ≤30% | ❌ FAIL |
| PF after Top Symbol Removal | ~1.115 | ≥1.3 | ❌ FAIL |

### Final Label: FAILED
**Primary Failure Gates**: 
1. Profit Factor too low (1.115 < 1.5)
2. PF Confidence Interval too low (1.000 < 1.2)
3. Monte Carlo percentile insufficient (48.20 < 95)
4. PF at 2x costs ineffective (0.003 < 1.3)
5. Concentration risk - all trades in one symbol (100% > 30%)
6. Strategy edge not robust after removing top symbol

### Key Insights
- The strategy generates frequent trades (1530 over ~10.75 years) but with marginal edge
- Win rate is acceptable at 53.3%, but average win size is too small relative to losses
- Strategy shows no significant edge over random signals (MC percentile 48.20%)
- Transaction costs completely eliminate any potential profitability
- Strategy lacks diversification - all trades essentially in TLT/SHY ratio
- Not suitable for live trading in current form

### Recommendation
Do not proceed to paper trading. Strategy requires significant refinement or abandonment.
Consider:
1. Adding filters to reduce trade frequency and increase edge
2. Incorporating volatility regime filters
3. Adding macroeconomic indicators (Fed policy, inflation data)
4. Testing different Treasury term structures (e.g., 10Y-2Y instead of 20Y-1Y)
5. Examining walk-forward performance to identify stable regimes

### Next Steps
Proceed to test remaining strategies in the idea list:
1. CTA Cross-Asset TS MOM (cta_cross_asset_tsmom)
2. TIPS Breakeven Inflation (bond_tips_breakeven) 
3. Equity Sector Rotation (equity_sector_rotation)
4. Commodity Momentum Term Structure (commodity_momentum_term)
