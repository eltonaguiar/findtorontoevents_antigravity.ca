"""Shared utilities for the alpha engine and audit dashboard.

This module provides common functions used across the codebase to ensure
consistency in calculations like win rate, risk metrics, etc.
"""

from typing import List, Dict, Any, Optional

# Standardized Win Rate Calculation
# =============================================================================
# Standard formula: wins / total_closed_trades (excluding zero-PnL trades)
# This standard is used across all 4 locations:
#   1. audit_dashboard/portfolio_manager.py
#   2. alpha_engine/strategy_leaderboard.py
#   3. alpha_engine/scanner.py
#   4. alpha_engine/production_scanner.py
# =============================================================================


def calculate_win_rate(
    wins: int,
    total_closed: int,
    zero_pnl_count: int = 0,
    exclude_zero_pnl: bool = True
) -> float:
    """
    Calculate win rate with standardized formula.

    Standard formula: wins / total_closed_trades
    - Zero-PnL trades are excluded from BOTH numerator and denominator by default
    - This matches the industry standard definition of win rate

    Args:
        wins: Number of winning trades (PnL > 0)
        total_closed: Total number of closed trades (wins + losses + zero_pnl)
        zero_pnl_count: Number of trades with exactly zero PnL
        exclude_zero_pnl: If True (default), exclude zero-PnL trades from calculation

    Returns:
        Win rate as a float between 0.0 and 1.0

    Examples:
        >>> calculate_win_rate(50, 100)  # 50 wins out of 100 trades
        0.5
        >>> calculate_win_rate(50, 110, 10)  # 50 wins, 50 losses, 10 zero-PnL
        0.5
        >>> calculate_win_rate(50, 100, 10, exclude_zero_pnl=False)  # Include zero-PnL
        0.5
        >>> calculate_win_rate(0, 0)  # Edge case: no trades
        0.0
    """
    if exclude_zero_pnl and zero_pnl_count > 0:
        # Exclude zero-PnL trades from denominator
        denominator = total_closed - zero_pnl_count
    else:
        denominator = total_closed

    if denominator <= 0:
        return 0.0

    return wins / denominator


def calculate_win_rate_from_picks(
    picks: List[Dict[str, Any]],
    pnl_key: str = "pnl_pct",
    status_key: str = "status",
    window: Optional[int] = None
) -> float:
    """
    Calculate win rate from a list of pick/trade dictionaries.

    Standard formula: wins / (wins + losses)
    - Zero-PnL trades (abs(pnl) <= 0.01%) are excluded from BOTH numerator and denominator
    - Open/unresolved picks are excluded

    Args:
        picks: List of pick dictionaries with PnL data
        pnl_key: Key to access PnL value (default: "pnl_pct")
        status_key: Key to access trade status (default: "status")
        window: If provided, only use the last N picks (for rolling calculations)

    Returns:
        Win rate as a float between 0.0 and 1.0
    """
    if not picks:
        return 0.0

    # Apply window if specified
    if window and len(picks) > window:
        picks = picks[-window:]

    wins = 0
    losses = 0

    for pick in picks:
        # Skip open/unresolved picks
        status = str(pick.get(status_key, "")).upper()
        if status in ("OPEN", "PENDING", "ACTIVE"):
            continue

        # Determine win/loss/flat from PnL
        pnl = pick.get(pnl_key)
        if pnl is None:
            # Fallback to status if PnL not available
            if status in ("WON", "WIN", "TP_HIT"):
                wins += 1
            elif status in ("LOST", "LOSS", "SL_HIT"):
                losses += 1
            continue

        try:
            pnl_val = float(pnl)
            if pnl_val > 0.01:  # Win (PnL > 0.01%)
                wins += 1
            elif pnl_val < -0.01:  # Loss (PnL < -0.01%)
                losses += 1
            # Zero-PnL trades (abs(pnl) <= 0.01%) are excluded
        except (TypeError, ValueError):
            continue

    total_resolved = wins + losses
    if total_resolved == 0:
        return 0.0

    return wins / total_resolved


def calculate_win_rate_from_pnls(pnls: List[float]) -> float:
    """
    Calculate win rate from a list of PnL values.

    Standard formula: wins / (wins + losses)
    - Zero-PnL trades (pnl == 0) are excluded from BOTH numerator and denominator

    Args:
        pnls: List of PnL percentage values

    Returns:
        Win rate as a float between 0.0 and 1.0
    """
    if not pnls:
        return 0.0

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    # Zero-PnL trades (p == 0) are excluded

    total_resolved = wins + losses
    if total_resolved == 0:
        return 0.0

    return wins / total_resolved


# Backwards compatibility aliases
win_rate = calculate_win_rate
rolling_win_rate = calculate_win_rate_from_picks
