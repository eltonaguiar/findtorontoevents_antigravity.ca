# ETFs — Asset Class Reference

## Overview
ETFs provide diversified exposure to sectors, bonds, and commodities. Strategies focus on sector rotation (buy strong, sell weak) and macro regime switches (risk-on vs risk-off). Lower alpha potential than individual stocks/futures but lower risk.

## Symbol Universe
| Symbol | Name | Category |
|--------|------|----------|
| SPY | S&P 500 | Broad market |
| QQQ | Nasdaq 100 | Tech-heavy |
| IWM | Russell 2000 | Small-cap |
| XLK | Technology Select | Sector |
| XLF | Financial Select | Sector |
| XLE | Energy Select | Sector |
| XLV | Healthcare Select | Sector |
| GLD | Gold | Commodity |
| SLV | Silver | Commodity |
| TLT | 20+ Year Treasury | Bond |
| HYG | High-Yield Corporate | Bond |

## Existing Portfolios (from `multi_asset/portfolio_defs.py`)

### 1. etf_sector_rotation
- **Strategy:** EMA Stack Momentum
- **Symbols:** SPY, QQQ, XLK, XLF, XLE, GLD, IWM
- **Logic:** Rotate into strongest sector ETFs based on EMA alignment + relative strength.
- **Risk:** SL 2.0× ATR, TP 4.0× ATR, max 20-day hold, 2% risk/trade

### 2. etf_bond_equity
- **Strategy:** VIX Spike Reversal
- **Symbols:** SPY, TLT, QQQ, GLD
- **Logic:** When VIX spikes >20% and reverses, rotate from bonds to equities.
- **Risk:** SL 2.5× ATR, TP 4.0× ATR, max 15-day hold, 2% risk/trade

## Strategy Sources
- `alpha_engine/equity_strategies.py` — sector rotation module
- Potential additions from `baby_strategies/`:
  - `sector_momentum_7d` — 7-day relative strength ranking
  - `etf_flow_rotation` — Fund flow data → allocation shift

## Data Source
- **Yahoo Finance** via `yfinance` — daily OHLCV
- **Trading hours:** Mon-Fri 9:30am-4pm ET

## Risk Parameters
- Max portfolio allocation: 15% of capital to ETFs
- Max concurrent positions: 4
- Position sizing: 2% risk per trade
- Minimum 5-day hold to avoid churn

## Filter Criteria
- Sharpe ≥ 1.0
- Max drawdown ≤ 12%
- Conservative profile adds volatility penalty for high-beta ETFs (IWM, XLE)
- Minimum holding period: 5 days

## Action Items
- [ ] Backtest sector rotation (XLK vs XLF vs XLE) over 2020-2026
- [ ] Implement VIX-based regime switch using ^VIX data from yfinance
- [ ] Wire ETF symbols into multi-asset scanner
- [ ] Add relative strength ranking across all ETFs
- [ ] Forward-test 30 days
