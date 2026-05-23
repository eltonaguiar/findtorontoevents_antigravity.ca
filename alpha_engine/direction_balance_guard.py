#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Direction Balance Guard
========================================
Caps LONG/SHORT ratio based on market regime (Fear & Greed Index).

Problem: During Extreme Fear (FGI=11), 77% of positions were LONG -- massively
overexposed to downside. This guard enforces regime-aware direction caps.

Rules:
  - Extreme Fear (FGI < 20):  Max 40% LONG, min 40% SHORT
  - Fear (FGI 20-40):         Max 50% LONG
  - Neutral (FGI 40-60):      No caps
  - Greed (FGI 60-80):        Max 50% SHORT
  - Extreme Greed (FGI > 80): Max 40% SHORT, min 40% LONG

stdlib only -- uses urllib for HTTP, reuses feargreed_cache.json pattern.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_FG_CACHE_FILE = _DATA_DIR / "feargreed_cache.json"
_FG_API_URL = "https://api.alternative.me/fng/?limit=7&format=json"
_FG_CACHE_TTL = 2 * 3600  # 2 hours
_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Fear & Greed fetch (reuses cache pattern from cryptopanic_feargreed.py)
# ---------------------------------------------------------------------------

def get_fear_greed() -> int:
    """Fetch current Fear & Greed Index value.

    Returns integer 0-100. Falls back to 50 (neutral) on failure.
    Reuses feargreed_cache.json written by cryptopanic_feargreed.py if fresh.
    """
    # Try reading existing cache first (may be written by cryptopanic_feargreed.py)
    try:
        if _FG_CACHE_FILE.exists():
            data = json.loads(_FG_CACHE_FILE.read_text(encoding="utf-8"))
            cached_at = data.get("_cached_at", 0)
            if time.time() - cached_at < _FG_CACHE_TTL and "current" in data:
                return int(data["current"])
    except Exception:
        pass

    # Fetch fresh from API
    try:
        req = urllib.request.Request(
            _FG_API_URL,
            headers={"User-Agent": "AlphaEngine/2.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        items = raw.get("data", [])
        if items:
            value = int(items[0].get("value", 50))
            # Save to cache for other modules
            cache_data = {
                "current": value,
                "classification": items[0].get("value_classification", "Neutral"),
                "_cached_at": time.time(),
                "_ttl": _FG_CACHE_TTL,
            }
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _FG_CACHE_FILE.write_text(
                json.dumps(cache_data, indent=2), encoding="utf-8"
            )
            return value
    except Exception as e:
        logger.warning("Fear & Greed fetch failed: %s", e)

    return 50  # neutral fallback


# ---------------------------------------------------------------------------
# Direction ratio helpers
# ---------------------------------------------------------------------------

def get_direction_ratio(active_picks: list[dict]) -> dict:
    """Count LONG/SHORT in active picks and return ratio.

    Returns:
        {"long": int, "short": int, "neutral": int, "total": int,
         "long_pct": float, "short_pct": float}
    """
    long_count = 0
    short_count = 0
    neutral_count = 0

    for pick in (active_picks or []):
        direction = str(
            pick.get("direction", pick.get("signal_type", ""))
        ).upper()
        if direction in ("LONG", "BUY"):
            long_count += 1
        elif direction in ("SHORT", "SELL"):
            short_count += 1
        else:
            neutral_count += 1

    total = long_count + short_count + neutral_count
    return {
        "long": long_count,
        "short": short_count,
        "neutral": neutral_count,
        "total": total,
        "long_pct": long_count / max(total, 1),
        "short_pct": short_count / max(total, 1),
    }


def _get_regime_label(fgi: int) -> str:
    """Classify FGI into regime label."""
    if fgi < 20:
        return "extreme_fear"
    if fgi < 40:
        return "fear"
    if fgi <= 60:
        return "neutral"
    if fgi <= 80:
        return "greed"
    return "extreme_greed"


def _get_direction_caps(fgi: int) -> dict:
    """Return max LONG% and max SHORT% for given FGI.

    Returns {"max_long_pct": float, "max_short_pct": float, "regime": str}
    """
    regime = _get_regime_label(fgi)
    if regime == "extreme_fear":
        return {"max_long_pct": 0.40, "max_short_pct": 1.0, "regime": regime}
    if regime == "fear":
        return {"max_long_pct": 0.50, "max_short_pct": 1.0, "regime": regime}
    if regime == "neutral":
        return {"max_long_pct": 1.0, "max_short_pct": 1.0, "regime": regime}
    if regime == "greed":
        return {"max_long_pct": 1.0, "max_short_pct": 0.50, "regime": regime}
    # extreme_greed
    return {"max_long_pct": 1.0, "max_short_pct": 0.40, "regime": regime}


# ---------------------------------------------------------------------------
# Position size reduction in fear
# ---------------------------------------------------------------------------

def halve_position_size_in_fear(pick: dict, fgi: int) -> dict:
    """When FGI < 20, multiply position size by 0.5 for LONG picks.

    Modifies pick in-place and returns it.
    """
    if fgi >= 20:
        return pick

    direction = str(
        pick.get("direction", pick.get("signal_type", ""))
    ).upper()
    if direction not in ("LONG", "BUY"):
        return pick

    # Halve allocation / position_size if present
    extra = pick.get("extra", {})
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except (json.JSONDecodeError, TypeError):
            extra = {}

    allocation = extra.get("allocation", 0)
    if allocation:
        extra["allocation"] = round(allocation * 0.5, 2)
        extra["fear_halved"] = True
        pick["extra"] = extra

    position_size = pick.get("position_size", 0)
    if position_size:
        pick["position_size"] = round(position_size * 0.5, 2)
        pick["fear_halved"] = True

    return pick


# ---------------------------------------------------------------------------
# Main guard: enforce direction balance
# ---------------------------------------------------------------------------

def enforce_direction_balance(
    candidate_picks: list[dict],
    active_picks: list[dict] | None = None,
    regime_data: dict | None = None,
) -> list[dict]:
    """Cap LONG/SHORT ratio based on market regime (Fear & Greed Index).

    1. Count current LONG/SHORT in active_picks
    2. For each candidate, check if adding it would exceed the cap
    3. If over cap, only allow picks in the underweighted direction
    4. Prioritize higher-confidence picks when filtering

    Args:
        candidate_picks: New signals to filter.
        active_picks: Currently open positions.
        regime_data: Optional dict with 'fgi' key. If absent, fetches live.

    Returns:
        Filtered list of candidate picks respecting direction caps.
    """
    if not candidate_picks:
        return []

    # Get FGI
    fgi = 50
    if regime_data and "fgi" in regime_data:
        fgi = int(regime_data["fgi"])
    else:
        fgi = get_fear_greed()

    caps = _get_direction_caps(fgi)
    regime = caps["regime"]
    max_long_pct = caps["max_long_pct"]
    max_short_pct = caps["max_short_pct"]

    # Neutral regime -- no caps needed
    if regime == "neutral":
        logger.info("[DIRECTION] Neutral regime (FGI=%d) -- no direction caps", fgi)
        return candidate_picks

    # Current portfolio direction counts
    ratio = get_direction_ratio(active_picks or [])
    current_long = ratio["long"]
    current_short = ratio["short"]
    current_total = ratio["total"]

    # Sort candidates by confidence descending (higher confidence first)
    sorted_candidates = sorted(
        candidate_picks,
        key=lambda p: float(p.get("confidence", 0)),
        reverse=True,
    )

    accepted = []
    capped = 0
    running_long = current_long
    running_short = current_short
    running_total = current_total

    for pick in sorted_candidates:
        direction = str(
            pick.get("direction", pick.get("signal_type", ""))
        ).upper()

        is_long = direction in ("LONG", "BUY")
        is_short = direction in ("SHORT", "SELL")

        # Project what the ratio would be after adding this pick
        projected_total = running_total + 1

        if is_long:
            projected_long_pct = (running_long + 1) / projected_total
            if projected_long_pct > max_long_pct:
                capped += 1
                pick["direction_capped"] = True
                pick["direction_cap_reason"] = (
                    f"FGI={fgi} ({regime}): LONG would be "
                    f"{projected_long_pct:.0%} > cap {max_long_pct:.0%}"
                )
                logger.info(
                    "[DIRECTION] CAPPED %s %s: %s",
                    pick.get("symbol", "?"),
                    pick.get("strategy", "?"),
                    pick["direction_cap_reason"],
                )
                continue
            running_long += 1

        elif is_short:
            projected_short_pct = (running_short + 1) / projected_total
            if projected_short_pct > max_short_pct:
                capped += 1
                pick["direction_capped"] = True
                pick["direction_cap_reason"] = (
                    f"FGI={fgi} ({regime}): SHORT would be "
                    f"{projected_short_pct:.0%} > cap {max_short_pct:.0%}"
                )
                logger.info(
                    "[DIRECTION] CAPPED %s %s: %s",
                    pick.get("symbol", "?"),
                    pick.get("strategy", "?"),
                    pick["direction_cap_reason"],
                )
                continue
            running_short += 1

        # Neutral direction -- always allowed
        running_total += 1

        # Apply position size halving in extreme fear for LONGs
        if fgi < 20 and is_long:
            pick = halve_position_size_in_fear(pick, fgi)

        accepted.append(pick)

    logger.info(
        "[DIRECTION] Balance guard: %d LONG, %d SHORT, regime=%s (FGI=%d), "
        "capped %d picks, accepted %d",
        running_long, running_short, regime, fgi, capped, len(accepted),
    )
    print(
        f"  [DIRECTION] Balance guard: {running_long} LONG, {running_short} SHORT, "
        f"regime={regime.upper()} (FGI={fgi}), capped {capped} picks"
    )

    return accepted
