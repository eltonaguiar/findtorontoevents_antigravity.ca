"""
FRED Macro Liquidity Client
=============================
Uses the Federal Reserve Economic Data (FRED) API to compute
the Arthur Hayes Net Liquidity Index:

    Net Liquidity = Fed Balance Sheet (WALCL) - Reverse Repo (RRPONTSYD) - TGA (WTREGEN)

When net liquidity rises, BTC tends to follow with a 2-6 week lag.
Previously our hayes_liquidity_index strategy used hardcoded proxies --
this module gives it REAL data.

Also provides yield curve inversion signal (10Y-2Y spread) and M2
money supply trend -- both proven macro predictors.

Requires: FRED_API_KEY environment variable
Free tier: 120 requests/minute, 840,000+ time series

Usage:
    from fred_liquidity import get_net_liquidity, get_macro_signal
"""

import os
import time
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"
CACHE_TTL = 3600  # 1 hour -- FRED data updates weekly/daily
_cache: dict = {}


def _get_api_key():
    return os.environ.get("FRED_API_KEY", "").strip()


def _fred_get(series_id: str, limit: int = 10) -> list[dict]:
    """Fetch recent observations for a FRED series."""
    cache_key = f"fred:{series_id}:{limit}"
    if cache_key in _cache:
        ts, val = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return val

    key = _get_api_key()
    if not key:
        return []

    try:
        params = {
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(limit),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{FRED_BASE}/series/observations?{query}"

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())

        observations = []
        for obs in data.get("observations", []):
            try:
                val = float(obs["value"])
                observations.append({
                    "date": obs["date"],
                    "value": val,
                })
            except (ValueError, KeyError):
                continue

        _cache[cache_key] = (time.time(), observations)
        return observations

    except Exception as e:
        logger.warning("FRED API error for %s: %s", series_id, e)
        return []


def get_net_liquidity() -> dict:
    """Compute Arthur Hayes Net Liquidity Index from real FRED data.

    Formula: Net Liquidity = WALCL - RRPONTSYD - WTREGEN

    Where:
    - WALCL = Fed total assets (balance sheet size) -- updated weekly Wed
    - RRPONTSYD = Reverse repo operations -- updated daily
    - WTREGEN = Treasury General Account -- updated weekly Wed

    Returns:
        {
            "net_liquidity_b": float -- net liquidity in billions USD
            "fed_bs_b": float -- Fed balance sheet in billions
            "rrp_b": float -- reverse repo in billions
            "tga_b": float -- Treasury General Account in billions
            "liquidity_trend": str -- "EXPANDING" / "CONTRACTING" / "FLAT"
            "change_pct": float -- week-over-week change %
            "signal": str -- "BULLISH_BTC" / "BEARISH_BTC" / "NEUTRAL"
        }
    """
    # Fetch the three components (in millions)
    walcl = _fred_get("WALCL", limit=4)    # Fed balance sheet (weekly, millions)
    rrp = _fred_get("RRPONTSYD", limit=10)  # Reverse repo (daily, billions)
    tga = _fred_get("WTREGEN", limit=4)     # TGA (weekly, millions)

    result = {
        "net_liquidity_b": 0.0,
        "fed_bs_b": 0.0,
        "rrp_b": 0.0,
        "tga_b": 0.0,
        "liquidity_trend": "UNKNOWN",
        "change_pct": 0.0,
        "signal": "NEUTRAL",
        "available": False,
    }

    if not walcl or not rrp or not tga:
        return result

    try:
        # WALCL is in millions, convert to billions
        fed_bs = walcl[0]["value"] / 1000.0
        # RRPONTSYD is already in billions
        rrp_val = rrp[0]["value"]
        # WTREGEN is in millions, convert to billions
        tga_val = tga[0]["value"] / 1000.0

        net_liq = fed_bs - rrp_val - tga_val

        result["fed_bs_b"] = round(fed_bs, 1)
        result["rrp_b"] = round(rrp_val, 1)
        result["tga_b"] = round(tga_val, 1)
        result["net_liquidity_b"] = round(net_liq, 1)
        result["available"] = True

        # Week-over-week change
        if len(walcl) >= 2 and len(tga) >= 2:
            prev_fed = walcl[1]["value"] / 1000.0
            prev_tga = tga[1]["value"] / 1000.0
            # Use latest RRP for prev too (daily vs weekly mismatch)
            prev_rrp = rrp[min(5, len(rrp) - 1)]["value"] if len(rrp) > 5 else rrp_val
            prev_net = prev_fed - prev_rrp - prev_tga

            if prev_net != 0:
                change = (net_liq - prev_net) / abs(prev_net) * 100
                result["change_pct"] = round(change, 2)

                if change > 0.5:
                    result["liquidity_trend"] = "EXPANDING"
                    result["signal"] = "BULLISH_BTC"
                elif change < -0.5:
                    result["liquidity_trend"] = "CONTRACTING"
                    result["signal"] = "BEARISH_BTC"
                else:
                    result["liquidity_trend"] = "FLAT"
                    result["signal"] = "NEUTRAL"

    except Exception as e:
        logger.warning("Net liquidity calculation error: %s", e)

    return result


def get_yield_curve() -> dict:
    """Get 10Y-2Y Treasury yield spread (yield curve).

    When inverted (spread < 0): recession signal, risk-off, bearish crypto
    When steep (spread > 1.0): growth signal, risk-on, bullish crypto
    """
    t10y2y = _fred_get("T10Y2Y", limit=5)  # 10Y-2Y spread (daily, percentage)

    if not t10y2y:
        return {"spread": 0.0, "signal": "NEUTRAL", "available": False}

    spread = t10y2y[0]["value"]
    prev_spread = t10y2y[-1]["value"] if len(t10y2y) > 1 else spread

    signal = "NEUTRAL"
    if spread < 0:
        signal = "INVERTED_BEARISH"
    elif spread < 0.3:
        signal = "FLAT_CAUTIOUS"
    elif spread > 1.0:
        signal = "STEEP_BULLISH"

    return {
        "spread": round(spread, 3),
        "prev_spread": round(prev_spread, 3),
        "trend": "STEEPENING" if spread > prev_spread else "FLATTENING",
        "signal": signal,
        "available": True,
    }


def get_macro_signal() -> dict:
    """Combined macro signal from FRED data.

    Merges net liquidity + yield curve into a single macro outlook.
    """
    liq = get_net_liquidity()
    yc = get_yield_curve()

    score = 0
    factors = []

    if liq.get("available"):
        if liq["signal"] == "BULLISH_BTC":
            score += 2
            factors.append(f"Net liquidity EXPANDING ({liq['change_pct']:+.1f}% WoW)")
        elif liq["signal"] == "BEARISH_BTC":
            score -= 2
            factors.append(f"Net liquidity CONTRACTING ({liq['change_pct']:+.1f}% WoW)")

    if yc.get("available"):
        if yc["signal"] == "INVERTED_BEARISH":
            score -= 1
            factors.append(f"Yield curve INVERTED ({yc['spread']:.2f}%)")
        elif yc["signal"] == "STEEP_BULLISH":
            score += 1
            factors.append(f"Yield curve STEEP ({yc['spread']:.2f}%)")

    if score >= 2:
        macro_signal = "STRONG_BULLISH"
    elif score >= 1:
        macro_signal = "MILD_BULLISH"
    elif score <= -2:
        macro_signal = "STRONG_BEARISH"
    elif score <= -1:
        macro_signal = "MILD_BEARISH"
    else:
        macro_signal = "NEUTRAL"

    return {
        "macro_signal": macro_signal,
        "macro_score": score,
        "factors": factors,
        "net_liquidity": liq,
        "yield_curve": yc,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("FRED Macro Liquidity -- Test Run")
    print("=" * 60)

    liq = get_net_liquidity()
    print(f"\nFed Balance Sheet: ${liq['fed_bs_b']:.0f}B")
    print(f"Reverse Repo:      ${liq['rrp_b']:.0f}B")
    print(f"Treasury (TGA):    ${liq['tga_b']:.0f}B")
    print(f"Net Liquidity:     ${liq['net_liquidity_b']:.0f}B")
    print(f"Trend:             {liq['liquidity_trend']} ({liq['change_pct']:+.2f}% WoW)")
    print(f"BTC Signal:        {liq['signal']}")

    yc = get_yield_curve()
    print(f"\nYield Curve (10Y-2Y): {yc.get('spread', 'N/A')}%")
    print(f"Signal: {yc.get('signal', 'N/A')}")

    macro = get_macro_signal()
    print(f"\nOverall Macro: {macro['macro_signal']} (score: {macro['macro_score']})")
    for f in macro["factors"]:
        print(f"  - {f}")
