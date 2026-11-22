# Block 1, Round 1 + 2 — FX spot acquisition and continuity audit

**Date:** 2026-11-22  ·  **Mode:** data acquisition only (no strategy testing, no trading)

## Requirement being satisfied (exact)

From [`tools/class_data_readiness.py`](../../tools/class_data_readiness.py:66):

```python
"FOREX": [("fx rates", DATA / "forex_rate_cache", 100)],
```

- Path: `data/forex_rate_cache/`
- Minimum: **100 real files** (the checker counts non-`.gitkeep` files recursively,
  *not* rows), so the shape that satisfies it is one file per pair.
- Side effect: `"BOND": [("rate curve", DATA / "forex_rate_cache", 1)]` shares the
  same directory, so filling it also clears BOND.

## Readiness BEFORE

```
  "BOND":    { "ready": false, "gaps": [ "rate curve: have 0, need 1" ] },
  "FOREX":   { "ready": false, "gaps": [ "fx rates: have 0, need 100" ] },
```

`data/forex_rate_cache/` contained only `.gitkeep`.

## Source attempts (in the instructed order of preference)

| # | Source | Request | Verbatim result | Outcome |
|---|--------|---------|-----------------|---------|
| 1 | Stooq daily CSV | `https://stooq.com/q/d/l/?s=eurusd&i=d` | `<!DOCTYPE html>...<noscript>This site requires JavaScript to verify your browser...</noscript><script nonce=...>` (JS proof-of-work challenge, **no CSV body**) | ❌ FAILED |
| 2 | Yahoo v8 chart (query1) | `https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?range=5y&interval=1d` | `Too Many Requests` | ❌ FAILED |
| 3 | Yahoo v8 chart (query2) | `https://query2.finance.yahoo.com/v8/finance/chart/EURUSD=X?range=5y&interval=1d` | `Too Many Requests` | ❌ FAILED |
| 4 | Frankfurter (ECB reference rates) | `https://api.frankfurter.app/2019-01-01..2026-11-21?from=USD&to=EUR,...` | `{"amount":1.0,"base":"EUR",...}` (valid JSON) | ✅ SUCCEEDED |

Frankfurter is not a new dependency: it is already adapter #2 in
[`alpha_engine/forex_price_failover.py`](../../alpha_engine/forex_price_failover.py:391).
No API key was used (no-key sources only).

## What was fetched

- Fetcher: [`tools/fx_spot_backfill.py`](../../tools/fx_spot_backfill.py:1)
- **Requests made: 1** (cap was 40). One multi-currency range call returns every
  date x every currency; pairs are derived locally.
- Raw response saved unmodified: `data/fx_spot_raw/frankfurter_USD_2019-01-01_2026-11-21.json`.
- **110 pair files** written as `data/forex_rate_cache/<PAIR>.csv` with a
  `date,close` header, spanning **2018-12-31 .. 2026-11-20, ~2,022 rows each**
  (9 years of ECB business days).
- Currencies: USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD, SEK, NOK, DKK (all G10 + DKK),
  giving 11 x 10 = 110 ordered pairs.

### Data integrity

- Every row is a date the source actually published. Nothing was interpolated,
  forward-filled, or synthesised.
- Cross pairs (e.g. `GBPJPY`) are exact arithmetic on two published ECB rates
  (`r[quote] / r[base]`); both legs are real observations on that date.
- Missing business days were deliberately left missing so the gap audit can see them.
- Note on nature of data: ECB reference rates are a daily fix, not tick OHLC. They
  are suitable for daily trend/carry research, not for intraday or spread modelling.

## Per-pair row counts (G10 majors, from the same call)

| Pair | Rows | First | Last |
|------|------|-------|------|
| EURUSD | 2022 | 2018-12-31 | 2026-11-20 |
| GBPUSD | 2022 | 2018-12-31 | 2026-11-20 |
| USDJPY | 2022 | 2018-12-31 | 2026-11-20 |
| AUDUSD | 2022 | 2018-12-31 | 2026-11-20 |
| USDCAD | 2022 | 2018-12-31 | 2026-11-20 |
| USDCHF | 2022 | 2018-12-31 | 2026-11-20 |
| NZDUSD | 2022 | 2018-12-31 | 2026-11-20 |

(All 110 files have the same 2,022-row span; `wc -l` reports 2023 lines including the header.)

## Round 1 gate

```
  "BOND":  { "ready": true, "gaps": [] },
  "FOREX": { "ready": true, "gaps": [] },
```

FOREX `fx rates` gap cleared: **110 files >= 100 required**. FOREX reads **READY**.
BOND also reads **READY** (1 file >= 1 required). Gate **PASSED**.

## Round 2 — continuity and gap audit

Tool: [`tools/fx_gap_audit.py`](../../tools/fx_gap_audit.py:1) →
[`reports/block1_r02_fx_gap_audit.json`](../../reports/block1_r02_fx_gap_audit.json).

- Gap definition: **business days** (Mon–Fri), with documented FX market closures
  excluded (New Year, Good Friday, Easter Monday, Christmas, Boxing Day, plus
  observed-shift weekdays). Weekends are never counted.
- Per pair: observation count, first date, last date, duplicate-date count, and
  every interior gap longer than 5 business days.

Result:

```
pairs audited: 110
pairs with >5bd interior gaps: 0 (0.00%)
gate: PASS  downgrade: False
```

- 0 duplicate dates in any pair.
- 0 pairs with >5-business-day interior gaps.
- Downgrade threshold (>20% of pairs gapped) not triggered; FOREX stays **READY**.

## Bonus Round 3 — commodity futures (attempted, FAILED)

Tried to populate `data/commodity_price_cache/` (needed by COMMODITY and FUTURES):

| Source | Request | Verbatim result |
|--------|---------|-----------------|
| Stooq | `https://stooq.com/q/d/l/?s=cl.f&i=d` | JS proof-of-work challenge HTML, no CSV |
| Yahoo v8 | `https://query1.finance.yahoo.com/v8/finance/chart/CL=F?range=2y&interval=1d` | `Too Many Requests` |
| FRED CSV | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO` | `curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR (err 2)`; retry `--http1.1`: `curl: (28) Operation timed out after 25003 milliseconds with 0 bytes received` |

Three distinct sources failed; nothing was written to `data/commodity_price_cache/`.
COMMODITY and FUTURES therefore remain **BLOCKED_DATA** (`futures prices: have 0, need 20`;
COMMODITY additionally `COT history: have 1, need 100`).

## Honest summary

FOREX is now testable on daily ECB spot series (110 pairs, ~2,022 rows each, no
interior gaps beyond normal market closures) for trend/carry-style research that
does not need intraday data or bid/ask spreads.
