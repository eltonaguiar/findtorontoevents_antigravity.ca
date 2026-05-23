# Asset-Class Data Supplements — 90-Day Plan Enhancement (2026-05-15)

**Companion to:** `reports/SUPREME_PLAN_90days.md` + the 8 `reports/asset_class_90day_plan_<CLASS>_2026-05-15.md` files.
**Author:** Claude (Opus 4.7) + 3-agent research swarm.
**Purpose:** supplement each asset-class 90-day plan with (a) free APIs, (b) more prediction-market data,
(c) copytrader picks — with concrete free-tier limits, endpoint URLs, and the *existing repo module* to
wire each into.

## Headline finding

**Most of the needed data is already coded but unwired.** `bond_data_fred.py` has the full yield curve
(unused — `bond-agent.yml` runs `SKIP_FRED=1`); `commodity_carry_momo.json` has 18-symbol carry
(`OPT_IN_SIDECAR`, no caller); `cftc_cot_fetcher.py`, `hyperliquid_scraper.py`, `funding_rate_scanner.py`,
`kalshi_signals.py`, `polymarket_signals.py`, `copy_trader_bridge.py`, `zulutrade_scraper.py`,
`myfxbook_scraper.py` all exist. **The gap is wiring/activation, not greenfield code.**

**Single highest-leverage NEW integration across all classes: Kalshi.** `alpha_engine/kalshi_signals.py`
exists, the public market-data API needs **no key**, and Kalshi carries the richest Fed-rate / FOMC /
CPI / GDP / weather / index-range market set — directly relevant to BOND, COMMODITY, FUTURES, EQUITY, FX.

**Honest copytrader verdict:** real free retail-copytrade feeds exist only for CRYPTO (Hyperliquid
leaderboard — on-chain, verifiable) and FOREX (ZuluTrade, MyFXBook). For COMMODITY/BOND/FUTURES there is
no credible free retail copytrade feed — **CFTC COT / TFF commercial-vs-speculator positioning is the
legitimate "smart-money copytrading" substitute** and is already partially wired. For PENNY_MEME,
copytrader feeds are a *liability* (clones net-negative −10) — filter them out, don't add them.

---

## EQUITY — Data Supplement

**Current gap:** fundamentals are a thin yfinance wrapper (PE/ROE, 6h cache, no point-in-time); no
primary SEC/EDGAR, no real earnings calendar, no FRED macro. The VIX-regime Tier-1 edge is researched
but unwired (M-009 / M-032 pending).

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| SEC EDGAR | 10-K/10-Q financials, Form 4 insider, 8-K | Unlimited, 10 req/s; `User-Agent` header required | None | `data.sec.gov/api/xbrl/...`, `submissions/CIK{n}.json` | new `alpha_engine/edgar_fundamentals.py` → `equity_factor_model.py` |
| FRED | VIX (`VIXCLS`), yield curve (`T10Y2Y`), ISM, CPI | Unlimited | Free key | `api.stlouisfed.org/fred/series/observations` | M-032 — `audit_trail/vix_regime_gate.py` |
| Finnhub | Real earnings calendar + surprise | 60 req/min | Free key | `finnhub.io/api/v1/calendar/earnings` | M-009 PEAD — `equity_factor_model.py` |
| Financial Modeling Prep | Fundamentals, ratios, estimates | 250 req/day, 5y history | Free key | `financialmodelingprep.com/api/v3/...` | backup fundamentals in `equity_factor_model.py` |
| Alpha Vantage | OHLCV / overview | **only 25 req/day** — last-resort failover only | Free key | `alphavantage.co/query` | tertiary failover in `equity_price_failover.py` |

**Prediction markets:** Kalshi has S&P 500 / Nasdaq EOD + weekly-range markets, Fed-decision and
CPI/jobs-print markets, per-company earnings-beat markets. Kalshi-implied VIX-spike / hawkish-Fed
probability feeds the VIX gate; an earnings-beat price is an orthogonal cross-check on the PEAD boost.
Free, no key: `external-api.kalshi.com/trade-api/v2` (30 req/s). Repo already has
`alpha_engine/kalshi_signals.py` + `prediction_market_consensus.py` — extend.

**Copytrader:** the `copy_trader_intel/` pipeline (best category: +25 boost, 59.6% WR / n=47) fits EQUITY.
Real modules: `alpha_engine/copytrader_integration.py`, `copy_trader_bridge.py`,
`tools/build_unified_copytrade_candidates.py`. Promote `copy_trader_intel` as a *primary* EQUITY signal
with elite filtering; zero out `copy_trader_clones` (currently −10).

**Priority — P0.** First step: in `audit_trail/vix_regime_gate.py` replace the yfinance `^VIX` pull with
a FRED `VIXCLS` fetch behind the existing `_VIX_CACHE`, gated by `FRED_API_KEY`, opt-in sidecar +
Wiring Plan. `edgar_fundamentals.py` is P1.

---

## ETF — Data Supplement

**Current gap:** `backtest_etf_economic.py` failed with DATA_GAP (no FRED key). Economic/macro-regime
rotation (M-032) unwired. Sector rotation relies purely on yfinance price momentum — no holdings/flows.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| FRED | Yield curve, CPI, ISM — macro-regime overlay | Unlimited | Free key | `api.stlouisfed.org/fred/...` | new `alpha_engine/etf_macro_regime.py`; unblocks `tools/backtest_etf_economic.py` |
| Issuer holdings JSON (SSGA / iShares) | Sector-ETF constituents + weights | none published; scrape politely | None | issuer fund pages (`.ajax?fileType=json`) | optional enrichment for `tools/etf_sector_emitter.py` |
| Finnhub | ETF profile, `/etf/holdings` | 60 req/min | Free key | `finnhub.io/api/v1/etf/holdings` | cross-check in `etf_strategies.py` |

Caveat: **etfdb.com has no free API**; real ETF *flow* data is paid. Free composition = issuer JSON or
Finnhub.

**Prediction markets:** Kalshi S&P/Nasdaq range + Fed-decision + recession-odds markets map onto
sector-rotation regime gating — high recession probability → tilt defensive (XLP/XLU/XLV), reinforcing
the VIX gate. Extend `kalshi_signals.py`.

**Copytrader:** low fit for sector baskets. Best use: `alpha_engine/copy_trader_analyzer.py` to detect
when tracked traders cluster into a sector → confluence booster in `score_booster.py`, not a primary
emitter.

**Priority — P1.** First step: add `FRED_API_KEY`, create `alpha_engine/etf_macro_regime.py` sidecar,
repoint `tools/backtest_etf_economic.py` at FRED `T10Y2Y`. (The plan's true P0 — enabling
`etf_sector_emitter.py` + VIX gate — needs no new data and ships first.)

---

## PENNY_MEME — Data Supplement

**Current gap:** full quarantine (MEMECOIN PF 0.50 / WR 15.7%; PENNY_STOCK PF 0.19 / WR 6.8%), 0% risk
allocation. The gap is **not** "more signal" — it is a missing hard liquidity/ADV gate, low-float
detection, and dilution (8-K) early warning so toxic symbols never reach emitters.

**Free APIs (defensive use only — filters, not signal generators)**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| SEC EDGAR | 8-K / S-1 / 424B5 dilution + reverse-split; shares-outstanding | Unlimited, 10 req/s; UA header | None | `data.sec.gov/submissions/CIK{n}.json`, `efts.sec.gov` full-text | new `is_low_quality_or_meme()` in `config.py` + `scanner.py` |
| LunarCrush | Meme-coin social volume/sentiment | per existing key | `LUNARCRUSH_API` (already in repo) | `lunarcrush.com/api4/public/...` | research-only — confirm pump=hype, do not emit |
| Reddit API | r/pennystocks, r/wallstreetbets mention spikes | free OAuth, 100 req/min | free OAuth app | `oauth.reddit.com/r/{sub}/...` | quarantine-evidence autopsy script only |
| StockTwits | symbol-stream volume | **currently unreliable** — registrations paused; public stream unstable | none | `api.stocktwits.com/api/2/streams/symbol/{SYM}.json` | skip — note as unavailable |

**Prediction markets:** **not applicable** — no Kalshi/Polymarket markets meaningfully cover penny
stocks / meme coins. State this explicitly as out-of-scope for this bucket.

**Copytrader:** **actively harmful here** — `copy_trader_clones` is net-negative (−10); copytrader/clone
sources historically over-emitted memes. Ensure `copytrader_integration.py` + `clone_ab_tester.py`
outputs are filtered by the new `is_low_quality_or_meme()` gate before `quality_gates.py`.

**Priority — P0.** First step: add `is_low_quality_or_meme(symbol)` to `alpha_engine/config.py` (static
list + heuristic: market-cap < $2B or ADV < $5M), call it in `scanner.py:877` + `production_scanner.py`
to return `[]`. SEC 8-K dilution detection is a P1 layer on top.

---

## CRYPTO — Data Supplement

**Current gap:** high volume (n≈8011) but sub-T2 quality (PF 1.36 / WR 46.7%) — 179-symbol noisy
universe, mediocre sources. On-chain data is "minimal/experimental" (BTC/ETH only). Funding,
liquidations, whale flows, prediction-market data are named as underused low-cost edges.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| Binance public (perps) | Funding rate, OI, klines | ~1200 wt/min, no key | None | `fapi.binance.com/fapi/v1/{fundingRate,openInterest}` | `funding_rate_scanner.py`, `crypto_data_failover.py` |
| CoinGecko (free) | 24h ADV, market cap — for ADV liquidity gate | ~30/min, ~10k/mo | None | `api.coingecko.com/api/v3/coins/markets` | new `is_liquid_crypto()` in `asset_class.py` |
| CoinGlass (free tier) | Funding, OI, liquidations, long/short ratio | basic free; paid from $29/mo | free key | `open-api-v4.coinglass.com/api/...` | `coinglass_integration.py` |
| DefiLlama | Protocol/chain TVL, stablecoin flows | genuinely free, no key | None | `api.llama.fi/v2/chains`, `/protocols` | `paper_trading/strategies/defi_tvl_momentum.py` |
| Hyperliquid public | OI, funding, mark price + copytrader leaderboard | free, no key, on-chain | None | `api.hyperliquid.xyz/info` (POST) | `copy_trader_intel/hyperliquid_scraper.py` |
| Alternative.me | Fear & Greed index | free, no key | None | `api.alternative.me/fng/` | `score_booster.py` |

Reuse the repo's failover (`crypto_data_failover.py`: Binance api/api1/api2/api3 → CoinGecko → KuCoin →
CryptoCompare) — do not add single-endpoint calls.

**Prediction markets:** Polymarket has rich BTC/ETH price-by-date + spot-ETF-flow markets (implied-price
distribution + directional bias); Kalshi runs CFTC-regulated crypto-price series. Free, no key:
`gamma-api.polymarket.com/markets`, `clob.polymarket.com`, Kalshi. Already wired in
`polymarket_signals.py` + `kalshi_signals.py` → feed `prediction_market_consensus.py` /
`pm_consensus_overlay.py`.

**Copytrader:** the strongest real copytrader signal. Hyperliquid leaderboard
(`stats-data.hyperliquid.xyz/Mainnet/leaderboard`) = free, on-chain, verifiable PnL — already scraped by
`copy_trader_intel/hyperliquid_scraper.py`. OKX/Bybit copy-trading via `okx_scraper.py` /
`bybit_scraper.py`. Bridge into live scanner: `alpha_engine/copy_trader_bridge.py` (reads
`copy_trader_intel/data/active_picks.json`, drops unverified clones).

**Priority — P0.** First step: implement `is_liquid_crypto(symbol)` + 24h-ADV gate in
`alpha_engine/asset_class.py` (cached CoinGecko snapshot), call before emit in `production_scanner.py`.
**P1:** enable Hyperliquid leaderboard ingestion via `copy_trader_bridge.py`; turn on
`CRYPTO_ONCHAIN_MOMENTUM_ENABLED` with Binance funding + DefiLlama TVL confirmation.

---

## FOREX — Data Supplement

**Current gap:** weakest class (PF 0.81, negative expectancy, `sizing_allowed=false`). "COT" is a fake
price-zscore proxy (not real CFTC positioning); carry uses a hardcoded `carry_yield_diff` snapshot (not
live rates); no live DXY regime gate; `smart_picks_by_asset.FOREX` is empty.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| FRED | DXY, Fed funds, US10Y, policy rates → live carry + DXY gate | free, generous | free key | `api.stlouisfed.org/fred/series/observations` | replace static `carry_yield_diff` in `config.py`; `_fx_regime_ok` in `forex_strategies.py` |
| CFTC Socrata | real COT — commercial/non-commercial net for 6E/6B/6J/6A | free, no key | None (token optional) | `publicdata.cftc.gov/resource/...` | extend `tools/cot_fetcher_socrata.py`; replace zscore proxy `forex_strategies.py:536` |
| ECB | euro reference FX rates, ECB policy rate | free, no key | None | `data-api.ecb.europa.eu/service/data/EXR/...` | carry cross-check in `config.py` |
| Frankfurter | daily/historical FX (ECB-sourced) — genuinely free | free, no key | None | `api.frankfurter.app/latest` | price cross-validation in `forex_strategies.py` |
| MyFXBook Community Outlook | retail long/short sentiment → fade-retail contrarian | free, no key | None | `myfxbook.com/api/get-community-outlook.json` | `copy_trader_intel/myfxbook_scraper.py` |
| Finnhub (forex) | FX candles, economic calendar | 60/min | free key | `finnhub.io/api/v1/...` | session gate in `forex_strategies.py` |

Note: `exchangerate.host` is now key-gated — prefer **Frankfurter**. ForexFactory has no free API —
Finnhub's economic calendar is the safer free option.

**Prediction markets:** Kalshi Fed-rate-decision / CPI / recession / election markets all move USD/DXY
and JPY crosses — DXY-regime + event-risk overlay (hawkish-Fed market biases USD-base pairs, gates the
carry strategy). Free, no key: Kalshi, Polymarket Gamma/CLOB. Wire `kalshi_signals.py` →
`prediction_market_consensus.py` → macro bias flag consumed by `forex_strategies.py` + `quality_gates.py`.

**Copytrader:** best external edge = verified-broker copy traders. **ZuluTrade** already implemented in
`copy_trader_intel/zulutrade_scraper.py` (public `webapi/zulurank/providers`, no key). **MyFXBook
AutoTrade** partially covered (`myfxbook_scraper.py`); community-outlook endpoint free, AutoTrade
positions need session auth — opt-in sidecar. MQL5 has no clean free API — manual benchmark only.

**Priority — P1** (plan verdict is prune-and-de-risk; external data comes after P0 direction/symbol
gates). First step: extend `tools/cot_fetcher_socrata.py` to pull CFTC FX-futures positioning
(6E/6B/6J/6A), replace the fake zscore proxy in `forex_strategies.py:536`; concurrently swap the
hardcoded `carry_yield_diff` in `config.py` for live FRED policy rates.

---

## COMMODITY — Data Supplement

**Current gap:** 73% of class PnL is one ag future (CT=F) via an over-emitting COT strategy that
collapses to n≈5 / PF 0.17 once deduped. `commodity_carry_momo_double_sort` exists as data only
(`commodity_carry_momo.json`, 18 symbols) but is `OPT_IN_SIDECAR` with no production caller. No
fundamental/inventory/weather feed — pure price + COT.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| CFTC COT (Socrata) | commercial vs non-commercial net positioning | free; weekly Fri (3d lag) | None (token optional) | `publicreporting.cftc.gov/resource/6dca-aqww.json` | already wired `cot_fetcher_socrata.py` + `cftc_cot_fetcher.py` — extend beyond CT=F |
| EIA Open Data v2 | weekly crude/natgas/distillate inventories, production | free; ~9000 req/hr | API key `EIA_API_KEY` | `api.eia.gov/v2/` | new `tools/eia_data_fetcher.py` → NG=F / energy carry |
| USDA NASS + WASDE | crop production/stocks, monthly supply-demand | free; 50k rows/call | API key `USDA_NASS_KEY` | `quickstats.nass.usda.gov/api/api_GET/` | new `tools/usda_nass_fetcher.py` — seasonal ag |
| FRED commodity series | PPI commodity indices, oil/gas/metals | free | `FRED_API_KEY` (in repo) | `api.stlouisfed.org/fred/...` | reuse `tools/fred_data_fetcher.py` |
| NOAA CDO / NWS | weather/precip/temp anomalies (agri + natgas demand) | free; NOAA 10k/day, NWS no key | NOAA token; NWS none | `ncdc.noaa.gov/cdo-web/api/v2/`, `api.weather.gov/` | new `tools/weather_fetcher.py` — side signal |

**Prediction markets:** Kalshi is the strongest fit — energy markets (natgas storage builds, crude
ranges, gasoline), weather markets (temp/precip/hurricane), ag-relevant macro. Forward-looking
confirm/veto on COT/carry (COT short cotton + Kalshi weather implies bullish growing-season risk →
downgrade). Kalshi market data needs no auth → `kalshi_signals.py` → `prediction_market_consensus.py`.
Polymarket has fewer commodity markets — lower priority.

**Copytrader:** thin and crypto-biased. The honest substitute is **CFTC COT itself** — commercials
(producers/hedgers) = smart-money; non-commercials (managed money/CTAs) = the crowd. The
`commercial_net_extreme` z-score in `cftc_cot_fetcher.py` already encodes this. Do not promise an
external commodity copytrader feed.

**Priority — P1.** First step: extend `tools/cftc_cot_fetcher.py` `--contracts` default to add KC=F,
SB=F, CC=F, ZC=F, ZS=F, ZW=F, then a Wiring-Plan PR consuming `commodity_carry_momo.json` in
`alpha_engine/smart_picks_engine.py`. EIA/USDA/NOAA fetchers are P2.

---

## BOND — Data Supplement

**Current gap:** n=11 resolved, PF 0.66, 79% TLT concentration; effective universe 2 of 14 symbols. The
`bond-agent.yml` emitter runs `SKIP_FRED=1` — the single most valuable bond source (the full yield
curve) is **not feeding live picks**. Three academic pilots specced but unwired.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| FRED (curve + spreads) | DGS1/2/5/10/30, T10Y2Y/T10Y3M, T10YIE/T5YIE breakevens, HY/IG OAS | free | `FRED_API_KEY` | `api.stlouisfed.org/fred/...` | **already coded** `alpha_engine/bond_data_fred.py` — gap is live emitter not consuming it |
| US Treasury FiscalData | daily par yield curve, auctions, debt | free, **no key** | None | `api.fiscaldata.treasury.gov/...` | new `tools/treasury_fiscaldata_fetcher.py` — no-key cross-check of FRED |
| Cboe ^MOVE via yfinance | bond-vol regime gate | free, unofficial | None | `yfinance` | Pilot B curve-carry MOVE gate |
| Yahoo bond ETFs | OHLCV for all 14 BOND_SYMBOLS | free | None | `yfinance` | already used `bond_scanner.py` |

Highest-leverage move: **stop running the emitter with `SKIP_FRED=1`** — `bond_data_fred.py` already has
the full curated curve + OAS bundle.

**Prediction markets:** Kalshi is **extremely strong** for BOND — the richest Fed-rate / FOMC / CPI /
inflation / GDP / unemployment market set anywhere, all direct curve drivers. A Kalshi Fed-funds market
implying a hike not priced by the 2Y → directional veto on long-duration TLT bets (the exact
concentration that lost money). Wire `kalshi_signals.py` → `prediction_market_consensus.py` as a macro
regime gate.

**Copytrader:** no credible free bond copytrading source. Honest analogue: CFTC COT *financial* (TFF —
Traders in Financial Futures) reports for ZN/ZB/ZT — dealer vs asset-manager vs leveraged-fund
positioning, published free. Do not claim a bond copytrader feed.

**Priority — P2** (plan correctly de-prioritizes BOND for capital). One cheap P1-hygiene step: edit
`.github/workflows/bond-agent.yml` to drop `SKIP_FRED=1` so `bond_yield_curve_slope` consumes
`bond_data_fred.py`; lower `BOND_ELITE_FLOOR` to 32–35 per the plan's Phase 1.

---

## FUTURES — Data Supplement

**Current gap:** n=0 — genuinely dead. ~70% of all `=F` activity is classified into COMMODITY by
root-symbol logic (`dashboard_generator.py:3344`), starving the FUTURES tile. The 4 academic strategies
fire rarely and fail curation. Plan's primary recommendation is **merge**, not revive.

**Free APIs to add**

| Source | Provides | Free-tier limit | Auth | Endpoint | Wire-in target |
|---|---|---|---|---|---|
| CFTC COT — TFF (financial) | dealer / asset-manager / leveraged-fund net for ES, NQ, ZN, ZB, 6E, 6J | free, weekly | None (Socrata) | `publicreporting.cftc.gov/resource/gpe5-46if.json` | switch `cftc_cot_fetcher.py` default source to TFF for financial futures |
| CME delayed quotes (via Yahoo) | continuous `=F` OHLCV ES/NQ/YM/RTY/ZN/ZT/ZB/6E/6B/6J | free, ~10-min delayed | None | `yfinance` | already used `futures_strategies.py` |
| EIA Open Data v2 | energy fundamentals (if energy futures stay post-merge) | free key | `EIA_API_KEY` | `api.eia.gov/v2/` | shared `tools/eia_data_fetcher.py` |
| FRED | policy-rate / curve for ZN/ZB + FX-carry context | free key | `FRED_API_KEY` | `api.stlouisfed.org/fred/...` | `tools/fred_data_fetcher.py` — supports m6a_carry_sign pilot |

The **Donchian breakout** system needs only OHLCV (yfinance) — no new API; the gap is wiring + regime.

**Prediction markets:** Kalshi Fed-rate markets map to ZN/ZB/ZT; S&P/Nasdaq-range markets map to ES/NQ —
directional gate on index-future + rate-future pilots via `kalshi_signals.py`.

**Copytrader:** CFTC COT/TFF large-trader positioning is the legitimate smart-money proxy for financial
futures. `copy_trader_intel/cta_strategy_replicator.py` + `alpha_engine/cta_bridge.py` are the closest
in-repo CTA-replication hooks. No credible free retail futures copytrade feed.

**Priority — P0**, but the P0 is the plan's **classification merge**, not a data add. First file:
`audit_trail/dashboard_generator.py:~3344` (`_COMMODITY_ROOTS` / `_INDEX_FUTURES_ROOTS`) to unify `=F`
contracts. Data-wise the first add is repointing `cftc_cot_fetcher.py` at the TFF dataset for ES/NQ/ZN.

---

## Priority matrix — first concrete action per class

| Class | Priority | First action (file to edit) |
|---|---|---|
| EQUITY | **P0** | `vix_regime_gate.py` — FRED `VIXCLS` behind `_VIX_CACHE` |
| CRYPTO | **P0** | `asset_class.py` — `is_liquid_crypto()` + CoinGecko ADV gate |
| PENNY_MEME | **P0** | `config.py` — `is_low_quality_or_meme()` hard quarantine gate |
| FUTURES | **P0** | `dashboard_generator.py:~3344` — classification merge |
| ETF | **P1** | `etf_macro_regime.py` sidecar + FRED `T10Y2Y` |
| FOREX | **P1** | `cot_fetcher_socrata.py` — real CFTC FX positioning |
| COMMODITY | **P1** | `cftc_cot_fetcher.py` — extend COT beyond CT=F |
| BOND | **P2** (P1 hygiene) | `bond-agent.yml` — drop `SKIP_FRED=1` |

## Cross-cutting recommendations

1. **Add `FRED_API_KEY` first** — the highest-leverage single env var: it unblocks EQUITY (VIX/curve),
   ETF (macro regime), FOREX (live carry), BOND (yield curve), COMMODITY (PPI). Genuinely free/unlimited.
2. **Wire Kalshi everywhere** — `kalshi_signals.py` exists, the API needs no key; it serves macro/rate/
   weather/index gating for 5 of 8 classes. One integration, broad payoff.
3. **Activate, don't build** — `bond_data_fred.py`, `commodity_carry_momo.json`, `cftc_cot_fetcher.py`,
   `hyperliquid_scraper.py` already exist. Each addition above should ship as an **opt-in sidecar with a
   `## Wiring Plan`** per the repo's Wire-Up Rule.
4. **Copytrader honesty** — real free copytrade feeds: CRYPTO (Hyperliquid) + FOREX (ZuluTrade/MyFXBook)
   only. COMMODITY/BOND/FUTURES → CFTC COT/TFF positioning is the substitute. PENNY_MEME → filter
   copytrader/clone output out, it is net-negative.
5. **Verified free-tier caveats:** Alpha Vantage collapsed to 25 req/day (failover only); StockTwits API
   registrations paused; `exchangerate.host` now key-gated (use Frankfurter); etfdb has no free API;
   CoinGlass institutional L2/L3 books are paid (basic funding/OI/liquidation free).
