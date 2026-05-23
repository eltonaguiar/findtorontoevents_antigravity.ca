# System F — Claws of Doom v3

**Dashboard:** https://eltonaguiar.github.io/CLAWSOFDOOM/
**Source repo:** https://github.com/eltonaguiar/CLAWSOFDOOM
**Engine:** `systems/claws_engine.py` (52KB, 6 strategies)

## Overview

Claws of Doom is a fully autonomous crypto trading signal generator running
24/7 via GitHub Actions every 15 minutes. It scans 3 major cryptocurrencies
(BTC, ETH, SOL) using 6 strategies with 5 API fallback layers.

## Strategies

| # | Strategy | Direction | TP | SL | Edge |
|---|----------|-----------|----|----|------|
| 1 | Extreme Fear Contrarian | LONG | +6% | -5% | Mean reversion from retail panic |
| 2 | Crash Reversal Bounce | LONG | +5% | -4% | Short squeeze after >10% daily drop |
| 3 | Momentum Breakout | LONG | +8% | -6% | Momentum continuation in risk-on |
| 4 | RSI Overbought + SMA Breakdown | SHORT | -5% | +3% | Exhaustion rally reversal |
| 5 | EMA Bearish Cross + RSI Divergence | SHORT | -6% | +4% | Trend reversal confirmation |
| 6 | Funding Rate Carry | BOTH | ±3% | ±2% | Funding rate mean-reversion |

## Data Sources (5 API Layers)

1. **Binance** (primary) — spot prices, 24h change, funding rates
2. **CoinGecko** — spot + 24h change
3. **CryptoCompare** — spot + 24h change
4. **CoinCap** — spot + 24h change
5. **Hardcoded estimates** (emergency fallback only)
6. **Fear & Greed Index** — alternative.me/crypto (with estimation fallback)

## Sync

Data is synced from the CLAWSOFDOOM repo every 30 minutes via
`.github/workflows/ml-battleground-f.yml`. Files synced:
- `active_picks.json`
- `closed_picks.json`
- `picks.json` (full scan output)
