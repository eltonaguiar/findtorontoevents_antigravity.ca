-- TimescaleDB Schema for Live Trading System

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =====================================================
-- MARKET DATA TABLES
-- =====================================================

-- Raw tick data hypertable
CREATE TABLE market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    size DECIMAL(18, 8) NOT NULL,
    exchange TEXT NOT NULL,
    side TEXT CHECK (side IN ('buy', 'sell', NULL)),
    PRIMARY KEY (time, symbol, exchange)
);

-- Convert to hypertable with 1-hour chunks
SELECT create_hypertable('market_ticks', 'time', chunk_time_interval => INTERVAL '1 hour');

-- Create indexes for common queries
CREATE INDEX idx_market_ticks_symbol ON market_ticks (symbol, time DESC);
CREATE INDEX idx_market_ticks_exchange ON market_ticks (exchange, time DESC);

-- Order book snapshots
CREATE TABLE order_book_snapshots (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    bid_price DECIMAL(18, 8) NOT NULL,
    bid_size DECIMAL(18, 8) NOT NULL,
    ask_price DECIMAL(18, 8) NOT NULL,
    ask_size DECIMAL(18, 8) NOT NULL,
    PRIMARY KEY (time, symbol, exchange)
);

SELECT create_hypertable('order_book_snapshots', 'time', chunk_time_interval => INTERVAL '1 hour');

-- =====================================================
-- TRADING TABLES
-- =====================================================

-- Orders table
CREATE TABLE orders (
    time TIMESTAMPTZ NOT NULL,
    order_id TEXT PRIMARY KEY,
    signal_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type TEXT NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    stop_price DECIMAL(18, 8),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SUBMITTED', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED')),
    filled_quantity DECIMAL(18, 8) DEFAULT 0,
    avg_fill_price DECIMAL(18, 8),
    exchange TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('orders', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_orders_symbol ON orders (symbol, time DESC);
CREATE INDEX idx_orders_signal ON orders (signal_id);
CREATE INDEX idx_orders_status ON orders (status);

-- Fills table
CREATE TABLE fills (
    time TIMESTAMPTZ NOT NULL,
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    symbol TEXT NOT NULL,
    filled_quantity DECIMAL(18, 8) NOT NULL,
    filled_price DECIMAL(18, 8) NOT NULL,
    fee DECIMAL(18, 8) NOT NULL DEFAULT 0,
    fee_currency TEXT,
    exchange TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('fills', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_fills_order ON fills (order_id);
CREATE INDEX idx_fills_symbol ON fills (symbol, time DESC);

-- =====================================================
-- POSITION TABLES
-- =====================================================

-- Current positions (regular table, not hypertable)
CREATE TABLE positions (
    symbol TEXT PRIMARY KEY,
    quantity DECIMAL(18, 8) NOT NULL DEFAULT 0,
    avg_entry_price DECIMAL(18, 8),
    unrealized_pnl DECIMAL(18, 8) DEFAULT 0,
    realized_pnl DECIMAL(18, 8) DEFAULT 0,
    total_fees DECIMAL(18, 8) DEFAULT 0,
    last_trade_time TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_positions_quantity ON positions (quantity) WHERE quantity != 0;

-- Position history (hypertable for time-series analysis)
CREATE TABLE position_history (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    avg_entry_price DECIMAL(18, 8),
    unrealized_pnl DECIMAL(18, 8),
    realized_pnl DECIMAL(18, 8),
    market_price DECIMAL(18, 8),
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('position_history', 'time', chunk_time_interval => INTERVAL '1 hour');

CREATE INDEX idx_position_history_symbol ON position_history (symbol, time DESC);

-- =====================================================
-- P&L TABLES
-- =====================================================

-- P&L snapshots (hypertable)
CREATE TABLE pnl_snapshots (
    time TIMESTAMPTZ NOT NULL,
    total_realized_pnl DECIMAL(18, 2) NOT NULL,
    total_unrealized_pnl DECIMAL(18, 2) NOT NULL,
    total_fees DECIMAL(18, 2) NOT NULL,
    gross_pnl DECIMAL(18, 2) NOT NULL,
    net_pnl DECIMAL(18, 2) NOT NULL,
    portfolio_value DECIMAL(18, 2) NOT NULL,
    cash_balance DECIMAL(18, 2) NOT NULL,
    margin_used DECIMAL(18, 2) DEFAULT 0
);

SELECT create_hypertable('pnl_snapshots', 'time', chunk_time_interval => INTERVAL '1 hour');

-- Trade statistics
CREATE TABLE trade_statistics (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2),
    avg_win DECIMAL(18, 2),
    avg_loss DECIMAL(18, 2),
    profit_factor DECIMAL(10, 2),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    max_drawdown_amount DECIMAL(18, 2)
);

SELECT create_hypertable('trade_statistics', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_trade_stats_symbol ON trade_statistics (symbol, time DESC);

-- =====================================================
-- SIGNAL TABLES
-- =====================================================

-- Generated signals
CREATE TABLE signals (
    time TIMESTAMPTZ NOT NULL,
    signal_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('ENTRY_LONG', 'ENTRY_SHORT', 'EXIT_LONG', 'EXIT_SHORT', 'HOLD')),
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    strategy TEXT NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    execution_time TIMESTAMPTZ,
    metadata JSONB
);

SELECT create_hypertable('signals', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_signals_symbol ON signals (symbol, time DESC);
CREATE INDEX idx_signals_strategy ON signals (strategy, time DESC);
CREATE INDEX idx_signals_executed ON signals (executed) WHERE executed = FALSE;

-- =====================================================
-- AUDIT AND LOGGING TABLES
-- =====================================================

-- System events
CREATE TABLE system_events (
    time TIMESTAMPTZ NOT NULL,
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    acknowledged BOOLEAN DEFAULT FALSE
);

SELECT create_hypertable('system_events', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_system_events_type ON system_events (event_type, time DESC);
CREATE INDEX idx_system_events_severity ON system_events (severity, time DESC) WHERE severity IN ('ERROR', 'CRITICAL');

-- Risk events
CREATE TABLE risk_events (
    time TIMESTAMPTZ NOT NULL,
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    symbol TEXT,
    order_id TEXT,
    reason TEXT NOT NULL,
    details JSONB
);

SELECT create_hypertable('risk_events', 'time', chunk_time_interval => INTERVAL '1 day');

-- =====================================================
-- CONFIGURATION TABLES
-- =====================================================

-- Trading configuration (regular table)
CREATE TABLE trading_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- Strategy configuration
CREATE TABLE strategy_config (
    strategy_name TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    symbols TEXT[] NOT NULL,
    parameters JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Risk limits configuration
CREATE TABLE risk_limits_config (
    id SERIAL PRIMARY KEY,
    max_position_value DECIMAL(18, 2) NOT NULL,
    max_position_pct DECIMAL(5, 4) NOT NULL,
    max_daily_loss DECIMAL(18, 2) NOT NULL,
    max_order_size DECIMAL(18, 8) NOT NULL,
    max_slippage_bps INTEGER NOT NULL,
    portfolio_drawdown_pct DECIMAL(5, 2) NOT NULL,
    single_position_loss_pct DECIMAL(5, 2) NOT NULL,
    data_feed_timeout_ms INTEGER NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

-- =====================================================
-- VIEWS
-- =====================================================

-- Current positions view
CREATE VIEW v_current_positions AS
SELECT 
    symbol,
    quantity,
    avg_entry_price,
    unrealized_pnl,
    realized_pnl,
    total_fees,
    last_trade_time,
    last_updated,
    CASE 
        WHEN quantity > 0 THEN 'LONG'
        WHEN quantity < 0 THEN 'SHORT'
        ELSE 'FLAT'
    END as position_side
FROM positions
WHERE quantity != 0;

-- Daily P&L view
CREATE VIEW v_daily_pnl AS
SELECT 
    time_bucket('1 day', time) as date,
    SUM(realized_pnl) as daily_realized_pnl,
    SUM(fee) as daily_fees,
    SUM(realized_pnl - fee) as daily_net_pnl,
    COUNT(*) as num_trades
FROM fills
GROUP BY time_bucket('1 day', time)
ORDER BY date DESC;

-- Open orders view
CREATE VIEW v_open_orders AS
SELECT 
    order_id,
    signal_id,
    symbol,
    side,
    order_type,
    quantity,
    price,
    filled_quantity,
    quantity - filled_quantity as remaining_quantity,
    status,
    time as created_at
FROM orders
WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIAL');

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Function to update position on fill
CREATE OR REPLACE FUNCTION update_position_on_fill()
RETURNS TRIGGER AS $$
DECLARE
    v_position positions%ROWTYPE;
    v_side TEXT;
    v_realized_pnl DECIMAL(18, 8) := 0;
BEGIN
    -- Get order side
    SELECT side INTO v_side FROM orders WHERE order_id = NEW.order_id;
    
    -- Get or create position
    SELECT * INTO v_position FROM positions WHERE symbol = NEW.symbol;
    
    IF NOT FOUND THEN
        INSERT INTO positions (symbol, quantity, avg_entry_price, realized_pnl)
        VALUES (
            NEW.symbol,
            CASE WHEN v_side = 'BUY' THEN NEW.filled_quantity ELSE -NEW.filled_quantity END,
            NEW.filled_price,
            0
        );
    ELSE
        -- Calculate realized P&L for closing trades
        IF v_position.quantity > 0 AND v_side = 'SELL' THEN
            v_realized_pnl := (NEW.filled_price - v_position.avg_entry_price) * 
                             LEAST(NEW.filled_quantity, v_position.quantity);
        ELSIF v_position.quantity < 0 AND v_side = 'BUY' THEN
            v_realized_pnl := (v_position.avg_entry_price - NEW.filled_price) * 
                             LEAST(NEW.filled_quantity, ABS(v_position.quantity));
        END IF;
        
        -- Update position
        UPDATE positions SET
            quantity = quantity + CASE WHEN v_side = 'BUY' THEN NEW.filled_quantity ELSE -NEW.filled_quantity END,
            avg_entry_price = CASE 
                WHEN quantity + CASE WHEN v_side = 'BUY' THEN NEW.filled_quantity ELSE -NEW.filled_quantity END = 0 THEN NULL
                WHEN (quantity > 0 AND v_side = 'BUY') OR (quantity < 0 AND v_side = 'SELL') THEN
                    (COALESCE(avg_entry_price * ABS(quantity), 0) + NEW.filled_price * NEW.filled_quantity) / 
                    (ABS(quantity) + NEW.filled_quantity)
                ELSE avg_entry_price
            END,
            realized_pnl = realized_pnl + v_realized_pnl,
            total_fees = total_fees + NEW.fee,
            last_trade_time = NEW.time,
            last_updated = NOW()
        WHERE symbol = NEW.symbol;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for position updates
CREATE TRIGGER trigger_update_position_on_fill
    AFTER INSERT ON fills
    FOR EACH ROW
    EXECUTE FUNCTION update_position_on_fill();

-- Function to record position history
CREATE OR REPLACE FUNCTION record_position_history()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO position_history (time, symbol, quantity, avg_entry_price, unrealized_pnl, realized_pnl)
    VALUES (NOW(), NEW.symbol, NEW.quantity, NEW.avg_entry_price, NEW.unrealized_pnl, NEW.realized_pnl);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for position history
CREATE TRIGGER trigger_record_position_history
    AFTER UPDATE ON positions
    FOR EACH ROW
    WHEN (OLD.quantity IS DISTINCT FROM NEW.quantity OR 
          OLD.unrealized_pnl IS DISTINCT FROM NEW.unrealized_pnl)
    EXECUTE FUNCTION record_position_history();

-- =====================================================
-- RETENTION POLICIES
-- =====================================================

-- Add retention policies for old data
SELECT add_retention_policy('market_ticks', INTERVAL '30 days');
SELECT add_retention_policy('order_book_snapshots', INTERVAL '7 days');
SELECT add_retention_policy('position_history', INTERVAL '90 days');
SELECT add_retention_policy('system_events', INTERVAL '30 days');

-- =====================================================
-- CONTINUOUS AGGREGATES
-- =====================================================

-- 1-minute OHLCV aggregates
CREATE MATERIALIZED VIEW market_ohlcv_1m
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 minute', time) as bucket,
    symbol,
    exchange,
    FIRST(price, time) as open,
    MAX(price) as high,
    MIN(price) as low,
    LAST(price, time) as close,
    SUM(size) as volume,
    COUNT(*) as num_trades
FROM market_ticks
GROUP BY bucket, symbol, exchange;

-- Create refresh policy for 1m aggregates
SELECT add_continuous_aggregate_policy('market_ohlcv_1m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);

-- 5-minute OHLCV aggregates
CREATE MATERIALIZED VIEW market_ohlcv_5m
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', time) as bucket,
    symbol,
    exchange,
    FIRST(price, time) as open,
    MAX(price) as high,
    MIN(price) as low,
    LAST(price, time) as close,
    SUM(size) as volume,
    COUNT(*) as num_trades
FROM market_ticks
GROUP BY bucket, symbol, exchange;

SELECT add_continuous_aggregate_policy('market_ohlcv_5m',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes'
);

-- 1-hour OHLCV aggregates
CREATE MATERIALIZED VIEW market_ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) as bucket,
    symbol,
    exchange,
    FIRST(price, time) as open,
    MAX(price) as high,
    MIN(price) as low,
    LAST(price, time) as close,
    SUM(size) as volume,
    COUNT(*) as num_trades
FROM market_ticks
GROUP BY bucket, symbol, exchange;

SELECT add_continuous_aggregate_policy('market_ohlcv_1h',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
