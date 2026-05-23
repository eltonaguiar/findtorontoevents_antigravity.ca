# Stocks — Asset Class Reference

## Overview
Blue-chip and growth stocks benefit from the same mean-reversion and momentum strategies proven on index futures. Higher idiosyncratic risk than futures but more symbol diversity.

## Symbol Universe
| Category | Symbols |
|----------|---------|
| Mega-cap tech | AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA |
| Financials | JPM, V, GS, BAC |
| Healthcare | UNH, JNJ, LLY |
| Energy | XOM, CVX |
| Growth | PLTR, SOFI, IONQ, SNOW |

## Existing Portfolios (from `multi_asset/portfolio_defs.py`)

### 1. stk_connors_rsi2
- **Strategy:** Connors RSI-2 (★★★ PROVEN)
- **Symbols:** AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V
- **Logic:** RSI(2) < 5 → BUY. Documented 75%+ WR on large-cap equities.
- **Risk:** SL 1.5× ATR, TP 3.0× ATR, max 10-day hold, 2% risk/trade

### 2. stk_momentum
- **Strategy:** Breakout ATR
- **Symbols:** AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V
- **Logic:** 20-day high breakout with ATR expansion > 1.5× and volume confirmation.
- **Risk:** SL 2.0× ATR, TP 4.0× ATR, max 15-day hold, 2% risk/trade

## Strategy Modules
- `alpha_engine/equity_strategies.py` — 6 strategies:
  1. `momentum_factor_12m` — Jegadeesh & Titman (1993), buy 12-month winners
  2. `mean_reversion_rsi` — RSI oversold bounce with SMA filter
  3. `breakout_atr` — Volume-confirmed ATR breakout
  4. `meme_stock_momentum` — Social sentiment + volume spike
  5. `penny_volume_surge` — Sub-$5 + 2× volume (see PENNY_STOCKS.md)
  6. `quality_factor` — ROE + debt/equity + earnings stability

## Data Source
- **Yahoo Finance** via `yfinance` — daily/weekly OHLCV
- **Trading hours:** Mon-Fri 9:30am-4pm ET

## Risk Parameters
- Max portfolio allocation: 15% of capital to stocks
- Max concurrent positions: 8 across all stock portfolios
- Position sizing: 2% risk per trade
- Avoid earnings week (add filter for earnings calendar)

## Filter Criteria
- Freshness ≤ 12h
- Sharpe ≥ 1.2
- Max drawdown ≤ 10%
- Minimum average volume > 1M shares/day

## Action Items
- [ ] Backtest Connors RSI-2 on AAPL/MSFT/NVDA/GOOGL individually
- [ ] Add earnings calendar filter to avoid holding through earnings
- [ ] Wire stock symbols into multi-asset scanner
- [ ] Test momentum_factor_12m with current market data
- [ ] Forward-test 30 days
