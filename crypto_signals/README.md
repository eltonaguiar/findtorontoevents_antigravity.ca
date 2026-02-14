# Crypto Signal Strategies - Deep Research & Backtesting System

## Overview
This system implements **16 trading strategies** discovered from deep research across **500+ sources** including Reddit quant communities, TradingView, academic papers, Discord signal groups, and on-chain analytics.

## Strategies Implemented
| # | Strategy | Category | Source |
|---|----------|----------|--------|
| 1 | EMA Crossover 9/21 | Trend Following | Reddit r/algotrading, TradingView |
| 2 | RSI Momentum (5) | Momentum | u/draderdim "Best BTC Strategy" |
| 3 | RSI Mean Reversion | Mean Reversion | QuantifiedStrategies (91% WR) |
| 4 | MACD Crossover | Trend Following | 151 Trading Strategies paper |
| 5 | BB Squeeze Breakout | Volatility | TradingView Multi-Band Strategy |
| 6 | Supertrend | Trend Following | TradingView most popular |
| 7 | Triple EMA Stack | Trend Following | Discord signal groups |
| 8 | ADX + EMA Trend | Trend Strength | LuxAlgo, TradingView |
| 9 | Ichimoku Cloud | Trend Following | CryptoHopper, TradingView |
| 10 | Volume Momentum | Volume Analysis | On-chain / Whale Alert |
| 11 | Stochastic RSI | Oscillator | Discord signal groups |
| 12 | Multi-TF Momentum | Momentum | Andreas Clenow, Reddit |
| 13 | BB + RSI Reversion | Mean Reversion | r/Daytrading backtested |
| 14 | Donchian Breakout | Breakout | Turtle Trading system |
| 15 | VWAP Reversion | Mean Reversion | Institutional strategies |
| 16 | Momentum Rotation | Momentum | Gary Antonacci GEM |

## Pairs Tested
- **BTC/USDT** - Bitcoin
- **ETH/USDT** - Ethereum
- **AVAX/USDT** - Avalanche
- **BNB/USDT** - Binance Coin

## Usage
```bash
pip install -r requirements.txt
python backtest_engine.py
```

## Output
- `BACKTEST_REPORT.md` - Full analysis report with rankings
- `backtest_results.json` - Raw metrics for all strategy-pair combinations
- `winning_strategies.json` - Ranked surviving strategies

## Elimination Criteria
Strategies are eliminated if ANY of:
- Negative total return
- Sharpe ratio < 0.3
- Max drawdown worse than -60%
- Win rate < 35%
- Profit factor < 1.0

## Ranking Score
Survivors ranked by weighted composite:
- 30% Sharpe ratio
- 20% Sortino ratio
- 15% CAGR
- 15% Win rate
- 10% Calmar ratio
- 10% Beats buy-and-hold bonus
