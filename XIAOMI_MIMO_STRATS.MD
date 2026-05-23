# XIAOMI MIMO — Overlooked Strategy Research
## Strategies MISSING from the Existing System (367+ implementations)

**Date:** 2026-04-18
**Purpose:** Deep research into trading/investment strategies across all asset classes that are NOT yet covered by the existing system.
**Existing system coverage:** RSI mean reversion, EMA crossovers, Bollinger bands, ATR volatility, volume breakouts, candlestick patterns, momentum/ROC, z-score reversion, funding rate arb, pairs trading, carry trades, basic factor strategies (BAB, QMJ), XGBoost/HMM/GRU-Attention/LightGBM models, basic cross-asset (BTC/SPX/VIX), DXY divergence, basic regime detection.

---

## TABLE OF CONTENTS

1. [Options & Volatility Strategies](#1-options--volatility-strategies)
2. [Fixed Income & Bond Strategies](#2-fixed-income--bond-strategies)
3. [Commodity Strategies](#3-commodity-strategies)
4. [Alternative & Exotic Strategies](#4-alternative--exotic-strategies)
5. [Real Assets & REITs](#5-real-assets--reits)
6. [Advanced ML & Quantitative Strategies](#6-advanced-ml--quantitative-strategies)
7. [Cross-Asset & Macro Strategies](#7-cross-asset--macro-strategies)
8. [Market Microstructure Strategies](#8-market-microstructure-strategies)
9. [Portfolio Construction & Risk Management](#9-portfolio-construction--risk-management)
10. [Implementation Roadmap](#10-implementation-roadmap)

---

## 1. Options & Volatility Strategies

### 1.1 Volatility Risk Premium Harvesting (Systematic Short Vol)

| Field | Detail |
|-------|--------|
| **Asset Class** | Equity index options (SPX, SPY, NDX), VIX futures |
| **Core Logic** | Implied volatility consistently exceeds realized volatility by 3-5% on average (the "variance risk premium"). Systematically selling options captures this spread. The premium exists because institutional investors overpay for hedging — they're structurally long gamma and willing to bleed theta for insurance. |
| **Key Indicators** | IV/RV ratio (entry when > 1.15), VIX spot level (scale inversely), realized vol regime (20-day rolling), put-call skew steepness, variance swap strike vs realized |
| **Holding Period** | 1-4 weeks (options selling cycle) |
| **Historical Edge** | CBOE PutWrite Index (PUT) returned ~10% annualized vs S&P 500 ~12% with ~30% less volatility since 2007. Documented extensively by Carr & Wu (2009). Persistent across decades and geographies. |
| **Complexity** | Medium-High — requires real-time options pricing, Greeks, dynamic sizing, tail hedges |
| **Correlation to Existing** | Low — uncorrelated to trend/momentum (directional) and pairs trading (relative value). Profits from level difference between IV and RV regardless of direction. |
| **Risk Factors** | Tail events (2008, 2020 COVID, Aug 2024 yen carry unwind). Requires strict position sizing (max 2-3% per unit vol). Margin expansion during crashes. Vanna/charm cascades. |

**Implementation Notes:** Scale entry by VIX level (full size VIX <15, half at 15-20, quarter at 20-25, pause >25). Always buy tail protection (20% OTM puts). Target theta/gamma ratio 3:1 minimum.

---

### 1.2 Gamma Scalping / Delta-Neutral Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Individual equity options, index options, commodity options |
| **Core Logic** | Buy straddles to own gamma, delta-hedge continuously. Profit when realized vol exceeds implied vol. Each rebalance captures gamma profit when underlying moves. |
| **Key Indicators** | Realized vs implied vol spread, IV percentile, upcoming catalyst dates, ATR vs option pricing, optimal hedge frequency |
| **Holding Period** | 1-14 days (around catalysts) or rolling 30-day |
| **Historical Edge** | Earnings straddles show 55-60% win rate when buying options with IV < 30th percentile before announcements. P&L proportional to (RV - IV) × position size. |
| **Complexity** | High — requires sub-second delta hedging, transaction cost modeling, real-time Greeks |
| **Correlation to Existing** | Zero directional correlation — market-neutral by design. Not pairs trading (single-name vol vs itself). |
| **Risk Factors** | Transaction costs erode gamma profits. Low RV environments make it hard to recoup theta. Pin risk. Gap risk overnight. |

---

### 1.3 Iron Condor Strategies with IV Rank Filtering

| Field | Detail |
|-------|--------|
| **Asset Class** | Index options (SPX, SPY, QQQ), sector ETFs |
| **Core Logic** | Sell OTM put spreads and OTM call spreads simultaneously — defined-risk short vol. IV rank filter ensures selling only when options are "expensive" relative to history. |
| **Key Indicators** | IV rank (>50% entry, >70% ideal), credit-to-width ratio (min 1/3), 45 DTE, 16-delta short strikes, 50% profit target, 2x credit stop |
| **Holding Period** | 21-45 days |
| **Historical Edge** | Tastytrade 15+ year backtests show 8-12% annualized with IV rank filter vs 4-6% without. Filter alone adds 3-5% annualized edge. |
| **Complexity** | Medium — four-leg but well-defined risk, automatable with options APIs |
| **Correlation to Existing** | Theta-based returns distinct from all directional strategies. Defined-risk structure differs from naked short vol. |
| **Risk Factors** | Commission slippage on 4-leg. Max loss 2-3x credit. Needs diversification across 5-8 uncorrelated underlyings. |

---

### 1.4 Calendar Spread Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Index options, equity options, commodity options |
| **Core Logic** | Sell near-term options, buy longer-term at same strike. Profits from accelerated theta decay of near-term leg vs slower decay of longer-term. Benefits from IV increases (longer-dated vega > shorter-dated). |
| **Key Indicators** | Term structure slope, IV level (best when low and expected to rise), ATM strike selection, upcoming events |
| **Holding Period** | 7-30 days |
| **Historical Edge** | Calendar spreads on SPX around FOMC show ~65% win rate (near-term IV crushes post-announcement while longer-term holds). |
| **Complexity** | Medium — two-leg, manageable risk |
| **Correlation to Existing** | Profits from time decay differential, not price direction — completely orthogonal to all existing strategies. |
| **Risk Factors** | Large price moves hurt (negative gamma). IV collapse in longer-dated post-event. Early assignment. |

---

### 1.5 VIX Term Structure Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | VIX futures (VX), VIX options, VIX-linked ETFs/ETNs |
| **Core Logic** | VIX futures term structure is in contango ~80% of time. Roll yield from contango is persistent, harvestable premium. When curve inverts to backwardation, front month converges faster — regime signal. |
| **Key Indicators** | VIX/VX1 ratio, contango steepness, VIX spot level, VIX9D/VIX ratio, VVIX (vol of vol) |
| **Holding Period** | 2-30 days |
| **Historical Edge** | Shorting front-month VIX futures during contango returned ~40-50% annualized on notional since 2004 (with severe drawdowns). Academic confirmation by Cheng (2019). |
| **Complexity** | Medium — two futures, clear signal. Simpler than options-based. |
| **Correlation to Existing** | Negative correlation to equity trend during crises. Uncorrelated in calm periods. |
| **Risk Factors** | Extreme drawdown potential (Volmageddon — XIV lost 90%+ in one day). Requires aggressive risk management. |

**Implementation Notes:** Only short VIX futures when contango >5% AND VIX <20. Hard stop at 20% loss. Consider VIX put spreads for defined risk.

---

### 1.6 Dispersion Trading (Index vs Components)

| Field | Detail |
|-------|--------|
| **Asset Class** | Index options (SPX, NDX, SX5E) vs component stock options |
| **Core Logic** | Index implied correlation is overpriced vs realized because investors pay up for index-level hedging. Sell index vol + buy component stock vol = short correlation. Profit when realized correlation < implied. |
| **Key Indicators** | Implied correlation, realized correlation (rolling 20-day), correlation risk premium, sector dispersion, earnings season timing |
| **Holding Period** | 1-3 months |
| **Historical Edge** | Implied correlation on SPX averaged 0.65 vs realized ~0.50 over 20 years. BNP Paribas (2025): correlation risk premium averages 10-15 index points on SX5E. Capstone, Citadel, Assenagon all run significant dispersion books. |
| **Complexity** | High — 50-500 options positions simultaneously |
| **Correlation to Existing** | Uncorrelated to all strategies — isolates pure correlation risk premium. Even short vol captures variance premium, not correlation premium. |
| **Risk Factors** | Correlation spikes to 1.0 during crises. Execution complexity. Stock borrow costs. Single-stock options liquidity. |

---

### 1.7 Skew Trading (Put-Call Skew Arbitrage)

| Field | Detail |
|-------|--------|
| **Asset Class** | Index options, equity options |
| **Core Logic** | Volatility skew is not constant — steepens and flattens. Trade changes in the shape of the vol surface, not level. Buy cheap skew, sell expensive skew. |
| **Key Indicators** | 25-delta put-call IV spread, skew percentile, risk reversal pricing, butterfly spreads at wings |
| **Holding Period** | 1-30 days |
| **Historical Edge** | 25-delta skew on SPX has half-life of ~15 days (Derman 1999). BNP Paribas (2025): skew-inclusive dispersion strategies generate 2-4% additional annualized alpha. |
| **Complexity** | High — multi-dimensional vol surface modeling |
| **Correlation to Existing** | Pure vol surface play — zero correlation to any price-directional strategy. |
| **Risk Factors** | Skew can stay at extremes. Execution costs across strikes. Model risk in surface fitting. |

---

### 1.8 Tail Risk Hedging via Put Spreads

| Field | Detail |
|-------|--------|
| **Asset Class** | Index options (SPX, SPY), equity options |
| **Core Logic** | Buy OTM put spreads for convex payoff profiles that benefit from crashes. Defined cost, defined max payoff. Alpha in timing — buy protection when cheap (low VIX, flat skew). |
| **Key Indicators** | VIX level (buy when <12-14), skew flatness, cost as % portfolio (<0.5%/month), catalyst calendar |
| **Holding Period** | 1-3 months |
| **Historical Edge** | 5% OTM put spreads cost ~0.3%/month, pay 5-10x in crashes. Taleb's Universa fund reportedly returns 20%+ annualized. "Barbell" approach improves Sharpe by 0.2-0.4. |
| **Complexity** | Low-Medium — two-leg, defined risk, automatable |
| **Correlation to Existing** | Maximum negative correlation to trend during crashes — put spreads pay immediately while trend takes time to react. True portfolio diversification. |
| **Risk Factors** | Cost drag in flat/rising markets. Timing risk. Expensive when IV already elevated. |

---

### 1.9 Systematic Covered Call Writing

| Field | Detail |
|-------|--------|
| **Asset Class** | Individual equities, equity ETFs (SPY, QQQ, sector ETFs) |
| **Core Logic** | Own underlying, systematically sell OTM calls. Collect theta while retaining upside. Systematic version uses IV rank + trend filter to optimize strike/timing. |
| **Key Indicators** | IV rank (>50th percentile), trend filter (mild uptrends only), 30-delta strike, 30-45 DTE, avoid earnings |
| **Holding Period** | 30-45 days per cycle |
| **Historical Edge** | BXM Index returned ~9% annualized vs S&P ~10% since 1988 but with ~25% less vol. Systematic with IV rank outperforms naive buy-write by 2-3%. JEPI gathered $35B+ AUM. |
| **Complexity** | Low — one short call per 100 shares, easily automated |
| **Correlation to Existing** | Provides income in flat markets where momentum loses. Different return profile from all existing strategies. |
| **Risk Factors** | Caps upside in strong rallies. Early assignment risk. Stock-specific risk remains. |

---

### 1.10 PMCC (LEAPS Diagonal Spreads)

| Field | Detail |
|-------|--------|
| **Asset Class** | Equity options with liquid LEAPS (AAPL, MSFT, SPY, QQQ) |
| **Core Logic** | Buy deep ITM LEAPS (delta 0.70-0.85) as stock replacement, sell shorter-dated OTM calls. Same premium as covered call with 60-70% less capital. |
| **Key Indicators** | LEAPS IV vs shorter-dated vol, underlying trend, IV rank, LEAPS delta 0.70-0.85, short call delta 0.20-0.30 |
| **Holding Period** | LEAPS: 6-24 months. Short call: 30-45 days (rolled). |
| **Historical Edge** | Backtests show 12-18% annualized on capital vs 8-10% for traditional covered calls. Capital efficiency is primary edge. |
| **Complexity** | Low-Medium — two legs, straightforward |
| **Correlation to Existing** | Leveraged long equity with income — partially correlated to momentum directionally but generates income in flat periods. |
| **Risk Factors** | LEAPS decay if stock drops (leveraged losses). Short call breach in rallies. LEAPS liquidity. |

---

## 2. Fixed Income & Bond Strategies

### 2.1 Yield Curve Factor Trading (Level, Slope, Curvature)

| Field | Detail |
|-------|--------|
| **Asset Class** | Government bonds, rates futures, swap spreads |
| **Core Logic** | Decompose yield curve into Nelson-Siegel factors: Level (parallel shift), Slope (short vs long), Curvature (belly vs wings). Each has different economic drivers and tradeable implications. |
| **Key Indicators** | Bond yields (2Y, 5Y, 10Y, 30Y), Nelson-Siegel loadings, factor z-scores, macro drivers (CPI for level, ISM/policy for slope, Treasury supply for curvature) |
| **Holding Period** | 5-60 days |
| **Historical Edge** | Diebold & Li (2006): Nelson-Siegel factors forecast yields better than random walk at 3-12 months. Curvature trades generate 2-4% annual returns as market-neutral rates strategy. |
| **Complexity** | Medium — Nelson-Siegel well-established. Bond futures basis and DV01-neutral construction add complexity. |
| **Correlation to Existing** | Very low — existing system has NO fixed income signals. Completely new signal domain. |
| **Risk Factors** | Factor instability during QE/QT. Basis risk between cash and futures. Financing costs. |

---

### 2.2 Credit-Equity Nexus

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, Credit (HY/IG bonds, CDS), Cross-asset |
| **Core Logic** | Credit markets often lead equities because credit investors are more risk-sensitive. Trade equity based on: HY spread level, HY spread momentum, credit-equity divergence, IG-HY spread. |
| **Key Indicators** | ICE BofA High Yield OAS, IG OAS, CDX indices, HY-IG spread, credit spread z-scores, credit-equity divergence |
| **Holding Period** | 5-30 days |
| **Historical Edge** | Gilchrist & Zakrajsek (2012): credit spread decomposition predicted GDP and equity returns R²=0.2-0.4. Huang & Kong (2003): credit leads equities by 1-3 months. Correctly identified 2016, 2018, 2022 buy ops and 2007-08, 2020 warnings. |
| **Complexity** | Low-Medium — credit spread data freely available on FRED. Trade via equity ETFs. |
| **Correlation to Existing** | Low-Medium — VIX is related but credit spreads contain different info (default risk vs implied vol). Credit-equity divergence is unique. |
| **Risk Factors** | Credit spread liquidity risk. Fed credit interventions distort signals. HY market composition changes. |

---

### 2.3 Bond Momentum & Trend Following

| Field | Detail |
|-------|--------|
| **Asset Class** | Government bonds, corporate bonds, bond ETFs |
| **Core Logic** | Bond returns exhibit momentum (3-12 month) driven by slow-moving yield trends. Long top-quartile bond performers, short bottom. Combine with carry signal (roll-down). |
| **Key Indicators** | 12-month bond returns, yield level, carry-to-volatility ratio, duration exposure |
| **Holding Period** | 3-12 months |
| **Historical Edge** | Asness et al. (2013) showed bond momentum earned 0.5-0.8% per month across 10 sovereign bond markets. Moskowitz et al. (2012) confirmed time-series momentum in bond futures with Sharpe ~0.7. |
| **Complexity** | Low — standard momentum computation. Bond futures trading. |
| **Correlation to Existing** | Low — existing system has no bond signals. |
| **Risk Factors** | Interest rate regime changes. Duration risk. Carry reversal during rate hiking cycles. |

---

### 2.4 Inflation-Linked Bond Relative Value

| Field | Detail |
|-------|--------|
| **Asset Class** | TIPS, inflation swaps, breakeven inflation |
| **Core Logic** | Trade the spread between nominal and inflation-linked bonds (breakeven inflation). When breakevens deviate from realized inflation expectations, mean-revert. |
| **Key Indicators** | 5Y/10Y breakeven inflation, realized CPI, inflation swap rates, Fed inflation forecasts |
| **Holding Period** | 1-6 months |
| **Historical Edge** | Breakeven inflation mean-reverts with half-life of 2-3 months. D'Amico et al. (2018) showed TIPS relative value strategies earned 1-2% annualized. |
| **Complexity** | Low-Medium — breakeven computation simple. TIPS liquidity can be thin. |
| **Correlation to Existing** | Very low — inflation-linked, entirely new signal. |
| **Risk Factors** | CPI revision risk. Liquidity in TIPS. Deflation protection feature distorts breakeven. |

---

### 2.5 Corporate Bond Factor Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Investment grade and high yield corporate bonds |
| **Core Logic** | Apply equity-style factors to credit: quality (leverage, coverage), value (spread vs default-adjusted fair value), momentum (return trend). Each factor earns premium in credit. |
| **Key Indicators** | OAS spread, credit rating, leverage ratio, interest coverage, 6-month return momentum |
| **Holding Period** | 1-6 months |
| **Historical Edge** | Israel, Palhares & Richardson (2018) showed credit factor strategies (quality+momentum+value) earned 2-3% annual alpha vs passive credit. |
| **Complexity** | Medium — requires bond-level data, credit analysis infrastructure |
| **Correlation to Existing** | Low — credit factors distinct from equity factors in existing system. |
| **Risk Factors** | Credit events (default/downgrade). Liquidity in corporate bonds. Factor crowding. |

---

## 3. Commodity Strategies

### 3.1 Term Structure / Roll Yield Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Commodity futures (energy, metals, agriculture) |
| **Core Logic** | Commodity futures term structure (contango/backwardation) generates roll yield. Backwardated markets: long futures earn positive roll yield. Contango markets: short futures earn roll yield. Systematically harvest this premium. |
| **Key Indicators** | Front-month vs back-month spread, term structure slope, inventory levels (EIA for oil, USDA for grains), convenience yield |
| **Holding Period** | 1-3 months (roll cycle) |
| **Historical Edge** | Erb & Harvey (2006): commodity roll yield earned 5-10% annualized across 30+ commodities. Fuertes, Miffre & Rallis (2010): term structure strategies Sharpe 0.5-0.8. |
| **Complexity** | Low-Medium — futures trading, roll computation |
| **Correlation to Existing** | Very low — existing system has no commodity term structure signals. |
| **Risk Factors** | Contango persistence (costly to hold). Supply shocks distort term structure. Roll costs. |

---

### 3.2 Gold/Silver Ratio Mean Reversion

| Field | Detail |
|-------|--------|
| **Asset Class** | Precious metals (gold futures, silver futures) |
| **Core Logic** | Gold/Silver ratio has historically mean-reverted around 60-70. Extreme ratios (>80 or <50) signal mispricing. Ratio reflects relative industrial demand (silver) vs safe-haven demand (gold). |
| **Key Indicators** | Gold/Silver ratio, ratio z-score (252-day), industrial production trends, risk appetite indicators |
| **Holding Period** | 3-12 months |
| **Historical Edge** | Mean-reversion profitable 75%+ of time at extremes. Ratio hit 120+ in March 2020 (COVID) then reverted to 65 within 18 months. |
| **Complexity** | Low — two futures, simple z-score |
| **Correlation to Existing** | Very low — precious metals pair trading not in existing system. |
| **Risk Factors** | Structural ratio shifts (silver industrial demand changes). Prolonged extremes. Futures roll costs. |

---

### 3.3 Energy Spread Trades

| Field | Detail |
|-------|--------|
| **Asset Class** | Energy futures — crack spread (refined products vs crude), spark spread (electricity vs natural gas), crush spread (soybean products vs beans) |
| **Core Logic** | Processing spreads represent the economics of converting raw commodities to products. When spreads deviate from historical norms, processing adjustments bring them back. |
| **Key Indicators** | Crack 3:2:1 spread, spark spread (heat rate × natgas price vs electricity price), crush ratio, seasonal patterns, refinery utilization rates |
| **Holding Period** | 2-8 weeks |
| **Historical Edge** | Processing spreads are mean-reverting with identifiable seasonal patterns. Haigh et al. (2004) showed crack spread strategies earned 8-15% annualized with low correlation to energy prices. |
| **Complexity** | Medium — requires multi-leg futures trading, seasonal modeling |
| **Correlation to Existing** | Very low — commodity processing spreads are unique. |
| **Risk Factors** | Refinery outages. Weather disruptions. Policy changes (carbon taxes). Basis risk between contract months. |

---

### 3.4 Commodity Seasonal Patterns

| Field | Detail |
|-------|--------|
| **Asset Class** | Agricultural commodities, energy (heating oil, natgas), precious metals |
| **Core Logic** | Commodity prices show persistent seasonal patterns driven by planting/harvest cycles, heating/cooling seasons, and jewelry demand. Systematic seasonal strategies exploit these calendar effects. |
| **Key Indicators** | Calendar month, historical seasonal profiles, inventory levels, weather forecasts, planting progress |
| **Holding Period** | 1-3 months (per seasonal window) |
| **Historical Edge** | Miffre (2016): seasonal commodity strategies earned 3-5% annual alpha. Heating oil shows strong Oct-Feb seasonal. Corn shows pre-planting premium (Mar-May). |
| **Complexity** | Low — calendar-based, simple historical analysis |
| **Correlation to Existing** | Very low — seasonal patterns are calendar-driven, independent of price signals. |
| **Risk Factors** | Seasonal patterns can break (climate change). Expanding/shifting seasons. Storage dynamics. |

---

## 4. Alternative & Exotic Strategies

### 4.1 DeFi Yield Farming & Basis Trades

| Field | Detail |
|-------|--------|
| **Asset Class** | Cryptocurrency (ETH, BTC, stablecoins on DeFi protocols) |
| **Core Logic** | Capture yield differentials between centralized and decentralized venues. Spot-perp basis on DEXes, lending rate arb across protocols, LP provision with hedged IL. |
| **Key Indicators** | DEX funding rates vs CEX, lending rate spreads, LP fee/APR, gas costs, smart contract audit status, TVL trends |
| **Holding Period** | Days to months |
| **Historical Edge** | DeFi basis trades on dYdX consistently showed 10-30% annualized in 2023-2025. Ethena's USDe grew to $6B+ TVL demonstrating scalability. |
| **Complexity** | Medium-High — smart contract interaction, multi-chain, gas optimization |
| **Correlation to Existing** | Uncorrelated to traditional strategies. CEX funding rate arb in existing system is separate market from DEX basis. |
| **Risk Factors** | Smart contract exploits, oracle manipulation, regulatory risk, bank-run dynamics, gas spikes. |

---

### 4.2 Liquid Staking Derivative Arbitrage

| Field | Detail |
|-------|--------|
| **Asset Class** | Cryptocurrency (stETH/ETH, cbETH/ETH, bSOL/SOL) |
| **Core Logic** | LSTs should trade 1:1 with native token but depeg due to liquidity constraints. Buy discount, wait for convergence. Hedge with short native perp (captures funding as bonus). |
| **Key Indicators** | LST/native ratio, redemption queue length, protocol TVL, staking APR vs DeFi rates, upcoming upgrades |
| **Holding Period** | Days to months |
| **Historical Edge** | stETH depegged to 0.93 ETH during 2022 collapse — recovered within weeks. Convergence profitable in 100% of historical instances for major LSTs. |
| **Complexity** | Low-Medium — buy LST, sell native perp |
| **Correlation to Existing** | Crypto-specific RV. Can combine LST discount + perp funding for stacked yield. |
| **Risk Factors** | Smart contract risk, extended depeg if protocol issues, slashing events, regulatory risk. |

---

### 4.3 Token Unlock / Vesting Schedule Trading

| Field | Detail |
|-------|--------|
| **Asset Class** | Cryptocurrency (tokens with upcoming large unlocks) |
| **Core Logic** | Token unlocks create predictable selling pressure. Market underestimates impact. Short tokens 7-14 days before unlocks (>5% of circulating supply), cover 7-14 days after. |
| **Key Indicators** | Unlock size as % circulating supply (>5% threshold), VC/insider holdings %, historical impact of prior unlocks, market sentiment |
| **Holding Period** | 2-4 weeks |
| **Historical Edge** | Tokens with >5% supply unlock underperform by 3-8% in 30-day window. ARB, OP, APT, SUI showed significant declines 2023-2024. |
| **Complexity** | Low-Medium — calendar-based, easily screened |
| **Correlation to Existing** | Event-driven alpha — uncorrelated to momentum/trend (may actually go long same period). Calendar-based signal independent of price signals. |
| **Risk Factors** | Short squeeze risk. Insiders may not sell. Borrow costs. Crypto rally can overwhelm unlock effect. |

---

### 4.4 Prediction Market Arbitrage

| Field | Detail |
|-------|--------|
| **Asset Class** | Event contracts (Polymarket, Kalshi) |
| **Core Logic** | Same events priced differently across prediction markets. Buy YES on cheaper platform, NO on more expensive. Synthetic arb — combine correlated events. |
| **Key Indicators** | Cross-platform price differentials, liquidity depth, settlement rules differences, fee structures |
| **Holding Period** | Hours to weeks |
| **Historical Edge** | $40M+ in extracted arb profits across Polymarket/Kalshi. Consistent 3-5 cent spreads on events expiring within days. DRW Holdings actively hiring prediction market traders. |
| **Complexity** | Medium — API integration with both platforms |
| **Correlation to Existing** | Uncorrelated to all financial market strategies — returns from event outcomes, not asset prices. |
| **Risk Factors** | Platform risk, liquidity limits, resolution ambiguity, capital lockup. |

---

### 4.5 Governance Token Value Accrual

| Field | Detail |
|-------|--------|
| **Asset Class** | Cryptocurrency (UNI, AAVE, MKR, CRV) |
| **Core Logic** | Governance tokens accrue value through revenue sharing, fee switches, or buybacks. Buy before governance votes to activate value accrual. Vote-escrow tokens reward long-term lockers. |
| **Key Indicators** | Revenue yield (revenue/market cap >5%), governance proposal activity, ve-token lockup metrics, fee switch proposals |
| **Holding Period** | Weeks to months |
| **Historical Edge** | MKR buyback drove 300%+ appreciation from 2023 lows. UNI fee switch speculation drove 40%+ rallies. CRV lockers earned 15-40% effective yield. |
| **Complexity** | Medium — governance monitoring, protocol revenue analysis |
| **Correlation to Existing** | Semi-correlated to crypto markets but driven by protocol-specific catalysts independent of broad direction. |
| **Risk Factors** | Governance attacks, smart contract risk, dilution, regulatory classification. |

---

### 4.6 RWA Token Yield Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Tokenized Treasuries, private credit tokens, real estate tokens |
| **Core Logic** | Tokenized RWAs bring traditional yields on-chain. Spread trade (borrow cheap stablecoins, earn higher RWA yield). RWA farming (protocol incentives + underlying yield). |
| **Key Indicators** | RWA token yield vs off-chain equivalent, incentive APR, credit risk, audit status, TVL growth |
| **Holding Period** | Months to years |
| **Historical Edge** | Ondo OUSG grew to $500M+ TVL at 4-5% yield. Centrifuge credit tokens yielded 8-12%. RWA sector grew 800%+ in 2023-2025. BlackRock BUIDL reached $1B+. |
| **Complexity** | Low-Medium — buy and hold for Treasuries |
| **Correlation to Existing** | Yields driven by traditional fixed income — partially correlated to rates. Provides real-world yield exposure absent from existing system. |
| **Risk Factors** | Smart contract risk, regulatory risk, default risk, KYC requirements. |

---

## 5. Real Assets & REITs

### 5.1 REIT Momentum and Mean Reversion

| Field | Detail |
|-------|--------|
| **Asset Class** | REITs (VNQ, IYR, individual REITs) |
| **Core Logic** | REITs exhibit strong momentum (3-12 month, slow lease repricing). Mean reversion at extremes (dividend yield anchoring). Buy top-quartile 6-month performers OR buy when yield spread vs 10Y Treasury >2σ. |
| **Key Indicators** | 6-month relative strength, dividend yield spread vs 10Y Treasury, FFO growth, occupancy rates, interest rate sensitivity |
| **Holding Period** | 3-12 months |
| **Historical Edge** | NAREIT: momentum factor delivers 2-4% annual alpha. Mean-reversion based on yield spread profitable 80%+ of time. Sector rotation adds 3-5% annually. |
| **Complexity** | Low — publicly traded ETFs, standard equity execution |
| **Correlation to Existing** | Semi-correlated to equity momentum but different sector exposure. Dividend-focused returns add income component. |
| **Risk Factors** | Interest rate risk, sector concentration, leverage, dividend cuts. |

---

### 5.2 Real Estate Sector Rotation

| Field | Detail |
|-------|--------|
| **Asset Class** | REIT sector ETFs |
| **Core Logic** | Different real estate sectors respond differently to cycles. Rotate based on: ISM PMI (industrial), employment (office), e-commerce growth (warehouse), cloud capex (data centers). |
| **Key Indicators** | ISM PMI, employment data, e-commerce growth rate, cloud capex trends, cap rate spreads |
| **Holding Period** | 6-18 months |
| **Historical Edge** | Sector rotation adds 3-5% annual alpha vs passive REIT indices. Industrial REITs outperformed office by 300%+ over 2015-2025. Data centers outperformed by 200%+ since 2020. |
| **Complexity** | Low — ETF-based, simple screening |
| **Correlation to Existing** | Real asset exposure uncorrelated to equity momentum. Interest rate sensitivity differs from equity beta. |

---

### 5.3 MLP Yield Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | MLPs (AMLP, EPD, ET, MPLX) |
| **Core Logic** | High distribution yields (6-8%) from midstream energy infrastructure. Alpha from yield spread over Treasuries, distribution growth, tax-deferred income. |
| **Key Indicators** | Yield spread vs 10Y (>4% entry), distribution coverage (>1.2x), growth streak (5+ years), leverage (<4x debt/EBITDA) |
| **Holding Period** | 1-5 years |
| **Historical Edge** | AMLP returned ~10% annualized (2010-2025) with ~7% yield. MLPs with >1.2x coverage and 5-year growth streak outperformed by 4-6%. Low correlation (0.3-0.4) to equities. |
| **Complexity** | Low — ETF available, simple screening |
| **Correlation to Existing** | High income provides cash flow in flat/declining markets. Energy infrastructure exposure unique. |

---

## 6. Advanced ML & Quantitative Strategies

### 6.1 Temporal Fusion Transformer (TFT)

| Field | Detail |
|-------|--------|
| **Asset Class** | All liquid assets with sufficient history |
| **Core Logic** | TFT combines LSTM + multi-head attention for multi-horizon probabilistic forecasts. Variable selection networks auto-gate features. Static covariate encoding for asset metadata. |
| **Key Indicators** | Same features as current pipeline + static metadata, known future inputs (earnings, FOMC), multi-resolution time series |
| **Holding Period** | 1-20 days |
| **Historical Edge** | Lim et al. (2021): 7-15% improvement over DeepAR/N-BEATS. Woo et al. (2022): ~5-8% Sharpe improvement over LSTM on S&P 500. |
| **Complexity** | High — PyTorch, custom multi-horizon pipeline, training 10-50x slower than trees |
| **Correlation to Existing** | Low — GRU-Attention is single-horizon sequential. TFT adds multi-horizon, variable selection, static covariates. Complementary. |
| **Risk Factors** | Overfitting on small datasets. Computational cost. Attention noise. |

---

### 6.2 Graph Neural Networks for Market Structure

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities (sector ETFs), Multi-asset (equities→rates→commodities→FX) |
| **Core Logic** | Model market as dynamic graph: nodes=assets, edges=statistical relationships. GNN learns relational embeddings encoding contagion, spillover, structural change. |
| **Key Indicators** | Rolling correlation matrices, Granger causality, supply chain data, institutional ownership overlap, ETF flows |
| **Holding Period** | 5-30 days |
| **Historical Edge** | Chen et al. (2022): GNN improved ranking IC by 15-25%. Li et al. (2024): GNN-implied contagion predicted sector drawdowns 3-5 days ahead in COVID crash. |
| **Complexity** | High — graph construction, GNN framework, GPU training |
| **Correlation to Existing** | Very low — existing models are point-in-time for individual assets. GNN explicitly models inter-asset relationships. |
| **Risk Factors** | Graph construction quality is bottleneck. Stationarity of graph structure. Limited data for rare topological events. |

---

### 6.3 Ensemble Meta-Learning (Strategy Selection)

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-strategy portfolio |
| **Core Logic** | Meta-learner predicts which strategy performs best in current market state. Takes regime indicators + recent strategy performance + market state as input. Outputs time-varying weights. Fundamentally different from stacking — combines allocation decisions, not predictions. |
| **Key Indicators** | Per-strategy rolling Sharpe/hit rate, regime indicators, signal strength distribution, market state |
| **Holding Period** | 1-30 days |
| **Historical Edge** | Liang et al. (2022): meta-learned weights improved Sharpe 0.4-0.8 over equal-weighted ensembles across 50+ strategies. Citadel/Millennium meta-allocation layer is significant alpha source. |
| **Complexity** | Medium-High — backtesting infra, walk-forward CV, handling strategies entering/exiting |
| **Correlation to Existing** | Low correlation with signals, high complementarity. This is the "strategy of strategies" layer. |
| **Risk Factors** | Meta-learner overfitting. Regime detection lag. Transaction costs. Correlated strategy failures. |

---

### 6.4 Alpha Decay Monitoring

| Field | Detail |
|-------|--------|
| **Asset Class** | All (meta-monitoring layer) |
| **Core Logic** | Monitor predictive power of each feature/model over time. When importance decays below threshold: reduce weight, flag for retraining, or reduce allocation. Edge isn't generating alpha — it's preserving it. |
| **Key Indicators** | Rolling SHAP values, rolling IC, rolling model performance, PSI (Population Stability Index), concept drift tests (ADWIN, CUSUM) |
| **Holding Period** | N/A (monitoring layer) |
| **Historical Edge** | De Prado (2018): alpha decay is #1 reason quant strategies fail. WorldQuant systematically decommissions factors based on decay metrics. |
| **Complexity** | Medium — logging infra, statistical tests, automated alerts |
| **Correlation to Existing** | Orthogonal meta-layer. No existing component does this systematically. |
| **Risk Factors** | False positives during regime change. Removing features about to re-activate. Noisy importance metrics. |

---

### 6.5 Online Learning / Adaptive Models

| Field | Detail |
|-------|--------|
| **Asset Class** | All liquid markets (primarily intraday) |
| **Core Logic** | Update model weights with each new data point via streaming gradient descent. Track non-stationary "optimal" weights in real-time. Faster adaptation than batch retraining. |
| **Key Indicators** | Learning rate schedules, forgetting factors, concept drift detectors (ADWIN, Page-Hinkley) |
| **Holding Period** | Intraday to 5 days |
| **Historical Edge** | Gomes et al. (2019): online ensembles maintained 60-70% peak alpha over 2 years vs 30-40% for batch models. Backbone of HFT signal engines. |
| **Complexity** | Medium — online normalization, memory management, drift detection |
| **Correlation to Existing** | Medium (different execution) — replaces training paradigm, not model family. Can run online + batch side by side. |
| **Risk Factors** | Catastrophic forgetting. Learning rate sensitivity. Amplified noise. Harder to validate. |

---

### 6.6 NLP for Earnings Calls & Fed Speeches

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities (earnings), FX/Rates (Fed), broad market (aggregate sentiment) |
| **Core Logic** | Fine-tuned LLMs extract sentiment (hawkish/dovish), topics, and linguistic anomalies from transcripts/speeches. Information asymmetry — NLP processes 1000s of transcripts faster than humans. |
| **Key Indicators** | Earnings call transcripts, FOMC statements/minutes, Fed speeches. Models: FinBERT, BloombergGPT, fine-tuned Llama/Mistral |
| **Holding Period** | 1-10 days |
| **Historical Edge** | Ke et al. (2019): FinBERT sentiment on earnings calls predicted PEAD with IC 0.05-0.08. Shapiro & Wilson (2022): Fed hawkishness scores predicted rate decisions 1-2 weeks ahead. |
| **Complexity** | Medium-High — real-time transcript feed, NLP pipeline, point-in-time data |
| **Correlation to Existing** | Very low — existing system is purely price/volume. Text data is entirely orthogonal information source. |
| **Risk Factors** | Model misinterpretation. Transcript delays. Language model drift. Sentiment can lag market reaction. |

---

### 6.7 Markov-Switching & Threshold Models

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, FX, rates, commodities |
| **Core Logic** | HMM assumes Gaussian emissions. MS-AR adds regime-dependent autoregressive dynamics. Threshold models (TAR) use deterministic threshold variables (e.g., VIX >30 → regime 2). Better regime boundary detection. |
| **Key Indicators** | Price/return series, threshold variables (VIX, yield spread, credit spread, PMI), lagged regime indicators |
| **Holding Period** | 5-60 days |
| **Historical Edge** | Ang & Bekaert (2002): MS-2 improved portfolio Sharpe 0.2-0.4. Hansen (1992): SETAR outperformed linear ARIMA for FX in rate-differential regimes. |
| **Complexity** | Medium — statsmodels has MS-AR. TAR simpler but needs threshold variable selection. |
| **Correlation to Existing** | Low-Medium — complementary to existing HMM. MS-AR allows AR dynamics within regimes. TAR adds deterministic threshold logic. |

---

### 6.8 Extreme Value Theory for Crash Prediction

| Field | Detail |
|-------|--------|
| **Asset Class** | All liquid markets |
| **Core Logic** | EVT models extreme returns separately via Generalized Pareto Distribution. Gives accurate VaR at extreme confidence (99%+), tail index as regime indicator, time-varying tail risk signals. |
| **Key Indicators** | Returns series, GARCH-filtered returns, threshold selection, tail index (ξ) and scale (β) |
| **Holding Period** | 1-10 days |
| **Historical Edge** | McNeil & Frey (2000): EVT-based VaR outperformed parametric VaR during crashes. Bali (2003): extreme risk measures predicted cross-sectional returns ~1%/month. |
| **Complexity** | Medium — threshold selection is sensitive step. GARCH pre-filtering needed. |
| **Correlation to Existing** | Medium with HMM (both detect bad regimes) but different mechanism. EVT focuses on tail behavior specifically. Can be used as feature in existing models. |

---

## 7. Cross-Asset & Macro Strategies

### 7.1 Global Macro Factor Models

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-asset (equities, bonds, commodities, FX, TIPS) |
| **Core Logic** | Extract latent macro factors (Growth, Inflation, Real Rates, Risk Appetite) from cross-section of assets. Use PCA or factor mimicking portfolios. Allocate to assets benefiting from current factor direction. |
| **Key Indicators** | Growth: ISM, IP, payrolls, copper. Inflation: breakevens, commodities. Real rates: TIPS. Risk appetite: VIX, credit, put/call. 15-30 macro series daily. |
| **Holding Period** | 1-3 months |
| **Historical Edge** | Menkhoff et al. (2012): factors explain 40-60% of cross-asset variation. Ilmanen (AQR, 2019): factor timing adds 1-2% annualized. |
| **Complexity** | Medium — PCA straightforward. Mixed-frequency data handling is harder. |
| **Correlation to Existing** | Medium — richer than existing pairwise (BTC/SPX/VIX, DXY). Can decompose existing signals into factor contributions. |

---

### 7.2 Intermarket Ratio Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Commodities, Equities — Gold/Oil, Copper/Gold, Stocks/Bonds, Silver/Gold |
| **Core Logic** | Ratios encode relative macro info: Copper/Gold = growth sentiment, Gold/Oil = inflation dynamics, Silver/Gold = risk appetite. Trade when ratios deviate from macro-implied equilibrium. |
| **Key Indicators** | Ratio z-scores (60d-252d), macro context (PMI, USD direction) |
| **Holding Period** | 5-60 days |
| **Historical Edge** | Goldman Sachs (2020): Copper/Gold predicted 10Y yields R²=0.6 at 3-month. Gold/Oil predicted 7/9 inflation regime changes since 1980. |
| **Complexity** | Low-Medium — ratios and z-scores simple to compute |
| **Correlation to Existing** | Low — relative value signals within asset classes. Copper/Gold growth signal not captured by SPX or VIX alone. |

---

### 7.3 Inflation Regime Trading

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-asset (TIPS, commodities, equities, bonds, gold, REITs) |
| **Core Logic** | Different assets in different inflation regimes. Rising: commodities, TIPS, energy. Falling: growth equities, long bonds. Stable: risk assets, carry. Detect regime and tilt portfolio. |
| **Key Indicators** | CPI/PCE trends, breakeven rates, commodity basket, yield curve slope, inflation surprise index, wage growth |
| **Holding Period** | 1-6 months |
| **Historical Edge** | Arnott & Harvey (2021): simple inflation regime strategy added 2-3% annual returns vs 60/40 over 1926-2020. 2021-2023 was strong real-world validation. |
| **Complexity** | Low-Medium — threshold on CPI trend simple. Asset switching needs multi-asset infra. |
| **Correlation to Existing** | Low — existing system doesn't model inflation regimes. Slow-moving macro indicators orthogonal to technical signals. |

---

### 7.4 Economic Surprise Index Trading

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, FX, Rates, Commodities |
| **Core Logic** | Citi Economic Surprise Index measures whether data beats/misses consensus. Sustained positive surprises → bullish risk. Extremes mean-revert. Cross-asset implications (positive → higher yields, stronger FX). |
| **Key Indicators** | CESI (US, EU, Japan, EM), component surprises, CESI momentum (20d), level extremes (>+50 or <-50) |
| **Holding Period** | 5-30 days |
| **Historical Edge** | Pratley (2011): buying equities on rising CESI returned 8-12% annualized. Extremes (>+80 or <-80) preceded reversals with 70% accuracy. 60%+ directional accuracy since 2000. |
| **Complexity** | Very Low — CESI freely on Bloomberg, simple rules |
| **Correlation to Existing** | Low — economic data-derived, fundamentally different from price-based signals. |

---

### 7.5 PMI Regime Strategies

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities (cyclicals vs defensives), Commodities, FX |
| **Core Logic** | PMI >50 = expansion. But direction matters more: PMI rising from below 50 → buy cyclicals; peaking above 50 → add commodities; falling from above 50 → rotate to defensives; bottoming below 50 → build cyclical positions. |
| **Key Indicators** | ISM Manufacturing/Services PMI, Global PMI, PMI momentum (3-month change), new orders sub-index |
| **Holding Period** | 1-3 months |
| **Historical Edge** | MSCI (2019): PMI rotation outperformed static allocation by 2-4% annualized. ISM below 45 = high recession probability (7/8 NBER recessions). New orders-to-inventory ratio predicted direction 65% accuracy. |
| **Complexity** | Very Low — single indicator, fixed schedule |
| **Correlation to Existing** | Low — slow-moving macro rotation orthogonal to fast technical signals. |

---

### 7.6 Safe Haven Flow Detection

| Field | Detail |
|-------|--------|
| **Asset Class** | FX (JPY, CHF, USD), Gold, Treasuries, VIX |
| **Core Logic** | Detect capital flowing from risk to safe havens. Volume/momentum in havens without catalyst, cross-asset correlation spikes, funding market stress. Use as risk-off signal for defensive rotation. |
| **Key Indicators** | JPY/CHF momentum, Gold momentum + ETF flows, Treasury yield changes, VIX term structure, credit spreads, FRA-OIS, put/call ratio, EPFR fund flows |
| **Holding Period** | 1-15 days |
| **Historical Edge** | Baur & Lucey (2010): gold confirmed safe haven in extreme drawdowns. Ranaldo & Söderlind (2010): JPY/CHF appreciated 2-5% in top-decile risk-off. Preceded worst drawdown days in 2008, 2011, 2020. |
| **Complexity** | Medium — multi-asset data, flow data, composite indicator |
| **Correlation to Existing** | Medium with VIX but more robust. Composite of JPY, CHF, gold, Treasuries, credit is less noisy than VIX alone. |

---

### 7.7 Currency Carry with Volatility Targeting

| Field | Detail |
|-------|--------|
| **Asset Class** | G10 and EM FX |
| **Core Logic** | Classic carry (borrow low-yield, invest high-yield) with vol targeting: scale inversely to realized vol. Carry collected in low-vol (size up), losses mitigated in high-vol (size down). Add momentum filter and drawdown deleveraging. |
| **Key Indicators** | Overnight rate differentials, realized vol (20d-60d, target 8-10% annual), momentum (3m-12m), drawdown state |
| **Holding Period** | 1-3 months |
| **Historical Edge** | Barroso & Santa-Clara (2015): vol-scaled carry doubled Sharpe (0.8→1.6). Lustig et al. (2011): carry factor returns compensate for crash risk; vol-targeting makes it consistent. |
| **Complexity** | Medium — FX forward infrastructure, daily vol adjustment |
| **Correlation to Existing** | Low — DXY is directional USD. Carry is relative value across currencies driven by rate differentials. |

---

### 7.8 Cross-Asset Momentum

| Field | Detail |
|-------|--------|
| **Asset Class** | 50-100 futures/equity index/bond/commodity/FX instruments |
| **Core Logic** | Momentum applied across all asset classes. Rank by 12-1 month return, long top decile, short bottom, vol-weight. Broader diversification than single-class momentum. |
| **Key Indicators** | 12-1 month returns, volatility scaling (10-12% annual vol target), transaction cost model |
| **Holding Period** | 1-12 months |
| **Historical Edge** | Asness, Moskowitz & Pedersen (2013): cross-asset momentum earned 1.0%/month, Sharpe ~0.8, negatively correlated with value. Moskowitz, Ooi & Pedersen (2012): time-series momentum across 58 futures, Sharpe 1.4. One of most robust anomalies in finance. |
| **Complexity** | Medium — signal trivial, execution in multi-asset portfolio management |
| **Correlation to Existing** | Medium-Low — existing ranking likely within equities only. Extends to all asset classes. |

---

## 8. Market Microstructure Strategies

### 8.1 Order Flow Imbalance (OFI)

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, Futures, Crypto |
| **Core Logic** | Net buying pressure from market orders. Persistent positive OFI → price rises. Predict using historical OFI patterns, order book imbalance, trade size distribution. |
| **Key Indicators** | Tick-by-tick trades with aggressor side, L2 order book, OFI time series, volume bars, trade size buckets |
| **Holding Period** | Minutes to hours |
| **Historical Edge** | Cont et al. (2014): OFI R²=0.15-0.30 for 5-min ahead returns. Cartea et al. (2014): 5-10 bps per trade net of costs. One of most robust microstructure signals. |
| **Complexity** | High — real-time tick data, low-latency execution |
| **Correlation to Existing** | Zero — existing system has no tick-level signals. Completely different data granularity. |
| **Risk Factors** | Execution slippage. Adverse selection. Infrastructure cost. Signal decay. |

---

### 8.2 VPIN (Volume-Synchronized Probability of Informed Trading)

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, Futures, Crypto |
| **Core Logic** | Estimate probability of informed (toxic) trading. High VPIN → high adverse selection risk, often precedes large moves or flash crashes. Use as risk filter (reduce activity when toxic). |
| **Key Indicators** | Tick data, Bulk Volume Classification, equal-volume buckets, VPIN threshold |
| **Holding Period** | Hours to days |
| **Historical Edge** | Easley, de Prado & O'Hara (2012): VPIN preceded May 2010 Flash Crash by hours. Predicts info events 1-2 days ahead with 60%+ accuracy. Primary edge is adverse selection avoidance. |
| **Complexity** | Medium — computation straightforward, tick data needed |
| **Correlation to Existing** | Low — microstructure risk/flow measure. Can serve as meta-filter on existing strategies. |

---

### 8.3 Market Maker Inventory Signals

| Field | Detail |
|-------|--------|
| **Asset Class** | Equities, Futures, FX |
| **Core Logic** | Market makers adjust quotes to manage inventory. When long inventory → offer cheaper asks → short-term bullish. When short → raise bids → bearish. Estimate from net trade flow, quote skewness. |
| **Key Indicators** | Trade data with aggressor side, quote data, spread, quote skew, net dealer flow |
| **Holding Period** | Minutes to hours |
| **Historical Edge** | Hendershott & Menkveld (2014): inventory positions predicted next-hour returns IC=0.04-0.06. Strongest around market close and during volatile periods. |
| **Complexity** | High — tick data, trade classification, real-time computation |
| **Correlation to Existing** | Zero — tick-level microstructure signal. |

---

## 9. Portfolio Construction & Risk Management

### 9.1 Dynamic Kelly Criterion Position Sizing

| Field | Detail |
|-------|--------|
| **Asset Class** | All (position sizing layer) |
| **Core Logic** | Kelly: f* = (p×b - q)/b. Use fractional Kelly (1/4 to 1/2) with dynamic win rate estimation. Adjust p and b per regime. Cap max fraction. Mathematically optimal for log-wealth growth. |
| **Key Indicators** | Rolling win rate, avg win/loss ratio, trade sample size, regime state, strategy correlations |
| **Holding Period** | N/A (sizing layer) |
| **Historical Edge** | Thorp (2006): Kelly grows wealth fastest long-run. Half-Kelly achieves 75% growth with 50% drawdown. Renaissance Technologies uses Kelly-like sizing. |
| **Complexity** | Medium — formula simple. Non-stationary win rates and portfolio Kelly (correlated strategies) harder. |
| **Correlation to Existing** | Orthogonal — doesn't change signals, changes capital allocation. |
| **Risk Factors** | Estimation error. Full Kelly 50%+ drawdowns. Non-stationarity. |

---

### 9.2 Hierarchical Risk Parity (HRP)

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-asset portfolio |
| **Core Logic** | HRP uses hierarchical clustering: identify natural asset groups, allocate within clusters first, then across. Avoids covariance matrix inversion instability. Regime-conditional covariance: different matrices per regime. |
| **Key Indicators** | Returns series, Ledoit-Wolf covariance, regime labels, hierarchical clustering linkage |
| **Holding Period** | Monthly rebalancing |
| **Historical Edge** | De Prado (2016): HRP outperformed Markowitz by 0.5-1.0 Sharpe, 30-50% lower turnover. Bridgewater's Pure Alpha uses risk parity principles (~12% annual). |
| **Complexity** | Medium — algorithm straightforward. Transaction cost management and multi-asset execution harder. |
| **Correlation to Existing** | Complementary portfolio construction layer. Principled replacement for heuristic construction. |

---

### 9.3 Drawdown-Aware Portfolio Optimization

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-asset portfolio |
| **Core Logic** | CVaR optimization (minimize tail risk), Max Drawdown constraint, CPPI (allocate to risky assets proportionally to cushion above floor). Mechanical de-risking prevents catastrophic losses. |
| **Key Indicators** | NAV, current drawdown, drawdown distribution, CPPI multiplier/floor, return distributions |
| **Holding Period** | Daily monitoring, rebalance on threshold breach |
| **Historical Edge** | Chekhlov et al. (2005): drawdown-constrained improved Sharpe 0.2-0.4. CPPI limited 2008 drawdown to ~25% vs 50%+ unhedged. |
| **Complexity** | Medium — CPPI simple, CVaR optimization needs scenarios |
| **Correlation to Existing** | Orthogonal risk layer. No existing component explicitly manages drawdowns. |

---

### 9.4 Correlation Regime Detection

| Field | Detail |
|-------|--------|
| **Asset Class** | Multi-asset portfolio |
| **Core Logic** | Correlations spike during crises (diversification fails when needed). Detect regimes: low corr (normal), high corr (crisis — reduce exposure), mixed (increase havens). Use eigenvalue concentration of correlation matrix. |
| **Key Indicators** | Rolling correlation matrices, average pairwise correlation, eigenvalue distribution, condition number, minimum spanning tree changes |
| **Holding Period** | Days to weeks |
| **Historical Edge** | Longin & Solnik (2001): equity correlations increase in bear markets. Kinlaw et al. (2013): eigenvalue-based detection improved Sharpe 0.3-0.5. |
| **Complexity** | Medium — correlation estimation standard, eigenvalue decomposition straightforward |
| **Correlation to Existing** | Medium with HMM — focused specifically on correlation structure, not return/vol regimes. |

---

### 9.5 Transaction Cost Optimization

| Field | Detail |
|-------|--------|
| **Asset Class** | All (portfolio construction layer) |
| **Core Logic** | Subtract estimated costs from expected returns. Add turnover penalty. No-trade regions (only rebalance if benefit > cost). Incorporate market impact models. |
| **Key Indicators** | Bid-ask spreads, impact estimates, commissions, current weights, liquidity measures |
| **Holding Period** | Rebalance only when cost-adjusted benefit exceeds threshold |
| **Historical Edge** | Garleanu & Pedersen (2013): cost-aware optimization reduced turnover 40-60% while maintaining 90%+ gross alpha. 10 bps cost reduction on monthly rebalancing = 1.2% annual returns. |
| **Complexity** | Medium — cost model integration, no-trade region computation |
| **Correlation to Existing** | Orthogonal — changes execution decisions, not signals. Always beneficial. |

---

## 10. Implementation Roadmap

### TIER 1 — Highest Value, Lowest Complexity (Implement First)

| # | Strategy | Asset Class | Why |
|---|----------|-------------|-----|
| 1 | Credit-Equity Nexus | Cross-asset | Low complexity, strong edge, new signal domain |
| 2 | Inflation Regime Trading | Multi-asset | Validated by 2021-2023, simple threshold |
| 3 | Economic Surprise Index | Multi-asset | Very low complexity, solid edge |
| 4 | PMI Regime Strategies | Multi-asset | Simple rotation framework |
| 5 | Iron Condors + IV Rank | Options | Well-documented edge, defined risk |
| 6 | Tail Risk Hedging | Options | Portfolio insurance, improves overall Sharpe |
| 7 | Token Unlock Trading | Crypto | Calendar-based, easily screened |
| 8 | LSD Arbitrage | Crypto | Low complexity, high convergence reliability |
| 9 | MLP Yield Strategies | Real assets | Simple, high income, low correlation |
| 10 | Intermarket Ratios | Commodities | Intuitive macro signals, low complexity |
| 11 | Alpha Decay Monitoring | Meta-layer | Preserves existing alpha |
| 12 | Covered Call Writing | Options | Easy, consistent income |

### TIER 2 — Strong Edge, Moderate Complexity

| # | Strategy | Asset Class | Why |
|---|----------|-------------|-----|
| 13 | Volatility Risk Premium | Options | Persistent structural premium |
| 14 | VIX Term Structure | Vol/Futures | Well-documented, needs risk mgmt |
| 15 | Commodity Term Structure | Commodities | Roll yield premium |
| 16 | Gold/Silver Ratio | Precious metals | Mean-reverting, intuitive |
| 17 | Ensemble Meta-Learning | Multi-strategy | "Strategy of strategies" layer |
| 18 | Yield Curve Factors | Fixed income | Entirely new asset class |
| 19 | Prediction Market Arb | Events | Growing market, institutional entry |
| 20 | DeFi Basis Trades | Crypto | Uncorrelated, crypto-native |
| 21 | Currency Carry + Vol Target | FX | Proven Sharpe improvement |
| 22 | Global Macro Factors | Multi-asset | Rich multi-dimensional signal |
| 23 | Safe Haven Flow Detection | Cross-asset | Crisis protection |
| 24 | Energy Spreads | Commodities | Seasonal, mean-reverting |
| 25 | Bayesian Optimization | Meta-layer | Improves all existing strategies |

### TIER 3 — Highest Alpha, Highest Complexity

| # | Strategy | Asset Class | Why |
|---|----------|-------------|-----|
| 26 | Dispersion Trading | Options | Structural alpha, implementation-heavy |
| 27 | Cross-Asset Momentum | Multi-asset | Most robust anomaly, needs infra |
| 28 | TFT (Temporal Fusion Transformer) | ML | Strong ML upgrade, GPU-intensive |
| 29 | Graph Neural Networks | ML | Novel market structure signal |
| 30 | RL Portfolio Management | ML | End-to-end optimization, unstable training |
| 31 | NLP for Fed/Earnings | Text data | Orthogonal info source |
| 32 | Online Learning | ML | Faster adaptation to non-stationarity |
| 33 | HRP Portfolio Construction | Multi-asset | Principled diversification |
| 34 | Drawdown-Aware Optimization | Multi-asset | Investor utility alignment |
| 35 | Copula Tail Dependence | Multi-asset | Unique tail risk signal |

### TIER 4 — Microstructure (Infrastructure-Dependent)

| # | Strategy | Why |
|---|----------|-----|
| 36 | Order Flow Imbalance | Needs tick data infrastructure |
| 37 | VPIN | Needs tick data, useful as risk filter |
| 38 | Market Maker Inventory | Needs tick data |
| 39 | Kyle's Lambda | Execution-focused, needs tick data |
| 40 | Iceberg Detection | Needs L3 data (most expensive) |

---

## RISK MANAGEMENT OVERLAY (All Strategies)

- **Single strategy max allocation:** 15% of portfolio
- **Asset class max allocation:** 40% (options/vol, crypto, real assets, fixed income)
- **Correlation budget:** Track pairwise correlations monthly; reduce if >0.7
- **Drawdown circuit breaker:** If any strategy loses >10% in a month, pause and review
- **Tail risk budget:** Maintain 2-3% of portfolio in tail hedges at all times
- **Liquidity reserve:** Keep 10% in cash/stablecoins for opportunistic entries
- **Alpha decay monitoring:** Review all strategies quarterly for performance degradation

---

## KEY GAPS IDENTIFIED

The biggest blind spots in the existing 367+ strategy system:

1. **No fixed income / bond strategies** — zero coverage of yield curve, credit, or rates
2. **No volatility as an asset class** — no VRP harvesting, no VIX term structure, no dispersion
3. **No inflation/macro regime detection** — missing 2021-2023 style signals
4. **No NLP/text signals** — purely price/volume, no Fed speeches or earnings calls
5. **No principled portfolio construction** — likely heuristic allocation, no HRP/Kelly
6. **No alpha decay monitoring** — no systematic detection of degrading signals
7. **No tick-level microstructure** — all signals are daily/hourly frequency
8. **Limited commodity strategies** — no term structure, spreads, or seasonal patterns
9. **No real asset exposure** — no REITs, MLPs, infrastructure
10. **No event-driven crypto** — missing token unlocks, airdrops, governance votes

---

*Document compiled 2026-04-18 by Xiaomi MiMo research. Sources include academic papers, hedge fund research, and systematic analysis of 367+ existing strategies in the findtorontoevents_antigravity.ca repository.*
