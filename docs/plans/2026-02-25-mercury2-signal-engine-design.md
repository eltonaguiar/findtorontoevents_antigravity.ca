# Mercury 2 — Unified Multi-Exchange Signal Engine

**Date:** 2026-02-25
**Status:** Approved

## Overview

Mercury 2 is a standalone signal engine that combines:
1. **Day-trading ensemble** — 3 XGBoost classifiers (conservative/aggressive/balanced) on 1h candles
2. **Daily top-gainer regressor** — LightGBM ranking model predicting next-24h returns, picks top-5

Both share the same data pipeline, feature engine, and risk manager.

## Architecture

```
mercury2/
├── scanner.py              # Main: load models → fetch latest → predict → risk filter → output
├── trainer.py              # Weekly retrain: fetch 2yr data → train → validate → save models
├── data_fetcher.py         # Binance REST OHLCV (1h) + funding rates
├── features.py             # 12-feature causal engine
├── ensemble.py             # 3 XGBoost classifiers
├── top_gainer.py           # LightGBM regressor for daily top-5
├── risk_engine.py          # ATR-based TP/SL, cost filter, position sizing
├── config.py               # Symbols, thresholds, risk params
├── models/                 # Pre-trained .joblib files (committed to repo)
├── data/
│   ├── active_picks.json
│   ├── closed_picks.json
│   ├── top_gainers.json
│   └── scan_summary.json
└── index.html              # Dashboard
```

## Symbols (20 Binance-only)

BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT,
TRXUSDT, DOTUSDT, LINKUSDT, LTCUSDT, BCHUSDT, SHIBUSDT, INJUSDT, SUIUSDT,
ARBUSDT, OPUSDT, AAVEUSDT, FETUSDT

## Features (12 causal)

1. ret_1h, ret_4h, ret_24h (momentum)
2. rsi_14, macd (oscillators)
3. atr_14, bb_width (volatility)
4. vol_ratio (volume)
5. above_200 (trend)
6. fng (sentiment)
7. btc_dom (macro)
8. pair_id (asset identity)

## Labels

- Day-trade: `label = 1 if price 4h ahead > 0` (binary)
- Top-gainer: `next_ret = close[+24h] / close - 1` (regression)

## Models

### Day-Trade Ensemble (3 XGBoost)
| Learner | max_depth | lr | n_estimators | regularization |
|---------|-----------|-----|-------------|----------------|
| Conservative | 3 | 0.05 | 150 | alpha=1.0, lambda=1.0 |
| Aggressive | 6 | 0.10 | 250 | alpha=0.1, lambda=0.1 |
| Balanced | 4 | 0.07 | 200 | defaults |

Ensemble probability = mean of 3 learners.

### Top-Gainer Regressor (LightGBM)
- objective=regression, lr=0.05, num_leaves=31, n_estimators=400
- Early stopping rounds=30
- Validation: Precision@5

## Validation Gates

- DSR (Deflated Sharpe Ratio) ≥ 0.60
- PSR (Probabilistic Sharpe Ratio) ≥ 0.60
- Models failing gates are flagged but not deployed

## Risk Engine

### Entry Guards
1. Ensemble probability ≥ 0.55
2. Probability ≥ 2× total_cost (~25 bps)
3. Trend: price > 200 SMA OR Fear & Greed < 20
4. Funding z-score within ±2
5. ATR-edge > 2× cost

### TP/SL
- TP = +3 × ATR
- SL = -2 × ATR
- R:R = 1.5

### Short Overlay
- RSI > 70 AND price < 200 SMA → SHORT signal
- Same TP/SL logic, reversed direction

### Position Sizing
- `size = (capital × risk_per_trade) / (ATR × 2)`
- risk_per_trade = 1% of capital

## Deployment

### Workflows
1. `mercury2-scan.yml` — Every 30 min, loads models, runs inference
2. `mercury2-retrain.yml` — Weekly Sunday, trains + validates + commits models

### Dashboard
- Deployed via GitHub Pages (existing deploy-riseoftheclaw.yml)
- URL: /mercury2/ on GitHub Pages

## Integration
- Market health from ml_battleground/shared/market_health.py
- Discord notifications via ml_battleground/shared/discord_notify.py
- Cross-system symbol lock to prevent conflicts

## Deferred (YAGNI)
- 5-min sub-model (no real-time execution capability)
- PostgreSQL/TimescaleDB (static JSON sufficient)
- Portfolio optimizer (needs forward-test data first)
- On-chain features (Glassnode, CryptoQuant) — placeholders ready
- Social sentiment (Twitter API) — placeholder ready
