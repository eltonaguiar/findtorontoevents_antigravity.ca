"""
Trade Geometry Validation Module

Provides unified trade geometry validation for ALL asset classes.
Fixes the critical bug in quality_gates.py where non-CRYPTO assets skip validation.

Key fixes:
- Removes bypass that returned True for non-CRYPTO assets
- Applies same directional validation to CRYPTO, FOREX, EQUITY, COMMODITY, FUTURES
- Validates TP > entry > SL for LONG, TP < entry < SL for SHORT

Usage:
    from audit_trail.trade_geometry import has_valid_trade_geometry, validate_pick
    
    if has_valid_trade_geometry(pick):
        # Valid trade geometry
        pass
"""

from typing import Any, Dict, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Supported asset classes."""
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    EQUITY = "EQUITY"
    COMMODITY = "COMMODITY"
    FUTURES = "FUTURES"
    ETF = "ETF"
    MEMECOIN = "MEMECOIN"
    UNKNOWN = "UNKNOWN"


# Asset class string to Enum mapping
_ASSET_CLASS_MAP: Dict[str, AssetClass] = {
    "CRYPTO": AssetClass.CRYPTO,
    "FOREX": AssetClass.FOREX,
    "EQUITY": AssetClass.EQUITY,
    "COMMODITY": AssetClass.COMMODITY,
    "FUTURES": AssetClass.FUTURES,
    "ETF": AssetClass.ETF,
    "MEMECOIN": AssetClass.MEMECOIN,
    "UNKNOWN": AssetClass.UNKNOWN,
}


def normalize_asset_class(asset_class: Any) -> AssetClass:
    """
    Normalize asset class string to AssetClass enum.
    
    Args:
        asset_class: Asset class string (e.g., "CRYPTO", "crypto", "Forex")
        
    Returns:
        AssetClass enum value
    """
    if asset_class is None:
        return AssetClass.CRYPTO
    
    ac_str = str(asset_class).upper().strip()
    return _ASSET_CLASS_MAP.get(ac_str, AssetClass.UNKNOWN)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_direction(pick: Dict[str, Any]) -> Optional[str]:
    """
    Extract normalized direction from pick.
    
    Args:
        pick: Pick dictionary
        
    Returns:
        "LONG", "SHORT", or None if unknown
    """
    direction = str(
        pick.get("direction", "") or pick.get("signal_type", "") or ""
    ).upper()
    
    if direction in ("LONG", "BUY"):
        return "LONG"
    if direction in ("SHORT", "SELL"):
        return "SHORT"
    
    return None


def validate_long_geometry(entry: float, tp: float, sl: float) -> bool:
    """
    Validate LONG position geometry.
    
    For LONG positions:
    - Entry must be positive
    - Take Profit must be ABOVE entry (tp > entry)
    - Stop Loss must be BELOW entry (sl < entry)
    - TP must be above SL (tp > sl) for valid risk/reward
    
    Args:
        entry: Entry price
        tp: Take profit price
        sl: Stop loss price
        
    Returns:
        True if valid LONG geometry
    """
    if entry <= 0:
        return False
    
    # LONG: TP must be above entry, SL must be below entry
    if tp <= entry:
        logger.debug(f"Invalid LONG geometry: TP ({tp}) <= entry ({entry})")
        return False
    
    if sl >= entry:
        return False
    
    # Additional check: TP should be above SL (positive R:R)
    if tp <= sl:
        logger.debug(f"Invalid LONG geometry: TP ({tp}) <= SL ({sl})")
        return False
    
    return True


def validate_short_geometry(entry: float, tp: float, sl: float) -> bool:
    """
    Validate SHORT position geometry.
    
    For SHORT positions:
    - Entry must be positive
    - Take Profit must be BELOW entry (tp < entry)
    - Stop Loss must be ABOVE entry (sl > entry)
    - TP must be below SL (tp < sl) for valid risk/reward
    
    Args:
        entry: Entry price
        tp: Take profit price
        sl: Stop loss price
        
    Returns:
        True if valid SHORT geometry
    """
    if entry <= 0:
        return False
    
    # SHORT: TP must be below entry, SL must be above entry
    if tp >= entry:
        logger.debug(f"Invalid SHORT geometry: TP ({tp}) >= entry ({entry})")
        return False
    
    if sl <= entry:
        return False
    
    # Additional check: TP should be below SL (positive R:R for short)
    if tp >= sl:
        logger.debug(f"Invalid SHORT geometry: TP ({tp}) >= SL ({sl})")
        return False
    
    return True


def validate_trade_geometry(
    entry: float, 
    tp: float, 
    sl: float, 
    direction: str
) -> bool:
    """
    Validate trade geometry based on direction.
    
    Args:
        entry: Entry price
        tp: Take profit price
        sl: Stop loss price
        direction: "LONG" or "SHORT"
        
    Returns:
        True if valid geometry for the given direction
    """
    if direction == "LONG":
        return validate_long_geometry(entry, tp, sl)
    elif direction == "SHORT":
        return validate_short_geometry(entry, tp, sl)
    
    return False


def is_exempt_from_validation(pick: Dict[str, Any]) -> bool:
    """
    Check if pick is exempt from geometry validation.
    
    Exemptions:
    - Picks without entry price (may be pending)
    - Picks without TP/SL (emitted without targets)
    - Sandbox/experimental strategies
    
    Args:
        pick: Pick dictionary
        
    Returns:
        True if exempt from validation
    """
    # No entry price - exempt (may be pending emission)
    entry = _safe_float(pick.get("entry_price"), 0)
    if entry <= 0:
        return True
    
    # No TP and no SL - exempt (emitted without targets)
    tp = _safe_float(pick.get("take_profit"), 0)
    sl = _safe_float(pick.get("stop_loss"), 0)
    
    # If both TP and SL are missing, allow through
    # Many valid picks don't have TP/SL at emission time
    if tp <= 0 and sl <= 0:
        return True
    
    # Check for exempt strategy/source patterns
    strategy = str(pick.get("strategy", "")).lower()
    source = str(pick.get("source_system", "")).lower()
    
    # Sandbox strategies are exempt
    sandbox_patterns = ("sandbox", "test", "experimental", "demo")
    if any(p in strategy or p in source for p in sandbox_patterns):
        return True
    
    return False


def has_valid_trade_geometry(pick: Dict[str, Any]) -> bool:
    """
    Unified trade geometry validation for ALL asset classes.
    
    This function replaces the buggy _has_valid_trade_geometry in quality_gates.py
    which incorrectly returned True for all non-CRYPTO assets.
    
    Now applies the same validation logic to:
    - CRYPTO
    - FOREX
    - EQUITY
    - COMMODITY
    - FUTURES
    - ETF
    - MEMECOIN
    
    Args:
        pick: Pick dictionary with entry_price, take_profit, stop_loss, direction
        
    Returns:
        True if trade geometry is valid, False otherwise
    """
    # Check exemption first
    if is_exempt_from_validation(pick):
        return True
    
    # Extract values
    entry = _safe_float(pick.get("entry_price"), 0)
    tp = _safe_float(pick.get("take_profit"), 0)
    sl = _safe_float(pick.get("stop_loss"), 0)
    
    # If entry is missing, fail validation
    if entry <= 0:
        logger.debug(f"Invalid trade geometry: missing entry price")
        return False
    
    # Get direction
    direction = get_direction(pick)
    if direction is None:
        # Unknown direction - fail (can't validate without knowing LONG/SHORT)
        logger.debug(f"Invalid trade geometry: unknown direction")
        return False
    
    # If both TP and SL are present, validate directional geometry
    if tp > 0 and sl > 0:
        return validate_trade_geometry(entry, tp, sl, direction)
    
    # If only one of TP/SL is present, warn but allow through
    # (some strategies only use one target)
    if tp > 0 or sl > 0:
        logger.debug(f"Partial TP/SL: TP={tp}, SL={sl}, allowing through")
    
    return True


def validate_pick(pick: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a pick and return detailed result.
    
    Args:
        pick: Pick dictionary
        
    Returns:
        Tuple of (is_valid, reason)
    """
    if has_valid_trade_geometry(pick):
        return True, "valid"
    
    # Get details for error message
    entry = _safe_float(pick.get("entry_price", 0))
    tp = _safe_float(pick.get("take_profit", 0))
    sl = _safe_float(pick.get("stop_loss", 0))
    direction = get_direction(pick)
    asset_class = normalize_asset_class(pick.get("asset_class", "CRYPTO"))
    
    reason = f"invalid_geometry: entry={entry}, tp={tp}, sl={sl}, direction={direction}, asset_class={asset_class.value}"
    
    return False, reason


def validate_batch(picks: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of picks and return summary.
    
    Args:
        picks: List of pick dictionaries
        
    Returns:
        Dictionary with validation summary
    """
    valid_count = 0
    invalid_count = 0
    invalid_picks = []
    
    for pick in picks:
        is_valid, reason = validate_pick(pick)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            invalid_picks.append({
                "symbol": pick.get("symbol", "UNKNOWN"),
                "strategy": pick.get("strategy", "UNKNOWN"),
                "asset_class": pick.get("asset_class", "UNKNOWN"),
                "reason": reason
            })
    
    return {
        "total": len(picks),
        "valid": valid_count,
        "invalid": invalid_count,
        "invalid_picks": invalid_picks[:10]  # Limit to first 10 for brevity
    }


# Backward compatibility alias for quality_gates.py migration
def _has_valid_trade_geometry(pick: Dict[str, Any]) -> bool:
    """
    Backward compatibility wrapper for quality_gates.py.
    
    DEPRECATED: Use has_valid_trade_geometry() instead.
    """
    return has_valid_trade_geometry(pick)


# Export commonly used functions
__all__ = [
    "has_valid_trade_geometry",
    "validate_pick",
    "validate_batch",
    "validate_long_geometry",
    "validate_short_geometry",
    "validate_trade_geometry",
    "get_direction",
    "normalize_asset_class",
    "AssetClass",
    "_has_valid_trade_geometry",  # Deprecated alias
]