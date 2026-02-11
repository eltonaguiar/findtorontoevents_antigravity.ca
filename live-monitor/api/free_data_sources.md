# Free Data Sources for Multi-Dimensional Analysis

## Current Data Sources (In-System)
- **Whale (13F)**: SEC 13F filings via `gm_sec_13f_holdings`
- **Insider**: SEC Form 4 via `gm_sec_insider_trades`
- **Analyst**: Finnhub (paid) - recommendation history + price targets
- **Crowd**: News sentiment + WSB via `lm_wsb_sentiment`
- **Fear/Greed**: Alternative.me API (free) + VIX-based
- **Regime**: VIX + market regime classification

## Free External Data Sources to Supplement

### 1. **Alpha Vantage** (Free Tier)
- **Rate Limit**: 5 API calls/day, 100/day with free tier
- **Endpoints**:
  - `https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=YOUR_KEY`
  - `https://www.alphavantage.co/query?function=OVERVIEW&symbol=AAPL&apikey=YOUR_KEY`
- **Data**: Daily prices, fundamentals, technical indicators
- **Use**: Enhanced momentum, technical scores

### 2. **Yahoo Finance API (Unofficial)**
- **Rate Limit**: None officially, but rate-limited by IP
- **Endpoints**:
  - `https://query1.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=price,summaryDetail,financialData`
- **Data**: Price data, P/E ratio, market cap, dividend yield
- **Use**: Fundamental analysis, valuation metrics

### 3. **Financial Modeling Prep** (Free Tier)
- **Rate Limit**: 250 requests/day
- **Endpoints**:
  - `https://financialmodelingprep.com/api/v3/quote/AAPL?apikey=YOUR_KEY`
  - `https://financialmodelingprep.com/api/v3/income-statement/AAPL?apikey=YOUR_KEY`
- **Data**: Real-time quotes, financial statements, ratios
- **Use**: Fundamental scoring, ratio analysis

### 4. **IEX Cloud** (Free Tier)
- **Rate Limit**: 50,000 messages/month (free tier)
- **Endpoints**:
  - `https://cloud.iexapis.com/stable/stock/AAPL/quote?token=YOUR_KEY`
  - `https://cloud.iexapis.com/stable/stock/AAPL/stats?token=YOUR_KEY`
- **Data**: Real-time quotes, company stats, financials
- **Use**: Real-time price data, company statistics

### 5. **SEC EDGAR Database** (Free)
- **Rate Limit**: None (but be respectful)
- **Endpoints**:
  - `https://www.sec.gov/files/company_tickers.json`
  - `https://www.sec.gov/Archives/edgar/data/0000320193/000032019324000096/0000320193-24-000096.txt`
- **Data**: All SEC filings (13F, 4, 8K, etc.)
- **Use**: Raw data source for insider/13F verification

### 6. **Reddit API (WSB)** (Free)
- **Rate Limit**: 1000 calls/hour
- **Endpoints**:
  - `https://www.reddit.com/r/wallstreetbets/search.json?q=AAPL&sort=relevance&limit=100`
- **Data**: WSB mentions, sentiment, trending stocks
- **Use**: Enhanced crowd sentiment, buzz detection

### 7. **Twitter/X API** (Free Tier)
- **Rate Limit**: 15 requests/15min (v2)
- **Endpoints**:
  - `https://api.twitter.com/2/tweets/search/recent?query=AAPL&max_results=100`
- **Data**: Stock-related tweets, sentiment
- **Use**: Real-time sentiment, news detection

### 8. **Google Finance** (Free)
- **Rate Limit**: None officially
- **Endpoints**:
  - `https://www.google.com/finance/quote/AAPL:NASDAQ`
- **Data**: Price data, market cap, P/E, sector
- **Use**: Cross-verify price data

### 9. **MarketWatch** (Free)
- **Rate Limit**: None officially
- **Endpoints**:
  - `https://www.marketwatch.com/investing/stock/aapl`
- **Data**: News, analyst ratings, financials
- **Use**: News sentiment, analyst consensus

### 10. **Finviz** (Free)
- **Rate Limit**: None officially (scraping)
- **Endpoints**:
  - `https://finviz.com/screener.ashx?v=111&f=cap_large`
- **Data**: Stock screener data, fundamentals, technicals
- **Use**: Fundamental screening, technical analysis

## Recommended Implementation Priority

### High Priority (High Impact, Free)
1. **Alpha Vantage** - Enhanced technical scores
2. **Financial Modeling Prep** - Fundamental scoring
3. **SEC EDGAR** - Raw data verification
4. **Reddit API** - Enhanced WSB sentiment

### Medium Priority (Moderate Impact, Free)
5. **Yahoo Finance** - Fundamental data
6. **IEX Cloud** - Real-time quotes
7. **Google Finance** - Cross-verify data

### Lower Priority (Lower Impact or Complex)
8. **Twitter API** - Sentiment (complex to parse)
9. **MarketWatch** - News (scraping required)
10. **Finviz** - Screener data (scraping required)

## Implementation Strategy

### Phase 1: API Integration (Week 1)
- Set up Alpha Vantage account (free)
- Create scraper for Alpha Vantage data
- Integrate technical scores into multi-dimensional analysis

### Phase 2: Enhanced Data Sources (Week 2)
- Add Financial Modeling Prep for fundamentals
- Implement SEC EDGAR parsing for raw data
- Enhance WSB sentiment with Reddit API

### Phase 3: Data Validation (Week 3)
- Cross-validate data from multiple sources
- Implement data quality scoring
- Add data health dashboard

## Data Quality Enhancement Dimensions

### New Dimensions to Add
1. **Value Score** - P/E, P/B, P/S ratios vs industry
2. **Growth Score** - Revenue growth, earnings growth
3. **Momentum Score** - Enhanced technical momentum
4. **Volatility Score** - Historical volatility, beta
5. **Liquidity Score** - Volume, bid-ask spread
6. **Sentiment Score** - Multi-source sentiment aggregation

### Weighting Recommendations
- Whale (13F): 15%
- Insider: 15%
- Analyst: 15%
- Crowd: 15%
- Fear/Greed: 15%
- Regime: 10%
- **Value**: 5% (NEW)
- **Growth**: 5% (NEW)
- **Momentum**: 5% (NEW)
