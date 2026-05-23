-- Central Audit Trail Schema
-- version: 1.0
-- Engine: SQLite (designed for MySQL migration)
-- Date: 2026-03-04

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1.0');

CREATE TABLE IF NOT EXISTS aggregation_runs (
    run_id              TEXT PRIMARY KEY,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    status              TEXT NOT NULL DEFAULT 'RUNNING',
    systems_loaded      INTEGER DEFAULT 0,
    raw_picks_count     INTEGER DEFAULT 0,
    consensus_count     INTEGER DEFAULT 0,
    regime_data         TEXT,
    portfolio_drawdown  REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS raw_picks (
    id                  TEXT PRIMARY KEY,
    aggregation_run_id  TEXT NOT NULL REFERENCES aggregation_runs(run_id),
    source_system       TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    asset_class         TEXT NOT NULL,
    direction           TEXT NOT NULL,
    entry_price         REAL,
    take_profit         REAL,
    stop_loss           REAL,
    risk_reward         REAL,
    confidence          REAL,
    strategy            TEXT,
    raw_payload         TEXT,
    signal_timestamp    TEXT,
    recorded_at         TEXT NOT NULL,
    dedup_hash          TEXT UNIQUE,
    was_stale           INTEGER DEFAULT 0,
    was_banned          INTEGER DEFAULT 0,
    was_demoted         INTEGER DEFAULT 0,
    was_wr_suppressed   INTEGER DEFAULT 0,
    created_by          TEXT DEFAULT 'aggregator',
    -- Enrichment signal columns (populated from enrichment_pipeline.py outputs)
    enrichment_grade        TEXT,      -- STRONG_ALIGNMENT / MODERATE_ALIGNMENT / STRONG_CONTRARY / NEUTRAL_CONDITIONS
    enrichment_alignment    INTEGER,   -- count of signals aligned with pick direction
    enrichment_contrary     INTEGER,   -- count of contrary signals
    enrichment_rsi          REAL,      -- rsi_14_1h
    enrichment_fear_greed   INTEGER,   -- fear_greed_index 0-100
    enrichment_funding_rate REAL,      -- avg_funding_8h across exchanges
    enrichment_nvt_ratio    REAL,      -- Messari NVT ratio
    enrichment_nvt_signal   TEXT,      -- OVERVALUED / ELEVATED / FAIR / UNDERVALUED
    enrichment_weekly_mom   TEXT,      -- Coinpaprika 7d momentum classification
    enrichment_pct_7d       REAL,      -- 7-day price change %
    enrichment_btc_mempool  TEXT,      -- btc_demand_signal (BTC picks only)
    enrichment_btc_fee_sat  INTEGER,   -- BTC fastest fee rate sat/vB
    enrichment_defi_cex_sig TEXT,      -- 1inch DEX/CEX signal
    enrichment_defi_spread  REAL,      -- defi_cex_spread_pct
    enrichment_dex_liq      TEXT,      -- 0x liquidity signal
    enrichment_active_addrs INTEGER,   -- Messari active addresses 24h
    enrichment_data         TEXT       -- full enrichment JSON blob
);

CREATE INDEX IF NOT EXISTS idx_raw_run    ON raw_picks(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_raw_sys    ON raw_picks(source_system);
CREATE INDEX IF NOT EXISTS idx_raw_sym    ON raw_picks(symbol);
CREATE INDEX IF NOT EXISTS idx_raw_ts     ON raw_picks(signal_timestamp);

CREATE TABLE IF NOT EXISTS consensus_picks (
    id                  TEXT PRIMARY KEY,
    aggregation_run_id  TEXT NOT NULL REFERENCES aggregation_runs(run_id),
    symbol              TEXT NOT NULL,
    asset_class         TEXT NOT NULL,
    direction           TEXT NOT NULL,
    entry_price         REAL,
    take_profit         REAL,
    stop_loss           REAL,
    risk_reward         REAL,
    confidence          REAL,
    agreement_count     INTEGER,
    source_systems      TEXT,
    source_strategies   TEXT,
    system_confidences  TEXT,
    consensus_tier      TEXT,
    classification      TEXT,
    regime_data         TEXT,
    discord_channel     TEXT,
    discord_message_id  TEXT,
    status              TEXT DEFAULT 'OPEN',
    exit_price          REAL,
    exit_reason         TEXT,
    pnl_pct             REAL,
    slippage_estimate   REAL,
    generated_at        TEXT NOT NULL,
    closed_at           TEXT,
    UNIQUE(symbol, direction, entry_price, generated_at)
);

CREATE INDEX IF NOT EXISTS idx_cons_run    ON consensus_picks(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_cons_sym    ON consensus_picks(symbol);
CREATE INDEX IF NOT EXISTS idx_cons_status ON consensus_picks(status);

CREATE TABLE IF NOT EXISTS audit_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT NOT NULL,
    pick_id             TEXT,
    aggregation_run_id  TEXT,
    symbol              TEXT,
    payload             TEXT,
    origin              TEXT DEFAULT 'aggregator',
    timestamp           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evt_run   ON audit_events(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_evt_pick  ON audit_events(pick_id);
CREATE INDEX IF NOT EXISTS idx_evt_type  ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_evt_sym   ON audit_events(symbol);

CREATE TABLE IF NOT EXISTS filter_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregation_run_id  TEXT,
    raw_pick_id         TEXT,
    symbol              TEXT,
    direction           TEXT,
    source_system       TEXT,
    filter_reason       TEXT NOT NULL,
    details             TEXT,
    timestamp           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_filt_run    ON filter_log(aggregation_run_id);
CREATE INDEX IF NOT EXISTS idx_filt_reason ON filter_log(filter_reason);
CREATE INDEX IF NOT EXISTS idx_filt_sym    ON filter_log(symbol);

CREATE TABLE IF NOT EXISTS strategy_stats (
    strategy        TEXT NOT NULL,
    source_system   TEXT NOT NULL,
    asset_class     TEXT,
    total_picks     INTEGER DEFAULT 0,
    consensus_picks INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    avg_pnl_pct     REAL DEFAULT 0.0,
    best_pnl        REAL DEFAULT 0.0,
    worst_pnl       REAL DEFAULT 0.0,
    avg_risk_reward REAL DEFAULT 0.0,
    last_updated    TEXT,
    PRIMARY KEY (strategy, source_system)
);

CREATE INDEX IF NOT EXISTS idx_stats_sys ON strategy_stats(source_system);
CREATE INDEX IF NOT EXISTS idx_stats_ac  ON strategy_stats(asset_class);

-- ── Backtesting Data Tables ──

CREATE TABLE IF NOT EXISTS bt_backtest_runs (
    id                  TEXT PRIMARY KEY,
    source_db           TEXT NOT NULL,
    source_table        TEXT NOT NULL DEFAULT '',
    strategy            TEXT NOT NULL,
    symbol              TEXT NOT NULL DEFAULT 'BTC/USDT',
    asset_class         TEXT NOT NULL DEFAULT 'CRYPTO',
    total_trades        INTEGER DEFAULT 0,
    wins                INTEGER DEFAULT 0,
    losses              INTEGER DEFAULT 0,
    win_rate            REAL DEFAULT 0.0,
    profit_factor       REAL DEFAULT 0.0,
    total_return        REAL DEFAULT 0.0,
    sharpe              REAL DEFAULT 0.0,
    max_drawdown        REAL DEFAULT 0.0,
    imported_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_btr_strat ON bt_backtest_runs(strategy);
CREATE INDEX IF NOT EXISTS idx_btr_asset ON bt_backtest_runs(asset_class);

CREATE TABLE IF NOT EXISTS bt_backtest_trades (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_run_id     TEXT REFERENCES bt_backtest_runs(id),
    source_db           TEXT NOT NULL,
    source_table        TEXT NOT NULL DEFAULT '',
    symbol              TEXT NOT NULL,
    asset_class         TEXT NOT NULL DEFAULT 'CRYPTO',
    direction           TEXT,
    strategy            TEXT NOT NULL,
    entry_price         REAL,
    exit_price          REAL,
    take_profit         REAL,
    stop_loss           REAL,
    entry_time          TEXT,
    exit_time           TEXT,
    pnl_pct             REAL,
    status              TEXT,
    confidence          REAL,
    raw_data            TEXT,
    imported_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_btt_sym   ON bt_backtest_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_btt_asset ON bt_backtest_trades(asset_class);
CREATE INDEX IF NOT EXISTS idx_btt_strat ON bt_backtest_trades(strategy);
CREATE INDEX IF NOT EXISTS idx_btt_run   ON bt_backtest_trades(backtest_run_id);

-- ── Schema v2: ML Score + Feature Persistence ──
-- Version: 2.0 (2026-04-22)
-- These columns are appended to raw_picks via pick_feature_store.run_sqlite_migration()
-- (idempotent ALTER TABLE — safe to apply multiple times).
-- New tables added below.

-- ── Symbol × Strategy Win-Rate Table ──
CREATE TABLE IF NOT EXISTS symbol_strategy_stats (
    symbol          TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    source_system   TEXT NOT NULL DEFAULT '',
    asset_class     TEXT,
    direction       TEXT DEFAULT 'BOTH',
    total_picks     INTEGER DEFAULT 0,
    wins            INTEGER DEFAULT 0,
    losses          INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    avg_pnl_pct     REAL DEFAULT 0.0,
    best_pnl        REAL DEFAULT 0.0,
    worst_pnl       REAL DEFAULT 0.0,
    avg_rr          REAL DEFAULT 0.0,
    avg_ml_score    REAL,
    avg_elite_score REAL,
    avg_smart_score REAL,
    avg_rsi         REAL,
    avg_volume_ratio REAL,
    last_updated    TEXT,
    PRIMARY KEY (symbol, strategy, source_system, direction)
);

CREATE INDEX IF NOT EXISTS idx_sss_sym   ON symbol_strategy_stats(symbol);
CREATE INDEX IF NOT EXISTS idx_sss_strat ON symbol_strategy_stats(strategy);
CREATE INDEX IF NOT EXISTS idx_sss_wr    ON symbol_strategy_stats(win_rate);

-- ── Feature × Outcome Edge Snapshot Table ──
CREATE TABLE IF NOT EXISTS feature_edge_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_at     TEXT NOT NULL,
    feature_name    TEXT NOT NULL,
    bucket_label    TEXT NOT NULL,
    bucket_low      REAL,
    bucket_high     REAL,
    n_picks         INTEGER DEFAULT 0,
    n_wins          INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    avg_pnl_pct     REAL DEFAULT 0.0,
    edge_score      REAL DEFAULT 0.0,
    asset_class     TEXT DEFAULT 'ALL',
    direction       TEXT DEFAULT 'ALL',
    UNIQUE(computed_at, feature_name, bucket_label, asset_class, direction)
);

CREATE INDEX IF NOT EXISTS idx_fes_feat ON feature_edge_snapshots(feature_name);
CREATE INDEX IF NOT EXISTS idx_fes_date ON feature_edge_snapshots(computed_at);
CREATE INDEX IF NOT EXISTS idx_fes_edge ON feature_edge_snapshots(edge_score);
