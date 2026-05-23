"""
Cross-System Symbol Lock for ML Battleground.
Prevents conflicting positions across System A, B, C.

Rules:
  - If another system has an active position on a symbol:
    - SAME direction: allow (consensus = stronger conviction)
    - OPPOSITE direction: block (conflict = ambiguous signal)
"""
import json
import os
from typing import Optional


# Paths to each system's active picks
_SYSTEM_PATHS = {
    "system_a_filter": os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "system_a_filter", "data", "active_picks.json",
    ),
    "system_b_regime": os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "system_b_regime", "data", "active_picks.json",
    ),
    "system_c_deeplearn": os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "system_c_deeplearn", "data", "active_picks.json",
    ),
}

# Also check ensemble if it exists
_ENSEMBLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ensemble_data", "active_picks.json",
)


def _load_picks(path: str) -> list:
    """Load picks from a JSON file, returning empty list on failure."""
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def get_active_symbols() -> dict:
    """
    Read active picks from ALL systems and return mapping:
    {symbol: [(system_name, signal_type), ...]}
    """
    result = {}

    for system_name, path in _SYSTEM_PATHS.items():
        picks = _load_picks(path)
        for pick in picks:
            symbol = pick.get("symbol", "")
            direction = pick.get("signal_type", "BUY")
            if symbol:
                result.setdefault(symbol, []).append((system_name, direction))

    # Check ensemble
    ensemble_picks = _load_picks(_ENSEMBLE_PATH)
    for pick in ensemble_picks:
        symbol = pick.get("symbol", "")
        direction = pick.get("signal_type", "BUY")
        if symbol:
            result.setdefault(symbol, []).append(("ensemble", direction))

    return result


def is_symbol_locked(symbol: str, requesting_system: str, direction: str = "BUY") -> tuple[bool, str]:
    """
    Check if a symbol is locked by another system.

    Returns (is_locked, reason).
    - If another system holds the SAME direction: NOT locked (consensus).
    - If another system holds the OPPOSITE direction: LOCKED (conflict).
    - If no other system holds this symbol: NOT locked.
    """
    active = get_active_symbols()
    holders = active.get(symbol, [])

    if not holders:
        return False, ""

    for holder_system, holder_direction in holders:
        if holder_system == requesting_system:
            continue  # skip self

        if holder_direction != direction:
            reason = (
                f"CONFLICT: {holder_system} has {holder_direction} on {symbol}, "
                f"cannot open {direction}"
            )
            return True, reason

    # All other holders agree on direction (or no other holders)
    consensus_systems = [s for s, d in holders if s != requesting_system and d == direction]
    if consensus_systems:
        print(f"    [symbol-lock] {symbol}: CONSENSUS with {consensus_systems} ({direction})")

    return False, ""


def get_conflicting_positions() -> list:
    """
    Return list of symbols where systems disagree on direction.
    Each entry: {symbol, systems: [{system, direction}, ...]}
    """
    active = get_active_symbols()
    conflicts = []

    for symbol, holders in active.items():
        directions = set(d for _, d in holders)
        if len(directions) > 1:
            conflicts.append({
                "symbol": symbol,
                "systems": [{"system": s, "direction": d} for s, d in holders],
            })

    return conflicts


def filter_signals_by_lock(
    signals: list,
    requesting_system: str,
) -> list:
    """
    Filter out signals that conflict with other systems' active positions.
    Convenience wrapper for scanner integration.
    Returns filtered list of signals.
    """
    if not signals:
        return signals

    filtered = []
    for sig in signals:
        symbol = sig.get("symbol", "")
        direction = sig.get("signal_type", "BUY")
        locked, reason = is_symbol_locked(symbol, requesting_system, direction)
        if locked:
            print(f"    [symbol-lock] {symbol} {direction}: BLOCKED ({reason})")
        else:
            filtered.append(sig)

    if len(filtered) < len(signals):
        print(f"  [symbol-lock] Filtered {len(signals) - len(filtered)} signals due to cross-system conflicts")

    return filtered
