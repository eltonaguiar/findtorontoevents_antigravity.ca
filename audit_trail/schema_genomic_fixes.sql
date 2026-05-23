-- Genomic & FreshPicks Audit Trail Schema Fixes
-- Version: 1.1
-- Date: March 9, 2026
-- Purpose: Add cross-verification support for genomic systems

-- =============================================================================
-- 1. Add strategy formula tracking to consensus_picks
-- =============================================================================

ALTER TABLE consensus_picks ADD COLUMN strategy_formula TEXT;
ALTER TABLE consensus_picks ADD COLUMN strategy_params TEXT;  -- JSON: fitness, WR, Sharpe from backtest
ALTER TABLE consensus_picks ADD COLUMN evolved_strategy_id TEXT;  -- Link to genomic systems
ALTER TABLE consensus_picks ADD COLUMN precomputed_fitness REAL;
ALTER TABLE consensus_picks ADD COLUMN precomputed_win_rate REAL;
ALTER TABLE consensus_picks ADD COLUMN validation_status TEXT DEFAULT 'PENDING';  -- VALIDATED, DEGRADED, INSUFFICIENT

CREATE INDEX IF NOT EXISTS idx_cons_evolved ON consensus_picks(evolved_strategy_id);
CREATE INDEX IF NOT EXISTS idx_cons_validation ON consensus_picks(validation_status);

-- =============================================================================
-- 2. Create forward test validation table
-- =============================================================================

CREATE TABLE IF NOT EXISTS forward_test_validation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    strategy_type TEXT NOT NULL,  -- 'gp', 'mape', 'ensemble', 'freshpicks'
    source_database TEXT NOT NULL,  -- 'genetic_programmer', 'mape_evolver', etc.
    
    -- Backtest metrics (pre-computed)
    backtest_fitness REAL,
    backtest_win_rate REAL,
    backtest_sharpe REAL,
    backtest_profit_factor REAL,
    backtest_max_drawdown REAL,
    backtest_trades INTEGER,
    
    -- Live metrics (forward test)
    live_win_rate REAL,
    live_sharpe REAL,
    live_profit_factor REAL,
    live_max_drawdown REAL,
    live_trades INTEGER,
    live_total_return REAL,
    
    -- Validation analysis
    win_rate_delta REAL GENERATED ALWAYS (live_win_rate - backtest_win_rate) STORED,
    fitness_delta REAL GENERATED ALWAYS (live_sharpe - backtest_sharpe) STORED,
    sample_size INTEGER DEFAULT 0,
    validation_status TEXT DEFAULT 'INSUFFICIENT_DATA',  -- VALIDATED, DEGRADED, INSUFFICIENT_DATA
    
    -- Metadata
    started_at TEXT NOT NULL,
    last_updated TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ftv_strategy ON forward_test_validation(strategy_id);
CREATE INDEX IF NOT EXISTS idx_ftv_status ON forward_test_validation(validation_status);
CREATE INDEX IF NOT EXISTS idx_ftv_type ON forward_test_validation(strategy_type);

-- =============================================================================
-- 3. Create unified strategy registry (cross-database linkage)
-- =============================================================================

CREATE TABLE IF NOT EXISTS unified_strategy_registry (
    strategy_id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT NOT NULL,  -- 'gp', 'mape', 'ensemble', 'freshpicks', 'manual'
    
    -- Source location
    source_database TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_id TEXT NOT NULL,  -- Original ID in source database
    
    -- Strategy formula/details
    buy_formula TEXT,
    sell_formula TEXT,
    parameters TEXT,  -- JSON of all parameters
    
    -- Pre-computed performance
    backtest_fitness REAL,
    backtest_win_rate REAL,
    backtest_sharpe REAL,
    backtest_max_drawdown REAL,
    
    -- Live performance (aggregated from positions)
    live_trades INTEGER DEFAULT 0,
    live_wins INTEGER DEFAULT 0,
    live_losses INTEGER DEFAULT 0,
    live_win_rate REAL DEFAULT 0.0,
    live_avg_pnl REAL DEFAULT 0.0,
    live_total_pnl REAL DEFAULT 0.0,
    
    -- Status
    is_active BOOLEAN DEFAULT 1,
    promotion_status TEXT DEFAULT 'TESTING',  -- TESTING, PRODUCTION, RETIRED
    created_at TEXT NOT NULL,
    last_trade_at TEXT,
    
    UNIQUE(source_database, source_table, source_id)
);

CREATE INDEX IF NOT EXISTS idx_usr_type ON unified_strategy_registry(strategy_type);
CREATE INDEX IF NOT EXISTS idx_usr_active ON unified_strategy_registry(is_active);
CREATE INDEX IF NOT EXISTS idx_usr_promotion ON unified_strategy_registry(promotion_status);

-- =============================================================================
-- 4. Create FreshPicks state snapshot table
-- =============================================================================

CREATE TABLE IF NOT EXISTS freshpicks_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pick_id TEXT NOT NULL,
    tracking_id TEXT NOT NULL,
    
    -- Entry-time state (critical for verification)
    symbol TEXT NOT NULL,
    entry_price REAL NOT NULL,
    direction TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    
    -- Funding rate data
    funding_rate_8h REAL NOT NULL,
    funding_rate_annualized REAL NOT NULL,
    funding_rate_timestamp TEXT,
    
    -- Technical indicators at entry
    price REAL,
    ema_20 REAL,
    ema_50 REAL,
    trend_4h TEXT,  -- 'bullish', 'bearish', 'neutral'
    volume_24h REAL,
    volume_avg_20d REAL,
    volume_ratio REAL,
    atr_14 REAL,
    
    -- Signal criteria
    funding_threshold_met BOOLEAN,
    volume_threshold_met BOOLEAN,
    trend_aligned BOOLEAN,
    confidence_score REAL,
    
    -- Results (populated on close)
    exit_price REAL,
    exit_time TEXT,
    pnl_pct REAL,
    status TEXT DEFAULT 'OPEN',  -- OPEN, CLOSED, EXPIRED
    
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fps_pick ON freshpicks_snapshots(pick_id);
CREATE INDEX IF NOT EXISTS idx_fps_tracking ON freshpicks_snapshots(tracking_id);
CREATE INDEX IF NOT EXISTS idx_fps_symbol ON freshpicks_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_fps_status ON freshpicks_snapshots(status);

-- =============================================================================
-- 5. Create position-genomic linkage table
-- =============================================================================

-- This links paper_trading positions to genomic strategies
CREATE TABLE IF NOT EXISTS position_strategy_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id TEXT NOT NULL,  -- from paper.db positions
    strategy_id TEXT NOT NULL,  -- from unified_strategy_registry
    
    -- Execution details
    entry_signal_time TEXT,
    execution_slippage REAL,  -- difference between signal price and fill
    
    -- Validation
    formula_applied_correctly BOOLEAN,
    validation_notes TEXT,
    
    created_at TEXT NOT NULL,
    UNIQUE(position_id, strategy_id)
);

CREATE INDEX IF NOT EXISTS idx_psl_position ON position_strategy_link(position_id);
CREATE INDEX IF NOT EXISTS idx_psl_strategy ON position_strategy_link(strategy_id);

-- =============================================================================
-- 6. Migration: Populate unified_strategy_registry from existing data
-- =============================================================================

-- Insert GP strategies from genetic_programmer.db
-- (Run this after connecting to both databases)

INSERT OR IGNORE INTO unified_strategy_registry (
    strategy_id, strategy_name, strategy_type,
    source_database, source_table, source_id,
    buy_formula, sell_formula,
    backtest_fitness, backtest_win_rate, backtest_sharpe,
    is_active, promotion_status, created_at
)
SELECT 
    'gp_' || s.strategy_id,
    s.name,
    'gp',
    'genetic_programmer',
    'gp_strategies',
    s.strategy_id,
    s.buy_formula,
    s.sell_formula,
    json_extract(s.fitness_json, '$.overall_fitness'),
    json_extract(s.fitness_json, '$.win_rate'),
    json_extract(s.fitness_json, '$.sharpe_ratio'),
    CASE WHEN s.status = 'WINNER' THEN 1 ELSE 0 END,
    CASE WHEN s.status = 'WINNER' THEN 'PRODUCTION' ELSE 'TESTING' END,
    s.created_at
FROM genetic_programmer.gp_strategies s
WHERE s.status = 'WINNER';

-- Insert MAPE strategies
INSERT OR IGNORE INTO unified_strategy_registry (
    strategy_id, strategy_name, strategy_type,
    source_database, source_table, source_id,
    backtest_fitness, backtest_win_rate,
    is_active, promotion_status, created_at
)
SELECT 
    'mape_' || m.strategy_id,
    'MAPE_' || m.cell_coords,
    'mape',
    'mape_evolver',
    'mape_archive',
    m.cell_coords,
    m.fitness,
    json_extract(m.behavior_json, '$.win_rate'),
    1,
    'PRODUCTION',
    m.created_at
FROM mape_evolver.mape_archive m
WHERE m.fitness > 0.5;

-- Insert Ensemble strategies
INSERT OR IGNORE INTO unified_strategy_registry (
    strategy_id, strategy_name, strategy_type,
    source_database, source_table, source_id,
    backtest_fitness, backtest_win_rate,
    is_active, promotion_status, created_at
)
SELECT 
    'ens_' || e.ensemble_id,
    e.name,
    'ensemble',
    'ensemble_evolver',
    'ensembles',
    e.ensemble_id,
    json_extract(e.fitness_json, '$.overall_fitness'),
    json_extract(e.fitness_json, '$.win_rate'),
    1,
    'PRODUCTION',
    e.created_at
FROM ensemble_evolver.ensembles e;

-- Insert FreshPicks as a strategy
INSERT OR IGNORE INTO unified_strategy_registry (
    strategy_id, strategy_name, strategy_type,
    source_database, source_table, source_id,
    buy_formula, sell_formula, parameters,
    backtest_fitness, backtest_win_rate,
    is_active, promotion_status, created_at
)
VALUES (
    'freshpicks_v1',
    'FreshPicks Funding Carry v1.0',
    'freshpicks',
    'freshpicks_dna_strategy',
    'DNAPickGenerator',
    'v1.0.0',
    'funding_rate_carry',
    'momentum_confirm',
    '{"min_funding_annualized": 0.10, "min_volume_ratio": 1.0, "min_rr": 1.5}',
    0.95,  -- Claimed fitness
    0.95,  -- Claimed 95% WR
    1,
    'PRODUCTION',
    datetime('now')
);

-- =============================================================================
-- 7. Update meta version
-- =============================================================================

UPDATE meta SET value = '1.1' WHERE key = 'schema_version';
INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_update_notes', 'Added genomic strategy tracking and FreshPicks snapshots');
INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_update_date', '2026-03-09');
