# Integrated Enhancement Roadmap
## Hedge Fund Quality Trading System - Action Plan

**Document Version:** 1.0  
**Created:** 2026-04-07  
**Review Cycle:** Weekly

---

## Executive Summary

### Current State Analysis

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Overall Win Rate | 45.6% | 55%+ | -9.4% |
| Crypto Win Rate | 47.7% | 55%+ | -7.3% |
| Equity Win Rate | 39.8% | 50%+ | -10.2% |
| Profit Factor (alpha_engine) | 0.88 | 1.5+ | -0.62 |
| Score-PnL Correlation | 0.19 | 0.50+ | -0.31 |
| PROBATION Tier Picks | 64.8% | <30% | +34.8% |
| High Score (70+) WR | 67.2% | 75%+ | -7.8% |

### Critical Findings

1. **Scoring System Works**: High scores (70+) show 67.2% win rate vs 35.6% for low scores
2. **Trust Tier System Broken**: 64.8% of picks in PROBATION indicates systematic issues
3. **Crypto Outperforms**: 47.7% WR vs 39.8% for equities - focus on crypto first
4. **Liquidity Problem**: Many low-volume coins dragging performance
5. **Missing Alpha Sources**: No funding rate, on-chain, or volatility regime integration

---

## Phase 1: Critical Fixes (Weeks 1-2)

### 1.1 Immediate Liquidity Filters [HIGH PRIORITY]

**Objective:** Eliminate illiquid picks that cause slippage and manipulation risk

| Action | Implementation | Expected Impact |
|--------|---------------|-----------------|
| Reject Tier 5 coins (<$3M volume) | Update pick validator | +3-5% WR improvement |
| Reduce Tier 4 positions 50% | Position sizing rule | Reduce drawdowns |
| Add slippage estimator | Pre-trade check | Avoid bad entries |

**Implementation:**
```python
# Add to pick validator
MIN_VOLUME_USD = 3_000_000
MAX_SLIPPAGE_PCT = 0.5

def validate_liquidity(pick):
    if pick.volume_24h < MIN_VOLUME_USD:
        return False, "Insufficient volume"
    if pick.estimated_slippage > MAX_SLIPPAGE_PCT:
        return False, "Excessive slippage"
    return True, "OK"
```

**Coins to CLOSE Immediately:**
- JTOUSDT ($0.79M volume)
- STRKUSDT ($1.39M volume)  
- APEUSDT ($0.95M volume)
- INJUSDT ($2.07M volume)
- DYDXUSDT ($2.26M volume)

---

### 1.2 Score Threshold Enforcement [HIGH PRIORITY]

**Objective:** Only trade high-conviction picks (proven edge)

| Score Range | Action | Position Size |
|-------------|--------|---------------|
| 85+ | Full trade | 1.5x normal |
| 75-84 | Trade | 1.0x normal |
| 65-74 | Reduce | 0.5x normal |
| <65 | REJECT | 0x (no trade) |

**Current Gap:** Many picks with scores 40-60 are being traded

**Implementation:**
```python
MIN_TRADE_SCORE = 65

def should_trade(pick):
    if pick.score < MIN_TRADE_SCORE:
        return False
    if pick.trust_tier == "PROBATION" and pick.score < 75:
        return False
    return True
```

---

### 1.3 Trust Tier Recovery Protocol [HIGH PRIORITY]

**Objective:** Fix the 64.8% PROBATION tier problem

**Current Tier Distribution:**
- PROVEN: ~15%
- WATCH: ~20%
- PROBATION: 64.8% ← **PROBLEM**
- SANDBOX: ~5%

**Recovery Rules:**
1. PROBATION tier requires 75+ score to trade
2. After 10 profitable trades, promote to WATCH
3. After 20 profitable trades with PF > 1.2, promote to PROVEN
4. Auto-demote strategies with PF < 0.9 after 50 trades

---

### 1.4 Funding Rate Integration [MEDIUM PRIORITY]

**Objective:** Add crypto-specific alpha from funding rates

**Implementation:**
```python
class FundingRateFilter:
    def apply(self, pick):
        funding = get_funding_rate(pick.symbol)
        
        # Extreme funding = contrarian signal
        if funding < -0.05:  # Very negative
            pick.score += 5  # Boost score
        elif funding > 0.08:  # Very positive
            pick.score -= 5  # Reduce score for longs
            
        return pick
```

**Data Source:** Binance funding rate API (free, 8h updates)

---

## Phase 2: Performance Improvements (Weeks 3-6)

### 2.1 Volatility Regime Detection

**Objective:** Adapt position sizing to market conditions

| Regime | ATR % | Position Size | Strategy |
|--------|-------|---------------|----------|
| LOW_VOL | <3% | 1.5x | Mean reversion |
| NORMAL_VOL | 3-6% | 1.0x | Trend following |
| HIGH_VOL | 6-10% | 0.6x | Momentum only |
| EXTREME_VOL | >10% | 0.3x | Scalp only |

**Implementation:**
```python
def detect_volatility_regime(prices):
    atr_14 = calculate_atr(prices, 14)
    atr_pct = (atr_14 / prices[-1]) * 100
    
    if atr_pct < 3.0:
        return VolRegime.LOW_VOL
    elif atr_pct < 6.0:
        return VolRegime.NORMAL_VOL
    elif atr_pct < 10.0:
        return VolRegime.HIGH_VOL
    else:
        return VolRegime.EXTREME_VOL
```

---

### 2.2 On-Chain Metrics for BTC/ETH

**Objective:** Add leading indicators for major cryptos

| Metric | Source | Signal |
|--------|--------|--------|
| Exchange Netflow | Glassnode | Outflow = bullish |
| Whale Wallets | CryptoQuant | Accumulation = bullish |
| Active Addresses | Glassnode | Growth = momentum |
| Transaction Volume | CryptoQuant | Spike = volatility |

**Implementation Priority:**
1. Week 3: Exchange netflow for BTC/ETH
2. Week 4: Whale wallet tracking
3. Week 5: Active addresses
4. Week 6: Full integration

---

### 2.3 Enhanced Risk Management

**Objective:** Implement hedge fund-level risk controls

**Circuit Breakers:**
| Drawdown | Action |
|----------|--------|
| 5% | Reduce new positions 25% |
| 10% | Reduce all positions 50%, halt new |
| 15% | Close all, mandatory 1-week break |
| 20% | Full reset, all strategies to SANDBOX |

**Daily Loss Limits:**
- 2% daily loss = halt new positions for 24h
- 5% weekly loss = reduce all positions 50%
- 10% monthly loss = emergency circuit breaker

---

### 2.4 Kelly Criterion Position Sizing

**Objective:** Optimize position sizes based on edge

```python
def kelly_position_size(win_rate, avg_win, avg_loss):
    """
    f* = (bp - q) / b
    where: b = avg_win/avg_loss, p = win_rate, q = 1-p
    """
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    
    full_kelly = (b * p - q) / b
    half_kelly = full_kelly * 0.5  # Use half-Kelly for safety
    
    return half_kelly
```

**Usage:** Apply to PROVEN tier strategies only

---

## Phase 3: Advanced Features (Weeks 7-12)

### 3.1 High-Certainty Crypto Score (HCCS)

**Objective:** Comprehensive crypto-specific scoring

| Component | Weight | Description |
|-----------|--------|-------------|
| Technical Confluence | 30% | Number of agreeing systems |
| Funding Edge | 20% | Funding rate percentile |
| Liquidity Quality | 15% | Volume tier |
| On-Chain Tailwind | 15% | Exchange flows, whale activity |
| Volatility Regime Fit | 10% | Strategy-volatility match |
| Exchange Flow | 10% | Coinbase premium, Korean premium |

**Certainty Levels:**
| HCCS | Level | Position Size |
|------|-------|---------------|
| 85+ | EXTREME | 2.0x |
| 75-84 | HIGH | 1.5x |
| 65-74 | MEDIUM | 1.0x |
| 50-64 | LOW | 0.5x |
| <50 | AVOID | 0x |

---

### 3.2 Funding Rate Reversion Strategy

**Objective:** Exploit extreme funding rates

**Setup:**
- Monitor funding every 8 hours
- Enter opposite to funding direction at extremes
- Hold until funding normalizes or 48 hours max

**Entry Criteria:**
```python
def funding_reversion_signal(symbol):
    funding = get_funding_rate(symbol)
    history = get_30d_funding_history(symbol)
    percentile = np.percentile(funding, history)
    
    if percentile > 95:
        return {"signal": "SHORT", "confidence": "HIGH"}
    elif percentile < 5:
        return {"signal": "LONG", "confidence": "HIGH"}
```

**Expected Performance:** 60-70% WR, PF 2.0+

---

### 3.3 On-Chain Momentum Strategy

**Objective:** Combine on-chain signals with technical breakout

**Entry Criteria:**
- Exchange netflow < -$5M (outflow)
- Whale buying > $10M (7d)
- Active address growth > 5%
- Price above 20 EMA + volume spike

**Expected Performance:** 50-55% WR, PF 1.8+

---

### 3.4 Scalping Framework

**Objective:** High-frequency crypto scalping

**Rules:**
- Only BTC, ETH, SOL, XRP (Tier 1-2)
- Minimum 0.3% profit target
- Maximum 0.15% stop loss
- Only during high volume (UTC 12:00-20:00)
- Avoid funding payment times

**Expected Performance:** 55-60% WR, PF 1.9+, 5-15 trades/day

---

## Success Metrics & Targets

### Primary KPIs

| Metric | Current | 30-Day Target | 90-Day Target |
|--------|---------|---------------|---------------|
| **Win Rate** | 45.6% | 52% | 58% |
| **Profit Factor** | 0.88 | 1.2 | 1.5 |
| **Max Drawdown** | Unknown | <10% | <8% |
| **Monthly Return** | ~0% | +3% | +5% |
| **Sharpe Ratio** | Negative | 1.0 | 1.5 |
| **Score-PnL Correlation** | 0.19 | 0.35 | 0.50 |

### Secondary KPIs

| Metric | Current | 30-Day Target | 90-Day Target |
|--------|---------|---------------|---------------|
| High Score (70+) WR | 67.2% | 72% | 78% |
| PROBATION Tier % | 64.8% | 45% | 25% |
| Average Trade PnL | 0.05% | +0.8% | +1.2% |
| Consecutive Losses | Unknown | <5 | <3 |

### Crypto-Specific Targets

| Metric | Current | 30-Day Target | 90-Day Target |
|--------|---------|---------------|---------------|
| Crypto Win Rate | 47.7% | 55% | 62% |
| Crypto PF | 0.88 | 1.3 | 1.6 |
| Funding Rate Edge | 0% | +3% WR | +5% WR |
| Liquidity Filter Impact | N/A | +2% WR | +4% WR |

---

## Quick Wins vs Long-Term Investments

### Quick Wins (Implement This Week)

| Action | Effort | Impact | Timeline |
|--------|--------|--------|----------|
| Close Tier 5 coins | 1 hour | +2% WR | Immediate |
| Enforce score >= 65 | 2 hours | +3% WR | 1 day |
| Add funding rate check | 4 hours | +2% WR | 2 days |
| Reduce PROBATION sizing | 1 hour | -1% DD | Immediate |
| Fix trust tier logic | 4 hours | +2% WR | 3 days |

**Total Quick Win Impact:** +9% WR improvement potential

---

### Medium-Term Investments (2-4 Weeks)

| Action | Effort | Impact | Timeline |
|--------|--------|--------|----------|
| Volatility regime detection | 16 hours | +2% WR, -3% DD | 2 weeks |
| On-chain integration (BTC/ETH) | 24 hours | +3% WR | 3 weeks |
| Kelly criterion sizing | 8 hours | +1% WR | 2 weeks |
| Enhanced circuit breakers | 12 hours | -2% DD | 2 weeks |
| HCCS scoring system | 40 hours | +4% WR | 4 weeks |

---

### Long-Term Investments (2-3 Months)

| Action | Effort | Impact | Timeline |
|--------|--------|--------|----------|
| Full on-chain (top 20) | 80 hours | +5% WR | 3 months |
| Funding reversion strategy | 40 hours | PF 2.0+ | 2 months |
| Scalping framework | 60 hours | PF 1.9+ | 3 months |
| ML model retraining | 120 hours | +5% WR | 3 months |
| Cross-asset correlation | 32 hours | -2% DD | 2 months |

---

## Implementation Checklist

### Next 2 Weeks (Sprint 1)

**Week 1:**
- [ ] Close all Tier 5 coins (JTO, STRK, APE, INJ, DYDX)
- [ ] Implement MIN_SCORE = 65 filter
- [ ] Reduce PROBATION tier position sizes 50%
- [ ] Add funding rate API integration
- [ ] Create liquidity validator

**Week 2:**
- [ ] Deploy funding rate scoring
- [ ] Fix trust tier promotion/demotion logic
- [ ] Add daily loss limit monitoring
- [ ] Implement 5% drawdown circuit breaker
- [ ] Backtest score threshold changes

---

### Next Month (Sprint 2)

**Week 3:**
- [ ] Deploy volatility regime detector
- [ ] Add on-chain netflow for BTC/ETH
- [ ] Implement Kelly criterion for PROVEN tier
- [ ] Create correlation monitoring
- [ ] Add slippage estimator

**Week 4:**
- [ ] Integrate whale wallet tracking
- [ ] Deploy HCCS scoring (v1)
- [ ] Add weekly loss limit (5%)
- [ ] Implement 10% drawdown circuit breaker
- [ ] Create performance attribution report

---

### Next Quarter (Sprint 3)

**Month 2:**
- [ ] Full on-chain integration (top 20 coins)
- [ ] Deploy funding reversion strategy
- [ ] Add active address metrics
- [ ] Implement monthly loss limit (10%)
- [ ] Create automated tier migration

**Month 3:**
- [ ] Deploy scalping framework
- [ ] Full HCCS v2 with all components
- [ ] Add cross-asset correlation limits
- [ ] Implement 15% drawdown circuit breaker
- [ ] Deploy ML model retraining pipeline

---

## Risk Management Framework

### Position Sizing Formula

```
POSITION SIZE = Portfolio x Base Risk % x Score Mult x Trust Mult x Vol Regime Mult x Drawdown Mult

Where:
- Base Risk % = 1.0% (default)
- Score Mult = 0.0-1.0 (based on score)
- Trust Mult = 0.25-1.5 (SANDBOX to PROVEN)
- Vol Regime Mult = 0.3-1.5 (EXTREME to LOW vol)
- Drawdown Mult = 0.0-1.0 (based on drawdown)
```

### Maximum Exposure Limits

| Asset Class | Max Exposure |
|-------------|--------------|
| Cryptocurrencies | 15% |
| US Equities | 40% |
| International Equities | 20% |
| Commodities | 10% |
| Forex | 10% |
| Cash Reserve | Minimum 10% |

### Per-Trade Limits

| Metric | Limit |
|--------|-------|
| Max position size | 2% of portfolio |
| Max risk per trade | 1% of portfolio |
| Max correlation | 0.70 between positions |
| Max sector exposure | 30% |

---

## Monitoring & Reporting

### Daily Dashboard Metrics

1. Win rate (7-day rolling)
2. Profit factor (30-day rolling)
3. Current drawdown
4. Active picks by tier
5. Score distribution
6. Funding rate extremes

### Weekly Review

1. Strategy performance by tier
2. Asset class attribution
3. Correlation matrix
4. Liquidity analysis
5. On-chain summary

### Monthly Review

1. Full performance attribution
2. Strategy tier migrations
3. Risk parameter calibration
4. ML model performance
5. Roadmap progress review

---

## Appendix: Current Pick Reclassification

### Immediate Actions Required

| Symbol | Current Tier | Action | Rationale |
|--------|--------------|--------|-----------|
| JTOUSDT | Tier 5 | **CLOSE** | $0.79M volume - critical |
| STRKUSDT | Tier 5 | **CLOSE** | $1.39M volume - critical |
| APEUSDT | Tier 5 | **CLOSE** | $0.95M volume - critical |
| INJUSDT | Tier 5 | **CLOSE** | $2.07M volume - insufficient |
| DYDXUSDT | Tier 5 | **CLOSE** | $2.26M volume - insufficient |
| REDUSDT | Tier 3 | **CLOSE** | +72% today - extreme risk |
| TRUUSDT | Tier 4 | **CLOSE** | +75% today - extreme risk |
| ZROUSDT | Tier 5 | **CLOSE** | $3.98M volume - borderline |
| APTUSDT | Tier 5 | **CLOSE** | $3.95M volume - borderline |

### Reduce Position Size

| Symbol | Current Tier | Action | Rationale |
|--------|--------------|--------|-----------|
| DOTUSDT | Tier 5 | Reduce 75% | Low volume |
| NEARUSDT | Tier 5 | Reduce 75% | Low volume |
| HBARUSDT | Tier 5 | Reduce 75% | Low volume |
| TONUSDT | Tier 5 | Reduce 75% | Low volume |
| AAVEUSDT | Tier 5 | Reduce 75% | Low volume |
| ADAUSDT | Tier 4 | Reduce 50% | Lower volume |
| AVAXUSDT | Tier 4 | Reduce 50% | Lower volume |
| FETUSDT | Tier 4 | Reduce 50% | AI narrative volatility |
| RENDERUSDT | Tier 4 | Reduce 50% | Lower volume |
| SUIUSDT | Tier 4 | Reduce 50% | Newer coin |

### Hold / Monitor

| Symbol | Current Tier | Action | Rationale |
|--------|--------------|--------|-----------|
| BTCUSDT | Tier 1 | HOLD | Excellent liquidity |
| ETHUSDT | Tier 1 | HOLD | Excellent liquidity |
| SOLUSDT | Tier 2 | HOLD | Strong volume |
| XRPUSDT | Tier 2 | HOLD | Good liquidity |
| BNBUSDT | Tier 3 | Reduce 25% | Lower than ideal |
| DOGEUSDT | Tier 3 | HOLD | Meme coin risk but liquid |
| TAOUSDT | Tier 3 | Reduce 25% | Monitor funding |
| ZECUSDT | Tier 3 | Reduce 25% | Privacy coin risk |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-07 | Integration Lead | Initial release |

**Next Review:** 2026-04-14  
**Approval:** Pending
