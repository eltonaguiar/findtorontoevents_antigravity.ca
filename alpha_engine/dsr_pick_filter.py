#!/usr/bin/env python3
"""DSR (Deflated Sharpe Ratio) Pick Filter — Harvey-Liu multiple-testing correction.

Reads tools/deflated_sharpe_results.json to identify the 25 strategies that
survive the DSR haircut (out of 52 analysed).  The 27 noise strategies have
negative or insignificant DSR and are destroying aggregate Sharpe (-0.21).

Usage:
    from alpha_engine.dsr_pick_filter import (
        get_dsr_survivors,
        filter_picks_by_dsr,
        tag_picks_with_dsr,
        get_dsr_score_adjustment,
    )
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DIR.parent
_DSR_PATH = _REPO_ROOT / "tools" / "deflated_sharpe_results.json"
_OUTPUT_PATH = _DIR / "data" / "dsr_filtered_picks.json"

# Module-level cache
_DSR_CACHE: Optional[Dict[str, Any]] = None


def _load_dsr_data() -> Dict[str, Any]:
    """Load and cache DSR results. Returns empty dict on failure (fail-open)."""
    global _DSR_CACHE
    if _DSR_CACHE is not None:
        return _DSR_CACHE
    try:
        with open(_DSR_PATH, "r", encoding="utf-8") as f:
            _DSR_CACHE = json.load(f)
        logger.info("Loaded DSR results: %d strategies (%d surviving)",
                     _DSR_CACHE.get("summary", {}).get("strategies_analysed", 0),
                     _DSR_CACHE.get("summary", {}).get("strategies_surviving", 0))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load DSR results from %s: %s", _DSR_PATH, exc)
        _DSR_CACHE = {}
    return _DSR_CACHE


def get_dsr_survivors() -> Set[str]:
    """Return set of strategy keys that survived the DSR haircut."""
    data = _load_dsr_data()
    survivors = set()
    for entry in data.get("all_strategies", []):
        if entry.get("survives", False):
            survivors.add(entry["key"])
    return survivors


def get_dsr_noise() -> Set[str]:
    """Return set of strategy keys flagged as noise by DSR."""
    data = _load_dsr_data()
    noise = set()
    for entry in data.get("all_strategies", []):
        if not entry.get("survives", False):
            noise.add(entry["key"])
    return noise


def get_dsr_lookup() -> Dict[str, Dict[str, Any]]:
    """Return dict mapping strategy key -> full DSR record."""
    data = _load_dsr_data()
    return {e["key"]: e for e in data.get("all_strategies", [])}


def dsr_status(strategy_name: str) -> str:
    """Classify a strategy: 'VALIDATED', 'NOISE', or 'UNSCORED'.

    UNSCORED means the strategy was not in the DSR analysis (e.g. too few
    trades to qualify).  These are treated neutrally — no bonus or penalty.
    """
    survivors = get_dsr_survivors()
    noise = get_dsr_noise()
    if strategy_name in survivors:
        return "VALIDATED"
    if strategy_name in noise:
        return "NOISE"
    return "UNSCORED"


def get_dsr_score_adjustment(strategy_name: str) -> Tuple[int, str]:
    """Return (score_delta, reason) for quality gate scoring.

    VALIDATED: +8 bonus  (statistically significant edge survives multiple-testing)
    NOISE:    -15 penalty (DSR < 0, strategy is indistinguishable from luck)
    UNSCORED:  0 (not enough data to judge)
    """
    status = dsr_status(strategy_name)
    if status == "VALIDATED":
        return (+8, f"dsr_validated({strategy_name[:25]}):+8")
    elif status == "NOISE":
        return (-15, f"dsr_noise({strategy_name[:25]}):-15")
    return (0, "")


def tag_picks_with_dsr(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add dsr_status field to each pick. Non-destructive (returns same list)."""
    lookup = get_dsr_lookup()
    for pick in picks:
        strat = pick.get("strategy", "")
        status = dsr_status(strat)
        pick["dsr_status"] = status
        rec = lookup.get(strat)
        if rec:
            pick["dsr_value"] = rec.get("dsr", 0)
            pick["dsr_win_rate"] = rec.get("win_rate_pct", 0)
    return picks


def filter_picks_by_dsr(picks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only picks from DSR-VALIDATED or UNSCORED strategies.

    NOISE strategies are excluded. UNSCORED are kept (fail-open for new
    strategies that haven't accumulated enough trades for DSR analysis).
    """
    noise = get_dsr_noise()
    filtered = []
    removed = 0
    for pick in picks:
        strat = pick.get("strategy", "")
        if strat in noise:
            removed += 1
            continue
        filtered.append(pick)
    if removed:
        logger.info("DSR filter: removed %d picks from %d noise strategies",
                     removed, len(noise))
    return filtered


def write_dsr_filtered_picks(picks: List[Dict[str, Any]]) -> Path:
    """Tag picks with DSR status and write filtered output for downstream consumers."""
    tagged = tag_picks_with_dsr(picks)
    validated = [p for p in tagged if p.get("dsr_status") != "NOISE"]

    survivors = get_dsr_survivors()
    noise = get_dsr_noise()
    output = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "dsr_survivors_count": len(survivors),
        "dsr_noise_count": len(noise),
        "total_picks_input": len(picks),
        "total_picks_output": len(validated),
        "noise_picks_removed": len(picks) - len(validated),
        "validated_picks": [p for p in tagged if p.get("dsr_status") == "VALIDATED"],
        "unscored_picks": [p for p in tagged if p.get("dsr_status") == "UNSCORED"],
        "noise_picks_demoted": [
            {"symbol": p.get("symbol"), "strategy": p.get("strategy"),
             "dsr_value": p.get("dsr_value", 0)}
            for p in tagged if p.get("dsr_status") == "NOISE"
        ],
    }
    os.makedirs(_OUTPUT_PATH.parent, exist_ok=True)
    _OUTPUT_PATH.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    logger.info("Wrote DSR-filtered picks to %s (%d validated, %d noise removed)",
                _OUTPUT_PATH, len(validated), len(picks) - len(validated))
    return _OUTPUT_PATH
