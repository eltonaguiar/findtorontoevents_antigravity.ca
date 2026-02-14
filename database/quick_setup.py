#!/usr/bin/env python3
"""
================================================================================
QUICK DATABASE SETUP - Crypto Tables Only
================================================================================
"""

import sys
import pymysql

# Database configs
DB_CONFIGS = {
    'memecoin': {
        'host': 'mysql.50webs.com',
        'user': 'ejaguiar1_memecoin',
        'password': os.environ.get('MEMECOIN_DB_PASS', ''),
        'database': 'ejaguiar1_memecoin',
        'port': 3306
    },
    'stocks': {
        'host': 'mysql.50webs.com',
        'user': 'ejaguiar1_stocks',
        'password': os.environ.get('STOCKS_DB_PASS', ''),
        'database': 'ejaguiar1_stocks',
        'port': 3306
    }
}

# Essential crypto tables to create
CRYPTO_TABLES_SQL = """
-- Crypto Assets Master List
CREATE TABLE IF NOT EXISTS crypto_assets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    asset_type ENUM('major', 'altcoin', 'meme', 'defi', 'nft', 'layer2') DEFAULT 'altcoin',
    market_cap_category ENUM('mega', 'large', 'mid', 'small', 'micro', 'nano') DEFAULT 'mid',
    is_meme BOOLEAN DEFAULT FALSE,
    blockchain VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_symbol (symbol),
    INDEX idx_type (asset_type),
    INDEX idx_meme (is_meme)
) ENGINE=InnoDB;

-- OHLCV Candlestick Data
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
    source VARCHAR(50) DEFAULT 'api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ohlcv (symbol, timeframe, timestamp),
    INDEX idx_symbol_time (symbol, timestamp),
    INDEX idx_timeframe (timeframe)
) ENGINE=InnoDB;

-- Trading Signals
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
    INDEX idx_strategy (strategy)
) ENGINE=InnoDB;

-- Pattern Recognition
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_pattern (symbol, pattern_type),
    INDEX idx_confidence (confidence)
) ENGINE=InnoDB;

-- Technical Indicators
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
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name_ver (model_name, model_version),
    INDEX idx_active (is_active)
) ENGINE=InnoDB;

-- ML Model Performance
CREATE TABLE IF NOT EXISTS ml_model_performance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id INT NOT NULL,
    prediction_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    predicted_signal VARCHAR(20),
    actual_outcome VARCHAR(20),
    confidence DECIMAL(5, 4),
    was_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_model (model_id),
    INDEX idx_date (prediction_date)
) ENGINE=InnoDB;
"""


def test_connection(config):
    """Test database connection"""
    try:
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION() as version")
        version = cursor.fetchone()['version']
        conn.close()
        return True, version
    except Exception as e:
        return False, str(e)


def create_tables(config):
    """Create crypto tables"""
    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        port=config['port'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    statements = [s.strip() for s in CRYPTO_TABLES_SQL.split(';') if s.strip()]
    
    created = []
    errors = []
    
    for stmt in statements:
        try:
            cursor.execute(stmt)
            # Extract table name from CREATE TABLE statement
            if 'CREATE TABLE' in stmt:
                table_name = stmt.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                created.append(table_name)
        except Exception as e:
            errors.append(str(e))
    
    conn.commit()
    conn.close()
    return created, errors


def seed_assets(config):
    """Seed crypto assets"""
    assets = [
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
    
    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        port=config['port'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    sql = """
        INSERT INTO crypto_assets (symbol, name, asset_type, market_cap_category, is_meme)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name=VALUES(name)
    """
    cursor.executemany(sql, assets)
    conn.commit()
    conn.close()
    return len(assets)


def main():
    print("=" * 60)
    print("CRYPTO DATABASE INFRASTRUCTURE SETUP")
    print("=" * 60)
    
    for db_name, config in DB_CONFIGS.items():
        print(f"\n[DB] {db_name}")
        print("-" * 40)
        
        # Test connection
        ok, msg = test_connection(config)
        if ok:
            print(f"  Connection: OK (MySQL {msg})")
        else:
            print(f"  Connection: FAILED - {msg}")
            continue
        
        # Create tables
        print("  Creating tables...")
        created, errors = create_tables(config)
        print(f"  Tables created: {len(created)}")
        if errors:
            print(f"  Warnings: {len(errors)} (tables may already exist)")
        
        # Seed assets
        print("  Seeding assets...")
        count = seed_assets(config)
        print(f"  Assets seeded: {count}")
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("\nNew tables available:")
    print("  - crypto_assets")
    print("  - crypto_ohlcv")
    print("  - crypto_signals")
    print("  - crypto_patterns")
    print("  - crypto_indicators")
    print("  - ml_models")
    print("  - ml_model_performance")


if __name__ == '__main__':
    main()
