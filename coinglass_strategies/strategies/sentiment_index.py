"""S7: Composite Sentiment Index — weighted multi-ratio score.

Full-data weights: top_trader_account 40%, taker 30%, global 20%, top_trader_position 10%.
Fallback weights (when top_trader/taker are NULL from Binance geo-block):
  global 70%, funding_rate 30%.

Funding rate is normalized as a sentiment indicator:
  - Positive funding -> longs pay shorts -> bullish sentiment (normalized > 0.5)
  - Negative funding -> shorts pay longs -> bearish sentiment (normalized < 0.5)
"""
import logging
from typing import Dict, List, Optional
from .base import Signal
from .. import config

logger = logging.getLogger(__name__)


def _normalize(value: float, values: List[float]) -> float:
    if not values:
        return 0.5
    mn, mx = min(values), max(values)
    if mx == mn:
        return 0.5
    return (value - mn) / (mx - mn)


def _normalize_funding(funding: float, funding_history: List[float]) -> float:
    """Normalize funding rate into 0-1 sentiment score.

    Positive funding = bullish sentiment (>0.5), negative = bearish (<0.5).
    Uses historical range for normalization, falls back to fixed range.
    """
    if funding_history and len(funding_history) >= 3:
        return _normalize(funding, funding_history)
    # Fixed-range fallback: typical funding range is -0.001 to +0.001
    # Map to 0-1 range with 0.5 as neutral
    clamped = max(-0.002, min(0.002, funding))
    return 0.5 + (clamped / 0.004)


def run(symbol: str, recent_rows: List[Dict], current_ratios: Dict) -> Optional[Signal]:
    if len(recent_rows) < 5:
        return None

    # Build historical data from DB rows
    hist = {"global": [], "top_trader_account": [], "taker": [],
            "top_trader_position": [], "funding_rate": []}
    for row in recent_rows:
        for key, col in [("global", "global_ratio"),
                         ("top_trader_account", "top_trader_account_ratio"),
                         ("taker", "taker_ratio"),
                         ("top_trader_position", "top_trader_position_ratio"),
                         ("funding_rate", "funding_rate")]:
            val = row.get(col)
            if val is not None:
                hist[key].append(float(val))

    # Current values
    cur = {
        "global": current_ratios.get("global"),
        "top_trader_account": current_ratios.get("top_trader_account"),
        "taker": current_ratios.get("taker"),
        "top_trader_position": current_ratios.get("top_trader_position"),
    }

    # Get latest funding_rate from DB rows (not in current_ratios)
    cur_funding = None
    for row in reversed(recent_rows):
        fr = row.get("funding_rate")
        if fr is not None:
            cur_funding = float(fr)
            break

    if cur["global"] is None:
        return None

    # Determine which weighting scheme to use
    has_top_trader = cur["top_trader_account"] is not None
    has_taker = cur["taker"] is not None

    if has_top_trader or has_taker:
        # Full-data mode: original weights
        weights = {"top_trader_account": 0.40, "taker": 0.30,
                   "global": 0.20, "top_trader_position": 0.10}
        mode = "full"
    else:
        # Fallback mode: global 70% + funding_rate 30%
        weights = {"global": 0.70}
        mode = "fallback"

    total_weight = 0.0
    index = 0.0

    # Process ratio-based components
    for key, weight in weights.items():
        val = cur.get(key)
        if val is not None and hist.get(key):
            norm = _normalize(val, hist[key])
            index += norm * weight
            total_weight += weight

    # Add funding_rate component in fallback mode
    if mode == "fallback" and cur_funding is not None:
        funding_norm = _normalize_funding(cur_funding, hist.get("funding_rate", []))
        funding_weight = 0.30
        index += funding_norm * funding_weight
        total_weight += funding_weight

    if total_weight == 0:
        return None

    index /= total_weight
    long_thresh = config.SENTIMENT_LONG_THRESHOLD
    short_thresh = config.SENTIMENT_SHORT_THRESHOLD
    if short_thresh < index < long_thresh:
        return None

    direction = "LONG" if index >= long_thresh else "SHORT"
    conf = 0.55 + 0.10 * abs(index - 0.5)
    conf = round(min(conf, 0.70), 3)

    reason = f"Sentiment index={index:.3f} [{mode}] (threshold: long>{long_thresh}, short<{short_thresh})"
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_sentiment_composite",
                  confidence=conf, reason=reason, ratios=current_ratios)
