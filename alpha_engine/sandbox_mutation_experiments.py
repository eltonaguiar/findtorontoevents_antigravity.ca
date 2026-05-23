"""
SANDBOX experiment relabels: subset of parent strategies get strategy id + trust_tier.

Config: alpha_engine/data/sandbox_mutation_experiments.json
Disable: SANDBOX_MUTATION_EXPERIMENTS=0
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent
_CONFIG_PATH = _ROOT / "data" / "sandbox_mutation_experiments.json"

_CFG: Optional[Dict[str, Any]] = None


def _normalize_dir(d: str) -> str:
    u = (d or "").strip().upper()
    if u in ("BUY", "LONG"):
        return "LONG"
    if u in ("SELL", "SHORT"):
        return "SHORT"
    return u


def _pick_timeframe_bucket(pick: Dict[str, Any]) -> str:
    """Prefer explicit pick fields, then classify_timeframe()."""
    for key in ("trade_timeframe", "timeframe", "mode", "trade_tf"):
        v = pick.get(key)
        if v is None:
            continue
        u = str(v).strip().upper()
        if u in ("SCALP", "INTRADAY", "SWING", "POSITION"):
            return u
    try:
        from cross_aggregation.timeframe_classifier import classify_timeframe

        return str(
            classify_timeframe(pick, str(pick.get("source_system") or ""))
        ).upper()
    except ImportError:
        return ""


def _load_cfg() -> Dict[str, Any]:
    global _CFG
    if _CFG is not None:
        return _CFG
    try:
        with _CONFIG_PATH.open(encoding="utf-8") as f:
            _CFG = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logger.debug("sandbox_mutation_experiments: %s", e)
        _CFG = {"experiments": []}
    return _CFG


def reload_sandbox_mutation_experiments() -> None:
    global _CFG
    _CFG = None


def apply_sandbox_experiment_relabels(pick: Dict[str, Any]) -> None:
    """Mutate pick in place when it matches an experiment row."""
    if os.environ.get("SANDBOX_MUTATION_EXPERIMENTS", "1").strip() in (
        "0",
        "false",
        "False",
        "no",
    ):
        return

    cfg = _load_cfg()
    experiments: List[Dict[str, Any]] = cfg.get("experiments") or []
    strategy = str(pick.get("strategy") or "").strip()
    if not strategy:
        return

    sym = str(pick.get("symbol") or "").strip().upper()
    direction = _normalize_dir(str(pick.get("direction") or pick.get("signal_type") or ""))

    for ex in experiments:
        parents = ex.get("parent_strategies") or []
        if strategy not in parents:
            continue
        ex_id = str(ex.get("id") or "").strip()
        if not ex_id:
            continue

        allowed_syms = ex.get("allowed_symbols")
        if isinstance(allowed_syms, list) and allowed_syms:
            allow_u = {str(s).strip().upper() for s in allowed_syms}
            if sym not in allow_u:
                continue

        allowed_dirs = ex.get("allowed_directions")
        if isinstance(allowed_dirs, list) and allowed_dirs:
            ad = {_normalize_dir(str(x)) for x in allowed_dirs}
            if direction and direction not in ad:
                continue

        allowed_tf = ex.get("allowed_timeframes")
        if isinstance(allowed_tf, list) and allowed_tf:
            tf = _pick_timeframe_bucket(pick)
            tf_u = {str(x).strip().upper() for x in allowed_tf}
            if not tf or tf not in tf_u:
                continue

        tier = str(ex.get("trust_tier") or "SANDBOX").strip().upper()
        pick["strategy"] = ex_id
        pick["trust_tier"] = tier
        pick["_sandbox_experiment"] = ex_id
        logger.debug(
            "sandbox experiment %s relabel from parent %s sym=%s",
            ex_id,
            strategy,
            sym,
        )
        return
