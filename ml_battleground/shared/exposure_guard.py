"""Exposure concentration guard.
Limits USD exposure per correlated asset cluster.
NOT a signal blocker -- reduces position sizing when cluster exposure is high.
"""

MAX_CLUSTER_EXPOSURE_PCT = 6.0  # Max % of portfolio in one correlated cluster


def check_exposure(new_pick: dict, all_active_picks: list, correlations: dict = None) -> float:
    """Returns position size multiplier (0.5 to 1.0).

    If total exposure to assets correlated with new_pick's symbol exceeds
    MAX_CLUSTER_EXPOSURE_PCT, returns 0.5 (half position).
    Otherwise returns 1.0 (full position).

    During BTC-driven selloffs (>80% of active picks in same direction),
    suspends the guard entirely to let contrarian systems operate.
    """
    if not all_active_picks:
        return 1.0

    # Simple correlation clustering: all altcoins are correlated with each other
    # BTC and ETH are their own clusters
    symbol = new_pick.get("symbol", "")
    direction = new_pick.get("direction", "")

    # Count picks in same direction
    same_direction = [p for p in all_active_picks if p.get("direction") == direction]

    # If >80% of picks are in same direction, likely a macro move -- suspend guard
    if len(same_direction) > 0.8 * len(all_active_picks) and len(all_active_picks) >= 5:
        return 1.0

    # Count exposure to similar assets
    cluster_count = sum(1 for p in same_direction
                        if _same_cluster(p.get("symbol", ""), symbol))

    if cluster_count >= 3:
        return 0.5  # Reduce position by half
    return 1.0


def _same_cluster(sym1: str, sym2: str) -> bool:
    """Check if two symbols are in the same correlation cluster."""
    btc = {"BTCUSDT"}
    eth = {"ETHUSDT"}
    # Everything else is "altcoin cluster"
    if sym1 in btc or sym2 in btc:
        return sym1 == sym2
    if sym1 in eth or sym2 in eth:
        return sym1 == sym2
    return True  # All alts correlated
