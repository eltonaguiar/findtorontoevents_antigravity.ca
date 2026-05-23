# COMPREHENSIVE STRATEGY CATALOG
## findtorontoevents.ca - All Trading Strategies by Asset Class

**Crawl Date:** February 17, 2026  
**Source:** findtorontoevents.ca

---

## 1. STOCKS (Large/Mid/Small Cap)

### 1.1 Crown Jewel / Consolidated Consensus Picks
- **Asset Class:** Stocks (Large/Mid/Small Cap)
- **Data Source:** Yahoo Finance v8 chart API
- **Update Frequency:** Daily (GitHub Actions weekdays 23:30 UTC)
- **Testing Status:** FORWARD-TESTED (Live tracking since Feb 2026)
- **Win Rate Claim:** Pending (65 open positions, first closures expected ~Feb 24, 2026)
- **Sharpe Ratio:** Pending
- **Asset-Specific:** Yes - US Stocks only
- **Description:** Multi-algorithm consensus system using 20 algorithms. Creates positions when 2+ algorithms agree. TP: +8%, SL: -4%, Max Hold: 14 days.

### 1.2 Challenger Bot (Smart Money Consensus)
- **Asset Class:** Stocks (12 mega-cap symbols)
- **Data Sources:** SEC EDGAR (13F + Form 4), Finnhub API (analyst ratings), Reddit API (WSB sentiment)
- **Update Frequency:** Daily (weekdays 6AM + Sunday 9AM EST)
- **Testing Status:** LIVE (Paper trading)
- **Win Rate Claim:** 0% (2 trades, 2 losses - FIX DEPLOYED Feb 12 with regime gating)
- **Sharpe Ratio:** N/A (insufficient data)
- **Asset-Specific:** Yes - 12 mega-cap stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, JPM, BAC, WMT, XOM, NFLX, JNJ)
- **Description:** Algorithm #20 in Live Monitor. Uses 4-pillar consensus: Analyst (30%), Insider MSPR (25%), 13F Institutional (25%), WSB Sentiment (20%).

### 1.3 Alpha Factor Suite
- **Asset Class:** Stocks (50 liquid US stocks)
- **Data Source:** Yahoo Finance
- **Update Frequency:** Daily (after market close via GitHub Actions)
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - 50-stock universe
- **Description:** 6 factor families (Momentum, Quality, Value, Earnings, Volatility, Growth) with regime-adjusted weights. 9 strategies generate picks daily.

### 1.4 Algorithm Competition Arena - Meta Learner (God-Mode)
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance (yfinance)
- **Update Frequency:** Weekly auto-refresh
- **Testing Status:** BACKTESTED (252 trading days) + FORWARD-TESTED (daily picks)
- **Win Rate Claim:** +23.69% return (beat SPY +13.12%)
- **Sharpe Ratio:** 1.409
- **Asset-Specific:** Yes - S&P 500
- **Description:** Regime-aware ensemble aggregating all 11 sub-strategies.

### 1.5 Algorithm Competition Arena - Classic Momentum
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED (252 trading days)
- **Win Rate Claim:** Jegadeesh & Titman 6-month momentum
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy top-K past winners by 6-month return with skip-month.

### 1.6 Algorithm Competition Arena - Trend Following
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy stocks above 50/200 MA with strong trend strength.

### 1.7 Algorithm Competition Arena - Breakout Momentum
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy stocks near 52-week highs with volume confirmation.

### 1.8 Algorithm Competition Arena - Bollinger Mean Reversion
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy oversold (below lower BB), sell overbought.

### 1.9 Algorithm Competition Arena - Short-Term Reversal
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy 5-day losers (oversold bounce), hold 3-5 days.

### 1.10 Algorithm Competition Arena - Quality Compounders
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** High ROE/ROIC, stable margins, low drawdown.

### 1.11 Algorithm Competition Arena - Value + Quality
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Buy undervalued stocks with quality filter.

### 1.12 Algorithm Competition Arena - Dividend Aristocrats
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** 25+ years of consecutive dividend increases.

### 1.13 Algorithm Competition Arena - Earnings Drift (PEAD)
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Post-earnings drift proxy with MACD confirmation.

### 1.14 Algorithm Competition Arena - Consecutive Beats
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Stocks with 3+ consecutive positive return periods.

### 1.15 Algorithm Competition Arena - ML Ranker (LightGBM)
- **Asset Class:** S&P 500 Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Composite ranking combining multiple indicators using LightGBM.

### 1.16 Horizon Picks - Quick (2 weeks)
- **Asset Class:** Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Daily
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** TP +10%, SL -5%, Max Hold: 14 days

### 1.17 Horizon Picks - Swing (2 months)
- **Asset Class:** Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Daily
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** TP +20%, SL -8%, Max Hold: 60 days

### 1.18 Horizon Picks - Long-term (1 year)
- **Asset Class:** Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Daily
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** TP +40%, SL -15%, Max Hold: 252 days

### 1.19 Top Picks (Daily Stock Recommendations)
- **Asset Class:** Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Daily (weekdays 5PM EST)
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** Pick direction accuracy tracked (NOT trading profitability)
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** TP: +8%, SL: -4%, Max Hold: 14 days

### 1.20 DayTrades Miracle Claude v2
- **Asset Class:** Stocks (CDR-focused)
- **Data Source:** Yahoo Finance
- **Update Frequency:** Real-time
- **Testing Status:** LIVE
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - CDR (Canadian Depositary Receipts) for commission-free trading
- **Description:** AI-powered day trading scanner with personalized recommendations based on budget.

### 1.21 Edge Finder - Stocks
- **Asset Class:** Stocks
- **Data Source:** Multiple (stock_picks, miracle v2, miracle v3)
- **Update Frequency:** Real-time
- **Testing Status:** BACKTESTED (30-day)
- **Win Rate Claim:** 72%+ (algorithms only used if proven)
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Multi-timeframe technical analysis. Scalp: 4h, Day Trade: 24h, Swing: 7d.

---

## 2. PENNY STOCKS ($0.01-$5 Range)

### 2.1 Penny Stock Finder (7-Factor Composite)
- **Asset Class:** Penny Stocks ($1-$5 range)
- **Data Sources:** Yahoo Finance (price, fundamentals, earnings), SEC EDGAR (13F filings, Form 4 insider trades)
- **Update Frequency:** Daily (weekdays 7 AM EST)
- **Testing Status:** BACKTESTED + LIVE
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - Exchange-listed penny stocks only (no OTC/Pink Sheets)
- **Description:** 7-factor scoring: Financial Health (30%), Momentum (25%), Volume (10%), Technical (10%), Earnings (10%), Smart Money (10%), Quality (5%). Hard filters: Z-Score > 1.5, volume > 200K, market cap > $50M.
- **Exit Rules:** SL -15%, TP +30%, Max Hold: 90 days, Position Size: 1.5%

### 2.2 Algorithm Competition Arena - Classic Momentum (Penny Stocks)
- **Asset Class:** Penny Stocks
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED (252 trading days)
- **Win Rate Claim:** +662.05% return
- **Sharpe Ratio:** 2.317
- **Asset-Specific:** Yes - Small caps
- **Description:** Jegadeesh & Titman 6-month momentum with skip-month on small caps.

---

## 3. CRYPTO (Major Coins, Altcoins)

### 3.1 Live Monitor - Core Algorithms (Crypto)
- **Asset Class:** Crypto (32 pairs)
- **Data Sources:** Kraken/FreeCryptoAPI (2-5 second delay)
- **Update Frequency:** Every 30 minutes
- **Testing Status:** LIVE (Paper trading)
- **Win Rate Claim:** Not specified per algorithm
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - 32 crypto pairs
- **Description:** $10K starting capital, 5% position sizing, max 10 positions.

#### Active Algorithms (13 of 20):
1. **Momentum Burst** - Detects sudden price acceleration
2. **RSI Reversal** - Finds oversold bounces (RSI below 30 then rising)
3. **Breakout 24h** - Price breaking above its 24-hour high
4. **DCA Dip** - Identifies dips in an uptrend worth buying
5. **Bollinger Squeeze** - Low volatility about to expand
6. **MACD Crossover** - Momentum shifting from bearish to bullish
7. **Consensus** - Only fires when 3+ other algorithms agree
8. **Volatility Breakout** - Price breaking out of a tight range
9. **Trend Sniper** - Multi-timeframe trend alignment (ADX + SMA)
10. **Dip Recovery** - Buying dips confirmed by volume recovery
11. **Volume Spike** - Abnormal volume preceding price moves
12. **VAM (Vol-Adjusted Momentum)** - Momentum weighted by volume conviction
13. **Mean Reversion Sniper** - Extreme deviation from average

### 3.2 Algorithm Competition Arena - Trend Following (Crypto)
- **Asset Class:** Cryptocurrency
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** +0.61% (beat BTC benchmark -37.58%)
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** All 12 algorithms beat BTC benchmark.

### 3.3 Edge Finder - Crypto
- **Asset Class:** Crypto
- **Data Source:** Multiple algorithms
- **Update Frequency:** Real-time
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** 72%+
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** 24/7 trading. Scalp: 4h, Day Trade: 24h, Swing: 7d.

---

## 4. MEME COINS (DOGE, PEPE, SHIB, etc.)

### 4.1 Meme Coin Scanner v2
- **Asset Class:** Meme Coins
- **Data Sources:** Kraken public API, CoinGecko, Crypto.com Exchange
- **Update Frequency:** Every 10 minutes
- **Testing Status:** FORWARD-TESTED
- **Win Rate Claim:** 5% (1 win / 19 losses, 20 resolved) - UNDERPERFORMING
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - Meme coins only
- **Description:** 7 meme-specific indicators: Explosive Volume (0-25 pts), Parabolic Momentum (0-20 pts), RSI Hype Zone (0-15 pts), Social Momentum Proxy (0-15 pts), Volume Concentration (0-10 pts), Breakout vs 4h High (0-10 pts), Low Market Cap Bonus (0-5 pts).
- **Quality Gates:** Must pass 2 of 3 (Trend Confirm, Momentum Gate, Volume Gate)
- **Thresholds:** Strong Buy (85-100), Buy (78-84), Lean Buy (72-77)
- **Exit Rules:** Targets +2-12%, Risk -1.5-4%, 2-hour resolve window

### 4.2 Algorithm Competition Arena - Bollinger Mean Reversion (Meme Coins)
- **Asset Class:** Meme Coins
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** +35.36%
- **Sharpe Ratio:** 1.163
- **Asset-Specific:** Yes
- **Description:** All 12 algorithms beat DOGE benchmark (-48%).

---

## 5. FOREX (Currency Pairs)

### 5.1 Live Monitor - Forex Algorithms
- **Asset Class:** Forex (10 pairs)
- **Data Source:** TwelveData (~15s delay)
- **Update Frequency:** Every 30 minutes (Mon-Fri)
- **Testing Status:** LIVE (Paper trading)
- **Win Rate Claim:** Not specified
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes - 10 currency pairs
- **Description:** Less volatile than crypto - typical daily moves 0.5-2%. Fee: 0 (cost in spread).

### 5.2 Algorithm Competition Arena - Classic Momentum (Forex)
- **Asset Class:** Forex
- **Data Source:** Yahoo Finance
- **Update Frequency:** Weekly
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** +7.23% (beat UUP benchmark -5%)
- **Sharpe Ratio:** 1.733
- **Asset-Specific:** Yes
- **Description:** 11/12 algorithms beat UUP benchmark.

### 5.3 Edge Finder - Forex
- **Asset Class:** Forex
- **Data Source:** Multiple algorithms
- **Update Frequency:** Real-time
- **Testing Status:** BACKTESTED
- **Win Rate Claim:** 72%+
- **Sharpe Ratio:** Not specified
- **Asset-Specific:** Yes
- **Description:** Scalp: 4h, Day Trade: 24h, Swing: 7d.

---

## SYSTEM ARCHITECTURE SUMMARY

### Data Sources Used Across All Strategies:
1. **Yahoo Finance** - Primary price data (stocks, crypto, forex, fundamentals)
2. **Finnhub API** - Analyst ratings, real-time stock prices
3. **SEC EDGAR** - 13F filings, Form 4 insider trades
4. **Kraken API** - Crypto/meme coin prices
5. **Crypto.com Exchange API** - Meme coin scanner
6. **CoinGecko** - Trending coins, market data
7. **TwelveData** - Forex prices
8. **Reddit API** - WSB sentiment

### Update Frequencies:
- **Real-time:** Live Monitor (every 30 min), Edge Finder
- **Daily:** Consensus picks, Top Picks, Penny Stocks, Smart Money
- **Weekly:** Algorithm Competition Arena

### Testing Status Distribution:
- **BACKTESTED:** Algorithm Competition Arena (12 strategies), Alpha Factor Suite
- **LIVE (Paper Trading):** Live Monitor (13 active algorithms), Challenger Bot, DayTrades Miracle
- **FORWARD-TESTED:** Consolidated Picks, Meme Coin Scanner

### Key Performance Claims Summary:
| Strategy | Asset Class | Win Rate | Sharpe | Status |
|----------|-------------|----------|--------|--------|
| Meta Learner (God-Mode) | Stocks | +23.69% return | 1.409 | Backtested |
| Classic Momentum (Penny) | Penny Stocks | +662.05% return | 2.317 | Backtested |
| Bollinger Mean Reversion (Meme) | Meme Coins | +35.36% return | 1.163 | Backtested |
| Classic Momentum (Forex) | Forex | +7.23% return | 1.733 | Backtested |
| Meme Coin Scanner v2 | Meme Coins | 5% WR | N/A | Forward-tested |
| Challenger Bot | Stocks | 0% WR (fix deployed) | N/A | Live |

### Paused Algorithms (7 stock-only):
- ETF Masters (3.4% WR)
- Sector Rotation (2.2% WR)
- Sector Momentum (0% WR)
- Blue Chip Growth (5.6% WR)
- Technical Momentum (0% WR)
- Composite Rating (0% WR)
- Cursor Genius (11.5% WR)

---

## NOTES

1. **Sample Size Warning:** Many strategies lack sufficient trade history for statistical significance. The Meme Coin Scanner explicitly notes that 20-29 resolved signals is "statistically underpowered" and requires 350+ for reliable estimates.

2. **Win Rate vs Trading Profitability:** The site explicitly distinguishes between "pick direction accuracy" (did the stock go up?) and "trading profitability" (TP/SL execution win rate). A 70% direction WR can still lose money with tight stops.

3. **Forward-Tested vs Backtested:** Forward-tested strategies track predictions before outcomes are known. Backtested strategies are tested on historical data and may contain overfitting bias.

4. **Asset-Specific vs Generic:** Most strategies are asset-specific (tuned for particular asset classes). The Alpha Factor Suite and Algorithm Competition Arena have different parameter sets per asset class.

5. **Risk Disclaimers:** All strategies carry "Not Financial Advice" disclaimers. The site emphasizes that past performance does not guarantee future results.
