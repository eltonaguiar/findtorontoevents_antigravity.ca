-- Experiment ledger -- SQLite port of docs/experiment_schema.pg.sql.
--
-- The Postgres original is kept alongside as experiment_schema.pg.sql; it is the
-- one that can actually enforce JSONB / TIMESTAMPTZ. This file exists so the
-- same 12 logical tables can be created with the stdlib alone:
--
--   python -c "import sqlite3,pathlib; db=sqlite3.connect(':memory:'); \
--     db.executescript(pathlib.Path('docs/experiment_schema.sql').read_text()); \
--     print(len([r for r in db.execute(\"select name from sqlite_master where type='table'\")]))"
--
-- Porting rules (mechanical, no schema redesign):
--   UUID -> TEXT, BIGSERIAL -> INTEGER PRIMARY KEY, TIMESTAMPTZ -> TEXT,
--   JSONB -> TEXT, DOUBLE PRECISION -> REAL, BIGINT -> INTEGER,
--   DEFAULT now() -> DEFAULT CURRENT_TIMESTAMP.
--
-- Two deliberate deviations from the Postgres original:
--   1. CREATE TABLE IF NOT EXISTS, so tools/experiment_tracker.py init_db() stays
--      idempotent (the tracker used to declare its own IF NOT EXISTS literal).
--   2. NO AUTOINCREMENT. "INTEGER PRIMARY KEY AUTOINCREMENT" makes SQLite create
--      an implicit sqlite_sequence table, which would silently make the count
--      above 13 instead of 12. Plain INTEGER PRIMARY KEY already auto-assigns
--      rowids; AUTOINCREMENT only adds a monotonicity guarantee this ledger does
--      not need (rows are append-only and never deleted).
--
-- Invariants enforced by the writer, not the DB:
--   * runs rows are immutable after status != 'running'
--   * fills/orders are append-only (no UPDATE/DELETE)
--   * metrics.scope='oos' only from purged/CPCV paths
--   * every run must reference a data_snapshot_id whose hash is recorded

CREATE TABLE IF NOT EXISTS runs (
  run_id           TEXT PRIMARY KEY,
  run_type         TEXT NOT NULL CHECK (run_type IN ('backtest','paper','live','monte_carlo')),
  parent_run_id    TEXT REFERENCES runs(run_id),
  strategy_name    TEXT NOT NULL,
  strategy_version TEXT NOT NULL,
  git_commit       TEXT NOT NULL,
  config_hash      TEXT NOT NULL,
  data_snapshot_id TEXT NOT NULL,
  seed             INTEGER,
  start_ts         TEXT NOT NULL,
  end_ts           TEXT NOT NULL,
  status           TEXT NOT NULL CHECK (status IN ('running','ok','failed','aborted')),
  notes            TEXT
);

CREATE TABLE IF NOT EXISTS run_params (
  run_id      TEXT REFERENCES runs(run_id),
  param_name  TEXT,
  param_value TEXT,
  param_type  TEXT,
  PRIMARY KEY (run_id, param_name)
);

CREATE TABLE IF NOT EXISTS market_events (
  event_id   INTEGER PRIMARY KEY,
  run_id     TEXT REFERENCES runs(run_id),
  ts         TEXT NOT NULL,
  symbol     TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('bar','tick','news','corporate_action')),
  payload    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
  signal_id     INTEGER PRIMARY KEY,
  run_id        TEXT REFERENCES runs(run_id),
  ts            TEXT NOT NULL,
  symbol        TEXT NOT NULL,
  direction     TEXT NOT NULL CHECK (direction IN ('long','short','flat')),
  strength      REAL,
  target_weight REAL,
  reason        TEXT,
  features      TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  order_id         TEXT PRIMARY KEY,
  run_id           TEXT REFERENCES runs(run_id),
  parent_signal_id INTEGER REFERENCES signals(signal_id),
  ts_created       TEXT NOT NULL,
  symbol           TEXT NOT NULL,
  side             TEXT NOT NULL CHECK (side IN ('buy','sell')),
  qty              REAL NOT NULL,
  order_type       TEXT NOT NULL CHECK (order_type IN ('market','limit','stop','stop_limit')),
  limit_price      REAL,
  stop_price       REAL,
  time_in_force    TEXT,
  status           TEXT NOT NULL,
  reject_reason    TEXT
);

CREATE TABLE IF NOT EXISTS fills (
  fill_id        INTEGER PRIMARY KEY,
  run_id         TEXT REFERENCES runs(run_id),
  order_id       TEXT REFERENCES orders(order_id),
  ts_filled      TEXT NOT NULL,
  symbol         TEXT NOT NULL,
  side           TEXT NOT NULL,
  qty            REAL NOT NULL,
  price          REAL NOT NULL,
  fee            REAL NOT NULL DEFAULT 0,
  slippage       REAL NOT NULL DEFAULT 0,
  liquidity_flag TEXT,
  venue          TEXT
);

CREATE TABLE IF NOT EXISTS positions (
  run_id        TEXT REFERENCES runs(run_id),
  ts            TEXT NOT NULL,
  symbol        TEXT NOT NULL,
  qty           REAL NOT NULL,
  avg_price     REAL NOT NULL,
  market_price  REAL,
  unrealized_pnl REAL,
  realized_pnl  REAL,
  exposure      REAL,
  PRIMARY KEY (run_id, ts, symbol)
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  run_id         TEXT REFERENCES runs(run_id),
  ts             TEXT NOT NULL,
  cash           REAL NOT NULL,
  equity         REAL NOT NULL,
  gross_exposure REAL,
  net_exposure   REAL,
  leverage       REAL,
  margin_used    REAL,
  drawdown       REAL,
  daily_pnl      REAL,
  PRIMARY KEY (run_id, ts)
);

CREATE TABLE IF NOT EXISTS risk_events (
  risk_event_id  INTEGER PRIMARY KEY,
  run_id         TEXT REFERENCES runs(run_id),
  ts             TEXT NOT NULL,
  type           TEXT NOT NULL,
  threshold      REAL,
  observed_value REAL,
  action_taken   TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
  run_id      TEXT REFERENCES runs(run_id),
  metric_name TEXT NOT NULL,
  value       REAL,
  scope       TEXT NOT NULL CHECK (scope IN ('overall','is','oos','window','regime','mc')),
  window_id   TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (run_id, metric_name, scope, window_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
  run_id        TEXT REFERENCES runs(run_id),
  artifact_type TEXT NOT NULL,
  path_or_uri   TEXT NOT NULL,
  checksum      TEXT NOT NULL,
  created_ts    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, artifact_type, path_or_uri)
);

CREATE TABLE IF NOT EXISTS mc_runs (
  run_id         TEXT PRIMARY KEY REFERENCES runs(run_id),
  parent_run_id  TEXT REFERENCES runs(run_id),
  n_simulations  INTEGER NOT NULL,
  block_size     INTEGER,
  ruin_threshold REAL,
  ruin_prob      REAL,
  mdd_p05        REAL,
  mdd_p50        REAL,
  mdd_p95        REAL
);
