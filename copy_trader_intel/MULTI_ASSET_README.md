# Multi-Asset Copytrader & Backtesting Pipeline

Extends the crypto-only copytrader infrastructure to **forex, futures, stocks, and commodities**.

## Architecture

```
Scrapers → Standardized Pick → Backtester (TP/SL Grid) → Variation Portfolios → Scorer → Audit Dashboard
                                                                                           findtorontoevents.ca/audit
```

## Quick Start

```bash
# 1. Scan all asset classes for signals
python copy_trader_intel/multi_asset_copytrader_scraper.py

# 2. Run walk-forward backtests
python copy_trader_intel/multi_asset_backtester.py

# 3. Build variation portfolios (conservative/moderate/aggressive/scalper/swing)
python copy_trader_intel/variation_portfolio_builder.py

# 4. Score everything and build leaderboard
python copy_trader_intel/multi_asset_scorer.py
```

## Files

| File | Purpose |
|------|---------|
| `multi_asset_copytrader_scraper.py` | Scans forex/futures/stocks for signals using proven strategies |
| `multi_asset_backtester.py` | Walk-forward backtester with TP/SL grid search |
| `variation_portfolio_builder.py` | Creates 7 portfolio variants from source picks |
| `multi_asset_scorer.py` | Scores variants, builds leaderboard, generates audit data |
| `multi_asset_config.json` | Centralized config for all thresholds and parameters |

## Strategies

### Forex
- **RSI-2 Mean Reversion** — Backtest: 57.6% WR, +32% PnL on 118 trades
- **Z-Score 200d Fade** — Backtest: 68.3% WR on 167 trades (p<0.001)
- **Carry Trade Momentum** — Burnside et al. (2011): Sharpe 0.9-1.2

### Futures / Commodities
- **Connors RSI-2** — 75.7% WR on SPY (p=6×10⁻⁶, Sharpe 4.84)
- **Bollinger Mean Reversion** — BB(20,2) with RSI confirmation
- **EMA Stack Momentum** — 9>21>50>200 aligned trend following

### Stocks
- **RSI-2 Pullback** — Connors RSI-2 equity variant (uptrend only)
- **EMA Golden Cross** — 9/21 EMA crossover with 50 EMA filter

## Portfolio Variants

| Variant | Confidence Gate | TP/SL Style | Description |
|---------|----------------|-------------|-------------|
| Conservative | 70% | Tight TP, wide SL | High conviction only |
| Moderate | 60% | Standard | Balanced risk/reward |
| Aggressive | 50% | Wide TP, tight SL | More signals accepted |
| Scalper | 55% | Very tight | Quick in/out |
| Swing | 65% | Wide | Multi-day holds |
| Long Only | 60% | Standard | No short positions |
| Multi-Asset Balanced | 60% | Standard | Equal alloc across classes |

## Scoring

Composite score (0-100) with grade (A-F):
- **Win Rate**: 30% weight
- **Profit Factor**: 25% weight
- **Sharpe Ratio**: 25% weight
- **Max Drawdown (inverse)**: 20% weight

## Dependencies

```
pip install yfinance requests
```

## Data Flow

```
multi_asset_copytrader_scraper.py
  → data/multi_asset_picks.json
  → data/multi_asset_forex_picks.json
  → data/multi_asset_futures_picks.json
  → data/multi_asset_equity_picks.json

multi_asset_backtester.py
  → data/multi_asset_backtest_results.json

variation_portfolio_builder.py
  → data/variation_portfolios.json

multi_asset_scorer.py
  → data/leaderboard.json
  → data/multi_asset_audit_scores.json  (audit pipeline compatible)
```
