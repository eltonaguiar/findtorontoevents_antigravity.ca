-- ============================================================================
-- profit_program_schema.sql
-- Database: ejaguiar1_stocks (mysql.50webs.com)  [also mirrored in SQLite where noted]
-- Purpose : Schema for the "profitable market system" program (Phase 0-5).
--   Supports: premia pods (H-144..H-148), forward-clock accrual, cost/benchmark
--   gates, global trial counter, regime log, liquidity/execution-quality metrics.
--
-- Companion plan: plans/2026-11-20-market-profit-system-plan.md (Zoo)
-- Todos:       plans/2026-11-20-profit-program-todos.json
-- Hypotheses:  plans/2026-11-20-residual-mean-reversion-hypotheses.md
--
-- MySQL 5.7+/8.0 compatible. InnoDB + utf8mb4. Idempotent (IF NOT EXISTS).
-- Pipeline OWNS writes; consumers READ.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. premia_pods — one row per registered hypothesis pod
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS premia_pods (
    pod_id              VARCHAR(32)   NOT NULL COMMENT 'H-144..H-148, etc.',
    asset_class         VARCHAR(16)   NOT NULL COMMENT 'EQUITY|ETF|COMMODITY|FOREX|CRYPTO|BOND|FUTURES',
    name                VARCHAR(128)  NOT NULL,
    mechanism           VARCHAR(255)      NULL,
    status              VARCHAR(16)   NOT NULL DEFAULT 'UNTESTED' COMMENT 'UNTESTED|TESTING|NOT_PROVED|PROVISIONAL|PROVED|RETIRED|OBSERVE',
    n_trials_counted    INT           NOT NULL DEFAULT 0 COMMENT 'effective trials contributed to global counter',
    promoted_at         DATETIME          NULL,
    kill_rule           TEXT              NULL COMMENT 'pre-committed kill rule (written before run)',
    source_ref          VARCHAR(255)      NULL,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (pod_id),
    KEY ix_pp_class (asset_class),
    KEY ix_pp_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Registered premia pods (hypothesis registry mirror).';

-- ----------------------------------------------------------------------------
-- 2. premia_picks — one row per emitted pick from a pod
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS premia_picks (
    id                  VARCHAR(64)   NOT NULL COMMENT 'pick id / dedup hash',
    pod_id              VARCHAR(32)   NOT NULL,
    symbol              VARCHAR(32)   NOT NULL,
    asset_class         VARCHAR(16)   NOT NULL,
    direction           VARCHAR(8)    NOT NULL COMMENT 'LONG|SHORT',
    entry_price         DECIMAL(20,8)     NULL,
    take_profit         DECIMAL(20,8)     NULL COMMENT 'NULL when symmetric time/vol exit (no TP)',
    stop_loss           DECIMAL(20,8)     NULL COMMENT 'NULL when symmetric time/vol exit (no SL)',
    position_size_pct   DECIMAL(8,4)      NULL COMMENT 'vol-targeted size, capped',
    cost_model_version  VARCHAR(16)   NOT NULL COMMENT 'e.g. v1.0 — provenance',
    benchmark_leg       VARCHAR(32)   NOT NULL COMMENT 'SPY_TR|BTC_HOLD|TBILL|AGG|GSG',
    regime_at_entry     VARCHAR(32)       NULL,
    signal_timestamp    DATETIME          NULL,
    recorded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    provenance_source   VARCHAR(64)       NULL COMMENT 'emitter / pipeline',
    PRIMARY KEY (id),
    KEY ix_ppp_pod (pod_id),
    KEY ix_ppp_class (asset_class),
    KEY ix_ppp_symbol (symbol),
    CONSTRAINT fk_ppp_pod FOREIGN KEY (pod_id) REFERENCES premia_pods(pod_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Picks emitted by premia pods, with provenance + benchmark leg.';

-- ----------------------------------------------------------------------------
-- 3. forward_rows — per-pick resolved outcome (forward clock)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS forward_rows (
    id                  BIGINT        NOT NULL AUTO_INCREMENT,
    pick_id             VARCHAR(64)   NOT NULL,
    resolved_ts         DATETIME      NOT NULL,
    realized_pnl_pct    DECIMAL(12,6)     NULL COMMENT 'net of cost',
    cost_pct            DECIMAL(12,6)     NULL COMMENT 'round-trip cost applied',
    excess_vs_benchmark DECIMAL(12,6)     NULL COMMENT 'realized - benchmark over same window',
    regime              VARCHAR(32)       NULL,
    bars_held           INT               NULL,
    exit_reason         VARCHAR(32)       NULL COMMENT 'TIME|STOP|TARGET|MANUAL',
    recorded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_fr_pick (pick_id),
    KEY ix_fr_resolved (resolved_ts),
    CONSTRAINT fk_fr_pick FOREIGN KEY (pick_id) REFERENCES premia_picks(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Forward-clock resolved outcomes per pick (net of cost).';

-- ----------------------------------------------------------------------------
-- 4. cost_benchmark_gates — per-class cost & benchmark configuration
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cost_benchmark_gates (
    asset_class         VARCHAR(16)   NOT NULL,
    fees_bps            DECIMAL(8,2)  NOT NULL DEFAULT 0 COMMENT 'per side',
    slippage_bps        DECIMAL(8,2)  NOT NULL DEFAULT 0 COMMENT 'per side',
    rollover_bps        DECIMAL(8,2)  NOT NULL DEFAULT 0 COMMENT 'per period (FX/crypto funding)',
    funding_bps         DECIMAL(8,2)  NOT NULL DEFAULT 0 COMMENT 'per period (crypto funding)',
    round_trip_bps      DECIMAL(8,2)  NOT NULL COMMENT '2 * (fees+slippage) + rollover/funding',
    stress_multiplier   DECIMAL(4,2)  NOT NULL DEFAULT 2.00 COMMENT '2x cost stress',
    benchmark_leg       VARCHAR(32)   NOT NULL COMMENT 'SPY_TR|BTC_HOLD|TBILL|AGG|GSG',
    one_bar_delay       TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1 = signals at close t, positions from t+1',
    cost_model_version  VARCHAR(16)   NOT NULL,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_class, cost_model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Per-class cost model + benchmark leg. Hard gate inputs.';

-- ----------------------------------------------------------------------------
-- 5. trial_counter — global cumulative trial count for DSR (single source of truth)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trial_counter (
    counter_key         VARCHAR(48)   NOT NULL COMMENT 'e.g. global, equity_residual, crypto_exec',
    n_trials            INT           NOT NULL DEFAULT 0 COMMENT 'cumulative independent trials tested',
    effective_n         DECIMAL(10,2)     NULL COMMENT 'effective N (correlated candidates > 1)',
    last_incremented_at DATETIME          NULL,
    last_incremented_by VARCHAR(64)       NULL COMMENT 'pod_id or scan that added trials',
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (counter_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Global cumulative trial counter feeding DSR everywhere (P0-f).';

INSERT INTO trial_counter (counter_key, n_trials, effective_n) VALUES
  ('global', 0, 0)
ON DUPLICATE KEY UPDATE counter_key = counter_key;

-- ----------------------------------------------------------------------------
-- 6. regime_log — regime per asset class per date
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regime_log (
    asset_class         VARCHAR(16)   NOT NULL,
    log_date            DATE          NOT NULL,
    regime              VARCHAR(32)   NOT NULL COMMENT 'TREND|CHOP|HIGH_VOL|LOW_VOL',
    vol_percentile      DECIMAL(6,2)      NULL,
    trend_score         DECIMAL(8,4)      NULL,
    recorded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_class, log_date),
    KEY ix_rl_regime (regime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Regime classification per class per day (P3-c exposure caps).';

-- ----------------------------------------------------------------------------
-- 7. liquidity_metrics — execution-quality measurements (bond/crypto)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS liquidity_metrics (
    id                  BIGINT        NOT NULL AUTO_INCREMENT,
    asset_class         VARCHAR(16)   NOT NULL,
    symbol              VARCHAR(32)   NOT NULL,
    venue               VARCHAR(32)       NULL COMMENT 'exchange/DEX/RFQ platform',
    spread_bps          DECIMAL(10,4)     NULL,
    depth_usd           DECIMAL(20,2)     NULL,
    slippage_bps        DECIMAL(10,4)     NULL COMMENT 'measured for a given notional',
    notional_usd        DECIMAL(20,2)     NULL,
    recorded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_lm_class (asset_class),
    KEY ix_lm_symbol (symbol),
    KEY ix_lm_ts (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Execution-quality / liquidity measurements (P1.9, P1.10).';

-- ----------------------------------------------------------------------------
-- 8. premia_verdicts — written promote/keep-paper/freeze verdicts per pod
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS premia_verdicts (
    id                  BIGINT        NOT NULL AUTO_INCREMENT,
    pod_id              VARCHAR(32)   NOT NULL,
    verdict             VARCHAR(16)   NOT NULL COMMENT 'PROMOTE|KEEP_PAPER|FREEZE|RETIRE',
    forward_n           INT           NOT NULL DEFAULT 0,
    net_ci_lower        DECIMAL(12,6)     NULL,
    dsr                 DECIMAL(8,4)      NULL,
    bh_q                DECIMAL(8,4)      NULL,
    kill_rule_triggered TINYINT(1)    NOT NULL DEFAULT 0,
    rationale           TEXT              NULL,
    decided_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_pv_pod (pod_id),
    KEY ix_pv_verdict (verdict),
    CONSTRAINT fk_pv_pod FOREIGN KEY (pod_id) REFERENCES premia_pods(pod_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Written promote/keep-paper/freeze/retire verdicts (P4).';

-- ----------------------------------------------------------------------------
-- Seed: cost_benchmark_gates defaults (per class, v1.0)
-- ----------------------------------------------------------------------------
INSERT INTO cost_benchmark_gates
  (asset_class, fees_bps, slippage_bps, rollover_bps, funding_bps, round_trip_bps, stress_multiplier, benchmark_leg, one_bar_delay, cost_model_version)
VALUES
  ('EQUITY',   5.00,  5.00, 0.00, 0.00, 20.00, 2.00, 'SPY_TR', 1, 'v1.0'),
  ('ETF',      3.00,  3.00, 0.00, 0.00, 12.00, 2.00, 'AGG',    1, 'v1.0'),
  ('COMMODITY',8.00,  8.00, 0.00, 0.00, 32.00, 2.00, 'GSG',    1, 'v1.0'),
  ('FOREX',    1.00,  1.00, 2.00, 0.00,  6.00, 2.00, 'TBILL',  1, 'v1.0'),
  ('CRYPTO',  10.00, 10.00, 0.00, 5.00, 45.00, 2.00, 'BTC_HOLD',1, 'v1.0'),
  ('BOND',     2.00,  2.00, 0.00, 0.00,  8.00, 2.00, 'AGG',    1, 'v1.0'),
  ('FUTURES',  4.00,  4.00, 0.00, 0.00, 16.00, 2.00, 'GSG',    1, 'v1.0')
ON DUPLICATE KEY UPDATE
  fees_bps=VALUES(fees_bps), slippage_bps=VALUES(slippage_bps),
  rollover_bps=VALUES(rollover_bps), funding_bps=VALUES(funding_bps),
  round_trip_bps=VALUES(round_trip_bps), stress_multiplier=VALUES(stress_multiplier),
  benchmark_leg=VALUES(benchmark_leg), one_bar_delay=VALUES(one_bar_delay);

-- ----------------------------------------------------------------------------
-- Seed: premia_pods (H-144..H-148 as filed in residual-mean-reversion-hypotheses.md)
-- ----------------------------------------------------------------------------
INSERT INTO premia_pods (pod_id, asset_class, name, mechanism, status, source_ref) VALUES
  ('H-144','EQUITY','Sector-ETF residual mean reversion','Regress returns on sector ETFs; OU s-score on residual; vol-sized, beta-hedged','UNTESTED','plans/2026-11-20-residual-mean-reversion-hypotheses.md'),
  ('H-145','COMMODITY','Energy calendar-spread mean reversion','Bollinger on front-2nd month spread; Kalman hedge ratio','UNTESTED','plans/2026-11-20-residual-mean-reversion-hypotheses.md'),
  ('H-146','CRYPTO','Cost-implied trade gate','Change position only when |forecast| > round-trip cost; measure turnover reduction + gross-alpha retention','UNTESTED','plans/2026-11-20-residual-mean-reversion-hypotheses.md'),
  ('H-147','EQUITY','Selection-alpha decomposition','Hedge each pick market-factor exposure over holding window; re-measure selection alpha','UNTESTED','plans/2026-11-20-residual-mean-reversion-hypotheses.md'),
  ('H-148','ETF','Intraday ETF-vs-constituent mean-reverting pair','Mean-reverting pair, no AP authority','UNTESTED','plans/2026-11-20-residual-mean-reversion-hypotheses.md')
ON DUPLICATE KEY UPDATE name=VALUES(name), mechanism=VALUES(mechanism), status=VALUES(status);

-- ----------------------------------------------------------------------------
-- Seed: trial_counter starting row
-- ----------------------------------------------------------------------------
INSERT INTO trial_counter (counter_key, n_trials, effective_n) VALUES
  ('global', 0, 0.00)
ON DUPLICATE KEY UPDATE counter_key = counter_key;

-- ============================================================================
-- Example queries
-- ============================================================================
-- A) All pods + status:
--   SELECT pod_id, asset_class, status, n_trials_counted FROM premia_pods ORDER BY pod_id;
-- B) Forward-clock progress per pod:
--   SELECT p.pod_id, COUNT(f.id) AS n_forward, AVG(f.realized_pnl_pct) AS mean_pnl,
--          AVG(f.excess_vs_benchmark) AS mean_excess
--   FROM premia_pods p LEFT JOIN premia_picks pk ON pk.pod_id=p.pod_id
--   LEFT JOIN forward_rows f ON f.pick_id=pk.id GROUP BY p.pod_id;
-- C) Cost stress check (2x):
--   SELECT asset_class, round_trip_bps, round_trip_bps*stress_multiplier AS stress_bps
--   FROM cost_benchmark_gates WHERE cost_model_version='v1.0';
-- D) Regime distribution:
--   SELECT asset_class, regime, COUNT(*) FROM regime_log GROUP BY 1,2;
-- ============================================================================