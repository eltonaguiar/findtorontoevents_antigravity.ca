# Researcher Profile: Dr. Anna Petrova

## Persona
- **Title:** DeFi Yield and Smart Contract Risk Specialist
- **Expertise:** Yield farming, liquidity provision, impermanent loss, smart contract risk modeling
- **Years Experience:** 7
- **Background:** PhD University of Zurich, former DeFi researcher at Messari, now builds ML models for yield optimization.

## Research Scope
**Primary Question:** How can ML predict and optimize DeFi yield opportunities while managing smart contract and impermanent loss risks?

**Target Systems/Areas:**
- Yield farming APY prediction (Uniswap, Aave, Compound)
- Impermanent loss forecasting for liquidity providers
- Smart contract risk scoring (audit scores, bug bounty, age)
- Protocol-level risk (TVL trends, governance)
- MEV (Maximal Extractable Value) prediction

## Methodology
1. **Sources:** DeFiLlama API, Etherscan, Dune Analytics, smart contract audit reports, academic papers on DeFi risk.
2. **Extraction:** APY time series, pool liquidity, volume, impermanent loss calculations, audit scores.
3. **Analysis:** Predict APY changes; identify safe vs risky protocols; model IL as function of price volatility.
4. **Validation:** Backtest yield strategies with ML-driven allocation; compare to naive equal-weight.

## Audit Findings (Codebase Analysis)

### 1. DeFi Protocol Integrations

**DeFi Token Universe (alpha_engine/config.py, lines 119-125):**
The Alpha Engine tracks DeFi protocol tokens as tradeable assets but does NOT integrate with the protocols themselves:
- `UNI-USD` (Uniswap) — tier: "defi", traded via Binance (UNIUSDT)
- `AAVE-USD` (Aave) — tier: "defi", traded via Binance (AAVEUSDT)
- `MAV-USD` (Maverick Protocol) — tier: "defi", traded via Binance (MAVUSDT)

**DeFi Token Classification (claude_gainer_ml/data_fetcher.py, lines 623-627):**
Extensive DeFi token classification for ML features:
- UNI, AAVE, MKR, SNX, COMP, LDO, CRV, DYDX, GMX, SUSHI, 1INCH, CAKE, PENDLE, ENA, ETHFI, JUP
- All classified as "defi" sector for sector-rotation and narrative strategies

**Verdict:** DeFi tokens are tracked as price assets for trading signals, but there is NO direct protocol integration (no Uniswap LP, no Aave lending/borrowing, no Compound supply/borrow). The system trades DeFi governance tokens on CEXes, not DeFi protocols on-chain.

### 2. Yield Farming and Liquidity Provision Strategies

**Funding Rate Carry (closest analog to yield farming):**

Three separate implementations exist for funding rate arbitrage, which is the closest CeFi equivalent to DeFi yield farming:

1. **alpha_engine/funding_rate_scanner.py** — Production scanner for Binance perpetual funding rates across 10 major pairs (BTC, ETH, SOL, BNB, AVAX, LINK, DOGE, XRP, ADA, MATIC). Signal logic:
   - Extreme negative funding (< -0.05%/8h) = BUY at 85% confidence
   - Negative funding (< -0.01%/8h) = BUY at 65% confidence
   - Includes full backtester with 90-day historical data, Sharpe calculation
   - **Proven result:** DOGE funding rate carry: 71% WR, Sharpe 8.19 (marginal p~0.042)

2. **ml_battleground/pilots/funding_rate_carry.py** — ML-enhanced funding rate carry pilot using GradientBoostingClassifier:
   - Features: last 5 funding rates, funding slope, 20-period mean, open interest, long/short ratio, price momentum, realized volatility
   - Trains on historical funding sequences, with heuristic fallback
   - Targets delta-neutral carry trades (long spot + short perp)
   - Reference: Gate.io 2025 study documented 19-115% annual returns

3. **alpha_engine/onchain_strategies.py (strategy #43: funding_rate_arbitrage)** — Market-neutral carry strategy integrated into the main Alpha Engine pipeline. Long spot + short perpetual to collect funding payments.

4. **funding_arb_analysis.py** — Standalone analysis tool for funding rate distribution statistics across multiple symbols and time periods.

**Verdict:** The system has robust CeFi funding rate yield strategies but NO DeFi yield farming (no Uniswap LP, no Aave/Compound lending, no liquidity provision on-chain).

### 3. Impermanent Loss Calculations

**Finding: NONE**

There are zero impermanent loss calculations anywhere in the codebase. No IL modeling, no LP position tracking, no AMM price impact estimation. The system exclusively trades on centralized exchanges (Binance spot and futures) where impermanent loss does not apply.

### 4. Smart Contract Risk Scoring

**Finding: NONE**

There is no smart contract audit scoring, no contract age analysis, no bug bounty tracking, and no protocol risk scoring. The system does not interact with smart contracts.

**Partial proxy:** The `claude_gainer_ml/token_sniffer.py` module exists but is focused on scam detection for new tokens, not smart contract risk scoring for DeFi protocols.

### 5. TVL Monitoring and DeFi Analytics

**DeFiLlama Integration (partial):**

Two strategies in `alpha_engine/event_strategies.py` and `alpha_engine/advanced_strategies.py` use the DeFiLlama API, but only for token unlock data — NOT for TVL or yield data:

1. **token_unlock_short** (event_strategies.py, line 116-159) — Fetches upcoming token unlocks from `https://api.llama.fi/unlocks` to generate short signals when >1% of circulating supply unlocks in 3-7 days.

2. **unlock_scoring_enhanced** (advanced_strategies.py, line 647-689) — Enhanced version using Keyrock scoring system with a 30-14 day entry/exit rule for token unlock shorts.

**Verdict:** DeFiLlama is used exclusively for token unlock schedules. No TVL tracking, no yield/APY data, no protocol health monitoring.

### 6. On-Chain Data Integration

**Substantial on-chain infrastructure exists but is NOT DeFi-specific:**

1. **scripts/onchain_analytics.py** — Uses Web3.py + Etherscan API for whale transaction monitoring:
   - Connects to Ethereum via Infura
   - Fetches large token transfers (>1 ETH) from Etherscan
   - Stores whale counts in MySQL database
   - Requires `INFURA_URL` and `ETHERSCAN_KEY` environment variables

2. **onchain_metrics_agent.py** (598 lines) — Comprehensive async on-chain metrics agent:
   - **GlassnodeClient:** API client for `api.glassnode.com/v1/metrics` (transaction counts, active addresses, new addresses, gas price, gas used, hashrate, difficulty, UTXO metrics)
   - **CryptoQuantClient:** API client for `api.cryptoquant.com/v1` (exchange inflow/outflow data)
   - **WhaleMonitor:** Scans for large on-chain transactions (thresholds: BTC $1M, ETH $500K, SOL $100K, ADA $50K)
   - **ExchangeFlowAnalyzer:** Tracks exchange inflows/outflows with net flow and flow ratio calculations
   - **NetworkMetricsAnalyzer:** Transaction counts, active addresses, gas metrics, hashrate, UTXO data
   - Data structures: WhaleTransaction, ExchangeFlows, NetworkMetrics, MiningMetrics
   - Currently uses placeholder API keys (not production-active)

3. **alpha_engine/onchain_strategies.py** (10 strategies, all production-active):
   - `mvrv_sma_proxy` — MVRV Z-Score via 200d SMA ratio (Mahmudov & Puell 2018)
   - `hash_ribbon_buy` — Miner capitulation recovery from blockchain.info (Edwards 2019, 78% WR)
   - `stablecoin_buying_power` — SSR from CoinGecko stablecoin market caps (CryptoQuant 2020)
   - `nvt_overvaluation` — NVT ratio from blockchain.info TX volume (Willy Woo 2017)
   - `fear_greed_extreme_dca` — F&G <=10 extreme-fear DCA
   - `sopr_dip_buy_proxy` — STH cost-basis proxy via 30d SMA (Shirakashi 2019)
   - `onchain_composite_score` — 4-layer confluence (MVRV + Volume + F&G + Whale bars)
   - `hayes_liquidity_index` — Fed BS - RRP - TGA from FRED (Arthur Hayes)
   - `pentoshi_htf_structure` — Weekly higher lows + EMA support pullback
   - `funding_rate_arbitrage` — Market-neutral carry (long spot + short perps)

**Verdict:** Strong on-chain analytics for BTC/ETH price signals, but no DeFi protocol-level on-chain analysis (no pool TVL tracking, no LP position monitoring, no governance voting analysis).

### 7. DeFi-Specific ML Models

**Finding: NONE dedicated to DeFi**

The ML models in the codebase are focused on:
- Price prediction (crypto_ml_edge, ml_crypto_predictor)
- Funding rate prediction (ml_battleground/pilots/funding_rate_carry.py uses GradientBoosting)
- Signal ranking (alpha_engine/ml_ranker.py, KIMI ml_signal_ranker.py)
- Regime detection (regime_terminal/)

No models exist for:
- APY/yield prediction
- Impermanent loss forecasting
- Smart contract exploit risk
- Protocol TVL trajectory prediction
- MEV prediction or extraction

## Gap Analysis: What Is Missing for DeFi Yield Optimization

| Capability | Current State | Gap Severity |
|---|---|---|
| DeFi protocol integration (Uniswap, Aave, Compound) | NOT PRESENT — trades DeFi tokens on CEX only | CRITICAL |
| Yield farming APY prediction | NOT PRESENT | CRITICAL |
| Impermanent loss calculations | NOT PRESENT | CRITICAL |
| Smart contract risk scoring | NOT PRESENT | HIGH |
| TVL monitoring | DeFiLlama used only for unlocks, not TVL | HIGH |
| On-chain data integration | STRONG — Glassnode, CryptoQuant, Etherscan, blockchain.info | LOW (but not DeFi-focused) |
| Funding rate carry (CeFi analog) | STRONG — 3 implementations, backtested, ML-enhanced | LOW |
| DeFi-specific ML models | NOT PRESENT | CRITICAL |
| MEV analysis | NOT PRESENT | MEDIUM |
| Governance/protocol risk | NOT PRESENT | MEDIUM |

## Actionable Recommendations

### High Priority (would transform the system)
- [ ] Integrate DeFiLlama `/yields` API for real-time pool APY and TVL data across Uniswap, Aave, Compound, Curve
- [ ] Build impermanent loss calculator: IL = 2*sqrt(r)/(1+r) - 1 where r = price ratio change; combine with volatility forecast to estimate expected IL
- [ ] Create smart contract risk scoring module: age (days since deploy), audit count (OpenZeppelin, Trail of Bits, Certik), TVL stability (30d coefficient of variation), exploit history
- [ ] Build XGBoost model for 7-day APY prediction using features: current APY, TVL, volume, token volatility, protocol age, audit score

### Medium Priority (incremental value)
- [ ] Extend DeFiLlama integration to pull TVL trends for protocol health scoring
- [ ] Add MEV analysis for Ethereum (Flashbots API or MEV-Boost data)
- [ ] Model IL as a real option and compare expected IL cost vs expected APY yield
- [ ] Diversify yield allocation across 3-5 protocols to mitigate single-point-of-failure risk

### Low Priority (nice to have)
- [ ] Integrate Dune Analytics for custom DeFi protocol queries
- [ ] Add governance proposal monitoring (Snapshot, Tally)
- [ ] Build protocol-level risk dashboard combining TVL, audit score, and on-chain activity

## Existing Strengths to Leverage

The codebase has strong foundations that could be extended for DeFi:

1. **On-chain data pipeline** — The `onchain_metrics_agent.py` Glassnode/CryptoQuant infrastructure could be extended to fetch DeFi-specific metrics (pool reserves, LP positions, protocol revenue)
2. **Funding rate carry expertise** — The 3 funding rate implementations demonstrate deep understanding of yield-bearing strategies; this logic could be adapted for DeFi yield optimization
3. **ML infrastructure** — The GradientBoosting model in `funding_rate_carry.py` provides a template for APY prediction models
4. **Free API strategy** — The system's philosophy of using free APIs (blockchain.info, CoinGecko, FRED, DeFiLlama) aligns well with DeFiLlama's free yields endpoint

## References
- DeFiLlama yields API: `https://yields.llama.fi/pools` (free, no key)
- Etherscan API integration: `scripts/onchain_analytics.py` (existing)
- Glassnode client: `onchain_metrics_agent.py` (existing, placeholder keys)
- "Impermanent Loss in Uniswap v3" (Adams et al., 2021)
- Smart contract audit frameworks: OpenZeppelin, Trail of Bits, Certik
- Gate.io 2025 funding rate carry study (referenced in `funding_rate_carry.py`)

---
*Researcher ID: 027* | *Status: Complete*