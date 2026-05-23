"""
Binance API Failover Helper
============================
Lightweight helper for making Binance API calls with automatic
endpoint failover. Handles HTTP 451 geo-blocks from US-based
GitHub Actions runners.

Usage:
    from shared.binance_api import binance_get, binance_futures_get

    # Spot API — tries all endpoints in order
    data = binance_get("/api/v3/ticker/price", params={"symbol": "BTCUSDT"})

    # Futures API — tries all fapi endpoints in order
    data = binance_futures_get("/fapi/v1/premiumIndex")
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoint lists — ordered by reliability for CI environments
# ---------------------------------------------------------------------------

BINANCE_SPOT_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",   # Public data API (unrestricted)
    "https://api.binance.us",            # US-legal endpoint
]

BINANCE_FUTURES_ENDPOINTS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://testnet.binancefuture.com",  # Testnet fallback (limited data)
]

# In GitHub Actions, deprioritize api.binance.com (known 451)
_IN_GITHUB_ACTIONS = bool(os.environ.get("GITHUB_ACTIONS"))

if _IN_GITHUB_ACTIONS:
    # Move geo-blocked endpoints to the end
    BINANCE_SPOT_ENDPOINTS = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api.binance.com",
    ]
    BINANCE_FUTURES_ENDPOINTS = [
        "https://fapi1.binance.com",
        "https://fapi2.binance.com",
        "https://fapi.binance.com",
    ]

# Track which endpoints are known-bad (circuit breaker)
_blocked_endpoints: dict[str, float] = {}
_BLOCK_DURATION = 300  # 5 minutes


def _is_blocked(endpoint: str) -> bool:
    """Check if endpoint is temporarily blocked."""
    blocked_until = _blocked_endpoints.get(endpoint, 0)
    if time.time() > blocked_until:
        _blocked_endpoints.pop(endpoint, None)
        return False
    return True


def _block_endpoint(endpoint: str):
    """Temporarily block an endpoint after failure."""
    _blocked_endpoints[endpoint] = time.time() + _BLOCK_DURATION
    logger.debug(f"Blocked {endpoint} for {_BLOCK_DURATION}s")


def _make_request(
    base_url: str,
    path: str,
    params: Optional[dict] = None,
    timeout: int = 10,
) -> Optional[dict | list]:
    """Make a single HTTP GET request, return parsed JSON or None."""
    url = base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BinanceFailover/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (451, 403):
            _block_endpoint(base_url)
            logger.warning(f"Binance {base_url} returned HTTP {e.code} (geo-blocked)")
        elif e.code == 429:
            _block_endpoint(base_url)
            logger.warning(f"Binance {base_url} returned HTTP 429 (rate limited)")
        else:
            logger.debug(f"Binance {base_url} returned HTTP {e.code}")
        return None
    except Exception as e:
        logger.debug(f"Binance {base_url} request failed: {e}")
        return None


def binance_get(
    path: str,
    params: Optional[dict] = None,
    timeout: int = 10,
    endpoints: Optional[list[str]] = None,
) -> Optional[dict | list]:
    """
    Make a Binance spot API GET request with endpoint failover.

    Args:
        path: API path, e.g. "/api/v3/ticker/price"
        params: Query parameters dict
        timeout: Request timeout in seconds
        endpoints: Override endpoint list (default: BINANCE_SPOT_ENDPOINTS)

    Returns:
        Parsed JSON response, or None if all endpoints fail.
    """
    eps = endpoints or BINANCE_SPOT_ENDPOINTS
    for base in eps:
        if _is_blocked(base):
            continue
        result = _make_request(base, path, params, timeout)
        if result is not None:
            return result

    # All blocked — try them all anyway as last resort
    for base in eps:
        result = _make_request(base, path, params, timeout)
        if result is not None:
            return result

    return None


def binance_futures_get(
    path: str,
    params: Optional[dict] = None,
    timeout: int = 10,
    endpoints: Optional[list[str]] = None,
) -> Optional[dict | list]:
    """
    Make a Binance futures API GET request with endpoint failover.

    Args:
        path: API path, e.g. "/fapi/v1/premiumIndex"
        params: Query parameters dict
        timeout: Request timeout in seconds
        endpoints: Override endpoint list (default: BINANCE_FUTURES_ENDPOINTS)

    Returns:
        Parsed JSON response, or None if all endpoints fail.
    """
    eps = endpoints or BINANCE_FUTURES_ENDPOINTS
    for base in eps:
        if _is_blocked(base):
            continue
        result = _make_request(base, path, params, timeout)
        if result is not None:
            return result

    # All blocked — try them all anyway as last resort
    for base in eps:
        result = _make_request(base, path, params, timeout)
        if result is not None:
            return result

    return None


def get_binance_price(symbol: str) -> Optional[float]:
    """
    Convenience: get current spot price for a Binance symbol.

    Args:
        symbol: e.g. "BTCUSDT"

    Returns:
        Price as float, or None if all endpoints fail.
    """
    data = binance_get("/api/v3/ticker/price", params={"symbol": symbol})
    if data and "price" in data:
        try:
            return float(data["price"])
        except (ValueError, TypeError):
            pass
    return None


def get_binance_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
) -> Optional[list]:
    """
    Convenience: get klines/candlestick data with failover.

    Args:
        symbol: e.g. "BTCUSDT"
        interval: e.g. "1h", "4h", "1d"
        limit: Number of candles

    Returns:
        Raw Binance klines array, or None if all endpoints fail.
    """
    return binance_get(
        "/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": str(limit)},
    )


def get_funding_rate(symbol: str, limit: int = 1) -> Optional[list]:
    """
    Convenience: get funding rate history with failover.

    Args:
        symbol: e.g. "BTCUSDT"
        limit: Number of records

    Returns:
        Funding rate data array, or None if all endpoints fail.
    """
    return binance_futures_get(
        "/fapi/v1/fundingRate",
        params={"symbol": symbol, "limit": str(limit)},
    )


def get_premium_index() -> Optional[list]:
    """
    Convenience: get all premium index (funding rates) with failover.

    Returns:
        Premium index data array, or None if all endpoints fail.
    """
    return binance_futures_get("/fapi/v1/premiumIndex")


def get_open_interest(symbol: str) -> Optional[dict]:
    """
    Convenience: get open interest for a symbol with failover.

    Returns:
        OI data dict, or None if all endpoints fail.
    """
    return binance_futures_get(
        "/fapi/v1/openInterest",
        params={"symbol": symbol},
    )
