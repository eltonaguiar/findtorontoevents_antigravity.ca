# Institutional Scalping Research Report
## How Major Firms Scalp Markets & What Retail Can Replicate

---

## 1. CITADEL SECURITIES - Market Making Scalping

### Overview
Citadel Securities handles ~35% of U.S. equity trading volume, moving approximately **$500 billion daily** across exchanges. Net trading revenue reached **$9.7 billion in 2024** with record net profit of **$4.2 billion**.

### Latency Requirements
- **Target:** Sub-microsecond to nanosecond execution times
- **Feed handling:** FPGA-accelerated market data decoding
- **Network:** Dedicated fiber/microwave links between venues
- **Co-location:** Direct proximity to exchange matching engines

### Technology Stack
| Component | Technology |
|-----------|------------|
| Primary Language | C++ (C++20/23, eyeing C++26) |
| Hardware Acceleration | FPGAs for critical path |
| CPUs | Intel Xeon / AMD EPYC (high clock speed) |
| GPUs | NVIDIA A100s for parallel processing |
| Storage | NVMe SSDs with terabytes of RAM |
| Networking | Custom kernel bypass (DPDK/RDMA) |

### Capital Requirements
- **Net trading capital:** $16 billion (end of 2024)
- **Minimum regulatory capital:** $20 million (excess of $300 million)
- **Infrastructure investment:** Hundreds of millions annually

### Profit Margins Per Trade
- **Typical spread capture:** $0.001 - $0.005 per share
- **Volume-based:** Profits from massive scale (billions of shares)
- **Maker rebates:** Additional $0.002-$0.003 per share on many venues
- **Net result:** Small margins × enormous volume = billions in profit

### Risk Management
- Real-time position monitoring across all venues
- Automatic position limit enforcement
- Kill switches for runaway strategies
- Cross-venue risk aggregation
- Pre-trade risk checks (<50 microseconds)

### Regulatory Constraints
- SEC/FINRA oversight for algorithmic trading
- Market Access Rule compliance
- Regular regulatory reporting
- Best execution obligations

---

## 2. JANE STREET - ETF Arbitrage Scalping

### Overview
Jane Street is a proprietary trading firm and market maker focusing on ETFs, options, bonds, and equities. In 2024, they achieved **$20.5 billion in net trading revenue** and averaged **$230 billion monthly** in fixed income trading volume.

### Latency Requirements
- **ETF creation/redemption:** Millisecond-level acceptable
- **Arbitrage detection:** Microsecond-level for competitive edge
- **Cross-market latency:** Minimized for international arbitrage

### Technology Stack
- **Primary Language:** OCaml (functional programming)
- **Data infrastructure:** Real-time pricing from yield curves, futures, swaps
- **Risk systems:** Integrated position tracking across asset classes
- **Custom hardware:** FPGA for latency-sensitive components

### Capital Requirements
- **Estimated trading capital:** $15+ billion
- **Balance sheet:** Massive inventory capacity for ETF creation units
- **Credit lines:** Extensive prime brokerage relationships

### Profit Margins Per Trade
- **ETF arbitrage:** $0.01-$0.10 per share typical
- **Options market making:** Premium decay capture
- **Basis trades:** Yield spread differentials (often small but consistent)
- **Scale:** 10% of US equity market volume in 2024

### Risk Management
- **Portfolio approach:** Treats ETFs as "structured risk bundles"
- **Hedging:** Automatic delta-neutral hedging
- **Position limits:** Strict by instrument and correlation
- **Stress testing:** Continuous scenario analysis

### Regulatory Constraints
- SEBI investigation (India) for alleged manipulation
- Multi-jurisdictional compliance (US, Europe, Asia)
- Position reporting requirements
- Market maker obligations on designated venues

---

## 3. JUMP TRADING - HFT Scalping Infrastructure

### Overview
Jump Trading is a pioneer in HFT since the early 2000s, operating at the intersection of technology and quantitative research. Known for being among the **fastest market participants**.

### Latency Requirements
- **Ultra-low latency:** Nanosecond-level execution
- **Microwave networks:** Between major trading centers (Chicago-NY)
- **Co-location:** Premium space at all major exchanges
- **FPGA tick-to-trade:** <100 nanoseconds for some strategies

### Technology Stack
| Component | Specification |
|-----------|---------------|
| FPGA | Custom-designed for trading logic |
| Network | Microwave + fiber redundancy |
| Software | C++ with kernel bypass |
| Data | Proprietary market data handlers |
| Hardware | Custom server designs |

### Capital Requirements
- **Estimated capital:** $5-10 billion
- **Infrastructure:** $100+ million annually in technology
- **Talent:** Top-tier compensation for elite developers

### Profit Margins Per Trade
- **Latency arbitrage:** $0.001-$0.01 per share
- **Statistical arbitrage:** Small edges from predictive models
- **Market making:** Spread capture + rebates
- **Crypto HFT:** Higher volatility = larger spreads

### Risk Management
- Real-time P&L monitoring
- Position limits by strategy
- Correlation risk controls
- Automated shutdown triggers

### Regulatory Constraints
- CFTC/SEC oversight
- Regular algorithmic trading reports
- Market manipulation surveillance
- Cross-border compliance

---

## 4. VIRTU FINANCIAL - 235+ Venue Scalping

### Overview
Virtu Financial operates across **235+ trading venues** in **50+ countries**, trading **25,000+ securities**. They are one of the largest liquidity providers globally.

### Latency Requirements
- **Multi-venue arbitrage:** Microsecond synchronization
- **Global connectivity:** Optimized routes to all venues
- **Smart order routing:** Real-time best execution analysis

### Technology Stack
- **Proprietary platform:** Single integrated system
- **Global network:** Low-latency connections worldwide
- **Analytics:** Real-time market structure analysis
- **Risk:** Centralized risk monitoring across all venues

### Capital Requirements
- **Public company:** $2+ billion market cap
- **Trading capital:** Significant but undisclosed
- **Technology spend:** Continuous heavy investment

### Profit Margins Per Trade
- **Per-venue spread capture:** $0.001-$0.005
- **Cross-venue arbitrage:** $0.01-$0.05
- **Volume:** Massive daily turnover across venues
- **Rebates:** Significant income from maker fees

### Risk Management
- **Centralized risk:** Single view across 235+ venues
- **Real-time monitoring:** Position tracking globally
- **Kill switches:** Venue-specific and global
- **Compliance:** Automated regulatory checks

### Regulatory Constraints
- Multi-jurisdictional compliance team
- Best execution reporting
- Market data licensing
- FINRA/SEC oversight

---

## 5. HUDSON RIVER TRADING (HRT) - ML-Based Scalping

### Overview
HRT is an algorithmic trading company where **models and code drive all trading decisions every nanosecond**. They have developed **transformer-based models** using decades of market microstructure data.

### Latency Requirements
- **AI inference:** Optimized for sub-microsecond predictions
- **Model deployment:** Real-time scoring of market conditions
- **Data ingestion:** High-throughput market data processing

### Technology Stack
| Component | Technology |
|-----------|------------|
| AI/ML | Transformer-based models |
| Compute | Massive GPU clusters for training |
| Inference | Optimized for low-latency deployment |
| Languages | Python (research), C++ (production) |
| Data | Decades of microstructure data |

### Capital Requirements
- **Private firm:** Estimated $5+ billion in capital
- **AI infrastructure:** Significant cloud/compute spend
- **Talent:** PhD-level researchers and engineers

### Profit Margins Per Trade
- **ML predictions:** Small edge from pattern recognition
- **Microstructure alpha:** Order flow prediction
- **Execution optimization:** Reduced market impact
- **Scale:** Hundreds of millions of shares daily

### Risk Management
- **Model risk:** Extensive backtesting and paper trading
- **Position controls:** AI-augmented risk monitoring
- **Regulatory compliance:** Automated checks
- **Model drift detection:** Continuous performance monitoring

### Regulatory Constraints
- Algorithmic trading regulations
- Model risk management requirements
- Market abuse surveillance
- Data privacy compliance

---

## 6. OPTIVER - Options Market Making Scalping

### Overview
Optiver is a leading global market maker using the **Avellaneda-Stoikov model** for market making. Generated **€3.5 billion trading revenue in 2024**.

### Latency Requirements
- **Options quoting:** Microsecond-level updates
- **Greek hedging:** Real-time delta/gamma management
- **Multi-leg execution:** Synchronized complex orders

### Technology Stack
- **Pricing Models:** Avellaneda-Stoikov framework
- **Risk Engine:** Real-time Greek calculations
- **Execution:** Smart order routing for options
- **Inventory Management:** Automated position balancing

### Capital Requirements
- **Trading capital:** Billions in inventory capacity
- **Margin requirements:** Significant for options positions
- **Technology:** Heavy investment in pricing infrastructure

### Profit Margins Per Trade
- **Spread capture:** $0.05-$0.50 per options contract
- **Rebates:** Exchange incentives for liquidity provision
- **Inventory management:** Theta decay capture
- **Volatility arbitrage:** VIX term structure trades

### Risk Management
- **Greek limits:** Delta, gamma, vega, theta controls
- **Scenario analysis:** Stress testing portfolios
- **Concentration limits:** By underlying and sector
- **Real-time P&L:** Continuous attribution

### Regulatory Constraints
- Options market maker obligations
- OCC margin requirements
- Exchange compliance
- MiFID II (Europe)

---

## INFRASTRUCTURE COSTS

### Co-Location Costs
| Exchange | Monthly Cost |
|----------|--------------|
| NYSE | $400-$2,000+ per rack unit |
| Nasdaq | $500-$2,500+ per rack unit |
| CME (Chicago) | $2,000-$5,000+ per rack |
| Full cabinet | $10,000-$25,000/month |
| Cross-connect | $300-$1,000/month per connection |

### FPGA Hardware Costs
| Component | Price Range |
|-----------|-------------|
| Entry-level FPGA | $2,000-$5,000 |
| Mid-range FPGA | $10,000-$30,000 |
| High-performance (AMD Alveo UL3422) | $70,000+ |
| Ultra-high-performance (UL3524) | $100,000+ |
| Custom FPGA development | $500,000-$2,000,000 |

### Data Feed Costs
| Feed Type | Monthly Cost |
|-----------|--------------|
| Basic retail data | $100-$500 |
| Professional equities | $1,000-$5,000 |
| Options data (OPRA) | $5,000-$15,000 |
| Futures (CME) | $1,000-$3,000 |
| Level 2 depth | $2,000-$10,000 |
| Proprietary HFT feeds | $10,000-$50,000+ |

### Exchange Fees (Maker-Taker Model)
| Venue | Maker Rebate | Taker Fee |
|-------|--------------|-----------|
| Nasdaq | $0.0029 | $0.0030 |
| NYSE | $0.0024 | $0.0028 |
| BATS | $0.0030 | $0.0030 |
| IEX | $0.0009 | $0.0009 |
| CME Futures | Varies | Varies |

---

## WHAT RETAIL CAN REALISTICALLY REPLICATE

### ✅ REPLICABLE STRATEGIES

#### 1. Market Making (Simplified)
- **Approach:** Quote around fair value on single venue
- **Tools:** Interactive Brokers, TastyTrade
- **Markets:** Options with wide spreads (less HFT competition)
- **Capital:** $25,000-$100,000
- **Expected returns:** 10-30% annually (with risk)

#### 2. Statistical Arbitrage (Slow Version)
- **Approach:** Mean reversion on correlated pairs
- **Timeframe:** Minutes to hours (not microseconds)
- **Tools:** Python, pandas, broker API
- **Capital:** $10,000-$50,000
- **Expected returns:** 15-40% annually

#### 3. Momentum Scalping
- **Approach:** Follow order flow on breakouts
- **Timeframe:** 1-5 minute charts
- **Tools:** TradingView, direct access broker
- **Capital:** $25,000+ (PDT rule)
- **Expected returns:** Variable, high risk

#### 4. ETF Arbitrage (Retail Version)
- **Approach:** Spot NAV deviations on liquid ETFs
- **Timeframe:** Intraday
- **Tools:** Real-time NAV data, broker API
- **Capital:** $50,000+
- **Expected returns:** 8-15% annually

### ❌ NOT REPLICABLE

| Institutional Capability | Why Retail Can't Match |
|--------------------------|------------------------|
| Nanosecond latency | Physics + cost barriers |
| 235+ venue access | Capital + connectivity costs |
| FPGA hardware | $100K+ per card + expertise |
| Co-location | $10K+/month minimum |
| Proprietary data feeds | $50K+/month licensing |
| Maker rebates at scale | Volume requirements |
| Cross-market arbitrage | Latency disadvantage |
| Order flow prediction | Data access limitations |

### PRACTICAL RETAIL SCALPING SETUP

#### Minimum Viable Infrastructure
```
Capital: $25,000-$50,000
Broker: Interactive Brokers Pro ($0.0035/share)
Platform: TradingView Pro+ ($60/month)
Data: Real-time Level 1 (included with broker)
Hardware: Standard PC with dual monitors
Internet: Reliable broadband (not latency-critical)
```

#### Recommended Retail Stack
```
Capital: $100,000+
Broker: Direct access (Lightspeed, CMEG)
Platform: Sterling Pro or DAS Trader
Data: Level 2 depth ($100-300/month)
Automation: Python + IB API or TradingView alerts
Hardware: Gaming PC with multiple monitors
```

### KEY PRINCIPLES RETAIL CAN ADOPT

1. **Risk Management**
   - Position limits (max 2-5% per trade)
   - Daily loss limits (stop trading after -2%)
   - Correlation awareness

2. **Discipline**
   - Pre-defined entry/exit rules
   - No emotional trading
   - Consistent position sizing

3. **Edge Development**
   - Focus on less competitive niches
   - Develop market-specific knowledge
   - Backtest strategies thoroughly

4. **Cost Control**
   - Minimize commissions (per-share pricing)
   - Avoid over-trading
   - Use limit orders when possible

### REALISTIC EXPECTATIONS

| Metric | Institutional | Realistic Retail |
|--------|---------------|------------------|
| Win rate | 55-65% | 50-60% |
| Profit per trade | $0.001-$0.01/share | $0.05-$0.25/share |
| Daily trades | 10,000-100,000 | 10-50 |
| Annual return target | 30-100% | 20-50% |
| Max drawdown | <5% | <15% |

---

## CONCLUSION

Institutional scalping operates on a completely different plane than retail trading. The combination of:
- **Nanosecond latency** ($ millions in infrastructure)
- **Massive scale** (billions in capital)
- **Proprietary technology** (FPGAs, microwave networks)
- **Regulatory advantages** (market maker status, rebates)

...creates an unbridgeable gap for individual traders.

**However**, retail traders can still profit by:
1. Operating in **less competitive niches** (small caps, options)
2. Using **longer timeframes** (minutes vs. microseconds)
3. Focusing on **information advantages** (earnings, news)
4. Maintaining **strict risk discipline**
5. Keeping **costs minimal**

The key insight: Don't compete with Citadel on speed. Compete on **timeframe**, **niche selection**, and **risk management**.

---

*Report compiled: February 2026*
*Sources: Public filings, industry reports, academic research*
