# Crypto Data Failover Shared Module

**Date:** 2026-04-17  
**Author:** Claude autonomous subagent + peer review  
**Files:** `alpha_engine/crypto_data_failover.py`, `tests/test_crypto_data_failover.py`

---

## Why this exists

On 2026-04-17 the project's crypto pipelines hit a **total outage**:

- `api.binance.com` returned **HTTP 451** (geo-blocked) from every US-based GitHub Actions runner.
- The only fallback wired into `crypto_signal_engine` was `binance_vision` — which sits in the **same IP block** and also returned 400/451.
- **CoinGecko, KuCoin, and CryptoCompare were never attempted.**
- Result: **0 new picks, 0 total active** for the entire run.

This violates the project rule in `CLAUDE.md` / `memory/feedback_api_failover.md`:

> "Never use a single Binance API endpoint. Always use a 3+ fallback chain:
> Binance mirrors (api, api1, api2, api3) → CoinGecko → KuCoin → CryptoCompare."

This module provides a **single, shared, well-tested implementation** so no caller can accidentally build a "Binance-only" mini-chain again.

---

## Public API

```python
from alpha_engine.crypto_data_failover import (
    fetch_tickers_24h,
    fetch_klines,
    fetch_funding_rate,
    FailoverConfig,
)

# 24h ticker stats (Binance-compatible schema)
tickers, source_name = fetch_tickers_24h()

# OHLCV candles (Binance kline format)
bars = fetch_klines("BTCUSDT", interval="1h", limit=100)

# Latest funding rate as decimal (0.0001 = 0.01%)
rate = fetch_funding_rate("BTCUSDT")

# Circuit-breaker config (singleton used by default)
config = FailoverConfig()
```

---

## Failover Chains

### Price / Volume / OHLCV

1. **Binance Futures API** — `fapi.binance.com`
2. **Binance Futures mirrors** — `fapi1.binance.com`, `fapi2.binance.com`
3. **Binance Spot API** — `api.binance.com`
4. **Binance Spot mirrors** — `api1/2/3.binance.com`, `data-api.binance.vision`, `api.binance.us`
5. **CoinGecko** — `/coins/markets` (tickers), `/coins/{id}/ohlc` (klines)
6. **KuCoin** — `/api/v1/market/allTickers` (tickers), `/market/candles` (klines)
7. **CryptoCompare** — `/data/top/totalvolfull` (tickers), `/data/v2/...` (klines)

### Funding Rate

1. **Binance Futures API + mirrors**
2. **Bybit** — `/v5/market/funding/history`
3. **OKX** — `/api/v5/public/funding-rate`
4. **Coinglass** — `/public/v2/funding_rates_history` (only if `COINGLASS_API_KEY` env var is set)

---

## Normalized Schemas

Every non-Binance source is converted to a **Binance-compatible schema** so downstream code doesn't need source-specific branches.

### Ticker schema
```json
{
  "symbol": "BTCUSDT",
  "lastPrice": "65432.10",
  "priceChange": "+123.45",
  "priceChangePercent": "+0.19",
  "volume": "12345.6",
  "quoteVolume": "812345678.9"
}
```

### Kline schema
```python
[open_time_ms, open, high, low, close, volume,
 close_time_ms, quote_volume, trade_count,
 taker_base, taker_quote, ignore]
```
All numeric fields after `open_time_ms` are **strings** (matching Binance native shape).

---

## Circuit Breaker Design

`FailoverConfig` persists state to `alpha_engine/data/failover_circuit.json`:

```json
{
  "coingecko": {
    "consecutive_failures": 3,
    "first_failure_ts": 1744890123.45,
    "open_until_ts": 1744890423.45
  }
}
```

- **Open condition:** 3 consecutive failures inside a 60-second window.
- **Cooldown:** 5 minutes (300 seconds).
- **Thread-safe:** Uses `threading.RLock()`.
- **Process-safe:** State is reloaded from disk on every check, so subsequent processes or cron jobs inherit the breaker state.

**Rationale for 5-minute cooldown:**
CoinGecko free-tier rate limits are 10–30 requests/minute. A 5-minute cooldown prevents a stampede of failing requests without being so long that a transient network hiccup blackholes the source for hours.

---

## CoinGecko Throttling

CoinGecko free tier is aggressively rate-limited. The module enforces a **2.1-second minimum interval** between CoinGecko calls (`COINGECKO_MIN_INTERVAL`), implemented with a module-level lock + timestamp. This keeps us well under the 30 req/min ceiling and is conservative enough for the 10 req/min low-tier.

---

## Integrations

The module is already wired into **3 production callers**:

| Caller | Function used | Notes |
|--------|---------------|-------|
| `alpha_engine/winner_reverse_engineer.py` | `fetch_tickers_24h`, `fetch_klines` | Legacy local Binance fallback retained for import-failure edge case |
| `crypto_signal_engine/data_fetcher.py` | `fetch_klines`, `fetch_funding_rate` | Added as "Layer 0" before the existing 5-layer legacy chain |
| `alpha_engine/funding_rate_scanner.py` | `fetch_funding_rate` | Synthesizes a Binance-shaped dict so downstream code is unchanged |

---

## Test Results

```bash
python -m pytest tests/test_crypto_data_failover.py -v
```

**27 passed in 8.71s**

Coverage includes:
- Symbol normalization (`BTC/USDT` → `BTCUSDT`)
- Per-source normalizers (CoinGecko, KuCoin, CryptoCompare)
- Schema rejection (zero volume → skipped)
- Circuit-breaker open/close/reset/persistence
- Fallback chain progression (mocked source failures)
- Public API signatures

---

## How to extend with new sources

1. Add the endpoint URL constant near the top of `crypto_data_failover.py`.
2. Write a `_fetch_<source>_<data_type>()` helper that returns native response or `None` on failure.
3. Write a `_normalize_<source>_<data_type>()` converter that returns the Binance schema or `None` if validation fails.
4. Insert the source into the `sources` list inside `fetch_tickers_24h()` / `fetch_klines()` / `fetch_funding_rate()`.
5. Add a mocked test in `tests/test_crypto_data_failover.py` showing the new source is reached when prior sources fail.

No new pip dependencies are required — use `urllib.request` (stdlib) for HTTP.

---

## Peer Review Notes

Reviewed by an independent AI subagent:

- **Verdict:** `APPROVE_WITH_SUGGESTIONS`
- **Post-review fix applied:** `crypto_signal_engine/data_fetcher.py` `_ohlcv_shared` was padding short kline rows with integer `0`; changed to `"0"` to match Binance string schema.
- **Future improvements noted:**
  - Consider debouncing disk writes in `FailoverConfig._save()` if the module is called at very high frequency.
  - Add explicit mocked tests for 451/403 geo-block paths.
  - Document `_normalize_symbol`'s behavior of converting `*USD` → `*USDT` for non-USDT stablecoin callers.

---

## Operational Checklist

- [x] Module created with zero new pip dependencies
- [x] Schema validators for every non-Binance source
- [x] Persistent circuit breaker implemented
- [x] CoinGecko throttle implemented
- [x] Integrated into 3 callers
- [x] 27 unit tests passing
- [x] Peer AI review completed
- [x] Minor padding fix applied post-review
