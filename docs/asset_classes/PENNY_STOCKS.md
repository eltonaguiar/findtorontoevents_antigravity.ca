# Penny Stocks — Asset Class Reference

## Overview
Penny stocks (< $5) offer asymmetric upside but extreme noise. Treat each trade like a lottery ticket — ultra-strict risk management (≤ 0.5% capital per trade). Volume breakouts are the primary edge.

## Symbol Universe
| Symbol | Name | Price Range | Avg Volume |
|--------|------|------------|------------|
| SOFI | SoFi Technologies | $5-15 | High |
| NIO | NIO Inc | $3-10 | High |
| MARA | Marathon Digital | $5-25 | High |
| RIOT | Riot Platforms | $5-20 | Medium |
| IONQ | IonQ | $5-30 | Medium |
| PLTR | Palantir | $15-30 | Ultra-high |

> Note: Some of these have grown beyond $5. The scanner should dynamically filter by current price.

## Existing Portfolio (from `multi_asset/portfolio_defs.py`)

### 1. penny_volume_breakout
- **Strategy:** Breakout ATR
- **Symbols:** SOFI, PLTR, NIO, MARA, RIOT, IONQ
- **Logic:** 20-day high breakout on penny stocks with 2×+ volume surge.
- **Risk:** SL 2.5× ATR, TP 5.0× ATR, max 7-day hold, 1.5% risk/trade

## Strategy Sources
- `alpha_engine/equity_strategies.py`:
  - `penny_volume_surge` — Sub-$5 + 2× volume + above 20d SMA
  - `meme_stock_momentum` — Social sentiment + volume spike
- `baby_strategies/`:
  - `adaptive_momentum` — Short-term momentum with adaptive lookback
  - `bb_squeeze_breakout` — Bollinger squeeze → expansion on low-float stocks
  - Various ROC strategies (`price_roc_*.py`)
- **Existing workflow:** `.github/workflows/penny-stock-picks.yml` — runs weekdays 12:00 UTC
- **Output:** `findstocks/portfolio2/data/penny_picks_latest.json`

## Data Source
- **Yahoo Finance** via `yfinance` — daily OHLCV
- **Penny stock screener:** Could add finviz/stockanalysis filtering for sub-$5, >200K volume

## Risk Parameters (STRICT)
- Max portfolio allocation: **3%** of capital (high-risk class)
- Max concurrent positions: 3
- Position sizing: **0.5-1.5%** risk per trade (treat as options)
- Max drawdown tolerance: 30% per trade (higher than other classes due to volatility)
- Stop at 2.5× ATR — no exceptions

## Filter Criteria
- Volume ≥ 200K shares on entry day
- Entry price ≤ $5 (or ≤ $10 for "low-cap growth")
- Max drawdown ≤ 30%
- Aggressive profile: +0.15 boost to profit weight
- Conservative profile: caps position to 0.5% capital

## Action Items
- [ ] Review output of existing penny-stock-picks.yml workflow for accuracy
- [ ] Backtest penny_volume_surge strategy on 2024-2026 data
- [ ] Add dynamic price filter (exclude symbols that grew past $10)
- [ ] Wire into multi-asset scanner with strict risk caps
- [ ] Forward-test 30 days with paper trades only
