"""
Coinalyze / Binance Derivatives Client
=======================================
Free open interest, funding rate, and long/short ratio data.
Primary source: Binance Futures public API (no key required).

Usage:
    from alpha_engine.coinalyze_client import get_derivatives_snapshot
    snap = get_derivatives_snapshot("BTCUSDT")
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BINANCE_FAPI = "https://fapi.binance.com"
REQUEST_TIMEOUT = 5  # seconds
CACHE_TTL = 300  # 5 minutes
_MIN_REQUEST_INTERVAL = 0.1  # 10 req/s max

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_cache: dict = {}  # key -> (timestamp, value)
_last_request_ts: float = 0.0


def _rate_limit():
    """Enforce max 10 requests/second."""
    global _last_request_ts
    now = time.time()
    elapsed = now - _last_request_ts
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_ts = time.time()


def _get_cached(key: str):
    """Return cached value if still fresh, else None."""
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _set_cached(key: str, val):
    _cache[key] = (time.time(), val)


def _binance_get(path: str, params: dict | None = None) -> dict | list | None:
    """GET from Binance Futures API with rate limiting and error handling."""
    _rate_limit()
    url = f"{BINANCE_FAPI}{path}"
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Binance API error %s: %s", path, e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_open_interest(symbol: str) -> dict:
    """
    Return current open interest and 24h change for a symbol.

    Returns:
        {
            "oi": float,          # current OI in contracts
            "oi_usd": float,      # approximate OI in USD (if available)
            "oi_change_24h": float # percent change over ~24h
        }
    """
    symbol = symbol.upper()
    cache_key = f"oi:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    result = {"oi": 0.0, "oi_usd": 0.0, "oi_change_24h": 0.0}

    # Current OI
    data = _binance_get("/fapi/v1/openInterest", {"symbol": symbol})
    if data and "openInterest" in data:
        result["oi"] = float(data["openInterest"])

    # Historical OI for 24h change (1h candles, 25 periods ~ 25h)
    hist = _binance_get(
        "/futures/data/openInterestHist",
        {"symbol": symbol, "period": "1h", "limit": 25},
    )
    if hist and isinstance(hist, list) and len(hist) >= 2:
        try:
            current_oi_usd = float(hist[-1].get("sumOpenInterestValue", 0))
            old_oi_usd = float(hist[0].get("sumOpenInterestValue", 0))
            result["oi_usd"] = current_oi_usd
            if old_oi_usd > 0:
                result["oi_change_24h"] = round(
                    (current_oi_usd - old_oi_usd) / old_oi_usd * 100, 2
                )
        except (ValueError, TypeError):
            pass

    _set_cached(cache_key, result)
    return result


def get_funding_rate(symbol: str) -> dict:
    """
    Return the most recent funding rate.

    Returns:
        {
            "funding_rate": float,   # e.g. 0.0001 = 0.01%
            "funding_time": int,     # unix ms timestamp
        }
    """
    symbol = symbol.upper()
    cache_key = f"fr:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    result = {"funding_rate": 0.0, "funding_time": 0}

    data = _binance_get("/fapi/v1/fundingRate", {"symbol": symbol, "limit": 1})
    if data and isinstance(data, list) and len(data) > 0:
        try:
            result["funding_rate"] = float(data[0].get("fundingRate", 0))
            result["funding_time"] = int(data[0].get("fundingTime", 0))
        except (ValueError, TypeError):
            pass

    _set_cached(cache_key, result)
    return result


def get_long_short_ratio(symbol: str) -> dict:
    """
    Return the global long/short account ratio.

    Returns:
        {
            "long_short_ratio": float,  # >1 means more long accounts
            "long_account": float,      # fraction (0-1)
            "short_account": float,     # fraction (0-1)
        }
    """
    symbol = symbol.upper()
    cache_key = f"lsr:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    result = {"long_short_ratio": 1.0, "long_account": 0.5, "short_account": 0.5}

    data = _binance_get(
        "/futures/data/globalLongShortAccountRatio",
        {"symbol": symbol, "period": "1h", "limit": 1},
    )
    if data and isinstance(data, list) and len(data) > 0:
        try:
            result["long_short_ratio"] = float(data[0].get("longShortRatio", 1.0))
            result["long_account"] = float(data[0].get("longAccount", 0.5))
            result["short_account"] = float(data[0].get("shortAccount", 0.5))
        except (ValueError, TypeError):
            pass

    _set_cached(cache_key, result)
    return result


def _interpret_signal(oi_change_24h: float, funding_rate: float, ls_ratio: float) -> str:
    """
    Simple heuristic to interpret derivatives data.

    BULLISH: rising OI + positive funding + more longs (momentum continuation)
    BEARISH: rising OI + negative funding + more shorts
    Nuance: extreme funding can signal contrarian reversal, but we keep it simple.
    """
    score = 0

    # OI change component
    if oi_change_24h > 5:
        score += 1  # strong inflow
    elif oi_change_24h < -5:
        score -= 1  # deleveraging

    # Funding rate component
    if funding_rate > 0.0005:
        score += 1  # heavily long
    elif funding_rate < -0.0005:
        score -= 1  # heavily short
    # Extreme funding is contrarian
    if funding_rate > 0.001:
        score -= 1  # overleveraged longs, risk of squeeze
    elif funding_rate < -0.001:
        score += 1  # overleveraged shorts, risk of squeeze

    # Long/short ratio component
    if ls_ratio > 1.5:
        score += 1
    elif ls_ratio < 0.67:
        score -= 1

    if score >= 2:
        return "BULLISH"
    elif score <= -2:
        return "BEARISH"
    return "NEUTRAL"


def get_derivatives_snapshot(symbol: str) -> dict:
    """
    Combined derivatives snapshot for a symbol.

    Returns:
        {
            "oi": float,              # current OI in USD
            "oi_change_24h": float,   # percent change
            "funding_rate": float,    # current funding rate
            "long_short_ratio": float,# >1 = more longs
            "signal": str,            # "BULLISH" / "BEARISH" / "NEUTRAL"
        }
    """
    oi_data = get_open_interest(symbol)
    fr_data = get_funding_rate(symbol)
    ls_data = get_long_short_ratio(symbol)

    oi_usd = oi_data["oi_usd"] if oi_data["oi_usd"] > 0 else oi_data["oi"]
    funding = fr_data["funding_rate"]
    ls_ratio = ls_data["long_short_ratio"]
    oi_change = oi_data["oi_change_24h"]

    return {
        "oi": oi_usd,
        "oi_change_24h": oi_change,
        "funding_rate": funding,
        "long_short_ratio": ls_ratio,
        "signal": _interpret_signal(oi_change, funding, ls_ratio),
    }


def get_derivatives_batch(symbols: list[str]) -> dict[str, dict]:
    """
    Batch derivatives snapshot for multiple symbols.

    Returns dict mapping symbol -> snapshot.
    """
    results = {}
    for sym in symbols:
        try:
            results[sym.upper()] = get_derivatives_snapshot(sym)
        except Exception as e:
            logger.warning("Failed to get derivatives for %s: %s", sym, e)
            results[sym.upper()] = {
                "oi": 0.0,
                "oi_change_24h": 0.0,
                "funding_rate": 0.0,
                "long_short_ratio": 1.0,
                "signal": "NEUTRAL",
            }
    return results


# ---------------------------------------------------------------------------
# Coinalyze Aggregated API (cross-exchange: Binance+OKX+Bybit+dYdX)
# Requires COINALYZE_API_KEY environment variable
# ---------------------------------------------------------------------------
COINALYZE_BASE = "https://api.coinalyze.net/v1"

def _get_coinalyze_key():
    """Get Coinalyze API key from environment."""
    import os
    return os.environ.get("COINALYZE_API_KEY", "")


def _coinalyze_get(path: str, params: dict | None = None) -> dict | list | None:
    """GET from Coinalyze API with rate limiting."""
    api_key = _get_coinalyze_key()
    if not api_key:
        return None
    _rate_limit()
    url = f"{COINALYZE_BASE}{path}"
    if params is None:
        params = {}
    params["api_key"] = api_key
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Coinalyze API error %s: %s", path, e)
        return None


# Coinalyze symbol mapping (their format uses _PERP.A for aggregated)
_COINALYZE_SYMBOLS = {
    "BTCUSDT": "BTCUSD_PERP.A",
    "ETHUSDT": "ETHUSD_PERP.A",
    "SOLUSDT": "SOLUSD_PERP.A",
    "XRPUSDT": "XRPUSD_PERP.A",
    "DOTUSDT": "DOTUSD_PERP.A",
    "LINKUSDT": "LINKUSD_PERP.A",
    "ADAUSDT": "ADAUSD_PERP.A",
    "NEARUSDT": "NEARUSD_PERP.A",
    "TRXUSDT": "TRXUSD_PERP.A",
    "INJUSDT": "INJUSD_PERP.A",
    "AVAXUSDT": "AVAXUSD_PERP.A",
    "DOGEUSDT": "DOGEUSD_PERP.A",
}


def get_aggregated_oi(symbol: str) -> dict:
    """Get AGGREGATED open interest across all exchanges for a symbol.

    This is strictly better than single-exchange (Binance) data because
    it includes OKX, Bybit, dYdX, and others in one number.
    """
    cache_key = f"cz_oi:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    cz_sym = _COINALYZE_SYMBOLS.get(symbol.upper())
    if not cz_sym:
        return {"aggregated_oi": 0.0, "source": "coinalyze", "available": False}

    data = _coinalyze_get("/open-interest", {"symbols": cz_sym})
    result = {"aggregated_oi": 0.0, "source": "coinalyze", "available": False}

    if data and isinstance(data, list) and len(data) > 0:
        try:
            result["aggregated_oi"] = float(data[0].get("value", 0))
            result["available"] = True
        except (ValueError, TypeError):
            pass

    _set_cached(cache_key, result)
    return result


def get_aggregated_funding(symbol: str) -> dict:
    """Get aggregated predicted funding rate across exchanges."""
    cache_key = f"cz_fr:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    cz_sym = _COINALYZE_SYMBOLS.get(symbol.upper())
    if not cz_sym:
        return {"predicted_funding": 0.0, "source": "coinalyze", "available": False}

    data = _coinalyze_get("/predicted-funding-rate", {"symbols": cz_sym})
    result = {"predicted_funding": 0.0, "source": "coinalyze", "available": False}

    if data and isinstance(data, list) and len(data) > 0:
        try:
            result["predicted_funding"] = float(data[0].get("value", 0))
            result["available"] = True
        except (ValueError, TypeError):
            pass

    _set_cached(cache_key, result)
    return result


def get_aggregated_liquidations(symbol: str) -> dict:
    """Get recent aggregated liquidation data."""
    cache_key = f"cz_liq:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    cz_sym = _COINALYZE_SYMBOLS.get(symbol.upper())
    if not cz_sym:
        return {"long_liquidations": 0.0, "short_liquidations": 0.0, "source": "coinalyze", "available": False}

    data = _coinalyze_get("/liquidation-history", {"symbols": cz_sym, "interval": "1hour", "limit": 1})
    result = {"long_liquidations": 0.0, "short_liquidations": 0.0, "source": "coinalyze", "available": False}

    if data and isinstance(data, list) and len(data) > 0:
        try:
            entry = data[0].get("history", [{}])
            if entry and isinstance(entry, list) and len(entry) > 0:
                result["long_liquidations"] = float(entry[-1].get("l", 0))
                result["short_liquidations"] = float(entry[-1].get("s", 0))
                result["available"] = True
        except (ValueError, TypeError, IndexError):
            pass

    _set_cached(cache_key, result)
    return result


def get_aggregated_snapshot(symbol: str) -> dict:
    """Combined Coinalyze aggregated snapshot -- OI + funding + liquidations.

    Falls back to Binance-only data if Coinalyze key is not available.
    """
    agg_oi = get_aggregated_oi(symbol)
    agg_fr = get_aggregated_funding(symbol)
    agg_liq = get_aggregated_liquidations(symbol)

    if not agg_oi.get("available"):
        # Fallback to Binance-only
        return get_derivatives_snapshot(symbol)

    # Merge with Binance data for long/short ratio (Coinalyze may not have it free)
    ls_data = get_long_short_ratio(symbol)
    oi_data = get_open_interest(symbol)

    return {
        "oi": agg_oi.get("aggregated_oi", 0.0),
        "oi_change_24h": oi_data.get("oi_change_24h", 0.0),
        "funding_rate": agg_fr.get("predicted_funding", 0.0) if agg_fr.get("available") else get_funding_rate(symbol).get("funding_rate", 0.0),
        "long_short_ratio": ls_data.get("long_short_ratio", 1.0),
        "long_liquidations": agg_liq.get("long_liquidations", 0.0),
        "short_liquidations": agg_liq.get("short_liquidations", 0.0),
        "signal": _interpret_signal(oi_data.get("oi_change_24h", 0.0),
                                     agg_fr.get("predicted_funding", 0.0) if agg_fr.get("available") else get_funding_rate(symbol).get("funding_rate", 0.0),
                                     ls_data.get("long_short_ratio", 1.0)),
        "source": "coinalyze_aggregated",
    }


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    print("=" * 60)
    print("Coinalyze / Binance Derivatives Client -- Test Run")
    print("=" * 60)

    for sym in test_symbols:
        print(f"\n--- {sym} ---")
        snap = get_derivatives_snapshot(sym)
        oi_display = snap["oi"]
        if oi_display > 1_000_000_000:
            oi_str = f"${oi_display / 1e9:.2f}B"
        elif oi_display > 1_000_000:
            oi_str = f"${oi_display / 1e6:.1f}M"
        else:
            oi_str = f"${oi_display:,.0f}"

        print(f"  Open Interest:    {oi_str}")
        print(f"  OI Change (24h):  {snap['oi_change_24h']:+.2f}%")
        print(f"  Funding Rate:     {snap['funding_rate']:.6f} ({snap['funding_rate']*100:.4f}%)")
        print(f"  L/S Ratio:        {snap['long_short_ratio']:.3f}")
        print(f"  Signal:           {snap['signal']}")

    # Test caching -- second call should be instant
    print("\n--- Cache test (BTCUSDT again, should be instant) ---")
    t0 = time.time()
    snap2 = get_derivatives_snapshot("BTCUSDT")
    elapsed = time.time() - t0
    print(f"  Cached call took {elapsed*1000:.1f}ms (expected <10ms)")

    print("\n--- Batch test ---")
    batch = get_derivatives_batch(["BTCUSDT", "ETHUSDT"])
    for sym, data in batch.items():
        print(f"  {sym}: OI={data['oi']:.0f}, signal={data['signal']}")

    print("\nDone.")
