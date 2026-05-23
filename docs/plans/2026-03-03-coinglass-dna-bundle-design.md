# Coinglass DNA Bundle — Design Document

> **Strategy Registry:** See [ALL_STRATEGIES.md](../ALL_STRATEGIES.md) for the full crypto strategy inventory across all systems.

**Date:** 2026-03-03
**Status:** Approved

## Overview

A new trading system that uses Coinglass/Binance long-short ratio data to generate 8 distinct trading strategies. The system scrapes 4 types of long/short ratios, stores historical data in SQLite, runs signal detection, manages a $10K paper portfolio, and sends updates to Discord #paper-trade.

## Symbols

BTC, ETH, SOL, BNB, DOGE (USDT perpetual futures pairs)

## Data Source — 3-Source Failover Chain

| Priority | Source | Auth | Endpoints |
|----------|--------|------|-----------|
| 1 | Binance Futures API | None (free) | globalLongShortAccountRatio, topLongShortAccountRatio, topLongShortPositionRatio, takerlongshortRatio |
| 2 | Coinglass open-api v2 | None (public, may rate-limit) | /public/v2/long_short |
| 3 | OKX public API | None (free) | /api/v5/rubik/stat/contracts-long-short-account-ratio |

All 4 ratio types per symbol:
- **Global Account L/S Ratio** — all accounts long vs short
- **Top Trader Account L/S Ratio** — top 20% by margin balance
- **Top Trader Position L/S Ratio** — position sizes of top traders
- **Taker Buy/Sell Ratio** — new taker orders long vs short

## Directory Structure

```
coinglass_strategies/
├── __init__.py
├── data_fetcher.py          # 3-source failover
├── ratio_store.py           # SQLite storage + rolling history
├── strategies/
│   ├── __init__.py
│   ├── extreme_reversion.py
│   ├── top_trader_divergence.py
│   ├── ratio_momentum.py
│   ├── cross_exchange_spread.py
│   ├── leverage_adjusted.py
│   ├── funding_confirmation.py
│   ├── sentiment_index.py
│   └── spike_detection.py
├── signal_engine.py         # Runs all 8 strategies
├── paper_portfolio.py       # $10K virtual portfolio
├── discord_notify.py        # #paper-trade webhook
├── scanner.py               # CLI: --scan, --portfolio, --backtest
└── data/
    ├── coinglass.db          # SQLite (ratios + portfolio + signals)
    └── active_picks.json     # Cross-aggregation compatible
```

## Strategy Definitions

### S1: Extreme Ratio Reversion (`coinglass_extreme_reversion`)
- **Logic:** Compute 24h rolling Z-score of Taker L/S ratio. When |Z| > 2, expect mean reversion.
- **Direction:** Contrarian — Z > 2 (too many longs) → SHORT; Z < -2 (too many shorts) → LONG
- **Confidence:** 0.55 + 0.05 * min(|Z| - 2, 4) → range [0.55, 0.75]
- **Rationale:** Retail takers herd into one side; extreme positioning gets liquidated.

### S2: Top-Trader Divergence (`coinglass_whale_divergence`)
- **Logic:** Compare Top-Trader Account ratio vs Global Account ratio. If sign(top - 1) ≠ sign(global - 1) and |diff| > 0.15, follow whales.
- **Direction:** Follow Top-Trader side
- **Confidence:** 0.60 + 0.10 * min(|diff| / 0.3, 2) → range [0.60, 0.80]
- **Rationale:** Top 20% traders (by margin) anticipate moves before retail.

### S3: Ratio Momentum (`coinglass_ratio_momentum`)
- **Logic:** Compute Δratio per period, apply SMA-3. If SMA-3 > 0 for ≥3 consecutive windows → bullish flow.
- **Direction:** Trend-following — positive momentum → LONG, negative → SHORT
- **Confidence:** 0.50 + 0.05 * consecutive_positive_windows → range [0.50, 0.65]
- **Rationale:** Position-flow momentum precedes price momentum in leveraged markets.

### S4: Cross-Exchange Spread (`coinglass_exchange_spread`)
- **Logic:** Compare same ratio between Binance and OKX. |spread| > 0.2 → divergence signal.
- **Direction:** Follow the exchange with higher open interest
- **Confidence:** 0.50 + 0.05 * min(|spread| / 0.2, 2) → range [0.50, 0.60]
- **Rationale:** Different user bases (retail vs institutional) create arbitrage pressure.

### S5: Leverage-Adjusted Ratio (`coinglass_leverage_squeeze`)
- **Logic:** Multiply raw ratio by funding rate sign as leverage proxy. When adjusted ratio extreme → squeeze risk.
- **Direction:** Contrarian — over-leveraged side gets liquidated
- **Confidence:** 0.55 + 0.05 * severity → range [0.55, 0.70]
- **Rationale:** High leverage + directional bias = cascade liquidation risk.

### S6: Funding-Rate Confirmation (`coinglass_funding_confluence`)
- **Logic:** Ratio > 1.15 AND funding > 0 → confirmed bullish; Ratio < 0.85 AND funding < 0 → confirmed bearish.
- **Direction:** Confirms dominant side (trend-following with conviction)
- **Confidence:** 0.60 + 0.05 * (agreement_strength) → range [0.60, 0.75]
- **Rationale:** Funding rate is a market-clearing mechanism; when it aligns with ratio, conviction is higher.

### S7: Sentiment Composite Index (`coinglass_sentiment_composite`)
- **Logic:** Weighted index: 40% top-trader + 30% taker + 20% global + 10% position. Normalize each to [0,1] over 30d window. SMA-5 smoothing.
- **Direction:** Index > 0.7 → LONG; Index < 0.3 → SHORT
- **Confidence:** 0.55 + 0.10 * |index - 0.5| → range [0.55, 0.70]
- **Rationale:** Composite reduces noise from any single metric.

### S8: Spike Detection (`coinglass_spike_detector`)
- **Logic:** Any ratio changes > 30% within a 15-minute window → event-driven alert.
- **Direction:** Trend-following (spike direction)
- **Confidence:** 0.50 + 0.05 * (spike_magnitude / 0.3) → range [0.50, 0.65]
- **Rationale:** Sudden positioning changes correlate with large on-chain or news events.

## Paper Portfolio

- **Starting capital:** $10,000
- **Position sizing:** 2% equity risk per trade, ATR-based
- **Max concurrent positions:** 5
- **TP/SL:** 1.5x ATR take-profit, 1.0x ATR stop-loss
- **Hold limit:** 48 hours (short-term sentiment signals)
- **Tracking:** SQLite tables: `positions`, `closed_trades`, `portfolio_snapshots`

## Discord Integration

- **Webhook:** #paper-trade channel
- **Environment variable:** `DISCORD_WEBHOOK_PAPERTRADE`
- **New signal alerts:** Immediate (embed with strategy name, symbol, direction, entry, TP/SL, ratios)
- **Portfolio summary:** Every 2 hours (equity, win rate, open positions, P&L, top/worst trades)
- **Ratio snapshot:** Included in portfolio summary (current ratios for all 5 symbols)

## GitHub Actions Workflow

```yaml
name: Coinglass DNA Scanner
on:
  schedule:
    - cron: '*/15 * * * *'    # Every 15 min: fetch + scan
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install requests
      - run: python -m coinglass_strategies.scanner --scan --portfolio
        env:
          DISCORD_WEBHOOK_PAPERTRADE: ${{ secrets.DISCORD_WEBHOOK_PAPERTRADE }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Coinglass scan [$(date -u +'%Y-%m-%d %H:%M UTC')]"
          file_pattern: "coinglass_strategies/data/*"
```

## Cross-Aggregation Integration

Output `coinglass_strategies/data/active_picks.json` in standard format:
```json
[{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "confidence": 0.72,
  "entry_price": 67500.0,
  "take_profit": 69800.0,
  "stop_loss": 66200.0,
  "strategy": "coinglass_whale_divergence",
  "source": "coinglass_strategies",
  "generated_at": "2026-03-03T12:00:00Z",
  "ratios": {
    "taker": 1.23,
    "global_account": 1.05,
    "top_trader_account": 0.89,
    "top_trader_position": 0.91
  }
}]
```

Add to `cross_aggregation/aggregator.py` source list:
```python
"coinglass_strategies/data/active_picks.json"
```
