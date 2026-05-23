# Crypto/Forex/Stocks Prediction System Analysis
## Comprehensive Analysis of Database, Scoring & Prediction Mechanisms

**Date:** April 6, 2026  
**Analyst:** AI Coordination Team  
**Status:** Production System Analysis  

---

## Executive Summary

This document provides a deep analysis of the findtorontoevents.ca prediction ecosystem, covering database architecture, scoring mechanisms, prediction validation, and optimization opportunities. The system currently manages **2,359+ picks** across **5 asset classes** with **25+ prediction systems**.

### Key Metrics at a Glance
| Metric | Value |
|--------|-------|
| Total Picks Tracked | 2,359 |
| Active Picks | 385 |
| Closed Picks | 1,974 |
| Asset Classes | 5 (Crypto, Equity, Forex, Commodity, Futures) |
| Prediction Systems | 25+ |
| Top Engine Win Rate | 64.1% (Battleground) |
| Ensemble Win Rate | 68% |

---

## 1. Database Architecture Analysis

### 1.1 Current SQLite Schema (crypto_data.db)

The system uses a hybrid storage approach:
- **SQLite** (`crypto_data.db`, ~3.4MB) - Local price history, backtest results
- **MySQL** (`ejaguiar1_stocks`) - Production signal outcomes, audit trails
- **JSON Files** - Active picks, system manifests, portfolio tracking

#### Core Tables (Inferred from Code Analysis)

```sql
-- Price History (Time-Series Data)
CREATE TABLE price_history (
    symbol VARCHAR(20) NOT NULL,
    timestamp DATETIME NOT NULL,
    open DECIMAL(15,8),
    high DECIMAL(15,8),
    low DECIMAL(15,8),
    close DECIMAL(15,8),
    volume DECIMAL(20,8),
    PRIMARY KEY (symbol, timestamp)
);

-- Signal/Strategy Registry
CREATE TABLE strategy_registry (
    strategy_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    dna_hash VARCHAR(64),
    category ENUM('crypto', 'forex', 'equity', 'commodity'),
    status ENUM('active', 'paused', 'retired'),
    created_at TIMESTAMP,
    win_rate DECIMAL(5,2),
    total_trades INT,
    avg_return_pct DECIMAL(8,4)
);

-- Forward Test Outcomes (MySQL)
CREATE TABLE at_signal_outcomes (
    signal_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    strategy_name VARCHAR(50),
    entry_price DECIMAL(15,8),
    exit_price DECIMAL(15,8),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    pnl_pct DECIMAL(8,4),
    result ENUM('win', 'loss', 'expired'),
    exit_reason VARCHAR(50),
    INDEX idx_symbol_time (symbol, entry_time),
    INDEX idx_strategy (strategy_name)
);

-- Raw Picks (Active Signals)
CREATE TABLE at_raw_picks (
    pick_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20),
    direction ENUM('LONG', 'SHORT'),
    entry_price DECIMAL(15,8),
    take_profit DECIMAL(15,8),
    stop_loss DECIMAL(15,8),
    score INT,  -- 0-100
    trust_score DECIMAL(4,2),
    system VARCHAR(50),
    strategy VARCHAR(50),
    entry_time TIMESTAMP,
    status ENUM('active', 'closed'),
    unrealized_pnl_pct DECIMAL(8,4)
);
```

### 1.2 Database Strengths

| Strength | Description |
|----------|-------------|
| **Partitioning** | Time-series data partitioned by date ranges |
| **Indexing** | Multi-column indexes on symbol/timestamp |
| **Audit Trail** | Complete signal lifecycle tracking |
| **Multi-Source** | SQLite + MySQL separation of concerns |
| **JSON Flexibility** | Schema-less picks for rapid iteration |

### 1.3 Database Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No data quality scoring | Cannot detect stale/anomalous data | HIGH |
| Missing creator reputation (meme coins) | Higher rug pull risk | MEDIUM |
| No wallet/whale tracking | Missing on-chain intelligence | MEDIUM |
| Limited correlation tracking | Position concentration risk | HIGH |

---

## 2. Scoring Mechanism Deep Dive

### 2.1 Six-Dimension Scoring Framework

The genome/quality_engine.py implements a weighted scoring system:

| Component | Weight | Calculation Method |
|-----------|--------|-------------------|
| **Backtest Validity** | 25% | Sharpe × 0.4 + Profit Factor × 0.3 + Max DD × 0.3 |
| **Statistical Significance** | 20% | min(√(sample_size)/10, 1.0) × confidence_interval_factor |
| **Risk-Adjusted Return** | 20% | Sortino × 0.5 + Calmar × 0.5 |
| **Regime Alignment** | 15% | Current_regime_match × backtest_regime_performance |
| **Consensus Strength** | 10% | agreeing_systems / total_systems |
| **Market Structure** | 10% | liquidity_score × 0.5 + spread_score × 0.5 |

### 2.2 Grade Assignment

| Grade | Score Range | Action |
|-------|-------------|--------|
| A+ | 95-100 | Max allocation (5% per trade) |
| A | 90-94 | Full allocation (4% per trade) |
| A- | 85-89 | Standard allocation (3% per trade) |
| B+ | 80-84 | Reduced allocation (2% per trade) |
| B | 75-79 | Caution allocation (1.5% per trade) |
| B- | 70-74 | Minimum threshold (1% per trade) |
| C+ | 65-69 | Paper trade only |
| C | 60-64 | Do not trade |
| D | <60 | Reject - Eliminate from rotation |

### 2.3 Current Score Distribution

Based on 2,359 picks analysis:

| Score Range | Count | Avg uPnL% | In Profit | Hit Rate |
|-------------|-------|-----------|-----------|----------|
| 80+ | 90 | -2.08% | 44 | 48.9% |
| 60-79 | 50 | +3.59% | 33 | 66.0% |
| 40-59 | 53 | -1.23% | 21 | 42.0% |
| 20-39 | 48 | -1.37% | 12 | 29.3% |
| 1-19 | 54 | -2.55% | 8 | 15.4% |

**Key Finding:** Higher scores (80+) do NOT correlate with higher win rates in current data. This indicates scoring calibration issues.

### 2.4 Scoring Issues Identified

1. **Score Inversion**: Score 60-79 range shows best performance (+3.59% avg), while 80+ shows worst (-2.08%)
2. **Trust Score Decay**: Trust scores appear inflated for legacy systems
3. **Missing Regime Weighting**: Same score in trending vs ranging markets should have different confidence

---

## 3. Prediction Mechanisms

### 3.1 Strategy DNA System

Each strategy is encoded with a "DNA" signature:

```json
{
  "strategy_id": "ema_cross_btc_1h_v1",
  "dna_hash": "a1b2c3d4e5f6",
  "genes": {
    "timeframe": "1h",
    "primary_indicator": "EMA",
    "entry_logic": "golden_cross",
    "exit_logic": "death_cross",
    "risk_profile": "medium",
    "position_sizing": "kelly_half",
    "market_regime": "trending"
  },
  "mutation_history": [],
  "parent_strategies": [],
  "created_at": "2026-03-02T00:00:00Z"
}
```

### 3.2 Combination Logic Types

| Type | Description | Use Case |
|------|-------------|----------|
| **AND** | All strategies must agree | High conviction, fewer trades |
| **OR** | Any strategy triggers | More signals, higher frequency |
| **MAJORITY** | >50% agreement | Balanced approach |
| **WEIGHTED** | Confidence-weighted voting | Dynamic based on performance |
| **SEQUENTIAL** | Primary triggers, secondary confirms | Confirmation-based |
| **CONSENSUS_75** | 75% agreement required | Institutional quality |

### 3.3 Active Prediction Systems (25+)

| System | Category | Status | Win Rate |
|--------|----------|--------|----------|
| Mercury 2 | ML Ensemble | Active | 62% |
| Battleground | Superpowers Arena | Active | 64.1% |
| Alpha Engine | ML Ensemble | Active | 35.9% |
| DNA Genome Engine | Permutation | Active | TBD |
| KIMI Rise of the Claw | Signal Aggregation | Active | 58% |
| ML Battleground Ensemble | Battleground | Active | 68% |

### 3.4 Prediction Output Format

```json
{
  "id": "pick_btc_20260302_001",
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "entry_price": 85000.00,
  "take_profit": 93500.00,
  "stop_loss": 80750.00,
  "risk_reward": 2.0,
  "strategy_dna": "combo_ema_rsi_funding_btc",
  "quality_score": 87,
  "grade": "A-",
  "verdict": "STRONG_BUY",
  "confidence": 0.82,
  "position_size_pct": 3.5,
  "consensus_count": 4,
  "agreeing_systems": ["alpha_engine", "mercury2", "dna_genome", "kimi"]
}
```

---

## 4. Performance Analysis

### 4.1 Engine-by-Engine Breakdown

| Engine | Win Rate | Trades | PnL | Status |
|--------|----------|--------|-----|--------|
| **Battleground** | 64.1% | 334 | +1357% | BEST |
| **Ensemble** | 68% | 50+ | - | Exceptional |
| **Alpha Engine** | 35.9% | 156 | +12.2%/win | OK |
| **Baby Strats** | 41.8% | 1975 | -5433% | RETIRED |

### 4.2 Asset Class Performance

| Asset Class | Picks | Total uPnL% | Avg uPnL% | In Profit |
|-------------|-------|-------------|-----------|-----------|
| CRYPTO | 288 | +120.20% | +0.42% | 129/157 |
| EQUITY | 75 | -400.91% | -5.35% | 20/46 |
| FOREX | 17 | -0.99% | -0.06% | 7/7 |
| COMMODITY | 4 | +0.00% | +0.00% | 0/0 |

### 4.3 Direction Bias Analysis

| Direction | Picks | Total uPnL% | Avg uPnL% | Hit Rate |
|-----------|-------|-------------|-----------|----------|
| LONG | 303 | -626.24% | -2.07% | 33.3% |
| SHORT | 82 | +344.54% | +4.20% | 67.1% |

**Critical Finding:** The system shows extreme directional bias - SHORT positions significantly outperform LONG positions.

---

## 5. Critical Issues & Root Causes

### 5.1 Score Correlation Failure

**Problem:** Higher scores (80+) correlate with worse performance (-2.08%) than mid-range scores (60-79: +3.59%).

**Root Causes:**
1. Over-optimization on historical data
2. Market regime shift not captured in scoring
3. Legacy strategy scores not decayed after poor performance

### 5.2 Direction Conflicts

**Problem:** Same asset has both LONG and SHORT positions simultaneously.

**Example:**
- BTCUSDT LONG (Battleground) vs BTCUSDT SHORT (Alpha Engine Fast)
- Creates net-neutral exposure, wasted commissions

**Root Cause:** No portfolio-level net-exposure logic across systems.

### 5.3 Risk-Reward Issues

**Problem:** Tight R:R ratios on proven winners (e.g., 1.33:1) getting wiped by small moves.

**Recommendation:** Implement ATR-scaled TP/SL:
```python
atr_val = atr(high, low, close, 14).iloc[-1]
take_profit = entry + 2.5 * atr_val
stop_loss = entry - 1.5 * atr_val  # R:R ~1.67:1
```

### 5.4 Data Quality Concerns

| Issue | Evidence | Severity |
|-------|----------|----------|
| Duplicate picks | 167 duplicates found | HIGH |
| Score out of range | 1 pick with invalid score | MEDIUM |
| Missing asset class tagging | Multiple unclassified | MEDIUM |

---

## 6. Optimization Opportunities

### 6.1 Immediate (This Week)

| Action | Expected Impact | Effort |
|--------|-----------------|--------|
| Fix score calibration | Restore 80+ score correlation | 4 hours |
| Implement conflict detection | Eliminate opposing positions | 2 hours |
| Add ATR-scaled TP/SL | Improve R:R on winners | 3 hours |
| Deduplicate active picks | Clean up 167 duplicates | 1 hour |

### 6.2 Short-term (This Month)

| Action | Expected Impact | Effort |
|--------|-----------------|--------|
| Add HMA trend filter | Filter counter-trend signals | 8 hours |
| Implement regime weighting | Adjust scores by market state | 12 hours |
| Add wallet/whale tracking | Enhanced on-chain intelligence | 16 hours |
| Creator reputation scoring | Reduce rug pull exposure | 10 hours |

### 6.3 Long-term (This Quarter)

| Action | Expected Impact | Effort |
|--------|-----------------|--------|
| ML-based anomaly detection | Auto-detect bad signals | 40 hours |
| Streaming architecture | Real-time signal processing | 80 hours |
| Portfolio optimization | Mean-variance allocation | 60 hours |
| Cross-exchange arbitrage | New profit streams | 100 hours |

---

## 7. Redis Bus Integration

### 7.1 Recommended Message Format

```json
{
  "type": "prediction_update",
  "timestamp": "2026-04-06T12:00:00Z",
  "symbol": "BTCUSDT",
  "asset_class": "crypto",
  "direction": "LONG",
  "prediction": {
    "entry_price": 85000.00,
    "predicted_tp": 93500.00,
    "predicted_sl": 80750.00,
    "risk_reward": 2.0,
    "timeframe": "1h"
  },
  "scoring": {
    "quality_score": 87,
    "grade": "A-",
    "confidence": 0.82,
    "trust_score": 8.6,
    "components": {
      "backtest_validity": 0.92,
      "statistical_significance": 0.85,
      "risk_adjusted_return": 0.88,
      "regime_alignment": 0.75,
      "consensus_strength": 0.90,
      "market_structure": 0.80
    }
  },
  "systems": {
    "consensus_count": 4,
    "agreeing": ["alpha_engine", "mercury2", "dna_genome", "kimi"],
    "disagreeing": ["battleground"]
  },
  "validation": {
    "pre_trade_checks_passed": true,
    "sufficient_backtest_data": true,
    "no_recent_similar_signal": true,
    "liquidity_sufficient": true,
    "correlation_within_limits": true
  },
  "metadata": {
    "strategy_dna": "combo_ema_rsi_funding_btc",
    "regime": "trending_bull",
    "position_size_pct": 3.5,
    "expected_return_pct": 10.0,
    "max_risk_pct": 5.0
  }
}
```

### 7.2 Bus Commands

```bash
# Publish new prediction
rc PUBLISH predictions:new '{"symbol":"BTCUSDT",...}'

# Request score recalculation
rc LPUSH bus:tasks:pending '{"task":"recalc_scores","symbol":"BTCUSDT"}'

# Broadcast system status
rc LPUSH bus:broadcast:log '{"from":"alpha_engine","status":"generated_5_picks"}'

# Conflict alert
rc PUBLISH alerts:conflict '{"symbol":"BTCUSDT","long_count":3,"short_count":2}'
```

---

## 8. Recommendations Summary

### 8.1 Must Fix (P0)

1. **Score Calibration** - Current scoring does not predict performance
2. **Conflict Resolution** - Same asset LONG/SHORT simultaneously
3. **Duplicate Cleanup** - 167 duplicate picks in active set

### 8.2 Should Fix (P1)

1. **ATR-Based TP/SL** - Improve risk-reward ratios
2. **HMA Trend Filter** - Filter counter-trend signals
3. **Regime Weighting** - Adjust scores by market state

### 8.3 Could Fix (P2)

1. **On-Chain Integration** - Whale wallet tracking
2. **Creator Reputation** - Meme coin rug pull protection
3. **Streaming Architecture** - Real-time processing

---

## 9. Conclusion

The findtorontoevents.ca prediction system is a sophisticated multi-engine platform with significant potential. Key findings:

### Strengths
- **Diverse System Ecosystem** - 25+ prediction engines reduce single-point failure
- **Comprehensive Tracking** - Full signal lifecycle from generation to outcome
- **DNA-Based Evolution** - Genetic algorithm approach to strategy improvement
- **Strong SHORT Performance** - 67.1% hit rate on short positions

### Weaknesses
- **Score Correlation Failure** - Higher scores do not predict better outcomes
- **Direction Conflicts** - No cross-system exposure netting
- **LONG Bias Underperformance** - LONG positions showing -2.07% average
- **Data Quality Issues** - Duplicates and misclassified picks

### Path to World-Class
1. Fix scoring calibration to restore predictive power
2. Implement portfolio-level conflict resolution
3. Add dynamic regime detection and weighting
4. Expand on-chain intelligence integration

---

**Document Version:** 1.0  
**Last Updated:** April 6, 2026  
**Next Review:** April 13, 2026
