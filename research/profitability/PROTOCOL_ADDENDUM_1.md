# Protocol Addendum 1 — ETF data source fallback

**Date:** 2026-11-14T18:22Z
**Status:** applied before any backtest result was inspected.

## Why

The locked v1 protocol named Stooq as the ETF/equity source. At data-load time Stooq returned a
JavaScript bot-challenge page (`This site requires JavaScript to verify your browser`) for every
symbol, and Yahoo returned HTTP 429. No price or backtest result had been produced when this
addendum was written.

## Change

ETF/equity daily closes are loaded from the **Nasdaq public quote API**:

```
https://api.nasdaq.com/api/quote/<SYMBOL>/historical?assetclass=etf&fromdate=2016-01-01&todate=<today>&limit=10000
```

- Keyless, returns ~10 years of daily OHLCV (observed 2,514 rows, 2016-11-14..2026-11-13).
- `Close/Last` is the regular close (not dividend-adjusted).
- Coverage is sufficient for the locked train (2018-2023) and OOS (2024+), and for the 12-month
  momentum lookback.

## Consequences / declared limitations

- AGG/BIL total return is understated because dividends are excluded from the close series.
  Strategy and benchmark use the same price-only series, so the **relative** comparison is
  unaffected; absolute CAGR/Sharpe for bond-heavy sleeves are conservative/understated.
- Nasdaq caps history near 10 years; the 2016 start still covers every v1 window.
- Stooq/Yahoo remain documented as attempted sources; no result depends on them.

No strategy parameter, split, cost, or acceptance gate was changed.
