# High Sharpe Ratio Momentum Strategy

## Executive Summary

The **High Sharpe Ratio Momentum Strategy** is a quantitative investment approach that identifies and invests in S&P 500 stocks delivering superior risk-adjusted returns. By combining the Sharpe ratio's mathematical rigor with momentum filters and disciplined risk management, this strategy aims to achieve 12-15% annual returns with lower volatility than the broader market.

---

## 1. Strategy Overview

### 1.1 Core Philosophy

The strategy is built on a fundamental principle of modern portfolio theory: **investors should be compensated for the risk they take**. The Sharpe ratio measures exactly this - how much excess return an investment generates per unit of risk (volatility).

By focusing on stocks with Sharpe ratios above 1.0, we target investments that have historically delivered returns exceeding the risk-free rate by more than their standard deviation - a mathematically sound threshold for superior risk-adjusted performance.

### 1.2 Key Differentiators

| Feature | Traditional Momentum | High Sharpe Momentum |
|---------|---------------------|----------------------|
| Selection Criteria | Raw price returns | Risk-adjusted returns |
| Risk Awareness | Low | High |
| Volatility Profile | Often higher | Lower than market |
| Drawdown Protection | Limited | Built-in via multiple mechanisms |
| Rebalancing Frequency | Monthly/Weekly | Quarterly (cost-efficient) |

---

## 2. Strategy Rules

### 2.1 Universe Definition

**Primary Universe**: S&P 500 Constituents
- Market cap: $15B+ (implied by S&P 500 inclusion)
- Liquidity: Minimum $2M daily trading volume
- Data availability: 3+ years of price history

### 2.2 Entry Rules (All Must Be Met)

| Rule | Parameter | Rationale |
|------|-----------|-----------|
| Universe Filter | S&P 500 constituent | Quality, liquidity, institutional coverage |
| Sharpe Ratio | 3-year rolling > 1.0 | Superior risk-adjusted returns |
| Momentum Filter | Price > 50-day SMA | Confirms positive trend |
| Liquidity Filter | Volume > 1M shares/day | Ensures tradability, minimal slippage |

**Sharpe Ratio Calculation**:
```
Sharpe Ratio = (Annualized Return - Risk-Free Rate) / Annualized Volatility

Where:
- Annualized Return = (Ending Price / Beginning Price)^(252/trading days) - 1
- Risk-Free Rate = 3-month T-Bill rate (annualized)
- Annualized Volatility = Daily Returns Std Dev × √252
```

### 2.3 Exit Rules (Any Condition Triggers Exit)

| Rule | Parameter | Rationale |
|------|-----------|-----------|
| Sharpe Degradation | 3-year Sharpe < 0.8 | Risk-adjusted performance deteriorated |
| Trend Break | Price < 200-day SMA | Long-term trend reversal |
| Stop Loss | -15% from entry | Hard risk limit per position |
| Rebalancing | Quarterly schedule | Systematic portfolio refresh |

### 2.4 Position Sizing

**Equal Weight Methodology**:
- Target: Top 10 qualifying stocks
- Weight per position: 10% (equal weight)
- Maximum position size: 10% (hard cap)
- Cash buffer: 0-10% (optional, based on opportunity set)

**Rebalancing Schedule**:
- Primary rebalancing: March, June, September, December (quarter-end)
- Emergency rebalancing: When exit rules trigger
- Rebalancing method: Sell entire position, reallocate to new qualifiers

---

## 3. Risk Management Framework

### 3.1 Position-Level Risk Controls

```
Position Risk Limits:
├── Maximum single position: 10% of portfolio
├── Stop loss: -15% from entry price
├── Maximum holding period: Until next quarterly rebalance (unless exit triggered)
└── Sector concentration: Maximum 30% in any single sector
```

### 3.2 Portfolio-Level Risk Controls

| Risk Metric | Limit | Action Trigger |
|-------------|-------|----------------|
| Maximum Drawdown | -20% | Reduce exposure to 50% cash |
| Portfolio Beta | 0.8 - 1.2 | Rebalance if outside range |
| Sector Concentration | 30% | Force diversification |
| Cash Allocation | 0-20% | Based on opportunity set size |

### 3.3 Correlation Check

Before finalizing portfolio composition:
1. Calculate 1-year correlation matrix for all selected stocks
2. If any pair correlation > 0.80, keep only the higher-Sharpe stock
3. Ensure minimum 4 sectors represented in final portfolio

---

## 4. Implementation Guide

### 4.1 Data Requirements

**Primary Data Source**: Yahoo Finance (via yfinance Python library)

**Required Data Fields**:
- Daily OHLCV (Open, High, Low, Close, Volume)
- 3-month Treasury Bill rates (risk-free rate)
- S&P 500 constituent list

**Data Frequency**: Daily closing prices
**Lookback Period**: 3 years (756 trading days)

### 4.2 Calculation Schedule

```
Monthly Activities (Days 1-3):
├── Download updated price data
├── Recalculate Sharpe ratios for all S&P 500 stocks
├── Update watchlist of qualifying stocks
└── Monitor existing positions for exit triggers

Quarterly Activities (March, June, September, December):
├── Execute full rebalancing
├── Review and update sector allocations
├── Calculate portfolio performance metrics
└── Generate strategy report
```

### 4.3 Python Implementation Skeleton

```python
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class HighSharpeStrategy:
    def __init__(self):
        self.universe = self.get_sp500_tickers()
        self.risk_free_rate = self.get_risk_free_rate()
        self.lookback_days = 756  # 3 years
        
    def calculate_sharpe_ratio(self, prices, risk_free_rate):
        """Calculate 3-year annualized Sharpe ratio"""
        returns = prices.pct_change().dropna()
        excess_returns = returns - (risk_free_rate / 252)
        
        if len(returns) < 252:
            return np.nan
            
        annualized_return = returns.mean() * 252
        annualized_volatility = returns.std() * np.sqrt(252)
        
        if annualized_volatility == 0:
            return np.nan
            
        sharpe = (annualized_return - risk_free_rate) / annualized_volatility
        return sharpe
    
    def get_momentum_signals(self, prices):
        """Calculate momentum filters"""
        current_price = prices.iloc[-1]
        sma_50 = prices.rolling(50).mean().iloc[-1]
        sma_200 = prices.rolling(200).mean().iloc[-1]
        
        return {
            'above_50_sma': current_price > sma_50,
            'above_200_sma': current_price > sma_200,
            'price': current_price
        }
    
    def screen_stocks(self):
        """Main screening function"""
        qualified_stocks = []
        
        for ticker in self.universe:
            try:
                # Download 3 years of data
                stock = yf.Ticker(ticker)
                hist = stock.history(period="3y")
                
                if len(hist) < 756:
                    continue
                
                # Calculate metrics
                sharpe = self.calculate_sharpe_ratio(hist['Close'], self.risk_free_rate)
                momentum = self.get_momentum_signals(hist['Close'])
                avg_volume = hist['Volume'].mean()
                
                # Apply filters
                if (sharpe > 1.0 and 
                    momentum['above_50_sma'] and 
                    avg_volume > 1_000_000):
                    
                    qualified_stocks.append({
                        'ticker': ticker,
                        'sharpe_ratio': sharpe,
                        'price': momentum['price'],
                        'volume': avg_volume
                    })
                    
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
        
        # Sort by Sharpe ratio and return top 10
        qualified_stocks.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
        return qualified_stocks[:10]
    
    def rebalance_portfolio(self, current_portfolio):
        """Execute quarterly rebalancing"""
        new_targets = self.screen_stocks()
        
        # Determine sells (exit rules)
        sells = []
        for position in current_portfolio:
            if self.should_exit(position):
                sells.append(position['ticker'])
        
        # Determine buys
        current_tickers = {p['ticker'] for p in current_portfolio}
        new_tickers = {s['ticker'] for s in new_targets}
        
        buys = list(new_tickers - current_tickers)
        
        return {
            'sells': sells,
            'buys': buys,
            'target_portfolio': new_targets
        }
    
    def should_exit(self, position):
        """Check exit conditions"""
        stock = yf.Ticker(position['ticker'])
        hist = stock.history(period="3y")
        
        # Check Sharpe degradation
        current_sharpe = self.calculate_sharpe_ratio(hist['Close'], self.risk_free_rate)
        if current_sharpe < 0.8:
            return True
        
        # Check trend break
        current_price = hist['Close'].iloc[-1]
        sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
        if current_price < sma_200:
            return True
        
        # Check stop loss
        if position['return_pct'] < -15:
            return True
        
        return False
```

---

## 5. Backtest Expectations (2015-2025)

### 5.1 Historical Context

The backtest period (2015-2025) includes diverse market conditions:
- **2015-2016**: Market correction and recovery
- **2017**: Low volatility bull market
- **2018**: Trade war volatility
- **2019**: Strong recovery
- **2020**: COVID-19 crash and V-shaped recovery
- **2021**: Post-pandemic rally
- **2022**: Inflation-driven bear market
- **2023-2024**: AI-driven tech rally
- **2025**: Current environment

### 5.2 Expected Performance Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Annual Return** | 12-15% | Outperformance through superior stock selection |
| **Sharpe Ratio** | 1.2+ | Higher than S&P 500 (~0.9-1.0) |
| **Maximum Drawdown** | <20% | Risk controls limit downside |
| **Volatility (Annual)** | 12-15% | Lower than S&P 500 (~16-18%) |
| **Win Rate** | 55-60% | Edge from risk-adjusted selection |
| **Beta** | 0.85-0.95 | Defensive characteristics |

### 5.3 Benchmark Comparison

```
Expected Performance vs S&P 500 (2015-2025):

                    Strategy    S&P 500
Annual Return       13.5%       12.0%
Sharpe Ratio        1.25        0.95
Max Drawdown        -18%        -34% (COVID)
Volatility          13%         17%

Risk-Adjusted Alpha: ~2-3% annually
```

### 5.4 Scenario Analysis

| Market Condition | Strategy Response | Expected Outcome |
|------------------|-------------------|------------------|
| Bull Market | Participate via momentum filter | Capture upside with quality stocks |
| Bear Market | Defensive via high-Sharpe selection | Lower drawdown than market |
| High Volatility | Favor low-volatility high-Sharpe names | Relative outperformance |
| Low Volatility | Capture momentum in steady risers | Strong absolute returns |

---

## 6. Why This Strategy Works

### 6.1 Mathematical Foundation

**The Sharpe Ratio Edge**:
The Sharpe ratio is one of the most widely accepted measures of risk-adjusted performance in finance. By selecting stocks with Sharpe ratios > 1.0, we are mathematically selecting investments that have:
- Generated returns exceeding the risk-free rate
- Done so with favorable volatility characteristics
- Demonstrated consistent performance over 3 years

**The Momentum Premium**:
Academic research (Jegadeesh & Titman, 1993; Asness et al., 2014) has consistently shown that stocks with positive price momentum tend to continue outperforming in the medium term. Our 50-day SMA filter captures this effect while avoiding mean-reversion traps.

### 6.2 Behavioral Edge

**Institutional Herding**: High-Sharpe stocks often benefit from institutional accumulation as risk managers favor proven risk-adjusted performers.

**Analyst Coverage**: S&P 500 stocks receive extensive analyst coverage, making Sharpe ratio calculations more reliable due to efficient price discovery.

**Quality Bias**: High Sharpe ratios often correlate with quality factors (profitability, stability), which have shown persistent premia.

### 6.3 Risk Management Benefits

| Mechanism | Benefit |
|-----------|---------|
| 3-Year Lookback | Avoids recency bias, captures through-cycle performance |
| Quarterly Rebalancing | Captures changing market leadership, reduces drift |
| Stop Losses | Hard limits on individual position risk |
| Sector Limits | Prevents concentration risk |
| Correlation Check | Ensures true diversification |

---

## 7. Operational Considerations

### 7.1 Transaction Costs

| Cost Component | Estimate | Impact Mitigation |
|----------------|----------|-------------------|
| Commission | $0 (most brokers) | Use commission-free brokers |
| Bid-Ask Spread | 0.05-0.10% | Large-cap liquidity minimizes impact |
| Market Impact | 0.05-0.15% | 1M+ daily volume requirement |
| **Total per Trade** | **0.10-0.25%** | Quarterly rebalancing keeps turnover manageable |

**Estimated Annual Turnover**: 150-200% (quarterly rebalancing + exits)
**Annual Transaction Cost Impact**: 0.15-0.50%

### 7.2 Tax Considerations

- **Rebalancing Frequency**: Quarterly strikes balance between capturing opportunities and tax efficiency
- **Holding Period**: Most positions held 3-12 months (short-term gains likely)
- **Tax-Loss Harvesting**: Strategy naturally realizes losses via stop-losses
- **Recommendation**: Consider tax-advantaged accounts (IRA, 401k) for implementation

### 7.3 Capacity Constraints

| AUM Level | Consideration |
|-----------|---------------|
| <$1M | No constraints, full flexibility |
| $1M-$10M | Monitor for increased market impact |
| $10M-$50M | May need to expand universe beyond top 10 |
| >$50M | Consider custom index approach |

---

## 8. Monitoring & Reporting

### 8.1 Key Performance Indicators

**Daily Monitoring**:
- Position-level returns vs stop-loss levels
- Portfolio beta vs target range
- Cash allocation

**Monthly Monitoring**:
- Rolling 3-year Sharpe ratio of portfolio
- Sector allocation drift
- Correlation matrix updates

**Quarterly Reporting**:
- Full strategy performance attribution
- Benchmark comparison (S&P 500)
- Risk metric review (VaR, CVaR, max drawdown)
- Rebalancing execution summary

### 8.2 Performance Attribution

```
Return Attribution Framework:
├── Stock Selection (Sharpe-based): Primary alpha source
├── Momentum Timing: Secondary alpha source
├── Risk Management: Drawdown reduction contribution
└── Rebalancing: Mean reversion capture
```

---

## 9. Strategy Risks & Mitigations

### 9.1 Identified Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Factor Crowding** | High-Sharpe stocks become overcrowded | Correlation checks, sector limits |
| **Regime Change** | Sharpe ratios become less predictive | Multi-factor confirmation |
| **Liquidity Crisis** | 1M volume requirement insufficient during stress | Cash buffer, position size limits |
| **Data Quality** | Yahoo Finance data delays/errors | Multiple data source verification |
| **Look-Ahead Bias** | Using information not available at decision time | Strict point-in-time calculations |

### 9.2 Strategy Failure Modes

**Scenario 1**: All high-Sharpe stocks become concentrated in one sector
- *Mitigation*: 30% sector limit forces diversification

**Scenario 2**: Market enters period where momentum consistently fails
- *Mitigation*: Sharpe ratio requirement ensures quality bias persists

**Scenario 3**: Risk-free rate spikes, distorting Sharpe calculations
- *Mitigation*: Use rolling average risk-free rate, monitor absolute returns

---

## 10. Conclusion

The High Sharpe Ratio Momentum Strategy represents a disciplined, mathematically-grounded approach to equity investing. By combining:

1. **Quantitative rigor** (Sharpe ratio selection)
2. **Technical confirmation** (momentum filters)
3. **Systematic risk management** (multiple exit rules)
4. **Regular rebalancing** (quarterly refresh)

This strategy aims to deliver superior risk-adjusted returns while maintaining lower volatility than the broader market.

The 2015-2025 backtest period provides a robust test across multiple market regimes, and the strategy's design principles are backed by decades of academic research and practical application.

---

## Appendix A: Sharpe Ratio Calculation Example

```
Stock: AAPL
Period: January 2022 - December 2024 (3 years)

Step 1: Calculate Daily Returns
- Total trading days: 756
- Starting price: $150.00
- Ending price: $220.00

Step 2: Calculate Annualized Return
Annual Return = (220/150)^(252/756) - 1
              = 1.4667^0.333 - 1
              = 1.136 - 1
              = 13.6%

Step 3: Calculate Annualized Volatility
- Daily return std dev: 1.2%
- Annualized Vol = 1.2% × √252
                 = 1.2% × 15.87
                 = 19.0%

Step 4: Calculate Sharpe Ratio
Risk-free rate: 4.5%
Sharpe = (13.6% - 4.5%) / 19.0%
       = 9.1% / 19.0%
       = 0.48

Result: AAPL does NOT qualify (Sharpe < 1.0)
```

## Appendix B: Rebalancing Calendar 2025

| Quarter | Rebalance Date | Notes |
|---------|---------------|-------|
| Q1 2025 | March 31, 2025 | First competition rebalance |
| Q2 2025 | June 30, 2025 | Mid-year review |
| Q3 2025 | September 30, 2025 | Pre-election positioning |
| Q4 2025 | December 31, 2025 | Year-end rebalancing |

## Appendix C: References

1. Sharpe, W.F. (1966). "Mutual Fund Performance." *Journal of Business*.
2. Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and Selling Losers." *Journal of Finance*.
3. Asness, C.S. et al. (2014). "The Total Return to Momentum." *Critical Finance Review*.
4. Sure Dividend (2024). "High Sharpe Ratio Stocks Methodology."

---

*Strategy Document Version 1.0*
*Created for Trading Competition*
*Last Updated: February 2025*
