# Forex — Asset Class Reference

## Overview
Forex is the most liquid market globally. Strategies focus on carry trade (decades of documented alpha), session-based breakouts, and mean reversion. Slower-moving than crypto/stocks — driven by central bank policy divergence.

## Symbol Universe
| Symbol | Pair | Category | Carry Direction |
|--------|------|----------|----------------|
| EURUSD=X | EUR/USD | Major | Short (ECB < Fed) |
| USDJPY=X | USD/JPY | Major | Long (yield diff) |
| GBPUSD=X | GBP/USD | Major | Neutral |
| AUDUSD=X | AUD/USD | Commodity | Long (carry) |
| NZDUSD=X | NZD/USD | Commodity | Long (carry) |
| USDCAD=X | USD/CAD | Commodity | Short |
| EURGBP=X | EUR/GBP | Cross | Neutral |

## Existing Portfolios (from `multi_asset/portfolio_defs.py`)

### 1. fx_mean_revert
- **Strategy:** Bollinger Mean Reversion
- **Symbols:** EURUSD=X, USDJPY=X, GBPUSD=X, AUDUSD=X, NZDUSD=X
- **Logic:** Bollinger band mean reversion on major pairs. Tighter TP/SL for forex.
- **Risk:** SL 1.5× ATR, TP 2.0× ATR, max 14-day hold, 1% risk/trade

### 2. fx_carry
- **Strategy:** Carry Trade Momentum
- **Symbols:** USDJPY=X, AUDUSD=X, NZDUSD=X, GBPUSD=X
- **Logic:** Long high-yield vs low-yield when 20d momentum confirms. JPY pairs primary.
- **Evidence:** Burnside et al. (2011) — Sharpe 0.5-0.8 raw, 0.9-1.2 with momentum filter
- **Risk:** SL 2.0× ATR, TP 3.0× ATR, max 30-day hold, 1% risk/trade

## Strategy Module: `alpha_engine/forex_strategies.py`
6 strategies with academic backing:
1. `carry_trade_momentum` — Long high-yield + momentum filter (Burnside 2011)
2. `london_breakout` — Range breakout at London open (7-8am GMT)
3. `mean_reversion_bollinger` — BB bounce on daily timeframe
4. `ai_cci_divergence` — CCI indicator divergence with trend
5. `session_momentum` — Trade in direction of Asian session range break
6. `bollinger_squeeze_breakout` — Low-volatility squeeze → expansion trade

## Data Source
- **Yahoo Finance** via `yfinance` — daily OHLCV (free, delayed)
- **OANDA** — potential upgrade for real-time streaming (requires API key)
- **Trading hours:** 24/5 (Sun 5pm ET – Fri 5pm ET)

## Risk Parameters
- Max portfolio allocation: 10% of capital to forex
- Max concurrent positions: 5 across all forex portfolios
- Position sizing: 1% risk per trade (forex volatility is lower)
- Leverage: None for paper trading; max 10:1 for live

## Filter Criteria
- Entry within last 4h (high-frequency edge)
- Realized P&L ≥ 0.5% per trade
- Volatility regime NORMAL (ADX < 20)
- Sharpe ≥ 1.0

## Action Items
- [ ] Backtest carry_trade_momentum on USDJPY/AUDUSD (2020-2026)
- [ ] Backtest london_breakout with intraday data (if available)
- [ ] Wire forex symbols into multi-asset scanner
- [ ] Add session-awareness (only scan during relevant sessions)
- [ ] Forward-test 30 days
