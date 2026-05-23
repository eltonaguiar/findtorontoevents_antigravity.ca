# Researcher Profile: Dr. Yuki Tanaka

## Persona
- **Title:** On-Chain Data Scientist
- **Expertise:** Blockchain analytics, network metrics, exchange flows, whale tracking
- **Years Experience:** 8
- **Background:** PhD ETH Zurich, former data scientist at Glassnode, now builds on-chain models for a crypto fund.

## Research Scope
**Primary Question:** Which on-chain metrics are most predictive of crypto price movements and how to integrate them into ML models?

**Target Systems/Areas:**
- Glassnode's institutional-grade metrics (NUPL, MVRV, SOPR, NVT)
- CryptoQuant exchange flow metrics
- Santiment social + on-chain hybrid
- Whale wallet tracking (accumulation/distribution)
- Miner flows and hash rate derivatives
- Stablecoin supply dynamics

## Methodology
1. **Sources:** Glassnode API docs, CryptoQuant research, Santiment whitepapers, academic papers on blockchain analytics, blockchain.info Charts API, CoinGecko API.
2. **Extraction:** Metric definitions, calculation formulas, lookback periods, historical availability, predictive power (correlation with returns).
3. **Analysis:** Combine on-chain with technical indicators; test for leading vs lagging characteristics.
4. **Validation:** Granger causality tests; feature importance in ML models; backtest profitability.

---

## COMPLETE FINDINGS (Feb 2026)

### Executive Summary: On-Chain Metrics -- Signal vs. Hype

**Verdict:** On-chain metrics have genuine predictive power for **medium-term** (1-8 week) regime detection and cycle positioning. They are **not useful for intraday trading** due to data lag (daily resolution on free tiers, 10-min minimum on expensive paid tiers). The biggest risk is that our current `onchain_strategies.py` uses OHLCV proxies that approximate but do not replicate the real on-chain signals. Some proxies are reasonable (MVRV via 200d SMA), others are fundamentally broken (SOPR without UTXO data). Below is an honest metric-by-metric assessment.

**Academic validation:** A 2024 study (ScienceDirect) combining on-chain features with CNN-LSTM achieved 82.44% accuracy on 7-day BTC direction prediction. Boruta-SVM using 92 on-chain metrics + 138 technical indicators was the most profitable model in backtesting. On-chain features consistently rank in the top feature importance when included in ML models.

---

## Metric-by-Metric Analysis

### 1. MVRV Ratio (Market Value to Realized Value)
- **Origin:** Murad Mahmudov & David Puell (2018), refined by @aweandwonder
- **Definition:** Market Cap / Realized Cap. Realized Cap = sum of each UTXO valued at the price when it last moved.
- **Signal:** MVRV Z-Score > 7 = cycle top (within 2 weeks historically); Z-Score < 0 = accumulation zone.
- **Historical accuracy:** Picked the market high of 2017 and 2021 cycles within two weeks. In 2018 and 2022, Z-Score below 0 flagged bottoms accurately.
- **Current state (Feb 2026):** Readings closer to buy zone than sell zone per Bitcoin Magazine Pro, with STH Realized Price supporting BTC at ~$113K, projecting MVRV-driven surges to $160K-$200K.
- **Predictive horizon:** 1-4 weeks for actionable signals; multi-month for cycle positioning.
- **Honest assessment:** STRONG for cycle-level calls. Weak for short-term trading. The metric has 4-5 genuine signals per multi-year cycle -- it is a regime detector, not a trade signal generator.
- **Our proxy quality:** Using 200d SMA as realized price proxy is a **reasonable approximation** for BTC. The 200d SMA tracks roughly where most holders bought. Correlation with true MVRV is moderate (~0.7). The proxy breaks down for altcoins where holder behavior differs significantly.
- **Free data sources:**
  - CoinGlass: https://www.coinglass.com/pro/i/mvrv-ratio (chart only, no API)
  - CryptoQuant: https://cryptoquant.com/asset/btc/chart/market-indicator/mvrv-ratio (paid API, $99/mo)
  - Glassnode free tier: Daily MVRV available via `GET /v1/metrics/market/mvrv` (24h resolution, delayed)

**RATING: 8/10 predictive power (cycle level) | 3/10 (intraday) | Proxy quality: 6/10**

---

### 2. NVT Ratio (Network Value to Transactions)
- **Origin:** Willy Woo (2017)
- **Definition:** Market Cap / Daily Transaction Volume (USD). Bitcoin's "P/E ratio."
- **Signal:** High NVT = network overvalued relative to usage; Low NVT = undervalued.
- **Current state:** In early 2025, CryptoQuant showed NVT ~35 with BTC at ~$82K, indicating "fair value" at that level. NVT spikes align well with cycle peaks and troughs historically.
- **Does it still work?** Partially. The metric is degraded by:
  1. Layer-2 activity (Lightning Network transactions not captured)
  2. ETF/institutional flows via OTC desks bypass on-chain visibility entirely
  3. Willy Woo himself has acknowledged macro disruptions impact the model (2022 calls were poorly timed)
- **Predictive horizon:** Multi-week. NVT is slow-moving and noisy day-to-day.
- **Our proxy quality:** Using blockchain.info TX volume is **one of our better proxies** since it uses the actual data source. However, the API endpoint (`https://blockchain.info/charts/estimated-transaction-volume-usd?format=json`) returns daily aggregates only.
- **Free data sources:**
  - blockchain.info Charts API: `https://blockchain.info/charts/estimated-transaction-volume-usd?timespan=1year&format=json` (free, no key, rate limit: 1 request per 10 seconds)
  - Woobull Charts: http://charts.woobull.com/bitcoin-nvt-ratio/ (visual only)

**RATING: 5/10 predictive power (degraded by L2/ETFs) | Proxy quality: 7/10 (uses real data)**

---

### 3. Exchange Netflow (Inflow/Outflow)
- **Definition:** Net BTC/crypto moving into minus out of exchange wallets.
- **Signal:** Large outflows = accumulation (bullish, coins moving to cold storage); Large inflows = distribution (bearish, coins moving to exchanges to sell).
- **Source:** CryptoQuant is the gold standard; CoinGlass also tracks spot flows.
- **Predictive horizon:** 1-7 days for significant flow events.
- **Honest assessment:** One of the MORE actionable on-chain metrics because it measures actual behavioral intent (moving to exchange = intent to sell). However:
  1. OTC trades are NOT captured (institutional desks handle billions off-chain)
  2. Exchange internal wallet shuffles create false signals
  3. Post-ETF era: Much BTC buying/selling happens via ETF shares, never touching blockchain
  4. Best used as a filter (only trade when netflow confirms direction) rather than standalone signal
- **Our proxy quality:** We do NOT have a real exchange netflow proxy in `onchain_strategies.py`. This is a gap. The closest we could get for free is monitoring large Binance wallet addresses via blockchain explorers, but this is fragile.
- **Free data sources:**
  - CoinGlass: https://www.coinglass.com/spot-inflow-outflow (visual, limited API)
  - CryptoQuant: https://cryptoquant.com/asset/btc/chart/exchange-flows/exchange-netflow-total (paid API, $99/mo minimum)
  - No reliable free API for this metric.

**RATING: 7/10 predictive power (with caveats) | Proxy quality: 0/10 (we have no proxy)**

---

### 4. Whale Wallet Tracking
- **Definition:** Monitoring wallets holding >1000 BTC for accumulation/distribution patterns.
- **Signal:** Whale accumulation in downtrends = bullish; whale distribution at highs = bearish.
- **Tools:** Whale Alert (real-time transaction alerts), Whalemap (cost-basis clusters), Nansen (entity labeling).
- **Honest assessment:** OVERHYPED for ML integration. Reasons:
  1. Not all large transactions are meaningful (exchange-to-exchange transfers, cold storage reshuffling)
  2. Modern whale tracking requires entity deanonymization and AI-driven wallet clustering -- raw address monitoring produces too many false positives
  3. Whales are not always good traders. Following whale wallets blindly has been shown to underperform
  4. Some whale movements are deliberate traps (spoofing large transfers to trigger retail)
  5. Best used qualitatively, not as a quantitative ML feature
- **Our proxy quality:** Our `whale_accumulation_detector` in crypto_strategies.py uses 5x volume spikes + bullish price action in downtrends. This is a **price/volume proxy**, not actual whale tracking. It captures some of the same dynamics but with much higher false positive rate.
- **Free data sources:**
  - Whale Alert: https://whale-alert.io/ (free tier: limited alerts, API from $15/mo)
  - blockchain.info: Can query individual addresses for free, but no aggregated whale metrics

**RATING: 4/10 predictive power for ML (too noisy) | 6/10 for discretionary trading | Proxy quality: 3/10**

---

### 5. Hash Ribbon Buy Signal
- **Origin:** Charles Edwards, Capriole Investments (2019)
- **Definition:** 30-day MA of hash rate crosses above 60-day MA after miner capitulation period.
- **Reported accuracy:** "78% win rate" is commonly cited. Actual data: 14 buy signals since 2013, approximately 64% turned profitable (assuming exit on first miner capitulation signal after entry). Charles Edwards claims 7 out of 7 recent signals preceded significant gains, including 500% gain within a year after April 2020 signal.
- **2024-2025 signals:** The indicator flashed multiple times in 2025 (at least 3 by mid-2025, 5 total by November 2025). The November 2025 signal at ~$81K preceded further upside. Post-2024-halving, miner capitulation was structural due to compressed revenues (hashprice at $42-43/PH/s/day vs all-in cost of $44).
- **Honest assessment:** GENUINE predictive power but very infrequent. This is a high-conviction, low-frequency signal. The mechanism is sound: miners selling at capitulation = forced selling pressure exhausted = bottom. However:
  1. Only 1-3 signals per year
  2. Not useful for active trading, only for position sizing / DCA timing
  3. The "78% WR" likely refers to profitable outcomes over multi-month horizons, not short-term trades
- **Our proxy quality:** Using blockchain.info hash rate API is GOOD -- we have access to the actual underlying data. Our `hash_ribbon_buy` strategy in onchain_strategies.py computes 30d/60d MA crossovers from real hash rate data. **This is one of our best on-chain implementations.**
- **Free data sources:**
  - blockchain.info: `https://blockchain.info/charts/hash-rate?timespan=1year&format=json` (free, no key)
  - Rate limit: max 1 query per 10 seconds

**RATING: 7/10 predictive power (high conviction, low frequency) | Proxy quality: 9/10 (uses real data)**

---

### 6. Stablecoin Supply Ratio (SSR)
- **Origin:** CryptoQuant Research (2020)
- **Definition:** BTC Market Cap / Total Stablecoin Market Cap. Measures relative buying power of stablecoins.
- **Signal:** Low SSR = high stablecoin buying power relative to BTC (bullish dry powder); High SSR = low buying power (bearish).
- **Stablecoins tracked:** USDT, USDC, TUSD, USDP, GUSD, DAI, SAI, BUSD.
- **Current state (Feb 2026):** Stablecoin market cap at ~$311 billion (13.58% of total crypto market cap). This represents massive potential buying power.
- **Honest assessment:** MODERATE predictive power. The logic is sound (more dry powder = more potential buying), but:
  1. Stablecoins are used for DeFi yield farming, not just BTC buying -- SSR overstates available buying pressure
  2. The metric moves slowly and is better for regime detection (months) than trade timing (days)
  3. Post-2024, stablecoin growth is partly driven by real-world payment adoption, not crypto speculation
- **Our proxy quality:** Using CoinGecko market caps for BTC + stablecoins is GOOD. Our `stablecoin_buying_power` strategy calculates SSR from real market cap data. **Solid proxy.**
- **Free data sources:**
  - CoinGecko: `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether,usd-coin,dai&vs_currencies=usd&include_market_cap=true` (free, 30 calls/min, 10K calls/mo)
  - Glassnode: `GET /v1/metrics/indicators/ssr` (daily, free tier)

**RATING: 5/10 predictive power (slow, regime-level) | Proxy quality: 8/10 (uses real market cap data)**

---

### 7. SOPR (Spent Output Profit Ratio)
- **Origin:** Renato Shirakashi (2019)
- **Definition:** Realized value of spent outputs / creation value of spent outputs. SOPR > 1 = sellers in profit; SOPR < 1 = sellers at a loss.
- **Signal:** In bull markets, SOPR dipping below 1 = "buy the dip" (panic selling at a loss = capitulation). STH-SOPR (Short-Term Holder variant) is more actionable.
- **Historical performance:** STH SOPR capitulation preceded moves from $26K to $70K (Aug 2023) and $54K to $100K (Aug 2024). Sustained SOPR > 1 during 2021 and 2024 coincided with strong uptrends.
- **Honest assessment:** GENUINE signal but context-dependent. Works well in bull markets, less reliable in bear/sideways markets. STH-SOPR is more actionable than aggregate SOPR.
- **Our proxy quality:** THIS IS OUR WEAKEST PROXY. SOPR requires actual UTXO data (the price at which each coin was last moved). Our `sopr_dip_buy_proxy` uses 30d SMA as a cost-basis approximation. This is a **fundamentally different calculation** that loses the core information (individual UTXO cost basis). The proxy correlates poorly with real SOPR (~0.3-0.4 estimated). **Consider replacing or flagging as low-confidence.**
- **Free data sources:**
  - CryptoQuant: https://cryptoquant.com/asset/btc/chart/market-indicator/spent-output-profit-ratio-sopr (paid API)
  - Glassnode: `GET /v1/metrics/indicators/sopr` (daily, free tier for basic SOPR)
  - No free real-time source. UTXO analysis requires full node or paid API.

**RATING: 7/10 predictive power (in bull markets) | Proxy quality: 2/10 (fundamentally broken proxy)**

---

### 8. NUPL (Net Unrealized Profit/Loss)
- **Definition:** (Market Cap - Realized Cap) / Market Cap. Shows aggregate unrealized profit/loss of all holders.
- **Signal:** NUPL > 0.75 = euphoria/market top zone; NUPL < -0.5 = capitulation/bottom zone.
- **Integration:** Z-score over 200 days; feed into LSTM as additional feature.
- **Honest assessment:** Very similar to MVRV in practice. Highly correlated (>0.95) with MVRV Z-Score. Adding both NUPL and MVRV to an ML model provides almost no additional information. **Pick one -- MVRV is better known and more widely tracked.**
- **Our proxy quality:** Not separately implemented, but captured partially by our MVRV proxy.
- **Free data sources:**
  - Glassnode: `GET /v1/metrics/indicators/net_unrealized_profit_loss` (daily, free tier)

**RATING: 7/10 predictive (but redundant with MVRV) | Proxy quality: N/A**

---

### 9. Fear & Greed Index (as on-chain adjacent)
- **Definition:** Composite of volatility (25%), market momentum/volume (25%), social media (15%), surveys (15%), BTC dominance (10%), Google trends (10%).
- **Signal:** F&G <= 10 = extreme fear = buy; F&G >= 90 = extreme greed = sell.
- **Our implementation:** `fear_greed_extreme_dca` triggers DCA entries when F&G <= 10. Nasdaq research showed 14.6% annual return from this approach.
- **Honest assessment:** The index itself is NOT on-chain data. It's a composite sentiment indicator. But it works well as a contrarian signal at extremes. Mid-range values (30-70) have almost zero predictive power.
- **Free data sources:**
  - Alternative.me: `https://api.alternative.me/fng/?limit=30&format=json` (free, no key, reliable)

**RATING: 6/10 at extremes only | Proxy quality: 10/10 (uses actual data source)**

---

### 10. Hayes Liquidity Index (Fed Balance Sheet - RRP - TGA)
- **Definition:** Federal Reserve Balance Sheet minus Reverse Repo Facility minus Treasury General Account = Net Liquidity.
- **Signal:** Rising net liquidity = risk assets rally; falling = risk-off.
- **Origin:** Arthur Hayes (BitMEX founder), popularized 2023-2026.
- **Honest assessment:** Not truly an on-chain metric, it's a macro liquidity indicator. But it has shown strong correlation with BTC price since 2020. The mechanism is causal: more liquidity in the system = more money flowing into risk assets including crypto.
- **Our implementation:** Uses FRED API data, which is the actual source. Good proxy.
- **Free data sources:**
  - FRED: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL` (Balance Sheet), `RRPONTSYD` (RRP), `WTREGEN` (TGA) -- all free, no key for CSV downloads.

**RATING: 6/10 (macro correlation, not direct causation) | Proxy quality: 9/10 (uses actual FRED data)**

---

## Free API Endpoint Reference

### Tier 1: Completely Free, No Key Required
| Source | Endpoint | Data | Rate Limit | Freshness |
|--------|----------|------|------------|-----------|
| Alternative.me | `api.alternative.me/fng/?limit=30` | Fear & Greed Index | Unlimited | Daily |
| blockchain.info | `blockchain.info/charts/hash-rate?format=json` | Hash Rate | 1/10sec | Daily |
| blockchain.info | `blockchain.info/charts/estimated-transaction-volume-usd?format=json` | TX Volume (NVT) | 1/10sec | Daily |
| blockchain.info | `blockchain.info/charts/difficulty?format=json` | Mining Difficulty | 1/10sec | Daily |
| FRED | `fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL` | Fed Balance Sheet | Unlimited | Weekly |
| Binance | `api.binance.com/fapi/v1/fundingRate` | Funding Rates | 1200/min | Real-time |
| Binance | `api.binance.com/fapi/v1/openInterest` | Open Interest | 1200/min | Real-time |

### Tier 2: Free with API Key (Rate Limited)
| Source | Endpoint | Data | Rate Limit | Freshness |
|--------|----------|------|------------|-----------|
| CoinGecko Demo | `api.coingecko.com/api/v3/simple/price` | Market Caps (SSR) | 30/min, 10K/mo | ~5min |
| CoinGecko Demo | `api.coingecko.com/api/v3/coins/{id}/market_chart` | Price History | 30/min | ~5min |
| Glassnode Free | `api.glassnode.com/v1/metrics/market/mvrv` | MVRV (daily) | Limited | 24h delay |
| Glassnode Free | `api.glassnode.com/v1/metrics/indicators/sopr` | SOPR (daily) | Limited | 24h delay |
| Glassnode Free | `api.glassnode.com/v1/metrics/indicators/ssr` | SSR (daily) | Limited | 24h delay |

### Tier 3: Paid Only (No Free Access)
| Source | Data | Min Cost | Notes |
|--------|------|----------|-------|
| CryptoQuant | Exchange Netflows | $99/mo | Gold standard for flow data |
| CryptoQuant | Whale Metrics | $99/mo | Entity-labeled flows |
| Glassnode Pro | Hourly/10-min resolution | $799/mo | Required for sub-daily data |
| Nansen | Wallet Labels/Entities | $150/mo | Smart money tracking |
| Santiment | Social + On-chain hybrid | $49/mo | Unique social sentiment data |

---

## Data Freshness & Lag Assessment

### Critical Question: Is On-Chain Data Too Slow for Intraday?

**YES, for free tiers. Marginally usable for paid tiers.**

| Resolution | Source | Cost | Usability |
|------------|--------|------|-----------|
| Daily (T+1) | Glassnode Free, blockchain.info | Free | Swing trading only (hold 3-14 days) |
| Daily (T+0) | CryptoQuant Standard | $99/mo | Same-day signals, still not intraday |
| Hourly | Glassnode Advanced | $299/mo | Intraday possible for slow strategies |
| 10-minute | Glassnode Professional | $799/mo | Reasonable for 4H+ timeframes |
| Real-time | Custom full-node parsing | Infrastructure cost | Only viable for well-funded operations |

**Recommendation for our system:** On-chain metrics should be used as **daily regime filters** (bull/bear/neutral classification) that gate or weight other faster signals (technical, funding rate, order book). Do NOT try to use on-chain data for entry/exit timing.

---

## Honest Assessment of Our Current Proxies (onchain_strategies.py)

| # | Strategy | Uses Real Data? | Proxy Quality | Recommendation |
|---|----------|----------------|---------------|----------------|
| 34 | mvrv_sma_proxy | No (200d SMA proxy) | 6/10 | Upgrade to Glassnode free API for daily MVRV |
| 35 | hash_ribbon_buy | YES (blockchain.info) | 9/10 | Keep as-is. One of our best implementations. |
| 36 | stablecoin_buying_power | YES (CoinGecko) | 8/10 | Keep as-is. Real market cap data. |
| 37 | nvt_overvaluation | YES (blockchain.info) | 7/10 | Keep, but note NVT degraded by L2/ETF era. |
| 38 | fear_greed_extreme_dca | YES (alternative.me) | 10/10 | Keep. Actual data, proven at extremes. |
| 39 | sopr_dip_buy_proxy | No (30d SMA proxy) | 2/10 | **REPLACE or DOWNWEIGHT.** Proxy is fundamentally broken. Consider Glassnode free SOPR instead. |
| 40 | onchain_composite_score | Mixed | 5/10 | Only as good as its component proxies. |
| 41 | hayes_liquidity_index | YES (FRED) | 9/10 | Keep. Actual macro data. Strong BTC correlation. |
| 42 | pentoshi_htf_structure | YES (price data) | 7/10 | Not really on-chain, but valid technical strategy. |
| 43 | funding_rate_arbitrage | YES (Binance API) | 9/10 | Keep. Real funding data, documented returns. |

### Top Priority Improvements
1. **Replace SOPR proxy** with Glassnode free tier daily SOPR (even delayed daily data is better than our broken proxy)
2. **Upgrade MVRV proxy** to use Glassnode free API daily MVRV when available, fall back to SMA proxy
3. **Add exchange netflow** as a feature if we invest $99/mo in CryptoQuant, otherwise skip it
4. **Do NOT add whale tracking** as an ML feature -- too noisy, better as discretionary overlay

---

## ML Integration Recommendations

### Feature Engineering for On-Chain Metrics
```
Recommended features for ML model input:
1. MVRV Z-Score (daily) → z-score over 200d → regime label {capitulation, accumulation, fair_value, overheated, euphoria}
2. Hash Ribbon state (daily) → binary {capitulation=0, recovery=1}
3. SSR percentile (daily) → percentile rank over 365d → buying_power_score [0-100]
4. Fear & Greed (daily) → raw value + 7d MA + extreme flag (<=10 or >=90)
5. Net Liquidity (weekly) → 30d rate of change → liquidity_trend {expanding, contracting}
6. Funding Rate (real-time) → 8h aggregated → carry_opportunity score
7. NVT ratio (daily) → z-score over 200d → valuation_signal {cheap, fair, expensive}
```

### What NOT to Do
- Do NOT feed raw on-chain values into ML models. They have different scales across cycles. Always normalize (z-score, percentile, or regime label).
- Do NOT use on-chain features for intraday prediction horizons. They update too slowly.
- Do NOT treat on-chain metrics as independent features -- MVRV, NUPL, and SOPR are highly correlated. Use PCA or pick one representative per cluster.
- Do NOT expect on-chain features to improve short-term (<24h) prediction accuracy. Academic papers show improvement primarily on 7-day+ horizons.

### Recommended Architecture
```
[On-chain features (daily)] → Regime Classifier (bull/bear/neutral)
                                      ↓
[Technical features (5m-4h)] → Trade Signal Generator
                                      ↓
                              Signal GATED by regime
                              (e.g., only take longs in bull regime)
```

This two-layer approach uses on-chain data where it is strong (regime detection) and avoids using it where it is weak (timing).

---

## Academic References

1. Mahmudov, M. & Puell, D. (2018). "Bitcoin Market-Value-to-Realized-Value (MVRV) Ratio." Medium.
2. Woo, W. (2017). "Bitcoin NVT Ratio." Woobull Charts.
3. Edwards, C. (2019). "Hash Ribbons & Bitcoin Bottoms." Capriole Investments.
4. Shirakashi, R. (2019). "Introducing SOPR." Medium.
5. CryptoQuant (2020). "Stablecoin Supply Ratio (SSR)." CryptoQuant Research.
6. Hayes, A. (2024-2026). "Net Liquidity Framework." BitMEX blog / Substack.
7. ScienceDirect (2024). "Using machine and deep learning models, on-chain data, and technical analysis for predicting bitcoin price direction." -- CNN-LSTM + Boruta achieved 82.44% accuracy on 7-day BTC direction.
8. ScienceDirect (2025). "Bitcoin price direction prediction using on-chain data and feature selection." -- 225 features (92 on-chain + 138 TA), Boruta-SVM most profitable.
9. arXiv (2024). "A Comprehensive Analysis of Machine Learning Models for Algorithmic Trading of Bitcoin." -- SVM achieved 83% accuracy, F1-Score 82%.
10. 21shares Research (2025). "The two eras of Bitcoin valuation: pre- and post-ETFs." -- On-chain metrics degraded by ETF-era dynamics.

---

## Actionable Insights

- [x] Audit all on-chain proxies in `onchain_strategies.py` -- completed above
- [ ] Replace SOPR proxy with Glassnode free tier daily SOPR API call
- [ ] Add Glassnode free MVRV as primary signal, keep SMA proxy as fallback
- [ ] Implement on-chain regime classifier (bull/bear/neutral) using MVRV + F&G + liquidity
- [ ] Use regime as a gate/weight for faster technical signals
- [ ] Do NOT invest in CryptoQuant/Nansen unless fund size justifies $99-799/mo
- [ ] Normalize all on-chain features as z-scores or percentile ranks before feeding to ML
- [ ] Test: Does adding on-chain regime label improve 7-day direction accuracy? (expected: yes, +3-8% based on literature)

---

*Researcher ID: 007* | *Status: COMPLETE* | *Last Updated: 2026-02-24*
