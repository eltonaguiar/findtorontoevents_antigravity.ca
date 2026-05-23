# DATABASE ANALYSIS REPORT
## Stock/Meme Coin Trading System Schema Analysis

**Date:** 2026-02-17  
**Analyst:** Database Analyzer Subagent  
**Scope:** SQL Schema Design for Algorithm Competition + Multi-Asset Tracking

---

## EXECUTIVE SUMMARY

This analysis provides a comprehensive comparison between **PROPER** database design for financial trading systems versus what is **TYPICALLY IMPLEMENTED** in hobby/mid-tier systems. The research covers stock tracking, meme coin monitoring, data quality validation, and API integration patterns.

---

## 1. STOCK TRACKING TABLES

### 1.1 PROPER Schema Design

```sql
-- Core ticker reference table
CREATE TABLE tickers (
    symbol VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(5) NOT NULL,  -- MIC code per ISO 10383
    sector VARCHAR(50),
    industry VARCHAR(100),
    market_cap_category ENUM('micro', 'small', 'mid', 'large', 'mega'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_exchange (exchange),
    INDEX idx_sector (sector)
) ENGINE=InnoDB;

-- Price history - DAILY granularity (EOD data)
CREATE TABLE price_history_daily (
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL,
    vwap DECIMAL(12,4),  -- Volume-weighted average price
    trades_count INT UNSIGNED,
    
    -- Technical indicators (pre-computed for performance)
    ema_9 DECIMAL(12,4),
    ema_20 DECIMAL(12,4),
    ema_50 DECIMAL(12,4),
    rsi_14 DECIMAL(5,2),
    
    -- Corporate actions tracking
    split_ratio DECIMAL(8,4) DEFAULT 1.0,
    dividend_amount DECIMAL(10,4) DEFAULT 0.00,
    
    -- Data quality flags
    is_adjusted BOOLEAN DEFAULT TRUE,
    data_source VARCHAR(20) NOT NULL,  -- 'yahoo', 'finnhub', 'polygon'
    data_quality_score TINYINT UNSIGNED,  -- 0-100
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, date),
    FOREIGN KEY (symbol) REFERENCES tickers(symbol),
    INDEX idx_date (date),
    INDEX idx_quality (data_quality_score)
) ENGINE=InnoDB PARTITION BY RANGE (YEAR(date)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pfuture VALUES LESS THAN MAXVALUE
);

-- Price history - INTRADAY (for real-time systems)
CREATE TABLE price_history_intraday (
    symbol VARCHAR(10) NOT NULL,
    timestamp DATETIME(3) NOT NULL,  -- Millisecond precision
    interval_seconds INT NOT NULL DEFAULT 60,  -- 1min, 5min, etc.
    open DECIMAL(12,4) NOT NULL,
    high DECIMAL(12,4) NOT NULL,
    low DECIMAL(12,4) NOT NULL,
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (symbol, timestamp, interval_seconds),
    FOREIGN KEY (symbol) REFERENCES tickers(symbol)
) ENGINE=InnoDB;
-- NOTE: For high-frequency data, use TimescaleDB hypertables instead

-- Algorithm definitions
CREATE TABLE algorithms (
    algo_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type ENUM('momentum', 'mean_reversion', 'arbitrage', 'ml_based', 'custom'),
    version VARCHAR(10) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,  -- SHA-256 of algo code for audit
    parameters_json JSON,  -- Configurable parameters
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    max_position_pct DECIMAL(5,2) DEFAULT 25.00,  -- Risk limit
    INDEX idx_strategy (strategy_type),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

-- Stock picks/positions (the competition entries)
CREATE TABLE picks (
    pick_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    algo_id VARCHAR(36) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    pick_type ENUM('long', 'short') NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    entry_timestamp TIMESTAMP NOT NULL,
    exit_price DECIMAL(12,4),
    exit_timestamp TIMESTAMP,
    position_size INT UNSIGNED NOT NULL,  -- Number of shares
    
    -- Competition context
    competition_id VARCHAR(36),
    round_number INT UNSIGNED,
    
    -- Performance metrics (calculated on exit)
    pnl_amount DECIMAL(15,4),
    pnl_percent DECIMAL(8,4),
    holding_period_hours DECIMAL(8,2),
    
    -- Status tracking
    status ENUM('open', 'closed', 'expired', 'stopped_out') DEFAULT 'open',
    
    -- Audit trail
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (algo_id) REFERENCES algorithms(algo_id),
    FOREIGN KEY (symbol) REFERENCES tickers(symbol),
    INDEX idx_algo_timestamp (algo_id, entry_timestamp),
    INDEX idx_status (status),
    INDEX idx_competition (competition_id)
) ENGINE=InnoDB;

-- Performance tracking (aggregated metrics)
CREATE TABLE performance_metrics (
    metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    algo_id VARCHAR(36) NOT NULL,
    competition_id VARCHAR(36),
    
    -- Time period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type ENUM('daily', 'weekly', 'monthly', 'competition') NOT NULL,
    
    -- Return metrics
    total_return_pct DECIMAL(10,4),
    annualized_return_pct DECIMAL(10,4),
    
    -- Risk metrics
    volatility DECIMAL(10,4),  -- Standard deviation
    max_drawdown_pct DECIMAL(10,4),
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    
    -- Trade statistics
    total_trades INT UNSIGNED,
    winning_trades INT UNSIGNED,
    losing_trades INT UNSIGNED,
    win_rate DECIMAL(5,2),
    avg_winner_pct DECIMAL(8,4),
    avg_loser_pct DECIMAL(8,4),
    profit_factor DECIMAL(8,4),
    
    -- Benchmark comparison
    benchmark_symbol VARCHAR(10) DEFAULT 'SPY',
    benchmark_return_pct DECIMAL(10,4),
    alpha DECIMAL(10,4),
    beta DECIMAL(8,4),
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (algo_id) REFERENCES algorithms(algo_id),
    UNIQUE KEY unique_period (algo_id, period_start, period_end, period_type),
    INDEX idx_return (total_return_pct),
    INDEX idx_sharpe (sharpe_ratio)
) ENGINE=InnoDB;

-- Audit log for all data changes
CREATE TABLE audit_log (
    audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    action ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    old_values JSON,
    new_values JSON,
    changed_by VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    INDEX idx_table_record (table_name, record_id),
    INDEX idx_timestamp (changed_at)
) ENGINE=InnoDB;
```

### 1.2 TYPICAL Implementation (What Usually Happens)

```sql
-- Simplified (often incomplete) schema
CREATE TABLE stocks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    symbol VARCHAR(10),
    name VARCHAR(100)
);

CREATE TABLE prices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stock_id INT,
    price DECIMAL(10,2),
    date DATE,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);

CREATE TABLE algorithms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50),
    code TEXT
);

CREATE TABLE picks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    algo_id INT,
    symbol VARCHAR(10),
    price DECIMAL(10,2),
    date DATE
);
```

**Common Issues in Typical Implementations:**
- ❌ No partitioning (slow queries on large datasets)
- ❌ No data quality tracking
- ❌ Missing audit trails
- ❌ No technical indicators pre-computed
- ❌ No risk metrics
- ❌ Missing benchmark comparisons
- ❌ No corporate action adjustments

---

## 2. MEME COIN TRACKING

### 2.1 PROPER Schema Design

```sql
-- Blockchain/network reference
CREATE TABLE blockchains (
    chain_id VARCHAR(20) PRIMARY KEY,  -- 'solana', 'ethereum', 'bsc'
    name VARCHAR(50) NOT NULL,
    native_token VARCHAR(10),
    rpc_endpoint VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

-- Token listings (meme coins and others)
CREATE TABLE tokens (
    token_id VARCHAR(100) PRIMARY KEY,  -- contract address
    chain_id VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    decimals INT UNSIGNED DEFAULT 9,
    
    -- Token metadata
    total_supply DECIMAL(30,0),
    circulating_supply DECIMAL(30,0),
    
    -- Creator/ownership info (crucial for pump detection)
    creator_address VARCHAR(100),
    creator_reputation_score DECIMAL(5,2),  -- 0-100 based on history
    
    -- Liquidity info
    liquidity_usd DECIMAL(20,2),
    liquidity_token_amount DECIMAL(30,0),
    liquidity_added_at TIMESTAMP,
    
    -- Launch info
    launch_platform ENUM('pump_fun', 'raydium', 'uniswap', 'pancakeswap', 'other'),
    launch_timestamp TIMESTAMP,
    launch_market_cap_usd DECIMAL(20,2),
    
    -- Status tracking
    is_migrated BOOLEAN DEFAULT FALSE,  -- Pump.fun specific
    migrated_to_dex VARCHAR(50),
    is_rug_pulled BOOLEAN DEFAULT FALSE,
    rug_pull_timestamp TIMESTAMP,
    
    -- Data quality
    is_verified BOOLEAN DEFAULT FALSE,
    verification_source VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chain_id) REFERENCES blockchains(chain_id),
    INDEX idx_chain (chain_id),
    INDEX idx_creator (creator_address),
    INDEX idx_launch_time (launch_timestamp),
    INDEX idx_platform (launch_platform)
) ENGINE=InnoDB;

-- Token price data (high frequency)
CREATE TABLE token_prices (
    token_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP(3) NOT NULL,  -- Millisecond precision
    
    -- Price data
    price_usd DECIMAL(20,10) NOT NULL,
    price_native DECIMAL(30,10),  -- Price in chain's native token
    
    -- Market data
    market_cap_usd DECIMAL(20,2),
    volume_24h_usd DECIMAL(20,2),
    liquidity_usd DECIMAL(20,2),
    
    -- Holder statistics
    holder_count INT UNSIGNED,
    holder_change_1h INT,
    
    -- Transaction metrics
    buy_count_1h INT UNSIGNED,
    sell_count_1h INT UNSIGNED,
    buy_volume_1h DECIMAL(20,2),
    sell_volume_1h DECIMAL(20,2),
    
    -- Data source
    source ENUM('dexscreener', 'birdeye', 'helius', 'direct_rpc') NOT NULL,
    
    PRIMARY KEY (token_id, timestamp),
    FOREIGN KEY (token_id) REFERENCES tokens(token_id)
) ENGINE=InnoDB;
-- NOTE: Use TimescaleDB hypertable for this: 
-- SELECT create_hypertable('token_prices', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- Pump detection metrics
CREATE TABLE pump_signals (
    signal_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    token_id VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Signal classification
    signal_type ENUM('early_pump', 'volume_spike', 'holder_growth', 
                     'whale_accumulation', 'social_mention_spike', 'suspicious_pattern'),
    confidence_score DECIMAL(5,2),  -- 0-100
    
    -- Trigger metrics
    price_change_1h_pct DECIMAL(10,4),
    price_change_5m_pct DECIMAL(10,4),
    volume_spike_ratio DECIMAL(10,2),  -- Current vs average
    holder_growth_1h_pct DECIMAL(10,4),
    
    -- Risk assessment
    rug_pull_risk_score DECIMAL(5,2),  -- 0-100
    risk_factors JSON,  -- Array of detected risk factors
    
    -- Creator history
    creator_previous_tokens_count INT UNSIGNED,
    creator_success_rate DECIMAL(5,2),  -- % of profitable launches
    
    -- Action taken
    was_traded BOOLEAN DEFAULT FALSE,
    trade_result ENUM('profit', 'loss', 'neutral', NULL),
    
    FOREIGN KEY (token_id) REFERENCES tokens(token_id),
    INDEX idx_token_time (token_id, detected_at),
    INDEX idx_confidence (confidence_score),
    INDEX idx_signal_type (signal_type)
) ENGINE=InnoDB;

-- Creator reputation tracking (crucial for meme coins)
CREATE TABLE creator_stats (
    creator_address VARCHAR(100) NOT NULL,
    chain_id VARCHAR(20) NOT NULL,
    
    -- Aggregate metrics
    total_tokens_created INT UNSIGNED DEFAULT 0,
    tokens_migrated INT UNSIGNED DEFAULT 0,
    tokens_rug_pulled INT UNSIGNED DEFAULT 0,
    
    -- Performance metrics
    avg_token_lifetime_hours DECIMAL(10,2),
    avg_max_market_cap DECIMAL(20,2),
    avg_roi_for_buyers DECIMAL(10,4),
    
    -- Reputation score (computed)
    reputation_score DECIMAL(5,2),  -- 0-100
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (creator_address, chain_id),
    FOREIGN KEY (chain_id) REFERENCES blockchains(chain_id),
    INDEX idx_reputation (reputation_score)
) ENGINE=InnoDB;

-- Wallet tracking (whale watching)
CREATE TABLE wallet_holdings (
    wallet_address VARCHAR(100) NOT NULL,
    token_id VARCHAR(100) NOT NULL,
    balance DECIMAL(30,0) NOT NULL,
    balance_usd DECIMAL(20,2),
    percentage_of_supply DECIMAL(8,4),
    
    -- Tracking
    first_acquired_at TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Classification
    wallet_type ENUM('retail', 'whale', 'dev', 'bot', 'exchange', 'unknown'),
    
    PRIMARY KEY (wallet_address, token_id),
    FOREIGN KEY (token_id) REFERENCES tokens(token_id),
    INDEX idx_wallet (wallet_address),
    INDEX idx_type (wallet_type)
) ENGINE=InnoDB;
```

### 2.2 TYPICAL Implementation

```sql
-- Basic token tracking only
CREATE TABLE meme_coins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    address VARCHAR(100),
    symbol VARCHAR(20),
    price DECIMAL(20,10),
    market_cap DECIMAL(20,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    coin_id INT,
    price DECIMAL(20,10),
    timestamp TIMESTAMP
);
```

**Critical Gaps in Typical Implementations:**
- ❌ No creator reputation tracking (essential for pump.fun)
- ❌ No wallet/whale tracking
- ❌ Missing rug pull detection
- ❌ No liquidity migration tracking
- ❌ No buy/sell pressure metrics
- ❌ Missing risk scoring

---

## 3. DATA QUALITY CHECKS

### 3.1 PROPER Data Quality Framework

```sql
-- Data quality validation table
CREATE TABLE data_quality_checks (
    check_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    check_type ENUM('price_stale', 'price_anomaly', 'volume_anomaly', 
                    'missing_data', 'source_discrepancy', 'timestamp_drift') NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    
    -- Issue details
    severity ENUM('info', 'warning', 'critical') NOT NULL,
    expected_value TEXT,
    actual_value TEXT,
    deviation_pct DECIMAL(10,4),
    
    -- Resolution
    status ENUM('open', 'investigating', 'resolved', 'false_positive') DEFAULT 'open',
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    INDEX idx_table (table_name, record_id)
) ENGINE=InnoDB;
```

### 3.2 Data Quality Validation Rules

| Check | Description | Action on Failure |
|-------|-------------|-------------------|
| **Price Staleness** | Price not updated in > 5 minutes | Flag as stale, use backup source |
| **Price Anomaly** | Price change > 20% in 1 minute | Validate against other sources |
| **Volume Anomaly** | Volume > 10x average | Manual review required |
| **Timestamp Drift** | Future timestamp or > 1 min old | Reject record, log error |
| **Source Discrepancy** | Price variance > 1% between sources | Weighted average or alert |
| **Zero Price** | Price = 0 or NULL | Reject, use last known good |

### 3.3 Real vs Simulated Data Detection

```sql
-- Data source tracking
CREATE TABLE data_source_log (
    source_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(50) NOT NULL,  -- 'yahoo_finance', 'finnhub', 'polygon', 'simulated'
    is_simulated BOOLEAN DEFAULT FALSE,
    is_delayed BOOLEAN DEFAULT FALSE,  -- 15-min delay for free tiers
    delay_minutes INT UNSIGNED DEFAULT 0,
    
    -- API metrics
    api_calls_count BIGINT UNSIGNED DEFAULT 0,
    api_errors_count BIGINT UNSIGNED DEFAULT 0,
    avg_response_ms INT UNSIGNED,
    
    last_successful_call TIMESTAMP,
    last_error TEXT,
    
    INDEX idx_simulated (is_simulated)
) ENGINE=InnoDB;
```

**Red Flags for Simulated Data:**
1. Prices always round to 2 decimal places
2. No after-hours/premarket data
3. Volume is always multiples of 100
4. No bid-ask spread data
5. Timestamps are exactly on the minute
6. No price gaps between sessions

---

## 4. API INTEGRATION ANALYSIS

### 4.1 Major Financial Data APIs

| Provider | Free Tier | Rate Limit | Real-time | Delay | Best For |
|----------|-----------|------------|-----------|-------|----------|
| **Yahoo Finance** (unofficial) | Free | ~2000/hour | ❌ | 15-20 min | Hobby projects |
| **Finnhub** | 60 calls/min | 60/min | ✅ WebSocket | Real-time | Small-scale |
| **Polygon.io** | 5 API calls/min | 5/min | ❌ | 15 min | Testing only |
| **Alpha Vantage** | 25 calls/day | 25/day | ❌ | Delayed | Very low volume |
| **IEX Cloud** | 50K messages/mo | Varies | ✅ | Real-time | Production |
| **Twelve Data** | 8 calls/min | 8/min | ❌ | Delayed | Basic needs |

### 4.2 Cryptocurrency/Meme Coin APIs

| Provider | Free Tier | Rate Limit | Chains | Notes |
|----------|-----------|------------|--------|-------|
| **Helius** (Solana) | Free tier | 100 req/sec | Solana | Best for Pump.fun |
| **Birdeye** | Limited | Varies | Multi | Good for DEX data |
| **DexScreener** | Free | 300 req/min | Multi | Rate limited |
| **Bitquery** | 100K credits | Varies | Multi | GraphQL API |
| **Moralis** | Free tier | Varies | Multi | Web3 focused |

### 4.3 PROPER API Integration Schema

```sql
-- API request tracking (for rate limiting and debugging)
CREATE TABLE api_request_log (
    request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    endpoint VARCHAR(100) NOT NULL,
    
    -- Request details
    request_params JSON,
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Response tracking
    response_status INT UNSIGNED,  -- HTTP status
    response_time_ms INT UNSIGNED,
    records_returned INT UNSIGNED,
    
    -- Error tracking
    error_code VARCHAR(50),
    error_message TEXT,
    retry_count TINYINT UNSIGNED DEFAULT 0,
    
    -- Rate limit tracking
    rate_limit_remaining INT,
    rate_limit_reset_at TIMESTAMP,
    
    INDEX idx_provider_time (provider, request_timestamp),
    INDEX idx_status (response_status)
) ENGINE=InnoDB PARTITION BY RANGE (UNIX_TIMESTAMP(request_timestamp)) (
    PARTITION p_recent VALUES LESS THAN (UNIX_TIMESTAMP('2025-01-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- API credentials and configuration
CREATE TABLE api_config (
    provider VARCHAR(50) PRIMARY KEY,
    api_key_encrypted TEXT,  -- Encrypted storage
    base_url VARCHAR(255),
    
    -- Rate limiting config
    max_requests_per_minute INT UNSIGNED,
    max_requests_per_day INT UNSIGNED,
    current_minute_count INT UNSIGNED DEFAULT 0,
    current_day_count INT UNSIGNED DEFAULT 0,
    minute_reset_at TIMESTAMP,
    day_reset_at TIMESTAMP,
    
    -- Feature flags
    is_active BOOLEAN DEFAULT TRUE,
    is_primary_source BOOLEAN DEFAULT FALSE,
    fallback_provider VARCHAR(50),
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;
```

---

## 5. REAL-TIME VS BATCH PROCESSING

### 5.1 Decision Matrix

| Use Case | Recommended Approach | Latency | Complexity |
|----------|---------------------|---------|------------|
| Price display dashboard | Real-time (WebSocket) | < 1s | Medium |
| Algorithm signal generation | Real-time (streaming) | < 5s | High |
| Performance reporting | Batch (hourly) | 1 hour | Low |
| Historical backtesting | Batch (nightly) | Daily | Low |
| Risk monitoring | Real-time | < 30s | High |
| Audit/compliance | Batch (daily) | Daily | Low |

### 5.2 PROPER Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Sources  │     │   Data Sources  │     │   Data Sources  │
│  (Stock APIs)   │     │   (DEX APIs)    │     │  (WebSockets)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Message Queue (Redis/Kafka)                 │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Real-time       │     │ Stream          │     │ Batch ETL       │
│ Processor       │     │ Processor       │     │ Pipeline        │
│ (Dashboard)     │     │ (Algorithms)    │     │ (Reporting)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Time-Series   │     │   Trading DB    │     │   Data Warehouse│
│    DB (Prices)  │     │   (Positions)   │     │   (Analytics)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 6. COMPARISON: PROPER vs TYPICAL

### 6.1 Schema Completeness

| Component | PROPER | TYPICAL |
|-----------|--------|---------|
| **Tickers** | 15+ fields with metadata | 3-4 fields |
| **Price History** | Partitioned, quality-scored | Single table |
| **Algorithms** | Versioned, hashed, parameterized | Simple name/code |
| **Picks/Positions** | Full lifecycle tracking | Entry only |
| **Performance** | 20+ metrics calculated | Basic P&L only |
| **Audit Trail** | Complete change history | None |
| **Meme Coins** | Creator rep + wallet tracking | Price only |
| **Pump Detection** | Multi-factor scoring | None |

### 6.2 Data Quality

| Aspect | PROPER | TYPICAL |
|--------|--------|---------|
| **Source Validation** | Multi-source verification | Single source |
| **Stale Detection** | < 5 min alerts | None |
| **Anomaly Detection** | Automated with thresholds | Manual only |
| **Audit Trail** | Immutable logs | None |
| **Backup Sources** | Configured fallback | None |

### 6.3 Performance

| Metric | PROPER | TYPICAL |
|--------|--------|---------|
| **Query Time (1 year)** | < 100ms | 5-30 seconds |
| **Storage Efficiency** | Compressed, partitioned | Unoptimized |
| **Concurrent Users** | 1000+ | < 50 |
| **Data Retention** | Configurable policies | Manual cleanup |

---

## 7. RED FLAGS TO WATCH FOR

### In Existing Databases:

1. **No timestamp columns** on critical tables
2. **No foreign key constraints** (data integrity issues)
3. **Prices stored as FLOAT** instead of DECIMAL (precision loss)
4. **No partitioning** on time-series tables
5. **Missing indexes** on query columns
6. **No data source tracking** (can't verify if real/simulated)
7. **No audit logs** (compliance risk)
8. **Single-table design** for everything
9. **No backup/DR strategy**
10. **No rate limiting tracking** (API ban risk)

### In API Integrations:

1. **Hardcoded API keys** in code
2. **No retry logic** with exponential backoff
3. **No fallback sources** configured
4. **No request logging** (can't debug issues)
5. **Polling instead of WebSockets** for real-time
6. **No rate limit tracking** (will get banned)

---

## 8. RECOMMENDATIONS

### Immediate Actions:

1. **Add audit logging** to all tables
2. **Implement data quality checks** with alerting
3. **Track API usage** to prevent rate limit violations
4. **Add source attribution** to all price data
5. **Implement partitioning** on time-series tables

### Short-term:

1. **Migrate to TimescaleDB** for time-series data
2. **Add creator reputation tracking** for meme coins
3. **Implement pump detection algorithms**
4. **Create automated performance metrics calculation**
5. **Add multi-source price validation**

### Long-term:

1. **Implement streaming architecture** for real-time data
2. **Add ML-based anomaly detection**
3. **Create data lineage tracking**
4. **Implement automated compliance reporting**

---

## 9. KEY TAKEAWAYS

1. **A proper financial database is 3-5x more complex** than typical implementations
2. **Data quality is more important than data quantity** - track source and confidence
3. **Audit trails are non-negotiable** for financial systems
4. **Time-series data requires special handling** (partitioning, compression)
5. **Meme coins need unique tracking** (creator rep, wallet analysis)
6. **API rate limits will kill your system** if not properly managed
7. **Real-time vs batch is an architectural decision** - not just a preference

---

*Report generated by Database Analyzer Subagent*
*For questions or clarifications, consult the main agent*
