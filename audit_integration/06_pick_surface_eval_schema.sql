-- ============================================================================
-- 06_pick_surface_eval_schema.sql
-- Per-pick surface-qualification + gate-input snapshot, so any /audit front-end
-- surface (Smart Picks button, Smart Picks tab, High Conviction, Money Ready,
-- any filter) is fully traceable and back-testable.
--
-- WHY: trading_picks.trust_score is NULL on ~100% of closed rows. The runtime
-- gate inputs (trust_score, trust_tier, forward_wr, regime, consensus_count,
-- smart_score) only exist in-memory at dashboard-generation time and are never
-- persisted. Result: you cannot reproduce the High Conviction gate, or audit
-- WHICH surface a pick qualified for, from the DB. This table fixes that by
-- FREEZING the gate-input snapshot + the 4 surface-qualification booleans at
-- decision time.
--
-- One row per pick per evaluation. Populated by the opt-in writer
-- tools/pick_surface_snapshot.py (see its Wiring Plan). Empty until wired.
--
-- Engine InnoDB, charset utf8mb4 / utf8mb4_unicode_ci (MUST match the existing
-- at_* tables). Idempotent. Target: ejaguiar1_stocks @ mysql.50webs.com.
-- ============================================================================

CREATE TABLE IF NOT EXISTS at_pick_surface_eval (
    id                 BIGINT       NOT NULL AUTO_INCREMENT,
    raw_pick_id        BIGINT       NULL,            -- FK at_raw_picks.id
    dedup_hash         CHAR(64)     NULL,
    aggregation_run_id VARCHAR(64)  NULL,
    symbol             VARCHAR(32)  NOT NULL,
    asset_class        VARCHAR(20)  NULL,
    direction          VARCHAR(8)   NULL,
    strategy           VARCHAR(120) NULL,
    source_system      VARCHAR(64)  NULL,
    decision_ts        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ── frozen gate-input snapshot (the fields trading_picks loses) ──────────
    elite_score        DECIMAL(8,3) NULL,
    smart_score        DECIMAL(8,3) NULL,
    trust_score        DECIMAL(8,3) NULL,
    trust_tier         VARCHAR(24)  NULL,            -- RELIABLE/PROBATION/...
    confidence         DECIMAL(6,4) NULL,
    forward_wr         DECIMAL(6,3) NULL,            -- strategy forward win-rate %
    risk_reward        DECIMAL(8,3) NULL,
    regime             VARCHAR(24)  NULL,            -- bull/bear/neutral at decision
    consensus_count    SMALLINT     NULL,            -- independent signal groups

    -- ── surface-qualification flags (which /audit surface this pick is on) ──
    in_active          TINYINT(1)   NOT NULL DEFAULT 0,  -- passes_active_gate
    in_smart_picks     TINYINT(1)   NOT NULL DEFAULT 0,  -- passes_smart_gate + top-N
    in_high_conviction TINYINT(1)   NOT NULL DEFAULT 0,  -- passes_high_conviction_pick
    in_money_ready     TINYINT(1)   NOT NULL DEFAULT 0,  -- class verdict MONEY_READY
    surface_detail     JSON         NULL,                -- per-surface reason / failing gate

    -- ── outcome (backfilled when the pick resolves) ─────────────────────────
    status             VARCHAR(16)  NULL,
    pnl_pct            DECIMAL(12,4) NULL,
    closed_at          DATETIME     NULL,

    PRIMARY KEY (id),
    KEY idx_apse_raw_pick   (raw_pick_id),
    KEY idx_apse_dedup      (dedup_hash),
    KEY idx_apse_class_ts   (asset_class, decision_ts),
    KEY idx_apse_smart      (in_smart_picks, asset_class),
    KEY idx_apse_hc         (in_high_conviction, asset_class),
    KEY idx_apse_money      (in_money_ready, asset_class),
    KEY idx_apse_outcome    (status, closed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Per-pick surface qualification + frozen gate-input snapshot. Opt-in writer.';

-- Query examples (what this table unlocks):
--   -- per-class WR/PF for picks that qualified for High Conviction:
--   SELECT asset_class, COUNT(*) n,
--          ROUND(100*SUM(pnl_pct>0)/COUNT(*),1) wr,
--          ROUND(SUM(GREATEST(pnl_pct,0))/NULLIF(ABS(SUM(LEAST(pnl_pct,0))),0),2) pf
--     FROM at_pick_surface_eval
--    WHERE in_high_conviction=1 AND pnl_pct IS NOT NULL
--    GROUP BY asset_class;
--   -- HC vs Smart Picks divergence (picks in one but not the other):
--   SELECT in_smart_picks, in_high_conviction, COUNT(*) FROM at_pick_surface_eval
--    GROUP BY in_smart_picks, in_high_conviction;
--   -- simulate any single-field cut — handled by tools/edge_finder.py.
