-- strategy_health/schema.sql
-- Version: 2026-03-04-v1

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS strategy_health (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    source_system     VARCHAR(100) NOT NULL,
    strategy          VARCHAR(200) NOT NULL,
    asset_class       VARCHAR(20),
    total_trades      INT DEFAULT 0,
    wins              INT DEFAULT 0,
    losses            INT DEFAULT 0,
    win_rate          DECIMAL(5,4) DEFAULT 0,
    avg_win_pct       DECIMAL(10,4) DEFAULT 0,
    avg_loss_pct      DECIMAL(10,4) DEFAULT 0,
    expectancy        DECIMAL(10,4) DEFAULT 0,
    fees_adj_expect   DECIMAL(10,4) DEFAULT 0,
    profit_factor     DECIMAL(10,4),
    rolling_30d_wr    DECIMAL(5,4),
    tier              ENUM('CORE','INCUBATOR','BANNED') DEFAULT 'INCUBATOR',
    tier_changed_at   DATETIME,
    tier_reason       TEXT,
    wf_passed         BOOLEAN DEFAULT NULL,
    wf_last_checked   DATETIME,
    last_evaluated    DATETIME,
    UNIQUE KEY uk_health (source_system, strategy),
    INDEX idx_sh_tier (tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS strategy_health_audit (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_system   VARCHAR(100),
    strategy        VARCHAR(200),
    old_tier        ENUM('CORE','INCUBATOR','BANNED'),
    new_tier        ENUM('CORE','INCUBATOR','BANNED'),
    reason          TEXT,
    metrics_snapshot JSON,
    created_at      DATETIME DEFAULT NOW(),
    INDEX idx_sha_strat (strategy),
    INDEX idx_sha_ts    (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
