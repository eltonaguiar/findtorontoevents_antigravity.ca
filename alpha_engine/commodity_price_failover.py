"""Commodity price failover chain — replaces yfinance-only for futures symbols.

Mirrors the discipline of ``alpha_engine/equity_price_failover.py``.
Built because ``universal_price_enricher.py`` silently returned price=0
for commodity futures (CL=F, GC=F, ZC=F etc.) on GHA runners where
yfinance fails with 401.

Public API
----------
    fetch_commodity_price(symbol)          -> {"price", "symbol", "asof", "source"} | None
    fetch_commodity_prices_batch(symbols)  -> dict[symbol, result_or_None]

``symbol`` is a Yahoo-style futures ticker: "GC=F" (gold), "CL=F" (crude),
"ZC=F" (corn), "SI=F" (silver), etc. The trailing ``=F`` is preserved
internally because Yahoo's v8 endpoint needs it.

Failover order (tested live 2026-06-06):
    1. Yahoo Finance v8 chart  — no auth, no rate limit, real-time (CONFIRMED working)
    2. Stooq futures endpoint   — no auth, free (gc.f, cl.f naming convention)
    3. FMP /quote               — FMP_API_KEY env, 250/day
    4. Finnhub /quote           — FINNHUB / FINNHUB_API_KEY env, 60 rpm
    5. FRED CSV                 — no auth, for gold/oil macro proxies (slow)

Covered symbol map (Yahoo =F tickers -> description):
    GC=F   Gold
    SI=F   Silver
    CL=F   Crude Oil (WTI)
    NG=F   Natural Gas
    HG=F   Copper
    ZC=F   Corn
    ZS=F   Soybeans
    ZW=F   Wheat
    ZO=F   Oats
    KC=F   Coffee
    CT=F   Cotton
    SB=F   Sugar

Caching: 15-minute on-disk TTL.
HTTP:    stdlib urllib only.
Testing: inject ``_HTTP_GET_JSON`` / ``_HTTP_GET_TEXT`` at module level.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("alpha_engine.commodity_price_failover")

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHE_DIR = Path(os.environ.get(
    "COMMODITY_PRICE_CACHE_DIR",
    Path(__file__).parent.parent / "data" / "commodity_price_cache",
))
CACHE_TTL_SEC = int(os.environ.get("COMMODITY_PRICE_CACHE_TTL_SEC", 60 * 15))

_HTTP_TIMEOUT = 6
_USER_AGENT = "FindTorontoEvents-CommodityFailover/1.0 (zerounderscore@gmail.com)"


# ---------------------------------------------------------------------------
# HTTP helpers
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


def _default_http_get_text(url: str, timeout: int = _HTTP_TIMEOUT,
                            headers: dict | None = None) -> Optional[str]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, **(headers or {})}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("http_get_text failed %s: %s", url, exc)
        return None


_HTTP_GET_JSON: Callable[..., Optional[dict | list]] = _default_http_get_json
_HTTP_GET_TEXT: Callable[..., Optional[str]] = _default_http_get_text


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(symbol: str) -> Path:
    safe = symbol.upper().replace("=F", "_F").replace("=", "_").replace("/", "_")[:20]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{safe}.json"


def _cache_read(symbol: str) -> Optional[dict]:
    p = _cache_path(symbol)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_write(symbol: str, payload: dict) -> None:
    try:
        _cache_path(symbol).write_text(json.dumps(payload), encoding="utf-8")
    except Exception as exc:
        logger.debug("cache write failed for %s: %s", symbol, exc)


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


# ---------------------------------------------------------------------------
# Stooq symbol mapping: Yahoo "GC=F" -> Stooq "gc.f"
# ---------------------------------------------------------------------------
_STOOQ_MAP = {
    "GC=F": "gc.f", "SI=F": "si.f", "CL=F": "cl.f", "NG=F": "ng.f",
    "HG=F": "hg.f", "ZC=F": "zc.f", "ZS=F": "zs.f", "ZW=F": "zw.f",
    "ZO=F": "zo.f", "KC=F": "kc.f", "CT=F": "ct.f", "SB=F": "sb.f",
    "PA=F": "pa.f", "PL=F": "pl.f", "RB=F": "rb.f", "HO=F": "ho.f",
}

# FRED series IDs for commodity macro proxies (daily, free, no key)
_FRED_MAP = {
    "GC=F": "GOLDAMGBD228NLBM",  # Gold fixing price, USD/troy oz
    "CL=F": "DCOILWTICO",         # WTI crude daily spot
    "NG=F": "MHHNGSP",            # Henry Hub natural gas spot
    "HG=F": "PCOPPUSDM",          # Copper (monthly, last resort)
}


# ---------------------------------------------------------------------------
# Source 1: Yahoo Finance v8 chart — no auth, real-time
# ---------------------------------------------------------------------------

def _adapter_yahoo_v8(symbol: str) -> Optional[dict]:
    """Yahoo Finance /v8/finance/chart — no auth, real-time commodity futures.

    Tested live 2026-06-06: GC=F, CL=F, SI=F, ZC=F, ZS=F, NG=F, HG=F all OK.
    """
    s = _normalize_symbol(symbol)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(s)}?interval=1d&range=1d"
    )
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        currency = meta.get("currency", "USD")
        if price <= 0:
            return None
        return {
            "price": price,
            "symbol": s,
            "currency": currency,
            "asof": _today_iso(),
            "source": "yahoo_v8",
        }
    except Exception as exc:
        logger.debug("yahoo_v8 commodity parse failed for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Source 2: Stooq — no auth, free (patchy for some contracts)
# ---------------------------------------------------------------------------

def _adapter_stooq(symbol: str) -> Optional[dict]:
    """Stooq commodity futures endpoint. No auth. Coverage: major futures only.

    Stooq uses e.g. gc.f for gold, cl.f for crude.
    Sometimes returns HTML captcha instead of CSV — we detect that.
    """
    s = _normalize_symbol(symbol)
    stooq_sym = _STOOQ_MAP.get(s)
    if not stooq_sym:
        return None
    url = f"https://stooq.com/q/l/?s={stooq_sym}&f=sd2t2ohlcv&h&e=csv"
    body = _HTTP_GET_TEXT(url)
    if not body or body.strip().startswith("<"):
        # Got HTML (captcha / rate limit) — skip
        return None
    try:
        rows = list(csv.DictReader(io.StringIO(body)))
        if not rows:
            return None
        row = rows[0]
        if row.get("Close") in (None, "", "N/D"):
            return None
        price = float(row["Close"])
        if price <= 0:
            return None
        return {
            "price": price,
            "symbol": s,
            "currency": "USD",
            "asof": row.get("Date", _today_iso()),
            "source": "stooq",
        }
    except Exception as exc:
        logger.debug("stooq parse failed for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Source 3: FMP /quote — FMP_API_KEY env, 250/day
# ---------------------------------------------------------------------------

def _adapter_fmp(symbol: str) -> Optional[dict]:
    """Financial Modeling Prep /quote. 250/day free tier. Key: FMP_API_KEY."""
    key = os.environ.get("FMP_API_KEY")
    if not key:
        return None
    s = _normalize_symbol(symbol)
    # FMP lists metals/energy as <X>USD (GCUSD, CLUSD, SIUSD...) but does NOT
    # list grains/softs that way (ZCUSD/KCUSD/CTUSD don't exist), so the naive
    # s.replace('=F','USD') would silently 404 for corn/coffee/cotton. Restrict
    # FMP to the contracts where the <X>USD convention is known to resolve;
    # everything else falls through to the next source (Yahoo v8 already covers
    # grains/softs at slot #1).
    _FMP_USD_OK = {"GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "PA=F", "PL=F",
                   "RB=F", "HO=F", "BZ=F"}
    if s not in _FMP_USD_OK:
        return None
    fmp_sym = s.replace("=F", "USD")
    url = f"https://financialmodelingprep.com/api/v3/quote/{urllib.parse.quote(fmp_sym)}?apikey={key}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, list) or not data:
        return None
    try:
        price = float(data[0].get("price", 0))
        if price <= 0:
            return None
        return {
            "price": price,
            "symbol": s,
            "currency": "USD",
            "asof": _today_iso(),
            "source": "fmp",
        }
    except Exception as exc:
        logger.debug("fmp parse failed for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Source 4: Finnhub /quote — FINNHUB / FINNHUB_API_KEY env, 60 rpm
# ---------------------------------------------------------------------------

def _adapter_finnhub(symbol: str) -> Optional[dict]:
    """Finnhub /quote for commodity futures. 60 rpm free tier."""
    key = os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB")
    if not key:
        return None
    s = _normalize_symbol(symbol)
    url = f"https://finnhub.io/api/v1/quote?symbol={urllib.parse.quote(s)}&token={key}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    try:
        price = float(data.get("c") or 0)
        if price <= 0:
            return None
        return {
            "price": price,
            "symbol": s,
            "currency": "USD",
            "asof": _today_iso(),
            "source": "finnhub",
        }
    except Exception as exc:
        logger.debug("finnhub commodity parse failed for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# Source 5: FRED CSV — no auth, daily, for gold/crude/natgas macro proxies
# ---------------------------------------------------------------------------

def _adapter_fred(symbol: str) -> Optional[dict]:
    """FRED daily commodity prices. No auth. Slow but reliable for GC/CL/NG."""
    s = _normalize_symbol(symbol)
    series_id = _FRED_MAP.get(s)
    if not series_id:
        return None
    # IMPORTANT: FRED series are macro SPOT/CASH prices (London gold fixing,
    # WTI cash, Henry Hub spot, monthly copper) — NOT the front-month futures
    # contract the pick was entered on. The futures price can differ from spot
    # by the full basis (contango/backwardation), so using a FRED value as the
    # "current" futures price produces phantom PnL and can falsely trip TP/SL.
    # We therefore tag every FRED result is_proxy=True / price_basis="spot" and
    # the enricher refuses to use proxy prices for PnL/closure (display-only).
    def _fred_result(price, asof):
        return {
            "price": price,
            "symbol": s,
            "currency": "USD",
            "asof": asof,
            "source": "fred",
            "is_proxy": True,
            "price_basis": "spot",
        }

    # Use FRED API key if available, fall back to anonymous CSV
    fred_key = os.environ.get("FRED_API_KEY")
    if fred_key:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={fred_key}&file_type=json"
            f"&sort_order=desc&limit=1"
        )
        data = _HTTP_GET_JSON(url)
        if isinstance(data, dict):
            try:
                obs = data.get("observations", [])
                if obs and obs[0].get("value") not in (".", None, ""):
                    price = float(obs[0]["value"])
                    if price > 0:
                        return _fred_result(price, obs[0].get("date", _today_iso()))
            except Exception:
                pass

    # Anonymous CSV fallback
    url_csv = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    body = _HTTP_GET_TEXT(url_csv, timeout=8)
    if not body:
        return None
    try:
        rows = list(csv.DictReader(io.StringIO(body)))
        for row in reversed(rows):
            val = row.get("VALUE", row.get(series_id, ""))
            if val and val != ".":
                price = float(val)
                if price > 0:
                    return _fred_result(price, row.get("DATE", _today_iso()))
    except Exception as exc:
        logger.debug("fred parse failed for %s: %s", symbol, exc)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ADAPTERS = [
    _adapter_yahoo_v8,
    _adapter_stooq,
    _adapter_fmp,
    _adapter_finnhub,
    _adapter_fred,
]


def fetch_commodity_price(symbol: str) -> Optional[dict]:
    """Return price for commodity futures ``symbol`` from first working source.

    Args:
        symbol: Yahoo-style futures ticker, e.g. "GC=F", "CL=F", "ZC=F"

    Returns:
        {"price": float, "symbol": str, "currency": str, "asof": str, "source": str}
        or None if all sources fail.
    """
    key = _normalize_symbol(symbol)
    cached = _cache_read(key)
    if cached:
        return cached

    for adapter in _ADAPTERS:
        result = adapter(symbol)
        if result and result.get("price", 0) > 0:
            _cache_write(key, result)
            logger.debug("commodity %s=%.4f from %s", key, result["price"], result["source"])
            return result

    logger.warning("all commodity adapters failed for %s", symbol)
    return None


def fetch_commodity_prices_batch(symbols: list[str]) -> dict[str, Optional[dict]]:
    """Fetch prices for multiple commodity symbols."""
    return {_normalize_symbol(s): fetch_commodity_price(s) for s in symbols}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    syms = sys.argv[1:] or ["GC=F", "CL=F", "SI=F", "ZC=F", "ZS=F", "NG=F", "HG=F", "CT=F"]
    print("Testing commodity failover chain...")
    for s in syms:
        r = fetch_commodity_price(s)
        if r:
            print(f"  {r['symbol']} = {r['price']:.4f} {r['currency']}  [{r['source']}]  {r['asof']}")
        else:
            print(f"  {s}: ALL SOURCES FAILED")
