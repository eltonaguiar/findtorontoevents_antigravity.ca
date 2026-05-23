"""
Unified Trading Cost Model — realistic fees + slippage for all asset classes.

Provides tier-based transaction cost estimation with size-dependent slippage.
Usable by ALL backtest and live trading systems across the project.

Cost breakdown (round-trip, base size $1000):
    Tier 1 (BTC/ETH):      0.10% fee + 0.05% slippage = 0.30% RT
    Tier 2 (major alts):   0.10% fee + 0.10% slippage = 0.40% RT
    Tier 3 (mid-cap alts): 0.10% fee + 0.20% slippage = 0.60% RT
    Tier 4 (low-cap/meme): 0.15% fee + 0.50% slippage = 1.30% RT
    Forex:                  0.005% fee + 0.01% slippage = 0.03% RT
    Equity:                 0.01% fee + 0.05% slippage = 0.12% RT
"""

import math
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Tier definitions: (taker_fee_one_way, base_slippage_one_way)
# Round-trip = 2 * (fee + slippage)
# ---------------------------------------------------------------------------
TIER_COSTS: Dict[str, Tuple[float, float]] = {
    "tier1":  (0.0010, 0.0005),   # BTC, ETH
    "tier2":  (0.0010, 0.0010),   # SOL, BNB, XRP, ADA, AVAX, DOT
    "tier3":  (0.0010, 0.0020),   # mid-cap alts
    "tier4":  (0.0015, 0.0050),   # low-cap / meme coins
    "forex":  (0.00005, 0.0001),  # major FX pairs
    "equity": (0.0001, 0.0005),   # US large-cap equities
}

# ---------------------------------------------------------------------------
# Symbol → tier mapping (30+ crypto, forex, equity)
# ---------------------------------------------------------------------------
SYMBOL_TIER: Dict[str, str] = {
    # Tier 1 — BTC, ETH (highest liquidity)
    "BTCUSDT": "tier1", "BTCUSD": "tier1", "BTC-USD": "tier1",
    "ETHUSDT": "tier1", "ETHUSD": "tier1", "ETH-USD": "tier1",
    "BTCBUSD": "tier1", "ETHBUSD": "tier1",

    # Tier 2 — major alts
    "SOLUSDT": "tier2", "SOLUSD": "tier2",
    "BNBUSDT": "tier2", "BNBUSD": "tier2",
    "XRPUSDT": "tier2", "XRPUSD": "tier2",
    "ADAUSDT": "tier2", "ADAUSD": "tier2",
    "AVAXUSDT": "tier2", "AVAXUSD": "tier2",
    "DOTUSDT": "tier2", "DOTUSD": "tier2",
    "LTCUSDT": "tier2", "LINKUSDT": "tier2",
    "NEARUSDT": "tier2", "SUIUSDT": "tier2",
    "APTUSDT": "tier2", "MATICUSDT": "tier2",
    "TRXUSDT": "tier2", "ATOMUSDT": "tier2",

    # Tier 3 — mid-cap
    "DOGEUSDT": "tier3", "SHIBUSDT": "tier3",
    "ARBUSDT": "tier3", "OPUSDT": "tier3",
    "INJUSDT": "tier3", "FETUSDT": "tier3",
    "TIAUSDT": "tier3", "SEIUSDT": "tier3",
    "FILUSDT": "tier3", "TAOUSDT": "tier3",
    "AAVEUSDT": "tier3", "UNIUSDT": "tier3",
    "RENDERUSDT": "tier3", "STXUSDT": "tier3",

    # Tier 4 — low-cap / meme
    "PEPEUSDT": "tier4", "FLOKIUSDT": "tier4",
    "BONKUSDT": "tier4", "WIFUSDT": "tier4",
    "MEMEUSDT": "tier4", "BOMEUSDT": "tier4",
    "1000PEPEUSDT": "tier4", "1000SHIBUSDT": "tier4",

    # Forex — major pairs
    "EURUSD": "forex", "GBPUSD": "forex", "USDJPY": "forex",
    "USDCHF": "forex", "AUDUSD": "forex", "USDCAD": "forex",
    "NZDUSD": "forex", "EURGBP": "forex", "EURJPY": "forex",
    "GBPJPY": "forex",

    # Equity — major indices / ETFs
    "SPY": "equity", "QQQ": "equity", "IWM": "equity",
    "AAPL": "equity", "MSFT": "equity", "GOOGL": "equity",
    "AMZN": "equity", "TSLA": "equity", "NVDA": "equity",
    "META": "equity",
}

# Base trade size for slippage calibration
_BASE_SIZE_USD = 1000.0


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol to uppercase, strip common suffixes/prefixes."""
    s = symbol.upper().strip()
    # Remove .P (perp marker) if present
    if s.endswith(".P"):
        s = s[:-2]
    return s


def get_tier(symbol: str) -> str:
    """Return the tier string for a symbol.

    Falls back to heuristic: forex pairs (6 chars, no digits) → forex,
    otherwise tier3 (conservative mid-cap assumption).
    """
    sym = _normalize_symbol(symbol)
    if sym in SYMBOL_TIER:
        return SYMBOL_TIER[sym]

    # Heuristic fallbacks
    # Forex: 6-letter all-alpha (e.g. EURUSD)
    if len(sym) == 6 and sym.isalpha() and sym[3:] in ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"):
        return "forex"
    # Equity: no "USDT"/"USD"/"BUSD" suffix and short name
    if not any(sym.endswith(suf) for suf in ("USDT", "USD", "BUSD")) and len(sym) <= 5 and sym.isalpha():
        return "equity"
    # Default: conservative mid-cap crypto
    return "tier3"


def _slippage_multiplier(size_usd: float) -> float:
    """Size-dependent slippage scaling using sqrt model.

    At $1000 (base): 1.0x slippage
    At $10000: ~3.16x slippage
    At $100: ~0.32x slippage
    """
    if size_usd <= 0:
        return 0.0
    return math.sqrt(size_usd / _BASE_SIZE_USD)


def estimate_round_trip_cost(symbol: str, size_usd: float = 1000.0) -> float:
    """Estimate total round-trip cost as a decimal fraction.

    Args:
        symbol: Trading pair (e.g. "BTCUSDT", "EURUSD", "SPY")
        size_usd: Trade notional in USD (affects slippage)

    Returns:
        Round-trip cost as fraction (e.g. 0.003 = 0.3%)

    Examples:
        >>> estimate_round_trip_cost("BTCUSDT")        # ~0.003
        >>> estimate_round_trip_cost("PEPEUSDT", 5000)  # ~0.029
        >>> estimate_round_trip_cost("EURUSD")          # ~0.0003
    """
    tier = get_tier(symbol)
    fee, base_slippage = TIER_COSTS[tier]
    slip = base_slippage * _slippage_multiplier(size_usd)
    return 2.0 * (fee + slip)


def apply_costs(
    entry_price: float,
    direction: str,
    symbol: str,
    size_usd: float = 1000.0,
) -> Tuple[float, float]:
    """Adjust entry price for transaction costs (one-way entry fill).

    For BUY: price is adjusted UP (worse fill).
    For SELL/SHORT: price is adjusted DOWN (worse fill).

    Args:
        entry_price: Raw entry price
        direction: "BUY" or "SELL" / "SHORT"
        symbol: Trading pair
        size_usd: Trade notional in USD

    Returns:
        (adjusted_entry_price, total_round_trip_cost_fraction)
    """
    rt_cost = estimate_round_trip_cost(symbol, size_usd)
    # Apply half the round-trip cost at entry (other half at exit)
    half_cost = rt_cost / 2.0

    direction_upper = direction.upper()
    if direction_upper in ("BUY", "LONG"):
        adjusted = entry_price * (1.0 + half_cost)
    elif direction_upper in ("SELL", "SHORT"):
        adjusted = entry_price * (1.0 - half_cost)
    else:
        raise ValueError(f"Unknown direction: {direction!r}. Use BUY/LONG or SELL/SHORT.")

    return adjusted, rt_cost


def adjust_backtest_results(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    symbol: str,
    size_usd: float = 1000.0,
) -> Dict[str, float]:
    """Adjust raw backtest metrics for realistic transaction costs.

    Subtracts round-trip cost from each winning trade and adds it to each
    losing trade, then recalculates win rate based on trades that remain
    profitable after costs.

    Args:
        win_rate: Raw win rate as fraction (e.g. 0.65 = 65%)
        avg_win: Average winning trade return as fraction (e.g. 0.02 = 2%)
        avg_loss: Average losing trade return as fraction (POSITIVE number, e.g. 0.01 = 1%)
        symbol: Trading pair
        size_usd: Trade notional in USD

    Returns:
        Dict with adjusted_win_rate, adjusted_avg_win, adjusted_avg_loss,
        cost_per_trade, expected_value_per_trade
    """
    rt_cost = estimate_round_trip_cost(symbol, size_usd)

    # Adjust returns: wins shrink, losses grow
    adj_win = avg_win - rt_cost
    adj_loss = avg_loss + rt_cost

    # Some "wins" become losses after costs
    if avg_win > 0:
        # Fraction of wins that survive costs (assume uniform distribution
        # of wins from 0 to 2*avg_win for simplicity)
        survival = max(0.0, min(1.0, 1.0 - rt_cost / (2.0 * avg_win)))
        adj_wr = win_rate * survival
    else:
        adj_wr = 0.0

    # Expected value per trade
    ev = adj_wr * max(adj_win, 0.0) - (1.0 - adj_wr) * adj_loss

    return {
        "adjusted_win_rate": round(adj_wr, 6),
        "adjusted_avg_win": round(max(adj_win, 0.0), 6),
        "adjusted_avg_loss": round(adj_loss, 6),
        "cost_per_trade": round(rt_cost, 6),
        "expected_value_per_trade": round(ev, 6),
    }


# ---------------------------------------------------------------------------
# Quick sanity check when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        ("BTCUSDT", 1000),
        ("SOLUSDT", 1000),
        ("DOGEUSDT", 1000),
        ("PEPEUSDT", 1000),
        ("EURUSD", 1000),
        ("SPY", 1000),
        ("BTCUSDT", 10000),
        ("PEPEUSDT", 10000),
    ]
    print(f"{'Symbol':<16} {'Size':>8} {'Tier':<8} {'RT Cost':>10}")
    print("-" * 48)
    for sym, size in test_cases:
        tier = get_tier(sym)
        cost = estimate_round_trip_cost(sym, size)
        print(f"{sym:<16} ${size:>6,} {tier:<8} {cost*100:>9.4f}%")

    print("\n--- Backtest adjustment example ---")
    raw = adjust_backtest_results(0.65, 0.02, 0.01, "BTCUSDT")
    print(f"BTCUSDT: raw WR=65%, adj WR={raw['adjusted_win_rate']*100:.2f}%, "
          f"EV/trade={raw['expected_value_per_trade']*100:.4f}%")
