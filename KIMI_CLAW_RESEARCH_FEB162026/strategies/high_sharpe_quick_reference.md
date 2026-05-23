# High Sharpe Ratio Momentum Strategy - Quick Reference Card

## Strategy at a Glance

| Element | Specification |
|---------|---------------|
| **Name** | High Sharpe Ratio Momentum |
| **Universe** | S&P 500 |
| **Selection** | Top 10 by 3-year Sharpe ratio |
| **Weighting** | Equal weight (10% each) |
| **Rebalancing** | Quarterly (Mar, Jun, Sep, Dec) |
| **Target Return** | 12-15% annually |
| **Target Sharpe** | 1.2+ |

---

## Entry Checklist

- [ ] Stock is S&P 500 constituent
- [ ] 3-year Sharpe ratio > 1.0
- [ ] Price above 50-day moving average
- [ ] Volume > 1M shares/day

---

## Exit Triggers (ANY)

- ⚠️ Sharpe ratio drops below 0.8
- ⚠️ Price falls below 200-day moving average
- ⚠️ Position loss reaches -15%
- ⚠️ Quarterly rebalancing date

---

## Risk Limits

| Level | Limit | Action |
|-------|-------|--------|
| Position | 10% max | Trim if exceeded |
| Stop Loss | -15% | Sell immediately |
| Sector | 30% max | Force diversification |
| Portfolio Drawdown | -20% | Move 50% to cash |

---

## Quarterly Workflow

```
Week Before Rebalance:
├── Download latest price data
├── Recalculate all Sharpe ratios
├── Generate new top 10 list
└── Check correlation matrix

Rebalance Day:
├── Sell positions triggering exit rules
├── Sell positions dropping out of top 10
├── Buy new qualifiers
└── Verify sector limits

Week After:
├── Update tracking spreadsheet
├── Review execution quality
└── Document rationale
```

---

## Key Formulas

**Sharpe Ratio:**
```
(Return - Risk Free Rate) / Volatility
```

**Position Size:**
```
Portfolio Value × 10% = Target Position Value
```

**Annualized Return:**
```
(End Price / Start Price)^(252/days) - 1
```

---

## 2025 Rebalance Dates

| Quarter | Date |
|---------|------|
| Q1 | March 31, 2025 |
| Q2 | June 30, 2025 |
| Q3 | September 30, 2025 |
| Q4 | December 31, 2025 |

---

## Performance Targets

| Metric | Target | Benchmark |
|--------|--------|-----------|
| Annual Return | 12-15% | S&P 500: ~12% |
| Sharpe Ratio | 1.2+ | S&P 500: ~0.95 |
| Max Drawdown | <20% | S&P 500: ~34% |
| Volatility | 12-15% | S&P 500: ~17% |

---

## Quick Screening Python

```python
import yfinance as yf
import pandas as pd

def quick_screen(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="3y")
    
    # Sharpe calculation
    returns = hist['Close'].pct_change()
    sharpe = (returns.mean() * 252) / (returns.std() * (252**0.5))
    
    # Momentum
    above_50 = hist['Close'][-1] > hist['Close'].rolling(50).mean()[-1]
    
    # Volume
    volume_ok = hist['Volume'].mean() > 1_000_000
    
    return {
        'ticker': ticker,
        'sharpe': round(sharpe, 2),
        'above_50_sma': above_50,
        'volume_ok': volume_ok,
        'qualified': sharpe > 1.0 and above_50 and volume_ok
    }
```

---

## Contact & Updates

- **Strategy Owner**: Trading Competition Team
- **Review Cycle**: Quarterly
- **Document Version**: 1.0
- **Last Updated**: February 2025
