# Comprehensive Trading Strategies Compilation
## Research Sources: Bloomberg, Reuters, FT, WSJ, CNBC, Investopedia, Seeking Alpha, TradingView

---

## Table of Contents
1. [Institutional Algorithmic Strategies](#1-institutional-algorithmic-strategies)
2. [Quantitative & Systematic Strategies](#2-quantitative--systematic-strategies)
3. [Technical Analysis Strategies](#3-technical-analysis-strategies)
4. [Momentum & Trend Following Strategies](#4-momentum--trend-following-strategies)
5. [Mean Reversion & Statistical Arbitrage](#5-mean-reversion--statistical-arbitrage)
6. [Options & Volatility Strategies](#6-options--volatility-strategies)
7. [Risk Management Frameworks](#7-risk-management-frameworks)
8. [Multi-Asset & Macro Strategies](#8-multi-asset--macro-strategies)

---

## 1. Institutional Algorithmic Strategies

### Strategy 1: VWAP (Volume-Weighted Average Price) Execution
**Source:** Bloomberg Intelligence - European Institutional Equity Trading Study 2025  
**URL:** https://www.bloomberg.com/professional/insights/trading/european-institutional-equity-trading-study-technology/

**Description:** VWAP is the second-most used execution benchmark among European buyside traders at 27% usage (up from previous years), particularly favored by small (31%) and medium-sized (29%) firms.

**Entry Rules:**
- Order slicing based on historical volume patterns
- Trade execution proportional to expected market volume
- Start execution at market open or specified time

**Exit Rules:**
- Complete order execution by market close
- Benchmark against VWAP calculation
- Post-trade TCA analysis

**Indicators Used:**
- Real-time volume data
- Historical volume profiles
- Market impact models

**Performance Claims:**
- Minimizes market impact for large orders
- 27% adoption rate among European institutional traders
- Preferred benchmark for smaller institutions

**Risk Management:**
- Pre-trade TCA estimation
- Maximum participation rate limits (typically 10-30% of volume)
- Stop execution if adverse price movement exceeds threshold

---

### Strategy 2: Implementation Shortfall (Arrival Price) Strategy
**Source:** Bloomberg Intelligence - US Institutional Equity Trading 2025  
**URL:** https://www.bloomberg.com/professional/products/bloomberg-terminal/research/bloomberg-intelligence/download/us-institutional-equity-trading-2025/

**Description:** Arrival price (Implementation Shortfall) remains the most-used execution benchmark at 30% overall, favored by 40% of large firms. Measures execution performance against the price at order initiation.

**Entry Rules:**
- Capture arrival price at order submission
- Balance urgency vs. market impact
- Use algorithmic slicing for large orders

**Exit Rules:**
- Complete execution within defined time horizon
- Measure slippage from arrival price
- Report implementation shortfall metrics

**Indicators Used:**
- Arrival price benchmark
- Realized vs. expected market impact
- Opportunity cost calculations

**Performance Claims:**
- 30% usage rate among European traders
- 33% preference among North American traders
- 7 percentage point drop from previous year indicates shifting preferences

**Risk Management:**
- Maximum acceptable shortfall threshold
- Time-based urgency parameters
- Market condition adjustments

---

### Strategy 3: Algo Wheel Strategy
**Source:** Bloomberg Intelligence - EET 2025 Technology Algo and TCA Trends  
**URL:** https://www.bloomberg.com/professional/insights/artificial-intelligence/eet-2025-technology-algo-and-tca-trends/

**Description:** Algorithm wheels automate order allocations across different brokers' algorithms to measure performance and direct flow to best performers. 42% of buyside firms using algo wheels in 2025 (up from 33% in 2024).

**Entry Rules:**
- Define broker universe (average 7.9 providers)
- Set allocation percentages based on historical performance
- Rotate orders systematically across providers

**Exit Rules:**
- Reallocate based on TCA results
- Remove underperforming brokers
- Quarterly or monthly rebalancing

**Indicators Used:**
- Post-trade TCA metrics
- Broker performance scores
- Market impact measurements

**Performance Claims:**
- 42% adoption rate in 2025
- Reduces manual input and broker selection bias
- Supports best execution obligations

**Risk Management:**
- Minimum number of brokers for diversification
- Maximum concentration limits
- Regular performance monitoring

---

### Strategy 4: Market-on-Close (MoC) Execution
**Source:** Bloomberg Intelligence - European Institutional Equity Trading Study  
**URL:** https://www.bloomberg.com/professional/insights/trading/european-institutional-equity-trading-study-technology/

**Description:** MoC concentrates liquidity near market close, allowing execution around predictable volume spikes. Used by 21% of traders consistently across firm sizes.

**Entry Rules:**
- Submit orders before close cutoff time
- Target closing price or volume-weighted close
- Size orders based on expected closing volume

**Exit Rules:**
- Execute at closing auction
- Benchmark against closing price
- Report tracking error

**Indicators Used:**
- Closing volume estimates
- Auction imbalance data
- Closing price predictions

**Performance Claims:**
- 21% consistent usage across firm sizes
- 27% usage in EU markets
- Lower market impact for large orders

**Risk Management:**
- Order size limits relative to expected close volume
- Contingency plans for auction disruptions
- Price limit protections

---

### Strategy 5: AI-Enhanced Broker Algo Selection
**Source:** Bloomberg Intelligence - EET 2025 AI Adoption Study  
**URL:** https://www.bloomberg.com/professional/insights/artificial-intelligence/eet-2025-technology-algo-and-tca-trends/

**Description:** Large buyside firms testing AI in broker algos - 25% actively testing, 11% frequent/daily use. AI helps optimize execution parameters in real-time.

**Entry Rules:**
- Deploy AI models for pre-trade analysis
- Select optimal algorithm based on market conditions
- Adjust parameters dynamically

**Exit Rules:**
- AI-driven exit timing optimization
- Real-time performance monitoring
- Automatic strategy switching

**Indicators Used:**
- Machine learning models
- Real-time market microstructure data
- Historical execution patterns

**Performance Claims:**
- 25% of large firms testing AI broker algos
- 26% expect AI execution decisions within 2 years
- Productivity gains without workforce reduction

**Risk Management:**
- Human oversight of AI decisions
- Maximum loss thresholds
- Kill switches for automated systems

---

## 2. Quantitative & Systematic Strategies

### Strategy 6: Multi-Factor Quant Strategy (Seeking Alpha PRO Quant)
**Source:** Seeking Alpha PRO Quant Portfolio  
**URL:** https://seekingalpha.com/article/4797290-leveraging-the-pro-quant-portfolio

**Description:** Multi-factor approach using Value, Growth, Profitability, EPS Revisions, and Momentum. Backtest shows 1,632% cumulative return vs 162% S&P 500 (Jan 2015 - May 2025).

**Entry Rules:**
- Stock must be Quant "Strong Buy" for consecutive trading days
- No active M&A activity
- SEC filings current
- Price under $10,000

**Exit Rules:**
- Sell if rating drops to Sell or Strong Sell (immediate)
- Sell if rating drops to Hold (weekly rebalance)
- M&A threshold breach
- Price exceeds $10,000

**Indicators Used:**
- 100+ metrics per stock vs sector peers
- Value, Growth, Profitability, Momentum, EPS Revisions factors
- Daily data refresh

**Performance Claims:**
- 1,632% cumulative return (2015-2025) vs 162% S&P 500
- 440% five-year return vs 90% S&P 500 equal weight
- 10x outperformance over 10 years

**Risk Management:**
- 30-stock equal-weight portfolio
- Weekly rebalancing
- Maximum 2-3 trades per week average
- Diversification across sectors

---

### Strategy 7: High-Frequency Statistical Arbitrage
**Source:** Reuters - High-Flyer Quant Fund Analysis  
**URL:** https://www.reuters.com/technology/artificial-intelligence/high-flyer-ai-quant-fund-behind-chinas-deepseek-2025-01-29/

**Description:** Quantitative hedge funds using AI models for high-frequency trading decisions. High-Flyer built 100 billion yuan portfolio using AI.

**Entry Rules:**
- Real-time signal generation from AI models
- Microsecond latency execution
- Multi-venue order routing

**Exit Rules:**
- Position holding times of seconds to minutes
- Automatic stop-loss at predetermined thresholds
- End-of-day position flattening

**Indicators Used:**
- Order book imbalance
- Price momentum micro-signals
- Cross-venue price discrepancies

**Performance Claims:**
- 100 billion yuan portfolio managed by AI
- Sub-millisecond execution capability
- Exploits microsecond-level inefficiencies

**Risk Management:**
- Real-time risk monitoring
- Position limits per strategy
- Automatic shutdown triggers
- Diversification across thousands of positions

---

### Strategy 8: Trend-Following CTA Strategy
**Source:** CNBC - Gold and Silver Quant Trading  
**URL:** https://www.cnbc.com/2026/02/09/gold-silver-price-volatility-quant-trading-algorithm-hedge-fund.html

**Description:** Trend-following funds use quantitative models to trade market moves. Applied to gold, silver, and other commodities during volatile periods.

**Entry Rules:**
- Price breakout above moving average
- Momentum confirmation
- Volume surge validation

**Exit Rules:**
- Trend reversal signal
- Trailing stop loss hit
- Momentum divergence

**Indicators Used:**
- Moving averages (20, 50, 200-day)
- MACD
- ADX for trend strength
- Volume analysis

**Performance Claims:**
- Profited from gold/silver volatility swings
- Systematic approach to volatile markets
- Machine learning enhanced signal generation

**Risk Management:**
- ATR-based position sizing
- Maximum portfolio heat limits
- Correlation monitoring across positions

---

### Strategy 9: Pairs Trading (Statistical Arbitrage)
**Source:** RADEX Markets - Trading Strategies Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Market-neutral strategy identifying two correlated assets and taking opposite positions - long underperformer, short outperformer.

**Entry Rules:**
- Calculate historical correlation (>0.8 preferred)
- Identify spread deviation from mean (>2 standard deviations)
- Enter when Z-score exceeds threshold

**Exit Rules:**
- Close when spread reverts to mean
- Stop loss at 3+ standard deviations
- Time-based exit if no convergence

**Indicators Used:**
- Correlation coefficient
- Cointegration tests
- Z-score calculations
- Bollinger Bands on spread

**Performance Claims:**
- Market-neutral returns
- Profits from convergence regardless of market direction
- Statistical edge from historical patterns

**Risk Management:**
- Correlation breakdown monitoring
- Maximum spread deviation limits
- Position sizing based on volatility

---

### Strategy 10: Mean Reversion Strategy
**Source:** RADEX Markets - Trading Strategies Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Strategy based on the idea that prices tend to return to their average over time. Best for range-bound markets.

**Entry Rules:**
- Price extends beyond 2 standard deviations from mean
- RSI indicates overbought (>70) or oversold (<30)
- Volume confirmation

**Exit Rules:**
- Price returns to moving average
- RSI normalizes (50 level)
- Time-based exit after 5-10 bars

**Indicators Used:**
- Bollinger Bands
- RSI (14-period)
- Simple Moving Average (20, 50)
- Volume indicators

**Performance Claims:**
- Predictable entries in sideways markets
- Effective for range trading
- Clear stop placement beyond extremes

**Risk Management:**
- Stop loss beyond 3 standard deviations
- Avoid trading during strong trends
- Position sizing based on volatility

---

## 3. Technical Analysis Strategies

### Strategy 11: Moving Average Crossover
**Source:** TradingView Pine Script Documentation  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Classic trend-following strategy using two moving averages. Entry when fast MA crosses above slow MA, exit on crossunder.

**Entry Rules:**
- Fast MA (e.g., 10-period) crosses above Slow MA (e.g., 20-period)
- Price above both MAs
- Volume confirmation

**Exit Rules:**
- Fast MA crosses below Slow MA
- Trailing stop below recent swing low
- Profit target at 2:1 risk-reward

**Indicators Used:**
- Simple Moving Average (10, 20, 50)
- Volume
- ATR for stop placement

**Performance Claims:**
- Captures major trends
- Simple to implement and understand
- Works across multiple timeframes

**Risk Management:**
- Stop loss below slow MA or recent low
- Position sizing: 1-2% risk per trade
- Maximum drawdown limit: 10%

---

### Strategy 12: Breakout Trading Strategy
**Source:** Investopedia - Mastering Breakout Trading  
**URL:** https://www.investopedia.com/articles/trading/08/trading-breakouts.asp

**Description:** Enter position when price breaks through defined support/resistance level with increased volume.

**Entry Rules:**
- Price closes above resistance (long) or below support (short)
- Volume above average (confirmation)
- Wait for retest of broken level (optional)

**Exit Rules:**
- Price returns below/above broken level (failure)
- Target at next resistance/support level
- Trailing stop activation after 75% to target

**Indicators Used:**
- Support/resistance levels
- Volume analysis
- Bollinger Bands
- ATR for target calculation

**Performance Claims:**
- Captures major price moves
- Clear entry/exit points
- High reward-to-risk potential

**Risk Management:**
- Stop loss below/above breakout level
- Position size based on stop distance
- Maximum 1% risk per trade

---

### Strategy 13: Fibonacci Retracement Strategy
**Source:** RADEX Markets - Trading Strategies Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Uses Fibonacci levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) to identify potential support/resistance and entry points.

**Entry Rules:**
- Identify swing high and low
- Draw Fibonacci retracement levels
- Enter at 38.2%, 50%, or 61.8% retracement
- Wait for price action confirmation (candlestick pattern)

**Exit Rules:**
- Take profit at previous swing high/low (100%)
- Stop loss below/above 78.6% level
- Partial profits at 61.8% extension

**Indicators Used:**
- Fibonacci retracement tool
- Candlestick patterns
- Volume
- RSI for confirmation

**Performance Claims:**
- Widely followed levels increase reliability
- Improved timing for entries
- Predictive support/resistance zones

**Risk Management:**
- Stop loss beyond 78.6% level
- Risk 1-2% per trade
- Avoid entries against major trend

---

### Strategy 14: Price Action Trading
**Source:** RADEX Markets - Trading Strategies Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Pure price-based trading without heavy reliance on indicators. Focuses on candlestick patterns, support/resistance, and chart formations.

**Entry Rules:**
- Pin bar at support/resistance
- Engulfing candle pattern
- Inside bar breakout
- Chart pattern completion (triangle, flag)

**Exit Rules:**
- Opposing price action signal
- Target at next key level
- Trailing stop below swing lows/highs

**Indicators Used:**
- Candlestick patterns
- Support/resistance zones
- Trendlines
- Chart patterns

**Performance Claims:**
- Clean charts reduce analysis paralysis
- Direct reading of market psychology
- Works across all markets and timeframes

**Risk Management:**
- Stop loss beyond pattern invalidation point
- Maximum 2% risk per setup
- Multiple timeframe confirmation

---

### Strategy 15: Gap Trading Strategy
**Source:** RADEX Markets - Trading Strategies Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Exploits price gaps between market close and open. Types: common, breakaway, runaway, exhaustion gaps.

**Entry Rules:**
- Identify gap type based on context
- Common gap: fade the gap (expect fill)
- Breakaway gap: trade in gap direction
- Volume confirmation for gap type

**Exit Rules:**
- Common gap: exit when gap fills
- Breakaway gap: trail stop or target next resistance
- Exhaustion gap: quick profit target

**Indicators Used:**
- Pre-market volume
- Gap size measurement
- Support/resistance levels
- Volume profile

**Performance Claims:**
- Profit from overnight moves
- Clear entry points at market open
- Quick profit potential

**Risk Management:**
- Stop loss beyond gap extreme
- Avoid holding through major news
- Position size for volatility

---

## 4. Momentum & Trend Following Strategies

### Strategy 16: Momentum Trading Strategy
**Source:** Investopedia - Momentum Trading Guide  
**URL:** https://www.investopedia.com/trading/introduction-to-momentum-trading/

**Description:** Buy assets showing strong recent performance, sell at peak. "Buy high, sell higher" - popularized by Richard Driehaus.

**Entry Rules:**
- Stock making new 52-week highs
- Strong volume (>150% of average)
- Positive earnings momentum
- RSI between 50-70 (not overbought)

**Exit Rules:**
- Momentum divergence
- Price falls below 20-day MA
- Volume decline
- Trailing stop at 10% below recent high

**Indicators Used:**
- 52-week highs
- Volume analysis
- RSI (avoid >70)
- MACD
- Rate of Change (ROC)

**Performance Claims:**
- Captures explosive price moves
- 50%+ returns possible in short periods
- Works best in bull markets

**Risk Management:**
- Tight stop losses essential
- Position size: 1-2% max
- Avoid chasing extended moves
- Cut losses quickly

---

### Strategy 17: RSI Momentum Strategy
**Source:** TradingView - RSI Strategy Example  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Uses RSI crossovers of the 50 level to identify momentum shifts. Long when RSI crosses above 50, short when crosses below.

**Entry Rules:**
- RSI (14) crosses above 50 (long)
- RSI (14) crosses below 50 (short)
- Price confirmation in direction

**Exit Rules:**
- Opposite RSI crossover
- Stop loss at recent swing point
- Profit target at next resistance/support

**Indicators Used:**
- RSI (14-period)
- Price action confirmation
- Volume

**Performance Claims:**
- Captures momentum shifts early
- Simple signal generation
- Works across multiple timeframes

**Risk Management:**
- Stop loss at swing high/low
- 1-2% risk per trade
- Filter with trend direction

---

### Strategy 18: Trend Following with ATR Stops
**Source:** TradingView Pine Script Examples  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Enter in direction of trend, use ATR-based trailing stops for exits. Dynamic stop placement based on volatility.

**Entry Rules:**
- Price above 50-day MA (long) or below (short)
- Pullback to 20-day MA
- Volume above average

**Exit Rules:**
- Trailing stop at 2-3x ATR from recent high/low
- Price closes below/above 50-day MA
- Time-based exit if no progress

**Indicators Used:**
- Moving Averages (20, 50)
- ATR (14-period)
- Volume
- ADX for trend strength

**Performance Claims:**
- Captures major trend moves
- Adapts to changing volatility
- Reduces whipsaws in choppy markets

**Risk Management:**
- ATR-based position sizing
- Maximum 2% risk per trade
- Correlation limits for multiple positions

---

### Strategy 19: Opening Range Breakout
**Source:** Investopedia - Day Trading Strategies  
**URL:** https://www.investopedia.com/articles/trading/06/daytradingretail.asp

**Description:** Trade breakouts of the first 15-30 minute range. Popularized by Toby Crabel.

**Entry Rules:**
- Define opening range (first 15-30 minutes)
- Enter long on break above range high
- Enter short on break below range low
- Volume confirmation

**Exit Rules:**
- Time-based exit (end of day)
- Stop loss at opposite side of range
- Profit target at 2-3x range width

**Indicators Used:**
- Opening range high/low
- Volume
- Pivot points

**Performance Claims:**
- Captures early day momentum
- High probability when range is narrow
- Clear risk/reward parameters

**Risk Management:**
- Stop loss at range opposite side
- Maximum 1% risk per trade
- Avoid trading on major news days

---

### Strategy 20: News-Based Momentum Trading
**Source:** RADEX Markets - News Trading Strategy  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Trade sharp volatility around economic releases and news events.

**Entry Rules:**
- Monitor economic calendar
- Enter on news surprise (deviation from forecast)
- Use limit orders to control slippage
- Wait for initial volatility to settle

**Exit Rules:**
- Quick profit target (momentum fades fast)
- Time-based exit (minutes to hours)
- Stop loss at pre-news level

**Indicators Used:**
- Economic calendar
- News sentiment analysis
- Pre-news support/resistance
- Volume spike detection

**Performance Claims:**
- Quick profits from volatility
- Frequent opportunities
- Short holding periods

**Risk Management:**
- Wider stops due to volatility
- Smaller position sizes
- Avoid holding through unknown events

---

## 5. Mean Reversion & Statistical Arbitrage

### Strategy 21: Bollinger Bands Mean Reversion
**Source:** RADEX Markets - Mean Reversion Strategy  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Trade price extremes relative to Bollinger Bands, expecting reversion to mean.

**Entry Rules:**
- Price touches or exceeds lower band (long)
- Price touches or exceeds upper band (short)
- RSI confirmation (oversold/overbought)
- Volume spike

**Exit Rules:**
- Price returns to middle band (20-period MA)
- Opposite band touched
- Time-based exit (5-10 bars)

**Indicators Used:**
- Bollinger Bands (20, 2)
- RSI (14)
- Volume
- Stochastic oscillator

**Performance Claims:**
- High win rate in range-bound markets
- Clear entry/exit points
- Works on multiple timeframes

**Risk Management:**
- Stop loss beyond outer band
- Avoid trading strong trends
- Position size for volatility

---

### Strategy 22: Statistical Arbitrage (Sector Pairs)
**Source:** Seeking Alpha - Pairs Trading  
**URL:** https://seekingalpha.com/article/4226165-trading-strategy-beat-s-and-p-500

**Description:** Trade pairs of stocks within same sector based on historical correlation.

**Entry Rules:**
- Calculate Z-score of spread
- Enter when Z-score > 2 or < -2
- Ensure correlation > 0.8

**Exit Rules:**
- Close when Z-score returns to 0
- Stop loss at Z-score > 3 or < -3
- Time-based exit after 20 days

**Indicators Used:**
- Correlation coefficient
- Z-score calculation
- Cointegration test
- Spread volatility

**Performance Claims:**
- Market-neutral returns
- Reduced portfolio volatility
- Statistical edge

**Risk Management:**
- Correlation breakdown monitoring
- Maximum spread deviation
- Equal dollar weighting

---

### Strategy 23: RSI Divergence Strategy
**Source:** Investopedia - Technical Analysis Strategies  
**URL:** https://www.investopedia.com/articles/active-trading/020915/mustknow-simple-effective-exit-trading-strategies.asp

**Description:** Trade divergences between price and RSI for reversal signals.

**Entry Rules:**
- Bullish divergence: price lower low, RSI higher low
- Bearish divergence: price higher high, RSI lower high
- Volume confirmation
- Support/resistance alignment

**Exit Rules:**
- RSI reaches overbought/oversold
- Price reaches target level
- Stop loss beyond recent swing

**Indicators Used:**
- RSI (14)
- Price action
- Volume
- Support/resistance levels

**Performance Claims:**
- Early reversal signals
- High reward-to-risk ratio
- Works across timeframes

**Risk Management:**
- Stop loss beyond divergence point
- Wait for confirmation candle
- 1-2% risk per trade

---

### Strategy 24: VWAP Reversion Strategy
**Source:** Bloomberg Intelligence - Institutional Trading Study  
**URL:** https://www.bloomberg.com/professional/insights/trading/european-institutional-equity-trading-study-technology/

**Description:** Trade deviations from VWAP expecting institutional order flow to push price back toward average.

**Entry Rules:**
- Price extends >1% above/below VWAP
- Volume above average
- Time of day consideration (avoid open/close)

**Exit Rules:**
- Price returns to VWAP
- Stop loss at 2% from VWAP
- Time-based exit (end of session)

**Indicators Used:**
- VWAP
- Volume
- Standard deviation bands around VWAP
- Time of day

**Performance Claims:**
- High probability intraday trades
- Institutional flow alignment
- Clear risk parameters

**Risk Management:**
- Stop loss at 2x deviation
- Avoid trading during trend days
- Position size for intraday volatility

---

### Strategy 25: Calendar Spread Arbitrage
**Source:** Investopedia - Arbitrage Trading  
**URL:** https://www.investopedia.com/terms/t/trading-strategy.asp

**Description:** Trade price discrepancies between different expiration dates of same underlying.

**Entry Rules:**
- Identify mispriced spreads
- Buy underpriced month, sell overpriced
- Minimum spread profit threshold

**Exit Rules:**
- Spread converges to fair value
- Expiration of near month
- Stop loss at 2x expected profit

**Indicators Used:**
- Futures curve analysis
- Implied carry calculations
- Historical spread ranges

**Performance Claims:**
- Low risk arbitrage
- Consistent small profits
- Market-neutral

**Risk Management:**
- Maximum spread deviation limits
- Position limits per spread
- Correlation monitoring

---

## 6. Options & Volatility Strategies

### Strategy 26: Long Straddle (Volatility Play)
**Source:** CNBC - Options Strategy for Volatile Swings  
**URL:** https://www.cnbc.com/2025/02/06/an-options-strategy-to-capitalize-on-volatile-stock-swings-in-either-direction.html

**Description:** Buy both call and put at same strike to profit from large moves in either direction.

**Entry Rules:**
- Expecting significant volatility
- Buy ATM call and put
- Enter before major event/earnings
- Implied volatility relatively low

**Exit Rules:**
- Take profit at 50-100% gain on either leg
- Exit before expiration (time decay)
- Cut loss at 50% of premium paid

**Indicators Used:**
- Implied volatility rank
- Historical volatility
- Expected move calculation
- Options Greeks

**Performance Claims:**
- Profit from large moves either direction
- No directional bias required
- Defined risk (premium paid)

**Risk Management:**
- Maximum loss = premium paid
- Position size: 1-2% of portfolio
- Time decay management

---

### Strategy 27: Iron Condor
**Source:** CNBC - Options Strategies  
**URL:** https://www.cnbc.com/2024/09/27/using-options-to-trade-an-index-thats-become-a-swing-traders-dream.html

**Description:** Sell OTM call spread and OTM put spread to profit from range-bound markets.

**Entry Rules:**
- Market in trading range
- Sell call spread above resistance
- Sell put spread below support
- Collect net credit

**Exit Rules:**
- Buy back at 50% of max profit
- Close if underlying breaches short strikes
- Exit before expiration

**Indicators Used:**
- Support/resistance levels
- Implied volatility
- Delta of short options
- Probability of profit

**Performance Claims:**
- High probability of profit (60-70%)
- Profit in sideways markets
- Defined risk and reward

**Risk Management:**
- Maximum risk = spread width - credit
- Position size: 1-2% per trade
- Adjustment plan if tested

---

### Strategy 28: VIX Hedging Strategy
**Source:** CNBC - Portfolio Protection  
**URL:** https://www.cnbc.com/2018/02/07/protect-your-portfolio-from-wild-stock-market-swings.html

**Description:** Use VIX-tracking ETFs as portfolio hedge during volatile periods.

**Entry Rules:**
- Portfolio at risk
- VIX at relatively low levels (<20)
- Buy VIX calls or VIXY/VIXM ETFs
- Small allocation (1-3%)

**Exit Rules:**
- VIX spike to high levels (>30)
- Portfolio stabilizes
- Time-based exit (30-60 days)

**Indicators Used:**
- VIX level
- VIX term structure
- Portfolio beta
- Correlation analysis

**Performance Claims:**
- Portfolio insurance during crashes
- Negative correlation to stocks
- Asymmetric payoff potential

**Risk Management:**
- Small allocation (hedge, not speculation)
- Roll positions if needed
- Accept premium decay as insurance cost

---

### Strategy 29: Covered Call Writing
**Source:** Investopedia - Exit Strategies  
**URL:** https://www.investopedia.com/articles/active-trading/020915/mustknow-simple-effective-exit-trading-strategies.asp

**Description:** Own underlying stock, sell OTM calls to generate income.

**Entry Rules:**
- Own 100+ shares of stock
- Sell call 1-2 strikes OTM
- 30-45 days to expiration
- Collect minimum 1-2% premium

**Exit Rules:**
- Buy back at 50% profit
- Let expire if OTM
- Roll up and out if ITM and want to keep stock

**Indicators Used:**
- Implied volatility
- Delta of options
- Support/resistance
- Earnings calendar

**Performance Claims:**
- Enhanced returns in sideways markets
- Downside protection (premium collected)
- Regular income generation

**Risk Management:**
- Willing to sell stock at strike
- Avoid earnings periods
- Diversify across positions

---

### Strategy 30: Put Selling (Cash-Secured Puts)
**Source:** Seeking Alpha - Income Strategies  
**URL:** https://seekingalpha.com/article/4864969-qqq-7-backtests-to-build-generational-wealth

**Description:** Sell OTM puts to collect premium, potentially acquire stock at discount.

**Entry Rules:**
- Want to own stock at lower price
- Sell put at support level
- 30-45 DTE
- Collect 1-2% premium

**Exit Rules:**
- Buy back at 50% profit
- Take assignment if ITM at expiration
- Roll down and out if tested

**Indicators Used:**
- Support levels
- Implied volatility rank
- Delta (0.30 or less)
- Fundamental analysis

**Performance Claims:**
- Income generation
- Potential stock acquisition at discount
- High probability if done correctly

**Risk Management:**
- Cash secured (have buying power)
- Only sell on stocks willing to own
- Position size appropriately

---

## 7. Risk Management Frameworks

### Strategy 31: Fixed Fractional Position Sizing
**Source:** Investopedia - Day Trading Risk Management  
**URL:** https://www.investopedia.com/articles/trading/06/daytradingretail.asp

**Description:** Risk fixed percentage of account per trade (typically 1-2%).

**Entry Rules:**
- Calculate position size: (Account Risk $) / (Stop Loss $)
- Account Risk = Account Value × Risk % (1-2%)
- Enter full calculated position

**Exit Rules:**
- Stop loss at predetermined level
- Take profit at 2-3x risk
- Trailing stop after 1R profit

**Indicators Used:**
- Account equity
- Stop loss distance
- Risk/reward ratio

**Performance Claims:**
- Prevents catastrophic losses
- Compounding benefits
- Psychological ease

**Risk Management:**
- Maximum 2% risk per trade
- Maximum 6% risk per day
- Weekly loss limits

---

### Strategy 32: Kelly Criterion Sizing
**Source:** Investopedia - Position Sizing  
**URL:** https://www.investopedia.com/articles/trading/06/daytradingretail.asp

**Description:** Mathematical formula to determine optimal bet size based on win rate and win/loss ratio.

**Entry Rules:**
- Calculate Kelly %: (Win Rate × Avg Win - Loss Rate × Avg Loss) / Avg Win
- Use half-Kelly or quarter-Kelly for safety
- Size position accordingly

**Exit Rules:**
- Standard stop loss
- Adjust size as statistics update

**Indicators Used:**
- Historical win rate
- Average win amount
- Average loss amount
- Expectancy

**Performance Claims:**
- Mathematically optimal growth
- Maximizes long-term returns
- Accounts for edge size

**Risk Management:**
- Use fractional Kelly (1/4 to 1/2)
- Minimum 100 trade sample
- Regular recalculation

---

### Strategy 33: ATR-Based Position Sizing
**Source:** TradingView Pine Script Documentation  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Adjust position size based on volatility (ATR) to normalize risk.

**Entry Rules:**
- Calculate ATR (14-period)
- Position Size = (Account × Risk%) / (ATR × Multiplier)
- Higher volatility = smaller position

**Exit Rules:**
- Stop loss at 2-3x ATR
- Trailing stop at 2x ATR

**Indicators Used:**
- ATR (14)
- Account equity
- Volatility percentile

**Performance Claims:**
- Consistent dollar risk per trade
- Adapts to market conditions
- Reduces position size in volatile periods

**Risk Management:**
- Fixed dollar risk regardless of volatility
- Maximum position size limits
- Correlation adjustments

---

### Strategy 34: Tiered Exit Strategy
**Source:** Investopedia - Scaling Exit Strategies  
**URL:** https://www.investopedia.com/articles/active-trading/020915/mustknow-simple-effective-exit-trading-strategies.asp

**Description:** Scale out of positions in pieces to capture different profit targets.

**Entry Rules:**
- Full position entry
- Pre-define three exit levels

**Exit Rules:**
- Exit 1/3 at 75% of risk-reward distance
- Exit 1/3 at full target
- Trail stop on final 1/3

**Indicators Used:**
- Risk-reward calculations
- Support/resistance levels
- Trailing stop mechanisms

**Performance Claims:**
- Locks in partial profits
- Lets winners run
- Improves risk-adjusted returns

**Risk Management:**
- Break-even stop after first exit
- Never risk more than planned
- Adjust for slippage

---

### Strategy 35: Maximum Drawdown Circuit Breaker
**Source:** TradingView - Risk Management Functions  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Automatically stop trading if drawdown exceeds predetermined threshold.

**Entry Rules:**
- Define maximum acceptable drawdown (e.g., 10%)
- Monitor equity curve continuously
- Normal entry rules apply when active

**Exit Rules:**
- Close all positions if drawdown limit hit
- Stop trading for defined period
- Review and reset before resuming

**Indicators Used:**
- Equity curve
- Peak equity value
- Current drawdown calculation

**Performance Claims:**
- Prevents ruin
- Forces trading breaks
- Preserves capital

**Risk Management:**
- 10% maximum drawdown typical
- 5% for conservative traders
- Daily, weekly, monthly limits

---

## 8. Multi-Asset & Macro Strategies

### Strategy 36: 60/40 Portfolio Rebalancing
**Source:** BlackRock Investment Directions 2025  
**URL:** https://www.blackrock.com/us/financial-professionals/insights/investment-directions-fall-2025

**Description:** Traditional portfolio allocation with periodic rebalancing to target weights.

**Entry Rules:**
- Allocate 60% equities, 40% bonds
- Use low-cost index ETFs
- Quarterly or threshold-based rebalancing

**Exit Rules:**
- Rebalance when allocation drifts >5%
- Trim winners, add to losers
- Tax-loss harvesting in taxable accounts

**Indicators Used:**
- Portfolio weights
- Correlation analysis
- Risk parity metrics

**Performance Claims:**
- Diversification benefits
- Risk-adjusted returns
- Simple to implement

**Risk Management:**
- Maximum single asset class limit
- Geographic diversification
- Regular rebalancing discipline

---

### Strategy 37: Risk Parity Strategy
**Source:** BlackRock - Alternative Investments  
**URL:** https://www.blackrock.com/us/financial-professionals/insights/investment-directions-fall-2025

**Description:** Allocate based on risk contribution rather than capital, targeting equal risk from all assets.

**Entry Rules:**
- Calculate volatility of each asset
- Inverse volatility weighting
- Leverage lower volatility assets

**Exit Rules:**
- Rebalance when risk contributions diverge
- Adjust for changing correlations
- Risk-off mode during stress

**Indicators Used:**
- Volatility (realized and implied)
- Correlation matrix
- Risk contribution calculations
- VaR/CVaR

**Performance Claims:**
- More stable returns
- Better risk-adjusted performance
- Diversification in crisis periods

**Risk Management:**
- Leverage limits
- Correlation stress testing
- Maximum volatility target

---

### Strategy 38: Global Macro Strategy
**Source:** M&G Investment Perspectives 2025  
**URL:** https://www.mandg.com/investments/institutional/en-gb/insights/2024/q4/investment-perspectives

**Description:** Top-down approach based on macroeconomic trends, policy changes, and global themes.

**Entry Rules:**
- Identify macro themes (inflation, rates, growth)
- Position in assets benefiting from theme
- Use ETFs, futures, forex

**Exit Rules:**
- Theme plays out or invalidates
- Policy shift signals
- Risk-off environment

**Indicators Used:**
- Economic data (GDP, inflation, employment)
- Central bank policy
- Currency trends
- Commodity prices

**Performance Claims:**
- Uncorrelated to traditional markets
- Exploits macro inefficiencies
- Flexible across asset classes

**Risk Management:**
- Theme concentration limits
- Stop losses on individual positions
- Correlation monitoring

---

### Strategy 39: Factor Investing Strategy
**Source:** BlackRock - Factor Exposures  
**URL:** https://www.blackrock.com/us/financial-professionals/insights/investment-directions-fall-2025

**Description:** Target specific risk factors (value, momentum, quality, low volatility) for enhanced returns.

**Entry Rules:**
- Screen for factor exposure
- Rank securities by factor score
- Long high-scoring, short low-scoring

**Exit Rules:**
- Factor rebalancing (monthly/quarterly)
- Factor performance deterioration
- Risk model constraints

**Indicators Used:**
- Value metrics (P/E, P/B)
- Momentum (12-month returns)
- Quality (ROE, earnings stability)
- Low volatility (beta, std dev)

**Performance Claims:**
- Systematic exposure to rewarded factors
- Diversification across factors
- Potential for alpha generation

**Risk Management:**
- Factor correlation monitoring
- Maximum factor exposure limits
- Risk model constraints

---

### Strategy 40: Liquid Alternatives Strategy
**Source:** BlackRock - Diversification Strategies  
**URL:** https://www.blackrock.com/us/financial-professionals/insights/investment-directions-fall-2025

**Description:** Use liquid alternative investments (long/short, managed futures, multi-strategy) for diversification.

**Entry Rules:**
- Allocate to liquid alt funds/ETFs
- Target low correlation to stocks/bonds
- Diversify across alt strategies

**Exit Rules:**
- Rebalance to target allocation
- Performance-based adjustments
- Correlation changes

**Indicators Used:**
- Correlation analysis
- Sharpe ratios
- Maximum drawdown
- Sortino ratio

**Performance Claims:**
- Uncorrelated returns
- Downside protection
- Portfolio volatility reduction

**Risk Management:**
- Maximum alt allocation (typically 10-20%)
- Strategy diversification
- Liquidity monitoring

---

## 9. Day Trading & Scalping Strategies

### Strategy 41: Scalping Strategy
**Source:** RADEX Markets - Scalping Guide  
**URL:** https://www.radexmarkets.com/en/News/NewsDetail?p=NG9nMEltSWZhdGs9

**Description:** Very short-term trading seeking small profits from minor price movements.

**Entry Rules:**
- Tight spreads required
- High volume stocks/forex pairs
- Enter on micro-breakouts
- Use 1-5 minute charts

**Exit Rules:**
- Quick profit target (few ticks/pips)
- Immediate stop loss
- Time-based exit (minutes)

**Indicators Used:**
- Level 2/order book
- Time and sales
- Moving averages (5, 9)
- Tick charts

**Performance Claims:**
- High win rate required
- Small consistent gains
- Compounding potential

**Risk Management:**
- Tight stops (few cents/pips)
- Maximum daily loss limit
- High win rate essential (>60%)

---

### Strategy 42: Range Trading (Intraday)
**Source:** Britannica - Day Trading vs Swing Trading  
**URL:** https://www.britannica.com/money/day-trading-vs-swing-trading

**Description:** Trade within defined intraday support and resistance levels.

**Entry Rules:**
- Identify morning range
- Buy at support, sell at resistance
- Volume confirmation
- Avoid breakouts

**Exit Rules:**
- Opposite side of range
- Stop loss beyond range
- Time-based exit (end of day)

**Indicators Used:**
- Pivot points
- Volume profile
- VWAP
- Opening range

**Performance Claims:**
- High probability in sideways markets
- Clear risk parameters
- Multiple opportunities daily

**Risk Management:**
- Stop loss beyond range
- Avoid trading breakouts
- Position size for range width

---

### Strategy 43: Fading Strategy
**Source:** Investopedia - Day Trading Tips  
**URL:** https://www.investopedia.com/articles/trading/06/daytradingretail.asp

**Description:** Short rapid moves upward, expecting quick reversal.

**Entry Rules:**
- Sharp upward spike
- Overbought conditions
- Resistance level reached
- Volume spike

**Exit Rules:**
- Buyers step back in
- Support level reached
- Time-based exit

**Indicators Used:**
- RSI > 70
- Bollinger Bands
- Volume
- Candlestick patterns

**Performance Claims:**
- Exploits emotional buying
- Quick profits
- High risk/reward

**Risk Management:**
- Tight stop loss
- Quick exit if wrong
- Avoid strong trends

---

### Strategy 44: Momentum Scalping
**Source:** Investopedia - Momentum Day Trading  
**URL:** https://www.investopedia.com/articles/trading/06/daytradingretail.asp

**Description:** Trade stocks showing strong intraday momentum.

**Entry Rules:**
- Stock up >2% on day
- Breaking intraday highs
- Volume >2x average
- Positive news catalyst

**Exit Rules:**
- Momentum wanes
- New intraday low
- End of day

**Indicators Used:**
- Real-time scanners
- Volume analysis
- Level 2 quotes
- Time and sales

**Performance Claims:**
- Exploits intraday trends
- High volatility = opportunity
- Multiple trades daily

**Risk Management:**
- Tight trailing stops
- Maximum loss per trade
- Avoid reversal patterns

---

### Strategy 45: VWAP Scalping
**Source:** Bloomberg - Institutional VWAP Usage  
**URL:** https://www.bloomberg.com/professional/insights/trading/european-institutional-equity-trading-study-technology/

**Description:** Use VWAP as dynamic support/resistance for intraday scalping.

**Entry Rules:**
- Price pulls back to VWAP
- Volume confirmation
- Trend alignment
- Candlestick confirmation

**Exit Rules:**
- Next resistance/support
- VWAP violation
- Quick profit target

**Indicators Used:**
- VWAP
- Standard deviation bands
- Volume
- 5-minute chart

**Performance Claims:**
- Aligns with institutional flow
- High probability bounces
- Clear reference point

**Risk Management:**
- Stop loss beyond VWAP
- Small position sizes
- Quick exits if wrong

---

## 10. Swing Trading Strategies

### Strategy 46: Swing Trading with Moving Averages
**Source:** Investopedia - Swing Trading Guide  
**URL:** https://www.investopedia.com/articles/trading/06/dayofswingtrader.asp

**Description:** Hold positions for days to weeks, capturing larger price swings.

**Entry Rules:**
- Pullback to 20 or 50-day MA in uptrend
- Bullish candlestick pattern
- Volume confirmation
- Sector strength

**Exit Rules:**
- Target at next resistance
- Stop loss below MA
- Time-based exit (1-4 weeks)

**Indicators Used:**
- Moving averages (20, 50)
- RSI
- MACD
- Volume

**Performance Claims:**
- Captures bigger moves than day trading
- Less time intensive
- Better for part-time traders

**Risk Management:**
- Stop loss at swing low
- Position size for overnight risk
- Earnings avoidance

---

### Strategy 47: Channel Trading
**Source:** Investopedia - Swing Trading Patterns  
**URL:** https://www.investopedia.com/articles/trading/06/dayofswingtrader.asp

**Description:** Trade within established price channels.

**Entry Rules:**
- Identify parallel trendlines
- Buy at lower channel
- Sell at upper channel
- Volume confirmation

**Exit Rules:**
- Opposite channel boundary
- Channel break (stop loss)
- Time-based exit

**Indicators Used:**
- Trendlines
- Channel width
- Volume
- RSI for extremes

**Performance Claims:**
- Clear entry/exit points
- High probability in trends
- Defined risk

**Risk Management:**
- Stop loss beyond channel
- Reduce size near extremes
- Watch for breakouts

---

### Strategy 48: Flag/Pennant Pattern Trading
**Source:** Investopedia - Chart Patterns  
**URL:** https://www.investopedia.com/articles/trading/06/dayofswingtrader.asp

**Description:** Trade continuation patterns after strong moves.

**Entry Rules:**
- Strong prior move (flagpole)
- Consolidation in flag/pennant
- Breakout from pattern
- Volume surge

**Exit Rules:**
- Measured move target
- Trailing stop
- Pattern failure

**Indicators Used:**
- Pattern recognition
- Volume analysis
- Fibonacci extensions
- ATR for stops

**Performance Claims:**
- High probability continuation
- Clear measured targets
- Good risk/reward

**Risk Management:**
- Stop below pattern
- Position size for measured move
- Partial profits at target

---

### Strategy 49: Sector Rotation Strategy
**Source:** Investopedia - Swing Trading Fundamentals  
**URL:** https://www.investopedia.com/articles/trading/06/dayofswingtrader.asp

**Description:** Rotate capital between sectors based on relative strength.

**Entry Rules:**
- Identify strongest sectors
- Buy strongest stocks in sector
- Use relative strength ranking

**Exit Rules:**
- Sector weakens relative to market
- Rotation to new sector
- Individual stock stop loss

**Indicators Used:**
- Relative strength
- Sector ETFs performance
- Economic cycle analysis
- Momentum indicators

**Performance Claims:**
- Aligns with macro trends
- Outperformance potential
- Risk through diversification

**Risk Management:**
- Sector exposure limits
- Stop losses on individual positions
- Correlation monitoring

---

### Strategy 50: Earnings Swing Strategy
**Source:** Investopedia - Swing Trading Catalysts  
**URL:** https://www.investopedia.com/articles/trading/06/dayofswingtrader.asp

**Description:** Trade around earnings announcements for volatility expansion.

**Entry Rules:**
- Earnings in 1-2 weeks
- Technical setup (flag, consolidation)
- Positive earnings surprise history
- Sector tailwinds

**Exit Rules:**
- Before earnings (conservative)
- Day after earnings (aggressive)
- Stop loss on technical breakdown

**Indicators Used:**
- Earnings calendar
- Historical earnings moves
- Implied volatility
- Technical patterns

**Performance Claims:**
- Volatility expansion profits
- Catalyst-driven moves
- High reward potential

**Risk Management:**
- Position size for volatility
- Consider options for defined risk
- Never hold through earnings (unless sized appropriately)

---

## 11. Advanced & Hybrid Strategies

### Strategy 51: Dollar-Cost Averaging (DCA) with Timing
**Source:** Seeking Alpha - QQQ Backtest Analysis  
**URL:** https://seekingalpha.com/article/4864969-qqq-7-backtests-to-build-generational-wealth

**Description:** Regular investment with opportunistic additional purchases on dips.

**Entry Rules:**
- Regular periodic investment
- Additional purchases on 5-10% dips
- Increase size on larger corrections (15%+)

**Exit Rules:**
- Long-term hold (years)
- Rebalancing annually
- Partial profit-taking in extremes

**Indicators Used:**
- Drawdown from highs
- Valuation metrics
- Moving averages (200-day)

**Performance Claims:**
- Reduces timing risk
- Lower average cost basis
- Psychological benefits

**Risk Management:**
- Only invest funds not needed for 5+ years
- Maximum single allocation limit
- Diversification across assets

---

### Strategy 52: Leveraged ETF Momentum Strategy
**Source:** Seeking Alpha - TQQQ Strategy  
**URL:** https://seekingalpha.com/article/4864969-qqq-7-backtests-to-build-generational-wealth

**Description:** Use leveraged ETFs (TQQQ) during strong uptrends, switch to cash/bonds in downtrends.

**Entry Rules:**
- QQQ above 200-day MA
- Gradual conversion from QQQ to TQQQ
- Scale in during confirmed uptrends

**Exit Rules:**
- QQQ below 200-day MA
- Convert TQQQ back to QQQ or cash
- Stop loss at 20% portfolio drawdown

**Indicators Used:**
- 200-day moving average
- Trend strength (ADX)
- Volatility (VIX)

**Performance Claims:**
- Amplified returns in uptrends
- Backtest shows strong long-term performance
- Volatility tax management through timing

**Risk Management:**
- Maximum TQQQ allocation (e.g., 50%)
- Volatility decay awareness
- Quick exit on trend change

---

### Strategy 53: Multi-Timeframe Strategy
**Source:** TradingView - Strategy Best Practices  
**URL:** https://www.tradingview.com/pine-script-docs/concepts/strategies/

**Description:** Align trades across multiple timeframes for higher probability setups.

**Entry Rules:**
- Daily trend alignment (higher timeframe)
- 4-hour setup
- 1-hour entry trigger
- All timeframes aligned

**Exit Rules:**
- Lower timeframe exit signal
- Higher timeframe trend change
- Trailing stop on lower timeframe

**Indicators Used:**
- Moving averages on all timeframes
- Trend indicators (MACD, ADX)
- Support/resistance on multiple timeframes

**Performance Claims:**
- Higher probability trades
- Better risk/reward
- Filters false signals

**Risk Management:**
- Stop loss on entry timeframe
- Position size based on higher timeframe volatility
- Maximum timeframe divergence limits

---

### Strategy 54: Sentiment-Based Strategy
**Source:** ResearchGate - Backtesting Sentiment Signals  
**URL:** https://www.researchgate.net/publication/393476731_Backtesting_Sentiment_Signals_for_Trading

**Description:** Use sentiment analysis from news, social media, and positioning data.

**Entry Rules:**
- Extreme negative sentiment (contrarian long)
- Extreme positive sentiment (contrarian short)
- Sentiment divergence from price

**Exit Rules:**
- Sentiment normalization
- Sentiment extreme in opposite direction
- Time-based exit

**Indicators Used:**
- Put/call ratio
- VIX
- AAII sentiment survey
- Social media sentiment
- News sentiment scores

**Performance Claims:**
- Contrarian edge
- Early reversal signals
- Uncorrelated to technicals

**Risk Management:**
- Sentiment can stay extreme
- Position size for contrarian risk
- Confirmation from price action

---

### Strategy 55: Machine Learning Enhanced Strategy
**Source:** Bloomberg - AI Trading Adoption  
**URL:** https://www.bloomberg.com/professional/insights/artificial-intelligence/eet-2025-technology-algo-and-tca-trends/

**Description:** Use ML models to predict price movements and optimize execution.

**Entry Rules:**
- ML model signal > threshold
- Feature alignment (technical, fundamental, sentiment)
- Probability score > 70%

**Exit Rules:**
- Model signal reversal
- Probability drops below 50%
- Time-based exit

**Indicators Used:**
- ML model predictions
- Feature importance metrics
- Confidence intervals
- Prediction accuracy tracking

**Performance Claims:**
- 26% expect AI execution decisions within 2 years
- Pattern recognition beyond human capability
- Adaptive to changing markets

**Risk Management:**
- Model validation on out-of-sample data
- Maximum model risk allocation
- Human oversight of decisions

---

## Summary Statistics

| Category | Number of Strategies |
|----------|---------------------|
| Institutional Algorithmic | 5 |
| Quantitative & Systematic | 5 |
| Technical Analysis | 5 |
| Momentum & Trend Following | 5 |
| Mean Reversion & Stat Arb | 5 |
| Options & Volatility | 5 |
| Risk Management | 5 |
| Multi-Asset & Macro | 5 |
| Day Trading & Scalping | 5 |
| Swing Trading | 5 |
| Advanced & Hybrid | 5 |
| **TOTAL** | **55** |

---

## Key Sources Referenced

1. **Bloomberg Intelligence** - Institutional equity trading studies, algo adoption, AI in trading
2. **Reuters** - Quant fund analysis, hedge fund strategies, market structure
3. **Financial Times** - Quant investing trends, systematic trading
4. **CNBC** - Options strategies, portfolio protection, retail trading
5. **Investopedia** - Comprehensive trading strategy guides, risk management
6. **Seeking Alpha** - Quant portfolio strategies, backtesting results, factor investing
7. **TradingView** - Pine Script strategies, backtesting documentation, technical analysis
8. **RADEX Markets** - Trading strategy compilation, entry/exit rules
9. **BlackRock** - Institutional portfolio strategies, factor investing, alternatives
10. **M&G Investments** - Macro strategies, sector allocation

---

*Document compiled: February 2026*  
*Research period: 2024-2025*  
*Total strategies documented: 55*
