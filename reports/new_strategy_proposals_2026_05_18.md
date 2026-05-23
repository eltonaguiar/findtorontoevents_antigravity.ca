# New Strategy Proposals — Genuinely-New, Non-Duplicate — 2026-05-18

**Author:** Claude Opus 4.7 (1M ctx)
**Goal:** Goal #1 — find genuine statistical edge per asset class on `findtorontoevents.ca/audit`.
**Mode:** read-only proposal. No code changed.

---

## 0. Hard constraints this report obeys (verified session findings — do not relitigate)

1. **No proven edge exists on the current ledger.** `tools/edge_stability_harness.py`
   (eff>=0.30, same-sign, >=3of5 windows) is the ONLY admissibility verdict. 8-9
   harness kills to date. The two COT commodity strategies show high WR but only
   2 windows of history — not yet 3-window-stable, so NOT yet "proven" by the harness.
2. **Variant sprawl is value-destructive.** 15x `futures_momentum_v*`, 149x
   `ml_enhanced_*`. Adding another variant of an existing mechanism is rejected
   on sight (M-104/M-105). Every proposal below is a *new mechanism on a new
   input class*, not a re-parameterisation.
3. **The directional-signal space on the price/volume/technical ledger is
   exhausted.** Grok's autopsy: only `method_a_score` (eff 1.21 in-sample,
   UNSTABLE walk-forward) and `risk_reward` (eff 1.076, WEAK) carry any signal,
   and neither is harness-admissible. The forward path is *genuinely-new INPUT
   DATA*, harness-gated.
4. **M-107 BANNED families — NOT proposed here, and any proposal that drifts
   toward one is flagged:** funding-rate directional, yield-curve / 2s10s slope,
   fear&greed / RSI contrarian, COT-derived *directional*, per-symbol curve-fit ML.

The base rate is brutal (8-9 kills). A proposal earns its place only by naming a
**real causal mechanism with a structural reason the edge is not yet arbitraged
away at our latency/size** — not a data-mined pattern.

---

## 1. What mechanisms are already covered (so proposals are non-duplicate)

Surveyed: `alpha_engine/*strategies*.py` (≈80 files), `alpha_engine/crypto_strategies.py`
docstring (strategies 1-130+), `coinglass_strategies/strategies/`, `equity_strategies.py`,
`forex_strategies.py`, `commodities_strategies.py`, `etf_strategies.py`,
`bond_strategies.py`, `event_strategies.py`, `news_sentiment_strategies.py`.

| Class | Covered mechanisms (DO NOT re-propose) |
|---|---|
| **CRYPTO** | momentum (TSMOM, multi-TF EMA), mean-reversion (OU, RSI2, half-life, multi-sigma), breakout (ATR vol, BB-Keltner squeeze), on-chain valuation (MVRV, SOPR, NVT, SSR, hash ribbon, MVRV-Z), funding/OI (carry, OI-funding squeeze, funding-rate arb), liquidations (cascade buy, liquidation imbalance), exchange netflow, seasonality (halving, day-of-week, turn-of-month, weekend drift, Fourier cycle), microstructure (Coinbase premium, OBI, 25-delta skew, cumulative delta), pattern (fractals, H&S, double-top), copy-trade (Hyperliquid/CEX), social (ApeWisdom, Google Trends, CoinGecko trending), max-pain/options-expiry. **SATURATED.** |
| **EQUITY** | 12-month momentum factor, penny volume breakout, meme social velocity, quality/value composite, intermarket risk-on, S/R bounce, Connors RSI2 (long+short), 2-bar RSI reversal, triple-RSI, VIX-spike reversal, turn-of-month, earnings-gap reversal, gap-reversal tech, PEAD earnings drift (factor model). |
| **FOREX** | carry, inverse-carry contrarian, Asian-range breakout, ORB, London-session breakout, Connors RSI2, cross-sectional momentum, COT positioning, 200d mean-reversion, IG retail contrarian. |
| **COMMODITY** | seasonal momentum, gold safe-haven, oil-inventory momentum, metals mean-reversion, agricultural spread, energy breakout, RSI divergence, DXY-inverse, 12m TSMOM, COT/CFTC commercial signal (the 2 high-WR strategies). |
| **ETF** | dual momentum (Antonacci), sector momentum, risk-parity rotation, trend-following, Faber tactical (10-mo SMA), RSI2 pullback. |
| **BOND** | yield momentum, duration rotation, mean-reversion, Connors RSI2, credit-spread mean-reversion, yield-curve slope (banned-adjacent — already in repo). |

**Conclusion of the survey:** every *price/volume/technical* mechanism is taken.
The only non-duplicate territory is **new input data** — physical-world data,
filings data, settlement/plumbing data, and cross-venue structural data that the
ledger has never seen. All proposals below live there.

---

## 2. Proposals — by asset class

Each proposal: a *causal* mechanism, a *free* data source, an economic rationale,
an expected-edge hypothesis, the harness validation path, effort, and risk. The
**pre-registration test statistic** is the one-line claim that must be filed in
`reports/hypothesis_registry.json` BEFORE any data is touched (M-107).

> Validation protocol for ALL proposals: build an opt-in research sidecar (no
> production caller), backfill a `closed_picks`-shaped ledger of resolved
> hypothetical picks tagged with the new signal, run `edge_stability_harness.py
> --field <signal>`. Admissible only if eff>=0.30 same-sign in >=3 of 5
> 14-day windows. If not admissible: archive the config, never re-test on the
> same sample. The signal is wired into `passes_active_gate` ONLY after the
> harness passes.

---

### CRYPTO

CRYPTO's price/volume/on-chain-valuation/funding space is the most saturated in
the system. New input must be *settlement-layer* or *cross-protocol structural*
data the ledger has never carried.

#### C-1. Stablecoin mint/burn authorization flow (primary-market supply)
- **Mechanism:** Tether and Circle publish on-chain `mint`/`burn` events for USDT
  and USDC at the *treasury* level. A mint authorization is dry powder entering
  the system *before* it reaches an exchange order book; a burn is capital
  leaving. This is **primary-market** supply creation — distinct from the
  *secondary-market* "stablecoin dry powder / SSR" strategies already in the
  ledger (those read aggregate circulating supply, a lagging snapshot). The
  signal is the *first derivative at the issuer*, leading the exchange-balance
  metrics by 12-48h.
- **Data source (free):** Tether/Circle treasury contract event logs via a free
  Ethereum/Tron RPC (Ankr, PublicNode, or `blockchair.com` free tier);
  `defillama.com/stablecoins` API (free, no key) for cross-chain aggregate.
- **Economic rationale:** New stablecoin supply is created on demand from
  authorized participants who are about to deploy it. There is a structural lead
  because issuance → exchange deposit → order placement is a multi-hop pipeline.
  The edge survives because the data is *machine-unfriendly* (event-log parsing
  across 3+ chains) — not because nobody knows it matters.
- **Expected-edge hypothesis:** In a 48h window after a net-mint day >$200M,
  BTC/ETH forward 3d return is positive at a higher rate than baseline.
- **Harness test statistic (pre-register):** "Picks tagged `net_mint_48h=True`
  have `signal_score = net_mint_usd_zscore`; eff(WON vs LOST) >= 0.30 same-sign
  in >=3 of 5 windows."
- **Effort:** ~3-4 days (multi-chain event-log parser is the cost).
- **Risk:** MEDIUM. Issuance is partly *reactive* to demand already expressed in
  price — reverse-causality could null the lead. Mitigate by lagging the signal
  strictly behind the mint timestamp.
- **Flag:** clean. Not a banned family; not a duplicate (secondary-supply SSR is
  different data).

#### C-2. Bitcoin miner cost-of-production stress (hashprice vs. realized price)
- **Mechanism:** When *hashprice* (USD revenue per terahash) falls below the
  marginal electricity cost of the median miner, miners are forced sellers to
  meet fiat obligations. This is **physical industry-economics** data — distinct
  from the `hash_ribbon` strategy in the ledger, which is a *moving-average
  crossover of hashrate itself* (a technical overlay). C-2 uses the
  *economic spread* between miner revenue and miner cost, not a hashrate MA.
- **Data source (free):** `mempool.space` API (free, no key) for hashrate +
  difficulty; Hashrate Index / Luxor publish a free hashprice index; Cambridge
  CBECI for energy-cost estimates. Difficulty epoch boundaries are deterministic.
- **Economic rationale:** Miners are the only *structurally inelastic* sellers in
  crypto — they must sell to pay power bills regardless of price view. When the
  cost-of-production spread goes negative, capitulation selling is mechanical and
  predictable; when it widens positive, miner-held supply is withheld. This is a
  genuine supply-side mechanism with no behavioural-finance hand-waving.
- **Expected-edge hypothesis:** When hashprice/elec-cost ratio < 1.0 for >5 days,
  BTC realises a local bottom within 21 days at above-baseline rate (capitulation
  exhaustion); when ratio > 1.5, forward 30d drift is positive.
- **Harness test statistic:** "Picks tagged with `miner_stress_ratio` quintile;
  eff(WON vs LOST) on the bottom/top quintile cohort >= 0.30 same-sign 3/5 windows."
- **Effort:** ~2-3 days.
- **Risk:** MEDIUM-LOW. Slow-moving signal (difficulty epochs ≈ 2 weeks) so it
  generates few picks — n may not reach 80/window for the harness. Mitigate by
  applying it to ALL crypto symbols on each epoch boundary.
- **Flag:** clean. Borderline-adjacent to "hash ribbon" but the *input* (economic
  spread, not hashrate MA) and the *mechanism* (forced-seller economics) are
  genuinely distinct. Verify non-duplication by confirming hash-ribbon uses
  `hashrate.rolling().mean()` only.

#### C-3. Layer-2 / bridge net-deposit flow (capital rotation into an ecosystem)
- **Mechanism:** Capital bridged *into* an L2 (Arbitrum, Base, Optimism) or a
  chain ecosystem is committed risk capital that will be deployed on that chain's
  assets within days. Net bridge inflow leads ecosystem-token outperformance.
  No existing strategy reads bridge TVL flow — `narrative_rotation` reads
  *CoinGecko category price momentum* (a lagging price aggregate), not the
  capital-movement input.
- **Data source (free):** `defillama.com/bridges` API (free, no key) — per-chain
  net bridge flow; L2Beat API (free) for L2 TVL.
- **Economic rationale:** Bridging has a real friction cost and a 7-day
  challenge-period lock on optimistic rollups — nobody bridges capital they don't
  intend to deploy. Net inflow is therefore a high-conviction commitment signal
  that leads on-chain asset demand.
- **Expected-edge hypothesis:** Ecosystem tokens of a chain with top-quintile 7d
  net bridge inflow outperform bottom-quintile over the next 7d.
- **Harness test statistic:** "`bridge_inflow_7d_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows on ecosystem-token picks."
- **Effort:** ~2 days.
- **Risk:** MEDIUM. Bridge flow can be airdrop-farming noise (mercenary capital
  that leaves immediately). Mitigate by requiring inflow to *persist* >3 days.
- **Flag:** clean, non-duplicate.

---

### EQUITY

EQUITY's technical + factor space is covered (momentum, value, quality, PEAD).
New input = *real-world activity data* and *filings-text* data not in the ledger.

#### E-1. Insider open-market cluster buys (Form 4, transaction code P)
- **Mechanism:** SEC Form 4 filings flag *open-market purchases* (code "P") by
  officers/directors. A *cluster* — 3+ distinct insiders buying the same stock
  within a short window — is a documented, academically-replicated alpha source
  (Cohen, Malloy & Pomorski 2012; Jeng et al.). No existing equity strategy uses
  insider data; the closest is `quality_value_composite` (fundamentals only).
- **Data source (free):** SEC EDGAR full-text + Form 4 XML feed (free, no key);
  `data.sec.gov` submissions API. `openinsider.com` aggregates it (scrapeable).
- **Economic rationale:** Insiders have a legal information advantage and a
  *revealed-preference* signal — open-market buys with personal capital, when
  clustered, are the strongest legal information event available. The edge
  persists because the filings are noisy (most insider activity is options
  exercise / 10b5-1 plans, NOT code P) and require careful filtering.
- **Expected-edge hypothesis:** Stocks with a 3+ insider code-P cluster in a
  10-day window outperform sector over the following 20 trading days.
- **Harness test statistic:** "`insider_cluster_buy=True` picks scored by
  `total_insider_buy_usd`; eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~3 days (EDGAR XML parsing + code-P filtering).
- **Risk:** LOW-MEDIUM. Well-known signal — possible it is partially arbitraged
  at the *liquid large-cap* end. Mitigate by restricting to mid/small-cap where
  insider information asymmetry is largest and institutional arb is thinner.
- **Flag:** clean. Likely *partially* arbitraged in mega-caps — flagged. Edge
  should concentrate in the small-cap cohort; pre-register stratified.

#### E-2. SEC 8-K material-event filing-text classification
- **Mechanism:** An 8-K is filed for material corporate events (item 1.01
  material agreements, 2.02 results, 5.02 officer departures, 8.01 other). The
  *type* and *text sentiment* of an unscheduled 8-K is a discrete information
  event. The ledger's `news_sentiment` strategies read *news-aggregator* text
  (lagging, noisy, secondary); 8-K is the *primary-source* filing at the moment
  of legal disclosure.
- **Data source (free):** SEC EDGAR 8-K feed (free, real-time RSS). FinBERT
  (open weights, free) for sentiment on the filing text.
- **Economic rationale:** The primary filing precedes most news-wire coverage by
  minutes-to-hours; for small-caps with thin analyst coverage the price has not
  yet adjusted. Item-code classification is a clean categorical input — e.g.
  item 5.02 CEO departure has a known directional prior.
- **Expected-edge hypothesis:** Small-cap stocks with an 8-K item 1.01/8.01
  classified positive by FinBERT drift positive over the next 5 trading days.
- **Harness test statistic:** "`filing_sentiment_score` (FinBERT logit on 8-K
  text); eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~4 days (EDGAR ingest + FinBERT inference pipeline).
- **Risk:** MEDIUM. NLP sentiment is noisy; 8-K text is boilerplate-heavy.
  Mitigate by using *item-code* as the primary signal and sentiment as a filter.
- **Flag:** clean. NOT the banned "fear&greed/RSI contrarian" family — this is
  primary-filing event classification, not a market-sentiment index.

#### E-3. Government contract awards (USAspending.gov)
- **Mechanism:** Federal contract awards are published on `USAspending.gov` with
  the awardee's name and dollar amount. A material new contract is a revenue
  event that, for small/mid-cap defence/IT/healthcare names, is *not yet in
  consensus estimates*. No existing strategy uses procurement data.
- **Data source (free):** `api.usaspending.gov` (free, fully open, no key).
- **Economic rationale:** A $50M contract for a $500M-market-cap company is a
  10% revenue event. The data is public but in a government database analysts do
  not systematically monitor — a genuine processing-cost moat.
- **Expected-edge hypothesis:** Stocks receiving a contract award >5% of TTM
  revenue drift positive over 20 trading days post-award-publication.
- **Harness test statistic:** "`contract_award_pct_revenue` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~2-3 days (awardee→ticker name-matching is the hard part).
- **Risk:** MEDIUM. Name-matching contractor legal names to tickers is error-
  prone; award publication often lags the press release. Mitigate with a
  curated name-map for the covered universe.
- **Flag:** clean, non-duplicate. Possible lag-to-press-release issue — flagged.

---

### FOREX

FOREX is the worst class (sub-floor). Its carry/momentum/COT/contrarian space is
fully covered and *failing*. New input = *central-bank communication* and
*real-economy nowcast* data — not another price overlay.

#### F-1. Central-bank communication tone (rate-decision statement diff)
- **Mechanism:** Each central bank (Fed, ECB, BoE, BoJ, RBA) publishes a policy
  *statement* at each meeting. The *textual diff* between consecutive statements
  — words added/removed around inflation, growth, and forward guidance — is a
  documented driver of FX (the "hawkish/dovish surprise"). No existing forex
  strategy reads CB text; carry/COT/contrarian are all positioning/price based.
- **Data source (free):** Fed/ECB/BoE/BoJ websites publish statements as plain
  HTML (free). FinBERT or a hawk-dove lexicon for tone scoring.
- **Economic rationale:** FX is a *relative* rates game. The market prices the
  *decision* instantly but mis-prices the *guidance tone* because the latter
  requires reading the statement diff carefully. The edge is the gap between the
  headline rate move and the guidance change — a classic information-processing
  moat that survives because it is event-driven (8 meetings/year per bank, not
  continuous).
- **Expected-edge hypothesis:** A currency whose CB statement turns hawkish-diff
  while the counterpart's stays neutral appreciates over the following 3-5 days.
- **Harness test statistic:** "`cb_tone_diff_score` (hawk-dove delta vs prior
  statement); eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~4 days (statement scraper per bank + diff-tone scorer).
- **Risk:** MEDIUM-HIGH. Sparse — ≈40 meetings/year total across G5 → n per
  14-day window will be tiny; the harness MIN_WINDOW_N=80 may never be reached.
  Mitigate by trading ALL crosses involving the bank's currency per event
  (one decision → ~6-8 picks).
- **Flag:** clean. NOT yield-curve (banned) — this is communication-text, not the
  2s10s slope. Sample-size risk is the real concern; flagged.

#### F-2. Economic-surprise nowcast (data vs consensus, real-time)
- **Mechanism:** A currency strengthens when its economy's incoming data *beats
  consensus* (the Citi Economic Surprise Index logic). The signal is the running
  sum of (actual − consensus) z-scores across that country's releases. No
  existing forex strategy uses surprise data — carry/momentum/contrarian are all
  price/positioning.
- **Data source (free):** `tradingeconomics.com` calendar (free tier, actual +
  forecast); FRED for the US series; the `econdb` free API. Forecast = consensus.
- **Economic rationale:** Relative growth surprise drives capital flows and rate
  expectations. Building a *clean surprise index* from scattered releases is a
  data-assembly cost most retail and even many funds do not pay — that assembly
  cost is the moat, not secret information.
- **Expected-edge hypothesis:** A currency with a top-quintile 30-day economic-
  surprise index outperforms a bottom-quintile currency over the next 10 days.
- **Harness test statistic:** "`econ_surprise_index_30d` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~3-4 days (calendar ingest + per-country aggregation).
- **Risk:** MEDIUM. Citi's ESI is itself a known product — the *aggregate* may be
  partly arbitraged by macro funds. The edge, if any, is in the *short-horizon
  freshness* (we update per-release vs monthly index rebuilds).
- **Flag:** **borderline-arbitraged** — the surprise-index concept is mainstream.
  Flagged. Pre-register with low prior; kill fast if window-1 eff is weak.

---

### COMMODITY

COMMODITY is the system's best class, and the two COT strategies are high-WR but
COT-directional adjacent (M-107 watch — they exist already; do not extend them).
New input = *physical-inventory and physical-shipping* data.

#### CO-1. Physical inventory / storage reports (EIA + USDA + LME/COMEX warehouse)
- **Mechanism:** Physical commodity prices are anchored to *inventory levels*.
  EIA weekly petroleum/natgas stocks, USDA WASDE crop stocks, and LME/COMEX
  warehouse stocks are scheduled reports whose *surprise vs expectation* moves
  the curve. The ledger's `oil_inventory_momentum` uses a *price-momentum proxy*
  for inventory — CO-1 uses the **actual published inventory number** and its
  surprise vs the API/Reuters consensus.
- **Data source (free):** EIA open API (free key, instant); USDA NASS / WASDE
  (free, no key); LME publishes daily warehouse stocks (free). COMEX warehouse
  stocks via CME free data.
- **Economic rationale:** Inventory is the single most direct supply/demand
  balance indicator for a physical commodity. A draw vs an expected build is a
  genuine fundamental surprise. The edge survives because the consensus is
  fragmented and the report timing is exploitable for short-horizon picks.
- **Expected-edge hypothesis:** A commodity with a top-decile inventory-surprise
  (draw vs expected) drifts positive over the following 5 trading days.
- **Harness test statistic:** "`inventory_surprise_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows on CL/NG/ZW/ZC/ZS picks."
- **Effort:** ~3 days (EIA + USDA ingest; consensus from prior-week + seasonal).
- **Risk:** MEDIUM. The headline inventory move is fast — by the time we read the
  report the front-month has moved. Mitigate by trading the *deferred* contract
  / the ETF (USO/UNG) where adjustment is slower, and by using the *5-day drift*
  not the report-day spike.
- **Flag:** clean, genuinely-new input. Strong causal mechanism.

#### CO-2. Maritime freight / shipping congestion (dry-bulk and tanker rates)
- **Mechanism:** The Baltic Dry Index and tanker rates are *real-time demand
  signals* for bulk commodities (iron ore, coal, grain) and crude. Rising
  freight = rising physical-cargo demand = forward commodity-price pressure.
  Port-congestion counts (AIS vessel data) are a leading inventory-pipeline
  signal. No existing commodity strategy uses shipping data.
- **Data source (free):** Baltic Exchange publishes the BDI daily summary (free
  via news feeds / `tradingeconomics.com`); free AIS aggregators publish port
  congestion counts; `vesselfinder.com`/`marinetraffic.com` have free tiers.
- **Economic rationale:** Freight is a *derived demand* for the underlying
  commodity and clears in a near-spot market — it reveals physical demand before
  it shows up in inventory reports. The data lives in a maritime-logistics
  silo most commodity-price models never touch: a genuine cross-domain moat.
- **Expected-edge hypothesis:** A 4-week rising BDI trend leads positive forward
  20d returns in dry-bulk commodities (iron ore, coal proxies, grains).
- **Harness test statistic:** "`bdi_trend_4w_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~3 days (BDI series is easy; AIS congestion is the harder add).
- **Risk:** MEDIUM. BDI also reflects ship-supply (newbuild deliveries) not just
  cargo demand — confounded. Mitigate by differencing against the global vessel
  orderbook, or accept it as a noisy first version and let the harness rule.
- **Flag:** clean, non-duplicate. Confounding by ship-supply — flagged.

---

### ETF

ETF mechanisms (dual momentum, sector/risk-parity rotation, Faber, RSI2) are all
*price-overlay* strategies. New input = the *primitive* that makes an ETF an ETF:
creation/redemption flow and NAV-arbitrage state.

#### ET-1. ETF creation/redemption share-count flow
- **Mechanism:** When an ETF's *shares outstanding* rises, an Authorized
  Participant created new units — committed capital flowing into the basket.
  Falling share count = redemption = outflow. Shares-outstanding flow is a
  *primary-market* fund-flow signal, distinct from every price-based rotation
  strategy in the ledger. It is the cleanest "smart-money allocation" tape ETFs
  produce.
- **Data source (free):** Issuers (SPDR, iShares, Vanguard, Invesco) publish
  daily shares-outstanding on their fund pages (free); `stockanalysis.com` and
  the SEC N-PORT filings carry it. yfinance exposes `sharesOutstanding` for many
  ETFs.
- **Economic rationale:** Creation/redemption is done by APs and large allocators
  — it is a revealed institutional-flow signal with no behavioural noise. Strong
  persistent inflow into a sector ETF is a momentum-of-capital signal that leads
  the basket. The data is free but *scattered across issuer sites* — assembly
  cost is the moat.
- **Expected-edge hypothesis:** Sector ETFs with top-quintile 10-day net-creation
  flow outperform bottom-quintile over the next 10 trading days.
- **Harness test statistic:** "`etf_creation_flow_10d_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~2-3 days (per-issuer shares-outstanding scraper).
- **Risk:** MEDIUM. Creation flow can be *index-driven mechanical rebalancing*,
  not a view. Mitigate by focusing on thematic/sector ETFs where flow is
  discretionary, excluding the mega broad-market funds.
- **Flag:** clean, genuinely-new input, strong mechanism. **Top candidate.**

#### ET-2. ETF premium/discount to iNAV (closed-end-style dislocation)
- **Mechanism:** An ETF can trade at a premium or discount to its intraday NAV
  when AP arbitrage is impaired (illiquid underlying, foreign-market closure,
  stress). A persistent discount in a liquid ETF is a mean-reversion signal;
  a persistent discount in a *bond/EM* ETF is an early stress signal. No
  existing ETF strategy reads the premium/discount state.
- **Data source (free):** Issuers publish end-of-day premium/discount (free,
  required by SEC). yfinance gives close vs `navPrice` for many funds.
- **Economic rationale:** The premium/discount is a direct read on AP-arbitrage
  health. When it dislocates, either (a) it mean-reverts as APs step in, or (b)
  it is a leading indicator of underlying stress the close price has not caught.
  Both are tradable; the harness will tell which dominates.
- **Expected-edge hypothesis:** ETFs trading >1 sigma discount to iNAV revert
  toward NAV over the next 3-5 trading days.
- **Harness test statistic:** "`etf_premium_discount_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~2 days.
- **Risk:** MEDIUM-HIGH. For the most liquid ETFs the dislocation is tiny and
  costs eat it; the signal only has size in less-liquid funds where slippage is
  also worst. Mitigate by restricting to mid-liquidity ETFs and modelling cost.
- **Flag:** clean, non-duplicate. Cost-vs-edge tension — flagged.

---

### BOND

BOND has n=18 (sub-floor sample). Its existing strategies (yield momentum,
duration, mean-reversion, RSI2, credit-spread, yield-curve slope) are *price/
yield overlays* — and yield-curve-slope is M-107-banned-adjacent. New input =
*primary-market issuance* and *flow* data.

#### B-1. Treasury auction demand (bid-to-cover + indirect-bidder share)
- **Mechanism:** Every Treasury auction publishes a *bid-to-cover ratio* and the
  *indirect-bidder* (foreign central bank) share. A weak auction (low cover,
  low indirect) signals deteriorating demand for duration → yields up / bond
  prices down. A strong auction signals the opposite. This is *primary-market
  issuance demand* — a discrete, scheduled, causal event with no existing
  strategy reading it (yield-momentum reads secondary prices only).
- **Data source (free):** US Treasury publishes every auction result at
  `treasurydirect.gov` with a free API (auction results endpoint, no key).
- **Economic rationale:** The auction is the moment supply meets demand for
  Treasury duration. A cover-ratio surprise vs the trailing average is a clean
  fundamental supply/demand read that leads the secondary curve by 1-3 days.
  Critically — this is **NOT the 2s10s slope** (banned): it is the *demand
  metric at a single tenor's auction*, a different input entirely.
- **Expected-edge hypothesis:** After a 10y/30y auction with bid-to-cover >0.5
  sigma below trailing average, TLT/EDV drift negative over 3-5 trading days.
- **Harness test statistic:** "`auction_cover_surprise_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows on TLT/IEF/EDV picks."
- **Effort:** ~2 days (TreasuryDirect API is clean and well-documented).
- **Risk:** MEDIUM. Sparse — ≈2-3 long-end auctions/month → n per window may not
  reach the harness MIN_WINDOW_N=80. Mitigate by including all tenors and
  trading multiple bond ETFs per auction. If n is structurally too low, the
  harness honestly cannot verdict it — accept that and report DATA_GAP.
- **Flag:** clean. **Explicitly NOT yield-curve slope** — auction-demand is a
  distinct primary-market input. Sample-size risk is the real concern; flagged.

#### B-2. TIPS-implied breakeven inflation *surprise* vs CPI nowcast
- **Mechanism:** The breakeven inflation rate (nominal yield − TIPS yield) is the
  market's inflation forecast. When the *realized* CPI nowcast diverges from the
  market breakeven, the bond market is mispricing inflation and will re-rate.
  The ledger has no inflation-expectation strategy. NOTE: this uses breakevens
  as a *level vs nowcast* comparison — NOT the yield-curve slope.
- **Data source (free):** FRED series `T10YIE` (10y breakeven), `DFII10` (TIPS
  yield) — free, no key; Cleveland Fed publishes a free CPI nowcast.
- **Economic rationale:** Bonds are an inflation bet. When the breakeven and the
  best available CPI nowcast disagree, one of them is wrong and the bond price
  must move. The edge is in *assembling the nowcast* (Cleveland Fed model)
  faster than the consensus re-rates the breakeven.
- **Expected-edge hypothesis:** When CPI-nowcast > 10y breakeven by >0.3 sigma,
  TLT drifts negative over the next 10 trading days (inflation re-rate higher).
- **Harness test statistic:** "`breakeven_nowcast_gap_zscore` as signal_score;
  eff(WON vs LOST) >= 0.30 same-sign 3/5 windows."
- **Effort:** ~2-3 days.
- **Risk:** MEDIUM-HIGH. **Borderline-arbitraged** — breakeven-vs-nowcast is a
  well-known macro trade; large funds run it. Also borderline-adjacent to the
  banned yield-curve family in *spirit* (it is a rates-derived macro signal),
  though it is technically a different input. Flagged on BOTH counts.
- **Flag:** **borderline-banned-adjacent AND borderline-arbitraged.** Requires
  operator sign-off before pre-registration. Lowest-priority BOND proposal.

---

## 3. Ranking — expected edge-per-effort

Scoring: *expected edge* (probability the mechanism is real AND not arbitraged AND
clears the harness, on a 1-5 scale given the 8-9-kill base rate) ÷ *effort* (days),
with banned/arbitrage flags as hard penalties.

| Rank | Proposal | Class | Edge prior | Effort | Edge/effort | Flag |
|---|---|---|---|---|---|---|
| **1** | **ET-1 ETF creation/redemption flow** | ETF | 4/5 | 2-3d | **HIGH** | clean |
| **2** | **CO-1 Physical inventory surprise** | COMMODITY | 4/5 | 3d | **HIGH** | clean |
| **3** | **E-1 Insider cluster buys (Form 4 code P)** | EQUITY | 4/5 | 3d | **HIGH** | partial-arb (large-cap) |
| 4 | C-2 Miner cost-of-production stress | CRYPTO | 3/5 | 2-3d | MED-HIGH | clean; low pick volume |
| 5 | B-1 Treasury auction demand | BOND | 3/5 | 2d | MED-HIGH | clean; sparse-sample |
| 6 | C-1 Stablecoin mint/burn flow | CRYPTO | 3/5 | 3-4d | MEDIUM | clean; reverse-causality |
| 7 | E-3 Government contract awards | EQUITY | 3/5 | 2-3d | MEDIUM | clean; name-match risk |
| 8 | C-3 L2/bridge net-deposit flow | CRYPTO | 3/5 | 2d | MEDIUM | clean; mercenary-capital |
| 9 | CO-2 Maritime freight congestion | COMMODITY | 3/5 | 3d | MEDIUM | clean; ship-supply confound |
| 10 | E-2 SEC 8-K filing-text classification | EQUITY | 2/5 | 4d | MEDIUM | clean; NLP noise |
| 11 | F-1 Central-bank communication tone | FOREX | 2/5 | 4d | LOW-MED | clean; sparse-sample |
| 12 | ET-2 ETF premium/discount to iNAV | ETF | 2/5 | 2d | LOW-MED | clean; cost-vs-edge |
| 13 | F-2 Economic-surprise nowcast | FOREX | 2/5 | 3-4d | LOW | **borderline-arbitraged** |
| 14 | B-2 TIPS breakeven vs CPI-nowcast | BOND | 1/5 | 2-3d | LOW | **banned-adjacent + arb** |

### Flagged proposals (read before pre-registering)
- **B-2 (TIPS breakeven)** — banned-adjacent (rates-derived macro) AND
  arbitraged. **Do NOT pre-register without explicit operator sign-off.**
- **F-2 (economic-surprise index)** — the Citi-ESI concept is mainstream;
  treat as a low-prior probe, kill fast if window-1 eff is weak.
- **E-1 (insider buys)** — likely arbitraged in mega-caps; pre-register the
  *small-cap-stratified* version only, not the full universe.
- **C-2 / B-1 / F-1** — not arbitraged and clean mechanisms, but the input is
  *sparse* (epoch / auction / meeting cadence). The harness needs n>=80 per
  14-day window; if the sparse cohort cannot reach it, the honest verdict is
  DATA_GAP, not a kill. Plan to fan each event across all symbols to lift n.

---

## 4. Honest caveats

1. **The base rate says most of these will be killed.** 8-9 prior kills. A 4/5
   "edge prior" still means a real chance of harness rejection. That is the
   point of the harness — propose, gate, archive.
2. **Sparse-input proposals (CB tone, auctions, miner epochs) may be
   un-verdictable** because the harness requires n>=80 per window. They are
   still worth building because fanning one event across many symbols can lift
   n — but if it cannot, report DATA_GAP and do not claim a kill or a win.
3. **None of these may touch a production pick path until the harness passes.**
   Each is an opt-in research sidecar with a pre-registered hypothesis filed in
   `reports/hypothesis_registry.json` BEFORE any data is pulled (M-107). The
   vetting report `reports/kilo_fork2_vetting_2026_05_18.md` shows exactly how
   the last new-signal effort failed this discipline — do not repeat it.
4. **Recommended first build:** ET-1 (ETF creation/redemption flow). Cleanest
   mechanism, genuinely-new primary-market input, lowest effort, no
   banned/arbitrage flag, and ETF is a class where lifting n also helps Goal #1
   independent of the edge verdict.

---

*Generated 2026-05-18. Read-only proposal — no code modified. Sources surveyed:
`alpha_engine/*strategies*.py`, `alpha_engine/crypto_strategies.py` docstring
(strategies 1-130+), `coinglass_strategies/strategies/`, `tools/edge_stability_harness.py`,
`reports/edge_analysis_by_strategy_2026-05-17.md`, `reports/kilo_fork2_vetting_2026_05_18.md`,
`reports/hypothesis_registry.json` (M-107 ban registry).*
