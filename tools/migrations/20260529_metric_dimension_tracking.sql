-- ============================================================
-- COMPREHENSIVE METRIC DIMENSION TRACKING
-- findtorontoevents.ca/audit
-- ============================================================
-- Purpose: Track every button, filter, nav-surface, metric tag,
-- and strategy viability badge across the audit dashboard.
-- Every dimension is queryable for statistically-valid edge
-- discovery across timeframes.
--
-- Database: ejaguiar1_stocks (primary)
-- Created:  2026-05-29
-- Author:   Claude Opus 4.7
-- ============================================================

-- ============================================================
-- 1. STRATEGY_SUMMARY — canonical strategy catalog per class
-- ============================================================
-- Documents ALL strategies per asset class with viability badges
-- from the dashboard (Fwd Validated, A-Viable, Probation, etc.)
-- ============================================================
CREATE TABLE IF NOT EXISTS strategy_summary (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name       VARCHAR(128) NOT NULL COMMENT 'Canonical key (e.g. rs-breakout-scout)',
    display_name        VARCHAR(256) COMMENT 'Display name on dashboard (e.g. rs-breakout-scout)',
    asset_class         VARCHAR(32) NOT NULL,
    source_module       VARCHAR(128) COMMENT 'Python file or system (e.g. kimi, inverse mutations)',
    strategy_type       VARCHAR(64) COMMENT 'Trend/MR/Carry/Breakout/Momentum/etc.',
    description         TEXT,
    timeframes          JSON COMMENT 'Array of timeframes: ["INTRA","SWING","POSITION"]',

    -- Viability badges (from Strategy column screenshots)
    fwd_validated       TINYINT DEFAULT 0 COMMENT 'Fwd Validated badge (green)',
    viable_pct          DECIMAL(5,2) COMMENT 'A-Viable badge (e.g. 39)',
    probation_pct       DECIMAL(5,2) COMMENT 'B-Probation badge (e.g. 15)',
    recovery_pct        DECIMAL(5,2) COMMENT 'C-Recovery badge (e.g. 5)',
    eliminated_pct      DECIMAL(5,2) COMMENT 'Eliminated badge (e.g. 0)',
    kimi_solo           TINYINT DEFAULT 0 COMMENT 'KIMI Solo badge (orange)',
    multi_agree         TINYINT DEFAULT 0 COMMENT 'Multi-Agree badge (blue)',

    -- Score dimensions (from Score column screenshots)
    avg_elite_score     DECIMAL(5,2),
    has_surfer_badge    TINYINT DEFAULT 0 COMMENT 'SURFER pill',
    has_safe_badge      TINYINT DEFAULT 0 COMMENT 'SAFE pill',
    avg_composite_ref   VARCHAR(16) COMMENT 'Average C:xx ref (e.g. C:60)',

    -- Performance (computed per window from pick_dimension_snapshot)
    window_7d_wr        DECIMAL(5,4),
    window_7d_pf        DECIMAL(10,4),
    window_14d_wr       DECIMAL(5,4),
    window_14d_pf       DECIMAL(10,4),
    window_30d_wr       DECIMAL(5,4),
    window_30d_pf       DECIMAL(10,4),
    window_48h_wr       DECIMAL(5,4),
    window_48h_pf       DECIMAL(10,4),
    window_all_wr       DECIMAL(5,4),
    window_all_pf       DECIMAL(10,4),

    -- Statistical validation
    n_total             INT DEFAULT 0 COMMENT 'All picks (active + resolved)',
    n_resolved          INT DEFAULT 0 COMMENT 'Resolved picks only',
    n_active            INT DEFAULT 0 COMMENT 'Active/open picks',
    dsr                 DECIMAL(6,4) COMMENT 'Deflated Sharpe Ratio',
    pbo                 DECIMAL(5,4) COMMENT 'Probability of Backtest Overfitting',
    wfe                 DECIMAL(5,4) COMMENT 'Walk-Forward Efficiency',
    bonferroni_survivor TINYINT DEFAULT 0 COMMENT 'Survived Bonferroni correction',

    -- Sizing status
    sizing_status       ENUM('shadow','probation','tier3','tier2','tier1','demoted','killed') DEFAULT 'shadow',
    sizing_pct          DECIMAL(5,2) COMMENT 'Current position sizing weight %',

    -- Metadata
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_verified_at    DATETIME COMMENT 'Last manual verification timestamp (EST)',

    UNIQUE KEY uk_strategy_class (strategy_name, asset_class),
    KEY idx_asset_class (asset_class),
    KEY idx_sizing_status (sizing_status),
    KEY idx_viable_pct (viable_pct),
    KEY idx_fwd_validated (fwd_validated),
    KEY idx_bonferroni (bonferroni_survivor),
    KEY idx_avg_score (avg_elite_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Canonical strategy catalog per asset class with viability badges and performance';


-- ============================================================
-- 2. METRIC_DIMENSIONS — dimension dictionary
-- ============================================================
-- Stores every discrete dimension value that appears as a pill/badge
-- on the dashboard. This is the dimension dictionary for edge
-- discovery: Score sub-tags, Trust ranges, AGV ranges, Regime labels,
-- Edge track tags, Strategy viability badges.
-- ============================================================
CREATE TABLE IF NOT EXISTS metric_dimensions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    dimension_group ENUM('score','trust','agv','regime','edge','strategy_badge','timeframe','direction','grade','composite_ref') NOT NULL,
    dimension_value VARCHAR(64) NOT NULL COMMENT 'The value (e.g. SURFER, C:60, B, Fwd Validated, BEAR)',
    description     VARCHAR(256),
    numeric_floor   DECIMAL(10,4) COMMENT 'Min numeric value for this dimension',
    numeric_ceil    DECIMAL(10,4) COMMENT 'Max numeric value for this dimension',

    -- Edge stats computed from pick_dimension_snapshot
    n_picks         INT DEFAULT 0,
    n_resolved      INT DEFAULT 0,
    n_wins          INT DEFAULT 0,
    n_losses        INT DEFAULT 0,
    win_rate        DECIMAL(5,4),
    profit_factor   DECIMAL(10,4),
    avg_pnl_pct     DECIMAL(10,4),
    sharpe          DECIMAL(10,4),
    dsr             DECIMAL(6,4),

    -- Per-timeframe stats
    window_7d_wr    DECIMAL(5,4),
    window_7d_pf    DECIMAL(10,4),
    window_7d_n     INT DEFAULT 0,
    window_14d_wr   DECIMAL(5,4),
    window_14d_pf   DECIMAL(10,4),
    window_14d_n    INT DEFAULT 0,
    window_30d_wr   DECIMAL(5,4),
    window_30d_pf   DECIMAL(10,4),
    window_30d_n    INT DEFAULT 0,

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_dim_group_value (dimension_group, dimension_value),
    KEY idx_dim_group (dimension_group),
    KEY idx_win_rate (win_rate),
    KEY idx_pf (profit_factor),
    KEY idx_ds_r (dsr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimension dictionary for Score/Trust/AGV/Edge/Strategy sub-tags with edge stats';


-- ============================================================
-- 3. PICK_DIMENSION_SNAPSHOT — per-pick dimension capture
-- ============================================================
-- Captures every dimension value for each pick at pick time.
-- Enables queries like:
--   "picks with elite_score>=60 AND trust>=5 AND regime=BEAR AND fwd_validated=1"
-- for edge discovery across any timeframe.
-- ============================================================
CREATE TABLE IF NOT EXISTS pick_dimension_snapshot (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    pick_id             BIGINT NOT NULL COMMENT 'Foreign key to picks.id or trading_picks.id',
    pick_uuid           VARCHAR(64) COMMENT 'Pick unique identifier from source system',
    symbol              VARCHAR(32) NOT NULL,
    asset_class         VARCHAR(32),
    direction           VARCHAR(8) COMMENT 'LONG/SHORT',
    strategy            VARCHAR(128),
    source_system       VARCHAR(64) COMMENT 'Source system (e.g. kimi, inverse mutations)',
    timeframe           VARCHAR(16) COMMENT 'INTRA/SWING/POSITION',

    -- ============ SCORE DIMENSIONS ============
    -- From screenshot: 61 with ↓, grade B, SURFER pill, SAFE pill, C:60
    elite_score         INT COMMENT 'Main score number (61, 58, 52, 70)',
    score_grade         CHAR(1) COMMENT 'Grade letter (A, B, C)',
    score_grade_numeric DECIMAL(5,2) COMMENT 'Grade numeric (60 for C:60)',
    score_surfer        TINYINT DEFAULT 0 COMMENT 'SURFER pill present',
    score_safe          TINYINT DEFAULT 0 COMMENT 'SAFE pill present',
    score_composite_ref VARCHAR(32) COMMENT 'Composite ref (C:60, C:72, C:51)',
    score_declining     TINYINT DEFAULT 0 COMMENT 'Score ↓ arrow',
    score_rising        TINYINT DEFAULT 0 COMMENT 'Score ↑ arrow',
    score_magnifier     TINYINT DEFAULT 0 COMMENT 'Score 🔍 indicator',
    score_confidence    DECIMAL(5,4),

    -- ============ TRUST DIMENSIONS ============
    trust_score         DECIMAL(5,2) COMMENT 'Trust numeric (5, 3.7)',
    trust_tier          VARCHAR(32) COMMENT 'PROVEN/DEVELOPING/WATCH/SANDBOX/PROBATION',
    trust_color         VARCHAR(16) COMMENT 'Visual color indicator',

    -- ============ AGV DIMENSIONS ============
    agv_score           INT COMMENT 'AGV numeric (66, 65, 70)',
    agv_tier            VARCHAR(32) COMMENT 'AGV classification letter',

    -- ============ REGIME DIMENSIONS ============
    regime_label        VARCHAR(32) COMMENT 'BEAR/BULL/CHOP/ACCUMULATION/DISTRIBUTION',
    regime_check        TINYINT DEFAULT 0 COMMENT 'Regime checkmark (✓)',
    regime_x            TINYINT DEFAULT 0 COMMENT 'Regime X mark',
    regime_demoted      TINYINT DEFAULT 0 COMMENT 'REGIME-DEMODTED badge',

    -- ============ EDGE DIMENSIONS ============
    edge_track_pct      DECIMAL(5,2) COMMENT '+3 pair closes (89%)',
    fwd_wr_pct          DECIMAL(5,2) COMMENT 'Forward WR % (72%, 0%)',
    fwd_n               INT COMMENT 'Forward N count (43, 0)',
    htf_trend           ENUM('UP','DOWN','FLAT') COMMENT 'Higher time frame (↑/↓/—)',
    strong_signal       TINYINT DEFAULT 0 COMMENT 'STRONG column indicator',

    -- ============ STRATEGY VIABILITY BADGES ============
    -- From screenshot: Fwd Validated, A-Viable 39%, B-Probation 15%,
    -- C-Recovery 5%, Eliminated 0%, Multi-Agree, KIMI Solo
    strat_fwd_validated TINYINT DEFAULT 0,
    strat_viable_pct    DECIMAL(5,2),
    strat_probation_pct DECIMAL(5,2),
    strat_recovery_pct  DECIMAL(5,2),
    strat_eliminated_pct DECIMAL(5,2),
    strat_kimi_solo     TINYINT DEFAULT 0,
    strat_multi_agree   TINYINT DEFAULT 0,

    -- ============ OUTCOME (for edge computation) ============
    status              VARCHAR(16),
    pnl_pct             DECIMAL(10,4),
    pnl_usd             DECIMAL(14,4),
    entry_price         DECIMAL(14,6),
    current_price       DECIMAL(14,6),
    tp_price            DECIMAL(14,6),
    sl_price            DECIMAL(14,6),
    unrealized_pnl_pct  DECIMAL(10,4),
    resolved_at         DATETIME,
    submitted_at        DATETIME,

    -- ============ METADATA ============
    captured_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_version    VARCHAR(32) COMMENT 'Version of dashboard schema',
    source_system       VARCHAR(64),

    KEY idx_pick_id (pick_id),
    KEY idx_symbol (symbol),
    KEY idx_strategy (strategy),
    KEY idx_status (status),
    KEY idx_elite_score (elite_score),
    KEY idx_trust_score (trust_score),
    KEY idx_agv_score (agv_score),
    KEY idx_regime (regime_label),
    KEY idx_timeframe (timeframe),
    KEY idx_asset_class (asset_class),
    KEY idx_fwd_validated (strat_fwd_validated),
    KEY idx_pnl (pnl_pct),
    KEY idx_captured (captured_at),
    KEY idx_submitted (submitted_at),
    -- Composite indexes for common edge queries
    KEY idx_score_trust_regime (elite_score, trust_score, regime_label),
    KEY idx_score_strat (elite_score, strat_fwd_validated),
    KEY idx_class_timeframe (asset_class, timeframe, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Per-pick dimension snapshot enabling edge discovery across all metric combinations';


-- ============================================================
-- 4. PICK_FUNNEL_VIEWS — performance by nav-surface/button
-- ============================================================
-- Every button/tab on the dashboard is a "view" with its own
-- filter criteria. This table tracks performance per view,
-- per asset class, per timeframe.
-- Views: Smart Picks button, Smart Picks tab, High Conviction,
-- Money Ready, Verified Alpha, ELITE, US Equity tab (long-term
-- value / swing plays / closed holds), CRYPTO tab, FOREX tab, etc.
-- ============================================================
CREATE TABLE IF NOT EXISTS pick_funnel_views (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    view_key                VARCHAR(64) NOT NULL COMMENT 'Canonical key (smart_picks_button, smart_picks_tab, high_conviction, money_ready, verified_alpha, elite, us_equity_tab, us_equity_ltv, us_equity_swing, us_equity_closed)',
    display_name            VARCHAR(128) NOT NULL,
    view_type               ENUM('button','tab','nav_surface','filter_preset') NOT NULL,
    view_group              VARCHAR(64) COMMENT 'Parent group (e.g. Smart Picks, US Equity)',

    asset_class             VARCHAR(32) COMMENT 'NULL = cross-asset',
    time_window             VARCHAR(16) COMMENT '7d/14d/30d/48h/90d/all',

    -- Filter criteria (what this view requires)
    filter_json             JSON COMMENT 'JSON of filter rules',
    min_elite_score         INT,
    min_confidence          DECIMAL(5,4),
    min_trust_score         DECIMAL(5,2),
    require_fwd_validated   TINYINT DEFAULT 0,
    require_multi_agree     TINYINT DEFAULT 0,
    regime_filter           VARCHAR(32) COMMENT 'Required regime (if any)',
    timeframe_filter        VARCHAR(16),
    direction_filter        VARCHAR(8),

    -- Performance metrics
    n_total                 INT DEFAULT 0,
    n_resolved              INT DEFAULT 0,
    n_active                INT DEFAULT 0,
    n_wins                  INT DEFAULT 0,
    n_losses                INT DEFAULT 0,
    win_rate                DECIMAL(5,4),
    profit_factor           DECIMAL(10,4),
    avg_pnl_pct             DECIMAL(10,4),
    avg_unrealized_pct      DECIMAL(10,4),
    sharpe                  DECIMAL(10,4),

    -- Source reconciliation
    source_file             VARCHAR(256) COMMENT 'Which JSON/DB query produces this view',
    source_table            VARCHAR(128) COMMENT 'DB table backing this view',
    generated_at            DATETIME DEFAULT CURRENT_TIMESTAMP,

    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_view_class_window (view_key, asset_class, time_window),
    KEY idx_view_type (view_type),
    KEY idx_win_rate (win_rate),
    KEY idx_asset_class (asset_class),
    KEY idx_time_window (time_window)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Performance by nav-surface/button (Smart Picks, High Conviction, etc.) per asset class per timeframe';


-- ============================================================
-- 5. EDGE_DISCOVERY — pre-computed edge significance
-- ============================================================
-- For every dimension combination that has enough resolved picks,
-- compute the statistical significance of the edge.
-- This is what the dashboard queries for "what links to edge?"
-- ============================================================
CREATE TABLE IF NOT EXISTS edge_discovery (
    id                      BIGINT AUTO_INCREMENT PRIMARY KEY,
    edge_key                VARCHAR(512) NOT NULL COMMENT 'Canonical key: elite_score_gte_60+trust_gte_5+regime_bear+fwd_validated',
    edge_label              VARCHAR(256) COMMENT 'Human-readable label',
    dimension_detail        JSON COMMENT 'JSON of the dimension filters',

    asset_class             VARCHAR(32),
    time_window             VARCHAR(16) COMMENT '7d/14d/30d/48h/90d/all',
    strategy                VARCHAR(128),

    -- Sample size
    n_total                 INT DEFAULT 0,
    n_resolved              INT DEFAULT 0,
    n_active                INT DEFAULT 0,
    min_n_threshold         INT DEFAULT 30,

    -- Edge metrics
    win_rate                DECIMAL(5,4),
    profit_factor           DECIMAL(10,4),
    avg_pnl_pct             DECIMAL(10,4),
    sharpe                  DECIMAL(10,4),
    dsr                     DECIMAL(6,4),
    pbo                     DECIMAL(5,4),
    wfe                     DECIMAL(5,4),

    -- Statistical significance
    z_score                 DECIMAL(10,4) COMMENT 'Z-score for WR deviation from 50%',
    p_value                 DECIMAL(10,6) COMMENT 'P-value for edge significance',
    bonferroni_adjusted_p   DECIMAL(10,6) COMMENT 'Bonferroni-adjusted p-value',
    survived_bonferroni     TINYINT DEFAULT 0 COMMENT 'TRUE if p_adj < 0.05 / num_tests',

    -- Verdict
    edge_verdict            ENUM('STRONG','MODERATE','WEAK','NONE','INVERTED') COMMENT 'Edge classification',
    recommendation          VARCHAR(256) COMMENT 'SIZABLE / WATCH / AVOID / KILL',

    -- Comparison to baseline (same class/window, no dimension filter)
    baseline_wr             DECIMAL(5,4) COMMENT 'WR for same asset class / window without filters',
    baseline_pf             DECIMAL(10,4),
    wr_lift_pp              DECIMAL(5,4) COMMENT 'WR improvement vs baseline in pp',
    pf_ratio                DECIMAL(10,4) COMMENT 'PF / baseline_PF',

    generated_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_edge_key (edge_key, asset_class, time_window, strategy),
    KEY idx_edge_verdict (edge_verdict),
    KEY idx_bonferroni (survived_bonferroni),
    KEY idx_win_rate (win_rate),
    KEY idx_asset_class (asset_class),
    KEY idx_time_window (time_window),
    KEY idx_strategy (strategy)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Pre-computed edge significance for dimension combinations across asset classes and timeframes';


-- ============================================================
-- 6. VIEW_DEFINITION_CATALOG — documents every button/filter
-- ============================================================
-- Human-readable catalog of every view/button on the dashboard
-- with its filter rules, data source, and purpose.
-- ============================================================
CREATE TABLE IF NOT EXISTS view_definition_catalog (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    view_key            VARCHAR(64) NOT NULL UNIQUE COMMENT 'Canonical key',
    display_name        VARCHAR(128) NOT NULL,
    view_type           VARCHAR(32),
    parent_section      VARCHAR(64) COMMENT 'Parent nav section',
    description         TEXT,
    filter_rules        JSON COMMENT 'Human-readable filter rules',
    sql_query           TEXT COMMENT 'The query that produces this view',
    data_source         VARCHAR(128) COMMENT 'Which table/file this reads from',
    refresh_schedule    VARCHAR(64) COMMENT 'e.g. hourly, daily',
    requires_db         TINYINT DEFAULT 0,
    is_live             TINYINT DEFAULT 0 COMMENT 'Currently live on dashboard',

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_view_type (view_type),
    KEY idx_is_live (is_live)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Human-readable catalog of every dashboard view/button with filter definitions';
