# Research Library Index
## Complete Trading Strategy Knowledge Base
### Last Updated: March 2, 2026

---

## Quick Navigation

| Document | Topic | Size | Key Strategies |
|----------|-------|------|----------------|
| [DEEP_RESEARCH_ML_AI_TRADING.md](DEEP_RESEARCH_ML_AI_TRADING.md) | ML/AI Trading | 16KB | Quantformer, LSTM, XGBoost Ensemble, On-Chain Analytics |
| [DEEP_RESEARCH_MARKET_MICROSTRUCTURE.md](DEEP_RESEARCH_MARKET_MICROSTRUCTURE.md) | Execution | 18KB | TWAP, VWAP, Smart Routing, Market Impact Models |
| [DEEP_RESEARCH_PORTFOLIO_CONSTRUCTION.md](DEEP_RESEARCH_PORTFOLIO_CONSTRUCTION.md) | Portfolio Mgmt | 21KB | Kelly Criterion, Risk Parity, CPPI, Factor Investing |
| [DEEP_RESEARCH_OPTIONS_VOLATILITY.md](DEEP_RESEARCH_OPTIONS_VOLATILITY.md) | Options Trading | 19KB | Greeks, VRP, 0DTE, Variance Swaps, Structured Products |
| [DEEP_RESEARCH_BEHAVIORAL_FINANCE.md](DEEP_RESEARCH_BEHAVIORAL_FINANCE.md) | Market Psychology | 26KB | Sentiment, Cognitive Biases, Contrarian Strategies |

---

## Research Summary by Strategy Type

### 1. Directional Strategies
**Documents:** ML/AI, Behavioral Finance, Portfolio Construction

**Key Approaches:**
- **ML Ensemble:** XGBoost + LSTM + Transformer with on-chain data (15-25% CAGR)
- **Momentum:** Factor-based with behavioral timing (6-12% alpha)
- **Mean Reversion:** Z-score with sentiment confirmation (4-10% alpha)
- **PEAD:** Post-earnings drift exploitation (4-8% alpha)

**Implementation:** See `baby_strategies/ml_ensemble_strategy.py`

---

### 2. Income/Options Strategies
**Documents:** Options & Volatility

**Key Approaches:**
- **VRP Harvesting:** Sell volatility for 4-8% annual alpha
- **Covered Calls:** Enhance returns by 2-4% annually
- **Iron Condors:** 10-20% annual returns, 75% win rate
- **0DTE Scalping:** 50-100%+ potential (high risk)

**Capital Requirements:**
- Retail: $2,000-$5,000 (spreads, covered calls)
- Advanced: $25,000+ (naked options)
- Professional: $50,000+ (0DTE, portfolio margin)

---

### 3. Portfolio Management
**Documents:** Portfolio Construction, Risk Management

**Key Approaches:**
| Strategy | Target CAGR | Sharpe | Max DD |
|----------|-------------|--------|--------|
| Half-Kelly (Single) | 15-25% | 1.0-1.3 | -25% |
| Risk Parity | 7-9% | 1.0-1.2 | -15% |
| CPPI (90% floor) | 8-12% | 0.8-1.0 | -10% |
| Factor Diversified | 10-14% | 1.1-1.4 | -15% |

**Implementation:** See position sizing functions in `regime_position_sizing.py`

---

### 4. Execution & Cost Reduction
**Documents:** Market Microstructure

**Expected Savings:**
- Smart Order Routing: 5-15 bps per trade
- Algorithm Selection: 5-10 bps
- Market Timing: 2-5 bps
- **Total: 10-20 bps per trade**

**Implementation:** See `baby_strategies/smart_execution_strategy.py`

---

### 5. Behavioral Alpha
**Documents:** Behavioral Finance

**Key Edges:**
- Contrarian Sentiment: 3-6% alpha (fade extremes)
- Window Dressing: 2-4% alpha (quarter-end)
- Overnight Effect: 2-4% alpha (smart money timing)
- Analyst Herding: 3-6% alpha (fade consensus)

**Indicators:**
- VIX, Put/Call Ratio, AAII Sentiment
- Fear & Greed Index, Margin Debt
- Social Media Sentiment

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. **Risk Management Setup**
   - Implement volatility targeting
   - Set max drawdown limits
   - Create position sizing framework

2. **Basic Strategies**
   - Deploy momentum with risk controls
   - Add mean reversion overlay
   - Implement stop-losses

**Documents:** Portfolio Construction, Behavioral Finance

### Phase 2: Enhancement (Weeks 3-4)
3. **ML Integration**
   - Deploy XGBoost ensemble
   - Add on-chain data for crypto
   - Implement walk-forward validation

4. **Execution Improvement**
   - Deploy smart order routing
   - Use TWAP/VWAP for large orders
   - Implement transaction cost analysis

**Documents:** ML/AI Trading, Market Microstructure

### Phase 3: Advanced (Weeks 5-8)
5. **Options Overlay**
   - Add covered calls for income
   - Use protective puts for insurance
   - Explore volatility trading

6. **Behavioral Signals**
   - Integrate sentiment indicators
   - Deploy contrarian filters
   - Monitor institutional flows

**Documents:** Options/Volatility, Behavioral Finance

---

## Strategy Bundles Reference

### Conservative Bundle (Wealth Preservation)
- **Target:** 8-12% CAGR, Sharpe 1.2-1.8, Max DD -8-15%
- **Allocation:**
  - 40% Protective Asset Allocation (PAA)
  - 30% All-Weather Core (Risk Parity)
  - 20% Risk-Managed Carry
  - 10% Inflation Protection

**Research:** Portfolio Construction + Risk Management

### Moderate Bundle (Balanced Growth)
- **Target:** 12-18% CAGR, Sharpe 1.1-1.5, Max DD -15-20%
- **Allocation:**
  - 35% Risk-Managed Momentum
  - 35% Risk Parity Core
  - 20% Multi-Asset Trend
  - 10% Defensive Allocation

**Research:** ML/AI + Portfolio Construction + Execution

### Aggressive Bundle (Alpha Hunter)
- **Target:** 18-28% CAGR, Sharpe 1.0-1.3, Max DD -25-35%
- **Allocation:**
  - 40% Dual Momentum
  - 30% Factor Rotation
  - 20% Sector Momentum
  - 10% Crypto Trend

**Research:** ML/AI + Behavioral Finance + Microstructure

---

## Key Formulas & Code Snippets

### Kelly Criterion
```python
def kelly_fraction(win_rate, avg_win, avg_loss):
    b = avg_win / abs(avg_loss)
    p = win_rate
    q = 1 - p
    return (p * b - q) / b

# Use Half-Kelly for safety
position_size = kelly_fraction(p, win, loss) * 0.5
```

### Risk Parity Weights
```python
def risk_parity_weights(cov_matrix):
    """Equal risk contribution"""
    n = len(cov_matrix)
    weights = np.ones(n) / n
    
    for _ in range(100):
        risk_contrib = weights * (cov_matrix @ weights)
        weights *= (risk_contrib.sum() / (n * risk_contrib))
        weights /= weights.sum()
    
    return weights
```

### Market Impact Model
```python
def market_impact(order_size, daily_volume, volatility, spread):
    participation = order_size / daily_volume
    temp_impact = spread + 0.5 * volatility * np.sqrt(participation)
    perm_impact = volatility * (participation ** 0.6)
    return temp_impact + perm_impact
```

---

## Research Glossary

| Term | Definition | Source Document |
|------|------------|-----------------|
| **Quantformer** | Transformer architecture for financial time series | ML/AI Trading |
| **VRP** | Volatility Risk Premium (implied > realized vol) | Options/Volatility |
| **CPPI** | Constant Proportion Portfolio Insurance | Portfolio Construction |
| **TWAP** | Time-Weighted Average Price execution | Market Microstructure |
| **PEAD** | Post-Earnings Announcement Drift | Behavioral Finance |
| **0DTE** | Zero Days to Expiration options | Options/Volatility |
| **NUPL** | Net Unrealized Profit/Loss (on-chain) | ML/AI Trading |
| **OFI** | Order Flow Imbalance | Market Microstructure |

---

## Performance Expectations Summary

### By Asset Class

| Asset Class | Conservative | Moderate | Aggressive |
|-------------|--------------|----------|------------|
| **Equities** | 8-10% CAGR | 12-16% CAGR | 18-25% CAGR |
| **Crypto** | 12-18% CAGR | 25-35% CAGR | 40-60% CAGR |
| **Options** | 4-8% (income) | 10-15% CAGR | 20-40% CAGR |
| **Multi-Asset** | 7-9% CAGR | 12-18% CAGR | 15-25% CAGR |

### By Risk Level

| Risk Profile | Expected Sharpe | Max Drawdown | Win Rate |
|--------------|-----------------|--------------|----------|
| Conservative | 1.2-1.5 | -8% to -15% | 60-65% |
| Moderate | 1.0-1.3 | -15% to -20% | 55-60% |
| Aggressive | 0.8-1.2 | -25% to -35% | 50-55% |

---

## Next Steps for Implementation

1. **Immediate (This Week)**
   - [ ] Read Portfolio Construction research
   - [ ] Implement Kelly position sizing
   - [ ] Set up risk monitoring dashboard

2. **Short-term (Next 2 Weeks)**
   - [ ] Deploy ML ensemble strategy
   - [ ] Integrate on-chain data feeds
   - [ ] Test smart execution algorithms

3. **Medium-term (Next Month)**
   - [ ] Add options overlay strategies
   - [ ] Implement sentiment analysis
   - [ ] Deploy full strategy bundles

4. **Ongoing**
   - [ ] Monitor strategy performance
   - [ ] Rebalance based on regime
   - [ ] Update models with new data

---

## Additional Resources

### Python Implementations
- `baby_strategies/ml_ensemble_strategy.py` - ML trading system
- `baby_strategies/smart_execution_strategy.py` - Execution algorithms
- `baby_strategies/bundle_optimized/` - Strategy bundles

### Backtesting Framework
- `backtest_framework.py` - Multi-strategy backtesting
- `risk_quantification_agent.py` - Risk monitoring

### Data Sources Referenced
- On-chain metrics (NUPL, MVRV, exchange flows)
- Social sentiment (Twitter, Reddit)
- Market microstructure (order book, flow)
- Alternative data (satellite, credit card)

---

*This index serves as the central reference for all trading strategy research. Each linked document contains detailed implementation guides, mathematical foundations, and expected performance metrics.*
