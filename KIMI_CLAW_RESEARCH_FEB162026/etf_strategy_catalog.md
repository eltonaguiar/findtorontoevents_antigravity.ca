# Comprehensive ETF Strategy Catalog

## Table of Contents
1. [Sector Rotation ETFs](#1-sector-rotation-etfs)
2. [Factor ETFs](#2-factor-etfs)
3. [International ETFs](#3-international-etfs)
4. [Bond ETFs](#4-bond-etfs)
5. [Commodity ETFs](#5-commodity-etfs)
6. [Crypto ETFs](#6-crypto-etfs)
7. [Inverse/Leveraged ETFs](#7-inverseleveraged-etfs)
8. [Thematic ETFs](#8-thematic-etfs)
9. [ETF Arbitrage & Structural Strategies](#9-etf-arbitrage--structural-strategies)
10. [ETF Options Strategies](#10-etf-options-strategies)
11. [Data Sources & Tools](#11-data-sources--tools)

---

## 1. Sector Rotation ETFs

### Key ETFs
| Symbol | Sector | Provider |
|--------|--------|----------|
| XLF | Financials | SPDR |
| XLK | Technology | SPDR |
| XLE | Energy | SPDR |
| XLI | Industrials | SPDR |
| XLP | Consumer Staples | SPDR |
| XLY | Consumer Discretionary | SPDR |
| XLB | Materials | SPDR |
| XLU | Utilities | SPDR |
| XLRE | Real Estate | SPDR |
| XLC | Communication Services | SPDR |

### Strategies

#### 1.1 Sector Momentum Rotation
- **Mechanism**: Rank sector ETFs by 12-month momentum, hold top 3-4 performers
- **Rebalancing**: Monthly
- **Performance**: ~13.94% annual return historically (Quantpedia)
- **Key Insight**: Sectors have different sensitivities to business cycles
- **Edge**: Behavioral factors (herding, overreaction) drive sector momentum

#### 1.2 Relative Strength Model
- Compare sector performance vs S&P 500
- Invest in sectors showing strongest relative strength
- Add trend-following filter to hedge during bear markets
- Outperforms buy-and-hold in ~70% of years

#### 1.3 Smart Flow Watch
- Monitor ETF flow data (creation/redemption activity)
- Large flows often front-run macro changes
- Follow institutional money rotation

#### 1.4 Business Cycle Rotation
- Early Cycle: Financials (XLF), Consumer Discretionary (XLY), Tech (XLK)
- Mid Cycle: Industrials (XLI), Materials (XLB)
- Late Cycle: Energy (XLE), Staples (XLP), Healthcare
- Recession: Utilities (XLU), Consumer Staples (XLP)

### Differences from Stock Strategies
- Sector ETFs diversify single-stock risk
- Lower transaction costs vs trading individual stocks
- More liquid than most individual stocks
- Macro-driven rather than company-specific

### Data Sources
- Sector ETF price data (Yahoo Finance, Bloomberg)
- ETF flow data (ETF.com, FactSet)
- Economic cycle indicators (ISM, LEI)
- Sector earnings momentum

---

## 2. Factor ETFs

### Key ETFs
| Symbol | Factor | Provider |
|--------|--------|----------|
| USMV | Minimum Volatility | iShares |
| MTUM | Momentum | iShares |
| QUAL | Quality | iShares |
| VLUE | Value | iShares |
| SIZE | Size (Small Cap) | iShares |
| SPHD | High Dividend/Low Vol | Invesco |
| RPV | Pure Value | Invesco |
| RPG | Pure Growth | Invesco |

### Strategies

#### 2.1 Factor Rotation
- Rotate between factors based on macro regime
- Value tends to outperform during recovery/inflation
- Momentum works in trending markets
- Low volatility outperforms during drawdowns
- Quality performs consistently across cycles

#### 2.2 Multi-Factor Combination
- Combine 2-4 factors for diversification
- Example: 25% USMV + 25% MTUM + 25% QUAL + 25% VLUE
- Reduces factor timing risk
- Smoother risk-adjusted returns

#### 2.3 Factor Timing
- Use macro indicators to time factor exposure:
  - Rising rates → Value, Small Cap
  - Falling rates → Growth, Quality
  - High volatility → Low Volatility, Quality
  - Economic expansion → Momentum, Small Cap

#### 2.4 Factor Momentum
- Factors themselves exhibit momentum
- Hold factors with strongest recent performance
- Rebalance quarterly or monthly

### Differences from Stock Strategies
- Systematic, rules-based exposure
- No single-stock selection needed
- Factor exposure is diversified across hundreds of stocks
- Lower turnover than active stock picking

### Data Sources
- Factor ETF prices and NAVs
- Factor research data (AQR, MSCI, FTSE Russell)
- Macro regime indicators
- Factor performance databases (Kenneth French)

---

## 3. International ETFs

### Key ETFs
| Symbol | Market | Provider |
|--------|--------|----------|
| EEM | Emerging Markets | iShares |
| VWO | Emerging Markets | Vanguard |
| EFA | Developed Markets (EAFE) | iShares |
| VEA | Developed Markets | Vanguard |
| IEFA | Core MSCI EAFE | iShares |
| VXUS | Total International | Vanguard |
| FXE | Euro Currency | Invesco |
| FXY | Japanese Yen | Invesco |

### Strategies

#### 3.1 Country/Region Rotation
- Rotate between developed and emerging markets
- Use momentum and relative strength signals
- Consider currency effects

#### 3.2 Currency Hedging Strategy
- Compare hedged vs unhedged versions
- Hedge when USD strengthening
- Unhedge when USD weakening
- Currency can be 50%+ of international returns

#### 3.3 Pairs Trading with Country ETFs
- Trade mean-reversion between correlated country ETFs
- Example: EEM vs VWO (same exposure, different providers)
- Can achieve ~27 bps monthly excess returns

#### 3.4 Time Zone Arbitrage
- International ETFs trade while underlying markets closed
- Price discovery happens during US hours
- News after foreign close creates next-day gaps

### Differences from Stock Strategies
- Currency exposure adds dimension
- Time zone differences create unique dynamics
- Less liquid than US ETFs
- NAV can be stale (underlying markets closed)

### Data Sources
- International ETF prices
- Currency data (EUR, JPY, GBP, etc.)
- Country economic indicators
- International market hours and holidays

---

## 4. Bond ETFs

### Key ETFs
| Symbol | Bond Type | Duration |
|--------|-----------|----------|
| TLT | Long-Term Treasuries | 20+ years |
| IEF | Intermediate Treasuries | 7-10 years |
| SHY | Short-Term Treasuries | 1-3 years |
| HYG | High Yield Corporate | Intermediate |
| LQD | Investment Grade Corporate | Intermediate |
| BND | Total Bond Market | Aggregate |
| AGG | Core US Aggregate | Aggregate |
| TIP | TIPS (Inflation-Protected) | Intermediate |
| MUB | Municipal Bonds | Intermediate |

### Strategies

#### 4.1 Duration Rotation
- Adjust duration based on interest rate outlook
- Rising rates → Short duration (SHY)
- Falling rates → Long duration (TLT)
- Steepener/Flattener trades using TLT/SHY ratio

#### 4.2 Credit Spread Trading
- Trade HYG/LQD ratio for credit cycle
- Widening spreads → Defensive (LQD, Treasuries)
- Tightening spreads → Risk-on (HYG)

#### 4.3 Bond Buy-Write (Covered Calls)
- Sell calls against bond ETF positions
- Generate income in low-yield environment
- TLT and HYG have liquid options

#### 4.4 Yield Curve Steepeners/Flatteners
- Long SHY + Short TLT = Steepener bet
- Long TLT + Short SHY = Flattener bet
- Profits from yield curve shape changes

### Differences from Stock Strategies
- Bond NAV calculated from mid/bid prices (not last trade)
- Premium/discount reflects liquidity, not just sentiment
- Options income can exceed bond yield
- Duration is key risk factor (not volatility)

### Data Sources
- Treasury yield data (FRED, Treasury.gov)
- Credit spread data (ICE BofA, Bloomberg)
- Bond ETF NAVs (often mid-marked)
- Fed policy expectations

---

## 5. Commodity ETFs

### Key ETFs
| Symbol | Commodity | Structure |
|--------|-----------|-----------|
| GLD | Gold | Physical |
| IAU | Gold | Physical |
| SLV | Silver | Physical |
| USO | Crude Oil | Futures |
| UNG | Natural Gas | Futures |
| DBC | Broad Commodities | Futures |
| PDBC | Optimized Commodities | Futures |
| USL | Oil (12-month) | Futures |
| BNO | Brent Oil | Futures |

### Strategies

#### 5.1 Contango/Backwardation Roll Yield
- **Contango**: Futures curve upward sloping → Negative roll yield
- **Backwardation**: Futures curve downward sloping → Positive roll yield
- Trade commodities in backwardation (USO during oil shortages)
- Avoid or short commodities in steep contango

#### 5.2 Physical vs Futures Arbitrage
- GLD/IAU hold physical metal (no roll yield issues)
- USO/UNG use futures (subject to contango decay)
- Physical ETFs better for long-term holds

#### 5.3 Commodity Momentum
- Commodities exhibit strong momentum
- Use 12-month momentum signals
- Combine with roll yield consideration

#### 5.4 Gold/Silver Ratio Trading
- Historical mean around 50-60
- Buy silver when ratio >80
- Buy gold when ratio <40
- Pair trade: Long SLV / Short GLD or vice versa

### Differences from Stock Strategies
- Futures-based ETFs have roll costs/benefits
- Physical ETFs have storage costs
- Commodities have no "earnings" or dividends
- Supply/demand fundamentals differ from stocks

### Data Sources
- Futures curve data (CME, ICE)
- Commitment of Traders (COT) reports
- Physical commodity prices
- Inventory/storage data

---

## 6. Crypto ETFs

### Key ETFs
| Symbol | Crypto | Structure |
|--------|--------|-----------|
| BITO | Bitcoin | Futures |
| BITI | Bitcoin Inverse | Futures |
| ETHE | Ethereum | Spot (Grayscale) |
| ETCG | Ethereum Classic | Spot (Grayscale) |
| BLOK | Blockchain Companies | Equity |
| WGMI | Bitcoin Miners | Equity |

### Strategies

#### 6.1 Spot vs Futures Arbitrage
- Spot Bitcoin ETFs (new) vs Futures ETFs (BITO)
- Futures ETFs have contango costs
- Trade premium/discount between structures

#### 6.2 Crypto Equity Proxy
- BLOK, WGMI as crypto exposure without direct holding
- Trade correlation breakdowns
- Crypto equities often lead/lag actual crypto

#### 6.3 Volatility Harvesting
- Crypto ETFs have extreme volatility
- Short strangles can generate high income
- Manage position size carefully

#### 6.4 Grayscale Premium/Discount
- GBTC, ETHE historically traded at premium/discount to NAV
- Trade the convergence
- Premium when demand high, discount when outflows

### Differences from Stock Strategies
- 24/7 underlying market vs ETF market hours
- Extreme volatility (2-5x stock volatility)
- Regulatory uncertainty premium
- Futures-based products have unique risks

### Data Sources
- Crypto spot prices (Coinbase, Binance)
- Futures data (CME)
- ETF NAV vs market price
- On-chain metrics (Glassnode, CryptoQuant)

---

## 7. Inverse/Leveraged ETFs

### Key ETFs
| Symbol | Leverage | Underlying |
|--------|----------|------------|
| TQQQ | +3x | Nasdaq-100 |
| SQQQ | -3x | Nasdaq-100 |
| UPRO | +3x | S&P 500 |
| SPXU | -3x | S&P 500 |
| UVXY | +1.5x | VIX Short-Term Futures |
| SVXY | -0.5x | VIX Short-Term Futures |
| SOXL | +3x | Semiconductors |
| LABU | +3x | Biotech |
| FNGU | +3x | FANG+ Stocks |

### Strategies

#### 7.1 Volatility Decay Harvesting
- Leveraged ETFs lose value in choppy markets
- Short both TQQQ and SQQQ (or UPRO/SPXU)
- Collect decay when market ranges
- Hedge with long underlying or options

#### 7.2 Trend-Following with Leverage
- Use only in strong trending markets
- Exit when volatility increases
- Never hold through consolidation
- Set tight stops

#### 7.3 Day Trading/Short-Term
- Designed for daily holding
- Intraday moves can be captured
- Close positions before overnight gap risk

#### 7.4 Hedging with Inverse ETFs
- SQQQ as portfolio hedge
- Cheaper than puts in high IV environment
- Rebalance daily to maintain hedge ratio

#### 7.5 UVXY/SVXY Volatility Trading
- UVXY has extreme decay (often 50%+ annually)
- Short UVXY during calm markets
- Long UVXY as crash insurance (short-term only)
- SVXY benefits from VIX contango

### Differences from Stock Strategies
- Daily reset creates compounding effects
- Volatility decay is major headwind
- Not suitable for long-term buy-and-hold
- Require active management

### Data Sources
- Underlying index prices
- VIX term structure
- Leveraged ETF NAVs
- Options implied volatility

---

## 8. Thematic ETFs

### Key ETFs
| Symbol | Theme | Provider |
|--------|-------|----------|
| ARKK | Innovation | ARK |
| ARKG | Genomics | ARK |
| ARKW | Next Gen Internet | ARK |
| BOTZ | Robotics & AI | Global X |
| LIT | Lithium & Batteries | Global X |
| CLOU | Cloud Computing | Global X |
| SOXX | Semiconductors | iShares |
| SMH | Semiconductors | VanEck |
| XBI | Biotech | SPDR |
| IBB | Nasdaq Biotech | iShares |

### Strategies

#### 8.1 Disruptive Innovation Cycle
- Thematic ETFs concentrate on emerging trends
- High growth potential but high volatility
- ARKK focuses on: AI, robotics, energy storage, DNA sequencing
- Trade based on innovation adoption curves

#### 8.2 Thematic Rotation
- Rotate between themes based on macro trends
- AI boom → BOTZ, CLOU
- EV growth → LIT
- Biotech breakthroughs → ARKG, XBI
- Semiconductor cycle → SOXX, SMH

#### 8.3 Active vs Passive Thematic
- ARK funds are actively managed
- Can adapt to changing landscape
- Higher fees but potential for alpha
- Track holdings changes for signals

#### 8.4 Thematic Pairs Trading
- BOTZ vs SOXX (AI exposure comparison)
- LIT vs XLE (energy transition)
- XBI vs IBB (speculative vs large-cap biotech)

### Differences from Stock Strategies
- Concentrated exposure to specific trends
- Higher volatility than broad market
- Theme can go out of favor for years
- Active management can add value

### Data Sources
- ETF holdings (daily for ARK)
- Theme-specific news and data
- Patent filings (innovation indicator)
- Industry adoption metrics

---

## 9. ETF Arbitrage & Structural Strategies

### 9.1 Creation/Redemption Arbitrage

#### Mechanism
- Authorized Participants (APs) create/redeem ETF shares
- Creation: Deliver basket of securities → Receive ETF shares
- Redemption: Deliver ETF shares → Receive basket of securities
- Keeps ETF price aligned with NAV

#### Strategy
- When ETF trades at premium: Buy basket, create ETF, sell ETF
- When ETF trades at discount: Buy ETF, redeem, sell basket
- Requires AP status or significant capital
- High-frequency, low-margin business

### 9.2 Premium/Discount Trading

#### Mechanism
- ETFs trade at premium (above NAV) or discount (below NAV)
- Caused by: supply/demand, time zone differences, illiquidity
- Premiums/discounts usually mean-revert

#### Strategy
- Buy ETFs trading at significant discount
- Sell ETFs trading at significant premium
- Requires monitoring iNAV (intraday NAV)
- Works best with international and bond ETFs

### 9.3 NAV Tracking Strategies

#### Mechanism
- ETFs publish iNAV every 15 seconds
- Compare ETF price to iNAV in real-time
- Deviations indicate trading opportunity

#### Strategy
- Buy when ETF price < iNAV (discount)
- Sell when ETF price > iNAV (premium)
- Requires low-latency data and execution
- Works best in volatile markets

### 9.4 After-Hours ETF Trading

#### Mechanism
- ETFs trade 4:00 PM - 8:00 PM ET
- Underlying securities may be closed
- Price discovery based on futures and news

#### Strategy
- Trade on earnings/news after 4 PM
- International ETFs price in overnight foreign market moves
- Bond ETFs price in post-close Treasury moves
- Higher spreads, requires limit orders

### 9.5 Statistical Arbitrage with ETFs

#### Pairs Trading
- Trade mean-reversion between similar ETFs
- EEM vs VWO (emerging markets)
| IWM vs VTWO (small cap)
- Requires cointegration analysis

#### ETF vs Basket
- Trade ETF against replicating basket
- SPY vs 500 stocks (requires significant capital)
- HFT strategy with sophisticated infrastructure

---

## 10. ETF Options Strategies

### 10.1 Covered Calls on ETFs

#### Strategy
- Own ETF shares
- Sell out-of-the-money calls
- Collect premium as income
- Cap upside at strike price

#### Best ETFs for Covered Calls
- SPY, QQQ, IWM (high liquidity)
- TLT, HYG (bond ETFs)
- GLD, SLV (commodity ETFs)

#### When to Use
- Neutral to slightly bullish outlook
- Want to generate income
- Willing to cap upside

### 10.2 Cash-Secured Puts

#### Strategy
- Sell out-of-the-money puts
- Collect premium
- If assigned, own ETF at effective discount

#### Best Use Cases
- Want to acquire ETF at lower price
- Bullish long-term but want income now
- Higher IV environments

### 10.3 Collar Strategy

#### Strategy
- Own ETF
- Buy protective put
- Sell covered call to finance put
- Limits both upside and downside

#### When to Use
- Want to hold ETF but limit risk
- Expecting volatility
- Protect gains without selling

### 10.4 Iron Condors

#### Strategy
- Sell OTM put spread
- Sell OTM call spread
- Profit if ETF stays in range
- Defined risk

#### Best ETFs
- Broad market ETFs (SPY, QQQ, IWM)
- Low volatility ETFs (USMV)
- Range-bound commodities (GLD)

### 10.5 Calendar Spreads

#### Strategy
- Sell near-term option
- Buy longer-term option at same strike
- Profit from time decay differential
- Works in low volatility

### 10.6 Leveraged ETF Options

#### Strategy
- Options on TQQQ, SQQQ, UVXY
- Higher leverage than underlying
- Extreme IV on UVXY
- Use for hedging or speculation

---

## 11. Data Sources & Tools

### Real-Time Data
| Source | Data Type | Cost |
|--------|-----------|------|
| Bloomberg Terminal | Full market data | High ($$$) |
| Refinitiv Eikon | ETF analytics | High ($$$) |
| FactSet | ETF flows, holdings | High ($$$) |
| TradingView | Charts, basic data | Free/Low |
| Yahoo Finance | Prices, basic NAV | Free |
| CME Group | Futures data | Free |

### ETF-Specific Data
| Source | Information |
|--------|-------------|
| ETF.com | Flows, premiums, analysis |
| ETF Database (ETFdb) | Screeners, comparisons |
| Morningstar | Ratings, analysis |
| ETF.com Flow Tool | Daily flow data |
| IHS Markit | iNAV data |
| ICE Data Services | ETF valuations |

### Calculated Data
| Metric | Source/Calculation |
|--------|-------------------|
| iNAV | Exchange disseminated (15 sec) |
| Premium/Discount | (Price - NAV) / NAV |
| Implied Liquidity | Bloomberg ETF implied liquidity |
| Creation Unit Size | Fund prospectus |
| Tracking Error | ETF return - Index return |

### API/Data Feeds
- **Alpaca**: Free equity/ETF data
- **Polygon.io**: Real-time and historical
- **IEX Cloud**: ETF data, affordable tiers
- **Quandl/NASDAQ Data Link**: Alternative data
- **FRED**: Economic data (free)

### Key Metrics to Monitor
1. **Premium/Discount to NAV** - Primary arb signal
2. **Bid-Ask Spread** - Liquidity indicator
3. **Volume** - Trading activity
4. **Implied Liquidity** - Market maker capacity
5. **Tracking Error** - Fund efficiency
6. **Expense Ratio** - Cost drag
7. **Flow Data** - Investor sentiment
8. **Options Open Interest** - Derivatives activity

---

## Summary: ETF-Specific Edges

### Structural Edges
1. **Creation/Redemption Mechanism** - Unique to ETFs
2. **Intraday Trading** - vs mutual funds
3. **Transparency** - Daily holdings disclosure
4. **Tax Efficiency** - In-kind redemptions

### Tactical Edges
1. **Sector Rotation** - Business cycle timing
2. **Factor Timing** - Macro regime awareness
3. **Premium/Discount** - NAV deviations
4. **Roll Yield** - Commodity futures curve
5. **Volatility Decay** - Leveraged ETF math

### Risk Considerations
1. **Liquidity varies** - Check implied liquidity
2. **Premium/Discount risk** - Especially international/bond
3. **Tracking error** - Not all ETFs track perfectly
4. **Counterparty risk** - Synthetic/derivative-based ETFs
5. **Tax implications** - Wash sale rules, K-1s (commodities)

---

*Compiled: February 2026*
*This catalog provides a comprehensive overview of ETF-specific strategies. Always conduct due diligence and consider your risk tolerance before implementing any strategy.*
