# crypto_edge_strategies: normalise fapi openInterest symbols

**Date:** 2026-11-26
**File:** `alpha_engine/crypto_edge_strategies.py`

## What was broken

`_fetch_all_open_interest()` passed each caller symbol straight into
`/fapi/v1/openInterest?symbol={sym}`. Binance futures accepts only `BASE + USDT`, so a
Yahoo-style ticker such as `SUI-USD` produced a request that could only fail, and the
open-interest input was silently lost.

## What changed

- Added `_binance_pair()` mirroring `alpha_engine/binance_sentiment.py:_binance_pair()`
  from PR #1172, so this module does not depend on an unmerged branch. Consolidate the
  two helpers once #1172 lands.
- `_fetch_all_open_interest()` now converts each symbol and skips unmappable ones instead
  of issuing a request that can only 400/451. The returned dict is keyed by the Binance
  pair, matching the existing docstring.
- The other two `/fapi/v1/openInterest` call sites (the `bsym` ones) were checked and
  deliberately left alone: `bsym` comes from `CRYPTO_SYMBOLS[...]["binance"]` and is
  guarded with `bsym not in premium_data` immediately before the request, so a Yahoo-style
  ticker can never reach them.

## Verification

- `python3 -m py_compile alpha_engine/crypto_edge_strategies.py` passes.
- Helper exercised directly: `SUI-USD → SUIUSDT`, `BTC-USD → BTCUSDT`,
  `ETHUSDT → ETHUSDT`, `SOL/USDT → SOLUSDT`, `  doge-usd  → DOGEUSDT`,
  `'' → None`, `BRK-B → None`.
- Known limitation inherited from the peer helper: a bare equity ticker still maps to a
  symbol that does not exist on Binance futures (`AAPL → AAPLUSDT`); the request then
  fails and the caller loses that input, exactly as before this change for such inputs.
