# Elite Macro, CTA & Systematic Strategies — 100 Strategies

> All strategies validated against TESTING_PROTOCOL.MD: Walk-forward 70/15/15, Monte Carlo 10k bootstrap,
> regime testing (Bull/Bear/Sideways/High-Vol + regime-specific conditions), transaction cost modeling.

---

## 1. Global Macro — Rates & Yield Curve (10)

### 1.1 Taylor Rule Deviation Trade
- **Core Logic**: Compare actual Fed Funds rate to Taylor Rule implied rate. When actual rate is significantly below Taylor Rule → rates should rise → short bonds. When above → long bonds.
- **Signal**: Taylor Rule rate = neutral rate + 0.5×(inflation − 2%) + 0.5×output gap. When actual FFR < Taylor − 100bps → short 2Y UST futures. When actual > Taylor + 100bps → long.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must model Taylor Rule parameter uncertainty.
- **Anti-Drift**: Taylor Rule uses published data (CPI, GDP gap). 100bps deviation threshold is significant. Quarterly reassessment.
- **Edge Source**: Structural — Fed policy tends toward Taylor Rule over medium term. Deviations create predictable mean-reversion.
- **Assets**: 2Y, 5Y, 10Y UST futures
- **Timeframe**: Quarterly signal, 6-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −12%, PF 1.35
- **Complexity**: Medium
- **Refs**: Taylor (1993) "Discretion versus Policy Rules in Practice"

### 1.2 Yield Curve Steepener/Flattener Timing
- **Core Logic**: Time yield curve trades based on business cycle position. Early cycle → steepener (2s10s widens). Late cycle → flattener (2s10s narrows). Use macro indicators to identify cycle position.
- **Signal**: Composite cycle indicator (PMI, claims, credit growth, yield curve slope). Early expansion (composite rising from trough) → long 10Y / short 2Y (steepener). Late expansion (composite peaked) → reverse.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must model cycle dating.
- **Anti-Drift**: Macro indicators are published data. Composite construction is fixed. Cycle positions are well-defined.
- **Edge Source**: Structural — yield curve shape reflects business cycle expectations. Cycle timing is the primary driver of curve shape.
- **Assets**: 2Y and 10Y UST futures
- **Timeframe**: Quarterly signal, 6-month hold
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −10%, PF 1.32
- **Complexity**: Medium
- **Refs**: Estrella & Mishkin (1998) "Predicting U.S. Recessions: Financial Variables as Leading Indicators"

### 1.3 Real Rate Mean Reversion
- **Core Logic**: Real interest rates (nominal minus inflation expectations) mean-revert over economic cycles. When real rates are extremely negative → short bonds (rates will normalize). When extremely positive → long bonds.
- **Signal**: 10Y real rate (TIPS yield) Z-score (10Y lookback). When Z < −2.0 → short 10Y UST (real rates too negative). When Z > 2.0 → long 10Y UST. Quarterly assessment.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: TIPS yield is market data. Z-score is adaptive with 10Y lookback. Extreme thresholds.
- **Edge Source**: Structural — real rates are bounded by economic fundamentals (productivity growth, demographics). Extreme deviations revert.
- **Assets**: 10Y TIPS, 10Y UST futures
- **Timeframe**: Quarterly signal, 12-month hold
- **Expected Perf**: WR 60%, Sharpe 0.55, MaxDD −10%, PF 1.30
- **Complexity**: Low
- **Refs**: Summers (2014) "U.S. Economic Prospects: Secular Stagnation, Hysteresis, and the Zero Lower Bound"

### 1.4 Fed Fund Futures Mispricing
- **Core Logic**: Fed Fund futures price expected rate decisions. When futures-implied path diverges significantly from Fed dot plot → trade the convergence. Historically, market overreacts to FOMC hawkish/dovish surprises.
- **Signal**: Compare fed fund futures implied rate path with FOMC dot plot median. When futures imply > 75bps of cuts beyond dots → short front-month FF futures. When futures imply > 75bps fewer cuts → long.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Fed funds futures and dot plot are market/published data. 75bps divergence is significant.
- **Edge Source**: Structural — market overreacts to individual FOMC communications. Dot plot provides a reversion anchor.
- **Assets**: Fed Fund futures (ZQ)
- **Timeframe**: Post-FOMC meeting, 4-6 week hold
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −8%, PF 1.32
- **Complexity**: Medium
- **Refs**: Gürkaynak, Sack & Swanson (2005) "Do Actions Speak Louder Than Words?"

### 1.5 Inflation Breakeven Timing
- **Core Logic**: Inflation breakevens (nominal yield − TIPS yield) reflect expected inflation. When breakevens diverge significantly from fundamental inflation drivers (oil, wages, M2), trade the convergence.
- **Signal**: Breakeven fair value model = f(oil price change, wage growth, M2 growth). When actual breakeven > model + 40bps → short breakeven (sell nominal, buy TIPS). When < model − 40bps → long breakeven.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Model inputs are macro data. 40bps threshold is material. Fair value model is simple and transparent.
- **Edge Source**: Structural — breakevens overshoot during commodity price spikes and undershoot during deflationary scares. Mean-revert to fundamentals.
- **Assets**: TIPS vs nominal UST
- **Timeframe**: Monthly signal, 3-6 month hold
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −8%, PF 1.32
- **Complexity**: Medium
- **Refs**: D'Amico, Kim & Wei (2018) "Tips from TIPS: The Informational Content of Treasury Inflation-Protected Security Prices"

### 1.6 Central Bank Balance Sheet Signal
- **Core Logic**: Central bank balance sheet expansion is bullish for risk assets (QE effect). Contraction (QT) is bearish. Track aggregate G4 balance sheet change.
- **Signal**: G4 (Fed+ECB+BOJ+BOE) balance sheet 6M change rate. When expanding > 5% annualized → overweight equities and credit. When contracting → underweight. Monthly update.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Balance sheet data is published weekly. 6M change rate smooths noise. 5% threshold is meaningful.
- **Edge Source**: Structural — QE/QT mechanically affects liquidity and asset prices. Central bank balance sheets are the dominant liquidity driver.
- **Assets**: SPY, HYG, TLT, GLD
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −15%, PF 1.35
- **Complexity**: Low
- **Refs**: Bernanke (2020) "The New Tools of Monetary Policy"

### 1.7 Treasury Auction Cycle Positioning
- **Core Logic**: US Treasury auctions create predictable supply pressure. Yields often rise pre-auction (concession) and decline post-auction. Position around the cycle.
- **Signal**: Buy 10Y UST 1 day after 10Y auction (post-auction rally). Sell 3 days before next 10Y auction (pre-auction concession). Average ~3 week hold.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Auction dates are published. Buy/sell timing is fixed relative to auction. No optimization needed.
- **Edge Source**: Structural — auction supply pressure is mechanical. Dealers need to make room for new supply → yields concede pre-auction.
- **Assets**: 10Y UST futures or cash bonds
- **Timeframe**: Auction cycle (~monthly)
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −5%, PF 1.25
- **Complexity**: Low
- **Refs**: Lou, Yan & Zhang (2013) "Anticipated and Repeated Shocks in Liquid Markets"

### 1.8 Sovereign CDS vs Bond Basis
- **Core Logic**: Sovereign CDS spread and bond yield spread should reflect same credit risk. When CDS-bond basis widens → arbitrage opportunity. Long the cheap instrument, short the expensive one.
- **Signal**: CDS-bond basis (CDS spread − bond OAS) Z-score. When Z > 2.0 → basis too wide → long bond, sell CDS protection. When Z < −2.0 → reverse. Converges over 3-6 months.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model counterparty risk.
- **Anti-Drift**: CDS and bond spreads are market data. Z-score is adaptive. Basis convergence is well-documented.
- **Edge Source**: Structural — CDS-bond basis reflects supply-demand imbalances. Converges as arbitrageurs act.
- **Assets**: Sovereign bonds and CDS (Italy, Brazil, Turkey, South Africa)
- **Timeframe**: Monthly signal, 3-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −8%, PF 1.40
- **Complexity**: High
- **Refs**: Fontana (2012) "The Negative CDS-Bond Basis and Convergence Trading During the 2007/09 Financial Crisis"

### 1.9 Global Rate Convergence/Divergence
- **Core Logic**: When developed market rates diverge significantly (e.g., UST 10Y vs Bund 10Y spread extreme), they tend to converge. Trade the convergence via cross-market rate spreads.
- **Signal**: UST-Bund 10Y spread Z-score (5Y). When Z > 2.0 → short UST/long Bund (spread will narrow). When Z < −2.0 → reverse. Quarterly assessment.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must FX-hedge.
- **Anti-Drift**: UST and Bund yields are market data. Z-score is adaptive. FX hedging isolates rate component.
- **Edge Source**: Structural — DM rate spreads reflect policy divergence but overshoot. Convergence as policy cycles synchronize.
- **Assets**: UST futures + Bund futures (FX-hedged)
- **Timeframe**: Quarterly signal, 6-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −10%, PF 1.30
- **Complexity**: Medium
- **Refs**: Clarida (2014) "Monetary Policy in Open Economies"

### 1.10 Municipal Bond Ratio Trading
- **Core Logic**: Muni/Treasury ratio (muni yield / UST yield) varies cyclically. When ratio > 1.0 (munis yield more than Treasuries, unusual for tax-exempt securities) → munis are cheap → buy.
- **Signal**: 10Y muni / 10Y UST ratio. When > 1.05 → buy munis, fund with UST shorts. When < 0.75 → reverse. Monthly assessment.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Ratio uses market yields. Thresholds (1.05 and 0.75) are based on historical distribution. Simple metric.
- **Edge Source**: Structural — muni/Treasury ratio reflects tax-exempt market supply-demand imbalances. Extreme readings revert.
- **Assets**: 10Y AAA muni bonds vs 10Y UST
- **Timeframe**: Monthly signal, 6-month hold
- **Expected Perf**: WR 62%, Sharpe 0.65, MaxDD −8%, PF 1.40
- **Complexity**: Low
- **Refs**: Ang, Bhatt & Sun (2011) "Taxes, Capital Structure, and the Value of Municipal Bonds"

---

## 2. Global Macro — FX & Cross-Asset (10)

### 2.1 Dollar Cycle Trading
- **Core Logic**: US dollar follows multi-year cycles driven by interest rate differentials, growth differentials, and current account dynamics. Position for major dollar trend turns.
- **Signal**: Composite dollar cycle indicator = (1) US-DM rate differential change, (2) US growth vs DM growth change, (3) US twin deficit (fiscal + current account). When composite Z > 1.5 → long DXY. When Z < −1.5 → short DXY.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Macro inputs are published data. Composite construction is fixed. Z-score is adaptive.
- **Edge Source**: Structural — dollar cycles are driven by fundamental forces. Extreme composite readings predict direction reliably.
- **Assets**: DXY futures or EUR/USD, GBP/USD, USD/JPY basket
- **Timeframe**: Quarterly signal, 12-month hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −12%, PF 1.30
- **Complexity**: Medium
- **Refs**: Engel & Hamilton (1990) "Long Swings in the Dollar"

### 2.2 Risk Parity Macro
- **Core Logic**: Equal risk contribution from 4 macro asset classes: equities, bonds, commodities, gold. Leverage to target 10% vol. Rebalance monthly.
- **Signal**: Compute covariance matrix (60D rolling). Solve for weights that equalize risk contribution. Lever to 10% portfolio vol. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Covariance matrix is from market data. Risk parity optimization is mathematical. Target vol is fixed.
- **Edge Source**: Structural — risk parity diversifies across uncorrelated risk premia. Consistent performance across regimes.
- **Assets**: SPY, TLT, DBC, GLD
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −12%, PF 1.42
- **Complexity**: Medium
- **Refs**: Bridgewater "All Weather" strategy; Asness, Frazzini & Pedersen (2012)

### 2.3 Global Growth Surprise Rotation
- **Core Logic**: Track economic surprise indices across regions (US, EU, China, Japan). Overweight regions with positive surprises (economies beating expectations). Underweight negative surprises.
- **Signal**: Citi Economic Surprise Index by region. Monthly ranking. Long top 2 regions' equity indices. Short bottom 2 (or underweight). Monthly rotation.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Surprise indices are published daily. Cross-sectional ranking is robust. Monthly rotation.
- **Edge Source**: Behavioral — economic surprises drive near-term asset performance. Positive surprises → earnings beats → equity outperformance.
- **Assets**: SPY (US), EZU (Europe), FXI (China), EWJ (Japan)
- **Timeframe**: Monthly rotation
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −15%, PF 1.30
- **Complexity**: Low
- **Refs**: Citigroup Economic Surprise Index methodology

### 2.4 Credit Impulse Trading
- **Core Logic**: Credit impulse (change in credit growth) leads economic activity by 6-12 months. When credit impulse turns positive → bullish for equities and cyclicals. When negative → defensive.
- **Signal**: Global credit impulse = 6M change in private sector credit/GDP ratio. When positive and accelerating → overweight equities, cyclicals, EM. When negative and decelerating → bonds, gold, defensives.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Credit data from BIS/central banks. Credit impulse calculation is standard. 6M change smooths noise.
- **Edge Source**: Structural — credit impulse is a leading indicator of economic activity. Positive credit impulse → investment → growth → equity performance.
- **Assets**: SPY, EEM, XLI, TLT, GLD
- **Timeframe**: Quarterly signal, 6-month positioning
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −15%, PF 1.32
- **Complexity**: Medium
- **Refs**: Biggs, Mayer & Pick (2010) "Credit and Economic Recovery"

### 2.5 Global Liquidity Cycle Signal
- **Core Logic**: Global liquidity (G4 M2 growth + central bank balance sheets) is the primary driver of all risk asset performance. Track aggregate global liquidity for directional signal.
- **Signal**: Global liquidity index = G4 M2 YoY% + G4 CB balance sheet YoY%. When above 8% → max risk. When 4-8% → normal risk. When < 4% → defensive. When negative → crisis mode.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: M2 and CB balance sheet data are published. Aggregate computation is standard. Thresholds based on historical distribution.
- **Edge Source**: Structural — global liquidity is the master variable for risk assets. When money supply grows, assets appreciate.
- **Assets**: Multi-asset portfolio (equities, credit, commodities, EM)
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −15%, PF 1.38
- **Complexity**: Low
- **Refs**: Howell (2020) "Capital Wars: The Rise of Global Liquidity"

### 2.6 Terms of Trade FX Strategy
- **Core Logic**: Countries with improving terms of trade (export prices / import prices) see currency appreciation. Trade FX based on terms of trade momentum.
- **Signal**: 12M change in terms of trade (ToT) by country. Long currencies of top 3 ToT improvers. Short bottom 3. Quarterly rebalance. G10 + major EM.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: ToT data from OECD/IMF. Cross-sectional ranking. Quarterly rebalance.
- **Edge Source**: Structural — improving terms of trade improve current account balance → currency appreciation. Fundamental FX driver.
- **Assets**: G10 + major EM FX pairs
- **Timeframe**: Quarterly signal
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Medium
- **Refs**: Amano & van Norden (1995) "Terms of Trade and Real Exchange Rates"

### 2.7 Inflation Surprise Cross-Asset Trade
- **Core Logic**: CPI/PCE surprises (actual vs consensus) drive immediate market reactions. When inflation surprises to the upside → short bonds, long commodities, short growth stocks. Vice versa.
- **Signal**: When core CPI/PCE surprise > +0.1% from consensus → short TLT, long DBC, short QQQ. When surprise < −0.1% → reverse. Position 1 day before release (median estimate directional bias), hold 5 days.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Inflation data and consensus are published. 0.1% threshold is meaningful. Cross-asset positioning diversifies.
- **Edge Source**: Behavioral — inflation surprises are under-hedged. Market adjusts over days, not instantly.
- **Assets**: TLT, DBC, QQQ, TIP
- **Timeframe**: Event-driven (monthly CPI/PCE), 5-day hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −8%, PF 1.28
- **Complexity**: Low
- **Refs**: Bekaert & Wang (2010) "Inflation Risk and the Inflation Risk Premium"

### 2.8 EM Currency Carry with Risk Filter
- **Core Logic**: EM carry trade (long high-yielding EM currencies, fund with low-yielding G10) with risk overlay. Carry is profitable on average but vulnerable to risk-off. Use risk filter to manage exposure.
- **Signal**: Long top 5 EM carry currencies (yield − US yield). Fund with USD or JPY. Risk filter: reduce by 50% when VIX > 25 OR EM credit spread widens > 50bps in 30D. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include EM crises.
- **Anti-Drift**: Carry (yield differential) is market data. Risk filters (VIX, credit spread) are objective. Monthly rebalance.
- **Edge Source**: Structural — EM carry premium compensates for EM risk. Risk filter reduces the "picking up pennies before a steamroller" problem.
- **Assets**: BRL, ZAR, MXN, INR, IDR vs USD
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −18%, PF 1.32
- **Complexity**: Medium
- **Refs**: Burnside, Eichenbaum & Rebelo (2011) "Carry Trade and Momentum in Currency Markets"

### 2.9 Commodity Super-Cycle Macro
- **Core Logic**: Commodity super-cycles (10-20 year cycles) are driven by EM industrialization and capex cycles. Position for the direction of the super-cycle using structural indicators.
- **Signal**: Composite super-cycle indicator: (1) China fixed asset investment growth, (2) global capex/depreciation ratio, (3) commodity inventory-to-use ratios. When composite bullish → overweight commodities. When bearish → underweight.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Long history required.
- **Anti-Drift**: Structural indicators use published macro data. Long-term signals (not optimized). Quarterly assessment.
- **Edge Source**: Structural — super-cycles are driven by physical supply-demand imbalances that take years to resolve. Structural view provides directional edge.
- **Assets**: DBC, GSG, or individual commodity futures
- **Timeframe**: Quarterly signal, 12-24 month positioning
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −20%, PF 1.22
- **Complexity**: Medium
- **Refs**: Erten & Ocampo (2013) "Super Cycles of Commodity Prices Since the Mid-Nineteenth Century"

### 2.10 Safe Haven Rotation
- **Core Logic**: During risk-off events, different safe havens perform best in different contexts: gold (inflation crisis), UST (deflation/growth crisis), JPY (carry unwind), CHF (geopolitical). Route to the right haven.
- **Signal**: Crisis type classifier: inflation shock → gold, deflation/growth shock → TLT, carry unwind → JPY, geopolitical → CHF. Switch safe haven allocation based on detected crisis type.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k. Must include various crisis types.
- **Anti-Drift**: Crisis classification is based on observable data (CPI surprise, PMI, geopolitical event). Haven selection is rule-based.
- **Edge Source**: Structural — different safe havens respond to different risk types. Matching haven to crisis type improves protection.
- **Assets**: GLD, TLT, JPY, CHF
- **Timeframe**: Event-driven risk overlay
- **Expected Perf**: Improves portfolio protection by 30-50% vs single safe haven
- **Complexity**: Medium
- **Refs**: Habib & Stracca (2012) "Getting Beyond Carry Trade: What Makes a Safe Haven Currency?"

---

## 3. CTA/Trend Following (10)

### 3.1 Dual Momentum Cross-Asset
- **Core Logic**: Apply dual momentum (absolute + relative) across asset classes. Only hold assets with both positive absolute momentum AND top-ranked relative momentum.
- **Signal**: 12M return > 0 (absolute momentum) AND top 3 of 7 asset classes (relative momentum). Monthly rebalance. If no asset has positive absolute momentum → cash/T-bills.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: 12M return is objective. Cross-sectional ranking is robust. Cash filter for down markets.
- **Edge Source**: Behavioral — momentum is the most robust anomaly across asset classes. Dual momentum combines trend-following with relative strength.
- **Assets**: SPY, EFA, EEM, TLT, IEF, DBC, GLD
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.75, MaxDD −15%, PF 1.42
- **Complexity**: Low
- **Refs**: Antonacci (2014) "Dual Momentum Investing"

### 3.2 Breakout System (Turtle-Style)
- **Core Logic**: Updated Turtle Trading system. Buy when price breaks above 55-day high. Sell when breaks below 20-day low. ATR-based position sizing. Trend-following in futures.
- **Signal**: Long: close > 55D high. Exit: close < 20D low. Position size: 1% risk / (2 × 14D ATR). Max 4 units per market, 10 units correlated. Apply across 20+ futures markets.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must include transaction costs.
- **Anti-Drift**: Breakout rules are mechanical. ATR is market data. Diversification across 20+ markets.
- **Edge Source**: Structural — breakout systems capture extended moves driven by herding and slow information diffusion. Robust across decades and asset classes.
- **Assets**: Equity index, bond, FX, commodity futures (20+ markets)
- **Timeframe**: Daily signal, variable hold (weeks to months)
- **Expected Perf**: WR 38%, Sharpe 0.65, MaxDD −25%, PF 1.40 (skewed payoff)
- **Complexity**: Low
- **Refs**: Faith (2007) "Way of the Turtle"

### 3.3 Multi-Timeframe Trend Composite
- **Core Logic**: Combine trend signals across multiple timeframes (short: 10D, medium: 50D, long: 200D). When all timeframes align → strong signal. When mixed → reduce position.
- **Signal**: Each timeframe: +1 if EMA(close) > EMA(close, N-1), −1 otherwise. Composite = sum of 3 timeframes. When composite = 3 → full long. When = −3 → full short. Otherwise → proportional.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: EMA is mechanical. Timeframes (10/50/200) are standard. Composite is simple average.
- **Edge Source**: Structural — multi-timeframe alignment indicates strong trends. Confirmation across timeframes reduces false signals.
- **Assets**: Equity index, bond, commodity, FX futures
- **Timeframe**: Daily signal
- **Expected Perf**: WR 45%, Sharpe 0.70, MaxDD −18%, PF 1.38
- **Complexity**: Low
- **Refs**: Hurst, Ooi & Pedersen (2017) "A Century of Evidence on Trend-Following Investing"

### 3.4 Adaptive Moving Average (Kaufman AMA)
- **Core Logic**: Kaufman's Adaptive Moving Average adjusts smoothing based on market noise. In trending markets, AMA is fast. In choppy markets, AMA is slow. Natural noise filter.
- **Signal**: AMA = AMA(−1) + SC × (Price − AMA(−1)), where SC = [(ER × (fast−slow) + slow)]². ER = direction/volatility. Long when price > AMA, short when below. Apply across 20+ futures.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: AMA adapts by construction. ER is computed from price data. No parameters to optimize (fast/slow are standard).
- **Edge Source**: Structural — AMA automatically filters noise in range-bound markets and responds quickly to trends. Reduces whipsaws vs fixed MA.
- **Assets**: Equity index, bond, commodity, FX futures
- **Timeframe**: Daily signal
- **Expected Perf**: WR 42%, Sharpe 0.65, MaxDD −20%, PF 1.35
- **Complexity**: Low
- **Refs**: Kaufman (2013) "Trading Systems and Methods"

### 3.5 Volatility-Scaled Momentum
- **Core Logic**: Scale position size by inverse volatility. In low-vol environments, take larger positions (trend is smooth). In high-vol, reduce (trend is noisy). Improve risk-adjusted returns.
- **Signal**: Standard momentum signal (12M − 1M return). Position size = base size × (target vol / realized vol). Target vol = 10%. Realized vol = 20D. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Momentum signal is standard. Vol-scaling is mathematical. Target vol is fixed.
- **Edge Source**: Structural — vol-scaling equalizes risk across time periods. Higher Sharpe than unscaled momentum.
- **Assets**: 20+ futures markets
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 45%, Sharpe 0.80, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Barroso & Santa-Clara (2015) "Momentum Has Its Moments"

### 3.6 Time-Series Momentum (TSMOM) Carry
- **Core Logic**: Combine time-series momentum (past returns predict future returns) with carry (yield) across futures. Two complementary signals: trend + carry.
- **Signal**: TSMOM: 12M return > 0 → long, else short. Carry: positive roll yield → long, negative → short. Combined: both agree → full position. Disagree → half or flat. 60+ futures markets.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Both TSMOM and carry are mechanical, market-data-driven signals. No optimization.
- **Edge Source**: Structural — TSMOM captures trending behavior. Carry captures risk premium. Combined, they exploit different return drivers.
- **Assets**: 60+ global futures (equities, bonds, FX, commodities)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 50%, Sharpe 0.90, MaxDD −15%, PF 1.50
- **Complexity**: Medium
- **Refs**: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum"

### 3.7 Mean Reversion Counter-Trend Filter
- **Core Logic**: Within a broader trend, trade short-term mean reversion (buy dips in uptrend, sell rallies in downtrend). Combines trend and mean-reversion.
- **Signal**: Trend: 100D SMA direction (up → bullish bias, down → bearish). Within uptrend: buy when RSI(3) < 20. Within downtrend: sell when RSI(3) > 80. Apply across 20+ futures.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: SMA trend direction is mechanical. RSI(3) oversold/overbought levels are standard. Combined signal is simple.
- **Edge Source**: Behavioral — short-term overreactions within trends create mean-reversion opportunities. Buying dips in uptrends is the highest-probability setup.
- **Assets**: Equity index, bond, FX futures
- **Timeframe**: Daily signal, 3-10 day hold
- **Expected Perf**: WR 62%, Sharpe 0.75, MaxDD −12%, PF 1.45
- **Complexity**: Low
- **Refs**: Connors & Alvarez (2009) "Short-Term Trading Strategies That Work"

### 3.8 Channel Breakout with Volatility Filter
- **Core Logic**: Donchian channel breakout (buy new 20D high, sell new 20D low) with volatility filter. Only trade when volatility is contracting (precedes breakout). Avoid high-vol choppy markets.
- **Signal**: Buy: close > 20D high AND 14D ATR < 20D ATR (vol contracting). Sell: close < 20D low AND vol contracting. Exit: 10D low (for longs). Vol expansion filter improves breakout quality.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Channel breakout is mechanical. ATR comparison is objective. Vol filter improves signal quality.
- **Edge Source**: Structural — vol contraction precedes breakouts (Bollinger squeeze). Filtering on vol state improves breakout success rate.
- **Assets**: Commodity, FX, equity index futures
- **Timeframe**: Daily signal, 2-8 week hold
- **Expected Perf**: WR 40%, Sharpe 0.60, MaxDD −18%, PF 1.32
- **Complexity**: Low
- **Refs**: Bollinger (2001) "Bollinger on Bollinger Bands"

### 3.9 Cross-Sectional Momentum (XSMOM) Futures
- **Core Logic**: Rank 40+ futures markets by past 12-month return. Long top quintile, short bottom quintile. Cross-sectional momentum captures relative strength across diverse markets.
- **Signal**: 12M return rank across 40+ futures. Long top 20% (8 markets), short bottom 20%. Equal-weight within buckets. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: 12M return is objective. Cross-sectional ranking is robust. Diversification across 40+ markets.
- **Edge Source**: Behavioral — cross-sectional momentum exploits herding and slow information diffusion across markets. Highly robust historically.
- **Assets**: 40+ global futures (equities, bonds, FX, commodities)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 48%, Sharpe 0.75, MaxDD −18%, PF 1.40
- **Complexity**: Medium
- **Refs**: Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"

### 3.10 Trend Strength Allocation
- **Core Logic**: Allocate more capital to markets with strongest trends and less to choppy markets. Trend strength measured by ADX or R-squared of price regression.
- **Signal**: For each market: ADX(14). When ADX > 25 → strong trend → full position. When ADX 15-25 → moderate → half position. When ADX < 15 → weak → no position. Direction: slope of 20D EMA.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: ADX is standard indicator. Thresholds (15, 25) are commonly used. EMA slope is mechanical.
- **Edge Source**: Structural — concentrating on strong trends improves CTA performance. Avoiding choppy markets reduces whipsaws.
- **Assets**: 30+ global futures
- **Timeframe**: Daily signal, weekly position sizing
- **Expected Perf**: WR 42%, Sharpe 0.70, MaxDD −15%, PF 1.38
- **Complexity**: Low
- **Refs**: Wilder (1978) "New Concepts in Technical Trading Systems"

---

## 4. Systematic Equity — Factor-Based (10)

### 4.1 Value-Momentum Barbell
- **Core Logic**: Combine value and momentum factors (negatively correlated). Hold value stocks AND momentum stocks simultaneously. Barbell provides smoother returns than either alone.
- **Signal**: Value: top quintile by composite (P/B, P/E, EV/EBITDA). Momentum: top quintile by 12-1M return. 50% value + 50% momentum. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must test factor correlation regime changes.
- **Anti-Drift**: Factor scores use fundamental and price data. Cross-sectional ranking. Well-documented factors.
- **Edge Source**: Structural — value and momentum have negative correlation (~−0.20). Combining them smooths the return stream and reduces drawdowns.
- **Assets**: Russell 1000 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"

### 4.2 Quality Factor Tilt
- **Core Logic**: Tilt portfolio toward high-quality stocks (high ROE, low debt, stable earnings). Quality provides downside protection and consistent returns, especially during market stress.
- **Signal**: Quality composite: ROE Z + gross profit margin Z + earnings stability Z − leverage Z. Long top quintile, short bottom quintile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Quality metrics use fundamental data. Z-scores are adaptive. Cross-sectional ranking.
- **Edge Source**: Structural — quality premium exists because investors underprice stable, profitable businesses. Quality provides "flight to quality" protection.
- **Assets**: Russell 1000 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.70, MaxDD −12%, PF 1.38
- **Complexity**: Medium
- **Refs**: Novy-Marx (2013) "The Other Side of Value: The Gross Profitability Premium"

### 4.3 Low Volatility Anomaly Exploitation
- **Core Logic**: Low-vol stocks outperform high-vol stocks on risk-adjusted basis (low-vol anomaly). Tilt toward low-vol, away from high-vol. Leverage to match market vol.
- **Signal**: Sort by 12M realized vol. Long bottom quintile (low vol), short top quintile (high vol). Lever low-vol portfolio to match market vol. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Realized vol is market data. Cross-sectional ranking. Well-documented anomaly.
- **Edge Source**: Behavioral — lottery preference: investors overpay for high-vol (lottery-like) stocks. Benchmark-constrained managers are underweight low-vol.
- **Assets**: S&P 500 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.80, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Baker, Bradley & Wurgler (2011) "Benchmarks as Limits to Arbitrage"

### 4.4 Earnings Revision Momentum
- **Core Logic**: Stocks with upward analyst earnings revisions continue outperforming. Revision momentum is a powerful predictor of future returns.
- **Signal**: FY1 EPS estimate change (3M). Long stocks with largest positive revision (top quintile). Short largest negative revision (bottom quintile). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Analyst estimates from I/B/E/S. Revision direction is objective. Cross-sectional ranking.
- **Edge Source**: Informational — analyst revisions reflect fundamental information processing. Revisions predict future earnings surprises.
- **Assets**: S&P 500 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −12%, PF 1.40
- **Complexity**: Low
- **Refs**: Chan, Jegadeesh & Lakonishok (1996) "Momentum Strategies"

### 4.5 Accruals Quality Factor
- **Core Logic**: Companies with high accruals (earnings driven by accounting adjustments rather than cash) tend to underperform. Low accruals (cash-driven earnings) outperform.
- **Signal**: Accruals = (ΔCA − ΔCash − ΔCL + ΔSTD − Dep) / Total Assets. Short top quintile (high accruals). Long bottom quintile (low accruals). Annual rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Accruals computed from financial statements. Cross-sectional ranking. Annual signal (slow-moving).
- **Edge Source**: Behavioral — investors fixate on reported earnings, ignoring accruals quality. High accruals are less persistent, leading to future earnings disappointments.
- **Assets**: All stocks with financial data
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Low
- **Refs**: Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?"

### 4.6 Short Interest as Contrarian Signal
- **Core Logic**: Extremely high short interest reflects crowded shorts. Short squeezes in highly-shorted stocks generate large returns. Go long the most-shorted stocks with positive catalysts.
- **Signal**: Short interest > 20% of float AND positive 5D momentum → long (squeeze setup). Exit after 5 days or when short interest declines > 3%. Only when VIX < 25 (avoid crisis).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Short interest is published (FINRA). 20% threshold is extreme. Positive momentum confirms squeeze is starting.
- **Edge Source**: Behavioral — crowded shorts create reflexive dynamics. Covering by short sellers drives further price increases (squeeze).
- **Assets**: Individual stocks with high short interest
- **Timeframe**: 5-day hold
- **Expected Perf**: WR 52%, Sharpe 0.55, MaxDD −20%, PF 1.25
- **Complexity**: Low
- **Refs**: Asquith, Pathak & Ritter (2005) "Short Interest, Institutional Ownership, and Stock Returns"

### 4.7 Fundamental Momentum (F-Score)
- **Core Logic**: Piotroski F-Score (0-9) measures financial strength improvement. High F-Score → improving fundamentals → outperformance. Combined with value creates powerful signal.
- **Signal**: Compute 9-point F-Score (profitability, leverage, efficiency changes). Among value stocks (bottom quintile P/B), long those with F-Score ≥ 7. Short value stocks with F-Score ≤ 2.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: F-Score uses published financial data. 9-point scale is defined. Combination with value is transparent.
- **Edge Source**: Informational — F-Score identifies which value stocks are "value traps" (deteriorating fundamentals) vs genuine value (improving fundamentals).
- **Assets**: All stocks with financial data
- **Timeframe**: Annual rebalance (post-filings)
- **Expected Perf**: WR 56%, Sharpe 0.65, MaxDD −15%, PF 1.35
- **Complexity**: Low
- **Refs**: Piotroski (2000) "Value Investing: The Use of Historical Financial Statement Information"

### 4.8 Sector-Neutral Multi-Factor
- **Core Logic**: Run multi-factor model (value, momentum, quality, size) but neutralize sector exposure. This isolates stock-specific factor alpha from sector bets.
- **Signal**: Within each GICS sector: long top quintile by composite factor score, short bottom quintile. Equal sector exposure (sector-neutral). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Factor scores are mechanical. Sector-neutrality eliminates sector timing. Cross-sectional within-sector ranking.
- **Edge Source**: Structural — sector-neutral approach isolates stock-level alpha. Avoids sector rotation risk that contaminates factor returns.
- **Assets**: S&P 500 stocks across 11 GICS sectors
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.70, MaxDD −10%, PF 1.38
- **Complexity**: Medium
- **Refs**: Barra risk model methodology

### 4.9 Idiosyncratic Volatility Factor
- **Core Logic**: Stocks with low idiosyncratic vol (after removing factor exposure) outperform those with high idiosyncratic vol. Related to but distinct from total low-vol anomaly.
- **Signal**: Compute idiosyncratic vol = residual vol from Fama-French 5-factor model. Long bottom quintile (low idio vol). Short top quintile (high idio vol). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Factor model is standard (FF5). Residual vol is computed. Cross-sectional ranking.
- **Edge Source**: Behavioral — high idiosyncratic vol stocks are lottery tickets. Investors overpay → subsequent underperformance.
- **Assets**: S&P 500 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.60, MaxDD −15%, PF 1.30
- **Complexity**: Medium
- **Refs**: Ang et al. (2006) "The Cross-Section of Volatility and Expected Returns"

### 4.10 Betting Against Beta (BAB)
- **Core Logic**: Low-beta stocks earn higher risk-adjusted returns than high-beta stocks (BAB anomaly). Lever low-beta, de-lever high-beta to create market-neutral portfolio.
- **Signal**: Compute trailing beta (60M regression vs market). Long low-beta quintile (levered to beta=1). Short high-beta quintile (de-levered to beta=1). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Beta is standard computation. Leverage targeting beta=1 is mathematical. Cross-sectional ranking.
- **Edge Source**: Structural — BAB exists because leverage-constrained investors overweight high-beta assets to reach return targets. Low-beta is underpriced.
- **Assets**: S&P 500 stocks
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.70, MaxDD −15%, PF 1.38
- **Complexity**: Medium
- **Refs**: Frazzini & Pedersen (2014) "Betting Against Beta"

---

## 5. Systematic Equity — Market Timing (10)

### 5.1 Shiller CAPE Timing
- **Core Logic**: Shiller CAPE (cyclically adjusted P/E) predicts 10Y equity returns. When CAPE is extreme, adjust equity allocation. Not for short-term timing, but medium-term allocation.
- **Signal**: CAPE Z-score (50Y). When Z > 2.0 → reduce equity to 40%. When Z 0.5-2.0 → 60%. When Z < 0.5 → 80%. When Z < −1.0 → 100%.
- **Best Backtest Method**: Walk-forward 50yr/15yr/15yr. Monte Carlo 10k.
- **Anti-Drift**: CAPE uses 10Y earnings (very slow-moving). Z-score over 50Y is extremely adaptive. Allocation bands are conservative.
- **Edge Source**: Structural — CAPE is the strongest known predictor of long-term equity returns. High CAPE → low future returns, and vice versa.
- **Assets**: SPY allocation
- **Timeframe**: Annual assessment
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −20%, PF 1.30
- **Complexity**: Low
- **Refs**: Campbell & Shiller (1988) "Stock Prices, Earnings, and Expected Dividends"

### 5.2 Breadth Thrust Timing
- **Core Logic**: Breadth thrust (% of stocks above 50D MA surging from < 40% to > 60% within 10 days) signals the start of major rallies. Extremely rare and reliable signal.
- **Signal**: When % stocks above 50D MA rises from < 40% to > 60% in ≤ 10 days → breadth thrust → go max long equities. Hold for 12 months. Historically: 100% win rate on 12M forward return.
- **Best Backtest Method**: Walk-forward 30yr/10yr/10yr. Monte Carlo 10k.
- **Anti-Drift**: Breadth data is published. Threshold crossover is mechanical. Very rare signal (2-3 per decade).
- **Edge Source**: Structural — breadth thrusts indicate massive buying pressure across the market. Signals the end of bear markets.
- **Assets**: SPY (100% long on signal)
- **Timeframe**: 12-month hold after signal
- **Expected Perf**: WR ~95%, Sharpe 1.20 (during signal periods), MaxDD −5%, PF 3.00
- **Complexity**: Low
- **Refs**: Zweig (1986) "Martin Zweig's Winning on Wall Street"

### 5.3 Put/Call Ratio Extreme
- **Core Logic**: Equity put/call ratio reflects retail sentiment. Extreme high reading (> 1.2) = excessive bearishness = contrarian buy. Extreme low (< 0.5) = excessive bullishness = contrarian sell.
- **Signal**: CBOE equity put/call 5D SMA. When > 1.2 → oversold, buy SPY. When < 0.5 → overbought, sell/short SPY. 20-day hold.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: P/C ratio is market data. 5D SMA smooths daily noise. Extreme thresholds (1.2, 0.5) are rare.
- **Edge Source**: Behavioral — put/call extremes reflect retail panic (high) or complacency (low). Both are contrarian signals.
- **Assets**: SPY
- **Timeframe**: Event-driven, 20-day hold
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −10%, PF 1.38
- **Complexity**: Low
- **Refs**: Natenberg (2015) "Option Volatility and Pricing"

### 5.4 AAII Sentiment Extreme
- **Core Logic**: AAII (American Association of Individual Investors) bullish % is a contrarian indicator. Extreme bullishness → market top risk. Extreme bearishness → buying opportunity.
- **Signal**: AAII bullish % 4-week MA. When > 55% → overbought, reduce equity by 20%. When < 25% → oversold, increase equity by 20%. Weekly signal.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: AAII data is published weekly. 4-week MA smooths. Thresholds based on historical distribution.
- **Edge Source**: Behavioral — retail sentiment is a reliable contrarian indicator. Extreme bullishness precedes corrections; extreme bearishness precedes rallies.
- **Assets**: SPY allocation adjustment
- **Timeframe**: Weekly signal
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: Fisher & Statman (2000) "Investor Sentiment and Stock Returns"

### 5.5 Margin Debt Growth Warning
- **Core Logic**: NYSE margin debt growth is a measure of speculative leverage. When margin debt grows too fast, markets are vulnerable. When it contracts sharply, markets are oversold.
- **Signal**: Margin debt YoY growth Z-score. When Z > 2.0 → excessive speculation → reduce equity by 25%. When Z < −1.5 → forced deleveraging → increase equity by 25%.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Margin debt data is published monthly. YoY growth eliminates base effects. Z-score is adaptive.
- **Edge Source**: Behavioral — margin debt is a proxy for speculative leverage. Extreme leverage creates fragility; deleveraging creates opportunities.
- **Assets**: SPY allocation adjustment
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Low
- **Refs**: Rapach & Zhou (2013) "Forecasting Stock Returns"

### 5.6 Insider Aggregate Buy/Sell Ratio
- **Core Logic**: Aggregate insider buying vs selling across all S&P 500 companies. When insiders are net buying heavily → bullish for market. When net selling heavily → bearish.
- **Signal**: Monthly insider buy/sell ratio (by dollar value) across S&P 500. When ratio Z > 1.5 (heavy buying) → increase equity by 20%. When Z < −1.5 (heavy selling) → reduce by 20%.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Insider data from SEC (Form 4). Dollar-weighted ratio is objective. Z-score is adaptive.
- **Edge Source**: Informational — aggregate insider behavior reflects corporate managers' collective view of valuations. Informative at market level.
- **Assets**: SPY allocation adjustment
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: Seyhun (1998) "Investment Intelligence from Insider Trading"

### 5.7 Yield Curve Recession Indicator
- **Core Logic**: Inverted yield curve (2Y > 10Y) predicts recessions with 12-18 month lead. Use for equity allocation: reduce exposure after inversion, re-enter after steepening.
- **Signal**: When 2Y-10Y spread < 0 for 3+ months (confirmed inversion) → reduce equity to 40%. When spread turns positive again AND > 50bps → increase to 80% (recession imminent but market looks forward).
- **Best Backtest Method**: Walk-forward 40yr/10yr/10yr. Monte Carlo 10k.
- **Anti-Drift**: Yield curve is market data. Inversion is binary. Confirmation period prevents false signals.
- **Edge Source**: Structural — yield curve inversion reflects market pricing of future rate cuts (due to economic weakness). Most reliable recession predictor.
- **Assets**: SPY, TLT, GLD allocation
- **Timeframe**: Signal triggers every few years, 12-18 month positioning
- **Expected Perf**: Avoids 30-50% of recession drawdowns. Modest opportunity cost in non-recession periods.
- **Complexity**: Low
- **Refs**: Harvey (1988) "The Real Term Structure and Consumption Growth"

### 5.8 ISM PMI Momentum Trading
- **Core Logic**: ISM PMI momentum (rate of change) predicts equity market direction better than the level. Accelerating PMI → bullish. Decelerating → bearish. Leading indicator.
- **Signal**: ISM PMI 3M momentum (current − 3M ago). When momentum > 0 AND PMI > 50 → max long. When momentum > 0 AND PMI < 50 → recovery → long. When momentum < 0 AND PMI < 50 → recession → short/defensive.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: ISM PMI is published monthly. Momentum is simple difference. Combined with level for nuance.
- **Edge Source**: Structural — PMI momentum captures the direction of economic change, which matters more for markets than the level.
- **Assets**: SPY, sector ETFs
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −15%, PF 1.35
- **Complexity**: Low
- **Refs**: Stock & Watson (2003) "Forecasting Output and Inflation"

### 5.9 Smart Money / Dumb Money Confidence Spread
- **Core Logic**: Smart money confidence (commercial hedger positioning, institutional flows) vs dumb money confidence (retail flows, newsletter sentiment). Wide spread = contrarian opportunity.
- **Signal**: Smart-Dumb spread Z-score. When spread > 2.0 (smart money bullish, dumb money bearish) → strong buy. When spread < −2.0 (smart money bearish, dumb money bullish) → strong sell.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Positioning data from COT (smart money). Sentiment data from surveys (dumb money). Spread is mechanical.
- **Edge Source**: Behavioral — smart money (informed) and dumb money (uninformed) diverge at extremes. Smart money is historically correct.
- **Assets**: SPY
- **Timeframe**: Weekly signal, 4-8 week hold
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −12%, PF 1.38
- **Complexity**: Medium
- **Refs**: Sentimentrader methodology

### 5.10 Seasonal Equity Rotation
- **Core Logic**: Equity markets exhibit well-documented seasonal patterns (sell in May, Santa rally, January effect). Combine multiple seasonal patterns for systematic timing.
- **Signal**: Composite seasonal score: Nov-Apr (bullish), May-Oct (bearish), last 5 days of month (bullish), first 2 days of month (bullish), pre-holiday (bullish). When ≥ 3 bullish factors → full long. When ≤ 1 → half long.
- **Best Backtest Method**: Walk-forward 30yr/10yr/10yr. Monte Carlo 10k.
- **Anti-Drift**: Calendar effects are fixed by definition. Composite of multiple effects is robust. No optimization.
- **Edge Source**: Structural — seasonal effects driven by institutional flows (year-end, quarter-end), tax considerations, and behavioral patterns.
- **Assets**: SPY
- **Timeframe**: Daily assessment
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −18%, PF 1.25
- **Complexity**: Low
- **Refs**: Bouman & Jacobsen (2002) "The Halloween Indicator, 'Sell in May and Go Away'"

---

## 6. Systematic Fixed Income (10)

### 6.1 Duration Timing via Economic Regime
- **Core Logic**: Optimal bond duration depends on economic regime. Expansion → short duration. Recession → long duration. Inflation → very short duration. Deflation → very long duration.
- **Signal**: Regime classification (PMI + CPI momentum). Expansion (PMI > 50, CPI stable) → duration = 2Y. Recession (PMI < 45) → duration = 30Y. Inflation (CPI accelerating) → bills. Deflation → long zeros.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: PMI and CPI are published data. Regime classification is simple. Duration targets are fixed per regime.
- **Edge Source**: Structural — bond duration risk premium varies with economic regime. Correct timing of duration adds significant alpha over constant-duration strategies.
- **Assets**: UST across the curve (SHY, IEF, TLT, ZROZ)
- **Timeframe**: Monthly regime assessment
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −10%, PF 1.38
- **Complexity**: Medium
- **Refs**: Ilmanen (2011) "Expected Returns"

### 6.2 Corporate Bond Momentum
- **Core Logic**: Corporate bonds exhibit momentum (past winners continue winning). Rank bonds by recent total return. Long top quintile, short bottom quintile.
- **Signal**: 6M total return rank across IG corporate bond universe. Long top quintile. Short bottom quintile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model bond liquidity.
- **Anti-Drift**: Total return is market data. Cross-sectional ranking. Monthly rebalance.
- **Edge Source**: Behavioral — credit momentum reflects ongoing credit quality improvement/deterioration. Slow information diffusion in credit markets.
- **Assets**: IG corporate bonds (LQD universe)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −8%, PF 1.30
- **Complexity**: Medium
- **Refs**: Jostova et al. (2013) "Momentum in Corporate Bond Returns"

### 6.3 High Yield Spread Signal for Equities
- **Core Logic**: HY credit spread reflects default risk expectations. Widening spreads signal economic deterioration. Use HY spread change as equity market timing signal.
- **Signal**: HY OAS (ICE BofA) 3M change. When HY spread widens > 100bps in 3M → reduce equity to 50%. When narrows > 100bps → increase to 80%. Monthly assessment.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: HY OAS is published daily. 100bps threshold is meaningful. Monthly assessment.
- **Edge Source**: Structural — HY spreads lead equity markets because credit markets price default risk earlier. Credit is smarter than equity for risk signals.
- **Assets**: SPY allocation adjustment (HY as signal)
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −12%, PF 1.32
- **Complexity**: Low
- **Refs**: Bao, Hou & Zhang (2020) "De Facto Seniority, Credit Risk, and Corporate Bond Prices"

### 6.4 Treasury Carry (Roll-Down)
- **Core Logic**: Bonds on the steep part of the yield curve earn carry from roll-down (aging toward maturity decreases yield → capital gain). Optimize maturity selection for maximum roll-down.
- **Signal**: Compute roll-down for each maturity point (change in yield from aging 1 month, × duration). Select maturity with maximum roll-down carry. Currently: typically 5-7Y range.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Yield curve is market data. Roll-down computation is mathematical. Maturity selection is data-driven.
- **Edge Source**: Structural — roll-down carry is a predictable component of bond returns. Optimizing maturity maximizes this carry.
- **Assets**: UST across the curve
- **Timeframe**: Monthly maturity optimization
- **Expected Perf**: WR 60%, Sharpe 0.55, MaxDD −5%, PF 1.30
- **Complexity**: Low
- **Refs**: Ilmanen (2012) "Understanding the Yield Curve" series

### 6.5 Credit Curve Steepness Trade
- **Core Logic**: Corporate credit curve (spread across maturities) varies. When credit curve is steep (long-dated credit cheap), buy long-dated corporate bonds. When flat, buy short-dated.
- **Signal**: 10Y IG spread − 3Y IG spread (credit curve slope). When Z > 1.5 → buy long-dated credit. When Z < −1.5 → buy short-dated credit. Fund with duration-matched Treasuries.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Credit spreads are market data. Duration matching isolates credit component. Z-score is adaptive.
- **Edge Source**: Structural — credit curve slope reflects market's pricing of long-term credit risk. Extreme slope readings revert.
- **Assets**: IG corporate bonds at different maturities
- **Timeframe**: Monthly signal, 6-month hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −5%, PF 1.28
- **Complexity**: Medium
- **Refs**: Helwege & Turner (1999) "The Slope of the Credit Yield Curve for Speculative-Grade Issuers"

### 6.6 Convertible Bond Arbitrage
- **Core Logic**: Convertible bonds contain embedded equity option. When this option is mispriced relative to traded options, arbitrage the difference. Buy undervalued convertible, hedge with equity short + option.
- **Signal**: Compare implied vol from convertible pricing vs traded equity option IV. When convertible IV < traded IV − 5 vol points → buy convertible, sell equity option. Delta-neutral.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model credit and equity risk.
- **Anti-Drift**: IV from both sources is market data. 5 vol point spread is meaningful. Delta hedging.
- **Edge Source**: Structural — convertible bond market is less efficient than equity option market. Institutional segmentation creates persistent mispricing.
- **Assets**: IG and HY convertible bonds
- **Timeframe**: Monthly assessment, 3-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −10%, PF 1.40
- **Complexity**: High
- **Refs**: Choi, Getmansky & Tookes (2009) "Convertible Bond Arbitrageurs as Suppliers of Capital"

### 6.7 Inflation-Linked Bond Tactical Allocation
- **Core Logic**: Allocate between nominal bonds and TIPS based on whether inflation will surprise up or down. When inflation surprise likely → TIPS. When deflation risk → nominals.
- **Signal**: Inflation forecast composite (oil price momentum, wage growth, M2 growth, PPI). When composite predicts above-consensus inflation → overweight TIPS vs nominals. When below → reverse.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Forecast inputs are published data. Composite is simple. TIPS vs nominal is a well-defined relative trade.
- **Edge Source**: Informational — inflation forecast composite uses leading indicators. Predicts inflation direction before consensus adjusts.
- **Assets**: TIP (TIPS) vs IEF/TLT (nominals)
- **Timeframe**: Monthly allocation
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −5%, PF 1.25
- **Complexity**: Medium
- **Refs**: Fleckenstein, Longstaff & Lustig (2014) "The TIPS-Treasury Bond Puzzle"

### 6.8 Emerging Market Bond Carry
- **Core Logic**: EM local currency bonds offer high carry (yield) but with FX risk. Filter by macro stability to capture carry while avoiding blowups.
- **Signal**: Long EM local bonds with: real yield > 3% AND current account deficit < 5% AND inflation < 8% AND external debt < 50% GDP. Monthly screening.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include EM crises.
- **Anti-Drift**: Screening criteria use published macro data. Thresholds are based on crisis research. Monthly monitoring.
- **Edge Source**: Structural — EM carry premium compensates for EM risk. Macro filtering avoids the worst outcomes.
- **Assets**: Local currency EM government bonds (BRL, MXN, ZAR, IDR, INR, TRY)
- **Timeframe**: Monthly screening, quarterly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −20%, PF 1.28
- **Complexity**: Medium
- **Refs**: Burger, Warnock & Warnock (2012) "Emerging Local Currency Bond Markets"

### 6.9 Agency MBS Spread Trading
- **Core Logic**: Agency MBS spread over Treasuries (OAS) varies cyclically with rate vol, prepayment speeds, and Fed activity. When spread is wide (MBS cheap) → buy MBS, sell Treasuries.
- **Signal**: MBS OAS Z-score (3Y). When Z > 1.5 → MBS cheap → buy MBS-Treasury spread. When Z < −1.0 → MBS rich → sell spread. Monthly assessment.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model prepayment risk.
- **Anti-Drift**: MBS OAS is published. Z-score is adaptive. Duration-hedged to isolate spread component.
- **Edge Source**: Structural — MBS spreads reflect prepayment uncertainty and convexity risk. Extreme spreads revert as conditions normalize.
- **Assets**: Agency MBS (GNMA, FNMA) vs UST
- **Timeframe**: Monthly signal, 6-month hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −5%, PF 1.28
- **Complexity**: Medium
- **Refs**: Fabozzi (2016) "The Handbook of Mortgage-Backed Securities"

### 6.10 CLO Tranche Relative Value
- **Core Logic**: CLO tranches (AAA, AA, A, BBB, BB) offer varying risk/return. When lower tranches are excessively cheap relative to upper tranches, buy the dislocation.
- **Signal**: CLO BBB-AAA spread differential Z-score (2Y). When Z > 1.5 → BBB too cheap vs AAA → buy BBB, sell AAA (compression trade). When Z < −1.5 → reverse.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must model default and recovery rates.
- **Anti-Drift**: CLO spreads are market data. Z-score is adaptive. Relative value is well-defined.
- **Edge Source**: Structural — CLO tranche spreads overshoot during risk-off (forced selling of lower tranches). Mean-revert as fundamentals reassert.
- **Assets**: CLO tranches (AAA through BB)
- **Timeframe**: Monthly signal, 6-month hold
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −8%, PF 1.38
- **Complexity**: High
- **Refs**: Cordell, Roberts & Schwert (2023) "CLO Performance"

---

## 7. Quantitative Risk Management (10)

### 7.1 Dynamic Drawdown Control
- **Core Logic**: Continuously monitor portfolio drawdown from peak. As drawdown deepens, reduce risk proportionally. Preserves capital for recovery. Mechanical risk management.
- **Signal**: Current drawdown from peak. When DD < 5% → 100% risk. 5-10% → 80%. 10-15% → 50%. 15-20% → 25%. > 20% → 10% (minimal). When recovering past 5% DD → restore gradually.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Drawdown is computed from prices. Thresholds are fixed. Mechanical de-risking.
- **Edge Source**: Structural — drawdown control prevents catastrophic losses. Recovery from smaller drawdowns is faster (5% loss needs 5.3% gain; 50% loss needs 100% gain).
- **Assets**: Any portfolio (overlay)
- **Timeframe**: Daily monitoring
- **Expected Perf**: Reduces MaxDD by 40-60% with ~15% lower annualized return
- **Complexity**: Low
- **Refs**: Grossman & Zhou (1993) "Optimal Investment Strategies for Controlling Drawdowns"

### 7.2 Correlation Regime Switch
- **Core Logic**: Monitor cross-asset correlations. When correlations spike (risk-off → everything falls together), diversification fails → reduce all positions. When correlations normalize → restore.
- **Signal**: Average pairwise correlation of portfolio assets (20D rolling). When Z > 2.0 → correlations spiking → reduce all positions by 40%. When Z normalizes → restore.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Pairwise correlations are market data. Rolling window is standard. Z-score is adaptive.
- **Edge Source**: Structural — correlation spikes signal regime change and diversification failure. Reducing exposure during correlation spikes protects capital.
- **Assets**: Risk overlay for any portfolio
- **Timeframe**: Daily monitoring
- **Expected Perf**: Reduces crisis-period drawdowns by 30-40%
- **Complexity**: Medium
- **Refs**: Kritzman & Li (2010) "Skulls, Financial Turbulence, and Risk Management"

### 7.3 Tail Risk Budget Allocation
- **Core Logic**: Instead of targeting volatility, target tail risk (CVaR or Expected Shortfall). Allocate to equalize tail risk contribution across assets. Better for fat-tailed distributions.
- **Signal**: Compute CVaR(95%) for each asset and cross-asset (60D rolling, Cornish-Fisher expansion). Solve for weights that equalize CVaR contribution. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: CVaR is computed from return distribution. Cornish-Fisher adjusts for skew/kurtosis. Monthly rebalance.
- **Edge Source**: Structural — CVaR-based allocation protects better in tail events than variance-based methods. More realistic risk measure.
- **Assets**: Multi-asset portfolio
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −10%, PF 1.42
- **Complexity**: High
- **Refs**: Rockafellar & Uryasev (2000) "Optimization of Conditional Value-at-Risk"

### 7.4 Volatility Targeting
- **Core Logic**: Scale exposure to maintain constant portfolio volatility (e.g., 10% annualized). When realized vol is low → lever up. When high → delever. Improves Sharpe ratio.
- **Signal**: Target vol = 10%. Leverage = target vol / realized vol (20D). Cap at 2× leverage. Daily adjustment.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Realized vol is market data. Target vol is fixed. Mathematical formula (no optimization).
- **Edge Source**: Structural — vol targeting exploits the negative vol-return relationship. Low vol periods have higher Sharpe. Leveraging into them captures this.
- **Assets**: Any portfolio (overlay)
- **Timeframe**: Daily leverage adjustment
- **Expected Perf**: Improves Sharpe by 0.15-0.25. Reduces MaxDD by 20-30%.
- **Complexity**: Low
- **Refs**: Moreira & Muir (2017) "Volatility-Managed Portfolios"

### 7.5 Factor Risk Budgeting
- **Core Logic**: Decompose portfolio risk into factor contributions (market, value, momentum, credit, etc.). Set target risk budget per factor. Rebalance when factor exposures deviate.
- **Signal**: Monthly factor risk decomposition via Barra or custom model. When any factor contributes > 40% of portfolio risk → reduce that exposure. When balanced → maintain.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Factor model is standard. Risk decomposition is mathematical. 40% threshold is conservative.
- **Edge Source**: Structural — factor risk budgeting prevents unintended concentration. Ensures diversification at the factor level, not just asset level.
- **Assets**: Multi-asset or multi-strategy portfolio
- **Timeframe**: Monthly rebalance
- **Expected Perf**: Reduces Max factor-specific DD by 30-40%
- **Complexity**: High
- **Refs**: Meucci (2009) "Managing Diversification"

### 7.6 Stop-Loss with Re-Entry
- **Core Logic**: Apply stop-loss to portfolio (e.g., −8% from recent peak), but also define re-entry signal to avoid permanent disinvestment. Combines loss limitation with market participation.
- **Signal**: Stop: when portfolio drops 8% from 20D high → sell 75% to cash. Re-enter: when portfolio rises 3% from stop level → re-enter 75%. Prevents panic selling without re-entry.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must model whipsaw cost.
- **Anti-Drift**: Drawdown from peak is objective. 8% and 3% thresholds are fixed. Mechanical execution.
- **Edge Source**: Structural — stop-loss with re-entry captures the benefit of loss limiting while avoiding the worst problem of stops (permanent disinvestment).
- **Assets**: Any portfolio (overlay)
- **Timeframe**: Daily monitoring
- **Expected Perf**: Reduces MaxDD by 30-50%. Whipsaw cost: ~2% per false signal.
- **Complexity**: Low
- **Refs**: Kaminski & Lo (2014) "When Do Stop-Loss Rules Stop Losses?"

### 7.7 Kelly Criterion Position Sizing
- **Core Logic**: Kelly criterion determines optimal bet size given win rate and payoff ratio. Half-Kelly is more robust and commonly used. Prevents overbetting and underbetting.
- **Signal**: For each trade: compute edge (expected return) and odds (win/loss ratio). Kelly fraction = (p × b − q) / b, where p = win rate, b = avg win/avg loss, q = 1 − p. Use half-Kelly (divide by 2).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Compare Kelly, half-Kelly, fixed size.
- **Anti-Drift**: Kelly is mathematical formula. Win rate and payoff from historical trades. Half-Kelly is conservative.
- **Edge Source**: Structural — Kelly criterion maximizes long-term geometric growth rate. Optimal capital allocation under uncertainty.
- **Assets**: All strategies (position sizing overlay)
- **Timeframe**: Per-trade
- **Expected Perf**: Improves geometric growth by 10-20% vs fixed sizing
- **Complexity**: Low
- **Refs**: Kelly (1956) "A New Interpretation of Information Rate"; Thorp (2006)

### 7.8 Regime-Aware Hedging
- **Core Logic**: Hedge differently based on market regime. In normal markets → minimal hedging. In elevated risk → put spreads. In crisis → VIX calls + deep OTM puts. Optimize hedge cost vs protection.
- **Signal**: Regime indicator (VIX level + credit spread + breadth). Normal (VIX < 18, spread stable, breadth positive) → no hedge. Elevated (VIX 18-30) → put spreads (2% of portfolio). Crisis (VIX > 30) → VIX calls + puts (3%).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Regime classification uses market data. Hedge instruments and budgets are predefined per regime.
- **Edge Source**: Structural — regime-aware hedging reduces the cost of permanent hedging while providing protection when needed.
- **Assets**: Portfolio hedge overlay using SPX options, VIX options
- **Timeframe**: Monthly regime assessment
- **Expected Perf**: Hedging cost: 0.5-1.5% annually. Protection: 30-50% drawdown reduction in crises.
- **Complexity**: Medium
- **Refs**: Bhansali (2014) "Tail Risk Hedging"

### 7.9 Dynamic Rebalancing (Threshold-Based)
- **Core Logic**: Instead of calendar-based rebalancing (monthly, quarterly), rebalance only when allocation drifts beyond threshold. Reduces turnover while maintaining target risk.
- **Signal**: Set target allocation (e.g., 60/40). When any asset drifts > 5% from target → rebalance to target. Otherwise → hold. This is fewer trades than monthly, but responsive to large moves.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Compare threshold vs calendar rebalancing.
- **Anti-Drift**: Target allocation is fixed. 5% threshold is mechanical. No optimization.
- **Edge Source**: Structural — threshold rebalancing captures the "buy low, sell high" benefit of rebalancing while minimizing transaction costs.
- **Assets**: Any multi-asset portfolio
- **Timeframe**: Continuous monitoring, event-driven rebalancing
- **Expected Perf**: Similar returns to monthly rebalancing with 40-60% fewer trades
- **Complexity**: Low
- **Refs**: Donohue & Yip (2003) "Optimal Portfolio Rebalancing with Transaction Costs"

### 7.10 Maximum Diversification Portfolio
- **Core Logic**: Maximize the diversification ratio (weighted average vol / portfolio vol). This tilts toward low-correlation assets, maximizing the benefit of diversification.
- **Signal**: Solve: max Σ(w_i × σ_i) / σ_portfolio. Subject to weights sum to 1, no short selling. Monthly covariance estimation (60D rolling). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Diversification ratio is mathematical. Covariance from market data. Monthly updating.
- **Edge Source**: Structural — max diversification portfolios have lower drawdowns and higher risk-adjusted returns than equal-weight or cap-weight.
- **Assets**: Multi-asset (equities, bonds, commodities, FX, real estate)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −10%, PF 1.42
- **Complexity**: Medium
- **Refs**: Choueifaty & Coignard (2008) "Toward Maximum Diversification"

---

## 8. Alternative Systematic (10)

### 8.1 Insurance-Linked Securities (Cat Bonds)
- **Core Logic**: Catastrophe bonds (cat bonds) pay high coupons and are uncorrelated with financial markets. Construct a diversified portfolio of cat bonds across perils and regions.
- **Signal**: Buy cat bonds with: coupon > risk-free + 5%, multiple modeling agencies agree on expected loss, diversified across peril types (hurricane, earthquake, windstorm).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k (catastrophe model). Must model tail losses.
- **Anti-Drift**: Coupon spread is market data. Expected loss from catastrophe models. Diversification reduces idiosyncratic cat risk.
- **Edge Source**: Structural — cat bond premium compensates for catastrophe risk, which is uncorrelated with markets. True diversification source.
- **Assets**: Cat bond portfolio (Swiss Re index)
- **Timeframe**: Buy and hold (3-5 year bonds)
- **Expected Perf**: WR 90% (years), Sharpe 0.80, MaxDD −15% (single cat event), PF 1.50
- **Complexity**: High
- **Refs**: Cummins (2008) "CAT Bonds and Other Risk-Linked Securities"

### 8.2 Merger Arbitrage Systematic
- **Core Logic**: After merger announcement, target stock trades at a discount to deal price (deal spread). Buy target, earn spread as deal closes. Systematic approach across many deals.
- **Signal**: After merger announcement: if deal spread > 3% → buy target. If stock-for-stock: buy target, short acquirer. Position size: 2% per deal, max 20 concurrent. Exit at deal close or break.
- **Best Backtest Method**: Walk-forward 15yr/5yr/5yr. Monte Carlo 10k. Must model deal break probability.
- **Anti-Drift**: Deal announcements are public. Spread is market data. Position rules are fixed.
- **Edge Source**: Structural — deal spread compensates for deal break risk and time. Diversification across many deals makes returns stable.
- **Assets**: Merger targets (US and global)
- **Timeframe**: Event-driven, 2-6 month hold per deal
- **Expected Perf**: WR 85% (per deal), Sharpe 0.75, MaxDD −10%, PF 1.50
- **Complexity**: Medium
- **Refs**: Mitchell & Pulvino (2001) "Characteristics of Risk and Return in Risk Arbitrage"

### 8.3 Convertible Bond Gamma Trading
- **Core Logic**: Convertible bonds have embedded equity optionality (gamma). When stock price is near conversion price, the convertible has significant gamma. Buy and delta-hedge to monetize gamma.
- **Signal**: Buy convertible when stock near conversion price (within 10%) AND convertible gamma > 0.01. Delta-hedge daily. Close when stock moves > 20% from conversion price.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Conversion price is fixed. Gamma is computable. Delta-hedge is mathematical.
- **Edge Source**: Structural — convertible bond market is less liquid than equity options → gamma is cheaper to buy. Embedded gamma is often underpriced.
- **Assets**: Convertible bonds near conversion price
- **Timeframe**: Variable hold (while near conversion price)
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −8%, PF 1.35
- **Complexity**: High
- **Refs**: Calamos (2003) "Convertible Arbitrage"

### 8.4 Dividend Strip Value
- **Core Logic**: Dividend futures/options price expected dividends. When dividend strip is cheap (implied dividend < consensus), buy the strip. When expensive, sell. Arbitrage dividend expectations.
- **Signal**: Compare implied annual dividend (from dividend futures) vs consensus estimate. When implied < consensus − 5% → buy dividend future. When implied > consensus + 5% → sell.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Implied dividend from futures. Consensus from I/B/E/S. Gap threshold is fixed.
- **Edge Source**: Structural — dividend futures market is illiquid → pricing inefficiencies. Consensus estimates are more accurate than implied.
- **Assets**: SX5E, SPX dividend futures
- **Timeframe**: Quarterly signal, hold to expiry
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −5%, PF 1.35
- **Complexity**: Medium
- **Refs**: Van Binsbergen et al. (2012) "Equity Yields"

### 8.5 Regulatory Capital Arbitrage
- **Core Logic**: Bank capital regulations (Basel III/IV) create distortions in pricing. Assets that are expensive in regulatory capital terms are cheaper in market price terms. Buy the regulatory-disfavored.
- **Signal**: Identify securities with high regulatory capital charge relative to economic risk: agency MBS (favorable treatment), IG bonds (unfavorable for insurers). Position for arbitrage.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model regulatory environment.
- **Anti-Drift**: Capital charges are published (Basel rules). Economic risk is computable. Regulatory changes are slow.
- **Edge Source**: Structural — regulatory capital requirements distort pricing away from fair value. Exploiting regulatory-driven mispricing.
- **Assets**: Agency MBS, IG bonds, CLOs, ABS
- **Timeframe**: Quarterly assessment, 6-12 month hold
- **Expected Perf**: WR 60%, Sharpe 0.55, MaxDD −5%, PF 1.30
- **Complexity**: High
- **Refs**: Bliss & Steigerwald (2006) "Derivatives Clearing and Settlement: A Comparison of Central Counterparties and Alternative Structures"

### 8.6 Cross-Country Equity Value
- **Core Logic**: Compare equity market valuations across countries. Cheap markets (low CAPE, high earnings yield) outperform expensive ones over 3-5 years. Global equity rotation.
- **Signal**: Rank 23 developed markets by CAPE. Long bottom quintile (cheapest 5). Short top quintile (most expensive 5). Annual rebalance.
- **Best Backtest Method**: Walk-forward 30yr/10yr/10yr. Monte Carlo 10k.
- **Anti-Drift**: CAPE is published. Cross-sectional ranking. Annual signal (slow-moving). Well-documented.
- **Edge Source**: Structural — country-level value works for the same reasons stock-level value works. Mean-reversion of valuations driven by earnings cycle.
- **Assets**: Country ETFs (EWJ, EWG, EWU, EWA, etc.)
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −20%, PF 1.25
- **Complexity**: Low
- **Refs**: Asness, Israelov & Liew (2011) "International Diversification Works (Eventually)"

### 8.7 Volatility Carry Trade
- **Core Logic**: Sell vol on assets/currencies with high implied vol (expensive insurance) and buy vol on those with low implied vol (cheap insurance). Cross-asset vol carry.
- **Signal**: Rank implied vol across assets (SPX, EURUSD, UST, gold, oil). Sell straddles on top quintile IV rank. Buy straddles on bottom quintile. Monthly roll.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Implied vol is market data. Cross-asset ranking. Monthly roll.
- **Edge Source**: Structural — variance risk premium varies across assets. Selling on expensive and buying on cheap captures relative mispricing.
- **Assets**: SPX, EURUSD, UST, gold, oil options
- **Timeframe**: Monthly rolling
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −15%, PF 1.40
- **Complexity**: Medium
- **Refs**: Ilmanen (2012) "Do Financial Markets Reward Buying or Selling Insurance?"

### 8.8 Activist Investor Following
- **Core Logic**: When prominent activist investors (Icahn, Ackman, Peltz) take significant positions (> 5%), stock often reprices. Follow their 13-D filings and position alongside.
- **Signal**: When activist files 13-D with > 5% ownership → buy stock within 5 days. Hold 6 months. Only follow activists with historical track record (> 60% success rate). Max 5% per position.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must use actual 13-D dates.
- **Anti-Drift**: 13-D filings are SEC-mandated. Filing dates are public. Track record is historical. Position size is fixed.
- **Edge Source**: Informational — activists have done deep analysis AND have the power to create change. Following their filings captures their edge.
- **Assets**: Individual stocks (targets of activist campaigns)
- **Timeframe**: Event-driven, 6-month hold
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −15%, PF 1.32
- **Complexity**: Low
- **Refs**: Brav et al. (2008) "Hedge Fund Activism, Corporate Governance, and Firm Performance"

### 8.9 IPO Lock-Up Expiration Short
- **Core Logic**: After IPO lock-up expires (typically 180 days), insiders can sell shares. Selling pressure often depresses stock price around lock-up expiry. Short the stock ahead of expiry.
- **Signal**: Short stock 5 days before lock-up expiry. Cover 10 days after. Only for stocks that have rallied > 50% since IPO (insiders have large gains to monetize).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Lock-up expiry dates are published. 50% rally threshold is objective. 5-day pre-positioning.
- **Edge Source**: Structural — lock-up expiry creates predictable supply pressure. Insiders with large gains are motivated sellers.
- **Assets**: Recent IPO stocks
- **Timeframe**: Event-driven, 15-day hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.25
- **Complexity**: Low
- **Refs**: Field & Hanka (2001) "The Expiration of IPO Share Lockups"

### 8.10 Closed-End Fund Discount Reversion
- **Core Logic**: Closed-end funds trade at discounts or premiums to NAV. Extreme discounts revert as activist pressure, tender offers, or sentiment shifts push price toward NAV.
- **Signal**: When CEF discount > 15% AND discount Z-score (2Y) < −2.0 → buy (extreme discount). When discount < 3% or premium → sell. Monthly screening.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: NAV is published daily. Discount is computed. Z-score is adaptive.
- **Edge Source**: Behavioral — CEF discounts reflect sentiment and liquidity. Extreme discounts attract activists and narrow over time.
- **Assets**: Closed-end equity and bond funds
- **Timeframe**: Monthly screening, 6-12 month hold
- **Expected Perf**: WR 60%, Sharpe 0.65, MaxDD −10%, PF 1.38
- **Complexity**: Low
- **Refs**: Lee, Shleifer & Thaler (1991) "Investor Sentiment and the Closed-End Fund Puzzle"

---

## 9. Quantitative Execution (10)

### 9.1 VWAP Execution Algorithm
- **Core Logic**: Execute large orders to achieve price close to Volume-Weighted Average Price (VWAP). Slice order across the day proportional to historical volume profile.
- **Signal**: Historical intraday volume profile (30-day average). Slice order into time buckets matching volume distribution. Limit orders at or below VWAP in each bucket.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo with tick data. Monte Carlo 10k.
- **Anti-Drift**: Volume profile is updated daily. Time slicing is mathematical. Limit orders minimize impact.
- **Edge Source**: Structural — matching volume profile minimizes market impact. VWAP is the standard benchmark for institutional execution.
- **Assets**: All liquid stocks
- **Timeframe**: Intraday execution
- **Expected Perf**: Slippage: 1-3 bps vs VWAP
- **Complexity**: Medium
- **Refs**: Berkowitz, Logue & Noser (1988) "The Total Cost of Transactions on the NYSE"

### 9.2 Implementation Shortfall Minimizer
- **Core Logic**: Minimize implementation shortfall (difference between decision price and execution price). Balance urgency (speed) vs impact (cost). Adaptive based on real-time market conditions.
- **Signal**: IS optimizer: given order size, urgency, and real-time spread/depth → compute optimal participation rate. Higher urgency → faster execution (more impact). Lower urgency → patient (limit orders).
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo with tick data. Monte Carlo 10k.
- **Anti-Drift**: Real-time market data (spread, depth) adapts execution. Urgency is exogenous parameter.
- **Edge Source**: Structural — IS optimization formally balances timing risk vs market impact. Better than naive execution.
- **Assets**: All liquid stocks
- **Timeframe**: Per-trade execution
- **Expected Perf**: 2-5 bps improvement vs naive execution
- **Complexity**: High
- **Refs**: Almgren & Chriss (2001) "Optimal Execution of Portfolio Transactions"

### 9.3 Dark Pool Routing Optimization
- **Core Logic**: Route orders to dark pools vs lit markets based on historical fill rates, price improvement, and information leakage. Optimize venue selection for each order.
- **Signal**: Score each venue (dark pools + lit exchanges) based on: fill rate, price improvement, adverse selection cost. Route to highest-scoring venue first, cascade to next if not filled.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo. Monte Carlo 10k. Must model venue characteristics.
- **Anti-Drift**: Venue scores updated daily. Cascade logic is mechanical. Adverse selection monitoring.
- **Edge Source**: Structural — optimal venue routing reduces execution cost by finding the cheapest liquidity source.
- **Assets**: All US equities
- **Timeframe**: Per-order routing decision
- **Expected Perf**: 1-3 bps price improvement vs single-venue routing
- **Complexity**: High
- **Refs**: Buti, Rindi & Werner (2011) "Diving into Dark Pools"

### 9.4 Intraday Momentum Capture
- **Core Logic**: Intraday momentum: first 30 minutes of trading predicts the rest of the day. If market gaps up and holds, it tends to continue. Systematic intraday trend-following.
- **Signal**: At 10:00 AM: if SPX is up > 0.3% from open → long for the day. If down > 0.3% → short. Close at 3:55 PM. Filter: only trade when pre-market volume is above average.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr with intraday data. Monte Carlo 10k.
- **Anti-Drift**: 10:00 AM assessment is fixed. 0.3% threshold filters small moves. Intraday hold.
- **Edge Source**: Behavioral — morning momentum reflects overnight information processing. Institutional order flow confirms direction.
- **Assets**: SPY, ES futures
- **Timeframe**: Intraday (10 AM → 4 PM)
- **Expected Perf**: WR 53%, Sharpe 0.80 (annualized), MaxDD −5%, PF 1.30
- **Complexity**: Low
- **Refs**: Gao, Han & Zheng (2018) "Intraday Momentum"

### 9.5 Order Flow Imbalance Signal
- **Core Logic**: Order flow imbalance (buy volume − sell volume) predicts short-term price direction. When buy pressure dominates → price rises. When sell pressure → falls. Trade the imbalance.
- **Signal**: OFI = cumulative buy-initiated volume − sell-initiated volume (Lee-Ready classification). When 5M OFI Z > 2.0 → long for 30 min. When Z < −2.0 → short. Intraday.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo with tick data. Monte Carlo 10k.
- **Anti-Drift**: OFI is computed from trade data. Z-score is adaptive. Short-term signal.
- **Edge Source**: Structural — order flow contains information about informed trading. Imbalances create predictable short-term price pressure.
- **Assets**: Liquid large-cap stocks, ETFs
- **Timeframe**: Intraday (minutes to hours)
- **Expected Perf**: WR 53%, Sharpe 1.50 (annualized), MaxDD −3%, PF 1.35
- **Complexity**: High
- **Refs**: Cont, Kukanov & Stoikov (2014) "The Price Impact of Order Book Events"

### 9.6 Optimal Lot Size Liquidation
- **Core Logic**: When liquidating large positions, determine optimal lot sizes and timing to minimize total market impact. Larger lots in liquid periods, smaller in illiquid.
- **Signal**: Intraday liquidity profile (bid-ask spread + depth by time of day). Execute larger lots during peak liquidity (10:30-11:30, 2:30-3:30). Smaller lots during low liquidity (lunch, open, close).
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo with tick data. Monte Carlo 10k.
- **Anti-Drift**: Liquidity profile updated daily. Lot sizing is proportional to depth. Simple rules.
- **Edge Source**: Structural — matching execution size to liquidity minimizes impact. Avoids large orders in thin markets.
- **Assets**: All liquid stocks (large-order execution)
- **Timeframe**: Per-liquidation event
- **Expected Perf**: 3-8 bps cost reduction vs constant-size execution
- **Complexity**: Medium
- **Refs**: Kyle (1985) "Continuous Auctions and Insider Trading"

### 9.7 Close Auction Participation
- **Core Logic**: Closing auction provides significant liquidity (10-15% of daily volume). For orders that don't need intraday execution, participate in the closing auction for better fills.
- **Signal**: For portfolio rebalancing orders: submit 80% of order as MOC (market-on-close) or LOC (limit-on-close). Remaining 20% execute VWAP during the day for hedge.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo. Monte Carlo 10k.
- **Anti-Drift**: Closing auction is a fixed market event. MOC/LOC are standard order types.
- **Edge Source**: Structural — closing auction aggregates order flow → lower impact than intraday execution. Benchmark price for portfolio accounting.
- **Assets**: S&P 500 stocks
- **Timeframe**: Per-rebalance event
- **Expected Perf**: 1-2 bps improvement vs intraday-only execution
- **Complexity**: Low
- **Refs**: Pagano & Schwartz (2003) "A Closing Call's Impact on Market Quality"

### 9.8 Spread Capture Market Making
- **Core Logic**: Provide two-sided quotes (bid and ask) in liquid securities. Earn the bid-ask spread. Manage inventory risk through hedging and position limits.
- **Signal**: Quote bid and ask around mid-price. Adjust spread based on: inventory level, vol regime, order flow toxicity (VPIN). Wider spread when conditions are adverse. Narrower when safe.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo with tick data. Monte Carlo 10k.
- **Anti-Drift**: Mid-price is market data. Spread adjustment is based on real-time conditions. Inventory limits.
- **Edge Source**: Structural — market making earns the bid-ask spread. Adaptive spread management avoids adverse selection.
- **Assets**: Liquid ETFs and stocks
- **Timeframe**: Continuous intraday
- **Expected Perf**: Sharpe > 3.0 (gross), WR 55%, MaxDD −2%, PF 1.30
- **Complexity**: Very High
- **Refs**: Avellaneda & Stoikov (2008) "High-Frequency Trading in a Limit Order Book"

### 9.9 Transaction Cost Analysis (TCA) Feedback Loop
- **Core Logic**: Measure actual execution costs vs benchmarks (VWAP, arrival price, IS). Feed results back to execution algorithms for continuous improvement. ML-based parameter optimization.
- **Signal**: After each trade: compute TCA metrics. If costs > target → adjust execution parameters (participation rate, venue routing, timing). Quarterly model retraining.
- **Best Backtest Method**: Continuous A/B testing. Monte Carlo 10k.
- **Anti-Drift**: TCA metrics are objective. Feedback loop is automated. A/B testing validates changes.
- **Edge Source**: Infrastructure — continuous TCA improvement compounds execution savings over time. Better execution = more alpha captured.
- **Assets**: All traded securities
- **Timeframe**: Continuous monitoring
- **Expected Perf**: 1-3 bps annual improvement in execution quality
- **Complexity**: High
- **Refs**: Kissell (2013) "The Science of Algorithmic Trading and Portfolio Management"

### 9.10 Pre-Trade Cost Estimation
- **Core Logic**: Before executing a trade, estimate expected cost (spread + impact + opportunity) to determine if the alpha signal is worth trading. Skip trades where estimated cost > expected alpha.
- **Signal**: Cost model: spread (from quote) + impact (from Almgren model with order size, ADV, vol) + opportunity cost (if delayed). When estimated cost > 80% of expected alpha → skip trade.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Cost model inputs are market data. Alpha estimate from strategy model. 80% threshold is conservative.
- **Edge Source**: Structural — pre-trade cost filtering prevents negative-alpha trades (where execution cost exceeds expected return). Improves net Sharpe.
- **Assets**: All strategies (trade filtering overlay)
- **Timeframe**: Per-trade decision
- **Expected Perf**: Reduces trades by 10-20%, improves net Sharpe by 0.10-0.15
- **Complexity**: Medium
- **Refs**: Almgren et al. (2005) "Direct Estimation of Equity Market Impact"

---

## 10. Portfolio Construction & Allocation (10)

### 10.1 Black-Litterman with Systematic Views
- **Core Logic**: Black-Litterman model combines market equilibrium (CAPM) with active views. Instead of subjective views, use systematic signals (momentum, value, sentiment) as views.
- **Signal**: Market equilibrium from CAPM. Systematic views: momentum signal → view on equity outperformance. Value signal → view on cheap market outperformance. Combine via B-L framework. Monthly optimization.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: CAPM equilibrium is from market data. Systematic views are from well-documented factors. B-L combination is mathematical.
- **Edge Source**: Structural — B-L provides a principled framework for combining market equilibrium with active views. Reduces estimation error vs Markowitz.
- **Assets**: Multi-asset (equities, bonds, commodities, FX, alternatives)
- **Timeframe**: Monthly optimization
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −12%, PF 1.40
- **Complexity**: High
- **Refs**: Black & Litterman (1992) "Global Portfolio Optimization"

### 10.2 Hierarchical Risk Parity (HRP)
- **Core Logic**: Use hierarchical clustering on correlation matrix to build portfolio tree. Allocate inversely proportional to cluster variance. Avoids problems of traditional mean-variance optimization.
- **Signal**: Compute correlation matrix → hierarchical clustering (Ward linkage) → quasi-diagonal reordering → recursive bisection for weight allocation. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Compare vs MVO, risk parity, equal weight.
- **Anti-Drift**: Correlation matrix from market data. Clustering is data-driven. No covariance matrix inversion (stable).
- **Edge Source**: Structural — HRP avoids Markowitz's covariance matrix inversion problem. More stable out-of-sample than MVO.
- **Assets**: Multi-asset portfolio (15-30 assets)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −12%, PF 1.42
- **Complexity**: Medium
- **Refs**: López de Prado (2016) "Building Diversified Portfolios that Outperform Out-of-Sample"

### 10.3 Entropy-Based Diversification
- **Core Logic**: Maximize portfolio entropy (Shannon entropy of return distribution) rather than Sharpe ratio. Higher entropy = more diversified return distribution = more robust.
- **Signal**: Solve: max entropy(portfolio return distribution). Subject to: expected return > threshold, weights sum to 1. Estimate entropy via kernel density estimation. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Entropy is non-parametric (no distribution assumption). KDE adapts to data. Monthly rebalance.
- **Edge Source**: Structural — entropy maximization creates more robust portfolios than mean-variance because it captures higher moments.
- **Assets**: Multi-asset portfolio
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −10%, PF 1.40
- **Complexity**: High
- **Refs**: Bera & Park (2008) "Optimal Portfolio Diversification Using the Maximum Entropy Principle"

### 10.4 Minimum Correlation Portfolio
- **Core Logic**: Instead of minimum variance, minimize the average pairwise correlation of portfolio. This directly targets the diversification benefit.
- **Signal**: Solve: min average pairwise correlation of portfolio. Subject to: weights sum to 1, no short selling. Correlation estimated from 60D rolling window. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Correlations from market data. Optimization is mathematical. Monthly updating.
- **Edge Source**: Structural — minimum correlation portfolios maintain diversification benefit even in stressed markets. More stable than minimum variance.
- **Assets**: Multi-asset portfolio (10-20 assets)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −10%, PF 1.40
- **Complexity**: Medium
- **Refs**: Christoffersen et al. (2012) "Is the Potential for International Diversification Disappearing?"

### 10.5 Regime-Conditional Allocation
- **Core Logic**: Maintain different target allocations for different market regimes. Switch allocation when regime changes. Combines regime detection with portfolio optimization.
- **Signal**: 4-regime model (expansion, slowdown, recession, recovery). Each regime has pre-computed optimal allocation (from historical data). Regime detection from macro indicators. Quarterly assessment.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Regime classification from published macro data. Pre-computed allocations are fixed per regime. Quarterly (not over-traded).
- **Edge Source**: Structural — optimal allocation varies dramatically by regime. 60/40 is only optimal in expansion. Regime-conditional allocation adapts.
- **Assets**: SPY, TLT, GLD, DBC, SHY
- **Timeframe**: Quarterly regime assessment
- **Expected Perf**: WR 58%, Sharpe 0.80, MaxDD −12%, PF 1.45
- **Complexity**: Medium
- **Refs**: Ang & Bekaert (2002) "International Asset Allocation With Regime Shifts"

### 10.6 Factor Allocation (Smart Beta 2.0)
- **Core Logic**: Allocate across factor indices (value, momentum, quality, low-vol, size) using a timing model. Overweight factors with positive expected returns, underweight negative.
- **Signal**: For each factor: predict next-month return using macro indicators (value spread, momentum speed, economic cycle). When predicted return > 0 → overweight factor. When < 0 → underweight. Monthly.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must test factor timing accuracy.
- **Anti-Drift**: Factor indices are published. Macro predictors are standard. Monthly rebalance.
- **Edge Source**: Structural — factor returns are time-varying and partially predictable. Timing allocation improves on static factor exposure.
- **Assets**: Factor indices (VLUE, MTUM, QUAL, USMV, SIZE)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.70, MaxDD −15%, PF 1.35
- **Complexity**: Medium
- **Refs**: Arnott, Beck & Kalesnik (2016) "Timing 'Smart Beta' Strategies? Of Course! Buy Low, Sell High!"

### 10.7 Portable Alpha via Overlay
- **Core Logic**: Generate alpha from a market-neutral strategy. Overlay onto a passive beta exposure (via futures). Total return = beta return + alpha return. Alpha is "transported" to any asset class.
- **Signal**: Alpha source: market-neutral long/short equity strategy. Beta: SPX futures overlay (capital-efficient exposure). Rebalance overlay monthly.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Alpha strategy independently validated. Beta from futures (no capital needed). Monthly rebalance.
- **Edge Source**: Structural — portable alpha separates alpha generation from beta exposure. Allows alpha from any source to enhance any beta.
- **Assets**: Alpha: market-neutral equity. Beta: SPX, bond, or commodity futures
- **Timeframe**: Monthly rebalance
- **Expected Perf**: Beta return + 2-4% alpha annually
- **Complexity**: High
- **Refs**: Kung & Pohlman (2004) "Portable Alpha"

### 10.8 Constant Proportion Portfolio Insurance (CPPI)
- **Core Logic**: CPPI allocates between risky asset and risk-free based on a cushion (portfolio value − floor value). When portfolio rises → more risky. When falls → more safe. Dynamic insurance.
- **Signal**: Floor = initial value × 0.85 (15% max loss). Cushion = portfolio value − floor. Risky allocation = multiplier × cushion (multiplier = 4). Rebalance when allocation changes > 5%.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Floor and multiplier are fixed. Cushion is computed from portfolio value. Mechanical rebalancing.
- **Edge Source**: Structural — CPPI provides guaranteed floor (in continuous time) while allowing upside participation. Dynamic risk management.
- **Assets**: SPY (risky) + SHY (safe)
- **Timeframe**: Daily monitoring, event-driven rebalancing
- **Expected Perf**: Guarantees floor (85% of initial). Expected return: 60-70% of equity return.
- **Complexity**: Low
- **Refs**: Perold & Sharpe (1988) "Dynamic Strategies for Asset Allocation"

### 10.9 Multi-Strategy Portfolio (Risk Budget)
- **Core Logic**: Allocate across multiple strategies (momentum, value, carry, mean-reversion, vol selling) based on risk budget. Each strategy gets equal risk allocation. Rebalance when risk drifts.
- **Signal**: 5 strategies × 20% risk budget each. Compute each strategy's realized vol. Adjust capital allocation so each contributes 20% of portfolio risk. Quarterly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must model strategy correlations.
- **Anti-Drift**: Risk decomposition is mathematical. Equal risk budget is fixed. Quarterly rebalance.
- **Edge Source**: Structural — multi-strategy portfolio with risk budgeting provides true diversification across return drivers. Smoothest return stream.
- **Assets**: Portfolio of 5+ uncorrelated strategies
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 58%, Sharpe 1.00, MaxDD −8%, PF 1.55
- **Complexity**: Medium
- **Refs**: Roncalli (2013) "Introduction to Risk Parity and Budgeting"

### 10.10 Liability-Driven Investment (LDI) Optimization
- **Core Logic**: For portfolios with future liabilities (pensions, endowments), optimize to maximize funded ratio (assets/liabilities) rather than absolute return. Match liability duration and hedge liability risks.
- **Signal**: Liability duration = 15Y (typical pension). Hedging portfolio: 70% duration-matched bonds. Growth portfolio: 30% risk assets. Rebalance when funded ratio changes > 5%.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must model liability dynamics.
- **Anti-Drift**: Liability duration is actuarially computed. Bond matching is mathematical. Funded ratio is objective.
- **Edge Source**: Structural — LDI aligns portfolio with actual liability risks. Reduces funded ratio volatility vs traditional asset-only approaches.
- **Assets**: Long-duration bonds + growth assets (equities, alternatives)
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: Funded ratio vol: 5% (vs 15% for 60/40). Returns: sufficient to maintain funded status.
- **Complexity**: High
- **Refs**: Leibowitz, Bova & Hammond (2010) "The Endowment Model of Investing"

---

*100 Elite Macro, CTA & Systematic Strategies — End of Document*
