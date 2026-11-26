# Forward-trade executor mapped every non-crypto symbol to a delisted ticker

**Date:** 2026-11-26
**File:** `forward_trade_executor_v2.py` (`ForwardTradeExecutor._symbol_to_yf`)
**Severity:** silent data loss — job green, prices never resolved for 13 instruments

## What was broken

`_symbol_to_yf` stripped a `USDT`/`USD` suffix and then unconditionally appended
`-USD` to whatever was left. That is correct for crypto and wrong for everything else:

| pick symbol | old output | valid yfinance symbol |
|---|---|---|
| `AAPL` | `AAPL-USD` | `AAPL` |
| `SPY` | `SPY-USD` | `SPY` |
| `^GSPC` | `^GSPC-USD` | `^GSPC` |
| `GC=F` | `GC=F-USD` | `GC=F` |
| `EURUSD` | `EUR-USD` | `EURUSD=X` |

Every non-crypto price and ATR lookup therefore hit a nonexistent ticker. The
lookup failed, the failure was logged, and the job still finished green — ~42
`delisted symbol` / `All sources failed` lines per hourly run, with the affected
instruments never getting an entry price or ATR. 13 non-crypto instruments were
affected.

## What changed

`_symbol_to_yf` now only rewrites genuine crypto:

- already `BASE-USD` → returned as-is
- `BASE/USDT`, `BASEUSDT`, `BASEUSDC`, `BASEBUSD` → `BASE-USD`
- bare `...USD` → `BASE-USD` for crypto bases, `PAIR=X` for fiat bases
  (`EURUSD`, `GBPUSD`, `JPYUSD`, …)
- anything else (equities, ETFs, indices `^`, futures `=F`, `BRK.B`) → passed
  through untouched

## Verification

Re-ran the mapping locally over 23 symbols covering crypto, equities, indices,
futures, dots and FX:

```
23/23 correct, 0 failures
BTCUSDT -> BTC-USD   AAPL -> AAPL     ^GSPC -> ^GSPC
KASUSDT -> KAS-USD   GC=F -> GC=F     EURUSD -> EURUSD=X
```

Crypto mappings are byte-identical to the old behaviour, so no existing crypto
pick changes. `py_compile` passes.

## Not changed

`alpha_engine/wavelet_cycle_strategies.py:145` has the same
append-`-USD`-then-strip-`USDT` pattern, but its docstring scopes it to Binance
symbols and no caller passes it non-crypto input. Left alone; if it is ever
generalised it should reuse this logic.
