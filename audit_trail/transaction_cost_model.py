"""
Transaction Cost Model — Realistic Cost Accounting for All Asset Classes.

Addresses HEDGE_FUND_LEVEL_ROOT_CAUSE_ANALYSIS.md Deficiency #1:
No edge survives if transaction costs exceed alpha.

Industry standard: Renaissance, Citadel, DE Shaw all model costs as FIRST-CLASS inputs.
A strategy must clear the cost hurdle to even be considered for live deployment.

Usage:
    from audit_trail.transaction_cost_model import compute_net_pnl, apply_costs_to_pick

    net_pnl = compute_net_pnl(gross_pnl_pct, asset_class, symbol, is_maker=False)
    pick_with_costs = apply_costs_to_pick(pick)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CostAssumption:
    """Per-asset-class transaction cost assumptions (round-trip)."""
    fee_pct: float       # Exchange/broker fee (RT)
    slippage_pct: float  # Estimated market-impact slippage (RT)
    spread_pct: float    # Bid-ask spread cost (RT)
    label: str           # Human-readable description

    @property
    def total_cost_pct(self) -> float:
        return self.fee_pct + self.slippage_pct + self.spread_pct


# ── COST ASSUMPTIONS (operator-editable) ──────────────────────────────
# Sources: Binance fee schedule, Interactive Brokers, forex broker data
# These are CONSERVATIVE estimates. Real costs may be lower (maker rebates)
# or higher (illiquid pairs, large orders, volatile markets).

COST_ASSUMPTIONS: Dict[str, CostAssumption] = {
    # Crypto spot: 0.10% taker fee per side × 2 + 0.05% slippage + 0.03% spread
    "CRYPTO_SPOT": CostAssumption(
        fee_pct=0.20, slippage_pct=0.10, spread_pct=0.06,
        label="Crypto spot (Binance taker 0.10%×2 + slip + spread)"
    ),
    # Crypto perp: 0.05% taker per side × 2 + 0.10% slippage + 0.04% spread
    "CRYPTO_PERP": CostAssumption(
        fee_pct=0.10, slippage_pct=0.20, spread_pct=0.08,
        label="Crypto perpetual futures (Binance perp taker + slip + spread)"
    ),
    # Meme coins: MUCH wider spread + higher slippage
    "CRYPTO_MEME": CostAssumption(
        fee_pct=0.20, slippage_pct=0.30, spread_pct=0.20,
        label="Meme/micro-cap crypto (thin books, wide spread)"
    ),
    # Forex major pairs: ~0.5-1.0 pip RT (0.005%-0.010%) + 0.2 pip slippage
    "FOREX_MAJOR": CostAssumption(
        fee_pct=0.00, slippage_pct=0.002, spread_pct=0.007,
        label="Forex majors (commission-free + 0.5-1.0 pip spread)"
    ),
    # Forex crosses: wider spread
    "FOREX_CROSS": CostAssumption(
        fee_pct=0.00, slippage_pct=0.003, spread_pct=0.012,
        label="Forex crosses (wider spread, less liquid)"
    ),
    # US equities: $0 commission + ~0.05% slippage
    "EQUITY": CostAssumption(
        fee_pct=0.00, slippage_pct=0.05, spread_pct=0.02,
        label="US equities ($0 commission + 0.05% slip + 0.02% spread)"
    ),
    # Bond ETFs: tight spread but some slippage on large orders
    "BOND_ETF": CostAssumption(
        fee_pct=0.00, slippage_pct=0.05, spread_pct=0.05,
        label="Bond ETFs ($0 commission + moderate slip/spread)"
    ),
    # Commodity futures: exchange fees + spread
    "COMMODITY": CostAssumption(
        fee_pct=0.05, slippage_pct=0.08, spread_pct=0.05,
        label="Commodity futures (exchange fees + moderate spread)"
    ),
    # ETF: similar to equity
    "ETF": CostAssumption(
        fee_pct=0.00, slippage_pct=0.03, spread_pct=0.02,
        label="ETFs ($0 commission + tight spread)"
    ),
    # Futures: exchange fees + tick spread
    "FUTURES": CostAssumption(
        fee_pct=0.04, slippage_pct=0.06, spread_pct=0.04,
        label="Futures (exchange fees + tick spread)"
    ),
    # Penny stocks: wide spread, low liquidity
    "PENNY": CostAssumption(
        fee_pct=0.00, slippage_pct=0.20, spread_pct=0.50,
        label="Penny stocks (extremely wide spread, low liquidity)"
    ),
}


def _classify_cost_bucket(asset_class: str, symbol: str = "") -> str:
    """Map (asset_class, symbol) → cost bucket key."""
    ac = str(asset_class or "").upper().strip()
    sym = str(symbol or "").upper().strip()

    if ac == "CRYPTO" or ac == "MEMECOIN":
        # Detect meme/micro-cap by symbol patterns or explicit class
        if ac == "MEMECOIN":
            return "CRYPTO_MEME"
        meme_indicators = ("DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF",
                          "TRUMP", "BRETT", "FARTCOIN", "POPCAT", "MEW",
                          "NEIRO", "TURBO", "MEME", "BOME")
        if any(m in sym for m in meme_indicators):
            return "CRYPTO_MEME"
        # Detect perp futures (BTC1!, ETH1!, etc.)
        if "!" in sym or sym.endswith("USDT"):
            return "CRYPTO_PERP"
        return "CRYPTO_SPOT"

    if ac == "FOREX":
        # Major pairs vs crosses
        majors = {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
                  "USDCAD", "NZDUSD"}
        clean = sym.replace("=X", "").replace("=F", "")
        if clean in majors:
            return "FOREX_MAJOR"
        return "FOREX_CROSS"

    if ac == "EQUITY" or ac == "STOCK":
        return "EQUITY"
    if ac == "BOND":
        return "BOND_ETF"
    if ac == "ETF" or ac == "ETF_LEVERAGED":
        return "ETF"
    if ac == "COMMODITY":
        return "COMMODITY"
    if ac == "FUTURES" or ac == "INDEX":
        return "FUTURES"
    if ac == "PENNY":
        return "PENNY"

    # Default: treat as equity
    return "EQUITY"


def get_cost_assumption(asset_class: str, symbol: str = "") -> CostAssumption:
    """Get the cost assumption for a given asset class and symbol."""
    bucket = _classify_cost_bucket(asset_class, symbol)
    return COST_ASSUMPTIONS.get(bucket, COST_ASSUMPTIONS["EQUITY"])


def get_cost_assumption_for_pick(pick: Dict[str, Any]) -> Optional[CostAssumption]:
    """Get the cost assumption for a pick dict. Returns None on error."""
    try:
        ac = str(pick.get("asset_class") or pick.get("category") or "CRYPTO")
        sym = str(pick.get("symbol") or "")
        return get_cost_assumption(ac, sym)
    except Exception:
        return None


def compute_net_pnl(
    gross_pnl_pct: float,
    asset_class: str,
    symbol: str = "",
    is_maker: bool = False,
) -> float:
    """Compute net-of-cost PnL from gross PnL.

    Args:
        gross_pnl_pct: Raw PnL percentage (e.g., 1.5 for +1.5%)
        asset_class: Asset class string (CRYPTO, FOREX, EQUITY, etc.)
        symbol: Symbol string for finer classification
        is_maker: If True, apply maker fee (typically lower than taker)

    Returns:
        Net PnL percentage after subtracting estimated transaction costs.
    """
    costs = get_cost_assumption(asset_class, symbol)

    # Maker rebate: typically 50% fee reduction for limit orders
    fee_multiplier = 0.5 if is_maker else 1.0
    net_cost = (costs.fee_pct * fee_multiplier) + costs.slippage_pct + costs.spread_pct

    return gross_pnl_pct - net_cost


def apply_costs_to_pick(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich a pick dict with cost-adjusted PnL fields.

    Adds:
        - _cost_assumption: the cost bucket used
        - _total_cost_pct: total estimated round-trip cost
        - net_of_cost_pnl_pct: gross PnL minus costs
        - cost_cleared: True if net PnL > 0 (edge survives costs)

    Returns a new dict (does not mutate input).
    """
    if not isinstance(pick, dict):
        return pick

    out = dict(pick)
    ac = str(pick.get("asset_class") or pick.get("category") or "CRYPTO")
    sym = str(pick.get("symbol") or "")

    costs = get_cost_assumption(ac, sym)
    gross_pnl = 0.0
    for k in ("pnl_pct", "net_pnl_pct", "unrealized_pnl_pct"):
        v = pick.get(k)
        if v is not None:
            try:
                gross_pnl = float(v)
                break
            except (TypeError, ValueError):
                continue

    net_pnl = compute_net_pnl(gross_pnl, ac, sym)

    out["_cost_assumption"] = costs.label
    out["_total_cost_pct"] = round(costs.total_cost_pct, 6)
    out["_gross_pnl_pct"] = round(gross_pnl, 6)
    out["net_of_cost_pnl_pct"] = round(net_pnl, 6)
    out["cost_cleared"] = net_pnl > 0

    return out


def apply_costs_to_picks(picks: list) -> list:
    """Batch apply cost adjustments to a list of picks."""
    return [apply_costs_to_pick(p) for p in picks if isinstance(p, dict)]


def cost_hurdle_summary(picks: list) -> Dict[str, Any]:
    """Compute how many picks survive cost adjustment, by asset class.

    Returns:
        Dict with per-asset-class stats:
        {asset_class: {total, survived, died, survival_rate, avg_cost_pct, avg_net_pnl}}
    """
    from collections import defaultdict
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "total": 0, "survived": 0, "died": 0,
        "gross_pnl_sum": 0.0, "net_pnl_sum": 0.0, "cost_sum": 0.0,
    })

    for pick in picks:
        if not isinstance(pick, dict):
            continue
        enriched = apply_costs_to_pick(pick)
        ac = str(enriched.get("asset_class") or enriched.get("category") or "UNKNOWN").upper()
        s = stats[ac]
        s["total"] += 1
        s["gross_pnl_sum"] += enriched.get("_gross_pnl_pct", 0)
        s["net_pnl_sum"] += enriched.get("net_of_cost_pnl_pct", 0)
        s["cost_sum"] += enriched.get("_total_cost_pct", 0)
        if enriched.get("cost_cleared"):
            s["survived"] += 1
        else:
            s["died"] += 1

    result = {}
    for ac, s in stats.items():
        total = s["total"]
        result[ac] = {
            "total": total,
            "survived": s["survived"],
            "died": s["died"],
            "survival_rate": round(s["survived"] / max(1, total), 4),
            "avg_cost_pct": round(s["cost_sum"] / max(1, total), 4),
            "avg_gross_pnl": round(s["gross_pnl_sum"] / max(1, total), 4),
            "avg_net_pnl": round(s["net_pnl_sum"] / max(1, total), 4),
        }

    return result
