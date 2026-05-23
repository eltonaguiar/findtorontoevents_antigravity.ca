#!/usr/bin/env python3
"""
Optional isotonic / bucket corrections for scanner `ml_score` (0–1 scale).

Drop a JSON file at ``alpha_engine/data/scanner_calibration_config.json``.
If the file is missing, invalid, or ``"enabled": false``, this module is a no-op.

Schema (v1):
  {
    "enabled": true,
    "ml_score_buckets": [
      {"lo": 0.70, "hi": 1.0, "delta": 0.07}
    ]
  }

For each signal, the first bucket where ``lo <= ml_score <= hi`` applies ``delta``;
``ml_score`` is clamped to [0, 1]. Original value is stored in
``ml_score_pre_scanner_cal`` when a change is applied.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_CONFIG_PATH = _DATA_DIR / "scanner_calibration_config.json"


def apply_optional_scanner_calibration(signals: list[dict[str, Any]]) -> int:
    """Apply bucket deltas to ``ml_score``. Returns count of signals adjusted."""
    if not _CONFIG_PATH.exists():
        return 0
    try:
        raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return 0
    if not raw.get("enabled", True):
        return 0
    buckets = raw.get("ml_score_buckets")
    if not isinstance(buckets, list) or not buckets:
        return 0

    adjusted = 0
    for s in signals:
        try:
            ml = float(s.get("ml_score") or 0.0)
        except (TypeError, ValueError):
            continue
        delta = 0.0
        for b in buckets:
            if not isinstance(b, dict):
                continue
            try:
                lo = float(b.get("lo", 0.0))
                hi = float(b.get("hi", 1.0))
                d = float(b.get("delta", 0.0))
            except (TypeError, ValueError):
                continue
            if d == 0.0:
                continue
            if lo <= ml <= hi:
                delta = d
                break
        if delta == 0.0:
            continue
        new_ml = max(0.0, min(1.0, ml + delta))
        if abs(new_ml - ml) < 1e-9:
            continue
        s["ml_score_pre_scanner_cal"] = ml
        s["ml_score"] = round(new_ml, 3)
        adjusted += 1
    return adjusted
