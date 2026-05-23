# Paper Trading Portfolio System — Design Document

**Date:** 2026-03-04
**Status:** Approved with enhancements

## Overview

A modular paper trading system that uses 10 new strategies built on free crypto data APIs, tracked across 9 portfolios (6 by strategy type + 3 by conviction tier), with results posted to Discord `#paper-trade` every 4 hours and on trade events.

## Architecture

```
Strategies (10 modules) → Portfolio Manager (9 portfolios) → Discord Reporter (#paper-trade)
                                    ↓
                           SQLite DB + JSON snapshots
                                    ↓
                         GitHub Actions (every 4h) → commit + push
```

## Strategies (Free Data Sources)

| # | Strategy | Source | Type | Edge |
|---|----------|--------|------|------|
| 1 | DeFi TVL Momentum | DeFiLlama | On-Chain | TVL growing >10%/week |
| 2 | Fear & Greed Contrarian | Alternative.me | Sentiment | Buy F&G ≤20, sell ≥80 |
| 3 | Funding Rate Carry | Binance Futures | Derivatives | Short overheated perps |
| 4 | Volume Breakout | CoinGecko | Technical | 3x vol + above 20d SMA |
| 5 | Stablecoin Supply Ratio | CoinGecko | On-Chain | SSR declining = buying power |
| 6 | Exchange Netflow | CryptoQuant | On-Chain | Large outflows = accumulation |
| 7 | RSI-2 Mean Reversion | Binance Klines | Technical | Connors RSI-2 on crypto |
| 8 | Whale Accumulation | CoinGecko+Binance | Hybrid | Unusual volume + price dip |
| 9 | Cross-Exchange Spread | Binance+Kraken | Arbitrage | Price divergence |
| 10 | BTC Dominance Rotation | CoinGecko | Macro | BTC.D falling → alts |

## Portfolios ($10K each, $90K total)

### By Strategy Type (6)
- technical: RSI-2, Volume Breakout
- sentiment: Fear & Greed Contrarian
- onchain: DeFi TVL, Stablecoin Supply, Exchange Netflow
- derivatives: Funding Rate Carry
- smart_money: Whale Accumulation, Cross-Exchange Spread
- macro: BTC Dominance Rotation

### By Conviction Tier (3)
- high_conviction: 3+ strategies agree
- medium_conviction: 2 strategies agree
- speculative: single strategy, confidence ≥ 0.7

## Risk Management
- 2% of portfolio equity per trade
- ATR-based stop-loss distance for position sizing
- Max 10% exposure per symbol per portfolio
- Max drawdown tracking per portfolio
- Transaction costs: 0.7% crypto round-trip

## Data Persistence
- SQLite DB (paper_trading/data/paper.db) as authoritative store
- JSON snapshots exported for Git commits and Discord
- Pydantic schema validation on all picks

## Discord Webhook
- Channel: #paper-trade
- Secret: DISCORD_WEBHOOK_PAPER_TRADE
- Posts: new entries, exits (TP/SL/expiry), 4-hourly portfolio summaries
- Rate-limit handling with retry/backoff

## GitHub Actions
- Every 4 hours via cron
- Commits JSON snapshots to repo
- Uses GH_PAT for push access

## File Structure
```
paper_trading/
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── defi_tvl_momentum.py
│   ├── fear_greed_contrarian.py
│   ├── funding_rate_carry.py
│   ├── volume_breakout.py
│   ├── stablecoin_supply.py
│   ├── exchange_netflow.py
│   ├── rsi2_mean_reversion.py
│   ├── whale_accumulation.py
│   ├── cross_exchange_spread.py
│   └── btc_dominance_rotation.py
├── portfolio_manager.py
├── discord_reporter.py
├── scanner.py
├── helpers.py (rate-limit, cache, fallback)
├── data/
│   ├── paper.db
│   ├── portfolios.json
│   ├── active_picks.json
│   ├── closed_picks.json
│   └── performance.json
└── __init__.py
```
