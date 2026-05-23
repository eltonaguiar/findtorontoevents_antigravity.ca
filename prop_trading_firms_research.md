# PROPRIETARY TRADING FIRMS RESEARCH REPORT
## Comprehensive Analysis of Top 10 Market Makers & Their Trading Edges

---

## EXECUTIVE SUMMARY

This report analyzes ten leading proprietary trading firms, examining their trading strategies, technology stacks, training programs, risk management frameworks, compensation structures, and trader selection criteria. The firms collectively represent over $50 billion in annual trading revenue and employ more than 25,000 people globally.

**Key Finding:** The most successful prop trading firms share common characteristics:
- Heavy investment in low-latency technology (microsecond execution)
- Meritocratic, flat organizational structures
- Scientific approach to trading (probability theory, game theory)
- Diversified strategies across asset classes
- Aggressive talent acquisition with compensation premiums of 2-3x over traditional finance

---

## 1. JANE STREET

### Overview
- **Founded:** 2000 (New York)
- **Employees:** ~3,000+
- **2024 Net Trading Revenue:** $14.2 billion
- **Daily Trading Volume:** $72+ billion
- **Primary Edge:** ETF Arbitrage & Market Making

### Trading Strategies Employed

#### 1. ETF Arbitrage (Core Strategy - ~30% of revenue)
- **Mechanism:** Exploits price discrepancies between ETFs and their underlying NAV
- **Authorized Participant Status:** One of ~50 firms globally with ability to create/redeem ETF shares directly with issuers (BlackRock, Vanguard)
- **Execution:** When ETF trades below NAV → buy cheap ETF, sell underlying stocks simultaneously
- **Risk Profile:** Near risk-free arbitrage (buying/selling same economic exposure)
- **Scale:** Handles significant percentage of global ETF trading volume

#### 2. Market Making (Stocks, Options, Bonds) - ~40% of revenue
- Provides continuous bid-ask quotes across 200+ markets
- Profits from bid-ask spreads at massive volume
- Core insight: "We don't have a view on the market. We have a view on the price."

#### 3. Statistical Arbitrage (~15% of revenue)
- Identifies statistical relationships between correlated assets
- Bets on convergence when historically correlated assets diverge
- Pure quantitative approach using mathematical models

#### 4. Crypto Market Making (~10% of revenue)
- Early mover advantage in crypto markets
- Provides liquidity on major exchanges
- Wider spreads in crypto = higher profit per trade

#### 5. Cross-Asset Trading (~5% of revenue)
- Exploits price gaps across time zones and asset classes
- Global infrastructure enables seeing price changes before local markets react

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Primary Language** | OCaml (world's largest commercial user) |
| **Execution Speed** | <10 microseconds (30,000x faster than human blink) |
| **Infrastructure** | Petabyte-scale data processing |
| **Hardware** | Co-located servers, custom FPGA solutions |
| **Key Advantage** | OCaml catches bugs at compile time that other languages miss at runtime |

**Why OCaml?**
- Functional programming eliminates entire classes of runtime errors
- In trading, one bug = millions in losses
- Jane Street contributed so much to OCaml ecosystem they practically own it (open-source 'Base' library)

### Training Programs
- **Duration:** Team-based learning, mock trading, options theory
- **Philosophy:** Flat hierarchy - new hires can push ideas directly to senior leadership
- **Meritocracy:** If an intern proves their strategy is better, it goes live
- **No prior trading experience required** for technical hires

### Risk Limits & Drawdown Rules
- **Risk Management:** Real-time position monitoring across thousands of instruments
- **Position Limits:** Algorithms adjust positions in microseconds
- **Drawdown Protocol:** Risk systems designed to cut losses instantly
- **Key Insight:** Individual trades can lose money, but statistical edge plays out over time (like a casino)

### Compensation Structure

| Level | Base Salary | Total Compensation |
|-------|-------------|-------------------|
| **Interns** | - | $16,000-$20,000+/month + housing |
| **New Grad Traders** | $300,000 | $400,000-$700,000 |
| **New Grad SWE** | $250,000 | $350,000-$500,000 |
| **Senior (5+ years)** | - | $2-10+ million |
| **Top Performers** | - | $20M+ (estimated) |
| **Partners (UK)** | - | $19.6M average |

**Compensation Philosophy:** 
- Described as "a little communist" - bonuses based on firm performance rather than individual P&L
- One great hire can generate $50-100M+ in annual revenue
- Paying $5M/year is a 10-20x return on investment

### What They Look For in Traders
- **Academic Background:** Math, physics, computer science, probability theory
- **Key Skills:** 
  - Problem-solving under uncertainty
  - Game theory and probability puzzles
  - Quick decision-making ($1,000 decisions in 100ms)
  - No LeetCode - focus on thinking, not coding
- **Acceptance Rate:** <1% (notoriously selective)
- **Preferred Schools:** MIT, Stanford, University of Chicago, Cambridge

### Market Making vs Proprietary Strategies
- **Primary:** Market making (providing liquidity, collecting spreads)
- **Secondary:** Proprietary arbitrage (ETF arb, stat arb)
- **Hybrid Model:** Both market maker and prop trader - trades own capital but also provides market infrastructure

### Replicable Edges
1. **ETF Arbitrage Framework:** Understanding NAV vs market price dynamics
2. **Speed + Accuracy:** Technology advantage in pricing accuracy, not just raw speed
3. **Cross-Market Monitoring:** Seeing relationships between instruments others miss
4. **Risk-First Approach:** Cutting losses instantly, letting winners run

---

## 2. OPTIVER

### Overview
- **Founded:** 1986 (Amsterdam)
- **Employees:** ~2,100+
- **2024 Trading Revenue:** $3.8 billion
- **Primary Edge:** Options Market Making & Derivatives

### Trading Strategies Employed

#### 1. Options Market Making (Core)
- One of the largest options market makers globally
- Provides liquidity in equity, index, and ETF options
- Sophisticated pricing models for volatility surfaces

#### 2. ETF Market Making
- Significant presence in ETF liquidity provision
- Cross-asset hedging strategies

#### 3. Delta 1 Trading
- Index futures and forwards trading
- Low-latency execution strategies

#### 4. Institutional Trading
- Large block order execution
- Custom solutions for institutional clients

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Focus** | Hardware acceleration (FPGAs) |
| **Platforms** | Proprietary "Optibook" simulated trading environment |
| **Infrastructure** | Global low-latency network |
| **Innovation** | Heavy investment in AI/ML (hired Chief Data & AI Architect from Two Sigma) |

### Training Programs
- **Duration:** 12 weeks comprehensive training
- **Structure:**
  - Week 1-4: Options theory in Amsterdam (all global hires)
  - Week 5-12: Simulated trading with live market data
  - Mentorship pairing with experienced traders
- **FutureFocus Program:** 5-day discovery program for 1st/2nd year students
- **University Partnerships:** Cambridge Trading Academy, IIT Bombay AI Innovation Lab

### Risk Limits & Drawdown Rules
- **Risk Framework:** Automated risk management integrated with trading systems
- **Position Management:** Real-time exposure monitoring
- **Philosophy:** Risk management as competitive advantage

### Compensation Structure

| Level | Total Compensation |
|-------|-------------------|
| **Entry-Level Trader** | $250,000-$400,000 |
| **Experienced Trader** | $300,000-$500,000 |
| **UK Office Average** | £467,400 ($639,400) per employee |

**Unique Feature:** "Marbles" profit-sharing system
- Marbles allocated based on performance
- Each marble = percentage of total firm P&L
- Very meritocratic but tied to firm performance

### What They Look For in Traders
- **Skills:**
  - Mental math (necessary but not sufficient)
  - Quick decision-making under pressure
  - Pattern recognition (like Sudoku)
  - Probabilistic reasoning (poker-like thinking)
  - Intellectual curiosity
- **Background:** All STEM majors considered (CS, math, engineering, physics, actuarial, economics)
- **Philosophy:** "We recruit technical problem solvers"

### Market Making vs Proprietary Strategies
- **Primary:** Pure market making (options, ETFs, derivatives)
- **Approach:** Technology-driven liquidity provision
- **Client-Facing:** More institutional client interaction than Jane Street

### Replicable Edges
1. **Options Pricing Expertise:** Deep understanding of volatility and Greeks
2. **Hardware Acceleration:** FPGA usage for microsecond advantages
3. **Global Training Model:** Standardized education program produces consistent results
4. **Academic Partnerships:** Early access to top talent through university programs

---

## 3. IMC TRADING

### Overview
- **Founded:** 1989 (Amsterdam)
- **Employees:** ~2,480
- **Headquarters:** Infinity Building, Amsterdam
- **Primary Edge:** Quantitative Market Making & Algorithmic Trading

### Trading Strategies Employed

#### 1. Market Making (Core)
- Active on 100+ exchanges worldwide
- Equities, derivatives, fixed income
- Technology-driven liquidity provision

#### 2. Quantitative Trading
- Systematic strategies across asset classes
- Machine learning and AI integration
- Mid-frequency to high-frequency execution

#### 3. Crypto Trading (via Altas Technologies acquisition, 2023)
- Algorithmic crypto market making
- HFT monetization frameworks
- ML-driven alpha research

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Research Environment** | Cutting-edge ML/AI infrastructure |
| **Execution** | Low-latency automated systems |
| **Data** | Large-scale computing for analytics |
| **Focus** | Continuous innovation and disruption |

### Training Programs
- **Philosophy:** Meritocratic, empowering talent
- **Approach:** Directional advice, useful frameworks, freedom to execute
- **Global Teams:** Quant researchers work side-by-side with traders daily
- **Investment:** Heavy ongoing investment in emerging tech and data solutions

### Risk Limits & Drawdown Rules
- **Framework:** Active dialogue between Trading and Risk Management
- **Approach:** Risk limits reflect risks and rewards properly
- **Monitoring:** Continuous risk assessment across global operations

### Compensation Structure

| Level | Total Compensation |
|-------|-------------------|
| **Entry-Level Trader** | $200,000-$350,000 |
| **US Intern Return Offers** | $425,000 (reported) |
| **Profit-Sharing:** | Can significantly boost total comp |

### What They Look For in Traders
- **Background:** Mathematics, Physics, CS, Robotics, Data Science, Engineering, Statistics
- **Mindset:** Creative and scientific
- **Approach:** Self-directed, ownership mentality
- **Values:** Collaboration, high-performance culture

### Market Making vs Proprietary Strategies
- **Hybrid:** Market making with proprietary quant strategies
- **Evolution:** Expanding from pure market making to more systematic trading

### Replicable Edges
1. **Scientific Mindset:** Applying rigorous research methodology to trading
2. **Technology Investment:** Heavy ongoing investment in ML/AI
3. **Global Presence:** 24/7 trading capabilities across time zones
4. **Collaborative Culture:** Quant researchers embedded with traders

---

## 4. DRW TRADING

### Overview
- **Founded:** 1992 (Chicago) by Don Wilson
- **Employees:** ~2,000 (800+ technologists)
- **Structure:** Diversified trading firm + family office model
- **Primary Edge:** Multi-Asset Quantitative Trading & Crypto

### Trading Strategies Employed

#### 1. Traditional Asset Classes
- Fixed Income
- ETFs
- Equities
- FX
- Commodities and Energy

#### 2. Crypto Assets (Cumberland - subsidiary)
- At forefront since 2014
- Spot, futures, swaps, options
- Institutional counterparty focus

#### 3. Prediction Markets (New Focus)
- Trading on Polymarket and Kalshi
- Event contracts (elections, sports, macro)
- Bayesian probability models
- NLP sentiment parsing

#### 4. Venture Capital
- Investments in financial/enterprise technology
- Strategic synergies with trading operations

#### 5. Real Estate
- Fully integrated investment arm
- Value-add property focus

### Technology Stack

| Component | Technology |
|-----------|------------|
| **NX Team** | Custom network infrastructure |
| **Crypto** | 24/7 global coverage |
| **Prediction Markets** | Custom systems for event contract trading |
| **Approach** | Cutting-edge technology across all asset classes |

### Training Programs
- **Philosophy:** Empower exceptional individuals
- **Approach:** Autonomy and ability to pivot quickly
- **Values:** Respect, curiosity, open minds
- **Culture:** High expectations, integrity, innovation, willingness to challenge consensus

### Risk Limits & Drawdown Rules
- **Framework:** Risk management integrated across all strategies
- **Approach:** Operate using own capital, trading at own risk
- **Monitoring:** Real-time exposure management

### Compensation Structure

| Level | Base Salary | Total Compensation |
|-------|-------------|-------------------|
| **Graduate Quant Trader** | - | Training provided |
| **Crypto Relationship Manager** | $150,000-$200,000 | + discretionary bonus |
| **Prediction Markets Trader** | $175,000-$200,000 | + discretionary bonus |
| **UK Average** | - | £321,800 (~$400k) |

### What They Look For in Traders
- **Crypto Roles:** Passion for crypto, understanding of digital asset market structure
- **Prediction Markets:** Genuine demonstrated interest (personal trading, model building)
- **Technical Skills:** Python, Java, Git, SQL, Linux familiarity
- **Soft Skills:** Entrepreneurial mindset, sense of urgency, communication
- **Philosophy:** "It's not just what we do that matters—it's how we do it"

### Market Making vs Proprietary Strategies
- **Hybrid:** Market making + proprietary trading + VC + real estate
- **Unique:** Family office model provides long-term capital stability

### Replicable Edges
1. **Early Mover Advantage:** Crypto since 2014, prediction markets now
2. **Diversification:** Multiple asset classes + VC + real estate
3. **Institutional Crypto:** Cumberland's institutional relationships
4. **Network Infrastructure:** NX team builds custom connectivity

---

## 5. SUSQUEHANNA INTERNATIONAL GROUP (SIG)

### Overview
- **Founded:** 1987 (Philadelphia area)
- **Employees:** ~3,500+
- **2024 Revenue:** $7.2 billion
- **Primary Edge:** Options Market Making & Quantitative Trading

### Trading Strategies Employed

#### 1. Options Market Making (Core)
- One of largest options market participants globally
- Specialist/designated primary market maker in ~600 equity options, 45 index options
- Covers every asset class worldwide

#### 2. ETF Market Making
- One of world's leading ETF market makers
- Traded >$11bn in ETFs per day (2025)
- ~7% of US ETF volume (as of 2018)

#### 3. Gaming & Sports Betting
- Nellie Analytics (Dublin-based sports betting)
- Quantitative sports trading business
- Game theory applications

#### 4. Prediction Markets
- Pioneer in prediction markets
- Leading institutional liquidity provider
- Event contracts (elections, sports, finance)

#### 5. Venture Capital
- SIG China (350+ investments, 70+ exits)
- Susquehanna Growth Equity (software, information services)
- Notable: $5M investment in ByteDance (TikTok) in 2012 → $15B+ stake

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Approach** | Deep integration of trading, technology, quant research |
| **Infrastructure** | Proprietary technology for millions of daily transactions |
| **Specialization** | Highly specialized trading desks per asset class |

### Training Programs
- **Duration:** 6-12 month HQ training + 10-week trading class
- **Total Timeline:** 1-2 years to fully-fledged trader
- **Components:**
  - Options theory
  - Desk placement
  - Mock trading
- **Philosophy:** Scientific rigor, curiosity, innovation

### Risk Limits & Drawdown Rules
- **Framework:** Collaborative risk management
- **Approach:** Global expertise leveraged for 24/7 opportunities
- **Monitoring:** Real-time exposure across millions of transactions

### Compensation Structure

| Level | Total Compensation |
|-------|-------------------|
| **Graduate Quant Trader** | $150,000-$250,000 |
| **Dublin Office Average** | $686,000 (2024) |
| **Peak (2022)** | $1.1M average |

### What They Look For in Traders
- **Background:** Quantitative, analytical
- **Philosophy:** Game theory and mathematical models
- **Culture:** Intellectually driven, highly collaborative
- **Unique:** Poker experience valued (founders were poker players)

### Market Making vs Proprietary Strategies
- **Primary:** Market making (options, ETFs)
- **Secondary:** Proprietary VC investments
- **Hybrid:** Trading operations + venture capital arm

### Replicable Edges
1. **Game Theory Application:** Poker-derived strategic thinking
2. **Options Expertise:** Deep specialization in derivatives
3. **Venture Integration:** VC arm provides strategic insights and returns
4. **Sports/Prediction Markets:** Unique diversification into event contracts

---

## 6. JUMP TRADING

### Overview
- **Founded:** 1999 (Chicago) by Bill DiSomma and Paul Gurinas
- **Employees:** 2,000+
- **AUM:** $7.6+ billion
- **Primary Edge:** High-Frequency Trading & Algorithmic Execution

### Trading Strategies Employed

#### 1. High-Frequency Trading (Core)
- Ultra-fast execution in microseconds
- Low-latency algorithms across asset classes
- Machine learning integration

#### 2. Fixed Income (Historical Strength)
- Dominated US fixed income market historically
- Treasury securities, futures

#### 3. Crypto Trading
- Early bullish entrant to crypto
- Significant infrastructure investment
- Recent challenges (FTX fallout, TerraUSD fine)

#### 4. Prediction Markets (New Focus)
- Equity stakes in Kalshi ($11B valuation) and Polymarket ($9B)
- Liquidity-for-equity deals
- 20+ dedicated staff for event contracts

#### 5. Cross-Asset Arbitrage
- Exploiting price discrepancies across markets
- Speed-based alpha generation

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Speed** | Picosecond-level optimization |
| **Infrastructure** | Microwave towers for speed advantages |
| **Hardware** | Custom low-latency systems |
| **Innovation** | AI models driving trading decisions |

### Training Programs
- **Approach:** "Weekend warriors" - potential 4-day week options
- **Philosophy:** Self-motivated, independent thinkers
- **Growth:** ~350 employees (2017) → 2,000+ (2025)

### Risk Limits & Drawdown Rules
- **Framework:** Sophisticated risk management for HFT
- **Challenge:** Crypto subsidiary faced $123M fine (TerraUSD)
- **Evolution:** Learning from setbacks, rebuilding cautiously

### Compensation Structure

| Level | Total Compensation |
|-------|-------------------|
| **Quant Researcher** | $350,000-$600,000 |
| **Quant Developer** | $300,000-$500,000 |
| **Software Engineer** | $300,000-$500,000 |
| **UK Average** | $659,500 (2024) |
| **Top Performers** | £1M+ (including £350k signing bonus, £500k guaranteed bonus) |

### What They Look For in Traders
- **Background:** Former CME pit traders, engineers, physicists
- **Skills:** Low-latency systems, algorithmic thinking
- **Culture:** Secretive, protective of strategies
- **Approach:** Aggressive, entrepreneurial

### Market Making vs Proprietary Strategies
- **Primary:** HFT proprietary trading
- **Secondary:** Market making (especially prediction markets)
- **Evolution:** Expanding into equity stakes in exchanges

### Replicable Edges
1. **Speed Infrastructure:** Microwave towers, co-location
2. **AI Integration:** Machine learning for execution
3. **Exchange Relationships:** Equity stakes align incentives
4. **Asset Class Diversification:** From fixed income to crypto to prediction markets

---

## 7. AKUNA CAPITAL

### Overview
- **Founded:** 2011 (Chicago)
- **Founders:** Andrew Killion (Sydney-based founding partners)
- **Offices:** Chicago, Sydney, Shanghai, London, Singapore
- **Primary Edge:** Options Market Making with Technology Focus

### Trading Strategies Employed

#### 1. Options Market Making (Core)
- Leading options market maker
- Successfully entered industry with sustainable growth
- Rapid innovation for liquidity provision

#### 2. Quantitative Trading
- Scientific approach combining quant expertise with derivatives understanding
- Machine learning algorithms for strategy development
- Portfolio construction optimization

#### 3. Automated Market Making
- Low-latency technologies
- Data-driven solutions
- Automation-first approach

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Primary Language** | C++ (for computational heavy-lifting) |
| **Secondary** | Python (Pandas, NumPy for analysis) |
| **Focus** | Low-latency, high-performance systems |
| **Infrastructure** | Multi-core, super-scalar processors |

### Training Programs
- **Akunacademy:** 10-week internship program
- **Options 101:** Free course on industry fundamentals
- **Sneak Peek Week:** One-week accelerated introduction
- **Philosophy:** No previous finance/trading experience required
- **Approach:** Team-based, collaborative learning

### Risk Limits & Drawdown Rules
- **Framework:** Risk management integrated with trading systems
- **Approach:** "Own your impact from day one"
- **Monitoring:** Real-time position management

### Compensation Structure

| Level | Base Salary | Total Compensation |
|-------|-------------|-------------------|
| **Junior Trader** | $130,000 | $180,000+ |
| **Junior Quant Developer** | $130,000+ | - |
| **Quant Dev Intern** | - | Pro-rated from $130k+ base |

### What They Look For in Traders
- **Technical Background:** CS, Engineering, Math, Physics
- **Skills:**
  - C++ programming
  - Object-oriented programming
  - Linear algebra, statistics
  - Problem-solving and analytical skills
- **Mindset:** Self-starter, ownership mentality, innovation
- **GPA:** 3.0+ major GPA

### Market Making vs Proprietary Strategies
- **Primary:** Options market making
- **Approach:** Technology-enabled liquidity provision
- **Differentiation:** Youth and agility in competitive landscape

### Replicable Edges
1. **Technology Focus:** Heavy investment in low-latency infrastructure
2. **Global Presence:** Offices in key financial centers
3. **Free Education:** Options 101 course attracts and educates talent
4. **Agility:** "Advantage of youth" - nimble in changing landscape

---

## 8. BELVEDERE TRADING

### Overview
- **Location:** Chicago (primary)
- **Expansion:** Singapore office
- **Primary Edge:** Options Market Making (Commodities, ETFs, Equity Indices)

### Trading Strategies Employed

#### 1. Commodities Options Market Making
- Energy, metals, agriculture
- Deep understanding of supply-demand dynamics
- Fundamental drivers analysis

#### 2. ETF Options Market Making
- Exchange-traded fund derivatives
- Liquidity provision across ETF universe

#### 3. Equity Index Options
- Broad market index derivatives
- Volatility trading

#### 4. Interest Rate Options
- Rates derivatives
- Macro-economic factor integration

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Tools** | Python, R, SQL |
| **Focus** | Data analysis, modeling, decision-support systems |
| **Infrastructure** | Proprietary trading systems |
| **Collaboration** | Traders partner with technologists for optimization |

### Training Programs
- **Philosophy:** Formal quantitative education
- **Approach:** Build and operate trading strategies
- **Development:** Continuous learning and optimization
- **Values:** Team Belvedere, "Me in Team", "Own It", "Build Rockets", "Passionate Discourse"

### Risk Limits & Drawdown Rules
- **Framework:** Disciplined risk management
- **Approach:** Real-time exposure monitoring
- **Philosophy:** Risk management as core competency

### Compensation Structure

| Level | Base Salary | Total Compensation |
|-------|-------------|-------------------|
| **Experienced Commodities Trader** | $150,000-$200,000 | + discretionary bonus |
| **Quantitative Trader (Entry)** | - | Competitive |

### What They Look For in Traders
- **Experience:** 3-7+ years for senior roles
- **Skills:**
  - Options pricing, volatility dynamics
  - Commodity market structure
  - Python/R/SQL proficiency
  - Large dataset analysis
- **Mindset:** Team-oriented, thrives under pressure, adaptability
- **Background:** Finance, Engineering, Physics, Math, Economics, CS

### Market Making vs Proprietary Strategies
- **Primary:** Pure options market making
- **Approach:** Providing liquidity through market-making activities
- **Specialization:** Commodities focus differentiates from competitors

### Replicable Edges
1. **Commodities Specialization:** Deep expertise in energy, metals, agriculture
2. **Quantitative Training:** Formal education on quantitative concepts
3. **Team Culture:** Collaborative environment with defined values
4. **International Expansion:** Singapore office for Asia-Pacific access

---

## 9. TRANSMARKET GROUP (TMG)

### Overview
- **Location:** Chicago
- **Primary Edge:** Futures & FX Trading, Arbitrage

### Trading Strategies Employed

#### 1. FX Futures and Spot Trading
- Foreign exchange derivatives
- Cross-currency arbitrage
- Macro-driven strategies

#### 2. Algorithmic Trading
- Quantitative execution strategies
- Systematic approaches to futures

#### 3. Arbitrage Strategies
- Exploiting price discrepancies
- Cross-market opportunities

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Approach** | Quant-driven execution |
| **Infrastructure** | Algorithmic trading systems |
| **Focus** | Automation and systematic strategies |

### Training Programs
- **Philosophy:** Hands-on learning
- **Approach:** Junior traders work alongside experienced professionals
- **Development:** Progressive responsibility increase

### Risk Limits & Drawdown Rules
- **Framework:** Risk management for futures trading
- **Approach:** Position limits and exposure monitoring

### Compensation Structure

| Level | Base Salary | Bonus | Total Compensation |
|-------|-------------|-------|-------------------|
| **Average** | $65,000 | $30,000 | $95,000 |
| **Prop Trading Group** | - | - | $82,500 average |
| **Senior FX Trader** | $120,000-$200,000 | - | - |
| **Algorithmic Trader** | $183,000-$308,000 | - | - |

**Note:** Lower compensation than top-tier firms, but potential upside for performers

### What They Look For in Traders
- **Background:** Quantitative, analytical
- **Skills:** Programming, statistical analysis
- **Approach:** Systematic thinking

### Market Making vs Proprietary Strategies
- **Primary:** Proprietary futures and FX trading
- **Approach:** Quantitative arbitrage and systematic strategies

### Replicable Edges
1. **Futures Specialization:** Focus on derivatives markets
2. **FX Expertise:** Currency market knowledge
3. **Algorithmic Approach:** Systematic execution

---

## 10. CHICAGO TRADING COMPANY (CTC)

### Overview
- **Founded:** 1995 (Chicago)
- **Primary Edge:** Options Market Making & Risk Management

### Trading Strategies Employed

#### 1. Options Market Making (Core)
- Leader in options trading
- Innovative pricing and risk management

#### 2. Agency Options Business (New)
- Building institutional client business
- Execution services for buy-side

#### 3. Quantitative Research
- Systematic strategy development
- Statistical analysis and back-testing
- Machine learning integration

#### 4. Institutional Derivatives Sales
- Client-facing derivatives business
- Business development focus

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Focus** | Innovative, cutting-edge systems |
| **Research** | Quantitative models, back-testing capabilities |
| **Approach** | Scientific method applied to business problems |

### Training Programs
- **Philosophy:** "Fun and trusting culture"
- **Approach:** Collaborative problem-solving
- **Values:** Ethical excellence, innovation, calculated risks
- **Development:** Continuous learning and skill-building

### Risk Limits & Drawdown Rules
- **Framework:** Sophisticated risk management
- **Approach:** "Helping the world price and manage risk"
- **Monitoring:** Real-time risk assessment

### Compensation Structure

| Level | Base Salary | Total Compensation |
|-------|-------------|-------------------|
| **Options Trader** | $112,000-$203,000 (monthly: $9,366-$16,956) |
| **Quantitative Researcher** | $200,000-$300,000 | + discretionary bonus |
| **Head of Institutional Sales** | $200,000-$300,000 | + discretionary bonus |
| **First Year Trader** | - | $150,000-$200,000 |
| **Full Trader** | - | $300,000-$3,000,000 |

**Note:** Partners can earn more than $3M

### What They Look For in Traders
- **Background:** Technical (engineering, CS, math, physics)
- **Skills:** Quantitative analysis, programming
- **Mindset:** Collaborative, innovative, ethical
- **Philosophy:** "Solve the industry's most challenging problems"

### Market Making vs Proprietary Strategies
- **Primary:** Market making with expanding agency business
- **Evolution:** Adding client-facing services to traditional prop model

### Replicable Edges
1. **Risk Management Focus:** Core competency in pricing and managing risk
2. **Ethical Culture:** Values-driven approach to trading
3. **Innovation:** Continuous investment in new strategies
4. **Agency Expansion:** Diversifying into client services

---

## COMPARATIVE ANALYSIS

### Compensation Ranking (Entry-Level Total Comp)

| Rank | Firm | Entry-Level TC |
|------|------|----------------|
| 1 | Jane Street | $400,000-$700,000 |
| 2 | Jump Trading | $350,000-$600,000 |
| 3 | Hudson River Trading | $350,000-$550,000 |
| 4 | Citadel Securities | $350,000-$550,000 |
| 5 | Optiver | $250,000-$400,000 |
| 6 | Five Rings | $300,000+ |
| 7 | IMC Trading | $200,000-$350,000 |
| 8 | SIG | $200,000-$350,000 |
| 9 | Chicago Trading Company | $150,000-$200,000 |
| 10 | Akuna Capital | $180,000+ |
| 11 | Belvedere Trading | $150,000-$200,000 |
| 12 | TransMarket Group | $95,000-$150,000 |

### Technology Stack Comparison

| Firm | Primary Language | Key Tech Focus |
|------|------------------|----------------|
| Jane Street | OCaml | Functional programming, correctness |
| Optiver | C++/FPGA | Hardware acceleration |
| IMC | Python/C++ | ML/AI integration |
| DRW | Python/Java | Multi-asset, crypto |
| SIG | Proprietary | Options pricing models |
| Jump | C++ | Low-latency, speed |
| Akuna | C++/Python | Low-latency options |
| Belvedere | Python/R/SQL | Data analysis |
| TMG | Various | Algorithmic execution |
| CTC | Various | Quant research |

### Training Program Comparison

| Firm | Duration | Key Feature |
|------|----------|-------------|
| Jane Street | Ongoing | Flat hierarchy, meritocracy |
| Optiver | 12 weeks | Amsterdam-based global training |
| IMC | Ongoing | Meritocratic, self-directed |
| DRW | Ongoing | Autonomy, pivot capability |
| SIG | 1-2 years | Game theory, poker background |
| Jump | Ongoing | "Weekend warrior" flexibility |
| Akuna | 10 weeks | Akunacademy, free Options 101 |
| Belvedere | Ongoing | Formal quant education |
| TMG | Ongoing | Hands-on learning |
| CTC | Ongoing | Collaborative innovation |

---

## KEY INSIGHTS & REPLICABLE EDGES

### 1. Technology as Competitive Advantage
All top firms invest heavily in:
- **Low-latency infrastructure:** Microsecond execution is table stakes
- **Custom hardware:** FPGAs, co-located servers
- **Programming languages:** C++ for speed, Python for research, OCaml for correctness
- **Machine Learning:** AI integration becoming standard

### 2. Risk Management Philosophy
- **Real-time monitoring:** Position limits enforced automatically
- **Instant cutoffs:** Losses cut immediately, winners run
- **Diversification:** Across asset classes, strategies, time horizons
- **Capital preservation:** First priority in volatile markets

### 3. Talent Acquisition & Retention
- **Premium compensation:** 2-3x traditional finance salaries
- **Meritocratic cultures:** Best ideas win regardless of seniority
- **Flat hierarchies:** Direct access to decision-makers
- **Intellectual stimulation:** Attracts top STEM graduates

### 4. Market Making vs Proprietary Strategies

| Aspect | Market Making | Proprietary |
|--------|--------------|-------------|
| **Revenue Source** | Bid-ask spreads | Price appreciation |
| **Risk Profile** | Lower (inventory risk) | Higher (directional) |
| **Hold Period** | Seconds to minutes | Minutes to days |
| **Key Skill** | Pricing accuracy | Alpha generation |
| **Capital Usage** | High turnover | Lower turnover |

### 5. Replicable Strategies for Individual Traders

#### A. ETF Arbitrage Framework
1. Monitor ETF price vs NAV
2. Identify creation/redemption opportunities
3. Execute simultaneous buy/sell
4. **Key Requirement:** Authorized Participant status (institutional only)

#### B. Options Market Making Principles
1. Understand volatility surfaces
2. Manage Greeks (delta, gamma, theta, vega)
3. Provide liquidity at fair prices
4. Hedge inventory risk continuously

#### C. Statistical Arbitrage Approach
1. Identify correlated assets
2. Monitor for divergence
3. Bet on mean reversion
4. **Key Requirement:** Robust back-testing, risk management

#### D. Cross-Asset Relationships
1. Monitor related markets (futures vs spot)
2. Identify lead-lag relationships
3. Exploit information asymmetry
4. **Key Requirement:** Multi-market access

### 6. What Separates Top Firms from Average

| Factor | Top Firms | Average Firms |
|--------|-----------|---------------|
| **Technology Investment** | $100M+ annually | Minimal |
| **Talent Density** | Top 0.1% of graduates | Average |
| **Risk Management** | Institutional-grade | Basic |
| **Market Access** | Direct, co-located | Retail brokers |
| **Information Edge** | Proprietary data | Public data |
| **Execution Speed** | Microseconds | Seconds |

---

## CONCLUSION

The proprietary trading industry represents the pinnacle of quantitative finance, where technology, mathematics, and risk management converge. The top firms share common characteristics:

1. **Technology-First:** They are technology companies that happen to trade
2. **Talent-Obsessed:** Willing to pay 2-3x market rates for top performers
3. **Risk-Managed:** Sophisticated systems to limit downside
4. **Diversified:** Multiple strategies, asset classes, and revenue streams
5. **Meritocratic:** Best ideas win, regardless of source

For individual traders, the key lessons are:
- **Focus on edges that can be systematized**
- **Risk management is more important than returns**
- **Technology investment compounds over time**
- **Diversification across strategies reduces drawdowns**
- **Continuous learning is non-negotiable**

The barriers to entry are high (capital, technology, regulatory), but the principles these firms employ can be adapted and learned from by serious traders at any scale.

---

*Report compiled: February 2026*
*Sources: Company websites, regulatory filings, industry reports, compensation databases*
