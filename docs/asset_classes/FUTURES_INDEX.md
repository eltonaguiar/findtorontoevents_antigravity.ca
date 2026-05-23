# Futures & Index — Asset Class Reference

## Overview
Index and commodity futures are our **highest-confidence** asset class. Deep liquidity, 23-hour trading, and well-documented mean-reversion edges make them ideal for systematic strategies.

## Symbol Universe
| Symbol | Name | Exchange | Liquidity |
|--------|------|----------|-----------|
| ES=F | S&P 500 E-mini | CME | Ultra-high |
| NQ=F | Nasdaq 100 E-mini | CME | Ultra-high |
| YM=F | Dow E-mini | CBOT | High |
| CL=F | Crude Oil WTI | NYMEX | High |
| GC=F | Gold | COMEX | High |
| SI=F | Silver | COMEX | Medium |
| ZN=F | 10-Year T-Note | CBOT | High |

## Existing Portfolios (from `multi_asset/portfolio_defs.py`)

### 1. idx_connors_rsi2
- **Strategy:** Connors RSI-2 (★★★ PROVEN)
- **Symbols:** ES=F, NQ=F, YM=F
- **Logic:** RSI(2) < 5 → BUY, RSI(2) > 95 → SELL. Mean reversion on oversold dips.
- **Evidence:** 75.7% WR on SPY (p = 6×10⁻⁶, Sharpe 4.84). Index futures are direct proxy.
- **Risk:** SL 1.5× ATR, TP 3.0× ATR, max 10-day hold, 2% risk/trade

### 2. idx_mean_revert
- **Strategy:** Bollinger Mean Reversion
- **Symbols:** ES=F, NQ=F, CL=F, GC=F, SI=F, ZN=F
- **Logic:** Buy below lower BB + RSI(14) < 30. Sell above upper BB + RSI(14) > 70.
- **Risk:** SL 2.0× ATR, TP 2.5× ATR, max 7-day hold, 1.5% risk/trade

### 3. idx_trend_follow
- **Strategy:** EMA Stack Momentum
- **Symbols:** ES=F, NQ=F, CL=F, GC=F
- **Logic:** EMA 9 > 21 > 50 > 200 aligned → LONG. Reverse for SHORT.
- **Risk:** SL 2.5× ATR, TP 5.0× ATR, max 20-day hold, 2% risk/trade

## Additional Strategies to Test
From `baby_strategies/` and `alpha_engine/`:
- `vol_risk_premium` — Sell volatility when VIX term structure in contango
- `dynamic_momentum_scaling` — Scale position size by momentum strength
- `smart_money_fvg` — Fair value gaps from order flow analysis
- `kalman_mean_reversion` — Kalman filter for adaptive mean-reversion bands

## Data Source
- **Yahoo Finance** via `yfinance` — daily OHLCV for all symbols
- **Trading hours:** ES/NQ: Sun 6pm–Fri 5pm ET (nearly 24h). CL/GC similar.

## Risk Parameters
- Max portfolio allocation: 10% of capital to futures
- Max concurrent positions: 6 across all futures portfolios
- Margin requirement: ~$12K per ES contract, ~$18K per NQ
- Position sizing: Fixed fractional (2% risk per trade)

## Filter Criteria (from scoring engine)
- Freshness ≤ 12h
- Sharpe ≥ 1.2
- Max drawdown ≤ 10%
- Position size ≤ 2% of capital

## Action Items
- [ ] Run Connors RSI-2 backtest on ES=F/NQ=F using `alpha_engine/backtest_new_strategies.py`
- [ ] Wire futures symbols into `alpha_engine/scanner.py`
- [ ] Set up GitHub Actions scan (market hours: Mon-Fri, 9:30am-4pm ET + overnight session)
- [ ] Forward-test for 30 days before going live
- [ ] Evaluate statistical significance (target p < 0.01)
