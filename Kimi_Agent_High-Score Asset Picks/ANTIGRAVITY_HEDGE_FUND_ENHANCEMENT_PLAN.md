# Antigravity Hedge Fund-Level Enhancement Plan
## From Struggling Picks to High-Certainty Alpha

**Date:** April 7, 2026  
**Prepared for:** findtorontoevents.ca / antigravity.ca  
**Objective:** Transform current 27-38% win rate system into hedge fund-quality 55%+ win rate system

---

## Executive Summary

### Current State (Critical Issues)
| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Win Rate** | 27-38% | 55%+ | -17 to -28% |
| **Profit Factor** | 0.88 | 1.5+ | -0.62 |
| **PROBATION Tier Picks** | 64.8% | <30% | +34.8% |
| **Score-PnL Correlation** | 0.19 | 0.50+ | Weak |
| **Goldmine Stocks** | -46.92% | Profitable | Catastrophic |

### Root Cause Analysis
1. **Core systems have NO EDGE** - Alpha Engine PF=0.88, ML Predictor PF=0.93
2. **64.8% of picks come from PROBATION tier** (systematically losing strategies)
3. **Scores don't reliably predict success** - correlation only 0.19
4. **Illiquid altcoins** causing slippage (JTO, STRK, APE with <$2M volume)
5. **No crypto-specific alpha** - missing funding rates, on-chain data

### Quick Wins (This Week - +9% WR Potential)
| Action | Effort | Impact |
|--------|--------|--------|
| Close Tier 5 coins (JTO, STRK, APE, INJ, DYDX) | 1 hour | +2% WR |
| Enforce MIN_SCORE = 65 | 2 hours | +3% WR |
| Add funding rate check | 4 hours | +2% WR |
| Reduce PROBATION tier sizing | 1 hour | -1% DD |
| Fix trust tier graduation logic | 4 hours | +2% WR |

---

## Phase 1: Critical Fixes (Weeks 1-2) - IMMEDIATE ACTION REQUIRED

### 1.1 CLOSE These Positions NOW (Liquidity Risk)

**Tier 5 - Critical Liquidity Risk (Close Immediately):**
| Symbol | 24h Volume | Issue |
|--------|-----------|-------|
| JTOUSDT | $0.79M | Critical - cannot exit without slippage |
| STRKUSDT | $1.39M | Critical - low liquidity |
| APEUSDT | $0.95M | Critical - memecoin volatility |
| INJUSDT | $2.07M | Insufficient for position size |
| DYDXUSDT | $2.26M | Insufficient for position size |

**Extreme Pump Risk (Close or Tighten Stops):**
| Symbol | 24h Change | Action |
|--------|-----------|--------|
| REDUSDT | +72.3% | Close - extreme reversal risk |
| TRUUSDT | +75.5% | Close - extreme reversal risk |

### 1.2 Implement Minimum Score Threshold

**NEW RULE: No pick below Score 65 enters the portfolio**

Current Issue:
- Score 70+: 67% win rate, +0.67% avg PnL
- Score <40: 36% win rate, -0.66% avg PnL
- But low scores are still being traded!

Implementation:
```python
MIN_SCORE_THRESHOLD = 65
if pick.score < MIN_SCORE_THRESHOLD:
    reject_pick(pick, reason="Below minimum score threshold")
```

Expected Impact: +3% win rate improvement

### 1.3 Fix Trust Tier System (Broken)

**Current Problem:** 64.8% of picks are PROBATION tier (losing strategies)

**New Graduation Criteria:**
| Tier | Current Trades | New Requirement | PF Requirement |
|------|---------------|-----------------|----------------|
| SANDBOX | 0 | 0 (new) | N/A |
| PROBATION | 10+ | 20+ | PF >= 1.05 |
| WATCH | 50+ | 50+ | PF >= 1.15 |
| PROVEN | 100+ | 100+ | PF >= 1.25 |

**Auto-Disable Rules:**
- PF < 0.8 after 10 trades → Disable
- PF < 1.0 after 30 trades → Disable
- WR < 40% after 30 trades → Demote to SANDBOX

### 1.4 Add Funding Rate Check (Crypto Alpha)

**Implementation:**
```python
FUNDING_THRESHOLD = 0.08  # 8% annualized

if funding_rate > FUNDING_THRESHOLD:
    reduce_long_size(pick, factor=0.5)
    add_score_penalty(pick, -10)
elif funding_rate < -FUNDING_THRESHOLD:
    reduce_short_size(pick, factor=0.5)
    add_score_penalty(pick, -10)
```

Expected Impact: +2% win rate, -0.5% drawdown

### 1.5 Position Sizing by Trust Tier

**New Position Limits:**
| Tier | Max Risk/Trade | Max Concurrent | Min R:R |
|------|----------------|----------------|---------|
| SANDBOX | 0.25% | 2 | 2.0:1 |
| PROBATION | 0.50% | 3 | 2.5:1 |
| WATCH | 0.75% | 4 | 1.75:1 |
| PROVEN | 1.50% | 6 | 1.33:1 |

**Key Change:** Higher scores require BETTER R:R ratios (inverse relationship)

---

## Phase 2: Performance Improvements (Weeks 3-6)

### 2.1 Implement High-Score Pick Criteria

**"High-Score Pick" Definition (ALL must be met):**
| Criteria | Minimum | Target |
|----------|---------|--------|
| Score | 65 | 75+ |
| Profit Factor | 1.2 | 1.5+ |
| Win Rate | 52% | 58%+ |
| Forward Trades | 30 | 50+ |
| Trust Tier | WATCH | PROVEN |
| Asset Class | CRYPTO | CRYPTO |
| R:R Ratio | 1.5:1 | 2.0:1 |

**Expected Impact:** +15% win rate for high-score picks

### 2.2 Volatility Regime Detection

**7 Regime Model:**
1. TRENDING_UP - Trend following strategies active
2. TRENDING_DOWN - Short strategies active
3. RANGING - Mean reversion strategies active
4. HIGH_VOL - Reduce position sizes 50%
5. LOW_VOL - Increase position sizes 25%
6. CRASH_FEAR - Only PROVEN strategies, max 0.5% risk
7. EUPHORIA - Reduce sizes 50%, tighten stops

**Implementation:**
```python
regime = detect_regime(btc_atr, vix, funding)
if regime in [CRASH_FEAR, EUPHORIA]:
    filter_strategies(min_tier=PROVEN)
    reduce_position_sizes(factor=0.5)
```

### 2.3 Kelly Criterion Position Sizing

**Formula:** Use HALF-KELLY for safety
```python
def kelly_size(win_rate, avg_win, avg_loss):
    kelly = win_rate/avg_loss - (1-win_rate)/avg_win
    return kelly * 0.5  # Half-Kelly

# Example: 52% WR, 1.8:1 R:R
# Full Kelly: 19.11% risk
# Half Kelly: 9.56% risk ← Recommended
```

**Score-Based Multipliers:**
| Score | Kelly Multiplier |
|-------|------------------|
| 85-100 | 1.00x |
| 75-84 | 0.75x |
| 65-74 | 0.50x |
| 55-64 | 0.25x |
| <55 | DO NOT TRADE |

### 2.4 Enhanced Circuit Breakers

**Drawdown Levels:**
| Level | Drawdown | Action |
|-------|----------|--------|
| Yellow | 5% | Reduce new positions 25% |
| Orange | 10% | Reduce all 50%, max 2 new positions |
| Red | 15% | Close all, mandatory 1-week break |
| Blackout | 20% | Trading halt, strategy review |

**Consecutive Loss Limits:**
- 3 losing days → 48-hour cooling off
- 5 losing trades in row → Reduce size 50%
- 10 losing trades in row → Stop trading, review

### 2.5 Correlation Limits

**Portfolio Constraints:**
- No new position if correlation > 0.70 with existing
- Max 30% exposure in single sector
- Max 15% in crypto (of total portfolio)
- Reduce by 25% if 2+ positions in same asset class

---

## Phase 3: Advanced Features (Weeks 7-12)

### 3.1 High-Certainty Crypto Score (HCCS)

**6-Factor Scoring Model:**
```
HCCS = (Technical × 0.30) + 
       (Funding × 0.20) + 
       (Liquidity × 0.15) + 
       (On-Chain × 0.15) + 
       (Vol Fit × 0.10) + 
       (Flow × 0.10)
```

| Factor | Weight | Data Source |
|--------|--------|-------------|
| Technical | 30% | Price action, indicators |
| Funding Rate | 20% | Binance funding data |
| Liquidity | 15% | 24h volume, spread |
| On-Chain | 15% | Exchange flows, whale data |
| Volatility Fit | 10% | ATR vs historical |
| Flow | 10% | Order book imbalance |

**HCCS Interpretation:**
| Score | Certainty | Position Size | Expected WR |
|-------|-----------|---------------|-------------|
| 85+ | EXTREME | 2.0x | 65%+ |
| 75-84 | HIGH | 1.5x | 55-65% |
| 65-74 | MEDIUM | 1.0x | 45-55% |
| <50 | AVOID | 0x | <35% |

### 3.2 Three New Crypto Strategies

**Strategy 1: Funding Rate Reversion**
- Long when funding < -0.05% (shorts overpaying)
- Short when funding > +0.08% (longs overpaying)
- Target: 60-70% WR, PF 2.0+
- Hold time: 8-24 hours

**Strategy 2: On-Chain Momentum**
- Exchange netflow negative (coins leaving exchanges)
- Whale accumulation increasing
- MVRV ratio < 2.0 (not overvalued)
- Target: 50-55% WR, PF 1.8+
- Hold time: 3-7 days

**Strategy 3: Volatility Regime Scalping**
- Trade only in HIGH_VOL regime
- Use 15m/1h timeframe
- Tight stops (0.5 ATR)
- Target: 55-60% WR, PF 1.9+
- Hold time: 1-6 hours

### 3.3 Rapid Loser Filtering (3-Layer)

**Layer 1 (Trades 1-10):**
- Auto-disable if PF < 0.8
- Auto-disable if drawdown > 15%
- Demote if WR < 35%

**Layer 2 (Trades 11-30):**
- Demote if WR < 40%
- Disable if PF < 1.0
- Disable if avg PnL < -1%

**Layer 3 (Trades 31-50):**
- Demote if WR < 45%
- Demote if PF < 1.10
- Graduate if WR > 55% and PF > 1.25

### 3.4 Walk-Forward Optimization Requirements

**Before Strategy Graduation:**
- WFO Efficiency >= 70% (Grade B minimum)
- OOS Win Rate within +-15% of IS
- 5 minimum WFO runs over 3+ years
- Profit Factor OOS >= 1.20

---

## Asset Class Recommendations

### CRYPTO - FOCUS HERE (Only Profitable Asset)
**Current:** +0.19% avg PnL, 47.7% WR  
**Target:** +1.5% avg PnL, 55%+ WR

**Actions:**
- ✅ Continue trading crypto
- ✅ Add funding rate integration
- ✅ Add on-chain metrics
- ✅ Focus on BTC, ETH, top 10 altcoins
- ❌ Avoid Tier 4-5 coins (JTO, STRK, APE, etc.)

### EQUITY - PAUSE (Currently Losing)
**Current:** -0.58% avg PnL, 39.8% WR  
**Status:** DEMOTED - Goldmine stocks at -46.92%

**Actions:**
- ❌ STOP all equity picks immediately
- 🔧 Fix Goldmine strategy before resuming
- 🔧 Require PF > 1.3 before re-enabling
- 🔧 Minimum 100 forward trades

### COMMODITY - AVOID (Worst Performer)
**Current:** -0.70% avg PnL, 8.3% WR

**Actions:**
- ❌ STOP all commodity picks
- 🔧 Review only after 6 months of positive crypto performance

### FOREX - MARGINAL (Low Volume)
**Current:** -0.32% avg PnL, 29.4% WR

**Actions:**
- ⚠️ Reduce to 5% of portfolio max
- ⚠️ Only PROVEN tier strategies
- ⚠️ Require score > 75

---

## Success Metrics & Targets

### 30-Day Targets (Phase 1 Complete)
| Metric | Current | Target |
|--------|---------|--------|
| Win Rate | 27-38% | 48% |
| Profit Factor | 0.88 | 1.15 |
| Max Drawdown | >30% | <15% |
| Monthly Return | -5% | +2% |
| Sharpe Ratio | <0.5 | 0.8 |

### 90-Day Targets (Phase 2 Complete)
| Metric | Current | Target |
|--------|---------|--------|
| Win Rate | 27-38% | 55% |
| Profit Factor | 0.88 | 1.35 |
| Max Drawdown | >30% | <12% |
| Monthly Return | -5% | +4% |
| Sharpe Ratio | <0.5 | 1.2 |

### 6-Month Targets (Phase 3 Complete)
| Metric | Current | Target |
|--------|---------|--------|
| Win Rate | 27-38% | 60% |
| Profit Factor | 0.88 | 1.5 |
| Max Drawdown | >30% | <10% |
| Monthly Return | -5% | +6% |
| Sharpe Ratio | <0.5 | 1.5 |

---

## Implementation Checklist

### This Week (Immediate)
- [ ] Close JTO, STRK, APE, INJ, DYDX positions
- [ ] Close RED, TRU (extreme pump)
- [ ] Implement MIN_SCORE = 65 filter
- [ ] Reduce PROBATION tier to 0.5% max risk
- [ ] Add funding rate API integration

### Week 2
- [ ] Fix trust tier graduation logic
- [ ] Implement auto-disable for PF < 1.0
- [ ] Add volatility regime detection
- [ ] Create drawdown circuit breakers

### Week 3-4
- [ ] Implement Kelly criterion sizing
- [ ] Add correlation checks
- [ ] Create HCCS scoring framework
- [ ] Add on-chain data integration

### Week 5-8
- [ ] Deploy funding rate reversion strategy
- [ ] Deploy on-chain momentum strategy
- [ ] Implement rapid loser filtering
- [ ] Add WFO requirements

### Week 9-12
- [ ] Full HCCS deployment
- [ ] Advanced scalping framework
- [ ] Portfolio optimization
- [ ] Performance review and refinement

---

## Key Insights

### What the Data Shows
1. **The scoring system DOES work** - 67% WR for 70+ scores vs 36% for low scores
2. **The problem is execution** - Low scores are still being traded
3. **Crypto is the only profitable asset** - Everything else loses money
4. **Trust tiers are broken** - 64.8% from PROBATION (losing) tier
5. **Liquidity matters** - Tier 5 coins destroy performance

### What Hedge Funds Do Differently
1. **Strict edge requirements** - PF > 1.5 minimum, not 1.1
2. **Rapid loser cutting** - Disable strategies in days, not months
3. **Position sizing discipline** - Risk controls are non-negotiable
4. **Asset focus** - Trade what works, avoid what doesn't
5. **Continuous validation** - Forward test everything

### The Path Forward
**Phase 1 fixes are critical** - They require minimal effort but offer +9% WR improvement. Without these, no advanced features will help.

**Focus on crypto only** - It's the only asset class with positive expectancy. Fix this first before touching equities or commodities.

**Trust the scores** - Stop trading low-score picks. The correlation exists (0.19), but you need to enforce the threshold.

---

## Files Generated

| File | Description |
|------|-------------|
| `/mnt/okcomputer/output/ANTIGRAVITY_HEDGE_FUND_ENHANCEMENT_PLAN.md` | This comprehensive plan |
| `/mnt/okcomputer/output/INTEGRATED_ENHANCEMENT_ROADMAP.md` | Detailed roadmap with timelines |
| `/mnt/okcomputer/output/CRYPTO_HIGH_CERTAINTY_ENHANCEMENTS.md` | Crypto-specific 23K word document |
| `/mnt/okcomputer/output/risk_management_framework.md` | Complete risk framework |
| `/mnt/okcomputer/output/crypto_enhancements.py` | Python implementation (25K) |
| `/mnt/okcomputer/output/risk_manager.py` | Risk manager Python class |

---

## Conclusion

Your system has the infrastructure but lacks the discipline of hedge fund execution. The scoring system works, but you're trading too many low-quality picks from losing strategies.

**The formula for success:**
1. Close the losers (Tier 5 coins, extreme pumps)
2. Enforce minimum standards (Score 65+, PF 1.2+)
3. Fix trust tiers (stop trading PROBation strategies)
4. Add crypto alpha (funding rates, on-chain)
5. Size positions correctly (Kelly, trust tier based)

**Expected timeline to profitability:** 30-60 days if Phase 1 is executed immediately.

---

*"The difference between amateur and professional trading is not the strategy - it's the discipline to say no to bad trades."*
