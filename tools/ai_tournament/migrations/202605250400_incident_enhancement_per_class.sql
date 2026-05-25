-- ============================================================================
-- Migration: 202605250400_incident_enhancement_per_class
-- Target:    ejaguiar1_stocks @ mysql.50webs.com
-- Purpose:   Capture per-asset-class issues (INCIDENT_*) and improvement
--            suggestions (ENHANCEMENT_*) coming back from the peer-AI swarm
--            (qwen, kilo, opencode/Ring, grok, nemotron, claude...).
-- Pattern:   8 asset classes × 2 buckets = 16 tables + 2 unified views
--            (vw_all_incidents, vw_all_enhancements) for cross-class queries.
-- Safety:    Idempotent (CREATE TABLE IF NOT EXISTS, DROP VIEW IF EXISTS).
-- Naming:    Asset-class suffix matches the UI tab labels: STOCKS, ETFS,
--            CRYPTO, FOREX, COMMODITIES, BONDS, FUTURES, PENNY. All <64 char
--            MySQL limit (INCIDENT_COMMODITIES = 19 chars — well under).
-- Date:      2026-05-25 04:00 UTC
-- ============================================================================

-- ---- 8 × INCIDENT_<CLASS> -------------------------------------------------
-- One row per bug / data-quality issue / outage / suspect stat per class.
-- Examples for INCIDENT_STOCKS today:
--   ('audit-2026-05-25', 'trust_score NULL on 99.99% of closed equity picks',
--    'P0', 'OPEN', 'trading_picks.trust_score', 'claude-opus-4-7',
--    'Backfill from strategy registry or remove from HC gate', ...)
-- ---------------------------------------------------------------------------

-- Generic skeleton applied to all 8 classes; defined once, then 8 CREATE
-- statements that re-use the column set. Each table is independent
-- (no FK between them) so per-class privileges can differ later.

CREATE TABLE IF NOT EXISTS INCIDENT_STOCKS (
    incident_id        INT          NOT NULL AUTO_INCREMENT,
    asset_class        VARCHAR(20)  NOT NULL DEFAULT 'STOCKS',
    source_ref         VARCHAR(255) DEFAULT NULL,
    title              VARCHAR(500) NOT NULL,
    description        TEXT         DEFAULT NULL,
    severity           ENUM('P0','P1','P2','P3','INFO') DEFAULT 'P2',
    status             ENUM('OPEN','TRIAGED','IN_PROGRESS','RESOLVED','WONTFIX','DUPLICATE') DEFAULT 'OPEN',
    affected_component VARCHAR(255) DEFAULT NULL,
    reported_by        VARCHAR(100) DEFAULT NULL,
    assigned_to        VARCHAR(100) DEFAULT NULL,
    recommended_fix    TEXT         DEFAULT NULL,
    evidence           JSON         DEFAULT NULL,
    resolution_notes   TEXT         DEFAULT NULL,
    duplicate_of       INT          DEFAULT NULL,
    link_md_path       VARCHAR(500) DEFAULT NULL,
    link_url           VARCHAR(1000) DEFAULT NULL,
    link_github_ref    VARCHAR(255) DEFAULT NULL,
    created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at        DATETIME     DEFAULT NULL,
    PRIMARY KEY (incident_id),
    KEY idx_in_status_sev (status, severity),
    KEY idx_in_reporter   (reported_by),
    KEY idx_in_component  (affected_component),
    KEY idx_in_created    (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS INCIDENT_OVERALL LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_ETFS LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_CRYPTO LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_FOREX LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_COMMODITIES LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_BONDS LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_FUTURES LIKE INCIDENT_STOCKS;
CREATE TABLE IF NOT EXISTS INCIDENT_PENNY LIKE INCIDENT_STOCKS;

-- The asset_class column carries the right default per table so a
-- LIKE-cloned table inherits 'STOCKS' as default — fix that:
ALTER TABLE INCIDENT_ETFS        ALTER COLUMN asset_class SET DEFAULT 'ETFS';
ALTER TABLE INCIDENT_CRYPTO      ALTER COLUMN asset_class SET DEFAULT 'CRYPTO';
ALTER TABLE INCIDENT_FOREX       ALTER COLUMN asset_class SET DEFAULT 'FOREX';
ALTER TABLE INCIDENT_COMMODITIES ALTER COLUMN asset_class SET DEFAULT 'COMMODITIES';
ALTER TABLE INCIDENT_BONDS       ALTER COLUMN asset_class SET DEFAULT 'BONDS';
ALTER TABLE INCIDENT_FUTURES     ALTER COLUMN asset_class SET DEFAULT 'FUTURES';
ALTER TABLE INCIDENT_PENNY       ALTER COLUMN asset_class SET DEFAULT 'PENNY';
ALTER TABLE INCIDENT_OVERALL     ALTER COLUMN asset_class SET DEFAULT 'OVERALL';

-- ---- 8 × ENHANCEMENT_<CLASS> ----------------------------------------------
-- One row per improvement suggestion / scoring tweak / new feature / data-feed
-- addition coming back from peer-AI analysis. Lifecycle status (BACKLOG →
-- VALIDATED → ACCEPTED → IMPLEMENTED / REJECTED).
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ENHANCEMENT_STOCKS (
    enhancement_id       INT          NOT NULL AUTO_INCREMENT,
    asset_class          VARCHAR(20)  NOT NULL DEFAULT 'STOCKS',
    source_ref           VARCHAR(255) DEFAULT NULL,
    title                VARCHAR(500) NOT NULL,
    description          TEXT         DEFAULT NULL,
    category             ENUM('SCORING','GATE','DATA_FEED','UI','METHODOLOGY','PERSONA','OTHER') DEFAULT 'OTHER',
    expected_impact      ENUM('HIGH','MEDIUM','LOW','UNKNOWN') DEFAULT 'UNKNOWN',
    effort               ENUM('S','M','L','XL') DEFAULT 'M',
    status               ENUM('BACKLOG','VALIDATED','ACCEPTED','IMPLEMENTED','REJECTED','SUPERSEDED') DEFAULT 'BACKLOG',
    proposed_by          VARCHAR(100) DEFAULT NULL,
    related_persona_id   VARCHAR(100) DEFAULT NULL,
    proposed_features    JSON         DEFAULT NULL,
    success_metric       VARCHAR(500) DEFAULT NULL,
    target_release       VARCHAR(50)  DEFAULT NULL,
    review_notes         TEXT         DEFAULT NULL,
    implementation_pr    VARCHAR(255) DEFAULT NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    implemented_at       DATETIME     DEFAULT NULL,
    PRIMARY KEY (enhancement_id),
    KEY idx_en_status_cat  (status, category),
    KEY idx_en_proposer    (proposed_by),
    KEY idx_en_impact      (expected_impact, effort),
    KEY idx_en_persona     (related_persona_id),
    KEY idx_en_created     (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ENHANCEMENT_OVERALL     LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_ETFS        LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_CRYPTO      LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_FOREX       LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_COMMODITIES LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_BONDS       LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_FUTURES     LIKE ENHANCEMENT_STOCKS;
CREATE TABLE IF NOT EXISTS ENHANCEMENT_PENNY       LIKE ENHANCEMENT_STOCKS;

ALTER TABLE ENHANCEMENT_ETFS        ALTER COLUMN asset_class SET DEFAULT 'ETFS';
ALTER TABLE ENHANCEMENT_CRYPTO      ALTER COLUMN asset_class SET DEFAULT 'CRYPTO';
ALTER TABLE ENHANCEMENT_FOREX       ALTER COLUMN asset_class SET DEFAULT 'FOREX';
ALTER TABLE ENHANCEMENT_COMMODITIES ALTER COLUMN asset_class SET DEFAULT 'COMMODITIES';
ALTER TABLE ENHANCEMENT_BONDS       ALTER COLUMN asset_class SET DEFAULT 'BONDS';
ALTER TABLE ENHANCEMENT_FUTURES     ALTER COLUMN asset_class SET DEFAULT 'FUTURES';
ALTER TABLE ENHANCEMENT_PENNY       ALTER COLUMN asset_class SET DEFAULT 'PENNY';
ALTER TABLE ENHANCEMENT_OVERALL     ALTER COLUMN asset_class SET DEFAULT 'OVERALL';

-- ---- Unified views (cross-class queries) ----------------------------------
DROP VIEW IF EXISTS vw_all_incidents;
CREATE VIEW vw_all_incidents AS
    SELECT * FROM INCIDENT_STOCKS
    UNION ALL SELECT * FROM INCIDENT_ETFS
    UNION ALL SELECT * FROM INCIDENT_CRYPTO
    UNION ALL SELECT * FROM INCIDENT_FOREX
    UNION ALL SELECT * FROM INCIDENT_COMMODITIES
    UNION ALL SELECT * FROM INCIDENT_BONDS
    UNION ALL SELECT * FROM INCIDENT_FUTURES
    UNION ALL SELECT * FROM INCIDENT_PENNY
    UNION ALL SELECT * FROM INCIDENT_OVERALL;

DROP VIEW IF EXISTS vw_all_enhancements;
CREATE VIEW vw_all_enhancements AS
    SELECT * FROM ENHANCEMENT_STOCKS
    UNION ALL SELECT * FROM ENHANCEMENT_ETFS
    UNION ALL SELECT * FROM ENHANCEMENT_CRYPTO
    UNION ALL SELECT * FROM ENHANCEMENT_FOREX
    UNION ALL SELECT * FROM ENHANCEMENT_COMMODITIES
    UNION ALL SELECT * FROM ENHANCEMENT_BONDS
    UNION ALL SELECT * FROM ENHANCEMENT_FUTURES
    UNION ALL SELECT * FROM ENHANCEMENT_PENNY
    UNION ALL SELECT * FROM ENHANCEMENT_OVERALL;

-- ---- Verification (run manually after migration) --------------------------
-- SHOW TABLES LIKE 'INCIDENT_%';
-- SHOW TABLES LIKE 'ENHANCEMENT_%';
-- SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES
--   WHERE TABLE_SCHEMA = DATABASE()
--     AND (TABLE_NAME LIKE 'INCIDENT_%' OR TABLE_NAME LIKE 'ENHANCEMENT_%');
-- SELECT COUNT(*) AS total_incidents    FROM vw_all_incidents;
-- SELECT COUNT(*) AS total_enhancements FROM vw_all_enhancements;
