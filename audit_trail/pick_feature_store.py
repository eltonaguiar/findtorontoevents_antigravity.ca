"""
Pick Feature Store
==================
Persists ML scores and technical indicator features computed by
``alpha_engine/feature_populator.py`` and ``audit_trail/quality_gates.py``
into the audit-trail SQLite/MySQL database so they are available for
post-hoc edge analysis and model retraining.

Previously these values were computed at scan time and then discarded — only
the binary pass/fail gate result survived. This module captures them.

INTEGRATION POINTS
------------------
Call ``store_pick_features(pick, db_conn)`` from:
  - ``audit_trail/dashboard_generator.py`` just after a pick is ingested
  - ``alpha_engine/smart_picks_engine.py`` after ``calculate_smart_score()``

Call ``update_pick_outcome(pick_id, pnl_pct, exit_reason, db_conn)`` when a
pick closes (from ``audit_trail/universal_pick_resolver.py``).

Database targets
----------------
SQLite  : appends columns to ``raw_picks`` (via schema_v2_migration())
MySQL   : writes to ``at_pick_features`` side-table (avoids ALTER TABLE on prod)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature key mapping
# feature_populator.py key -> column name stored in DB
# ---------------------------------------------------------------------------
ML_SCORE_COLUMNS: Dict[str, str] = {
    "ml_score":           "ml_score",
    "elite_score":        "elite_score",
    "smart_score":        "smart_score",
    "trust_score":        "trust_score",
    "darwin_score_v2":    "darwin_score_v2",
    "method_a_score":     "method_a_score",
    "ml_composite_score": "ml_composite_score",
    "wf_verdict":         "wf_verdict",
    "strat_fwd_wr":       "strat_fwd_wr",
    "forward_wr":         "forward_wr",
    "agreement_count":    "agreement_count",
    "high_conviction_gate_passed": "high_conviction",
    # Claude ML Gainer + Antigravity ML native scores. Without these, the
    # gate rules merged in PR #346 (pump_probability band at [0.35, 0.50))
    # remain dead code because the feature store never persists them.
    # See review #348 Cerebras consult finding.
    "pump_probability":   "ml_pump_probability",
    "confidence_tier":    "ml_confidence_tier",    # str: "VERY HIGH" / "HIGH" / etc.
    "gainer_score":       "ml_gainer_score",       # Antigravity ML's 0-100 score
    "ml_signals":         "ml_signals_json",        # JSON-encoded signal list
}

TECHNICAL_FEATURE_COLUMNS: Dict[str, str] = {
    "rsi_at_entry":       "feat_rsi",
    "volume_ratio":       "feat_volume_ratio",
    "atr_at_entry":       "feat_atr_pct",
    "close_to_vwap":      "feat_vwap_dev",
    "macd_hist_norm":     "feat_macd_hist",
    "btc_correlation":    "feat_btc_corr",
    "regime_encoded":     "feat_regime",
    "funding_rate_raw":   "feat_funding_rate",
    "cs_momentum_rank":   "feat_cs_momentum",
    "orderbook_imbalance":"feat_ob_imbalance",
    "stoch_k30":          "feat_stoch_k",
    "cci20_norm":         "feat_cci",
    "williams_r":         "feat_williams_r",
}

ALL_FEATURE_COLUMNS = {**ML_SCORE_COLUMNS, **TECHNICAL_FEATURE_COLUMNS}


# ---------------------------------------------------------------------------
# SQLite schema migration (v2 – adds feature columns to raw_picks + new tables)
# ---------------------------------------------------------------------------

SQLITE_MIGRATION_V2 = """
-- ML score columns on raw_picks (idempotent ALTER TABLE)
ALTER TABLE raw_picks ADD COLUMN ml_score           REAL;
ALTER TABLE raw_picks ADD COLUMN elite_score        REAL;
ALTER TABLE raw_picks ADD COLUMN smart_score        REAL;
ALTER TABLE raw_picks ADD COLUMN trust_score        REAL;
ALTER TABLE raw_picks ADD COLUMN darwin_score_v2    REAL;
ALTER TABLE raw_picks ADD COLUMN method_a_score     REAL;
ALTER TABLE raw_picks ADD COLUMN ml_composite_score REAL;
ALTER TABLE raw_picks ADD COLUMN wf_verdict         TEXT;
ALTER TABLE raw_picks ADD COLUMN strat_fwd_wr       REAL;
ALTER TABLE raw_picks ADD COLUMN forward_wr         REAL;
ALTER TABLE raw_picks ADD COLUMN agreement_count    INTEGER;
ALTER TABLE raw_picks ADD COLUMN high_conviction    INTEGER DEFAULT 0;

-- Claude ML / Antigravity ML native scores (complements PR #346 gate rules)
ALTER TABLE raw_picks ADD COLUMN ml_pump_probability REAL;
ALTER TABLE raw_picks ADD COLUMN ml_confidence_tier  TEXT;
ALTER TABLE raw_picks ADD COLUMN ml_gainer_score     REAL;
ALTER TABLE raw_picks ADD COLUMN ml_signals_json     TEXT;

-- Technical indicator snapshot columns on raw_picks
ALTER TABLE raw_picks ADD COLUMN feat_rsi           REAL;
ALTER TABLE raw_picks ADD COLUMN feat_volume_ratio  REAL;
ALTER TABLE raw_picks ADD COLUMN feat_atr_pct       REAL;
ALTER TABLE raw_picks ADD COLUMN feat_vwap_dev      REAL;
ALTER TABLE raw_picks ADD COLUMN feat_macd_hist     REAL;
ALTER TABLE raw_picks ADD COLUMN feat_btc_corr      REAL;
ALTER TABLE raw_picks ADD COLUMN feat_regime        INTEGER;
ALTER TABLE raw_picks ADD COLUMN feat_funding_rate  REAL;
ALTER TABLE raw_picks ADD COLUMN feat_cs_momentum   REAL;
ALTER TABLE raw_picks ADD COLUMN feat_ob_imbalance  REAL;
ALTER TABLE raw_picks ADD COLUMN feat_stoch_k       REAL;
ALTER TABLE raw_picks ADD COLUMN feat_cci           REAL;
ALTER TABLE raw_picks ADD COLUMN feat_williams_r    REAL;
"""

SYMBOL_STRATEGY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS symbol_strategy_stats (
    symbol          TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    source_system   TEXT NOT NULL DEFAULT '',
    asset_class     TEXT,
    direction       TEXT,          -- LONG / SHORT / BOTH
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
    avg_rsi         REAL,          -- mean RSI at entry across closed picks
    avg_volume_ratio REAL,         -- mean volume ratio at entry
    last_updated    TEXT,
    PRIMARY KEY (symbol, strategy, source_system, direction)
);
CREATE INDEX IF NOT EXISTS idx_sss_sym   ON symbol_strategy_stats(symbol);
CREATE INDEX IF NOT EXISTS idx_sss_strat ON symbol_strategy_stats(strategy);
CREATE INDEX IF NOT EXISTS idx_sss_wr    ON symbol_strategy_stats(win_rate);
"""

FEATURE_EDGE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS feature_edge_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_at     TEXT NOT NULL,
    feature_name    TEXT NOT NULL,
    bucket_label    TEXT NOT NULL,   -- e.g. 'rsi_30_40', 'vol_ratio_1_2'
    bucket_low      REAL,
    bucket_high     REAL,
    n_picks         INTEGER DEFAULT 0,
    n_wins          INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    avg_pnl_pct     REAL DEFAULT 0.0,
    edge_score      REAL DEFAULT 0.0, -- win_rate * avg_pnl (reward-weighted edge)
    asset_class     TEXT DEFAULT 'ALL',
    direction       TEXT DEFAULT 'ALL',
    UNIQUE(computed_at, feature_name, bucket_label, asset_class, direction)
);
CREATE INDEX IF NOT EXISTS idx_fes_feat ON feature_edge_snapshots(feature_name);
CREATE INDEX IF NOT EXISTS idx_fes_date ON feature_edge_snapshots(computed_at);
"""


def run_sqlite_migration(conn: sqlite3.Connection) -> None:
    """Apply idempotent v2 migration (adds feature columns if missing)."""
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key='schema_version'")
    row = cur.fetchone()
    current = row[0] if row else "1.0"
    if current >= "2.0":
        return

    # ALTER TABLE statements fail if column already exists – catch and skip
    for stmt in SQLITE_MIGRATION_V2.strip().split(";"):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as exc:
            if "duplicate column" in str(exc).lower():
                pass
            else:
                logger.warning("Migration stmt skipped: %s — %s", stmt[:60], exc)

    cur.execute(SYMBOL_STRATEGY_TABLE_DDL)
    cur.execute(FEATURE_EDGE_TABLE_DDL)
    cur.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '2.0')"
    )
    conn.commit()
    logger.info("pick_feature_store: schema migrated to v2.0")


# ---------------------------------------------------------------------------
# MySQL side-table DDL (avoids ALTER TABLE on production MySQL)
# ---------------------------------------------------------------------------

MYSQL_SIDE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `at_pick_features` (
  `pick_id`             VARCHAR(64)  NOT NULL,
  `symbol`              VARCHAR(32)  NOT NULL,
  `strategy`            VARCHAR(128) NOT NULL DEFAULT '',
  `source_system`       VARCHAR(64)  NOT NULL DEFAULT '',
  `asset_class`         VARCHAR(32),
  `direction`           VARCHAR(8),
  `status`              VARCHAR(16)  DEFAULT 'OPEN',
  `pnl_pct`             FLOAT,
  -- ML scores
  `ml_score`            FLOAT,
  `elite_score`         FLOAT,
  `smart_score`         FLOAT,
  `trust_score`         FLOAT,
  `darwin_score_v2`     FLOAT,
  `method_a_score`      FLOAT,
  `ml_composite_score`  FLOAT,
  `wf_verdict`          VARCHAR(16),
  `strat_fwd_wr`        FLOAT,
  `forward_wr`          FLOAT,
  `agreement_count`     SMALLINT,
  `high_conviction`     TINYINT(1)   DEFAULT 0,
  -- Technical features at entry
  `feat_rsi`            FLOAT,
  `feat_volume_ratio`   FLOAT,
  `feat_atr_pct`        FLOAT,
  `feat_vwap_dev`       FLOAT,
  `feat_macd_hist`      FLOAT,
  `feat_btc_corr`       FLOAT,
  `feat_regime`         TINYINT,
  `feat_funding_rate`   FLOAT,
  `feat_cs_momentum`    FLOAT,
  `feat_ob_imbalance`   FLOAT,
  `feat_stoch_k`        FLOAT,
  `feat_cci`            FLOAT,
  `feat_williams_r`     FLOAT,
  `recorded_at`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`pick_id`),
  KEY `idx_apf_sym`    (`symbol`),
  KEY `idx_apf_strat`  (`strategy`),
  KEY `idx_apf_status` (`status`),
  KEY `idx_apf_ml`     (`ml_score`),
  KEY `idx_apf_elite`  (`elite_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

MYSQL_SYMBOL_STRATEGY_DDL = """
CREATE TABLE IF NOT EXISTS `at_symbol_strategy_stats` (
  `symbol`          VARCHAR(32)  NOT NULL,
  `strategy`        VARCHAR(128) NOT NULL,
  `source_system`   VARCHAR(64)  NOT NULL DEFAULT '',
  `asset_class`     VARCHAR(32),
  `direction`       VARCHAR(8),
  `total_picks`     INT          DEFAULT 0,
  `wins`            INT          DEFAULT 0,
  `losses`          INT          DEFAULT 0,
  `win_rate`        FLOAT        DEFAULT 0.0,
  `avg_pnl_pct`     FLOAT        DEFAULT 0.0,
  `best_pnl`        FLOAT        DEFAULT 0.0,
  `worst_pnl`       FLOAT        DEFAULT 0.0,
  `avg_rr`          FLOAT        DEFAULT 0.0,
  `avg_ml_score`    FLOAT,
  `avg_elite_score` FLOAT,
  `avg_smart_score` FLOAT,
  `avg_rsi`         FLOAT,
  `avg_volume_ratio` FLOAT,
  `last_updated`    DATETIME,
  PRIMARY KEY (`symbol`, `strategy`, `source_system`, `direction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


# ---------------------------------------------------------------------------
# Core write helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def extract_feature_row(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all storable feature values from a pick dict."""
    row: Dict[str, Any] = {
        "pick_id":       pick.get("id", ""),
        "symbol":        pick.get("symbol", ""),
        "strategy":      pick.get("strategy", ""),
        "source_system": pick.get("source_system", ""),
        "asset_class":   pick.get("asset_class", ""),
        "direction":     pick.get("direction", ""),
        "status":        pick.get("status", "OPEN"),
        "pnl_pct":       _safe_float(pick.get("pnl_pct")),
    }
    for src_key, col in ALL_FEATURE_COLUMNS.items():
        raw = pick.get(src_key)
        # wf_verdict and high_conviction are strings/bools
        if col in ("wf_verdict",):
            row[col] = str(raw) if raw is not None else None
        elif col in ("high_conviction", "agreement_count"):
            row[col] = _safe_int(raw)
        else:
            row[col] = _safe_float(raw)
    return row


def store_pick_features_sqlite(
    pick: Dict[str, Any],
    conn: sqlite3.Connection,
) -> bool:
    """
    Upsert feature values into raw_picks for the given pick id.
    Safe to call before or after outcome resolution.
    """
    pick_id = pick.get("id")
    if not pick_id:
        return False

    row = extract_feature_row(pick)
    col_names = [c for c in row if c not in ("pick_id", "symbol", "strategy",
                                              "source_system", "asset_class",
                                              "direction", "status", "pnl_pct")]
    if not col_names:
        return False

    # Build UPDATE statement (only update columns that have non-None values)
    assignments = []
    values = []
    for col in col_names:
        if row[col] is not None:
            assignments.append(f"{col} = ?")
            values.append(row[col])

    if not assignments:
        return False

    values.append(pick_id)
    sql = "UPDATE raw_picks SET " + ", ".join(assignments) + " WHERE id = ?"
    try:
        cur = conn.cursor()
        cur.execute(sql, values)
        # 2026-04-27 (perf): per-row conn.commit() removed. The dashboard cycle
        # calls this in a ~3,600-row loop (active + recent_closed + smart_picks)
        # so per-row commit + per-row fsync was a meaningful chunk of the
        # workflow runtime that PR #436 just widened. The caller in
        # dashboard_generator.py:13713 holds the connection in a `with` block
        # which auto-commits on exit. See docs/CODE_REVIEW_2026_04_27.md
        # (audit-C3). If you need durability between rows, call
        # conn.commit() at the call site, not here.
        return cur.rowcount > 0
    except sqlite3.Error as exc:
        logger.warning("store_pick_features_sqlite failed for %s: %s", pick_id, exc)
        return False


def store_pick_features_mysql(
    pick: Dict[str, Any],
    mysql_conn: Any,
) -> bool:
    """
    Insert/replace a row into at_pick_features (MySQL side-table).
    ``mysql_conn`` should be a mysql.connector connection object.
    """
    row = extract_feature_row(pick)
    if not row.get("pick_id"):
        return False

    cols = list(row.keys())
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(f"`{c}`" for c in cols)
    updates = ", ".join(
        f"`{c}` = VALUES(`{c}`)" for c in cols if c != "pick_id"
    )
    sql = (
        f"INSERT INTO at_pick_features ({col_list}) VALUES ({placeholders})"
        f" ON DUPLICATE KEY UPDATE {updates}"
    )
    try:
        cur = mysql_conn.cursor()
        cur.execute(sql, [row[c] for c in cols])
        mysql_conn.commit()
        return True
    except Exception as exc:
        logger.warning("store_pick_features_mysql failed: %s", exc)
        return False


def update_pick_outcome(
    pick_id: str,
    pnl_pct: float,
    exit_reason: str,
    conn: sqlite3.Connection,
) -> None:
    """Update status + pnl on both raw_picks and at_pick_features after close."""
    # 2026-04-27: WIN/LOSS-only classification silently mislabelled break-even
    # closes (pnl_pct == 0.0) as LOSS, contradicting forward_validator and
    # outcome_resolver which carry EVEN/FLAT as a third state. Mislabel inflated
    # the LOSS column in the per-symbol WR table this module feeds. The 1bp
    # threshold mirrors feedback_noncrypto_resolver_live_close_bug.md and matches
    # outcome_resolver.py. See docs/CODE_REVIEW_2026_04_27.md (audit-C2).
    if pnl_pct > 0.0001:
        status = "WIN"
    elif pnl_pct < -0.0001:
        status = "LOSS"
    else:
        status = "EVEN"
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE raw_picks SET status=?, pnl_pct=? WHERE id=?",
            (status, pnl_pct, pick_id),
        )
        conn.commit()
    except sqlite3.Error as exc:
        logger.warning("update_pick_outcome failed: %s", exc)


def store_pick_features(
    pick: Dict[str, Any],
    conn: Any,
    backend: str = "sqlite",
) -> bool:
    """Unified entry point: route to sqlite or mysql backend."""
    if backend == "mysql":
        return store_pick_features_mysql(pick, conn)
    return store_pick_features_sqlite(pick, conn)


# Tiered retention. 18 features per pick × forever would grow without bound;
# the policy is hot < 90d (per-pick), warm 90-365d (weekly aggregate),
# cold dropped. Idempotent — safe to call once per dashboard cycle.

RETAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_picks_weekly (
    week           TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    strategy       TEXT NOT NULL,
    direction      TEXT NOT NULL,
    n              INTEGER NOT NULL,
    win_rate       REAL,
    avg_pnl_pct    REAL,
    avg_rsi        REAL,
    avg_atr        REAL,
    avg_volume_ratio REAL,
    avg_vwap_dev   REAL,
    avg_macd_hist  REAL,
    avg_btc_corr   REAL,
    avg_elite_score REAL,
    avg_smart_score REAL,
    avg_ml_score   REAL,
    PRIMARY KEY (week, symbol, strategy, direction)
);
CREATE INDEX IF NOT EXISTS idx_rpw_week    ON raw_picks_weekly(week);
CREATE INDEX IF NOT EXISTS idx_rpw_symbol  ON raw_picks_weekly(symbol);
"""


def retain_features(
    conn: sqlite3.Connection,
    *,
    hot_days: int = 90,
    warm_days: int = 365,
) -> Dict[str, int]:
    """Tier old per-pick feature rows into weekly aggregates; drop very old.

    Idempotent: INSERT OR IGNORE on (week, symbol, strategy, direction) PK so
    concurrent dashboard cycles cannot produce duplicate rollups.
    Returns {"rolled_up", "hot_purged", "warm_purged"} counts.
    """
    cur = conn.cursor()
    for stmt in RETAIN_SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                cur.execute(stmt)
            except sqlite3.Error as exc:
                logger.warning("retain_features schema stmt failed: %s", exc)

    rolled = cur.execute(
        """
        INSERT OR IGNORE INTO raw_picks_weekly
            (week, symbol, strategy, direction, n, win_rate, avg_pnl_pct,
             avg_rsi, avg_atr, avg_volume_ratio, avg_vwap_dev, avg_macd_hist,
             avg_btc_corr, avg_elite_score, avg_smart_score, avg_ml_score)
        SELECT strftime('%Y-W%W', closed_at)         AS week,
               symbol, strategy, direction,
               COUNT(*) AS n,
               AVG(CASE WHEN status='WIN' THEN 1.0 ELSE 0.0 END) AS win_rate,
               AVG(pnl_pct), AVG(rsi), AVG(atr), AVG(volume_ratio),
               AVG(vwap_dev), AVG(macd_hist), AVG(btc_corr),
               AVG(elite_score), AVG(smart_score), AVG(ml_score)
        FROM raw_picks
        WHERE closed_at IS NOT NULL
          AND closed_at < datetime('now', '-' || ? || ' days')
        GROUP BY week, symbol, strategy, direction
        """,
        (hot_days,),
    ).rowcount

    hot_purged = cur.execute(
        "DELETE FROM raw_picks WHERE closed_at IS NOT NULL "
        "AND closed_at < datetime('now', '-' || ? || ' days')",
        (hot_days,),
    ).rowcount

    warm_purged = cur.execute(
        "DELETE FROM raw_picks_weekly WHERE week < strftime('%Y-W%W', "
        "datetime('now', '-' || ? || ' days'))",
        (warm_days,),
    ).rowcount

    conn.commit()
    return {
        "rolled_up": max(rolled, 0),
        "hot_purged": max(hot_purged, 0),
        "warm_purged": max(warm_purged, 0),
    }
