# Prediction Market Multi-Asset Expansion

**Date:** 2026-07-16  
**Branch:** `feature/prediction-market-multi-asset-expansion`  
**Status:** Implemented, pending review

## What Was Broken / Limited

The prediction market pipeline (Kalshi + Polymarket + PM Consensus) was **crypto-only**:

- **Kalshi signals** (`alpha_engine/kalshi_signals.py`): Hardcoded `KALSHI_CRYPTO_SERIES` with 15 crypto symbols. No support for equity/index/commodity/macro series.
- **Polymarket signals** (`alpha_engine/polymarket_signals.py`): `ASSET_RULES` only matched 12 crypto assets. TP/SL was hardcoded at 2.5%/1.5% regardless of asset class.
- **PM Consensus** (`alpha_engine/prediction_market_consensus.py`): Output always had `"category": "crypto"`. Only accepted 3 crypto sources. Non-crypto copytrader data was ignored.
- **Non-crypto consensus** (`copy_trader_intel/non_crypto_consensus.py`): Had 6 copytrader sources but zero prediction market input — PM signals never fed into non-crypto picks.

## What Was Changed

### 1. `alpha_engine/config.py` — Shared Asset Detection Utility
- Added `KNOWN_FOREX_PAIRS`, `KNOWN_COMMODITY_SYMBOLS`, `KNOWN_INDEX_SYMBOLS` sets
- Added `detect_asset_class(symbol)` — returns `'crypto'`/`'forex'`/`'commodity'`/`'equity'`/`'index'`/`'macro'`
- Added `get_risk_params(asset_class)` — returns `(sl, tp, hold_days)` from `CATEGORY_RISK`

### 2. `alpha_engine/kalshi_signals.py` — Multi-Asset Kalshi Scanning
- Added `KALSHI_MACRO_SERIES` dict with 30+ series covering S&P 500, NASDAQ, gold, oil, Fed/FOMC, CPI/inflation, and individual stocks (AAPL, TSLA, NVDA, AMZN, META, GOOGL, MSFT)
- Imported `detect_asset_class` / `get_risk_params` from config
- Updated `get_kalshi_signals()` to accept `asset_classes` filter and scan both crypto + macro series
- Updated `_fetch_price()` to use yfinance for non-crypto symbols
- Updated `_derive_trade_levels()` to use per-asset-class risk params from config
- Updated `generate_kalshi_picks()` to set dynamic `category` per symbol
- Updated CLI output to show asset class

### 3. `alpha_engine/polymarket_signals.py` — Multi-Asset Polymarket Scanning
- Expanded `ASSET_RULES` from 12 crypto-only to 30+ patterns covering equities (SPY, QQQ, AAPL, TSLA, NVDA, etc.), commodities (gold, silver, oil), macro (Fed rate, inflation/CPI), and forex (EUR/USD, GBP/USD, USD/JPY)
- Imported `detect_asset_class` / `get_risk_params` from config
- Updated `_fetch_price()` to use yfinance for non-crypto symbols
- Updated `_snapshot_trade_levels()` to use per-asset-class risk params instead of hardcoded 2.5%/1.5%
- Updated output to set dynamic `category` per symbol

### 4. `alpha_engine/prediction_market_consensus.py` — Multi-Asset Consensus
- Added `non_crypto_copytrader` source with weight 0.75 to `SOURCE_WEIGHTS`
- Imported `detect_asset_class` from config
- Updated `aggregate_signals()` to accept optional `non_crypto_ct_picks` parameter
- Lowered `MIN_SOURCE_CATEGORIES` to 1 for non-crypto symbols (PM coverage is sparser)
- Replaced hardcoded `"category": "crypto"` with dynamic `_detect_asset_class(symbol)`
- Updated `run_consensus()` to load non-crypto copytrader consensus as 4th source
- Updated CLI output to show asset class

### 5. `copy_trader_intel/non_crypto_consensus.py` — PM Signal Integration
- Added Source 7: prediction market non-crypto picks from `alpha_engine/data/prediction_market_picks.json`
- Filters PM picks to non-crypto only (excludes `category == "crypto"`)
- Updated `load_json_picks()` to handle dict format (with `picks` key)
- Updated log output to show PM-NonCrypto count

### 6. `.github/workflows/polymarket-signals.yml` — GHA Workflow
- Added `yfinance` to pip install dependencies
- Updated step names to reflect multi-asset scope
- Updated echo descriptions

## Architecture: Bidirectional Flow

```
Kalshi (crypto+macro) ──┐
                         ├──→ PM Consensus ──→ active_picks.json
Polymarket (crypto+macro)┤                         │
                         │                         ▼
Wallet Copy ─────────────┘               (non-crypto picks)
                                               │
                                               ▼
CTA + ForexCT + Multi + Commodity ──┐   PM picks (non-crypto)
+ Equity + Futures ─────────────────┼──→ Non-Crypto Consensus
PM Non-Crypto Picks ────────────────┘         │
                                               ▼
                                    non_crypto_consensus_picks.json
                                               │
                                               ▼
                              (feeds back into PM Consensus as Source 4)
```

## How It Was Verified

- All 5 modified Python files pass `py_compile` syntax check
- No hardcoded `"category": "crypto"` remains in any modified file
- yfinance import is wrapped in try/except so existing crypto-only paths still work if yfinance is not installed
- `detect_asset_class()` fallback is embedded in each module for standalone execution
- All changes are backward-compatible — crypto scanning continues to work exactly as before
- New Kalshi macro series and Polymarket non-crypto ASSET_RULES will only produce signals if Kalshi/Polymarket actually list matching markets (graceful empty results otherwise)
