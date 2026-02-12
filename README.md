# Trading Systems Performance Analysis

## Overview

This repository hosts multiple algorithmic trading systems for stocks, cryptocurrency, forex, penny stocks, meme coins, and sports betting. All systems are accessible via [https://findtorontoevents.ca/](https://findtorontoevents.ca/)

## Performance Summary by Algorithm

### Top Performing Algorithms (Stocks)

#### Kelly Criterion Analysis (Live Trading Recommendations)

| Algorithm | Win Rate | Avg Win | Avg Loss | Trades | Edge | Recommended % |
|-----------|----------|---------|----------|--------|------|---------------|
| Cursor Genius | 85.71% | 8.11% | 6.22% | 14 | 0.98 | 6.3% |
| ETF Masters | 82.35% | 2.31% | 1.27% | 17 | 1.32 | 6.3% |
| Blue Chip Growth | 80.00% | 5.60% | 3.80% | 25 | 0.98 | 6.3% |
| Sector Rotation | 72.73% | 3.19% | 2.38% | 11 | 0.70 | 6.3% |

#### Backtest Simulation Results

| Algorithm | Total Trades | Avg Win Rate | Avg Return | Sharpe Ratio |
|-----------|--------------|--------------|------------|---------------|
| Composite Rating | 38 | 52.75% | 0.0339 | 17.9140 |
| CAN SLIM | 30 | 38.39% | -0.1406 | -0.0700 |
| Alpha Predator | 73 | 22.11% | -1.0047 | -0.0937 |

#### Current Stock Picks Performance

| Algorithm | Picks | Verified | Wins | Losses | Win Rate | Avg Return |
|-----------|-------|----------|------|--------|----------|------------|
| Technical Momentum | 7 | 0 | 0 | 0 | 0.0% | 0.00% |
| Alpha Predator | 19 | 0 | 0 | 0 | 0.0% | 0.00% |
| Composite Rating | 1 | 0 | 0 | 0 | 0.0% | 0.00% |
| CAN SLIM | 3 | 0 | 0 | 0 | 0.0% | 0.00% |

## Best Performing URLs by Category

### STOCKS

**Best URL:** [https://findtorontoevents.ca/findstocks/portfolio2/picks.html](https://findtorontoevents.ca/findstocks/portfolio2/picks.html)

**Algorithm:** ETF Masters

**Why:** Highest win rate with positive edge

**Performance:**
- Win Rate: 82.35%
- Edge: 1.3185
- Trades: 17

### CRYPTO

**Best URL:** [https://findtorontoevents.ca/findcryptopairs/winners.html](https://findtorontoevents.ca/findcryptopairs/winners.html)

**Algorithm:** Crypto Winners Scanner

**Why:** Real-time analysis of largest crypto pair set

**Description:** 600+ crypto pairs analyzed in real-time

### FOREX

**Best URL:** [https://findtorontoevents.ca/findforex2/](https://findtorontoevents.ca/findforex2/)

**Algorithm:** Forex Scanner

**Why:** Comprehensive major pair coverage

**Description:** Major forex pairs with technical analysis

### MEME COINS

**Best URL:** [https://findtorontoevents.ca/findcryptopairs/meme.html](https://findtorontoevents.ca/findcryptopairs/meme.html)

**Algorithm:** Meme Coin Scanner

**Why:** Dedicated meme coin analysis

**Description:** Specialized meme coin tracking

### PENNY STOCKS

**Best URL:** [https://findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html](https://findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html)

**Algorithm:** Penny Stock Tracker

**Why:** Specialized penny stock scanner

**Description:** Low-price stock opportunities

### SPORTS BETTING

**Best URL:** [https://findtorontoevents.ca/live-monitor/sports-betting.html](https://findtorontoevents.ca/live-monitor/sports-betting.html)

**Algorithm:** Sports Betting Dashboard

**Why:** Live sports betting predictions

**Description:** Real-time sports betting analytics

## All User-Facing URLs

### STOCKS

- [Main](https://findtorontoevents.ca/findstocks/)
- [Research](https://findtorontoevents.ca/findstocks/research/)
- [Alpha](https://findtorontoevents.ca/findstocks/alpha/)
- [Portfolio](https://findtorontoevents.ca/findstocks/portfolio/)
- [Portfolio2](https://findtorontoevents.ca/findstocks/portfolio2/)
- [Penny Stocks](https://findtorontoevents.ca/findstocks/portfolio2/penny-stocks.html)
- [Picks](https://findtorontoevents.ca/findstocks/portfolio2/picks.html)
- [Dashboard](https://findtorontoevents.ca/findstocks/portfolio2/dashboard.html)
- [Leaderboard](https://findtorontoevents.ca/findstocks/portfolio2/leaderboard.html)

### CRYPTO

- [Main](https://findtorontoevents.ca/findcryptopairs/)
- [Portfolio](https://findtorontoevents.ca/findcryptopairs/portfolio/)
- [Winners](https://findtorontoevents.ca/findcryptopairs/winners.html)
- [Meme Coins](https://findtorontoevents.ca/findcryptopairs/meme.html)

### FOREX

- [Main](https://findtorontoevents.ca/findforex2/)
- [Portfolio](https://findtorontoevents.ca/findforex2/portfolio/)

### SPORTS BETTING

- [Main](https://findtorontoevents.ca/live-monitor/sports-betting.html)
- [Predictions](https://findtorontoevents.ca/predictions/sports.html)
- [Dashboard](https://findtorontoevents.ca/predictions/dashboard.html)

## Analysis Methodology

This analysis is based on:

1. **Kelly Criterion Analysis** - Optimal bet sizing based on win rates and edge calculations
2. **Backtest Simulations** - Historical performance testing across multiple threshold levels
3. **Live Pick Tracking** - Real-time monitoring of algorithm recommendations

### Data Sources

- `kelly_algos.json` - Kelly criterion analysis with edge calculations
- `backtest-simulation.json` - Historical backtest results
- `pick-performance.json` - Current live picks performance tracking

### Key Metrics

- **Win Rate**: Percentage of profitable trades
- **Edge**: Mathematical advantage (positive = profitable system)
- **Sharpe Ratio**: Risk-adjusted return metric
- **Recommended %**: Kelly criterion optimal position sizing

---

*Last Updated: 2026-02-12*
*Analysis covers all trading systems hosted at findtorontoevents.ca*
