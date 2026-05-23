# Risk Management & Position Sizing Framework
## Multi-Asset Trading System

---

## Executive Summary

This framework provides a comprehensive risk management system designed to achieve consistent profitability while preserving capital. It integrates trust-based position sizing, Kelly criterion optimization, drawdown circuit breakers, and portfolio-level constraints.

**Key Principles:**
1. Capital preservation is paramount
2. Position size should reflect both signal quality AND strategy performance
3. Drawdowns must be controlled proactively
4. Correlation risk requires active monitoring

---

## 1. Trust Tier Position Sizing Framework

### Tier Definitions & Position Limits

| Tier | Description | Max Risk/Trade | Max Concurrent | Min Score | Min R:R |
|------|-------------|----------------|----------------|-----------|---------|
| **SANDBOX** | Unproven strategy, no track record | 0.25% | 2 | 70 | 2.0:1 |
| **PROBATION** | Losing history, drawdown > 10% | 0.50% | 3 | 75 | 2.5:1 |
| **WATCH** | Marginal edge, breakeven results | 0.75% | 4 | 65 | 1.75:1 |
| **PROVEN** | Profitable track record, Sharpe > 1.0 | 1.50% | 6 | 55 | 1.33:1 |

### Trust Tier Multipliers (applied to base position size)

| Tier | Multiplier | Rationale |
|------|------------|-----------|
| SANDBOX | 0.25x | Minimal exposure while validating |
| PROBATION | 0.50x | Reduced size until edge re-established |
| WATCH | 0.75x | Moderate exposure while monitoring |
| PROVEN | 1.50x | Full size for validated strategies |

### Example Position Sizes ($10,000 Portfolio)

| Tier | Max Position | Per-Trade Risk |
|------|--------------|----------------|
| SANDBOX | $25 | $25 |
| PROBATION | $50 | $50 |
| WATCH | $75 | $75 |
| PROVEN | $150 | $150 |

---

## 2. Risk Controls Framework

### A. Daily/Weekly/Monthly Loss Limits

| Limit Level | Threshold | Action | Example ($10K) |
|-------------|-----------|--------|----------------|
| **Daily** | 2% of portfolio | HALT NEW POSITIONS for 24 hours | $200 |
| **Weekly** | 5% of portfolio | REDUCE ALL POSITIONS 50%, HALT NEW | $500 |
| **Monthly** | 10% of portfolio | EMERGENCY CIRCUIT BREAKER - Close all | $1,000 |
| **Consecutive Losses** | 3 losing days | MANDATORY 48-hour cooling off | N/A |

### B. Correlation Limits

| Rule | Limit | Rationale |
|------|-------|-----------|
| Max Correlation per Position | No new position if correlation > 0.70 | Prevents concentration risk |
| Sector Exposure Limit | Max 30% in single sector | Diversification |
| Asset Class Correlation | Reduce each by 25% if 2+ in same class | Reduce systematic risk |
| Market Beta Limit | Portfolio beta 0.5 - 1.5 | Control market exposure |

### C. Drawdown Circuit Breakers

| Drawdown Level | Action | Position Multiplier |
|----------------|--------|---------------------|
| **5%** (YELLOW) | Reduce new positions 25% | 0.75x |
| **10%** (ORANGE) | Reduce all positions 50%, max 2 new | 0.50x |
| **15%** (RED) | Close all, mandatory 1-week break | 0.00x |
| **20%** (BLACKOUT) | Trading halt, strategy review | 0.00x |

### D. Recovery Protocol

1. **After 5% drawdown**: Must recover 50% of drawdown before normal sizing
2. **After 10% drawdown**: Must recover 75% of drawdown before normal sizing
3. **After 15% drawdown**: Must recover 100% of drawdown before normal sizing
4. **After 20% drawdown**: Complete reset, all signals back to SANDBOX

---

## 3. Kelly Criterion Position Sizing

### Formula

```
f* = (bp - q) / b

Where:
  f* = optimal fraction of capital to risk
  b = average win / average loss (R:R ratio)
  p = probability of winning
  q = probability of losing (1 - p)
```

### Kelly Calculations by Edge Level

| Scenario | Win Rate | R:R | Full Kelly | Half Kelly | Quarter Kelly |
|----------|----------|-----|------------|------------|---------------|
| Conservative | 45% | 2.0 | 17.50% | 8.75% | 4.38% |
| Moderate | 50% | 2.0 | 25.00% | 12.50% | 6.25% |
| Strong | 55% | 2.5 | 37.00% | 18.50% | 9.25% |
| Excellent | 60% | 3.0 | 46.67% | 23.33% | 11.67% |
| Current System (Est.) | 48% | 1.8 | 19.11% | 9.56% | 4.78% |

### Recommendation: Use HALF-KELLY

**Rationale:**
- Full Kelly is too volatile for most traders
- Half-Kelly reduces drawdowns by ~50% with only 25% reduction in growth
- Provides buffer for estimation errors
- More psychologically manageable

### Score-Based Kelly Multipliers

| Score Range | Kelly Multiplier | Rationale |
|-------------|------------------|-----------|
| 85-100 | 1.00x (Full) | Exceptional conviction |
| 75-84 | 0.75x | Strong signal |
| 65-74 | 0.50x | Moderate signal |
| 55-64 | 0.25x | Weak signal |
| Below 55 | 0.00x | NO TRADE |

---

## 4. High-Score Pick Risk Framework

### A. Minimum R:R Requirements by Score

| Score Range | Minimum R:R | Rationale |
|-------------|-------------|-----------|
| 85-100 | 1.33:1 | High conviction, lower R:R acceptable |
| 75-84 | 1.75:1 | Strong signal needs solid R:R |
| 65-74 | 2.00:1 | Moderate signal needs better R:R |
| 55-64 | 2.50:1 | Weak signal needs excellent R:R |
| Below 55 | N/A | DO NOT TRADE |

**CRITICAL RULE:** Never trade with R:R below 1.25:1 regardless of score.

### B. Max Position Size for High-Conviction Picks

**Score 85+ (Exceptional Conviction):**
- Base Max: 2.0% of portfolio ($200 on $10K)
- With Trust Multiplier:
  - PROVEN: 2.0% max
  - WATCH: 1.5% max
  - PROBATION: 1.0% max
  - SANDBOX: 0.5% max

**Score 75-84 (Strong Conviction):**
- Base Max: 1.5% of portfolio ($150 on $10K)
- With Trust Multiplier:
  - PROVEN: 1.5% max
  - WATCH: 1.0% max
  - PROBATION: 0.75% max
  - SANDBOX: 0.25% max

### C. Scaling In Rules (Adding to Winners)

1. Only scale in if position is profitable (+2% or more)
2. Maximum 3 scale-in entries per position
3. Each scale-in is 50% of initial position size
4. Move stop loss to breakeven after first scale-in
5. Trail stop at 50% of unrealized profits after 2nd scale-in

**Example for $100 initial position:**
- Entry 1: $100 (initial)
- Entry 2: $50 (at +3% profit)
- Entry 3: $25 (at +6% profit)
- **Total Max: $175**

### D. Scaling Out Rules (Taking Partial Profits)

1. Take 25% off at +1R profit
2. Take 25% off at +2R profit
3. Take 25% off at +3R profit
4. Let final 25% run with trailing stop

**Example for 2:1 R:R target:**
- Exit 1: 25% at +1R (recover 25% of risk)
- Exit 2: 25% at +2R (recover 50% of risk)
- Exit 3: 25% at +3R (recover 75% of risk)
- Exit 4: 25% with trailing stop (unlimited upside)

### E. Time-Based Stop Rules

| Trade Type | Time Limit | Required Move | Action if Not Met |
|------------|------------|---------------|-------------------|
| Day Trade | 2 hours | +0.5% | Close position |
| Swing (2-5 days) | 24 hours | +1% | Close position |
| Position (1-4 weeks) | 1 week | +2% | Close position |

---

## 5. Portfolio-Level Constraints

### A. Max Exposure Per Asset Class

| Asset Class | Max Exposure | Rationale |
|-------------|--------------|-----------|
| US Equities | 40% | Core holding, highest liquidity |
| International Equities | 20% | Diversification |
| Cryptocurrencies | 15% | High volatility, limit risk |
| Commodities | 10% | Inflation hedge, uncorrelated |
| Forex/Currencies | 10% | Additional diversification |
| Fixed Income/ETFs | 5% | Stability, low correlation |

**Cash Reserve:** Minimum 10% at all times

### B. Max Concurrent Positions

| Trust Tier | Max Concurrent | Rationale |
|------------|----------------|-----------|
| SANDBOX | 2 | Limited exposure while testing |
| PROBATION | 3 | Reduced activity during recovery |
| WATCH | 5 | Moderate diversification |
| PROVEN | 8 | Full deployment for proven strategies |
| **TOTAL MAX** | **12** | Hard limit across all tiers |

### C. Rebalancing Frequency

**Daily:**
- Check all stop losses
- Review correlation matrix
- Verify position sizes vs. limits
- Update trust tier assignments

**Weekly (Every Friday):**
- Full portfolio review
- Rebalance asset class exposures
- Update Kelly calculations
- Adjust trust tier multipliers

**Monthly:**
- Complete strategy performance review
- Reassess all trust tier assignments
- Update correlation assumptions
- Review all risk parameters

**Emergency:**
- Triggered by circuit breakers
- Immediate position reduction
- Cash preservation mode

---

## 6. Final Position Sizing Formula

### Complete Formula

```
POSITION SIZE = Portfolio Value × Base Risk % × Score Multiplier × Trust Tier Multiplier × Drawdown Multiplier
```

### Component Definitions

| Component | Default Value | Range |
|-----------|---------------|-------|
| Portfolio Value | Current total value | N/A |
| Base Risk % | 1.0% | 0.5% - 2.0% |
| Score Multiplier | Based on signal score | 0.0x - 1.0x |
| Trust Tier Multiplier | Based on performance | 0.25x - 1.5x |
| Drawdown Multiplier | Based on drawdown | 0.0x - 1.0x |

### Example Calculations ($10,000 Portfolio)

| Scenario | Position Size | % of Portfolio |
|----------|---------------|----------------|
| High Score + Proven + Normal | $150 | 1.50% |
| Medium Score + Watch + Normal | $38 | 0.38% |
| High Score + Probation + 5% DD | $38 | 0.38% |
| Sandbox + Any Score | $12 | 0.12% |

---

## 7. Implementation Checklist

### Immediate Actions

- [ ] Implement trust tier tracking system
- [ ] Set up daily loss limit monitoring
- [ ] Configure drawdown circuit breakers
- [ ] Create correlation monitoring dashboard
- [ ] Establish position sizing calculator

### Short-Term (Week 1)

- [ ] Backtest framework on historical data
- [ ] Calibrate score multipliers based on results
- [ ] Set up automated stop loss monitoring
- [ ] Create trust tier migration rules

### Medium-Term (Month 1)

- [ ] Analyze Kelly criterion effectiveness
- [ ] Refine R:R requirements by score
- [ ] Optimize asset class exposure limits
- [ ] Document lessons learned

---

## 8. Key Performance Indicators (KPIs)

### Risk Metrics

| Metric | Target | Alert Level |
|--------|--------|-------------|
| Max Drawdown | < 10% | 15% |
| Daily Loss | < 2% | 3% |
| Weekly Loss | < 5% | 7% |
| Portfolio Beta | 0.5 - 1.5 | Outside range |

### Performance Metrics

| Metric | Target | Minimum |
|--------|--------|---------|
| Sharpe Ratio | > 1.5 | > 1.0 |
| Sortino Ratio | > 2.0 | > 1.5 |
| Win Rate | > 50% | > 45% |
| Average R:R | > 1.5:1 | > 1.25:1 |

---

*Framework Version 1.0 | Created for Multi-Asset Trading System*
