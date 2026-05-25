-- ============================================================================
-- Migration: 202605250300_pick_research_and_prompts
-- Target:    ejaguiar1_stocks @ mysql.50webs.com (MySQL 5.7 / MariaDB 10.x)
-- Purpose:   Capture per-submission prompts, per-pick research metadata,
--            and denormalize provider onto tournament_picks.
-- Safety:    Idempotent. Uses CREATE TABLE IF NOT EXISTS + information_schema
--            guards (ADD COLUMN IF NOT EXISTS is MySQL 8.0.29+, not available
--            on 50webs). All new columns NULLABLE so existing INSERTs in
--            tools/ai_tournament/ingest_to_db.py:173-196 keep working unchanged.
-- Author:    Claude Opus 4.7
-- Date:      2026-05-25
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. tournament_prompts — one row per model submission run
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tournament_prompts (
    submission_id                  INT          NOT NULL AUTO_INCREMENT,
    model_id                       VARCHAR(100) NOT NULL,
    provider                       VARCHAR(100) DEFAULT NULL,
    prompt_version                 VARCHAR(50)  DEFAULT NULL,
    system_prompt                  TEXT         DEFAULT NULL,
    user_prompt                    TEXT         DEFAULT NULL,
    ideal_trading_style_by_class   JSON         DEFAULT NULL,
    generated_at                   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (submission_id),
    KEY idx_tp_model_generated  (model_id, generated_at),
    KEY idx_tp_provider         (provider),
    KEY idx_tp_prompt_version   (prompt_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 2. tournament_pick_research — one row per pick (1:1 with tournament_picks)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tournament_pick_research (
    pick_id              INT  NOT NULL,
    symbols_screened     INT  DEFAULT NULL,
    sources_jsonl        JSON DEFAULT NULL,
    research_basis       ENUM('informed','partial','speculation','random_guess')
                              DEFAULT NULL,
    self_audit_response  TEXT DEFAULT NULL,
    recorded_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pick_id),
    KEY idx_tpr_basis  (research_basis),
    CONSTRAINT fk_tpr_pick
        FOREIGN KEY (pick_id)
        REFERENCES tournament_picks (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. ALTER tournament_picks — add prompt_submission_id, provider
--    50webs MariaDB does NOT support `ADD COLUMN IF NOT EXISTS` reliably.
--    Use an information_schema guard via stored procedure for idempotency.
-- ---------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS _tournament_picks_add_cols;

DELIMITER //
CREATE PROCEDURE _tournament_picks_add_cols()
BEGIN
    -- prompt_submission_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'tournament_picks'
          AND COLUMN_NAME  = 'prompt_submission_id'
    ) THEN
        ALTER TABLE tournament_picks
            ADD COLUMN prompt_submission_id INT NULL DEFAULT NULL AFTER gameplan_id;
        ALTER TABLE tournament_picks
            ADD KEY idx_tp_prompt_submission (prompt_submission_id);
        ALTER TABLE tournament_picks
            ADD CONSTRAINT fk_tp_prompt_submission
                FOREIGN KEY (prompt_submission_id)
                REFERENCES tournament_prompts (submission_id)
                ON DELETE SET NULL
                ON UPDATE CASCADE;
    END IF;

    -- provider (denormalized from tournament_model_stats)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'tournament_picks'
          AND COLUMN_NAME  = 'provider'
    ) THEN
        ALTER TABLE tournament_picks
            ADD COLUMN provider VARCHAR(100) NULL DEFAULT NULL AFTER model_id;
        ALTER TABLE tournament_picks
            ADD KEY idx_tp_provider (provider);
    END IF;
END //
DELIMITER ;

CALL _tournament_picks_add_cols();
DROP PROCEDURE IF EXISTS _tournament_picks_add_cols;

-- ---------------------------------------------------------------------------
-- 4. Backfill provider for historical rows from tournament_model_stats.
--    Safe: only updates rows where provider IS NULL.
-- ---------------------------------------------------------------------------
UPDATE tournament_picks p
JOIN  tournament_model_stats m ON m.model_id = p.model_id
SET   p.provider = m.provider
WHERE p.provider IS NULL
  AND m.provider IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Verification queries (run manually after migration):
--
--   SHOW CREATE TABLE tournament_prompts;
--   SHOW CREATE TABLE tournament_pick_research;
--   SHOW COLUMNS FROM tournament_picks LIKE 'prompt_submission_id';
--   SHOW COLUMNS FROM tournament_picks LIKE 'provider';
--   SELECT COUNT(*) AS picks_with_provider FROM tournament_picks WHERE provider IS NOT NULL;
--   SELECT COUNT(*) AS picks_without_provider FROM tournament_picks WHERE provider IS NULL;
-- ---------------------------------------------------------------------------
