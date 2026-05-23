-- ============================================================================
-- 05_pick_audit_trail_schema.sql
-- Audit-trail acceleration layer for findtorontoevents.ca/audit pick flow.
--
-- Problem: tracing one pick from emitter -> gates -> active/closed today means
-- joining at_raw_picks + at_filter_log (818k rows, REJECT-only, no ordered
-- trace, no PASS rows) + at_consensus_picks + at_signal_outcomes + 17 MB of
-- JSON snapshots. Slow and lossy.
--
-- This migration adds:
--   at_pick_audit_trail  -- one row per (pick, gate evaluation). Full ordered
--                           PASS/REJECT/SKIP/WARN trace. Populated by an opt-in
--                           Python writer (see Wiring Plan in the audit-pick-
--                           flow skill). Empty until that writer is wired.
--   at_pick_flow_daily   -- per-day per-asset-class funnel rollup. Populated
--                           NIGHTLY by ev_pick_flow_daily_rollup from tables
--                           that ALREADY exist. Works immediately, zero Python.
--   at_job_log           -- run log for scheduled DB events.
--
-- Engine: InnoDB. Charset: utf8mb4 / utf8mb4_unicode_ci  (MUST match the
-- existing at_* tables — at_raw_picks/at_filter_log are utf8mb4_unicode_ci;
-- a utf8mb4_0900_ai_ci table breaks JOINs with "Illegal mix of collations").
-- Idempotent: safe to re-run. Target: ejaguiar1_stocks @ mysql.50webs.com
-- (MySQL 8.4.7, event_scheduler=ON verified, InnoDB verified).
--
-- APPLIED LIVE 2026-05-18. Event-scheduler fire verified with a 2-minute
-- one-shot test event (logged to at_job_log, then auto-dropped).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Fine-grained per-gate trace  (one row per pick per gate evaluation)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS at_pick_audit_trail (
    id                 BIGINT       NOT NULL AUTO_INCREMENT,
    raw_pick_id        BIGINT       NULL,            -- FK at_raw_picks.id
    dedup_hash         CHAR(64)     NULL,            -- survives if raw_pick_id unknown
    aggregation_run_id VARCHAR(64)  NULL,
    symbol             VARCHAR(32)  NOT NULL,
    asset_class        VARCHAR(20)  NULL,
    source_system      VARCHAR(64)  NULL,
    strategy           VARCHAR(120) NULL,
    direction          VARCHAR(8)   NULL,
    pipeline_stage     ENUM('EMIT','ACTIVE_GATE','SMART_GATE','HC_GATE',
                            'MONEY_READY','CONSENSUS','OUTCOME') NOT NULL,
    gate_name          VARCHAR(80)  NOT NULL,        -- e.g. 'M-108_magnitude_sanity'
    gate_order         SMALLINT     NULL,            -- position in the gate sequence
    decision           ENUM('PASS','REJECT','SKIP','WARN') NOT NULL,
    reason             VARCHAR(255) NULL,
    detail             JSON         NULL,            -- {threshold, observed, config_key}
    score_snapshot     DECIMAL(8,3) NULL,
    evaluated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_apat_raw_pick   (raw_pick_id),
    KEY idx_apat_dedup      (dedup_hash),
    KEY idx_apat_class_time (asset_class, evaluated_at),
    KEY idx_apat_gate       (gate_name, decision),
    KEY idx_apat_run        (aggregation_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Per-pick per-gate decision trace. Populated by opt-in writer.';

-- ----------------------------------------------------------------------------
-- 2. Per-day per-asset-class funnel rollup
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS at_pick_flow_daily (
    flow_date         DATE          NOT NULL,
    asset_class       VARCHAR(20)   NOT NULL,
    raw_emitted       INT           NOT NULL DEFAULT 0,  -- at_raw_picks recorded that day
    rejected_total    INT           NOT NULL DEFAULT 0,  -- at_filter_log rows that day
    reject_top_reason VARCHAR(64)   NULL,
    consensus_count   INT           NOT NULL DEFAULT 0,
    closed_count      INT           NOT NULL DEFAULT 0,  -- picks with closed_at that day
    wins              INT           NOT NULL DEFAULT 0,
    losses            INT           NOT NULL DEFAULT 0,
    gross_win_pct     DECIMAL(12,3) NOT NULL DEFAULT 0,
    gross_loss_pct    DECIMAL(12,3) NOT NULL DEFAULT 0,
    win_rate          DECIMAL(6,3)  NULL,               -- wins / closed_count * 100
    profit_factor     DECIMAL(8,3)  NULL,               -- gross_win / gross_loss
    refreshed_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (flow_date, asset_class),
    KEY idx_apfd_class (asset_class, flow_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Nightly per-class pick funnel rollup. Source: at_raw_picks+at_filter_log.';

-- ----------------------------------------------------------------------------
-- 3. Scheduled-event run log
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS at_job_log (
    id                BIGINT       NOT NULL AUTO_INCREMENT,
    job_name          VARCHAR(64)  NOT NULL,
    run_time          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status            VARCHAR(16)  NOT NULL DEFAULT 'OK',   -- OK | ERROR
    records_processed INT          NULL,
    note              VARCHAR(255) NULL,
    PRIMARY KEY (id),
    KEY idx_jl_job (job_name, run_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Run log for scheduled DB events.';

-- ----------------------------------------------------------------------------
-- 4. Rollup procedure  (recomputes one day; callable for backfill)
--    - DECLARE EXIT HANDLER logs failures to at_job_log then RESIGNALs
--    - 400-day retention sweep on at_pick_flow_daily
--    - self-logs every run to at_job_log
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_rebuild_pick_flow_daily;
DELIMITER $$
CREATE PROCEDURE sp_rebuild_pick_flow_daily(IN p_day DATE)
BEGIN
    DECLARE v_rows INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        INSERT INTO at_job_log(job_name,status,records_processed,note)
        VALUES('sp_rebuild_pick_flow_daily','ERROR',NULL,CONCAT('failed for ',p_day));
        RESIGNAL;
    END;

    REPLACE INTO at_pick_flow_daily
        (flow_date,asset_class,raw_emitted,closed_count,wins,losses,
         gross_win_pct,gross_loss_pct,win_rate,profit_factor,refreshed_at)
    SELECT p_day, COALESCE(NULLIF(asset_class,''),'UNKNOWN') AS ac,
        SUM(DATE(recorded_at)=p_day),
        SUM(DATE(closed_at)=p_day AND pnl_pct IS NOT NULL),
        SUM(DATE(closed_at)=p_day AND pnl_pct>0),
        SUM(DATE(closed_at)=p_day AND pnl_pct<=0 AND pnl_pct IS NOT NULL),
        ROUND(SUM(CASE WHEN DATE(closed_at)=p_day AND pnl_pct>0
            THEN pnl_pct ELSE 0 END),3),
        ROUND(ABS(SUM(CASE WHEN DATE(closed_at)=p_day AND pnl_pct<=0
            THEN pnl_pct ELSE 0 END)),3),
        NULL, NULL, NOW()
    FROM at_raw_picks
    WHERE DATE(recorded_at)=p_day OR DATE(closed_at)=p_day
    GROUP BY ac;
    SET v_rows = ROW_COUNT();

    UPDATE at_pick_flow_daily
       SET win_rate     = CASE WHEN closed_count>0
                            THEN ROUND(100*wins/closed_count,3) END,
           profit_factor = CASE WHEN gross_loss_pct>0
                            THEN ROUND(gross_win_pct/gross_loss_pct,3) END
     WHERE flow_date=p_day;

    -- rejected_total = total rows; reject_top_reason = MODAL reason (most frequent,
    -- not alphabetically-first — a GROUP_CONCAT+SUBSTRING_INDEX hack would be wrong).
    UPDATE at_pick_flow_daily d
      JOIN (
        SELECT ac, n, top_reason FROM (
          SELECT COALESCE(NULLIF(asset_class,''),'UNKNOWN') ac,
                 filter_reason AS top_reason,
                 SUM(COUNT(*)) OVER (PARTITION BY
                     COALESCE(NULLIF(asset_class,''),'UNKNOWN')) n,
                 ROW_NUMBER() OVER (PARTITION BY
                     COALESCE(NULLIF(asset_class,''),'UNKNOWN')
                     ORDER BY COUNT(*) DESC, filter_reason) rk
          FROM at_filter_log
          WHERE DATE(created_at)=p_day
          GROUP BY ac, filter_reason
        ) z WHERE rk=1
      ) f ON f.ac=d.asset_class AND d.flow_date=p_day
       SET d.rejected_total=f.n, d.reject_top_reason=f.top_reason;

    DELETE FROM at_pick_flow_daily WHERE flow_date < CURDATE()-INTERVAL 400 DAY;

    INSERT INTO at_job_log(job_name,status,records_processed,note)
    VALUES('sp_rebuild_pick_flow_daily','OK',v_rows,CONCAT('rollup for ',p_day));
END$$
DELIMITER ;

-- ----------------------------------------------------------------------------
-- 5. Nightly event  (rebuilds yesterday at 06:10 server time)
--    Requires event_scheduler=ON  (SET GLOBAL event_scheduler=ON if needed;
--    verified ON on this server).
-- ----------------------------------------------------------------------------
DROP EVENT IF EXISTS ev_pick_flow_daily_rollup;
CREATE EVENT ev_pick_flow_daily_rollup
    ON SCHEDULE EVERY 1 DAY
    STARTS (TIMESTAMP(CURDATE()) + INTERVAL 1 DAY + INTERVAL 370 MINUTE)
    DO CALL sp_rebuild_pick_flow_daily(CURDATE() - INTERVAL 1 DAY);

-- Backfill the trailing window once after first apply:
--   CALL sp_rebuild_pick_flow_daily('2026-05-18');  -- repeat per day, ~15 days
-- Verify the scheduler actually fires (one-shot 2-min probe, auto-drops):
--   CREATE EVENT ev_probe ON SCHEDULE AT CURRENT_TIMESTAMP+INTERVAL 2 MINUTE
--     ON COMPLETION NOT PRESERVE
--     DO INSERT INTO at_job_log(job_name,note) VALUES('ev_probe','fire test');
--   -- wait 2 min, then: SELECT * FROM at_job_log WHERE job_name='ev_probe';
