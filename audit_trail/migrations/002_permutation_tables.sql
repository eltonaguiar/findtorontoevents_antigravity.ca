-- ============================================================
-- Migration 002: Cross-Permutation Tracking Tables
-- ============================================================
-- Adds tables for cross-system and cross-strategy permutation
-- analysis results, linking to the audit trail.
-- Date: 2026-03-08
-- ============================================================

SET NAMES utf8mb4;

-- ── Cross-System Permutation Results ─────────────────────────

CREATE TABLE IF NOT EXISTS at_permutation_snapshots (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_type       ENUM('SYSTEM','STRATEGY') NOT NULL,
    permutation_id      VARCHAR(100) NOT NULL COMMENT 'e.g. solo_battleground, pair_alpha_kimi',
    permutation_name    VARCHAR(200) NOT NULL COMMENT 'e.g. Solo: Battleground',
    category            VARCHAR(50) DEFAULT NULL COMMENT 'trend, confluence, category, hybrid (strategy only)',
    systems             JSON COMMENT 'array of system identifiers',
    strategies          JSON COMMENT 'array of strategy identifiers',
    min_agreement       INT DEFAULT 1,
    trust_score         DECIMAL(5,1) DEFAULT 0.0,
    trust_tier          VARCHAR(50) DEFAULT 'Unproven',
    total_trades        INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    win_rate            DECIMAL(5,1) DEFAULT 0.0,
    total_pnl           DECIMAL(12,4) DEFAULT 0.0,
    avg_pnl             DECIMAL(10,4) DEFAULT 0.0,
    profit_factor       DECIMAL(10,4) DEFAULT NULL,
    active_pick_count   INT DEFAULT 0,
    closed_pick_count   INT DEFAULT 0,
    snapshot_at         DATETIME NOT NULL COMMENT 'when this snapshot was computed',
    INDEX idx_ps_type   (snapshot_type),
    INDEX idx_ps_perm   (permutation_id),
    INDEX idx_ps_trust  (trust_score DESC),
    INDEX idx_ps_tier   (trust_tier),
    INDEX idx_ps_snap   (snapshot_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Permutation Pick Membership ──────────────────────────────
-- Tracks which picks belong to which permutations

CREATE TABLE IF NOT EXISTS at_permutation_picks (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_id         INT NOT NULL COMMENT 'FK to at_permutation_snapshots',
    permutation_id      VARCHAR(100) NOT NULL,
    symbol              VARCHAR(50) NOT NULL,
    direction           ENUM('LONG','SHORT') NOT NULL,
    agreement_count     INT DEFAULT 1,
    source_systems      JSON,
    confidence          DECIMAL(5,4) DEFAULT NULL,
    pnl_pct             DECIMAL(10,4) DEFAULT NULL,
    exit_reason         VARCHAR(50) DEFAULT NULL,
    pick_status         ENUM('ACTIVE','CLOSED') NOT NULL DEFAULT 'ACTIVE',
    recorded_at         DATETIME NOT NULL,
    FOREIGN KEY (snapshot_id) REFERENCES at_permutation_snapshots(id) ON DELETE CASCADE,
    INDEX idx_pp_perm   (permutation_id),
    INDEX idx_pp_sym    (symbol),
    INDEX idx_pp_status (pick_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
