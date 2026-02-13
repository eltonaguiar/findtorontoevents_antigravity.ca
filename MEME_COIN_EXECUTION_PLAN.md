# Meme Coin System Enhancement - Execution Plan

## Project Overview
Based on comprehensive third-party AI audits (ChatGPT, Kimi, Grok), this plan addresses critical flaws in our meme coin prediction framework (currently 3-5% win rate) to achieve target 40%+ accuracy.

## Executive Summary
- **Current State**: 3.4% win rate, inverted confidence tiers, 2015-era architecture
- **Target**: 40%+ win rate within 12 weeks
- **Approach**: Quick wins with free data → ML pipeline → On-chain integration → Validation

---

## PHASE 1: Quick Data Infrastructure (Weeks 1-2)
**Goal**: Build resilient data collection with multiple free sources and failovers

### Task 1.1: Multi-Exchange Price Validation
**Priority**: P0 | **Cost**: FREE | **Owner**: Data Infrastructure Agent

Build price aggregation system with automatic failover:
```
Priority Chain:
1. Kraken API (primary)
2. Binance API (failover 1) - 1200 req/min free
3. Coinbase API (failover 2) - 100 req/sec free
4. CoinGecko API (failover 3) - 10-30 req/min free
5. Cached price (emergency fallback)
```

**Deliverables**:
- [ ] MultiExchangePriceAggregator class
- [ ] Automatic failover logic with health checks
- [ ] Price anomaly detection (>2% spread flags warning)
- [ ] 30-second caching layer to minimize API calls
- [ ] Rate limit tracking per exchange

**Files to Create/Modify**:
- `findcryptopairs/api/multi_exchange_prices.php`
- `findcryptopairs/api/price_cache.php`

---

### Task 1.2: Free Sentiment Scraping Pipeline
**Priority**: P0 | **Cost**: FREE | **Owner**: Sentiment Data Agent

Implement web scraping for multiple sentiment sources:

**Source 1: Reddit (via PRAW)**
- Subreddits: r/CryptoMoonShots, r/SatoshiStreetBets, r/CryptoCurrency
- Metrics: Mention count, upvote ratio, comment velocity
- Rate limit: 100 req/min (free tier)

**Source 2: 4chan /biz/**
- API: 4chan JSON API (no auth required)
- Metrics: Thread creation rate, reply counts
- Keywords: Coin symbols, "moon", "pump", "rug"

**Source 3: Google Trends**
- Tool: pytrends (unofficial, free)
- Metrics: Search interest by region/time
- Query: Coin symbol + "buy", "price", "news"

**Source 4: Nitter (Twitter/X)**
- Tool: Nitter scraper instances (free, no API key)
- Metrics: Mention velocity, hashtag trends
- Failover: Multiple Nitter instances

**Deliverables**:
- [ ] RedditScraper class with sentiment scoring
- [ ] FourChanScraper for /biz/ threads
- [ ] GoogleTrendsScraper for search interest
- [ ] NitterScraper for Twitter mentions
- [ ] Unified SentimentAggregator with conflict resolution
- [ ] Rate limiting and caching (5-min cache for Reddit, 1-hour for Trends)

**Files to Create**:
- `findcryptopairs/api/sentiment_reddit.php`
- `findcryptopairs/api/sentiment_4chan.php`
- `findcryptopairs/api/sentiment_trends.php`
- `findcryptopairs/api/sentiment_nitter.php`
- `findcryptopairs/api/sentiment_aggregate.php`

---

### Task 1.3: Data Caching & Rate Limiting System
**Priority**: P0 | **Cost**: FREE | **Owner**: Backend Infrastructure Agent

Build robust caching to respect API limits and ensure reliability:

**Deliverables**:
- [ ] Redis/file-based cache wrapper
- [ ] Rate limit tracker per API source
- [ ] Automatic backoff on 429 errors
- [ ] Cache warming for critical data
- [ ] Health check endpoint for all data sources

**Implementation**:
```php
class DataCache {
    public function get($key, $ttl = 300);
    public function set($key, $value, $ttl = 300);
    public function remember($key, $ttl, $callback);
}

class RateLimiter {
    public function checkLimit($source, $maxRequests, $windowSeconds);
    public function getBackoffTime($source);
}
```

---

## PHASE 2: Feature Engineering & ML Pipeline (Weeks 3-6)

### Task 2.1: Sentiment Feature Engineering
**Priority**: P1 | **Cost**: FREE | **Owner**: ML Feature Agent

Transform raw sentiment data into predictive features:

**Features to Engineer**:
1. **Sentiment Velocity**: d/dt(mentions) over 30-120 min windows
2. **Sentiment Volatility**: Standard deviation of sentiment scores
3. **Cross-Platform Correlation**: Agreement between Reddit/Twitter/4chan
4. **Influencer Weighting**: Track mentions from accounts with >10k followers
5. **Keyword Intensity**: Detect "moon", "lambo", "diamond hands" vs "rug", "scam"
6. **Sentiment-Price Divergence**: When price flat but sentiment rising

**Academic Target**: Research shows these features achieve 74% accuracy with XGBoost

---

### Task 2.2: XGBoost Classifier Implementation
**Priority**: P1 | **Cost**: FREE | **Owner**: ML Model Agent

Build the core prediction model:

**Input Features**:
- Price momentum (5m, 15m, 1h, 4h, 24h)
- Volume metrics (relative, acceleration)
- Sentiment features (from Task 2.1)
- Market regime (BTC trend)
- Time features (hour of day, day of week)

**Model Architecture**:
```python
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit

# Binary classification: Will hit TP before SL?
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    objective='binary:logistic'
)

# Walk-forward validation (crucial for time series)
tscv = TimeSeriesSplit(n_splits=5)
```

**Deliverables**:
- [ ] Feature extraction pipeline
- [ ] XGBoost model training script
- [ ] Walk-forward validation framework
- [ ] Model persistence (save/load trained models)
- [ ] Prediction API endpoint
- [ ] Model performance tracking

**Files to Create**:
- `findcryptopairs/ml/train_model.py`
- `findcryptopairs/ml/predict.php`
- `findcryptopairs/ml/features.php`

---

### Task 2.3: Fix Inverted Confidence Tiers
**Priority**: P0 | **Cost**: FREE | **Owner**: Diagnostic Analysis Agent

**Problem**: Strong Buy (8-10) has 0% win rate, Lean Buy (1-4) has 5% win rate

**Diagnostic Tasks**:
- [ ] Analyze correlation between individual features and outcomes
- [ ] Test signal inversion (high scores = short signals?)
- [ ] Re-optimize thresholds (72/78/85 may be wrong)
- [ ] Identify which features are negatively correlated
- [ ] Check for momentum exhaustion patterns

**Hypothesis**: High scores identify "hot" coins at visibility peak (exhaustion), not "heating" coins

**Deliverables**:
- [ ] Feature correlation analysis report
- [ ] Threshold optimization study
- [ ] Calibrated probability scores (replace fixed thresholds)

---

## PHASE 3: On-Chain & Safety Gating (Weeks 7-10)

### Task 3.1: Free On-Chain Data Integration
**Priority**: P2 | **Cost**: FREE | **Owner**: Blockchain Data Agent

Integrate free blockchain data sources:

**Etherscan API (5 calls/sec free)**:
- Token holder distribution
- Large transfer alerts (>1% of supply)
- Contract verification status

**Dune Analytics (free dashboards)**:
- Holder concentration metrics
- Wallet age analysis
- Smart money tracking

**DeFi Llama (free)**:
- TVL changes
- Liquidity pool depth
- Yield metrics

**Bubblemaps (free tier)**:
- Visual wallet clustering
- Holder distribution visualization

---

### Task 3.2: Rug Pull Detection Heuristics
**Priority**: P1 | **Cost**: FREE | **Owner**: Security Agent

Implement basic safety checks:

**Checks**:
- [ ] Contract verified on Etherscan
- [ ] No mint function (or renounced ownership)
- [ ] Liquidity locked (check LP tokens)
- [ ] Top 10 holders < 30% supply
- [ ] No hidden transaction taxes > 5%
- [ ] Contract age > 7 days
- [ ] TokenSniffer score > 50

**Scoring**:
```php
$safetyScore = 0;
if ($verified) $safetyScore += 20;
if ($noMint) $safetyScore += 20;
if ($liquidityLocked) $safetyScore += 20;
if ($top10 < 30) $safetyScore += 20;
if ($age > 7) $safetyScore += 20;

if ($safetyScore < 60) {
    // Flag as high risk
}
```

---

### Task 3.3: Whale Wallet Tracking
**Priority**: P2 | **Cost**: FREE | **Owner**: On-Chain Analytics Agent

Basic whale monitoring:

**Features**:
- Track known whale wallets (>$100k positions)
- Alert on large accumulation (>5% position increase)
- Alert on large distribution (>5% position decrease)
- Wallet age scoring (older = more trustworthy)

---

## PHASE 4: Testing & Validation (Weeks 11-12)

### Task 4.1: Proper Backtesting Framework
**Priority**: P1 | **Cost**: FREE | **Owner**: Validation Agent

Build rigorous backtesting:

**Requirements**:
- [ ] Walk-forward analysis (no lookahead bias)
- [ ] Transaction cost modeling (fees + slippage)
- [ ] Cross-validation by regime (bull/bear/sideways)
- [ ] A/B testing infrastructure

**Metrics to Track**:
- Win rate by tier
- Expectancy (average P&L per trade)
- Sharpe ratio
- Max drawdown
- Profit factor

---

### Task 4.2: Collect 350+ Resolved Signals
**Priority**: P0 | **Cost**: FREE | **Owner**: Data Collection Agent

**Problem**: Current 20-29 signals is statistically meaningless

**Solution**:
- Run new model in shadow mode (generate signals, don't trade)
- Paper trade all signals for 2-4 weeks
- Collect outcomes at 2h, 4h, 8h, 24h horizons
- Target: 350+ resolved signals for statistical validity

---

### Task 4.3: A/B Testing Framework
**Priority**: P1 | **Cost**: FREE | **Owner**: Testing Agent

Compare new model vs baseline:

**Test Setup**:
- Control: Current rule-based system
- Treatment: XGBoost + sentiment + on-chain
- Run both simultaneously
- Compare win rates, expectancy, drawdowns
- Statistical significance test (p < 0.05)

---

## Expected Outcomes by Phase

| Phase | Timeline | Expected Win Rate | Key Deliverables |
|-------|----------|-------------------|------------------|
| Baseline | Now | 3-5% | Current system |
| Phase 1 | Week 2 | 10-15% | Multi-exchange, sentiment scraping |
| Phase 2 | Week 6 | 25-35% | XGBoost model, fixed confidence tiers |
| Phase 3 | Week 10 | 35-45% | On-chain safety, whale tracking |
| Phase 4 | Week 12 | 40%+ validated | Statistical proof, A/B test results |

---

## Resource Requirements

### Personnel (Agents Needed)
1. **Data Infrastructure Agent** - API integrations, caching
2. **Sentiment Data Agent** - Reddit, 4chan, Trends scraping
3. **ML Model Agent** - XGBoost, feature engineering
4. **Blockchain Data Agent** - Etherscan, Dune integration
5. **Diagnostic Analysis Agent** - Fix inverted tiers
6. **Security Agent** - Rug pull detection
7. **Validation Agent** - Backtesting, A/B testing

### Costs
- **Infrastructure**: $0 (using free APIs and existing server)
- **Data**: $0 (all sources have free tiers)
- **Compute**: $0 (CPU-based training, no GPU required for XGBoost)
- **Total Budget**: $0 (entirely free-stack implementation)

---

## Risk Mitigation

1. **API Rate Limits**: Built-in caching and backoff
2. **Web Scraping Fragility**: Multiple failover sources
3. **Model Overfitting**: Walk-forward validation, never backtest on future data
4. **Market Regime Change**: Continuous monitoring, automatic retraining triggers

---

## Success Criteria

- [ ] Win rate improves from 3.4% to 40%+
- [ ] Confidence tiers no longer inverted
- [ ] 350+ statistically valid signals collected
- [ ] A/B test shows statistically significant improvement (p < 0.05)
- [ ] System runs entirely on free data sources
- [ ] <2 second latency for signal generation

---

*Plan created based on ChatGPT, Kimi, and Grok AI research audits*
*Last updated: February 2026*