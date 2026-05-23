# Fixes Applied: Symbol Hygiene + Geo-Block Log Noise

**Date:** 2026-04-17

## What was broken

1. Renamed/dead symbol contamination was still able to flow into active pick feeds.
- Renamed symbols (example: `MATICUSDT` -> `POLUSDT`) could persist across mixed writers.
- Known dead symbols could remain unless each writer pruned them manually.
- Duplicate rows for the same strategy/symbol/direction/source could survive merge paths.

2. Geo-block warnings were noisy.
- Binance futures endpoints (`fapi`) can return HTTP 451 in CI.
- Repeated attempts across mirrors produced repetitive warning logs, reducing signal-to-noise.

## What was changed

### 1) `alpha_engine/feed_hygiene.py`
- Added centralized symbol alias normalization:
  - `MATICUSDT` -> `POLUSDT`
  - `MATICUSD` -> `POLUSDT`
- Added dead symbol pruning for known delisted assets:
  - `LUNAUSDT`, `USTUSDT`, `FTTUSDT`, `SRMUSDT`
- Added duplicate suppression at sanitation time using key:
  - `(strategy, symbol, direction, source_system)`
- Expanded rejection counters and logs with:
  - `dead_symbol`
  - `duplicate`

### 2) `alpha_engine/api_failover.py`
- Added symbol alias normalization:
  - `MATICUSDT`/`MATICUSD` normalize to `POLUSDT`
- Added CoinGecko mapping for POL:
  - `POL -> polygon-ecosystem-token`
- Suppressed repeated 451 warning spam by endpoint:
  - First 451 per `(host, path)` logs warning
  - Subsequent ones log at debug level only

## Verification

- `py_compile` passed:
  - `alpha_engine/feed_hygiene.py`
  - `alpha_engine/api_failover.py`

## Impact

- Cleaner `active_picks` hygiene across all writers that use shared sanitizer.
- Safer handling of Polygon token rename without strategy-specific patchwork.
- Cleaner CI/runtime logs with fewer redundant geo-block warnings.
