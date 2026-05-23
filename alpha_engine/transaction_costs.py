"""
ALPHA_ENGINE -- Transaction Cost Model
=======================================
Realistic P&L calculation accounting for exchange fees, spread/slippage,
and funding costs.  Used by scanner.py (Alpha Engine) and live_scanner.py
(KIMI Rise of the Claw) to adjust TP targets and compute net P&L.

Cost sources:
  - Binance fee schedule (2024): 0.1% maker/taker (default tier)
  - Kraken Research (2023): altcoin spreads 0.1-0.5%
  - CFA Institute: equity spread analysis
  - OANDA typical spreads for forex majors

Round-trip cost = (entry slippage + entry fee) + (exit slippage + exit fee)
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Cost models per asset class
# ---------------------------------------------------------------------------

COST_MODELS: dict[str, dict[str, float]] = {
    "crypto_spot": {
        "maker_fee": 0.001,        # 0.10% (Binance default tier)
        "taker_fee": 0.001,        # 0.10%
        "slippage": 0.001,         # 0.10% estimated market impact
        "spread": 0.0005,          # 0.05% typical BTC/ETH spread
        "total_per_trade": 0.0025, # ~0.25% round-trip
    },
    "crypto_altcoin": {
        "maker_fee": 0.001,
        "taker_fee": 0.001,
        "slippage": 0.003,         # 0.30% (lower liquidity)
        "spread": 0.002,           # 0.20% typical altcoin spread
        "total_per_trade": 0.007,  # ~0.70% round-trip
    },
    "meme_coins": {
        "maker_fee": 0.001,
        "taker_fee": 0.001,
        "slippage": 0.005,         # 0.50% (extreme volatility)
        "spread": 0.003,           # 0.30%
        "total_per_trade": 0.01,   # ~1.00% round-trip
    },
    "forex": {
        "spread": 0.0002,          # 2 pips on majors
        "slippage": 0.0001,        # 1 pip
        "commission": 0.00005,     # $5 per $100K lot
        "total_per_trade": 0.0003, # ~0.03% round-trip
    },
    "stocks_etf": {
        "commission": 0.0,         # $0 commission (modern brokers)
        "spread": 0.0001,          # $0.01 on $100 stock
        "slippage": 0.0002,        # 0.02%
        "total_per_trade": 0.0003, # ~0.03% round-trip
    },
    "penny_stocks": {
        "commission": 0.0,
        "spread": 0.01,            # 1% typical penny spread
        "slippage": 0.005,         # 0.50%
        "total_per_trade": 0.015,  # ~1.50% round-trip
    },
}

# Mapping from category strings used in config.py / scanner.py to cost model keys
_CATEGORY_TO_COST_MODEL: dict[str, str] = {
    "crypto": "crypto_spot",
    "meme":   "meme_coins",
    "penny":  "penny_stocks",
    "forex":  "forex",
    "stock":  "stocks_etf",
}

# Symbols known to be major crypto (use tighter crypto_spot model)
_MAJOR_CRYPTO = {
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD",
}

# Symbols known to be altcoins (use crypto_altcoin model)
_ALT_CRYPTO = {
    "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "NEAR-USD",
    "SUI-USD", "TIA-USD", "INJ-USD", "ATOM-USD", "FIL-USD",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cost_model(symbol: str, category: str = "") -> dict[str, float]:
    """
    Determine the appropriate cost model based on symbol and category.

    Priority:
      1. Exact symbol match (major crypto vs altcoin vs meme)
      2. Category-based lookup
      3. Default to stocks_etf (lowest cost assumption)
    """
    # Crypto: distinguish major / alt / meme by symbol
    if symbol in _MAJOR_CRYPTO:
        return COST_MODELS["crypto_spot"]
    if symbol in _ALT_CRYPTO:
        return COST_MODELS["crypto_altcoin"]

    # Symbol heuristics
    if symbol.endswith("-USD"):
        # Generic crypto -- check category for meme
        if category == "meme":
            return COST_MODELS["meme_coins"]
        return COST_MODELS["crypto_altcoin"]  # conservative default for unknowns

    if symbol.endswith("=X"):
        return COST_MODELS["forex"]

    # Category-based fallback
    model_key = _CATEGORY_TO_COST_MODEL.get(category, "stocks_etf")
    return COST_MODELS.get(model_key, COST_MODELS["stocks_etf"])


def get_round_trip_cost(symbol: str, category: str = "") -> float:
    """
    Return the total round-trip transaction cost as a decimal fraction.
    E.g., 0.007 means 0.7% total for entry + exit.
    """
    model = get_cost_model(symbol, category)
    return model["total_per_trade"]


def apply_costs(
    entry_price: float,
    exit_price: float,
    symbol: str,
    category: str = "",
    signal_type: str = "BUY",
) -> dict:
    """
    Apply transaction costs to a trade and return adjusted P&L.

    Returns dict with:
      - gross_pnl_pct:  P&L before costs (decimal, e.g. 0.05 = 5%)
      - net_pnl_pct:    P&L after costs (decimal)
      - transaction_cost_pct: total costs deducted (decimal)
      - cost_model:     name of the cost model used
      - entry_slippage: estimated entry price after slippage
      - exit_slippage:  estimated exit price after slippage
    """
    model = get_cost_model(symbol, category)
    cost_pct = model["total_per_trade"]

    if entry_price <= 0:
        return {
            "gross_pnl_pct": 0.0,
            "net_pnl_pct": 0.0,
            "transaction_cost_pct": 0.0,
            "cost_model": "N/A",
            "entry_slippage": entry_price,
            "exit_slippage": exit_price,
        }

    # Gross P&L (no costs)
    if signal_type == "BUY":
        gross_pnl_pct = (exit_price - entry_price) / entry_price
    else:  # SELL / SHORT
        gross_pnl_pct = (entry_price - exit_price) / entry_price

    # Net P&L = gross - round-trip costs
    net_pnl_pct = gross_pnl_pct - cost_pct

    # Estimate slippage-adjusted prices for reporting
    slippage = model.get("slippage", 0.0)
    spread_half = model.get("spread", 0.0) / 2.0
    if signal_type == "BUY":
        entry_slippage = entry_price * (1 + slippage + spread_half)
        exit_slippage = exit_price * (1 - slippage - spread_half)
    else:
        entry_slippage = entry_price * (1 - slippage - spread_half)
        exit_slippage = exit_price * (1 + slippage + spread_half)

    # Determine cost model name for reporting
    for name, m in COST_MODELS.items():
        if m is model:
            model_name = name
            break
    else:
        model_name = "unknown"

    return {
        "gross_pnl_pct": round(gross_pnl_pct, 6),
        "net_pnl_pct": round(net_pnl_pct, 6),
        "transaction_cost_pct": round(cost_pct, 6),
        "cost_model": model_name,
        "entry_slippage": round(entry_slippage, 8),
        "exit_slippage": round(exit_slippage, 8),
    }


def adjust_tp_for_costs(
    entry_price: float,
    raw_tp: float,
    symbol: str,
    category: str = "",
    signal_type: str = "BUY",
) -> float:
    """
    Widen the take-profit target to account for transaction costs.
    The TP needs to be far enough that after paying costs, net P&L is positive.

    For BUY: new_tp = raw_tp + (entry * cost)
    For SELL: new_tp = raw_tp - (entry * cost)
    """
    cost_pct = get_round_trip_cost(symbol, category)

    if entry_price <= 0 or raw_tp <= 0:
        return raw_tp

    cost_offset = entry_price * cost_pct

    if signal_type == "BUY":
        return round(raw_tp + cost_offset, 8)
    else:
        return round(raw_tp - cost_offset, 8)


def adjusted_win_rate(
    gross_wr: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    cost_per_trade: float,
) -> float:
    """
    Calculate net win rate after accounting for costs eating into wins.

    Costs reduce gross wins and increase gross losses:
      - Trades that were marginally winning (gross win < cost) become net losses
      - Estimate: fraction of wins that are < cost becomes ~cost/avg_win

    Formula (approximation):
      net_wr = gross_wr * (1 - cost_per_trade / avg_win_pct) if avg_win_pct > 0

    Parameters:
      gross_wr: gross win rate as fraction (e.g. 0.60 = 60%)
      avg_win_pct: average winning trade P&L as fraction (e.g. 0.05 = 5%)
      avg_loss_pct: average losing trade P&L as fraction (positive, e.g. 0.03 = 3%)
      cost_per_trade: round-trip cost as fraction (e.g. 0.007 = 0.7%)

    Returns: net win rate as fraction (e.g. 0.55 = 55%)
    """
    if avg_win_pct <= 0 or gross_wr <= 0:
        return 0.0

    # Fraction of wins that become losses after costs
    # (assumes uniform distribution of win sizes -- conservative estimate)
    marginal_loss_fraction = min(cost_per_trade / avg_win_pct, 0.5)

    net_wr = gross_wr * (1.0 - marginal_loss_fraction)
    return round(max(net_wr, 0.0), 4)


def net_expectancy(
    gross_wr: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    cost_per_trade: float,
) -> float:
    """
    Calculate net expectancy per trade (expected P&L after costs).

    E = (WR * avg_win) - ((1-WR) * avg_loss) - cost_per_trade

    Returns decimal (e.g. 0.005 = 0.5% expected gain per trade).
    """
    gross_expectancy = (gross_wr * avg_win_pct) - ((1 - gross_wr) * avg_loss_pct)
    return round(gross_expectancy - cost_per_trade, 6)


# ---------------------------------------------------------------------------
# Position sizing helpers (Kelly + risk-based)
# ---------------------------------------------------------------------------

def kelly_position_size(
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    cost_per_trade: float,
    capital: float,
    kelly_fraction_cap: float = 0.25,
) -> float:
    """
    Kelly-optimal position size adjusted for transaction costs.

    Kelly% = WR - (1-WR)/(avg_win/avg_loss)
    Reduced by cost drag: effective_wr accounts for costs.

    Returns dollar position size (capped at kelly_fraction_cap * capital).
    """
    if avg_loss_pct <= 0 or avg_win_pct <= 0 or win_rate <= 0:
        return 0.0

    # Adjust win/loss for costs
    net_win = avg_win_pct - cost_per_trade
    net_loss = avg_loss_pct + cost_per_trade

    if net_win <= 0 or net_loss <= 0:
        return 0.0

    b = net_win / net_loss  # odds ratio
    kelly = win_rate - (1 - win_rate) / b

    # Cap Kelly at fraction_cap (full Kelly is too aggressive)
    kelly = max(min(kelly, kelly_fraction_cap), 0.0)

    return round(kelly * capital, 2)


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick demonstration
    print("Transaction Cost Models")
    print("=" * 60)
    for name, model in COST_MODELS.items():
        print(f"  {name:20s}: {model['total_per_trade']*100:.2f}% round-trip")
    print()

    # Example: BTC trade
    result = apply_costs(50000, 52000, "BTC-USD", "crypto", "BUY")
    print(f"BTC-USD BUY $50,000 -> $52,000:")
    print(f"  Gross P&L: {result['gross_pnl_pct']*100:+.2f}%")
    print(f"  Net P&L:   {result['net_pnl_pct']*100:+.2f}%")
    print(f"  Costs:     {result['transaction_cost_pct']*100:.2f}%")
    print(f"  Model:     {result['cost_model']}")
    print()

    # Example: meme coin trade
    result2 = apply_costs(0.0001, 0.000115, "PEPE-USD", "meme", "BUY")
    print(f"PEPE BUY $0.0001 -> $0.000115:")
    print(f"  Gross P&L: {result2['gross_pnl_pct']*100:+.2f}%")
    print(f"  Net P&L:   {result2['net_pnl_pct']*100:+.2f}%")
    print(f"  Costs:     {result2['transaction_cost_pct']*100:.2f}%")
    print()

    # Net win rate example
    net_wr = adjusted_win_rate(0.55, 0.04, 0.03, 0.007)
    print(f"55% gross WR, 4% avg win, 3% avg loss, 0.7% cost:")
    print(f"  Net WR: {net_wr*100:.1f}%")
    print(f"  Net expectancy: {net_expectancy(0.55, 0.04, 0.03, 0.007)*100:.3f}%")
    print()

    # Adjusted TP
    raw_tp = 52000.0
    adj_tp = adjust_tp_for_costs(50000.0, raw_tp, "BTC-USD", "crypto")
    print(f"BTC-USD TP adjustment: {raw_tp} -> {adj_tp} (+{(adj_tp-raw_tp):.2f})")
