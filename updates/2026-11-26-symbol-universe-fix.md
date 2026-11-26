# Symbol universe: stop requesting tickers that cannot resolve (2026-11-26)

## What was broken

`picks-now-refresh.yml` run `45746318864` concluded **success** with **1,427 error
lines** in its log. Two separate causes:

1. **The universe contained symbols Yahoo cannot resolve.** 840 of the errors came
   from the step *Refresh OHLC coverage for tracker symbols*, which iterates
   `picks_now_tracker` symbols. Those carry social-feed formatting — `$SQ`,
   `$ADA`, `$BTC` — and dead tickers. `normalize_yf_symbol()` stripped spaces and
   upper-cased, but **did not strip `$`**, so `$SQ` was requested from Yahoo
   verbatim and could only fail. `SQ` itself no longer exists (Block Inc.
   renamed to `XYZ`).
2. **yfinance logs every miss itself.** `yfinance` emits
   `No data found, symbol may be delisted` at **ERROR** level for each empty
   symbol, and an HTTP-404 `quoteSummary` error for ETFs/funds with no
   fundamentals (`SPY`, `QQQ`, `IVV`, `IWM`, `TLT` — a documented coverage fact,
   already handled by `tools/harvest_analyst_signals.py`, which returns
   `status=not_covered`). Nothing about these is actionable, but they made a
   successful run look broken and would hide a real error among them.

## What changed

`tools/refresh_stock_ohlcv.py`

- `normalize_yf_symbol()` now strips a leading `$` and any `$` in the symbol.
- `KNOWN_DELISTED` — six tickers with a written reason each (`SQ` → renamed XYZ,
  `NKLA` delisted, `MATIC-USD` → POL, `RNDR-USD` → RENDER, `FB` → META, `TWTR`
  taken private). Returned as `None`, so they are never requested.
- `CRYPTO_BASES` — a bare crypto code (`ADA`, `BTC`, …) is **not** silently
  rewritten to `ADA-USD`. That would put crypto into a stock-only table; the
  crypto pipeline owns those symbols, so they are dropped here instead.
- `_quiet_yfinance()` sets the `yfinance` logger to `CRITICAL` and stops
  propagation, so the library cannot flood the log with per-symbol misses.
- Per-symbol `logger.warning("No data for %s ...")` replaced by one aggregated
  line: `No data for N symbol(s) — delisted/invalid or not covered by Yahoo: …`
  (first 25, then `(+N more)`).

`tools/picks_now_professional.py`

- same `yfinance` logger silencing, with the reason written down in the code.

## Verification

```
$ python3 -m pytest tests/test_refresh_stock_ohlcv_symbols.py -q
7 passed

$ python3 -c "from tools.refresh_stock_ohlcv import normalize_yf_symbol as n; ..."
  '$SQ'       -> None          '$ADA'      -> None
  'SQ'        -> None          'ADA'       -> None
  '$BTC'      -> None          'SPY'       -> 'SPY'
  '$SPY'      -> 'SPY'         'BTC-USD'   -> 'BTC-USD'
  'EURUSD=X'  -> 'EURUSD=X'    'GC=F'      -> 'GC=F'
  '$'         -> None          ''          -> None
```

Both files `py_compile` clean. The test caught a contradiction in my first
expectation (`$SQ` must end up `None`, not `SQ`); the test was corrected, the
behaviour was not.

## Expected effect

The 840-line block of `No data found, symbol may be delisted` disappears entirely,
and the workflow logs one summary line instead. Symbols that cannot resolve are
no longer requested, which also removes one network round-trip per dead ticker
per run.

## Not changed

- ETF/fund "no fundamentals" is still a real coverage gap for fundamentals-based
  scoring, but it is not an error and is already modelled as `not_covered`.
- `picks-now-refresh`'s 403 on `git push` is a separate defect (fleet-wide main
  contention, 14 workflows affected) documented in
  `updates/2026-11-26-gha-latest-run-log-audit.md`.
