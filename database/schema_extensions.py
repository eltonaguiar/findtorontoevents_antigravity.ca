#!/usr/bin/env python3
"""
================================================================================
SCHEMA EXTENSIONS FOR EXISTING DATABASES
================================================================================

Adds crypto/meme coin tables to existing databases:

1. ejaguiar1_memecoin (primary crypto database):
   - crypto_ohlcv, crypto_assets, crypto_signals
   - meme_coin_special (enhanced meme tracking)
   - crypto_patterns, crypto_indicators

2. ejaguiar1_stocks (stocks + crypto hybrid):
   - crypto_ohlcv (with prefix if needed)
   - stocks_ohlcv, stocks_assets
   - penny_stocks tracking
   
3. ejaguiar1_favcreators (forex + overflow):
   - forex_ohlcv, forex_pairs
   - crypto_backup tables

All tables optimized for:
- Fast time-series queries
- Pattern matching
- ML model storage
================================================================================
"""

from typing import Dict, List
from multi_db_manager import manager


# ============================================
# CRYPTO TABLES FOR MEMECOIN DATABASE
# ============================================
MEMECOIN_CRYPTO_SCHEMA = """
-- Crypto Assets Master List
CREATE TABLE IF NOT EXISTS crypto_assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset_type ENUM('major', 'altcoin', 'meme', 'defi', 'nft', 'layer2', 'gaming') DEFAULT 'altcoin',
    market_cap_category ENUM('mega', 'large', 'mid', 'small', 'micro', 'nano') DEFAULT 'mid',
    is_meme BOOLEAN DEFAULT FALSE,
    is_penny BOOLEAN DEFAULT FALSE,
    blockchain VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata JSON,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_type (asset_type),
    INDEX idx_meme (is_meme)
) ENGINE=InnoDB;

-- OHLCV Candlestick Data (partitioned)
CREATE TABLE IF NOT EXISTS crypto_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(24, 8) NOT NULL,
    source VARCHAR(50) DEFAULT 'coingecko',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp),
    INDEX idx_timeframe (timeframe)
) ENGINE=InnoDB;

-- Pre-computed Technical Indicators
CREATE TABLE IF NOT EXISTS crypto_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    rsi_14 DECIMAL(8, 4),
    macd DECIMAL(18, 8),
    macd_signal DECIMAL(18, 8),
    ema_9 DECIMAL(18, 8),
    ema_21 DECIMAL(18, 8),
    sma_50 DECIMAL(18, 8),
    sma_200 DECIMAL(18, 8),
    bb_upper DECIMAL(18, 8),
    bb_lower DECIMAL(18, 8),
    atr_14 DECIMAL(18, 8),
    volume_sma_20 DECIMAL(24, 8),
    stochastic_k DECIMAL(8, 4),
    adx_14 DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ind (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp)
) ENGINE=InnoDB;

-- Pattern Recognition Storage
CREATE TABLE IF NOT EXISTS crypto_patterns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    start_timestamp BIGINT NOT NULL,
    end_timestamp BIGINT NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    price_at_detection DECIMAL(18, 8),
    target_price DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    embedding_vector JSON,
    features JSON,
    success_rating DECIMAL(3, 2),
    times_observed INT DEFAULT 1,
    times_successful INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_pattern (symbol, pattern_type),
    INDEX idx_confidence (confidence),
    INDEX idx_timestamp (start_timestamp)
) ENGINE=InnoDB;

-- Trading Signals with Backtest Tracking
CREATE TABLE IF NOT EXISTS crypto_signals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    signal_type ENUM('buy', 'sell', 'strong_buy', 'strong_sell', 'neutral') NOT NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    target_price_1 DECIMAL(18, 8),
    target_price_2 DECIMAL(18, 8),
    target_price_3 DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    position_size DECIMAL(8, 4),
    risk_reward_ratio DECIMAL(5, 2),
    confidence DECIMAL(5, 2),
    timeframe VARCHAR(10) NOT NULL,
    strategy VARCHAR(50),
    indicators_triggered JSON,
    status ENUM('active', 'hit_target_1', 'hit_target_2', 'hit_target_3', 'stopped_out', 'expired') DEFAULT 'active',
    exit_price DECIMAL(18, 8),
    pnl_percent DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_strategy (strategy),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- Meme Coin Special Tracking
CREATE TABLE IF NOT EXISTS meme_coin_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    launch_timestamp BIGINT,
    launch_price DECIMAL(18, 8),
    ath_price DECIMAL(18, 8),
    ath_timestamp BIGINT,
    atl_price DECIMAL(18, 8),
    volatility_30d DECIMAL(8, 4),
    max_daily_gain DECIMAL(8, 4),
    max_daily_loss DECIMAL(8, 4),
    meme_category ENUM('animal', 'political', 'celebrity', 'food', 'other') DEFAULT 'other',
    twitter_followers INT,
    telegram_members INT,
    is_rug_pull BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_category (meme_category),
    INDEX idx_volatility (volatility_30d)
) ENGINE=InnoDB;

-- Market-wide Data
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    total_market_cap DECIMAL(24, 2),
    total_volume_24h DECIMAL(24, 2),
    btc_dominance DECIMAL(5, 2),
    eth_dominance DECIMAL(5, 2),
    fear_greed_index INT,
    altcoin_season_index DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ts (timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB;

-- ML Model Registry
CREATE TABLE IF NOT EXISTS ml_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_type VARCHAR(50),
    asset_class VARCHAR(20),
    training_start DATE,
    training_end DATE,
    accuracy DECIMAL(5, 4),
    precision_score DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),
    features_used JSON,
    hyperparameters JSON,
    model_path VARCHAR(500),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name_ver (model_name, model_version),
    INDEX idx_active (is_active),
    INDEX idx_type (model_type)
) ENGINE=InnoDB;

-- Model Performance Tracking
CREATE TABLE IF NOT EXISTS ml_model_performance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id INT NOT NULL,
    prediction_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    predicted_signal VARCHAR(20),
    actual_outcome VARCHAR(20),
    confidence DECIMAL(5, 4),
    was_correct BOOLEAN,
    pnl_if_followed DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model (model_id),
    INDEX idx_date (prediction_date),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB;
"""


# ============================================
# STOCKS TABLES FOR STOCKS DATABASE
# ============================================
STOCKS_SCHEMA = """
-- Stock Assets
CREATE TABLE IF NOT EXISTS stock_assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    exchange VARCHAR(20),
    sector VARCHAR(50),
    industry VARCHAR(100),
    market_cap_category ENUM('mega', 'large', 'mid', 'small', 'micro', 'nano') DEFAULT 'mid',
    is_penny BOOLEAN DEFAULT FALSE,
    is_etf BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_sector (sector),
    INDEX idx_penny (is_penny)
) ENGINE=InnoDB;

-- Stock OHLCV
CREATE TABLE IF NOT EXISTS stock_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(12, 4) NOT NULL,
    high DECIMAL(12, 4) NOT NULL,
    low DECIMAL(12, 4) NOT NULL,
    close DECIMAL(12, 4) NOT NULL,
    volume BIGINT NOT NULL,
    source VARCHAR(50) DEFAULT 'yahoo',
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp)
) ENGINE=InnoDB;

-- Penny Stock Special Tracking
CREATE TABLE IF NOT EXISTS penny_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    avg_volume_30d BIGINT,
    volatility_30d DECIMAL(8, 4),
    float_shares BIGINT,
    short_interest DECIMAL(8, 4),
    catalyst_news TEXT,
    pump_score INT,
    is_premarket_gainer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_pump (pump_score),
    INDEX idx_volatility (volatility_30d)
) ENGINE=InnoDB;

-- Stock Signals
CREATE TABLE IF NOT EXISTS stock_signals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    signal_type ENUM('buy', 'sell', 'strong_buy', 'strong_sell') NOT NULL,
    entry_price DECIMAL(12, 4) NOT NULL,
    target_price DECIMAL(12, 4),
    stop_loss DECIMAL(12, 4),
    position_size DECIMAL(8, 4),
    risk_reward DECIMAL(5, 2),
    confidence DECIMAL(5, 2),
    strategy VARCHAR(50),
    catalyst TEXT,
    status ENUM('active', 'closed', 'stopped') DEFAULT 'active',
    pnl_percent DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Add crypto tables with 'crypto_' prefix for stocks DB hybrid use
CREATE TABLE IF NOT EXISTS crypto_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(24, 8) NOT NULL,
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS crypto_signals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    signal_id VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    signal_type ENUM('buy', 'sell', 'strong_buy', 'strong_sell') NOT NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    target_price DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    status ENUM('active', 'closed', 'stopped') DEFAULT 'active',
    pnl_percent DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_status (status)
) ENGINE=InnoDB;
"""


# ============================================
# FOREX TABLES FOR FAVCREATORS DATABASE
# ============================================
FOREX_SCHEMA = """
-- Forex Currency Pairs
CREATE TABLE IF NOT EXISTS forex_pairs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    base_currency VARCHAR(5) NOT NULL,
    quote_currency VARCHAR(5) NOT NULL,
    pip_value DECIMAL(10, 8),
    spread_avg DECIMAL(8, 6),
    market_hours VARCHAR(50),
    is_major BOOLEAN DEFAULT FALSE,
    is_exotic BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_major (is_major)
) ENGINE=InnoDB;

-- Forex OHLCV
CREATE TABLE IF NOT EXISTS forex_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(18, 8) NOT NULL,
    high DECIMAL(18, 8) NOT NULL,
    low DECIMAL(18, 8) NOT NULL,
    close DECIMAL(18, 8) NOT NULL,
    volume DECIMAL(18, 4),
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp)
) ENGINE=InnoDB;

-- Economic Calendar Events
CREATE TABLE IF NOT EXISTS economic_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(200) NOT NULL,
    currency VARCHAR(5) NOT NULL,
    impact ENUM('low', 'medium', 'high') DEFAULT 'medium',
    event_timestamp BIGINT NOT NULL,
    actual_value DECIMAL(12, 4),
    forecast_value DECIMAL(12, 4),
    previous_value DECIMAL(12, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_currency (currency),
    INDEX idx_timestamp (event_timestamp),
    INDEX idx_impact (impact)
) ENGINE=InnoDB;
"""


class SchemaManager:
    """Manages schema creation across all databases"""
    
    def __init__(self):
        self.manager = manager
    
    def create_memecoin_schema(self):
        """Create crypto tables in memecoin database"""
        print("Creating schema in ejaguiar1_memecoin...")
        statements = [s.strip() for s in MEMECOIN_CRYPTO_SCHEMA.split(';') if s.strip()]
        
        with self.manager.connection('memecoin') as conn:
            with conn.cursor() as cursor:
                for stmt in statements:
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        print(f"  Warning: {e}")
                conn.commit()
        
        print("[OK] Memecoin schema created")
    
    def create_stocks_schema(self):
        """Create tables in stocks database"""
        print("Creating schema in ejaguiar1_stocks...")
        statements = [s.strip() for s in STOCKS_SCHEMA.split(';') if s.strip()]
        
        with self.manager.connection('stocks') as conn:
            with conn.cursor() as cursor:
                for stmt in statements:
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        print(f"  Warning: {e}")
                conn.commit()
        
        print("[OK] Stocks schema created")
    
    def create_forex_schema(self):
        """Create forex tables in favcreators database"""
        print("Creating schema in ejaguiar1_favcreators...")
        statements = [s.strip() for s in FOREX_SCHEMA.split(';') if s.strip()]
        
        with self.manager.connection('favcreators') as conn:
            with conn.cursor() as cursor:
                for stmt in statements:
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        print(f"  Warning: {e}")
                conn.commit()
        
        print("[OK] Forex schema created")
    
    def seed_initial_data(self):
        """Seed initial crypto and stock data"""
        
        # Seed crypto assets
        crypto_assets = [
            ('BTC', 'Bitcoin', 'major', 'mega', False),
            ('ETH', 'Ethereum', 'major', 'mega', False),
            ('BNB', 'Binance Coin', 'major', 'large', False),
            ('SOL', 'Solana', 'major', 'large', False),
            ('XRP', 'Ripple', 'major', 'large', False),
            ('ADA', 'Cardano', 'major', 'mid', False),
            ('AVAX', 'Avalanche', 'major', 'mid', False),
            ('DOT', 'Polkadot', 'major', 'mid', False),
            ('DOGE', 'Dogecoin', 'meme', 'large', True),
            ('SHIB', 'Shiba Inu', 'meme', 'mid', True),
            ('PEPE', 'Pepe', 'meme', 'mid', True),
            ('FLOKI', 'Floki', 'meme', 'small', True),
            ('BONK', 'Bonk', 'meme', 'mid', True),
            ('WIF', 'Dogwifhat', 'meme', 'mid', True),
        ]
        
        sql = """
            INSERT INTO crypto_assets (symbol, name, asset_type, market_cap_category, is_meme)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            name=VALUES(name), asset_type=VALUES(asset_type)
        """
        
        with self.manager.connection('memecoin') as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, crypto_assets)
                conn.commit()
        
        print(f"[OK] Seeded {len(crypto_assets)} crypto assets")
        
        # Seed meme coin stats for meme coins
        meme_stats = [
            ('DOGE', 'animal'),
            ('SHIB', 'animal'),
            ('PEPE', 'animal'),
            ('FLOKI', 'animal'),
            ('BONK', 'animal'),
            ('WIF', 'animal'),
        ]
        
        sql_meme = """
            INSERT INTO meme_coin_stats (symbol, meme_category)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE meme_category=VALUES(meme_category)
        """
        
        with self.manager.connection('memecoin') as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql_meme, meme_stats)
                conn.commit()
        
        print(f"[OK] Seeded {len(meme_stats)} meme coin stats")


if __name__ == '__main__':
    print("Schema Extension Manager")
    print("=" * 50)
    
    # Test connections
    results = manager.test_all_connections()
    
    if all(results.values()):
        schema_mgr = SchemaManager()
        
        print("\nCreating schemas...")
        schema_mgr.create_memecoin_schema()
        schema_mgr.create_stocks_schema()
        schema_mgr.create_forex_schema()
        
        print("\nSeeding initial data...")
        schema_mgr.seed_initial_data()
        
        print("\n[STATUS] Final Database Status:")
        for db_name in manager.databases:
            tables = manager.list_tables(db_name)
            print(f"\n{db_name}: {len(tables)} tables")
            for table in tables[:10]:  # Show first 10
                count = manager.get_table_counts(db_name).get(table, 0)
                print(f"  - {table}: {count:,} rows")
            if len(tables) > 10:
                print(f"  ... and {len(tables)-10} more tables")
    else:
        print("\n[FAIL] Some databases failed to connect. Please check credentials.")
