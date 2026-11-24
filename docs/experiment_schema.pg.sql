-- Experiment ledger (Postgres-flavoured). Append-only event log; never UPDATE fills.
-- Every run is one immutable row; artifacts are content-addressed.

CREATE TABLE runs (
  run_id          UUID PRIMARY KEY,
  run_type        TEXT NOT NULL CHECK (run_type IN ('backtest','paper','live','monte_carlo')),
  parent_run_id   UUID REFERENCES runs(run_id),
  strategy_name   TEXT NOT NULL,
  strategy_version TEXT NOT NULL,
  git_commit      TEXT NOT NULL,
  config_hash     TEXT NOT NULL,
  data_snapshot_id TEXT NOT NULL,
  seed            BIGINT,
  start_ts        TIMESTAMPTZ NOT NULL,
  end_ts          TIMESTAMPTZ NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('running','ok','failed','aborted')),
  notes           TEXT
);

CREATE TABLE run_params (
  run_id     UUID REFERENCES runs(run_id),
  param_name TEXT,
  param_value TEXT,
  param_type TEXT,
  PRIMARY KEY (run_id, param_name)
);

CREATE TABLE market_events (
  event_id   BIGSERIAL PRIMARY KEY,
  run_id     UUID REFERENCES runs(run_id),
  ts         TIMESTAMPTZ NOT NULL,
  symbol     TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('bar','tick','news','corporate_action')),
  payload    JSONB NOT NULL
);

CREATE TABLE signals (
  signal_id    BIGSERIAL PRIMARY KEY,
  run_id       UUID REFERENCES runs(run_id),
  ts           TIMESTAMPTZ NOT NULL,
  symbol       TEXT NOT NULL,
  direction    TEXT NOT NULL CHECK (direction IN ('long','short','flat')),
  strength     DOUBLE PRECISION,
  target_weight DOUBLE PRECISION,
  reason       TEXT,
  features     JSONB
);

CREATE TABLE orders (
  order_id      UUID PRIMARY KEY,
  run_id        UUID REFERENCES runs(run_id),
  parent_signal_id BIGINT REFERENCES signals(signal_id),
  ts_created    TIMESTAMPTZ NOT NULL,
  symbol        TEXT NOT NULL,
  side          TEXT NOT NULL CHECK (side IN ('buy','sell')),
  qty           DOUBLE PRECISION NOT NULL,
  order_type    TEXT NOT NULL CHECK (order_type IN ('market','limit','stop','stop_limit')),
  limit_price   DOUBLE PRECISION,
  stop_price    DOUBLE PRECISION,
  time_in_force TEXT,
  status        TEXT NOT NULL,
  reject_reason TEXT
);

CREATE TABLE fills (
  fill_id       BIGSERIAL PRIMARY KEY,
  run_id        UUID REFERENCES runs(run_id),
  order_id      UUID REFERENCES orders(order_id),
  ts_filled     TIMESTAMPTZ NOT NULL,
  symbol        TEXT NOT NULL,
  side          TEXT NOT NULL,
  qty           DOUBLE PRECISION NOT NULL,
  price         DOUBLE PRECISION NOT NULL,
  fee           DOUBLE PRECISION NOT NULL DEFAULT 0,
  slippage      DOUBLE PRECISION NOT NULL DEFAULT 0,
  liquidity_flag TEXT,
  venue         TEXT
);

CREATE TABLE positions (
  run_id      UUID REFERENCES runs(run_id),
  ts          TIMESTAMPTZ NOT NULL,
  symbol      TEXT NOT NULL,
  qty         DOUBLE PRECISION NOT NULL,
  avg_price   DOUBLE PRECISION NOT NULL,
  market_price DOUBLE PRECISION,
  unrealized_pnl DOUBLE PRECISION,
  realized_pnl  DOUBLE PRECISION,
  exposure      DOUBLE PRECISION,
  PRIMARY KEY (run_id, ts, symbol)
);

CREATE TABLE portfolio_snapshots (
  run_id      UUID REFERENCES runs(run_id),
  ts          TIMESTAMPTZ NOT NULL,
  cash        DOUBLE PRECISION NOT NULL,
  equity      DOUBLE PRECISION NOT NULL,
  gross_exposure DOUBLE PRECISION,
  net_exposure   DOUBLE PRECISION,
  leverage       DOUBLE PRECISION,
  margin_used    DOUBLE PRECISION,
  drawdown       DOUBLE PRECISION,
  daily_pnl      DOUBLE PRECISION,
  PRIMARY KEY (run_id, ts)
);

CREATE TABLE risk_events (
  risk_event_id BIGSERIAL PRIMARY KEY,
  run_id        UUID REFERENCES runs(run_id),
  ts            TIMESTAMPTZ NOT NULL,
  type          TEXT NOT NULL,
  threshold     DOUBLE PRECISION,
  observed_value DOUBLE PRECISION,
  action_taken  TEXT
);

CREATE TABLE metrics (
  run_id      UUID REFERENCES runs(run_id),
  metric_name TEXT NOT NULL,
  value       DOUBLE PRECISION,
  scope       TEXT NOT NULL CHECK (scope IN ('overall','is','oos','window','regime','mc')),
  window_id   TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (run_id, metric_name, scope, window_id)
);

CREATE TABLE artifacts (
  run_id        UUID REFERENCES runs(run_id),
  artifact_type TEXT NOT NULL,
  path_or_uri   TEXT NOT NULL,
  checksum      TEXT NOT NULL,
  created_ts    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, artifact_type, path_or_uri)
);

CREATE TABLE mc_runs (
  run_id        UUID PRIMARY KEY REFERENCES runs(run_id),
  parent_run_id UUID REFERENCES runs(run_id),
  n_simulations INTEGER NOT NULL,
  block_size    INTEGER,
  ruin_threshold DOUBLE PRECISION,
  ruin_prob     DOUBLE PRECISION,
  mdd_p05       DOUBLE PRECISION,
  mdd_p50       DOUBLE PRECISION,
  mdd_p95       DOUBLE PRECISION
);

-- Invariants enforced by the writer, not the DB:
--  * runs rows are immutable after status != 'running'
--  * fills/orders are append-only (no UPDATE/DELETE)
--  * metrics.scope='oos' only from purged/CPCV paths
--  * every run must reference a data_snapshot_id whose hash is recorded
