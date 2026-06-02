"""
EAGLE2 Per-Asset-Class Cost & Slippage Model — v1.0 (2026-06-02)

Unified cost model applied to every strategy backtest and live PnL calculation.
Cost curves account for spread, commission, and slippage per asset class.

Fees are in basis points (1 bp = 0.01% = 0.0001 fractional).
"""
from __future__ import annotations

# ── Execution Costs (spread + commission) in basis points ───────────────
# Sources: Binance spot (taker 0.075-0.1% + BNB discount), Interactive Brokers
# tiered/Pro, FXCM Standard account, CME retail futures
EXECUTION_COST_BPS: dict[str, float] = {
    "CRYPTO": 8.0,      # 0.08% round-trip (taker 0.04% × 2, with BNB disc)
    "EQUITY": 5.0,      # 0.05% (IB Pro tiered: ~0.0035/sh × 2 / avg $2K pos)
    "ETF": 2.0,         # 0.02% (IB Pro: ~$0.005/sh × 2 / avg $50 ETF)
    "FOREX": 1.5,       # 0.015% (FXCM Standard: 1.5 pip avg spread on majors)
    "COMMODITY": 3.0,   # 0.03% (CME micro: $0.10 tick × 2 / ~$700 notional)
    "FUTURES": 2.5,     # 0.025% (CME micro ES: $0.25 × 2 / ~$2000 notional)
    "BOND": 3.0,        # 0.03% (TLT equity proxy: 0.02% spread + commission)
    "STOCK": 5.0,       # alias for EQUITY
    "INDEX": 2.0,       # alias for ETF
}
EXECUTION_COST_DEFAULT = 5.0  # Conservatively default to equity-tier costs

# ── Slippage (market impact + adverse selection) in basis points ────────
# Conservative estimates for retail-sized orders (~$500-$5000). Higher for
# lower-liquidity classes.
SLIPPAGE_BPS: dict[str, float] = {
    "CRYPTO": 5.0,       # 0.05% (altcoin top-100 liquidity gap)
    "EQUITY": 2.0,       # 0.02% (mid-cap, market order on liquid name)
    "ETF": 1.0,          # 0.01% (highly liquid, tight spreads)
    "FOREX": 0.5,        # 0.005% (majors: EURUSD, USDJPY very tight)
    "COMMODITY": 4.0,    # 0.04% (less liquid micro contracts)
    "FUTURES": 3.0,      # 0.03% (micro futures, decent liquidity)
    "BOND": 1.5,         # 0.015% (TLT/TLTW liquid, tight)
    "STOCK": 2.0,        # alias
    "INDEX": 1.0,        # alias
}
SLIPPAGE_DEFAULT = 3.0  # Conservative default


def get_cost_bps(asset_class: str) -> float:
    """Return execution cost in basis points for an asset class."""
    ac = str(asset_class or "").upper().strip()
    return EXECUTION_COST_BPS.get(ac, EXECUTION_COST_DEFAULT)


def get_slippage_bps(asset_class: str) -> float:
    """Return slippage estimate in basis points for an asset class."""
    ac = str(asset_class or "").upper().strip()
    return SLIPPAGE_BPS.get(ac, SLIPPAGE_DEFAULT)


def get_total_bps(asset_class: str) -> float:
    """Return total round-trip cost (execution + slippage) in basis points."""
    return get_cost_bps(asset_class) + get_slippage_bps(asset_class)


def apply_costs(pnl_pct: float, asset_class: str) -> float:
    """Apply round-trip costs to a trade's PnL percentage.

    Args:
        pnl_pct: Raw PnL as decimal (0.05 = 5%)
        asset_class: CRYPTO, EQUITY, ETF, FOREX, COMMODITY, FUTURES, BOND

    Returns:
        Cost-adjusted PnL as decimal
    """
    total_bps = get_total_bps(asset_class)
    cost_pct = total_bps / 10000.0  # bps → decimal
    return pnl_pct - cost_pct


def get_annualized_cost_ratio(asset_class: str, trades_per_year: int) -> float:
    """Estimate annualized cost drag as a fraction of capital.

    Args:
        asset_class: Asset class string
        trades_per_year: Expected number of round-trips per year

    Returns:
        Annual cost as decimal (0.01 = 1% of capital)
    """
    cost_per_trade = get_total_bps(asset_class) / 10000.0
    return cost_per_trade * trades_per_year


# ── Cost model summary table (for reporting) ───────────────────────────
def cost_summary() -> dict[str, dict[str, float]]:
    """Return a summary table of costs by asset class."""
    classes = ["CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "FUTURES", "BOND"]
    return {ac: {
        "execution_bps": get_cost_bps(ac),
        "slippage_bps": get_slippage_bps(ac),
        "total_bps": get_total_bps(ac),
        "cost_per_trade_pct": round(get_total_bps(ac) / 10000.0, 5),
    } for ac in classes}
