# Fix: Add Binance Endpoint Failover to 4 BROKEN Workflows

**Date:** 2026-04-16  
**Author:** Codebuff (Buffy)  
**Status:** Applied, Python + YAML validated  

---

## Problem

4 workflows were classified as BROKEN in `docs/BINANCE_DEPENDENCY_AUDIT.md` because they use a single hardcoded Binance API endpoint with no fallback. When GitHub Actions runs from US-based runners, `api.binance.com` and `fapi.binance.com` return HTTP 451 (geo-blocked), causing these workflows to fail silently.

## Fix Strategy

- **Python scripts** (3 files): Replace hardcoded `requests.get()` / `aiohttp` calls with `shared.binance_api.binance_get()` / `binance_futures_get()` which automatically try all Binance mirrors + circuit breaker + Bybit/CoinGecko fallback.
- **Inline YAML Python** (1 file): Add inline mirror list with failover loop (can't import `shared.binance_api` from workflow inline Python).

## Files Changed

### 1. `live_trading_bot.py`
- Replaced `requests` import with `from shared.binance_api import binance_get, binance_futures_get`
- Replaced all 5 `DataFetcher` methods (`get_funding_rate`, `get_order_book`, `get_liquidation_data`, `get_24h_stats`, `get_klines`) from `requests.get(url)` to `binance_futures_get(path, params=...)`
- Added `if not data: return None` / `return pd.DataFrame()` None-checks for 3 methods that lacked them
- Removed `self.base_url` / `self.spot_url` (no longer needed)

### 2. `real_2hour_challenge.py`
- Replaced `requests` import with `from shared.binance_api import binance_get, binance_futures_get`
- Replaced `get_binance_data()` and `get_funding_rate()` from `requests.get()` to `binance_get()` / `binance_futures_get()`
- Added `if data:` / `if data and isinstance(data, list) and data:` checks

### 3. `live_spike_trader.py`
- Added `from shared.binance_api import binance_get, binance_futures_get`
- Replaced all 3 `LiveDataFeed` async methods + funding history call from `aiohttp` to `asyncio.to_thread(binance_get/..., ...)` wrapping the sync failover helpers
- Removed dead `aiohttp` import, `self.session`, `init_session()`, `close()` methods
- Replaced `init_session()` / `close()` calls in `AutonomousSpikeTrader` with comments

### 4. `.github/workflows/genome-evolution.yml`
- Added inline mirror list: `data-api.binance.vision`, `api1-3.binance.com`, `api.binance.com`, `api.binance.us`
- Added `GITHUB_ACTIONS` detection to deprioritize geo-blocked `api.binance.com`
- Replaced single-URL fetch with failover loop that tries each mirror in order
- Added `User-Agent` header and per-mirror error logging

## Verification

- All 4 Python files pass `py_compile` syntax validation
- `genome-evolution.yml` passes YAML syntax validation
- Code reviewer confirmed all None-checks are correct
- `asyncio.to_thread` with `urllib`-based `binance_api` is safe (thread-safe, no shared state)

## Remaining Work

Per BINANCE.MD, these files still need failover:
- `ensemble_gate.py` — Binance-only for funding rate + OI
- `mtf_gate.py` — partial (has CryptoCompare, needs Bybit/KuCoin)
- `mega_mutation_live_tracker.py` line 268
- `forward_validator.py` line 3044 (low priority)
