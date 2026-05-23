# _GEO_BLOCKED Sentinel Propagation Tests — 2026-04-19

**Author:** Buffy (AI Code Review)
**Scope:** New test class `TestGeoBlockedSentinel` in `tests/test_crypto_data_failover.py`

---

## What Changed

Added 20 new tests to `tests/test_crypto_data_failover.py` in a new `TestGeoBlockedSentinel` class, bringing total test count from 27 to 47.

## Files Modified

| File | Change |
|------|--------|
| `tests/test_crypto_data_failover.py` | Added `TestGeoBlockedSentinel` class with 20 tests |

## Why

The `_GEO_BLOCKED` sentinel was added to `crypto_data_failover.py` in a previous fix to handle 451/403 geo-blocked responses correctly. Previously, HTTP 451/403 were caught by the generic `except` handler and returned `None`, which caused `_try_source` to call `record_failure()` — consuming circuit-breaker budget on sources that are **permanently** geo-blocked (not temporarily down). The fix introduced a `_GEO_BLOCKED = object()` sentinel that propagates through all 12 per-source fetchers so `_try_source` can skip breaker recording for known-permanent failures.

However, this sentinel propagation was **not tested**. If a future refactor removed a `if data is _GEO_BLOCKED: return _GEO_BLOCKED` line from any of the 12 fetchers, the bug would silently return — geo-blocks would again consume breaker budget, eventually opening breakers on Binance and blocking the entire failover chain (the exact production incident this fix was designed to prevent).

## Test Coverage

### Layer 1: `_http_get_json` returns correct sentinel (3 tests)
- `test_http_get_json_returns_geo_blocked_on_451` — 451 → `_GEO_BLOCKED`
- `test_http_get_json_returns_geo_blocked_on_403` — 403 → `_GEO_BLOCKED`
- `test_http_get_json_returns_none_on_500` — 500 → `None` (NOT `_GEO_BLOCKED`)

### Layer 2: All 12 per-source fetchers propagate `_GEO_BLOCKED` (12 tests)
- **Tickers:** `_fetch_binance_tickers`, `_fetch_coingecko_tickers`, `_fetch_kucoin_tickers`, `_fetch_cryptocompare_tickers`
- **Klines:** `_fetch_binance_klines`, `_fetch_kucoin_klines`, `_fetch_coingecko_klines`, `_fetch_cryptocompare_klines`
- **Funding:** `_fetch_binance_funding`, `_fetch_bybit_funding`, `_fetch_okx_funding`, `_fetch_coinglass_funding`

Each test mocks `_http_get_json` to return `_GEO_BLOCKED` and asserts the fetcher propagates it (not `None`).

### Layer 3: `_try_source` skips breaker recording for `_GEO_BLOCKED` (3 tests)
- `test_try_source_does_not_record_failure_on_geo_blocked` — no failure recorded, no breaker entry
- `test_try_source_records_failure_on_normal_error` — normal `None` failures still consume budget (3 failures → breaker opens)
- `test_geo_blocked_does_not_trip_breaker_but_normal_failures_still_do` — mix of geo-blocks + normal failures: only normals count

### Layer 4: Full end-to-end chain (2 tests)
- `test_tickers_chain_succeeds_despite_geo_blocked_binance` — All Binance + CoinGecko geo-blocked → KuCoin succeeds, no Binance/CoinGecko breaker entries
- `test_funding_chain_succeeds_despite_geo_blocked_binance` — Binance geo-blocked → Bybit down (normal) → OKX succeeds, only Bybit has breaker entry

## Benefits / Purpose

1. **Regression prevention:** If any of the 12 `if data is _GEO_BLOCKED: return _GEO_BLOCKED` lines is accidentally removed, the corresponding test will fail immediately.
2. **Behavioral clarity:** The tests document the exact contract: `_GEO_BLOCKED` means "permanently unreachable" and must not consume breaker budget, while `None` means "temporarily failed" and must consume it.
3. **End-to-end confidence:** The E2E tests verify the full chain works correctly under geo-block conditions — the exact scenario that caused 0 picks for an entire production run on 2026-04-17.
4. **Circuit-breaker integrity:** Geo-blocks don't waste breaker budget, so breakers remain available to protect against real (temporary) source failures.

## Validation

- Syntax check: ✅ Pass
- All 47 tests: ✅ Pass (10.79s)
- Code review: ✅ Approved (no issues)
