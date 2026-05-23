"""
Anti-Overfit Gate — Hard gate preventing unvalidated strategies from Smart Picks.

Root cause: backtest-forward correlation is -0.91 because overfit strategies go
live without any walk-forward validation. The quan_engine/backtest/anti_overfit.py
module implements an 8-check suite, but it was NEVER enforced as a gate.

This module reads alpha_engine/data/anti_overfit_registry.json to determine
which strategies have passed the 8-check anti-overfit validation:
  1. OOS Sharpe >= 70% of IS
  2. OOS WR within 10pp of IS
  3. PF > 1.5 in ALL OOS windows
  4. Max consecutive losses <= 5
  5. Max drawdown <= 15%
  6. No single trade > 20% of total PnL
  7. KS test p > 0.05 (IS vs OOS distributions similar)
  8. Profitable in >= 67% of OOS windows

FAIL-CLOSED: strategies not in the registry are treated as unvalidated.

Usage:
    from alpha_engine.anti_overfit_gate import (
        has_passed_anti_overfit,
        get_anti_overfit_score_adjustment,
    )
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Set, Tuple

logger = logging.getLogger(__name__)

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data", "anti_overfit_registry.json",
)

_REGISTRY_CACHE: Dict[str, Any] | None = None


def _load_registry() -> Dict[str, Any]:
    """Load the anti-overfit registry (cached after first call)."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            _REGISTRY_CACHE = json.load(f)
        logger.info(
            "Loaded anti-overfit registry: %d validated strategies",
            len(_REGISTRY_CACHE.get("validated_strategies", {})),
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load anti-overfit registry: %s", exc)
        _REGISTRY_CACHE = {}
    return _REGISTRY_CACHE


def get_validated_strategies() -> Set[str]:
    """Return set of strategy names that have passed the 8-check anti-overfit suite."""
    data = _load_registry()
    return set(data.get("validated_strategies", {}).keys())


def get_gold_standard_strategies() -> Set[str]:
    """Return set of strategies that pass both DSR + FDR (highest confidence)."""
    data = _load_registry()
    return set(data.get("gold_standard", []))


def has_passed_anti_overfit(strategy_name: str) -> bool:
    """Check if a strategy has passed anti-overfit validation.

    FAIL-CLOSED: if strategy is not in the registry, it has NOT passed.
    This prevents unvalidated strategies from reaching Smart Picks.
    """
    validated = get_validated_strategies()
    return strategy_name in validated


def get_anti_overfit_score_adjustment(strategy_name: str) -> Tuple[int, str]:
    """Return (score_delta, reason) for quality gate scoring.

    VALIDATED (gold_standard): +5 bonus (passed DSR + FDR + anti-overfit)
    VALIDATED (standard):       0 neutral (passed anti-overfit, no extra bonus)
    NOT VALIDATED:             -20 penalty (unvalidated — overfit risk)
    """
    if not has_passed_anti_overfit(strategy_name):
        return (-20, f"anti_overfit_unvalidated({strategy_name[:30]}):-20")

    gold = get_gold_standard_strategies()
    if strategy_name in gold:
        return (+5, f"anti_overfit_gold({strategy_name[:30]}):+5")

    return (0, "")


def register_strategy(strategy_name: str, check_results: Dict[str, Any],
                       passed: bool) -> None:
    """Add a strategy to the registry after running the 8-check suite.

    Only strategies that pass ALL 8 checks are added as validated.
    Failed strategies are logged but not added (fail-closed).
    """
    if not passed:
        logger.warning(
            "Strategy %s FAILED anti-overfit checks — not added to registry",
            strategy_name,
        )
        return

    data = _load_registry()
    if "validated_strategies" not in data:
        data["validated_strategies"] = {}

    from datetime import datetime, timezone
    data["validated_strategies"][strategy_name] = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "checks": check_results,
    }

    try:
        with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Registered %s in anti-overfit registry", strategy_name)
    except OSError as exc:
        logger.error("Failed to write anti-overfit registry: %s", exc)


def get_registry_stats() -> Dict[str, Any]:
    """Return summary stats for CI logging: approved count, gold count, etc."""
    data = _load_registry()
    validated = data.get("validated_strategies", {})
    gold = data.get("gold_standard", [])
    return {
        "approved": len(validated),
        "gold_standard": len(gold),
        "gold_names": sorted(gold),
        "strategy_names": sorted(validated.keys()),
    }


def audit_active_picks_against_registry(active_picks_path: str | None = None) -> Dict[str, Any]:
    """Check active_picks.json for strategies not in the anti-overfit registry.

    Returns dict with:
      - total_picks: number of active picks checked
      - approved: picks whose strategy IS in the registry
      - unapproved: picks whose strategy is NOT in the registry
      - unapproved_strategies: set of strategy names not in registry
      - smart_picks_blocked: strategies that would be hard-blocked from Smart Picks
    """
    if active_picks_path is None:
        active_picks_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "active_picks.json",
        )

    validated = get_validated_strategies()

    try:
        with open(active_picks_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_picks": 0, "approved": 0, "unapproved": 0,
                "unapproved_strategies": set(), "smart_picks_blocked": set()}

    picks = raw if isinstance(raw, list) else raw.get("picks", [])

    approved_count = 0
    unapproved_count = 0
    unapproved_strats: set = set()

    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or "unknown"
        if strat in validated:
            approved_count += 1
        else:
            unapproved_count += 1
            unapproved_strats.add(strat)

    result = {
        "total_picks": len(picks),
        "approved": approved_count,
        "unapproved": unapproved_count,
        "unapproved_strategies": unapproved_strats,
        "smart_picks_blocked": unapproved_strats,  # same set -- blocked from Smart Picks
    }

    if unapproved_strats:
        logger.warning(
            "ANTI-OVERFIT GATE: %d picks from %d unapproved strategies: %s",
            unapproved_count, len(unapproved_strats),
            ", ".join(sorted(unapproved_strats)[:10]),
        )
    else:
        logger.info("ANTI-OVERFIT GATE: all %d picks from approved strategies", len(picks))

    return result
