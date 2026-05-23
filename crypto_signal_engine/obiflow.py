"""Order Book Imbalance (OBI) / Order Flow Imbalance (OFI) signal.

OBI = (bid_volume - ask_volume) / (bid_volume + ask_volume)
  > +0.2 = buy pressure (bullish)
  < -0.2 = sell pressure (bearish)

OFI = rolling z-score of OBI over N periods
  Cold-start: first 12h fills with 0 (safe default, neither bullish nor bearish)

Shadow mode default (OBI_GATE_ENFORCE=0): logs signal but does not block picks.
Wire into passes_active_gate() for CRYPTO after 30-day shadow confirms signal quality.

## Wiring Plan
Target: audit_trail/quality_gates.py::passes_active_gate()
Integration gate: if asset_class == CRYPTO and OBI_GATE_ENFORCE=1:
    ofi = compute_ofi_zscore(symbol)
    if ofi < -2.0:  # strong sell pressure
        return False, M-040:obi_strong_sell_pressure
Target PR: after 30-day shadow with OBI_SHADOW_LOG=1
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

OBI_WINDOW = int(os.getenv("OBI_WINDOW", "48"))          # hours
OBI_SELL_THRESHOLD = float(os.getenv("OBI_SELL_THRESHOLD", "-2.0"))  # z-score
OBI_GATE_ENFORCE = os.getenv("OBI_GATE_ENFORCE", "0") == "1"
OBI_SHADOW_LOG = os.getenv("OBI_SHADOW_LOG", "1") == "1"

_OBI_LOG_PATH = Path("audit_dashboard/data/obi_shadow_log.json")


def compute_obi(bid_volume: float, ask_volume: float) -> float:
    """Order Book Imbalance: +1 = all bids, -1 = all asks."""
    total = bid_volume + ask_volume
    if total == 0:
        return 0.0
    return (bid_volume - ask_volume) / total


def compute_ofi_zscore(obi_history: list) -> float:
    """Z-score of OBI series. Returns 0.0 during cold-start (< 12 samples)."""
    if len(obi_history) < 12:
        return 0.0  # cold-start guard
    arr = np.array(obi_history[-OBI_WINDOW:], dtype=float)
    std = arr.std()
    if std == 0:
        return 0.0
    return float((arr[-1] - arr.mean()) / std)


def evaluate_obi_signal(
    symbol: str,
    bid_volume: Optional[float] = None,
    ask_volume: Optional[float] = None,
) -> dict:
    """
    Evaluate OBI signal for a symbol. Returns signal dict.
    bid_volume/ask_volume: if None, signal is unavailable (fail-open).
    """
    if bid_volume is None or ask_volume is None:
        return {
            "symbol": symbol,
            "obi": None,
            "ofi_zscore": 0.0,
            "signal": "unavailable",
            "blocked": False,
        }

    obi = compute_obi(bid_volume, ask_volume)
    # In production, obi_history would come from a rolling cache/DB.
    # Stub: single observation — zscore defaults to 0 (cold-start safe).
    ofi_z = compute_ofi_zscore([obi])

    blocked = OBI_GATE_ENFORCE and ofi_z < OBI_SELL_THRESHOLD
    signal = (
        "SELL_PRESSURE" if ofi_z < -1.0
        else "BUY_PRESSURE" if ofi_z > 1.0
        else "NEUTRAL"
    )

    result = {
        "symbol": symbol,
        "obi": round(obi, 4),
        "ofi_zscore": round(ofi_z, 4),
        "signal": signal,
        "blocked": blocked,
        "ts": datetime.now(timezone.utc).isoformat(),
        "enforce_mode": OBI_GATE_ENFORCE,
    }

    if OBI_SHADOW_LOG:
        _append_shadow_log(result)

    return result


def _append_shadow_log(entry: dict) -> None:
    try:
        if _OBI_LOG_PATH.exists():
            data = json.loads(_OBI_LOG_PATH.read_text())
        else:
            data = []
        data.append(entry)
        data = data[-500:]  # keep last 500
        _OBI_LOG_PATH.write_text(json.dumps(data, indent=2))
    except Exception as e:
        logger.debug("OBI shadow log write failed: %s", e)
