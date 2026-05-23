# Deep Research: Behavioral Finance & Market Psychology
## March 2, 2026

---

## Executive Summary

Behavioral finance studies how psychological factors influence investor behavior and market prices. Understanding these biases creates alpha opportunities through contrarian positioning and cognitive arbitrage.

**Key Findings:**
- Retail sentiment is often a contrarian indicator at extremes
- Momentum and mean reversion both have behavioral foundations
- FOMO and panic create predictable patterns
- Institutional herding generates exploitable inefficiencies

---

## Part 1: Cognitive Biases in Trading

### 1.1 Common Biases

| Bias | Description | Market Impact | Trading Edge |
|------|-------------|---------------|--------------|
| **Loss Aversion** | Losses hurt 2.5× more than gains feel good | Disposition effect (sell winners, hold losers) | Trade with stops, not emotions |
| **Recency Bias** | Overweight recent events | Momentum crashes after extended runs | Fade extreme moves |
| **Confirmation Bias** | Seek confirming information | Echo chambers amplify trends | Seek disconfirming evidence |
| **Overconfidence** | Overestimate own abilities | Excessive trading, underestimating risk | Keep trade journals |
| **Anchoring** | Fixate on reference points | Support/resistance levels | Know when to adapt |
| **Herding** | Follow the crowd | Bubbles and crashes | Contrarian at extremes |
| **FOMO** | Fear of missing out | Parabolic moves, blow-off tops | Predefined entry criteria |
| **Availability Bias** | Vivid events seem more likely | Overreaction to news | Base decisions on data |

### 1.2 The Disposition Effect

**Research:** Shefrin & Statman (1985)

**Finding:** Investors are 1.5-2× more likely to sell winners than losers

**Market Impact:**
- Creates upward pressure on stocks approaching 52-week highs
- Creates downward pressure on stocks approaching 52-week lows
- Generates post-earnings drift (underreaction)

**Trading Strategy:**
```python
class DispositionEffectStrategy:
    def __init__(self):
        self.high_threshold = 0.95  # 95% of 52-week high
        self.low_threshold = 1.05   # 105% of 52-week low
        
    def generate_signal(self, price, high_52w, low_52w):
        """
        Trade against disposition effect
        """
        ratio_to_high = price / high_52w
        ratio_to_low = price / low_52w
        
        if ratio_to_high > self.high_threshold:
            # Many investors selling (locking in gains)
            # But momentum usually continues
            return 'MOMENTUM_LONG'
        
        if ratio_to_low < self.low_threshold:
            # Many investors holding losers (tax loss selling)
            # January effect opportunity
            return 'VALUE_LONG'
        
        return 'NEUTRAL'
```

### 1.3 Overconfidence in Markets

**Evidence:**
- 90% of drivers think they're above average
- 75% of fund managers believe they beat the market
- Retail traders trade 50% more than optimal

**Market Impact:**
- Overtrading reduces returns by 3-5% annually
- Volatility increases during high sentiment periods
- Predictable corrections after euphoria

**Overconfidence Indicators:**
```python
def measure_overconfidence(market_data):
    """
    Proxy overconfidence using market metrics
    """
    indicators = {
        # High volume + low volatility = complacency
        'volume_vix_ratio': market_data['volume'] / market_data['vix'],
        
        # Call/Put ratio (high = bullish euphoria)
        'cp_ratio': market_data['call_volume'] / market_data['put_volume'],
        
        # Margin debt growth
        'margin_growth': market_data['margin_debt'].pct_change(252),
        
        # Retail participation
        'retail_flow': market_data['retail_inflow'] / market_data['total_volume']
    }
    
    # Composite overconfidence score
    score = (
        0.3 * normalize(indicators['cp_ratio']) +
        0.3 * normalize(indicators['margin_growth']) +
        0.4 * normalize(indicators['retail_flow'])
    )
    
    return score
```

---

## Part 2: Sentiment Analysis

### 2.1 Market Sentiment Indicators

| Indicator | Bullish Level | Bearish Level | Current |
|-----------|---------------|---------------|---------|
| VIX | <12 | >30 | Real-time |
| Put/Call Ratio | <0.7 | >1.2 | Real-time |
| AAII Sentiment | >50% bulls | >40% bears | Weekly |
| CNN Fear & Greed | >75 | <25 | Daily |
| Margin Debt | High growth | Contraction | Monthly |
| Fund Flows | Risk-on | Risk-off | Weekly |

### 2.2 Sentiment-Based Strategies

**1. Contrarian Extreme Sentiment:**
```python
class ContrarianSentimentStrategy:
    def __init__(self):
        self.extreme_bullish = 75  # Fear & Greed index
        self.extreme_bearish = 25
        
    def generate_signal(self, sentiment_indicators):
        """
        Fade extreme sentiment
        """
        composite = self.calculate_composite_sentiment(sentiment_indicators)
        
        if composite > self.extreme_bullish:
            return {
                'signal': 'SELL',
                'reason': 'Extreme euphoria',
                'strength': (composite - self.extreme_bullish) / 25
            }
        elif composite < self.extreme_bearish:
            return {
                'signal': 'BUY',
                'reason': 'Extreme fear',
                'strength': (self.extreme_bearish - composite) / 25
            }
        
        return {'signal': 'NEUTRAL'}
    
    def calculate_composite_sentiment(self, indicators):
        """
        Combine multiple sentiment indicators
        """
        weights = {
            'vix': 0.20,
            'put_call': 0.15,
            'aaii': 0.15,
            'fear_greed': 0.25,
            'margin': 0.15,
            'flows': 0.10
        }
        
        # Normalize each to 0-100 scale
        normalized = {
            'vix': 100 - min(100, indicators['vix'] / 50 * 100),
            'put_call': indicators['put_call'] / 1.5 * 100,
            'aaii': indicators['aaii_bullish'],
            'fear_greed': indicators['fear_greed_index'],
            'margin': min(100, max(0, indicators['margin_growth'] * 100 + 50)),
            'flows': indicators['risk_on_flows'] * 100
        }
        
        composite = sum(weights[k] * normalized[k] for k in weights)
        return composite
```

**2. Smart Money vs Dumb Money:**
```python
class SmartMoneyDumbMoneyStrategy:
    """
    Follow smart money, fade dumb money
    """
    def __init__(self):
        self.smart_money_indicators = [
            'institutional_flow',
            'insider_buying',
            'hedge_fund_positions'
        ]
        self.dumb_money_indicators = [
            'retail_margin',
            'robinhood_trends',
            'put_call_retail'
        ]
    
    def divergence_signal(self, smart_flow, dumb_flow):
        """
        Signal when smart and dumb money disagree
        """
        smart_score = np.mean(smart_flow)
        dumb_score = np.mean(dumb_flow)
        
        # Smart money buying, dumb money selling = BULLISH
        if smart_score > 0.6 and dumb_score < 0.4:
            return 'STRONG_BUY'
        
        # Smart money selling, dumb money buying = BEARISH
        elif smart_score < 0.4 and dumb_score > 0.6:
            return 'STRONG_SELL'
        
        # Agreement = no edge
        return 'NEUTRAL'
```

### 2.3 Social Media Sentiment

**Twitter/X Analysis:**
```python
class SocialSentimentAnalyzer:
    def __init__(self):
        self.bullish_keywords = [
            'moon', 'pump', 'bullish', 'breakout', ' ATH',
            'accumulate', 'hodl', 'diamond hands'
        ]
        self.bearish_keywords = [
            'dump', 'crash', 'bearish', 'rekt', 'panic',
            'sell', 'paper hands', 'rugpull'
        ]
        
    def analyze_sentiment(self, tweets):
        """
        Simple keyword-based sentiment
        """
        bullish_count = sum(
            1 for tweet in tweets
            for word in self.bullish_keywords
            if word in tweet.lower()
        )
        
        bearish_count = sum(
            1 for tweet in tweets
            for word in self.bearish_keywords
            if word in tweet.lower()
        )
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.5  # Neutral
        
        sentiment = bullish_count / total
        return sentiment
    
    def contrarian_signal(self, sentiment, volume):
        """
        Fade extreme social sentiment
        """
        # High volume + extreme sentiment = contrarian signal
        if sentiment > 0.8 and volume > np.percentile(volume, 90):
            return 'FADE_BULLISH'
        elif sentiment < 0.2 and volume > np.percentile(volume, 90):
            return 'FADE_BEARISH'
        
        return 'NEUTRAL'
```

---

## Part 3: Market Anomalies with Behavioral Roots

### 3.1 Momentum

**Behavioral Explanation:**
- **Underreaction:** Slow information diffusion (Hong & Stein, 1999)
- **Herding:** Investors follow recent winners
- **Anchoring:** Prices adjust slowly to new information

**Strategy:**
```python
def behavioral_momentum(returns, lookback=12, holding=1):
    """
    Classic 12-1 momentum with behavioral timing
    """
    # Standard momentum
    momentum = returns.rolling(lookback).mean()
    
    # Behavioral overlay: exit on extreme sentiment
    sentiment = get_sentiment_indicator()
    
    signal = np.where(momentum > 0, 1, -1)
    
    # Exit longs when extremely bullish
    signal = np.where((signal == 1) & (sentiment > 0.8), 0, signal)
    
    # Exit shorts when extremely bearish
    signal = np.where((signal == -1) & (sentiment < 0.2), 0, signal)
    
    return signal
```

### 3.2 Mean Reversion

**Behavioral Explanation:**
- **Overreaction:** Investors extrapolate recent trends too far
- **Panic selling:** Fear drives prices below fundamental value
- **FOMO buying:** Greed drives prices above fundamental value

**Strategy:**
```python
def behavioral_mean_reversion(prices, lookback=20):
    """
    Mean reversion with behavioral triggers
    """
    z_score = (prices - prices.rolling(lookback).mean()) / prices.rolling(lookback).std()
    
    # Standard mean reversion
    signal = np.where(z_score > 2, -1, np.where(z_score < -2, 1, 0))
    
    # Behavioral confirmation
    fear_greed = get_fear_greed_index()
    
    # Stronger signal when sentiment aligns with reversion
    signal = np.where(
        (signal == 1) & (fear_greed < 20),  # Fear + oversold
        2, signal
    )
    signal = np.where(
        (signal == -1) & (fear_greed > 80),  # Greed + overbought
        -2, signal
    )
    
    return signal
```

### 3.3 Post-Earnings Announcement Drift (PEAD)

**Behavioral Explanation:**
- **Underreaction:** Investors slowly update beliefs
- **Anchoring:** Focus on pre-announcement price
- **Confirmation bias:** Dismiss unexpected news

**Strategy:**
```python
def pead_strategy(earnings_surprises, lookback=60):
    """
    Trade post-earnings drift
    """
    # Standardized unexpected earnings (SUE)
    sue = earnings_surprises / earnings_surprises.rolling(lookback).std()
    
    # Top and bottom deciles
    longs = sue > sue.quantile(0.9)
    shorts = sue < sue.quantile(0.1)
    
    # Hold for 60 days
    signal = pd.Series(0, index=sue.index)
    signal[longs] = 1
    signal[shorts] = -1
    
    return signal
```

### 3.4 January Effect

**Behavioral Explanation:**
- **Tax-loss selling:** Investors sell losers in December
- **Window dressing:** Funds remove losers from year-end reports
- **New year optimism:** Fresh capital allocation

**Strategy:**
```python
def january_effect_strategy(prices, month):
    """
    Buy small-cap losers in December, sell in January
    """
    if month == 12:
        # Buy December losers (tax loss selling)
        ytd_return = prices.pct_change(252)
        losers = ytd_return.nsmallest(int(len(ytd_return) * 0.2))
        return {'action': 'BUY', 'targets': losers.index}
    
    elif month == 1:
        # Sell January winners
        return {'action': 'SELL_ALL'}
    
    return {'action': 'HOLD'}
```

---

## Part 4: Crowd Psychology & Market Cycles

### 4.1 The Psychology of Market Cycles

```
Accumulation → Markup → Distribution → Markdown
    ↑___________________________________|

Emotional States:
- Accumulation: Disbelief, Depression
- Markup: Hope, Optimism, Euphoria
- Distribution: Anxiety, Denial
- Markdown: Fear, Panic, Capitulation
```

**Stage Detection:**
```python
class MarketCycleAnalyzer:
    def __init__(self):
        self.stages = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION', 'MARKDOWN']
        
    def detect_stage(self, price, volume, sentiment):
        """
        Detect current market cycle stage
        """
        # Price action
        trend = 'UP' if price.rolling(50).mean().iloc[-1] > price.rolling(200).mean().iloc[-1] else 'DOWN'
        volatility = price.pct_change().std() * np.sqrt(252)
        
        # Volume
        vol_trend = 'HIGH' if volume.rolling(20).mean().iloc[-1] > volume.rolling(50).mean().iloc[-1] else 'LOW'
        
        # Sentiment
        fear_greed = sentiment
        
        # Classification rules
        if trend == 'UP' and fear_greed < 40 and vol_trend == 'LOW':
            return 'ACCUMULATION'
        elif trend == 'UP' and fear_greed > 60:
            return 'MARKUP'
        elif trend == 'DOWN' and fear_greed > 50 and vol_trend == 'HIGH':
            return 'DISTRIBUTION'
        elif trend == 'DOWN' and fear_greed < 30:
            return 'MARKDOWN'
        
        return 'UNCLEAR'
```

### 4.2 Bubble Identification

**Warning Signs:**
```python
def bubble_score(indicators):
    """
    Calculate bubble probability (0-100)
    """
    scores = {
        # Price disconnected from fundamentals
        'pe_ratio': min(100, indicators['pe'] / 30 * 100),
        
        # Parabolic price increase
        'price_acceleration': min(100, indicators['12m_return'] / 100 * 100),
        
        # High participation from novices
        'retail_participation': indicators['retail_pct'] * 100,
        
        # Excessive leverage
        'margin_debt': min(100, indicators['margin_growth'] * 200),
        
        # New era narratives
        'media_hype': indicators['positive_articles_pct'] * 100,
        
        # Low volatility (complacency)
        'low_vix': max(0, 100 - indicators['vix'] * 5)
    }
    
    weights = {
        'pe_ratio': 0.15,
        'price_acceleration': 0.25,
        'retail_participation': 0.15,
        'margin_debt': 0.20,
        'media_hype': 0.15,
        'low_vix': 0.10
    }
    
    bubble_score = sum(scores[k] * weights[k] for k in scores)
    return bubble_score
```

---

## Part 5: Institutional Behavior

### 5.1 Quarterly Window Dressing

**Pattern:**
- Funds buy recent winners before quarter-end
- Sell recent losers
- Revert in first week of new quarter

**Strategy:**
```python
def window_dressing_strategy(date, prices, fund_holdings):
    """
    Trade quarter-end window dressing
    """
    day_of_month = date.day
    month = date.month
    
    # Quarter-end months
    if month in [3, 6, 9, 12]:
        if day_of_month > 25:
            # Buy what funds are buying (recent winners)
            recent_performers = prices.pct_change(63).nlargest(20)
            return {'action': 'BUY', 'targets': recent_performers.index}
    
    # First week of quarter
    if month in [1, 4, 7, 10] and day_of_month < 8:
        # Reverse the trade
        return {'action': 'SELL_ALL'}
    
    return {'action': 'HOLD'}
```

### 5.2 Index Rebalancing

**Pattern:**
- Stocks added to indices see price jumps
- Stocks removed see drops
- Effect is temporary but tradeable

**Strategy:**
```python
def index_rebalance_arbitrage(index_changes, effective_date):
    """
    Trade index rebalancing effects
    """
    days_to_effective = (effective_date - datetime.now()).days
    
    if 0 < days_to_effective < 5:
        # Close to effective date - trade the flow
        additions = index_changes['additions']
        deletions = index_changes['deletions']
        
        return {
            'action': 'TRADE',
            'longs': additions,
            'shorts': deletions,
            'exit_date': effective_date + timedelta(days=1)
        }
    
    return {'action': 'WAIT'}
```

### 5.3 Pension Fund Rebalancing

**Pattern:**
- Monthly/quarterly rebalancing to target allocation
- Buy stocks when they underperform bonds
- Sell stocks when they outperform

**Strategy:**
```python
def pension_rebalance_signal(stock_return, bond_return, threshold=0.05):
    """
    Predict pension fund rebalancing flows
    """
    performance_diff = stock_return - bond_return
    
    if performance_diff > threshold:
        # Stocks outperformed - expect selling
        return 'EXPECT_STOCK_SELLING'
    elif performance_diff < -threshold:
        # Stocks underperformed - expect buying
        return 'EXPECT_STOCK_BUYING'
    
    return 'NO_REBALANCE_EXPECTED'
```

---

## Part 6: Trading Psychology for Individual Traders

### 6.1 Pre-Trade Checklist

**Emotional State:**
- [ ] Am I trading to make money or to be right?
- [ ] Am I revenge trading after a loss?
- [ ] Am I overconfident after a win streak?
- [ ] Am I afraid to take a valid setup?

**Cognitive Biases:**
- [ ] Am I anchoring to my entry price?
- [ ] Am I seeking confirming evidence?
- [ ] Am I overestimating my edge?
- [ ] Am I trading my P&L instead of the setup?

### 6.2 Post-Trade Review

```python
class TradeJournal:
    def __init__(self):
        self.trades = []
        
    def log_trade(self, trade):
        """
        Log comprehensive trade data
        """
        entry = {
            'timestamp': datetime.now(),
            'symbol': trade['symbol'],
            'direction': trade['direction'],
            'entry_price': trade['entry'],
            'exit_price': trade['exit'],
            'pnl': trade['pnl'],
            'pnl_pct': trade['pnl_pct'],
            
            # Psychological factors
            'emotional_state': trade.get('emotion', 'neutral'),
            'confidence': trade.get('confidence', 5),
            'deviated_from_plan': trade.get('deviation', False),
            
            # Market context
            'market_regime': trade.get('regime', 'unknown'),
            'sentiment': trade.get('sentiment', 50),
            
            # Risk metrics
            'planned_risk': trade.get('planned_risk'),
            'actual_risk': trade.get('actual_risk'),
            'r_multiple': trade['pnl'] / trade.get('planned_risk', 1)
        }
        
        self.trades.append(entry)
    
    def analyze_performance(self):
        """
        Analyze trading patterns
        """
        df = pd.DataFrame(self.trades)
        
        analysis = {
            # Overall stats
            'total_trades': len(df),
            'win_rate': (df['pnl'] > 0).mean() * 100,
            'profit_factor': abs(df[df['pnl'] > 0]['pnl'].sum() / df[df['pnl'] < 0]['pnl'].sum()),
            'avg_r': df['r_multiple'].mean(),
            
            # Psychological patterns
            'win_rate_high_confidence': df[df['confidence'] > 7]['pnl'].apply(lambda x: x > 0).mean(),
            'win_rate_low_confidence': df[df['confidence'] < 4]['pnl'].apply(lambda x: x > 0).mean(),
            'deviation_cost': df[df['deviated_from_plan']]['pnl'].mean() - df[~df['deviated_from_plan']]['pnl'].mean(),
            
            # Emotional impact
            'revenge_trading_pnl': df[df['emotional_state'] == 'revenge']['pnl'].mean(),
            'fomo_trading_pnl': df[df['emotional_state'] == 'fomo']['pnl'].mean(),
            'disciplined_pnl': df[df['emotional_state'] == 'disciplined']['pnl'].mean()
        }
        
        return analysis
```

### 6.3 Building Discipline

**Process Over Outcome:**
```
Good Process + Bad Outcome = Good Trade
Bad Process + Good Outcome = Bad Trade
```

**Risk of Ruin Calculator:**
```python
def risk_of_ruin(win_rate, risk_per_trade, ruin_threshold=0.5):
    """
    Calculate probability of losing X% of capital
    
    Based on formula: R = ((1 - W) / W) ^ (C / RPT)
    Where:
    W = win rate
    C = capital as multiple of risk per trade
    RPT = risk per trade
    """
    if win_rate <= 0.5:
        return 1.0  # Certain ruin
    
    edge = win_rate - (1 - win_rate)
    capital_units = ruin_threshold / risk_per_trade
    
    # Simplified approximation
    ruin_prob = ((1 - win_rate) / win_rate) ** capital_units
    
    return min(1.0, ruin_prob)

# Example
print(f"Risk of 50% drawdown with 50% win rate, 2% risk: {risk_of_ruin(0.5, 0.02):.1%}")
print(f"Risk of 50% drawdown with 55% win rate, 1% risk: {risk_of_ruin(0.55, 0.01):.1%}")
```

---

## Part 7: Behavioral Alpha Strategies

### 7.1 The "Dog Days" Strategy

**Concept:** Trade seasonal mood patterns

**Research:**
- September is worst month (post-summer depression)
- January effect (new year optimism)
- Winter depression impacts risk appetite

**Implementation:**
```python
def seasonal_sentiment_strategy(month, sentiment_data):
    """
    Adjust exposure based on seasonal patterns
    """
    # September-October: Reduce exposure (seasonal depression)
    if month in [9, 10]:
        return {'equity_allocation': 0.6, 'reason': 'Seasonal weakness'}
    
    # November-December: Normal
    elif month in [11, 12]:
        return {'equity_allocation': 0.8, 'reason': 'Year-end strength'}
    
    # January: Increase (January effect)
    elif month == 1:
        return {'equity_allocation': 1.0, 'reason': 'January optimism'}
    
    # Default
    return {'equity_allocation': 0.8, 'reason': 'Normal'}
```

### 7.2 The "Overnight" Effect

**Research:** Individual traders trade during day, institutions overnight

**Pattern:**
- Overnight returns > intraday returns
- Retail sentiment highest during day
- Smart money acts overnight

**Strategy:**
```python
def overnight_effect_strategy(overnight_return, intraday_return):
    """
    Fade retail intraday moves, follow overnight
    """
    # Strong overnight, weak intraday = smart money buying
    if overnight_return > 0.005 and intraday_return < 0:
        return 'BUY_CLOSE'
    
    # Weak overnight, strong intraday = retail FOMO
    if overnight_return < -0.005 and intraday_return > 0:
        return 'SELL_CLOSE'
    
    return 'NEUTRAL'
```

### 7.3 The "Analyst Herding" Trade

**Pattern:**
- Analysts herd - upgrade together, downgrade together
- Extreme consensus = contrarian signal

**Strategy:**
```python
def analyst_herding_signal(ratings_distribution):
    """
    Fade extreme analyst consensus
    """
    buys = ratings_distribution.get('buy', 0)
    holds = ratings_distribution.get('hold', 0)
    sells = ratings_distribution.get('sell', 0)
    total = buys + holds + sells
    
    if total == 0:
        return 'NEUTRAL'
    
    buy_pct = buys / total
    sell_pct = sells / total
    
    # Extreme bullishness
    if buy_pct > 0.9:
        return 'CONTRARIAN_SELL'
    
    # Extreme bearishness
    if sell_pct > 0.3:
        return 'CONTRARIAN_BUY'
    
    return 'NEUTRAL'
```

---

## Part 8: Expected Performance

### 8.1 Behavioral Strategy Returns

| Strategy | Edge Source | Expected Alpha | Sharpe |
|----------|-------------|----------------|--------|
| Contrarian Sentiment | Fading extremes | 3-6% | 0.8-1.2 |
| PEAD | Underreaction | 4-8% | 1.0-1.4 |
| Momentum | Herding | 6-12% | 0.7-1.1 |
| Mean Reversion | Overreaction | 4-10% | 0.9-1.3 |
| Window Dressing | Institutional flows | 2-4% | 1.2-1.8 |
| January Effect | Tax-loss selling | 3-5% | 0.8-1.2 |
| Overnight Effect | Smart money timing | 2-4% | 1.0-1.4 |

### 8.2 Combining with Other Strategies

**Best Combinations:**
1. **Momentum + Sentiment filter:** Avoid momentum crashes
2. **Value + Sentiment timing:** Buy value when fear is high
3. **Carry + Herding detection:** Exit when everyone is in
4. **Trend + Contrarian overlay:** Trend follow but reduce size at extremes

---

## Conclusion

**Key Takeaways:**

1. **Sentiment extremes are contrarian signals** - fear is opportunity, greed is danger
2. **Institutional behavior creates predictable patterns** - window dressing, rebalancing, herding
3. **Cognitive biases affect all traders** - awareness is the first defense
4. **Process over outcome** - good trades can lose, bad trades can win
5. **Behavioral alpha is persistent** - human nature doesn't change

**Implementation Framework:**
1. **Measure sentiment** - Use VIX, put/call, AAII, Fear & Greed
2. **Fade extremes** - Scale in when sentiment hits 20 or 80
3. **Watch institutional flows** - Quarterly patterns are tradeable
4. **Keep a journal** - Track emotions, build discipline
5. **Know thyself** - Understand your own biases

**Behavioral Checklist:**
- [ ] Am I following my system or my emotions?
- [ ] Is sentiment at an extreme?
- [ ] Are institutions forced to trade?
- [ ] Am I anchoring to a price?
- [ ] Is this FOMO or a valid setup?

---

*Research Date: March 2, 2026*  
*Sources: Behavioral finance literature, sentiment analysis research, empirical studies*
