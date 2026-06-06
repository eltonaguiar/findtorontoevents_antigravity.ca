"""Forex price failover chain — replaces yfinance-only for FX symbols.

Mirrors the discipline of ``alpha_engine/equity_price_failover.py``.
Built because ``universal_price_enricher.py`` silently emitted price=0
for all forex symbols on GHA runners where yfinance fails with 401.

Public API
----------
    fetch_forex_rate(pair)          -> {"price", "base", "quote", "asof", "source"} | None
    fetch_forex_rates_batch(pairs)  -> dict[pair, result_or_None]

``pair`` is a standard 6-char FX symbol: "EURUSD", "GBPUSD", "USDJPY", etc.
The caller may also pass Yahoo-style pairs: "EURUSD=X" — the trailing ``=X``
is stripped automatically.

Failover order (tested live 2026-06-06, all no-key sources verified):
    1. Yahoo Finance v8 chart  — no auth, no rate limit, real-time (best for =X)
    2. Frankfurter API          — ECB rates, no auth, free, updates daily
    3. Open Exchange Rates      — no auth free tier, hourly updates
    4. Finnhub /forex/rates     — FINNHUB / FINNHUB_API_KEY env, 60 rpm
    5. Twelve Data /price       — TWELVE_DATA_API_KEY env, 800/day
    6. Alpha Vantage FX_RATE    — ALPHA_VANTAGE_API_KEY env, 25/min

yfinance is intentionally NOT in this chain — it is what we are replacing.
The caller falls back to yfinance only if this entire chain returns None.

Caching: 15-minute on-disk TTL at ``data/forex_rate_cache/{pair}.json``.
HTTP:    stdlib urllib only (no requests).
Testing: inject ``_HTTP_GET_JSON`` / ``_HTTP_GET_TEXT`` at module level.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("alpha_engine.forex_price_failover")

# ---------------------------------------------------------------------------
# Cache (15-minute TTL — FX updates intraday)
# ---------------------------------------------------------------------------
CACHE_DIR = Path(os.environ.get(
    "FOREX_RATE_CACHE_DIR",
    Path(__file__).parent.parent / "data" / "forex_rate_cache",
))
CACHE_TTL_SEC = int(os.environ.get("FOREX_RATE_CACHE_TTL_SEC", 60 * 15))

_HTTP_TIMEOUT = 6
_USER_AGENT = "FindTorontoEvents-ForexFailover/1.0 (zerounderscore@gmail.com)"


# ---------------------------------------------------------------------------
# HTTP helpers (same pattern as equity_price_failover)
# ---------------------------------------------------------------------------

def _default_http_get_json(url: str, timeout: int = _HTTP_TIMEOUT,
                            headers: dict | None = None) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, **(headers or {})}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.debug("http_get_json failed %s: %s", url, exc)
        return None


_HTTP_GET_JSON: Callable[..., Optional[dict | list]] = _default_http_get_json


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(pair: str) -> Path:
    safe = pair.upper().replace("=X", "").replace("/", "_")[:20]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{safe}.json"


def _cache_read(pair: str) -> Optional[dict]:
    p = _cache_path(pair)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_write(pair: str, payload: dict) -> None:
    try:
        _cache_path(pair).write_text(json.dumps(payload), encoding="utf-8")
    except Exception as exc:
        logger.debug("cache write failed for %s: %s", pair, exc)


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_pair(pair: str) -> str:
    """Strip =X suffix, uppercase, e.g. 'eurusd=X' -> 'EURUSD'."""
    return pair.upper().replace("=X", "").replace(" ", "").replace("/", "")


def _split_pair(pair: str) -> tuple[str, str]:
    """'EURUSD' -> ('EUR', 'USD')"""
    p = _normalize_pair(pair)
    if len(p) == 6:
        return p[:3], p[3:]
    return p, "USD"


# ---------------------------------------------------------------------------
# Source 1: Yahoo Finance v8 chart — no auth, real-time, tested working
# ---------------------------------------------------------------------------

def _adapter_yahoo_v8(pair: str) -> Optional[dict]:
    """Yahoo Finance /v8/finance/chart — no auth, no key, real-time quotes.

    Accepts standard pair format (EURUSD) and converts to Yahoo's =X suffix.
    Tested live 2026-06-06: all major pairs return price correctly.
    """
    p = _normalize_pair(pair)
    yahoo_sym = f"{p}=X"
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(yahoo_sym)}?interval=1d&range=1d"
    )
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        if price <= 0:
            return None
        base, quote = _split_pair(p)
        return {
            "price": price,
            "base": base,
            "quote": quote,
            "asof": _today_iso(),
            "source": "yahoo_v8",
        }
    except Exception as exc:
        logger.debug("yahoo_v8 parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Source 2: Frankfurter API — ECB rates, no auth, daily updates
# ---------------------------------------------------------------------------

def _adapter_frankfurter(pair: str) -> Optional[dict]:
    """Frankfurter (ECB) API — free, no key, daily updates.

    https://api.frankfurter.app/latest?from=BASE&to=QUOTE
    Covers major pairs. Updates daily from ECB reference rates.
    Tested live 2026-06-06: EUR, GBP, JPY, AUD, CAD, CHF, NZD all working.
    """
    base, quote = _split_pair(pair)
    url = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    try:
        rates = data.get("rates", {})
        price = float(rates.get(quote, 0))
        if price <= 0:
            return None
        return {
            "price": price,
            "base": base,
            "quote": quote,
            "asof": data.get("date", _today_iso()),
            "source": "frankfurter",
        }
    except Exception as exc:
        logger.debug("frankfurter parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Source 3: Open Exchange Rates — free tier, hourly updates, no key
# ---------------------------------------------------------------------------

# Module-level rate cache to avoid hammering open.er-api on batch calls
_OER_CACHE: dict = {}
_OER_CACHE_TIME: float = 0.0
_OER_CACHE_TTL = 900  # 15 min


def _get_oer_rates() -> dict:
    global _OER_CACHE, _OER_CACHE_TIME
    if _OER_CACHE and time.time() - _OER_CACHE_TIME < _OER_CACHE_TTL:
        return _OER_CACHE
    url = "https://open.er-api.com/v6/latest/USD"
    data = _HTTP_GET_JSON(url)
    if isinstance(data, dict) and data.get("rates"):
        _OER_CACHE = data["rates"]
        _OER_CACHE_TIME = time.time()
    return _OER_CACHE


def _adapter_open_er_api(pair: str) -> Optional[dict]:
    """Open Exchange Rates v6 — free, no key, hourly updates.

    All rates are relative to USD base. Cross-rates computed for non-USD pairs.
    Tested live 2026-06-06: EUR, GBP, JPY, AUD, CAD all present.
    """
    base, quote = _split_pair(pair)
    rates = _get_oer_rates()
    if not rates:
        return None
    try:
        # All OER rates are USD-based; compute cross if needed
        if base == "USD":
            price = float(rates[quote])
        elif quote == "USD":
            price = 1.0 / float(rates[base])
        else:
            price = float(rates[quote]) / float(rates[base])
        if price <= 0:
            return None
        return {
            "price": round(price, 6),
            "base": base,
            "quote": quote,
            "asof": _today_iso(),
            "source": "open_er_api",
        }
    except Exception as exc:
        logger.debug("open_er_api parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Source 4: Finnhub /forex/rates — key optional (FINNHUB / FINNHUB_API_KEY)
# ---------------------------------------------------------------------------

_FINNHUB_RATES_CACHE: dict = {}
_FINNHUB_RATES_TIME: float = 0.0


def _get_finnhub_rates() -> dict:
    global _FINNHUB_RATES_CACHE, _FINNHUB_RATES_TIME
    if _FINNHUB_RATES_CACHE and time.time() - _FINNHUB_RATES_TIME < _OER_CACHE_TTL:
        return _FINNHUB_RATES_CACHE
    key = os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB")
    if not key:
        return {}
    url = f"https://finnhub.io/api/v1/forex/rates?base=USD&token={key}"
    data = _HTTP_GET_JSON(url)
    if isinstance(data, dict) and data.get("quote"):
        _FINNHUB_RATES_CACHE = data["quote"]
        _FINNHUB_RATES_TIME = time.time()
    return _FINNHUB_RATES_CACHE


def _adapter_finnhub_forex(pair: str) -> Optional[dict]:
    """Finnhub /forex/rates — 60 rpm free, key from FINNHUB / FINNHUB_API_KEY."""
    base, quote = _split_pair(pair)
    rates = _get_finnhub_rates()
    if not rates:
        return None
    try:
        if base == "USD":
            price = float(rates[quote])
        elif quote == "USD":
            price = 1.0 / float(rates[base])
        else:
            price = float(rates[quote]) / float(rates[base])
        if price <= 0:
            return None
        return {
            "price": round(price, 6),
            "base": base,
            "quote": quote,
            "asof": _today_iso(),
            "source": "finnhub",
        }
    except Exception as exc:
        logger.debug("finnhub forex parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Source 5: Twelve Data /price — TWELVE_DATA_API_KEY env, 800/day
# ---------------------------------------------------------------------------

def _adapter_twelve_data_forex(pair: str) -> Optional[dict]:
    """Twelve Data /price endpoint for forex. 800 req/day free tier."""
    key = os.environ.get("TWELVE_DATA_API_KEY")
    if not key:
        return None
    base, quote = _split_pair(pair)
    symbol = f"{base}/{quote}"
    url = f"https://api.twelvedata.com/price?symbol={urllib.parse.quote(symbol)}&apikey={key}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict) or data.get("status") == "error":
        return None
    try:
        price = float(data.get("price", 0))
        if price <= 0:
            return None
        return {"price": price, "base": base, "quote": quote,
                "asof": _today_iso(), "source": "twelve_data"}
    except Exception as exc:
        logger.debug("twelve_data forex parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Source 6: Alpha Vantage FX_RATE — ALPHA_VANTAGE_API_KEY env, 25/min
# ---------------------------------------------------------------------------

def _adapter_alpha_vantage_forex(pair: str) -> Optional[dict]:
    """Alpha Vantage CURRENCY_EXCHANGE_RATE. 25/min free tier."""
    key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not key:
        return None
    base, quote = _split_pair(pair)
    url = (
        f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE"
        f"&from_currency={base}&to_currency={quote}&apikey={key}"
    )
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    try:
        inner = data.get("Realtime Currency Exchange Rate", {})
        price = float(inner.get("5. Exchange Rate", 0))
        if price <= 0:
            return None
        return {"price": price, "base": base, "quote": quote,
                "asof": _today_iso(), "source": "alpha_vantage"}
    except Exception as exc:
        logger.debug("alpha_vantage forex parse failed for %s: %s", pair, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ADAPTERS = [
    _adapter_yahoo_v8,
    _adapter_frankfurter,
    _adapter_open_er_api,
    _adapter_finnhub_forex,
    _adapter_twelve_data_forex,
    _adapter_alpha_vantage_forex,
]


def fetch_forex_rate(pair: str) -> Optional[dict]:
    """Return rate for ``pair`` from the first working source.

    Args:
        pair: FX pair like "EURUSD", "GBPUSD=X", "EUR/USD"

    Returns:
        {"price": float, "base": str, "quote": str, "asof": str, "source": str}
        or None if all sources fail.
    """
    key = _normalize_pair(pair)
    cached = _cache_read(key)
    if cached:
        return cached

    for adapter in _ADAPTERS:
        result = adapter(pair)
        if result and result.get("price", 0) > 0:
            _cache_write(key, result)
            logger.debug("forex rate %s=%.5f from %s", key, result["price"], result["source"])
            return result

    logger.warning("all forex adapters failed for %s", pair)
    return None


def fetch_forex_rates_batch(pairs: list[str]) -> dict[str, Optional[dict]]:
    """Fetch rates for multiple pairs. Tries OER/Frankfurter bulk calls first
    to minimize individual requests, then falls through per-pair chain.

    Returns:
        dict mapping each input pair (normalized) to result or None.
    """
    results: dict[str, Optional[dict]] = {}
    # Pre-warm OER cache — one HTTP call covers all pairs
    _get_oer_rates()

    for pair in pairs:
        key = _normalize_pair(pair)
        results[key] = fetch_forex_rate(pair)

    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    pairs = sys.argv[1:] or ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"]
    print("Testing forex failover chain...")
    for p in pairs:
        r = fetch_forex_rate(p)
        if r:
            print(f"  {r['base']}/{r['quote']} = {r['price']:.5f}  [{r['source']}]  {r['asof']}")
        else:
            print(f"  {p}: ALL SOURCES FAILED")
