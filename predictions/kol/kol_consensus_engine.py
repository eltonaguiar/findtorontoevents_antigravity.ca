"""
KOL Consensus Engine
====================
Aggregates individual KOL predictions into weighted consensus signals.
When multiple KOLs from different categories agree on a symbol+direction,
this produces ULTRA / STRONG / MODERATE consensus picks.

Usage (GitHub Actions):
    python -m predictions.kol.kol_consensus_engine

Usage (direct):
    python predictions/kol/kol_consensus_engine.py
"""

from __future__ import annotations

import sys
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent  # predictions/
sys.path.insert(0, str(ROOT))
from db import get_db

sys.path.insert(0, str(ROOT / "kol"))
from kol_registry import get_active_kols, get_kol_by_handle, CATEGORY_LABELS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Signal strength thresholds
ULTRA_THRESHOLD = 5.0       # weighted votes
ULTRA_MIN_CATEGORIES = 3
STRONG_THRESHOLD = 3.0
STRONG_MIN_CATEGORIES = 2
MODERATE_THRESHOLD = 2.0

# Max age for predictions to be included in consensus
MAX_PREDICTION_AGE_HOURS = 72

OUTPUT_PATH = ROOT / "data" / "kol_consensus_picks.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_kol_dynamic_weight(conn: sqlite3.Connection, handle: str) -> float:
    """Read dynamic_weight from predictors table; default 1.0 if missing.

    Tries multiple predictor_id formats since scrapers use prefixed IDs
    (analyst:handle, youtube:handle, etc.).
    """
    prefixes = ["", "analyst:", "youtube:", "telegram:", "substack:", "web:"]
    try:
        for pfx in prefixes:
            row = conn.execute(
                "SELECT dynamic_weight FROM predictors WHERE predictor_id = ?",
                (f"{pfx}{handle}" if pfx else handle,),
            ).fetchone()
            if row and row["dynamic_weight"] is not None:
                return float(row["dynamic_weight"])
    except (sqlite3.OperationalError, KeyError):
        pass
    return 1.0


def _get_predictor_win_rate(conn: sqlite3.Connection, handle: str) -> float:
    """Read best win_rate from predictors table across all platform prefixes."""
    prefixes = ["", "analyst:", "youtube:", "telegram:", "substack:", "web:"]
    best_wr = 0.0
    try:
        for pfx in prefixes:
            row = conn.execute(
                "SELECT win_rate FROM predictors WHERE predictor_id = ?",
                (f"{pfx}{handle}" if pfx else handle,),
            ).fetchone()
            if row and row["win_rate"] is not None:
                best_wr = max(best_wr, float(row["win_rate"]))
    except (sqlite3.OperationalError, KeyError):
        pass
    return best_wr


def _get_active_kol_predictions(
    conn: sqlite3.Connection,
    max_age_hours: int = MAX_PREDICTION_AGE_HOURS,
) -> list[dict]:
    """
    Return active predictions from registered KOLs within the age window.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()

    try:
        rows = conn.execute(
            """
            SELECT * FROM predictions
            WHERE status = 'ACTIVE'
              AND scraped_at >= ?
            ORDER BY scraped_at DESC
            """,
            (cutoff,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(f"[kol_consensus] DB query error: {exc}")
        return []

    # Build set of registered KOL handles for fast lookup
    registered_handles = {k["handle"] for k in get_active_kols()}

    # predictor_id uses prefixed format: "analyst:woonomic", "youtube:handle", etc.
    # Extract the handle suffix after the colon for matching against registry.
    results = []
    seen_dedup = set()  # (handle, symbol, direction) for cross-platform dedup

    for row in rows:
        pred = dict(row)
        predictor_id = pred.get("predictor_id", "")

        # Exclude news-inferred signals from consensus (weak signals)
        if pred.get("analyst_category") == "news_inferred":
            continue

        # Extract handle from prefixed predictor_id (e.g. "analyst:woonomic" -> "woonomic")
        handle = predictor_id.split(":", 1)[-1] if ":" in predictor_id else predictor_id

        if handle not in registered_handles:
            continue

        # Cross-platform dedup: same KOL posting the same call on Twitter + YouTube
        # + Substack within the window should count as ONE vote, not three.
        dedup_key = (handle, pred.get("symbol", "").upper(), pred.get("direction", "").upper())
        if dedup_key in seen_dedup:
            continue
        seen_dedup.add(dedup_key)

        # Store the resolved handle for downstream lookup
        pred["_resolved_handle"] = handle
        results.append(pred)

    return results


# ---------------------------------------------------------------------------
# Core consensus logic
# ---------------------------------------------------------------------------

def compute_kol_consensus(conn: sqlite3.Connection) -> list[dict]:
    """
    Group active KOL predictions by (symbol, direction) and compute
    weighted consensus signals. Only emit MODERATE or stronger.
    """
    predictions = _get_active_kol_predictions(conn)
    if not predictions:
        return []

    # Group by (symbol, direction)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for pred in predictions:
        key = (pred["symbol"].upper(), pred["direction"].upper())
        groups[key].append(pred)

    consensus_signals = []

    for (symbol, direction), preds in groups.items():
        kol_handles = []
        kol_display_names = []
        categories = set()
        weighted_votes = 0.0
        win_rates = []

        for pred in preds:
            handle = pred.get("_resolved_handle") or pred["predictor_id"]
            kol_info = get_kol_by_handle(handle)
            if not kol_info:
                continue

            kol_handles.append(handle)
            kol_display_names.append(kol_info["display_name"])
            categories.add(kol_info["category"])

            weight = _get_kol_dynamic_weight(conn, handle)
            # Apply initial_weight from registry as a multiplier
            weight *= kol_info.get("initial_weight", 1.0)
            weighted_votes += weight

            wr = _get_predictor_win_rate(conn, handle)
            if wr > 0:
                win_rates.append(wr)

        if not kol_handles:
            continue

        category_diversity = len(categories)
        avg_kol_wr = round(sum(win_rates) / len(win_rates), 4) if win_rates else 0.0

        # Determine signal strength
        if weighted_votes >= ULTRA_THRESHOLD and category_diversity >= ULTRA_MIN_CATEGORIES:
            strength = "ULTRA"
            confidence = 0.80
        elif weighted_votes >= STRONG_THRESHOLD and category_diversity >= STRONG_MIN_CATEGORIES:
            strength = "STRONG"
            confidence = 0.70
        elif weighted_votes >= MODERATE_THRESHOLD:
            strength = "MODERATE"
            confidence = 0.60
        else:
            # WEAK -- skip
            continue

        # Collect price levels from KOL predictions for bridge use
        entry_prices = [p["entry_price"] for p in preds if p.get("entry_price")]
        tp_prices = [p["take_profit"] for p in preds if p.get("take_profit")]
        sl_prices = [p["stop_loss"] for p in preds if p.get("stop_loss")]
        avg_entry = round(sum(entry_prices) / len(entry_prices), 8) if entry_prices else None

        # Use median of stated KOL targets when >=2 sources quote levels
        # (avoids arbitrary % defaults when real data exists)
        median_tp = sorted(tp_prices)[len(tp_prices) // 2] if len(tp_prices) >= 2 else None
        median_sl = sorted(sl_prices)[len(sl_prices) // 2] if len(sl_prices) >= 2 else None

        consensus_signals.append({
            "symbol": symbol,
            "direction": direction,
            "strength": strength,
            "confidence": confidence,
            "weighted_votes": round(weighted_votes, 2),
            "consensus_count": len(kol_handles),
            "kol_handles": kol_handles,
            "kol_names": kol_display_names,
            "categories": sorted(categories),
            "category_diversity": category_diversity,
            "avg_kol_wr": avg_kol_wr,
            "avg_entry_price": avg_entry,
            "median_take_profit": median_tp,
            "median_stop_loss": median_sl,
            "tp_sources": len(tp_prices),
            "sl_sources": len(sl_prices),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        })

    # Sort by strength (ULTRA first) then weighted_votes descending
    strength_order = {"ULTRA": 0, "STRONG": 1, "MODERATE": 2}
    consensus_signals.sort(
        key=lambda s: (strength_order.get(s["strength"], 9), -s["weighted_votes"])
    )

    return consensus_signals


def compute_news_consensus(conn: sqlite3.Connection) -> list[dict]:
    """Compute consensus from cross-platform NEWS agreement.

    Unlike KOL consensus (first-person calls), this uses news-inferred signals.
    Requires 3+ different news platforms agreeing on symbol+direction to produce
    a signal. These are weaker than KOL calls, so confidence is capped lower.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=MAX_PREDICTION_AGE_HOURS)).isoformat()

    try:
        rows = conn.execute("""
            SELECT symbol, direction, platform, COUNT(*) as cnt
            FROM predictions
            WHERE status = 'ACTIVE'
              AND scraped_at >= ?
              AND analyst_category = 'news_inferred'
            GROUP BY symbol, direction, platform
        """, (cutoff,)).fetchall()
    except sqlite3.OperationalError:
        return []

    # Group by (symbol, direction) → set of platforms
    from collections import defaultdict
    groups: dict[tuple[str, str], dict] = defaultdict(lambda: {"platforms": set(), "total": 0})
    for r in rows:
        key = (r["symbol"].upper(), r["direction"].upper())
        groups[key]["platforms"].add(r["platform"])
        groups[key]["total"] += r["cnt"]

    signals = []
    for (symbol, direction), info in groups.items():
        n_platforms = len(info["platforms"])
        if n_platforms < 3:
            continue  # Need 3+ platforms for news consensus

        # Weaker confidence than KOL consensus
        if n_platforms >= 5:
            strength = "STRONG"
            confidence = 0.60
        elif n_platforms >= 4:
            strength = "MODERATE"
            confidence = 0.55
        else:  # 3 platforms
            strength = "MODERATE"
            confidence = 0.50

        signals.append({
            "symbol": symbol,
            "direction": direction,
            "strength": strength,
            "confidence": confidence,
            "weighted_votes": float(n_platforms),
            "consensus_count": info["total"],
            "kol_handles": [],
            "kol_names": list(info["platforms"]),
            "categories": ["news_inferred"],
            "category_diversity": 1,  # all news — 1 category
            "avg_kol_wr": 0.0,
            "avg_entry_price": None,
            "median_take_profit": None,
            "median_stop_loss": None,
            "tp_sources": 0,
            "sl_sources": 0,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "_news_consensus": True,  # tag for bridge to apply different rules
        })

    return signals


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Main entry point for GitHub Actions."""
    try:
        conn = get_db()
    except Exception as exc:
        print(f"[kol_consensus] Failed to connect to DB: {exc}")
        return

    try:
        signals = compute_kol_consensus(conn)
    except Exception as exc:
        print(f"[kol_consensus] Error computing KOL consensus: {exc}")
        signals = []

    # Also compute news consensus (cross-platform news agreement)
    try:
        news_signals = compute_news_consensus(conn)
        if news_signals:
            # Avoid duplicating symbols already in KOL consensus
            kol_keys = {(s["symbol"], s["direction"]) for s in signals}
            for ns in news_signals:
                if (ns["symbol"], ns["direction"]) not in kol_keys:
                    signals.append(ns)
            print(f"[kol_consensus] Added {len(news_signals)} news consensus signals")
    except Exception as exc:
        print(f"[kol_consensus] Error computing news consensus: {exc}")

    # Count by strength
    ultra = sum(1 for s in signals if s["strength"] == "ULTRA")
    strong = sum(1 for s in signals if s["strength"] == "STRONG")
    moderate = sum(1 for s in signals if s["strength"] == "MODERATE")

    print(f"[kol_consensus] {len(signals)} consensus signals "
          f"({ultra} ULTRA, {strong} STRONG, {moderate} MODERATE)")

    # Pass to bridge for pick generation
    if signals:
        try:
            from kol_consensus_bridge import generate_picks
            generate_picks(signals)
        except ImportError:
            # Fallback: try absolute import
            try:
                from predictions.kol.kol_consensus_bridge import generate_picks
                generate_picks(signals)
            except ImportError as exc:
                print(f"[kol_consensus] Bridge not available, writing raw signals: {exc}")
                # Write raw signals as fallback
                OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                OUTPUT_PATH.write_text(json.dumps(signals, indent=2, default=str))
                print(f"[kol_consensus] Wrote raw signals to {OUTPUT_PATH}")
    else:
        print("[kol_consensus] No consensus signals to process.")
        # Write empty picks file so downstream consumers don't error
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps([], indent=2))

    conn.close()


if __name__ == "__main__":
    run()
