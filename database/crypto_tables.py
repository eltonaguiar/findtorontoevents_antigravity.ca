#!/usr/bin/env python3
"""
================================================================================
CRYPTO & MEME COIN DATABASE SCHEMA
================================================================================

Tables for cryptocurrency and meme coin data storage:
- crypto_ohlcv: OHLCV candlestick data (partitioned by month)
- crypto_assets: Asset metadata and classification
- crypto_patterns: Detected patterns with embeddings
- crypto_signals: Trading signals with backtesting results
- crypto_market_data: Market cap, volume, dominance metrics
- meme_coins: Special tracking for high-volatility meme coins

Optimized for:
- Fast time-series queries (indexed timestamp, symbol)
- Pattern matching (embedding vectors stored as JSON)
- Real-time signal generation (low-latency reads)
================================================================================
"""

from typing import List, Dict, Optional
from datetime import datetime
import json


# SQL Schema for Crypto Tables
CRYPTO_SCHEMA_SQL = """
-- =============================================
-- CRYPTO ASSETS METADATA TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS crypto_assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset_type ENUM('major', 'altcoin', 'meme', 'defi', 'nft', 'layer2') DEFAULT 'altcoin',
    market_cap_category ENUM('large', 'mid', 'small', 'micro', 'nano') DEFAULT 'mid',
    is_meme BOOLEAN DEFAULT FALSE,
    is_penny BOOLEAN DEFAULT FALSE,
    blockchain VARCHAR(50),
    contract_address VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata JSON,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_asset_type (asset_type),
    INDEX idx_meme (is_meme),
    INDEX idx_market_cap (market_cap_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- OHLCV CANDLESTICK DATA (Time-Series)
-- =============================================
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
    quote_volume DECIMAL(24, 8),
    trades_count INT,
    source VARCHAR(50) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp),
    INDEX idx_timeframe (timeframe),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (timestamp) (
    PARTITION p2024 VALUES LESS THAN (1735689600),
    PARTITION p2025 VALUES LESS THAN (1767225600),
    PARTITION p2026 VALUES LESS THAN (1798761600),
    PARTITION pfuture VALUES LESS THAN MAXVALUE
);

-- =============================================
-- TECHNICAL INDICATORS (Pre-computed)
-- =============================================
CREATE TABLE IF NOT EXISTS crypto_indicators (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp BIGINT NOT NULL,
    rsi_14 DECIMAL(8, 4),
    macd DECIMAL(18, 8),
    macd_signal DECIMAL(18, 8),
    macd_histogram DECIMAL(18, 8),
    ema_9 DECIMAL(18, 8),
    ema_21 DECIMAL(18, 8),
    sma_50 DECIMAL(18, 8),
    sma_200 DECIMAL(18, 8),
    bb_upper DECIMAL(18, 8),
    bb_middle DECIMAL(18, 8),
    bb_lower DECIMAL(18, 8),
    atr_14 DECIMAL(18, 8),
    volume_sma_20 DECIMAL(24, 8),
    stochastic_k DECIMAL(8, 4),
    stochastic_d DECIMAL(8, 4),
    cci_20 DECIMAL(12, 4),
    williams_r DECIMAL(8, 4),
    adx_14 DECIMAL(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_indicators (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- PATTERN RECOGNITION STORAGE
-- =============================================
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
    -- Embedding vector for similarity search (stored as JSON array)
    embedding_vector JSON,
    -- Pattern features for ML
    features JSON,
    -- Success tracking for pattern validation
    success_rating DECIMAL(3, 2),
    times_observed INT DEFAULT 1,
    times_successful INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_pattern (symbol, pattern_type),
    INDEX idx_pattern_name (pattern_name),
    INDEX idx_timeframe (timeframe),
    INDEX idx_confidence (confidence),
    INDEX idx_timestamp (start_timestamp),
    FULLTEXT INDEX idx_pattern_ft (pattern_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- TRADING SIGNALS (With Backtest Results)
-- =============================================
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
    -- Signal lifecycle
    status ENUM('active', 'hit_target_1', 'hit_target_2', 'hit_target_3', 'stopped_out', 'expired') DEFAULT 'active',
    exit_price DECIMAL(18, 8),
    exit_timestamp BIGINT,
    pnl_percent DECIMAL(8, 4),
    pnl_absolute DECIMAL(18, 8),
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_status (status),
    INDEX idx_signal_type (signal_type),
    INDEX idx_created (created_at),
    INDEX idx_strategy (strategy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- MEME COIN SPECIAL TRACKING
-- =============================================
CREATE TABLE IF NOT EXISTS meme_coins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    launch_timestamp BIGINT,
    launch_price DECIMAL(18, 8),
    ath_price DECIMAL(18, 8),
    ath_timestamp BIGINT,
    atl_price DECIMAL(18, 8),
    atl_timestamp BIGINT,
    -- Social metrics
    twitter_followers INT,
    telegram_members INT,
    reddit_subscribers INT,
    -- Risk metrics
    volatility_30d DECIMAL(8, 4),
    max_daily_gain DECIMAL(8, 4),
    max_daily_loss DECIMAL(8, 4),
    -- Classification
    meme_category ENUM('animal', 'political', 'celebrity', 'food', 'other') DEFAULT 'other',
    -- Safety
    is_rug_pull BOOLEAN DEFAULT FALSE,
    is_honeypot BOOLEAN DEFAULT FALSE,
    audit_score INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_meme_category (meme_category),
    INDEX idx_launch_date (launch_timestamp),
    INDEX idx_volatility (volatility_30d)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- MARKET DATA (Global metrics)
-- =============================================
CREATE TABLE IF NOT EXISTS crypto_market_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    total_market_cap DECIMAL(24, 2),
    total_volume_24h DECIMAL(24, 2),
    btc_dominance DECIMAL(5, 2),
    eth_dominance DECIMAL(5, 2),
    fear_greed_index INT,
    fear_greed_classification VARCHAR(20),
    altcoin_season_index DECIMAL(5, 2),
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_timestamp (timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- CORRELATION MATRIX (Asset relationships)
-- =============================================
CREATE TABLE IF NOT EXISTS crypto_correlations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol_1 VARCHAR(20) NOT NULL,
    symbol_2 VARCHAR(20) NOT NULL,
    correlation_30d DECIMAL(5, 4),
    correlation_90d DECIMAL(5, 4),
    correlation_1y DECIMAL(5, 4),
    beta DECIMAL(6, 4),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pair (symbol_1, symbol_2),
    INDEX idx_symbol1 (symbol_1),
    INDEX idx_symbol2 (symbol_2),
    INDEX idx_correlation (correlation_30d)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- NEWS & SENTIMENT
-- =============================================
CREATE TABLE IF NOT EXISTS crypto_news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    url VARCHAR(500),
    content TEXT,
    symbols TEXT,
    sentiment_score DECIMAL(5, 4),
    sentiment_label ENUM('very_positive', 'positive', 'neutral', 'negative', 'very_negative'),
    published_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbols (symbols(100)),
    INDEX idx_sentiment (sentiment_score),
    INDEX idx_published (published_at),
    FULLTEXT INDEX idx_title_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


class CryptoSchema:
    """
    Crypto Database Schema Manager
    Handles creation and migration of crypto-related tables
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_all_tables(self):
        """Create all crypto tables"""
        print("Creating crypto database schema...")
        self.db.create_tables(CRYPTO_SCHEMA_SQL)
        print("[OK] Crypto tables created successfully")
    
    def seed_default_assets(self):
        """Seed database with default crypto assets"""
        assets = [
            # Major cryptocurrencies
            ('BTC', 'Bitcoin', 'major', 'large', False),
            ('ETH', 'Ethereum', 'major', 'large', False),
            ('BNB', 'Binance Coin', 'major', 'large', False),
            ('SOL', 'Solana', 'major', 'large', False),
            ('XRP', 'Ripple', 'major', 'large', False),
            ('ADA', 'Cardano', 'major', 'large', False),
            ('AVAX', 'Avalanche', 'major', 'mid', False),
            ('DOT', 'Polkadot', 'major', 'mid', False),
            
            # Meme coins
            ('DOGE', 'Dogecoin', 'meme', 'large', True),
            ('SHIB', 'Shiba Inu', 'meme', 'mid', True),
            ('PEPE', 'Pepe', 'meme', 'mid', True),
            ('FLOKI', 'Floki', 'meme', 'small', True),
            ('BONK', 'Bonk', 'meme', 'mid', True),
            ('WIF', 'Dogwifhat', 'meme', 'mid', True),
            ('BOME', 'Book of Meme', 'meme', 'small', True),
            ('POPCAT', 'Popcat', 'meme', 'small', True),
            ('MOG', 'Mog Coin', 'meme', 'micro', True),
            ('SPX', 'SPX6900', 'meme', 'micro', True),
        ]
        
        sql = """
            INSERT INTO crypto_assets 
            (symbol, name, asset_type, market_cap_category, is_meme) 
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            name=VALUES(name), asset_type=VALUES(asset_type), 
            market_cap_category=VALUES(market_cap_category), is_meme=VALUES(is_meme)
        """
        
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, assets)
                conn.commit()
        
        print(f"[OK] Seeded {len(assets)} crypto assets")
    
    def get_table_sizes(self) -> Dict[str, int]:
        """Get row counts for all crypto tables"""
        tables = [
            'crypto_assets', 'crypto_ohlcv', 'crypto_indicators',
            'crypto_patterns', 'crypto_signals', 'meme_coins',
            'crypto_market_data', 'crypto_correlations', 'crypto_news'
        ]
        
        sizes = {}
        for table in tables:
            try:
                result = self.db.execute(f"SELECT COUNT(*) as count FROM {table}")
                sizes[table] = result[0]['count'] if result else 0
            except Exception as e:
                sizes[table] = -1  # Table doesn't exist
        
        return sizes


if __name__ == '__main__':
    from mysql_core import MySQLDatabase
    
    # Test schema creation
    db = MySQLDatabase()
    schema = CryptoSchema(db)
    
    if db.test_connection():
        schema.create_all_tables()
        schema.seed_default_assets()
        
        print("\nTable sizes:")
        for table, count in schema.get_table_sizes().items():
            print(f"  {table}: {count:,} rows")
