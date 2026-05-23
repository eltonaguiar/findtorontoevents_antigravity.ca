# Crypto Signal Engine — Design Document

**Date:** 2026-02-25
**Status:** Approved
**Location:** `crypto_signal_engine/`

## Problem Statement

All existing ML systems fail to deliver consistent winning picks:
- crypto_ml_edge: 7/8 models fail DSR (95%+ class imbalance from cost-gated labels)
- ml_battleground: 10-20% win rate across 20 closed trades (-$19.11 total)
- alpha_engine: 0 closed trades (no realized performance)
- KIMI: 0 closed trades

Root causes: extreme label imbalance, DSR gate too strict (0.95), no unified output.

## Solution

New standalone ML signal engine running in parallel with existing systems for comparison.

### Two Output Modes

1. **Day-trade signals** — 3 XGBoost ensemble (conservative/aggressive/balanced) on BTC/ETH/BNB at 1h
2. **Top-gainer predictor** — LightGBM regressor ranks ~40 symbols by expected next-day return

### Key Design Decisions

| Existing Failure | Fix |
|---|---|
| 95% class imbalance | Binary labels (price up/down after 4h) → ~50/50 split |
| DSR gate 0.95 impossible | DSR ≥ 0.75, PSR ≥ 0.75 |
| Per-pair models fail on altcoins | Global model across ALL symbols |
| 24 features + broken SHAP | 12 proven features, no SHAP |
| No output channel | JSON → GitHub Pages dashboard; Discord-ready |
| Single API point of failure | 5-layer API failover (Binance → CoinGecko → CryptoCompare → CoinLore → cache) |

## Architecture

```
GitHub Actions (every 30 min — scan mode)
GitHub Actions (daily 02:00 UTC — retrain mode)
    │
    ▼
engine.py --mode scan|retrain
    ├── Fetch data via 5-layer API failover
    ├── Build 12 features
    ├── Load saved models (scan) or retrain (retrain)
    ├── 3-model XGBoost ensemble → probability
    ├── Risk engine (5 guards) → filtered picks
    ├── Performance tracker (P&L, TP/SL close)
    ├── Top-gainer regressor (retrain mode only)
    └── Write JSON outputs
         ├── data/active_picks.json
         ├── data/closed_picks.json
         ├── data/top_gainers.json
         └── data/models/ (saved model files)

docs/index.html → GitHub Pages dashboard
```

## API Failover (5 layers)

```python
PRICE_SOURCES = [
    ("binance",      "https://api.binance.com/api/v3/klines"),
    ("binance_us",   "https://api.binance.us/api/v3/klines"),
    ("coingecko",    "https://api.coingecko.com/api/v3/coins/{id}/ohlc"),
    ("cryptocompare","https://min-api.cryptocompare.com/data/v2/histohour"),
    ("cache",        "Use last known good data from data/price_cache.json"),
]

FUNDING_SOURCES = [
    ("binance_fapi", "https://fapi.binance.com/fapi/v1/fundingRate"),
    ("binance_dapi", "https://dapi.binance.com/dapi/v1/fundingRate"),
    ("fallback",     "Use 0.0 (neutral) — funding is a feature, not critical"),
]

SENTIMENT_SOURCES = [
    ("alternative",  "https://api.alternative.me/fng/"),
    ("fallback",     "Use 50 (neutral)"),
]
```

## File Layout

```
crypto_signal_engine/
├── engine.py              # Main: fetch, features, predict, risk, output (~600 lines)
├── trainer.py             # Train/retrain models, validation (~250 lines)
├── config.py              # All constants, symbol list, slippage map
├── data_fetcher.py        # 5-layer API failover for all data sources
├── backtest.py            # Paper-trade simulation
├── requirements.txt       # pandas numpy xgboost lightgbm scipy requests
├── data/
│   ├── active_picks.json
│   ├── closed_picks.json
│   ├── top_gainers.json
│   ├── price_cache.json   # Last known good prices (failover layer 5)
│   ├── validation.json    # DSR/PSR/Sharpe metrics
│   └── models/
│       ├── xgb_conservative.json
│       ├── xgb_aggressive.json
│       ├── xgb_balanced.json
│       └── lgb_top_gainer.txt
├── docs/
│   └── index.html         # Dashboard (GitHub Pages)
└── .github/
    └── workflows/
        └── signal-engine.yml
```

## 12 Features

| # | Feature | Source | Why |
|---|---------|--------|-----|
| 1 | ret_1h | OHLCV | Short momentum |
| 2 | ret_4h | OHLCV | Medium momentum |
| 3 | ret_24h | OHLCV | Daily momentum |
| 4 | rsi_14 | Calculated | Overbought/oversold |
| 5 | macd | Calculated | Trend strength |
| 6 | atr | Calculated | Volatility + TP/SL basis |
| 7 | bb_width | Calculated | Squeeze/expansion |
| 8 | vol_ratio | OHLCV | Volume anomaly (24h avg) |
| 9 | above_200 | Calculated | Trend regime (binary) |
| 10 | fng | alternative.me | Sentiment |
| 11 | btc_dom | CoinGecko | Macro rotation |
| 12 | funding_z | Binance futures | Leverage sentiment z-score |

## Risk Engine (5 Guards)

1. **Confidence** ≥ 0.55 (day-trade) / ≥ 0.70 (premium/Discord)
2. **Cost-adjusted edge** ≥ 2× total cost (fee + slippage)
3. **Trend guard**: price > 200 SMA OR F&G < 20 (longs); RSI > 70 + price < 200 SMA (shorts)
4. **Funding extreme**: |funding_z| < 2σ
5. **ATR edge**: 3×ATR > 2× total cost

## TP/SL

- LONG: TP = entry + 3×ATR, SL = entry - 2×ATR
- SHORT: TP = entry - 3×ATR, SL = entry + 2×ATR
- Position size: 1% capital / (2×ATR)

## Validation Gates

- DSR ≥ 0.75, PSR ≥ 0.75
- Walk-forward 80/20 split with 20-bar purge gap
- Logged to data/validation.json

## Symbols

### Day-trade (core 3): BTCUSDT, ETHUSDT, BNBUSDT
### Top-gainer (all ~40): Full list from RAW_SYMBOLS in prototypes

For top-gainer, use Binance REST API only (covers ~35 of 41 symbols).
Non-Binance symbols (TON, RIVER, GLM, ULTIMA, VVV, ZBCN) excluded from v1.

## Deployment

- GitHub Actions `signal-engine.yml`:
  - Every 30 min: `python engine.py --mode scan`
  - Daily 02:00 UTC: `python engine.py --mode retrain`
- Auto-commit JSON data files
- GitHub Pages deploy for dashboard
- Discord webhook: Phase 2 (separate script, not in v1)

## NOT Building (YAGNI for v1)

- No FastAPI server (GitHub Actions cron)
- No PostgreSQL/TimescaleDB (JSON files)
- No ccxt dependency (raw REST APIs)
- No on-chain placeholder features (add real data later)
- No meta-stacker (simple average of 3 models)
- No subscription/API-key system
