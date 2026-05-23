# H-034 EQUITY anti-PEAD 1-day post-earnings over-reaction reversal — 2026-05-19

_Generated 2026-05-19T06:34:54+00:00 by `tools/h034_anti_pead_reversal.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** Fetches free yfinance data, runs the pre-registered signal through `edge_stability_harness` (imported UNMODIFIED), writes this report.

## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-034)

OPPOSITE-SIGN to killed H-010 (PEAD drift). For each earnings announcement on day d, measure the day-of price gap `GAP = close_d/close_{d-1}-1`. On day d+1 FADE the over-reaction: SHORT a strong gap-up, LONG a strong gap-down; enter at the open of d+1, exit at the close of d+2. 'Strong' = |GAP| above the name's own past-earnings top-tercile.

**Why this is NOT H-010:** H-010 uses the EPS SURPRISE (SUE), trades WITH the surprise sign, holds 20-60 days (a DRIFT). H-034 uses the day-of PRICE GAP, trades AGAINST the gap sign, holds 1 day (a REVERSAL). Opposite direction, different input, ~30x shorter horizon.

**No-look-ahead:** GAP uses `close_{d-1}` and `close_d` (known at the close of d); the strong-gap tercile uses only earnings strictly before this event; entry open d+1, exit close d+2.

## Data

- yfinance daily OHLCV + `get_earnings_dates`, free, no key. Cached to `tools/cache/h034_price_cache.json` + `h034_earnings_cache.json`.
- Fixed basket tickers with usable price + earnings history: 50.
- Earnings-event resolved records (continuous book): **1985**.
- Of which qualifying strong-gap (over-reaction) events: **709**.

| ticker | events | strong-gap | wins | WR |
|---|---|---|---|---|
| AAPL | 40 | 17 | 19 | 47.5% |
| MSFT | 40 | 11 | 24 | 60.0% |
| GOOGL | 40 | 19 | 26 | 65.0% |
| AMZN | 40 | 15 | 24 | 60.0% |
| META | 40 | 12 | 25 | 62.5% |
| NVDA | 39 | 12 | 22 | 56.4% |
| TSLA | 40 | 11 | 16 | 40.0% |
| JPM | 40 | 18 | 22 | 55.0% |
| BAC | 40 | 19 | 20 | 50.0% |
| WMT | 39 | 14 | 19 | 48.7% |
| XOM | 40 | 13 | 23 | 57.5% |
| CVX | 40 | 12 | 27 | 67.5% |
| JNJ | 40 | 11 | 17 | 42.5% |
| PG | 40 | 11 | 17 | 42.5% |
| KO | 40 | 12 | 17 | 42.5% |
| PEP | 40 | 19 | 23 | 57.5% |
| DIS | 40 | 21 | 22 | 55.0% |
| NFLX | 40 | 11 | 21 | 52.5% |
| INTC | 40 | 18 | 22 | 55.0% |
| AMD | 40 | 13 | 22 | 55.0% |
| CSCO | 40 | 10 | 25 | 62.5% |
| ORCL | 40 | 16 | 24 | 60.0% |
| CRM | 39 | 12 | 13 | 33.3% |
| ADBE | 40 | 15 | 22 | 55.0% |
| QCOM | 40 | 14 | 22 | 55.0% |
| TXN | 40 | 14 | 20 | 50.0% |
| HD | 39 | 15 | 15 | 38.5% |
| MCD | 40 | 8 | 21 | 52.5% |
| NKE | 40 | 12 | 23 | 57.5% |
| COST | 40 | 11 | 17 | 42.5% |
| UNH | 40 | 18 | 16 | 40.0% |
| PFE | 40 | 14 | 19 | 47.5% |
| MRK | 40 | 15 | 14 | 35.0% |
| ABBV | 40 | 13 | 18 | 45.0% |
| T | 40 | 22 | 21 | 52.5% |
| VZ | 40 | 15 | 20 | 50.0% |
| C | 40 | 16 | 20 | 50.0% |
| GS | 40 | 13 | 15 | 37.5% |
| MS | 40 | 16 | 18 | 45.0% |
| CAT | 40 | 12 | 24 | 60.0% |
| BA | 40 | 12 | 18 | 45.0% |
| GE | 40 | 21 | 14 | 35.0% |
| F | 40 | 11 | 23 | 57.5% |
| GM | 40 | 17 | 21 | 52.5% |
| UBER | 29 | 11 | 15 | 51.7% |
| PYPL | 40 | 20 | 21 | 52.5% |
| SBUX | 40 | 11 | 22 | 55.0% |
| MU | 40 | 11 | 26 | 65.0% |
| AMAT | 40 | 11 | 19 | 47.5% |
| LRCX | 40 | 14 | 22 | 55.0% |

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): ``
- windows scored: 0  (strong: 0)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — only 0/0 windows reach eff>=0.3

## Edge & cost survival (over the qualifying strong-gap events)

- pooled WR: 52.19%
- gross mean per-trade return: 0.002215
- net mean per-trade return (after 30bps): -0.000785
- cost-survival (|gross| > 30bps): 92.1%  (gate >= 60%: PASS)

## VERDICT: **UNTESTED**

Honest non-verdict — the harness did not get >= 3 scored 14-day windows. Earnings events are quarterly per name, so even a 50-name basket gives sparse 14-day windows; the blocker is event density, not design.
