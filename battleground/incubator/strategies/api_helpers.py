#!/usr/bin/env python3
"""
Shared API helpers with geo-restriction fallbacks for Binance endpoints.
========================================================================

Problem: GitHub Actions runners are US-based, and api.binance.com returns
HTTP 451 (geo-blocked). This module provides fallback chains that try
unrestricted public endpoints first.

Usage:
    from api_helpers import fetch_klines, fetch_funding_rate, fetch_current_price
"""

from __future__ import annotations

import logging
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Klines Fallback Chain ─────────────────────────────────────────────
# data-api.binance.vision is the public data API (unrestricted, no geo-block)
BINANCE_KLINES_ENDPOINTS = [
    "https://data-api.binance.vision/api/v3/klines",  # Public data API (unrestricted)
    "https://api.binance.us/api/v3/klines",            # US exchange
    "https://api.binance.com/api/v3/klines",            # Main (geo-blocked in US)
]

# ── Futures Klines Fallback Chain ─────────────────────────────────────
FUTURES_KLINES_ENDPOINTS = [
    "https://fapi.binance.com/fapi/v1/klines",  # Main futures (may be blocked)
    "https://data-api.binance.vision/api/v3/klines",  # Fallback to spot data API
]

# ── Funding Rate Fallback Chain ───────────────────────────────────────
BINANCE_FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
OKX_FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate"

# ── Price Fallback Chain ──────────────────────────────────────────────
PRICE_ENDPOINTS = [
    ("binance_futures", "https://fapi.binance.com/fapi/v1/ticker/price"),
    ("binance_spot", "https://data-api.binance.vision/api/v3/ticker/price"),
    ("okx", "https://www.okx.com/api/v5/market/ticker"),
]


def _symbol_to_okx_inst_id(symbol: str) -> str:
    """Convert Binance symbol format to OKX instId format.
    BTCUSDT -> BTC-USDT-SWAP
    """
    # Common USDT pairs
    for base in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
                 "DOT", "LINK", "MATIC", "UNI", "SHIB", "LTC", "ATOM"]:
        if symbol.startswith(base) and symbol.endswith("USDT"):
            return f"{base}-USDT-SWAP"
    # Generic fallback: split before USDT
    if symbol.endswith("USDT"):
        base = symbol[:-4]
        return f"{base}-USDT-SWAP"
    return symbol


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = 200,
    timeout: int = 10,
) -> List[list]:
    """
    Fetch klines (OHLCV) with geo-restriction fallback chain.

    Tries endpoints in order:
    1. data-api.binance.vision (public, unrestricted)
    2. api.binance.us (US exchange)
    3. api.binance.com (main, geo-blocked in US)

    Returns list of kline arrays (Binance format) or empty list on failure.
    Each kline: [open_time, open, high, low, close, volume, ...]
    """
    if requests is None:
        logger.error("requests library not available")
        return []

    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for endpoint in BINANCE_KLINES_ENDPOINTS:
        try:
            resp = requests.get(endpoint, params=params, timeout=timeout)
            if resp.status_code == 451:
                logger.debug("Geo-blocked at %s, trying next endpoint", endpoint)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                logger.debug("Klines fetched from %s (%d candles)", endpoint, len(data))
                return data
        except requests.exceptions.RequestException as e:
            logger.debug("Klines endpoint %s failed: %s", endpoint, e)
            continue

    logger.error("All klines endpoints failed for %s", symbol)
    return []


def fetch_futures_klines(
    symbol: str,
    interval: str = "5m",
    limit: int = 30,
    timeout: int = 10,
) -> List[list]:
    """
    Fetch futures klines with fallback to spot data API.

    Returns list of kline arrays or empty list on failure.
    """
    if requests is None:
        logger.error("requests library not available")
        return []

    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for endpoint in FUTURES_KLINES_ENDPOINTS:
        try:
            resp = requests.get(endpoint, params=params, timeout=timeout)
            if resp.status_code == 451:
                logger.debug("Geo-blocked at %s, trying next endpoint", endpoint)
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                logger.debug("Futures klines fetched from %s (%d candles)", endpoint, len(data))
                return data
        except requests.exceptions.RequestException as e:
            logger.debug("Futures klines endpoint %s failed: %s", endpoint, e)
            continue

    logger.error("All futures klines endpoints failed for %s", symbol)
    return []


def fetch_funding_rate(
    symbol: str,
    limit: int = 30,
    timeout: int = 10,
) -> Optional[List[dict]]:
    """
    Fetch funding rate history with fallback chain.

    Tries:
    1. Binance fapi (may be geo-blocked)
    2. OKX public API

    Returns list of {"rate": float, "time": int} dicts sorted oldest->newest,
    or None on failure.
    """
    if requests is None:
        logger.error("requests library not available")
        return None

    # Try Binance fapi first
    try:
        resp = requests.get(
            BINANCE_FUNDING_URL,
            params={"symbol": symbol, "limit": limit},
            timeout=timeout,
        )
        if resp.status_code != 451:
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                logger.debug("Funding rates fetched from Binance fapi (%d periods)", len(data))
                return [
                    {
                        "rate": float(item["fundingRate"]),
                        "time": int(item["fundingTime"]),
                    }
                    for item in data
                ]
        else:
            logger.debug("Binance fapi geo-blocked (451), trying OKX")
    except requests.exceptions.RequestException as e:
        logger.debug("Binance funding rate failed: %s", e)

    # Fallback: OKX
    try:
        inst_id = _symbol_to_okx_inst_id(symbol)
        resp = requests.get(
            OKX_FUNDING_URL,
            params={"instId": inst_id},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == "0" and data.get("data"):
            okx_data = data["data"]
            result = []
            for item in okx_data:
                rate = float(item.get("fundingRate", 0))
                ts = int(item.get("fundingTime", 0))
                result.append({"rate": rate, "time": ts})
            if result:
                logger.debug("Funding rates fetched from OKX (%d periods)", len(result))
                return result
    except requests.exceptions.RequestException as e:
        logger.debug("OKX funding rate failed: %s", e)

    logger.error("All funding rate endpoints failed for %s", symbol)
    return None


def fetch_current_price(
    symbol: str,
    timeout: int = 10,
) -> Optional[float]:
    """
    Fetch current price with fallback chain.

    Tries:
    1. Binance futures ticker
    2. Binance spot data API (unrestricted)
    3. OKX market ticker

    Returns price as float, or None on failure.
    """
    if requests is None:
        logger.error("requests library not available")
        return None

    for source, base_url in PRICE_ENDPOINTS:
        try:
            if source == "okx":
                inst_id = _symbol_to_okx_inst_id(symbol)
                resp = requests.get(
                    base_url,
                    params={"instId": inst_id},
                    timeout=timeout,
                )
                if resp.status_code == 451:
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == "0" and data.get("data"):
                    price = float(data["data"][0]["last"])
                    logger.debug("Price fetched from OKX: %.2f", price)
                    return price
            else:
                resp = requests.get(
                    base_url,
                    params={"symbol": symbol},
                    timeout=timeout,
                )
                if resp.status_code == 451:
                    logger.debug("Geo-blocked at %s, trying next", source)
                    continue
                resp.raise_for_status()
                data = resp.json()
                price = float(data["price"])
                logger.debug("Price fetched from %s: %.2f", source, price)
                return price
        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError) as e:
            logger.debug("Price fetch from %s failed: %s", source, e)
            continue

    logger.error("All price endpoints failed for %s", symbol)
    return None


def fetch_funding_rate_single(
    symbol: str,
    timeout: int = 10,
) -> Optional[float]:
    """
    Fetch the latest single funding rate value.

    Uses fetch_funding_rate() and returns just the most recent rate,
    or None on failure.
    """
    data = fetch_funding_rate(symbol, limit=1, timeout=timeout)
    if data and len(data) > 0:
        return data[-1]["rate"]
    return None
