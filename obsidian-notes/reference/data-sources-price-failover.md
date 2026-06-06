---
tags: [reference, data-sources, failover, infrastructure]
created: 2026-06-06
---

# Data Sources — Price Failover by Asset Class

> Sourced from: `alpha_engine/equity_price_failover.py`, `alpha_engine/api_failover.py`, `alpha_engine/ohlcv_failover.py`, `alpha_engine/universal_price_enricher.py`
> Rule: **Never depend on a single endpoint.** Always use 3+ fallback chain (per CLAUDE.md API Failover Rule).

---

## EQUITY (US stocks, ETFs)

**Module:** `alpha_engine/equity_price_failover.py`

### Quote (price + volume) — ordered by reliability

| # | Source | Auth | Rate limit | Notes |
|---|--------|------|-----------|-------|
| 1 | **Stooq** `stooq.com/q/l/?s=X.us` | None (anon) | None known | Free, no key needed. Needs `.us` suffix for US stocks. Requires `STOOQ_API_KEY` for historical endpoint |
| 2 | **Finnhub** `/quote` | `FINNHUB_API_KEY` | 60 req/min | Also has earnings, events. 60 rpm free |
| 3 | **Tiingo** IEX quote | `TIINGO_API_KEY` | 500/day | Reliable, clean data |
| 4 | **Twelve Data** `/quote` | `TWELVE_DATA_API_KEY` | 800/day | Good for OHLCV history too |
| 5 | **Alpha Vantage** `GLOBAL_QUOTE` | `ALPHA_VANTAGE_API_KEY` | 25/min | Slow but ubiquitous fallback |
| 6 | **Financial Modeling Prep (FMP)** `/quote` | `FMP_API_KEY` | 250/day | Batch-friendly, has fundamentals |
| 7 | **yfinance** `.history(period="5d")` | None | Flaky in GHA | **Last resort only** — 401s silently on GHA runners |

### Market Cap — ordered by reliability

| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Finnhub** `/stock/profile2` | `FINNHUB_API_KEY` | Returns marketCapitalization in $M |
| 2 | **FMP** `/quote` | `FMP_API_KEY` | `marketCap` in USD, batch-friendly |
| 3 | **Polygon.io** `/v3/reference/tickers` | `POLYGON_API_KEY` | 5/min free tier |
| 4 | **SEC EDGAR** `companyfacts` | None | Free, no auth. Derived: sharesOutstanding × price |
| 5 | **yfinance** `.info["marketCap"]` | None | Last resort |

### OHLCV History

| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Stooq** `/q/d/l/` | `STOOQ_API_KEY` (free reg) | Module: `alpha_engine/equity_data_stooq.py` |
| 2 | **Tiingo** `/tiingo/daily/` | `TIINGO_API_KEY` | Module: `alpha_engine/ohlcv_failover.py:91` |
| 3 | **yfinance** | None | Last resort |

---

## CRYPTO (perpetuals + spot)

**Module:** `alpha_engine/api_failover.py`

### Spot price + OHLCV — ordered

| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Binance** (spot) `api.binance.com` → api1 → api2 → api3 → data-api.binance.vision → binance.us | None | 4-mirror chain. `data-api.binance.vision` preferred (CDN, high uptime) |
| 2 | **CoinGecko** `api.coingecko.com/api/v3` | None (free) | Needs CG symbol ID mapping (`_to_coingecko_id`) |
| 3 | **KuCoin** `api.kucoin.com` | None (spot quotes) | Symbol format: `BTC-USDT` |
| 4 | **CryptoCompare** `min-api.cryptocompare.com/data` | None (limited) | OHLCV history fallback |

### Perpetuals / Funding Rate

| # | Source | Notes |
|---|--------|-------|
| 1 | **Binance FAPI** `fapi.binance.com` → fapi1 → fapi2 | Perp funding, OI, mark price |
| 2 | **KuCoin futures** | Fallback for OI/funding |

---

## FOREX

**Module:** `alpha_engine/forex_price_failover.py` ✅ WIRED 2026-06-06

Wired into `universal_price_enricher._fetch_yfinance_prices()` — called BEFORE yfinance for all `=X` symbols. Tested live: EUR/USD=1.1527, GBP/USD=1.3336, USD/JPY=160.293, AUD/USD=0.705, USD/CAD=1.3933, USD/CHF=0.7962 all from `yahoo_v8` with no auth.

### Failover chain (ordered)

| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Yahoo v8 chart** `query1.finance.yahoo.com/v8` | None | Primary — tested, real-time, all major pairs |
| 2 | **Frankfurter** `api.frankfurter.app` | None | ECB rates, daily, EUR as hub |
| 3 | **Open.er-api** `open.er-api.com/v6` | None | USD-base, hourly, bulk-efficient (module cache) |
| 4 | **Finnhub** `/forex/rates` | `FINNHUB`/`FINNHUB_API_KEY` env | 60 rpm; 403'd on free plan forex (key may be Basic tier) |
| 5 | **Twelve Data** `/price` | `TWELVE_DATA_API_KEY` env | 800/day |
| 6 | **Alpha Vantage** `CURRENCY_EXCHANGE_RATE` | `ALPHA_VANTAGE_API_KEY` env | 25/min, last resort |

---

## COMMODITY

**Module:** `alpha_engine/commodity_price_failover.py` ✅ WIRED 2026-06-06

Wired into `universal_price_enricher._fetch_yfinance_prices()` — called BEFORE yfinance for all `=F` symbols. Tested live: GC=F=4365.3, CL=F=90.54, SI=F=69.10, ZC=F=417.5, ZS=F=1121.5, NG=F=3.229, HG=F=6.285, CT=F=74.57 all from `yahoo_v8`.

### Failover chain (ordered)

| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Yahoo v8 chart** `query1.finance.yahoo.com/v8` | None | Primary — tested all 8 futures symbols |
| 2 | **Stooq** `stooq.com/q/l/?s=gc.f` | None | Free, patchy — HTML captcha possible |
| 3 | **FMP** `/quote` | `FMP_API_KEY` env | 250/day; 429 possible at rate limit |
| 4 | **Finnhub** `/quote` | `FINNHUB`/`FINNHUB_API_KEY` env | 60 rpm |
| 5 | **FRED CSV** `fred.stlouisfed.org` | None / `FRED_API_KEY` | Gold, crude, natgas, copper macro proxy; daily |

**Covered symbols:** GC=F (gold), SI=F (silver), CL=F (crude WTI), NG=F (nat gas), HG=F (copper), ZC=F (corn), ZS=F (soybeans), ZW=F (wheat), ZO=F (oats), KC=F (coffee), CT=F (cotton), SB=F (sugar), PA=F (palladium), PL=F (platinum), RB=F (gasoline), HO=F (heating oil)

---

## BOND / MACRO

**Module:** `alpha_engine/onchain_macro_strategies.py`, `alpha_engine/cyclical_strategies.py`, `alpha_engine/commodity_bdi.py`

| Source | Auth | What it provides | Used in |
|--------|------|-----------------|---------|
| **FRED** `fred.stlouisfed.org/graph/fredgraph.csv` | None (anon CSV) | DGS10, DGS2, M2, CPI, yield curve | Many modules |
| **FRED API** `api.stlouisfed.org/fred/series/observations` | `FRED_API_KEY` (free) | Same data, JSON, more reliable | `commodity_bdi.py` |
| **yfinance** `^TNX`, `^IRX` | None | Treasury yield proxies | Fallback |

---

## Earnings / Events

| Source | Auth | What it provides | Module |
|--------|------|-----------------|--------|
| **Finnhub** `/stock/earnings` | `FINNHUB_API_KEY` | EPS beats, calendar | `alpha_engine/earnings_calendar_fetcher.py` |
| **FMP** earnings endpoint | `FMP_API_KEY` | Quarterly EPS history | — |

---

## Gap Analysis — What Needs Wiring

| Class | Module | Status |
|-------|--------|--------|
| EQUITY | `equity_price_failover.py` | ✅ 7-source chain |
| CRYPTO | `api_failover.py` | ✅ 4-source chain |
| FOREX | `forex_price_failover.py` | ✅ 6-source chain WIRED 2026-06-06 |
| COMMODITY | `commodity_price_failover.py` | ✅ 5-source chain WIRED 2026-06-06 |
| BOND/MACRO | FRED CSV + FRED API | ✅ wired |

---

## Environment Variables Reference

| Var | Source | Free tier |
|-----|--------|----------|
| `FINNHUB_API_KEY` | finnhub.io | 60 rpm, free |
| `TIINGO_API_KEY` | tiingo.com | 500/day, free |
| `TWELVE_DATA_API_KEY` | twelvedata.com | 800/day, free |
| `ALPHA_VANTAGE_API_KEY` | alphavantage.co | 25/min, free |
| `FMP_API_KEY` | financialmodelingprep.com | 250/day, free |
| `POLYGON_API_KEY` | polygon.io | 5/min, free |
| `STOOQ_API_KEY` | stooq.com | Free registration |
| `FRED_API_KEY` | fred.stlouisfed.org | Free, unlimited |
| `EIA_API_KEY` | api.eia.gov | Free registration |
| `EXCHANGERATE_API_KEY` | exchangerate-api.com | 1500/month free |

## Related

- [[reference/data-quality-checklist]]
- [[asset-classes/FOREX]]
- [[asset-classes/COMMODITY]]
