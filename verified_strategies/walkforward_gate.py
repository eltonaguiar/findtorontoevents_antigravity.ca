"""Read WALKFORWARD_REPORT.json gates for verified production sidecars."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

_REPORT = Path(__file__).resolve().parent / "WALKFORWARD_REPORT.json"


def _load_report() -> Dict[str, Any]:
    if not _REPORT.exists():
        return {}
    try:
        return json.loads(_REPORT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def sleeve_verdict(sleeve_key: str) -> Optional[str]:
    """Return PASS | FAIL | INSUFFICIENT | None if missing."""
    data = _load_report()
    block = data.get(sleeve_key)
    if not isinstance(block, dict):
        return None
    return block.get("verdict")


def donchian_oos_allowed() -> bool:
    """CRYPTO_VERIFIED_DONCHIAN requires OOS walk-forward PASS."""
    v = sleeve_verdict("crypto_donchian")
    return v == "PASS"


def vwap_reversion_oos_allowed() -> bool:
    v = sleeve_verdict("vwap_reversion")
    return v == "PASS"


def bollinger_mr_oos_allowed() -> bool:
    v = sleeve_verdict("bollinger_mr")
    return v == "PASS"


def dual_momentum_oos_allowed() -> bool:
    v = sleeve_verdict("dual_momentum")
    return v == "PASS"


def etf_dual_momentum_oos_allowed() -> bool:
    """Advisory: ETF pilot prefers OOS PASS (not a hard scanner block)."""
    v = sleeve_verdict("etf_dual_momentum")
    return v == "PASS"