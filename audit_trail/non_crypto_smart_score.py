"""
Non-crypto Smart Score — VIX regime, earnings, sector momentum (Downloads-aligned).

Callers must pass real optional inputs (days_to_earnings, sector_momentum_20d, etc.);
unknown → neutral bands (no fabricated fundamentals).
"""

from __future__ import annotations

import math
from typing import Any, Optional

SECTOR_ETF_MAP: dict[str, str] = {
    "AAPL": "XLK",
    "MSFT": "XLK",
    "GOOGL": "XLK",
    "META": "XLK",
    "NVDA": "XLK",
    "AMZN": "XLY",
    "TSLA": "XLY",
    "PFE": "XLV",
    "UNH": "XLV",
    "ABBV": "XLV",
    "JNJ": "XLV",
    "JPM": "XLF",
    "BAC": "XLF",
    "GS": "XLF",
    "XOM": "XLE",
    "CVX": "XLE",
    "WMT": "XLP",
    "SBUX": "XLY",
    "KO": "XLP",
    "GM": "XLI",
    "F": "XLI",
    "CAT": "XLI",
    "GME": "SPY",
    "AMC": "SPY",
}


def get_sector_etf(symbol: str) -> str:
    return SECTOR_ETF_MAP.get(str(symbol or "").upper(), "SPY")


def calculate_non_crypto_smart_score(
    pick: dict[str, Any],
    vix_regime: str = "UNKNOWN",
    vix: Optional[float] = None,
    days_to_earnings: Optional[int] = None,
    sector_momentum_20d: Optional[float] = None,
    daily_aligned: Optional[bool] = None,
    weekly_aligned: Optional[bool] = None,
) -> dict[str, Any]:
    _ = vix
    score = 0.0
    breakdown: dict[str, float] = {}

    direction = str(pick.get("direction", "LONG")).upper()

    if vix_regime in ("CLEAR_BULL", "PARTLY_CLOUDY"):
        if direction in ("LONG", "BUY"):
            score += 25
            breakdown["regime"] = 25.0
        else:
            score += 5
            breakdown["regime"] = 5.0
    elif vix_regime == "OVERCAST":
        score += 12
        breakdown["regime"] = 12.0
    elif vix_regime in ("STORM", "HURRICANE"):
        if direction in ("SHORT", "SELL"):
            score += 25
            breakdown["regime"] = 25.0
        else:
            score += 5
            breakdown["regime"] = 5.0
    else:
        score += 12
        breakdown["regime"] = 12.0

    elite = float(pick.get("elite_score", 50) or 50)
    elite_pts = min(35.0, max(0.0, elite * 0.35))
    score += elite_pts
    breakdown["elite"] = round(elite_pts, 1)

    age_h = float(pick.get("age_hours", 0) or 0)
    freshness_pts = 15.0 * math.exp(-age_h / 18.0)
    score += freshness_pts
    breakdown["freshness"] = round(freshness_pts, 1)

    tp = float(pick.get("tp", 0) or pick.get("take_profit", 0) or 0)
    entry = float(pick.get("entry", 0) or pick.get("entry_price", 0) or 0)
    current = float(pick.get("current_price", entry) or entry)

    tp_pts = 7.0
    if tp and entry and abs(tp - entry) > 1e-12:
        if direction in ("LONG", "BUY"):
            tp_remaining = (tp - current) / (tp - entry) if (tp - entry) > 0 else 0.0
        else:
            tp_remaining = (current - tp) / (entry - tp) if (entry - tp) > 0 else 0.0
        tp_remaining = max(0.0, min(1.0, tp_remaining))
        if tp_remaining > 0.7:
            tp_pts = 15.0
        elif tp_remaining > 0.5:
            tp_pts = 10.0
        elif tp_remaining > 0.3:
            tp_pts = 5.0
        else:
            tp_pts = 0.0
    score += tp_pts
    breakdown["tp_remaining"] = tp_pts

    if daily_aligned is True and weekly_aligned is True:
        tf_pts = 10.0
    elif daily_aligned is True or weekly_aligned is True:
        tf_pts = 5.0
    elif daily_aligned is False and weekly_aligned is False:
        tf_pts = 0.0
    else:
        tf_pts = 5.0
    score += tf_pts
    breakdown["tf_alignment"] = tf_pts

    earnings_pts = 0.0
    if days_to_earnings is not None:
        if days_to_earnings > 10:
            earnings_pts = 10.0
        elif days_to_earnings > 5:
            earnings_pts = 5.0
        elif days_to_earnings > 2:
            earnings_pts = 0.0
        elif days_to_earnings >= 0 and direction in ("LONG", "BUY"):
            earnings_pts = -15.0
        elif -5 < days_to_earnings < -1 and direction in ("SHORT", "SELL"):
            earnings_pts = -15.0
    score += earnings_pts
    breakdown["earnings_gate"] = earnings_pts

    sector_pts = 0.0
    if sector_momentum_20d is not None:
        if direction in ("LONG", "BUY"):
            if sector_momentum_20d > 3:
                sector_pts = 5.0
            elif sector_momentum_20d > 0:
                sector_pts = 3.0
            elif sector_momentum_20d > -3:
                sector_pts = 0.0
            else:
                sector_pts = -10.0
        else:
            if sector_momentum_20d < -3:
                sector_pts = 5.0
            elif sector_momentum_20d < 0:
                sector_pts = 3.0
            else:
                sector_pts = -5.0
    score += sector_pts
    breakdown["sector_momentum"] = sector_pts

    final_score = min(100.0, max(0.0, score))
    return {
        "smart_score": round(final_score, 1),
        "breakdown": breakdown,
        "vix_regime": vix_regime,
        "earnings_gate": earnings_pts,
        "sector_gate": sector_pts,
    }
