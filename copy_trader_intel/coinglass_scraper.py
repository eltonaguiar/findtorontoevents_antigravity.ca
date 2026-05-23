#!/usr/bin/env python3
"""
CoinGlass Top Trader Sentiment & Positioning Scraper
=====================================================
Scrapes CoinGlass aggregated futures data for top trader positioning signals
and converts them into active_picks.json compatible format.

CoinGlass aggregates data across exchanges (Binance, OKX, Bybit, Bitget, etc.):
  - Top trader long/short ratios (account + position weighted)
  - Global long/short account ratios
  - Open interest data (OI changes signal institutional moves)
  - Funding rates (extreme funding = reversal signal)
  - Liquidation data (cascade bottoms = entry signals)

=== CoinGlass API v3 (requires COINGLASS_API_KEY) ===
  Header: CG-API-KEY: <key>
  Free tier: 30 req/min

  Endpoints used:
    GET /api/futures/globalLongShortAccountRatio
        params: symbol, interval (h1/h4/1d), limit
        returns: [{longAccount, shortAccount, longShortRatio, buyRatio, sellRatio, timestamp}]

    GET /api/futures/topLongShortAccountRatio
        params: symbol, interval, limit
        returns: [{longAccount, shortAccount, longShortRatio, timestamp}]

    GET /api/futures/topLongShortPositionRatio
        params: symbol, interval, limit
        returns: [{longAccount, shortAccount, longShortRatio, timestamp}]

    GET /api/futures/openInterest/ohlc-history
        params: symbol, interval (1h/4h/1d), limit
        returns: [{o, h, l, c, timestamp}]

    GET /api/futures/fundingRate/ohlc-history
        params: symbol, interval, limit

    GET /api/futures/liquidation/detail
        params: symbol, interval, limit

=== CoinGlass API v2 (requires coinglassSecret header) ===
  Header: coinglassSecret: <key>

    GET /public/v2/long_short
    GET /public/v2/open_interest
    GET /public/v2/funding
    GET /public/v2/indicator/top_long_short_position_ratio
    GET /public/v2/indicator/top_long_short_account_ratio

=== Exchange Direct Fallback (no API key needed) ===
  Binance Futures: /futures/data/topLongShortAccountRatio, topLongShortPositionRatio
  OKX Rubik:       /api/v5/rubik/stat/contracts/long-short-account-ratio-contract-top-trader
  Bybit:           /v5/market/account-ratio

API Failover: CoinGlass v3 -> CoinGlass v2 -> Binance Futures -> OKX -> Bybit
Rate limit: 0.5s between calls per source.
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- Constants --
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

COINGLASS_V3 = "https://open-api-v3.coinglass.com"
COINGLASS_V2 = "https://open-api.coinglass.com"

# Exchange direct API mirrors (failover chain per project rules)
BINANCE_FAPI_MIRRORS = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
OKX_API = "https://www.okx.com"
BYBIT_API = "https://api.bybit.com"

# CoinGecko for price lookups (failover)
COINGECKO_API = "https://api.coingecko.com"
BINANCE_SPOT = "https://api.binance.com"

RATE_LIMIT_SEC = 0.5
REQUEST_TIMEOUT = 12

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# Symbols to scan -- top futures coins by volume
SYMBOLS = [
    "BTC", "ETH", "SOL", "DOGE", "XRP",
    "BNB", "ADA", "AVAX", "LINK", "DOT",
    "LTC", "SUI", "PEPE", "ARB", "OP",
    "APT", "NEAR", "FIL", "ATOM", "MATIC",
]

# CoinGecko ID map for price lookups
CG_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "DOGE": "dogecoin", "XRP": "ripple", "BNB": "binancecoin",
    "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink",
    "DOT": "polkadot", "LTC": "litecoin", "SUI": "sui",
    "PEPE": "pepe", "ARB": "arbitrum", "OP": "optimism",
    "APT": "aptos", "NEAR": "near", "FIL": "filecoin",
    "ATOM": "cosmos", "MATIC": "matic-network",
}

# -- Source health tracking --
_source_failures: Dict[str, int] = {}
_source_disabled: Dict[str, bool] = {}
_FAILURE_THRESHOLD = 3


def _record_failure(source: str) -> None:
    _source_failures[source] = _source_failures.get(source, 0) + 1
    if _source_failures[source] >= _FAILURE_THRESHOLD:
        _source_disabled[source] = True
        print(f"    [WARN] Source '{source}' disabled after {_source_failures[source]} failures")


def _record_success(source: str) -> None:
    _source_failures[source] = 0


def _is_disabled(source: str) -> bool:
    return _source_disabled.get(source, False)


# ======================================================================
# API Key Loading
# ======================================================================

def _get_coinglass_key() -> str:
    """Load CoinGlass API key from env or Windows User-level env."""
    key = os.environ.get("COINGLASS_API_KEY", "")
    if not key and sys.platform == "win32":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[Environment]::GetEnvironmentVariable('COINGLASS_API_KEY', 'User')"],
                capture_output=True, text=True, timeout=5
            )
            key = result.stdout.strip()
        except Exception:
            pass
    return key


# ======================================================================
# HTTP Helpers
# ======================================================================

def _http_get(url: str, params: dict = None, headers: dict = None,
              source: str = None, timeout: int = REQUEST_TIMEOUT) -> Optional[dict]:
    """GET with single retry. No retry on 4xx."""
    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, headers=headers or HEADERS,
                                timeout=timeout)
            if 400 <= resp.status_code < 500:
                if source:
                    _record_failure(source)
                return None
            resp.raise_for_status()
            data = resp.json()
            if source:
                _record_success(source)
            return data
        except requests.exceptions.HTTPError:
            if source:
                _record_failure(source)
            return None
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
            else:
                if source:
                    _record_failure(source)
    return None


def _safe_float(val, default=None):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


# ======================================================================
# CoinGlass v3 API (primary -- requires API key)
# ======================================================================

def _cg_v3_headers() -> dict:
    key = _get_coinglass_key()
    return {**HEADERS, "CG-API-KEY": key}


def fetch_cg_v3_global_ls(symbol: str, interval: str = "h1") -> Optional[Dict]:
    """Fetch global long/short account ratio from CoinGlass v3."""
    if _is_disabled("cg_v3") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V3}/api/futures/globalLongShortAccountRatio"
    data = _http_get(url, params={"symbol": symbol, "interval": interval, "limit": 1},
                     headers=_cg_v3_headers(), source="cg_v3")
    if data and data.get("success") and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            return items[-1]
    return None


def fetch_cg_v3_top_ls_account(symbol: str, interval: str = "h1") -> Optional[Dict]:
    """Fetch top trader long/short account ratio from CoinGlass v3."""
    if _is_disabled("cg_v3") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V3}/api/futures/topLongShortAccountRatio"
    data = _http_get(url, params={"symbol": symbol, "interval": interval, "limit": 1},
                     headers=_cg_v3_headers(), source="cg_v3")
    if data and data.get("success") and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            return items[-1]
    return None


def fetch_cg_v3_top_ls_position(symbol: str, interval: str = "h1") -> Optional[Dict]:
    """Fetch top trader long/short position ratio from CoinGlass v3."""
    if _is_disabled("cg_v3") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V3}/api/futures/topLongShortPositionRatio"
    data = _http_get(url, params={"symbol": symbol, "interval": interval, "limit": 1},
                     headers=_cg_v3_headers(), source="cg_v3")
    if data and data.get("success") and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            return items[-1]
    return None


def fetch_cg_v3_oi(symbol: str, interval: str = "1h") -> Optional[Dict]:
    """Fetch open interest OHLC from CoinGlass v3."""
    if _is_disabled("cg_v3") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V3}/api/futures/openInterest/ohlc-history"
    data = _http_get(url, params={"symbol": symbol, "interval": interval, "limit": 2},
                     headers=_cg_v3_headers(), source="cg_v3")
    if data and data.get("success") and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and len(items) >= 2:
            return {"current": items[-1], "previous": items[-2]}
    return None


def fetch_cg_v3_funding(symbol: str) -> Optional[float]:
    """Fetch latest funding rate from CoinGlass v3."""
    if _is_disabled("cg_v3") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V3}/api/futures/fundingRate/ohlc-history"
    data = _http_get(url, params={"symbol": symbol, "interval": "1h", "limit": 1},
                     headers=_cg_v3_headers(), source="cg_v3")
    if data and data.get("success") and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            return _safe_float(items[-1].get("c", items[-1].get("close")))
    return None


# ======================================================================
# CoinGlass v2 API (fallback 1 -- requires coinglassSecret header)
# ======================================================================

def _cg_v2_headers() -> dict:
    key = _get_coinglass_key()
    return {**HEADERS, "coinglassSecret": key}


def fetch_cg_v2_long_short(symbol: str) -> Optional[Dict]:
    """Fetch long/short data from CoinGlass v2."""
    if _is_disabled("cg_v2") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V2}/public/v2/long_short"
    data = _http_get(url, params={"symbol": symbol, "timeType": 2},
                     headers=_cg_v2_headers(), source="cg_v2")
    if data and data.get("code") == "0" and data.get("data"):
        return data["data"]
    return None


def fetch_cg_v2_top_ls_position(symbol: str) -> Optional[Dict]:
    """Fetch top trader position ratio from CoinGlass v2."""
    if _is_disabled("cg_v2") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V2}/public/v2/indicator/top_long_short_position_ratio"
    data = _http_get(url, params={"symbol": symbol, "timeType": 2},
                     headers=_cg_v2_headers(), source="cg_v2")
    if data and data.get("code") == "0" and data.get("data"):
        return data["data"]
    return None


def fetch_cg_v2_oi(symbol: str) -> Optional[Dict]:
    """Fetch open interest from CoinGlass v2."""
    if _is_disabled("cg_v2") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V2}/public/v2/open_interest"
    data = _http_get(url, params={"symbol": symbol, "timeType": 2},
                     headers=_cg_v2_headers(), source="cg_v2")
    if data and data.get("code") == "0" and data.get("data"):
        return data["data"]
    return None


def fetch_cg_v2_funding(symbol: str) -> Optional[float]:
    """Fetch funding rate from CoinGlass v2."""
    if _is_disabled("cg_v2") or not _get_coinglass_key():
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{COINGLASS_V2}/public/v2/funding"
    data = _http_get(url, params={"symbol": symbol},
                     headers=_cg_v2_headers(), source="cg_v2")
    if data and data.get("code") == "0" and data.get("data"):
        items = data["data"]
        if isinstance(items, list) and items:
            return _safe_float(items[0].get("rate"))
    return None


# ======================================================================
# Exchange Direct APIs (fallback 2 -- no API key needed)
# ======================================================================

def fetch_binance_top_ls(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch top trader L/S ratios directly from Binance Futures."""
    result = {"top_account": None, "top_position": None, "global": None, "taker": None}
    if _is_disabled("binance"):
        return result

    sym = f"{symbol}USDT"
    endpoints = [
        ("global", "globalLongShortAccountRatio"),
        ("top_account", "topLongShortAccountRatio"),
        ("top_position", "topLongShortPositionRatio"),
        ("taker", "takerlongshortRatio"),
    ]

    for key, endpoint in endpoints:
        time.sleep(RATE_LIMIT_SEC)
        for mirror in BINANCE_FAPI_MIRRORS:
            url = f"{mirror}/futures/data/{endpoint}"
            data = _http_get(url, params={"symbol": sym, "period": "1h", "limit": 1},
                             source="binance")
            if data and isinstance(data, list) and data:
                ratio = _safe_float(data[0].get("longShortRatio",
                                    data[0].get("buySellRatio")))
                if ratio is not None:
                    result[key] = ratio
                    break
            if _is_disabled("binance"):
                return result
    return result


def fetch_okx_top_ls(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch top trader L/S from OKX Rubik API."""
    result = {"top_account": None, "top_position": None, "global": None, "taker": None}
    if _is_disabled("okx"):
        return result

    okx_inst = f"{symbol}-USDT-SWAP"

    # Global L/S
    time.sleep(RATE_LIMIT_SEC)
    url = f"{OKX_API}/api/v5/rubik/stat/contracts/long-short-account-ratio"
    data = _http_get(url, params={"ccy": symbol, "period": "5m"}, source="okx")
    if data and data.get("data"):
        latest = data["data"][0]
        if isinstance(latest, list) and len(latest) >= 2:
            result["global"] = _safe_float(latest[1])

    # Top trader L/S
    time.sleep(RATE_LIMIT_SEC)
    url_top = f"{OKX_API}/api/v5/rubik/stat/contracts/long-short-account-ratio-contract-top-trader"
    data_top = _http_get(url_top, params={"instId": okx_inst, "period": "5m"}, source="okx")
    if data_top and data_top.get("data"):
        latest_top = data_top["data"][0]
        if isinstance(latest_top, list) and len(latest_top) >= 2:
            result["top_account"] = _safe_float(latest_top[1])
        elif isinstance(latest_top, dict):
            result["top_account"] = _safe_float(
                latest_top.get("longShortAccountRatio") or latest_top.get("ratio"))

    # Taker buy/sell
    time.sleep(RATE_LIMIT_SEC)
    url_taker = f"{OKX_API}/api/v5/rubik/stat/taker-volume"
    data_taker = _http_get(url_taker, params={"ccy": symbol, "instType": "SWAP",
                                               "period": "5m"}, source="okx")
    if data_taker and data_taker.get("data"):
        latest_taker = data_taker["data"][0]
        if isinstance(latest_taker, list) and len(latest_taker) >= 3:
            sell_vol = _safe_float(latest_taker[1])
            buy_vol = _safe_float(latest_taker[2])
            if sell_vol and buy_vol and sell_vol > 0:
                result["taker"] = round(buy_vol / sell_vol, 4)

    return result


def fetch_bybit_ls(symbol: str) -> Optional[float]:
    """Fetch long/short ratio from Bybit v5 API."""
    if _is_disabled("bybit"):
        return None
    time.sleep(RATE_LIMIT_SEC)
    url = f"{BYBIT_API}/v5/market/account-ratio"
    data = _http_get(url, params={"category": "linear", "symbol": f"{symbol}USDT",
                                   "period": "1h", "limit": 1}, source="bybit")
    if data and data.get("result") and data["result"].get("list"):
        items = data["result"]["list"]
        if items:
            return _safe_float(items[0].get("buyRatio"))
    return None


# ======================================================================
# Price Fetching (Binance spot -> CoinGecko failover)
# ======================================================================

def fetch_price(symbol: str) -> Optional[float]:
    """Fetch current price with multi-source failover."""
    sym = f"{symbol}USDT"

    # Binance spot
    if not _is_disabled("binance_spot"):
        data = _http_get(f"{BINANCE_SPOT}/api/v3/ticker/price",
                         params={"symbol": sym}, source="binance_spot")
        if data:
            price = _safe_float(data.get("price"))
            if price:
                return price

    # CoinGecko
    cg_id = CG_ID_MAP.get(symbol, symbol.lower())
    data = _http_get(f"{COINGECKO_API}/api/v3/simple/price",
                     params={"ids": cg_id, "vs_currencies": "usd"}, source="coingecko")
    if data and cg_id in data:
        price = _safe_float(data[cg_id].get("usd"))
        if price:
            return price

    return None


# ======================================================================
# Funding Rate Fetching
# ======================================================================

def fetch_funding_rate(symbol: str) -> Optional[float]:
    """Fetch funding rate with multi-source failover."""
    sym = f"{symbol}USDT"

    # Binance
    if not _is_disabled("binance"):
        for mirror in BINANCE_FAPI_MIRRORS:
            data = _http_get(f"{mirror}/fapi/v1/fundingRate",
                             params={"symbol": sym, "limit": 1}, source="binance")
            if data and isinstance(data, list) and data:
                rate = _safe_float(data[0].get("fundingRate"))
                if rate is not None:
                    return rate
                break

    # OKX
    if not _is_disabled("okx"):
        okx_sym = f"{symbol}-USDT-SWAP"
        data = _http_get(f"{OKX_API}/api/v5/public/funding-rate",
                         params={"instId": okx_sym}, source="okx")
        if data and data.get("data") and data["data"]:
            rate = _safe_float(data["data"][0].get("fundingRate"))
            if rate is not None:
                return rate

    return None


# ======================================================================
# Unified Data Fetch (CoinGlass -> Binance -> OKX -> Bybit)
# ======================================================================

def fetch_all_sentiment(symbol: str) -> Dict:
    """
    Fetch all top trader sentiment data for a symbol with full failover chain.
    Returns unified dict with: global_ls, top_account_ls, top_position_ls,
    taker_ratio, funding_rate, oi_change_pct, source.
    """
    result = {
        "symbol": symbol,
        "global_ls": None,        # Global L/S account ratio
        "top_account_ls": None,   # Top traders by account ratio
        "top_position_ls": None,  # Top traders by position ratio
        "taker_ratio": None,      # Taker buy/sell ratio
        "funding_rate": None,     # Current funding rate
        "oi_change_pct": None,    # OI change percent (1h)
        "bybit_ls": None,         # Bybit L/S ratio
        "source": None,
        "fetched_at": None,
    }

    has_cg_key = bool(_get_coinglass_key())
    primary_source = None

    # -- Source 1: CoinGlass v3 API --
    if has_cg_key and not _is_disabled("cg_v3"):
        global_data = fetch_cg_v3_global_ls(symbol)
        if global_data:
            result["global_ls"] = _safe_float(
                global_data.get("longShortRatio", global_data.get("longRate",
                global_data.get("buyRatio"))))
            primary_source = "coinglass_v3"

        top_acct = fetch_cg_v3_top_ls_account(symbol)
        if top_acct:
            result["top_account_ls"] = _safe_float(
                top_acct.get("longShortRatio", top_acct.get("longRate")))

        top_pos = fetch_cg_v3_top_ls_position(symbol)
        if top_pos:
            result["top_position_ls"] = _safe_float(
                top_pos.get("longShortRatio", top_pos.get("longRate")))

        oi_data = fetch_cg_v3_oi(symbol)
        if oi_data:
            curr_c = _safe_float(oi_data["current"].get("c", oi_data["current"].get("close")))
            prev_c = _safe_float(oi_data["previous"].get("c", oi_data["previous"].get("close")))
            if curr_c and prev_c and prev_c > 0:
                result["oi_change_pct"] = round((curr_c - prev_c) / prev_c * 100, 2)

        funding = fetch_cg_v3_funding(symbol)
        if funding is not None:
            result["funding_rate"] = funding

    # -- Source 2: CoinGlass v2 API --
    if has_cg_key and not _is_disabled("cg_v2"):
        if result["global_ls"] is None:
            v2_ls = fetch_cg_v2_long_short(symbol)
            if v2_ls:
                if isinstance(v2_ls, list) and v2_ls:
                    result["global_ls"] = _safe_float(v2_ls[0].get("longRate"))
                elif isinstance(v2_ls, dict):
                    result["global_ls"] = _safe_float(v2_ls.get("longRate"))
                if result["global_ls"] is not None and primary_source is None:
                    primary_source = "coinglass_v2"

        if result["top_position_ls"] is None:
            v2_pos = fetch_cg_v2_top_ls_position(symbol)
            if v2_pos:
                if isinstance(v2_pos, list) and v2_pos:
                    result["top_position_ls"] = _safe_float(v2_pos[0].get("longRate"))
                elif isinstance(v2_pos, dict):
                    result["top_position_ls"] = _safe_float(v2_pos.get("longRate"))

        if result["funding_rate"] is None:
            v2_fund = fetch_cg_v2_funding(symbol)
            if v2_fund is not None:
                result["funding_rate"] = v2_fund

    # -- Source 3: Binance Futures (no API key needed) --
    if not _is_disabled("binance"):
        binance = fetch_binance_top_ls(symbol)
        if result["global_ls"] is None and binance["global"] is not None:
            result["global_ls"] = binance["global"]
            if primary_source is None:
                primary_source = "binance"
        if result["top_account_ls"] is None and binance["top_account"] is not None:
            result["top_account_ls"] = binance["top_account"]
        if result["top_position_ls"] is None and binance["top_position"] is not None:
            result["top_position_ls"] = binance["top_position"]
        if result["taker_ratio"] is None and binance["taker"] is not None:
            result["taker_ratio"] = binance["taker"]

    # -- Source 4: OKX (no API key needed) --
    if not _is_disabled("okx"):
        okx = fetch_okx_top_ls(symbol)
        if result["global_ls"] is None and okx["global"] is not None:
            result["global_ls"] = okx["global"]
            if primary_source is None:
                primary_source = "okx"
        if result["top_account_ls"] is None and okx["top_account"] is not None:
            result["top_account_ls"] = okx["top_account"]
        if result["taker_ratio"] is None and okx["taker"] is not None:
            result["taker_ratio"] = okx["taker"]

    # -- Source 5: Bybit (no API key needed) --
    if result["global_ls"] is None and not _is_disabled("bybit"):
        bybit_ratio = fetch_bybit_ls(symbol)
        if bybit_ratio is not None:
            result["bybit_ls"] = bybit_ratio
            if primary_source is None:
                primary_source = "bybit"

    # -- Funding rate from exchange direct --
    if result["funding_rate"] is None:
        result["funding_rate"] = fetch_funding_rate(symbol)

    result["source"] = primary_source
    result["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return result


# ======================================================================
# Signal Analysis & Pick Generation
# ======================================================================

# Strategy thresholds
EXTREME_LONG_THRESHOLD = 0.70    # >70% long = crowd is over-leveraged long
EXTREME_SHORT_THRESHOLD = 0.30   # <30% long = crowd is over-leveraged short
WHALE_DIVERGE_THRESHOLD = 0.12   # Diff between top trader vs global > 12%
FUNDING_EXTREME = 0.0005         # |funding| > 0.05% = extreme
OI_SURGE_THRESHOLD = 5.0         # OI change > 5% in 1h = significant
TAKER_EXTREME_BUY = 1.20         # Taker buy/sell > 1.20 = aggressive buying
TAKER_EXTREME_SELL = 0.80        # Taker buy/sell < 0.80 = aggressive selling


def analyze_sentiment(data: Dict) -> List[Dict]:
    """
    Analyze sentiment data and generate trading signals.
    Multiple strategies can fire for the same symbol.

    Strategies:
    1. CROWD_EXTREME_REVERSION: Crowd >70% one side -> fade the crowd
    2. WHALE_DIVERGENCE: Top traders disagree with crowd -> follow whales
    3. FUNDING_REVERSAL: Extreme funding + top trader positioning -> reversal
    4. OI_SURGE_BREAKOUT: OI surging + top traders positioned -> breakout
    5. TAKER_AGGRESSION: Taker ratio extreme + top trader confirmation
    """
    signals = []
    symbol = data["symbol"]
    global_ls = data.get("global_ls")
    top_acct = data.get("top_account_ls")
    top_pos = data.get("top_position_ls")
    taker = data.get("taker_ratio")
    funding = data.get("funding_rate")
    oi_change = data.get("oi_change_pct")

    # Use best available L/S ratio
    best_ls = global_ls or top_acct or top_pos or data.get("bybit_ls")
    if best_ls is None:
        return signals

    # Normalize: some APIs return ratio (1.5 = 60% long / 40% short),
    # others return long% directly (0.60). Convert all to long% (0-1 range).
    if best_ls > 1:
        # It's a ratio: longShortRatio = longAccounts / shortAccounts
        long_pct = best_ls / (1 + best_ls)
    else:
        long_pct = best_ls

    # Same normalization for top trader ratios
    def _to_pct(val):
        if val is None:
            return None
        if val > 1:
            return val / (1 + val)
        return val

    top_acct_pct = _to_pct(top_acct)
    top_pos_pct = _to_pct(top_pos)
    best_top = top_pos_pct or top_acct_pct

    # --- Strategy 1: CROWD EXTREME REVERSION ---
    # When retail is extremely one-sided, fade them
    if long_pct >= EXTREME_LONG_THRESHOLD:
        # Crowd is heavily long -> SHORT signal (contrarian)
        extremity = (long_pct - EXTREME_LONG_THRESHOLD) / (1 - EXTREME_LONG_THRESHOLD)
        confidence = round(0.60 + min(0.25, extremity * 0.35), 3)
        # Boost if top traders agree with contrarian view (they're short)
        if best_top and best_top < 0.45:
            confidence = round(min(0.92, confidence + 0.10), 3)
        signals.append({
            "strategy": "cg_crowd_extreme_reversion",
            "direction": "SHORT",
            "confidence": confidence,
            "reason": f"Crowd {long_pct*100:.1f}% long (extreme) -> fade to SHORT"
                      f"{' | top traders confirm SHORT' if best_top and best_top < 0.45 else ''}",
        })

    elif long_pct <= EXTREME_SHORT_THRESHOLD:
        # Crowd is heavily short -> LONG signal (contrarian)
        extremity = (EXTREME_SHORT_THRESHOLD - long_pct) / EXTREME_SHORT_THRESHOLD
        confidence = round(0.60 + min(0.25, extremity * 0.35), 3)
        if best_top and best_top > 0.55:
            confidence = round(min(0.92, confidence + 0.10), 3)
        signals.append({
            "strategy": "cg_crowd_extreme_reversion",
            "direction": "LONG",
            "confidence": confidence,
            "reason": f"Crowd {long_pct*100:.1f}% long (extreme short) -> fade to LONG"
                      f"{' | top traders confirm LONG' if best_top and best_top > 0.55 else ''}",
        })

    # --- Strategy 2: WHALE DIVERGENCE ---
    # Top traders positioned differently from crowd
    if best_top is not None:
        diff = best_top - long_pct
        if abs(diff) >= WHALE_DIVERGE_THRESHOLD:
            direction = "LONG" if diff > 0 else "SHORT"
            confidence = round(0.62 + min(0.25, abs(diff) * 1.5), 3)
            signals.append({
                "strategy": "cg_whale_divergence",
                "direction": direction,
                "confidence": confidence,
                "reason": f"Whales {best_top*100:.1f}% long vs crowd {long_pct*100:.1f}% "
                          f"(divergence {abs(diff)*100:.1f}%) -> follow whales {direction}",
            })

    # --- Strategy 3: FUNDING REVERSAL ---
    # Extreme funding + positioned top traders = reversal signal
    if funding is not None and abs(funding) >= FUNDING_EXTREME:
        if funding > FUNDING_EXTREME:
            # Positive funding = longs paying shorts = over-leveraged longs
            direction = "SHORT"
            confidence = round(0.58 + min(0.25, abs(funding) / 0.001 * 0.15), 3)
            if best_top and best_top < 0.48:
                confidence = round(min(0.90, confidence + 0.08), 3)
            signals.append({
                "strategy": "cg_funding_reversal",
                "direction": direction,
                "confidence": confidence,
                "reason": f"Funding {funding*100:.4f}% (longs overleveraged) -> SHORT"
                          f"{' | whales confirm' if best_top and best_top < 0.48 else ''}",
            })
        elif funding < -FUNDING_EXTREME:
            # Negative funding = shorts paying longs = over-leveraged shorts
            direction = "LONG"
            confidence = round(0.58 + min(0.25, abs(funding) / 0.001 * 0.15), 3)
            if best_top and best_top > 0.52:
                confidence = round(min(0.90, confidence + 0.08), 3)
            signals.append({
                "strategy": "cg_funding_reversal",
                "direction": direction,
                "confidence": confidence,
                "reason": f"Funding {funding*100:.4f}% (shorts overleveraged) -> LONG"
                          f"{' | whales confirm' if best_top and best_top > 0.52 else ''}",
            })

    # --- Strategy 4: OI SURGE + TOP TRADER ALIGNMENT ---
    # Rising OI with top trader positioning = breakout confirmation
    if oi_change is not None and abs(oi_change) >= OI_SURGE_THRESHOLD and best_top is not None:
        if oi_change > OI_SURGE_THRESHOLD:
            # OI surging + top traders positioned = strong conviction
            if best_top > 0.55:
                confidence = round(0.63 + min(0.22, oi_change / 20 * 0.15), 3)
                signals.append({
                    "strategy": "cg_oi_surge_breakout",
                    "direction": "LONG",
                    "confidence": confidence,
                    "reason": f"OI surging +{oi_change:.1f}% + top traders {best_top*100:.0f}% "
                              f"long -> LONG breakout",
                })
            elif best_top < 0.45:
                confidence = round(0.63 + min(0.22, oi_change / 20 * 0.15), 3)
                signals.append({
                    "strategy": "cg_oi_surge_breakout",
                    "direction": "SHORT",
                    "confidence": confidence,
                    "reason": f"OI surging +{oi_change:.1f}% + top traders {best_top*100:.0f}% "
                              f"long -> SHORT breakout",
                })

    # --- Strategy 5: TAKER AGGRESSION ---
    # Extreme taker buy/sell ratio with top trader confirmation
    if taker is not None:
        if taker >= TAKER_EXTREME_BUY and (best_top is None or best_top > 0.50):
            confidence = round(0.60 + min(0.20, (taker - 1.0) * 0.5), 3)
            signals.append({
                "strategy": "cg_taker_aggression",
                "direction": "LONG",
                "confidence": confidence,
                "reason": f"Taker buy/sell {taker:.2f} (aggressive buying)"
                          f"{' + whales agree' if best_top and best_top > 0.55 else ''}",
            })
        elif taker <= TAKER_EXTREME_SELL and (best_top is None or best_top < 0.50):
            confidence = round(0.60 + min(0.20, (1.0 - taker) * 0.5), 3)
            signals.append({
                "strategy": "cg_taker_aggression",
                "direction": "SHORT",
                "confidence": confidence,
                "reason": f"Taker buy/sell {taker:.2f} (aggressive selling)"
                          f"{' + whales agree' if best_top and best_top < 0.45 else ''}",
            })

    return signals


def signal_to_pick(signal: Dict, symbol: str, price: float, data: Dict) -> Dict:
    """Convert a sentiment signal into an active_picks.json compatible pick."""
    direction = signal["direction"]
    confidence = signal["confidence"]
    strategy = signal["strategy"]

    # TP/SL: use ATR-like approach based on price
    # Approximate 1h ATR as ~1.5% of price for crypto
    atr_approx = price * 0.015

    if direction == "LONG":
        tp = round(price + atr_approx * 2.0, 8)
        sl = round(price - atr_approx * 1.0, 8)
    else:
        tp = round(price - atr_approx * 2.0, 8)
        sl = round(price + atr_approx * 1.0, 8)

    now = datetime.now(timezone.utc)
    pick_id = f"coinglass_{strategy}::{symbol}USDT::{now.strftime('%Y-%m-%d_%H%M')}"

    return {
        "id": pick_id,
        "strategy": strategy,
        "symbol": f"{symbol}USDT",
        "category": "crypto",
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": price,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": confidence,
        "ml_score": confidence,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": 200.0,
        "position_sizing": "coinglass_sentiment",
        "risk_per_trade_pct": 0.02,
        "max_safe_leverage": 3.0,
        "forward_trades": 0,
        "forward_wr": 0,
        "forward_validated": False,
        "elite_score": min(100, int(confidence * 100)),
        "elite_grade": "A" if confidence >= 0.80 else "B" if confidence >= 0.65 else "C",
        "reason": signal["reason"],
        "source_system": "coinglass_sentiment",
        # Sentiment metadata
        "global_ls_pct": data.get("global_ls"),
        "top_account_ls": data.get("top_account_ls"),
        "top_position_ls": data.get("top_position_ls"),
        "taker_ratio": data.get("taker_ratio"),
        "funding_rate": data.get("funding_rate"),
        "oi_change_pct": data.get("oi_change_pct"),
        "data_source": data.get("source"),
        "timestamp": now.isoformat(),
    }


# ======================================================================
# Main Scanner
# ======================================================================

def scan_coinglass(symbols: List[str] = None, max_picks: int = 20) -> Tuple[List[Dict], List[Dict]]:
    """
    Main scan: fetch sentiment for all symbols, analyze, generate picks.
    Returns (profiles, picks).
    """
    if symbols is None:
        symbols = SYMBOLS

    print("=" * 70)
    print("  COINGLASS TOP TRADER SENTIMENT SCRAPER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    has_key = bool(_get_coinglass_key())
    if has_key:
        key = _get_coinglass_key()
        print(f"  Mode: COINGLASS API (key={key[:6]}...{key[-4:]})")
    else:
        print("  Mode: EXCHANGE DIRECT (no CoinGlass API key)")
        print("  Tip: Set COINGLASS_API_KEY for aggregated multi-exchange data")
        print("  Free tier: https://www.coinglass.com/pricing (30 req/min)")

    print(f"  Scanning {len(symbols)} symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    print()

    all_profiles = []
    all_picks = []
    sources_used = set()

    for i, symbol in enumerate(symbols):
        print(f"  [{i+1}/{len(symbols)}] {symbol} ", end="", flush=True)

        # Fetch all sentiment data
        data = fetch_all_sentiment(symbol)

        if data["source"] is None:
            print("-- no data from any source")
            continue

        sources_used.add(data["source"])

        # Analyze and generate signals
        signals = analyze_sentiment(data)

        # Store profile
        profile = {
            "symbol": symbol,
            "global_ls": data.get("global_ls"),
            "top_account_ls": data.get("top_account_ls"),
            "top_position_ls": data.get("top_position_ls"),
            "taker_ratio": data.get("taker_ratio"),
            "funding_rate": data.get("funding_rate"),
            "oi_change_pct": data.get("oi_change_pct"),
            "bybit_ls": data.get("bybit_ls"),
            "signals_count": len(signals),
            "source": data["source"],
            "fetched_at": data["fetched_at"],
        }
        all_profiles.append(profile)

        if not signals:
            # Print summary even without signals
            ls_str = f"LS:{data.get('global_ls', '?')}"
            fund_str = f"Fund:{data.get('funding_rate', '?')}"
            print(f"src={data['source']} {ls_str} {fund_str} -- no signals (neutral)")
            continue

        # Get price and generate picks
        price = fetch_price(symbol)
        if price is None or price <= 0:
            print(f"src={data['source']} -- {len(signals)} signals but no price available")
            continue

        for sig in signals:
            pick = signal_to_pick(sig, symbol, price, data)
            all_picks.append(pick)

        sig_summary = ", ".join(f"{s['direction']}({s['strategy'].replace('cg_', '')})" for s in signals)
        print(f"src={data['source']} | {sig_summary}")

    # Deduplicate: keep highest confidence per symbol+direction
    deduped = {}
    for pick in all_picks:
        key = f"{pick['symbol']}__{pick['direction']}"
        if key not in deduped or pick["confidence"] > deduped[key]["confidence"]:
            deduped[key] = pick
    picks = sorted(deduped.values(), key=lambda p: p["confidence"], reverse=True)[:max_picks]

    print(f"\n  Scan complete: {len(all_profiles)} symbols analyzed, "
          f"{len(all_picks)} raw signals, {len(picks)} picks (deduped)")
    print(f"  Sources used: {', '.join(sorted(sources_used)) if sources_used else 'none'}")
    if _source_disabled:
        print(f"  Sources disabled: {', '.join(k for k, v in _source_disabled.items() if v)}")

    return all_profiles, picks


def save_coinglass_results(profiles: List[Dict], picks: List[Dict]):
    """Save CoinGlass results to data files."""
    now_iso = datetime.now(timezone.utc).isoformat()

    profiles_path = DATA_DIR / "coinglass_trader_profiles.json"
    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_iso,
            "source": "coinglass_sentiment",
            "symbol_count": len(profiles),
            "profiles": profiles,
        }, f, indent=2, default=str)
    print(f"  Saved {len(profiles)} profiles to {profiles_path}")

    picks_path = DATA_DIR / "coinglass_picks.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"  Saved {len(picks)} picks to {picks_path}")

    return profiles_path, picks_path


if __name__ == "__main__":
    profiles, picks = scan_coinglass()
    save_coinglass_results(profiles, picks)
    print(f"\nDone. {len(picks)} CoinGlass sentiment picks generated.")
