---
tags: [reference, data-sources, api-failover]
created: 2026-06-06
status: active
---

# Data Sources & API Failover Chains

Every module must follow the **API Failover Rule** (CLAUDE.md): never use a single endpoint. Every asset class has a proven failover chain already implemented in this repo.

---

## EQUITY — Price + Market Cap

**Module:** `alpha_engine/equity_price_failover.py`
**Wire-up:** `value_screener_runner.py` → `tools/run_ueps_pickers.py` → `ueps-pick-runner.yml`

### Quote (price + volume)
| # | Source | Auth | Rate Limit | Caveat |
|---|--------|------|-----------|--------|
| 1 | **Stooq** (stooq.com) | None (anon) | Unknown | `.us` suffix for US equities |
| 2 | **Finnhub** (`FINNHUB_API_KEY`) | API key | 60 rpm | Also env var `FINNHUB` |
| 3 | **Tiingo** (`TIINGO_API_KEY`) | API key | 500/day | IEX quote endpoint |
| 4 | **Twelve Data** (`TWELVE_DATA_API_KEY`) | API key | 800/day | `/quote` endpoint |
| 5 | **Alpha Vantage** (`ALPHA_VANTAGE_API_KEY`) | API key | 25/min | `GLOBAL_QUOTE` |
| 6 | **FMP** (`FMP_API_KEY`) | API key | 250/day | `/quote` |
| 7 | **yfinance** | None | Unreliable | **Last resort** — flaky in GHA |

### Market Cap (USD)
| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Finnhub** `/stock/profile2` | API key | Returns `marketCapitalization` in $M |
| 2 | **FMP** `/quote` | API key | `marketCap` in USD, batch-friendly |
| 3 | **Polygon.io** (`POLYGON_API_KEY`) | API key | 5/min |
| 4 | **SEC EDGAR** `companyfacts` | None | Derived: sharesOutstanding × price |
| 5 | **yfinance** `.info["marketCap"]` | None | **Last resort** |

### OHLCV History (needed by picks_now)
**No existing OHLCV-history failover for equities in this repo yet.**
Possible sources to wire:
- **FMP** `/stable/historical-price-eod/{symbol}` — 4 years free tier
- **Tiingo** `/tiingo/daily/{symbol}/prices` — 500/day free
- **Twelve Data** `/time_series` — 800/day free
- **Alpha Vantage** `TIME_SERIES_DAILY` — 25/min free
- **Polygon.io** `/v2/aggs/ticker/{symbol}/range/1/day/...` — 5/min free

### Analyst Consensus (needed by picks_now)
**Already partially wired** via `load_fmp_scores()` in `picks_now_professional.py` (FMP API key).
Also available from:
- **yfinance** `.info["recommendationMean", "targetMeanPrice", "numberOfAnalystOpinions"]`
- **Finnhub** `/stock/recommendation?symbol=`
- **FMP** `/rating/{symbol}` — analyst rating summary

---

## CRYPTO — OHLCV + Price + Funding

**Module:** `alpha_engine/api_failover.py`
**Exports:** `fetch_price()`, `fetch_klines()`, `fetch_ticker_24h()`, `fetch_funding_rate()`, `fetch_orderbook()`

### Spot OHLCV / Price
| # | Source | Auth | Notes |
|---|--------|------|-------|
| 1 | **Binance mirrors** | None | api, api1, api2, api3, data-api, binance.us |
| 2 | **Bybit v5** | None | market kline / tickers |
| 3 | **CoinGecko** | None | `/simple/price` + `/coins/{id}/ohlc` |
| 4 | **KuCoin** | None | `/v1/market/candles` |
| 5 | **CryptoCompare** | None | `histohour` / `histoday` |

### Futures (funding rate, OI)
| # | Source | Notes |
|---|--------|-------|
| 1 | **Binance fapi mirrors** | fapi, fapi1, fapi2 |
| 2 | **Bybit v5** | linear tickers / fundingRate |
| 3 | **CoinGlass** | If key available |

### GHA-specific handling
In CI (`GITHUB_ACTIONS` env), Binance US endpoints are preferred to avoid geo-blocking:
```python
if os.environ.get("GITHUB_ACTIONS"):
    _preferred_spot = ["https://data-api.binance.vision", "https://api.binance.us"]
```

---

## FOREX — Price

**Not centralized.** Currently only fetched via yfinance (`=X` suffix) in most modules.

### Sources found in codebase
| Source | Module | Auth |
|--------|--------|------|
| **yfinance** `EURUSD=X` | Various | None |
| **FX Empire** | Not yet wired | API key? |
| **OANDA** | Not yet wired | API key |
| **ExchangeRate-API** | Not yet wired | Free tier 1,500/mo |
| **Alpha Vantage** `CURRENCY_EXCHANGE_RATE` | Not wired for FX | 25/min |

### Existing implementations
- `alpha_engine/forex_backtest.py` — uses yfinance
- `forex_bb_mr_rehab_v1.py` — baby strategy using yfinance
- `fxp_price_history` DB table — MySQL price history storage

---

## COMMODITY — Price + Inventory

### Prices
| Source | Module | Auth |
|--------|--------|------|
| **yfinance** (`=F` suffix) | Various | None |
| **FRED** `api.stlouisfed.org` | `alpha_engine/commodity_bdi.py` | Free API key |
| **EIA** `api.eia.gov/v2` | `tools/co1_commodity_inventory_surprise_research.py` | Free API key |

### COT (Commitments of Traders)
- `cftc_cot_commercial_signal` — existing strategy (n=5, WR 0% — dead)
- Reported via `tools/pending_spa_scan.py`

---

## BOND — Yields + Prices

| Source | Module | Auth |
|--------|--------|------|
| **FRED** (DGS10, DGS2, etc.) | `alpha_engine/onchain_macro_strategies.py` | Free |
| **FRED** (BDIY Baltic Dry) | `alpha_engine/commodity_bdi.py` | Free |
| **yfinance** (TLT, IEF, SHY) | Various | None |

FRED CSV endpoints (no API key needed for basic series):
```python
fred_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
```

---

## MACRO — Economic Indicators

| Indicator | Source | Module |
|-----------|--------|--------|
| M2 Money Supply | FRED | `alpha_engine/cyclical_strategies.py` |
| Yield Curve (10Y-2Y) | FRED | `alpha_engine/onchain_macro_strategies.py` |
| Baltic Dry Index | FRED | `alpha_engine/commodity_bdi.py` |

---

## How to Wire Failover in a New Module

1. **Import the appropriate failover module** — `equity_price_failover` for equities, `api_failover` for crypto
2. **Declare the failover chain** as a list of (source_name, callable) tuples
3. **Iterate with try/except** — first success returns; failure falls through
4. **Use `urllib.request`** (stdlib) or `requests` — same pattern as existing modules
5. **Add 1h on-disk cache** if the same ticker will be fetched repeatedly (see `equity_price_failover.py` for the cache pattern)
6. **Log the source** so debug traces show which source served the data

### Picks-now specific (pending)
`tools/picks_now_professional.py` currently relies on yfinance for everything.
Priority order to wire:
1. **Crypto OHLCV** → `alpha_engine/api_failover.fetch_klines()`
2. **Equity analyst data** → FMP `/rating` endpoint (already have API key)
3. **Equity OHLCV history** → FMP `/historical-price-eod` or Tiingo
4. **Market cap** → `alpha_engine/equity_price_failover.fetch_market_cap()`

---

## Related

- [[reference/data-quality-checklist]]
- [[reference/performance-tiers]]
- [[strategies/READY-TO-TRADE-NOW]]
