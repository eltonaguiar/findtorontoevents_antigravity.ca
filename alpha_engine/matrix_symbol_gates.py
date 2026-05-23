"""
Hard gates from matrix_symbol_gates.json (system × symbol allow/block from closed picks).

Disable with env ``MATRIX_SYMBOL_GATES=0``. Block rules win over allow rules.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent
_DEFAULT_PATH = _ROOT / "data" / "matrix_symbol_gates.json"

_DATA: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _DATA
    if _DATA is not None:
        return _DATA
    path = _DEFAULT_PATH
    try:
        with path.open(encoding="utf-8") as f:
            _DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logger.debug("matrix_symbol_gates: no data (%s)", e)
        _DATA = {}
    return _DATA


def reload_matrix_symbol_gates() -> None:
    """Test hook: clear cache."""
    global _DATA
    _DATA = None


def matrix_symbol_gate_blocks(pick: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Returns (True, reason) if pick should be blocked from active display.
    """
    if os.environ.get("MATRIX_SYMBOL_GATES", "1").strip() in ("0", "false", "False", "no"):
        return False, ""

    data = _load()
    if not data:
        return False, ""

    sys_raw = str(pick.get("source_system") or pick.get("source") or "").strip().lower()
    if not sys_raw:
        return False, ""

    sym = str(pick.get("symbol") or "").strip().upper()
    if not sym:
        return False, ""

    block: Dict[str, List[str]] = data.get("block") or {}
    allow: Dict[str, List[str]] = data.get("allow") or {}

    blocked = block.get(sys_raw) or []
    if sym in blocked:
        return True, f"matrix_block:{sys_raw}:{sym}"

    allowed = allow.get(sys_raw) or []
    if allowed and sym not in allowed:
        return True, f"matrix_allow_only:{sys_raw}:{sym}"

    return False, ""
