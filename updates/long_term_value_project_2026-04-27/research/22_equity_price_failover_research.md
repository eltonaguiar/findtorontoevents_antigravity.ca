# Equity price + market-cap failover — research note (2026-04-28)

**Branch:** `fix/ueps-equity-price-failover-2026-04-28`
**Module:** `alpha_engine/equity_price_failover.py`
**Tests:** `tests/test_equity_price_failover.py` (26 tests, all passing)
**Trigger:** GH Actions run `25066227910` logged
`yfinance unavailable — market caps cannot be fetched` for every ticker, so
`tools/run_ueps_pickers.py` emitted `long=0 short=0` on every cron cycle
since the UEPS pick-runner workflow shipped.

## Root cause

`.github/workflows/ueps-pick-runner.yml` (and three sibling UEPS workflows)
contained a conditional install of the form:

```yaml
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  pip install pandas pyarrow yfinance
fi
```

`requirements.txt` is checked in but does NOT pin `yfinance`. Because the
`if`-branch always wins, yfinance was never installed on the runner. The
lazy import inside `value_screener_runner.fetch_market_caps_via_yfinance`
silently returned `dict.fromkeys(tickers, None)`, the SafetyGate then
filtered out every ticker because mc < 300M, and the screener emitted
zero picks. Same failure mode for `value_screener_weekly.yml`,
`swing_screener_daily.yml`, and `value_resolver_quarterly.yml`.

**Fix #1 (1-line).** All four UEPS workflows now `pip install pandas pyarrow
yfinance` UNCONDITIONALLY before the optional `requirements.txt` install,
mirroring the pattern used by `crypto-smart-picks.yml`.

## Why a failover chain is required, not just a yfinance fix

Per `CLAUDE.md` "API Failover Rule" (see also `feedback_api_failover.md`):
> Never use a single endpoint. Always use 3+ fallback chain.

The crypto path (`alpha_engine/api_failover.py`) already does this for
Binance via Bybit/CoinGecko/KuCoin/CryptoCompare. The equity path was a
bare `yfinance.Ticker(...).history(...)` call — single point of failure,
no cache, no source diversity. yfinance has hit the runner three times in
the last two weeks alone (HTTP 401, 429, and the import-failure observed
in run 25066227910). Even with yfinance always installed, **a single bad
day at Yahoo silently zeroes UEPS picks** until someone notices the
dashboard tile is empty.

## Sources surveyed (web + Cerebras Qwen-3-235B)

I asked Cerebras (`qwen-3-235b-a22b-instruct-2507`) for free quote APIs
known working in 2024-2025, beyond the seven I already had on the
shortlist. Cross-checked every suggestion against vendor docs via web
search. Key findings:

| Source | Free-tier limit | Has market cap? | GHA gotcha | Verdict |
|---|---|---|---|---|
| **Stooq** anonymous quote endpoint | none documented | NO (price only) | EOD CSV, .us suffix required | TIER 1 — primary, no auth |
| **Finnhub** `/quote` + `/stock/profile2` | 60 rpm | YES (in `marketCapitalization` $M) | Requires key (already have `FINNHUB` env var) | TIER 2 quote / TIER 1 mc |
| **Tiingo** `/iex` | 500/day | NO | Requires key | TIER 3 quote |
| **Twelve Data** `/quote` | 800/day | NO (separate `/profile` call) | Requires key | TIER 4 quote |
| **Alpha Vantage** `GLOBAL_QUOTE` | 25/min, 500/day | NO | IP-throttled — GHA shared IPs collide | TIER 5 quote |
| **Financial Modeling Prep** `/quote` | 250/day | YES (in `marketCap` USD) | Requires key | TIER 6 quote / TIER 2 mc — bonus: piggybacks marketCap |
| **Polygon.io** `/v3/reference/tickers` | 5/min | YES | Requires key | TIER 3 mc |
| **SEC EDGAR** `companyfacts` | none (polite UA only) | DERIVED (sharesOutstanding × price) | 10-Q/10-K lag of 30-90 days | TIER 4 mc — no auth, last-mile guarantee |
| **yfinance** library | scrape, flaky | YES (in `info["marketCap"]`) | Import failure, 401/429 | TIER 5 quote / TIER 5 mc — last resort |

### Sources Cerebras suggested but rejected

- **IEX Cloud** — 50k messages/month free tier was deprecated in mid-2024
  (the company announced full retirement Aug 31 2024). Cerebras flagged
  "deprecation risk" — confirmed via vendor blog. **Not implemented.**
- **RapidAPI Yahoo Finance** — proxies Yahoo, 100/day free, but the
  RapidAPI marketplace can throttle GHA-runner-class traffic per its
  ToS. Not a meaningful upgrade over the direct yfinance call we
  already have. **Not implemented.**
- **Marketstack** — 100/month free is too tight to be useful as a
  fallback for a 50-ticker universe running every 4h (~ 7,200/month
  required). Could be a future add for daily-cadence callers but not
  a fit for the pick-runner. **Not implemented.**
- **EOD Historical Data** — 20/day free tier defeats the purpose of a
  fallback. **Not implemented.**

## Failover order chosen

Quote (price + volume) chain:

1. **Stooq** — no auth, no rate limit, EOD lag is acceptable since the
   value-screener uses prices to compute market_cap × $300M floor and
   intrinsic-value estimates that don't move on a daily basis.
2. **Finnhub** — best free-tier quality with a key we already provision
   (`FINNHUB` env var, optional alias `FINNHUB_API_KEY`).
3. **Tiingo** — high-quality IEX quote.
4. **Twelve Data** — broad coverage, redundant with Tiingo.
5. **Alpha Vantage** — last commercial fallback. Treat as flaky.
6. **FMP** — adds price + market cap on a single call.
7. **yfinance** — last resort. Demoted from "default" to "tier 5".

Market-cap chain:

1. **Finnhub `/stock/profile2`** — direct, in $M, converts to $.
2. **FMP `/quote` piggyback** — re-uses the FMP adapter already in the
   quote chain. Free.
3. **Polygon `/v3/reference/tickers`** — institutional source, 5/min.
4. **SEC EDGAR companyfacts** — no auth, derived from
   `CommonStockSharesOutstanding × fetch_quote(price)`. This is the
   "always-works" guarantor since EDGAR has no rate limit and no
   auth, and we already have a FundamentalsFetcher that maps it.
5. **yfinance** — last resort.

## Caching

1-hour on-disk TTL at `data/equity_quote_cache/{TICKER}.{kind}.json`.
Successful fetches dedupe across runs within the same hour, so the
50-ticker S&P-100 universe burns at most 50 fetches per cron cycle on
any one source instead of `50 × 6 sources`. Cache is keyed by ticker +
kind (`quote` vs `marketcap`) so they refresh independently. TTL is
controllable via `EQUITY_QUOTE_CACHE_TTL_SEC` env var for tests.

## Wire-up

Per CLAUDE.md "Wire-Up Rule" this is wired into the production pick-
generation path:

- `alpha_engine/value_screener_runner.py` — both `fetch_*_via_yfinance`
  helpers now route through `equity_price_failover.fetch_*_default`.
  Names preserved for back-compat with `tools/run_ueps_pickers.py` and
  the existing test suite.
- `tools/run_ueps_pickers.py` — unchanged, imports the (now failover-
  backed) helpers from `value_screener_runner`.
- `.github/workflows/ueps-pick-runner.yml` — production caller, runs
  every 4h, writes `audit_dashboard/data/ueps_picks.json`.
- `.github/workflows/value_screener_weekly.yml` — Mon 06:00 UTC weekly
  bulk emit.
- `.github/workflows/swing_screener_daily.yml` — daily swing layer.
- `.github/workflows/value_resolver_quarterly.yml` — quarterly thesis
  resolver.

## Test plan executed

- `pytest tests/test_equity_price_failover.py` — 26/26 passed.
- `pytest tests/test_value_screener_runner.py` — 16/16 passed (no
  regression from the wire-in).
- Adapters use `_HTTP_GET_JSON` / `_HTTP_GET_TEXT` injection hooks —
  zero live network calls in CI.

## Source-of-record per ticker (post-deploy expectation)

Once the 4h cron fires post-merge, expect the log line
`fetch_quote(<TICKER>) <- <SOURCE> @ <PRICE>` to dominate with
`<SOURCE>=stooq` (free, primary). Tickers that Stooq has gated or
returns N/D for will fall through to `finnhub` once the runner has the
`FINNHUB` env var (already configured). Market caps will primarily come
from `finnhub` (tier 1) since we have the key, with `edgar` as the
no-auth always-on safety net for any ticker the commercial sources fail
on.

## Sources

- [Finnhub free-tier overview](https://finnhub.io/)
- [Alpha Vantage free-tier overview](https://www.alphavantage.co/)
- [EODHD live API page (delayed quotes confirmed)](https://eodhd.com/financial-apis/live-v2-for-us-stocks-extended-quotes-2025)
- [Top 5 free stock APIs 2025 (DEV.to)](https://dev.to/williamsmithh/top-5-stock-market-data-api-free-tools-for-developers-in-2025-3601)
- [Best Free Finance APIs 2025 (NoteAPIConnector)](https://noteapiconnector.com/best-free-finance-apis)
- [Financial Modeling Prep pricing](https://site.financialmodelingprep.com/pricing-plans)
- [SEC EDGAR APIs (official)](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- AI second-opinion: Cerebras `qwen-3-235b-a22b-instruct-2507` (Apr 28 2026)
