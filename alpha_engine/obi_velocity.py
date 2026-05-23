"""
OBI Velocity Module
====================
Tracks order book imbalance (OBI) history per symbol and computes velocity
(rate of change) features over multiple lookback windows.

Academic basis: EFMA 2025 paper shows Sharpe 3.04-3.63 when combining ML with
order flow velocity features. The *change* in OBI over 5/15/60 snapshots is a
stronger leading indicator than the absolute OBI value.

Features produced:
  - obi_delta_5:      OBI change over last 5 snapshots  (normalized [-1, 1])
  - obi_delta_15:     OBI change over last 15 snapshots (normalized [-1, 1])
  - obi_acceleration: second derivative (delta of delta) (normalized [-1, 1])
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default history file location (inside alpha_engine/data/)
_DEFAULT_HISTORY_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "obi_history.json"

# Maximum snapshots retained per symbol (prevents unbounded growth)
MAX_SNAPSHOTS = 100


def _load_history(history_file: Path) -> Dict:
    """Load OBI history from JSON file. Returns empty dict if missing/corrupt."""
    try:
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"OBI history load failed ({history_file}): {e}")
    return {}


def _save_history(history: Dict, history_file: Path) -> None:
    """Persist OBI history to JSON. Creates parent dirs if needed."""
    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, separators=(",", ":"))
    except OSError as e:
        logger.error(f"OBI history save failed ({history_file}): {e}")


def record_obi_snapshot(
    symbol: str,
    obi_value: float,
    history: Dict,
    timestamp: Optional[str] = None,
) -> None:
    """Append a single OBI observation to the in-memory history dict.

    Args:
        symbol:    Trading pair (e.g. 'BTCUSDT').
        obi_value: Current OBI in [-1, +1].
        history:   Mutable dict of {symbol: [{ts, obi}, ...]}.
        timestamp: ISO-8601 string; auto-generated if None.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    if symbol not in history:
        history[symbol] = []

    history[symbol].append({"ts": timestamp, "obi": round(obi_value, 6)})

    # Trim to MAX_SNAPSHOTS (keep most recent)
    if len(history[symbol]) > MAX_SNAPSHOTS:
        history[symbol] = history[symbol][-MAX_SNAPSHOTS:]


def compute_obi_velocity(
    symbol: str,
    current_obi: float,
    history: Dict,
) -> Dict[str, float]:
    """Compute OBI velocity (rate of change) over multiple windows.

    The function uses the *already-recorded* history for the symbol.
    If there aren't enough snapshots for a given window, the delta for
    that window defaults to 0.0 (conservative / no-signal).

    Returns:
        dict with keys:
            obi_delta_5:      OBI change over last 5 snapshots  [-1, 1]
            obi_delta_15:     OBI change over last 15 snapshots [-1, 1]
            obi_acceleration: second derivative of OBI           [-1, 1]
    """
    entries = history.get(symbol, [])

    def _get_obi_at(lookback: int) -> Optional[float]:
        """Get the OBI value `lookback` snapshots ago (1-indexed)."""
        idx = len(entries) - lookback
        if idx < 0:
            return None
        return entries[idx].get("obi")

    # Delta-5: current minus 5-snapshots-ago
    prev_5 = _get_obi_at(5)
    delta_5 = (current_obi - prev_5) if prev_5 is not None else 0.0

    # Delta-15: current minus 15-snapshots-ago
    prev_15 = _get_obi_at(15)
    delta_15 = (current_obi - prev_15) if prev_15 is not None else 0.0

    # Acceleration: delta-of-delta (compare recent delta_5 vs earlier delta_5)
    # Earlier delta_5 = obi[now-5] - obi[now-10]
    prev_10 = _get_obi_at(10)
    if prev_5 is not None and prev_10 is not None:
        earlier_delta_5 = prev_5 - prev_10
        acceleration = delta_5 - earlier_delta_5
    else:
        acceleration = 0.0

    # Clamp all to [-1, 1] -- OBI itself is in [-1,1] so max theoretical
    # delta is 2.0, but we normalize by halving to stay in [-1,1].
    def _clamp(v: float) -> float:
        return max(-1.0, min(1.0, v / 2.0))

    return {
        "obi_delta_5": _clamp(delta_5),
        "obi_delta_15": _clamp(delta_15),
        "obi_acceleration": _clamp(acceleration),
    }


def compute_obi_velocity_batch(
    obi_scores: Dict[str, float],
    history_file: Optional[Path] = None,
) -> Dict[str, Dict[str, float]]:
    """Batch-compute OBI velocity for all symbols that have a current OBI score.

    Workflow:
      1. Load history from disk.
      2. For each symbol, compute velocity from history + current value.
      3. Record the new snapshot into history.
      4. Save updated history to disk.

    Args:
        obi_scores: {symbol: current_obi} from get_orderbook_scores_batch().
        history_file: Path to JSON history file (default: data/obi_history.json).

    Returns:
        {symbol: {obi_delta_5, obi_delta_15, obi_acceleration}}
    """
    if history_file is None:
        history_file = _DEFAULT_HISTORY_PATH

    history = _load_history(history_file)
    results: Dict[str, Dict[str, float]] = {}
    ts = datetime.now(timezone.utc).isoformat()

    for symbol, current_obi in obi_scores.items():
        # Compute velocity BEFORE recording this snapshot (so current is "now")
        velocity = compute_obi_velocity(symbol, current_obi, history)
        results[symbol] = velocity

        # Record this snapshot for future velocity computations
        record_obi_snapshot(symbol, current_obi, history, timestamp=ts)

    # Persist updated history
    _save_history(history, history_file)

    return results
