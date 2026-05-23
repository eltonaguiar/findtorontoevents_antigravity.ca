"""S8: Spike Detection — event-driven sudden ratio change.

Checks all available ratio types AND funding_rate for sudden spikes.
When top_trader_account and taker are NULL (Binance geo-block), still works
with global_ratio + funding_rate spikes.

Funding rate spikes use absolute change (not percentage) since funding
rates are small numbers where % change is misleading. A funding rate
shift of >0.0005 in one interval is significant.
"""
import logging
from typing import Dict, List, Optional
from .base import Signal
from .. import config

logger = logging.getLogger(__name__)

# Funding rate absolute change threshold (0.05% = 0.0005)
_FUNDING_SPIKE_THRESHOLD = 0.0005


def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    if len(recent_rows) < 2:
        return None
    prev = recent_rows[-2] if len(recent_rows) >= 2 else recent_rows[-1]
    threshold_pct = config.SPIKE_THRESHOLD_PCT

    # --- Check ratio-based spikes (percentage change) ---
    ratio_keys = [
        ("global_ratio", "global", "Global"),
        ("top_trader_account_ratio", "top_trader_account", "Top-Trader Account"),
        ("taker_ratio", "taker", "Taker"),
        ("top_trader_position_ratio", "top_trader_position", "Top-Trader Position"),
    ]
    best_spike = None
    best_pct = 0.0
    for db_col, cur_key, label in ratio_keys:
        prev_val = prev.get(db_col)
        cur_val = current_ratios.get(cur_key)
        if prev_val is None or cur_val is None or prev_val == 0:
            continue
        pct_change = abs(cur_val - float(prev_val)) / float(prev_val) * 100
        if pct_change > threshold_pct and pct_change > best_pct:
            best_pct = pct_change
            best_spike = (label, float(prev_val), cur_val, pct_change)

    # --- Check funding_rate spike (absolute change) ---
    prev_funding = prev.get("funding_rate")
    # Get current funding from latest DB row
    cur_funding = None
    for row in reversed(recent_rows):
        fr = row.get("funding_rate")
        if fr is not None:
            cur_funding = float(fr)
            break

    funding_spike = None
    if prev_funding is not None and cur_funding is not None:
        abs_change = abs(cur_funding - float(prev_funding))
        if abs_change >= _FUNDING_SPIKE_THRESHOLD:
            # Convert to equivalent "pct" scale for comparison with ratio spikes
            # A 0.001 funding shift is roughly equivalent to a 50% ratio spike in signal strength
            equiv_pct = abs_change / _FUNDING_SPIKE_THRESHOLD * (threshold_pct / 2)
            funding_spike = ("Funding Rate", float(prev_funding), cur_funding, equiv_pct, abs_change)

    # Pick the strongest spike (ratio or funding)
    if funding_spike and (best_spike is None or funding_spike[3] > best_pct):
        label, prev_val, cur_val, _, abs_change = funding_spike
        # Funding direction: rate going MORE positive = bullish pressure (longs paying more)
        # Contrarian: spike positive = crowded long = SHORT; spike negative = crowded short = LONG
        direction = "SHORT" if cur_val > prev_val else "LONG"
        conf = 0.50 + 0.05 * min(abs_change / _FUNDING_SPIKE_THRESHOLD, 3.0)
        conf = round(min(conf, 0.65), 3)
        return Signal(symbol=symbol, direction=direction, strategy="coinglass_spike_detector",
                      confidence=conf,
                      reason=f"Funding rate spike: {prev_val:.6f}->{cur_val:.6f} (abs change={abs_change:.6f})",
                      ratios=current_ratios)

    if best_spike is None:
        return None

    label, prev_val, cur_val, pct = best_spike
    direction = "LONG" if cur_val > prev_val else "SHORT"
    conf = 0.50 + 0.05 * min(pct / 30.0, 3.0)
    conf = round(min(conf, 0.65), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_spike_detector",
                  confidence=conf, reason=f"{label} spike: {prev_val:.3f}->{cur_val:.3f} ({pct:.1f}% change)",
                  ratios=current_ratios)
