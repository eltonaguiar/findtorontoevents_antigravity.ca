"""
Transaction cost model for crypto trading.
Adapted from alpha_engine/transaction_costs.py.
"""

# Round-trip costs (entry + exit) as decimal
# Raised: 0.20% fees + 0.15% slippage buffer minimum = 0.35%
# Low-liquidity (tier3) uses 0.50% to account for wider spreads
COST_BY_TIER = {
    "tier1": 0.0035,   # BTC, ETH, BNB, SOL, XRP — 0.20% fees + 0.15% slippage
    "tier2": 0.0050,   # alt L1 — moderate spreads, worse fills
    "tier3": 0.0080,   # mid-cap — wider spreads, significant slippage
}

PAIR_TIER = {
    "BTCUSDT": "tier1", "ETHUSDT": "tier1", "BNBUSDT": "tier1",
    "SOLUSDT": "tier1", "XRPUSDT": "tier1", "LTCUSDT": "tier1",
    "ADAUSDT": "tier2", "TAOUSDT": "tier2", "AVAXUSDT": "tier2",
    "LINKUSDT": "tier2", "NEARUSDT": "tier2", "SUIUSDT": "tier2",
    "APTUSDT": "tier2",
    "DOGEUSDT": "tier3", "ARBUSDT": "tier3", "OPUSDT": "tier3",
    "INJUSDT": "tier3", "FETUSDT": "tier3", "TIAUSDT": "tier3",
    "SEIUSDT": "tier3", "FILUSDT": "tier3",
}


def round_trip_cost(pair: str, panic: bool = False) -> float:
    """Round-trip cost. Add 50% slippage surcharge during panic conditions."""
    tier = PAIR_TIER.get(pair, "tier3")
    base = COST_BY_TIER[tier]
    if panic:
        base *= 1.5  # Liquidity evaporates in panic → 50% more slippage
    return base


def net_pnl(entry: float, exit_price: float, pair: str, signal_type: str = "BUY") -> float:
    """Net PnL percentage after costs."""
    cost = round_trip_cost(pair)
    if signal_type == "BUY":
        gross = (exit_price - entry) / entry
    else:
        gross = (entry - exit_price) / entry
    return gross - cost
