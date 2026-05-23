# Algorithm Backup Plan Architecture
## Emergency Backup Strategy for Trading Operations

**Document Version:** 1.0  
**Last Updated:** 2026-02-17  
**Classification:** OPERATIONS CRITICAL  
**Owner:** Trading Operations Team

---

## Executive Summary

This document establishes a comprehensive backup hierarchy for all trading algorithms across five asset classes. Given the current state of underperforming live algorithms, this plan ensures zero-downtime continuity through a 4-tier backup system.

**Key Principle:** *Never trade without a backup. Never rely on a single point of failure.*

---

## 1. BACKUP HIERARCHY OVERVIEW

### Tier Structure

| Tier | Name | Response Time | Human Involvement | Risk Level |
|------|------|---------------|-------------------|------------|
| 0 | Primary (Live) | Real-time | None | Normal |
| 1 | Backup 1 (Auto-Failover) | < 30 seconds | None | Low |
| 2 | Backup 2 (Manual Override) | < 5 minutes | Required | Medium |
| 3 | Backup 3 (Shutdown Protocol) | Immediate | Required | Emergency |

### Failover Triggers

```
PRIMARY → BACKUP 1: Performance degradation > 15% or signal failure
BACKUP 1 → BACKUP 2: Backup 1 fails validation or 3 consecutive errors
BACKUP 2 → BACKUP 3: Manual decision OR circuit breaker triggered
```

---

## 2. ASSET CLASS BACKUP PLANS

### 2.1 STOCKS (Large Cap / Equities)

#### Primary Algorithm: Live ML Momentum Strategy
- **Description:** Deep learning model predicting 1-5 day price movements
- **Complexity:** High
- **Dependencies:** Real-time market data, ML inference cluster
- **Current Status:** ⚠️ UNDERPERFORMING (-8% vs benchmark)

#### Backup 1: VWAP Mean Reversion
- **Description:** Simple volume-weighted average price mean reversion
- **Logic:** Buy when price < VWAP - 2σ, Sell when price > VWAP + 2σ
- **Parameters:**
  - Lookback: 20 periods
  - Entry threshold: 2 standard deviations
  - Position size: 2% max per trade
  - Stop loss: 1.5% from entry
- **Why This Works:** Proven over decades, minimal parameters, no ML dependencies
- **Activation:** Automatic on primary failure

#### Backup 2: Manual Sector Rotation
- **Description:** Human trader executes based on macro sector trends
- **Process:**
  1. Halt all automated trading
  2. Review sector heatmap (finviz.com, tradingview)
  3. Identify strongest/weakest sectors
  4. Execute SPY/QQQ/IWM options or sector ETFs
  5. Position sizing: Max 5% per trade, 20% total exposure
- **Tools Required:** Broker platform, real-time news feed
- **Expected Response:** 5-15 minutes to full deployment

#### Backup 3: Shutdown Triggers
- Portfolio drawdown > 10% in single session
- VIX spike > 40 (market panic)
- Primary + Backup 1 both fail within 1 hour
- News event: Fed announcement, earnings surprise, geopolitical shock

---

### 2.2 PENNY STOCKS (Microcap / Low Float)

#### Primary Algorithm: Breakout Scanner + Momentum
- **Description:** Scans for volume spikes and price breakouts
- **Complexity:** Medium-High
- **Dependencies:** Level 2 data, social sentiment feeds
- **Current Status:** ⚠️ BROKEN (signal latency issues)

#### Backup 1: Volume Spike Alert System
- **Description:** Simple threshold-based volume alerts
- **Logic:** Alert when volume > 3x 20-day average AND price change > 5%
- **Parameters:**
  - Min price: $0.10 (avoid delisting risk)
  - Max price: $10.00 (penny stock range)
  - Min volume: 100K shares
  - Float: < 100M shares preferred
- **Execution:** Market orders with 2% position max
- **Why This Works:** Captures the same moves as complex algos but simpler

#### Backup 2: Manual Float Rotation
- **Description:** Human scans for low-float momentum plays
- **Process:**
  1. Use scanners: TradeIdeas, Benzinga Pro, or ThinkOrSwim
  2. Filter: Float < 50M, Volume > 1M, Price $0.50-$5
  3. Check for catalysts (news, filings, sector momentum)
  4. Enter on confirmed breakout with volume
  5. Hard stops: -5% max loss per trade
- **Position Sizing:** Max 1% per trade (high risk asset class)
- **Daily Loss Limit:** 3% of account

#### Backup 3: Shutdown Triggers
- Any single loss > 5% of position
- Three consecutive losing trades
- SEC halt or trading suspension on any held position
- Liquidity dries up (spread > 5% of price)
- Account drawdown > 15% from high water mark

---

### 2.3 CRYPTO (Bitcoin, Ethereum, Altcoins)

#### Primary Algorithm: Multi-Timeframe Trend Following
- **Description:** ML-enhanced trend detection across 4h/1d/1w timeframes
- **Complexity:** High
- **Dependencies:** Exchange APIs, on-chain data, funding rates
- **Current Status:** ⚠️ UNDERPERFORMING (whipsaw losses)

#### Backup 1: Dual Moving Average Crossover
- **Description:** Golden cross / death cross system
- **Logic:** 
  - Long when 50 EMA crosses above 200 EMA
  - Short when 50 EMA crosses below 200 EMA (if allowed)
  - Flat when EMAs converge (no signal)
- **Parameters:**
  - Fast EMA: 50 periods
  - Slow EMA: 200 periods
  - Timeframe: 4-hour candles
  - Position size: 5% max per asset
- **Why This Works:** Catches major trends, avoids chop, battle-tested

#### Backup 2: Manual Support/Resistance Trading
- **Description:** Human trades key technical levels
- **Process:**
  1. Identify major S/R levels on daily/weekly charts
  2. Wait for price to approach key level
  3. Confirm with volume and candlestick patterns
  4. Enter with tight stops below/above level
  5. Take profits at next major level
- **Key Levels to Watch:**
  - BTC: $40K, $50K, $60K, $70K psychological levels
  - ETH: $2K, $2.5K, $3K, $4K psychological levels
- **Risk:** 2% max per trade, 10% total crypto exposure

#### Backup 3: Shutdown Triggers
- Exchange API failure or withdrawal freeze
- Regulatory announcement (SEC, etc.)
- 20% single-day move (extreme volatility)
- Funding rate > 0.1% (overheated market)
- Stablecoin depeg event (USDT, USDC)

---

### 2.4 MEME STOCKS / SOCIAL SENTIMENT

#### Primary Algorithm: Reddit/Twitter Sentiment Engine
- **Description:** NLP analysis of social media for ticker mentions
- **Complexity:** High
- **Dependencies:** Social media APIs, sentiment models, options flow
- **Current Status:** ⚠️ BROKEN (API rate limits, model drift)

#### Backup 1: Unusual Options Activity Scanner
- **Description:** Detect large block trades and sweep orders
- **Logic:** Alert when:
  - Volume > 2x open interest
  - Premium > $100K in single order
  - Out-of-the-money calls being bought aggressively
- **Parameters:**
  - Min volume: 5x average daily volume
  - Focus: Near-term expirations (1-4 weeks)
  - Direction: Follow the smart money (call buying = bullish)
- **Execution:** Enter within 15 minutes of alert
- **Why This Works:** Smart money often precedes social media hype

#### Backup 2: Manual Social Monitoring
- **Description:** Human monitors key communities
- **Process:**
  1. Check r/wallstreetbets, r/pennystocks, StockTwits hourly
  2. Look for tickers with 3+ mentions in hot posts
  3. Verify with volume spike on chart
  4. Enter early (before mainstream news)
  5. Exit on hype peak (when CNBC mentions it)
- **Tools:** Reddit, Twitter, Discord, StockTwits
- **Risk Management:** 1% max, 24-48 hour holds only

#### Backup 3: Shutdown Triggers
- Position moves > 50% intraday (exit immediately)
- Broker restricts trading (meme stock circuit breaker)
 - Short squeeze peak indicators (parabolic move + volume drop)
- Social sentiment turns negative rapidly
- Any halt/resume cycle

---

### 2.5 FOREX (Currency Pairs)

#### Primary Algorithm: Carry Trade + Macro Model
- **Description:** Interest rate differential trading with macro overlays
- **Complexity:** Medium-High
- **Dependencies:** Central bank data, economic calendar, rate forecasts
- **Current Status:** ⚠️ UNDERPERFORMING (range-bound markets)

#### Backup 1: RSI Range Trading
- **Description:** Mean reversion using Relative Strength Index
- **Logic:**
  - Buy when RSI(14) < 30 (oversold)
  - Sell when RSI(14) > 70 (overbought)
  - Only trade in established ranges (ADX < 25)
- **Parameters:**
  - RSI period: 14
  - Entry: RSI 30/70
  - Exit: RSI 50 (neutral) or stop loss
  - Stop loss: 1% from entry
  - Take profit: 2% (2:1 R/R)
- **Best Pairs:** EUR/USD, USD/JPY, GBP/USD (liquid, low spread)

#### Backup 2: Manual Economic Calendar Trading
- **Description:** Trade major news events
- **Process:**
  1. Review Forex Factory calendar daily
  2. Identify high-impact events (red folder)
  3. Wait 5 minutes after release for dust to settle
  4. Trade in direction of surprise vs consensus
  5. Use tight stops (0.5% risk)
- **Key Events:** NFP, CPI, FOMC, ECB, BOE, GDP
- **Risk:** 1% per event, max 2 events per day

#### Backup 3: Shutdown Triggers
- Spread widens > 5 pips on major pairs
- Broker slippage > 3 pips consistently
- Flash crash or extreme volatility event
- Geopolitical crisis (war, sanctions)
- Account drawdown > 8% (forex is leveraged)

---

## 3. ALGORITHM FAILOVER AUTOMATION

### 3.1 Health Check System

```python
# Pseudocode for failover logic

class AlgorithmMonitor:
    
    CHECK_INTERVAL = 30  # seconds
    
    def health_check(self, algorithm):
        checks = {
            'heartbeat': algorithm.last_ping < 60,
            'performance': algorithm.pnl_1h > -0.5%,  # Max 0.5% hourly loss
            'signal_quality': algorithm.signal_accuracy > 40%,  # Min 40% win rate
            'latency': algorithm.execution_latency < 500ms,
            'error_rate': algorithm.errors_1h < 3
        }
        return all(checks.values())
    
    def failover(self, asset_class):
        primary = self.get_primary(asset_class)
        backup1 = self.get_backup1(asset_class)
        
        if not self.health_check(primary):
            self.log_emergency(f"Primary failed for {asset_class}")
            self.activate_backup1(asset_class)
            self.alert_ops_team(asset_class, primary.status)
```

### 3.2 Failover Decision Matrix

| Condition | Action | Notification |
|-----------|--------|--------------|
| Primary latency > 1s | Activate Backup 1 | Slack #trading-alerts |
| Primary 3 consecutive losses | Activate Backup 1 | SMS + Email |
| Primary error rate > 5/hour | Activate Backup 1 | Phone call |
| Backup 1 fails validation | Activate Backup 2 (Manual) | Emergency call |
| Circuit breaker triggered | Activate Backup 3 (Shutdown) | All channels |

### 3.3 Auto-Failover Configuration

```yaml
failover_config:
  stocks:
    primary: ml_momentum_v2
    backup1: vwap_mean_reversion
    activation_delay: 30s
    position_transfer: true
    
  penny_stocks:
    primary: breakout_scanner
    backup1: volume_spike_alert
    activation_delay: 15s
    position_transfer: false  # Close all, restart fresh
    
  crypto:
    primary: trend_following_ml
    backup1: dual_ma_crossover
    activation_delay: 60s
    position_transfer: true
    
  meme:
    primary: sentiment_engine
    backup1: unusual_options_activity
    activation_delay: 10s
    position_transfer: false
    
  forex:
    primary: carry_trade_macro
    backup1: rsi_range_trading
    activation_delay: 45s
    position_transfer: true
```

---

## 4. PERFORMANCE MONITORING ALERTS

### 4.1 Alert Severity Levels

| Level | Color | Response Time | Channel | Example |
|-------|-------|---------------|---------|---------|
| INFO | Blue | N/A | Slack | Daily P&L report |
| WARNING | Yellow | 1 hour | Slack + Email | Performance -5% |
| CRITICAL | Red | 15 minutes | SMS + Call | Backup activation |
| EMERGENCY | Purple | Immediate | All channels | Circuit breaker |

### 4.2 Alert Rules

```yaml
alerts:
  # Performance Alerts
  daily_loss:
    threshold: -3%
    severity: WARNING
    message: "Daily loss threshold exceeded"
    
  hourly_loss:
    threshold: -1%
    severity: CRITICAL
    message: "Hourly loss spike detected"
    
  drawdown:
    threshold: -10%
    severity: EMERGENCY
    message: "Maximum drawdown breached"
    action: initiate_shutdown
    
  # System Alerts
  latency_spike:
    threshold: 1000ms
    severity: WARNING
    message: "Execution latency elevated"
    
  api_error:
    threshold: 3 errors/5min
    severity: CRITICAL
    message: "API connectivity issues"
    
  signal_failure:
    threshold: 5 minutes no signal
    severity: CRITICAL
    message: "Signal generation failure"
    action: activate_backup1
    
  # Risk Alerts
  position_oversized:
    threshold: 110% of max
    severity: WARNING
    message: "Position size exceeds limits"
    
  correlation_spike:
    threshold: 0.9 correlation
    severity: WARNING
    message: "Portfolio correlation elevated"
    
  margin_call_risk:
    threshold: 80% margin used
    severity: CRITICAL
    message: "Approaching margin limits"
```

### 4.3 Alert Routing

```
INFO → Slack #trading-logs
WARNING → Slack #trading-alerts + Email
CRITICAL → SMS + Phone call + Slack #emergency
EMERGENCY → All channels + Auto-escalation to senior management
```

---

## 5. CIRCUIT BREAKERS

### 5.1 Account-Level Circuit Breakers

| Trigger | Threshold | Action | Cooldown |
|---------|-----------|--------|----------|
| Daily Loss Limit | -5% | Halt trading for 2 hours | Until next session |
| Max Drawdown | -15% | Halt trading for 24 hours | Manual reset only |
| Consecutive Losses | 5 trades | Reduce size by 50% | After 2 wins |
| Win Rate Drop | < 30% over 20 trades | Review strategy | Manual reset |
| Volatility Spike | VIX > 40 or equivalent | Reduce exposure 75% | VIX < 35 |

### 5.2 Asset Class Circuit Breakers

```yaml
circuit_breakers:
  stocks:
    single_position_loss: -5%
    sector_rotation: halt_if_sector_down_10%
    
  penny_stocks:
    daily_loss_limit: -3%
    single_trade_loss: -10%
    liquidity_check: spread_must_be_<_2%
    
  crypto:
    exchange_failure: halt_all_crypto
    stablecoin_depeg: convert_to_fiat
    funding_rate_extreme: close_if_>_0.1%
    
  meme:
    social_sentiment_flip: close_if_sentiment_turns_negative
    broker_restriction: immediate_liquidation
    parabolic_move: take_profit_50%
    
  forex:
    spread_widening: halt_if_spread_>_5_pips
    slippage_spike: halt_if_slippage_>_3_pips
    weekend_gap: close_all_friday_5pm
```

### 5.3 Manual Override

All circuit breakers can be manually overridden by:
- Head of Trading (any breaker)
- Risk Manager (account-level only)
- Requires two-person approval for emergency overrides
- Override logged with reason and timestamp

---

## 6. RECOVERY PROCEDURES

### 6.1 Algorithm Recovery Workflow

```
┌─────────────────┐
│  Detect Failure │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Activate Backup │
└────────┬────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Diagnose Issue  │────▶│ Can Fix Quickly?│
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌──────────────┐         ┌──────────────┐
            │ YES - Repair │         │ NO - Replace │
            └──────┬───────┘         └──────┬───────┘
                   ▼                        ▼
         ┌─────────────────┐      ┌─────────────────┐
         │ Test in Sandbox │      │ Deploy New Algo │
         └────────┬────────┘      └────────┬────────┘
                  ▼                        ▼
         ┌─────────────────┐      ┌─────────────────┐
         │ Validation Pass?│      │ Validation Pass?│
         └────────┬────────┘      └────────┬────────┘
                  │                        │
       ┌─────────┴─────────┐    ┌─────────┴─────────┐
       ▼                   ▼    ▼                   ▼
┌────────────┐      ┌────────────┐      ┌────────────┐
│ Promote to │      │ Keep Backup│      │ Keep Backup│
│ Primary    │      │ Running    │      │ Running    │
└────────────┘      └────────────┘      └────────────┘
```

### 6.2 Recovery Checklist

#### Phase 1: Immediate Response (0-15 minutes)
- [ ] Confirm primary algorithm failure
- [ ] Activate Backup 1 automatically
- [ ] Notify operations team
- [ ] Document failure time and symptoms
- [ ] Review open positions and P&L impact

#### Phase 2: Stabilization (15-60 minutes)
- [ ] Verify Backup 1 is functioning correctly
- [ ] Check all positions are as expected
- [ ] Review risk metrics
- [ ] Begin diagnostic of primary algorithm
- [ ] Update stakeholders

#### Phase 3: Diagnosis (1-4 hours)
- [ ] Review logs for error patterns
- [ ] Check data feeds and API connections
- [ ] Test primary algorithm in sandbox
- [ ] Identify root cause
- [ ] Estimate fix timeline

#### Phase 4: Recovery (4+ hours)
- [ ] Deploy fix to staging
- [ ] Run backtests to verify fix
- [ ] Schedule promotion to primary
- [ ] Gradual position transfer from Backup 1
- [ ] Monitor closely for 24 hours

### 6.3 Post-Incident Review

**Within 24 hours:**
- Timeline of events
- P&L impact analysis
- Root cause identification

**Within 1 week:**
- Detailed incident report
- Process improvements
- Algorithm enhancements
- Backup plan updates

---

## 7. EMERGENCY CONTACTS

| Role | Name | Primary | Secondary | After Hours |
|------|------|---------|-----------|-------------|
| Head of Trading | [TBD] | [TBD] | [TBD] | [TBD] |
| Risk Manager | [TBD] | [TBD] | [TBD] | [TBD] |
| Tech Lead | [TBD] | [TBD] | [TBD] | [TBD] |
| Operations | [TBD] | [TBD] | [TBD] | [TBD] |

---

## 8. APPENDICES

### Appendix A: Quick Reference Cards

#### Stock Trading - Backup 1 Activation
```
IF primary_ml_momentum fails:
  1. Auto-activate vwap_mean_reversion
  2. Parameters: lookback=20, threshold=2σ
  3. Position size: 2% max
  4. Stop loss: 1.5%
  5. Monitor for 30 minutes
```

#### Crypto Trading - Emergency Shutdown
```
IF shutdown_triggered:
  1. Close all leveraged positions IMMEDIATELY
  2. Spot holdings: evaluate case by case
  3. Withdraw to cold storage if exchange risk
  4. Document all actions
  5. Wait for 24h cool-down
```

### Appendix B: Backup Algorithm Code Templates

#### VWAP Mean Reversion (Python)
```python
def vwap_signal(prices, volumes, lookback=20):
    typical_price = (prices['high'] + prices['low'] + prices['close']) / 3
    vwap = (typical_price * volumes).rolling(lookback).sum() / volumes.rolling(lookback).sum()
    std = typical_price.rolling(lookback).std()
    
    current_price = prices['close'].iloc[-1]
    current_vwap = vwap.iloc[-1]
    current_std = std.iloc[-1]
    
    if current_price < current_vwap - 2 * current_std:
        return 'BUY'
    elif current_price > current_vwap + 2 * current_std:
        return 'SELL'
    return 'HOLD'
```

#### Dual MA Crossover (Python)
```python
def ma_crossover_signal(prices, fast=50, slow=200):
    fast_ma = prices.ewm(span=fast).mean()
    slow_ma = prices.ewm(span=slow).mean()
    
    if fast_ma.iloc[-2] <= slow_ma.iloc[-2] and fast_ma.iloc[-1] > slow_ma.iloc[-1]:
        return 'LONG'
    elif fast_ma.iloc[-2] >= slow_ma.iloc[-2] and fast_ma.iloc[-1] < slow_ma.iloc[-1]:
        return 'SHORT'
    return 'FLAT'
```

#### RSI Range Trading (Python)
```python
def rsi_signal(prices, period=14, oversold=30, overbought=70):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    current_rsi = rsi.iloc[-1]
    
    if current_rsi < oversold:
        return 'BUY'
    elif current_rsi > overbought:
        return 'SELL'
    return 'HOLD'
```

### Appendix C: Risk Limits Summary

| Asset Class | Max Position | Max Daily Loss | Max Drawdown | Leverage |
|-------------|--------------|----------------|--------------|----------|
| Stocks | 5% | -3% | -10% | 1x |
| Penny Stocks | 1% | -3% | -15% | 1x |
| Crypto | 5% | -5% | -20% | 2x max |
| Meme | 1% | -3% | -15% | 1x |
| Forex | 2% | -2% | -8% | 10x max |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-17 | Backup Plan Architect | Initial release |

**Next Review Date:** 2026-03-17  
**Review Cycle:** Monthly or after any major incident

---

*This document is classified as OPERATIONS CRITICAL. Keep updated and accessible to all trading personnel.*
