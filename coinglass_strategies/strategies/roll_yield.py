"""S10: Roll-Yield / Funding Rate Term-Structure — exploits persistent
positive or negative funding rates to harvest carry/roll yield.

Unlike the existing funding_confirmation.py which looks for funding-ratio
confluence with long/short ratios, this strategy specifically targets the
term structure of funding rates over time.

Logic:
  - Track funding rate history (rolling 24h window)
  - Compute cumulative funding cost/yield over multiple periods
  - If annualized funding yield > threshold AND is persistently positive:
    → SHORT signal (pay nothing, earn funding from longs paying shorts)
  - If annualized funding yield < -threshold AND persistently negative:
    → LONG signal (earn funding from shorts paying longs)
  - Requires consistency: funding must have been in the same sign for
    at least N consecutive observations to confirm persistence.

This is distinct from:
  - funding_confirmation.py (single funding + ratio confluence)
  - funding_rate_extreme in alpha_engine (one-off extreme funding events)
  - FreshPicks DNA (uses VWMA z-score, different methodology)
"""
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

from .base import Signal

logger = logging.getLogger(__name__)

BINANCE_FUTURES = "https://fapi.binance.com"
OKX_API = "https://www.okx.com"

# Funding rate history for term-structure analysis
_funding_history: Dict[str, List[Dict]] = {}
_MAX_FUNDING_HISTORY = 48  # 48 × 8h = 16 days of funding data


def _fetch_funding_history(symbol: str, limit: int = 10) -> List[Dict]:
    """Fetch recent funding rate history from Binance."""
    try:
        resp = requests.get(
            f"{BINANCE_FUTURES}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return [
                    {
                        "rate": float(r.get("fundingRate", 0)),
                        "time": int(r.get("fundingTime", 0)),
                    }
                    for r in data
                    if r.get("fundingRate") is not None
                ]
    except Exception as e:
        logger.debug("Binance funding history failed for %s: %s", symbol, e)

    # OKX fallback
    try:
        okx_sym = symbol.replace("USDT", "-USDT-SWAP")
        resp = requests.get(
            f"{OKX_API}/api/v5/public/funding-rate-history",
            params={"instId": okx_sym, "limit": str(limit)},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data"):
                return [
                    {
                        "rate": float(r.get("fundingRate", 0)),
                        "time": int(r.get("fundingTime", 0)),
                    }
                    for r in data["data"]
                    if r.get("fundingRate") is not None
                ]
    except Exception as e:
        logger.debug("OKX funding history failed for %s: %s", symbol, e)

    return []


def run(symbol: str, recent_rows: list, current_ratios: dict) -> Optional[Signal]:
    """Roll-yield / funding term-structure strategy.

    Identifies persistent funding rate regimes and trades the carry.
    """
    history = _fetch_funding_history(symbol, limit=24)
    if len(history) < 6:
        return None  # Need at least 6 funding periods (2 days)

    rates = [h["rate"] for h in history]

    # Compute metrics
    avg_rate = sum(rates) / len(rates)
    recent_avg = sum(rates[-3:]) / 3  # Last 3 periods (24h)
    annualized_yield = avg_rate * 3 * 365  # 3 periods/day × 365 days

    # Count consecutive same-sign funding periods (from most recent)
    consecutive = 0
    sign = 1 if rates[-1] >= 0 else -1
    for r in reversed(rates):
        if (r >= 0 and sign > 0) or (r < 0 and sign < 0):
            consecutive += 1
        else:
            break

    # Thresholds
    MIN_ANNUALIZED_YIELD = 0.10  # 10% annualized
    MIN_CONSECUTIVE = 4  # 4 consecutive periods (~32h)
    MIN_RECENT_MAGNITUDE = 0.0001  # 0.01% per period

    if abs(annualized_yield) < MIN_ANNUALIZED_YIELD:
        return None
    if consecutive < MIN_CONSECUTIVE:
        return None
    if abs(recent_avg) < MIN_RECENT_MAGNITUDE:
        return None

    # Direction: trade opposite to the funding payers
    if avg_rate > 0:
        # Longs are paying shorts → SHORT earns carry
        direction = "SHORT"
        reason = (
            f"Roll-yield carry: persistent positive funding "
            f"({avg_rate*100:.4f}% avg over {len(rates)} periods). "
            f"Annualized yield: {annualized_yield*100:.1f}%. "
            f"Consecutive positive: {consecutive} periods. "
            f"Last 3 avg: {recent_avg*100:.4f}%. "
            f"Shorts earn carry from overleveraged longs."
        )
    else:
        # Shorts are paying longs → LONG earns carry
        direction = "LONG"
        reason = (
            f"Roll-yield carry: persistent negative funding "
            f"({avg_rate*100:.4f}% avg over {len(rates)} periods). "
            f"Annualized yield: {abs(annualized_yield)*100:.1f}%. "
            f"Consecutive negative: {consecutive} periods. "
            f"Last 3 avg: {recent_avg*100:.4f}%. "
            f"Longs earn carry from overleveraged shorts."
        )

    # Confidence based on persistence and magnitude
    persistence_score = min(consecutive / 12.0, 1.0)  # Max at 12 consecutive
    magnitude_score = min(abs(annualized_yield) / 0.50, 1.0)  # Max at 50% ann.
    conf = 0.50 + 0.15 * persistence_score + 0.15 * magnitude_score
    conf = round(min(conf, 0.85), 3)

    return Signal(
        symbol=symbol,
        direction=direction,
        strategy="coinglass_roll_yield",
        confidence=conf,
        reason=reason,
        ratios={
            "avg_funding_rate": round(avg_rate, 8),
            "recent_avg_rate": round(recent_avg, 8),
            "annualized_yield": round(annualized_yield, 4),
            "consecutive_periods": consecutive,
            "total_periods": len(rates),
            **current_ratios,
        },
    )
