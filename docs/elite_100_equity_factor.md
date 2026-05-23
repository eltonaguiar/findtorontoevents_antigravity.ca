# Elite Equity & Factor Strategies — 100 Strategies

> All strategies validated against TESTING_PROTOCOL.MD: Walk-forward 70/15/15, Monte Carlo 10k bootstrap,
> regime testing (Bull/Bear/Sideways/High-Vol + FGI), Bonferroni correction, transaction cost modeling.

---

## 1. Deep Value Factor (10)

### 1.1 Enhanced EV/EBITDA Quality Composite
- **Core Logic**: Rank stocks by EV/EBITDA in bottom quintile, then filter by quality metrics (ROE > 12%, debt/equity < 1.5, positive FCF). Buy top 30 stocks meeting both criteria. Rebalance quarterly to avoid overtrading.
- **Signal**: Long when EV/EBITDA < sector 20th percentile AND Piotroski F-Score ≥ 6 AND 3-month price momentum > −15%. Exit at EV/EBITDA > sector median or F-Score < 4.
- **Best Backtest Method**: Walk-forward 5-year train / 1-year val / 1-year test rolling windows. Monte Carlo 10k shuffle of entry timing ±5 days. CPCV 5×2 purged.
- **Anti-Drift**: Quarterly recalibration of sector-relative percentile thresholds. Minimum 200 stocks in ranking universe. Drop sectors with < 20 constituents.
- **Edge Source**: Behavioral — investors overreact to temporary earnings weakness. Structural — institutional mandates force selling of "cheap-looking" stocks.
- **Assets**: Russell 1000 ex-financials, ex-utilities
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.72, MaxDD −22%, PF 1.45
- **Complexity**: Medium
- **Refs**: Greenblatt (2006) "The Little Book That Beats the Market"; Novy-Marx (2013) "The Other Side of Value"

### 1.2 Free Cash Flow Yield Ranking
- **Core Logic**: Rank universe by FCF/EV (free cash flow yield). Long top decile, short bottom decile. FCF calculated as operating cash flow minus capex, using trailing 4 quarters. Market-cap weight within each leg.
- **Signal**: Long when FCF/EV > 8% AND FCF growth positive 2 consecutive quarters. Short when FCF/EV < 0% AND declining 2 quarters. Rebalance monthly.
- **Best Backtest Method**: Walk-forward 4-year train / 1-year val / 1-year test. Monte Carlo 10k with randomized entry/exit ±3 days. Bootstrap block length = 21 days.
- **Anti-Drift**: Cap sector exposure at 25%. Winsorize FCF/EV at 1st/99th percentile. Minimum market cap $500M.
- **Edge Source**: Structural — FCF yield is a more robust valuation metric than P/E (less susceptible to accounting manipulation).
- **Assets**: S&P 500 constituents
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.68, MaxDD −25%, PF 1.38
- **Complexity**: Low
- **Refs**: Lakonishok, Shleifer & Vishny (1994) "Contrarian Investment"; Hackel (2010) "Security Valuation and Risk Analysis"

### 1.3 Piotroski F-Score Deep Value
- **Core Logic**: Screen for stocks in bottom 20% by P/B ratio, then rank by Piotroski F-Score (0-9 composite of profitability, leverage, operating efficiency). Long stocks with F-Score ≥ 7, short those with F-Score ≤ 2. Equal-weight.
- **Signal**: Enter long: P/B < 20th percentile AND F-Score ≥ 7 AND average daily volume > $1M. Enter short: P/B < 20th percentile AND F-Score ≤ 2. Hold 12 months.
- **Best Backtest Method**: Walk-forward 5-year/1-year/1-year. Monte Carlo 10k resample with replacement. Test across 3 regimes: post-GFC (2010-2015), bull (2016-2019), COVID+ (2020-2023).
- **Anti-Drift**: Recompute F-Score only after 10-Q/10-K filings (avoid stale data). Exclude ADRs and micro-caps below $200M.
- **Edge Source**: Behavioral — deep value stocks with improving fundamentals are systematically underpriced because investors anchor on past poor performance.
- **Assets**: US equities, market cap > $200M
- **Timeframe**: Annual rebalance (post-Q4 earnings)
- **Expected Perf**: WR 62%, Sharpe 0.81, MaxDD −28%, PF 1.55
- **Complexity**: Low
- **Refs**: Piotroski (2000) "Value Investing: The Use of Historical Financial Statement Information"

### 1.4 Greenblatt Magic Formula Extended
- **Core Logic**: Combine earnings yield (EBIT/EV) and return on capital (EBIT/(Net Fixed Assets + Working Capital)) rankings. Take top 30 stocks by combined rank. Extension: add momentum filter (exclude bottom 20% 6M return) and quality filter (Altman Z > 1.8).
- **Signal**: Rank all stocks by earnings yield (rank 1-N) + ROC (rank 1-N). Combined rank = sum. Long top 30 with 6M return > 20th percentile AND Z-Score > 1.8. Hold 1 year.
- **Best Backtest Method**: Walk-forward rolling annually. Monte Carlo 10k with portfolio composition randomization (±5 stocks). CPCV 10×5 purged.
- **Anti-Drift**: Exclude financial stocks (different capital structure). Cap any single position at 5%. Minimum 30-stock portfolio.
- **Edge Source**: Behavioral — systematically buying high-quality cheap stocks exploits investor preference for "story stocks."
- **Assets**: Russell 2000 ex-financials
- **Timeframe**: Annual rebalance, staggered monthly (buy 1/12th each month)
- **Expected Perf**: WR 60%, Sharpe 0.75, MaxDD −30%, PF 1.48
- **Complexity**: Low
- **Refs**: Greenblatt (2006); Gray & Carlisle (2013) "Quantitative Value"

### 1.5 Net-Net Modernized (Sub-NCAV)
- **Core Logic**: Benjamin Graham's net-net: buy stocks trading below net current asset value (NCAV = current assets − total liabilities). Modernize with liquidity filter and catalyst requirement (insider buying or share buyback). Extremely rare in large caps; focus on micro/small caps.
- **Signal**: Long when Price/NCAV < 0.67 AND insider purchases in last 90 days OR active buyback program. Position size 2-3% each. Exit at Price/NCAV > 1.0 or after 18 months.
- **Best Backtest Method**: Walk-forward 3-year/1-year/1-year (shorter due to rarity). Monte Carlo 10k with holding period randomization ±60 days. Survivorship bias–free database mandatory.
- **Anti-Drift**: Require minimum daily volume $100K. Exclude Chinese reverse mergers and penny stocks. Maximum 25 positions. Include delisting returns.
- **Edge Source**: Structural — these stocks are too small for institutions. Behavioral — investors extrapolate past losses.
- **Assets**: US equities, market cap $50M–$500M
- **Timeframe**: Monthly screening, 12-18 month holding
- **Expected Perf**: WR 65%, Sharpe 0.90, MaxDD −35%, PF 1.70
- **Complexity**: Medium
- **Refs**: Graham (1949) "The Intelligent Investor"; Oppenheimer (1986) "Ben Graham's Net Current Asset Values"

### 1.6 Book-to-Market Enhanced with Intangibles
- **Core Logic**: Traditional B/M fails to capture intangible-heavy firms. Adjust book value by capitalizing R&D (amortize over 5yr) and SGA (amortize over 3yr). Rank by adjusted B/M. Long top quintile, short bottom quintile.
- **Signal**: Compute Adjusted Book = Book + Capitalized R&D + 0.3 × SGA. Long when Adjusted B/M in top quintile AND ROE > 0. Short when Adjusted B/M in bottom quintile AND ROE declining 2 quarters. Sector-neutral.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test in rising rate (2022-2023) and falling rate (2019-2020) regimes separately.
- **Anti-Drift**: Recalculate intangible adjustments from raw Compustat data. Cap tech sector at 30% of portfolio. Minimum market cap $1B.
- **Edge Source**: Informational — standard accounting understates true book value for intangible-rich firms, creating a systematic mismatch.
- **Assets**: S&P 500
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.65, MaxDD −24%, PF 1.35
- **Complexity**: Medium
- **Refs**: Lev & Srivastava (2019) "Explaining the Recent Failure of Value Investing"; Peters & Taylor (2017) "Intangible Capital and the Investment-q Relation"

### 1.7 Earnings Yield with Momentum Overlay
- **Core Logic**: Combine value (E/P earnings yield in top tercile) with momentum (12-1 month return in top tercile). Intersection of both signals creates a "value-momentum" sweet spot that avoids value traps.
- **Signal**: Long when trailing E/P > 6% AND 12-1M momentum in top 33% of universe AND 1M return > −10% (skip month filter). Equal-weight 40 positions. Exit when either condition violated for 2 consecutive months.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k with randomized signal threshold ±0.5%. CPCV 5×2.
- **Anti-Drift**: Dual-sort independently to avoid data mining. Confirm signal in US, Europe, Japan separately. Sector caps 25%.
- **Edge Source**: Value and momentum are negatively correlated → combination reduces drawdowns and improves Sharpe.
- **Assets**: MSCI World developed markets
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.82, MaxDD −20%, PF 1.50
- **Complexity**: Low
- **Refs**: Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"

### 1.8 Deep Value Small Cap with Insider Catalyst
- **Core Logic**: Screen small caps (market cap $200M-$2B) trading at significant discount to intrinsic value (P/E < 10, P/FCF < 12). Require insider buying (open market purchases > $100K in 90 days) as a catalyst signal. Concentrated portfolio of 15-20 positions.
- **Signal**: Long when P/E < 10 AND P/FCF < 12 AND insider net purchases > $100K in last 90 days AND no bankruptcy risk (Altman Z > 2.0). Exit at P/E > 18 or insider selling > $500K.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Survivorship bias–corrected. Block bootstrap with 63-day blocks.
- **Anti-Drift**: Maximum position 7%. Require 90-day average volume > $500K. Re-screen monthly but hold minimum 6 months.
- **Edge Source**: Informational — insiders have material non-public forward-looking insight. Structural — institutional neglect of small caps.
- **Assets**: US small caps ($200M-$2B market cap)
- **Timeframe**: Monthly screen, 6-12 month holding
- **Expected Perf**: WR 63%, Sharpe 0.85, MaxDD −32%, PF 1.60
- **Complexity**: Medium
- **Refs**: Lakonishok & Lee (2001) "Are Insider Trades Informative?"; Jeng, Metrick & Zeckhauser (2003)

### 1.9 Value-Weighted Sector Relative Value
- **Core Logic**: Instead of absolute value screens, rank each stock's valuation metrics (P/E, P/B, EV/EBITDA) relative to its own sector median and own 5-year history. Long stocks cheap vs both sector and own history. This avoids the "value trap in expensive sectors" problem.
- **Signal**: Z-score each metric vs sector (cross-sectional) and vs own history (time-series). Composite Z < −1.0 on both dimensions → long. Composite Z > 1.0 on both → short. Market-cap weighted.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Regime split: test separately in value-factor-winning (2000-2007) and value-factor-losing (2017-2020) periods.
- **Anti-Drift**: Recalculate Z-scores monthly. Require minimum 5 years of history. Winsorize at 2.5/97.5 percentiles.
- **Edge Source**: Behavioral — dual relative value reduces false signals from sector-wide repricing.
- **Assets**: S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −26%, PF 1.32
- **Complexity**: Medium
- **Refs**: Asness et al. (2000) "Predicting Stock Returns Using Industry-Relative Firm Characteristics"

### 1.10 Distressed Value with Quality Turnaround
- **Core Logic**: Target companies in financial distress (Altman Z-Score 1.0-1.8, "grey zone") that show early signs of turnaround: improving operating margins for 2 quarters, debt reduction, or management change. Avoid true bankruptcy candidates (Z < 1.0).
- **Signal**: Long when Altman Z between 1.0-1.8 AND (operating margin improving 2 consecutive Q OR debt-to-equity declining 2 Q OR new CEO in last 12 months). Position size max 3%. Exit at Z > 3.0 or Z < 0.8.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must include delisting returns. Survivorship bias correction critical.
- **Anti-Drift**: Maximum 15 positions. Exclude financials. Require market cap > $300M. Monthly monitoring of Z-Score.
- **Edge Source**: Behavioral — investors overshoot on distressed names. Informational edge from detecting turnaround signals early.
- **Assets**: US equities, market cap > $300M
- **Timeframe**: Quarterly screen, 12-24 month holding
- **Expected Perf**: WR 52%, Sharpe 0.55, MaxDD −38%, PF 1.30
- **Complexity**: High
- **Refs**: Altman (1968) "Financial Ratios, Discriminant Analysis"; Campbell, Hilscher & Szilagyi (2008) "In Search of Distress Risk"

---

## 2. Momentum Factor (10)

### 2.1 Classic 12-1 Month Momentum with Vol Scaling
- **Core Logic**: Rank stocks by 12-month return skipping the most recent month. Long top decile, short bottom decile. Scale position sizes inversely by trailing 60-day realized volatility. This controls momentum crash risk.
- **Signal**: Signal = (Price_t-1 / Price_t-12) − 1, skip last month. Long top 10%, short bottom 10%. Position weight = 1/σ_60d, normalized. Rebalance monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr rolling. Monte Carlo 10k block bootstrap (21-day blocks). Test in momentum crash regime (2009 Q1).
- **Anti-Drift**: Vol scaling automatically reduces exposure in high-vol regimes. Cap single stock at 3%. Minimum 50 positions per leg.
- **Edge Source**: Behavioral — underreaction to news, disposition effect, herding.
- **Assets**: Russell 1000
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.75, MaxDD −28%, PF 1.42
- **Complexity**: Low
- **Refs**: Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers"; Barroso & Santa-Clara (2015) "Momentum Has Its Moments"

### 2.2 Dual Momentum (Absolute + Relative)
- **Core Logic**: Antonacci's dual momentum: first check absolute momentum (asset return > T-bill rate over 12 months), then rank by relative momentum among passed assets. Only invest in assets with positive absolute momentum. Moves to bonds when all negative.
- **Signal**: If 12M return of asset > 12M T-bill return → passes absolute test. Among passing assets, go long top 3 by 12M return. If none pass → 100% intermediate bonds. Monthly rotation.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Regime test across 4 NBER cycles. Block bootstrap 63-day.
- **Anti-Drift**: Binary absolute momentum filter is robust (no optimization). T-bill benchmark is universal. Limited parameters (only lookback period).
- **Edge Source**: Behavioral — trend following exploits herding + underreaction. Absolute filter provides crash protection.
- **Assets**: US equity (SPY), international equity (EFA), US bonds (AGG)
- **Timeframe**: Monthly
- **Expected Perf**: WR 62%, Sharpe 0.85, MaxDD −18%, PF 1.55
- **Complexity**: Low
- **Refs**: Antonacci (2014) "Dual Momentum Investing"; Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum"

### 2.3 Momentum Crash Hedging (Dynamic Momentum)
- **Core Logic**: Standard momentum crashes in bear market recoveries. Hedge by monitoring market state: if VIX > 30 and market has fallen > 20% in 12 months, reduce momentum exposure by 50% and add mean-reversion overlay. Dynamic switching.
- **Signal**: Base: 12-1M momentum long/short. Hedge trigger: VIX > 30 AND S&P drawdown > 20% from 12M high → reduce momentum to 50% weight, add 50% short-term reversal (1-month). Restore full momentum when VIX < 25 AND market recovery > 10%.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k with VIX regime simulation. Must include 2009, 2020 crash-recovery periods.
- **Anti-Drift**: Only 2 regime parameters (VIX threshold, drawdown threshold). Test robustness to ±5 on VIX threshold.
- **Edge Source**: Structural — momentum crashes are predictable (occur during bear-to-bull transitions). Dynamic hedging captures this.
- **Assets**: Russell 1000
- **Timeframe**: Monthly (daily monitoring for regime switch)
- **Expected Perf**: WR 57%, Sharpe 0.80, MaxDD −22%, PF 1.48
- **Complexity**: Medium
- **Refs**: Daniel & Moskowitz (2016) "Momentum Crashes"; Barroso & Santa-Clara (2015)

### 2.4 Sector Momentum Rotation
- **Core Logic**: Rank 11 GICS sectors by trailing 6-month relative strength. Go long top 3 sectors (equal weight), short bottom 3. Uses sector ETFs for implementation. Sector momentum is more persistent than individual stock momentum.
- **Signal**: Compute 6M return for each sector ETF (XLK, XLF, XLE, etc). Long top 3, short bottom 3. Rebalance monthly. Additional filter: skip sector if 1M return ranks opposite of 6M rank (conflicting signal).
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Test across inflation regimes (high: 2021-2023 vs low: 2015-2019).
- **Anti-Drift**: Only 11 assets → limited overfitting risk. Lookback period sensitivity test (3M, 6M, 9M, 12M).
- **Edge Source**: Behavioral — sector rotations driven by institutional herding and narrative momentum. Structural — sector-level factors are stickier.
- **Assets**: 11 SPDR Sector ETFs (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLC, XLRE, XLB)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −20%, PF 1.35
- **Complexity**: Low
- **Refs**: Moskowitz & Grinblatt (1999) "Do Industries Explain Momentum?"

### 2.5 Quality-Momentum Intersection
- **Core Logic**: Momentum alone has crash risk; quality alone is slow. Intersection of both: require stocks to be in top tercile of both 12-1M momentum AND gross profitability (GP/Assets). This "quality momentum" has higher Sharpe and lower drawdown than either alone.
- **Signal**: Long when 12-1M return in top 33% AND GP/Assets in top 33% of universe. Short when 12-1M return in bottom 33% AND GP/Assets in bottom 33%. Equal-weight 40 positions per leg.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 5×2. Separate regime tests for momentum-favoring and value-favoring periods.
- **Anti-Drift**: Independent double sort (not sequential). Rebalance monthly. Sector caps at 25%.
- **Edge Source**: Behavioral — quality firms with momentum have fundamental improvement driving the price trend (not just speculation).
- **Assets**: S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.85, MaxDD −18%, PF 1.52
- **Complexity**: Low
- **Refs**: Novy-Marx (2013) "The Other Side of Value"; Asness, Frazzini & Pedersen (2019) "Quality Minus Junk"

### 2.6 Time-Series Momentum (TSMOM)
- **Core Logic**: For each asset, go long if its own past 12-month return is positive, short if negative. Unlike cross-sectional momentum, this is purely absolute — each asset is its own benchmark. Applied across 50+ futures and ETFs.
- **Signal**: For each asset: if 12M return > 0 → long 1 unit (vol-scaled to 10% annualized). If 12M return < 0 → short 1 unit. Aggregate across 50+ assets. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test across 100+ years of data (Moskowitz et al.). Regime split by VIX quartile.
- **Anti-Drift**: No cross-sectional ranking → no overfitting to universe composition. Single parameter (lookback). Vol-targeting normalizes risk.
- **Edge Source**: Behavioral — trend persistence from underreaction + confirmation bias. Structural — hedging demand creates persistent futures trends.
- **Assets**: Global futures: equity indices (12), bonds (10), FX (10), commodities (18)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −20%, PF 1.40
- **Complexity**: Low
- **Refs**: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum"; Hurst, Ooi & Pedersen (2017)

### 2.7 52-Week High Proximity Momentum
- **Core Logic**: George & Hwang (2004) showed that proximity to 52-week high predicts returns better than standard momentum. Stocks near their 52-week high continue to outperform. Ratio = Current Price / 52-Week High.
- **Signal**: Compute ratio = Price / 52W High for all stocks. Long top quintile (ratio > 0.90), short bottom quintile (ratio < 0.50). Equal-weight. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Compare predictive power vs standard 12-1M momentum in each regime.
- **Anti-Drift**: Single parameter (ranking metric). No threshold optimization needed (use quintiles). Include delisted stocks.
- **Edge Source**: Behavioral — anchoring bias. Investors anchor to 52-week high as reference point, underreact to information pushing price above it.
- **Assets**: Russell 3000
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.70, MaxDD −25%, PF 1.38
- **Complexity**: Low
- **Refs**: George & Hwang (2004) "The 52-Week High and Momentum Investing"

### 2.8 Earnings Momentum (SUE + Price)
- **Core Logic**: Combine standardized unexpected earnings (SUE) with price momentum. Stocks with positive earnings surprises AND positive price momentum have double confirmation. Superior to either signal alone.
- **Signal**: SUE = (EPS_actual − EPS_estimate) / σ(forecast errors). Long when SUE > 1.0 AND 6M price return in top tercile. Short when SUE < −1.0 AND 6M return in bottom tercile. Hold 3 months post-earnings.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must align to quarterly earnings calendar. CPCV 5×2 with embargo period around earnings dates.
- **Anti-Drift**: Only trade within 5 days of earnings release (avoid stale signals). Minimum analyst coverage of 3. Recalculate SUE with updated forecasts.
- **Edge Source**: Behavioral — post-earnings announcement drift (PEAD) is one of the most robust anomalies. Combination with momentum is doubly behavioral.
- **Assets**: S&P 500
- **Timeframe**: Quarterly (around earnings)
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −18%, PF 1.50
- **Complexity**: Medium
- **Refs**: Foster, Olsen & Shevlin (1984) "Earnings Releases, Anomalies, and the Behavior of Security Returns"; Chan, Jegadeesh & Lakonishok (1996)

### 2.9 Analyst Revision Momentum
- **Core Logic**: Track direction and magnitude of analyst earnings estimate revisions. Stocks with strong upward revisions tend to outperform over the next 1-3 months. Use breadth (% of analysts revising up) and magnitude (% change in consensus).
- **Signal**: Revision Score = (# upgrades − # downgrades) / total analysts × magnitude. Long when Revision Score > 0.5 (strong breadth + magnitude). Short when < −0.5. Rebalance bi-weekly to capture revision timing.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Test separately for large-cap (analyst-heavy) and mid-cap. Block bootstrap 10-day.
- **Anti-Drift**: Minimum 5 analysts covering. Weight by recency of revision. Ignore revisions > 30 days old.
- **Edge Source**: Informational — analyst revisions incorporate private information. Behavioral — market underreacts to revision changes.
- **Assets**: S&P 500, Russell Midcap
- **Timeframe**: Bi-weekly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.72, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Chan, Jegadeesh & Lakonishok (1996) "Momentum Strategies"; Gleason & Lee (2003) "Analyst Forecast Revisions and Market Price Discovery"

### 2.10 Residual Momentum (Industry-Adjusted)
- **Core Logic**: Decompose stock returns into industry component and stock-specific (residual) component. Rank by residual momentum (past 12-1 month idiosyncratic return after removing industry effect). This is more persistent and less crash-prone than raw momentum.
- **Signal**: Run cross-sectional regression: R_i = α + β_industry × R_industry + ε_i. Cumulate ε_i over 12-1 months. Long top quintile residual momentum, short bottom quintile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Compare to standard momentum in 2009 crash (residual momentum had smaller crash).
- **Anti-Drift**: Industry classification updated annually (GICS). Regression refit monthly with 60-month rolling window. Min 20 stocks per industry.
- **Edge Source**: Residual momentum isolates firm-specific information flow, removing sector noise. More stable than raw momentum.
- **Assets**: Russell 1000
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.78, MaxDD −22%, PF 1.44
- **Complexity**: Medium
- **Refs**: Blitz, Huij & Martens (2011) "Residual Momentum"

---

## 3. Quality Factor (10)

### 3.1 Gross Profitability Premium
- **Core Logic**: Novy-Marx (2013) showed gross profits/assets is the cleanest quality measure and predicts returns independently of value. Long top quintile GP/Assets, short bottom quintile. Sector-neutral to avoid industry bias.
- **Signal**: GP/Assets = (Revenue − COGS) / Total Assets. Long top 20% sector-neutral. Short bottom 20%. Equal-weight. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 5×2.
- **Anti-Drift**: Single metric with no parameters. Sector-neutral construction. Minimum market cap $500M.
- **Edge Source**: Behavioral — investors neglect "boring" high-quality firms. GP/Assets avoids earnings manipulation.
- **Assets**: S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.70, MaxDD −20%, PF 1.38
- **Complexity**: Low
- **Refs**: Novy-Marx (2013) "The Other Side of Value"

### 3.2 ROE Stability Signal
- **Core Logic**: Not just high ROE, but stable ROE. Companies with low variance in ROE over trailing 5 years combined with ROE > 15% have persistent outperformance. Stability signals sustainable competitive advantage.
- **Signal**: Compute 5-year ROE mean and ROE coefficient of variation (CV = σ/μ). Long when ROE mean > 15% AND CV < 0.2. Short when ROE mean < 5% AND CV > 0.5. Quarterly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Regime test: compare in growth (2017-2021) vs value (2022-2023) markets.
- **Anti-Drift**: Require full 5-year history. Exclude firms with accounting restatements. Minimum market cap $1B.
- **Edge Source**: Structural — consistent high returns indicate durable moats. Behavioral — investors overweight recent ROE change over stability.
- **Assets**: S&P 500
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.68, MaxDD −18%, PF 1.40
- **Complexity**: Low
- **Refs**: Asness, Frazzini & Pedersen (2019) "Quality Minus Junk"

### 3.3 Accrual Quality (Earnings Quality)
- **Core Logic**: Companies with high accruals (earnings far exceeding cash flow) have lower quality earnings. Sloan (1996) accrual anomaly: short high-accrual firms, long low-accrual firms. Accruals = (ΔCA − ΔCash − ΔCL + ΔSTD − Dep) / Avg Total Assets.
- **Signal**: Compute total accruals / total assets. Long bottom quintile (cash-rich earnings). Short top quintile (accrual-heavy). Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test separately pre-SOX (2002) and post-SOX to check if anomaly persists.
- **Anti-Drift**: Use both balance-sheet and cash-flow-statement accrual measures. Cross-validate signal. Require 10-K filing availability.
- **Edge Source**: Behavioral — investors fixate on reported earnings, not cash flow quality. Accrual component of earnings is less persistent.
- **Assets**: Russell 1000
- **Timeframe**: Monthly rebalance (after 10-Q/10-K)
- **Expected Perf**: WR 54%, Sharpe 0.58, MaxDD −22%, PF 1.30
- **Complexity**: Medium
- **Refs**: Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?"

### 3.4 Altman Z-Score Ranking
- **Core Logic**: Altman Z-Score measures bankruptcy risk. Instead of just avoiding low Z stocks, use Z-Score as a ranking metric across the entire universe. Long top quintile (Z > 4.0, safest), short bottom quintile (Z < 1.8, riskiest). Quality premium from safety.
- **Signal**: Z = 1.2×(WC/TA) + 1.4×(RE/TA) + 3.3×(EBIT/TA) + 0.6×(MV_E/BV_D) + 1.0×(Sales/TA). Long Z > 4.0. Short Z < 1.8 (grey zone). Equal-weight.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must test in credit stress regimes (2008, 2020). Include delisting returns.
- **Anti-Drift**: Classic formula with fixed coefficients (no optimization). Exclude financials (different Z formula). Update quarterly.
- **Edge Source**: Structural — distress risk premium is not fully compensated. Behavioral — investors overvalue risky "lottery ticket" stocks.
- **Assets**: US equities ex-financials, market cap > $500M
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.62, MaxDD −24%, PF 1.32
- **Complexity**: Low
- **Refs**: Altman (1968) "Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy"

### 3.5 Beneish M-Score Short Detector
- **Core Logic**: Beneish M-Score identifies earnings manipulation. Companies with M-Score > −1.78 have higher probability of manipulation. Short these stocks. Combined with value screen to avoid shorting expensive stocks (already priced for perfection).
- **Signal**: Compute 8-variable M-Score. Short when M-Score > −1.78 AND P/E > 25 (expensive + manipulation risk). Position size 2% each. Cover when M-Score < −2.5 or earnings restate.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must include actual fraud/restatement events as validation. Survivorship bias–free.
- **Anti-Drift**: M-Score formula is fixed (Beneish 1999). No parameter optimization. Require all 8 variables available. Short-only → hedge with index long.
- **Edge Source**: Informational — M-Score detects statistical anomalies in financial statements that precede manipulation revelations. 76% accuracy in Beneish's original study.
- **Assets**: US equities, market cap > $1B
- **Timeframe**: Quarterly (after 10-Q filing)
- **Expected Perf**: WR 60%, Sharpe 0.55, MaxDD −15% (short book only), PF 1.35
- **Complexity**: Medium
- **Refs**: Beneish (1999) "The Detection of Earnings Manipulation"

### 3.6 Quality at Reasonable Price (QARP)
- **Core Logic**: Intersection of quality (ROE > 15%, low debt, stable margins) and reasonable valuation (P/E < 20, PEG < 1.5). Avoids the expensive quality trap and the low-quality value trap.
- **Signal**: Quality Score = normalize(ROE, margin stability, debt/equity). Valuation Score = normalize(1/PE, 1/PEG, FCF yield). Composite = 0.6 × Quality + 0.4 × Valuation. Long top 30 by composite. Monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test with varying weights (50/50, 60/40, 70/30) — all should be profitable.
- **Anti-Drift**: Limit to 2 parameters (quality/value weight). Sector caps 25%. Minimum market cap $2B.
- **Edge Source**: Behavioral — investors either chase quality (at any price) or value (any quality). Intersection is systematically underowned.
- **Assets**: S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.78, MaxDD −17%, PF 1.48
- **Complexity**: Medium
- **Refs**: Sloan (2019); Asness, Frazzini & Pedersen (2019) "Quality Minus Junk"

### 3.7 Franchise Quality (Durable Moats)
- **Core Logic**: Identify companies with durable competitive advantages using quantitative moat metrics: high and stable ROIC (> WACC for 10+ years), low earnings variability, high market share in oligopolistic industries. These "franchise" businesses compound returns.
- **Signal**: ROIC > WACC for 8+ of last 10 years AND earnings CV < 0.25 AND Herfindahl index of industry > 0.15 (concentrated). Long top 20 scoring stocks. Equal-weight. Annual rebalance.
- **Best Backtest Method**: Walk-forward 7yr/2yr/2yr (longer due to 10-year lookback). Monte Carlo 10k. Regime: compare in recession vs expansion.
- **Anti-Drift**: ROIC uses invested capital (not just equity), more robust. 10-year window reduces sensitivity to cycle. Minimum $5B market cap.
- **Edge Source**: Structural — franchise businesses have pricing power and high barriers to entry. Market underestimates persistence of high ROIC.
- **Assets**: S&P 500
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 60%, Sharpe 0.72, MaxDD −22%, PF 1.45
- **Complexity**: Medium
- **Refs**: Greenwald et al. (2001) "Value Investing: From Graham to Buffett and Beyond"

### 3.8 Capital Allocation Quality
- **Core Logic**: Score management's capital allocation track record: (1) buyback timing (did buybacks when stock was cheap?), (2) M&A success (did acquisitions create value?), (3) capex efficiency (ROIC on incremental invested capital). Long firms with top capital allocation records.
- **Signal**: Composite Capital Allocation Score: buyback_timing_score + acquisition_value_score + incremental_ROIC. Long top quintile, short bottom quintile. Quarterly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Requires 5-year rolling capital allocation history.
- **Anti-Drift**: Use realized outcomes (not intentions). 5-year rolling window. Equal-weight to avoid large-cap bias.
- **Edge Source**: Behavioral — investors focus on current earnings, not management quality. Structural — good capital allocators compound value silently.
- **Assets**: Russell 1000
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.65, MaxDD −24%, PF 1.38
- **Complexity**: High
- **Refs**: Mauboussin (2012) "The Success Equation"; Thorndike (2012) "The Outsiders"

### 3.9 Dividend Quality Composite
- **Core Logic**: Not just high dividend yield, but dividend quality: (1) payout ratio < 60%, (2) dividend coverage by FCF > 1.5x, (3) consecutive dividend increases > 10 years, (4) low earnings volatility. Screens for safe, growing dividends.
- **Signal**: Dividend Quality Score = normalize(payout_ratio_inverse, FCF_coverage, streak_length, earnings_stability). Long top 30 by DQ Score with yield > 2%. Sell if dividend cut or DQ Score drops to bottom quartile.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2008-2009 (many dividend cuts) and 2020 as stress tests.
- **Anti-Drift**: Focus on objective metrics (not management guidance). Minimum 10-year dividend history required. Cap REITs/utilities at 30%.
- **Edge Source**: Behavioral — investors chase high yield, ignoring sustainability. Quality dividends have lower drawdowns and higher risk-adjusted returns.
- **Assets**: S&P Dividend Aristocrats + broader screen
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 59%, Sharpe 0.70, MaxDD −20%, PF 1.42
- **Complexity**: Medium
- **Refs**: Arnott & Asness (2003) "Surprise! Higher Dividends = Higher Earnings Growth"

### 3.10 Quality-Momentum Combination Factor
- **Core Logic**: AQR's QMJ (Quality Minus Junk) combined with UMD (Up Minus Down momentum). Equal-risk-weight both factors. The negative correlation between value and momentum means quality-momentum combo has superior risk-adjusted returns.
- **Signal**: QMJ Score = profitability + growth + safety scores (Asness 2019). UMD = 12-1M return. Composite = 0.5 × rank(QMJ) + 0.5 × rank(UMD). Long top quintile, short bottom quintile.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 10×5. Test factor correlation stability over time.
- **Anti-Drift**: Two well-documented factors with negative correlation. Weight by inverse volatility. Sector-neutral.
- **Edge Source**: Portfolio construction — negative factor correlation creates a Sharpe ratio higher than either factor alone.
- **Assets**: MSCI World
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.88, MaxDD −16%, PF 1.55
- **Complexity**: Medium
- **Refs**: Asness, Frazzini & Pedersen (2019) "Quality Minus Junk"; Asness, Moskowitz & Pedersen (2013)

---

## 4. Size & Liquidity (10)

### 4.1 Small Cap Value (Size + B/M)
- **Core Logic**: Fama-French size premium combined with value: buy small-cap stocks with high book-to-market. Small-cap value has historically been the highest-returning equity factor intersection.
- **Signal**: Universe: market cap 10th-30th percentile of NYSE. Within this, long top tercile by B/M. Short large-cap (top 30% mktcap) low B/M. 6M rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must test in "death of value" period 2017-2020.
- **Anti-Drift**: Use NYSE breakpoints (avoids micro-cap proliferation). Include delisted returns. Minimum 200 stocks in portfolio.
- **Edge Source**: Structural — institutional constraints prevent large funds from buying small caps. Behavioral — small-cap value stocks are neglected.
- **Assets**: CRSP universe, NYSE breakpoints
- **Timeframe**: Semi-annual rebalance (June/December)
- **Expected Perf**: WR 58%, Sharpe 0.72, MaxDD −35%, PF 1.40
- **Complexity**: Low
- **Refs**: Fama & French (1993) "Common Risk Factors in the Returns on Stocks and Bonds"

### 4.2 Micro-Cap Momentum
- **Core Logic**: Momentum is strongest in micro-caps where institutional coverage is lowest and information diffuses slowly. Apply 6-1 month momentum to stocks with market cap $50M-$300M. Higher returns but higher transaction costs.
- **Signal**: 6-1 month return ranking. Long top quintile micro-caps, short bottom quintile. Equal-weight max 50 positions per leg. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k with realistic micro-cap spreads (50-100bps per trade). Survivorship bias–free.
- **Anti-Drift**: Include bid-ask spread costs of 50bps. Minimum daily volume $200K. Exclude stocks with > 20 days of zero trading in 6 months.
- **Edge Source**: Informational — slower information diffusion in micro-caps means momentum signals persist longer.
- **Assets**: US micro-caps ($50M-$300M)
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −40%, PF 1.35
- **Complexity**: Medium
- **Refs**: Hong, Lim & Stein (2000) "Bad News Travels Slowly"

### 4.3 Size-Profitability Interaction
- **Core Logic**: The size premium is concentrated in profitable small caps. Unprofitable small caps (which drag down the average) actually underperform. Interact size with profitability: long small + profitable, short large + unprofitable.
- **Signal**: Double sort: size (small = bottom 30% NYSE mktcap) × profitability (GP/Assets top/bottom tercile). Long small-profitable, short large-unprofitable. Equal-weight.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test independently in US, Europe, Japan.
- **Anti-Drift**: Double-sort is non-parametric. Use NYSE breakpoints. Include financial and non-financial.
- **Edge Source**: The interaction reveals that size premium is really a quality premium — profitable small firms are genuinely mispriced.
- **Assets**: CRSP universe
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.75, MaxDD −28%, PF 1.42
- **Complexity**: Low
- **Refs**: Novy-Marx (2013); Fama & French (2015) "A Five-Factor Asset Pricing Model"

### 4.4 Liquidity Premium Capture
- **Core Logic**: Illiquid stocks earn a premium (Amihud 2002). Measure illiquidity as absolute return per dollar of volume. Long illiquid stocks (top quintile Amihud ratio), short liquid stocks (bottom quintile). Requires patient capital due to execution costs.
- **Signal**: Amihud ILLIQ = avg(|daily return| / daily dollar volume) over 250 days. Long top quintile ILLIQ, short bottom quintile. Equal-weight. Quarterly rebalance to reduce turnover.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must model realistic execution with 100bps+ spread for illiquid stocks.
- **Anti-Drift**: Use rolling 250-day Amihud (stable). Minimum $50M market cap. Exclude days with zero volume.
- **Edge Source**: Structural — institutional investors cannot hold illiquid stocks. Risk premium for bearing liquidity risk.
- **Assets**: US equities, market cap > $50M
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −30%, PF 1.30
- **Complexity**: Medium
- **Refs**: Amihud (2002) "Illiquidity and Stock Returns"

### 4.5 Illiquidity Premium with Time Variation
- **Core Logic**: The illiquidity premium is time-varying — larger during market stress when liquidity dries up. Overweight illiquidity factor when aggregate liquidity is high (cheap to buy illiquid stocks), underweight when aggregate liquidity is low.
- **Signal**: Base: Amihud ILLIQ long/short. Timing: when VIX < 20 and market bid-ask spreads narrow → 1.5x illiquidity exposure. When VIX > 30 → 0.5x exposure (reduce).
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2008 and 2020 liquidity crises.
- **Anti-Drift**: Only 2 timing parameters (VIX low/high thresholds). Test robustness ±5 on thresholds.
- **Edge Source**: Structural — liquidity premium is higher when liquidity is freely available (cheap to access). Time-varying exposure captures this.
- **Assets**: US equities, market cap > $100M
- **Timeframe**: Quarterly rebalance, monthly timing adjustment
- **Expected Perf**: WR 56%, Sharpe 0.68, MaxDD −25%, PF 1.38
- **Complexity**: Medium
- **Refs**: Amihud (2002); Pastor & Stambaugh (2003) "Liquidity Risk and Expected Stock Returns"

### 4.6 Small Cap Quality Filter
- **Core Logic**: Most small-cap indices include many unprofitable, speculative companies. Apply quality filter: require positive FCF, debt/equity < 1.0, and 3-year revenue CAGR > 5%. The filtered small-cap portfolio outperforms broad small-cap indices with lower drawdown.
- **Signal**: Universe: Russell 2000. Filter: FCF > 0 AND D/E < 1.0 AND 3Y revenue CAGR > 5%. Equal-weight top 100 by combined quality rank. Quarterly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Compare to unfiltered Russell 2000.
- **Anti-Drift**: Objective quality filters (no optimization). Quarterly update after earnings. Minimum 100-stock portfolio.
- **Edge Source**: Structural — removing unprofitable small caps eliminates the "junk" that drags down the size premium.
- **Assets**: Russell 2000
- **Timeframe**: Quarterly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.70, MaxDD −28%, PF 1.40
- **Complexity**: Low
- **Refs**: Asness, Frazzini & Pedersen (2018) "Size Matters, If You Control Your Junk"

### 4.7 Size-Reversal Short-Term
- **Core Logic**: Short-term reversal (1-week, 1-month) is strongest in small caps where market-making is thin and overreaction is common. Buy small caps that dropped > 10% in the last week, short those that rose > 10%.
- **Signal**: Weekly return < −10% AND market cap < $2B → long. Weekly return > +10% AND market cap < $2B → short. Hold 5 trading days. Position size 1% each.
- **Best Backtest Method**: Walk-forward 2yr/6mo/6mo. Monte Carlo 10k with realistic small-cap spreads. Block bootstrap 5-day.
- **Anti-Drift**: News filter: exclude stocks with pending earnings, M&A, or FDA events. Require volume > 2x 20-day average (avoid illiquid gaps).
- **Edge Source**: Behavioral — overreaction to news and liquidity-driven selling in small caps.
- **Assets**: Russell 2000
- **Timeframe**: Weekly rebalance, 5-day holding
- **Expected Perf**: WR 54%, Sharpe 0.60, MaxDD −15%, PF 1.25
- **Complexity**: Medium
- **Refs**: Lehmann (1990) "Fads, Martingales, and Market Efficiency"; Jegadeesh (1990)

### 4.8 Small Cap Earnings Surprise
- **Core Logic**: Earnings surprise effect is 2-3x stronger in small caps than large caps due to lower analyst coverage and slower information diffusion. Buy small caps with large positive earnings surprises (SUE > 2.0).
- **Signal**: SUE > 2.0 AND market cap $200M-$2B AND analyst coverage < 10. Long for 60 trading days post-announcement. Equal-weight up to 30 positions.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must include exact earnings announcement dates.
- **Anti-Drift**: Fixed 60-day holding period (no exit optimization). SUE calculation uses rolling 8-quarter forecast error σ.
- **Edge Source**: Informational — low coverage means earnings information takes weeks to fully impound into small-cap prices.
- **Assets**: US small caps ($200M-$2B), analyst coverage < 10
- **Timeframe**: Event-driven (around earnings)
- **Expected Perf**: WR 61%, Sharpe 0.80, MaxDD −20%, PF 1.50
- **Complexity**: Medium
- **Refs**: Bernard & Thomas (1989) "Post-Earnings-Announcement Drift"

### 4.9 Micro-Cap Insider Buying Cluster
- **Core Logic**: When 3+ insiders at a micro-cap company buy in a 30-day window, this is a strong positive signal. Cluster insider buying in micro-caps has > 70% hit rate over 6 months.
- **Signal**: Cluster = 3+ distinct insiders making open-market purchases within 30 calendar days. Market cap < $500M. No insider sells in same period. Long for 6 months.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Survivorship bias–free. Include delisting returns.
- **Anti-Drift**: Objective cluster definition (3+ insiders, 30-day window). Only open-market purchases (not options exercises). Real-time SEC Form 4 data.
- **Edge Source**: Informational — insiders collectively buying is strongest predictive signal. In micro-caps, their purchases are larger relative to float.
- **Assets**: US micro-caps ($50M-$500M)
- **Timeframe**: Event-driven, 6-month hold
- **Expected Perf**: WR 65%, Sharpe 0.85, MaxDD −25%, PF 1.60
- **Complexity**: Medium
- **Refs**: Lakonishok & Lee (2001); Cziraki, De Goeij & Geerts (2014) "Insider Trading Activity and Returns"

### 4.10 Small Cap Seasonal January Effect
- **Core Logic**: Small caps outperform in January (tax-loss selling reversal). Build portfolio of tax-loss candidates (stocks down > 20% YTD) in December, hold through January. The effect is concentrated in the first 5 trading days.
- **Signal**: In mid-December: buy small caps (market cap < $2B) that are down > 20% YTD AND have high short interest (> 10% float). Hold until Feb 1. Sell all.
- **Best Backtest Method**: Walk-forward 10yr/2yr/2yr (annual signal). Monte Carlo 10k. Test in years with strong vs weak December selling.
- **Anti-Drift**: Annual event (January only) → no overtrading. Use mechanical YTD return threshold. Limited parameters.
- **Edge Source**: Structural — tax-loss selling creates artificial year-end depression. Reversal in January as selling pressure lifts.
- **Assets**: Russell 2000 stocks down > 20% YTD
- **Timeframe**: Annual (mid-Dec to end-Jan)
- **Expected Perf**: WR 68%, Sharpe 1.20 (annualized), MaxDD −10%, PF 1.80
- **Complexity**: Low
- **Refs**: Keim (1983) "Size-Related Anomalies and Stock Return Seasonality"

---

## 5. Statistical Arbitrage (10)

### 5.1 Pairs Trading via Cointegration
- **Core Logic**: Identify pairs of stocks with cointegrated prices (Engle-Granger or Johansen test). When the spread deviates > 2σ from equilibrium, trade the convergence: buy the underperformer, short the outperformer.
- **Signal**: Test for cointegration using ADF test (p < 0.05) on log price spread. Enter when Z-score of spread > 2.0 (short spread) or < −2.0 (long spread). Exit at Z = 0. Stop loss at Z = 3.5.
- **Best Backtest Method**: Walk-forward 2yr/6mo/6mo. Monte Carlo 10k. CPCV 5×2 with embargo. Half-life test for mean-reversion speed.
- **Anti-Drift**: Re-test cointegration monthly. Drop pairs if ADF p > 0.10. Maximum holding period 20 days. Require sector match.
- **Edge Source**: Structural — pairs within same sector share common factors. Temporary divergence from fundamental relationship.
- **Assets**: S&P 500 same-sector pairs (e.g., KO-PEP, XOM-CVX)
- **Timeframe**: Daily signals, 5-20 day holding
- **Expected Perf**: WR 62%, Sharpe 1.10, MaxDD −12%, PF 1.55
- **Complexity**: Medium
- **Refs**: Gatev, Goetzmann & Rouwenhorst (2006) "Pairs Trading: Performance of a Relative-Value Arbitrage Rule"

### 5.2 Sector-Neutral Statistical Arbitrage
- **Core Logic**: Within each sector, rank stocks by short-term reversal (5-day return). Buy oversold stocks, sell overbought. Sector-neutral ensures no macro exposure. This is a pure alpha strategy exploiting microstructure noise.
- **Signal**: Within each GICS sector, compute 5-day return Z-score. Long stocks with Z < −2.0, short stocks with Z > 2.0. Dollar-neutral within each sector. Daily rebalance.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo. Monte Carlo 10k. Block bootstrap 5-day. Must include 2020 March crash.
- **Anti-Drift**: Sector-neutral by construction. No cross-sector bets. Maximum position 1%. Minimum 200 positions total.
- **Edge Source**: Microstructure — short-term overreaction due to liquidity demand, not information. Sector neutrality isolates this effect.
- **Assets**: S&P 500
- **Timeframe**: Daily rebalance
- **Expected Perf**: WR 53%, Sharpe 1.50, MaxDD −8%, PF 1.20
- **Complexity**: High
- **Refs**: Avellaneda & Lee (2010) "Statistical Arbitrage in the US Equities Market"

### 5.3 PCA-Based Factor Arbitrage
- **Core Logic**: Run PCA on return covariance matrix. First 3-5 components capture systematic factors. Residual returns (after removing PCA factors) exhibit mean-reversion. Trade residual return Z-scores.
- **Signal**: Daily: fit PCA on 60-day rolling window. Compute residual return = actual − predicted (from top 5 PCs). Z-score residual over 20-day lookback. Long when Z < −2, short when Z > 2. Exit at Z = 0.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo. Monte Carlo 10k. Sensitivity to number of PCA components (3, 5, 7).
- **Anti-Drift**: Rolling PCA window adapts to changing factor structure. Minimum eigenvalue ratio > 0.05 for retained components. Re-estimate daily.
- **Edge Source**: Informational — PCA isolates idiosyncratic shocks. Residual mean-reversion is microstructure-driven.
- **Assets**: Russell 1000
- **Timeframe**: Daily signals, 3-10 day holding
- **Expected Perf**: WR 54%, Sharpe 1.30, MaxDD −10%, PF 1.25
- **Complexity**: High
- **Refs**: Avellaneda & Lee (2010); Jolliffe (2002) "Principal Component Analysis"

### 5.4 ETF vs Components Arbitrage
- **Core Logic**: When ETF price deviates from net asset value (NAV) of underlying components, trade the convergence. Buy cheap side (ETF or basket), sell expensive side. Deviation typically mean-reverts within 1-3 days.
- **Signal**: Compute implied NAV from component prices. Premium = (ETF Price − NAV) / NAV. When premium > 50bps → short ETF, long components. When discount > 50bps → long ETF, short components. Close at 0.
- **Best Backtest Method**: Walk-forward 1yr/3mo/3mo. Monte Carlo 10k with execution cost Monte Carlo (random fill rates).
- **Anti-Drift**: Fundamental arbitrage (convergence guaranteed at creation/redemption). Monitor creation/redemption activity.
- **Edge Source**: Structural — ETF creation/redemption mechanism guarantees convergence. Premium/discount from retail order flow imbalance.
- **Assets**: SPY, QQQ, IWM, XLF, XLE and their components
- **Timeframe**: Intraday to 3-day
- **Expected Perf**: WR 72%, Sharpe 2.00, MaxDD −3%, PF 1.80
- **Complexity**: High
- **Refs**: Petajisto (2017) "Inefficiencies in the Pricing of Exchange-Traded Funds"

### 5.5 ADR-Ordinary Spread Arbitrage
- **Core Logic**: American Depositary Receipts (ADRs) and their underlying ordinary shares sometimes trade at different effective prices due to time zone differences and FX. When spread exceeds transaction costs, trade convergence.
- **Signal**: ADR Premium = (ADR Price / FX rate × ratio) − Ordinary Price. Enter when |premium| > 1.5% (after costs). Pairs trade. Close when premium < 0.3%.
- **Best Backtest Method**: Walk-forward 2yr/6mo/6mo. Monte Carlo 10k. Must model FX hedging cost, ADR conversion fees, and borrowing costs.
- **Anti-Drift**: Fundamental arbitrage (convertibility). Monitor ADR program changes. Require dual-listed on liquid exchanges.
- **Edge Source**: Structural — time zone mismatch, FX friction, investor segmentation between US and home market.
- **Assets**: Liquid ADRs: TSM, BABA, SAP, NVO, ASML, BP, SHEL, TM, etc.
- **Timeframe**: Daily signals, 1-5 day holding
- **Expected Perf**: WR 65%, Sharpe 1.20, MaxDD −5%, PF 1.50
- **Complexity**: High
- **Refs**: Gagnon & Karolyi (2010) "Multi-Market Trading and Arbitrage"

### 5.6 Stub Value Arbitrage
- **Core Logic**: When a parent company owns a publicly traded subsidiary, compute stub value = parent market cap − (ownership % × subsidiary market cap). If stub is negative or implausibly low, the parent is undervalued vs the subsidiary.
- **Signal**: Stub Value / Parent Assets < 0 OR < 10th percentile historically → long parent, short subsidiary (proportional to ownership %). Exit when stub normalizes.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Case study validation (Yahoo-Alibaba, 3Com-Palm, etc.).
- **Anti-Drift**: Limited universe (< 50 opportunities at any time). Fundamental anchor (negative stub is irrational). Monitor corporate action risk.
- **Edge Source**: Structural — complexity, investor segmentation, and forced selling (index-driven) create mispricings.
- **Assets**: Parent-subsidiary pairs (e.g., SoftBank-ARM, IAC-ANGI)
- **Timeframe**: Monthly screening, 3-12 month holding
- **Expected Perf**: WR 60%, Sharpe 0.80, MaxDD −20%, PF 1.45
- **Complexity**: High
- **Refs**: Mitchell, Pulvino & Stafford (2002) "Limited Arbitrage in Equity Markets"; Lamont & Thaler (2003)

### 5.7 Holding Company Discount
- **Core Logic**: Holding companies (Berkshire, Leucadia, etc.) and closed-end funds trade at persistent discounts to NAV. Buy when discount is abnormally wide (> 2σ from own history), expecting mean-reversion.
- **Signal**: Discount = (NAV − Price) / NAV. Enter long when discount > own 3-year mean + 2σ. Exit when discount < own 3-year mean. Maximum holding 12 months.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Cross-validate with out-of-sample holding companies.
- **Anti-Drift**: NAV computed from public holdings (no estimation). Track activist involvement (catalyst for discount narrowing).
- **Edge Source**: Structural — tax overhang, management fee drag, conglomerate discount. Behavioral — sentiment-driven discount widening.
- **Assets**: US-listed holding companies and closed-end equity funds
- **Timeframe**: Monthly screening
- **Expected Perf**: WR 58%, Sharpe 0.55, MaxDD −18%, PF 1.35
- **Complexity**: Medium
- **Refs**: Pontiff (1996) "Costly Arbitrage: Evidence from Closed-End Funds"

### 5.8 Dual-Listed Premium Trading
- **Core Logic**: Some companies are dual-listed on two exchanges (e.g., Royal Dutch Shell A/B, Unilever NV/PLC). Relative pricing should be stable but fluctuates due to country-specific demand. Trade the premium when it deviates.
- **Signal**: Compute price ratio vs historical mean (250-day). Enter when ratio Z-score > 2.0. Trade convergence.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Include FX costs.
- **Anti-Drift**: Fundamental arbitrage (same cash flows). Monitor unification risk (e.g., Shell unified A/B in 2005).
- **Edge Source**: Structural — investor segmentation by geography, index membership differences.
- **Assets**: Dual-listed pairs (Rio Tinto AU/UK, BHP AU/UK, etc.)
- **Timeframe**: Weekly, 5-30 day holding
- **Expected Perf**: WR 63%, Sharpe 1.00, MaxDD −8%, PF 1.45
- **Complexity**: Medium
- **Refs**: De Jong, Rosenthal & Van Dijk (2009) "The Risk and Return of Arbitrage in Dual-Listed Companies"

### 5.9 Index Inclusion/Exclusion Arbitrage
- **Core Logic**: Stocks added to major indices (S&P 500, Russell 2000) experience temporary price increase as index funds buy; deletions see selling pressure. Buy additions before effective date, short deletions.
- **Signal**: Announcement → trade within 24h. Long additions with 2% target. Short deletions with 2% target. Hold until effective date + 5 days. Position size 1-2% each.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must have exact announcement and effective dates. Pre-2000 and post-2000 separate (more indexing post-2000).
- **Anti-Drift**: Calendar-driven (no optimization). Use actual announcement dates from press releases. Monitor for reversals post-effective.
- **Edge Source**: Structural — index fund demand is mechanical and predictable. Price impact from concentrated buying/selling.
- **Assets**: S&P 500, Russell 2000 additions/deletions
- **Timeframe**: Event-driven, 5-15 day holding
- **Expected Perf**: WR 68%, Sharpe 1.50, MaxDD −5%, PF 1.70
- **Complexity**: Low
- **Refs**: Chen, Noronha & Singal (2004) "The Price Response to S&P 500 Index Additions and Deletions"

### 5.10 Merger Arbitrage Spread
- **Core Logic**: After merger announcement, target trades at discount to offer price (merger spread). Long target, short acquirer (in stock deals). Earn spread if deal closes. Risk management: size by deal probability.
- **Signal**: Spread = (Offer Price − Target Price) / Target Price. Enter when spread > 3% (annualized > 10%). Weight by estimated deal probability (0.5-0.95 based on regulatory, shareholder, financing risk). Exit at close or break.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Include broken deal losses. Regime test in 2008 (many broken deals) vs 2015-2019 (most closed).
- **Anti-Drift**: Fundamental anchor (deal terms are public). Maximum 5% per deal. Diversify 15-25 deals at a time.
- **Edge Source**: Structural — deal completion risk is compensated. Insurance-like returns (frequent small gains, rare large losses).
- **Assets**: Announced M&A deals, $1B+ deal value
- **Timeframe**: Event-driven, 1-6 month holding
- **Expected Perf**: WR 85%, Sharpe 0.70, MaxDD −15%, PF 1.60
- **Complexity**: Medium
- **Refs**: Mitchell & Pulvino (2001) "Characteristics of Risk and Return in Risk Arbitrage"

---

## 6. Event-Driven (10)

### 6.1 Post-Earnings Announcement Drift (PEAD) Enhanced
- **Core Logic**: Stocks with positive earnings surprises continue to drift up for 60 days; negative surprises drift down. Enhanced version: use SUE > 2.0, add volume surge confirmation, and momentum filter.
- **Signal**: SUE > 2.0 AND abnormal volume on announcement day > 2x average AND 20-day pre-earnings momentum > 0. Long for 60 days. Symmetric for shorts (SUE < −2.0).
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Align to quarterly earnings calendar. CPCV 5×2.
- **Anti-Drift**: Fixed holding period (no exit optimization). SUE calculation standardized. Volume filter removes low-attention surprises.
- **Edge Source**: Behavioral — underreaction to earnings information. Enhanced version filters for high-attention confirmations.
- **Assets**: S&P 500
- **Timeframe**: Event-driven, 60-day hold
- **Expected Perf**: WR 60%, Sharpe 0.85, MaxDD −15%, PF 1.50
- **Complexity**: Medium
- **Refs**: Bernard & Thomas (1989); Ball & Brown (1968)

### 6.2 Spin-Off Alpha
- **Core Logic**: Corporate spin-offs generate alpha because (1) parent shareholders dump the smaller spin-off (forced selling), (2) index funds sell if spin-off isn't in index, (3) spin-off management has new incentives. Buy spin-offs 5 days after ex-date.
- **Signal**: Buy spin-off 5 days after ex-date. Hold 12 months. Additional filter: insider buying at spin-off within 30 days = stronger signal. Position 2-3% each.
- **Best Backtest Method**: Walk-forward 5yr/2yr/2yr. Monte Carlo 10k. Include all spin-offs with market cap > $100M.
- **Anti-Drift**: Calendar-based entry (5 days post ex-date). Require SEC filing completeness. Minimum spin-off market cap $100M.
- **Edge Source**: Structural — forced selling creates temporary undervaluation. Aligned management incentives drive improvement.
- **Assets**: US spin-offs, market cap > $100M
- **Timeframe**: Event-driven, 12-month hold
- **Expected Perf**: WR 62%, Sharpe 0.80, MaxDD −25%, PF 1.50
- **Complexity**: Medium
- **Refs**: Greenblatt (1997) "You Can Be a Stock Market Genius"

### 6.3 IPO Lock-Up Expiry Short
- **Core Logic**: When IPO lock-up period expires (typically 180 days post-IPO), insiders can sell. Stocks often decline 2-5% around lock-up expiry due to supply increase. Short 3 days before expiry, cover 5 days after.
- **Signal**: Short 3 trading days before lock-up expiry. Cover 5 days after. Additional: stronger signal if (1) IPO traded above offer price, (2) high insider ownership, (3) VC-backed. Position max 2%.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include exact lock-up dates from S-1 filings.
- **Anti-Drift**: Calendar-based signal. Lock-up dates are public. Maximum 2% position (binary outcome risk). Require borrow availability.
- **Edge Source**: Structural — supply/demand imbalance at lock-up expiry. Insiders selling into constrained float.
- **Assets**: US IPOs with > $100M market cap at expiry
- **Timeframe**: Event-driven, 8-day hold
- **Expected Perf**: WR 60%, Sharpe 0.90, MaxDD −8%, PF 1.40
- **Complexity**: Low
- **Refs**: Field & Hanka (2001) "The Expiration of IPO Share Lockups"; Bradley et al. (2001)

### 6.4 Share Buyback Completion Signal
- **Core Logic**: Not just buyback announcements, but tracking actual buyback completion (via 10-Q cash flow statement). Companies that actually execute > 75% of announced buyback within 12 months outperform those that don't. Real skin in the game.
- **Signal**: Track actual shares repurchased (from 10-Q) vs announced program. Long when cumulative completion > 75% within first year. Sell when buyback program ends or company issues new shares.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Require full quarterly data on share counts.
- **Anti-Drift**: Objective metric (share count changes from SEC filings). No parameter optimization (75% is industry standard).
- **Edge Source**: Informational — completion rate reveals management conviction. Behavioral — market ignores execution data.
- **Assets**: S&P 500 buyback announcements
- **Timeframe**: Quarterly monitoring, 12-month hold
- **Expected Perf**: WR 58%, Sharpe 0.65, MaxDD −22%, PF 1.38
- **Complexity**: Medium
- **Refs**: Peyer & Vermaelen (2009) "The Nature and Persistence of Buyback Anomalies"; Grullon & Michaely (2004)

### 6.5 Activist 13D Filing Alpha
- **Core Logic**: When activist investors file 13D (> 5% ownership), target stocks outperform. Especially strong when activist has track record of successful campaigns. Buy within 5 days of 13D filing.
- **Signal**: 13D filed by known activist (Icahn, Ackman, Elliott, etc.) or activist fund. Market cap > $500M. Buy within 5 days. Hold 12 months or until campaign resolution. Position 2-3%.
- **Best Backtest Method**: Walk-forward 5yr/2yr/2yr. Monte Carlo 10k. Survivorship bias: include failed campaigns.
- **Anti-Drift**: Event-based with objective trigger (SEC filing). Known activist list updated annually based on 13D track records.
- **Edge Source**: Informational — activists signal undervaluation and provide catalyst. Structural — governance improvement.
- **Assets**: US equities, market cap > $500M, activist 13D filings
- **Timeframe**: Event-driven, 12-month hold
- **Expected Perf**: WR 63%, Sharpe 0.75, MaxDD −20%, PF 1.50
- **Complexity**: Medium
- **Refs**: Brav et al. (2008) "Hedge Fund Activism, Corporate Governance, and Firm Performance"

### 6.6 Secondary Offering Fade
- **Core Logic**: Secondary stock offerings (follow-on offerings) create selling pressure and signal insider desire to sell at current prices. Short around pricing date, cover 30 days later as selling pressure from underwriter stabilization ends.
- **Signal**: Short on secondary offering pricing date. Cover 30 trading days later. Filter: overnight offering (not marketed) = stronger signal. Position 1-2%.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Include all SEC-registered secondaries.
- **Anti-Drift**: Calendar-based (pricing date public). Maximum 2% position. Require borrow availability.
- **Edge Source**: Structural — supply increase from new shares. Informational — insiders chose to sell at current prices.
- **Assets**: US equities with secondary offerings, market cap > $500M
- **Timeframe**: Event-driven, 30-day hold
- **Expected Perf**: WR 57%, Sharpe 0.60, MaxDD −10%, PF 1.30
- **Complexity**: Low
- **Refs**: Altinkilic & Hansen (2003) "Discounting and Underpricing in Seasoned Equity Offers"

### 6.7 Index Rebalancing Front-Run
- **Core Logic**: Russell 2000 reconstitution (end of June) creates massive demand for additions and supply for deletions. Front-run by predicting additions/deletions based on market cap rankings and buying/shorting before the public announcement.
- **Signal**: In May: identify stocks near Russell 2000/3000 market cap boundary. Predict additions (rising above threshold) → long. Predict deletions (falling below) → short. Close 5 days after reconstitution effective date.
- **Best Backtest Method**: Walk-forward 10yr/2yr/2yr (annual event). Monte Carlo 10k. Test prediction accuracy of additions/deletions.
- **Anti-Drift**: Annual event (June). Use FTSE Russell methodology for predictions. Limit to high-confidence predictions (> 80% predicted probability).
- **Edge Source**: Structural — index fund rebalancing creates ~$100B+ in forced trading. Predictable demand/supply shock.
- **Assets**: Russell 2000/3000 reconstitution candidates
- **Timeframe**: Annual (May-July), 6-week trade
- **Expected Perf**: WR 65%, Sharpe 1.50, MaxDD −5%, PF 1.70
- **Complexity**: Medium
- **Refs**: Petajisto (2011) "The Index Premium and Its Hidden Cost for Index Funds"

### 6.8 Enhanced Dividend Capture
- **Core Logic**: Traditional dividend capture (buy before ex-date, sell after) fails due to price drop = dividend. Enhancement: target stocks with "sticky" price around ex-date (high institutional ownership, low vol) where price drop < dividend due to microstructure effects.
- **Signal**: Buy 1 day before ex-date when: trailing 20-day realized vol < 15% annualized AND institutional ownership > 70% AND dividend yield > 3%. Sell 3 days after ex-date. Target: capture > 60% of dividend net of price drop.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must model tax implications and short-term capital gains.
- **Anti-Drift**: Limited parameters. Use actual ex-dates (no optimization). Monitor tax law changes.
- **Edge Source**: Microstructure — in liquid, institutionally held stocks, ex-date price drops can be < 100% of dividend due to limit order dynamics.
- **Assets**: S&P 500 stocks with > 3% dividend yield
- **Timeframe**: Event-driven, 4-day hold
- **Expected Perf**: WR 55%, Sharpe 0.50, MaxDD −5%, PF 1.20
- **Complexity**: Medium
- **Refs**: Elton & Gruber (1970) "Marginal Stockholder Tax Rates and the Clientele Effect"

### 6.9 Rights Offering Discount
- **Core Logic**: Companies issuing rights offerings (at a discount to market price) often see the stock price drop to near the subscription price before recovering. Buy when stock drops to rights offering price, sell when it recovers.
- **Signal**: Stock price approaches rights offering subscription price (within 5%). Buy at subscription price + 2%. Hold until price > ex-rights theoretical price. Maximum 60 days.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Include failed rights offerings.
- **Anti-Drift**: Fundamental anchor (subscription price is public). Fixed time limit (60 days).
- **Edge Source**: Structural — forced selling by investors who don't want to invest more capital. Temporary supply/demand imbalance.
- **Assets**: US/UK rights offerings, market cap > $200M
- **Timeframe**: Event-driven, 30-60 day hold
- **Expected Perf**: WR 58%, Sharpe 0.60, MaxDD −15%, PF 1.35
- **Complexity**: Medium
- **Refs**: Eckbo & Masulis (1992) "Adverse Selection and the Rights Offer Paradox"

### 6.10 Forced Selling Detection (Fund Liquidation)
- **Core Logic**: When mutual funds or hedge funds face large redemptions, they are forced to sell holdings regardless of fundamentals. Detect forced selling via (1) large outflows from fund complex, (2) abnormal selling pressure in concentrated holdings. Buy oversold stocks.
- **Signal**: Detect potential forced selling: mutual fund flows < −5% of AUM in a month AND stock down > 10% on 5x normal volume AND stock is top-10 holding of distressed fund. Buy immediately. Hold 60 days.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2008, 2016 (HF liquidations), 2020 as stress tests.
- **Anti-Drift**: Detection rules are structural (observable flows). No curve-fitting. Real-time 13F + flow data.
- **Edge Source**: Structural — forced selling creates prices disconnected from fundamentals. Predictable reversal.
- **Assets**: US equities in concentrated mutual fund/hedge fund positions
- **Timeframe**: Event-driven, 60-day hold
- **Expected Perf**: WR 62%, Sharpe 0.85, MaxDD −18%, PF 1.50
- **Complexity**: High
- **Refs**: Coval & Stafford (2007) "Asset Fire Sales (and Purchases) in Equity Markets"

---

## 7. Sector Rotation (10)

### 7.1 Business Cycle Sector Rotation
- **Core Logic**: Different sectors outperform at different stages of the business cycle. Map ISM PMI to cycle stage: early expansion (PMI rising above 50) → cyclicals; late expansion (PMI > 55 and flattening) → energy/materials; contraction → defensives/utilities.
- **Signal**: PMI > 52 and rising → long XLI, XLY, XLF (cyclicals). PMI > 55 and flat/falling → long XLE, XLB (late cycle). PMI < 48 → long XLP, XLU, XLV (defensives). Monthly rotation.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Regime test across 4 NBER cycles. Use ISM publication lag (1 day).
- **Anti-Drift**: Only 3 regimes (simple). PMI is single published number. Test with ±2 on thresholds.
- **Edge Source**: Structural — sector earnings sensitivity to business cycle is well-documented. Behavioral — investors are slow to rotate.
- **Assets**: 11 SPDR Sector ETFs
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.65, MaxDD −22%, PF 1.35
- **Complexity**: Low
- **Refs**: Stovall (1996) "Sector Investing"; Fidelity Business Cycle Research

### 7.2 Relative Strength Sector Rotation
- **Core Logic**: Rank sectors by 6-month relative strength (return vs SPY). Long top 3 sectors, short bottom 3. This captures sector momentum — sectors in uptrend tend to continue.
- **Signal**: RS = Sector 6M return − SPY 6M return. Long top 3 RS sectors. Short bottom 3 RS sectors. Equal-weight. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Lookback sensitivity (3M, 6M, 9M, 12M).
- **Anti-Drift**: Minimal parameters (only lookback period). Universe is fixed (11 sectors).
- **Edge Source**: Behavioral — sector trends driven by institutional rotation and narrative momentum.
- **Assets**: 11 SPDR Sector ETFs
- **Timeframe**: Monthly
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −20%, PF 1.32
- **Complexity**: Low
- **Refs**: Moskowitz & Grinblatt (1999) "Do Industries Explain Momentum?"

### 7.3 Mean-Reversion Sector Rotation
- **Core Logic**: Sectors that have underperformed over 12 months tend to outperform over the next 3-6 months (sector mean-reversion). Buy bottom 3 sectors by 12M return, sell top 3. This works best when sector dispersion is extreme.
- **Signal**: Rank sectors by 12M return. Long bottom 3. Short top 3. Additional filter: only trade when sector return dispersion (σ of sector returns) > 75th percentile historically. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Regime: dispersion high (>75th pct) vs low.
- **Anti-Drift**: Dispersion filter reduces false signals. Single lookback parameter.
- **Edge Source**: Behavioral — sectors overshoot due to narrative cycles. Structural — sector fundamentals are mean-reverting.
- **Assets**: 11 SPDR Sector ETFs
- **Timeframe**: Monthly rebalance, 3-6 month holding
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −25%, PF 1.30
- **Complexity**: Low
- **Refs**: De Bondt & Thaler (1985) "Does the Stock Market Overreact?"

### 7.4 Credit-Equity Sector Rotation
- **Core Logic**: Credit spreads lead equity sector moves. When HY-IG spread widens → risk-off, rotate to defensives. When spread narrows → risk-on, rotate to cyclicals. Credit market has better-informed participants (banks, insurance companies).
- **Signal**: HY-IG OAS spread Z-score (60-day). Z < −1.0 (narrowing rapidly) → long XLY, XLI, XLK, XLF. Z > 1.0 (widening rapidly) → long XLP, XLU, XLV, XLRE. Monthly rotation.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include 2008 and 2020. Lead-lag analysis of credit vs equity.
- **Anti-Drift**: Credit spread is observable market price. Single parameter (Z-score lookback). Test at 30, 60, 90 day lookbacks.
- **Edge Source**: Informational — credit markets process risk information faster than equity markets. Cross-asset signal.
- **Assets**: Sector ETFs + HY/IG bond spread data
- **Timeframe**: Monthly
- **Expected Perf**: WR 57%, Sharpe 0.68, MaxDD −18%, PF 1.40
- **Complexity**: Medium
- **Refs**: Faust et al. (2013) "Credit Spreads as Predictors of Real-Time Economic Activity"

### 7.5 Yield Curve Sector Rotation
- **Core Logic**: Yield curve shape predicts sector performance. Steepening curve → financials outperform (profit from borrow short/lend long). Flattening/inverting → utilities, staples outperform (flight to safety).
- **Signal**: 10Y-2Y spread. If > 100bps and rising → overweight XLF, XLI, XLE. If < 50bps or inverting → overweight XLP, XLU, XLV. If between 50-100bps → equal-weight. Monthly.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Test across 5 rate cycles.
- **Anti-Drift**: Yield curve is observable. Limited parameters (2 thresholds). Test with ±25bps on thresholds.
- **Edge Source**: Structural — yield curve directly impacts financial sector profitability. Leading indicator of economic regime.
- **Assets**: Sector ETFs + Treasury yield curve data
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.62, MaxDD −20%, PF 1.35
- **Complexity**: Low
- **Refs**: Estrella & Mishkin (1998) "Predicting U.S. Recessions"

### 7.6 PMI Breadth Sector Rotation
- **Core Logic**: Instead of just ISM manufacturing PMI, use breadth of regional PMIs (NY, Philly, Dallas, KC, Chicago, Richmond). When breadth > 67% (4/6 expanding) → cyclicals. When breadth < 33% → defensives. Breadth reduces false signals from individual PMI noise.
- **Signal**: PMI Breadth = count(regional PMIs > 50) / 6. Breadth > 0.67 → long cyclicals (XLI, XLY, XLK). Breadth < 0.33 → long defensives (XLP, XLU, XLV). Between → equal-weight.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Regime: compare to using only ISM (breadth should outperform).
- **Anti-Drift**: Uses 6 independent data sources → robust. Binary classification (expanding/contracting) per PMI.
- **Edge Source**: Informational — breadth aggregation provides more robust economic signal than any single indicator.
- **Assets**: Sector ETFs
- **Timeframe**: Monthly (after all regional PMIs published)
- **Expected Perf**: WR 57%, Sharpe 0.68, MaxDD −18%, PF 1.40
- **Complexity**: Medium
- **Refs**: Berge & Jordà (2011) "Evaluating the Classification of Economic Activity into Recessions and Expansions"

### 7.7 Sentiment-Based Sector Rotation
- **Core Logic**: Use put-call ratio, AAII sentiment survey, and VIX to gauge market sentiment. Extreme bearish sentiment → buy cyclicals (contrarian). Extreme bullish → buy defensives (protection). Combine 3 indicators for composite.
- **Signal**: Composite Sentiment = normalize(put-call ratio, inverted) + normalize(% AAII bears) + normalize(VIX). When composite Z > 1.5 (extreme fear) → long cyclicals. When Z < −1.5 (extreme greed) → long defensives. Monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Regime: test in trending vs ranging markets.
- **Anti-Drift**: Uses 3 independent sentiment sources. Contrarian signal (robustly documented). Z-score thresholds at ±1.5 (conservative).
- **Edge Source**: Behavioral — extreme sentiment is contrarian signal. Crowd psychology overshoots.
- **Assets**: Sector ETFs
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.60, MaxDD −22%, PF 1.32
- **Complexity**: Medium
- **Refs**: Baker & Wurgler (2006) "Investor Sentiment and the Cross-Section of Stock Returns"

### 7.8 Volatility-Based Sector Rotation
- **Core Logic**: In high-volatility environments, low-beta sectors outperform. In low-volatility environments, high-beta sectors outperform. Rotate based on VIX regime.
- **Signal**: VIX < 15 → long high-beta sectors (XLK, XLY, XLF). VIX 15-25 → equal-weight. VIX > 25 → long low-beta sectors (XLP, XLU, XLRE). Weekly monitoring, monthly execution.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test with ±3 on VIX thresholds.
- **Anti-Drift**: VIX is observable. 3-regime model with limited parameters. Sector betas are stable over 6-month periods.
- **Edge Source**: Structural — beta premium is time-varying. Low-vol investing outperforms risk-adjusted in high-vol regimes.
- **Assets**: Sector ETFs
- **Timeframe**: Monthly
- **Expected Perf**: WR 55%, Sharpe 0.58, MaxDD −20%, PF 1.30
- **Complexity**: Low
- **Refs**: Baker, Bradley & Wurgler (2011) "Benchmarks as Limits to Arbitrage"

### 7.9 Momentum-Quality Sector Combo
- **Core Logic**: Rank sectors by 6M momentum AND average quality score of constituents. Select sectors that are both trending up and improving in quality. This avoids momentum in low-quality sectors (value traps).
- **Signal**: For each sector: 6M RS momentum score + average constituent GP/Assets Z-score. Composite = 0.5 × RS + 0.5 × Quality. Long top 3 sectors by composite. Monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Compare to pure momentum and pure quality sector rotation.
- **Anti-Drift**: Two orthogonal signals combined. Limited parameters. Sector-level (only 11 assets).
- **Edge Source**: Combination of momentum and quality at sector level reduces crash risk vs pure momentum.
- **Assets**: 11 Sector ETFs + constituent fundamentals
- **Timeframe**: Monthly
- **Expected Perf**: WR 57%, Sharpe 0.72, MaxDD −16%, PF 1.42
- **Complexity**: Medium
- **Refs**: Asness, Frazzini & Pedersen (2019); Moskowitz & Grinblatt (1999)

### 7.10 Seasonal Sector Rotation
- **Core Logic**: Certain sectors have reliable seasonal patterns: energy outperforms in Q4 (heating season), retail in Q4 (holiday), tech in Q1 (CES/earnings). Rotate based on historical monthly sector performance patterns.
- **Signal**: For each month, rank sectors by average excess return in that month over past 20 years. Long top 3 sectors for the current month. Monthly rotation.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Out-of-sample (use 20-year lookback, test on next 5 years).
- **Anti-Drift**: 20-year average smooths noise. Only 11 × 12 = 132 data points to estimate (relatively few). Require seasonal pattern > 1σ significance.
- **Edge Source**: Structural — seasonal earnings patterns, commodity cycles, consumer behavior. Partially rational (heating oil demand in winter).
- **Assets**: 11 Sector ETFs
- **Timeframe**: Monthly rotation
- **Expected Perf**: WR 54%, Sharpe 0.50, MaxDD −22%, PF 1.25
- **Complexity**: Low
- **Refs**: Jacobsen & Visaltanachoti (2009) "The Halloween Effect in U.S. Sectors"

---

## 8. Earnings Strategies (10)

### 8.1 PEAD with SUE Quintile Spreading
- **Core Logic**: Sort stocks into SUE quintiles. Long top quintile (big positive surprise), short bottom quintile. The drift lasts ~60 trading days. Enhanced by weighting more heavily stocks with analyst downgrades reversed by actual results.
- **Signal**: SUE = (EPS_actual − EPS_consensus) / σ(EPS surprise history). Long SUE top 20%. Short SUE bottom 20%. Hold 60 days. Extra weight if consensus was declining pre-earnings (larger surprise impact).
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Earnings calendar–aligned. CPCV 5×2 with 5-day embargo.
- **Anti-Drift**: Fixed holding period. Standardized SUE calculation. Minimum 3 analyst estimates.
- **Edge Source**: Behavioral — investors underreact to earnings news. ~60-day drift is one of the most robust anomalies in finance.
- **Assets**: S&P 500
- **Timeframe**: Event-driven (quarterly), 60-day hold
- **Expected Perf**: WR 58%, Sharpe 0.80, MaxDD −15%, PF 1.45
- **Complexity**: Medium
- **Refs**: Bernard & Thomas (1989) "Post-Earnings-Announcement Drift"

### 8.2 Standardized Unexpected Earnings Momentum
- **Core Logic**: Track 4 consecutive quarters of SUE direction. Stocks with 4 consecutive positive SUE quarters have strong forward returns (consistent fundamental momentum). Sell when SUE turns negative.
- **Signal**: Long when 4 consecutive quarters of SUE > 0. Position size proportional to average SUE magnitude. Exit when SUE < 0 for any quarter.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Sensitivity to streak length (2, 3, 4 quarters).
- **Anti-Drift**: Binary condition (positive/negative SUE) reduces curve fitting. Streak requirement filters noise.
- **Edge Source**: Behavioral — positive earnings momentum persists because analysts are slow to revise estimates upward enough.
- **Assets**: S&P 500
- **Timeframe**: Quarterly assessment, variable hold
- **Expected Perf**: WR 60%, Sharpe 0.75, MaxDD −18%, PF 1.45
- **Complexity**: Low
- **Refs**: Chan, Jegadeesh & Lakonishok (1996) "Momentum Strategies"

### 8.3 Whisper Number Deviation
- **Core Logic**: "Whisper numbers" (unofficial consensus) are often higher than published consensus. Stocks that beat whisper numbers outperform; those that beat consensus but miss whisper underperform (sell the news).
- **Signal**: If actual EPS > whisper estimate AND > consensus → strong long (hold 30 days). If actual > consensus but < whisper → short (sell the news, hold 10 days). Position 1-2%.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Must have whisper estimate data source.
- **Anti-Drift**: Whisper numbers are from independent sources (not analyst). Binary comparison (beat/miss). Short holding periods.
- **Edge Source**: Informational — whisper numbers capture market expectations beyond published consensus. Behavioral — "buy the rumor, sell the news."
- **Assets**: Large-cap US equities with whisper data
- **Timeframe**: Event-driven, 10-30 day hold
- **Expected Perf**: WR 56%, Sharpe 0.65, MaxDD −12%, PF 1.35
- **Complexity**: Medium
- **Refs**: Bagnoli, Beneish & Watts (1999) "Whisper Forecasts of Quarterly Earnings per Share"

### 8.4 Earnings Guidance Revision Signal
- **Core Logic**: When companies raise forward guidance, stock outperforms over 30-60 days. Guidance raises are more informative than earnings beats because they are forward-looking management signals.
- **Signal**: Management raises full-year EPS guidance by > 2% above prior guidance → long. Lowers by > 2% → short. Hold 45 days.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must have exact guidance dates and amounts.
- **Anti-Drift**: Binary signal (raise/lower) with 2% magnitude threshold. Forward-looking (not backward). Fixed hold period.
- **Edge Source**: Informational — management guidance conveys private information about business trajectory. More reliable than analyst estimates.
- **Assets**: S&P 500 companies that issue guidance
- **Timeframe**: Event-driven, 45-day hold
- **Expected Perf**: WR 59%, Sharpe 0.75, MaxDD −14%, PF 1.45
- **Complexity**: Medium
- **Refs**: Hutton, Lee & Shu (2012) "Do Managers Always Know Better?"

### 8.5 Earnings Quality Trend
- **Core Logic**: Track the ratio of cash flow from operations to net income over 4 quarters. Rising ratio (cash > earnings) → quality improving. Falling ratio → quality deteriorating. Quality improvement precedes stock outperformance.
- **Signal**: Cash-to-Earnings Ratio = CFO / Net Income (4Q rolling). Long when ratio rising for 3 consecutive quarters AND > 1.0. Short when falling 3 quarters AND < 0.8. Quarterly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test separately for growth stocks and value stocks.
- **Anti-Drift**: Fundamental metric from financial statements. Trend direction (not level) → less sensitive to industry differences.
- **Edge Source**: Informational — cash flow quality trends predict future earnings revisions. Behavioral — investors focus on reported earnings.
- **Assets**: S&P 500
- **Timeframe**: Quarterly assessment
- **Expected Perf**: WR 57%, Sharpe 0.62, MaxDD −20%, PF 1.35
- **Complexity**: Medium
- **Refs**: Sloan (1996) "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows?"

### 8.6 Earnings Acceleration
- **Core Logic**: Not just positive earnings growth, but accelerating growth. If Q-over-Q earnings growth rate is increasing (positive second derivative), the stock is in a fundamental acceleration phase. These stocks significantly outperform.
- **Signal**: EPS Growth Acceleration = (EPS growth Q_current − EPS growth Q_prior). Long when acceleration > 0 for 2 consecutive quarters AND EPS growth > 0. Short when deceleration < 0 for 2 quarters AND EPS growth turning negative.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Test with 1Q and 2Q acceleration requirements.
- **Anti-Drift**: Second derivative requires strong trend (less noisy than first derivative). Minimum EPS > $0.10 to avoid small-base effects.
- **Edge Source**: Behavioral — investors anchor on current growth rate, underestimate acceleration. Momentum in fundamentals.
- **Assets**: Russell 1000
- **Timeframe**: Quarterly
- **Expected Perf**: WR 58%, Sharpe 0.70, MaxDD −22%, PF 1.40
- **Complexity**: Medium
- **Refs**: Chordia & Shivakumar (2006) "Earnings and Price Momentum"

### 8.7 Revenue Surprise Signal
- **Core Logic**: Revenue surprises are harder to manipulate than earnings surprises and predict future earnings better. A positive revenue surprise with negative earnings surprise (cost overrun) is temporary. Positive revenue + positive earnings = strongest signal.
- **Signal**: Revenue surprise = (actual − consensus) / consensus. Long when revenue surprise > 3% AND earnings surprise > 0. Short when revenue surprise < −3% AND earnings surprise < 0. Hold 45 days.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must include revenue estimate data.
- **Anti-Drift**: Revenue is top-line (hard to manipulate). Dual condition (revenue + earnings) reduces noise.
- **Edge Source**: Informational — revenue is more fundamental than earnings. Top-line growth signals genuine demand.
- **Assets**: S&P 500
- **Timeframe**: Event-driven, 45-day hold
- **Expected Perf**: WR 59%, Sharpe 0.72, MaxDD −15%, PF 1.42
- **Complexity**: Medium
- **Refs**: Jegadeesh & Livnat (2006) "Revenue Surprises and Stock Returns"

### 8.8 Margin Expansion Signal
- **Core Logic**: When a company's gross or operating margin is expanding (2+ consecutive quarters of margin improvement), it signals pricing power or cost efficiency. Margin expansion in revenue-growing companies is an especially strong signal.
- **Signal**: Operating margin expanding 2+ consecutive quarters AND revenue growth > 0 AND margin now above 3-year average → long. Margin contracting 2+ quarters AND revenue declining → short. Quarterly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Sector-adjusted margins (compare within sector).
- **Anti-Drift**: Use sector-relative margins to normalize. Require 2-quarter trend (not single-quarter noise).
- **Edge Source**: Fundamental — margin expansion drives earnings growth. Behavioral — investors focus on absolute margins, not trends.
- **Assets**: Russell 1000
- **Timeframe**: Quarterly
- **Expected Perf**: WR 57%, Sharpe 0.65, MaxDD −20%, PF 1.38
- **Complexity**: Medium
- **Refs**: Soliman (2008) "The Use of DuPont Analysis by Market Participants"

### 8.9 Earnings Call NLP Sentiment
- **Core Logic**: Apply NLP to earnings call transcripts. Score management tone (positive vs hedging language), Q&A section sentiment (analyst pushback), and compare to prior quarter. Tone improvement → positive signal.
- **Signal**: NLP Sentiment Score delta = current quarter score − prior quarter score. Long when delta > +0.2 (1-5 scale) AND earnings surprise ≥ 0. Short when delta < −0.2 AND earnings surprise ≤ 0. Hold 30 days.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr. Monte Carlo 10k. Must use consistent NLP model across all quarters. Out-of-sample validation on new transcripts.
- **Anti-Drift**: Delta score (change in tone) is more robust than absolute tone. Model retraining quarterly. Manual validation sample.
- **Edge Source**: Informational — management's non-verbal cues and language patterns reveal private information not in the numbers.
- **Assets**: S&P 500 (all companies with earnings calls)
- **Timeframe**: Event-driven, 30-day hold
- **Expected Perf**: WR 56%, Sharpe 0.60, MaxDD −14%, PF 1.32
- **Complexity**: High
- **Refs**: Loughran & McDonald (2011) "When Is a Liability Not a Liability?"

### 8.10 Analyst Revision Breadth
- **Core Logic**: Track the breadth of analyst estimate revisions (% of analysts revising up minus % revising down). High positive breadth (>60% revising up) signals strong consensus improvement. More predictive than magnitude of revision.
- **Signal**: Revision Breadth = (# revisions up − # revisions down) / total analysts in last 30 days. Long when breadth > 0.6 (strong agreement). Short when breadth < −0.6. Monthly.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Compare to single-analyst revision signal.
- **Anti-Drift**: Breadth is a robust aggregate (not single analyst). 30-day rolling window. Minimum 5 analysts.
- **Edge Source**: Informational — when many analysts simultaneously revise, the information content is high. Behavioral — investors track individual analyst calls, not breadth.
- **Assets**: S&P 500, minimum 5 analysts
- **Timeframe**: Monthly
- **Expected Perf**: WR 57%, Sharpe 0.68, MaxDD −16%, PF 1.38
- **Complexity**: Medium
- **Refs**: Gleason & Lee (2003) "Analyst Forecast Revisions and Market Price Discovery"

---

## 9. Multi-Factor (10)

### 9.1 Fama-French 5-Factor Tilt
- **Core Logic**: Systematically tilt portfolio toward all 5 FF factors simultaneously: size (SMB), value (HML), profitability (RMW), investment (CMA), plus momentum (UMD). Equal risk contribution across factors.
- **Signal**: For each stock, compute composite Z-score = w1×Z(size) + w2×Z(B/M) + w3×Z(profitability) + w4×Z(investment) + w5×Z(12-1M momentum). Weights = inverse factor vol. Long top quintile, short bottom quintile.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 10×5. Factor correlation stability test.
- **Anti-Drift**: Inverse-vol weighting adapts to factor regimes. Each factor is independently documented. Sector-neutral.
- **Edge Source**: Portfolio construction — diversified factor exposure reduces idiosyncratic factor risk.
- **Assets**: Russell 1000
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 57%, Sharpe 0.85, MaxDD −18%, PF 1.50
- **Complexity**: Medium
- **Refs**: Fama & French (2015) "A Five-Factor Asset Pricing Model"

### 9.2 Barra Risk Factor Timing
- **Core Logic**: Time exposure to Barra risk factors (momentum, volatility, size, value, growth, leverage, liquidity) based on macroeconomic indicators. Overweight factors with positive macro tailwinds.
- **Signal**: Monthly: compute macro indicator dashboard (PMI, credit spreads, yield curve, VIX). Map to factor regime. Overweight momentum+growth when PMI rising + VIX low. Overweight value+size when PMI bottoming + credit tightening.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Must test across multiple macro cycles.
- **Anti-Drift**: Macro indicators are exogenous. Factor-macro relationships documented in literature. Limited number of regimes (4).
- **Edge Source**: Structural — factor premiums are time-varying and linked to macro conditions. Timing adds 1-2% annually.
- **Assets**: Russell 1000, Barra factor portfolio construction
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.72, MaxDD −22%, PF 1.40
- **Complexity**: High
- **Refs**: Hodges et al. (2017) "Factor Timing with Cross-Sectional and Time-Series Predictors"

### 9.3 AQR Multi-Strategy Replication
- **Core Logic**: Replicate AQR-style multi-strategy approach: equal-risk-weight across value (HML), momentum (UMD), carry (long-short dividend yield), and defensive (low-vol). Global implementation across equities, bonds, FX, commodities.
- **Signal**: For each of 4 factors across 4 asset classes → 16 sub-strategies. Each sub-strategy is long/short quintile. Aggregate with equal risk contribution. Target 10% portfolio vol.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test factor-level and aggregate. Stress test: all factors underperforming simultaneously.
- **Anti-Drift**: 4 × 4 = 16 diversified strategies. Vol-targeting normalizes. No factor timing (static allocation).
- **Edge Source**: Diversification — 16 low-correlated return streams. Each factor has independent academic support.
- **Assets**: Global equities, bond futures, FX majors, commodity futures
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.90, MaxDD −15%, PF 1.55
- **Complexity**: High
- **Refs**: Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere"; Koijen et al. (2018) "Carry"

### 9.4 Factor Momentum (Rotating Hot Factors)
- **Core Logic**: Factors themselves have momentum — the best-performing factor over 12 months tends to continue outperforming. Apply time-series momentum to factor returns: overweight factors with positive 12M return.
- **Signal**: Compute 12M return for each of 7 factors (value, momentum, size, quality, low-vol, dividend, growth). Long factors with 12M return > 0 (vol-scaled). Underweight factors with 12M return < 0. Monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must test during factor rotation events (2020 growth→value).
- **Anti-Drift**: Single lookback parameter. Binary signal (positive/negative). Applied to well-documented factors.
- **Edge Source**: Structural — factor returns are auto-correlated (institutional rebalancing, macro persistence). Factor momentum documented by Gupta & Kelly (2019).
- **Assets**: US factor portfolios (long/short)
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.72, MaxDD −20%, PF 1.40
- **Complexity**: Medium
- **Refs**: Gupta & Kelly (2019) "Factor Momentum Everywhere"; Arnott et al. (2019)

### 9.5 Factor Crowding Avoidance
- **Core Logic**: When a factor becomes crowded (too many investors holding the same positions), its future returns decline and crash risk increases. Monitor factor crowding via valuation spread, short interest concentration, and pairwise correlation of factor holdings.
- **Signal**: Crowding Score = valuation spread percentile + average pairwise correlation of top quintile holdings + short interest concentration in bottom quintile. When crowding > 80th percentile → reduce factor exposure by 50%. When < 20th percentile → increase to 150%.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include momentum crash of 2009 and value crash of 2020 (both crowding-related).
- **Anti-Drift**: Crowding metrics are observable. Contrarian overlay reduces crash risk. Applied to any factor.
- **Edge Source**: Structural — crowded factors have compressed expected returns and elevated crash risk. Avoiding crowding is risk management.
- **Assets**: Factor portfolios (any)
- **Timeframe**: Monthly assessment
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −15%, PF 1.35
- **Complexity**: High
- **Refs**: Lou & Polk (2022) "Comomentum"; Betermier et al. (2022) "Crowding and Factor Returns"

### 9.6 Factor Interaction Effects
- **Core Logic**: Some factor combinations are non-linearly powerful. Size + value (small-cap value) has historically been the strongest. Momentum + quality avoids crashes. Map interaction terms and exploit the strongest intersections.
- **Signal**: Create 2D sorts: size × value, momentum × quality, value × momentum. For each 2D cell, compute historical alpha. Overweight cells with highest alpha. Portfolio = allocation to best interaction cells.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 5×2. Must test interaction stability over time.
- **Anti-Drift**: Only top-3 interactions used (limit complexity). Re-evaluate annually. Academic documentation of each interaction.
- **Edge Source**: Behavioral — interaction effects are less well-known than individual factors. Structural — they capture genuine economic effects.
- **Assets**: Russell 1000, independent double sorts
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 58%, Sharpe 0.80, MaxDD −20%, PF 1.48
- **Complexity**: Medium
- **Refs**: Fama & French (1993, 2015); Novy-Marx (2013)

### 9.7 Conditional Factor (Regime-Dependent Allocation)
- **Core Logic**: Different factors outperform in different macro regimes. Map 4 regimes (expansion, slowdown, contraction, recovery) to optimal factor allocation. Use ISM PMI + yield curve to identify regime.
- **Signal**: Expansion (PMI > 55, curve steep) → momentum + growth. Slowdown (PMI falling, curve flattening) → quality + low-vol. Contraction (PMI < 48) → defensive + min-variance. Recovery (PMI rising from low) → value + small cap.
- **Best Backtest Method**: Walk-forward 10yr/3yr/3yr. Monte Carlo 10k. Test across 4+ NBER cycles.
- **Anti-Drift**: 4-regime model (limited complexity). Macro indicators are exogenous. Factor-regime mapping based on 50+ years of data.
- **Edge Source**: Structural — factor premiums covary with macro conditions. Timing adds alpha without adding factors.
- **Assets**: Factor portfolios + macro data
- **Timeframe**: Monthly (regime assessment)
- **Expected Perf**: WR 57%, Sharpe 0.75, MaxDD −18%, PF 1.42
- **Complexity**: High
- **Refs**: Amenc et al. (2016) "Factor Investing and Risk Allocation"; Bender et al. (2018)

### 9.8 Defensive Factor Timing
- **Core Logic**: Time allocation to defensive factors (low-volatility, quality, min-variance) based on tail risk indicators. Overweight defensive when tail risk is high (VIX > 25, credit spreads widening, drawdown > 5%).
- **Signal**: Tail Risk Score = max(VIX Z-score, HY spread Z-score, drawdown Z-score). When score > 1.0 → 75% defensive factors. When score < −0.5 → 25% defensive (overweight cyclicals). Between → 50% defensive.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Stress test: 2008, 2011, 2018, 2020.
- **Anti-Drift**: Observable risk indicators. Limited parameters (2 thresholds). Defensive bias is the safe default.
- **Edge Source**: Structural — defensive factors outperform in risk-off. Timing improves by avoiding defensive underperformance in strong risk-on periods.
- **Assets**: Factor portfolios (low-vol, quality, min-variance)
- **Timeframe**: Monthly (weekly monitoring)
- **Expected Perf**: WR 56%, Sharpe 0.68, MaxDD −14%, PF 1.38
- **Complexity**: Medium
- **Refs**: Baker, Bradley & Wurgler (2011); Frazzini & Pedersen (2014) "Betting Against Beta"

### 9.9 ESG-Aware Multi-Factor
- **Core Logic**: Integrate ESG scores as an additional factor alongside traditional factors. ESG momentum (improving ESG scores) predicts returns. Exclude ESG controversies (which predict negative returns) while maintaining factor exposure.
- **Signal**: Composite = 0.2 × value + 0.2 × momentum + 0.2 × quality + 0.2 × low-vol + 0.2 × ESG momentum (12M ESG score change). Exclude bottom 10% by ESG controversy score. Long top quintile composite.
- **Best Backtest Method**: Walk-forward 3yr/1yr/1yr (ESG data shorter history). Monte Carlo 10k. Compare to non-ESG version.
- **Anti-Drift**: ESG data from multiple providers (MSCI, Sustainalytics). Momentum in ESG score (not level) to avoid static bias. Yearly recalibrate.
- **Edge Source**: Informational — ESG improvements predict future cash flow stability. Behavioral — ESG is increasingly priced by institutions.
- **Assets**: MSCI World or S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 56%, Sharpe 0.70, MaxDD −19%, PF 1.38
- **Complexity**: Medium
- **Refs**: Pedersen, Fitzgibbons & Pomorski (2021) "Responsible Investing: The ESG-Efficient Frontier"

### 9.10 Sector-Neutral Multi-Factor
- **Core Logic**: Apply multi-factor scoring within each sector (not cross-sector). This eliminates sector bets and isolates pure stock selection alpha. Within each sector, rank by composite factor score and go long top / short bottom.
- **Signal**: Within each of 11 GICS sectors: composite = equal-weight(value, momentum, quality, low-vol). Long top 20% per sector, short bottom 20%. Dollar-neutral within each sector AND across sectors.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. CPCV 5×2.
- **Anti-Drift**: Sector-neutral by construction. Factors applied within sector → controls for industry effects. Minimum 10 stocks per sector leg.
- **Edge Source**: Pure stock selection alpha, isolated from macro/sector bets. Each factor contributes independently.
- **Assets**: S&P 500, 11 GICS sectors
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.75, MaxDD −12%, PF 1.40
- **Complexity**: Medium
- **Refs**: Bender et al. (2018) "Reducing the Dimensionality of Multi-Factor Investing"

---

## 10. Anomaly Exploitation (10)

### 10.1 Lottery Stock Short
- **Core Logic**: Stocks with lottery-like characteristics (high skewness, high volatility, low price) are systematically overpriced because retail investors overpay for "jackpot" potential. Short portfolio of lottery stocks, hedged with index long.
- **Signal**: Lottery Score = rank(max daily return in past month) + rank(idiosyncratic volatility) + rank(1/price). Short top quintile lottery stocks. Hedge with equal dollar SPY long. Monthly.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test in bull (when lottery stocks soar) and bear markets.
- **Anti-Drift**: Lottery characteristics are observable ex-ante. Simple ranking. Include borrow costs.
- **Edge Source**: Behavioral — prospect theory predicts overweighting of small probabilities. Retail preference for lottery payoffs.
- **Assets**: Russell 3000, include OTC
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.65, MaxDD −25%, PF 1.35
- **Complexity**: Medium
- **Refs**: Bali, Cakici & Whitelaw (2011) "Maxing Out: Stocks as Lotteries and the Cross-Section of Expected Returns"

### 10.2 Low Volatility Anomaly
- **Core Logic**: Low-volatility stocks earn higher risk-adjusted returns than high-volatility stocks — contradicting CAPM. Long low-vol, short high-vol. The anomaly persists because institutional benchmarking creates demand for high-beta stocks.
- **Signal**: Compute 60-day realized volatility. Long bottom quintile (low vol), short top quintile (high vol). Market-cap weighted within each quintile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must test in strong bull markets (when high-vol outperforms temporarily).
- **Anti-Drift**: Single metric (realized vol). Minimal parameters. Include borrow costs for short leg.
- **Edge Source**: Structural — benchmarking + leverage constraints force institutions to buy high-beta stocks. Behavioral — investors prefer exciting high-vol stocks.
- **Assets**: S&P 500
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 55%, Sharpe 0.72, MaxDD −16%, PF 1.38
- **Complexity**: Low
- **Refs**: Baker, Bradley & Wurgler (2011) "Benchmarks as Limits to Arbitrage"; Frazzini & Pedersen (2014)

### 10.3 Idiosyncratic Volatility Puzzle
- **Core Logic**: Stocks with high idiosyncratic volatility (after removing market, size, value factors) have abnormally low future returns. Short high idiosyncratic vol, long low. Related to lottery preference and attention.
- **Signal**: Regress stock returns on Fama-French 3 factors. Compute σ(residuals) over 30 days. Short top quintile idio-vol, long bottom quintile. Monthly rebalance.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Must include speculative bubble periods (1999, 2021).
- **Anti-Drift**: Factor regression controls for systematic risk. Rolling 30-day window. Include borrow costs.
- **Edge Source**: Behavioral — attention-driven buying of high idio-vol stocks. Lottery preference. Over-optimism by unsophisticated investors.
- **Assets**: Russell 3000
- **Timeframe**: Monthly rebalance
- **Expected Perf**: WR 54%, Sharpe 0.60, MaxDD −20%, PF 1.30
- **Complexity**: Medium
- **Refs**: Ang et al. (2006) "The Cross-Section of Volatility and Expected Returns"

### 10.4 Accrual Anomaly Enhanced
- **Core Logic**: Sloan (1996) accrual anomaly: stocks with high accruals (earnings far exceeding cash flow) underperform. Enhanced: use both balance-sheet and cash-flow accruals, combine with analyst revision direction.
- **Signal**: Total Accruals = (ΔCA − ΔCash) − (ΔCL − ΔSTD − ΔTP) − Dep, scaled by average total assets. Short top decile accruals AND analyst revisions declining. Long bottom decile accruals AND revisions rising.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Test pre- and post-SOX periods. CPCV 5×2.
- **Anti-Drift**: Dual signal (accruals + revisions) provides confirmation. Use both BS and CF accrual measures.
- **Edge Source**: Behavioral — fixation on reported earnings. Accounting manipulation via accruals is predictably reversed.
- **Assets**: Russell 1000
- **Timeframe**: Quarterly (after 10-Q)
- **Expected Perf**: WR 56%, Sharpe 0.62, MaxDD −18%, PF 1.35
- **Complexity**: Medium
- **Refs**: Sloan (1996); Richardson et al. (2005) "Accrual Reliability, Earnings Persistence and Stock Prices"

### 10.5 Asset Growth Anomaly
- **Core Logic**: Companies with high asset growth (total assets growing > 20% YoY) tend to underperform. Empire-building, dilutive acquisitions, and overinvestment destroy shareholder value. Short high-growth, long low-growth.
- **Signal**: Asset Growth = (Total Assets_t − Total Assets_t-1) / Total Assets_t-1. Short top quintile (> 20% growth). Long bottom quintile (< 2% growth). Annual rebalance.
- **Best Backtest Method**: Walk-forward 5yr/2yr/2yr. Monte Carlo 10k. Include M&A-driven growth separately.
- **Anti-Drift**: Single metric from balance sheet. Annual signal (low turnover). No parameter optimization.
- **Edge Source**: Behavioral — investors overvalue growth and underestimate dilution/overinvestment costs.
- **Assets**: Russell 1000
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 55%, Sharpe 0.58, MaxDD −22%, PF 1.30
- **Complexity**: Low
- **Refs**: Cooper, Gulen & Schill (2008) "Asset Growth and the Cross-Section of Stock Returns"

### 10.6 Net Stock Issuance Anomaly
- **Core Logic**: Companies that issue new shares (secondary offerings, stock compensation) underperform, while companies reducing share count (buybacks) outperform. Net issuance is a strong negative predictor.
- **Signal**: Net Issuance = log(split-adjusted shares outstanding_t / shares_t-1). Short top quintile (heavy issuers). Long bottom quintile (heavy repurchasers). Annual rebalance.
- **Best Backtest Method**: Walk-forward 5yr/2yr/2yr. Monte Carlo 10k. Include both voluntary and involuntary issuance.
- **Anti-Drift**: Single metric from SEC filings. Annual frequency. No threshold optimization.
- **Edge Source**: Informational — management times issuance (issue when overvalued) and repurchase (when undervalued). Dilution effect.
- **Assets**: Russell 1000
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 56%, Sharpe 0.60, MaxDD −20%, PF 1.32
- **Complexity**: Low
- **Refs**: Pontiff & Woodgate (2008) "Share Issuance and Cross-Sectional Returns"; Daniel & Titman (2006)

### 10.7 R&D to Market Cap Signal
- **Core Logic**: Companies with high R&D spending relative to market cap are systematically undervalued because GAAP expenses R&D immediately (understating true economic value). Long high R&D/MarketCap firms with positive revenue growth.
- **Signal**: R&D/Market Cap in top quintile AND revenue growth > 0 AND R&D spending growing → long. Filter: require R&D/Revenue > 10% (true R&D-intensive firms). Hold 12 months.
- **Best Backtest Method**: Walk-forward 5yr/1yr/1yr. Monte Carlo 10k. Sector-adjusted (tech/biotech have structurally higher R&D).
- **Anti-Drift**: Sector-adjust R&D ratios. Require positive revenue trend (avoid cash-burning startups). Minimum market cap $500M.
- **Edge Source**: Accounting — GAAP misprices intangible investments. R&D creates future earnings not reflected in current book value.
- **Assets**: R&D-intensive sectors (tech, biotech, pharma, industrials)
- **Timeframe**: Annual rebalance
- **Expected Perf**: WR 57%, Sharpe 0.65, MaxDD −28%, PF 1.38
- **Complexity**: Medium
- **Refs**: Chan, Lakonishok & Sougiannis (2001) "The Stock Market Valuation of Research and Development Expenditures"

### 10.8 Customer Momentum
- **Core Logic**: Track the stock performance of a company's major customers (disclosed in 10-K filings). If a company's top customers are outperforming, the supplier tends to follow with a lag. Supply chain information diffuses slowly.
- **Signal**: Compute weighted average 3M return of company's disclosed major customers. Long suppliers where customer momentum > 10%. Short where customer momentum < −10%. Monthly.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must parse 10-K customer disclosures. Test lead-lag stability.
- **Anti-Drift**: Use disclosed relationships only (10-K filings). 3M lookback is standard for supply chain signals.
- **Edge Source**: Informational — supply chain information travels slowly. Customer success predicts supplier demand.
- **Assets**: US equities with 10-K customer disclosures
- **Timeframe**: Monthly
- **Expected Perf**: WR 56%, Sharpe 0.62, MaxDD −20%, PF 1.35
- **Complexity**: High
- **Refs**: Cohen & Frazzini (2008) "Economic Links and Predictable Returns"

### 10.9 Geographic Momentum
- **Core Logic**: Companies with revenue concentration in fast-growing geographic regions outperform. Parse geographic revenue segments from 10-K. If a company's highest-growth region contributes > 30% of revenue, the company benefits from that tailwind.
- **Signal**: For each company, compute revenue-weighted GDP growth of its geographic segments. Long top quintile (highest geographic tailwind). Short bottom quintile. Quarterly.
- **Best Backtest Method**: Walk-forward 4yr/1yr/1yr. Monte Carlo 10k. Must have geographic revenue segment data.
- **Anti-Drift**: GDP growth rates are exogenous. Revenue weights from SEC filings. Quarterly update post-10-Q.
- **Edge Source**: Informational — investors underestimate geographic revenue mix. Companies exposed to high-growth regions benefit disproportionately.
- **Assets**: S&P 500 multinationals
- **Timeframe**: Quarterly
- **Expected Perf**: WR 55%, Sharpe 0.55, MaxDD −22%, PF 1.30
- **Complexity**: High
- **Refs**: Garcia & Norli (2012) "Geographic Dispersion and Stock Returns"

### 10.10 Attention-Driven Trading
- **Core Logic**: Stocks experiencing abnormal attention (Google search volume, social media mentions, news articles) experience short-term overpricing due to retail buying, followed by reversal. Sell the attention spike.
- **Signal**: Attention Z-score = (current week searches − 4-week average) / σ. Short when Z > 3.0 AND volume > 3x average AND retail order flow indicator positive. Cover after 10 days. Position 1% each.
- **Best Backtest Method**: Walk-forward 2yr/6mo/6mo. Monte Carlo 10k. Block bootstrap 5-day. Must include meme stock era (2021).
- **Anti-Drift**: Z-score > 3.0 is conservative threshold. 10-day fixed holding. Combine multiple attention measures (Google, social, news).
- **Edge Source**: Behavioral — attention-driven buying by uninformed investors creates temporary overpricing. Barber & Odean (2008) "All That Glitters."
- **Assets**: Russell 3000 with Google Trends data
- **Timeframe**: Weekly screening, 10-day hold
- **Expected Perf**: WR 55%, Sharpe 0.60, MaxDD −12%, PF 1.30
- **Complexity**: Medium
- **Refs**: Barber & Odean (2008) "All That Glitters: The Effect of Attention and News on the Buying Behavior of Individual and Institutional Investors"; Da, Engelberg & Gao (2011)

---

*100 Elite Equity & Factor Strategies — End of Document*
