#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strong Signal 5-Filter System
==============================
Data-backed filter pipeline that identifies the highest-quality picks.

Based on STRONG_SIGNALS_BLUEPRINT.md analysis of 788+ closed picks:
  - Confidence 0.60-0.70 = 61% WR (best), 0.70-0.80 = 55%, 0.80+ = 49%
  - R:R 2.0-2.5 = 73.7% WR, R:R < 1.5 = 39%
  - Stop distance 1.5-3% = optimal
  - Regime alignment is the #1 predictor

Exports:
  filter_strong_signals(picks, regime, closed_picks) -> list[dict]
  compute_strong_signal_score(pick, regime, strategy_stats) -> int
  is_strong_signal(pick, regime, strategy_stats) -> bool
  get_filter_report(picks, regime, closed_picks) -> dict
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regime alignment
_BULL_REGIMES = {"bullish", "leaning_bull", "strong_bull"}
_BEAR_REGIMES = {"bearish", "leaning_bear", "strong_bear"}
_NEUTRAL_REGIMES = {"choppy", "ranging", "neutral", "consolidation"}

# R:R thresholds
RR_HARD_MIN = 1.5
RR_SWEET_LOW = 2.0
RR_SWEET_HIGH = 2.5

# Confidence thresholds
CONF_NOISE_FLOOR = 0.55
CONF_MARGINAL_CEIL = 0.60
CONF_BEST_LOW = 0.60
CONF_BEST_HIGH = 0.70
CONF_GOOD_HIGH = 0.95      # Widened from 0.80 — legitimate high-conf picks were blocked
CONF_OVERFIT_FLOOR = 0.95   # Only flag >0.95 as overconfidence (was 0.80)

# Stop distance thresholds (as fraction of entry price)
STOP_SHAKEOUT = 0.01       # < 1% = shakeout risk
STOP_OPTIMAL_LOW = 0.015   # 1.5%
STOP_OPTIMAL_HIGH = 0.03   # 3%
STOP_WIDE_MAX = 0.04       # 4%

# Strategy validation thresholds
STRAT_MIN_TRADES_LOW = 5
STRAT_MIN_WR_LOW = 0.55
STRAT_MIN_TRADES_HIGH = 10
STRAT_MIN_WR_HIGH = 0.45

# Score threshold to qualify as "strong"
STRONG_SIGNAL_THRESHOLD = 25


# ---------------------------------------------------------------------------
# Helper: compute per-strategy stats from closed picks
# ---------------------------------------------------------------------------

def _compute_strategy_stats(closed_picks: list[dict] | None) -> dict[str, dict]:
    """Build {strategy_name: {total, wins, wr}} from closed picks."""
    if not closed_picks:
        return {}
    stats: dict[str, dict[str, Any]] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "")
        if not strat:
            continue
        status = (pick.get("status") or "").upper()
        if status not in ("WON", "LOST"):
            continue
        if strat not in stats:
            stats[strat] = {"total": 0, "wins": 0, "wr": 0.0}
        stats[strat]["total"] += 1
        if status == "WON":
            stats[strat]["wins"] += 1
    # Compute WR
    for s in stats.values():
        s["wr"] = s["wins"] / s["total"] if s["total"] > 0 else 0.0
    return stats


# ---------------------------------------------------------------------------
# Helper: extract pick fields safely
# ---------------------------------------------------------------------------

def _pick_direction(pick: dict) -> str:
    """Return normalized direction: 'LONG' or 'SHORT'."""
    d = (pick.get("direction") or pick.get("signal_type") or "BUY").upper()
    return "SHORT" if d in ("SELL", "SHORT") else "LONG"


def _pick_rr(pick: dict) -> float:
    """Extract risk:reward ratio from pick."""
    rr = pick.get("risk_reward")
    if rr is not None:
        try:
            return float(rr)
        except (TypeError, ValueError):
            pass
    # Compute from entry/tp/sl if not present
    entry = pick.get("entry_price") or 0
    tp = pick.get("take_profit") or 0
    sl = pick.get("stop_loss") or 0
    if entry <= 0 or tp <= 0 or sl <= 0:
        return 0.0
    direction = _pick_direction(pick)
    if direction == "LONG":
        reward = tp - entry
        risk = entry - sl
    else:
        reward = entry - tp
        risk = sl - entry
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def _pick_stop_distance(pick: dict) -> float:
    """Compute stop distance as fraction of entry price."""
    entry = pick.get("entry_price") or 0
    sl = pick.get("stop_loss") or 0
    if entry <= 0 or sl <= 0:
        return 0.0
    return abs(entry - sl) / entry


def _pick_confidence(pick: dict) -> float:
    """Extract confidence, normalized to 0-1."""
    conf = pick.get("confidence") or 0
    if conf > 1.0:
        conf = conf / 100.0
    return conf


# ---------------------------------------------------------------------------
# Individual filter functions
# ---------------------------------------------------------------------------

def _filter1_regime_alignment(pick: dict, regime: str) -> tuple[bool, str, int]:
    """Filter 1: Regime Alignment (HARD gate).

    Returns (passed, reason, score_adjustment).
    """
    direction = _pick_direction(pick)
    regime_lower = regime.lower()

    if direction == "LONG":
        if regime_lower in _BULL_REGIMES:
            return True, "LONG aligned with bullish regime", 0
        elif regime_lower in _NEUTRAL_REGIMES:
            return True, "LONG in neutral regime (confidence reduced)", -5
        else:
            return False, f"LONG blocked in {regime} regime", 0
    else:  # SHORT
        if regime_lower in _BEAR_REGIMES:
            return True, "SHORT aligned with bearish regime", 0
        elif regime_lower in _NEUTRAL_REGIMES:
            return True, "SHORT in neutral regime (confidence reduced)", -5
        else:
            return False, f"SHORT blocked in {regime} regime", 0


def _filter2_risk_reward(pick: dict) -> tuple[bool, str, int]:
    """Filter 2: R:R >= 1.5 (HARD gate).

    Returns (passed, reason, score_adjustment).
    """
    rr = _pick_rr(pick)
    if rr <= 0:
        # Can't compute R:R -- allow but no bonus
        return True, f"R:R not computable (missing TP/SL)", -3
    if rr < RR_HARD_MIN:
        return False, f"R:R {rr:.2f} < {RR_HARD_MIN} (39% WR zone)", 0
    if RR_SWEET_LOW <= rr <= RR_SWEET_HIGH:
        return True, f"R:R {rr:.2f} in sweet spot 2.0-2.5 (73.7% WR)", 5
    if rr > RR_SWEET_HIGH:
        return True, f"R:R {rr:.2f} > 2.5 (TP may be unreachable)", 1
    # 1.5 <= rr < 2.0
    return True, f"R:R {rr:.2f} acceptable", 3


def _filter3_strategy_validation(pick: dict, strategy_stats: dict[str, dict]) -> tuple[bool, str, int]:
    """Filter 3: Strategy Validation (SOFT gate for unproven, HARD gate for proven losers).

    Validated: 10+ closed trades at >= 45% WR, or 5+ at >= 55% WR -> full bonus.
    Unproven (< 5 trades or 0 trades) -> pass with penalty (can't validate yet).
    Proven losers (5+ trades failing WR thresholds) -> HARD block.

    Returns (passed, reason, score_adjustment).
    """
    strat = pick.get("strategy", "")
    stats = strategy_stats.get(strat)

    if not stats:
        # No data -- allow with penalty (strategy hasn't had a chance to prove itself)
        return True, f"strategy '{strat}' unvalidated (0 trades, penalty)", -10

    total = stats["total"]
    wr = stats["wr"]

    # Path 1: 10+ trades at >= 45% WR -> validated
    if total >= STRAT_MIN_TRADES_HIGH and wr >= STRAT_MIN_WR_HIGH:
        bonus = 8 if wr >= 0.55 else 4
        return True, f"strategy validated: {total} trades, {wr:.0%} WR", bonus

    # Path 2: 5+ trades at >= 55% WR -> early-validated
    if total >= STRAT_MIN_TRADES_LOW and wr >= STRAT_MIN_WR_LOW:
        return True, f"strategy early-validated: {total} trades, {wr:.0%} WR", 6

    # Proven losers: 10+ trades below 45% WR -> HARD block
    if total >= STRAT_MIN_TRADES_HIGH and wr < STRAT_MIN_WR_HIGH:
        return False, f"strategy failing: {total} trades, {wr:.0%} WR < {STRAT_MIN_WR_HIGH:.0%}", 0

    # 5-9 trades below 55% WR -> HARD block (enough data to know it's underperforming)
    if total >= STRAT_MIN_TRADES_LOW and wr < STRAT_MIN_WR_LOW:
        return False, f"strategy weak: {total} trades, {wr:.0%} WR < {STRAT_MIN_WR_LOW:.0%}", 0

    # < 5 trades -- unproven, allow with penalty
    return True, f"strategy unproven: {total} trades (penalty)", -5


def _filter4_confidence(pick: dict) -> tuple[bool, str, int]:
    """Filter 4: Confidence 0.55-0.80 (HARD gate).

    Returns (passed, reason, score_adjustment).
    """
    conf = _pick_confidence(pick)

    if conf < CONF_NOISE_FLOOR:
        return False, f"confidence {conf:.2f} < {CONF_NOISE_FLOOR} (noise)", 0

    if CONF_NOISE_FLOOR <= conf < CONF_MARGINAL_CEIL:
        return True, f"confidence {conf:.2f} marginal (penalty)", 2

    if CONF_BEST_LOW <= conf <= CONF_BEST_HIGH:
        return True, f"confidence {conf:.2f} in sweet spot 0.60-0.70 (61% WR)", 8

    if CONF_BEST_HIGH < conf <= 0.80:
        return True, f"confidence {conf:.2f} good zone 0.70-0.80 (55% WR)", 6

    if 0.80 < conf <= CONF_GOOD_HIGH:
        return True, f"confidence {conf:.2f} high-confidence zone 0.80-0.95", 4

    # conf > 0.95
    return True, f"confidence {conf:.2f} > 0.95 (possible overconfidence)", 2


def _filter5_stop_distance(pick: dict) -> tuple[bool, str, int]:
    """Filter 5: Stop Distance 1.5-4% (SOFT gate -- never blocks, only penalizes).

    Returns (passed, reason, score_adjustment).
    """
    stop_dist = _pick_stop_distance(pick)

    if stop_dist <= 0:
        # Can't compute -- no penalty, no bonus
        return True, "stop distance not computable", 0

    if stop_dist < STOP_SHAKEOUT:
        return True, f"stop {stop_dist:.1%} < 1% (shakeout risk)", -3

    if STOP_SHAKEOUT <= stop_dist < STOP_OPTIMAL_LOW:
        return True, f"stop {stop_dist:.1%} tight but acceptable", 2

    if STOP_OPTIMAL_LOW <= stop_dist <= STOP_OPTIMAL_HIGH:
        return True, f"stop {stop_dist:.1%} optimal zone 1.5-3%", 5

    if STOP_OPTIMAL_HIGH < stop_dist <= STOP_WIDE_MAX:
        return True, f"stop {stop_dist:.1%} slightly wide", 1

    # > 4%
    return True, f"stop {stop_dist:.1%} > 4% (poor risk management)", -2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_strong_signal_score(pick: dict, regime: str,
                                strategy_stats: dict[str, dict] | None = None) -> int:
    """Compute a 0-100 strong signal score for a single pick.

    The score is the sum of bonuses/penalties from all 5 filters,
    mapped onto a 0-100 scale with a base of 50.
    Hard-gate failures return 0.
    """
    if strategy_stats is None:
        strategy_stats = {}

    total_adj = 0
    filters = [
        _filter1_regime_alignment(pick, regime),
        _filter2_risk_reward(pick),
        _filter3_strategy_validation(pick, strategy_stats),
        _filter4_confidence(pick),
        _filter5_stop_distance(pick),
    ]

    for passed, _reason, adj in filters:
        if not passed:
            return 0  # Hard gate failure = score 0
        total_adj += adj

    # Base 50 + adjustments, clamped to 0-100
    # Max possible: 50 + 5 + 8 + 8 + 5 = 76
    # Typical strong: 50 + 3 + 6 + 6 + 2 = 67
    score = 50 + total_adj
    return max(0, min(100, score))


def is_strong_signal(pick: dict, regime: str,
                     strategy_stats: dict[str, dict] | None = None) -> bool:
    """Return True if pick passes all 5 filters and meets score threshold."""
    score = compute_strong_signal_score(pick, regime, strategy_stats)
    return score >= STRONG_SIGNAL_THRESHOLD


def get_filter_report(picks: list[dict], regime: str,
                      closed_picks: list[dict] | None = None) -> dict:
    """Return a diagnostic report with pass/fail counts per filter.

    Returns dict with:
      - total_input: int
      - total_strong: int
      - filter_stats: {filter_name: {passed: int, failed: int, reasons: list}}
      - strong_picks: list of symbols that passed
    """
    strategy_stats = _compute_strategy_stats(closed_picks)

    filter_names = [
        "1_regime_alignment",
        "2_risk_reward",
        "3_strategy_validation",
        "4_confidence",
        "5_stop_distance",
    ]
    filter_funcs = [
        lambda p: _filter1_regime_alignment(p, regime),
        lambda p: _filter2_risk_reward(p),
        lambda p: _filter3_strategy_validation(p, strategy_stats),
        lambda p: _filter4_confidence(p),
        lambda p: _filter5_stop_distance(p),
    ]

    stats = {name: {"passed": 0, "failed": 0, "fail_reasons": []} for name in filter_names}
    strong_symbols = []
    total_strong = 0

    for pick in picks:
        all_passed = True
        for name, func in zip(filter_names, filter_funcs):
            passed, reason, _adj = func(pick)
            if passed:
                stats[name]["passed"] += 1
            else:
                stats[name]["failed"] += 1
                stats[name]["fail_reasons"].append(
                    f"{pick.get('symbol', '?')} ({pick.get('strategy', '?')}): {reason}"
                )
                all_passed = False

        if all_passed:
            score = compute_strong_signal_score(pick, regime, strategy_stats)
            if score >= STRONG_SIGNAL_THRESHOLD:
                total_strong += 1
                strong_symbols.append(pick.get("symbol", "?"))

    return {
        "total_input": len(picks),
        "total_strong": total_strong,
        "regime": regime,
        "filter_stats": stats,
        "strong_symbols": strong_symbols,
    }


def filter_strong_signals(picks: list[dict], regime: str,
                          closed_picks: list[dict] | None = None) -> list[dict]:
    """Apply the 5-filter pipeline. Returns only strong signals.

    Each pick in the returned list is tagged with:
      - strong_signal: True
      - strong_signal_score: 0-100
      - _strong_filter_details: list of per-filter results

    Picks that fail are NOT modified (caller can still use them).
    """
    strategy_stats = _compute_strategy_stats(closed_picks)
    strong = []

    filter_names = [
        "regime_alignment",
        "risk_reward",
        "strategy_validation",
        "confidence",
        "stop_distance",
    ]

    for pick in picks:
        details = []
        all_passed = True

        # Run all 5 filters
        results = [
            _filter1_regime_alignment(pick, regime),
            _filter2_risk_reward(pick),
            _filter3_strategy_validation(pick, strategy_stats),
            _filter4_confidence(pick),
            _filter5_stop_distance(pick),
        ]

        for name, (passed, reason, adj) in zip(filter_names, results):
            details.append({"filter": name, "passed": passed, "reason": reason, "adj": adj})
            if not passed:
                all_passed = False

        score = compute_strong_signal_score(pick, regime, strategy_stats) if all_passed else 0
        is_strong = all_passed and score >= STRONG_SIGNAL_THRESHOLD

        # Tag the pick (mutates in place)
        pick["strong_signal"] = is_strong
        pick["strong_signal_score"] = score
        pick["_strong_filter_details"] = details

        if is_strong:
            strong.append(pick)

    return strong


def tag_all_picks(picks: list[dict], regime: str,
                  closed_picks: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Tag ALL picks with strong_signal fields and return (all_picks, strong_only).

    Unlike filter_strong_signals which only returns strong picks,
    this function tags every pick and returns both the full list and the filtered subset.
    Used by production_scanner to tag without blocking.
    """
    strategy_stats = _compute_strategy_stats(closed_picks)
    strong_only = []

    for pick in picks:
        details = []
        all_passed = True

        results = [
            _filter1_regime_alignment(pick, regime),
            _filter2_risk_reward(pick),
            _filter3_strategy_validation(pick, strategy_stats),
            _filter4_confidence(pick),
            _filter5_stop_distance(pick),
        ]

        filter_names = [
            "regime_alignment", "risk_reward", "strategy_validation",
            "confidence", "stop_distance",
        ]

        for name, (passed, reason, adj) in zip(filter_names, results):
            details.append({"filter": name, "passed": passed, "reason": reason, "adj": adj})
            if not passed:
                all_passed = False

        score = compute_strong_signal_score(pick, regime, strategy_stats) if all_passed else 0
        is_strong = all_passed and score >= STRONG_SIGNAL_THRESHOLD

        pick["strong_signal"] = is_strong
        pick["strong_signal_score"] = score
        pick["_strong_filter_details"] = details

        if is_strong:
            strong_only.append(pick)

    return picks, strong_only


def write_strong_picks(strong_picks: list[dict], data_dir: Path | str) -> Path:
    """Write strong_picks.json for the smart picks engine.

    Only includes picks that passed all 5 filters.
    """
    import math as _math

    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        if isinstance(obj, float) and (_math.isnan(obj) or _math.isinf(obj)):
            return None
        if hasattr(obj, "item"):
            v = obj.item()
            if isinstance(v, float) and (_math.isnan(v) or _math.isinf(v)):
                return None
            return v
        return obj

    from datetime import datetime, timezone

    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "strong_picks.json"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "filter_system": "strong_signal_5filter_v1",
        "total_strong": len(strong_picks),
        "picks": _sanitize(strong_picks),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return out_path
