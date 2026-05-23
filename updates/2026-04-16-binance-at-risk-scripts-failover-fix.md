# Fix: Add Binance Endpoint Failover to 4 AT_RISK Scripts

**Date:** 2026-04-16  
**Author:** Codebuff (Buffy)  
**Status:** Applied, Python syntax validated  

---

## Problem

4 scripts were classified as AT_RISK in `docs/BINANCE_DEPENDENCY_AUDIT.md` because they use a single hardcoded Binance API endpoint or limited mirror list with no alternative data source fallback. When GitHub Actions runs from US-based runners, `api.binance.com` and `fapi.binance.com` return HTTP 451 (geo-blocked), causing these scripts to fail silently or return no data.

## Fix Strategy

- **Python scripts with `shared.binance_api` available**: Use `binance_get()` / `binance_futures_get()` as primary (multi-mirror failover + circuit breaker + Bybit/CoinGecko fallback), with inline Bybit/KuCoin as additional fallback.
- **Python scripts using stdlib-only**: Add inline Bybit v5 and KuCoin fallback functions (no geo-block, no auth required).
- **Fallback chain priority**: Binance mirrors → Bybit v5 → KuCoin → CryptoCompare

## Files Changed

### 1. `alpha_engine/ensemble_gate.py`

- Added `BYBIT_V5_BASE` constant and `_BYBIT_INTERVAL_MAP`
- Added `_fetch_bybit_funding()` — Bybit v5 linear tickers fallback for funding rate
- Added `_fetch_bybit_oi()` — Bybit v5 open-interest fallback for OI data
- Added `_fetch_bybit_klines()` — Bybit v5 spot klines fallback for volume/price data
- Integrated Bybit fallbacks into `_check_funding_rate()`, `_check_oi_change()`, `_check_volume_spike()`
- Added inline Bybit OI history fallback in `_check_oi_change()` for the OI history endpoint

### 2. `alpha_engine/mtf_gate.py`

- Added `_fetch_klines_bybit()` — Bybit v5 spot klines with interval mapping
- Added `_fetch_klines_kucoin()` — KuCoin v1 market candles with symbol format conversion
- Added `_fetch_klines_fallback()` — full fallback chain: Bybit → KuCoin → CryptoCompare
- Wired fallback chain into `check_mtf_alignment()` — when `_fetch_klines()` returns empty, tries fallback for each timeframe
- Fixed redundant `import time as _time_mod` — now uses module-level `time` import

### 3. `genome/mega_mutation_live_tracker.py`

- Replaced `requests`-based 3-mirror list in `fetch_klines()` with `shared.binance_api.binance_get()` (with `ImportError` fallback)
- Added `_klines_from_raw()` helper to convert Binance-style kline list to OHLCV dict (shared by all sources)
- Added Bybit v5 kline fallback and KuCoin candle fallback in `fetch_klines()`
- Added Bybit v5 price fallback and KuCoin price fallback in `fetch_current_price()`
- Removed `import requests` dependency

### 4. `alpha_engine/forward_validator.py`

- Replaced hardcoded `https://api.binance.com/api/v3/klines` URL in GARCH volatility forecast section
- Primary: `shared.binance_api.binance_get()` with full mirror failover
- Fallback: inline 5-mirror loop (`data-api.binance.vision` → `api1-3` → `api.binance.com`) when `shared` module unavailable
- Added `isinstance(_kdata, list)` guard for `binance_get` returning `None` or dict on failure

## Validation

All 4 files pass `py_compile` syntax validation. Code review confirmed:
- None checks are correct on all failover paths
- Bybit/KuCoin API response format conversions are accurate
- `isinstance` guards properly handle `binance_get` returning `None`
- No race conditions or import issues

## BINANCE.MD Updated

All 4 AT_RISK items marked as **FIXED**:
- `ensemble_gate.py` — Bybit v5 fallback for funding rate, OI, and klines
- `mtf_gate.py` — full fallback chain: Bybit → KuCoin → CryptoCompare
- `mega_mutation_live_tracker.py` — `shared.binance_api` + Bybit/KuCoin inline fallback
- `forward_validator.py` — `shared.binance_api` + inline 5-mirror loop in GARCH kline fetch
