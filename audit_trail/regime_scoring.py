"""
Regime / “market weather” weights for strategy-family scoring adjustments.

Consumes only real inputs (VIX, SPX vs moving average proxy, breadth %) passed in by
callers — no invented market data. Use `weather_adjusted_score` as a multiplier hook
from dashboard or quality_gates when those inputs are available.
"""

from __future__ import annotations

from typing import Any

MARKET_WEATHER: dict[str, dict[str, Any]] = {
    "CLEAR_BULL": {
        "momentum_weight": 1.3,
        "mean_reversion_weight": 0.6,
        "breakout_weight": 1.4,
        "pead_weight": 1.0,
        "contrarian_weight": 0.4,
        "max_positions": 8,
        "sl_multiplier": 0.9,
    },
    "PARTLY_CLOUDY": {
        "momentum_weight": 1.0,
        "mean_reversion_weight": 1.0,
        "breakout_weight": 0.8,
        "pead_weight": 1.2,
        "contrarian_weight": 0.8,
        "max_positions": 6,
        "sl_multiplier": 1.0,
    },
    "OVERCAST": {
        "momentum_weight": 0.7,
        "mean_reversion_weight": 1.3,
        "breakout_weight": 0.5,
        "pead_weight": 0.8,
        "contrarian_weight": 1.2,
        "max_positions": 4,
        "sl_multiplier": 1.2,
    },
    "STORM": {
        "momentum_weight": 0.3,
        "mean_reversion_weight": 1.5,
        "breakout_weight": 0.2,
        "pead_weight": 0.5,
        "contrarian_weight": 1.5,
        "max_positions": 3,
        "sl_multiplier": 1.5,
    },
    "HURRICANE": {
        "momentum_weight": 0.0,
        "mean_reversion_weight": 0.0,
        "breakout_weight": 0.0,
        "pead_weight": 0.0,
        "contrarian_weight": 0.5,
        "max_positions": 1,
        "sl_multiplier": 2.0,
    },
}


def get_market_weather(
    vix: float,
    spx_vs_200dma_pct: float,
    market_breadth_pct: float | None,
) -> str:
    """Classify weather from observable macro inputs (caller supplies real values)."""
    breadth = market_breadth_pct if market_breadth_pct is not None else 50.0
    if vix > 35:
        return "HURRICANE"
    if vix > 25 and spx_vs_200dma_pct < 0:
        return "STORM"
    if vix > 20 or breadth < 42.0:
        return "OVERCAST"
    if vix > 15:
        return "PARTLY_CLOUDY"
    return "CLEAR_BULL"


def classify_strategy_family(strategy: str) -> str:
    s = (strategy or "").lower()
    if any(x in s for x in ("rsi", "connors", "mean", "reversion", "bb", "boll")):
        return "mean_reversion"
    if any(x in s for x in ("breakout", "squeeze", "donchian", "momentum_ride")):
        return "breakout"
    if any(x in s for x in ("pead", "earnings", "eps", "revision")):
        return "pead"
    if any(x in s for x in ("fear", "greed", "contrarian", "fade")):
        return "contrarian"
    return "momentum"


def weather_adjusted_score(
    pick_score: float,
    weather: str,
    strategy_name: str,
    *,
    active_position_count: int = 0,
) -> float:
    """Scale a pick score by regime weights; optional exposure penalty."""
    cfg = MARKET_WEATHER.get(weather, MARKET_WEATHER["PARTLY_CLOUDY"])
    fam = classify_strategy_family(strategy_name)
    key = "%s_weight" % fam
    w = float(cfg.get(key, 1.0))
    adjusted = float(pick_score) * w
    mx = int(cfg.get("max_positions", 6))
    if active_position_count >= mx and mx > 0:
        adjusted *= 0.5
    return max(0.0, min(100.0, adjusted))
