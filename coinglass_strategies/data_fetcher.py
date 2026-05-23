"""Multi-source ratio fetcher with smart geo-block detection.

Binance (primary) -> Bybit -> OKX -> Coinglass API -> CoinGecko.
Session-level source disabling: after 2 consecutive failures from any
source, that source is skipped for all remaining symbols.
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ── M-039: Exchange spread divergence (2026-05-17) ─────────────────────────
# When the same asset trades at significantly different prices across exchanges,
# it often signals a false breakout or manipulation. Default OFF (shadow mode)
# until multi-exchange price feed is fully wired.
# Enable: EXCHANGE_DIVERGENCE_GATE=1
EXCHANGE_DIVERGENCE_THRESHOLD = float(os.getenv("EXCHANGE_DIVERGENCE_THRESHOLD", "0.005"))

logger = logging.getLogger(__name__)

_BINANCE_FAPI_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
_BINANCE_SPOT_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
BINANCE_FUTURES = "https://fapi.binance.com"
BINANCE_SPOT = "https://api.binance.com"
BYBIT_API = "https://api.bybit.com"
COINGLASS_API = "https://open-api.coinglass.com"
OKX_API = "https://www.okx.com"
COINGECKO_API = "https://api.coingecko.com"

# Per-source rate limit tracking
_last_call: Dict[str, float] = {}
_MIN_INTERVAL = 1.0  # seconds between calls to same source

# Session-level source disabling (geo-block / persistent failure detection)
_source_failures: Dict[str, int] = {}
_source_disabled: Dict[str, bool] = {}
_FAILURE_THRESHOLD = 2  # disable source after this many consecutive failures

# HTTP status codes that should never be retried
_NO_RETRY_CODES = {400, 401, 403, 404, 410, 418, 451}


def _record_failure(source: str) -> None:
    """Record a failure for a source; disable after threshold."""
    _source_failures[source] = _source_failures.get(source, 0) + 1
    if _source_failures[source] >= _FAILURE_THRESHOLD:
        _source_disabled[source] = True
        logger.warning("Source '%s' disabled after %d consecutive failures",
                       source, _source_failures[source])


def _record_success(source: str) -> None:
    """Reset failure counter on success."""
    _source_failures[source] = 0


def _is_source_disabled(source: str) -> bool:
    """Check if a source has been disabled this session."""
    return _source_disabled.get(source, False)


def _rate_limit(source: str):
    """Enforce minimum interval between calls to the same source."""
    now = time.time()
    last = _last_call.get(source, 0)
    wait = _MIN_INTERVAL - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[source] = time.time()


def _http_get(url: str, params: dict = None, timeout: int = 10,
              headers: dict = None, source: str = None) -> Optional[dict]:
    """GET with single retry — but NO retry on 4xx client errors.

    4xx errors (403, 451 geo-block, etc.) are permanent; retrying wastes time.
    Only retries on 5xx server errors, timeouts, and connection errors.
    """
    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, timeout=timeout,
                                headers=headers or {})
            # On 4xx: fail immediately, no retry
            if resp.status_code in _NO_RETRY_CODES:
                logger.warning("GET %s returned %d (no retry) — %s",
                               url, resp.status_code, resp.reason)
                if source:
                    _record_failure(source)
                return None
            resp.raise_for_status()
            if source:
                _record_success(source)
            return resp.json()
        except requests.exceptions.HTTPError as exc:
            # Check if this was a 4xx we didn't catch above
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                logger.warning("GET %s HTTP %d (no retry)", url,
                               exc.response.status_code)
                if source:
                    _record_failure(source)
                return None
            if attempt == 0:
                time.sleep(1)
            else:
                logger.warning("GET %s failed: %s", url, exc)
                if source:
                    _record_failure(source)
        except Exception as exc:
            if attempt == 0:
                time.sleep(1)
            else:
                logger.warning("GET %s failed: %s", url, exc)
                if source:
                    _record_failure(source)
    return None


# -- Binance Futures (primary) --------------------------------------------
def _binance_ratio(endpoint: str, symbol: str,
                   period: str = "15m") -> Optional[float]:
    """Fetch a single ratio type from Binance Futures data endpoints with failover."""
    if _is_source_disabled("binance_futures"):
        return None
    _rate_limit("binance_futures")
    for fbase in _BINANCE_FAPI_BASES:
        url = f"{fbase}/futures/data/{endpoint}"
        data = _http_get(url, params={"symbol": symbol, "period": period,
                                      "limit": 1}, source="binance_futures")
        if data and isinstance(data, list) and len(data) > 0:
            row = data[0]
            if "longShortRatio" in row:
                return float(row["longShortRatio"])
            elif "buySellRatio" in row:
                return float(row["buySellRatio"])
        # If source got disabled from 451, skip remaining endpoints
        if _is_source_disabled("binance_futures"):
            break
    return None


def fetch_binance(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch all 4 ratio types from Binance Futures.

    Probes with global ratio first. If that fails (451 geo-block),
    skips the other 3 endpoints immediately.
    """
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}

    if _is_source_disabled("binance_futures"):
        return result

    # Probe: try global ratio first
    result["global"] = _binance_ratio("globalLongShortAccountRatio", symbol)
    if result["global"] is None:
        # If global failed, Binance is likely geo-blocked — skip remaining
        logger.info("Binance probe failed for %s, skipping remaining endpoints",
                    symbol)
        return result

    # Global succeeded — fetch the rest
    result["top_trader_account"] = _binance_ratio(
        "topLongShortAccountRatio", symbol)
    result["top_trader_position"] = _binance_ratio(
        "topLongShortPositionRatio", symbol)
    result["taker"] = _binance_ratio("takerlongshortRatio", symbol)
    return result


# -- Bybit (fallback 1) ---------------------------------------------------
def fetch_bybit(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch from Bybit V5 API — not geo-blocked from GitHub Actions.

    Bybit provides:
      - account-ratio: global long/short account ratio
      - No top-trader or taker endpoints, but global ratio is reliable.
    """
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if _is_source_disabled("bybit"):
        return result

    bybit_sym = symbol  # Bybit uses BTCUSDT format

    # 1. Global long/short account ratio
    _rate_limit("bybit")
    url = f"{BYBIT_API}/v5/market/account-ratio"
    data = _http_get(url, params={"category": "linear", "symbol": bybit_sym,
                                   "period": "1h", "limit": 1},
                     source="bybit")
    if data and data.get("result") and data["result"].get("list"):
        latest = data["result"]["list"][0]
        # Bybit returns buyRatio / sellRatio
        buy_ratio = _safe_float(latest.get("buyRatio"))
        sell_ratio = _safe_float(latest.get("sellRatio"))
        if buy_ratio is not None and sell_ratio is not None and sell_ratio > 0:
            result["global"] = round(buy_ratio / sell_ratio, 4)

    return result


# -- OKX (fallback 2) ----------------------------------------------------
def fetch_okx(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch from OKX Rubik long/short ratio endpoints.

    Fetches global ratio, top trader account ratio, and taker buy/sell ratio.
    OKX Rubik endpoints:
      - contracts/long-short-account-ratio  (global L/S)
      - contracts/long-short-account-ratio-contract-top-trader  (top trader L/S)
      - taker-volume  (taker buy/sell ratio — requires instType=SWAP&ccy=BTC)
    """
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if _is_source_disabled("okx"):
        return result

    okx_ccy = symbol[:-4] if symbol.endswith("USDT") else symbol.replace("-USDT", "")
    okx_inst = f"{okx_ccy}-USDT-SWAP"

    # 1. Global long/short account ratio
    _rate_limit("okx")
    url = f"{OKX_API}/api/v5/rubik/stat/contracts/long-short-account-ratio"
    data = _http_get(url, params={"ccy": okx_ccy, "period": "5m"}, source="okx")
    if data and data.get("data"):
        latest = data["data"][0]
        if len(latest) >= 2:
            result["global"] = _safe_float(latest[1])

    # 2. Top trader long/short account ratio
    _rate_limit("okx")
    url_top = f"{OKX_API}/api/v5/rubik/stat/contracts/long-short-account-ratio-contract-top-trader"
    data_top = _http_get(url_top, params={"instId": okx_inst, "period": "5m"},
                         source="okx")
    if data_top and data_top.get("data"):
        latest_top = data_top["data"][0]
        # Response format: [ts, longShortAccountRatio]
        if isinstance(latest_top, list) and len(latest_top) >= 2:
            result["top_trader_account"] = _safe_float(latest_top[1])
        elif isinstance(latest_top, dict):
            result["top_trader_account"] = _safe_float(
                latest_top.get("longShortAccountRatio") or latest_top.get("ratio"))

    # 3. Taker buy/sell volume ratio (fixed: instType=SWAP and ccy are REQUIRED)
    _rate_limit("okx")
    url_taker = f"{OKX_API}/api/v5/rubik/stat/taker-volume"
    data_taker = _http_get(url_taker, params={"ccy": okx_ccy, "instType": "SWAP",
                                               "period": "5m"},
                           source="okx")
    if data_taker and data_taker.get("data"):
        latest_taker = data_taker["data"][0]
        # Response format: [ts, sellVol, buyVol]
        if isinstance(latest_taker, list) and len(latest_taker) >= 3:
            sell_vol = _safe_float(latest_taker[1])
            buy_vol = _safe_float(latest_taker[2])
            if sell_vol and buy_vol and sell_vol > 0:
                result["taker"] = round(buy_vol / sell_vol, 4)

    return result


# -- Coinglass API (fallback 3) -------------------------------------------
def fetch_coinglass(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch from Coinglass public v2 endpoint (requires API key)."""
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if _is_source_disabled("coinglass_api"):
        return result
    api_key = os.environ.get("COINGLASS_API_KEY", "")
    if not api_key:
        logger.debug("No COINGLASS_API_KEY set, skipping Coinglass API")
        return result
    _rate_limit("coinglass_api")
    base_sym = symbol.replace("USDT", "")
    url = f"{COINGLASS_API}/public/v2/long_short"
    headers = {"coinglassSecret": api_key}
    data = _http_get(url, params={"symbol": base_sym, "timeType": 2},
                     headers=headers, source="coinglass_api")
    if not data or not isinstance(data, dict):
        return result
    items = data.get("data", [])
    if isinstance(items, list):
        for item in items:
            if item.get("symbol", "").upper() == base_sym.upper():
                result["global"] = _safe_float(item.get("longRate"))
                break
    elif isinstance(items, dict):
        result["global"] = _safe_float(items.get("longRate"))
    return result


# -- CoinGecko (fallback 4 — price-derived sentiment) --------------------
def fetch_coingecko_ratio(symbol: str) -> Dict[str, Optional[float]]:
    """Derive a sentiment proxy from CoinGecko market data.

    CoinGecko doesn't provide L/S ratios directly, but the
    24h price change can serve as a directional sentiment proxy.
    Positive change → bullish bias (ratio > 1), negative → bearish (< 1).
    """
    result = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    if _is_source_disabled("coingecko"):
        return result

    from . import config as cfg
    base = symbol.replace("USDT", "").replace("USD", "")
    cg_id = cfg.SYMBOL_TO_COINGECKO.get(symbol, base.lower())

    _rate_limit("coingecko")
    url = f"{COINGECKO_API}/api/v3/simple/price"
    data = _http_get(url, params={"ids": cg_id, "vs_currencies": "usd",
                                   "include_24hr_change": "true"},
                     source="coingecko")
    if data and cg_id in data:
        pct = _safe_float(data[cg_id].get("usd_24h_change"))
        if pct is not None:
            # Convert % change to a ratio-like value:
            # +5% → 1.05 (bullish), -5% → 0.95 (bearish)
            result["global"] = round(1.0 + (pct / 100.0), 4)
    return result


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# -- Main entry point ---------------------------------------------------
def fetch_all_ratios(symbol: str) -> Dict[str, Optional[float]]:
    """Fetch all 4 ratio types with 5-source failover and gap-filling.

    Order: Binance Futures -> Bybit -> OKX -> Coinglass API -> CoinGecko.
    Sources disabled after repeated failures are automatically skipped.

    After getting global ratio from the first successful source, attempts
    to fill any remaining NULL fields (top_trader_account, top_trader_position,
    taker) from subsequent sources — particularly OKX which provides
    top_trader and taker data that Binance geo-blocks.

    Returns dict with keys: global, top_trader_account,
    top_trader_position, taker, source, fetched_at.
    """
    sources = [
        ("binance", fetch_binance),
        ("bybit", fetch_bybit),
        ("okx", fetch_okx),
        ("coinglass", fetch_coinglass),
        ("coingecko", fetch_coingecko_ratio),
    ]

    _RATIO_KEYS = ("global", "top_trader_account", "top_trader_position", "taker")
    merged = {"global": None, "top_trader_account": None,
              "top_trader_position": None, "taker": None}
    primary_source = None

    for source_name, fetcher in sources:
        ratios = fetcher(symbol)

        # Track primary source (first one providing global ratio)
        if primary_source is None and ratios.get("global") is not None:
            primary_source = source_name

        # Fill in any NULL fields from this source
        for key in _RATIO_KEYS:
            if merged[key] is None and ratios.get(key) is not None:
                merged[key] = ratios[key]

        # If all fields populated, stop early
        if all(merged[k] is not None for k in _RATIO_KEYS):
            break

    if primary_source:
        merged["source"] = primary_source
        merged["fetched_at"] = datetime.now(timezone.utc).isoformat()
        nulls = [k for k in _RATIO_KEYS if merged[k] is None]
        if nulls:
            logger.info("Gaps remaining for %s after all sources: %s",
                        symbol, ", ".join(nulls))
        return merged

    logger.error("All sources failed for %s", symbol)
    merged["source"] = None
    merged["fetched_at"] = None
    return merged


# -- Funding Rate (with Bybit + OKX fallback) ----------------------------
def fetch_funding_rate(symbol: str) -> Optional[float]:
    """Fetch current funding rate with failover.

    Order: Binance Futures -> Bybit -> OKX -> Binance Spot (premium index).
    Binance Futures is geo-blocked (HTTP 451) from GitHub Actions,
    so Bybit and OKX are the primary working sources in CI.
    """
    # Try Binance Futures first
    if not _is_source_disabled("binance_futures"):
        _rate_limit("binance_futures")
        for fbase in _BINANCE_FAPI_BASES:
            url = f"{fbase}/fapi/v1/fundingRate"
            data = _http_get(url, params={"symbol": symbol, "limit": 1},
                             source="binance_futures")
            if data and isinstance(data, list) and len(data) > 0:
                rate = _safe_float(data[0].get("fundingRate"))
                if rate is not None:
                    return rate
            if _is_source_disabled("binance_futures"):
                break

    # Fallback 1: Bybit funding rate history
    if not _is_source_disabled("bybit"):
        _rate_limit("bybit")
        url = f"{BYBIT_API}/v5/market/funding/history"
        data = _http_get(url, params={"category": "linear", "symbol": symbol,
                                       "limit": 1}, source="bybit")
        if data and data.get("result") and data["result"].get("list"):
            rate = _safe_float(data["result"]["list"][0].get("fundingRate"))
            if rate is not None:
                return rate

    # Fallback 2: OKX funding rate
    if not _is_source_disabled("okx"):
        _rate_limit("okx")
        okx_sym = symbol[:-4] + "-USDT-SWAP" if symbol.endswith("USDT") else symbol
        url = f"{OKX_API}/api/v5/public/funding-rate"
        data = _http_get(url, params={"instId": okx_sym}, source="okx")
        if data and data.get("data") and len(data["data"]) > 0:
            rate = _safe_float(data["data"][0].get("fundingRate"))
            if rate is not None:
                return rate

    # Fallback 3: Binance Spot premium index (different domain, usually not blocked)
    if not _is_source_disabled("binance_spot"):
        _rate_limit("binance_spot")
        for sbase in _BINANCE_SPOT_BASES:
            url = f"{sbase}/fapi/v1/premiumIndex"
            data = _http_get(url, params={"symbol": symbol},
                             source="binance_spot")
            if data and isinstance(data, dict):
                rate = _safe_float(data.get("lastFundingRate"))
                if rate is not None:
                    return rate
            if _is_source_disabled("binance_spot"):
                break

    logger.info("No funding rate available for %s from any source", symbol)
    return None


# -- Current Price (with CoinGecko fallback) -----------------------------
def fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch latest price with Binance spot -> CoinGecko fallback."""
    # Try Binance spot (usually NOT geo-blocked)
    if not _is_source_disabled("binance_spot"):
        _rate_limit("binance_spot")
        url = f"{BINANCE_SPOT}/api/v3/ticker/price"
        data = _http_get(url, params={"symbol": symbol},
                         source="binance_spot")
        if data:
            price = _safe_float(data.get("price"))
            if price is not None:
                return price

    # Fallback: CoinGecko
    if not _is_source_disabled("coingecko"):
        _rate_limit("coingecko")
        # Map common symbols to CoinGecko IDs
        cg_id_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "DOGE": "dogecoin", "XRP": "ripple", "ADA": "cardano",
            "AVAX": "avalanche-2", "DOT": "polkadot", "MATIC": "matic-network",
            "LINK": "chainlink", "BNB": "binancecoin", "LTC": "litecoin",
            "UNI": "uniswap", "ATOM": "cosmos", "NEAR": "near",
            "ARB": "arbitrum", "OP": "optimism", "APT": "aptos",
            "SUI": "sui", "FIL": "filecoin", "PEPE": "pepe",
        }
        base = symbol.replace("USDT", "").replace("USD", "")
        cg_id = cg_id_map.get(base, base.lower())
        url = f"{COINGECKO_API}/api/v3/simple/price"
        data = _http_get(url, params={"ids": cg_id, "vs_currencies": "usd"},
                         source="coingecko")
        if data and cg_id in data:
            price = _safe_float(data[cg_id].get("usd"))
            if price is not None:
                return price

    logger.warning("Price fetch failed for %s from all sources", symbol)
    return None


# -- ATR (with Binance spot + OKX fallback) ------------------------------
def fetch_atr(symbol: str, period: int = 14) -> Optional[float]:
    """Compute ATR from recent klines with failover.

    Order: Binance Futures -> Binance Spot -> OKX.
    """
    klines = None

    # Try Binance Futures
    if not _is_source_disabled("binance_futures"):
        _rate_limit("binance_futures")
        url = f"{BINANCE_FUTURES}/fapi/v1/klines"
        klines = _http_get(url, params={"symbol": symbol, "interval": "1h",
                                        "limit": period + 1},
                           source="binance_futures")

    # Fallback: Binance Spot (different domain, usually not blocked)
    if not klines and not _is_source_disabled("binance_spot"):
        _rate_limit("binance_spot")
        url = f"{BINANCE_SPOT}/api/v3/klines"
        klines = _http_get(url, params={"symbol": symbol, "interval": "1h",
                                        "limit": period + 1},
                           source="binance_spot")

    # Fallback: Bybit
    if not klines and not _is_source_disabled("bybit"):
        _rate_limit("bybit")
        url = f"{BYBIT_API}/v5/market/kline"
        data = _http_get(url, params={"category": "linear", "symbol": symbol,
                                       "interval": "60",
                                       "limit": period + 1},
                         source="bybit")
        if data and data.get("result") and data["result"].get("list"):
            # Bybit format: [[startTime, open, high, low, close, vol, turnover], ...]
            # Returned newest first, reverse for chronological order
            klines = list(reversed(data["result"]["list"]))

    # Fallback: OKX
    if not klines and not _is_source_disabled("okx"):
        _rate_limit("okx")
        okx_sym = symbol[:-4] + "-USDT" if symbol.endswith("USDT") else symbol
        url = f"{OKX_API}/api/v5/market/candles"
        data = _http_get(url, params={"instId": okx_sym, "bar": "1H",
                                      "limit": str(period + 1)},
                         source="okx")
        if data and data.get("data"):
            # OKX format: [[ts, o, h, l, c, vol, ...], ...]
            klines = data["data"]
            # OKX returns newest first, reverse to match Binance order
            klines = list(reversed(klines))

    if not klines or len(klines) < period + 1:
        return None

    trs = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i - 1][4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


# ── M-039: Exchange spread divergence helpers (2026-05-17) ─────────────────


def compute_exchange_spread_divergence(prices_by_exchange: Dict[str, float]) -> float:
    """Return spread divergence ratio: (max_price - min_price) / avg_price.

    > 0.005 (0.5%) = significant divergence, likely false breakout or manipulation.
    Returns 0.0 when fewer than 2 exchanges are provided.

    Args:
        prices_by_exchange: mapping of exchange name -> last price for the same asset.
    """
    if len(prices_by_exchange) < 2:
        return 0.0
    prices = list(prices_by_exchange.values())
    avg = sum(prices) / len(prices)
    if avg == 0.0:
        return 0.0
    return (max(prices) - min(prices)) / avg


def is_exchange_divergence_high(symbol: str) -> bool:
    """Return True if exchange spread divergence exceeds threshold (filter false breakouts).

    Stub: always returns False until a multi-exchange price feed is wired.
    When wired, call compute_exchange_spread_divergence() with live prices from
    Binance + Bybit + OKX and compare against EXCHANGE_DIVERGENCE_THRESHOLD.

    Gate is default OFF — enable via EXCHANGE_DIVERGENCE_GATE=1 env var.

    Wiring plan:
      Target: audit_trail/quality_gates.py::passes_active_gate / passes_smart_gate
      Expected: wire when fetch_bybit / fetch_okx last-price endpoints confirmed stable.
    """
    # Stub: return False until multi-exchange live price feed is wired
    return False
