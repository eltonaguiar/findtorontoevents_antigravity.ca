"""
KOL Performance Tracker
=======================
Tracks per-KOL accuracy and computes dynamic weights for the consensus engine.

Recalculates win rates, Sharpe ratios, calibration scores, and Bayesian-shrunk
weights for every registered KOL. Exports a ranked leaderboard to JSON.

Usage (GitHub Actions):
    python predictions/kol/kol_performance_tracker.py
"""

import sys
import json
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent  # predictions/
sys.path.insert(0, str(ROOT))
from db import get_db
sys.path.insert(0, str(ROOT / "kol"))
from kol_registry import get_active_kols, get_kol_by_handle, CATEGORY_LABELS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_TRADES_FOR_WEIGHT = 20   # Full weight after 20 closed trades
WEIGHT_FLOOR = 0.1
WEIGHT_CEILING = 3.0
STALE_DAYS = 60              # Decay weight after 60 days inactive
LEADERBOARD_PATH = ROOT / "data" / "kol_leaderboard.json"

CLOSED_STATUSES = ("TP_HIT", "SL_HIT", "EXPIRED", "CLOSED")


# ---------------------------------------------------------------------------
# Schema migration — add columns that may not exist yet
# ---------------------------------------------------------------------------

def _ensure_columns(conn: sqlite3.Connection) -> None:
    """Add dynamic_weight and calibration_score columns if missing."""
    migrations = [
        ("predictors", "dynamic_weight", "REAL DEFAULT 1.0"),
        ("predictors", "calibration_score", "REAL DEFAULT 0.0"),
    ]
    for table, col, typedef in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()


# ---------------------------------------------------------------------------
# Core stats recalculation
# ---------------------------------------------------------------------------

def recalculate_kol_stats(conn: sqlite3.Connection, predictor_id: str) -> dict:
    """Recalculate all performance stats for a single KOL from closed predictions."""
    _ensure_columns(conn)

    rows = conn.execute(
        """SELECT direction, outcome_pnl_pct, status
           FROM predictions
           WHERE predictor_id = ? AND status IN (?, ?, ?, ?)""",
        (predictor_id, *CLOSED_STATUSES),
    ).fetchall()

    total = len(rows)
    if total == 0:
        return {
            "predictor_id": predictor_id,
            "total_predictions": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_pnl_pct": 0.0,
            "best_pick_pnl": None,
            "worst_pick_pnl": None,
            "sharpe": 0.0,
            "calibration_score": 0.0,
        }

    wins = sum(1 for r in rows if r["status"] == "TP_HIT")
    losses = sum(1 for r in rows if r["status"] == "SL_HIT")
    win_rate = wins / total if total > 0 else 0.0

    pnls = [r["outcome_pnl_pct"] for r in rows if r["outcome_pnl_pct"] is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    best_pnl = max(pnls) if pnls else None
    worst_pnl = min(pnls) if pnls else None

    # Sharpe ratio: mean / stdev
    if len(pnls) >= 2:
        mean_pnl = sum(pnls) / len(pnls)
        variance = sum((x - mean_pnl) ** 2 for x in pnls) / (len(pnls) - 1)
        stdev = math.sqrt(variance) if variance > 0 else 0.0
        sharpe = mean_pnl / stdev if stdev > 0 else 0.0
    else:
        sharpe = 0.0

    # Calibration score: fraction of directional predictions that were correct
    # A LONG prediction is correct if pnl > 0; SHORT correct if pnl < 0
    correct = 0
    calibration_total = 0
    for r in rows:
        pnl = r["outcome_pnl_pct"]
        direction = (r["direction"] or "").upper()
        if pnl is None or direction not in ("LONG", "SHORT"):
            continue
        calibration_total += 1
        if (direction == "LONG" and pnl > 0) or (direction == "SHORT" and pnl < 0):
            correct += 1
    calibration_score = correct / calibration_total if calibration_total > 0 else 0.0

    # Update predictors table
    conn.execute(
        """UPDATE predictors SET
               total_predictions = ?,
               wins = ?,
               losses = ?,
               win_rate = ?,
               avg_pnl_pct = ?,
               best_pick_pnl = ?,
               worst_pick_pnl = ?,
               sharpe = ?,
               calibration_score = ?
           WHERE predictor_id = ?""",
        (total, wins, losses, win_rate, avg_pnl, best_pnl, worst_pnl,
         sharpe, calibration_score, predictor_id),
    )
    conn.commit()

    return {
        "predictor_id": predictor_id,
        "total_predictions": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_pnl_pct": avg_pnl,
        "best_pick_pnl": best_pnl,
        "worst_pick_pnl": worst_pnl,
        "sharpe": sharpe,
        "calibration_score": calibration_score,
    }


# ---------------------------------------------------------------------------
# Population stats
# ---------------------------------------------------------------------------

def _compute_population_stats(conn: sqlite3.Connection) -> dict:
    """Average win rate across all KOLs with >= 5 closed trades."""
    row = conn.execute(
        """SELECT AVG(win_rate) AS avg_wr, COUNT(*) AS cnt
           FROM predictors
           WHERE total_predictions >= 5 AND win_rate > 0"""
    ).fetchone()
    return {
        "avg_wr": row["avg_wr"] if row["avg_wr"] is not None else 0.5,
        "count": row["cnt"] if row["cnt"] is not None else 0,
    }


# ---------------------------------------------------------------------------
# Dynamic weight computation
# ---------------------------------------------------------------------------

def update_dynamic_weights(conn: sqlite3.Connection) -> None:
    """Compute Bayesian-shrunk dynamic weights for every registered KOL."""
    _ensure_columns(conn)
    pop = _compute_population_stats(conn)
    population_wr = pop["avg_wr"] if pop["avg_wr"] > 0 else 0.5

    # Get all registered KOL handles
    registered_handles = {k["handle"] for k in get_active_kols()}

    rows = conn.execute(
        """SELECT predictor_id, win_rate, total_predictions
           FROM predictors
           WHERE total_predictions > 0"""
    ).fetchall()

    for r in rows:
        pid = r["predictor_id"]
        # Only weight registered KOLs
        if pid not in registered_handles:
            continue

        kol_wr = r["win_rate"] or 0.0
        closed_trades = r["total_predictions"] or 0

        # Look up initial_weight from registry
        kol_info = get_kol_by_handle(pid)
        base_weight = kol_info["initial_weight"] if kol_info else 1.0

        # Bayesian shrinkage toward population mean
        raw_weight = kol_wr / population_wr if population_wr > 0 else 1.0
        sample_factor = min(1.0, closed_trades / MIN_TRADES_FOR_WEIGHT)
        weight = base_weight * (sample_factor * raw_weight + (1 - sample_factor) * 1.0)
        weight = max(WEIGHT_FLOOR, min(WEIGHT_CEILING, weight))

        conn.execute(
            "UPDATE predictors SET dynamic_weight = ? WHERE predictor_id = ?",
            (round(weight, 4), pid),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Stale KOL decay
# ---------------------------------------------------------------------------

def decay_stale_kols(conn: sqlite3.Connection, max_inactive_days: int = STALE_DAYS) -> int:
    """Halve dynamic_weight for KOLs inactive longer than max_inactive_days.

    Returns the number of KOLs decayed.
    """
    _ensure_columns(conn)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_inactive_days)).isoformat()

    stale = conn.execute(
        """SELECT predictor_id, dynamic_weight
           FROM predictors
           WHERE last_active < ? AND dynamic_weight > ?""",
        (cutoff, WEIGHT_FLOOR),
    ).fetchall()

    decayed = 0
    for r in stale:
        new_weight = max(WEIGHT_FLOOR, (r["dynamic_weight"] or 1.0) * 0.5)
        conn.execute(
            "UPDATE predictors SET dynamic_weight = ? WHERE predictor_id = ?",
            (round(new_weight, 4), r["predictor_id"]),
        )
        decayed += 1

    conn.commit()
    return decayed


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def _rank_column(values: list[float], ascending: bool = False) -> list[float]:
    """Return normalized rank scores (0-1) for a list of values."""
    if not values:
        return []
    n = len(values)
    if n == 1:
        return [1.0]
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=not ascending)
    ranks = [0.0] * n
    for rank_pos, (orig_idx, _) in enumerate(indexed):
        ranks[orig_idx] = 1.0 - (rank_pos / (n - 1))  # 1.0 = best, 0.0 = worst
    return ranks


def get_kol_leaderboard(conn: sqlite3.Connection, min_trades: int = 5) -> list[dict]:
    """Build ranked KOL leaderboard using composite scoring.

    Composite = 0.4*wr_rank + 0.3*calibration_rank + 0.2*sharpe_rank + 0.1*volume_rank
    """
    _ensure_columns(conn)

    rows = conn.execute(
        """SELECT predictor_id, display_name, platform, total_predictions,
                  wins, losses, win_rate, avg_pnl_pct, best_pick_pnl,
                  worst_pick_pnl, sharpe, calibration_score, dynamic_weight,
                  tier, last_active
           FROM predictors
           WHERE total_predictions >= ?
           ORDER BY win_rate DESC""",
        (min_trades,),
    ).fetchall()

    # Filter to registered KOLs only
    registered_handles = {k["handle"] for k in get_active_kols()}
    entries = [dict(r) for r in rows if r["predictor_id"] in registered_handles]

    if not entries:
        return []

    # Extract ranking columns
    wrs = [e["win_rate"] or 0.0 for e in entries]
    cals = [e["calibration_score"] or 0.0 for e in entries]
    sharpes = [e["sharpe"] or 0.0 for e in entries]
    volumes = [float(e["total_predictions"] or 0) for e in entries]

    wr_ranks = _rank_column(wrs)
    cal_ranks = _rank_column(cals)
    sharpe_ranks = _rank_column(sharpes)
    vol_ranks = _rank_column(volumes)

    for i, entry in enumerate(entries):
        composite = (
            0.4 * wr_ranks[i]
            + 0.3 * cal_ranks[i]
            + 0.2 * sharpe_ranks[i]
            + 0.1 * vol_ranks[i]
        )
        entry["composite_score"] = round(composite, 4)

        # Add category from registry
        kol_info = get_kol_by_handle(entry["predictor_id"])
        entry["category"] = kol_info["category"] if kol_info else "unknown"

    # Sort by composite score descending
    entries.sort(key=lambda e: e["composite_score"], reverse=True)

    # Assign rank
    for rank, entry in enumerate(entries, start=1):
        entry["rank"] = rank

    return entries


# ---------------------------------------------------------------------------
# Leaderboard export
# ---------------------------------------------------------------------------

def export_leaderboard_json(conn: sqlite3.Connection) -> None:
    """Export ranked leaderboard and category summary to JSON."""
    entries = get_kol_leaderboard(conn)

    # Category summary: average WR per category
    cat_stats: dict[str, list[float]] = {}
    for e in entries:
        cat = e.get("category", "unknown")
        cat_stats.setdefault(cat, []).append(e["win_rate"] or 0.0)

    category_summary = {}
    for cat, wrs in cat_stats.items():
        category_summary[cat] = {
            "label": CATEGORY_LABELS.get(cat, cat),
            "count": len(wrs),
            "avg_win_rate": round(sum(wrs) / len(wrs), 4) if wrs else 0.0,
        }

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_ranked": len(entries),
        "category_summary": category_summary,
        "leaderboard": entries,
    }

    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_PATH.write_text(json.dumps(data, indent=2, default=str))
    print(f"[KOL Tracker] Exported leaderboard to {LEADERBOARD_PATH} ({len(entries)} KOLs)")


# ---------------------------------------------------------------------------
# Main entry point (GitHub Actions)
# ---------------------------------------------------------------------------

def update_all_kol_stats() -> None:
    """Recalculate stats, update weights, decay stale KOLs, export leaderboard."""
    conn = get_db()
    _ensure_columns(conn)

    kols = get_active_kols()
    print(f"[KOL Tracker] Processing {len(kols)} registered KOLs...")

    updated = 0
    for kol in kols:
        handle = kol["handle"]
        # Check if this KOL has any predictions in DB
        count = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE predictor_id = ?",
            (handle,),
        ).fetchone()[0]
        if count > 0:
            stats = recalculate_kol_stats(conn, handle)
            updated += 1
            wr = stats["win_rate"]
            total = stats["total_predictions"]
            print(f"  {handle:20s}  trades={total:4d}  WR={wr:.1%}  sharpe={stats['sharpe']:.2f}")

    print(f"\n[KOL Tracker] Recalculated stats for {updated}/{len(kols)} KOLs")

    # Update dynamic weights
    update_dynamic_weights(conn)
    print("[KOL Tracker] Dynamic weights updated")

    # Decay stale KOLs
    decayed = decay_stale_kols(conn)
    if decayed:
        print(f"[KOL Tracker] Decayed {decayed} stale KOLs")

    # Export leaderboard
    export_leaderboard_json(conn)

    conn.close()
    print("[KOL Tracker] Done.")


if __name__ == "__main__":
    update_all_kol_stats()
