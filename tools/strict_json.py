"""Strict-JSON serialisation for dashboard payloads.

`json.dump` emits bare `NaN` / `Infinity` by default, and `json.loads` accepts
them back — so a payload can round-trip through Python forever while being
invalid JSON that a browser refuses to parse. `ci.yml` rejects those tokens and
`tests/test_dashboard_payload_strict_json.py` enforces it.

Producers must call `save_strict_json()` (or `dumps_strict()`), which replaces
non-finite numbers with `null` and passes `allow_nan=False` so a regression
raises at write time instead of shipping an unparseable payload.
"""
from __future__ import annotations

import json
import math
import numbers
from pathlib import Path
from typing import Any


def clean_non_finite(obj: Any) -> Any:
    """Recursively replace NaN/±Infinity floats with None (JSON null)."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, numbers.Real):
        try:
            f = float(obj)
        except (TypeError, ValueError):
            return None
        return f if math.isfinite(f) else None
    if isinstance(obj, dict):
        return {k: clean_non_finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [clean_non_finite(v) for v in obj]
    return obj


def dumps_strict(obj: Any, **kwargs) -> str:
    """json.dumps that cannot emit NaN/Infinity. Raises if one survives cleaning."""
    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(clean_non_finite(obj), allow_nan=False, **kwargs)


def save_strict_json(path, obj: Any, **kwargs) -> None:
    """Write `obj` to `path` as strict JSON, creating parent directories."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps_strict(obj, **kwargs), encoding="utf-8")
