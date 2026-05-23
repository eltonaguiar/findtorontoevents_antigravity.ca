"""
ALPHA_ENGINE -- Basket Generator
=================================
Generates balanced trading baskets instead of correlated spray-and-pray.

Key features:
  - Correlation group enforcement (max 1 pick per group)
  - Hedge requirement (synthetic hedge if all same direction)
  - Risk-parity position sizing (inverse ATR weighting)
  - CLI support for quick basket generation

Usage:
  python -m alpha_engine.basket_generator
  python alpha_engine/basket_generator.py
"""

import json
import os
import sys
import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Correlation groups — tokens that move together get grouped
# ---------------------------------------------------------------------------
CORRELATION_GROUPS = {
    "large_cap":  ["BTC", "ETH"],
    "alt_l1":     ["SOL", "AVAX", "NEAR", "DOT", "SUI"],
    "defi":       ["AAVE", "LINK", "UNI", "CRV"],
    "ai_infra":   ["FET", "RENDER", "TAO", "TIA"],
    "meme":       ["DOGE", "SHIB", "PEPE", "BONK", "FARTCOIN"],
    "exchange":   ["BNB"],
    "gaming":     ["AXS", "PIXEL", "GALA"],
}

# Reverse lookup: symbol -> group
_SYMBOL_TO_GROUP = {}
for _grp, _syms in CORRELATION_GROUPS.items():
    for _s in _syms:
        _SYMBOL_TO_GROUP[_s] = _grp


def _extract_base_symbol(symbol: str) -> str:
    """Strip USDT/USD/BUSD suffix to get the base token."""
    for suffix in ("USDT", "USD", "BUSD", "USDC"):
        if symbol.upper().endswith(suffix):
            return symbol.upper()[: -len(suffix)]
    return symbol.upper()


def _get_group(symbol: str) -> str:
    """Return correlation group for a symbol, or 'other_<SYM>' if ungrouped."""
    base = _extract_base_symbol(symbol)
    return _SYMBOL_TO_GROUP.get(base, f"other_{base}")


def _estimate_atr(pick: dict) -> float:
    """
    Estimate ATR from pick data.  Uses price_change_24h_pct as a volatility
    proxy when real ATR isn't available.  Falls back to 5% if nothing useful.
    """
    # Try enrichment RSI data or price change as vol proxy
    price_change = abs(pick.get("price_change_24h_pct", 0) or 0)
    if price_change > 0:
        return price_change

    # Try entry/SL spread as ATR proxy
    entry = pick.get("entry_price", 0) or 0
    sl = pick.get("stop_loss", 0) or 0
    if entry > 0 and sl > 0:
        return abs(entry - sl) / entry * 100

    # Default 5% volatility
    return 5.0


def _compute_risk_parity_sizes(basket_picks: list, target_risk: float = 1.0) -> list:
    """
    Size positions inversely proportional to ATR.
    size_i = (target_risk / ATR_i) / sum(target_risk / ATR_j for all j)
    """
    if not basket_picks:
        return []

    inv_atrs = []
    for p in basket_picks:
        atr = _estimate_atr(p)
        atr = max(atr, 0.1)  # floor to avoid division by zero
        inv_atrs.append(target_risk / atr)

    total_inv_atr = sum(inv_atrs)
    if total_inv_atr == 0:
        # Equal weight fallback
        n = len(basket_picks)
        return [100.0 / n] * n

    raw_pcts = [(iv / total_inv_atr) * 100.0 for iv in inv_atrs]
    # Cap any single position at 40% to prevent concentration (PEPE 76% bug)
    MAX_SINGLE = 40.0
    capped = [min(p, MAX_SINGLE) for p in raw_pcts]
    # Redistribute excess to others
    total_capped = sum(capped)
    return [p / total_capped * 100.0 for p in capped] if total_capped > 0 else raw_pcts


def _compute_correlation_score(basket_picks: list) -> float:
    """
    0 = fully uncorrelated (all different groups), 1 = perfectly correlated
    (all same group).  Based on group overlap ratio.
    """
    if len(basket_picks) <= 1:
        return 0.0

    groups = [_get_group(p["symbol"]) for p in basket_picks]
    unique = len(set(groups))
    total = len(groups)

    # Ratio of duplicated groups
    return 1.0 - (unique / total)


def _diversification_grade(basket_picks: list) -> str:
    """A=4+ groups, B=3, C=2, D=1."""
    groups = set(_get_group(p["symbol"]) for p in basket_picks)
    n = len(groups)
    if n >= 4:
        return "A"
    elif n == 3:
        return "B"
    elif n == 2:
        return "C"
    else:
        return "D"


def _allows_group(selected_groups: dict, group: str) -> bool:
    """
    Check whether adding a pick from `group` is allowed.
    Max 1 per group, except large_cap can have 2 (one BTC, one ETH).
    """
    count = selected_groups.get(group, 0)
    if group == "large_cap":
        return count < 2
    return count < 1


def _large_cap_allows_symbol(selected_picks: list, symbol: str) -> bool:
    """
    For large_cap group: allow only if the base symbol isn't already present.
    i.e., BTC+ETH is OK but BTC+BTC is not.
    """
    base = _extract_base_symbol(symbol)
    for p in selected_picks:
        if _get_group(p["symbol"]) == "large_cap":
            if _extract_base_symbol(p["symbol"]) == base:
                return False
    return True


def generate_balanced_basket(
    picks: list,
    max_positions: int = 4,
    require_hedge: bool = True,
    portfolio_usd: float = 1000.0,
) -> dict:
    """
    Generate a balanced trading basket from scored picks.

    Args:
        picks: list of pick dicts (must have 'symbol', 'direction', 'elite_score')
        max_positions: maximum number of positions in the basket
        require_hedge: if True, ensures at least one SHORT or synthetic hedge
        portfolio_usd: total portfolio value for USD sizing

    Returns:
        dict with 'basket', 'hedge', 'correlation_score', 'diversification_grade',
        'total_positions', 'long_pct', 'short_pct'
    """
    if not picks:
        return {
            "basket": [],
            "hedge": None,
            "correlation_score": 0.0,
            "diversification_grade": "D",
            "total_positions": 0,
            "long_pct": 0.0,
            "short_pct": 0.0,
        }

    # M-108: Sort by strategy rolling WR composite when available (elite_score eff≈0.005=noise).
    # m108_rank_score is set by elite_scorer.py after strategy_wr_ranker enrichment.
    def _rank_key(p: dict) -> float:
        r = p.get("m108_rank_score")
        if r is not None:
            return float(r)
        return float(p.get("elite_score", 0)) / 183.0  # normalize to 0-1 for fair comparison

    scored = [p for p in picks if p.get("elite_score") is not None or p.get("m108_rank_score") is not None]
    scored.sort(key=_rank_key, reverse=True)

    longs = [p for p in scored if p.get("direction", "").upper() == "LONG"]
    shorts = [p for p in scored if p.get("direction", "").upper() == "SHORT"]

    # ---- Pick selection algorithm ----
    selected = []
    selected_groups = {}  # group -> count
    direction_counts = {"LONG": 0, "SHORT": 0}

    for pick in scored:
        if len(selected) >= max_positions:
            break

        group = _get_group(pick["symbol"])
        direction = pick.get("direction", "LONG").upper()

        # (a) Check correlation group constraint
        if not _allows_group(selected_groups, group):
            continue

        # For large_cap, also check we don't double up on same base
        if group == "large_cap" and not _large_cap_allows_symbol(selected, pick["symbol"]):
            continue

        # (b) Max 3 same-direction
        if direction_counts.get(direction, 0) >= 3:
            continue

        # Accept this pick
        selected.append(pick)
        selected_groups[group] = selected_groups.get(group, 0) + 1
        direction_counts[direction] = direction_counts.get(direction, 0) + 1

    # ---- Hedge requirement ----
    hedge = None
    all_long = all(p.get("direction", "LONG").upper() == "LONG" for p in selected)
    all_short = all(p.get("direction", "LONG").upper() == "SHORT" for p in selected)

    if require_hedge and selected:
        # Check if any SHORT picks score above threshold (use rank_key for M-108 consistency)
        good_shorts = [s for s in shorts if _rank_key(s) > 0.19  # ~35/183 normalized
                       and s not in selected]

        if all_long and good_shorts:
            # Replace lowest scorer with best opposite-direction pick
            lowest = min(selected, key=_rank_key)
            best_short = good_shorts[0]

            # Only replace if we have more than 1 pick
            if len(selected) > 1:
                selected.remove(lowest)
                selected.append(best_short)
                # Update direction counts
                direction_counts["LONG"] -= 1
                direction_counts["SHORT"] = direction_counts.get("SHORT", 0) + 1
            else:
                # Single pick — use synthetic hedge instead
                hedge = _make_synthetic_hedge(selected)

        elif all_long:
            # No good shorts available — synthetic hedge
            hedge = _make_synthetic_hedge(selected)

        elif all_short:
            # All short, try to add a long
            good_longs = [l for l in longs if _rank_key(l) > 0.27  # ~50/183 normalized
                          and l not in selected]
            if good_longs and len(selected) > 1:
                lowest = min(selected, key=_rank_key)
                selected.remove(lowest)
                selected.append(good_longs[0])
                direction_counts["SHORT"] -= 1
                direction_counts["LONG"] = direction_counts.get("LONG", 0) + 1

    # ---- Risk-parity position sizing ----
    size_pcts = _compute_risk_parity_sizes(selected)

    # If hedge exists, reduce all sizes by 20% and allocate to hedge
    hedge_reduction = 0.20 if hedge else 0.0
    adjusted_pcts = [s * (1.0 - hedge_reduction) for s in size_pcts]

    if hedge:
        hedge["size_pct"] = round(hedge_reduction * 100.0, 1)
        hedge["size_usd"] = round(hedge["size_pct"] / 100.0 * portfolio_usd, 2)

    # ---- Build output basket ----
    basket_items = []
    for i, pick in enumerate(selected):
        pct = adjusted_pcts[i] if i < len(adjusted_pcts) else 0
        group = _get_group(pick["symbol"])
        basket_items.append({
            "symbol": pick["symbol"],
            "direction": pick.get("direction", "LONG").upper(),
            "score": pick.get("elite_score", 0),
            "size_pct": round(pct, 1),
            "size_usd": round(pct / 100.0 * portfolio_usd, 2),
            "group": group,
            "reason": pick.get("reason", "")[:80],
        })

    # ---- Compute stats ----
    long_pct = sum(b["size_pct"] for b in basket_items if b["direction"] == "LONG")
    short_pct = sum(b["size_pct"] for b in basket_items if b["direction"] == "SHORT")
    if hedge:
        short_pct += hedge["size_pct"]

    return {
        "basket": basket_items,
        "hedge": hedge,
        "correlation_score": round(_compute_correlation_score(selected), 2),
        "diversification_grade": _diversification_grade(selected),
        "total_positions": len(basket_items) + (1 if hedge else 0),
        "long_pct": round(long_pct, 1),
        "short_pct": round(short_pct, 1),
    }


def _make_synthetic_hedge(selected: list) -> dict:
    """
    Create a synthetic hedge entry from the weakest-scoring pick in the basket.
    """
    if not selected:
        return None
    weakest = min(selected, key=lambda p: p.get("m108_rank_score") or p.get("elite_score", 0) / 183.0)
    return {
        "symbol": weakest["symbol"],
        "direction": "SHORT" if weakest.get("direction", "LONG").upper() == "LONG" else "LONG",
        "size_pct": 0.0,  # Will be set by caller
        "reason": "Correlation hedge (synthetic — weakest scorer inverted)",
    }


def print_basket_summary(result: dict) -> None:
    """Pretty-print the basket for CLI output."""
    basket = result.get("basket", [])
    hedge = result.get("hedge")

    print("=" * 64)
    print("  BALANCED TRADING BASKET")
    print("=" * 64)

    if not basket:
        print("  (no picks available)")
        print("=" * 64)
        return

    print(f"  Positions: {result['total_positions']}  |  "
          f"Diversification: {result['diversification_grade']}  |  "
          f"Correlation: {result['correlation_score']:.2f}")
    print(f"  Long: {result['long_pct']:.1f}%  |  Short: {result['short_pct']:.1f}%")
    print("-" * 64)

    for i, item in enumerate(basket, 1):
        arrow = "^" if item["direction"] == "LONG" else "v"
        print(f"  {i}. {arrow} {item['symbol']:<14} "
              f"Score: {item['score']:>3}  "
              f"Size: {item['size_pct']:>5.1f}% (${item['size_usd']:>8.2f})  "
              f"[{item['group']}]")

    if hedge:
        arrow = "^" if hedge["direction"] == "LONG" else "v"
        print("-" * 64)
        print(f"  H. {arrow} {hedge['symbol']:<14} "
              f"HEDGE  "
              f"Size: {hedge['size_pct']:>5.1f}% (${hedge.get('size_usd', 0):>8.2f})")
        print(f"     Reason: {hedge['reason']}")

    print("=" * 64)


def _load_active_picks() -> list:
    """Load picks from active_picks.json."""
    # Try relative to this file first, then cwd
    candidates = [
        Path(__file__).parent / "data" / "active_picks.json",
        Path("alpha_engine") / "data" / "active_picks.json",
        Path("data") / "active_picks.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            # Some formats wrap in a dict
            if isinstance(data, dict) and "picks" in data:
                return data["picks"]
            return []
    print(f"ERROR: active_picks.json not found. Tried: {[str(c) for c in candidates]}")
    sys.exit(1)


if __name__ == "__main__":
    picks = _load_active_picks()
    open_picks = [p for p in picks if p.get("status", "").upper() == "OPEN"]

    if not open_picks:
        print("No OPEN picks found in active_picks.json")
        sys.exit(0)

    print(f"Loaded {len(open_picks)} open picks from active_picks.json\n")

    result = generate_balanced_basket(open_picks, max_positions=4, require_hedge=True)
    print_basket_summary(result)

    # Also dump JSON for piping
    print("\n--- JSON output ---")
    print(json.dumps(result, indent=2, default=str))
