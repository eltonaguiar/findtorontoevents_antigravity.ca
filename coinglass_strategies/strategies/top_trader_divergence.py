"""S2: Top-Trader Divergence — whale lead signal.

Primary mode: top_trader_account vs global ratio divergence (follows whales).
Fallback mode: global ratio vs funding_rate direction divergence.
  - If global says LONG (>1.0) but funding is very negative, that's a
    divergence signal (crowd is long but smart money is shorting via funding).
  - If global says SHORT (<1.0) but funding is very positive, same logic inverted.
"""
import logging
from typing import Dict, List, Optional
from .base import Signal
from .. import config

logger = logging.getLogger(__name__)


def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    glob = current_ratios.get("global")
    if glob is None:
        return None

    top = current_ratios.get("top_trader_account")

    # --- Primary mode: top_trader_account vs global divergence ---
    if top is not None:
        top_side = 1 if top > 1 else -1
        glob_side = 1 if glob > 1 else -1
        diff = abs(top - glob)
        if top_side == glob_side or diff < config.WHALE_DIVERGENCE_MIN_DIFF:
            return None
        direction = "LONG" if top > 1 else "SHORT"
        conf = 0.60 + 0.10 * min(diff / 0.3, 2.0)
        conf = round(min(conf, 0.80), 3)
        return Signal(symbol=symbol, direction=direction, strategy="coinglass_whale_divergence",
                      confidence=conf, reason=f"Top-trader={top:.3f} vs Global={glob:.3f} (diff={diff:.3f}), following whales",
                      ratios=current_ratios)

    # --- Fallback mode: global ratio vs funding_rate divergence ---
    # Get latest funding_rate from recent DB rows
    funding = None
    for row in reversed(recent_rows):
        fr = row.get("funding_rate")
        if fr is not None:
            funding = float(fr)
            break

    if funding is None:
        logger.debug("S2-WhaleDivergence: no top_trader_account or funding_rate for %s, skipping", symbol)
        return None

    # Divergence detection:
    # Global LONG (>1.0) + very negative funding => shorts are paying longs, contrarian SHORT
    # Global SHORT (<1.0) + very positive funding => longs are paying shorts, contrarian LONG
    glob_long = glob > 1.0
    funding_negative = funding < -0.0005  # meaningfully negative (not just noise)
    funding_positive = funding > 0.0005   # meaningfully positive

    if glob_long and funding_negative:
        # Crowd is long but funding says shorts are dominant — follow funding (SHORT)
        direction = "SHORT"
        divergence_strength = abs(funding) * 1000 + abs(glob - 1.0)  # combined measure
    elif not glob_long and funding_positive:
        # Crowd is short but funding says longs are dominant — follow funding (LONG)
        direction = "LONG"
        divergence_strength = abs(funding) * 1000 + abs(glob - 1.0)
    else:
        return None

    # Require minimum divergence strength
    if divergence_strength < 0.3:
        return None

    # Slightly lower confidence for fallback mode (capped at 0.72 vs 0.80 for primary)
    conf = 0.55 + 0.08 * min(divergence_strength / 0.5, 2.0)
    conf = round(min(conf, 0.72), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_whale_divergence",
                  confidence=conf,
                  reason=f"[Fallback] Global={glob:.3f} vs Funding={funding:.6f} divergence (strength={divergence_strength:.3f})",
                  ratios=current_ratios)
