#!/usr/bin/env python3
"""
Strategy Leaderboard -- Automated ranking, promotion, and demotion system.
==========================================================================
Replaces manual strategy killing with continuous, data-driven tier classification.
Each scanner cycle updates strategy rankings based on closed pick performance,
applying confidence multipliers that boost proven winners and penalize losers.

Tiers:
  TOP_TIER        (top 10 by composite score)   -> 1.3x confidence boost
  PROVEN          (WR >50%, PF >1.2, >=20 trades) -> 1.1x boost
  NEUTRAL         (< 10 trades)                 -> 1.0x (unproven)
  UNDERPERFORMING (WR <40%, >=10 trades)        -> 0.5x penalty
  TOXIC           (WR <25% & >=15 trades, OR max consec losses >10) -> 0.2x penalty

Regime-aware: when regime data is available, computes separate leaderboards
per regime so a strategy that thrives in bull markets but dies in bear markets
gets the appropriate modifier for the current conditions.

stdlib only -- no external dependencies.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import standardized win rate calculation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import calculate_win_rate_from_picks as _shared_calc_wr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"

MIN_TRADES_FOR_RANKING = 5
MIN_TRADES_PROVEN = 20
MIN_TRADES_UNDERPERFORMING = 10
MIN_TRADES_TOXIC = 15
MAX_CONSEC_LOSSES_TOXIC = 10

TIER_MODIFIERS = {
    "TOP_TIER": 1.3,
    "PROVEN": 1.1,
    "NEUTRAL": 1.0,
    "UNDERPERFORMING": 0.5,
    "TOXIC": 0.2,
}

TOP_TIER_COUNT = 10
HISTORY_CAP = 90

REGIME_MAP_KEYS = {"BULLISH", "BEARISH", "RANGING", "CHOPPY", "TRANSITIONAL"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_float(val, default=0.0):
    """Convert value to float safely."""
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _compute_sharpe(pnl_series: list[float]) -> float:
    """Sharpe ratio of a PnL percentage series (annualized assuming daily)."""
    if len(pnl_series) < 2:
        return 0.0
    mean_pnl = sum(pnl_series) / len(pnl_series)
    variance = sum((p - mean_pnl) ** 2 for p in pnl_series) / (len(pnl_series) - 1)
    std_pnl = math.sqrt(variance) if variance > 0 else 0.0
    if std_pnl == 0:
        return 0.0
    # Annualize: assume ~365 trading days for crypto
    return (mean_pnl / std_pnl) * math.sqrt(365)


def _max_consecutive_losses(statuses: list[str]) -> int:
    """Count the longest streak of consecutive losses."""
    max_streak = 0
    current = 0
    for s in statuses:
        if s.upper() in ("LOST", "LOSS", "SL_HIT"):
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalize a value to [0, 1]."""
    if max_val <= min_val:
        return 0.5
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def _rolling_win_rate(picks: list[dict], window: int = 50) -> float:
    """Compute win rate over the last `window` RESOLVED picks.

    Standardized formula: wins / (wins + losses).
    Zero-PnL trades are excluded from BOTH; open/unresolved picks are excluded.
    Uses shared.calculate_win_rate_from_picks for consistency.
    """
    return _shared_calc_wr(picks, pnl_key="pnl_pct", status_key="status", window=window)


def _is_win(pick: dict) -> bool:
    """Determine if a pick was a win (pnl > 0)."""
    status = str(pick.get("status", "")).upper()
    if status in ("WON", "WIN", "TP_HIT"):
        return True
    pnl = _safe_float(pick.get("pnl_pct"), None)
    if pnl is not None and pnl > 0:
        return True
    exit_reason = str(pick.get("exit_reason", "")).upper()
    if exit_reason == "TP_HIT":
        return True
    return False


def _is_loss(pick: dict) -> bool:
    """Determine if a pick was a loss (pnl < 0). Zero-PnL is NOT a loss."""
    status = str(pick.get("status", "")).upper()
    if status in ("LOST", "LOSS", "SL_HIT"):
        return True
    pnl = _safe_float(pick.get("pnl_pct"), None)
    if pnl is not None and pnl < 0:
        return True
    exit_reason = str(pick.get("exit_reason", "")).upper()
    if exit_reason == "SL_HIT":
        return True
    return False


def _is_flat(pick: dict) -> bool:
    """Determine if a pick resolved flat (near-zero pnl) rather than win/loss."""
    if _is_win(pick) or _is_loss(pick):
        return False
    status = str(pick.get("status", "")).upper()
    if status == "FLAT":
        return True
    pnl = _safe_float(pick.get("pnl_pct"), None)
    return pnl is not None and abs(pnl) <= 0.01


def _get_regime_label(pick: dict) -> str:
    """Extract normalized regime label from a pick."""
    regime = str(pick.get("regime_at_entry", "") or "").upper().strip()
    if regime in REGIME_MAP_KEYS:
        return regime
    # Map common aliases
    if regime in ("BULL", "UP", "UPTREND"):
        return "BULLISH"
    if regime in ("BEAR", "DOWN", "DOWNTREND"):
        return "BEARISH"
    if regime in ("RANGE", "SIDEWAYS", "FLAT"):
        return "RANGING"
    if regime in ("CHOP", "VOLATILE"):
        return "CHOPPY"
    return ""


# ---------------------------------------------------------------------------
# Core: compute_strategy_rankings
# ---------------------------------------------------------------------------
def compute_strategy_rankings(
    closed_picks: list[dict],
    regime: str | None = None,
) -> list[dict]:
    """
    Group closed picks by strategy, compute performance metrics for each
    strategy with >= MIN_TRADES_FOR_RANKING closed picks.

    Args:
        closed_picks: List of closed pick dicts (from closed_picks.json).
        regime: If provided, only use picks from this regime.

    Returns:
        Sorted list of strategy ranking dicts (best first by composite score).
    """
    # Filter by regime if requested
    if regime:
        regime_upper = regime.upper()
        closed_picks = [
            p for p in closed_picks
            if _get_regime_label(p) == regime_upper
        ]

    # Group by strategy
    by_strategy: dict[str, list[dict]] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "")
        if not strat:
            continue
        by_strategy.setdefault(strat, []).append(pick)

    rankings = []
    for strat_name, picks in by_strategy.items():
        if len(picks) < MIN_TRADES_FOR_RANKING:
            continue

        # Sort picks by entry date for rolling calculations
        picks.sort(key=lambda p: p.get("entry_date", "") or p.get("exit_date", ""))

        # Win rate (rolling 50)
        wr = _rolling_win_rate(picks, window=50)

        # PnL series
        pnl_series = [_safe_float(p.get("pnl_pct")) for p in picks]
        avg_pnl = sum(pnl_series) / len(pnl_series) if pnl_series else 0.0

        # Profit factor
        gross_wins = sum(p for p in pnl_series if p > 0)
        gross_losses = abs(sum(p for p in pnl_series if p < 0))
        pf = (gross_wins / gross_losses) if gross_losses > 0 else (
            10.0 if gross_wins > 0 else 0.0
        )

        # Sharpe
        sharpe = _compute_sharpe(pnl_series)

        # Max consecutive losses
        statuses = [str(p.get("status", "") or p.get("exit_reason", "")) for p in picks]
        max_consec = _max_consecutive_losses(statuses)

        # Consistency: 1 - (std of pnl / mean of abs pnl) -- lower variance = higher
        abs_pnls = [abs(p) for p in pnl_series if p != 0]
        if abs_pnls and len(pnl_series) >= 2:
            mean_abs = sum(abs_pnls) / len(abs_pnls)
            variance = sum((p - avg_pnl) ** 2 for p in pnl_series) / (len(pnl_series) - 1)
            std_pnl = math.sqrt(variance) if variance > 0 else 0.0
            consistency = max(0.0, 1.0 - (std_pnl / mean_abs)) if mean_abs > 0 else 0.0
        else:
            consistency = 0.5

        rankings.append({
            "strategy": strat_name,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "avg_pnl": round(avg_pnl, 6),
            "sharpe": round(sharpe, 4),
            "max_consec_losses": max_consec,
            "trades": len(picks),
            "consistency": round(consistency, 4),
        })

    # Compute composite scores
    if rankings:
        # Get ranges for normalization
        pf_values = [r["pf"] for r in rankings]
        sharpe_values = [r["sharpe"] for r in rankings]
        consistency_values = [r["consistency"] for r in rankings]

        pf_min, pf_max = min(pf_values), max(pf_values)
        sharpe_min, sharpe_max = min(sharpe_values), max(sharpe_values)
        cons_min, cons_max = min(consistency_values), max(consistency_values)

        for r in rankings:
            pf_norm = _normalize(r["pf"], pf_min, pf_max)
            sharpe_norm = _normalize(r["sharpe"], sharpe_min, sharpe_max)
            cons_norm = _normalize(r["consistency"], cons_min, cons_max)

            composite = (
                r["wr"] * 0.4
                + pf_norm * 0.3
                + sharpe_norm * 0.2
                + cons_norm * 0.1
            )
            r["composite_score"] = round(composite, 4)

    # Sort by composite score descending
    rankings.sort(key=lambda r: r.get("composite_score", 0), reverse=True)
    return rankings


# ---------------------------------------------------------------------------
# Core: classify_strategies
# ---------------------------------------------------------------------------
def classify_strategies(rankings: list[dict]) -> dict[str, list[dict]]:
    """
    Classify ranked strategies into tiers.

    Returns:
        Dict with keys: TOP_TIER, PROVEN, NEUTRAL, UNDERPERFORMING, TOXIC
        Each value is a list of ranking dicts with added 'tier' and 'modifier' fields.
    """
    tiers: dict[str, list[dict]] = {
        "TOP_TIER": [],
        "PROVEN": [],
        "NEUTRAL": [],
        "UNDERPERFORMING": [],
        "TOXIC": [],
    }

    # First pass: identify top 10 by composite score (already sorted)
    top_tier_names = set()
    for r in rankings[:TOP_TIER_COUNT]:
        # Must have minimum trades to be top-tier
        if r["trades"] >= MIN_TRADES_FOR_RANKING:
            top_tier_names.add(r["strategy"])

    for r in rankings:
        strat = r["strategy"]
        trades = r["trades"]
        wr = r["wr"]
        pf = r["pf"]
        max_consec = r["max_consec_losses"]

        # Classify
        if strat in top_tier_names:
            tier = "TOP_TIER"
        elif wr < 0.25 and trades >= MIN_TRADES_TOXIC:
            tier = "TOXIC"
        elif max_consec > MAX_CONSEC_LOSSES_TOXIC:
            tier = "TOXIC"
        elif wr < 0.40 and trades >= MIN_TRADES_UNDERPERFORMING:
            tier = "UNDERPERFORMING"
        elif wr > 0.50 and pf > 1.2 and trades >= MIN_TRADES_PROVEN:
            tier = "PROVEN"
        elif trades < MIN_TRADES_UNDERPERFORMING:
            tier = "NEUTRAL"
        else:
            tier = "NEUTRAL"

        r["tier"] = tier
        r["modifier"] = TIER_MODIFIERS[tier]
        tiers[tier].append(r)

    return tiers


# ---------------------------------------------------------------------------
# Core: get_strategy_modifier
# ---------------------------------------------------------------------------
def get_strategy_modifier(
    strategy_name: str,
    leaderboard_data: dict,
) -> float:
    """
    Returns the confidence multiplier for a given strategy.

    Args:
        strategy_name: Name of the strategy.
        leaderboard_data: Full leaderboard JSON dict (as saved to file).

    Returns:
        Float multiplier (1.0 if strategy not found).
    """
    if not leaderboard_data or not strategy_name:
        return 1.0

    for entry in leaderboard_data.get("rankings", []):
        if entry.get("strategy") == strategy_name:
            return _safe_float(entry.get("modifier"), 1.0)

    return 1.0


# ---------------------------------------------------------------------------
# Core: update_leaderboard
# ---------------------------------------------------------------------------
def update_leaderboard(
    closed_picks_path: str | Path | None = None,
    regime: str | None = None,
) -> dict:
    """
    Main entry point: reads closed picks, computes rankings, classifies,
    saves leaderboard JSON.

    Args:
        closed_picks_path: Path to closed_picks.json. Defaults to DATA_DIR.
        regime: Optional regime string to filter picks.

    Returns:
        The full leaderboard dict.
    """
    if closed_picks_path is None:
        closed_picks_path = DATA_DIR / "closed_picks.json"
    closed_picks_path = Path(closed_picks_path)

    # Load closed picks
    if not closed_picks_path.exists():
        logger.warning("No closed picks file at %s", closed_picks_path)
        return {}

    try:
        with open(closed_picks_path, "r", encoding="utf-8") as f:
            closed_picks = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load closed picks: %s", e)
        return {}

    if not isinstance(closed_picks, list):
        logger.error("closed_picks.json is not a list")
        return {}

    # Auto-detect regime from fast_regime.json if not provided
    effective_regime = regime
    if not effective_regime:
        try:
            regime_path = DATA_DIR / "fast_regime.json"
            if regime_path.exists():
                with open(regime_path, "r", encoding="utf-8") as f:
                    regime_data = json.load(f)
                effective_regime = str(regime_data.get("regime", "")).upper() or None
        except Exception:
            pass

    # Compute overall rankings (always, regardless of regime)
    all_rankings = compute_strategy_rankings(closed_picks, regime=None)
    all_tiers = classify_strategies(all_rankings)

    # Compute regime-specific rankings if regime available
    regime_rankings = None
    regime_tiers = None
    if effective_regime:
        regime_rankings = compute_strategy_rankings(closed_picks, regime=effective_regime)
        if regime_rankings:
            regime_tiers = classify_strategies(regime_rankings)

    # Use regime-specific if available and has data, otherwise fallback to overall
    if regime_tiers and regime_rankings:
        active_rankings = regime_rankings
        active_tiers = regime_tiers
    else:
        active_rankings = all_rankings
        active_tiers = all_tiers

    # Build output
    leaderboard = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime": effective_regime or "ALL",
        "total_strategies": len(active_rankings),
        "top_tier": [r["strategy"] for r in active_tiers.get("TOP_TIER", [])],
        "proven": [r["strategy"] for r in active_tiers.get("PROVEN", [])],
        "neutral": [r["strategy"] for r in active_tiers.get("NEUTRAL", [])],
        "underperforming": [r["strategy"] for r in active_tiers.get("UNDERPERFORMING", [])],
        "toxic": [r["strategy"] for r in active_tiers.get("TOXIC", [])],
        "rankings": active_rankings,
        "history": [],
    }

    # Load existing history and append
    leaderboard_path = DATA_DIR / "strategy_leaderboard.json"
    existing_history = []
    if leaderboard_path.exists():
        try:
            with open(leaderboard_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_history = existing.get("history", [])
        except Exception:
            pass

    # Add today's summary to history
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    promotions = len(active_tiers.get("TOP_TIER", [])) + len(active_tiers.get("PROVEN", []))
    demotions = len(active_tiers.get("UNDERPERFORMING", [])) + len(active_tiers.get("TOXIC", []))
    top_wr = active_rankings[0]["wr"] if active_rankings else 0.0

    # Avoid duplicate entries for same day
    existing_history = [h for h in existing_history if h.get("date") != today]
    existing_history.append({
        "date": today,
        "promotions": promotions,
        "demotions": demotions,
        "top_wr": round(top_wr, 4),
        "total_strategies": len(active_rankings),
        "regime": effective_regime or "ALL",
    })

    # Cap history
    if len(existing_history) > HISTORY_CAP:
        existing_history = existing_history[-HISTORY_CAP:]

    leaderboard["history"] = existing_history

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(leaderboard_path, "w", encoding="utf-8") as f:
            json.dump(leaderboard, f, indent=2, ensure_ascii=False)
        logger.info(
            "Leaderboard saved: %d strategies (%d top-tier, %d proven, %d underperforming, %d toxic)",
            len(active_rankings),
            len(active_tiers.get("TOP_TIER", [])),
            len(active_tiers.get("PROVEN", [])),
            len(active_tiers.get("UNDERPERFORMING", [])),
            len(active_tiers.get("TOXIC", [])),
        )
    except OSError as e:
        logger.error("Failed to save leaderboard: %s", e)

    return leaderboard


# ---------------------------------------------------------------------------
# Core: apply_leaderboard_to_picks
# ---------------------------------------------------------------------------
def apply_leaderboard_to_picks(
    picks: list[dict],
    leaderboard_data: dict,
) -> list[dict]:
    """
    Apply leaderboard modifiers to a list of picks.

    For each pick:
      - Multiplies confidence by the strategy's leaderboard modifier
      - Adds leaderboard_tier and leaderboard_modifier fields

    Args:
        picks: List of signal/pick dicts.
        leaderboard_data: Full leaderboard dict.

    Returns:
        Modified list of picks (same list, mutated in-place for efficiency).
    """
    if not leaderboard_data or not picks:
        return picks

    # Build a fast lookup from rankings
    modifier_map: dict[str, tuple[float, str]] = {}
    for entry in leaderboard_data.get("rankings", []):
        strat = entry.get("strategy", "")
        if strat:
            modifier_map[strat] = (
                _safe_float(entry.get("modifier"), 1.0),
                entry.get("tier", "NEUTRAL"),
            )

    for pick in picks:
        strat_name = pick.get("strategy", "")
        modifier, tier = modifier_map.get(strat_name, (1.0, "NEUTRAL"))

        # Apply modifier to confidence
        original_conf = _safe_float(pick.get("confidence"), 0.5)
        pick["confidence"] = round(original_conf * modifier, 4)
        pick["leaderboard_tier"] = tier
        pick["leaderboard_modifier"] = modifier

    return picks


# ---------------------------------------------------------------------------
# CLI entry point (for standalone testing / manual runs)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    regime_arg = None
    if len(sys.argv) > 1:
        regime_arg = sys.argv[1].upper()

    lb = update_leaderboard(regime=regime_arg)
    if lb:
        print(f"Leaderboard updated: {lb['total_strategies']} strategies")
        print(f"  Regime: {lb['regime']}")
        print(f"  TOP_TIER ({len(lb['top_tier'])}): {', '.join(lb['top_tier'][:5])}...")
        print(f"  PROVEN ({len(lb['proven'])}): {len(lb['proven'])} strategies")
        print(f"  NEUTRAL ({len(lb['neutral'])}): {len(lb['neutral'])} strategies")
        print(f"  UNDERPERFORMING ({len(lb['underperforming'])}): {len(lb['underperforming'])} strategies")
        print(f"  TOXIC ({len(lb['toxic'])}): {len(lb['toxic'])} strategies")

        if lb["rankings"]:
            print(f"\n  Best strategy: {lb['rankings'][0]['strategy']} "
                  f"(WR={lb['rankings'][0]['wr']:.1%}, PF={lb['rankings'][0]['pf']:.2f})")
    else:
        print("No leaderboard data (no closed picks?)")
