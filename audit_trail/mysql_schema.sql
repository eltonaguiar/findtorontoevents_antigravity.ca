-- ============================================================
-- Audit Trail MySQL Schema for ejaguiar1_stocks
-- ============================================================
-- Adds NEW tables only (never DROP existing).
-- Prefix: at_ = audit trail, bt_ = backtesting
-- ALL tables have asset_class + symbol for filtering.
-- Date: 2026-03-04
-- ============================================================

SET NAMES utf8mb4;

-- ── Core Audit Trail Tables (at_) ──────────────────────────

CREATE TABLE IF NOT EXISTS at_aggregation_runs (
    run_id              CHAR(36) PRIMARY KEY,
    started_at          DATETIME NOT NULL,
    finished_at         DATETIME,
    status              ENUM('RUNNING','COMPLETED','FAILED') NOT NULL DEFAULT 'RUNNING',
    systems_loaded      INT DEFAULT 0,
    raw_picks_count     INT DEFAULT 0,
    consensus_count     INT DEFAULT 0,
    regime_data         JSON,
    portfolio_drawdown  DECIMAL(10,4) DEFAULT 0,
    source              VARCHAR(50) DEFAULT 'aggregator' COMMENT 'backfill | aggregator | manual',
    INDEX idx_atr_status  (status),
    INDEX idx_atr_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_raw_picks (
    id                  CHAR(36) PRIMARY KEY,
    aggregation_run_id  CHAR(36) NOT NULL,
    source_system       VARCHAR(100) NOT NULL,
    symbol              VARCHAR(50) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    direction           ENUM('LONG','SHORT') NOT NULL,
    entry_price         DECIMAL(18,8),
    take_profit         DECIMAL(18,8),
    stop_loss           DECIMAL(18,8),
    risk_reward         DECIMAL(10,4),
    confidence          DECIMAL(5,4),
    strategy            VARCHAR(200),
    raw_payload         JSON,
    signal_timestamp    DATETIME,
    recorded_at         DATETIME NOT NULL,
    dedup_hash          CHAR(64) UNIQUE,
    was_stale           TINYINT(1) DEFAULT 0,
    was_banned          TINYINT(1) DEFAULT 0,
    was_demoted         TINYINT(1) DEFAULT 0,
    was_wr_suppressed   TINYINT(1) DEFAULT 0,
    created_by          VARCHAR(50) DEFAULT 'aggregator',
    -- outcome fields
    status              ENUM('OPEN','WON','LOST','EXPIRED','CLOSED') DEFAULT 'OPEN',
    exit_price          DECIMAL(18,8),
    exit_reason         VARCHAR(50),
    pnl_pct             DECIMAL(10,4),
    closed_at           DATETIME,
    FOREIGN KEY (aggregation_run_id) REFERENCES at_aggregation_runs(run_id),
    INDEX idx_rp_sys    (source_system),
    INDEX idx_rp_sym    (symbol),
    INDEX idx_rp_ts     (signal_timestamp),
    INDEX idx_rp_asset  (asset_class),
    INDEX idx_rp_status (status),
    INDEX idx_rp_run    (aggregation_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_consensus_picks (
    id                  CHAR(36) PRIMARY KEY,
    aggregation_run_id  CHAR(36) NOT NULL,
    symbol              VARCHAR(50) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
    direction           ENUM('LONG','SHORT') NOT NULL,
    entry_price         DECIMAL(18,8),
    take_profit         DECIMAL(18,8),
    stop_loss           DECIMAL(18,8),
    risk_reward         DECIMAL(10,4),
    confidence          DECIMAL(5,4),
    agreement_count     INT,
    source_systems      JSON,
    source_strategies   JSON,
    system_confidences  JSON,
    consensus_tier      VARCHAR(50),
    classification      VARCHAR(50),
    regime_data         JSON,
    discord_channel     VARCHAR(100),
    discord_message_id  VARCHAR(100),
    status              ENUM('OPEN','WON','LOST','EXPIRED','CLOSED') DEFAULT 'OPEN',
    exit_price          DECIMAL(18,8),
    exit_reason         VARCHAR(50),
    pnl_pct             DECIMAL(10,4),
    slippage_estimate   DECIMAL(10,4),
    generated_at        DATETIME NOT NULL,
    closed_at           DATETIME,
    FOREIGN KEY (aggregation_run_id) REFERENCES at_aggregation_runs(run_id),
    UNIQUE KEY uk_consensus (symbol, direction, entry_price, generated_at),
    INDEX idx_cp_sym    (symbol),
    INDEX idx_cp_status (status),
    INDEX idx_cp_asset  (asset_class),
    INDEX idx_cp_run    (aggregation_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_audit_events (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    event_type          VARCHAR(100) NOT NULL,
    pick_id             CHAR(36),
    aggregation_run_id  CHAR(36),
    symbol              VARCHAR(50),
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    payload             JSON,
    origin              VARCHAR(50) DEFAULT 'aggregator',
    created_at          DATETIME NOT NULL,
    INDEX idx_ae_type   (event_type),
    INDEX idx_ae_pick   (pick_id),
    INDEX idx_ae_sym    (symbol),
    INDEX idx_ae_run    (aggregation_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_filter_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    aggregation_run_id  CHAR(36),
    raw_pick_id         CHAR(36),
    symbol              VARCHAR(50),
    direction           VARCHAR(10),
    source_system       VARCHAR(100),
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    filter_reason       VARCHAR(100) NOT NULL,
    details             TEXT,
    created_at          DATETIME NOT NULL,
    INDEX idx_fl_reason (filter_reason),
    INDEX idx_fl_sym    (symbol),
    INDEX idx_fl_run    (aggregation_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_strategy_stats (
    strategy            VARCHAR(200) NOT NULL,
    source_system       VARCHAR(100) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    total_picks         INT DEFAULT 0,
    consensus_picks     INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    win_rate            DECIMAL(5,4) DEFAULT 0,
    avg_pnl_pct         DECIMAL(10,4) DEFAULT 0,
    best_pnl            DECIMAL(10,4) DEFAULT 0,
    worst_pnl           DECIMAL(10,4) DEFAULT 0,
    avg_risk_reward     DECIMAL(10,4) DEFAULT 0,
    last_updated        DATETIME,
    PRIMARY KEY (strategy, source_system),
    INDEX idx_ss_asset  (asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Discord Notification Tracking (at_discord_*) ──────────

CREATE TABLE IF NOT EXISTS at_discord_sent (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    channel             VARCHAR(100) NOT NULL COMMENT 'consensus | fresh-picks | dna-master | sandbox | kimi | alpha',
    webhook_name        VARCHAR(100) COMMENT 'DISCORD_WEBHOOK_URL | DISCORD_WEBHOOK_FRESHPICKS etc',
    symbol              VARCHAR(50) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    direction           ENUM('LONG','SHORT'),
    entry_price         DECIMAL(18,8),
    take_profit         DECIMAL(18,8),
    stop_loss           DECIMAL(18,8),
    confidence          DECIMAL(5,4),
    strategy            VARCHAR(200),
    source_system       VARCHAR(100),
    dedup_key           VARCHAR(200) UNIQUE COMMENT 'symbol__direction__entry_price or strategy::symbol::date',
    consensus_pick_id   CHAR(36) COMMENT 'FK to at_consensus_picks if applicable',
    sent_at             DATETIME NOT NULL,
    discord_message_id  VARCHAR(100),
    sent_payload        JSON COMMENT 'full embed/message sent',
    INDEX idx_ds_chan    (channel),
    INDEX idx_ds_sym    (symbol),
    INDEX idx_ds_asset  (asset_class),
    INDEX idx_ds_sent   (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS at_discord_gate_state (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    channel             VARCHAR(100) NOT NULL,
    symbol              VARCHAR(50) NOT NULL,
    direction           VARCHAR(10),
    gate_status         VARCHAR(50) COMMENT 'all_sent | quality_gate | rate_limited',
    total_scanned       INT DEFAULT 0,
    blocked_count       INT DEFAULT 0,
    entry_price         DECIMAL(18,8),
    confidence          DECIMAL(5,4),
    system_name         VARCHAR(100),
    recorded_at         DATETIME NOT NULL,
    INDEX idx_dg_chan    (channel),
    INDEX idx_dg_sym    (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Backtesting Data Tables (bt_) ─────────────────────────

CREATE TABLE IF NOT EXISTS bt_backtest_runs (
    id                  CHAR(36) PRIMARY KEY,
    source_db           VARCHAR(200) NOT NULL COMMENT 'original sqlite db relative path',
    source_table        VARCHAR(100) NOT NULL,
    strategy            VARCHAR(200),
    symbol              VARCHAR(50),
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    total_trades        INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    win_rate            DECIMAL(5,4),
    profit_factor       DECIMAL(10,4),
    total_return        DECIMAL(10,4),
    sharpe              DECIMAL(10,4),
    max_drawdown        DECIMAL(10,4),
    imported_at         DATETIME NOT NULL,
    INDEX idx_br_strat  (strategy),
    INDEX idx_br_asset  (asset_class),
    INDEX idx_br_sym    (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS bt_backtest_trades (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    backtest_run_id     CHAR(36),
    source_db           VARCHAR(200) NOT NULL,
    source_table        VARCHAR(100) NOT NULL,
    symbol              VARCHAR(50) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    direction           ENUM('LONG','SHORT'),
    strategy            VARCHAR(200),
    entry_price         DECIMAL(18,8),
    exit_price          DECIMAL(18,8),
    take_profit         DECIMAL(18,8),
    stop_loss           DECIMAL(18,8),
    entry_time          DATETIME,
    exit_time           DATETIME,
    pnl_pct             DECIMAL(10,4),
    status              VARCHAR(20),
    confidence          DECIMAL(5,4),
    raw_data            JSON COMMENT 'full original row as JSON',
    imported_at         DATETIME NOT NULL,
    FOREIGN KEY (backtest_run_id) REFERENCES bt_backtest_runs(id),
    INDEX idx_bt_sym    (symbol),
    INDEX idx_bt_asset  (asset_class),
    INDEX idx_bt_strat  (strategy),
    INDEX idx_bt_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Import Tracking ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS at_sqlite_imports (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    source_db_path      VARCHAR(500) NOT NULL,
    source_table        VARCHAR(100) NOT NULL,
    rows_imported       INT DEFAULT 0,
    target_table        VARCHAR(100) NOT NULL,
    asset_class         ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','UNKNOWN') DEFAULT 'UNKNOWN',
    imported_at         DATETIME NOT NULL,
    notes               TEXT,
    UNIQUE KEY uk_import (source_db_path(200), source_table),
    INDEX idx_si_asset  (asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Pick Outcomes ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS at_pick_outcomes (
    pick_id             CHAR(36) PRIMARY KEY,
    symbol              VARCHAR(50),
    strategy            VARCHAR(200),
    asset_class         VARCHAR(20),
    status              ENUM('OPEN','WON','LOST','EXPIRED','FLAT') NOT NULL,
    resolution_method   ENUM('TP_HIT','SL_HIT','TIME_EXPIRED','MANUAL'),
    pnl_pct             DECIMAL(10,4),
    resolved_at         DATETIME,
    resolver_version    VARCHAR(20),
    INDEX idx_po_status   (status),
    INDEX idx_po_strategy (strategy),
    INDEX idx_po_resolved (resolved_at),
    INDEX idx_po_asset    (asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
