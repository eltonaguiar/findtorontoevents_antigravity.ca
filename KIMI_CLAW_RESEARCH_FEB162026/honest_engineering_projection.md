# Honest Engineering Projection: Quantitative Trading System

**Document Type:** Engineering Cost Analysis & Risk Assessment  
**Date:** February 2025  
**Classification:** Internal - No Marketing Claims Permitted

---

## Executive Summary (Reality Check)

The "$1M budget, $1M+ by Month 12" claim is **not grounded in engineering reality**. This document replaces aspirational business projections with actual costs, realistic timelines, and evidence-based risk assessments.

**Bottom Line:** A retail quantitative trading operation with $1M capital faces a **60-80% probability of net loss** within the first 12 months, even with competent execution.

---

## 1. Realistic Cost Breakdown

### 1.1 Data Subscriptions (Actual Market Prices)

| Data Source | Tier | Monthly Cost | Annual Cost | Notes |
|-------------|------|--------------|-------------|-------|
| **Polygon.io** | Stocks Starter (15-min delay) | $29 | $348 | Minimum viable for US equities |
| **Polygon.io** | Stocks Developer (real-time) | $79 | $948 | Required for intraday strategies |
| **Polygon.io** | Stocks Advanced | $199 | $2,388 | Full tick data, WebSocket streaming |
| **Alpaca** | Market Data API | $0 | $0 | Included with brokerage (limited) |
| **EODHD** | Fundamental Data | $29 | $348 | Financial statements, ratios |
| **RavenPack** | News Analytics | $500-2,000 | $6,000-24,000 | **Enterprise only** - no retail tier |
| **Bloomberg Terminal** | Professional | $2,000+ | $24,000+ | Institutional-grade (not realistic for $1M AUM) |
| **Refinitiv Eikon** | Standard | $1,500+ | $18,000+ | Institutional-grade |

**Realistic Retail Setup:**
- **Minimum:** Polygon Starter + Alpaca = ~$29/month ($348/year)
- **Recommended:** Polygon Developer + EODHD = ~$108/month ($1,296/year)
- **Professional:** Polygon Advanced + Alternative Data = ~$500-700/month ($6,000-8,400/year)

**Critical Reality:** Data costs scale with strategy complexity. A multi-factor strategy requiring:
- Real-time L1/L2 data: $200-500/month
- Alternative data (satellite, credit cards): $1,000-10,000/month (enterprise contracts only)
- Historical tick data (5+ years): $2,000-5,000 one-time or $300-500/month

### 1.2 API & Trading Costs

| Provider | Commission | API Fees | Notes |
|----------|------------|----------|-------|
| **Alpaca** | $0 (US equities) | $0 | Best for retail; limited to US markets |
| **Interactive Brokers** | $0.0035-0.005/share | $0 | Professional-grade; minimum $2,000/month activity |
| **TD Ameritrade/Schwab** | $0 | $0 | Limited API access; rate limits apply |
| **Tradier** | $0 | $10-30/month | Options-focused |

**Hidden Costs:**
- **Regulatory fees:** SEC fee ($8 per $1M sold), FINRA TAF ($0.000145/share)
- **Exchange fees:** $0.001-0.003/share for removing liquidity (market orders)
- **API rate limits:** Exceeding limits requires enterprise contracts ($500+/month)

**Monthly Trading Cost Estimate (assuming $1M volume/month):**
- Commissions: $0 (Alpaca/IBKR)
- Regulatory fees: ~$50-100
- Exchange fees: ~$100-300 (depending on order types)
- **Total: $150-400/month**

### 1.3 Infrastructure Costs (AWS)

#### Compute (EC2)

| Instance Type | vCPUs | RAM | Hourly Cost | Monthly (730 hrs) | Use Case |
|---------------|-------|-----|-------------|-------------------|----------|
| **t3.medium** | 2 | 4 GB | $0.0416 | $30.37 | Development, backtesting |
| **c6i.large** | 2 | 4 GB | $0.085 | $62.05 | Light production |
| **c6i.xlarge** | 4 | 8 GB | $0.17 | $124.10 | Production trading engine |
| **c6i.2xlarge** | 8 | 16 GB | $0.34 | $248.20 | Multi-strategy, ML workloads |
| **c7i.2xlarge** | 8 | 16 GB | $0.357 | $260.61 | 19% better price/perf vs c6i |

#### Storage (EBS)

| Type | Cost/GB-month | Use Case |
|------|---------------|----------|
| gp3 (SSD) | $0.08 | General purpose |
| io2 (Provisioned IOPS) | $0.125 + $0.065/IOPS | High-frequency data |

**Storage estimate:** 500GB-2TB for historical data = $40-160/month

#### Database (RDS/RDS-Free on EC2)

| Option | Monthly Cost | Notes |
|--------|--------------|-------|
| **PostgreSQL on EC2** | $0 (included) | Self-managed; backup responsibility |
| **RDS PostgreSQL (db.t3.micro)** | ~$15 | Managed; limited to 1-year free tier |
| **RDS PostgreSQL (db.t3.medium)** | ~$60 | Production-ready managed DB |
| **TimescaleDB (self-hosted)** | $0 | Time-series optimized; requires expertise |

#### Networking

| Service | Cost | Notes |
|---------|------|-------|
| Data Transfer Out | $0.09/GB | First 10TB/month |
| NAT Gateway | $0.045/hour + $0.045/GB | ~$35/month base + usage |
| Load Balancer | $0.0225/hour | ~$16/month base |

#### Realistic Infrastructure Setup

**Development Environment:**
- 1x t3.medium (dev/backtesting): $30/month
- 100GB gp3 storage: $8/month
- **Subtotal: ~$40/month**

**Production Environment (Minimal):**
- 1x c6i.xlarge (trading engine): $124/month
- 1x t3.medium (database): $30/month
- 500GB gp3 storage: $40/month
- NAT Gateway: $35/month
- Data transfer: $20/month
- **Subtotal: ~$250/month**

**Production Environment (Recommended):**
- 2x c6i.2xlarge (HA trading cluster): $500/month
- 1x RDS PostgreSQL (db.t3.medium): $60/month
- 1TB gp3 + 500GB io2: $120/month
- Load balancer + NAT: $60/month
- Monitoring (CloudWatch): $50/month
- **Subtotal: ~$800-1,000/month**

### 1.4 Development Time & Labor Costs

**Quantitative Developer Market Rates (2024-2025):**
- Junior Quant Dev: $65-85/hour ($130K-170K/year)
- Mid-level Quant Dev: $85-120/hour ($180K-250K/year)
- Senior Quant Dev: $120-180/hour ($250K-400K/year)
- Contract/Freelance: $100-200/hour

**Realistic Development Hours by Phase:**

| Phase | Hours | Rate | Cost | Notes |
|-------|-------|------|------|-------|
| **Architecture & Design** | 40-80 | $100/hr | $4,000-8,000 | System design, tech stack selection |
| **Data Pipeline** | 80-160 | $100/hr | $8,000-16,000 | ETL, data cleaning, storage |
| **Backtesting Engine** | 120-240 | $100/hr | $12,000-24,000 | Event-driven, realistic slippage |
| **Strategy Implementation** | 80-200 | $120/hr | $9,600-24,000 | Per strategy; highly variable |
| **Execution Engine** | 80-160 | $100/hr | $8,000-16,000 | Order management, risk controls |
| **Risk Management** | 60-120 | $120/hr | $7,200-14,400 | Position sizing, circuit breakers |
| **Monitoring & Alerting** | 40-80 | $100/hr | $4,000-8,000 | Dashboards, logging, alerts |
| **Testing & QA** | 80-160 | $80/hr | $6,400-12,800 | Unit tests, integration tests |
| **Documentation** | 40-80 | $80/hr | $3,200-6,400 | API docs, runbooks |

**Total Development Cost (Single Strategy):**
- **Minimum viable:** ~$50,000-75,000
- **Production-ready:** ~$100,000-150,000
- **Multi-strategy platform:** ~$200,000-400,000

### 1.5 Total Cost Summary (Year 1)

| Category | Conservative | Realistic | Professional |
|----------|--------------|-----------|--------------|
| Data Subscriptions | $1,000 | $3,000 | $12,000 |
| Trading/API Costs | $2,000 | $4,000 | $6,000 |
| Infrastructure | $3,000 | $6,000 | $12,000 |
| Development Labor | $75,000 | $125,000 | $250,000 |
| **Total Year 1** | **$81,000** | **$138,000** | **$280,000** |

**Note:** This does NOT include:
- Legal/compliance costs ($5,000-50,000)
- Accounting/audit ($2,000-10,000)
- Office/workspace ($0-24,000)
- Hardware (if not cloud-based) ($2,000-10,000)

---

## 2. Honest Timeline

### Week 1: What Can ACTUALLY Be Done

**Reality:** You will have a **development environment** and **data access**.

**Deliverables:**
- [ ] AWS/GCP account setup
- [ ] Polygon.io or Alpaca API keys
- [ ] Basic Python environment (pandas, numpy, backtrader/zipline)
- [ ] Historical data download (1-2 symbols, 1 year)
- [ ] **Simple** backtest of a moving average crossover strategy

**What You WON'T Have:**
- A working trading strategy
- Real-time data pipeline
- Risk management
- Paper trading
- Any edge whatsoever

**Hours Required:** 20-40 hours (experienced dev)

### Month 1: What's Realistic

**Reality:** You will have a **basic backtesting framework** and **1-2 simple strategies** tested on historical data.

**Deliverables:**
- [ ] Data pipeline for daily/weekly data
- [ ] 2-3 simple technical indicator strategies
- [ ] Basic backtesting with transaction cost modeling
- [ ] Initial performance metrics (Sharpe, max drawdown)
- [ ] **Critical:** First encounter with overfitting

**What You WON'T Have:**
- Live trading
- Realistic slippage/impact models
- Robust risk management
- Validated edge (backtest ≠ live)

**Expected Progress:**
- 50-100 backtests run
- 90%+ of strategies will show promising backtests
- 0 strategies ready for live trading

**Hours Required:** 120-200 hours

### Month 3: What's Achievable

**Reality:** You will have a **paper trading system** with **1 strategy** that survived initial robustness checks.

**Deliverables:**
- [ ] Event-driven backtester (not vectorized)
- [ ] Realistic market impact model
- [ ] Walk-forward analysis framework
- [ ] 1 strategy with out-of-sample validation
- [ ] Paper trading integration
- [ ] Basic risk management (position limits, stop losses)

**What You WON'T Have:**
- Live trading with real money
- Multiple uncorrelated strategies
- Sophisticated risk models
- Proven profitability

**Expected Progress:**
- 500+ backtests run
- 95% of strategies discarded (overfitting, curve-fitting)
- 1-3 strategies in paper trading
- **First reality check:** Paper results rarely match backtests

**Hours Required:** 300-500 hours

### Month 6: What's Probable (Not Aspirational)

**Reality:** You will have **1 strategy in live trading** with **small size** and **heavy monitoring**.

**Deliverables:**
- [ ] Live trading system (minimum viable)
- [ ] 1 strategy trading 10-20% of intended capital
- [ ] Real-time monitoring and alerting
- [ ] 3-6 months of paper trading results
- [ ] Risk management with circuit breakers

**Probable Outcomes:**
- **60% probability:** Strategy underperforms vs. backtest by 30-50%
- **30% probability:** Strategy breaks even or slightly profitable
- **10% probability:** Strategy meets or exceeds backtest expectations
- **25% probability:** Strategy is shut down due to unexpected behavior

**What You WON'T Have:**
- Consistent profitability
- Multiple strategies
- Full capital deployment
- Automated operation without oversight

**Hours Required:** 600-1,000 hours

### Month 12: Probable State

**Reality:** Most retail quant operations at this stage are either:

1. **Shut down** (40% probability): Strategy failed, capital lost, operation unprofitable
2. **Breakeven** (35% probability): Small gains offset by costs, still searching for edge
3. **Modestly profitable** (20% probability): 5-15% returns, barely worth the effort
4. **Actually profitable** (5% probability): 15%+ returns, ready to scale

**Expected Metrics (if still operating):**
- Number of live strategies: 1-2
- Deployed capital: 30-50% of $1M
- Annual return: -20% to +20% (high variance)
- Sharpe ratio: 0.5-1.0 (if profitable)
- Time to recovery from drawdown: 3-6 months

---

## 3. Realistic Return Projections

### 3.1 The Backtest Trap

**Industry Statistic:** Over 90% of strategies that appear profitable in backtests fail in live trading.

**Reasons:**
1. **Survivorship bias:** Backtests use current constituents, ignoring delisted companies
2. **Look-ahead bias:** Using information not available at the time of the trade
3. **Overfitting:** Optimizing parameters to historical noise
4. **Transaction costs:** Real slippage, spread, and impact exceed assumptions
5. **Market regime change:** Historical patterns don't repeat

### 3.2 Forward-Test Based Projections

**Conservative Estimates (based on academic research and industry data):**

| Metric | Conservative | Moderate | Optimistic |
|--------|--------------|----------|------------|
| **Annual Return** | -10% to +5% | 5-15% | 15-25% |
| **Sharpe Ratio** | 0.0-0.3 | 0.3-0.8 | 0.8-1.2 |
| **Max Drawdown** | 20-40% | 15-25% | 10-20% |
| **Win Rate** | 45-52% | 50-58% | 55-65% |
| **Profit Factor** | 0.9-1.1 | 1.1-1.3 | 1.3-1.6 |

**Reality Check:**
- Renaissance Technologies Medallion Fund: 39% annual return (after fees) - **unreplicable**
- Average hedge fund: 7-10% annual return
- Retail traders: 90% lose money within 1 year

### 3.3 Worst-Case Scenarios

**Scenario 1: Strategy Decay (40% probability)**
- Strategy works for 3-6 months, then stops
- Cause: Market regime change, alpha decay, crowding
- Loss: 10-30% of capital before detection

**Scenario 2: Overfitting Blowup (25% probability)**
- Backtest showed 30% annual returns
- Live trading: -20% in first 3 months
- Cause: Curve-fitting to historical noise
- Loss: 20-40% of capital

**Scenario 3: Technical Failure (10% probability)**
- API outage, data feed error, or bug causes bad trades
- Cause: Insufficient testing, lack of circuit breakers
- Loss: 5-20% in hours

**Scenario 4: Black Swan Event (5% probability)**
- Market crash, flash crash, or geopolitical event
- Cause: Unhedged exposure, correlation breakdown
- Loss: 30-50% of capital

### 3.4 Probability-Weighted Returns

| Outcome | Probability | Return | Weighted Return |
|---------|-------------|--------|-----------------|
| Significant Loss (-30%) | 25% | -$300K | -$75K |
| Moderate Loss (-10%) | 25% | -$100K | -$25K |
| Breakeven (0%) | 25% | $0 | $0 |
| Modest Gain (+10%) | 15% | +$100K | +$15K |
| Good Return (+20%) | 8% | +$200K | +$16K |
| Exceptional (+40%) | 2% | +$400K | +$8K |

**Expected Value: -$61,000 (Year 1)**

This does NOT include operational costs of $81K-280K.

---

## 4. Risk Disclosure

### 4.1 Probability of Losing Money

**Retail Quantitative Trading Statistics:**
- **90% of retail traders lose money** within 12 months
- **80% of algorithmic strategies** fail within 6 months of live trading
- **95% of backtested strategies** fail out-of-sample

**Specific to This Operation:**
- Probability of losing >20% of capital: **40%**
- Probability of losing >50% of capital: **15%**
- Probability of total loss: **5%**

### 4.2 Probability of Strategy Decay

**Alpha Decay Rates:**
- Mean reversion strategies: 6-18 months half-life
- Momentum strategies: 12-36 months half-life
- Machine learning strategies: 3-12 months half-life
- Arbitrage strategies: 1-6 months half-life

**Your Strategy Will Stop Working.** The only questions are:
1. When?
2. Will you detect it before major losses?
3. Do you have replacement strategies ready?

### 4.3 Probability of Overfitting

**Warning Signs You're Overfitting:**
- Sharpe ratio >2.0 in backtest
- Maximum drawdown <5%
- Win rate >60%
- Profit factor >2.0
- Parameter sensitivity: tiny changes cause huge performance swings

**Reality:** If your backtest looks too good to be true, it is.

### 4.4 What Could Go Wrong (Comprehensive)

#### Technical Failures
- **API rate limiting** during volatile periods
- **Data feed outages** causing stale prices
- **Server crashes** during market hours
- **Database corruption** losing trade history
- **Clock skew** causing timestamp errors
- **Network latency** causing missed fills

#### Market Risks
- **Flash crashes** triggering stop losses
- **Gap opens** exceeding risk limits
- **Liquidity evaporation** in small-cap positions
- **Correlation breakdown** during stress periods
- **Regulatory changes** making strategies illegal
- **Exchange halts** trapping positions

#### Operational Risks
- **Fat-finger errors** (wrong position size)
- **Deployment bugs** pushing untested code
- **Configuration errors** (wrong API keys, wrong symbols)
- **Monitoring failures** missing critical alerts
- **Key person risk** (only one developer understands system)

#### Business Risks
- **Data provider shutdown** or price increase
- **Broker API changes** breaking integration
- **Regulatory requirements** (SEC registration, audits)
- **Tax complications** (wash sales, mark-to-market)
- **Capital withdrawal** during drawdowns (behavioral)

### 4.5 Hidden Costs Not in Budget

| Cost | Amount | When |
|------|--------|------|
| Legal entity setup | $1,000-5,000 | Month 1 |
| Securities lawyer consultation | $500-2,000 | As needed |
| CPA/tax preparation | $2,000-5,000 | Year 1 |
| Audit (if required) | $5,000-20,000 | Year 1 |
| Errors & omissions insurance | $2,000-10,000 | Year 1 |
| Continuing education/courses | $500-3,000 | Ongoing |
| Hardware upgrades | $1,000-5,000 | As needed |
| Emergency cloud scaling | $500-2,000 | During volatility |

---

## 5. Engineering Recommendations

### 5.1 Minimum Viable Approach

**Phase 1 (Months 1-3): Validation**
- Budget: $10,000-15,000
- Goal: Validate that you can build and test strategies
- Success metric: 3 strategies with out-of-sample testing
- **Do NOT trade live capital yet**

**Phase 2 (Months 3-6): Paper Trading**
- Budget: $15,000-25,000
- Goal: Paper trade 1-2 strategies with real-time data
- Success metric: Paper results within 20% of backtest
- **Still no live capital**

**Phase 3 (Months 6-12): Limited Live Trading**
- Budget: $25,000-50,000
- Capital deployed: $100,000-200,000 (not full $1M)
- Goal: Prove live profitability
- Success metric: 6 months of live trading, Sharpe >0.5

### 5.2 Red Flags to Stop Immediately

Stop the project if:
1. Backtest Sharpe ratio >2.0 (overfitting)
2. No out-of-sample validation
3. Strategy depends on "secret" indicators
4. No stop-loss or risk limits
5. Can't explain why strategy works
6. No plan for when it stops working
7. Development taking >2x estimated time

### 5.3 Success Metrics (Realistic)

**Month 6:**
- 1 strategy in paper trading
- Backtesting framework operational
- Risk management implemented
- **Not:** Live profitability

**Month 12:**
- 1 strategy in live trading (small size)
- 3-6 months of live track record
- Sharpe ratio >0.5 (if profitable)
- Max drawdown <20%
- **Not:** 50%+ returns

**Month 24:**
- 2-3 uncorrelated strategies
- Full capital deployment
- 12+ months live track record
- Sharpe ratio >0.8
- **Maybe:** 10-20% annual returns

---

## 6. Conclusion

### The Honest Truth

Building a profitable quantitative trading system with $1M capital is **possible but unlikely**.

**Realistic Year 1 Outcome:**
- Costs: $100,000-150,000
- Returns: -20% to +10% on deployed capital
- Deployed capital: $200,000-500,000 (not full $1M)
- Net result: **-$120,000 to -$50,000**

**This is not pessimism. This is the base rate.**

### What Would Change the Odds

1. **Prior experience:** Former quant at established firm
2. **Team:** Multiple developers, not solo
3. **Capital:** $5M+ (economies of scale on data/costs)
4. **Edge:** Proprietary data or unique insight
5. **Time:** 3-5 year horizon, not 12 months
6. **Expectations:** 8-12% returns, not 50%+

### Final Recommendation

**Do not deploy $1M in capital in Year 1.**

Instead:
1. Budget $50,000-100,000 for development and learning
2. Deploy $100,000-200,000 maximum in Year 1
3. Focus on building robust infrastructure
4. Plan for 2-3 years to reach consistent profitability
5. Have a "kill switch" plan if metrics aren't met

**The goal of Year 1 is not profit. The goal is survival and learning.**

---

*Document Version: 1.0*  
*Classification: Engineering - Internal Use Only*  
*No Marketing Claims Permitted*
