"""
Macro overlay hook for Smart Picks — reads alpha_engine/data/macro_factors_snapshot.json.

No synthetic factor values are invented. When the snapshot has a non-empty
``series`` object, optional per-asset-class scores can be merged onto the
scored pick row for hf_quality_gate and auditing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SNAPSHOT = _REPO_ROOT / "alpha_engine" / "data" / "macro_factors_snapshot.json"
_WEIGHTS = _REPO_ROOT / "alpha_engine" / "data" / "macro_regression_weights.json"


def _load_snapshot() -> dict[str, Any]:
    if not _SNAPSHOT.is_file():
        return {}
    try:
        raw = json.loads(_SNAPSHOT.read_text(encoding="utf-8", errors="replace"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _load_regression_weights() -> dict[str, Any]:
    if not _WEIGHTS.is_file():
        return {}
    try:
        raw = json.loads(_WEIGHTS.read_text(encoding="utf-8", errors="replace"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def linear_macro_score_from_series(
    series: dict[str, Any], weights_doc: Optional[dict[str, Any]] = None
) -> Optional[float]:
    """
    score = intercept + sum(weight[k] * series[k]) for keys present in both.
    Returns None if weights are empty or no overlapping numeric factors.
    """
    wd = weights_doc if weights_doc is not None else _load_regression_weights()
    wmap = wd.get("weights")
    if not isinstance(wmap, dict) or not wmap:
        return None
    try:
        total = float(wd.get("intercept", 0) or 0)
    except (TypeError, ValueError):
        total = 0.0
    used = 0
    for key, coef in wmap.items():
        if key not in series:
            continue
        try:
            total += float(coef) * float(series[key])
            used += 1
        except (TypeError, ValueError):
            continue
    if used == 0:
        return None
    return total


def attach_macro_overlay(scored: dict[str, Any], source_pick: Optional[dict] = None) -> None:
    """Mutate ``scored`` with macro_score / macro_overlay_meta when data exists."""
    snap = _load_snapshot()
    series = snap.get("series")
    if not isinstance(series, dict) or not series:
        return

    ac = str(scored.get("asset_class") or "").upper() or "CRYPTO"
    by_ac = snap.get("by_asset_class")
    score_val = None
    if isinstance(by_ac, dict) and ac in by_ac:
        cell = by_ac[ac]
        if isinstance(cell, dict) and cell.get("macro_score") is not None:
            try:
                score_val = float(cell["macro_score"])
            except (TypeError, ValueError):
                score_val = None
        elif isinstance(cell, (int, float)):
            score_val = float(cell)

    scored["macro_overlay_as_of"] = snap.get("as_of")
    if score_val is None and isinstance(series, dict) and series:
        lin = linear_macro_score_from_series(series)
        if lin is not None:
            score_val = lin
            scored["macro_overlay_source"] = "macro_regression_weights.json+snapshot"
    if score_val is not None:
        scored["macro_score"] = round(float(score_val), 6)
    if scored.get("macro_overlay_source") is None:
        scored["macro_overlay_source"] = snap.get("source", "macro_factors_snapshot.json")
