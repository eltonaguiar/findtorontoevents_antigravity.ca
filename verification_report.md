# REDDIT TRADER VERIFICATION REPORT
## Deep-Dive Analysis of Top 3 Reddit Algo Traders

**Date:** February 18, 2026  
**Analyst:** Meta-Agent Coordinator  
**Status:** VERIFICATION IN PROGRESS

---

## 1. u/DevFuturesTrader (r/Daytrading)

### CLAIMS SUMMARY
| Metric | Claimed Value |
|--------|---------------|
| Gross Profit YTD | $138,450 |
| Net Profit (Post-tax) | $103,750 |
| Win Rate | ~52% |
| Profit Factor | 2.15 |
| Max Drawdown | -4.5% |
| Instrument | ES/NQ Futures |
| Strategy | Mean Reversion via Volumetric Liquidity |

### VERIFICATION CHECKLIST

#### ✅ CREDIBLE INDICATORS
1. **Technical Depth**: Detailed description of volumetric analysis, anchored VWAP, CVD divergence
2. **Developer Background**: Acknowledges being a developer - explains the edge
3. **Realistic Win Rate**: 52% is plausible for mean reversion (not inflated 80%+ claims)
4. **Specific Methodology**: 
   - 2SD VWAP bands
   - CVD divergence detection
   - LVN/HVN volume profile zones
   - 5-min candle close trigger
5. **Risk Management**: Hard stops beyond absorption wicks, defined targets
6. **Tax Awareness**: Mentions Section 1256 tax treatment (sophisticated knowledge)
7. **Wednesday Filter**: Specific day-of-week optimization (detail-oriented)

#### ⚠️ RED FLAGS / UNVERIFIED
1. **No Broker Screenshots**: No actual P&L screenshots provided in post
2. **No Trade History**: No timestamped trade log
3. **YTD Only**: Claims only cover year-to-date, not multi-year
4. **Sample Size**: Unknown number of trades (52% win rate needs sufficient sample)
5. **Reproducibility**: Strategy requires tick data and custom volume profile tools

#### 🔍 CROSS-REFERENCE FINDINGS
- **Strategy Type**: Standard mean reversion with volume profile overlay
- **Similar To**: Traditional VWAP reversion + order flow concepts
- **Edge Claim**: Speed of calculation via custom script
- **Plausibility**: HIGH - Strategy logic is sound and well-documented

#### 📊 VERIFICATION SCORE: 7.5/10
**Verdict:** CREDIBLE but unverified. The trader demonstrates deep market microstructure knowledge consistent with institutional background. Strategy description is detailed enough to implement. Lack of broker statements is the main gap.

---

## 2. u/heyredditaddict (r/thetagang)

### CLAIMS SUMMARY
| Metric | Claimed Value | Benchmark |
|--------|---------------|-----------|
| Returns | 31.7% | SPY 19.4% |
| Max Drawdown | 3.87% | SPY 16.68% |
| Sharpe Ratio | 2.93 | SPY 0.89 |
| Strategy | Theta selling on SPY | - |
| Track Record | 1 year live | - |

### VERIFICATION CHECKLIST

#### ✅ CREDIBLE INDICATORS
1. **Benchmark Comparison**: Provides direct comparison to SPY (professional approach)
2. **Risk Metrics**: Includes Sharpe ratio and max drawdown
3. **Specific Strategy**: OTM put/call selling (90% of trades) + IV crush plays
4. **Real Money Claim**: Explicitly states "live trades with real money"
5. **Risk-Adjusted Returns**: Lower drawdown than benchmark is realistic for theta
6. **Platform Activity**: Active on Reddit with detailed post history

#### ⚠️ RED FLAGS / UNVERIFIED
1. **No Screenshots**: No broker statements or P&L screenshots in post
2. **1 Year Only**: Single year track record (2023 was favorable for theta)
3. **No Trade Count**: Unknown number of trades/position sizing
4. **Selection Bias**: Posted after successful year (survivorship bias possible)
5. **IV Crush Plays**: "Occasional far OTM IV crush plays" could be high risk

#### 🔍 CROSS-REFERENCE FINDINGS
- **2023 Context**: 2023 was excellent for theta strategies (low volatility, upward drift)
- **Wheel Strategy**: Same user has 3-year wheel strategy history (61% in 2023)
- **Consistency**: Different strategy (wheel vs theta algo) but consistent profitability
- **Similar Strategies**: Tastytrade research supports short volatility edge

#### 📊 VERIFICATION SCORE: 7/10
**Verdict:** CREDIBLE with caveats. The benchmark comparison and risk metrics suggest sophistication. However, 2023 was an unusually good year for short vol strategies. Need 2022 and 2024 data to verify robustness.

---

## 3. u/No-Instruction-1234 (r/algotrading)

### CLAIMS SUMMARY
| Metric | Claimed Value |
|--------|---------------|
| 2025 Returns | 39% |
| Cumulative Return (2022-2025) | 104% |
| Max Drawdown | 6.65% |
| AUM Growth | $12K → $1.5M |
| Pairs Traded | XAUUSD, USDJPY only |
| Risk-Reward | 2:1 |

### VERIFICATION CHECKLIST

#### ✅ CREDIBLE INDICATORS
1. **Multi-Year Track Record**: 3+ years of claims (2022-2025)
2. **Evolution Story**: Transparent about abandoning failed approaches
3. **Philosophical Consistency**: References Taleb/Antifragile (sophisticated)
4. **Focus**: Reduced from 32 pairs to 2 (specialization)
5. **Risk Management**: 2:1 RR is conservative and sustainable
6. **Drawdown**: 6.65% is realistic and controlled
7. **AUM Growth**: $12K to $1.5M is achievable with compounding

#### ⚠️ RED FLAGS / UNVERIFIED
1. **No Verification**: No MyFXBook, broker statements, or screenshots
2. **Exceptional Returns**: 39% annual is high for forex (not impossible but notable)
3. **AUM Claim**: $1.5M is a specific claim that should be verifiable
4. **Survivorship**: Posted in 2025 after successful period
5. **Strategy Vagueness**: "Breakout strategy" is generic - lacks implementation details

#### 🔍 CROSS-REFERENCE FINDINGS
- **2022-2024 Period**: Includes 2022 (difficult year) in track record
- **Pair Selection**: XAUUSD and USDJPY are liquid, trending markets
- **Compounding Math**: $12K → $1.5M in ~4 years requires ~120% annual return
  - Claimed: 104% cumulative over 3 years
  - Gap: $12K at 104% cumulative = ~$24K, not $1.5M
  - **INCONSISTENCY DETECTED**: AUM claim doesn't match return claim

#### 📊 VERIFICATION SCORE: 5/10
**Verdict:** QUESTIONABLE. The math doesn't add up - 104% cumulative return on $12K cannot produce $1.5M. Either:
1. Additional deposits were made (not mentioned)
2. Leverage was used extremely aggressively
3. Returns are overstated
4. Timeline is different than stated

---

## CROSS-TRADER ANALYSIS

### Common Patterns
| Aspect | u/DevFuturesTrader | u/heyredditaddict | u/No-Instruction-1234 |
|--------|-------------------|-------------------|----------------------|
| Track Record | YTD only | 1 year | 3+ years (claimed) |
| Verification | None | None | None |
| Screenshots | No | No | No |
| Benchmark | None | SPY | None |
| Risk Metrics | Detailed | Detailed | Limited |
| Strategy Detail | High | Medium | Low |
| Plausibility | High | Medium | Low (math gap) |

### RED FLAGS SUMMARY
1. **No broker statements** from any trader
2. **No timestamped trade logs**
3. **No MyFXBook/verified tracking**
4. **Math inconsistency** in u/No-Instruction-1234's AUM claim
5. **Survivorship bias** - all posted after successful periods

### CREDIBLE ELEMENTS
1. **Technical sophistication** in descriptions
2. **Risk awareness** (drawdowns, Sharpe ratios)
3. **Strategy evolution** stories (not "always profitable")
4. **Specific parameters** (not vague "secret sauce")
5. **Benchmark comparisons** (u/heyredditaddict)

---

## RECOMMENDATIONS

### For Further Verification
1. **Request broker statements** with redacted account numbers
2. **MyFXBook/FX Blue verification** for forex traders
3. **Trade log analysis** for entry/exit timing verification
4. **Out-of-sample testing** of claimed strategies
5. **Cross-reference** with market conditions during claimed periods

### Strategy Implementation Priority
1. **u/DevFuturesTrader** - Highest priority (most detailed, plausible)
2. **u/heyredditaddict** - Medium priority (good benchmark data)
3. **u/No-Instruction-1234** - Low priority (math inconsistency, vague strategy)

---

## CONCLUSION

**Most Credible:** u/DevFuturesTrader  
**Best Documented:** u/heyredditaddict  
**Most Questionable:** u/No-Instruction-1234

**Overall Assessment:** These traders demonstrate market knowledge consistent with profitability, but **none provide sufficient verification** to confirm their claims. The strategies described are plausible and implementable, but live performance remains unverified.

**Recommendation:** Implement strategies in paper trading before risking capital.

---

*Report Generated: February 18, 2026*  
*Status: AWAITING ADDITIONAL VERIFICATION DATA*
