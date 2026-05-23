# Researcher 028: Dr. Christopher Lee
## MEV and Blockchain Extraction Specialist
**PhD UC Berkeley EECS | 6 Years Experience | Former Blockchain Engineer, MEV Firm**

**Research Date:** February 24, 2026
**Mission:** Comprehensive analysis of the MEV landscape (2024-2026), its current state, profitability, technical architecture, ethical dimensions, and relevance as a feature for ML prediction models.

---

## Section 1: MEV Landscape 2025-2026 — Total Extractable Value, Trends, Competition

### Current Scale

Maximal Extractable Value (MEV) refers to profit that block producers (validators, miners) or searchers can capture by reordering, including, or excluding transactions within blocks they produce. The scale in 2025-2026 is substantial and growing:

- **$24 million** extracted on Ethereum in a single 30-day window (December 2025 - January 2026)
- **$561.92 million** in total MEV transaction volume tracked in 2025 across major types
- **$289.76 million** from sandwich attacks alone — 51.56% of total MEV volume
- **$3.37 million** in pure arbitrage profits in September 2025 (EigenPhi, 30-day window)
- **$233.8 million** extracted by 19 major CEX-DEX searchers from 7.2 million identified arbitrages between August 2023 and March 2025

On Solana specifically:
- **$370M to $500M** extracted via sandwich attacks over a 16-month period (Jan 2024 to May 2025)
- **$3.2M** of SOL extracted via sandwich attacks in October 2025 alone

The ESMA (European Securities and Markets Authority) published a formal July 2025 report confirming MEV is "widespread on Ethereum and growing on some blockchains," with explicit findings that it "operates against the principles of fairness and integrity that underpin orderly markets."

### Competition and Centralization

The searcher landscape is highly concentrated:
- **80% of MEV** is captured by the top 5 searcher entities (Flashbots data, 2024)
- Centralization index rose **25% year-over-year** through 2024-2025
- Over **90% of arbitrage transactions** now route through private channels (MEV-Boost / private mempools)
- In October 2025, only **515 distinct bots** operated on Ethereum, with roughly 100 active sandwich bots per typical month
- ~30% of sandwich bots recorded **net losses** and roughly one-third operated at break-even

**What this means:** The MEV extraction market is a winner-take-all oligopoly. Retail attempts to enter are unprofitable. Margins have been competed down to near-zero for new entrants.

### Revenue Distribution

The most striking finding about MEV economics:
- Searchers often pay **more than 90% of their revenue to block proposers**
- Major searchers like SCP and Wintermute retain only **10-15% of arbitrage revenue**; the rest flows to builders/validators
- Average profit per sandwich attack: just **$3**
- Monthly net profits after gas costs for sandwich activity averaged approximately **$260,000/month in 2025** across all active bots — shared among ~100 bots

**Key takeaway:** The apparent MEV "goldmine" is largely captured by validators and builders, not searchers. The competition for MEV extraction has driven margins to commodity levels.

---

## Section 2: Flashbots and MEV-Boost — Current Architecture and Builder Landscape

### MEV-Boost Architecture (Proposer-Builder Separation)

MEV-Boost implements Proposer-Builder Separation (PBS) outside the Ethereum protocol:

```
Searchers → Bundles → Builders → Blocks → Relays → Validators (Proposers)
```

**Key components:**

1. **Searchers** — Identify MEV opportunities (arbitrage, liquidation, sandwich). Submit bundles (atomic transaction packages) to builders.
2. **Builders** — Aggregate bundles and ordinary transactions into full blocks optimized for maximum fee revenue. Compete for validator business.
3. **Relays** — Trusted intermediaries that verify blocks from builders and present the highest-paying block to validators. Flashbots relay is the dominant actor.
4. **Validators (Proposers)** — Accept the highest-bid block from a relay via MEV-Boost sidecar. No visibility into block contents until after commitment.

**The MEV-Boost sidecar** is a separate piece of software validators run alongside their consensus client. It queries multiple relays and selects the highest-value block header, committing the validator to that block without seeing its contents (prevents censorship).

### Builder Market Concentration (2025)

- **Beaverbuild**: ~50% of Ethereum block production market share
- **Top 2 builders**: >90% of all Ethereum blocks
- This extreme concentration has attracted regulatory and academic criticism

### BuilderNet: The Decentralization Response (2025)

In response to builder centralization, Flashbots launched **BuilderNet**:
- **November 2024**: Initial release, jointly operated by Flashbots, Beaverbuild, and Nethermind
- **December 2024**: Flashbots migrated all builders, orderflow, and refunds to BuilderNet; ceased operating centralized block builders
- **February 2025**: BuilderNet v1.2 released — streamlined operator onboarding, TDX (Intel Trust Domain Extensions) image builds, container-based architecture
- **Goal**: Neutralize exclusive orderflow deals, distribute MEV more equitably, enhance censorship resistance

### SUAVE: The Long-Term Vision

Flashbots' SUAVE (Single Unifying Auction for Value Expression) vision:
- An Ethereum-native, MEV-aware, **privacy-first encrypted mempool**
- Eliminates central control points including Flashbots itself
- Prevents exclusive orderflow entrenchment
- Status (2025): Research phase transitioning to BuilderNet as first milestone
- **Flashnet** is planned next: a censorship-resistance and anonymity tool connecting block-building pipeline actors

### Technical Requirements to Participate

| Role | Requirements | Capital |
|------|-------------|---------|
| Searcher | Algorithm, bundle submission API, Flashbots account | Variable ($10K-$10M+ depending on strategy) |
| Builder | High-performance server, orderflow relationships, block assembly software | $500K+ in infrastructure + competitive capital |
| Relay | Trust relationships, uptime guarantees, legal compliance | Significant operational investment |
| Validator | 32 ETH stake, consensus client + MEV-Boost sidecar | ~$100K at current ETH prices |

---

## Section 3: Sandwich Attack Detection — Can You Detect and Avoid Being Sandwiched?

### How Sandwich Attacks Work

1. Attacker monitors public mempool for pending large DEX swaps
2. **Front-run**: Attacker submits identical trade BEFORE victim with higher gas fee
3. Victim's trade executes, moving price against victim (they get worse fill)
4. **Back-run**: Attacker immediately reverses position, profiting from price impact

Empirical data: Single adversaries reliably execute sandwich attacks with:
- **Round-trip detection + execution latency: ~450ms**
- **Execution latency alone: ~200ms**
- 19/20 success rate in controlled experiments

### Detection Methods (2025 State of the Art)

**Academic Research:**
- A 2025 paper in *Discover Computing* presents a Geth-based real-time detection system for both single-token and **multi-token** sandwich attacks (the research gap was that prior methods missed multi-token variants)
- Detection involves pattern matching on transaction sequences within blocks: frontrun tx + victim tx + backrun tx from same attacker address or contract
- **Cross-chain sandwich attacks** (August-October 2025 Symbiosis protocol data): 21.4% profit rate vs 0.8% for single-chain MEV — researchers applied heuristic detection models to 2 months of cross-chain data

**Practical Detection Signals:**
- Transaction ordering anomalies within a block (two transactions bracketing a victim's swap)
- Gas price signature: attacker front-run has gas price precisely 1 wei higher than victim
- Recurring bot addresses (EigenPhi and Arkham track known MEV bots)
- Unusual pool price movement within a single block (pre- and post-victim trade price)

### Protection Strategies (2025 Best Practices)

| Method | Protection Level | How It Works |
|--------|-----------------|--------------|
| **Flashbots Protect RPC** | High (sandwich-specific) | Routes transactions through private mempool, invisible to public |
| **CoW Protocol batch auctions** | Very High | Settles in 10-minute batch auctions; eliminates priority gas wars; max 0.5% slippage |
| **MEV Blocker** | High | Sends transactions to >25 searchers who compete to give user best execution |
| **1inch Fusion** | High | Dutch auction mechanism — no upfront price commitment |
| **Encrypted mempools (commit-reveal)** | Very High (experimental) | Transactions encrypted until committed; prevents mempool visibility |
| **Low slippage tolerance** | Moderate | Makes sandwich unprofitable (no room for attacker profit) |

**Flashbots Protect by the numbers (2025):**
- 2.1 million unique Ethereum accounts protected
- $43 billion in DEX volume protected
- 313 ETH in MEV refunds returned to users
- 95%+ sandwich attack prevention rate

**Encrypted mempools** using commit-reveal schemes offer theoretical 95%+ protection but add latency and complexity. A December 2025 EIP formalized encrypted mempool specifications.

---

## Section 4: DEX Arbitrage via MEV — Profitability After Gas and Builder Fees

### Mechanism

**Cyclic DEX arbitrage**: Exploit price discrepancies between AMM pools. Example: ETH priced differently on Uniswap vs. SushiSwap — buy on cheaper, sell on more expensive, atomic transaction.

**CEX-DEX arbitrage**: When a CEX price moves first (e.g., Coinbase), arbitrageurs race to update DEX prices. This is the dominant form of profitable arbitrage in 2025.

### Revenue and Profitability (2025)

| Metric | Value |
|--------|-------|
| CEX-DEX arb revenue (Aug 2023 - Mar 2025) | $233.8M (19 major searchers) |
| Arbitrage profit, September 2025 (30-day) | $3.37M |
| Gas consumption per complex arb strategy | 200,000 to 1,000,000 gas units |
| Percentage of arb revenue paid to validators | >90% for many searchers |
| Searcher net retention (top firms) | 10-15% of gross |

### The Profitability Squeeze

The critical finding from a 2025 paper ("Measuring CEX-DEX Extracted Value and Searcher Profitability," arXiv:2507.13023):
- Searchers like SCP and Wintermute **transfer nearly 90% of revenue to integrated builders**
- "Builders may retain some margin upon winning the block"
- Net result: a $1M gross arbitrage opportunity might yield $100K-$150K to the searcher

**L2 and Optimistic MEV (2025):**
- Optimistic MEV consumed >50% of on-chain gas on Base and Optimism in Q1 2025
- But paid <25% of total fees — extreme capital efficiency advantage
- L2 MEV is an emerging frontier where competition is lower and margins potentially higher

### Technical Requirements

- High-performance Ethereum/Solana full node (preferably a dedicated RPC node)
- Sub-millisecond orderflow processing pipeline
- Smart contract deployment for atomic execution (single transaction, multi-pool)
- Gas price optimization engine (EIP-1559 priority fee calculation)
- Flashbots bundle submission integration
- CEX price feeds with sub-100ms latency for CEX-DEX arb
- Capital: $50K minimum to be competitive; $1M+ for meaningful opportunity sizing

---

## Section 5: Liquidation Bot Opportunities — DeFi Lending Protocol Liquidations

### Mechanism

DeFi lending protocols (Aave, Compound, MakerDAO) require over-collateralization. When a position falls below the liquidation threshold (health factor <1 on Aave), any external actor can trigger liquidation and receive a **liquidation bonus** as reward.

Aave liquidation bonuses by asset class:
- USDC, DAI, ETH: **5% bonus** on liquidated collateral
- WBTC: **5-7.5%**
- Riskier assets (MANA, YFI): **10-15%**

### Historical Revenue

- **$2.5 billion** in collateral liquidated on Aave and Compound throughout their history (as of 2025)
- **$150 million** in liquidation incentives paid to liquidators (some leaked to miners as gas)
- November 2023 - January 2024: ~$42M of collateral liquidated, $1.9M in premiums (4.5% average)
- June 2025: Aave hit record $44B TVL — larger pool = larger potential liquidation events

### Profitability Requirements

A profitable liquidation requires: **liquidation bonus > gas fees + builder payment**

This threshold becomes challenging during:
1. High network congestion (gas spikes)
2. Small position sizes (low bonus absolute value)
3. Multiple competing bots (gas price war raises costs)

Incorporating transaction fees and MEV-driven sandwiching of liquidation events, **profitability eventually becomes negative beyond a critical fee threshold**.

### 2025 Developments: Oracle-Based Liquidation Capture

- Chainlink's **Smart Value Recapture (SVR)** covered ~75% of Aave's total Ethereum TVL by early 2025
- SVR recapture rates above **80%** — returning value that previously leaked to MEV bots back to the protocol
- Pyth Network analysis confirmed "value leakage and fragmentation" in traditional liquidations; oracle solutions now capture >90% of value that would otherwise leak

**What this means for liquidation bots:** Oracle-integrated protocols are systematically capturing value away from external liquidation bots. The opportunity window is shrinking for traditional liquidation MEV as protocols internalize this value.

### Current Opportunity Assessment

| Factor | Assessment |
|--------|-----------|
| Gross revenue potential | Still significant during volatile markets (price crashes create cascades) |
| Net profitability | Squeezed by gas, competition, and protocol improvements |
| Capital requirement | $50K-$500K (must hold enough to execute large liquidations) |
| Technical barrier | Medium (requires health factor monitoring, gas optimization) |
| Trend | Declining as protocols improve oracle integrations |

---

## Section 6: MEV on Solana — Jito and MEV Extraction Outside Ethereum

### Solana's Unique MEV Architecture

Solana does not have a traditional mempool. Transactions are streamed directly to validators via Gulf Stream. This theoretically eliminates traditional frontrunning — but creates different MEV vectors.

**Jito Labs** is the dominant MEV infrastructure provider on Solana:
- **94% market share** among Solana validators by Q2 2025
- **Block Engine** charges 6% fee on all MEV rewards
- Revenue projection: ~$4.7M in Q3 2025 alone (~$19M annualized post-JIP-24)
- Added staking yield: MEV boosts validator APY by 20-30% (from ~6% base to ~7.2-7.8%)

### Jito's Bundle Mechanism

Jito Bundles are groups of transactions executed atomically, sold via an auction-based marketplace:
- Searchers bid tips (in SOL) for bundle inclusion
- Block Engine selects highest-tip bundles for each leader slot
- Validators receive tips on top of standard block rewards

### The Sandwich Attack Crisis on Solana

Jito shut down its **public mempool in March 2024** specifically because it enabled rampant sandwich attacks. Despite this:
- Sandwich bots pivoted to "**wide sandwiches**" — front-run and back-run NOT in the same block
- 93% of attacks came from wide sandwich variants after the public mempool shutdown
- 30,000 to 60,000 SOL extracted per month via wide sandwiches; record of **87,000 SOL in January 2025**
- Over 500K instances of sandwich attacks resulting in **$7.7M+ in losses** for victims

**Enforcement Actions:**
- Jito banned 15+ validators from receiving JitoSOL delegation after on-chain data exposed MEV abuse
- Solana Foundation ousted **30+ validators** for enabling sandwich MEV (2024)
- Marinade Finance blacklisted **50+ validators** using on-chain analysis and Ghostlogs tools

### Solana vs. Ethereum MEV Comparison

| Dimension | Ethereum | Solana |
|-----------|----------|--------|
| MEV infrastructure | MEV-Boost (mature) | Jito (growing, 94% share) |
| Sandwich attack severity | Declining (private mempools) | Still severe ($370M-$500M extracted 16 months) |
| Arbitrage dominance | CEX-DEX arb primary | Cross-DEX arb + sandwich |
| Cross-chain MEV profit rate | ~0.8% | ~21.4% (cross-chain) |
| Regulatory scrutiny | ESMA July 2025 report | Less formal, but foundation enforcement |

---

## Section 7: MEV Impact on Crypto Prices — Does MEV Activity Predict Volatility?

### Established Correlations

Research documents that MEV activity correlates with broader market conditions:

**MEV count correlates with:**
- ETH spot price volatility (higher volatility = more MEV opportunity)
- Retail trading activity on DEXes (more victims = more MEV)
- DEX aggregator usage volume
- Network congestion (gas prices spike during high MEV periods)

**The causal relationship is bidirectional:**
- Market volatility creates MEV opportunities (price gaps widen, arbitrage windows open)
- MEV activity itself can amplify price volatility (cascading sandwich attacks move prices; liquidation cascades create further price falls)

### Sandwich Attacks and Price Impact

- MEV bots continuously calculate profit margins based on trade size, slippage settings, and pool liquidity depth
- Tokens with lower liquidity are more vulnerable — less capital required to create profitable price impact
- Large sandwich attacks materially move prices: one Uniswap V3 stablecoin swap victim lost $215,000 in a single March 2025 attack — the price impact was substantial enough to move the pool price

### Liquidation Cascades as Price Predictors

From `KIMI_RISEOFTHECLAW/crypto_acceleration_engine.py` (our own codebase):
- Liquidation cascades are detectable as **volume spikes >3x average combined with price recovery patterns**
- These events are predictable: positions near liquidation thresholds can be identified from on-chain health factor data
- A Binance Futures API already provides liquidation data that acts as a leading indicator for price moves

**Academic finding (arXiv:2602.12104):** "Liquidation Dynamics in DeFi and the Role of Transaction Fees" — liquidation events follow predictable patterns tied to collateralization ratios; monitoring health factors across large DeFi positions provides advance warning of potential cascade events.

### ESMA's Market Integrity Assessment

ESMA's July 2025 paper explicitly states: "MEV creates detriment to DeFi users to the extent that profits accrued to MEV extractors come in deduction to the wealth of users." This is regulatory confirmation that MEV is a systematic tax on market participants.

From a market impact perspective:
- Cryptocurrency price shocks generate positive financial market spillovers: **18% of equity** and **27% of commodity** price fluctuations are linked to crypto shocks (2024-2025 research)
- MEV, as a component of crypto market microstructure, contributes to these dynamics

### Summary: MEV as a Volatility Signal

| MEV Signal | Relationship to Volatility |
|-----------|--------------------------|
| Arbitrage volume spike | Lagging indicator of volatility (arises after price movement) |
| Sandwich attack frequency | Concurrent indicator (high activity during high DEX volume) |
| Gas price spike | Leading/concurrent indicator (anticipates block congestion) |
| Liquidation event count | Leading indicator of further price drops (cascade risk) |
| Builder revenue increase | Concurrent indicator of high MEV opportunity environment |

---

## Section 8: Ethical MEV — Arbitrage and Liquidation vs. Sandwiching

### The Ethical Taxonomy

MEV exists on a spectrum from clearly beneficial to clearly predatory:

**Tier 1: BENEFICIAL (Market-Stabilizing)**

*DEX Arbitrage:*
- Ensures price consistency across DEX pools
- Benefits all users by improving price discovery
- Does not directly harm any counterparty
- ESMA and Ethereum Foundation both classify this as benign

*Protocol Liquidations:*
- Ensures DeFi lending protocols remain solvent
- Protects lenders from bad debt
- Required for protocol health — without liquidators, protocols fail
- The borrower agreed to liquidation terms when taking the position

**Tier 2: GRAY AREA (Extractive but Not Targeting Users)**

*Backrunning:*
- Submitting a transaction immediately after another to capture residual arbitrage
- Does not change the victim's outcome
- Extracts value from the market rather than from a specific user

*Cross-exchange arbitrage (CEX-DEX):*
- Exploits latency advantages
- May disadvantage liquidity providers on DEXes who provide stale prices
- Ongoing academic debate about net market impact

**Tier 3: PREDATORY (Directly Harms Users)**

*Sandwich attacks:*
- Directly increases user's effective price impact (they pay more, receive less)
- Transfers wealth from retail users to bots
- No market efficiency benefit — purely redistributive (harmful redistribution)
- ESMA: "Goes against principles of fairness and integrity"

*Front-running:*
- Exploits information asymmetry from mempool visibility
- Analogous to illegal insider trading in traditional finance
- EU MiCA guidelines (April 2025) explicitly address front-running as potential market abuse

### Quantitative Comparison (Ethereum, 2025)

| MEV Type | Monthly Revenue (2025) | Ethical Classification |
|----------|----------------------|----------------------|
| Arbitrage | $1.72 million (30-day) | Beneficial |
| Liquidations | Variable (spike during crashes) | Beneficial |
| Sandwich attacks | $740K (30-day, October 2025) | Predatory |

**Key shift:** On Ethereum, arbitrage now significantly outpaces sandwich attack revenue ($1.72M vs $740K). Sandwich attacks have declined due to private mempools. On Solana, sandwiches remain dominant and harmful.

### Regulatory Trajectory

- **MiCA (EU):** April 2025 final guidelines address MEV-related market abuse; NCAs instructed to identify and address MEV practices
- **ESMA July 2025:** Formal recommendation for "adequate solutions to address negative consequences of MEV"
- **Trend:** Regulatory pressure is increasing; harmful MEV practices face growing legal risk in EU jurisdictions

---

## Section 9: MEV as a Feature for ML Models — Can MEV Activity Predict Market Moves?

### Current State of Research

No published academic paper (as of February 2026) has specifically used MEV activity metrics as input features in a crypto price prediction model. This represents a genuine research gap and potential alpha.

However, indirect evidence strongly suggests MEV metrics are informative:

**From ESMA (July 2025):**
> "MEV count relates to ETH volatility, retail trading activity, and DEX aggregator usage"

This is the most direct statement from regulators confirming that MEV metrics carry information about market state.

### Proposed MEV Feature Set for ML Models

Based on synthesizing the research, here are the MEV-derived features with highest predictive potential:

**Class A: High Confidence Features (Directly Observable)**

| Feature | Data Source | Prediction Target | Rationale |
|---------|------------|-------------------|-----------|
| `arbitrage_tx_count_1h` | EigenPhi API, Zeromev | Volatility, price gap | High arb activity signals price discrepancy/movement |
| `sandwich_attack_count_1h` | EigenPhi, Arkham | DEX sentiment, user risk | High sandwich rate signals heavy retail DEX activity |
| `gas_price_priority_fee` | Ethereum RPC, Etherscan | Congestion, urgency | Spike precedes high-activity/volatility periods |
| `liquidation_count_4h` | Aave liquidation events | Price drop continuation | Cascades predict further downside |
| `mev_revenue_per_block` | Flashbots MEV-Boost relay | Builder revenue = market heat | High revenue = high volatility environment |
| `builder_revenue_24h` | Flashbots relay data | Market activity level | Revenue correlates with total on-chain activity |

**Class B: Moderate Confidence Features**

| Feature | Data Source | Prediction Target | Rationale |
|---------|------------|-------------------|-----------|
| `jito_tip_volume_1h` (Solana) | Jito Block Engine API | SOL volatility | High tips = competitive MEV = high opportunity environment |
| `sandwich_victim_loss_rate` | EigenPhi | DEX slippage environment | High losses = low liquidity conditions |
| `private_tx_ratio` | Flashbots relay API | Market transparency | Increase in private flow signals institutional activity |
| `cex_dex_arb_gap` | CEX prices vs DEX prices | Short-term price reversion | Gap size predicts arb closing move |
| `dex_pool_rebalance_frequency` | Uniswap v3 subgraph | Pool stress, volatility | High rebalancing = high price movement environment |

**Class C: Experimental Features**

| Feature | Data Source | Prediction Target | Notes |
|---------|------------|-------------------|-------|
| `cross_chain_mev_activity` | Bridge transaction data | Cross-chain flow | Emerging cross-chain sandwich data (2025 research) |
| `mev_bot_concentration` | On-chain analysis | Market microstructure health | Higher concentration = less efficient market |
| `flashbots_protect_volume` | Flashbots public data | Retail activity proxy | More protected users = higher retail participation |

### Specific ML Integration Strategies

**Strategy 1: MEV Regime Classifier**
- Label market regimes as "High MEV / Low MEV" based on 24-hour rolling arbitrage + sandwich volumes
- Use regime as a contextual feature or regime-switching prior for existing models
- Expected benefit: Better-calibrated position sizing during high-MEV regimes (higher volatility)

**Strategy 2: Liquidation Cascade Early Warning**
- Aggregate on-chain health factors from Aave/Compound for large positions
- Predict probability of cascade in next 4-hour window
- Use as negative momentum signal (high cascade probability = bearish short-term)
- Note: Our `crypto_acceleration_engine.py` already does a proxy version of this

**Strategy 3: Gas Price as Sentiment Indicator**
- Gas price spikes (especially priority fee spikes) precede high-activity periods
- Create a "gas urgency index" normalized by 30-day average
- Use as volatility expansion feature

**Strategy 4: CEX-DEX Arbitrage Gap Monitor**
- Monitor price difference between Binance/Coinbase prices and Uniswap/Curve prices in real time
- Large persistent gaps signal latency advantage exploitation; resolution direction predicts short-term DEX price movement
- This is executable within the existing system architecture

### Estimated Predictive Value

Based on ESMA's finding that MEV count "relates to ETH volatility" and the empirical data on MEV-volatility correlations:
- MEV features are likely to add **5-15% improvement** in volatility prediction models as supplementary features
- They are unlikely to be primary predictors (market fundamentals dominate)
- Best use: **Feature enrichment for microstructure-based models** and **regime detection**

---

## Section 10: Private Transaction Pools — Protecting Trades from MEV

### The Problem: Mempool Transparency

Public Ethereum mempool transactions are visible to anyone running a full node before they are included in a block. This ~12-second (one slot) visibility window is sufficient for MEV bots to:
1. Analyze the transaction
2. Calculate profitability
3. Submit a competing bundle via Flashbots

### Current Private Transaction Infrastructure (2025)

**Flashbots Protect:**
- Routes user transactions through private mempool
- Transactions only included if they won't revert (saves gas on failed transactions)
- Returns MEV refunds to users
- 2.1M unique users, $43B in volume protected, 313 ETH returned
- 2025 upgrade: Running infrastructure in **Trusted Execution Environments (TEEs)** — operators cannot view sensitive transaction data or tamper with software
- Quick Start: Change MetaMask RPC to `https://rpc.flashbots.net`

**CoW Protocol:**
- Batch auction mechanism: aggregates orders and settles every 10 minutes
- Eliminates priority gas auction (no frontrunning possible)
- Maximum slippage capped at 0.5%
- Solver-based execution: professional solvers compete to find best execution, not to frontrun

**MEV Blocker:**
- Sends transactions to 25+ competing searchers
- Searchers must give user best execution to get the orderflow
- Creates competitive pressure that benefits users rather than exploiting them

**1inch Fusion:**
- Dutch auction mechanism for swap orders
- Users set minimum acceptable price; Dutch auction finds clearing price
- Eliminates fixed-price commitment that enables sandwiching

**Encrypted Mempool (December 2025 EIP):**
- Commit-reveal scheme: users submit encrypted transactions
- Transactions only decrypt after block commitment
- Provides 95%+ sandwich protection theoretically
- Status: EIP formalized December 2025; implementations in progress
- Limitation: Adds latency; introduces new complexity vectors

### Jito on Solana

- Jito shut down public mempool in March 2024 (to reduce sandwich attacks)
- Transactions now route through Jito's Block Engine directly
- However, "wide sandwiches" (cross-block) circumvented this protection
- Private bundle submission now preferred: bundle → Jito → leader validator

### Practical Guidance for Our System

Since our system generates signals but does not execute on-chain trades directly, MEV protection for **execution** would be the responsibility of the trading infrastructure implementing our signals. If on-chain DEX execution is ever added:
1. Always use Flashbots Protect RPC or equivalent
2. Set minimum slippage tolerance to limit sandwich profitability
3. Consider CoW Protocol for large DEX orders
4. Never submit large AMM trades to public mempool

---

## Section 11: MEV Type Summary — Quick Reference

### MEV Type: DEX Arbitrage (Cyclic/CEX-DEX)

| Dimension | Details |
|-----------|---------|
| **Mechanism** | Exploit price discrepancies between AMM pools or CEX/DEX price gaps atomically |
| **Monthly Revenue (Ethereum 2025)** | ~$1.72M (30-day September 2025) |
| **Technical Requirements** | Full node, Flashbots integration, smart contract router, CEX price feed (<100ms) |
| **ML Prediction Opportunity** | CEX-DEX gap as feature; arb volume as volatility regime indicator |
| **Ethical Classification** | Beneficial — improves price efficiency |
| **Trend** | Competitive saturation; L2 arb emerging as new frontier |

### MEV Type: Sandwich Attacks

| Dimension | Details |
|-----------|---------|
| **Mechanism** | Front-run victim's DEX swap, let victim trade (moving price), back-run to close |
| **Monthly Revenue (Ethereum 2025)** | ~$740K gross, ~$260K net after gas |
| **Technical Requirements** | Mempool monitoring, gas price auction, flash loan capital |
| **ML Prediction Opportunity** | Sandwich count = retail DEX activity indicator; victim loss rate = slippage environment |
| **Ethical Classification** | Predatory — directly harms users |
| **Trend** | Declining on Ethereum; rampant on Solana despite enforcement |

### MEV Type: Liquidation Capture

| Dimension | Details |
|-----------|---------|
| **Mechanism** | Monitor DeFi health factors; execute liquidation when position breaches threshold |
| **Historical Revenue** | ~$150M in total incentives paid (Aave + Compound lifetime) |
| **Technical Requirements** | DeFi protocol monitoring, flash loan access (for large liquidations), gas optimization |
| **ML Prediction Opportunity** | Health factor aggregates predict cascade probability; cascade events predict price drops |
| **Ethical Classification** | Beneficial — maintains protocol solvency |
| **Trend** | Declining as oracle solutions (Chainlink SVR) internalize this value |

### MEV Type: Jito MEV on Solana

| Dimension | Details |
|-----------|---------|
| **Mechanism** | Bundle-based transaction ordering auctions via Jito Block Engine |
| **Revenue** | $4.7M/quarter (Q3 2025 Block Engine alone); validators earn +20-30% APY |
| **Technical Requirements** | Jito searcher account, SOL tip capital, bundle construction |
| **ML Prediction Opportunity** | Jito tip volume = SOL market activity level; can proxy for volatility |
| **Ethical Classification** | Architecture is neutral; enables both arbitrage (beneficial) and sandwiches (predatory) |
| **Trend** | Growing rapidly; 94% validator adoption; regulatory pressure increasing |

---

## Top 5 Recommendations for Our System

### Preamble: Our System Position

Our system is a **signal engine**, not an MEV bot. We observe market microstructure data, generate BUY/SELL signals with TP/SL targets, and do not execute on-chain transactions. This is the correct strategic positioning. Here is whether and how MEV activity should inform our models:

---

### Recommendation 1: ADD MEV-Adjacent Features to Microstructure Models (HIGH PRIORITY)

**Should we do this? YES — immediately actionable with existing infrastructure.**

The ESMA July 2025 report confirmed: "MEV count relates to ETH volatility, retail trading activity, and DEX aggregator usage." This is the clearest evidence that MEV metrics carry market information.

**Specific additions to `microstructure_features_integration.py`:**

```python
# Add to existing feature pipeline (60-second update loop is fine for these)
mev_features = {
    "arb_tx_count_1h": fetch_eigenphi_arbitrage_count(),       # EigenPhi public API
    "gas_priority_fee_gwei": fetch_eth_priority_fee(),          # Infura/Alchemy free tier
    "sandwich_count_24h": fetch_eigenphi_sandwich_count(),      # EigenPhi public API
    "jito_tip_volume_sol": fetch_jito_tip_stats(),              # Jito public API
    "aave_liquidation_count_4h": fetch_aave_liquidations(),     # Aave subgraph (free)
}
```

**Expected benefit:** Better-calibrated signals during high-volatility regimes; liquidation count as leading indicator for downside continuation.

---

### Recommendation 2: USE Liquidation Cascade Count as a Bearish Momentum Feature (HIGH PRIORITY)

**Should we do this? YES — strongest MEV-adjacent signal with clear directional prediction.**

Liquidation cascades have a documented causal relationship with price drops:
1. Price drops → positions hit liquidation threshold
2. Liquidation bots execute → forced selling increases price drop
3. New positions hit threshold → cascade

**Integration with existing code:** Our `crypto_acceleration_engine.py` already has `fetch_binance_liquidations()` as a proxy. Upgrade to use Aave's GraphQL subgraph for actual health factor data. Feature: `positions_near_liquidation_threshold_usd` (positions within 5% of liquidation price, total USD).

**Signal rule:** When `positions_near_liquidation_threshold_usd` crosses $500M+, add a bearish bias modifier to existing signals.

---

### Recommendation 3: BUILD a Gas Price Urgency Index as a Volatility Leading Indicator (MEDIUM PRIORITY)

**Should we do this? YES — free data, clear interpretation.**

Gas price spikes on Ethereum precede high-activity periods. The priority fee (tip) component of EIP-1559 gas is particularly signal-rich because it reflects how urgently actors want their transactions included.

**Proposed index:**
```python
gas_urgency_index = current_priority_fee_gwei / rolling_30d_mean_priority_fee_gwei
# > 2.0: High urgency environment → expect volatility expansion
# < 0.5: Low urgency environment → sideways or accumulation
```

**Data source:** Ethereum RPC `eth_maxPriorityFeePerGas` (free, available on any Infura/Alchemy endpoint). This requires no MEV infrastructure at all.

---

### Recommendation 4: MONITOR CEX-DEX Arbitrage Gaps for Short-Term Price Reversion Signals (MEDIUM PRIORITY)

**Should we do this? YES — this extends existing cross-exchange strategy.**

Our existing cross-exchange spread detection (Strategy 54 in `event_strategies.py`) monitors spot vs. futures basis on Binance. Extending this to monitor CEX spot price vs. Uniswap V3 pool price gives a view into the MEV arbitrage opportunity currently available.

**Logic:**
- Large CEX-DEX gap = MEV bots are actively closing it = DEX price will move toward CEX price
- Direction of gap = direction of expected DEX price move
- Gap closure speed = a measure of MEV competition intensity in real time

**Implementation approach:** Compare Coinbase BTC spot price vs. Uniswap WBTC/ETH pool implied BTC price. When gap >0.3%, flag expected reversion within the next 1-5 minutes.

---

### Recommendation 5: DO NOT Build or Extend MEV Extraction Capabilities (MAINTAIN CURRENT POSITION)

**Should we add MEV extraction? NO — for multiple reinforcing reasons:**

1. **Competition is decisive:** 80% of MEV captured by 5 entities; 30% of active sandwich bots run at a loss; searchers pay 90%+ of revenue to block builders. New entrants face an insurmountable disadvantage.

2. **Regulatory risk is rising:** ESMA July 2025 formally identified MEV as a market integrity concern; MiCA guidelines explicitly address front-running. Sandwich attacks in the EU now face potential market abuse classification. Legal risk is material.

3. **Technical gap is enormous:** Real MEV extraction requires sub-100ms execution infrastructure, Ethereum full nodes, Flashbots relay integration, and smart contract deployment. Our current 60-second feature update loop is 600x too slow.

4. **Ethical alignment:** Our system's value proposition is generating insight for traders, not extracting from them. Sandwich attacks would directly contradict this mission and risk reputational damage.

5. **Opportunity cost:** The engineering effort required to build MEV infrastructure would far exceed the returns given the competitive landscape. That effort is better applied to improving our signal models.

**The optimal position:** Observe and learn from MEV activity as a market signal without participating in extraction. This is exactly what our current architecture achieves.

---

## Final Assessment: MEV Activity as a Prediction Feature

**Bottom line:** MEV activity metrics are **valuable secondary features** for ML models, particularly for:

1. **Volatility regime detection** (high MEV = high volatility environment)
2. **Short-term price direction on DEXes** (CEX-DEX gap predicts reversion)
3. **Downside cascade risk** (liquidation counts predict continuation)
4. **Market microstructure health** (sandwich/arbitrage ratio indicates retail vs. institutional activity)

They are NOT standalone predictive signals — they are enrichment features that improve the calibration of existing models. Incorporating 3-5 MEV-adjacent features into the existing `microstructure_features_integration.py` pipeline is the recommended first step, at zero additional infrastructure cost (all data sources are publicly available APIs).

---

## References and Sources

- [ESMA: Maximal Extractable Value Implications for Crypto Markets (July 2025)](https://www.esma.europa.eu/sites/default/files/2025-07/ESMA50-481369926-29744_Maximal_Extractable_Value_Implications_for_crypto_markets.pdf)
- [Extropy: An Analysis of Arbitrage Markets Across Ethereum, Solana (2025)](https://academy.extropy.io/pages/articles/mev-crosschain-analysis-2025.html)
- [Flashbots: MEV-Boost Architecture Overview](https://docs.flashbots.net/flashbots-mev-boost/architecture-overview/specifications)
- [Flashbots: BuilderNet announcement and BuilderNet v1.2 (2025)](https://blockworks.co/news/flashbots-block-building-network-mev)
- [Flashbots Protect: 2 Million Users milestone](https://writings.flashbots.net/2m-protect-users)
- [Springer/Discover Computing: Real-time detection system for multi-token sandwich attacks (2025)](https://link.springer.com/article/10.1007/s10791-025-09694-z)
- [arXiv 2511.15245: Cross-Chain Sandwich Attacks in DeFi (August-October 2025 data)](https://arxiv.org/html/2511.15245v1)
- [Ancilar/Medium: Implementing Effective MEV Protection in 2025](https://medium.com/@ancilartech/implementing-effective-mev-protection-in-2025-c8a65570be3a)
- [arXiv 2507.13023: Measuring CEX-DEX Extracted Value and Searcher Profitability](https://arxiv.org/html/2507.13023v1)
- [arXiv 2602.12104: Liquidation Dynamics in DeFi and the Role of Transaction Fees](https://arxiv.org/html/2602.12104)
- [Pyth Network: Value Leakage and Fragmentation in Liquidations](https://www.pyth.network/blog/value-leakage-and-fragmentation-in-liquidations)
- [Jito Labs: Validators page and MEV economics](https://www.jito.wtf/validators/)
- [Tokenomics.com: Jito Tokenomics — How JTO Captures MEV](https://tokenomics.com/articles/jito-tokenomics-how-jto-captures-mev-and-staking-revenue-on-solana)
- [Solana Compass: Solana MEV Exposed — Sandwich Attacks, Arbitrage, Validator Behavior (Accelerate 2025)](https://solanacompass.com/learn/accelerate-25/scale-or-die-at-accelerate-2025-the-state-of-solana-mev)
- [Cryptopolitan: Jito bans 15 additional validators for sandwich attacks](https://www.cryptopolitan.com/jito-bans-15-additional-validators-after-data-emerges-of-widespread-sandwich-attacks/)
- [ACM IMC 2025: Quantifying the Threat of Sandwiching MEV on Jito](https://dl.acm.org/doi/10.1145/3730567.3764493)
- [EigenPhi: Daily MEV Data Reports](https://eigenphi.io/mev/ethereum/dailyReport)
- [CoinTelegraph: Sandwich attacks on Ethereum have waned (EigenPhi exclusive data)](https://cointelegraph.com/news/exclusive-data-from-eigenphi-reveals-that-sandwich-attacks-on-ethereum-have-waned)
- [Flashbots: The Future of MEV is SUAVE](https://writings.flashbots.net/the-future-of-mev-is-suave)
- [Ethereum.org: Maximal Extractable Value documentation](https://ethereum.org/developers/docs/mev/)
- [AiCoin: Current Status Survey of MEV on Various Public Chains (2025)](https://www.aicoin.com/en/article/418971)
- [arXiv 2405.17944: Remeasuring Arbitrage and Sandwich Attacks of MEV in Ethereum](https://arxiv.org/html/2405.17944v2)
- [ScienceDirect: Linking MEV attacks to further maximize attackers gains (2025)](https://www.sciencedirect.com/science/article/pii/S2096720925000673)
- [FinanceFeeds: Top MEV Protection Tools in 2025](https://financefeeds.com/top-mev-protection-tools-in-2025/)
- [Encrypted Mempool EIP — December 2025](https://en.cryptonomist.ch/2025/12/17/encrypted-mempool-eip/)
- [arXiv 2506.14768: Optimistic MEV in Ethereum Layer 2s](https://arxiv.org/pdf/2506.14768)

---

*Researcher ID: 028 | Status: Complete — Full Web Research Edition*
*Compiled: February 24, 2026 | Role: Dr. Christopher Lee, MEV & Blockchain Extraction Specialist*
