-- ============================================================================
-- audit_picks_summary_schema.sql
-- Database: ejaguiar1_stocks  (mysql.50webs.com)
-- Purpose : Let a user / AI quickly answer, for findtorontoevents.ca/audit:
--   1. What are the current ACTIVE picks, and WHY were they picked?
--   2. What safety-gate parameters did each pick pass?
--   3. Which symbols in the universe did NOT become active picks, and WHY?
--      (DSR fail, score below floor, gate X blocked, leakage, etc.)
--   4. What does every criterion / gate / score actually MEAN? (definitions)
--
-- All tables are written by the pipeline (GitHub Actions -> dashboard
-- generator). They are a flattened, query-friendly mirror of the JSON the
-- pipeline already produces (pf_registry.json, dashboard_data.json,
-- active_picks.json). READ them; the pipeline OWNS the writes.
--
-- MySQL 5.7+/8.0 compatible. InnoDB + utf8mb4. Idempotent (IF NOT EXISTS).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. audit_active_picks — one row per current ACTIVE pick + why it was picked
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_active_picks (
    id                  VARCHAR(64)   NOT NULL COMMENT 'pick id / dedup_hash',
    symbol              VARCHAR(32)   NOT NULL,
    asset_class         VARCHAR(16)   NOT NULL COMMENT 'CRYPTO|EQUITY|COMMODITY|FOREX|ETF|BOND|FUTURES',
    direction           VARCHAR(8)    NOT NULL COMMENT 'LONG|SHORT',
    source_system       VARCHAR(64)       NULL COMMENT 'emitter that produced the pick',
    strategy            VARCHAR(96)       NULL COMMENT 'strategy name',
    entry_price         DECIMAL(20,8)     NULL,
    take_profit         DECIMAL(20,8)     NULL,
    stop_loss           DECIMAL(20,8)     NULL,
    confidence          DECIMAL(6,4)      NULL COMMENT 'raw model confidence 0-1 (NOT verdict-grade — see audit_criteria_definitions)',
    score               DECIMAL(8,2)      NULL COMMENT 'post-booster smart/elite score',
    -- WHY it was picked --------------------------------------------------------
    rationale_tags      VARCHAR(512)      NULL COMMENT 'comma-separated signal tags, e.g. "cot_extreme,rsi_oversold"',
    rationale_text      TEXT              NULL COMMENT 'human-readable thesis',
    regime_at_entry     VARCHAR(32)       NULL COMMENT 'market regime when emitted',
    -- provenance / integrity ---------------------------------------------------
    signal_timestamp    DATETIME          NULL,
    recorded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_registry_ver VARCHAR(16)       NULL COMMENT 'pf_registry schema_version this row reconciles to',
    leak_corrected      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1 = numbers are post-dedup + post-slippage + leak-checked',
    PRIMARY KEY (id),
    KEY ix_aap_class   (asset_class),
    KEY ix_aap_symbol  (symbol),
    KEY ix_aap_strat   (strategy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Current ACTIVE picks shown on /audit + why each was picked.';

-- ----------------------------------------------------------------------------
-- 2. audit_pick_safety_gates — per-pick gate evaluations (the safety params)
--    One row per (pick, gate). Lets you answer "what did this pick pass?".
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_pick_safety_gates (
    pick_id             VARCHAR(64)   NOT NULL,
    gate_name           VARCHAR(64)   NOT NULL COMMENT 'FK -> audit_criteria_definitions.criterion_key',
    gate_value          DECIMAL(16,6)     NULL COMMENT 'the pick''s value for this gate',
    gate_threshold      DECIMAL(16,6)     NULL COMMENT 'the pass threshold in effect',
    passed              TINYINT(1)    NOT NULL COMMENT '1 = passed, 0 = failed',
    note                VARCHAR(255)      NULL,
    evaluated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pick_id, gate_name),
    KEY ix_apsg_gate (gate_name),
    KEY ix_apsg_pass (passed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Per-pick safety-gate parameters + pass/fail for every active pick.';

-- ----------------------------------------------------------------------------
-- 3. audit_rejected_symbols — universe symbols that did NOT become a pick
--    Answers "which symbols were considered but rejected, and why?".
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_rejected_symbols (
    id                  BIGINT        NOT NULL AUTO_INCREMENT,
    symbol              VARCHAR(32)   NOT NULL,
    asset_class         VARCHAR(16)   NOT NULL,
    scan_cycle_utc      DATETIME      NOT NULL COMMENT 'when this symbol was evaluated',
    reject_stage        VARCHAR(32)   NOT NULL COMMENT 'UNIVERSE|SCANNER|SCORE_FLOOR|SAFETY_GATE|DSR|CONCENTRATION|LEAKAGE|BLOCKED',
    reject_reason       VARCHAR(64)   NOT NULL COMMENT 'FK -> audit_criteria_definitions.criterion_key',
    reject_detail       VARCHAR(255)      NULL COMMENT 'e.g. "elite_score 42 < floor 60", "DSR 0.41 < 0.95"',
    observed_value      DECIMAL(16,6)     NULL,
    required_value      DECIMAL(16,6)     NULL,
    PRIMARY KEY (id),
    KEY ix_ars_symbol (symbol),
    KEY ix_ars_class  (asset_class),
    KEY ix_ars_stage  (reject_stage),
    KEY ix_ars_cycle  (scan_cycle_utc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Symbols evaluated but NOT promoted to active picks, with the exact reason.';

-- ----------------------------------------------------------------------------
-- 4. audit_criteria_definitions — the documentation table.
--    Every score / gate / reject-reason defined ONCE here. Both
--    audit_pick_safety_gates.gate_name and audit_rejected_symbols.reject_reason
--    reference criterion_key.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_criteria_definitions (
    criterion_key       VARCHAR(64)   NOT NULL,
    display_name        VARCHAR(96)   NOT NULL,
    category            VARCHAR(32)   NOT NULL COMMENT 'SCORE|SAFETY_GATE|STAT_TEST|CONCENTRATION|DATA_INTEGRITY',
    definition          TEXT          NOT NULL COMMENT 'what it measures, plain language',
    default_threshold   VARCHAR(64)       NULL COMMENT 'pass condition, e.g. ">=0.95", ">=60", "<0.60"',
    is_verdict_grade    TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '0 = informational only, not used for real-money sizing',
    source_ref          VARCHAR(255)      NULL COMMENT 'code path / doc that defines it',
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (criterion_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Canonical definitions for every score, gate, stat-test and reject reason.';

-- ----------------------------------------------------------------------------
-- 5. audit_pipeline_meta — single-row freshness / provenance stamp
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_pipeline_meta (
    meta_key            VARCHAR(48)   NOT NULL,
    meta_value          VARCHAR(255)  NOT NULL,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (meta_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Pipeline run freshness + which registry version the audit_* tables reflect.';

-- ============================================================================
-- Seed: audit_criteria_definitions — the canonical glossary.
-- INSERT ... ON DUPLICATE KEY UPDATE so re-running the file refreshes defs.
-- ============================================================================
INSERT INTO audit_criteria_definitions
  (criterion_key, display_name, category, definition, default_threshold, is_verdict_grade, source_ref)
VALUES
 ('dsr','Deflated Sharpe Ratio','STAT_TEST',
  'Probability the observed Sharpe is genuine after correcting for multiple-testing (Bailey & Lopez de Prado). nb_trials must reflect the true number of independent strategies tried, NOT 1.',
  '>=0.95',1,'alpha_engine/deflated_sharpe.py'),
 ('pbo','Probability of Backtest Overfitting','STAT_TEST',
  'CSCV estimate of the chance the selected config is overfit. Low = edge likely real.',
  '<=0.05',1,'tools/pbo_cscv.py'),
 ('spa','White Reality Check / Hansen SPA','STAT_TEST',
  'Family-wise test that the best strategy in a set beats a benchmark after multiple-comparison correction.',
  'p<=0.10',1,'tools/whites_reality_check.py (M-065, planned)'),
 ('profit_factor','Profit Factor (net)','SCORE',
  'gross_profit / gross_loss on NET-of-slippage, deduped, policy-clean closed picks. The verdict-grade PF.',
  '>=1.5 (Tier-2)',1,'pf_registry.json::by_asset_class_policy_clean_net'),
 ('win_rate','Win Rate','SCORE',
  'Fraction of resolved picks with net pnl > 0.','>=0.50',1,'pf_registry.json'),
 ('elite_score','Elite Score','SCORE',
  'Composite post-booster score. INFORMATIONAL — discrimination tests show it is near-noise on fresh data; do not size on it alone.',
  '>=60 (production floor)',0,'alpha_engine/score_booster.py'),
 ('confidence','Raw Model Confidence','SCORE',
  'Self-reported model confidence 0-1. NOT a signal-quality axis: confidence >=0.5 is emitted almost only by the ml_enhanced family. Not verdict-grade.',
  'n/a',0,'reports/deep_dive_crypto_ml_enhanced_artifact_2026-05-17.md'),
 ('symbol_concentration','Single-Symbol Concentration','CONCENTRATION',
  'Share of a class''s resolved picks held by its top symbol. Above the cap the class verdict is capped at WATCH — a one-symbol bet is not a class edge.',
  '<0.60',1,'alpha_engine/money_ready_verdict.py MAX_SYMBOL_CONCENTRATION'),
 ('slippage_net','Round-Trip Slippage','DATA_INTEGRITY',
  'Per-class round-trip execution cost deducted from gross pnl to get net pnl. M-069 fixed a 100x units bug here.',
  'per-class bps',1,'alpha_engine/charter_slippage.py'),
 ('dedup','Re-emission Dedup','DATA_INTEGRITY',
  'Collapses duplicate re-emissions of the same signal (key: strategy,symbol,direction,trade_date,~entry_price). ~41% of raw closed picks are duplicates.',
  '1 row per signal',1,'tools/build_pf_registry.py'),
 ('cot_leakage','COT Publication Look-Ahead','DATA_INTEGRITY',
  'COT/commercial-positioning signals that used CFTC data not available at decision time. cot_positioning is leakage-falsified (M-095).',
  'must be lag-corrected',1,'MASTER_ACTION_PLAN_2026-05-15.md M-095'),
 ('blocked_source','Blocked Source / Strategy','SAFETY_GATE',
  'Strategy or source_system in BLOCKED_SOURCE_SYSTEMS / PERMANENTLY_KILLED_STRATEGIES — statistically proven losers or leakage. Excluded from emission AND from verdict aggregates.',
  'not in blocklist',1,'audit_trail/quality_gates.py'),
 ('min_n','Minimum Sample','SAFETY_GATE',
  'Charter floor on resolved-pick count before a class/strategy can carry a real-money verdict.',
  'n>=100 (Tier-2)',1,'docs/PERFORMANCE_CHARTER.md'),
 ('penny_meme_gate','Penny / Meme Class Gate','SAFETY_GATE',
  'Class-wide block of PENNY_STOCK + MEMECOIN asset classes from emission.',
  'class not in {PENNY_STOCK,MEMECOIN}',1,'audit_trail/quality_gates.py')
ON DUPLICATE KEY UPDATE
  display_name=VALUES(display_name), category=VALUES(category),
  definition=VALUES(definition), default_threshold=VALUES(default_threshold),
  is_verdict_grade=VALUES(is_verdict_grade), source_ref=VALUES(source_ref);

-- ============================================================================
-- Example queries (the user-facing "quick summary" the tables exist for)
-- ============================================================================
-- A) Active picks + why, per class:
--   SELECT asset_class, symbol, direction, strategy, score, rationale_tags
--   FROM audit_active_picks ORDER BY asset_class, score DESC;
--
-- B) Why a symbol was rejected:
--   SELECT symbol, reject_stage, reject_reason, reject_detail
--   FROM audit_rejected_symbols WHERE symbol='AAPL' ORDER BY scan_cycle_utc DESC;
--
-- C) Rejection reasons ranked (where is the funnel losing symbols?):
--   SELECT reject_stage, reject_reason, COUNT(*) n
--   FROM audit_rejected_symbols GROUP BY 1,2 ORDER BY n DESC;
--
-- D) A pick's full safety-gate sheet with definitions:
--   SELECT g.gate_name, d.definition, g.gate_value, g.gate_threshold, g.passed
--   FROM audit_pick_safety_gates g
--   JOIN audit_criteria_definitions d ON d.criterion_key = g.gate_name
--   WHERE g.pick_id = ?;
-- ============================================================================
