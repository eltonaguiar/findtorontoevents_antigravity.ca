"""
Feature Edge Analyzer
======================
Analyzes which technical indicator values and ML score ranges correlate with
winning picks, using data persisted by ``pick_feature_store.py``.

This answers questions like:
  - "Do picks with RSI 30–40 at entry win more often than RSI 60–70?"
  - "Does a high volume_ratio (>2x) improve win rate?"
  - "Which wf_verdict tiers produce the best outcomes?"
  - "Are high elite_score picks actually winning more?"

Results are written to ``feature_edge_snapshots`` for dashboard display and
CSV export.

USAGE
-----
    python -m audit_trail.feature_edge_analyzer          # analyze all features
    python -m audit_trail.feature_edge_analyzer --csv    # also export CSV

INTEGRATION
-----------
Called by ``audit_trail/dashboard_generator.py`` at the end of each run to
refresh the edge snapshot table shown on the /audit dashboard.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature bucket definitions
# Each entry: (column_name, list_of_bucket_edges, label_prefix)
# Buckets are [low, high) ranges; last bucket is [low, +inf)
# ---------------------------------------------------------------------------

NUMERIC_FEATURES: List[Tuple[str, List[float], str]] = [
    # RSI at entry: oversold vs neutral vs overbought
    ("feat_rsi",         [0, 30, 40, 50, 60, 70, 100],  "rsi"),
    # Volume ratio: below average, at, above
    ("feat_volume_ratio",[0, 0.5, 1.0, 1.5, 2.0, 3.0, 999], "vol_ratio"),
    # ATR % of price: tighter vs wider market
    ("feat_atr_pct",     [0, 0.5, 1.0, 2.0, 3.0, 5.0, 999], "atr_pct"),
    # VWAP deviation: distance from fair value
    ("feat_vwap_dev",    [-5, -2, -1, 0, 1, 2, 5],      "vwap_dev"),
    # BTC correlation: low vs high correlation
    ("feat_btc_corr",    [-1, -0.5, 0, 0.3, 0.6, 0.8, 1.0], "btc_corr"),
    # Regime: -1=bear, 0=neutral, 1=bull
    ("feat_regime",      [-1.5, -0.5, 0.5, 1.5],        "regime"),
    # Funding rate: negative (shorts paid), zero, positive (longs pay)
    ("feat_funding_rate",[-1, -0.01, 0, 0.01, 0.1, 1],  "funding"),
    # Cross-sectional momentum rank: 0..1
    ("feat_cs_momentum", [0, 0.2, 0.4, 0.6, 0.8, 1.0],  "cs_mom"),
    # Order book imbalance: -1=sell pressure, +1=buy pressure
    ("feat_ob_imbalance",[-1, -0.3, -0.1, 0.1, 0.3, 1], "ob_imb"),
    # MACD histogram normalised
    ("feat_macd_hist",   [-1, -0.05, -0.01, 0, 0.01, 0.05, 1], "macd"),
    # ML scores
    ("ml_score",         [0, 20, 40, 60, 70, 80, 90, 100], "ml_score"),
    ("elite_score",      [0, 20, 40, 60, 70, 80, 90, 100], "elite_score"),
    ("smart_score",      [0, 30, 50, 60, 70, 80, 100],    "smart_score"),
    ("trust_score",      [0, 3, 5, 7, 10, 20],            "trust_score"),
    ("strat_fwd_wr",     [0, 0.4, 0.5, 0.55, 0.6, 0.7, 1.0], "strat_fwd_wr"),
    ("darwin_score_v2",  [0, 30, 50, 60, 70, 80, 100],    "darwin_v2"),
]

CATEGORICAL_FEATURES: List[str] = [
    "wf_verdict",
    "feat_regime",
    "direction",
    "asset_class",
]

# 2026-04-27 (security review): SQL identifiers must be whitelisted before
# being interpolated into f-string queries. Set of all column names this
# module is permitted to scan, computed once at import time.
_ALLOWED_FEATURE_COLUMNS: frozenset = frozenset(
    {entry[0] for entry in NUMERIC_FEATURES} | set(CATEGORICAL_FEATURES)
)


def _bucket_label(low: float, high: Optional[float], prefix: str) -> str:
    if high is None:
        return f"{prefix}_{low}+"
    return f"{prefix}_{low}_{high}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _get_available_cols(conn: sqlite3.Connection, table: str) -> set:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}


def analyze_numeric_feature(
    conn: sqlite3.Connection,
    col: str,
    edges: List[float],
    label_prefix: str,
    asset_class: str = "ALL",
    direction: str = "ALL",
    computed_at: str = "",
) -> List[Dict[str, Any]]:
    """Bucket a numeric feature and compute win rate per bucket."""
    # 2026-04-27 (security review): whitelist `col` against the known feature
    # set before f-string interpolation. `asset_class`/`direction` are
    # bound as parameters below. See docs/CODE_REVIEW_2026_04_27.md (audit-C1).
    if col not in _ALLOWED_FEATURE_COLUMNS:
        logger.warning("analyze_numeric_feature: rejected non-whitelist column %r", col)
        return []
    results = []
    n_edges = len(edges)
    for i in range(n_edges - 1):
        low = edges[i]
        high = edges[i + 1]
        label = _bucket_label(low, high, label_prefix)

        # Build SQL. `col` is whitelisted above so identifier-interpolation
        # is safe; numeric edges are floats; user-controllable string values
        # (asset_class, direction) are bound as positional parameters.
        params: List[Any] = []
        conditions = [
            f"rp.{col} IS NOT NULL",
            f"rp.{col} >= {float(low)}",
            f"rp.{col} < {float(high)}",
            "rp.status IN ('WIN', 'LOSS', 'CLOSED', 'TP', 'SL')",
            "rp.pnl_pct IS NOT NULL",
        ]
        if asset_class != "ALL":
            conditions.append("rp.asset_class = ?")
            params.append(asset_class)
        if direction != "ALL":
            conditions.append("rp.direction = ?")
            params.append(direction)

        where = " AND ".join(conditions)
        sql = f"""
            SELECT COUNT(*) AS n,
                   SUM(CASE WHEN rp.pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
                   AVG(rp.pnl_pct) AS avg_pnl
              FROM raw_picks rp
             WHERE {where}
        """
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
        except sqlite3.Error as exc:
            logger.debug("analyze_numeric_feature %s skip: %s", col, exc)
            continue

        if not row or not row[0]:
            continue

        n_picks = row[0]
        n_wins = row[1] or 0
        avg_pnl = row[2] or 0.0
        wr = n_wins / n_picks if n_picks > 0 else 0.0
        edge = wr * avg_pnl  # reward-weighted edge score

        results.append({
            "computed_at":  computed_at,
            "feature_name": col,
            "bucket_label": label,
            "bucket_low":   low,
            "bucket_high":  high,
            "n_picks":      n_picks,
            "n_wins":       n_wins,
            "win_rate":     round(wr, 4),
            "avg_pnl_pct":  round(avg_pnl, 4),
            "edge_score":   round(edge, 4),
            "asset_class":  asset_class,
            "direction":    direction,
        })

    return results


def analyze_categorical_feature(
    conn: sqlite3.Connection,
    col: str,
    computed_at: str = "",
) -> List[Dict[str, Any]]:
    """Group by a categorical column and compute win rate per value."""
    # 2026-04-27 (security review): whitelist `col` before f-string
    # interpolation as a SQL identifier.
    if col not in _ALLOWED_FEATURE_COLUMNS:
        logger.warning("analyze_categorical_feature: rejected non-whitelist column %r", col)
        return []
    try:
        cur = conn.cursor()
        sql = f"""
            SELECT rp.{col},
                   COUNT(*) AS n,
                   SUM(CASE WHEN rp.pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
                   AVG(rp.pnl_pct) AS avg_pnl
              FROM raw_picks rp
             WHERE rp.{col} IS NOT NULL
               AND rp.status IN ('WIN', 'LOSS', 'CLOSED', 'TP', 'SL')
               AND rp.pnl_pct IS NOT NULL
             GROUP BY rp.{col}
             ORDER BY wins * 1.0 / COUNT(*) DESC
        """
        cur.execute(sql)
        rows = cur.fetchall()
    except sqlite3.Error as exc:
        logger.debug("analyze_categorical_feature %s skip: %s", col, exc)
        return []

    results = []
    for row in rows:
        val, n, wins, avg_pnl = row
        wr = (wins or 0) / n if n > 0 else 0.0
        edge = wr * (avg_pnl or 0.0)
        results.append({
            "computed_at":  computed_at,
            "feature_name": col,
            "bucket_label": f"{col}_{val}",
            "bucket_low":   None,
            "bucket_high":  None,
            "n_picks":      n,
            "n_wins":       wins or 0,
            "win_rate":     round(wr, 4),
            "avg_pnl_pct":  round(avg_pnl or 0, 4),
            "edge_score":   round(edge, 4),
            "asset_class":  "ALL",
            "direction":    "ALL",
        })
    return results


def _upsert_snapshot(cur: sqlite3.Cursor, row: Dict[str, Any]) -> None:
    cur.execute(
        """INSERT OR REPLACE INTO feature_edge_snapshots
           (computed_at, feature_name, bucket_label, bucket_low, bucket_high,
            n_picks, n_wins, win_rate, avg_pnl_pct, edge_score,
            asset_class, direction)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["computed_at"], row["feature_name"], row["bucket_label"],
            row["bucket_low"], row["bucket_high"],
            row["n_picks"], row["n_wins"], row["win_rate"],
            row["avg_pnl_pct"], row["edge_score"],
            row["asset_class"], row["direction"],
        ),
    )


def run_full_analysis(
    conn: sqlite3.Connection,
    asset_classes: Optional[List[str]] = None,
    directions: Optional[List[str]] = None,
    export_csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run complete edge analysis across all features and write results to
    ``feature_edge_snapshots``.  Returns a summary dict suitable for logging.
    """
    computed_at = _now_utc()
    available = _get_available_cols(conn, "raw_picks")
    cur = conn.cursor()

    if asset_classes is None:
        asset_classes = ["ALL"]
    if directions is None:
        directions = ["ALL"]

    all_rows: List[Dict[str, Any]] = []
    skipped_cols = []

    for col, edges, prefix in NUMERIC_FEATURES:
        if col not in available and col not in {"ml_score", "elite_score", "smart_score",
                                                 "trust_score", "strat_fwd_wr",
                                                 "darwin_score_v2", "wf_verdict"}:
            skipped_cols.append(col)
            continue
        for ac in asset_classes:
            for dir_ in directions:
                rows = analyze_numeric_feature(conn, col, edges, prefix, ac, dir_, computed_at)
                all_rows.extend(rows)

    for col in CATEGORICAL_FEATURES:
        if col not in available and col not in {"direction", "asset_class", "wf_verdict"}:
            skipped_cols.append(col)
            continue
        rows = analyze_categorical_feature(conn, col, computed_at)
        all_rows.extend(rows)

    for row in all_rows:
        _upsert_snapshot(cur, row)
    conn.commit()

    logger.info(
        "feature_edge_analyzer: wrote %d bucket snapshots (%s skipped cols)",
        len(all_rows), len(skipped_cols),
    )

    if export_csv_path:
        _export_csv(all_rows, export_csv_path)

    return {
        "computed_at":    computed_at,
        "total_buckets":  len(all_rows),
        "skipped_cols":   skipped_cols,
    }


# ---------------------------------------------------------------------------
# Best edges query for dashboard
# ---------------------------------------------------------------------------

def get_top_feature_edges(
    conn: sqlite3.Connection,
    min_picks: int = 10,
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """Return the highest edge_score buckets for dashboard display."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT feature_name, bucket_label, n_picks, win_rate, avg_pnl_pct, edge_score,
                   asset_class, direction
              FROM feature_edge_snapshots
             WHERE n_picks >= ?
               AND asset_class = 'ALL'
             ORDER BY edge_score DESC
             LIMIT ?
            """,
            (min_picks, top_n),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def get_feature_edge_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """High-level summary for the audit dashboard card."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(DISTINCT feature_name) FROM feature_edge_snapshots"
        )
        n_features = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM feature_edge_snapshots WHERE win_rate >= 0.60 AND n_picks >= 10"
        )
        n_strong_edges = cur.fetchone()[0]
        cur.execute(
            """SELECT feature_name, bucket_label, win_rate, n_picks
                 FROM feature_edge_snapshots
                WHERE n_picks >= 10
                ORDER BY win_rate DESC LIMIT 3"""
        )
        top = [
            {"feature": r[0], "bucket": r[1], "win_rate": r[2], "n": r[3]}
            for r in cur.fetchall()
        ]
        return {
            "features_analyzed": n_features,
            "strong_edge_buckets": n_strong_edges,
            "top_edges": top,
        }
    except sqlite3.Error:
        return {"features_analyzed": 0, "strong_edge_buckets": 0, "top_edges": []}


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def _export_csv(rows: List[Dict[str, Any]], path: str) -> None:
    if not rows:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info("feature_edge_analyzer: exported CSV to %s", path)
    except OSError as exc:
        logger.warning("CSV export failed: %s", exc)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Analyze feature edge correlations")
    parser.add_argument("--db", default="audit_trail/audit_trail.db",
                        help="Path to audit trail SQLite DB")
    parser.add_argument("--csv", action="store_true", help="Export results to CSV")
    parser.add_argument("--top", type=int, default=20, help="Show top N edges")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"DB not found: {args.db}")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    csv_path = args.db.replace(".db", "_feature_edges.csv") if args.csv else None

    summary = run_full_analysis(conn, export_csv_path=csv_path)
    print(f"\nAnalysis complete: {summary['total_buckets']} buckets written")
    if summary["skipped_cols"]:
        print(f"Skipped (not yet in schema): {summary['skipped_cols']}")

    top = get_top_feature_edges(conn, top_n=args.top)
    if top:
        print(f"\nTop {len(top)} feature edge buckets:\n")
        print(f"{'Feature':<22} {'Bucket':<30} {'N':>5} {'WR':>6} {'AvgPnL':>8} {'Edge':>7}")
        print("-" * 82)
        for r in top:
            print(
                f"{r['feature_name']:<22} {r['bucket_label']:<30} "
                f"{r['n_picks']:>5} {r['win_rate']:>6.1%} "
                f"{r['avg_pnl_pct']:>8.2f} {r['edge_score']:>7.3f}"
            )

    conn.close()
