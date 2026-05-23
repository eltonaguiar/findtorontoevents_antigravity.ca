-- Migration 001: Discord Audit Tables
-- Database: ejaguiar1_stocks (mysql.50webs.com)
-- Date: 2026-03-04
-- Description: Add Discord tracking to consensus_tracked + create audit tables
-- ============================================================================

-- ── 1. ALTER consensus_tracked: add Discord columns ─────────────────────────

ALTER TABLE consensus_tracked
  ADD COLUMN discord_sent       TINYINT(1)   NOT NULL DEFAULT 0       AFTER updated_at,
  ADD COLUMN discord_channel    VARCHAR(50)  DEFAULT NULL              AFTER discord_sent,
  ADD COLUMN discord_message_id VARCHAR(100) DEFAULT NULL              AFTER discord_channel,
  ADD COLUMN discord_sent_at    DATETIME     DEFAULT NULL              AFTER discord_message_id;

-- Index for finding unsent picks quickly
ALTER TABLE consensus_tracked
  ADD INDEX idx_discord_unsent (discord_sent, ticker, direction);

-- ── 2. at_discord_notifications: immutable log of every Discord send ────────

CREATE TABLE IF NOT EXISTS at_discord_notifications (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    symbol              VARCHAR(50)     NOT NULL,
    direction           VARCHAR(10)     NOT NULL DEFAULT 'LONG',
    entry_price         DECIMAL(18,8)   DEFAULT NULL,
    take_profit         DECIMAL(18,8)   DEFAULT NULL,
    stop_loss           DECIMAL(18,8)   DEFAULT NULL,
    confidence          DECIMAL(5,4)    DEFAULT NULL,
    agreement_count     INT             DEFAULT NULL,
    source_systems      JSON            DEFAULT NULL  COMMENT 'Array of system names that agreed',
    strategy            VARCHAR(100)    DEFAULT NULL,
    signal_tier         VARCHAR(20)     DEFAULT NULL  COMMENT 'STRONG_BUY/BUY/SELL/STRONG_SELL/NEUTRAL',
    asset_class         VARCHAR(20)     DEFAULT 'CRYPTO',
    discord_channel     VARCHAR(50)     NOT NULL      COMMENT 'consensus/freshpicks/portfolio/sandbox/dna_master',
    discord_webhook     VARCHAR(50)     DEFAULT NULL  COMMENT 'Env var name used (DISCORD_WEBHOOK_URL etc)',
    discord_message_id  VARCHAR(100)    DEFAULT NULL,
    event_type          VARCHAR(30)     NOT NULL      COMMENT 'PICK_POSTED/TP_HIT/SL_HIT/POSITION_UPDATE/REVERSAL/PORTFOLIO_SUMMARY',
    pnl_pct             DECIMAL(10,4)   DEFAULT NULL  COMMENT 'Realized P/L for TP_HIT/SL_HIT events',
    payload             JSON            DEFAULT NULL  COMMENT 'Full context JSON (pick dict, extra fields)',
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_symbol_dir       (symbol, direction),
    INDEX idx_event_type       (event_type, created_at),
    INDEX idx_channel_created  (discord_channel, created_at),
    INDEX idx_created_at       (created_at),
    UNIQUE INDEX idx_dedup     (symbol, direction, event_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 3. at_discord_gate_log: every gate decision (pass/reject) ───────────────

CREATE TABLE IF NOT EXISTS at_discord_gate_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    symbol              VARCHAR(50)     NOT NULL,
    direction           VARCHAR(10)     NOT NULL DEFAULT 'LONG',
    system_name         VARCHAR(100)    DEFAULT NULL  COMMENT 'Source system that generated the pick',
    strategy            VARCHAR(100)    DEFAULT NULL,
    gate_name           VARCHAR(30)     NOT NULL      COMMENT 'G1_DEDUP, G2_CONFIDENCE, G3_STRATEGY, G4_RR, G5_DYNAMIC_TPSL, G6_ENRICH, G7_RATE_CAP, G8_REGIME',
    gate_result         VARCHAR(10)     NOT NULL DEFAULT 'REJECT' COMMENT 'PASS or REJECT',
    reason              VARCHAR(255)    DEFAULT NULL,
    confidence          DECIMAL(5,4)    DEFAULT NULL,
    entry_price         DECIMAL(18,8)   DEFAULT NULL,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_symbol_gate      (symbol, direction, gate_name),
    INDEX idx_gate_result      (gate_name, gate_result, created_at),
    INDEX idx_created_at       (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
