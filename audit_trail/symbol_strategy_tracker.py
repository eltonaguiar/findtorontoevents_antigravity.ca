"""
Symbol × Strategy Edge Tracker
================================
Maintains ``symbol_strategy_stats`` (SQLite) / ``at_symbol_strategy_stats``
(MySQL) — granular win-rate tracking at the *symbol + strategy* level, not
just the strategy level that ``strategy_stats`` already provides.

WHY THIS MATTERS
----------------
``strategy_stats`` tracks win rate per strategy across ALL symbols.  But a
strategy may have a 55% win rate globally and an 80% win rate specifically on
BTCUSDT — or 30% on a thinly-traded altcoin.  This table surfaces those
per-symbol edges so the dashboard and gates can act on them.

INTEGRATION
-----------
Call ``update_from_closed_pick(pick, conn)`` whenever a pick closes.
Call ``rebuild_from_closed_picks(conn)`` to recalculate stats from scratch
(e.g. after a schema migration or historical import).

Call ``get_edge_picks(min_win_rate, min_picks, conn)`` to retrieve symbol-
strategy combinations with proven edge for display on the audit dashboard.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe(val: Any, cast=float) -> Optional[Any]:
    try:
        return cast(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Single-pick update (call on every pick close)
# ---------------------------------------------------------------------------

def update_from_closed_pick(pick: Dict[str, Any], conn: sqlite3.Connection) -> None:
    """
    Update symbol_strategy_stats for one closed pick.
    Idempotent if called multiple times for the same pick (uses pick_id dedup
    via a separate ``_ss_processed`` in-memory set per connection — not
    persisted across restarts, so full rebuild is the safe path).
    """
    symbol    = pick.get("symbol", "")
    strategy  = pick.get("strategy", "") or ""
    system    = pick.get("source_system", "") or ""
    direction = pick.get("direction", "BOTH") or "BOTH"
    asset_cl  = pick.get("asset_class", "") or ""
    pnl       = _safe(pick.get("pnl_pct"), float)
    rr        = _safe(pick.get("risk_reward"), float)
    ml        = _safe(pick.get("ml_score"), float)
    elite     = _safe(pick.get("elite_score"), float)
    smart     = _safe(pick.get("smart_score"), float)
    rsi       = _safe(pick.get("rsi_at_entry") or pick.get("feat_rsi"), float)
    vol_ratio = _safe(pick.get("volume_ratio") or pick.get("feat_volume_ratio"), float)

    if not symbol or pnl is None:
        return

    # 2026-04-27: trinary classification — break-evens count as neither win
    # nor loss (mirrors update_pick_outcome and forward_validator). The 1bp
    # threshold matches feedback_noncrypto_resolver_live_close_bug.md and
    # outcome_resolver. See docs/CODE_REVIEW_2026_04_27.md (audit-C2).
    if pnl > 0.0001:
        is_win, is_loss = 1, 0
    elif pnl < -0.0001:
        is_win, is_loss = 0, 1
    else:
        # EVEN — count toward total_picks but not wins/losses
        is_win, is_loss = 0, 0

    cur = conn.cursor()

    # Fetch current row (if any)
    cur.execute(
        """SELECT total_picks, wins, losses, avg_pnl_pct, best_pnl, worst_pnl,
                  avg_rr, avg_ml_score, avg_elite_score, avg_smart_score,
                  avg_rsi, avg_volume_ratio
             FROM symbol_strategy_stats
            WHERE symbol=? AND strategy=? AND source_system=? AND direction=?""",
        (symbol, strategy, system, direction),
    )
    row = cur.fetchone()

    if row:
        n, wins, losses, avg_pnl, best, worst, avg_rr, avg_ml, avg_el, avg_sm, avg_rsi_v, avg_vol = row
        n_new = n + 1
        wins_new = wins + is_win
        losses_new = losses + is_loss
        # WR is wins / decided picks (excludes EVENs); fall back to 0 if all even
        decided_new = wins_new + losses_new
        wr_new = (wins_new / decided_new) if decided_new > 0 else 0.0
        avg_pnl_new = (avg_pnl * n + pnl) / n_new
        best_new = max(best or pnl, pnl)
        worst_new = min(worst or pnl, pnl)
        avg_rr_new = ((avg_rr or 0) * n + (rr or 0)) / n_new
        avg_ml_new = ((avg_ml or 0) * n + (ml or 0)) / n_new if ml is not None else avg_ml
        avg_el_new = ((avg_el or 0) * n + (elite or 0)) / n_new if elite is not None else avg_el
        avg_sm_new = ((avg_sm or 0) * n + (smart or 0)) / n_new if smart is not None else avg_sm
        avg_rsi_new = ((avg_rsi_v or 0) * n + (rsi or 0)) / n_new if rsi is not None else avg_rsi_v
        avg_vol_new = ((avg_vol or 0) * n + (vol_ratio or 0)) / n_new if vol_ratio is not None else avg_vol

        cur.execute(
            """UPDATE symbol_strategy_stats
                  SET total_picks=?, wins=?, losses=?, win_rate=?, avg_pnl_pct=?,
                      best_pnl=?, worst_pnl=?, avg_rr=?,
                      avg_ml_score=?, avg_elite_score=?, avg_smart_score=?,
                      avg_rsi=?, avg_volume_ratio=?, last_updated=?
                WHERE symbol=? AND strategy=? AND source_system=? AND direction=?""",
            (n_new, wins_new, losses_new, wr_new, avg_pnl_new,
             best_new, worst_new, avg_rr_new,
             avg_ml_new, avg_el_new, avg_sm_new,
             avg_rsi_new, avg_vol_new, _now_utc(),
             symbol, strategy, system, direction),
        )
    else:
        decided_first = is_win + is_loss
        wr = (is_win / decided_first) if decided_first > 0 else 0.0
        cur.execute(
            """INSERT INTO symbol_strategy_stats
               (symbol, strategy, source_system, asset_class, direction,
                total_picks, wins, losses, win_rate, avg_pnl_pct,
                best_pnl, worst_pnl, avg_rr,
                avg_ml_score, avg_elite_score, avg_smart_score,
                avg_rsi, avg_volume_ratio, last_updated)
               VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?)""",
            (symbol, strategy, system, asset_cl, direction,
             1, is_win, is_loss, wr, pnl,
             pnl, pnl, rr or 0,
             ml, elite, smart,
             rsi, vol_ratio, _now_utc()),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Full rebuild from closed raw_picks
# ---------------------------------------------------------------------------

def rebuild_from_closed_picks(conn: sqlite3.Connection) -> int:
    """
    Recalculate all symbol_strategy_stats from scratch using closed raw_picks.
    Useful after historical imports or schema migrations.
    Returns number of rows written.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM symbol_strategy_stats")

    # Check which ML/feature columns exist (migration may not have run yet)
    cur.execute("PRAGMA table_info(raw_picks)")
    existing_cols = {r[1] for r in cur.fetchall()}

    def col(name: str, alias: str) -> str:
        return f"rp.{name} AS {alias}" if name in existing_cols else f"NULL AS {alias}"

    ml_cols = ", ".join([
        col("ml_score", "ml_score"),
        col("elite_score", "elite_score"),
        col("smart_score", "smart_score"),
        col("feat_rsi", "rsi"),
        col("feat_volume_ratio", "vol_ratio"),
    ])

    query = f"""
        SELECT rp.symbol,
               COALESCE(rp.strategy, '') AS strategy,
               COALESCE(rp.source_system, '') AS source_system,
               COALESCE(rp.asset_class, '') AS asset_class,
               COALESCE(rp.direction, 'BOTH') AS direction,
               rp.pnl_pct,
               rp.risk_reward,
               {ml_cols}
          FROM raw_picks rp
         WHERE rp.status IN ('WIN', 'LOSS', 'CLOSED', 'TP', 'SL')
           AND rp.pnl_pct IS NOT NULL
    """
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except sqlite3.Error as exc:
        logger.error("rebuild_from_closed_picks query failed: %s", exc)
        return 0

    for r in rows:
        pick = {
            "symbol": r[0], "strategy": r[1], "source_system": r[2],
            "asset_class": r[3], "direction": r[4], "pnl_pct": r[5],
            "risk_reward": r[6], "ml_score": r[7], "elite_score": r[8],
            "smart_score": r[9], "feat_rsi": r[10], "feat_volume_ratio": r[11],
        }
        update_from_closed_pick(pick, conn)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM symbol_strategy_stats")
    return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Query helpers for dashboard
# ---------------------------------------------------------------------------

def get_edge_picks(
    conn: sqlite3.Connection,
    min_win_rate: float = 0.55,
    min_picks: int = 5,
    asset_class: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Return symbol-strategy combos with statistically meaningful edge.

    Parameters
    ----------
    min_win_rate : float  Minimum win rate threshold (default 55%)
    min_picks    : int    Minimum closed picks required (default 5)
    asset_class  : str    Filter by asset class (optional)
    direction    : str    Filter by direction LONG/SHORT (optional)
    limit        : int    Max rows returned
    """
    filters = ["total_picks >= ?", "win_rate >= ?"]
    params: List[Any] = [min_picks, min_win_rate]

    if asset_class:
        filters.append("asset_class = ?")
        params.append(asset_class)
    if direction and direction != "BOTH":
        filters.append("direction = ?")
        params.append(direction)

    where = " AND ".join(filters)
    sql = f"""
        SELECT symbol, strategy, source_system, asset_class, direction,
               total_picks, wins, losses, win_rate, avg_pnl_pct,
               best_pnl, worst_pnl, avg_rr,
               avg_ml_score, avg_elite_score, avg_smart_score,
               avg_rsi, avg_volume_ratio, last_updated
          FROM symbol_strategy_stats
         WHERE {where}
         ORDER BY win_rate DESC, total_picks DESC
         LIMIT ?
    """
    params.append(limit)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except sqlite3.Error as exc:
        logger.warning("get_edge_picks failed: %s", exc)
        return []


def get_symbol_strategy_summary(
    conn: sqlite3.Connection,
) -> Dict[str, Any]:
    """
    High-level summary stats for the audit dashboard summary card.
    Returns counts and best performers.
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM symbol_strategy_stats WHERE total_picks >= 5")
        total_combos = cur.fetchone()[0]

        cur.execute(
            """SELECT COUNT(*) FROM symbol_strategy_stats
               WHERE total_picks >= 5 AND win_rate >= 0.60"""
        )
        high_edge_combos = cur.fetchone()[0]

        cur.execute(
            """SELECT symbol, strategy, win_rate, total_picks
                 FROM symbol_strategy_stats
                WHERE total_picks >= 10
                ORDER BY win_rate DESC LIMIT 5"""
        )
        top_combos = [
            {"symbol": r[0], "strategy": r[1], "win_rate": r[2], "picks": r[3]}
            for r in cur.fetchall()
        ]
        return {
            "total_combinations": total_combos,
            "high_edge_combinations": high_edge_combos,
            "top_combinations": top_combos,
        }
    except sqlite3.Error:
        return {"total_combinations": 0, "high_edge_combinations": 0, "top_combinations": []}
