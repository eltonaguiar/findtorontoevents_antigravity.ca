-- AI-Model Hedge-Fund-Style Portfolios — Phase 1 schema
-- DB: ejaguiar1_stocks (MySQL). Source: docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §6
-- All tables prefixed PF_ to namespace this paper-trading subsystem.
-- Idempotent: CREATE TABLE IF NOT EXISTS. Additive only — does not touch existing pick/money-ready tables.

-- One row per (model_id, risk_appetite) portfolio, or per fund-of-funds book.
CREATE TABLE IF NOT EXISTS PF_PORTFOLIO (
  id              BIGINT       NOT NULL AUTO_INCREMENT,
  portfolio_key   VARCHAR(255) NOT NULL,
  model_id        VARCHAR(255) NULL,
  risk_appetite   VARCHAR(32)  NOT NULL,
  kind            VARCHAR(16)  NOT NULL DEFAULT 'model',   -- 'model' | 'fof'
  starting_nav    DECIMAL(18,4) NOT NULL DEFAULT 100000.0000,
  status          VARCHAR(16)  NOT NULL DEFAULT 'active',  -- 'active' | 'frozen'
  config_snapshot JSON         NULL,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pf_portfolio_key (portfolio_key),
  KEY idx_pf_portfolio_model (model_id),
  KEY idx_pf_portfolio_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One row per open/closed position.
CREATE TABLE IF NOT EXISTS PF_POSITION (
  id              BIGINT       NOT NULL AUTO_INCREMENT,
  portfolio_id    BIGINT       NOT NULL,
  symbol          VARCHAR(64)  NOT NULL,
  asset_class     VARCHAR(32)  NOT NULL,
  direction       VARCHAR(8)   NOT NULL,                   -- 'long' | 'short'
  status          VARCHAR(16)  NOT NULL DEFAULT 'open',    -- 'open' | 'closed'
  entry_date      DATE         NULL,
  entry_price     DECIMAL(18,4) NULL,
  qty             DECIMAL(18,4) NULL,
  weight_at_entry DECIMAL(8,4) NULL,
  tp_price        DECIMAL(18,4) NULL,
  sl_price        DECIMAL(18,4) NULL,
  exit_date       DATE         NULL,
  exit_price      DECIMAL(18,4) NULL,
  exit_reason     TEXT         NULL,
  realized_pnl_pct DECIMAL(8,4) NULL,
  realized_pnl_usd DECIMAL(18,4) NULL,
  source_pick_id  VARCHAR(255) NULL,
  entry_reason    TEXT         NULL,
  sizing_reason   TEXT         NULL,
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_pf_position_portfolio (portfolio_id),
  KEY idx_pf_position_status (status),
  KEY idx_pf_position_symbol (symbol),
  CONSTRAINT fk_pf_position_portfolio FOREIGN KEY (portfolio_id) REFERENCES PF_PORTFOLIO (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Daily NAV mark per portfolio (the equity curve). Idempotent per (portfolio_id, asof_date).
CREATE TABLE IF NOT EXISTS PF_NAV_SNAPSHOT (
  id                 BIGINT       NOT NULL AUTO_INCREMENT,
  portfolio_id       BIGINT       NOT NULL,
  asof_date          DATE         NOT NULL,
  nav_usd            DECIMAL(18,4) NOT NULL,
  cash_usd           DECIMAL(18,4) NULL,
  gross_exposure_pct DECIMAL(8,4) NULL,
  n_open             INT          NULL,
  daily_return_pct   DECIMAL(8,4) NULL,
  drawdown_pct       DECIMAL(8,4) NULL,
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pf_nav_portfolio_date (portfolio_id, asof_date),
  KEY idx_pf_nav_portfolio (portfolio_id),
  KEY idx_pf_nav_asof (asof_date),
  CONSTRAINT fk_pf_nav_portfolio FOREIGN KEY (portfolio_id) REFERENCES PF_PORTFOLIO (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit log of every gate decision (entry rejected, stop hit, breaker tripped).
CREATE TABLE IF NOT EXISTS PF_RULE_EVENT (
  id           BIGINT       NOT NULL AUTO_INCREMENT,
  portfolio_id BIGINT       NOT NULL,
  asof_date    DATE         NOT NULL,
  event_type   VARCHAR(64)  NOT NULL,
  symbol       VARCHAR(64)  NULL,
  detail       JSON         NULL,
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_pf_rule_portfolio (portfolio_id),
  KEY idx_pf_rule_asof (asof_date),
  KEY idx_pf_rule_event_type (event_type),
  CONSTRAINT fk_pf_rule_portfolio FOREIGN KEY (portfolio_id) REFERENCES PF_PORTFOLIO (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Rolling per-portfolio risk/return metrics (dashboard + meta-analysis). Idempotent per (portfolio_id, asof_date).
CREATE TABLE IF NOT EXISTS PF_DAILY_METRICS (
  id                 BIGINT       NOT NULL AUTO_INCREMENT,
  portfolio_id       BIGINT       NOT NULL,
  asof_date          DATE         NOT NULL,
  sharpe_30d         DECIMAL(8,4) NULL,
  sortino_30d        DECIMAL(8,4) NULL,
  max_dd             DECIMAL(8,4) NULL,
  cagr               DECIMAL(8,4) NULL,
  vol_realized       DECIMAL(8,4) NULL,
  pf_to_date         DECIMAL(8,4) NULL,
  wr_to_date         DECIMAL(8,4) NULL,
  turnover           DECIMAL(8,4) NULL,
  exposure_by_class  JSON         NULL,
  created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pf_metrics_portfolio_date (portfolio_id, asof_date),
  KEY idx_pf_metrics_portfolio (portfolio_id),
  KEY idx_pf_metrics_asof (asof_date),
  CONSTRAINT fk_pf_metrics_portfolio FOREIGN KEY (portfolio_id) REFERENCES PF_PORTFOLIO (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
