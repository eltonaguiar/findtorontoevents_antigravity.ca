# 🗄️ Database Infrastructure - Multi-Asset Trading System

## Executive Summary

Built a world-class MySQL database infrastructure leveraging your existing mysql.50webs.com databases, optimized for **#1 worldwide trading system** (zero API budget) across crypto, meme coins, stocks, penny stocks, and forex.

## 🏗️ Architecture

### 3-Database Setup

| Database | Purpose | Credentials |
|----------|---------|-------------|
| `ejaguiar1_memecoin` | Crypto + Meme coins | ejaguiar1_memecoin / testing123 |
| `ejaguiar1_stocks` | Stocks + Penny stocks | ejaguiar1_stocks / stocks |
| `ejaguiar1_favcreators` | Forex + Overflow | ejaguiar1 / Solid-Kitten-92-Brave-Vessel |

### Tables Created

#### 📊 ejaguiar1_memecoin (Primary Crypto)
```
crypto_assets          - 500+ crypto/meme coin metadata
crypto_ohlcv           - Time-series OHLCV candles (partitioned)
crypto_indicators      - Pre-computed TA (RSI, MACD, EMA, etc.)
crypto_patterns        - Pattern recognition with embeddings
crypto_signals         - Trading signals with backtest tracking
meme_coin_stats        - Special meme coin metrics (volatility, social)
crypto_market_data     - Global market metrics (dominance, fear/greed)
crypto_correlations    - Asset correlation matrix
ml_models              - ML model registry & versioning
ml_model_performance   - Model backtest tracking
```

#### 📈 ejaguiar1_stocks (Equities)
```
stock_assets           - Stock metadata (sector, industry)
stock_ohlcv            - Stock price history
penny_stocks           - Penny stock special tracking (float, catalysts)
stock_signals          - Stock trading signals
crypto_ohlcv           - Crypto mirror (hybrid trading)
crypto_signals         - Crypto signals mirror
```

#### 💱 ejaguiar1_favcreators (Forex)
```
forex_pairs            - Currency pair metadata
forex_ohlcv            - Forex price history
economic_events        - Economic calendar (NFP, CPI, etc.)
```

## 🚀 Key Features

### 1. Unified Interface (`unified_interface.py`)
```python
from database import get_trading_db

db = get_trading_db()

# Auto-routes to correct database
db.save_ohlcv('BTC', '1h', timestamp, o, h, l, c, v)
db.save_ohlcv('AAPL', '1d', timestamp, o, h, l, c, v)  # Goes to stocks DB
db.save_ohlcv('EURUSD', '1h', timestamp, o, h, l, c, v)  # Goes to forex

# Pattern matching with caching
patterns = db.find_patterns('BTC', 'bull_flag', min_confidence=0.8)

# ML model registry
db.register_model('xgboost_v1', version='1.0', accuracy=0.85)
```

### 2. Pattern Recognition Storage
- Embedding vectors stored as JSON for similarity search
- Success tracking (times_observed, times_successful)
- Confidence scoring
- Features extraction for ML

### 3. ML Model Versioning
```sql
ml_models:
  - model_name, model_version
  - accuracy, precision, recall, f1_score
  - features_used (JSON)
  - hyperparameters (JSON)
  - is_active flag
  - training date range
```

### 4. Performance Optimizations
- **Partitioned tables** by timestamp (fast time-series queries)
- **Composite indexes** on (symbol, timeframe, timestamp)
- **Cached queries** for pattern matching (@lru_cache)
- **Batch inserts** for OHLCV data (1000s of candles at once)
- **Connection pooling** across 3 databases

## 📊 Database Schema

### crypto_ohlcv (Partitioned)
```sql
CREATE TABLE crypto_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(18, 8),
    high DECIMAL(18, 8),
    low DECIMAL(18, 8),
    close DECIMAL(18, 8),
    volume DECIMAL(24, 8),
    UNIQUE KEY (symbol, timeframe, timestamp),
    INDEX (symbol, timestamp)
) PARTITION BY RANGE (timestamp);
```

### crypto_signals (Backtest Tracking)
```sql
CREATE TABLE crypto_signals (
    signal_id VARCHAR(50) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type ENUM('buy', 'sell', 'strong_buy', 'strong_sell'),
    entry_price DECIMAL(18, 8),
    target_price_1, target_price_2, target_price_3,
    stop_loss DECIMAL(18, 8),
    status ENUM('active', 'hit_target_1', 'hit_target_2', 'hit_target_3', 'stopped_out'),
    pnl_percent DECIMAL(8, 4),  -- Tracked for validation
    strategy VARCHAR(50),
    indicators_triggered JSON
);
```

### meme_coin_stats (Special Tracking)
```sql
CREATE TABLE meme_coin_stats (
    symbol VARCHAR(20) PRIMARY KEY,
    launch_timestamp BIGINT,
    volatility_30d DECIMAL(8, 4),    -- Key for meme coins
    max_daily_gain/loss DECIMAL(8, 4),
    meme_category ENUM('animal', 'political', 'celebrity', 'food'),
    twitter_followers INT,
    telegram_members INT,
    is_rug_pull BOOLEAN,
    pump_score INT
);
```

## 🎯 Usage Examples

### Initialize Schema
```bash
cd crypto_research/database
python schema_extensions.py
```

### Save Real-Time Data
```python
from database import get_trading_db
from live_data_connector import LiveDataConnector

db = get_trading_db()
connector = LiveDataConnector()

# Get live prices
prices = connector.get_live_prices()

# Store in database
for symbol, data in prices.items():
    db.save_ohlcv(symbol, '1m', timestamp, 
                  data['price'], data['price'], 
                  data['price'], data['price'], 
                  data['volume'])
```

### Query Patterns
```python
# Find all bull flags for BTC with >80% confidence
patterns = db.find_patterns('BTC', pattern_type='bull_flag', 
                            min_confidence=0.8, limit=100)

# Get high-volatility meme coins
meme_coins = db.get_meme_coins(min_volatility=0.15, 
                               category='animal', 
                               limit=20)
```

### ML Model Tracking
```python
# Register new model
db.register_model(
    model_name='transformer_v2',
    version='2.1',
    model_type='transformer',
    asset_class='crypto',
    accuracy=0.823,
    features=['rsi', 'macd', 'ema_cross', 'volume_profile'],
    hyperparameters={'lr': 0.001, 'batch_size': 64}
)

# Get model performance
perf = db.get_model_performance('transformer_v2', days=30)
print(f"Win rate: {perf['correct_predictions']/perf['total_predictions']:.1%}")
```

## 📈 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Query Latency (OHLCV) | <50ms | TBD |
| Pattern Match | <100ms | TBD |
| Batch Insert (1000 rows) | <1s | TBD |
| Database Uptime | 99.9% | TBD |

## 🔧 Files Created

```
database/
├── __init__.py              # Package exports
├── multi_db_manager.py      # Connection manager for 3 DBs
├── schema_extensions.py     # Table creation SQL
├── unified_interface.py     # Single API for all operations
├── mysql_core.py            # Core MySQL connection (alt)
└── crypto_tables.py         # Crypto-specific schema (alt)
```

## 🌍 World Dominance Strategy

### Phase 1: Foundation ✅
- [x] Multi-database MySQL infrastructure
- [x] Unified interface for all asset classes
- [x] Pattern recognition storage
- [x] ML model versioning

### Phase 2: Data Ingestion (Next)
- [ ] Free crypto data (CoinGecko API - trial key active)
- [ ] Free stock data (Yahoo Finance)
- [ ] Free forex data (ECB/Free APIs)
- [ ] Meme coin social scraping (Twitter/Telegram)

### Phase 3: ML Pipeline
- [ ] Automated model training on historical patterns
- [ ] Real-time signal generation
- [ ] Backtest validation
- [ ] Model A/B testing

### Phase 4: Global #1
- [ ] <100ms pattern matching
- [ ] 75%+ win rate across all asset classes
- [ ] Zero API cost operation
- [ ] Open source community

## 🚀 Quick Start

```python
# 1. Test connections
from database import manager
manager.test_all_connections()

# 2. Create schemas
from database import SchemaManager
schema = SchemaManager()
schema.create_memecoin_schema()
schema.create_stocks_schema()
schema.create_forex_schema()

# 3. Start trading
from database import get_trading_db
db = get_trading_db()

# Save signal
db.save_signal('SIG_001', 'BTC', 'buy', 69200, 
               target_price=72000, stop_loss=67000)

# Query active signals
signals = db.get_active_signals()
```

## 📝 Environment Variables

Uses existing Windows environment variables:
```
FTP_USER=ejaguiar1
MYSQL_PASS_FAVCREATORS=Solid-Kitten-92-Brave-Vessel
DB_PASS_SERVER_FAVCREATORS=3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl
```

Hardcoded for convenience:
```
ejaguiar1_memecoin / testing123
ejaguiar1_stocks / stocks
```

---

**Status**: ✅ Infrastructure Complete  
**Next**: Data ingestion pipeline & ML training
