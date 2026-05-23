# Researcher Profile: Dr. William Chen

## Persona
- **Title:** Crypto-Native and Governance Token Specialist
- **Expertise:** DAO governance, tokenomics, protocol revenue modeling
- **Years Experience:** 8
- **Background:** PhD Stanford Economics, former researcher at a16z Crypto, now builds ML models for governance tokens and DeFi protocols.

## Research Scope
**Primary Question:** How can ML predict governance token prices and protocol health, incorporating on-chain and governance activity?

**Target Systems/Areas:**
- Governance token valuation models
- DAO proposal activity and sentiment
- Protocol revenue sharing (fee distribution)
- Token unlock schedules (supply inflation)
- Delegation dynamics
- Treasury diversification

## Methodology
1. **Sources:** Token terminal, Dune Analytics, Tally (governance data), Snapshot, academic papers on tokenomics.
2. **Extraction:** Revenue, fees, treasury value, active proposals, voter turnout, delegation concentration.
3. **Analysis:** Correlate governance metrics with token price; predict token unlocks impact.
4. **Validation:** Backtest token selection based on governance health scores.

---

## Codebase Audit Findings

### 1. Token Unlock Schedule Tracking -- STRONG IMPLEMENTATION

**Status: Implemented and Production-Active (2 strategies)**

The codebase has two fully implemented token unlock strategies, both live in the Alpha Engine's 30-minute scanning pipeline:

#### Strategy 48: `token_unlock_short` (event_strategies.py, lines 116-217)
- **Data Source:** DeFiLlama Unlocks API (`https://api.llama.fi/unlocks`) -- FREE, no API key
- **Logic:** Fetches top 50 upcoming unlock events, matches tokens to the internal symbol universe, filters for unlocks 3-7 days away exceeding 1% of circulating supply
- **Signal:** SELL (short) with confidence scaling by unlock percentage (0.55 + unlock_pct * 0.03, capped at 0.85)
- **TP/SL:** 5% downside target, 3% stop loss
- **Academic Basis:** Keyrock (2024) -- 16,000+ events analyzed, 90% of cliff unlocks cause negative pressure, average -5% over 7 days
- **File:** `E:\findtorontoevents_antigravity.ca\alpha_engine\event_strategies.py`

#### Strategy 60: `unlock_scoring_enhanced` (advanced_strategies.py, lines 647-801)
- **Scoring System (0-9 points):**
  - Recipient type: TEAM (+3), INVESTOR (+2), UNKNOWN (+1), ECOSYSTEM (skip -- avg +1.18%)
  - Supply percentage: >5% (+3), >2% (+2), >1% (+1)
  - Unlock style: CLIFF (+2), LINEAR (+0), UNKNOWN (+1)
  - Has perpetual market on Binance (+1)
- **Time Window:** "30-14 Rule" -- looks 7-14 days ahead (sweet spot per Keyrock)
- **Signal Threshold:** Score >= 5 triggers SELL signal
- **Differentiated TP:** TEAM unlocks target -15% (Keyrock avg -25%), INVESTOR -7%, others -5%
- **File:** `E:\findtorontoevents_antigravity.ca\alpha_engine\advanced_strategies.py`

**Performance Status:** Both strategies currently in MONITOR phase with 0/5 picks (insufficient data for auto-tuner evaluation), indicating they are deployed but haven't yet triggered enough signals in the live environment.

### 2. Protocol Revenue and Fee Monitoring -- PARTIAL (Proxy Only)

**Status: Indirect proxies exist; no direct Token Terminal or Dune integration**

There is **no direct protocol revenue tracking** (e.g., Token Terminal API, Dune Analytics queries, or fee distribution monitoring). However, several proxy mechanisms exist:

- **NVT Overvaluation** (`onchain_strategies.py`, line 414): Uses blockchain.info transaction volume as a proxy for network "revenue" via the NVT ratio (Willy Woo 2017). Signals SELL when NVT is overvalued (price outpacing transaction volume) and BUY when NVT is undervalued. This is the closest thing to protocol revenue tracking in the codebase.
- **Stablecoin Buying Power (SSR)** (`onchain_strategies.py`, line 308): Monitors stablecoin supply ratio via CoinGecko market caps as a proxy for available buying power -- related to protocol liquidity but not revenue.
- **Fundamental Features Module** (`alpha_engine/features/fundamental.py`): Computes quality composite scores including ROE, ROIC, gross/operating/net margins, FCF yield, earnings yield, Piotroski F-Score proxy, and balance sheet resilience. However, this is designed for equities and stocks, NOT for crypto protocol revenue.

**Gap:** No integration with Token Terminal, DefiLlama protocol revenue endpoints, or fee-sharing data (e.g., Uniswap fee revenue, Aave protocol income, MakerDAO surplus buffer).

### 3. Governance Activity Tracking -- NOT IMPLEMENTED

**Status: Not present in codebase**

There is **no governance activity tracking** in the codebase:
- No Tally API integration (on-chain governance proposals/votes)
- No Snapshot API integration (off-chain governance)
- No proposal sentiment analysis
- No voter turnout monitoring
- No delegation concentration tracking

The `ml_crypto_predictor/researchers/governance_researcher.py` file exists but focuses on **ML model governance** (explainability, audit trails, compliance, SHAP, regulatory compliance) -- NOT on crypto DAO governance. It is a model risk management module, not a governance token analytics module.

### 4. Tokenomics Modeling -- PARTIAL

**Status: Supply-side only (unlocks); no burn/inflation modeling**

- **Supply Inflation (Unlocks):** Well-covered by the two token unlock strategies described above.
- **No Token Burn Tracking:** No code monitors deflationary token burns (e.g., ETH EIP-1559, BNB auto-burn, SHIB burns).
- **No Circulating Supply Growth Modeling:** No time-series modeling of supply schedules or emission curves.
- **No Vesting Schedule Visualization:** Unlock data is fetched and processed but not stored or visualized over time.

### 5. Fundamental Analysis of Crypto Projects -- PARTIAL

**Status: Price-technical + on-chain proxies only; no qualitative fundamentals**

The codebase has a rich set of **quantitative on-chain metrics** (`onchain_strategies.py`, 10 strategies) that serve as protocol health proxies:

| Strategy | Metric | What it Measures |
|---|---|---|
| `mvrv_sma_proxy` | MVRV Z-Score via 200d SMA | Market vs realized value (overvaluation) |
| `nvt_overvaluation` | NVT Ratio | Price vs transaction volume (usage-based valuation) |
| `stablecoin_buying_power` | SSR Ratio | Available buying power in stablecoins |
| `fear_greed_extreme_dca` | Fear & Greed Index | Market sentiment extremes |
| `hayes_liquidity_index` | Fed BS - RRP - TGA | Macro liquidity (Arthur Hayes thesis) |
| `onchain_composite_score` | 4-layer confluence | Multi-signal on-chain composite |
| `hash_ribbon_buy` | Hash Rate Ribbons | Miner capitulation recovery |
| `sopr_dip_buy_proxy` | SOPR-like via 30d SMA | Short-term holder cost basis |

However, there is **no qualitative fundamental analysis** such as: team assessment, roadmap evaluation, competitive moat analysis, developer activity (GitHub commits), or TVL growth tracking.

### 6. DAO-Related Analytics -- NOT IMPLEMENTED

**Status: Not present**

No DAO-specific analytics exist:
- No treasury tracking (DAO treasuries like Uniswap, Lido, Arbitrum)
- No treasury diversification analysis
- No governance participation rate monitoring
- No delegation power distribution analysis (Herfindahl index of voting power)
- No proposal outcome prediction models

### 7. Token Scoring and Ranking Systems -- IMPLEMENTED (ML-Based)

**Status: ML Signal Ranker exists but is strategy-agnostic, not token-specific**

#### ML Signal Ranker (`alpha_engine/ml_ranker.py`)
- **Architecture:** RandomForestClassifier with balanced class weights
- **Features:** 18 engineered features per signal (confidence, risk/reward, strategy type, time-of-day, day-of-week, etc.)
- **Training:** Auto-trains when >= 50 closed picks accumulate; heuristic fallback during cold start
- **Purpose:** Ranks and filters all incoming signals across 100+ strategies -- not specifically token-focused

#### Narrative/Sector Rotation Scoring (`event_strategies.py`, lines 544-660)
- Tracks CoinGecko category performance (AI, DePIN, RWA, Layer-1, DeFi, Meme, Infrastructure)
- Identifies "hot categories" with >3% 24h market cap growth
- Maps categories to tradeable symbols via hardcoded `NARRATIVE_MAP`
- Buys sector laggards that haven't yet participated in the rally

#### Sector Momentum 7d (`advanced_strategies.py`, lines 1027-1126)
- 7-day rolling momentum on CoinGecko categories
- Filters flash narratives (meme < 2 weeks)
- `SECTOR_SYMBOLS` map covers: layer-1, smart-contract-platform, defi, meme-token, infrastructure, real-world-assets, artificial-intelligence

#### Top Gainer Pattern Data (`alpha_engine/data/top_gainer_patterns.json`)
- Historical pattern data includes governance-related entries (e.g., DCR/Decred: "Treasury governance upgrade + 10yr anniversary" with +32% gain)
- Categories include "Privacy/Governance" as a tracked sector

### 8. Funding Rate as Protocol Revenue Proxy

**Status: Strong implementation (3 strategies)**

While not "protocol revenue" in the traditional DeFi sense, funding rate strategies represent protocol-level fee mechanics:

- **`funding_rate_scanner.py`:** Standalone Binance funding rate scanner across 10 major pairs, with annualized rate calculation and signal classification (71% WR on DOGE, Sharpe 8.19)
- **`funding_rate_arbitrage`** (`onchain_strategies.py`, line 1233): Market-neutral carry (long spot + short perps) targeting ~22-50%+ annualized, delta-neutral
- **`funding_rate_carry`** (`crypto_strategies.py`): Short overleveraged longs when funding is extreme positive (60% WR per Kraken Research)

---

## Summary Assessment

| Capability | Status | Implementation Level | Files |
|---|---|---|---|
| Token Unlock Tracking | STRONG | 2 production strategies, DeFiLlama API, Keyrock scoring | `event_strategies.py`, `advanced_strategies.py` |
| Protocol Revenue Monitoring | WEAK | NVT ratio as proxy only; no Token Terminal | `onchain_strategies.py` |
| Governance Activity (DAO votes) | ABSENT | No Tally, Snapshot, or governance API integration | -- |
| Tokenomics (burn/inflation) | PARTIAL | Supply-side unlocks only; no burn tracking | `event_strategies.py` |
| Fundamental Analysis | PARTIAL | On-chain quantitative proxies; equity fundamentals module exists but not adapted for crypto | `onchain_strategies.py`, `features/fundamental.py` |
| DAO Analytics | ABSENT | No treasury, delegation, or participation tracking | -- |
| Token Scoring/Ranking | MODERATE | ML ranker (strategy-agnostic); sector rotation scoring | `ml_ranker.py`, `event_strategies.py`, `advanced_strategies.py` |
| Funding Rate / Fee Mechanics | STRONG | 3 strategies, Binance real-time data, arb + carry | `funding_rate_scanner.py`, `onchain_strategies.py`, `crypto_strategies.py` |

## Critical Gaps for Governance Token Modeling

1. **No Tally/Snapshot Integration:** Cannot track governance proposals, voting patterns, or delegation dynamics -- essential for governance token valuation
2. **No Token Terminal API:** Missing protocol revenue, fees, and P/E ratio data -- the most fundamental DeFi valuation metric
3. **No Token Burn Tracking:** Cannot model deflationary dynamics (ETH burns, BNB quarterly burns, etc.)
4. **No Treasury Analytics:** No monitoring of DAO treasury size, diversification, or spending rates
5. **No Developer Activity Metrics:** No GitHub commit tracking or developer ecosystem health assessment
6. **No TVL Tracking:** Total Value Locked is absent as a signal despite being a core DeFi health metric
7. **Equity Fundamental Module Not Adapted:** The `fundamental.py` feature module has a strong framework (ROE, ROIC, Piotroski) but is designed for stocks, not crypto protocols

## Recommendations for Governance Token Model Enhancement

### Priority 1: Data Sources to Integrate
- **DefiLlama TVL API** (free): `https://api.llama.fi/tvl/{protocol}` -- TVL trends as protocol health
- **DefiLlama Revenue API** (free): `https://api.llama.fi/overview/fees` -- protocol revenue
- **Snapshot GraphQL** (free): `https://hub.snapshot.org/graphql` -- governance proposals, vote counts
- **Ultrasound.money API** (free): ETH burn rate tracking

### Priority 2: New Strategies to Build
- `governance_activity_score`: Track proposal frequency + voter turnout + delegation concentration -> bullish when community engagement rises
- `protocol_revenue_momentum`: Buy tokens with accelerating 30d protocol revenue (Token Terminal style)
- `tvl_momentum_divergence`: Buy when TVL grows but token price hasn't caught up
- `treasury_health_score`: Monitor DAO treasuries; avoid protocols with declining runway

### Priority 3: Adapt Existing Infrastructure
- Extend `features/fundamental.py` to support crypto-native metrics (TVL, revenue, fees, burn rate)
- Add governance data to `ml_ranker.py` feature set (18 -> 22+ features)
- Create `governance_strategies.py` module following the established pattern in `event_strategies.py`

## References
- Keyrock (2024) -- Token unlock impact analysis (16,000+ events)
- Willy Woo (2017) -- NVT Ratio
- Arthur Hayes (2024-2026) -- Macro liquidity index
- Daniel & Moskowitz (2016) JFE -- Momentum crash hedging
- Token Terminal documentation
- DefiLlama API documentation
- Snapshot governance API documentation

---
*Researcher ID: 030* | *Status: Complete*
