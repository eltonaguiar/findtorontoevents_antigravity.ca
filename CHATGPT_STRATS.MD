# CHATGPT Strategy Research: Practical Gaps Beyond Current Coverage

Generated: 2026-04-18

## Executive Take

After auditing the repo and running parallel subagent research, the main conclusion is clear:

- The codebase is already broad on classic momentum, mean reversion, breakout, carry, on-chain, funding, cross-asset correlation, regime filters, prediction-market overlays, and technical multi-factor composites.
- The biggest overlooked areas are not "more indicators." They are structural and institutional edges: options positioning, flow-of-funds plumbing, macro release drift, rates/curve RV, commodity scarcity signals, and event-driven corporate actions.
- The most useful next research lane is practical and data-aware. The least useful lane is speculative frontier work like quantum, neuromorphic, or topological finance. That may be interesting, but it is not the highest expected-value build for this repo.

## What I Compared Against

Local coverage snapshot came from these repo files:

- `STRATEGY_INVENTORY_COMPLETE.md`
- `strategy_catalog.md`
- `alpha_engine/config.py`
- `paper_trading/strategy_combination_config.json`
- `strategy_status_report.md`

That audit suggests the repo is strongest in:

- Crypto-native trend, funding, on-chain, sentiment, basis, liquidation, and technical systems
- Stock factor, momentum, quality, PEAD, sector rotation, and consensus systems
- Mean reversion, breakout, and confluence families across baby strategies and paper-trading wrappers
- Macro-lite regime filters, VIX-aware logic, and some options-skew / vol-adjacent work

That same audit suggests thinner coverage in:

- Deep rates / yield-curve strategy families
- Richer options-surface and dealer-positioning frameworks
- Structural flows from ETFs, index rebalances, borrow markets, and close auctions
- Corporate-action and event-driven relative value
- Alternative data that is operationally useful rather than novelty for novelty's sake

## Ranked Shortlist

### Tier 1: Highest-Fit Additions

These are the best candidates if the goal is "new edge that actually fits the current repo."

#### 1. Forced-Flow Rebalance Strategies

**Thesis**

Exploit predictable demand shocks around:

- index inclusions / deletions
- ETF creations / redemptions
- close-auction imbalance pressure
- periodic rebalance windows

**Why this is different from current coverage**

The repo has broad factor and momentum work, but it does not appear to have a dedicated "flow plumbing" stack that treats index methodology and ETF primary-market flows as alpha sources.

**Asset fit**

- Stocks
- Sector ETFs
- Multi-asset baskets

**Data needed**

- Index rebalance calendars
- ETF shares outstanding / creation-redemption activity
- Auction imbalance data if available
- Benchmark methodology documents

**Implementation fit**

High

**Sources**

- ETF flow predictability: https://academic.oup.com/rof/article-pdf/25/4/937/38939778/rfaa027.pdf
- S&P U.S. index methodology: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-us-indices.pdf
- Russell / index inclusion price effects: https://www.nber.org/papers/w19290.pdf

#### 2. Macro Release Surprise Drift

**Thesis**

Trade the immediate and short-horizon response after macro surprises versus consensus, especially around CPI, NFP, GDP, PMIs, and FOMC events.

**Why this is different from current coverage**

The repo has FOMC and macro-aware ideas, but not a clean release-surprise engine that explicitly uses consensus-vs-actual deltas and post-release drift windows.

**Asset fit**

- Forex
- Rates
- Equity index futures / ETFs
- Multi-asset macro baskets

**Data needed**

- Economic calendar
- Consensus estimates
- Actual release values
- High-frequency post-event prices

**Implementation fit**

High to medium

**Sources**

- NBER macro announcements: https://www.nber.org/papers/w1296
- Federal Reserve IFDP 823: https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm

#### 3. Options Gamma, Pinning, and Dealer Hedge Feedback

**Thesis**

Use gamma exposure, expiration clustering, and open-interest concentration to identify:

- price magnets
- squeeze-prone negative-gamma regimes
- suppressed-volatility positive-gamma regimes

**Why this is different from current coverage**

The repo has some options skew / vol logic, but dealer-positioning and gamma-regime logic is a distinct family. This is closer to market-structure plumbing than simple skew signals.

**Asset fit**

- Stocks
- Index ETFs
- BTC / ETH if options data is available

**Data needed**

- Full option chain
- Open interest by strike and expiry
- Implied vol surface
- Gamma exposure estimates

**Implementation fit**

Medium

**Sources**

- Option gamma and stock returns: https://www.sciencedirect.com/science/article/pii/S0927539823001093
- Cboe gamma dashboard: https://www.cboe.com/us/indices/dashboard/gamma/
- Option-market impact paper: https://academic.oup.com/rfs/article/34/4/1952/5873587

#### 4. Yield-Curve Carry and Rolldown / Treasury Curve RV

**Thesis**

Harvest carry and rolldown more explicitly in rates, and add DV01-neutral spread logic rather than treating curve exposure as a generic macro filter.

**Why this is different from current coverage**

The repo has some carry and macro exposure, but not a serious rates curve family. This is one of the clearest real gaps identified in the code audit.

**Asset fit**

- Treasuries
- Bond ETFs
- Rates futures
- Multi-asset macro sleeves

**Data needed**

- Yield curve
- Futures chain
- CTD / conversion factors
- DV01 calculations

**Implementation fit**

Medium

**Sources**

- Carry investing on the yield curve summary: https://rpc.cfainstitute.org/research/financial-analysts-journal/2019/ip-carry-investing-on-the-yield-curve
- Carry paper: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2862050_code374406.pdf?abstractid=2298565&mirid=1
- Treasury futures calendar spreads with tails: https://www.cmegroup.com/education/articles-and-reports/treasury-futures-calendar-spreads-with-tails

#### 5. Short Interest, Borrow Fee, and Securities-Lending Stress

**Thesis**

Use borrow scarcity and lending stress as a structural factor. Expensive-to-borrow names often carry persistent crowding and fragility information that is different from plain short-interest screens.

**Why this is different from current coverage**

The repo covers sentiment and some crowd logic, but not an explicit securities-lending / borrow-cost edge family.

**Asset fit**

- Stocks
- Small caps
- Short-bias sleeves

**Data needed**

- Short interest
- Days-to-cover
- Borrow fee / rebate rate
- Loan availability / locate data if available

**Implementation fit**

Medium

**Sources**

- Borrowing fees and expected returns: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3726227
- FINRA short-interest data: https://www.finra.org/finra-data/browse-catalog/equity-short-interest/data

#### 6. Analyst Revision Momentum and Dispersion

**Thesis**

Shift from static analyst ratings to dynamic analyst-change signals:

- estimate revisions
- target-price changes
- revision clusters
- disagreement / dispersion

**Why this is different from current coverage**

The repo already uses analyst data in places, but the stronger edge is in revisions and disagreement rather than the level of the rating itself.

**Asset fit**

- Stocks

**Data needed**

- Analyst recommendation history
- EPS estimate revisions
- Target-price revision history
- Event timestamps

**Implementation fit**

Medium

**Sources**

- Analyst revisions and momentum: https://www.nber.org/papers/w14971
- Analyst disagreement / dispersion: https://www.nber.org/papers/w12866

### Tier 2: Strong Ideas, More Data Plumbing

These are still attractive, but they either overlap partially with existing logic or need more specialized data.

#### 7. Volatility Risk Premium / Put-Write Carry

**Thesis**

Systematically harvest the gap between implied and realized volatility, ideally with regime filters so the system is not blindly short vol into stress.

**Why this is different from current coverage**

The repo touches options vol and skew, but VRP as a dedicated family is broader: put-write carry, delta-hedged short variance, or surface-aware short-vol sleeves.

**Asset fit**

- Equity indexes
- Liquid stocks
- BTC / ETH options

**Data needed**

- Implied vol
- Realized vol
- Option surface
- Event risk filters

**Implementation fit**

Medium

**Sources**

- Federal Reserve VRP paper: https://www.federalreserve.gov/econres/feds/dynamic-estimation-of-volatility-risk-premia-and-investor-risk-aversion-from-option-implied-and-realized-volatilities.htm
- Cboe put-write research: https://cdn.cboe.com/resources/spx/bondarenko-oleg-putwrite-putw-2019.pdf
- Cboe VIX products: https://www.cboe.com/products/vix-index-volatility

#### 8. Volatility Term-Structure / Calendar Relative Value

**Thesis**

Trade front-vs-back implied volatility or variance when the curve is too steep, flat, or inverted relative to realized-event risk.

**Why this is different from current coverage**

This goes beyond a single skew or VIX feature. It treats the surface as a curve and looks for relative-value dislocations across tenors.

**Asset fit**

- Equity indexes
- FX options
- Rates options
- Crypto options

**Data needed**

- Multi-expiry IV surface
- Realized vol
- Event calendar
- Open interest

**Implementation fit**

Medium to hard

**Sources**

- Cboe VIX term structure: https://www.cboe.com/tradable-products/vix/term-structure/
- VIX interpolation white paper: https://cdn.cboe.com/resources/education/research_publications/VIXInterpolationWhitepaper.pdf

#### 9. Commodity Convenience Yield / Inventory Scarcity

**Thesis**

Use convenience yield, basis, and inventory pressure to identify when commodity term structure is reflecting real scarcity rather than generic trend.

**Why this is different from current coverage**

The repo has some commodity and CTA logic, but not a dedicated inventory-scarcity / convenience-yield family.

**Asset fit**

- Commodities
- Commodity futures
- Commodity-linked equities

**Data needed**

- Futures curve
- Inventory data
- Basis / carry measures
- Seasonality

**Implementation fit**

Medium

**Sources**

- Predictive power of convenience yields: https://www.sciencedirect.com/science/article/pii/S0301420719305252
- Convenience yield and inventory evidence: https://www.sciencedirect.com/science/article/pii/S0301420713000421
- Carry across assets: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2862050_code374406.pdf?abstractid=2298565&mirid=1

#### 10. Dispersion / Implied Correlation

**Thesis**

Trade the gap between index-implied correlation and single-name implied volatility. This is a classic "surface relative value" strategy family rather than a directional one.

**Why this is different from current coverage**

The repo has correlation-based trend and reversion signals, but not options-implied correlation / dispersion.

**Asset fit**

- Stocks
- Sector baskets
- Index ETFs

**Data needed**

- Index option IV
- Single-name option IV
- Basket weights
- Realized correlation

**Implementation fit**

Hard

**Sources**

- Dispersion trading evidence: https://www.sciencedirect.com/science/article/abs/pii/S1044028309000593
- Correlation risk premium evidence: https://www.sciencedirect.com/science/article/pii/S0378426621003502
- Cboe implied correlation: https://www.cboe.com/us/indices/implied/

#### 11. Merger Arbitrage / Deal-Spread Event Trading

**Thesis**

Trade announced M&A spreads with deal-probability, antitrust, financing, and market-regime filters.

**Why this is different from current coverage**

The repo has PEAD and some event logic, but not a dedicated corporate-action spread strategy family.

**Asset fit**

- Stocks
- Event-driven sleeves

**Data needed**

- M&A deal database
- Deal terms
- Borrow data for stock-for-stock deals
- Regulatory and legal event tracking

**Implementation fit**

Medium to hard

**Sources**

- Mitchell and Pulvino, risk arbitrage: https://www.andreisimonov.com/N4106/pdf/MitchellPulvinoJFDec2001.pdf
- Limited arbitrage in mergers and acquisitions: https://www.sciencedirect.com/science/article/abs/pii/S0304405X02000727

#### 12. FX Forward / Hedging-Flow Distortion

**Thesis**

Use quarter-end and institutional hedging flow distortions in FX forwards and swaps as structural signals rather than relying only on carry and momentum.

**Why this is different from current coverage**

The repo has carry and some macro/currency logic, but not a dedicated "institutional hedging flow" family.

**Asset fit**

- Forex
- Rates / FX macro books
- Multi-asset hedging overlays

**Data needed**

- Forward points
- Cross-currency basis
- Quarter-end dates
- Dealer / bank hedging proxies

**Implementation fit**

Hard

**Sources**

- Boston Fed / RFS demand effects in FX forward markets: https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/2018/wp1806-revised.pdf
- BIS on FX swaps and global dollar hedging flows: https://www.bis.org/publ/qtrpdf/r_qt2309b.htm

### Tier 3: Optional High-Cost Research Lanes

These are valid, but they are less attractive than the tiers above unless the repo is ready to pay for richer data and build new ingestion infrastructure.

#### 13. Search / Web-Attention Shock Strategies

**Why it matters**

Attention spikes can lead price, especially around earnings, launches, regulatory headlines, and crypto narratives.

**Data needed**

- Google Trends
- News-volume counts
- Topic velocity

**Sources**

- Google Trends docs: https://developers.google.com/search/apis/trends
- Scientific Reports paper: https://www.nature.com/articles/s41598-019-50131-1

#### 14. Employee Sentiment / Workforce Expectations

**Why it matters**

Workforce sentiment can expose operating deterioration or improvement before it appears in reported fundamentals.

**Data needed**

- Review text / scores
- Hiring signals
- Salary or expectations proxies

**Sources**

- Employee expectations paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3321275
- Employee sentiment index paper: https://www.sciencedirect.com/science/article/pii/S0957417421007259

#### 15. Satellite / Logistics / Throughput Data

**Why it matters**

Physical-activity signals can outperform narrative-heavy alternatives when the goal is to measure demand, bottlenecks, or supply stress.

**Data needed**

- Satellite imagery
- AIS shipping data
- Port throughput
- Parking lot counts

**Sources**

- Port satellite imagery and stock returns: https://www.nature.com/articles/s41599-023-01891-9
- NBER satellite imagery overview: https://www.nber.org/papers/w27879

## Practical Priority Order

If the goal is to add the best overlooked families without blowing up data complexity, the best order is:

1. Forced-flow rebalance strategies
2. Macro release surprise drift
3. Options gamma / pinning / dealer hedge feedback
4. Yield-curve carry and rolldown
5. Short-interest / borrow-fee pressure
6. Analyst revision momentum / dispersion
7. Volatility risk premium
8. Commodity convenience yield / inventory scarcity
9. Merger arbitrage
10. FX forward / hedging-flow distortion

## What To Skip For Now

Do not prioritize these ahead of the list above:

- quantum-inspired trading
- neuromorphic trading
- topological data analysis as a primary strategy family
- "holographic" or string-theory market analogies
- other frontier ideas that are hard to validate and weakly connected to current data access

Those are research curiosities, not the highest-probability additions for this repo.

## Repo-Facing Build Suggestions

### Low-friction prototypes

- Macro surprise drift
- Index / ETF rebalance flow tracking
- Analyst revision momentum
- Borrow-fee / short-interest pressure

### Medium-friction prototypes

- Dealer gamma regime tracker
- Yield-curve carry / rolldown
- Commodity scarcity / convenience yield
- VRP with event filters

### High-friction institutional builds

- Dispersion / implied correlation
- Merger arbitrage
- FX hedging-flow distortions
- Rich alternative-data ingestion

## All-Asset-Class Expansion

The shortlist above is still intentionally selective. If the goal is a broader research inventory across all asset classes, these are additional strategy families worth tracking.

### Equities and Equity-Linked

#### 16. Spin-offs and Split-off Special Situations

**Thesis**

Corporate spin-offs often create forced selling, mandate mismatch, and temporary mispricing in both parent and child securities.

**Data needed**

- Spin-off announcement calendar
- Deal terms
- Parent / child sector mapping
- Post-spin liquidity and ownership changes

**Sources**

- Spin-off wealth creation overview: https://www.nature.com/articles/s41599-021-00807-9
- Empirical spin-off evidence: https://www.tandfonline.com/doi/full/10.1080/23322039.2022.2109277

#### 17. Hedge Fund Activism / 13D Event Trading

**Thesis**

Schedule 13D filings, activist stake disclosure, and follow-on engagement campaigns create persistent event-driven return patterns that are distinct from standard factor models.

**Data needed**

- 13D / 13D-A filings
- Activist identity and campaign type
- Ownership changes
- Proxy / board / strategic-review milestones

**Sources**

- Hedge fund activism returns: https://law.duke.edu/sites/default/files/centers/gfmc/session_3/2_brav_et_al-hedge_fund_activism-2008.pdf
- International activism evidence: https://academic.oup.com/rfs/article/30/9/2933/3852480

#### 18. Insider Purchase Clusters

**Thesis**

Single insider trades are noisy; clustered insider buying, especially across multiple officers or directors, carries a stronger signal about valuation and near-term fundamentals.

**Data needed**

- Form 4 filings
- Insider role classification
- Cluster timing and transaction size
- Market-cap and liquidity filters

**Sources**

- Insider informativeness: https://www.nber.org/papers/w6656
- Forms 3/4/5 reference: https://www.sec.gov/forms/forms-3-4-5.pdf

#### 19. Buyback Signal Quality and Execution Edge

**Thesis**

Repurchase programs matter more when they are credible, sizeable, and launched under valuation stress. The edge is in separating real capital-allocation signals from boilerplate authorizations.

**Data needed**

- Repurchase announcements
- Actual executed buybacks
- Program size and method
- Balance-sheet and valuation context

**Sources**

- Repurchase announcement evidence: https://www.sciencedirect.com/science/article/pii/S0929119920302315
- Execution and buyback mechanics: https://arxiv.org/abs/2307.09617

#### 20. Closed-End Fund Discount / Holding-Vehicle Discount

**Thesis**

Persistent discounts between market price and net asset value can be traded as sentiment, governance, or liquidity dislocations rather than pure valuation signals.

**Data needed**

- Fund NAV
- Market price
- Discount history
- Corporate actions and sentiment proxies

**Sources**

- Closed-end fund puzzle: https://www.nber.org/papers/w3465
- Rational discount model: https://www.nber.org/papers/w10412

#### 21. Low-Volatility / Low-Beta Equity Sleeves

**Thesis**

Low-volatility and low-beta portfolios often outperform on a risk-adjusted basis and can be used as standalone sleeves or as financing legs for higher-turnover tactical strategies.

**Data needed**

- Realized volatility
- Beta estimates
- Sector-neutral and dollar-neutral construction inputs

**Sources**

- Low-vol anomaly overview: https://arxiv.org/abs/1510.01679
- Adaptive multi-factor low-vol study: https://arxiv.org/abs/2003.08302

#### 22. Legal / Regulatory Event Drift

**Thesis**

Court rulings, antitrust actions, and regulatory decisions often create underreacted repricing, especially in concentrated sectors or merger situations.

**Data needed**

- Legal-event calendar
- Company linkage to the case or ruling
- Historical event windows
- Sector and factor controls

**Sources**

- Supreme Court abnormal return study: https://arxiv.org/abs/1508.05751
- Activism and legal-event overlap example: https://www.nber.org/papers/w21227.pdf

#### Extra Equity Families Worth Tracking

- **BAB / low-beta relative value**: long low-beta / low-vol names and short high-beta names, especially when leverage constraints or retail speculation inflate the high-beta leg.
  Sources: https://www.nber.org/papers/w16601 and https://econpapers.repec.org/RePEc:eee:jfinec:v:111:y:2014:i:1:p:1-25
- **Illiquidity premium**: use Amihud illiquidity, spreads, and turnover to isolate structurally underowned names rather than simple size exposure.
  Sources: https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf and https://cfr.ivo-welch.info/published/papers/amihud2020illiquidity.pdf
- **Days-to-cover / short-constraint squeeze setups**: treat days-to-cover as cleaner than raw short interest when looking for crowding, forced buying, or borrow-driven fragility.
  Sources: https://www.nber.org/papers/w21166 and https://www.nber.org/papers/w8494
- **Sector and style flow rotation**: track ETF and institutional style flows to express the trade through sectors or style baskets instead of single names.
  Sources: https://www.nber.org/papers/w10355 and https://www.sec.gov/rules-regulations/2001/11/actively-managed-exchange-traded-funds
- **SEO and lockup-expiry supply shocks**: new float, insider unlocks, and secondary issuance create mechanical supply that can dominate narrative in newly public or small-cap names.
  Sources: https://academic.oup.com/rof/article/18/3/1023/1571800 and https://www.anderson.ucla.edu/documents/areas/fac/finance/subra_lockup.pdf

### Rates and FX

#### 23. Relative Term-Structure RV

**Thesis**

Trade differences in cross-country curve shape, not just spot rate differentials. Forward-rate and multi-tenor curve gaps can forecast both bond and FX excess returns.

**Data needed**

- Sovereign zero curves
- Swap curves
- FX spot and forwards
- Inflation expectations

**Sources**

- Forward rates and FX: https://www.nber.org/papers/w11840
- Interest-rate-factor FX paper: https://www.sciencedirect.com/science/article/abs/pii/S0927539821000050

#### 24. Unspanned Inflation / Yield-Curve Residuals

**Thesis**

Some inflation and policy uncertainty is not fully captured by standard curve factors. That residual can drive both rates and FX returns.

**Data needed**

- Yield-curve factor model
- Inflation expectations
- Macro surprise data
- Bond and FX excess returns

**Sources**

- BIS spanning puzzle paper: https://www.bis.org/publ/work1320.htm
- Inflation and term structure: https://www.nber.org/papers/w8246

#### 25. Cross-Currency Basis Mean Reversion

**Thesis**

CIP deviations are often balance-sheet and hedging-demand shocks, not free arbitrage. Extremes in the basis can mean-revert once quarter-end or funding stress passes.

**Data needed**

- Cross-currency basis
- OIS / funding curves
- Repo and dealer stress proxies
- Quarter-end calendar

**Sources**

- Covered interest parity lost: https://www.bis.org/publ/qtrpdf/r_qt1609e.htm
- Hedging channel of exchange rates: https://www.federalreserve.gov/econres/ifdp/the-hedging-channel-of-exchange-rate-determination.htm

#### 26. Basis Term-Structure Carry

**Thesis**

The basis itself has a curve. Forward-starting or tenor-structure basis trades can harvest roll-down and carry when term structure becomes abnormally steep.

**Data needed**

- Multi-tenor basis curve
- Funding curves
- External imbalance data
- Hedge-flow proxies

**Sources**

- Fed IFDP 1283: https://www.federalreserve.gov/econres/ifdp/files/ifdp1283.pdf
- BIS on FX swaps and positions: https://www.bis.org/publ/qtrpdf/r_qt2309b.htm

#### 27. Quarter-End Funding Squeeze Trades

**Thesis**

Month-end and quarter-end balance-sheet windows create repeatable funding stress in basis-sensitive currencies and rates instruments.

**Data needed**

- Daily basis series
- Repo spreads
- Quarter-end calendar
- Dealer inventory constraints

**Sources**

- BIS liquidity spillovers: https://www.bis.org/publ/work836.htm
- Covered interest parity lost: https://www.bis.org/publ/qtrpdf/r_qt1609e.htm

#### 28. Fixing-Flow Window Trades

**Thesis**

WMR, ECB, and Tokyo fixing windows concentrate client flow and can create short-duration price distortions that differ materially from the rest of the trading day.

**Data needed**

- Intraday spot and forward prices
- Benchmark fix calendar
- Volume / order-book data

**Sources**

- Bank of England FX investigation: https://www.bankofengland.co.uk/-/media/boe/files/report/2014/foreign-exchange-market-investigation-report-by-lord-grabiner.pdf
- WM/R fix microstructure: https://www.nber.org/system/files/working_papers/w21518/w21518.pdf

#### 29. Treasury RV: Swap Spreads, On/Off-the-Run, Auction Cycle

**Thesis**

Rates relative value goes well beyond curve carry. Treasury vs swap spread dislocations, on-the-run / off-the-run gaps, and auction-cycle effects are distinct strategy families.

**Data needed**

- Treasury cash and futures prices
- Swap rates
- Auction calendar
- Balance-sheet and hedge-fund positioning proxies

**Sources**

- BIS Treasury and IRS relative-value overview: https://www.bis.org/publ/qtrpdf/r_qt2512y.htm
- CME Treasury calendar spread material: https://www.cmegroup.com/education/articles-and-reports/treasury-futures-calendar-spreads-with-tails

### Commodities, Energy, and Real Assets

#### 30. Curve Shape / Convenience-Yield State Trades

**Thesis**

Trade the level and curvature of the commodity curve when scarcity and convenience yield change. The edge is in the curve regime, not just outright backwardation.

**Data needed**

- Nearby and deferred futures
- Spot proxy
- Funding costs
- Inventory and storage data

**Sources**

- Commodity futures fundamentals: https://www.nber.org/papers/w13249
- EIA balance framework: https://www.eia.gov/finance/markets/crudeoil/balance.php

#### 31. Inventory-Level / Stock-to-Use Signals

**Thesis**

Absolute inventories versus seasonal norms can predict convergence pressure and risk premia in nearby futures and calendar spreads.

**Data needed**

- Inventory levels
- Seasonally adjusted stock-to-use
- Production and consumption
- Curve structure

**Sources**

- Commodity futures fundamentals: https://www.nber.org/papers/w13249
- Macrosynergy inventory overview: https://macrosynergy.com/research/how-inventory-levels-affect-commodity-futures-curves-and-returns/

#### 32. Inventory-Surprise Event Trading

**Thesis**

EIA and USDA report surprises often move the front of the curve faster than the outright complex, creating event-specific spread opportunities.

**Data needed**

- Release calendar
- Consensus expectations
- Intraday futures
- Historical surprise archive

**Sources**

- Short-run commodity dynamics: https://www.nber.org/papers/w3295
- EIA oil balance material: https://www.eia.gov/finance/markets/crudeoil/balance.php

#### 33. Seasonality / Harvest / Weather Windows

**Thesis**

Planting, harvest, driving season, winter heating, and maintenance cycles create recurring return and volatility windows that can be traded directly or used as filters.

**Data needed**

- Historical futures
- Crop / weather calendars
- Seasonal volatility
- Roll schedule

**Sources**

- Commodity return seasonality: https://www.sciencedirect.com/science/article/pii/S1059056024002934
- Commodity options seasonality: https://www.sciencedirect.com/science/article/abs/pii/S0378426612002646

#### 34. Freight and Logistics Dislocation Trades

**Thesis**

Port congestion, tanker rates, and route-specific freight spikes can break normal cross-region arbitrage and create location and timing spreads.

**Data needed**

- Freight indices
- Port and route data
- Regional spot prices
- Shipping-capacity data

**Sources**

- ICE freight products: https://www.ice.com/energy/freight
- IMF shipping-cost paper: https://www.imf.org/en/publications/wp/issues/2022/03/25/shipping-costs-and-inflation-515144

#### 35. Regional Basis / Location-Spread Strategies

**Thesis**

Hub-to-hub spreads such as WTI-Brent or Henry Hub versus regional gas hubs reflect transport constraints, local scarcity, and infrastructure bottlenecks.

**Data needed**

- Regional spot and futures
- Pipeline and storage data
- Delivery specs
- Outage and congestion data

**Sources**

- Geographic barriers and integration: https://www.nber.org/papers/w20247
- ICE NGX overview: https://www.ice.com/publicdocs/Product_Summary.pdf

#### 36. Crack, Spark, and Crush Margin Trades

**Thesis**

Input-output margin strategies often have cleaner economics than outright commodity direction because they tie directly to refinery, generator, or processor profitability.

**Data needed**

- Crude / gasoline / diesel
- Gas / power / heat-rate
- Soybean / meal / oil / biofuel series
- Utilization and outage data

**Sources**

- Crack spreads: https://www.cmegroup.com/education/articles-and-reports/introduction-to-crack-spreads
- EIA spark spread explainer: https://www.eia.gov/todayinenergy/includes/sparkspread_explain.php
- Soybean crush reference: https://www.cmegroup.com/education/courses/introduction-to-grains-and-oilseeds/understanding-soybean-crush

#### 37. Commodity-Producer Equity Linkage

**Thesis**

Producer equities can be treated as levered, imperfect, or nonlinear claims on the underlying commodity, creating relative-value opportunities between equity baskets and futures.

**Data needed**

- Producer equity returns
- Commodity futures
- Production mix and hedging disclosures
- Balance-sheet leverage

**Sources**

- Gold-mining evidence: https://www.nber.org/papers/w7075
- Energy producer asset-pricing linkages: https://www.nber.org/papers/w22914

### Crypto and Digital Assets

#### 38. Crypto Options Surface Relative Value

**Thesis**

Trade the rich/cheap pockets of BTC and ETH vol surfaces across tenor, skew, and smile rather than treating crypto options as simple directional bets.

**Data needed**

- Full option chain
- Greeks and IV by delta / tenor
- Realized vol
- OI and funding context

**Sources**

- CME options analytics: https://www.cmegroup.com/news/2025/options-analytics-greeks-implied-volatility.html
- Crypto options modeling paper: https://arxiv.org/abs/2403.16006

#### 39. Stablecoin Peg and Lending-Rate Plumbing

**Thesis**

Peg stress, borrow/lend rates, and redemption pressure can create separate relative-value opportunities that are only loosely connected to broad crypto beta.

**Data needed**

- Stablecoin spot quotes
- Borrow and lend rates
- Mint / redeem flows
- Reserve composition

**Sources**

- Stablecoin pegs paper: https://www.cambridge.org/core/services/aop-cambridge-core/content/view/1BB04806528A0A58032102A6D85D3CC1/S0022109025000134a.pdf/leverage-and-stablecoin-pegs.pdf
- BIS stablecoin considerations: https://www.bis.org/cpmi/publ/d220.htm

#### 40. Stablecoin FX Spillovers

**Thesis**

Stablecoins can function as parallel dollar rails and create pricing pressure in local FX markets, especially where capital controls or banking frictions matter.

**Data needed**

- Fiat / stablecoin pair quotes
- Stablecoin inflows
- Spot and forward FX
- Cross-market friction proxies

**Sources**

- IMF stablecoin spillover paper: https://www.imf.org/-/media/files/publications/wp/2026/english/wpiea2026056-source-pdf.pdf
- BIS stablecoin paper: https://www.bis.org/cpmi/publ/d220.htm

#### 41. Staking Unlock / Exit-Queue Basis

**Thesis**

ETH staking withdrawals, validator exit queues, and LST discounts create timing and liquidity trades that are structurally different from spot momentum.

**Data needed**

- Exit-queue data
- Withdrawal flows
- LST pricing
- Staking APR and borrow demand

**Sources**

- Ethereum withdrawals: https://ethereum.org/ur/staking/withdrawals/
- EIP-4895: https://eips.ethereum.org/EIPS/eip-4895

#### 42. Recursive LSD Leverage / Unwind Risk

**Thesis**

Looped leverage through stETH / wstETH and lending protocols creates nonlinear unwind risk that can be tracked before liquidations show up in price.

**Data needed**

- LST supply
- Lending utilization
- Liquidation thresholds
- Loop-depth proxies

**Sources**

- LSD leverage paper: https://arxiv.org/abs/2401.08610
- Liquid staking empirical paper: https://arxiv.org/abs/2401.16353

#### 43. Onchain Flow and Exchange-Reserve Regimes

**Thesis**

Exchange inflows/outflows, miner deposits, and stablecoin transfer velocity often shift before spot price fully reflects the change in regime.

**Data needed**

- Exchange balances
- Entity-adjusted flows
- Stablecoin transfer volume
- Cohort and miner metrics

**Sources**

- Glassnode exchange metrics: https://insights.glassnode.com/exchange-metrics/
- Network-price dynamics paper: https://arxiv.org/abs/1907.03577

#### 44. Perpetual Swap Microstructure

**Thesis**

Perps have unique mark-price, liquidation-band, and OI-reporting mechanics that create short-horizon structure trades beyond plain funding carry.

**Data needed**

- Tick trades
- Order book
- Mark, index, and last price
- Funding, OI, and liquidation prints

**Sources**

- OI and volume reconciliation paper: https://arxiv.org/abs/2310.14973
- Bybit mark-price methodology: https://www.bybit.com/en/help-center/article/Mark-Price-Calculation-Perpetual-Expiry-Contracts

#### 45. Cross-Exchange Lead-Lag / Venue-Quality Arbitrage

**Thesis**

Crypto price discovery is fragmented. Cleaner or faster venues often lead noisier ones, which creates transient relative-value opportunities if execution quality is strong.

**Data needed**

- Multi-venue trades and quotes
- Latency stamps
- Market-quality scores
- Transfer and withdrawal friction

**Sources**

- Coin Metrics TEF: https://coinmetrics.io/special-insights/trusted-exchange-framework/
- Latency and price discovery paper: https://www.cambridge.org/core/services/aop-cambridge-core/content/view/524F0B00D8E9BAC8723956A6E2187E57/S002210901900067Xa.pdf/orderflow_segmentation_liquidity_and_price_discovery_the_role_of_latency_delays.pdf

#### 46. Token Unlock / Vesting-Cliff Supply Overhang

**Thesis**

Large unlocks create predictable supply pressure when float is thin, liquidity is weak, and borrow is available.

**Data needed**

- Vesting schedule
- Unlock size
- Circulating supply
- Order-book depth

**Sources**

- Messari token unlocks API: https://docs.messari.io/api-reference/endpoints/token-unlocks/token-unlocks-api
- Cliff-unlock research note: https://messari.io/report/don-t-look-down-navigating-markets-around-cliff-unlocks

#### 47. Buyback / Burn / Emissions-Governance Repricing

**Thesis**

Protocol treasury policy can create structural repricing when revenue is redirected into buybacks, burns, or emissions reductions.

**Data needed**

- Protocol revenue
- Burn and buyback cadence
- Governance proposals
- Treasury and emissions schedule

**Sources**

- Vertex overview: https://messari.io/report/understanding-vertex-a-comprehensive-overview
- Binance tokenomics deep dive: https://research.binance.com/static/pdf/Tokenomics_Deep_Dive_Stefan_Piech_Shivam_Sharma.pdf

### Cross-Asset, Credit, and Relative Value

#### 48. Dispersion / Implied Correlation

**Thesis**

Trade the gap between index-implied correlation and single-name implied vol. This is a distinct cross-asset vol family, not just another options overlay.

**Data needed**

- Index and constituent IV
- Basket weights
- Realized correlation

**Sources**

- Dispersion trading evidence: https://www.sciencedirect.com/science/article/abs/pii/S1044028309000593
- Cboe implied correlation: https://www.cboe.com/us/indices/implied/

#### 49. Cross-Asset Volatility Risk Premium

**Thesis**

Rank and trade implied-minus-realized volatility across equities, rates, FX, credit, and commodities rather than running a single-asset short-vol book.

**Data needed**

- Implied vol across asset classes
- Realized vol
- Event filters
- Funding and carry metrics

**Sources**

- Federal Reserve VRP paper: https://www.federalreserve.gov/econres/feds/dynamic-estimation-of-volatility-risk-premia-and-investor-risk-aversion-from-option-implied-and-realized-volatilities.htm
- Cboe cross-asset VRP discussion: https://www.cboe.com/insights/posts/tariff-and-powell-risk-drive-elevated-cross-asset-vr-ps/

#### 50. Event Volatility / Catalyst Pricing

**Thesis**

Trade the pricing of known catalysts in options markets: earnings, macro releases, policy meetings, and other binary events.

**Data needed**

- Option chain
- Event calendar
- Historical post-event moves
- IV term structure

**Sources**

- CME event volatility calculator: https://www.cmegroup.com/tools-information/quikstrike/event-volatility-calculator.html
- Earnings vol-spread paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2551260

#### 51. Merger Arbitrage

**Thesis**

Trade deal spreads with financing, regulatory, borrow, and market-regime filters. This is one of the cleanest corporate event-driven families missing from the repo.

**Data needed**

- Deal database
- Consideration terms
- Borrow data
- Antitrust and legal milestones

**Sources**

- Mitchell and Pulvino: https://www.andreisimonov.com/N4106/pdf/MitchellPulvinoJFDec2001.pdf
- Limited arbitrage in M&A: https://www.sciencedirect.com/science/article/abs/pii/S0304405X02000727

#### 52. Capital Structure Arbitrage

**Thesis**

Exploit inconsistency between a company’s equity, bonds, and CDS / credit spread pricing, especially after shocks that hit one part of the capital structure faster than the others.

**Data needed**

- Equity prices and options
- Bonds or CDS spreads
- Structural model inputs
- Balance-sheet and default-risk variables

**Sources**

- Capital structure arbitrage study: https://www.mdpi.com/1911-8074/10/1/3
- CDS spread drivers via BIS: https://www.bis.org/publ/work181.htm

#### 53. Convertible Arbitrage

**Thesis**

Trade mispricing between a convertible bond and the embedded equity option, usually hedged against the underlying equity and credit risk.

**Data needed**

- Convertible terms
- Underlying equity and vol
- Credit spread inputs
- Borrow and financing rates

**Sources**

- Fidelity overview: https://institutional.fidelity.com/app/literature/item/9912569.html
- Tilburg convertible arbitrage analysis: https://research.tilburguniversity.edu/files/779871/98.pdf

## Expansion II

This pass is split on purpose:

- **54-160** expand coverage fast across all asset classes without turning the document into filler.
- **161-200** are the higher-conviction families that are worth taking through [`TESTING_PROTOCOL.MD`](./TESTING_PROTOCOL.MD) with stricter anti-overfit and anti-drift controls.

### Broad Inventory Expansion

These are additional strategy families worth tracking. They are **not** all equally strong. The point of this section is breadth. The protocol-grade section that follows is the quality filter.

### Equities and Equity-Linked Expansion

**Representative sources**

- Momentum and earnings underreaction: https://www.nber.org/papers/w5375
- Friday / attention-driven drift: https://www.nber.org/papers/w11683
- Dividend initiation and omission drift: https://www.nber.org/papers/w4778
- Equity issuance supply effects: https://www.nber.org/papers/w3170
- Strategic disclosure timing / vesting months: https://www.nber.org/papers/w20476

#### 54. Post-Earnings Announcement Drift with Attention Filters
- **Edge**: underreaction is stronger when earnings compete with macro noise, Friday timing, or crowded news cycles.
- **Validation**: event-time backtest by announcement cohort; next-open execution; delisting-adjusted data; borrow-aware short leg.

#### 55. Dividend Initiation / Omission Drift
- **Edge**: payout policy changes keep drifting after the initial announcement reaction.
- **Validation**: event study by yield-change bucket and sector; exclude overlapping earnings windows.

#### 56. SEO / Follow-On Offering Supply Shock
- **Edge**: secondary issuance adds mechanical supply and often pressures post-deal returns.
- **Validation**: announcement-to-pricing-to-30D windows; separate marketed vs accelerated deals.

#### 57. Rights Offering Mispricing
- **Edge**: complex deal terms and distressed issuance often create temporary mispricing around ex-rights and subscription periods.
- **Validation**: include subscription mechanics, dilution math, and borrow constraints.

#### 58. Index Inclusion / Deletion
- **Edge**: passive demand and benchmark chasing create predictable announcement and rebalance effects.
- **Validation**: separate announcement drift from rebalance day impact; liquidity-capacity test is mandatory.

#### 59. Russell Reconstitution Flow
- **Edge**: predictable annual membership changes create front-runnable and reversal-prone flow windows.
- **Validation**: event-time cohorts by market-cap boundary and crowding.

#### 60. ADR / Local Dual-Listing Basis
- **Edge**: cross-venue segmentation, FX noise, and local-market frictions create temporary basis dislocations.
- **Validation**: enforce timestamp normalization, FX conversion parity, and venue-latency haircuts.

#### 61. Share-Class Arbitrage
- **Edge**: economically similar share classes can drift apart under retail flow and short-sale frictions.
- **Validation**: corporate-action adjusted spreads; hard borrow and float screens.

#### 62. Holdco Discount / Stub Trades
- **Edge**: holding-company structures and listed stubs frequently trade at persistent look-through discounts.
- **Validation**: mark through ownership trees, debt, taxes, and catalyst calendar.

#### 63. Post-Bankruptcy Emergence Drift
- **Edge**: newly emerged equities are underfollowed, technically forced-sold, and often misclassified by screens.
- **Validation**: isolate Chapter 11 emergence date, float unlock schedule, and creditor ownership turnover.

#### 64. Earnings-Call Language Dispersion
- **Edge**: disagreement and tone dispersion across analysts and management can carry information beyond headline beats/misses.
- **Validation**: forward-only NLP snapshots; no hindsight transcript revisions.

#### 65. Crowdsourced Estimate Divergence
- **Edge**: gaps between crowd estimates and sell-side consensus can flag underpriced earnings surprise risk.
- **Validation**: freeze consensus snapshots before release; bucket by liquidity and analyst coverage.

#### 66. Credit-Card Spend Surprise
- **Edge**: transaction data can lead revenue surprises in consumer names and sector baskets.
- **Validation**: strict lag discipline; only use point-in-time vendor vintages.

#### 67. App-Download / Web-Traffic Lead Signals
- **Edge**: user growth often shows up in app rankings and traffic trends before sell-side revisions move.
- **Validation**: adjust for seasonality, ad campaigns, and geography mix.

#### 68. Job-Postings Growth Predictor
- **Edge**: hiring acceleration and role mix changes can foreshadow demand growth or cost pressure.
- **Validation**: lag postings realistically; separate engineering, sales, and fulfillment job families.

#### 69. Patent Filing Momentum
- **Edge**: innovation cadence and patent quality can matter before revenues catch up in R&D-heavy sectors.
- **Validation**: use filing date, not grant date; adjust for sector filing norms.

#### 70. Congressional Trading Mimicry
- **Edge**: reported trades can act as weak but sometimes useful catalyst flags in niche names and sectors.
- **Validation**: enforce disclosure lag; treat as low-frequency overlay, not high-turn signal.

#### 71. 13F Crowding Reversal
- **Edge**: crowded hedge-fund ownership can amplify unwind risk after disappointments.
- **Validation**: account for filing lag and stale positions; use as a crowding overlay.

#### 72. Mutual Fund Window-Dressing Reversal
- **Edge**: quarter-end holdings cosmetics can create short-lived distortions in recent winners and losers.
- **Validation**: quarter-end calendar cohorts; separate true trend from reporting effects.

#### 73. Tax-Loss Selling / January Reversal
- **Edge**: forced year-end selling in prior losers can mean-revert once tax pressure clears.
- **Validation**: small-cap and retail-heavy buckets; control for liquidity.

#### 74. Buyback Blackout Exit / Restart Effect
- **Edge**: blackout windows remove a known corporate bid; restart periods can restore support.
- **Validation**: tie to earnings calendar and actual executed repurchases where possible.

#### 75. Strategic News Release Timing
- **Edge**: firms cluster negative or low-attention disclosures into distracted windows.
- **Validation**: compare Friday, holiday-adjacent, and macro-heavy days versus normal disclosure days.

#### 76. Accruals / Earnings Quality Spread
- **Edge**: low-quality earnings and aggressive accruals still drift negatively after reporting.
- **Validation**: point-in-time accounting data only; restatement-aware.

#### 77. Net Payout Yield / Shareholder Yield
- **Edge**: total cash returned via dividends, buybacks, and debt paydown can outperform simple dividend screens.
- **Validation**: measure realized cash return, not announced intent.

#### 78. Asset Growth / Investment Anomaly
- **Edge**: aggressive asset growth and empire building often forecast weaker future returns.
- **Validation**: use filing-date availability; sector-normalize balance-sheet expansion.

#### 79. Closing Auction Imbalance Reversal
- **Edge**: passive and benchmark flow distorts closing auction prices and often mean-reverts.
- **Validation**: intraday imbalance data; open-to-close vs close-to-next-open decomposition.

#### 80. Forced-Seller / Liquidation Reversal
- **Edge**: mechanically sold names often snap back once urgency clears.
- **Validation**: identify likely forced sellers via flow, leverage, or fund-event proxies; capacity test matters.

### Rates and FX Expansion

**Representative sources**

- Cross-asset carry: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2311574
- Currency value: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2795087
- Post-FOMC drift in bonds: https://www.nber.org/papers/w25127
- End-of-month Treasury returns: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3496962_code382831.pdf?abstractid=3440417&mirid=1
- Treasury bond risk premia: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2588853_code598300.pdf?abstractid=1709636&mirid=1

#### 81. Treasury Auction Cycle
- **Edge**: auctions reshape positioning, liquidity, and short-term relative value around issuance windows.
- **Validation**: test pre-auction, auction-day, and post-auction windows separately by tenor.

#### 82. End-of-Month Treasury Return Effect
- **Edge**: benchmark extension and duration demand create predictable month-end bond pressure.
- **Validation**: separate coupon buckets and duration extension size.

#### 83. On-the-Run / Off-the-Run Spread
- **Edge**: liquidity premia create repeatable gaps between newest and seasoned Treasury issues.
- **Validation**: control for specials, repo, and financing costs.

#### 84. Mortgage Convexity Hedging Flow
- **Edge**: mortgage servicers and MBS investors hedge duration nonlinearly as yields move.
- **Validation**: state-conditioned backtests by rate level, vol regime, and refi incentive.

#### 85. Swap Spread Mean Reversion
- **Edge**: Treasury-swap spreads reflect balance-sheet, liquidity, and funding distortions rather than pure macro alone.
- **Validation**: include repo, issuance calendar, and dealer balance-sheet stress proxies.

#### 86. FRA-OIS / Funding Stress Mean Reversion
- **Edge**: funding spreads widen mechanically around stress windows and then mean-revert.
- **Validation**: quarter-end, crisis, and central-bank-liquidity subperiods must be separated.

#### 87. Inflation Breakeven Relative Value
- **Edge**: TIPS vs nominals can misprice realized inflation risk, liquidity, and policy shocks.
- **Validation**: decompose liquidity versus pure inflation component; use inflation-swap cross-check.

#### 88. Real-Yield / Nominal-Yield Divergence
- **Edge**: real-rate shocks often spill into gold, growth equities, and FX before the full cross-asset repricing completes.
- **Validation**: test as a cross-asset signal, not just a rates trade.

#### 89. Yield-Curve Butterfly Relative Value
- **Edge**: belly vs wings dislocations can mean-revert faster than outright level or slope trades.
- **Validation**: duration-neutral construction and auction-calendar conditioning.

#### 90. Post-FOMC Bond Drift
- **Edge**: mutual fund and asset allocator flow adjusts to policy surprises over days, not just minutes.
- **Validation**: narrow-window shock classification plus multi-day follow-through test.

#### 91. Central Bank Reaction-Function NLP
- **Edge**: policy language shifts can forecast rates and FX repricing better than simple surprise metrics.
- **Validation**: freeze statement text versions and speech timestamps; avoid hindsight labels.

#### 92. Cross-Country Duration Relative Value
- **Edge**: global curves can diverge beyond what macro fundamentals justify.
- **Validation**: hedge FX explicitly and separate local-duration from currency return.

#### 93. EM Local-Rates Carry, Hedged vs Unhedged
- **Edge**: local bond carry may survive or fail depending on whether FX is hedged.
- **Validation**: split local-currency carry and FX carry; include capital-control and liquidity screens.

#### 94. Currency Value
- **Edge**: PPP-style or external-balance valuation signals add information beyond carry and momentum.
- **Validation**: point-in-time macro inputs; long windows and robust persistence tests.

#### 95. Carry + Value + Momentum FX Blend
- **Edge**: the combo is stronger and more diversified than any one sleeve alone.
- **Validation**: independently validate each sleeve, then test the blend with clone-penalty logic.

#### 96. Reserve-Manager Hedging Flow Proxy
- **Edge**: reserve adjustments and sovereign hedging can push FX away from fundamentals near rebalance windows.
- **Validation**: low-frequency overlay; tie to reserve disclosures and cross-border flow proxies.

#### 97. EMFX Intervention Fade
- **Edge**: official intervention can create short-horizon overshoots and later normalization.
- **Validation**: intervention-day cohorts only; execution assumptions must reflect wide spreads.

#### 98. London-New York Overlap Momentum
- **Edge**: liquidity concentration and institutional handoff create session-specific continuation or reversal.
- **Validation**: intraday, session-aware backtests with exact clock alignment.

#### 99. COT Positioning Squeeze
- **Edge**: extreme speculative positioning can set up crowded squeezes in FX and rates.
- **Validation**: weekly-frequency signal; do not overfit short horizons to a weekly dataset.

#### 100. CTA Crowding / Trend Exhaustion
- **Edge**: heavily crowded trends can snap when vol spikes and reversals force de-risking.
- **Validation**: use only public or robust proxies for systematic trend exposure; regime split is essential.

### Commodities, Energy, and Real-Asset Expansion

**Representative sources**

- Commodity tactical strategies and roll yield: https://www.nber.org/papers/w11222
- Commodity futures fundamentals: https://www.nber.org/papers/w13249
- Shipping costs and inflation: https://www.imf.org/en/publications/wp/issues/2022/03/25/shipping-costs-and-inflation-515144
- EIA oil balance framework: https://www.eia.gov/finance/markets/crudeoil/balance.php
- Spark spread explainer: https://www.eia.gov/todayinenergy/includes/sparkspread_explain.php

#### 101. Commodity Time-Series Momentum
- **Edge**: trend persistence remains one of the few broad commodity effects with durable cross-market evidence.
- **Validation**: contract-normalized continuous series; roll method sensitivity test is mandatory.

#### 102. Commodity Carry / Roll Yield
- **Edge**: front-to-backwardation structure often embeds tradable risk premia.
- **Validation**: separate static carry from spot moves; include roll-cost accounting.

#### 103. Hedging Pressure / COT Commodity Signal
- **Edge**: commercial hedging and speculator crowding can forecast risk premia.
- **Validation**: weekly data only; avoid pretending it supports intraday timing.

#### 104. Seasonal Inventory Spreads
- **Edge**: normal seasonal builds and draws create predictable spread behavior in energy and ags.
- **Validation**: compare to seasonal norms, not raw levels alone.

#### 105. Crop-Weather Anomaly
- **Edge**: temperature, rainfall, and drought stress matter through crop calendars, not generic macro rules.
- **Validation**: event windows by planting, pollination, and harvest phase.

#### 106. Shipping Rate Momentum
- **Edge**: freight shocks can lead commodity and industrial supply repricing.
- **Validation**: tie route-level freight to asset exposure; control for global growth regime.

#### 107. Port Congestion / Location Spread
- **Edge**: transport bottlenecks create temporary basis and delivery dislocations.
- **Validation**: use regional prices, pipeline capacity, and outage data.

#### 108. Refinery Outage Crack Spread
- **Edge**: refinery outages reshape product balances faster than headline crude moves imply.
- **Validation**: outage calendar and inventory surprise overlays are required.

#### 109. NatGas Storage Surprise / Weather-Adjusted Signal
- **Edge**: raw storage prints matter less than surprise versus weather-implied expectation.
- **Validation**: degree-day normalization and contract-specific seasonality.

#### 110. Carbon / Power Cross-Commodity Spread
- **Edge**: emissions prices, gas, coal, and power pricing can diverge under policy or fuel-switch stress.
- **Validation**: regional market construction is critical; avoid mixing incompatible contracts.

#### 111. Copper-Gold Macro Growth Spread
- **Edge**: copper vs gold can encode growth and real-rate shifts before equities fully react.
- **Validation**: cross-asset validation versus PMIs, cyclicals, and rates.

#### 112. Gold vs Real-Rate Dislocation
- **Edge**: gold often mean-reverts toward real-yield regime once panic flow or USD noise fades.
- **Validation**: separate real-rate effect from USD effect and crisis hedge effect.

#### 113. Miners vs Bullion Basis
- **Edge**: producer equities can overshoot or lag the metal due to leverage and balance-sheet convexity.
- **Validation**: hedge production mix and currency exposure where possible.

#### 114. Livestock Feed Crush Spread
- **Edge**: feed costs and livestock pricing create fundamental margin trades that can outrun outright directional bets.
- **Validation**: margin model must include feed basket and seasonality.

#### 115. Fertilizer Input-Output Spread
- **Edge**: gas, ammonia, potash, and crop pricing create tradable agricultural margin squeezes.
- **Validation**: isolate regional pricing and policy/export restrictions.

#### 116. REIT Implied Cap-Rate vs Bonds
- **Edge**: listed real estate can decouple from rates-implied private-market cap rates.
- **Validation**: sector-specific REIT baskets; leverage and refinancing risk adjustments.

### Credit, Volatility, and Capital-Structure Expansion

**Representative sources**

- CDS-bond basis and price discovery: https://www.bis.org/publ/work160.htm
- Sovereign CDS-bond basis with arbitrage costs: https://www.bis.org/publ/work631.pdf
- Dispersion trading evidence: https://www.sciencedirect.com/science/article/abs/pii/S1044028309000593
- Closed-end fund puzzle: https://www.nber.org/papers/w3465
- Closed-end fund discount model: https://www.nber.org/papers/w10412

#### 117. CDS-Bond Basis
- **Edge**: CDS often leads cash bonds, creating basis and convergence opportunities.
- **Validation**: include transaction costs, repo, and shorting frictions explicitly.

#### 118. Index vs Single-Name CDS Dispersion
- **Edge**: credit index pricing can diverge from basket-level credit risk.
- **Validation**: rolling constituent mapping and liquidity bucket filters.

#### 119. Fallen Angel / Rising Star
- **Edge**: forced mandate flows around rating changes distort prices before normalization.
- **Validation**: bucket by index eligibility and ETF ownership.

#### 120. Downgrade / Upgrade Drift
- **Edge**: credit rating events often keep moving after the headline.
- **Validation**: distinguish expected vs surprise actions; sector-adjust abnormal returns.

#### 121. New Issue Concession
- **Edge**: fresh corporate debt frequently prices with concession that partially mean-reverts.
- **Validation**: compare to matched outstanding curve; account for syndicate stabilization.

#### 122. Distressed Reorg / Post-Default Emergence
- **Edge**: capital-structure reset names can be technically mispriced after emergence or exchange offers.
- **Validation**: catalyst-specific windows and liquidity haircuts.

#### 123. Preferred vs Common Capital-Structure Spread
- **Edge**: preferreds and common stock can react at different speeds to balance-sheet shocks.
- **Validation**: issuer-level hedge; treat yield and call features correctly.

#### 124. Bond ETF NAV Dislocation
- **Edge**: ETF premiums/discounts can reflect liquidity transformation stress rather than fair value.
- **Validation**: compare ETF price, basket estimate, and underlying cash-bond liquidity state.

#### 125. Muni-Treasury Ratio Mean Reversion
- **Edge**: municipal/Treasury relative value overshoots under tax and fund-flow stress.
- **Validation**: tax-regime aware and fund-flow conditioned.

#### 126. Agency MBS Basis
- **Edge**: agency spreads versus Treasuries can gap under convexity and balance-sheet stress.
- **Validation**: mortgage convexity overlay and financing assumptions required.

#### 127. Callable Bond vs Swaption Relative Value
- **Edge**: embedded option pricing in callable debt can diverge from listed vol markets.
- **Validation**: surface-consistent option inputs and liquidity haircut.

#### 128. Skew Risk Premium
- **Edge**: downside skew often stays rich versus realized crash frequency outside event windows.
- **Validation**: event blackout and jump-risk stress are mandatory.

#### 129. VIX / VVIX Regime Spread
- **Edge**: vol-of-vol often signals unstable short-vol regimes before realized vol catches up.
- **Validation**: treat as regime filter first, standalone trade second.

#### 130. Vol-of-Vol Mean Reversion
- **Edge**: volatility of implied volatility tends to overshoot in panic episodes.
- **Validation**: short sample fragility is high; use long history and crisis subsamples.

#### 131. Earnings / Event Volatility Gap
- **Edge**: markets misprice how much of implied vol is event-specific versus residual.
- **Validation**: event-vol stripping and post-event bleed decomposition.

#### 132. Variance / Corridor Variance Carry
- **Edge**: variance risk premia can be harvested more precisely than simple short-option rules.
- **Validation**: use surface-consistent realized and implied measures; tail stress required.

### Crypto and Digital-Asset Expansion

**Representative sources**

- Stablecoins and safe asset prices: https://www.bis.org/publ/work1270.htm
- Stablecoins and payments / regulation: https://www.bis.org/cpmi/publ/d220.htm
- BitMEX funding-rate dynamics: https://arxiv.org/abs/1912.03270
- Primer on perpetuals: https://arxiv.org/abs/2209.03307
- Crypto factor investing foundation: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3061151_code231136.pdf?abstractid=3055498

#### 133. Spot-Perp Cash-and-Carry
- **Edge**: structural basis and funding demand can create repeatable delta-neutral yield.
- **Validation**: exchange-specific borrow, haircut, and withdrawal friction must be modeled.

#### 134. Perp Funding Mean Reversion
- **Edge**: extreme funding usually marks crowded leverage that later mean-reverts.
- **Validation**: include liquidation, fees, and execution slippage by venue quality.

#### 135. Funding Term-Structure Spread
- **Edge**: near/far funding differentials can price leverage stress more cleanly than spot funding alone.
- **Validation**: multi-venue synchronization and point-in-time funding snapshot storage.

#### 136. Open-Interest / Liquidation Squeeze
- **Edge**: crowded leverage unwinds generate directional continuation followed by reversal opportunities.
- **Validation**: test pre-liquidation, cascade, and post-cascade phases separately.

#### 137. Crypto GEX Flip / Dealer Gamma
- **Edge**: options dealer hedging can stabilize or amplify price moves around large strikes and expiries.
- **Validation**: strike-level OI, IV surface, and expiry clustering are mandatory.

#### 138. Spot ETF Flow Spillover
- **Edge**: ETF subscriptions and creations can transmit regulated-market flow into spot and basis markets.
- **Validation**: tie flow timestamps to venue-level spot and derivative response.

#### 139. Stablecoin Issuance Shock
- **Edge**: new stablecoin supply can act as dry powder and safe-asset demand at the same time.
- **Validation**: separate issuance, exchange inflow, and reserve-allocation effects.

#### 140. Bridge-Flow Migration
- **Edge**: cross-chain capital migration often precedes token relative performance.
- **Validation**: bridge accounting must exclude double-counting and wash loops.

#### 141. DEX LP Concentration Alpha
- **Edge**: concentrated liquidity placement can telegraph where passive liquidity will defend or fail.
- **Validation**: pool-level, not token-level, backtests.

#### 142. Airdrop Overhang
- **Edge**: claim events and farmer distribution create predictable post-distribution supply pressure.
- **Validation**: tokenomics calendar, claim eligibility, and venue depth must all be modeled.

#### 143. Governance Proposal Repricing
- **Edge**: token price can move structurally when governance changes fee switch, treasury use, or emissions.
- **Validation**: point-in-time proposal text and voting milestones only.

#### 144. Protocol Revenue / Fee-Switch
- **Edge**: the market often reprices slowly when protocol cash-flow rights become more direct.
- **Validation**: isolate realized revenue from speculative narrative proxies.

#### 145. Lending Utilization Stress
- **Edge**: borrow utilization and reserve depletion can foreshadow squeezes and depeg risk.
- **Validation**: protocol-specific utilization and liquidation engine behavior must be modeled.

#### 146. Flash-Loan Volatility Predictor
- **Edge**: abnormal flash-loan activity can flag imminent exploit, governance, or liquidity events.
- **Validation**: high false-positive rate; use as a risk overlay unless proven otherwise.

#### 147. MEV Congestion / Failure Signal
- **Edge**: mempool stress and failed transactions often reveal unstable order-flow conditions before price gaps.
- **Validation**: chain-specific latency and gas regime segmentation.

#### 148. Exchange Outage / Venue Fragmentation Arbitrage
- **Edge**: temporary venue outages or degraded connectivity create cross-exchange dislocations.
- **Validation**: only meaningful with venue-quality and transfer-friction modeling.

#### 149. Miner Capitulation / Hash-Ribbon Regime
- **Edge**: miner stress can matter as a medium-horizon regime filter more than as a standalone trigger.
- **Validation**: use as gating signal; avoid overfitting exact crossover thresholds.

#### 150. Entity-Adjusted Whale Flow
- **Edge**: corrected wallet clustering can reveal large-holder distribution earlier than raw address counts.
- **Validation**: point-in-time cluster methodology and reclassification drift must be tracked.

### Cross-Asset Flow and Allocation Expansion

**Representative sources**

- Limits of arbitrage: https://www.nber.org/papers/w5167
- Institutional theory of momentum and reversal: https://www.nber.org/papers/w14523
- Cross-asset value and momentum: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2174501
- Carry across asset classes: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2311574
- Closing auction / passive investing: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3440239_code2427035.pdf?abstractid=3440239&mirid=1

#### 151. Risk-Parity Deleveraging Signal
- **Edge**: target-vol allocators can force cross-asset selling when realized vol rises abruptly.
- **Validation**: estimate allocator sensitivity, not just market returns.

#### 152. Vol-Control Fund Rebalance
- **Edge**: vol-targeted funds adjust exposure mechanically, especially after large realized-vol shocks.
- **Validation**: daily signal with realized-vol estimator sensitivity test.

#### 153. Pension Month-End Rebalance
- **Edge**: large benchmarked allocators rebalance equity/bond drift at predictable month-end windows.
- **Validation**: backtest only the rebalance window; avoid contaminating with generic trend.

#### 154. Quarter-End Window Dressing
- **Edge**: institutional cosmetics around quarter-end distort leadership and loser baskets.
- **Validation**: quarter-end-only cohort analysis.

#### 155. Passive Flow Crowding Detector
- **Edge**: names and sectors with heavy passive ownership can move mechanically on weight changes and flow shocks.
- **Validation**: combine ownership, turnover, and benchmark-weight sensitivity.

#### 156. Credit Impulse Equity Lead
- **Edge**: changes in credit creation can lead cyclical equity rotation and commodity demand.
- **Validation**: long-horizon macro backtest with revision-aware data vintages.

#### 157. Equity-Bond Correlation Regime Switch
- **Edge**: when stock/bond correlation flips sign, many multi-asset signals need different sizing and hedging.
- **Validation**: regime classifier must be stable and simple; use as overlay first.

#### 158. Cross-Asset Correlation Breakdown
- **Edge**: correlation shocks create dispersion opportunities and risk-off contagion trades.
- **Validation**: use rolling realized correlation with crisis subsample stress.

#### 159. Geopolitical Risk Premium Basket
- **Edge**: geopolitical shocks can create recurring safe-haven and supply-chain repricing patterns.
- **Validation**: event-based cohorts only; broad discretionary narratives are not enough.

#### 160. Global Liquidity / RRP Drain Signal
- **Edge**: liquidity plumbing can influence cross-asset beta and safe-asset scarcity.
- **Validation**: slow-moving overlay; revision-aware macro data is required.

## Protocol-Grade Validation Stack

If the goal is not just "more strategies" but **extremely strong strategies that survive live trading**, the repo should apply the existing [`TESTING_PROTOCOL.MD`](./TESTING_PROTOCOL.MD) gates plus a few additional layers that are standard in serious quant research.

**Primary validation references**

- Probability of Backtest Overfitting (PBO): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Deflated Sharpe Ratio (DSR): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Multiple-testing crisis in finance: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3299597_code434076.pdf?abstractid=3177057
- CPCV / purged testing comparison: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4686376_code4361537.pdf?abstractid=4686376&mirid=1
- White Reality Check / Hansen SPA usage in trading-rule studies: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2315379_code2110565.pdf?abstractid=2315379&mirid=1
- Efficient predictability tests under persistent predictors: https://www.nber.org/papers/w10026

**Hard acceptance stack**

- Start with the repo protocol exactly as written: Layer 0 through Layer 7, next-bar-open execution, asset-specific cost model, walk-forward freshness, Layer 2.5 gates, and forward-sample decay control.
- Add **purged walk-forward with embargo** for any overlapping label horizon.
- Add **CPCV or at minimum purged K-fold** for parameter-rich or ML-driven signals.
- Report **PBO** and **DSR**, not just raw Sharpe.
- Use **White Reality Check / Hansen SPA style** multiple-model correction whenever large strategy grids or many variants are tried.
- Reject any family that depends on one symbol, one crisis, one structural break, or one lucky parameter island.

**Monte Carlo and stress methods by asset class**

- **Equities / event strategies**: stratified event-time bootstrap by year, sector, and event bucket; short-leg borrow stress; delisting and halt simulation.
- **Rates / FX**: block bootstrap around macro days, quarter-ends, and auction windows; curve-factor shock Monte Carlo; spread-widening stress.
- **Futures / commodities**: contract-roll sensitivity tests, storage/inventory regime bootstrap, weather-seasonality block resampling, and tick-value normalization checks.
- **Options / vol**: surface-preserving delta/tenor shock Monte Carlo, jump-gap scenarios, vega/gamma liquidity stress, and calendar-spread slippage stress.
- **Crypto**: venue-aware block bootstrap, outage/depeg/liquidation cascade scenarios, funding-rate shock simulation, and withdrawal-delay stress.

**Anti-drift controls**

- Freeze all features point-in-time and store vendor vintages.
- Measure **IS vs OOS vs forward decay** explicitly; anything with large unexplained decay is probationary.
- Track **regime coverage**: no production claim unless the edge survives in at least two materially different regimes.
- Run **parameter-stability maps** and reject razor-thin peaks.
- Track **population stability / feature drift** for inputs that come from NLP, clustering, or vendor models.
- Revalidate after market-structure changes: ETF launches, contract-spec changes, stablecoin reserve changes, exchange rule changes, and benchmark methodology updates.

The next section is therefore a **quality-ranked shortlist**, not just a bigger list.

## Protocol-Grade Strong Candidates

These are the families most worth building if the objective is "strong enough to survive honest testing," not "largest possible idea pile."

#### 161. Multi-Asset Time-Series Momentum
- **Why strong**: one of the deepest cross-asset literatures with evidence across futures, rates, FX, and commodities.
- **Best backtests**: contract-normalized continuous futures; purged walk-forward; crisis subsample; carry-interaction split.
- **Anti-drift**: dynamic crash filter and panic-state sizing are mandatory because momentum crashes are real.

#### 162. Dynamic Crisis-Alpha Trend Following
- **Why strong**: trend following improves when volatility state and panic regime are used to adapt risk.
- **Best backtests**: same as 161 plus hidden-state or simple regime overlays tested only out of sample.
- **Anti-drift**: keep regime model simple; complexity often just hides a vol-timed momentum strategy.

#### 163. Cross-Asset Carry Basket
- **Why strong**: carry has broad academic support across bonds, FX, commodities, equities, and options.
- **Best backtests**: asset-specific carry definitions; recession and funding-stress subsamples; CPCV for portfolio construction.
- **Anti-drift**: strong recession and funding drawdown caps are required.

#### 164. FX Carry + Value + Momentum Composite
- **Why strong**: the blend is empirically stronger and more diversified than pure carry.
- **Best backtests**: daily/weekly rebalancing comparison, spread+carry costs, intervention-day exclusions.
- **Anti-drift**: avoid over-optimizing weights; equal-risk sleeves usually generalize better.

#### 165. PEAD with Attention Filter
- **Why strong**: underreaction is persistent, and attention filters improve signal quality.
- **Best backtests**: event-time cohorts, announcement-date holdouts, borrow-aware short leg, delisting-adjusted returns.
- **Anti-drift**: if the edge disappears outside small caps or Friday clusters, do not market it as broad equity alpha.

#### 166. Analyst Revision Momentum with Borrow Stress
- **Why strong**: revisions update slower than price in many names, especially outside mega-cap coverage.
- **Best backtests**: point-in-time estimate history; sector-neutral portfolios; short borrow and crowding haircuts.
- **Anti-drift**: revision vendors and methodology shifts must be versioned.

#### 167. Spin-Off Forced Selling
- **Why strong**: it is a structural mandate-mismatch trade, not a fragile chart pattern.
- **Best backtests**: event studies from announcement through first 3-12 months post distribution.
- **Anti-drift**: only keep cohorts with true forced-selling mechanics, not every corporate separation.

#### 168. Merger Arbitrage with Regulatory Filter
- **Why strong**: corporate-action spreads are economically grounded and catalyst-driven.
- **Best backtests**: deal-by-deal framework with financing, borrow, and antitrust regime features.
- **Anti-drift**: never evaluate on price spread alone; regulatory climate changes can break old averages.

#### 169. Treasury On/Off-the-Run plus Auction Cycle RV
- **Why strong**: both edges come from liquidity segmentation and issuance mechanics.
- **Best backtests**: tenor-specific RV baskets; financing and specials included; auction-state segmentation.
- **Anti-drift**: balance-sheet regulation changes can alter the edge, so revalidate after market-structure shifts.

#### 170. Cross-Currency Basis Mean Reversion
- **Why strong**: balance-sheet scarcity and hedging demand repeatedly create basis dislocations.
- **Best backtests**: quarter-end and stress-window cohorts; tenor-specific basis curves; financing costs.
- **Anti-drift**: do not assume CIP breaks are free money; capital usage can erase paper alpha.

#### 171. Treasury End-of-Month Rebalance
- **Why strong**: benchmark extension flow is mechanical and recurring.
- **Best backtests**: month-end-only windows; duration-extension forecast from index methodology.
- **Anti-drift**: effect size can compress after broad publication, so trade capacity matters.

#### 172. Inflation Breakeven Relative Value
- **Why strong**: breakevens reflect both inflation views and liquidity distortions, giving multiple independent drivers.
- **Best backtests**: TIPS vs nominals vs swaps; policy-shock windows; liquidity-state segmentation.
- **Anti-drift**: if the edge is really just a liquidity trade, size it as such.

#### 173. Commodity Carry with Inventory State
- **Why strong**: roll yield is materially stronger when conditioned on inventory scarcity.
- **Best backtests**: inventory quintiles, roll-method sensitivity, commodity-by-commodity validation.
- **Anti-drift**: avoid generic pooled rules that ignore contract-specific storage economics.

#### 174. Crack Spread with Outage and Inventory Gating
- **Why strong**: refinery margins have direct economic interpretation and recurring catalysts.
- **Best backtests**: outage calendar, seasonal demand, and product inventory surprise interaction.
- **Anti-drift**: maintain regional contract consistency; mismatched locations create fake alpha.

#### 175. Gold vs Real-Rate Dislocation
- **Why strong**: gold repeatedly re-prices around real-yield changes with well-known lag/overshoot episodes.
- **Best backtests**: cross-asset framework using real yields, USD, and risk-off controls.
- **Anti-drift**: crisis beta can dominate for periods, so treat as conditional RV, not fixed beta.

#### 176. CDS-Bond Basis
- **Why strong**: the two markets often adjust at different speeds, especially in stress.
- **Best backtests**: issuer-level basis series with transaction cost and financing model.
- **Anti-drift**: liquidity and shorting friction are part of the signal, not nuisance noise to ignore.

#### 177. Fallen Angel / Rising Star
- **Why strong**: forced benchmark turnover and mandate effects are structural.
- **Best backtests**: rating-event cohorts, ETF ownership overlay, liquidity bucket segmentation.
- **Anti-drift**: rating-agency policy shifts and index-rule changes require periodic refresh.

#### 178. Bond ETF NAV Dislocation
- **Why strong**: ETF liquidity transformation creates real tradable stress episodes.
- **Best backtests**: premium/discount, iNAV proxy, basket liquidity, and primary-market activity.
- **Anti-drift**: treat this as episodic alpha; outside stress it often disappears.

#### 179. Convertible Arbitrage
- **Why strong**: embedded option, equity hedge, and credit spread give multiple valuation anchors.
- **Best backtests**: option-value model, borrow costs, callable features, and credit spread sensitivity.
- **Anti-drift**: issuance waves and borrow regimes can change economics materially.

#### 180. Dispersion / Implied Correlation
- **Why strong**: it is one of the cleaner structural vol trades when basket and single-name implementation is disciplined.
- **Best backtests**: surface-consistent constituent/index options; sector-neutral basket construction.
- **Anti-drift**: crowding and correlation regime shifts can make static short-index / long-single-name rules dangerous.

#### 181. Event Volatility around Earnings and FOMC
- **Why strong**: known catalysts create explicit mispricing opportunities in vol term structure.
- **Best backtests**: event-vol stripping, announcement-specific expected move models, post-event bleed.
- **Anti-drift**: keep catalyst-specific models separate; do not pool earnings and macro blindly.

#### 182. Equity Index Gamma / Pinning
- **Why strong**: dealer hedging around large expiries and strikes is structurally grounded.
- **Best backtests**: strike-level OI and IV history, expiry clustering, intraday execution study.
- **Anti-drift**: market-maker behavior changes as option market structure evolves, so refresh the map frequently.

#### 183. Volatility Risk Premium with Event Filters
- **Why strong**: VRP is persistent, but only when you avoid obvious jump-risk windows.
- **Best backtests**: implied-realized spread with explicit event blackout and tail-gap stress.
- **Anti-drift**: if most PnL comes from one low-vol era, the strategy is not protocol-grade.

#### 184. Stablecoin Peg and Lending Plumbing
- **Why strong**: redemptions, reserve frictions, and borrow scarcity create economically grounded dislocations.
- **Best backtests**: mint/redeem flows, lending rates, depeg windows, and reserve-change events.
- **Anti-drift**: reserve transparency and exchange policy changes can invalidate old behavior quickly.

#### 185. Spot-Perp Cash-and-Carry
- **Why strong**: one of the clearest structural crypto yield trades when frictions are honestly modeled.
- **Best backtests**: venue-level fees, borrow, haircut, transfer delay, and liquidation-risk stress.
- **Anti-drift**: exchange credit risk and basis compression are the core threats.

#### 186. Perp Funding Mean Reversion
- **Why strong**: extreme funding usually reflects crowded leverage rather than durable fundamentals.
- **Best backtests**: funding deciles, liquidation-cluster overlay, cross-venue confirmation.
- **Anti-drift**: exchange rule changes to funding formulas can alter the signal quickly.

#### 187. Open-Interest / Liquidation Cascade Reversal
- **Why strong**: forced liquidations create predictable overextension and snapback behavior.
- **Best backtests**: pre-cascade, cascade, and post-cascade sub-strategies tested separately.
- **Anti-drift**: if the strategy only works on one exchange or one coin, it stays experimental.

#### 188. Token Unlock Supply Overhang
- **Why strong**: supply schedule is known in advance and liquidity is often thin.
- **Best backtests**: unlock size vs float, exchange depth, and borrow availability.
- **Anti-drift**: treasury behavior and OTC hedging can offset unlock effects, so governance context matters.

#### 189. Exchange-Reserve / Whale-Flow Regime
- **Why strong**: entity-adjusted flow regimes can shift before price fully reflects them.
- **Best backtests**: regime classification by exchange balances, stablecoin inflows, and whale transfer patterns.
- **Anti-drift**: clustering methodology drift must be versioned and audited.

#### 190. ETF Create/Redeem Flow
- **Why strong**: creation/redemption mechanics are one of the cleanest modern forced-flow edges.
- **Best backtests**: shares-outstanding changes, AUM flow shocks, basket impact by top holdings.
- **Anti-drift**: crowding is the main decay risk; keep capacity estimates front and center.

#### 191. Index Inclusion / Russell Reconstitution
- **Why strong**: passive benchmark effects remain economically real and calendar-based.
- **Best backtests**: announcement-to-effective-date and reversal-phase decomposition.
- **Anti-drift**: broad publication has likely compressed the easy part, so execution quality matters.

#### 192. Closing Auction Imbalance Reversal
- **Why strong**: passive closing flow is structurally motivated and often transient.
- **Best backtests**: MOC imbalance buckets, overnight reversal, and large-flow day segmentation.
- **Anti-drift**: changes in closing-auction participation or market-structure rules can alter edge size.

#### 193. Buyback Restart / Blackout Edge
- **Why strong**: corporate buyback flow is real and recurring, especially in large caps.
- **Best backtests**: blackout and restart windows tied to earnings calendar and realized repurchase history.
- **Anti-drift**: authorization headlines are weaker than actual execution; do not confuse them.

#### 194. Dividend Initiation / Omission Drift
- **Why strong**: payout policy changes have durable, economically intuitive signal content.
- **Best backtests**: separate initiations, increases, cuts, and omissions; sector-normalize.
- **Anti-drift**: changing payout norms can dilute pooled averages, so recency weighting helps.

#### 195. Passive Flow Crowding plus Vol-Control Rebalance
- **Why strong**: both rely on mechanical allocators rather than discretionary narratives.
- **Best backtests**: ownership-weighted crowding signal plus daily vol-target rebalance estimator.
- **Anti-drift**: these effects crowd easily, so expected capacity is smaller than headline backtests imply.

#### 196. Risk-Parity Deleveraging
- **Why strong**: allocator deleveraging is economically grounded and cross-asset by construction.
- **Best backtests**: realized-vol shocks, cross-asset covariance changes, and target-vol proxy models.
- **Anti-drift**: only useful if the proxy really tracks allocator behavior; otherwise it is just macro storytelling.

#### 197. Macro Release Surprise Drift
- **Why strong**: underreaction around major releases shows up in multiple asset classes.
- **Best backtests**: surprise-signed event studies, cross-asset windows, and no-overlap event filtering.
- **Anti-drift**: news-vendor methodology and benchmark survey changes must be frozen point in time.

#### 198. Fixing-Flow Window Trade
- **Why strong**: concentrated benchmark execution is structural, not theoretical.
- **Best backtests**: intraday trade/quote data by fix window, liquidity bucket, and day type.
- **Anti-drift**: the edge can decay if too many liquidity providers target the same window.

#### 199. Spark Spread / Carbon-Power Relative Value
- **Why strong**: fuel-switch economics create direct, explainable margin trades.
- **Best backtests**: plant-level or regional spread proxies, outage calendar, weather regime tests.
- **Anti-drift**: policy and grid structure matter; keep regions separate.

#### 200. Capital Structure Arbitrage
- **Why strong**: equity, debt, and options should not stay inconsistent forever when the issuer is liquid enough.
- **Best backtests**: structural credit model plus realized event windows; include borrow and financing.
- **Anti-drift**: most paper alpha dies in frictions, so only the most liquid issuers should graduate.

## One More Strong Strategy Per Asset Class

This is the tighter addendum. Each idea below has reasonably strong paper-level support for positive expectancy or solid risk-adjusted returns, but that evidence is **not** a live guarantee. Every one still has to survive [`TESTING_PROTOCOL.MD`](./TESTING_PROTOCOL.MD), realistic costs, and forward decay checks.

#### 201. Equities: Quality Minus Junk
- **Why this one**: if you want one more equity strategy with a real literature behind it, this is cleaner than another fragile chart pattern. Long profitable, growing, safer, well-managed firms; short low-quality junk.
- **Paper-level evidence**: Asness, Frazzini, and Pedersen report that QMJ earns significant risk-adjusted returns, with an information ratio above 1 in the U.S. and across 24 countries.
- **Best backtests**: point-in-time fundamentals only, monthly rebalance, sector-neutral and beta-neutral versions, short borrow costs, and delisting handling.
- **Main failure mode**: stale accounting data and accidental lookahead will fake the edge immediately.
- **Sources**:
  - QMJ paper: https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/Quality-Minus-Junk.pdf
  - QMJ dataset note: https://www.aqr.com/insights/datasets/quality-minus-junk-factors-daily

#### 202. Rates: Cochrane-Piazzesi Forward-Rate Bond Premium
- **Why this one**: it is one of the most defensible rates signals in the literature. Use the tent-shaped forward-rate factor to forecast excess Treasury returns and tilt duration or curve exposure accordingly.
- **Paper-level evidence**: Cochrane and Piazzesi report that a single forward-rate factor predicts 1-year excess returns on 1-5 year maturity bonds, with R2 up to 43%.
- **Best backtests**: yield-curve snapshots frozen point in time, roll-down separated from forecast alpha, tenor-specific walk-forward, auction-window stress, and financing assumptions.
- **Main failure mode**: confusing forecast power with implementable trade PnL after duration, financing, and rebalance costs.
- **Sources**:
  - NBER working paper: https://www.nber.org/papers/w9178
  - SSRN version on expected Treasury returns: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2588853_code598300.pdf?abstractid=1709636&mirid=1

#### 203. FX: Currency Momentum
- **Why this one**: carry gets crowded and crashy; currency momentum is a distinct sleeve with different drivers and better diversification value.
- **Paper-level evidence**: Menkhoff, Sarno, Schmeling, and Schrimpf report a cross-sectional spread in excess returns of up to 10% per year between past winner and loser currencies.
- **Best backtests**: spot-plus-forward total return construction, G10 vs EM split, weekly/monthly rebalance comparison, intervention-day flags, and spread-cost haircuts by currency bucket.
- **Main failure mode**: using spot-only returns and ignoring forward carry, fix timing, and wide-spread EM execution.
- **Sources**:
  - BIS working paper / JFE version listing: https://ideas.repec.org/p/bis/biswps/366.html
  - Trend-following revisit in currencies: https://papers.ssrn.com/Sol3/Delivery.cfm/SSRN_ID2949379_code2672176.pdf?abstractid=2949379

#### 204. Commodities: Momentum Plus Term-Structure Double Sort
- **Why this one**: this is stronger than plain commodity momentum because it conditions on curve shape. Long backwardated winners, short contangoed losers.
- **Paper-level evidence**: Fuertes, Miffre, and Rallis report annualized alphas of 10.14% for momentum, 12.66% for term structure, and 21.02% for the combined double-sort strategy; they also report robustness net of reasonable transaction costs.
- **Best backtests**: continuous-contract construction sensitivity, roll-method sensitivity, only liquid contracts, slippage by commodity bucket, and seasonality / inventory regime splits.
- **Main failure mode**: fake alpha from bad back-adjustment or from mixing illiquid contract histories with liquid execution assumptions.
- **Sources**:
  - Commodity momentum + term structure: https://www.sciencedirect.com/science/article/pii/S0378426610001354
  - Curve-aware extension: https://www.sciencedirect.com/science/article/pii/S0378426614002751

#### 205. Credit: Corporate Bond Value plus Short-Maturity Composite
- **Why this one**: if you want a credit strategy with better odds of surviving costs, start with cross-sectional corporate bond premia that still show up net of transaction costs instead of reaching for exotic distressed trades first.
- **Paper-level evidence**: Baltussen, Muskens, and Verwijmeren report that, net of costs, four factors offer unique, robust, and sizable corporate bond return premia, led by short maturity and bond value among the cleaner implementation candidates.
- **Best backtests**: TRACE-style transaction-cost model, duration-matched and rating-matched construction, issue-age controls, ETF-flow stress, and liquidity bucket exclusions.
- **Main failure mode**: paper alpha disappears if turnover and dealer spread assumptions are too optimistic.
- **Sources**:
  - Corporate bond cross-section: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5130312
  - New-bond pricing and liquidity effects: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2161452_code77772.pdf?abstractid=2161452&mirid=1

#### 206. Crypto: Cross-Sectional Cryptocurrency Carry
- **Why this one**: this is different from basic spot-perp cash-and-carry. Rank liquid cryptocurrencies by carry / interest differential and trade high-carry versus low-carry names in a cross-sectional book.
- **Paper-level evidence**: Fan, Jiao, Lu, Tong report an annualized return of 43.4% with a Sharpe ratio of 0.74 for a high-interest minus low-interest cryptocurrency carry trade.
- **Best backtests**: venue-level borrow and funding data, exchange-credit haircuts, delisting and collapse handling, liquidation-cascade stress, and portfolio-level caps by exchange and token family.
- **Main failure mode**: ignoring exchange failure risk, withdrawal delays, and fake yield signals from thin venues.
- **Sources**:
  - Crypto carry trade paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4666425
  - Realistic crypto momentum benchmark: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4675565

## Bottom Line

The catalog is now much broader, but breadth is not the hard part anymore.

The practical next move is:

- use **54-160** as the expanded research inventory
- treat **161-200** as the serious build queue
- treat **201-206** as the extra high-conviction per-asset-class addendum
- enforce [`TESTING_PROTOCOL.MD`](./TESTING_PROTOCOL.MD) plus CPCV / PBO / DSR / Reality Check style anti-overfit controls
- pick only strategies that survive realistic friction, regime, and drift tests

That is the path to more strategies **without** quietly lowering quality.
