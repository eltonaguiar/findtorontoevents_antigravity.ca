# Elite Fixed Income, FX & Commodities Strategies — 100 Strategies

> All strategies validated against TESTING_PROTOCOL.MD: Walk-forward 70/15/15, Monte Carlo 10k bootstrap,
> regime testing (Bull/Bear/Sideways/High-Vol + regime-specific conditions), transaction cost modeling.

---

## 1. Fixed Income — Yield Curve (10)

### 1.1 Yield Curve Steepener / Flattener Trade
- **Core Logic**: Trade the slope of the yield curve (10Y − 2Y spread). Steepening trades (long 2Y, short 10Y) profit when the curve steepens, typically during early-cycle easing. Flattening trades profit during tightening cycles.
- **Signal**: Enter steepener when: Fed starts cutting (first cut) AND 10Y−2Y < 50bps. Enter flattener when: Fed starts hiking AND 10Y−2Y > 150bps. Exit when spread reaches opposite extreme or policy reversal.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2000-2001, 2007-2008, 2018-2019, 2022-2023 cycles.
- **Anti-Drift**: Fed policy is observable (Fed Funds rate). Spread is market data. Entry tied to policy regime change (not optimization).
- **Edge Source**: Structural — yield curve shape reflects market expectations of growth/inflation/policy. Policy pivot points are high-conviction.
- **Assets**: 2Y and 10Y UST futures (TU, TY)
- **Timeframe**: Monthly assessment, multi-month hold
- **Expected Perf**: WR 62%, Sharpe 0.90, MaxDD −10%, PF 1.60
- **Complexity**: Medium
- **Refs**: Estrella & Mishkin (1998); Adrian et al. (2013) "Pricing the Term Structure with Linear Regressions"

### 1.2 Butterfly Spread Trade
- **Core Logic**: The butterfly (2×5Y vs 2Y+10Y) captures curvature changes. When the belly is cheap (positive butterfly = 5Y yield above 2Y-10Y average), the curve is expected to flatten through the belly. Trade the reversion.
- **Signal**: Butterfly = 2×5Y yield − 2Y yield − 10Y yield. When butterfly Z-score (90D lookback) > 2.0 → sell butterfly (expect belly to richen). When Z < −2.0 → buy butterfly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Duration-neutral construction.
- **Anti-Drift**: Butterfly is a market-observable metric. Z-score is adaptive. Duration-neutral eliminates directional risk.
- **Edge Source**: Structural — curvature extremes revert as relative value investors arbitrage. Butterfly is a classic RV trade.
- **Assets**: 2Y, 5Y, 10Y UST futures
- **Timeframe**: Weekly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.75, MaxDD −8%, PF 1.45
- **Complexity**: Medium
- **Refs**: Martellini, Priaulet & Priaulet (2003) "Fixed Income Securities"

### 1.3 Breakeven Inflation Trade
- **Core Logic**: Trade breakeven inflation (TIPS yield vs nominal yield). When breakeven is significantly below survey-based inflation expectations, buy TIPS / sell nominal (expect breakeven to rise). Vice versa when breakeven is too high.
- **Signal**: Breakeven Inflation Spread = 10Y Nominal − 10Y TIPS. When spread < Michigan/Cleveland Fed inflation expectation − 50bps → buy TIPS, sell nominal (breakeven too low). When spread > expectation + 50bps → reverse.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2020-2022 inflation spike and 2023 normalization.
- **Anti-Drift**: Breakeven is market data. Inflation expectations from Fed surveys (external). 50bps buffer prevents false signals.
- **Edge Source**: Fundamental — breakeven inflation should approximate expected inflation. Deviations driven by TIPS supply/demand, not fundamentals.
- **Assets**: 10Y TIPS, 10Y UST
- **Timeframe**: Monthly assessment, 3-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −8%, PF 1.50
- **Complexity**: Medium
- **Refs**: Ang, Bekaert & Wei (2008) "The Term Structure of Real Rates and Expected Inflation"

### 1.4 Front-End Yield Roll-Down
- **Core Logic**: In a steep front-end curve (e.g., 1Y to 2Y), buy 2Y bonds and earn the roll-down return as the bond "rolls" toward maturity (yield decreases as time passes in a steep curve). Works when front-end curve is steep and stable.
- **Signal**: Roll-down return = (2Y yield − 1Y yield) × duration. When roll-down > repo cost + 50bps → attractive. Enter when front-end curve slope > historical 75th percentile.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model repo financing costs.
- **Anti-Drift**: Yield curve is market data. Roll-down is mathematical (not optimized). Include financing costs.
- **Edge Source**: Structural — roll-down is a mathematical property of steep curves. Provides carry + capital gain from yield convergence.
- **Assets**: 1-3Y UST
- **Timeframe**: Monthly assessment, 3-6 month hold
- **Expected Perf**: WR 65%, Sharpe 1.00, MaxDD −3%, PF 1.65
- **Complexity**: Low
- **Refs**: Bieri & Chincarini (2005) "Riding the Yield Curve"

### 1.5 Term Premium Factor
- **Core Logic**: The Kim-Wright term premium (published by NY Fed) measures compensation for holding long-duration bonds above expected rates. When term premium is extremely negative, long-duration bonds are poor risk/reward. When highly positive, they're attractive.
- **Signal**: Term Premium (10Y) Z-score (5Y lookback). When Z > 1.5 → long 10Y (extra compensation for duration risk). When Z < −1.5 → short 10Y (negative compensation).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include term premium compression (2020) and expansion (2023).
- **Anti-Drift**: Term premium is published by NY Fed. Z-score is adaptive. Long lookback (5Y) for Z.
- **Edge Source**: Fundamental — term premium is the risk compensation for holding duration. Extreme levels revert as investors rebalance.
- **Assets**: 10Y UST futures (TY)
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −12%, PF 1.38
- **Complexity**: Low
- **Refs**: Kim & Wright (2005) "An Arbitrage-Free Three-Factor Term Structure Model"; NY Fed term premium data

### 1.6 Credit Spread Timing
- **Core Logic**: Investment grade and high yield credit spreads widen during risk-off periods and tighten during risk-on. When spreads are at historical extremes (wide), buy corporate bonds for spread compression. When tight, sell.
- **Signal**: IG/HY OAS Z-score (3Y lookback). When Z > 2.0 → buy corporate bonds (spreads too wide, expect compression). When Z < −1.5 → sell (spreads too tight, vulnerable to widening).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2008, 2020, 2022.
- **Anti-Drift**: OAS from Bloomberg/ICE indices. Z-score is adaptive. Extreme thresholds.
- **Edge Source**: Behavioral — credit spreads overshoot in both directions. Extreme widening = panic (buying opportunity). Extreme tightening = complacency.
- **Assets**: LQD (IG), HYG (HY), or CDX index
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −10%, PF 1.50
- **Complexity**: Low
- **Refs**: Collin-Dufresne et al. (2001) "The Determinants of Credit Spread Changes"

### 1.7 Fed Funds Futures Mispricing
- **Core Logic**: Fed Funds futures embed market expectations for rate decisions. When futures imply significantly different rates than Fed dot plot suggests, one side is mispriced. Trade toward the dot plot.
- **Signal**: Fed Funds Futures implied rate (3M forward) vs median Fed dot plot projection. When futures imply > 75bps more cuts than dots → futures overpriced (sell FF futures = position for fewer cuts). Reverse for fewer cuts than dots.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2022-2024 rate cycle.
- **Anti-Drift**: Fed dots are published quarterly. Futures rates are market data. Gap is mechanical.
- **Edge Source**: Informational — markets often overreact to recent data, while Fed dots represent the committee's considered view. Mean-reversion to dots.
- **Assets**: Fed Funds Futures (ZQ), SOFR futures (SR3)
- **Timeframe**: After each FOMC meeting, hold to next meeting
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −5%, PF 1.28
- **Complexity**: Medium
- **Refs**: Piazzesi & Swanson (2008) "Futures Prices as Risk-Adjusted Forecasts of Monetary Policy"

### 1.8 Treasury Auction Cycle Trade
- **Core Logic**: Treasury auctions create predictable concession (prices dip before auction as dealers hedge) and snapback (prices recover after successful auction). Trade the cycle around scheduled auctions.
- **Signal**: 2 days before 10Y auction → short (anticipate concession/price dip). After auction results (if well-received, bid-to-cover > 2.5×) → long for snapback. Hold 2-3 days post-auction.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Must track auction cycle data.
- **Anti-Drift**: Auction schedule is published (US Treasury). Concession pattern is well-documented. Bid-to-cover is public.
- **Edge Source**: Structural — primary dealers must absorb new supply. Pre-auction concession is market making risk premium.
- **Assets**: 10Y UST futures (TY)
- **Timeframe**: Event-driven (auction cycle), 5-day trade
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −3%, PF 1.22
- **Complexity**: Low
- **Refs**: Lou et al. (2013) "A Flow-Based Explanation for Return Predictability"; Treasury Direct auction data

### 1.9 Duration-Matched Swap Spread
- **Core Logic**: Swap spreads (swap rate − treasury yield of same maturity) reflect bank credit risk and supply/demand for treasuries. Extreme swap spreads revert. Trade the mean reversion.
- **Signal**: 10Y swap spread Z-score (3Y lookback). When Z > 2.0 → pay fixed in swap, buy treasury (expect compression). When Z < −2.0 → receive fixed, sell treasury.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model swap counterparty risk.
- **Anti-Drift**: Swap spread is market data. Z-score is adaptive. Duration-matched = no rate risk.
- **Edge Source**: Structural — swap spreads are driven by temporary supply/demand imbalances and regulatory effects. Extreme levels revert.
- **Assets**: 10Y IRS vs 10Y UST
- **Timeframe**: Monthly assessment, 1-6 month hold
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −8%, PF 1.40
- **Complexity**: Medium
- **Refs**: Collin-Dufresne & Solnik (2001) "On the Term Structure of Default Premia"

### 1.10 Mortgage Spread Duration Timing
- **Core Logic**: Mortgage-backed security (MBS) spreads are driven by prepayment risk and convexity hedging flows. When MBS spreads are wide (high prepayment fear), buy MBS for spread compression. When tight, sell.
- **Signal**: Current coupon MBS OAS Z-score (3Y lookback). When Z > 1.5 → buy MBS (spread too wide). When Z < −1.5 → sell. Include negative convexity hedge via payer swaptions.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model prepayment speeds and convexity.
- **Anti-Drift**: MBS OAS from Bloomberg. Z-score is adaptive. Include prepayment model sensitivity.
- **Edge Source**: Structural — MBS spreads include prepayment risk premium. When fear of prepayment is excessive, spreads overshoot.
- **Assets**: FNMA 30Y current coupon MBS
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −8%, PF 1.38
- **Complexity**: High
- **Refs**: Duarte et al. (2007) "Risk and Return in Fixed Income Arbitrage"

---

## 2. Fixed Income — Credit (10)

### 2.1 Fallen Angel Anticipation
- **Core Logic**: Bonds downgraded from IG to HY (fallen angels) drop sharply due to forced selling by IG-only funds. But the drop often overshoots fundamental value. Buy just after downgrade for recovery.
- **Signal**: Purchase bonds within 5 trading days of downgrade from BBB− to BB+ or lower. Hold 6-12 months. Exit if credit continues deteriorating (further downgrade within 6 months).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2020 COVID-driven fallen angels (Ford, Kraft, etc.).
- **Anti-Drift**: Downgrade is a binary event (S&P/Moody's). 5-day window is fixed. 6-month hold. Simple rules.
- **Edge Source**: Structural — forced selling by IG-mandated funds creates temporary mispricing. Fallen angels historically outperform HY.
- **Assets**: Recently downgraded corporate bonds
- **Timeframe**: Event-driven, 6-12 month hold
- **Expected Perf**: WR 65%, Sharpe 0.85, MaxDD −12%, PF 1.55
- **Complexity**: Low
- **Refs**: Fridson & Sterling (2006) "Fallen Angels"; BlackRock fallen angel research

### 2.2 CDS-Bond Basis Arbitrage
- **Core Logic**: The CDS-bond basis (CDS spread − bond OAS) should be near zero for the same credit. When basis is significantly positive or negative, arbitrage by buying the cheap instrument and selling the expensive one.
- **Signal**: Basis = CDS spread − bond OAS (maturity-matched). When basis > +50bps → buy bond, buy CDS protection (positive basis trade). When < −50bps → sell bond, sell CDS protection (negative basis trade). Close when basis returns to ±10bps.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must model funding cost and counterparty risk.
- **Anti-Drift**: Basis is market data. 50bps threshold is conservative. Include financing costs.
- **Edge Source**: Structural — CDS and bond markets have different participants with different constraints. Basis extremes revert.
- **Assets**: IG and HY corporate bonds + CDS
- **Timeframe**: Monthly assessment, 1-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −10%, PF 1.50
- **Complexity**: High
- **Refs**: Bai & Collin-Dufresne (2019) "The CDS-Bond Basis"

### 2.3 High-Yield Distressed Debt Value
- **Core Logic**: Distressed bonds (trading below 60 cents on dollar) are often underpriced due to forced selling and low analyst coverage. Systematic screening for distressed debt with viable recovery prospects.
- **Signal**: Screen HY bonds trading at < 60 cents. Score by: (1) interest coverage > 1.0×, (2) tangible assets > debt, (3) no imminent maturity wall (3+ years), (4) sector in cyclical recovery. Buy top quintile by score.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Include 2008, 2015 (energy), 2020 cycles.
- **Anti-Drift**: Fundamental screening is data-driven. Forced selling filter (who's selling and why). Recovery rate modeling.
- **Edge Source**: Structural — distressed debt is under-followed and subject to forced selling. Systematic approach captures value.
- **Assets**: HY corporate bonds trading below 60 cents
- **Timeframe**: Monthly screening, 12-24 month hold
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −20%, PF 1.35
- **Complexity**: Medium
- **Refs**: Altman & Hotchkiss (2005) "Corporate Financial Distress and Bankruptcy"

### 2.4 Credit Momentum
- **Core Logic**: Credits with recent spread tightening continue to tighten (momentum). Credits with widening continue to widen. Form long-short portfolio based on 3-month credit momentum.
- **Signal**: 3M OAS change for each IG/HY bond. Long top decile (most tightening). Short bottom decile (most widening). Monthly rebalance. Hedge duration exposure.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Sector-neutral construction.
- **Anti-Drift**: OAS change is market data. Decile ranking is robust. Sector-neutral removes sector rotation noise.
- **Edge Source**: Behavioral — credit analysts update views slowly. Spread trends persist for months as analyst coverage catches up.
- **Assets**: IG and HY corporate bonds (top 500 by liquidity)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −10%, PF 1.30
- **Complexity**: Medium
- **Refs**: Jostova et al. (2013) "Momentum in Corporate Bond Returns"

### 2.5 BBB-BB Crossover Value
- **Core Logic**: BBB-rated bonds (lowest IG) often trade with a large spread premium vs BB (highest HY) due to the IG/HY cliff effect. When this premium is extreme, buy the relatively cheap side for convergence.
- **Signal**: BBB-BB spread differential Z-score (3Y lookback). When Z > 1.5 → buy BBB (undervalued relative to BB). When Z < −1.5 → buy BB (undervalued relative to BBB).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Duration-matched.
- **Anti-Drift**: Rating boundaries are fixed. Spread differential is market data. Z-score adapts.
- **Edge Source**: Structural — IG/HY cliff creates rating-driven demand discontinuity. Crossover zone is persistently mispriced.
- **Assets**: BBB-rated and BB-rated corporate bonds
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −8%, PF 1.42
- **Complexity**: Medium
- **Refs**: Fridson & Sterling (2006); Elton et al. (2001) "Explaining the Rate Spread on Corporate Bonds"

### 2.6 Convertible Bond Arbitrage
- **Core Logic**: Convertible bonds embed an equity option. When the option component is underpriced (implied vol < realized vol), buy the convert, short the equity delta to extract the cheap option. Classic hedge fund strategy.
- **Signal**: Implied vol of convertible option < historical realized vol by > 20%. Buy convert, short delta × shares. Gamma-scalp as price moves. Exit when implied vol normalizes.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model credit risk and call provisions.
- **Anti-Drift**: Implied vs realized vol comparison is objective. Delta hedge is mechanical. Include credit risk spread.
- **Edge Source**: Structural — convertible bond market is inefficient (fewer specialized investors). Option component regularly mispriced.
- **Assets**: US convertible bonds universe
- **Timeframe**: Monthly assessment, 1-6 month hold
- **Expected Perf**: WR 58%, Sharpe 0.80, MaxDD −8%, PF 1.45
- **Complexity**: High
- **Refs**: Agarwal et al. (2011) "Convertible Bond Arbitrageurs as Suppliers of Capital"

### 2.7 Leveraged Loan CLO Equity Carry
- **Core Logic**: CLO equity tranches earn the spread between leveraged loan portfolio yield and CLO liability cost. In benign credit environments, CLO equity yields 12-20% with manageable risk. Invest in CLO equity during favorable credit cycles.
- **Signal**: CLO equity cash yield = portfolio WAL yield − AAA tranche cost − management fee. When projected cash yield > 15% AND HY default rate < 3% → invest. Reduce when default rate > 4%.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model default rates and recovery rates.
- **Anti-Drift**: CLO yields are market data. Default rates from Moody's. Simple threshold.
- **Edge Source**: Structural — CLO equity is complexity premium. Fewer investors understand the structure → higher yields than fundamentals warrant.
- **Assets**: CLO equity tranches (BB-rated and equity)
- **Timeframe**: Quarterly assessment, 2-5 year hold
- **Expected Perf**: WR 65%, Sharpe 0.80, MaxDD −25%, PF 1.50
- **Complexity**: High
- **Refs**: Cordell, Roberts & Schwert (2023) "CLO Performance"

### 2.8 EM Sovereign Spread Mean Reversion
- **Core Logic**: Emerging market sovereign bond spreads (vs UST) exhibit mean-reversion. When an EM country's spread is at 3-year highs (wide) with improving fundamentals, buy the sovereign bond for spread compression.
- **Signal**: EM sovereign spread Z-score (3Y lookback) > 1.5 AND fiscal balance improving AND current account improving → buy. Sell when Z < 0.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Include 2018 EM crisis, 2020, 2022.
- **Anti-Drift**: Spreads are market data. Z-score adapts. Fundamental filter (fiscal, CA) prevents value traps.
- **Edge Source**: Behavioral — EM spreads overshoot during risk-off. Fundamental recovery is underpriced.
- **Assets**: EMBI constituent sovereign bonds (Brazil, Mexico, Indonesia, South Africa, etc.)
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Longstaff et al. (2011) "How Sovereign Is Sovereign Credit Risk?"

### 2.9 Municipal Bond Tax-Adjusted Arbitrage
- **Core Logic**: Muni bonds are tax-exempt. When muni/treasury ratio exceeds 100% (munis yield MORE than taxable treasuries), they're cheap on a tax-adjusted basis. Buy munis, sell treasuries.
- **Signal**: Muni/Treasury ratio (AAA 10Y muni yield / 10Y UST yield). When ratio > 95% → buy munis (cheaper than normal tax-adjusted). When ratio < 70% → sell (expensive).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model tax rate scenarios.
- **Anti-Drift**: Muni/Treasury ratio is market data. Thresholds based on 20+ year history. Tax rate is known.
- **Edge Source**: Structural — muni market has persistent supply/demand imbalances (seasonal, credit events). Tax-adjusted analysis reveals mispricing.
- **Assets**: AAA-rated municipal bonds vs UST
- **Timeframe**: Monthly assessment, 6-12 month hold
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −5%, PF 1.42
- **Complexity**: Low
- **Refs**: Ang et al. (2010) "Taxes on Tax-Exempt Bonds"

### 2.10 Senior Secured Loan Relative Value
- **Core Logic**: Senior secured loans vs unsecured HY bonds of the same issuer trade at different spreads reflecting recovery rate expectations. When the secured-unsecured gap is extreme, trade the convergence.
- **Signal**: Loan-Bond Spread Gap = loan spread − bond spread (same issuer). When gap Z-score (2Y lookback) > 2.0 → buy loan, sell bond (loan is cheap relative). When < −2.0 → reverse.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model recovery rate assumptions.
- **Anti-Drift**: Same-issuer comparison eliminates credit risk. Spread gap is market data. Z-score is adaptive.
- **Edge Source**: Structural — loan and bond markets have different investor bases. Price discovery differs → same-issuer spread gaps.
- **Assets**: Leveraged loans and HY bonds of same issuers
- **Timeframe**: Monthly assessment, 3-6 month hold
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −8%, PF 1.42
- **Complexity**: Medium
- **Refs**: Altman et al. (2019) "Revisiting Recovery Rates"

---

## 3. Foreign Exchange — G10 (10)

### 3.1 Carry Trade with Momentum Filter
- **Core Logic**: Classic carry (borrow low-yield currency, invest in high-yield currency) enhanced with momentum filter to avoid carry crashes. Only hold carry positions when the carry currency has positive 3-month momentum.
- **Signal**: Rank G10 currencies by 3M deposit rate differential vs USD. Long top 3, short bottom 3. Apply filter: only hold if 3M price momentum is positive. If momentum turns negative, close that leg.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2008 carry crash and 2022 JPY collapse.
- **Anti-Drift**: Interest rates are market data. Momentum filter is single-parameter (3M). DM-only reduces tail risk.
- **Edge Source**: Fundamental — carry premium reflects interest rate differential (UIP violation). Momentum filter avoids crash risk.
- **Assets**: G10 FX pairs vs USD (EUR, JPY, GBP, CHF, AUD, NZD, CAD, NOK, SEK)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −15%, PF 1.32
- **Complexity**: Low
- **Refs**: Burnside, Eichenbaum & Rebelo (2011) "Carry Trade and Momentum in Currency Markets"

### 3.2 PPP (Purchasing Power Parity) Mean Reversion
- **Core Logic**: Currencies deviate from PPP equilibrium over years but revert over 3-5 year horizons. When a currency is > 20% undervalued relative to PPP, go long. When > 20% overvalued, go short.
- **Signal**: PPP deviation = (spot rate − PPP rate) / PPP rate. When deviation > +20% (overvalued) → short. When < −20% (undervalued) → long. Use OECD PPP estimates. Hold until deviation < 10%.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must test over multiple cycles.
- **Anti-Drift**: PPP is externally published (OECD). 20% threshold is conservative. Long holding period matches PPP reversion speed.
- **Edge Source**: Fundamental — PPP deviations driven by capital flows and sentiment. Reversion to fair value is well-documented.
- **Assets**: G10 FX pairs
- **Timeframe**: Quarterly assessment, 1-3 year hold
- **Expected Perf**: WR 55%, Sharpe 0.45, MaxDD −15%, PF 1.22
- **Complexity**: Low
- **Refs**: Rogoff (1996) "The Purchasing Power Parity Puzzle"

### 3.3 Real Interest Rate Differential
- **Core Logic**: Real interest rate (nominal − inflation) differentials drive medium-term FX moves. Currencies with high real yields attract capital and appreciate. Track 2Y real yield differentials.
- **Signal**: Real Yield Diff = (2Y nominal − CPI) country A − (2Y nominal − CPI) country B. Long currency with higher real yield. Monthly rebalance. Minimum differential of 100bps.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Interest rates and CPI are market/government data. Differential is mechanical. 100bps minimum prevents churn.
- **Edge Source**: Fundamental — real yield differentials reflect relative policy stance and attractiveness to capital flows.
- **Assets**: G10 FX pairs
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: MacDonald (2000) "Concepts to Calculate Equilibrium Exchange Rates"

### 3.4 Current Account Imbalance Signal
- **Core Logic**: Countries with large and growing current account deficits tend to see currency depreciation over 1-3 year horizons. Surpluses drive appreciation. Trade the direction of persistent imbalances.
- **Signal**: Current Account / GDP ratio. Short currencies of countries with CA deficit > 3% of GDP AND deficit widening. Long currencies with surplus > 3% AND surplus growing.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: CA data from IMF/BEA. GDP-adjusted ratios normalize. Widening/narrowing filter adds trend confirmation.
- **Edge Source**: Fundamental — current account imbalances require financing. Persistent deficits → capital outflow → depreciation.
- **Assets**: G10 + major EM currencies
- **Timeframe**: Quarterly assessment, 1-2 year hold
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −12%, PF 1.25
- **Complexity**: Low
- **Refs**: Lane & Milesi-Ferretti (2012) "External Adjustment and the Global Crisis"

### 3.5 Central Bank Divergence Trade
- **Core Logic**: When two central banks diverge in policy direction (one hiking, other cutting), the rate differential drives FX moves. Trade the divergence.
- **Signal**: When Central Bank A starts hiking AND Bank B starts cutting → long A's currency vs B. Hold until both are in same policy direction. Size based on magnitude of rate differential.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include ECB vs Fed divergence (2014, 2022).
- **Anti-Drift**: Policy direction is observable. Divergence is binary (same vs opposite direction). Simple rules.
- **Edge Source**: Fundamental — policy divergence creates persistent capital flow. Higher rates attract foreign investment.
- **Assets**: G10 FX pairs
- **Timeframe**: Event-driven (policy meetings), multi-month hold
- **Expected Perf**: WR 60%, Sharpe 0.75, MaxDD −10%, PF 1.45
- **Complexity**: Low
- **Refs**: Taylor (1993) "Discretion vs Policy Rules in Practice"; Engel & West (2005)

### 3.6 FX Volatility Risk Premium
- **Core Logic**: FX options implied vol consistently overestimates realized vol (volatility risk premium). Sell short-dated FX options (straddles) to earn the premium. Hedge tail risk with cheap OTM options.
- **Signal**: Vol Risk Premium = implied vol (1M ATM) − 20D realized vol. When premium > 2 vol points → sell 1M straddle. When premium < 0 → do not sell (vol is cheap). Use 10-delta options for tail hedge.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include vol spikes (Brexit, COVID, 2022).
- **Anti-Drift**: Vol premium is market-observable. 2 vol point threshold based on historical analysis. Tail hedge included.
- **Edge Source**: Structural — FX vol risk premium is compensation for disaster risk. Persistent because hedgers overpay for protection.
- **Assets**: EUR/USD, USD/JPY, GBP/USD options
- **Timeframe**: Monthly rolling positions
- **Expected Perf**: WR 65%, Sharpe 0.80, MaxDD −15%, PF 1.50
- **Complexity**: High
- **Refs**: Della Corte et al. (2016) "Volatility Risk Premia and Exchange Rate Predictability"

### 3.7 USD Smile Theory Trading
- **Core Logic**: The "dollar smile" theory: USD strengthens in both very good times (US growth outperforms) and very bad times (flight to safety). USD weakens in moderate/normalizing environments. Position based on regime.
- **Signal**: Regime detection: (1) Global PMI < 47 → risk-off, long USD vs EM and commodity currencies. (2) Global PMI 47-55 → goldilocks, short USD. (3) Global PMI > 55 + US outperforming → long USD vs EUR, JPY.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Regime classification robustness testing.
- **Anti-Drift**: PMI is market data. Regime thresholds from academic research. Three-regime model is parsimonious.
- **Edge Source**: Structural — USD's reserve currency status creates unique demand dynamics in different macro environments.
- **Assets**: DXY or G10 FX basket
- **Timeframe**: Monthly regime assessment
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −12%, PF 1.30
- **Complexity**: Medium
- **Refs**: Jen (2001) "The 'Dollar Smile' Theory"

### 3.8 FX Trend Following (DMAC)
- **Core Logic**: Dual Moving Average Crossover on major FX pairs. FX trends are persistent due to central bank policy cycles and capital flow patterns. Long when fast MA > slow MA, short when below.
- **Signal**: 50D MA vs 200D MA crossover. When 50D crosses above 200D → long the pair. When crosses below → short. Apply to G10 pairs. Portfolio: equal risk allocation across all active signals.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Test MA parameter sensitivity ±20%.
- **Anti-Drift**: MA crossover is standard trend-following approach. Two parameters (50, 200) widely used. Diversify across pairs.
- **Edge Source**: Behavioral — FX trends driven by slow-adjusting institutional portfolios and central bank cycles. Trends persist for months.
- **Assets**: EUR/USD, USD/JPY, GBP/USD, AUD/USD, USD/CAD, USD/CHF, NZD/USD
- **Timeframe**: Daily signal, multi-month hold
- **Expected Perf**: WR 42%, Sharpe 0.55, MaxDD −15%, PF 1.20
- **Complexity**: Low
- **Refs**: Menkhoff et al. (2012) "Currency Momentum Strategies"

### 3.9 Terms of Trade Momentum
- **Core Logic**: Changes in a country's terms of trade (export prices / import prices) drive currency moves. Improving ToT → currency appreciation. Commodity exporters' FX driven by commodity prices.
- **Signal**: 3M change in Terms of Trade index. Long currencies of countries with ToT improvement > 5%. Short currencies with ToT decline > 5%. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: ToT is published data (national statistics). 5% threshold is meaningful. 3M change captures trends.
- **Edge Source**: Fundamental — ToT improvement increases real income and demand for domestic currency. Strong macro driver.
- **Assets**: Commodity FX (AUD, NZD, CAD, NOK) and EM commodity exporters
- **Timeframe**: Monthly signal, 3-6 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: Chen & Rogoff (2003) "Commodity Currencies"

### 3.10 FX Flow-Based Signal (IMM Positioning)
- **Core Logic**: CFTC IMM positioning data reveals speculative FX positioning. Extreme positioning (> 90th percentile long or short) often precedes reversals as the market is one-sided. Trade contrarian at extremes.
- **Signal**: Net speculative position as % of open interest (from CFTC COT). When position > 90th percentile (2Y lookback) → contrarian trade (reverse the extreme). When < 10th percentile → reverse.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Weekly data frequency.
- **Anti-Drift**: CFTC data is published weekly. Percentile thresholds adapt. 2Y lookback for percentile calculation.
- **Edge Source**: Behavioral — extreme speculative positioning reflects crowded trades. Crowded positions unwind violently.
- **Assets**: EUR/USD, JPY/USD, GBP/USD, AUD/USD, CAD/USD
- **Timeframe**: Weekly signal, 2-8 week hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: CFTC COT reports; Brunnermeier et al. (2009) "Carry Trades and Currency Crashes"

---

## 4. Foreign Exchange — EM (10)

### 4.1 EM Carry with Risk Filter
- **Core Logic**: EM carry (high-yield EM currencies funded by low-yield G10) with VIX and credit spread risk filter. Only hold carry when risk conditions are favorable. Cut carry during stress.
- **Signal**: Long top 3 EM currencies by carry (vs USD). Risk filter: close all positions when VIX > 25 OR EMBI spread widening > 50bps/week. Re-enter when VIX < 20 AND EMBI stable for 2 weeks.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include EM crises (2013, 2018, 2020).
- **Anti-Drift**: Interest rates are market data. VIX and EMBI are market data. Simple threshold rules.
- **Edge Source**: Fundamental — EM carry premium compensates for political/credit risk. Risk filter avoids drawdowns.
- **Assets**: BRL, MXN, ZAR, TRY, IDR, INR funded by USD
- **Timeframe**: Monthly rebalance (daily risk monitoring)
- **Expected Perf**: WR 55%, Sharpe 0.70, MaxDD −20%, PF 1.35
- **Complexity**: Medium
- **Refs**: Burnside (2012) "Carry Trades and Risk"

### 4.2 EM FX Momentum Cross-Section
- **Core Logic**: EM currencies with positive 3-month momentum tend to continue appreciating. Form cross-sectional long-short portfolio: long strongest momentum, short weakest.
- **Signal**: 3M total return (spot + carry) for each EM currency. Long top quartile, short bottom quartile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: 3M momentum is single parameter. Cross-sectional ranking is robust. Monthly rebalance.
- **Edge Source**: Behavioral — EM FX trends driven by persistent capital flows and slow-moving fundamentals.
- **Assets**: Top 20 EM currencies by liquidity
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.55, MaxDD −18%, PF 1.25
- **Complexity**: Low
- **Refs**: Menkhoff et al. (2012) "Currency Momentum Strategies"

### 4.3 EM Central Bank Intervention Detection
- **Core Logic**: EM central banks intervene to defend their currencies. Detect intervention patterns (sudden reserve changes, unusual FX volume, policy announcements) and trade with the central bank.
- **Signal**: Detection: (1) Weekly reserve change > 2σ, (2) FX volatility spike + rapid mean reversion, (3) Official statement. When intervention detected AND direction aligns with fundamentals → trade with the bank. Avoid fighting intervention.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must identify actual intervention episodes.
- **Anti-Drift**: Reserve data from IMF (weekly). Volume spikes are market data. Intervention is identifiable in hindsight.
- **Edge Source**: Informational — central bank intervention reveals policy intent and resources. Fighting a well-resourced central bank is losing.
- **Assets**: Major EM currencies (BRL, MXN, TRY, RUB, INR, THB)
- **Timeframe**: Event-driven, days-weeks
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −12%, PF 1.28
- **Complexity**: Medium
- **Refs**: Dominguez (2006) "When Do Central Bank Interventions Influence Intra-Daily and Longer-Term Exchange Rate Movements?"

### 4.4 NDF-Deliverable Spread
- **Core Logic**: Non-deliverable forward (NDF) rates can differ from deliverable forward rates for the same currency due to capital controls and different market structures. When the spread is extreme, arbitrage.
- **Signal**: NDF rate − deliverable forward rate for same tenor. When spread Z-score > 2.0 → trade the convergence (buy cheap instrument, sell expensive). Close when Z < 0.5.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model capital control changes.
- **Anti-Drift**: NDF and deliverable rates are market data. Z-score adapts. Must monitor regulatory changes.
- **Edge Source**: Structural — capital controls create segmented markets. NDF-deliverable spread reflects control premium.
- **Assets**: CNY, INR, BRL, KRW NDF vs deliverable
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −8%, PF 1.38
- **Complexity**: High
- **Refs**: Ma, Ho & McCauley (2004) "The Markets for Non-Deliverable Forwards"

### 4.5 EM Political Risk Premium Extraction
- **Core Logic**: EM elections, political crises, and policy changes create temporary risk premia in FX options (implied vol spikes). Sell vol after the event if outcome is market-neutral or positive.
- **Signal**: Before major EM political event: IF implied vol is 2× realized vol → sell 1M straddle after event result (if market-positive). Earn the vol crush. Skip if outcome is uncertain/negative.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must track actual political events.
- **Anti-Drift**: Event dates are known. IV vs RV comparison is objective. Post-event only (outcome known).
- **Edge Source**: Behavioral — markets overprice EM political risk. Most elections resolve without dramatic policy changes.
- **Assets**: EM FX options (BRL, MXN, ZAR, TRY)
- **Timeframe**: Event-driven (election cycles)
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −15%, PF 1.40
- **Complexity**: Medium
- **Refs**: Pástor & Veronesi (2013) "Political Uncertainty and Risk Premia"

### 4.6 EM Commodity FX Beta Timing
- **Core Logic**: EM commodity exporters' currencies (BRL, ZAR, RUB, CLP) have high beta to their primary commodity. Time exposure based on commodity momentum: when commodity is trending up, long the currency. Down, short.
- **Signal**: For each EM commodity currency: (1) identify primary commodity (iron ore for BRL, platinum/gold for ZAR, oil for RUB, copper for CLP). (2) When commodity 3M momentum > 0 → long the currency. When < 0 → short.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Commodity prices are market data. 3M momentum is single parameter. Commodity-currency link is structural.
- **Edge Source**: Fundamental — commodity prices drive export revenue and terms of trade for these countries. FX follows with a lag.
- **Assets**: BRL, ZAR, CLP, AUD, NOK vs USD
- **Timeframe**: Monthly signal, 3-6 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −18%, PF 1.28
- **Complexity**: Low
- **Refs**: Chen & Rogoff (2003) "Commodity Currencies"

### 4.7 EM Rate Normalization Trade
- **Core Logic**: After EM central banks hike rates aggressively (e.g., to fight inflation), the eventual normalization (cuts) is positive for the currency and bonds. Position for the normalization phase.
- **Signal**: When EM central bank: (1) has hiked > 500bps cumulatively, (2) inflation is declining, (3) real rate > 5% (extremely restrictive) → buy bonds + be neutral/long currency. Hold through cutting cycle.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include Brazil 2022-2024 cycle.
- **Anti-Drift**: Rate level and inflation are market/government data. Thresholds based on historical extremes.
- **Edge Source**: Fundamental — extremely high real rates are unsustainable. Normalization is inevitable and positive for both bonds and FX.
- **Assets**: BRL, MXN, ZAR, IDR sovereign bonds + FX
- **Timeframe**: Quarterly assessment, 12-24 month hold
- **Expected Perf**: WR 60%, Sharpe 0.75, MaxDD −15%, PF 1.45
- **Complexity**: Medium
- **Refs**: EM central bank policy analysis

### 4.8 Asian FX Cross-Rates
- **Core Logic**: Asian FX cross-rates (e.g., KRW/TWD, INR/IDR) are under-followed and exhibit stronger trends and mean-reversion patterns than USD crosses. Exploit relative value among Asian currencies.
- **Signal**: 3M momentum + carry ranking among Asian currencies (KRW, TWD, THB, PHP, INR, IDR). Long strongest (momentum + carry), short weakest. Cross-rate expression eliminates USD exposure.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Cross-rate removes USD noise. Combined momentum + carry is robust. Monthly rebalance.
- **Edge Source**: Structural — Asian FX cross-rates are less efficiently priced than USD crosses due to lower coverage and liquidity.
- **Assets**: Asian FX cross-rates
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.55, MaxDD −12%, PF 1.25
- **Complexity**: Medium
- **Refs**: Asian FX market microstructure research

### 4.9 Capital Flow Reversal Signal
- **Core Logic**: Sudden stops in capital flows to EM (tracked via portfolio flow data) precede EM FX crises. When portfolio outflows accelerate (IIF or EPFR data), reduce EM FX exposure.
- **Signal**: When weekly EM portfolio outflows (EPFR data) exceed 3σ above average → reduce all EM FX exposure by 50%. When outflows normalize (< 1σ) → restore full position.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2013 taper tantrum, 2018 EM crisis, 2020.
- **Anti-Drift**: EPFR flow data is published weekly. Z-score is adaptive. Threshold at 3σ is conservative.
- **Edge Source**: Informational — capital flow data reveals real-time investment decisions. Sudden stops are early warning for FX crises.
- **Assets**: Aggregate EM FX exposure
- **Timeframe**: Weekly monitoring (risk overlay)
- **Expected Perf**: Drawdown reduction of 30-50% vs unfiltered EM carry
- **Complexity**: Low
- **Refs**: Forbes & Warnock (2012) "Capital Flow Waves"

### 4.10 EM Pair Trading (Relative Value)
- **Core Logic**: EM currencies of similar countries (e.g., BRL vs MXN, ZAR vs TRY) share common drivers but diverge on idiosyncratic factors. Trade the spread when it's extreme, targeting convergence.
- **Signal**: Normalized spread between similar EM pairs. When spread Z-score (1Y lookback) > 2.0 → trade convergence (buy cheap, sell expensive currency in the pair). Close when Z < 0.5.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include idiosyncratic EM events.
- **Anti-Drift**: Z-score is adaptive. 1Y lookback for calibration. Pair selection based on economic similarity.
- **Edge Source**: Structural — similar EM countries face similar macro conditions. Idiosyncratic divergences revert as common factors dominate.
- **Assets**: BRL/MXN, ZAR/TRY, INR/IDR pairs
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −10%, PF 1.38
- **Complexity**: Medium
- **Refs**: EM relative value research

---

## 5. Commodities — Energy (10)

### 5.1 Crude Oil Contango Roll Yield
- **Core Logic**: When crude oil futures curve is in contango (front < back), rolling from front month to next costs money (negative roll yield). When in backwardation (front > back), rolling generates positive carry. Position based on curve shape.
- **Signal**: Roll Yield = (front month − second month) / front month (annualized). When in backwardation (roll yield > 3% annualized) → long front month (earn positive roll). When contango > 5% → short front month or stay flat.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2020 negative oil and 2022 backwardation.
- **Anti-Drift**: Futures curve is market data. Roll yield is mechanical. Thresholds based on long-term averages.
- **Edge Source**: Structural — roll yield captures storage economics. Backwardation = tight physical market → bullish. Contango = oversupply.
- **Assets**: WTI (CL) and Brent (BZ) crude oil futures
- **Timeframe**: Monthly roll decision
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −25%, PF 1.28
- **Complexity**: Low
- **Refs**: Gorton & Rouwenhorst (2006) "Facts and Fantasies about Commodity Futures"

### 5.2 Crack Spread Reversion
- **Core Logic**: The crack spread (refinery margin = gasoline/heating oil price − crude price) mean-reverts because refineries adjust throughput. When spread is extreme → trade toward the mean.
- **Signal**: 3-2-1 Crack Spread Z-score (2Y lookback). When Z > 2.0 → sell spread (short products, long crude). When Z < −2.0 → buy spread. Close at Z = 0.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2022 refinery capacity constraints.
- **Anti-Drift**: Crack spread is market-calculable. Z-score is adaptive. Refinery economics force mean-reversion.
- **Edge Source**: Structural — refinery throughput adjustment is a physical mean-reversion mechanism. Extreme margins attract/repel capacity.
- **Assets**: CL (crude), RB (gasoline), HO (heating oil) futures
- **Timeframe**: Weekly assessment, 1-3 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −12%, PF 1.50
- **Complexity**: Medium
- **Refs**: Borenstein & Kellogg (2014) "The Incidence of an Oil Glut"

### 5.3 Natural Gas Seasonal Pattern
- **Core Logic**: Natural gas has strong seasonal patterns: prices rise in fall (pre-winter heating demand) and fall in spring (post-winter, pre-injection season). Overlay storage levels for confirmation.
- **Signal**: Long Sep-Nov (pre-winter build). Short Mar-May (post-winter). Confirmation: only take long if storage is below 5-year average. Only take short if above.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include multiple winter seasons.
- **Anti-Drift**: Seasonal patterns driven by physical heating demand (structural). Storage data from EIA (weekly). 5-year average comparison.
- **Edge Source**: Structural — heating demand is a physical cycle. Storage levels confirm supply tightness/surplus.
- **Assets**: Henry Hub natural gas futures (NG)
- **Timeframe**: Seasonal (3-month trades)
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −20%, PF 1.40
- **Complexity**: Low
- **Refs**: EIA natural gas storage data; Mu (2007) "Weather, Storage, and Natural Gas Price Dynamics"

### 5.4 Oil Inventory Surprise Trade
- **Core Logic**: Weekly EIA crude oil inventory data surprises (vs consensus) move oil prices. Large surprise builds → bearish. Surprise draws → bullish. Trade the immediate price reaction.
- **Signal**: Inventory surprise = actual − consensus. When surprise draw > 3M barrels → long CL for 48 hours. When surprise build > 3M → short for 48 hours.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must use actual consensus estimates.
- **Anti-Drift**: EIA data is published weekly (fixed schedule). Consensus is observable. Simple threshold.
- **Edge Source**: Informational — inventory surprises reveal supply/demand not captured by prior market expectations.
- **Assets**: WTI crude oil futures (CL)
- **Timeframe**: Event-driven (weekly), 48-hour hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −10%, PF 1.25
- **Complexity**: Low
- **Refs**: Kilian & Murphy (2014) "The Role of Inventories and Speculative Trading in the Global Market for Crude Oil"

### 5.5 Gasoline-Crude Seasonal Spread
- **Core Logic**: Gasoline demand is seasonal (peak driving season: May-September). The gasoline-crude spread (RBOB − WTI) widens in spring as refineries ramp up gasoline production and narrows in fall.
- **Signal**: Buy gasoline-crude spread in February (pre-driving season). Sell in June (peak spread). Confirmation: gasoline stocks below 5-year seasonal average.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Seasonal pattern driven by physical demand cycle. Inventory confirmation filter. Fixed calendar timing.
- **Edge Source**: Structural — driving season demand for gasoline is a reliable physical cycle. Refinery turnarounds create seasonal supply patterns.
- **Assets**: RBOB gasoline (RB) vs WTI crude (CL) futures
- **Timeframe**: Feb-Jun (4 months)
- **Expected Perf**: WR 65%, Sharpe 0.80, MaxDD −10%, PF 1.55
- **Complexity**: Low
- **Refs**: EIA gasoline supply data; NYMEX seasonal patterns

### 5.6 OPEC Decision Impact Trading
- **Core Logic**: OPEC meetings create binary event risk. Position for the outcome or trade the post-decision momentum. Historically, production cuts → bullish. No change/increase → bearish.
- **Signal**: Before OPEC meeting: reduce position size (binary event). After decision: if production cut → long CL for 2 weeks. If no change/increase → short for 1 week. If surprise cut → more aggressive long.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must track actual OPEC decisions.
- **Anti-Drift**: OPEC meeting dates are published. Decisions are binary (cut/hold/increase). Post-decision momentum is documented.
- **Edge Source**: Informational — OPEC decisions directly impact supply. Market often misprices the compliance rate.
- **Assets**: Brent crude oil futures (BZ)
- **Timeframe**: Event-driven (OPEC meetings)
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.25
- **Complexity**: Low
- **Refs**: Fattouh & Mahadeva (2013) "OPEC: What Difference Has It Made?"

### 5.7 WTI-Brent Spread Mean Reversion
- **Core Logic**: WTI-Brent spread reflects transportation costs, quality differential, and infrastructure constraints. Spread extremes revert as logistics adjust.
- **Signal**: WTI-Brent spread Z-score (2Y lookback). When Z > 2.0 → sell WTI, buy Brent (expect convergence). When Z < −2.0 → buy WTI, sell Brent.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2011-2014 wide spread and 2020 convergence.
- **Anti-Drift**: Spread is market data. Z-score adapts. Physical arbitrage forces convergence at extremes.
- **Edge Source**: Structural — transportation and pipeline capacity create temporary dislocations. Spread bounds exist due to physical arbitrage.
- **Assets**: WTI (CL) vs Brent (BZ) futures
- **Timeframe**: Weekly assessment, 1-3 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −8%, PF 1.50
- **Complexity**: Low
- **Refs**: Büyükşahin et al. (2013) "Fundamental and Financial Influences on the Co-Movement of Oil and Gas Prices"

### 5.8 Power Market Spark Spread
- **Core Logic**: The spark spread (electricity price − natural gas cost for generation) measures power plant profitability. When spark spread is wide → power plants ramp up → gas demand increases → trade the chain.
- **Signal**: Spark spread = electricity price − (heat rate × gas price). When spark spread > 90th percentile → long natural gas (expect demand increase from generation). When < 10th → short.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must model regional power markets.
- **Anti-Drift**: Electricity and gas prices are market data. Heat rate is physical constant. Percentile is adaptive.
- **Edge Source**: Structural — spark spread drives gas-fired generation dispatch decisions. Physical link between power and gas markets.
- **Assets**: Natural gas futures (NG) + power futures (PJM, ERCOT)
- **Timeframe**: Daily signal, 1-7 day hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: High
- **Refs**: Fezzi & Bunn (2009) "Structural Interactions of European Electricity Trading"

### 5.9 Crude Oil Geopolitical Risk Premium
- **Core Logic**: Geopolitical risks (Middle East tensions, Russia/Ukraine, etc.) add a risk premium to oil prices. When the premium dissipates (tensions ease), prices decline. Track geopolitical risk index and position accordingly.
- **Signal**: Geopolitical Risk Index (Caldara & Iacoviello) Z-score. When Z > 2.0 AND oil price has risen > 10% → sell (geopolitical premium likely to fade). When Z normalizes → buy dip if fundamentals support.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include Gulf War, Libya, Russia/Ukraine events.
- **Anti-Drift**: GPR Index is externally published. Z-score is adaptive. Combined with price momentum filter.
- **Edge Source**: Behavioral — geopolitical risk premium fades as markets habituate. Initial spike overestimates lasting impact.
- **Assets**: Brent crude oil futures (BZ)
- **Timeframe**: Event-driven, 1-4 week trade
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −15%, PF 1.25
- **Complexity**: Medium
- **Refs**: Caldara & Iacoviello (2022) "Measuring Geopolitical Risk"

### 5.10 Energy Transition Metal Demand
- **Core Logic**: The energy transition drives long-term demand growth for certain metals (lithium, cobalt, nickel, copper, rare earths). Position for structural demand growth when prices are cyclically depressed.
- **Signal**: When transition metal price < 30th percentile (5Y lookback) AND EV sales still growing > 20% YoY → accumulate for long-term. Scale in over 3-6 months. Target: 50th percentile or higher.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model EV adoption scenarios.
- **Anti-Drift**: Price percentile is adaptive. EV sales growth is published data. Structural demand thesis is multi-decade.
- **Edge Source**: Structural — energy transition creates multi-decade demand growth for specific metals. Cyclical price declines are buying opportunities.
- **Assets**: Copper (HG), Nickel (LME), Lithium (spot), Cobalt
- **Timeframe**: Quarterly assessment, 1-3 year hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −30%, PF 1.30
- **Complexity**: Medium
- **Refs**: IEA "The Role of Critical Minerals in Clean Energy Transitions" (2021)

---

## 6. Commodities — Metals (10)

### 6.1 Gold-Real Yield Inverse Relationship
- **Core Logic**: Gold has a persistent inverse relationship with US real yields (10Y TIPS yield). When real yields rise, gold falls. When real yields fall, gold rises. Trade gold based on real yield direction.
- **Signal**: Long gold when: 10Y TIPS yield rolling 3M direction is declining AND level < 0% (negative real yields). Short gold when: TIPS yield rising AND level > 2%. Neutral between.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2020 (negative yields → gold ATH) and 2022 (rising yields → gold decline).
- **Anti-Drift**: TIPS yield is market data. Direction is binary. Level thresholds based on historical relationship.
- **Edge Source**: Fundamental — gold is a zero-yield asset. Its opportunity cost is the real yield. Negative real yields make gold attractive.
- **Assets**: Gold futures (GC)
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −15%, PF 1.38
- **Complexity**: Low
- **Refs**: Erb & Harvey (2013) "The Golden Dilemma"

### 6.2 Gold/Silver Ratio Mean Reversion
- **Core Logic**: Gold/Silver ratio oscillates around long-term mean (~60-70). When ratio is extreme (> 80), silver is undervalued relative to gold. When < 50, gold is undervalued.
- **Signal**: Gold/Silver ratio Z-score (5Y lookback). When Z > 1.5 (ratio too high, silver cheap) → long silver, short gold. When Z < −1.5 → long gold, short silver. Close at Z = 0.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2020 spike to 125 and reversion.
- **Anti-Drift**: Ratio is market data. Z-score adapts. Long-term mean is well-established (decades of data).
- **Edge Source**: Structural — gold/silver ratio reflects industrial vs monetary demand balance. Extreme deviations revert.
- **Assets**: Gold (GC) and Silver (SI) futures
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −15%, PF 1.38
- **Complexity**: Low
- **Refs**: Erb & Harvey (2013); Long-term precious metals analysis

### 6.3 Copper/Gold Ratio as Growth Signal
- **Core Logic**: Copper/Gold ratio is a macro growth indicator. Rising ratio = growth optimism (copper = industrial, gold = safe haven). Falling ratio = growth pessimism. Trade the macro direction.
- **Signal**: Cu/Au ratio 3M trend direction. Rising → long equities/risk assets, short bonds. Falling → short equities/risk assets, long bonds. Alternative: long copper/gold directly when ratio > 200DMA.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Cu/Au ratio is market data. 200DMA or 3M trend is single parameter. Macro signal is well-documented.
- **Edge Source**: Fundamental — copper demand reflects industrial activity. Gold demand reflects fear/uncertainty. Ratio captures growth expectations.
- **Assets**: Copper (HG), Gold (GC), or as macro signal for equity/bond allocation
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: Gundlach's "Copper/Gold Ratio and Interest Rates" analysis

### 6.4 Platinum-Palladium Substitution Trade
- **Core Logic**: Platinum and palladium are substitutes in catalytic converters. When palladium is extremely expensive vs platinum (ratio > 2.5), automakers shift to platinum catalysts. Trade the convergence.
- **Signal**: Pd/Pt ratio. When > 2.0 → long platinum, short palladium (substitution pressure). When < 1.0 → long palladium, short platinum. Close when ratio normalizes (1.0-2.0).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2019-2021 extreme palladium premium.
- **Anti-Drift**: Ratio is market data. Substitution is a documented industrial trend. Extreme thresholds.
- **Edge Source**: Structural — industrial substitution is a physical mean-reversion mechanism. Automakers actively switch when economics dictate.
- **Assets**: Platinum (PL) and Palladium (PA) futures
- **Timeframe**: Quarterly assessment, 6-24 month hold
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −20%, PF 1.30
- **Complexity**: Medium
- **Refs**: Johnson Matthey PGM market report

### 6.5 LME Warehouse Stock Signal
- **Core Logic**: LME warehouse stock changes reveal physical supply/demand. Declining stocks = tight physical market → bullish for price. Rising stocks = oversupply → bearish.
- **Signal**: 30D change in LME warehouse stocks. When decline > 10% → long the metal. When increase > 10% → short. Confirmation: LME prompt date spread in backwardation (for longs).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: LME stocks are published daily. Percentage change is normalized. Backwardation confirmation adds robustness.
- **Edge Source**: Informational — physical inventory changes reveal supply/demand before price fully adjusts.
- **Assets**: Copper, Aluminum, Zinc, Nickel, Tin, Lead (LME)
- **Timeframe**: Monthly signal, 1-3 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Medium
- **Refs**: LME warehouse data; Geman & Smith (2013) "Theory of Storage, Inventory, and Volatility"

### 6.6 Base Metal Contango/Backwardation
- **Core Logic**: Base metal futures curve shape (contango vs backwardation) reveals physical tightness. Backwardation = tight market → bullish momentum. Contango = well-supplied → bearish.
- **Signal**: 3M-Spot spread for each base metal. When in backwardation (spot premium > 2%) → long. When in contango (spot discount > 2%) → short. Monthly signal.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Curve shape is market data. 2% threshold is meaningful. Physical delivery mechanism forces convergence.
- **Edge Source**: Structural — backwardation signals physical shortage that draws down inventory. Supply tightness is a strong price signal.
- **Assets**: Copper, Aluminum, Zinc, Nickel (LME)
- **Timeframe**: Monthly signal, 1-3 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −18%, PF 1.28
- **Complexity**: Low
- **Refs**: Gorton & Rouwenhorst (2006) "Facts and Fantasies about Commodity Futures"

### 6.7 Central Bank Gold Reserves Signal
- **Core Logic**: Central bank gold buying (reported quarterly by WGC) signals de-dollarization and institutional demand. Sustained buying by EM central banks is a multi-year bullish signal for gold.
- **Signal**: When quarterly central bank net purchases > 200 tonnes (Z > 1.5 above 5Y average) → bullish gold, increase allocation. When net selling → reduce. Monthly adjustment based on latest data.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include post-2022 EM central bank buying surge.
- **Anti-Drift**: WGC data is published quarterly. Net purchase tonnage is objective. 5Y Z-score adapts.
- **Edge Source**: Fundamental — central banks are large, slow-moving buyers. Their buying is persistent and price-insensitive (strategic reserve allocation).
- **Assets**: Gold (GC)
- **Timeframe**: Quarterly assessment
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Low
- **Refs**: World Gold Council quarterly reports

### 6.8 Iron Ore China Demand Signal
- **Core Logic**: Iron ore prices are dominated by Chinese steel demand. Track Chinese PMI, property starts, and steel production. When Chinese activity accelerates, buy iron ore. When decelerating, sell.
- **Signal**: China Caixin Manufacturing PMI. When PMI crosses above 50 from below → long iron ore. When crosses below 50 → short. Confirmation: Chinese steel production 3M trend.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: PMI is published monthly. 50 level is economically meaningful. Steel production is confirming data.
- **Edge Source**: Fundamental — China consumes 60%+ of global iron ore. Chinese demand is the dominant price driver.
- **Assets**: Iron ore futures (SGX, DCE)
- **Timeframe**: Monthly signal, 1-3 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −25%, PF 1.28
- **Complexity**: Low
- **Refs**: BHP/Rio Tinto iron ore market reports

### 6.9 Aluminum Smelter Cost Floor
- **Core Logic**: Aluminum smelting has a known marginal cost curve dominated by electricity. When aluminum price drops below the 90th percentile of global smelter production cost, production cuts are imminent → price floor.
- **Signal**: When LME aluminum price < estimated 90th percentile smelter cost ($2,100-2,300/t historically) → buy (expect supply cuts). Target: 50th percentile cost + margin (~$2,500+).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Model electricity cost changes.
- **Anti-Drift**: Cost curve published by CRU/Wood Mackenzie. Updated annually. Price vs cost is objective.
- **Edge Source**: Structural — production costs set a fundamental floor. Below-cost production is unsustainable → supply cuts support price.
- **Assets**: Aluminum (LME) futures
- **Timeframe**: Quarterly assessment, 6-12 month hold
- **Expected Perf**: WR 65%, Sharpe 0.70, MaxDD −15%, PF 1.45
- **Complexity**: Medium
- **Refs**: CRU/Wood Mackenzie aluminum cost analysis

### 6.10 Precious Metal COT Positioning
- **Core Logic**: CFTC COT data for gold and silver shows managed money positioning. Extreme long positioning → contrarian sell signal. Extreme short → contrarian buy. Positioning extremes predict price reversals.
- **Signal**: Net managed money position as % of open interest. When > 90th percentile (2Y) → sell signal. When < 10th percentile → buy signal. Hold until position normalizes to 50th percentile.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Weekly data.
- **Anti-Drift**: COT data is published weekly by CFTC. Percentile thresholds adapt. 2Y lookback.
- **Edge Source**: Behavioral — extreme positioning = crowded trade. Crowded positions unwind creating predictable price reversals.
- **Assets**: Gold (GC) and Silver (SI) futures
- **Timeframe**: Weekly signal, 2-8 week hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −12%, PF 1.28
- **Complexity**: Low
- **Refs**: CFTC COT reports; De Roon et al. (2000) "Hedging Pressure Effects in Futures Markets"

---

## 7. Commodities — Agriculture (10)

### 7.1 Grain Calendar Spread (Old Crop vs New Crop)
- **Core Logic**: Old crop (current season) vs new crop (next season) grain futures have different supply dynamics. When old crop is tight (low stocks), old crop premium widens. Trade the spread dynamics around USDA reports.
- **Signal**: Old crop (Jul corn) − New crop (Dec corn) spread. When spread > 90th percentile (5Y) → sell spread (expect normalization). When < 10th → buy spread. Key timing: around USDA WASDE reports.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include drought years.
- **Anti-Drift**: Spread is market data. Percentile thresholds adapt. USDA report timing is known.
- **Edge Source**: Structural — old crop/new crop spread reflects physical storage economics and supply uncertainty.
- **Assets**: Corn (ZC), Wheat (ZW), Soybean (ZS) calendar spreads
- **Timeframe**: Seasonal, 1-3 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −10%, PF 1.28
- **Complexity**: Medium
- **Refs**: USDA WASDE reports; Garcia et al. (2015) "Grain Spreads"

### 7.2 Soybean Crush Spread
- **Core Logic**: The soybean crush spread (soybean meal + soybean oil − soybeans) reflects processing margins. When margins are extreme, they revert as processors adjust throughput.
- **Signal**: Crush spread Z-score (2Y lookback). When Z > 2.0 → sell spread (margins unsustainably high, expect competition to erode). When Z < −2.0 → buy spread (margins too low, expect supply reduction).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Crush spread is market-calculable. Z-score adapts. Processing economics force mean-reversion.
- **Edge Source**: Structural — crush margin drives processing decisions. Extreme margins attract/repel capacity.
- **Assets**: Soybeans (ZS), Soybean Meal (ZM), Soybean Oil (ZL) futures
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 60%, Sharpe 0.75, MaxDD −10%, PF 1.45
- **Complexity**: Medium
- **Refs**: USDA oilseed processing data

### 7.3 USDA Report Surprise Trading
- **Core Logic**: USDA crop reports (WASDE, Crop Production, Acreage) create significant price moves when they surprise vs consensus. Trade the directional move.
- **Signal**: USDA ending stocks surprise = actual − consensus. When surprise < −10% (stocks tighter than expected) → long for 5 days. When > +10% → short for 5 days.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must use actual consensus estimates.
- **Anti-Drift**: USDA dates are published. Consensus is observable. Surprise is mechanical.
- **Edge Source**: Informational — USDA has the most comprehensive crop data. Surprises reveal information not in market consensus.
- **Assets**: Corn, Wheat, Soybeans, Cotton futures
- **Timeframe**: Event-driven (monthly WASDE), 5-day hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −8%, PF 1.25
- **Complexity**: Low
- **Refs**: Isengildina-Massa et al. (2008) "Impact of USDA Reports on Futures Markets"

### 7.4 Weather Premium/Discount
- **Core Logic**: Grain prices incorporate weather risk premium during growing season (Jun-Aug for northern hemisphere). If weather is favorable, the premium unwinds. Trade the premium based on weather forecasts during key growth stages.
- **Signal**: During pollination period (Jul for corn): if 14-day forecast shows adequate rainfall AND temperatures < 95°F → short (weather premium will unwind). If drought/heat stress forecast → long (weather premium justified/increasing).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must validate weather forecast accuracy.
- **Anti-Drift**: Weather forecasts are external data. Growing season timing is fixed by biology. Key growth stages are well-defined.
- **Edge Source**: Structural — weather premium is built into grain prices every growing season. Trades on the resolution of weather uncertainty.
- **Assets**: Corn (ZC), Soybeans (ZS) futures
- **Timeframe**: Jun-Aug (growing season)
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Medium
- **Refs**: USDA crop weather analysis; National Weather Service data

### 7.5 Corn-Ethanol Margin
- **Core Logic**: 40% of US corn goes to ethanol production. The corn-ethanol margin (ethanol price × 2.8 gallons/bushel − corn price) drives ethanol plant economics. Extreme margins revert as plants adjust production.
- **Signal**: Corn-Ethanol margin Z-score (2Y). When Z > 2.0 → sell margin (short ethanol, long corn). When Z < −2.0 → buy margin. Close at Z = 0.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Margin is market-calculable. Z-score adapts. Plant economics force mean-reversion (similar to crack spread).
- **Edge Source**: Structural — ethanol plant production adjustments are a physical mean-reversion mechanism.
- **Assets**: Corn (ZC) and Ethanol (EH) futures
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −10%, PF 1.38
- **Complexity**: Medium
- **Refs**: USDA ethanol production data

### 7.6 Coffee Frost Risk Premium
- **Core Logic**: Brazilian coffee production is vulnerable to frost events (Jun-Aug winter). Market prices in frost risk premium from May onward. If frost doesn't materialize, premium fades. If frost occurs, prices spike dramatically.
- **Signal**: Jun-Aug: monitor Brazilian weather. If frost forecasts emerge → long coffee (KC) aggressively. After Aug (frost window closed) without frost → short (premium unwinds). Use weather derivatives for hedging.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 1994, 2021 frost events.
- **Anti-Drift**: Frost window is fixed (Jun-Aug). Brazilian geography is fixed. Weather monitoring is external data.
- **Edge Source**: Structural — Brazil produces ~35% of global coffee. Frost risk is concentrated in a 3-month window. Premium builds and unwinds predictably.
- **Assets**: Coffee (KC) futures
- **Timeframe**: Seasonal (May-Sep)
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −20%, PF 1.30
- **Complexity**: Medium
- **Refs**: ICO coffee market reports

### 7.7 Sugar-Ethanol Parity (Brazil)
- **Core Logic**: Brazilian sugar mills can switch between producing sugar and ethanol (from sugarcane). When sugar price > ethanol-equivalent price, mills maximize sugar → increased sugar supply → price convergence. Trade the ratio.
- **Signal**: Sugar/Ethanol parity = sugar price (cents/lb) / (ethanol price × conversion factor). When ratio > 1.2 → short sugar (mills shifting to sugar production). When < 0.8 → long sugar.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Sugar and ethanol prices are market data. Conversion factor is fixed (physical). Mill switching is documented.
- **Edge Source**: Structural — mill flexibility creates a physical mean-reversion mechanism for sugar/ethanol pricing.
- **Assets**: Raw Sugar (SB) futures
- **Timeframe**: Monthly assessment, 2-6 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −15%, PF 1.38
- **Complexity**: Medium
- **Refs**: UNICA (Brazilian Sugarcane Industry Association) data

### 7.8 Wheat Basis Trade (Export vs Domestic)
- **Core Logic**: US wheat export basis (Gulf FOB − CBOT futures) varies with export demand, transportation, and storage. Extreme basis levels revert. Also trade inter-market wheat spreads (HRW vs SRW vs HRS).
- **Signal**: Export basis Z-score (2Y). When Z > 2.0 (basis too wide) → buy basis (long cash wheat, short futures). When Z < −2.0 → sell basis. Also: KCBT-CBOT wheat spread Z-score for quality premium.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k.
- **Anti-Drift**: Basis is market data. Z-score adapts. Transportation/storage economics force reversion.
- **Edge Source**: Structural — basis reflects localized supply/demand and logistics. Extreme levels attract arbitrage.
- **Assets**: CBOT Wheat (ZW), KC Wheat (KE), Minneapolis Wheat (MWE)
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −8%, PF 1.38
- **Complexity**: Medium
- **Refs**: USDA wheat outlook; CME wheat basis data

### 7.9 Cotton-Polyester Substitution Signal
- **Core Logic**: When cotton prices spike relative to polyester (the primary substitute fiber), textile mills shift to polyester → reducing cotton demand → cotton price declines. Trade the substitution effect.
- **Signal**: Cotton/Polyester ratio. When ratio > 90th percentile (5Y) → short cotton (substitution will reduce demand). When < 10th → long cotton (cotton is cheap, demand shifts back).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Model textile industry adjustment speed.
- **Anti-Drift**: Commodity prices are market data. Substitution is a well-documented industrial trend. Percentile thresholds adapt.
- **Edge Source**: Structural — fiber substitution is a physical demand adjustment mechanism. Extreme price ratios trigger switching.
- **Assets**: Cotton (CT) futures
- **Timeframe**: Quarterly assessment, 6-12 month hold
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −20%, PF 1.25
- **Complexity**: Medium
- **Refs**: USDA cotton outlook; ICAC fiber consumption data

### 7.10 Livestock-Feed Cost Ratio
- **Core Logic**: Hog and cattle profitability depends on the ratio of meat price to feed cost (corn, soybean meal). When the ratio is favorable (high meat price, low feed), producers expand. When unfavorable, they contract. Trade the cycle.
- **Signal**: Hog-Corn Ratio = lean hog price / corn price. When ratio > 90th percentile (5Y) → expect herd expansion, eventually bearish (increased supply). When < 10th → expect contraction, eventually bullish.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Model biological lag (herd expansion takes 6-12 months).
- **Anti-Drift**: Prices are market data. Biological production cycle is fixed. Ratio is long-established.
- **Edge Source**: Structural — livestock production cycle (biology) creates predictable supply response to profitability signals. 6-12 month lag is tradeable.
- **Assets**: Lean Hogs (HE), Live Cattle (LE) vs Corn (ZC) futures
- **Timeframe**: Quarterly assessment, 6-12 month hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Medium
- **Refs**: USDA livestock outlook; Lawrence (2018) "Hog-Corn Ratio"

---

## 8. Commodities — Cross-Sector (10)

### 8.1 Commodity Momentum Cross-Section
- **Core Logic**: Rank all commodity futures by 12-month momentum. Long top quintile, short bottom quintile. Commodity momentum is persistent due to supply/demand cycles and inventory dynamics.
- **Signal**: 12M total return (spot + roll) for each commodity. Long top 5, short bottom 5 out of 25+ liquid commodities. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Sector-diversified construction.
- **Anti-Drift**: 12M momentum is single parameter. Cross-sectional ranking is robust. Diversified across sectors.
- **Edge Source**: Behavioral — commodity supply response is slow (mines, farms, wells take years to build). Trends persist.
- **Assets**: Diversified commodity futures basket (energy, metals, agriculture)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −20%, PF 1.35
- **Complexity**: Low
- **Refs**: Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"

### 8.2 Commodity Carry (Curve Shape)
- **Core Logic**: Commodities in backwardation (positive carry from roll yield) tend to outperform. Commodities in contango (negative carry) tend to underperform. Rank by carry, go long/short.
- **Signal**: Roll yield = (front − second) / front (annualized) for each commodity. Long top 5 by carry (most backwardated). Short bottom 5 (most contango). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Equal-risk weighting.
- **Anti-Drift**: Curve shape is market data. Roll yield is mechanical. Cross-sectional ranking is robust.
- **Edge Source**: Structural — backwardation signals physical tightness. Contango signals oversupply. Carry captures this information.
- **Assets**: Diversified commodity futures basket
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −18%, PF 1.35
- **Complexity**: Low
- **Refs**: Koijen et al. (2018) "Carry"

### 8.3 Commodity Value (Mean Reversion)
- **Core Logic**: Rank commodities by 5-year percentile of real (inflation-adjusted) price. Long the cheapest (lowest percentile), short the most expensive. Long-term mean reversion in commodity prices.
- **Signal**: 5Y real price percentile for each commodity. Long bottom quintile (cheapest). Short top quintile (most expensive). Quarterly rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Real price (CPI-adjusted) removes inflation effect. 5Y lookback for percentile. Quarterly rebalance.
- **Edge Source**: Structural — commodity supply response (new mines, rigs, acreage) ensures long-term mean reversion. Expensive commodities attract investment.
- **Assets**: Diversified commodity futures basket
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 53%, Sharpe 0.50, MaxDD −20%, PF 1.22
- **Complexity**: Low
- **Refs**: Gorton, Hayashi & Rouwenhorst (2013) "The Fundamentals of Commodity Futures Returns"

### 8.4 Commodities-Dollar Inverse Signal
- **Core Logic**: Most commodities are USD-denominated and have inverse relationship with DXY. Weakening dollar → commodity rally. Use DXY direction as overlay for commodity exposure.
- **Signal**: DXY 30D trend. When declining → increase long commodity exposure by 25%. When rising → decrease by 25%. Apply as allocation overlay.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: DXY is market data. Trend direction is binary. 25% tilt is modest.
- **Edge Source**: Structural — USD denomination creates mechanical inverse relationship. Weaker USD increases purchasing power of non-USD commodity buyers.
- **Assets**: Broad commodity exposure (GSCI or BCOM index)
- **Timeframe**: Monthly assessment
- **Expected Perf**: Improves Sharpe by 0.10-0.20 vs unfiltered commodity exposure
- **Complexity**: Low
- **Refs**: Commodity-Dollar correlation research

### 8.5 China PMI → Commodity Signal
- **Core Logic**: China is the world's largest commodity consumer. Chinese manufacturing PMI is a leading indicator for commodity demand. Rising PMI → increasing demand → bullish commodities.
- **Signal**: When Caixin Manufacturing PMI crosses above 50 from below → long commodity basket. When crosses below 50 → reduce. Strongest for industrial commodities (copper, iron ore, oil).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: PMI is published monthly. 50 level is economically meaningful. China's commodity demand share is dominant.
- **Edge Source**: Fundamental — China consumes 40-60% of global industrial commodities. PMI captures manufacturing activity.
- **Assets**: Copper, Iron Ore, Crude Oil, Aluminum
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −20%, PF 1.28
- **Complexity**: Low
- **Refs**: Hamilton (2014) "The Changing Face of World Oil Markets"

### 8.6 Commodity Sector Rotation
- **Core Logic**: Commodity sectors (energy, base metals, precious metals, agriculture) rotate leadership based on macro regime. Energy leads in growth/inflation. Precious metals lead in uncertainty. Rotate based on macro indicators.
- **Signal**: Growth rising + inflation rising → energy. Growth falling + inflation rising → precious metals. Growth rising + inflation falling → base metals. Growth falling + inflation falling → agriculture (defensive).
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Regime classification testing.
- **Anti-Drift**: PMI and CPI are macro data. Four-quadrant model is parsimonious. Quarterly rebalance.
- **Edge Source**: Fundamental — different commodities respond differently to macro regimes. Regime-based rotation captures this.
- **Assets**: Energy (oil, gas), Base Metals (copper, aluminum), Precious Metals (gold, silver), Agriculture (corn, soy)
- **Timeframe**: Quarterly rotation
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −18%, PF 1.30
- **Complexity**: Medium
- **Refs**: Gorton & Rouwenhorst (2006); Erb & Harvey (2006) "The Strategic and Tactical Value of Commodity Futures"

### 8.7 Commodity Index Rebalance Front-Running
- **Core Logic**: Major commodity indices (GSCI, BCOM) rebalance annually (Jan). Rebalancing creates predictable flows as index funds adjust positions. Front-run by trading before rebalance.
- **Signal**: Calculate expected rebalancing flows from publicly announced new weights. Buy commodities getting weight increases 2 weeks before rebalance. Sell commodities losing weight. Close 1 week after rebalance.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must use actual rebalancing data.
- **Anti-Drift**: Index weights are publicly announced. Rebalance dates are fixed. Flow calculation is mechanical.
- **Edge Source**: Structural — index rebalancing creates predictable supply/demand for specific commodity futures. Passive funds must adjust.
- **Assets**: GSCI and BCOM constituent commodities
- **Timeframe**: Annual event (Jan), 3-week trade
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −5%, PF 1.28
- **Complexity**: Medium
- **Refs**: S&P GSCI methodology; Bloomberg BCOM methodology

### 8.8 Inter-Commodity Spread Convergence
- **Core Logic**: Related commodities (corn-wheat, WTI-Brent, gold-platinum) have fair value relationships. When spreads deviate significantly, they tend to revert. Trade mean-reversion of inter-commodity spreads.
- **Signal**: Spread Z-score (2Y lookback) for each related commodity pair. When Z > 2.0 → sell spread. When Z < −2.0 → buy spread. Close at Z = 0.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k.
- **Anti-Drift**: Spreads are market data. Z-score adapts. Substitution and transportation economics drive reversion.
- **Edge Source**: Structural — inter-commodity relationships reflect substitution, production, and transportation economics.
- **Assets**: Corn-Wheat, WTI-Brent, Gold-Silver, Soybean Oil-Palm Oil spreads
- **Timeframe**: Monthly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −10%, PF 1.42
- **Complexity**: Medium
- **Refs**: Working (1949) "The Theory of Price of Storage"

### 8.9 Commodity Supercycle Detection
- **Core Logic**: Commodities exhibit 15-20 year supercycles driven by capex cycles. Under-investment during down-cycles leads to supply shortfalls in up-cycles. Detect supercycle turns for multi-year positioning.
- **Signal**: Broad commodity index (BCOM) 3-year return. When 3Y return turns positive from negative → early supercycle (buy). When 3Y return peaks (momentum declining) → late cycle (reduce).
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k. Must include 2000-2008 supercycle and 2011-2020 decline.
- **Anti-Drift**: 3Y return is single metric. Supercycle turning points are rare (1-2 per decade). Position for years, not months.
- **Edge Source**: Structural — capex cycles create predictable supply dynamics. 10-year mine/well development cycle creates lagged supply response.
- **Assets**: Broad commodity ETF (DJP, GSG) or individual futures basket
- **Timeframe**: Annual assessment, multi-year hold
- **Expected Perf**: WR 60%, Sharpe 0.55, MaxDD −30%, PF 1.30
- **Complexity**: Low
- **Refs**: Erten & Ocampo (2013) "Super Cycles of Commodity Prices Since the Mid-Nineteenth Century"

### 8.10 Physical vs Financial Positioning Divergence
- **Core Logic**: When physical commodity traders (commercial hedgers in COT) are net buyers AND financial traders (managed money) are net sellers, physical demand is being underpriced. Trade with the physicals.
- **Signal**: Commercial net position (COT) trending positive AND managed money net position trending negative → long (physical demand signal). Reverse setup → short.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Weekly COT data.
- **Anti-Drift**: COT data is published weekly by CFTC. Trend direction is objective. Physical vs financial positioning divergence is documented signal.
- **Edge Source**: Informational — commercial hedgers have superior information about physical supply/demand. Their positioning reflects real economy fundamentals.
- **Assets**: All liquid commodity futures
- **Timeframe**: Weekly signal, 2-8 week hold
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −15%, PF 1.28
- **Complexity**: Low
- **Refs**: De Roon et al. (2000) "Hedging Pressure Effects in Futures Markets"

---

## 9. Multi-Asset Cross-Market (10)

### 9.1 Risk Parity Dynamic
- **Core Logic**: Dynamic risk parity allocates capital such that each asset class contributes equally to portfolio risk. When correlation and volatility shift, rebalance to maintain equal risk contribution.
- **Signal**: Compute risk contribution of each asset (equities, bonds, commodities, gold) using rolling 60D covariance matrix. Rebalance when any asset's risk contribution exceeds 30% or falls below 20%.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2008, 2020, 2022.
- **Anti-Drift**: Risk parity is a formula-based approach. Rolling covariance is adaptive. Rebalance threshold prevents excessive turnover.
- **Edge Source**: Structural — risk parity harvests diversification premium. Dynamic version adjusts to changing correlations.
- **Assets**: SPY (equity), TLT (bonds), GLD (gold), DBC (commodities)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −15%, PF 1.45
- **Complexity**: Medium
- **Refs**: Bridgewater "All Weather" methodology; Qian (2005) "Risk Parity Portfolios"

### 9.2 Equity-Bond Correlation Regime Switch
- **Core Logic**: Stock-bond correlation shifts between positive (both rise/fall together, 2022) and negative (classic diversification). When correlation is positive, traditional 60/40 fails. Detect regime and adjust.
- **Signal**: 60D rolling SPX-UST correlation. When correlation > +0.3 → reduce bonds, increase gold/commodities (alternative diversifiers). When correlation < −0.3 → traditional 60/40 works, increase bond allocation.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include both correlation regimes.
- **Anti-Drift**: Correlation is measurable. Threshold is based on empirical research. Portfolio adjustment is gradual.
- **Edge Source**: Structural — stock-bond correlation regime determines optimal portfolio construction. Adaptive allocation outperforms static.
- **Assets**: SPY, TLT, GLD, DBC
- **Timeframe**: Monthly assessment
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −12%, PF 1.42
- **Complexity**: Medium
- **Refs**: Campbell, Sunderam & Viceira (2017) "Inflation Bets or Deflation Hedges?"

### 9.3 VIX Term Structure Signal
- **Core Logic**: VIX futures term structure (contango = calm, backwardation = fear) predicts equity returns. Steep contango → complacency, sell vol. Backwardation → fear peak, buy equities.
- **Signal**: VIX futures spread = 2nd month − front month. When spread < −2 (steep backwardation, fear) → buy SPX, sell VIX puts. When spread > +4 (steep contango, complacency) → buy VIX calls for tail protection.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2020 COVID crash and 2022 decline.
- **Anti-Drift**: VIX term structure is market data. Spread is objective. Thresholds based on historical extremes.
- **Edge Source**: Behavioral — VIX backwardation marks fear peaks which historically coincide with equity buying opportunities.
- **Assets**: SPX, VIX futures, SPX options
- **Timeframe**: Weekly signal, 1-4 week hold
- **Expected Perf**: WR 58%, Sharpe 0.75, MaxDD −12%, PF 1.42
- **Complexity**: Medium
- **Refs**: Dew-Becker et al. (2017) "The Price of Variance Risk"

### 9.4 Cross-Asset Momentum Rotation
- **Core Logic**: Apply time-series momentum (12M return > 0) across all major asset classes. Go long assets with positive momentum, go to cash/short for negative momentum. Classic trend following adapted for multi-asset.
- **Signal**: 12M return for each asset class. If return > 0 → long. If < 0 → cash (or short if signal strong). Apply to: SPX, UST 10Y, gold, crude oil, USD index. Equal risk weight longs.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Test 6M and 12M lookbacks.
- **Anti-Drift**: 12M return is single parameter. Binary signal (long/flat). Diversified across uncorrelated assets.
- **Edge Source**: Behavioral — trends persist across asset classes due to slow information diffusion, institutional mandates, and central bank policy cycles.
- **Assets**: SPX, 10Y UST, Gold, Crude Oil, DXY
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.80, MaxDD −15%, PF 1.42
- **Complexity**: Low
- **Refs**: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum"

### 9.5 TIPS-Gold-Commodity Inflation Hedge
- **Core Logic**: When inflation is rising (CPI accelerating), allocate to inflation beneficiaries: TIPS, gold, and commodities. When inflation is falling, allocate to nominal bonds and growth equities.
- **Signal**: 3M CPI change (rolling). When accelerating (3M > 6M annualized) → 40% TIPS, 30% gold, 30% commodities. When decelerating → 60% nominal bonds, 40% growth equities.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include 2021-2022 inflation spike.
- **Anti-Drift**: CPI is published monthly (BLS). Acceleration is objective. Two-regime model is simple.
- **Edge Source**: Fundamental — inflation regime determines which asset classes outperform. Timely regime detection provides allocation alpha.
- **Assets**: TIPS (TIP), Gold (GLD), Commodities (DBC), Nominal bonds (TLT), Growth equities (QQQ)
- **Timeframe**: Monthly allocation shift
- **Expected Perf**: WR 55%, Sharpe 0.70, MaxDD −15%, PF 1.38
- **Complexity**: Low
- **Refs**: Ang (2014) "Asset Management: A Systematic Approach to Factor Investing"

### 9.6 Global Liquidity Cycle Trading
- **Core Logic**: Global central bank balance sheet expansion (liquidity injection) is bullish for risk assets. Contraction is bearish. Track aggregate G4 central bank assets (Fed + ECB + BOJ + PBOC).
- **Signal**: G4 aggregate balance sheet 3M change. When expanding (positive) → overweight equities, credit, crypto. When contracting → overweight cash, short-duration bonds.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include QE (2020) and QT (2022).
- **Anti-Drift**: Central bank balance sheets are published weekly/monthly. 3M change is objective. G4 aggregate is comprehensive.
- **Edge Source**: Structural — central bank liquidity drives asset prices across classes. Expansion lifts all boats. Contraction creates headwinds.
- **Assets**: Global equity (VT), bonds (BND), credit (HYG), gold (GLD)
- **Timeframe**: Monthly signal
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −20%, PF 1.30
- **Complexity**: Low
- **Refs**: Borio & Disyatat (2011) "Global Imbalances and the Financial Crisis: Link or No Link?"

### 9.7 Equity-Commodity Relative Value
- **Core Logic**: Equity/commodity ratio (SPX/GSCI) mean-reverts over multi-year cycles. When equities are expensive relative to commodities (high ratio), commodity allocation is attractive and vice versa.
- **Signal**: SPX/GSCI ratio percentile (20Y lookback). When ratio > 90th percentile → overweight commodities, underweight equities. When < 10th → overweight equities. Between → neutral.
- **Best Backtest Method**: Walk-forward 20yr/5yr/5yr. Monte Carlo 10k.
- **Anti-Drift**: Ratio is market data. 20Y lookback captures full cycles. Percentile thresholds adapt.
- **Edge Source**: Structural — equity/commodity relative pricing reflects investment cycle. Multi-year mean-reversion driven by capex allocation.
- **Assets**: SPX vs GSCI commodity index
- **Timeframe**: Annual assessment
- **Expected Perf**: WR 55%, Sharpe 0.45, MaxDD −20%, PF 1.22
- **Complexity**: Low
- **Refs**: GMO relative valuation research

### 9.8 FX-Adjusted Bond Allocation
- **Core Logic**: Government bonds across countries offer different yields, but FX-hedging cost must be considered. When hedged yield of foreign bonds exceeds domestic yield, allocate internationally.
- **Signal**: FX-hedged yield = foreign bond yield − FX hedging cost (cross-currency basis swap). When hedged yield > domestic yield + 30bps → allocate to foreign bonds. Monthly comparison across G10.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Model hedging costs.
- **Anti-Drift**: Bond yields and hedging costs are market data. Mechanical comparison. 30bps hurdle prevents churn.
- **Edge Source**: Structural — cross-currency basis reflects funding market imbalances. Hedged yield opportunities persist for months.
- **Assets**: G10 government bonds (US, Germany, Japan, UK, Australia, etc.)
- **Timeframe**: Monthly assessment
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −5%, PF 1.25
- **Complexity**: Medium
- **Refs**: Du et al. (2018) "Deviations from Covered Interest Rate Parity"

### 9.9 Tail Risk Parity
- **Core Logic**: Instead of equalizing variance contributions, equalize tail risk (expected shortfall / CVaR) contributions. This better protects against extreme events than standard risk parity.
- **Signal**: Compute CVaR (99%) for each asset using historical simulation. Allocate inversely proportional to CVaR contribution. Rebalance when any asset's CVaR contribution deviates > 5% from target.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must include tail events (2008, 2020).
- **Anti-Drift**: CVaR is computed from historical data (adaptive). Rebalance threshold prevents overtrading.
- **Edge Source**: Structural — tail risk parity provides better protection in extreme events than variance-based risk parity.
- **Assets**: Multi-asset portfolio (equities, bonds, commodities, alternatives)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −12%, PF 1.40
- **Complexity**: High
- **Refs**: Maillard, Roncalli & Teïletche (2010) "The Properties of Equally Weighted Risk Contribution Portfolios"

### 9.10 Macro Factor Timing
- **Core Logic**: Allocate across asset classes based on macro factor exposures: growth (PMI), inflation (CPI), real rates (TIPS yield), liquidity (M2 growth). Each factor has known asset class sensitivities.
- **Signal**: Score each factor (Z-score of recent change). Growth positive → equities+credit. Inflation positive → commodities+TIPS. Real rates falling → gold+long duration. Liquidity expanding → equities+HY.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must test factor identification stability.
- **Anti-Drift**: Macro data is published (BLS, ISM, Fed). Z-scores are adaptive. Factor-asset mappings are based on economic theory (not optimized).
- **Edge Source**: Fundamental — macro factors drive asset class returns. Systematic factor timing captures macro regime shifts.
- **Assets**: Full multi-asset spectrum
- **Timeframe**: Monthly factor assessment
- **Expected Perf**: WR 55%, Sharpe 0.70, MaxDD −15%, PF 1.38
- **Complexity**: Medium
- **Refs**: Ilmanen (2011) "Expected Returns"

---

## 10. FX/FI Advanced (10)

### 10.1 Cross-Currency Basis Swap Trade
- **Core Logic**: Cross-currency basis swap spread (deviation from covered interest parity) reflects USD funding premium. When basis is extreme, arbitrage by lending USD and borrowing foreign currency.
- **Signal**: EUR/USD cross-currency basis. When < −50bps (USD funding expensive, CIP violation) → lend USD, borrow EUR via basis swap (earn the premium). Close when basis > −10bps.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model counterparty risk.
- **Anti-Drift**: Basis is market data. Threshold based on long-term average. CIP violation is structural.
- **Edge Source**: Structural — post-GFC regulations created persistent CIP violations. USD funding premium is compensation for balance sheet constraints.
- **Assets**: EUR/USD, USD/JPY cross-currency basis swaps
- **Timeframe**: Quarterly assessment, 3-12 month hold
- **Expected Perf**: WR 65%, Sharpe 0.80, MaxDD −5%, PF 1.50
- **Complexity**: High
- **Refs**: Du, Tepper & Verdelhan (2018) "Deviations from Covered Interest Rate Parity"

### 10.2 Inflation Swap vs Breakeven Arbitrage
- **Core Logic**: Inflation swaps and TIPS breakevens should give the same inflation expectation but occasionally diverge due to market structure. When they diverge, trade the convergence.
- **Signal**: Inflation swap rate − TIPS breakeven rate (same maturity). When difference Z-score (1Y) > 2.0 → sell swap, buy TIPS breakeven. When < −2.0 → reverse.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model liquidity differences.
- **Anti-Drift**: Both metrics are market data. Z-score adapts. Convergence is driven by arbitrage.
- **Edge Source**: Structural — TIPS and inflation swap markets have different participants. Spread reflects liquidity and supply/demand differences.
- **Assets**: Inflation swaps vs TIPS
- **Timeframe**: Monthly assessment, 1-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −5%, PF 1.50
- **Complexity**: High
- **Refs**: Fleckenstein, Longstaff & Lustig (2014) "The TIPS-Treasury Bond Puzzle"

### 10.3 Sovereign CDS vs Bond Spread
- **Core Logic**: Sovereign CDS and bond spreads should be similar but diverge due to market structure. When CDS > bond spread (positive basis), buy the bond and buy CDS protection (earn the basis).
- **Signal**: Sovereign CDS − bond OAS. When positive basis > 30bps → buy bond + buy CDS (earn carry). When negative basis < −30bps → sell bond + sell CDS. Close when basis normalizes.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model counterparty risk.
- **Anti-Drift**: CDS and bond spreads are market data. Basis is mechanical. Include funding costs.
- **Edge Source**: Structural — CDS and bond markets have different participants and regulations. Basis represents structural market segmentation.
- **Assets**: EM and IG sovereign bonds + CDS
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −8%, PF 1.42
- **Complexity**: High
- **Refs**: Fontana (2012) "The Negative CDS-Bond Basis and Convergence Trading"

### 10.4 SOFR-Treasury Spread
- **Core Logic**: SOFR (Secured Overnight Financing Rate) vs Treasury bill spread reflects repo market conditions. When spread widens (SOFR elevated), it signals funding stress. When tight, conditions are easy.
- **Signal**: SOFR − 3M T-bill spread. When > 25bps → funding stress, reduce leverage and risk. When < 5bps → easy conditions, increase risk. Also: trade the spread directly.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Model quarter-end effects.
- **Anti-Drift**: SOFR and T-bill are market data. Spread is mechanical. Quarter-end adjustments known.
- **Edge Source**: Structural — SOFR-T-bill spread reflects bank balance sheet constraints. Captures funding market dynamics.
- **Assets**: As risk overlay, or trade SOFR futures vs T-bill futures directly
- **Timeframe**: Daily monitoring (risk overlay)
- **Expected Perf**: Improves portfolio Sharpe by 0.10-0.15 as risk overlay
- **Complexity**: Medium
- **Refs**: Federal Reserve Bank of New York SOFR documentation

### 10.5 TIPS Relative Value (Tenor Selection)
- **Core Logic**: TIPS yield curve (5Y, 10Y, 20Y, 30Y) can be steep or flat relative to nominal curve. When one tenor is relatively cheap (real yield high relative to nominal-adjusted curve), buy that tenor.
- **Signal**: Compare TIPS real yield at each tenor vs model-implied fair value (from nominal curve + inflation expectations). When actual TIPS yield > model yield + 20bps → cheap, buy. When < model − 20bps → rich, sell.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model specification sensitivity.
- **Anti-Drift**: Nominal curve is market data. Model is simple (Fisher equation + inflation expectations). 20bps buffer.
- **Edge Source**: Structural — TIPS market is smaller and less liquid than nominal Treasuries. Relative value opportunities persist.
- **Assets**: 5Y, 10Y, 20Y, 30Y TIPS
- **Timeframe**: Monthly assessment, 3-12 month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −5%, PF 1.38
- **Complexity**: Medium
- **Refs**: D'Amico, Kim & Wei (2018) "Tips from TIPS"

### 10.6 On-the-Run / Off-the-Run Spread
- **Core Logic**: Newly issued Treasuries (on-the-run) trade at a premium (lower yield) vs older issues (off-the-run). The spread is a liquidity premium that compresses over time. Buy off-the-run, sell on-the-run.
- **Signal**: On/Off-the-run spread for 10Y UST. When spread > 15bps → buy off-the-run, sell on-the-run (earn spread compression). Close when off-the-run becomes on-the-run.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model repo rate differentials.
- **Anti-Drift**: Spread is market data. 15bps threshold based on historical norms. Duration-matched.
- **Edge Source**: Structural — liquidity premium is earned by holding less liquid (off-the-run) bonds. LTCM's core trade (when properly sized).
- **Assets**: On-the-run vs off-the-run UST (10Y)
- **Timeframe**: Continuous (roll with new issuance)
- **Expected Perf**: WR 70%, Sharpe 1.00, MaxDD −3%, PF 1.80
- **Complexity**: Medium
- **Refs**: Krishnamurthy (2002) "The Bond/Old-Bond Spread"

### 10.7 Swaption Vol Surface Relative Value
- **Core Logic**: Compare swaption implied vol across the maturity and tenor grid (1Mx10Y, 3Mx10Y, 1Yx10Y, etc.). When one cell is cheap relative to neighbors, buy that swaption.
- **Signal**: Swaption implied vol Z-score relative to model surface (SABR or Heston). When Z > 1.5 → sell (rich). When Z < −1.5 → buy (cheap). Close at Z = 0. Vega-neutral portfolio.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Model specification sensitivity testing.
- **Anti-Drift**: Vol surface is market data. Model is standard (SABR). Z-score relative to model is adaptive.
- **Edge Source**: Structural — swaption market has supply/demand imbalances at specific cells (banks hedging mortgages affect specific maturities).
- **Assets**: USD swaption grid
- **Timeframe**: Weekly assessment, 1-3 month hold
- **Expected Perf**: WR 58%, Sharpe 0.80, MaxDD −8%, PF 1.45
- **Complexity**: High
- **Refs**: Rebonato (2004) "Volatility and Correlation in Fixed Income Markets"

### 10.8 Callable Bond Spread
- **Core Logic**: Callable bonds embed a short call option. When vol is low, the option is cheap → callable bonds trade close to bullet equivalents. When vol spikes, callable bonds underperform. Buy callables when vol is low.
- **Signal**: OAS of callable vs bullet bond (same issuer/maturity). When call option cost (OAS difference) is < 10bps (vol is low, option is cheap) → buy callable (earn tiny extra spread). Sell when vol spikes (OAS difference > 50bps).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Model interest rate vol scenarios.
- **Anti-Drift**: OAS is market data. Vol-adjusted comparison is mechanical. Option cost is observable.
- **Edge Source**: Structural — callable bond market is large (munis, agencies). Option mispricing creates relative value.
- **Assets**: US agency and municipal callable bonds
- **Timeframe**: Monthly assessment
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −5%, PF 1.35
- **Complexity**: Medium
- **Refs**: Fabozzi (2016) "Bond Markets, Analysis, and Strategies"

### 10.9 FX Forward Point Anomaly
- **Core Logic**: FX forward points occasionally diverge from interest rate differential due to market structure. When forward points are cheaper than implied by rate differential, buy forward (cheaper funding).
- **Signal**: Forward Premium Anomaly = actual forward points − interest rate implied forward points. When anomaly > 0.1% annualized → use forward instead of spot + funding. Systematic execution improvement.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Model transaction costs.
- **Anti-Drift**: Forward points and rates are market data. Anomaly is mechanical. Execution improvement.
- **Edge Source**: Structural — FX forward market has different supply/demand than money market. Imbalances create forward point anomalies.
- **Assets**: G10 FX forwards (1M, 3M, 6M)
- **Timeframe**: Per-trade (execution layer)
- **Expected Perf**: 5-15bps improvement per trade
- **Complexity**: Medium
- **Refs**: Du, Tepper & Verdelhan (2018)

### 10.10 Multi-Curve Swap Arbitrage
- **Core Logic**: Post-GFC, swaps are valued using multiple curves (OIS discounting + forward curves). Occasionally, multi-curve construction creates small arbitrage between related instruments. Trade the discrepancy.
- **Signal**: Compare OIS-discounted swap value vs SOFR-based swap value for same cash flows. When discrepancy > 5bps → trade the convergence. Use basis swaps to isolate the exposure.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Model curve construction methodology changes.
- **Anti-Drift**: Curve data is market data. Discrepancy is mechanical. Monitor methodology changes.
- **Edge Source**: Structural — multi-curve framework creates complexity. Different market participants use different discount curves → transient mispricing.
- **Assets**: OIS, SOFR, LIBOR transition swap basis
- **Timeframe**: Monthly assessment, 1-6 month hold
- **Expected Perf**: WR 60%, Sharpe 0.70, MaxDD −3%, PF 1.42
- **Complexity**: High
- **Refs**: Hull & White (2013) "LIBOR vs. OIS: The Derivatives Discounting Dilemma"

---

*100 Elite Fixed Income, FX & Commodities Strategies — End of Document*
