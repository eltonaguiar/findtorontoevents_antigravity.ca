"""Equity price + market-cap failover chain.

Mirrors the discipline of `alpha_engine/api_failover.py` (crypto) for
US-listed equity tickers. Built because yfinance fails to import (or
silently 401s) on GitHub Actions ubuntu-latest runners on a regular
basis, leaving `value_screener_runner.py` emitting `long=0 short=0`
on every cron — see `gh run view 25066227910 --log` for the symptom
("yfinance unavailable — market caps cannot be fetched").

This module exposes three public functions:

    fetch_quote(ticker)            -> {"price", "volume", "asof", "source"} | None
    fetch_market_cap(ticker)       -> float | None
    fetch_quotes_batch(tickers)    -> dict[ticker, quote_or_None]

Each tries a chain of free-tier sources and returns the first success.
On total failure they return None so the caller can short-circuit.
A 1-hour on-disk cache lives at `data/equity_quote_cache/{ticker}.json`
to limit per-runner request count and survive the 25-minute GHA budget.

Failover order (per the project's "API Failover Rule" — never depend
on a single endpoint):

  Quote (price + volume):
    1. Stooq anonymous quote endpoint     (no auth, no rate limit, .us suffix)
    2. Finnhub /quote                     (60 rpm, FINNHUB_API_KEY env, also 'FINNHUB')
    3. Tiingo IEX quote                   (500/day,  TIINGO_API_KEY env)
    4. Twelve Data /quote                 (800/day,  TWELVE_DATA_API_KEY env)
    5. Alpha Vantage GLOBAL_QUOTE         (25/min,   ALPHA_VANTAGE_API_KEY env)
    6. Financial Modeling Prep /quote     (250/day,  FMP_API_KEY env)
    7. yfinance .history(period="5d")     (last resort — flaky in GHA)

  Market cap (USD):
    1. Finnhub /stock/profile2            (yields marketCapitalization in $M)
    2. Financial Modeling Prep /quote     (marketCap in USD, batch-friendly)
    3. Polygon.io /v3/reference/tickers   (5/min, POLYGON_API_KEY env)
    4. SEC EDGAR companyfacts             (no auth — derived: sharesOutstanding * price)
    5. yfinance .info["marketCap"]        (last resort)

Adapters use stdlib `urllib.request` (no `requests` dependency, per the
explicit constraint) with a 5-second timeout each. Failure of one source
NEVER cascades — the chain just falls through to the next.

Tests inject `_http_get_json` via the module-level `_HTTP_GET_JSON` hook
to avoid live network in CI; see `tests/test_equity_price_failover.py`.

Wire-up: this module is the new default for `fetch_prices_via_yfinance`
and `fetch_market_caps_via_yfinance` in `alpha_engine/value_screener_runner.py`.
yfinance is intentionally retained as the *last* fallback so dev boxes
that have it installed still get the broadest coverage. Per CLAUDE.md
"Wire-Up Rule" this is wired into the production pick-generation path
(value_screener_runner.run -> tools/run_ueps_pickers.py -> ueps-pick-runner.yml).
"""
from __future__ import annotations

import concurrent.futures
import csv
import io
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("alpha_engine.equity_price_failover")

# ---------------------------------------------------------------------------
# Cache (1h TTL on disk)
# ---------------------------------------------------------------------------
CACHE_DIR = Path(os.environ.get(
    "EQUITY_QUOTE_CACHE_DIR",
    Path(__file__).parent.parent / "data" / "equity_quote_cache",
))
CACHE_TTL_SEC = int(os.environ.get("EQUITY_QUOTE_CACHE_TTL_SEC", 60 * 60))


_TICKER_SAFE_RE = re.compile(r"[^A-Z0-9._-]+")


def _cache_path(ticker: str, kind: str) -> Path:
    # Only allow alnum + . _ - in the ticker portion of the filename so a
    # malformed ticker (`..`, `\\foo`, `/etc/passwd`) cannot escape CACHE_DIR.
    safe = _TICKER_SAFE_RE.sub("_", ticker.upper())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{safe}.{kind}.json"


def _cache_read(ticker: str, kind: str) -> Optional[dict]:
    p = _cache_path(ticker, kind)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_write(ticker: str, kind: str, payload: dict) -> None:
    p = _cache_path(ticker, kind)
    try:
        p.write_text(json.dumps(payload), encoding="utf-8")
    except Exception as exc:
        logger.debug("cache write failed for %s.%s: %s", ticker, kind, exc)


# ---------------------------------------------------------------------------
# HTTP helpers — stdlib urllib only (no requests dep per project constraint)
# ---------------------------------------------------------------------------
_HTTP_TIMEOUT = 5
_USER_AGENT = "FindTorontoEvents-EquityFailover/1.0 (zerounderscore@gmail.com)"


def _default_http_get_json(url: str, timeout: int = _HTTP_TIMEOUT,
                           headers: dict | None = None) -> Optional[dict | list]:
    """Default JSON GET. Returns parsed JSON or None on any failure."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, **(headers or {})}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return json.loads(body)
    except Exception as exc:  # noqa: BLE001 — adapters expect None on any failure
        logger.debug("http_get_json failed %s: %s", url, exc)
        return None


def _default_http_get_text(url: str, timeout: int = _HTTP_TIMEOUT,
                           headers: dict | None = None) -> Optional[str]:
    """Default text GET — used by Stooq CSV adapter."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, **(headers or {})}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        logger.debug("http_get_text failed %s: %s", url, exc)
        return None


# Module-level injection hooks — tests overwrite these with mocks. We expose
# them as module attributes (rather than ctor args) so adapters stay simple
# and the mocking pattern matches the existing `alpha_engine.api_failover`
# convention. To override in a test:
#
#     import alpha_engine.equity_price_failover as epf
#     epf._HTTP_GET_JSON = lambda url, timeout=5, headers=None: my_stub(url)
#
_HTTP_GET_JSON: Callable[..., Optional[dict | list]] = _default_http_get_json
_HTTP_GET_TEXT: Callable[..., Optional[str]] = _default_http_get_text


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


# ---------------------------------------------------------------------------
# Quote adapters — each returns {"price", "volume", "asof", "source"} | None
# ---------------------------------------------------------------------------
# Tickers with these exchange suffixes are non-US listings — the `.us`
# Stooq snapshot endpoint will silently return wrong-ticker data (e.g.
# `ASML.AS` -> `asml.as.us` resolves to a different security) so we must
# detect and skip. Stooq DOES support some of these (`.HK`, `.L`, `.PA`,
# `.AS`, `.DE`, `.MI`, `.MC`, `.WAR`, `.JP`, `.AX`, `.NZ`) but the EOD
# coverage is patchy, so we conservatively skip rather than silently
# return possibly-wrong data. US-listed tickers with internal dots
# (`BRK.B`, `BRK.A`, `BF.B`) appear without an exchange code on Stooq —
# the Stooq convention replaces the dot with a hyphen (`brk-b.us`) so
# we normalize that explicitly.
_NON_US_EXCHANGE_SUFFIXES = frozenset({
    "AS", "L", "PA", "DE", "MI", "MC", "WAR", "JP", "AX", "NZ", "HK",
    "TO", "V", "T", "ST", "OL", "HE", "BR", "VI", "LS", "AT", "IS",
    "TA", "JK", "KS", "KQ", "SS", "SZ", "TW", "TWO", "BO", "NS", "SI",
    "SR", "QA", "DU", "AB", "ME", "RG", "VL", "TL", "BK", "MX", "BA",
    "SA", "SN", "CO", "F",
})

# US-listed tickers like BRK.B / BF.B that contain a dot use a hyphen on
# Stooq (e.g. `brk-b.us`). Translate those before building the URL.
_US_DOTTED_CLASS_SHARES = frozenset({"BRK.A", "BRK.B", "BF.B", "BF.A",
                                       "RDS.A", "RDS.B"})


def _stooq_symbol(ticker: str) -> Optional[str]:
    """Map a normalized ticker to a Stooq symbol, or None if non-US.

    Returns:
        - "<ticker>.us" for plain US tickers (e.g. AAPL -> aapl.us)
        - "brk-b.us" for known US class-share tickers
        - None when the ticker has a non-US exchange suffix
    """
    t = _normalize_ticker(ticker)
    if not t:
        return None
    if "." in t:
        # Class-share US ticker (BRK.B etc.) → hyphenate
        if t in _US_DOTTED_CLASS_SHARES:
            return f"{t.replace('.', '-').lower()}.us"
        # Otherwise this is an exchange-qualified symbol — check the suffix
        suffix = t.rsplit(".", 1)[-1]
        if suffix in _NON_US_EXCHANGE_SUFFIXES:
            return None  # Stooq `.us` would silently mis-resolve this
        # Unknown suffix: refuse to guess — skip rather than ship wrong prices
        return None
    return f"{t.lower()}.us"


def _adapter_stooq_quote(ticker: str) -> Optional[dict]:
    """Stooq anonymous quote endpoint. Free, no key, no rate limit.

    Endpoint: https://stooq.com/q/l/?s={ticker}.us&f=sd2t2ohlcv&h&e=csv
    Returns one CSV row with the latest EOD close (delayed during the
    session). The historical bulk CSV is captcha-gated — we only use the
    snapshot endpoint here.

    Non-US tickers (anything with an exchange suffix like .AS, .HK, .L)
    are skipped — Stooq's `.us` suffix would silently return wrong-ticker
    data. See `_stooq_symbol` for the mapping rules.
    """
    t = _normalize_ticker(ticker)
    if not t:
        return None
    sym = _stooq_symbol(t)
    if sym is None:
        # Non-US listing or unknown-suffix ticker — let the next adapter handle it
        logger.debug("stooq: skipping %s (non-US or unknown exchange suffix)", t)
        return None
    url = f"https://stooq.com/q/l/?s={urllib.parse.quote(sym)}&f=sd2t2ohlcv&h&e=csv"
    body = _HTTP_GET_TEXT(url)
    if not body:
        return None
    try:
        rows = list(csv.DictReader(io.StringIO(body)))
        if not rows:
            return None
        row = rows[0]
        if row.get("Date") in (None, "", "N/D") or row.get("Close") in (None, "", "N/D"):
            return None
        close = float(row["Close"])
        if close <= 0:
            return None
        vol = 0
        try:
            vol = int(float(row.get("Volume") or 0))
        except (ValueError, TypeError):
            pass
        return {
            "price": close,
            "volume": vol,
            "asof": row.get("Date") or _today_iso(),
            "source": "stooq",
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("stooq parse failed for %s: %s", t, exc)
        return None


def _adapter_finnhub_quote(ticker: str) -> Optional[dict]:
    """Finnhub /quote. 60 rpm. Key in FINNHUB_API_KEY (or 'FINNHUB' legacy)."""
    api_key = os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = f"https://finnhub.io/api/v1/quote?symbol={urllib.parse.quote(t)}&token={api_key}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    # Finnhub returns {c: current, h, l, o, pc, t} — c=0 means unknown
    try:
        price = float(data.get("c") or 0)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None
    return {
        "price": price,
        "volume": 0,  # /quote doesn't ship volume; caller can fetch it elsewhere
        "asof": datetime.fromtimestamp(int(data.get("t") or 0),
                                       tz=timezone.utc).date().isoformat()
                if data.get("t") else _today_iso(),
        "source": "finnhub",
    }


def _adapter_tiingo_quote(ticker: str) -> Optional[dict]:
    """Tiingo IEX quote. 500/day, key in TIINGO_API_KEY."""
    api_key = os.environ.get("TIINGO_API_KEY")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = f"https://api.tiingo.com/iex/?tickers={urllib.parse.quote(t)}&token={api_key}"
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, list) or not data:
        return None
    rec = data[0] if isinstance(data[0], dict) else {}
    try:
        price = float(rec.get("last") or rec.get("tngoLast") or 0)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None
    vol = 0
    try:
        vol = int(rec.get("volume") or 0)
    except (ValueError, TypeError):
        pass
    return {
        "price": price,
        "volume": vol,
        "asof": (rec.get("timestamp") or _today_iso())[:10],
        "source": "tiingo",
    }


def _adapter_twelvedata_quote(ticker: str) -> Optional[dict]:
    """Twelve Data /quote. 800/day, key in TWELVE_DATA_API_KEY."""
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = (f"https://api.twelvedata.com/quote?symbol={urllib.parse.quote(t)}"
           f"&apikey={api_key}")
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    if data.get("status") == "error":
        return None
    try:
        price = float(data.get("close") or 0)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None
    vol = 0
    try:
        vol = int(float(data.get("volume") or 0))
    except (ValueError, TypeError):
        pass
    return {
        "price": price,
        "volume": vol,
        "asof": data.get("datetime", _today_iso())[:10],
        "source": "twelvedata",
    }


def _adapter_alphavantage_quote(ticker: str) -> Optional[dict]:
    """Alpha Vantage GLOBAL_QUOTE. 25/min, 500/day, ALPHA_VANTAGE_API_KEY env.

    NOTE: AV throttles tightly per IP. GHA's ephemeral IPs share the same
    pool, so concurrent jobs may collide. Treated as a high-tier fallback,
    not a primary.
    """
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = (f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
           f"&symbol={urllib.parse.quote(t)}&apikey={api_key}")
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    quote = data.get("Global Quote") or data.get("globalQuote") or {}
    if not isinstance(quote, dict) or not quote:
        return None
    try:
        price = float(quote.get("05. price") or 0)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None
    vol = 0
    try:
        vol = int(float(quote.get("06. volume") or 0))
    except (ValueError, TypeError):
        pass
    return {
        "price": price,
        "volume": vol,
        "asof": quote.get("07. latest trading day", _today_iso()),
        "source": "alphavantage",
    }


def _adapter_fmp_quote(ticker: str) -> Optional[dict]:
    """Financial Modeling Prep /quote. 250/day, FMP_API_KEY env.

    Returns price AND marketCap on a single call — that's why FMP is shared
    between the price chain (high tier) and the market_cap chain (tier 2).
    """
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = (f"https://financialmodelingprep.com/api/v3/quote/"
           f"{urllib.parse.quote(t)}?apikey={api_key}")
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, list) or not data:
        return None
    rec = data[0] if isinstance(data[0], dict) else {}
    try:
        price = float(rec.get("price") or 0)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None
    vol = 0
    try:
        vol = int(rec.get("volume") or 0)
    except (ValueError, TypeError):
        pass
    return {
        "price": price,
        "volume": vol,
        "asof": _today_iso(),
        "source": "fmp",
        # Bonus: piggyback market_cap so caller can warm the mc cache
        "_market_cap": rec.get("marketCap"),
    }


def _adapter_yfinance_quote(ticker: str) -> Optional[dict]:
    """yfinance fallback. Last-resort because import fails in GHA regularly."""
    try:
        import yfinance as yf  # noqa: PLC0415 — lazy by design
    except ImportError:
        logger.debug("yfinance unavailable in this runtime — skipping")
        return None
    t = _normalize_ticker(ticker)
    try:
        hist = yf.Ticker(t).history(period="5d")
        if hist is None or hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        if price <= 0:
            return None
        vol = 0
        try:
            vol = int(hist["Volume"].iloc[-1] or 0)
        except Exception:
            pass
        return {
            "price": price,
            "volume": vol,
            "asof": hist.index[-1].date().isoformat() if hasattr(hist.index[-1], "date")
                    else _today_iso(),
            "source": "yfinance",
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("yfinance fetch failed for %s: %s", t, exc)
        return None


# Quote chain in tier order. Tests can rebind by patching this list.
_QUOTE_CHAIN: list[Callable[[str], Optional[dict]]] = [
    _adapter_stooq_quote,
    _adapter_finnhub_quote,
    _adapter_tiingo_quote,
    _adapter_twelvedata_quote,
    _adapter_alphavantage_quote,
    _adapter_fmp_quote,
    _adapter_yfinance_quote,
]


# ---------------------------------------------------------------------------
# Market-cap adapters — each returns float (USD) | None
# ---------------------------------------------------------------------------
def _adapter_finnhub_marketcap(ticker: str) -> Optional[float]:
    """Finnhub /stock/profile2. marketCapitalization is in $M (millions)."""
    api_key = os.environ.get("FINNHUB_API_KEY") or os.environ.get("FINNHUB")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = (f"https://finnhub.io/api/v1/stock/profile2?symbol="
           f"{urllib.parse.quote(t)}&token={api_key}")
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    raw = data.get("marketCapitalization")
    if raw is None:
        return None
    try:
        return float(raw) * 1_000_000  # convert $M → $
    except (ValueError, TypeError):
        return None


def _adapter_fmp_marketcap(ticker: str) -> Optional[float]:
    """FMP /quote already reports marketCap in USD on the same payload.

    Cache strategy: FMP's /quote endpoint returns price + marketCap on the
    same call. To avoid burning 2x of the 250/day FMP budget when both
    `fetch_quote` and `fetch_market_cap` are called for the same ticker,
    we route through `fetch_quote` (which uses the disk cache) and rely
    on the side-channel marketcap cache that `fetch_quote` writes whenever
    an adapter returns `_market_cap` piggyback. See `fetch_quote` below.
    """
    t = _normalize_ticker(ticker)
    if not t:
        return None
    # First: check if a previous fetch_quote() call for this ticker already
    # warmed the marketcap cache via piggyback. Bypasses HTTP entirely.
    cached_mc = _cache_read(t, "marketcap")
    if cached_mc and cached_mc.get("market_cap"):
        try:
            mc = float(cached_mc["market_cap"])
            if mc > 0 and cached_mc.get("source") == "fmp_piggyback":
                return mc
        except (ValueError, TypeError):
            pass
    # No piggyback cached yet — call FMP via fetch_quote to populate both
    # the quote cache AND (via side-channel) the marketcap cache.
    if not (os.environ.get("FMP_API_KEY")):
        return None
    # Use fetch_quote so the disk cache short-circuits any duplicate FMP call
    # made within the cache TTL. fetch_quote walks the chain in order and
    # may not actually hit FMP if an earlier adapter (e.g. Stooq) succeeded
    # — in that case the marketcap cache stays cold and we fall through.
    fetch_quote(t, use_cache=True)
    # Re-read the marketcap cache: fetch_quote writes it as a side-effect
    # when an adapter returns _market_cap piggyback.
    cached_mc = _cache_read(t, "marketcap")
    if cached_mc and cached_mc.get("market_cap"):
        try:
            mc = float(cached_mc["market_cap"])
            if mc > 0 and cached_mc.get("source") == "fmp_piggyback":
                return mc
        except (ValueError, TypeError):
            pass
    return None


def _adapter_polygon_marketcap(ticker: str) -> Optional[float]:
    """Polygon /v3/reference/tickers/{T}. 5/min free, POLYGON_API_KEY env."""
    api_key = os.environ.get("POLYGON_API_KEY")
    if not api_key:
        return None
    t = _normalize_ticker(ticker)
    url = (f"https://api.polygon.io/v3/reference/tickers/{urllib.parse.quote(t)}"
           f"?apiKey={api_key}")
    data = _HTTP_GET_JSON(url)
    if not isinstance(data, dict):
        return None
    results = data.get("results")
    if not isinstance(results, dict):
        return None
    raw = results.get("market_cap")
    try:
        mc = float(raw or 0)
        return mc if mc > 0 else None
    except (ValueError, TypeError):
        return None


def _edgar_minimal_price(ticker: str) -> Optional[float]:
    """Minimal price fetch for EDGAR market-cap multiplication.

    Decoupled from the full quote chain so EDGAR's marketcap success
    doesn't depend on all 7 quote sources — only on Stooq + Finnhub.
    Per the cross-AI review: a recursive `fetch_quote` call here couples
    EDGAR success to the full quote chain, which defeats the
    "independent fallback" intent (if quotes fail across all 7, EDGAR
    can't price-multiply and we lose the marketcap fallback we built it
    for). Use a 2-step minimal chain instead.
    """
    for adapter in (_adapter_stooq_quote, _adapter_finnhub_quote):
        try:
            q = adapter(ticker)
        except Exception:  # noqa: BLE001
            continue
        if q and q.get("price"):
            try:
                return float(q["price"])
            except (ValueError, TypeError):
                continue
    return None


def _adapter_edgar_marketcap(ticker: str,
                              *, price: Optional[float] = None) -> Optional[float]:
    """SEC EDGAR-derived: shares_outstanding * latest price.

    No auth, no rate limit — but EDGAR shares figures are
    the most-recent-filed quarterly (10-Q/10-K), so they lag 30-90 days
    versus live float. That's still acceptable for the value-screener's
    $300M floor (which never lives near the boundary for S&P 100 names).

    Re-uses `alpha_engine.fundamentals_fetcher.FundamentalsFetcher` so we
    don't duplicate the polite-UA + CIK-mapping logic. Imported lazily
    so test sandboxes that don't ship EDGAR fixtures still pass.

    Price decoupling: the optional `price` kwarg lets the caller pass a
    known-good price (e.g. the one already obtained from `fetch_quote`)
    so EDGAR doesn't recurse into the full quote chain. When `price` is
    not provided, falls back to a minimal 2-source price fetch (Stooq +
    Finnhub) to stay independent of the rest of the chain.
    """
    try:
        from alpha_engine.fundamentals_fetcher import FundamentalsFetcher  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        logger.debug("EDGAR adapter unavailable: %s", exc)
        return None
    try:
        rec = FundamentalsFetcher().fetch(ticker)
    except Exception as exc:  # noqa: BLE001
        logger.debug("EDGAR fetch failed for %s: %s", ticker, exc)
        return None
    shares = (rec.balance_sheet or {}).get("shares_outstanding")
    if not shares or float(shares) <= 0:
        return None
    if price is None:
        price = _edgar_minimal_price(ticker)
    if price is None or price <= 0:
        return None
    try:
        return float(shares) * float(price)
    except (ValueError, TypeError):
        return None


def _adapter_yfinance_marketcap(ticker: str) -> Optional[float]:
    """yfinance .info["marketCap"] — last-resort, flaky."""
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError:
        return None
    try:
        info = yf.Ticker(_normalize_ticker(ticker)).info or {}
        mc = info.get("marketCap")
        return float(mc) if mc and float(mc) > 0 else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("yfinance marketcap fetch failed for %s: %s", ticker, exc)
        return None


_MARKETCAP_CHAIN: list[Callable[[str], Optional[float]]] = [
    _adapter_finnhub_marketcap,
    _adapter_fmp_marketcap,
    _adapter_polygon_marketcap,
    _adapter_edgar_marketcap,
    _adapter_yfinance_marketcap,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fetch_quote(ticker: str, *, use_cache: bool = True) -> Optional[dict]:
    """Return latest quote dict for `ticker`, or None on total chain failure.

    Output schema:
        {"price": float, "volume": int, "asof": "YYYY-MM-DD",
         "source": "<adapter-name>"}
    """
    t = _normalize_ticker(ticker)
    if not t:
        return None
    if use_cache:
        cached = _cache_read(t, "quote")
        if cached:
            return cached
    for adapter in _QUOTE_CHAIN:
        try:
            result = adapter(t)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s quote adapter raised for %s: %s",
                           adapter.__name__, t, exc)
            continue
        if result and result.get("price"):
            # Strip private fields before persisting — _market_cap is consumed
            # by the caller via fetch_market_cap, but it shouldn't leak into
            # the cached quote payload.
            persisted = {k: v for k, v in result.items() if not k.startswith("_")}
            if use_cache:
                _cache_write(t, "quote", persisted)
                # Side-channel: when an adapter (currently only FMP) returns
                # `_market_cap` piggyback, persist a separate marketcap cache
                # entry so a later fetch_market_cap() call doesn't burn a 2nd
                # HTTP request. See _adapter_fmp_marketcap for the consumer.
                piggyback_mc = result.get("_market_cap")
                if piggyback_mc is not None:
                    try:
                        mc_val = float(piggyback_mc)
                        if mc_val > 0:
                            _cache_write(t, "marketcap", {
                                "market_cap": mc_val,
                                "source": f"{result['source']}_piggyback",
                            })
                    except (ValueError, TypeError):
                        pass
            logger.info("fetch_quote(%s) <- %s @ %s", t,
                        result["source"], result["price"])
            return persisted
    logger.warning("fetch_quote(%s): ALL %d sources failed", t, len(_QUOTE_CHAIN))
    return None


def fetch_market_cap(ticker: str, *, use_cache: bool = True) -> Optional[float]:
    """Return market cap (USD) for `ticker`, or None on total chain failure.

    EDGAR adapter is special: it needs a current price to multiply by
    shares-outstanding. To avoid recursing into the full quote chain
    (which couples EDGAR's success to ALL quote sources), we pre-fetch
    the price ONCE here and pass it as a kwarg. Other adapters take only
    `ticker`.
    """
    t = _normalize_ticker(ticker)
    if not t:
        return None
    if use_cache:
        cached = _cache_read(t, "marketcap")
        if cached and cached.get("market_cap"):
            return float(cached["market_cap"])
    # Cache for the EDGAR price hint — avoid recomputing if multiple
    # adapters need it. We only fetch on demand (inside the loop), so the
    # cost is zero unless EDGAR is actually reached.
    edgar_price_hint: Optional[float] = None
    edgar_price_attempted = False
    for adapter in _MARKETCAP_CHAIN:
        try:
            if adapter is _adapter_edgar_marketcap:
                if not edgar_price_attempted:
                    edgar_price_hint = _edgar_minimal_price(t)
                    edgar_price_attempted = True
                mc = adapter(t, price=edgar_price_hint)
            else:
                mc = adapter(t)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s marketcap adapter raised for %s: %s",
                           adapter.__name__, t, exc)
            continue
        if mc and mc > 0:
            if use_cache:
                _cache_write(t, "marketcap",
                             {"market_cap": mc, "source": adapter.__name__})
            logger.info("fetch_market_cap(%s) <- $%.0f via %s",
                        t, mc, adapter.__name__)
            return float(mc)
    logger.warning("fetch_market_cap(%s): ALL %d sources failed",
                   t, len(_MARKETCAP_CHAIN))
    return None


# ---------------------------------------------------------------------------
# Batch fetching — parallel + per-run circuit breaker for GHA budget safety
# ---------------------------------------------------------------------------
# Default ThreadPoolExecutor worker count. Conservative — 8 keeps us well
# under any single API's per-second rate limit even if all 50 tickers
# happen to take the same path. Tunable via env for emergency throttle.
_BATCH_MAX_WORKERS = int(os.environ.get("EQUITY_FAILOVER_MAX_WORKERS", 8))

# Per-run failure budget: if this many tickers in a row return None from
# every source, abort the rest of the batch. Prevents the 7-adapter ×
# 50-ticker × 5-second worst case (~30 min) from blowing past GHA's
# 25-min job budget when ALL upstreams are down. Tunable via env for
# debugging; set to 0 to disable.
_BATCH_FAILURE_BUDGET = int(os.environ.get("EQUITY_FAILOVER_FAILURE_BUDGET", 10))


def _parallel_fetch(tickers: list[str],
                    fetcher: Callable[[str], object],
                    *,
                    max_workers: Optional[int] = None,
                    failure_budget: Optional[int] = None) -> dict[str, object]:
    """Run `fetcher(ticker)` in parallel with a circuit breaker.

    Submits tickers in windows of `max_workers` so the consecutive-failure
    breaker can trip BEFORE every ticker is in flight. Without windowing,
    submitting all 50 tickers up front would race the breaker check and
    blow the GHA budget anyway.

    Concurrency rationale: each fetch is I/O-bound (urllib HTTP). The GIL
    is released during socket I/O so threading is the right primitive
    here — no need for asyncio or processes. Stdlib only per project
    constraint.
    """
    if not tickers:
        return {}
    workers = max_workers if max_workers is not None else _BATCH_MAX_WORKERS
    workers = max(1, min(workers, len(tickers)))
    budget = failure_budget if failure_budget is not None else _BATCH_FAILURE_BUDGET
    results: dict[str, object] = {}
    consecutive_failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        # Process in windows of `workers` size. Each window is fully fanned out
        # in parallel, then we wait for all results, update the breaker counter,
        # and decide whether to start the next window. This caps the worst-case
        # over-fetch at exactly one window past the breaker trip — far better
        # than fanning out everything up front.
        i = 0
        while i < len(tickers):
            window = tickers[i:i + workers]
            futures: dict[concurrent.futures.Future, str] = {
                ex.submit(fetcher, t): t for t in window
            }
            # Collect window results
            window_results: dict[str, object] = {}
            for fut in concurrent.futures.as_completed(futures):
                t = futures[fut]
                try:
                    window_results[t] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("parallel fetch raised for %s: %s", t, exc)
                    window_results[t] = None
            # Apply results in original order so the breaker counter is
            # deterministic across runs.
            window_aborted = False
            for t in window:
                results[t] = window_results.get(t)
                if results[t] is None:
                    consecutive_failures += 1
                    if budget > 0 and consecutive_failures >= budget and not window_aborted:
                        logger.error(
                            "circuit-breaker tripped: %d consecutive failures "
                            "(budget=%d) — aborting remaining tickers",
                            consecutive_failures, budget,
                        )
                        window_aborted = True
                else:
                    consecutive_failures = 0
            if window_aborted:
                # Mark all remaining (unsubmitted) tickers as None and stop
                for t in tickers[i + len(window):]:
                    results[t] = None
                break
            i += len(window)
    return results


def fetch_quotes_batch(tickers: list[str], *,
                       use_cache: bool = True,
                       max_workers: Optional[int] = None,
                       failure_budget: Optional[int] = None,
                       ) -> dict[str, Optional[dict]]:
    """Fetch quotes for a list of tickers in parallel.

    Uses `concurrent.futures.ThreadPoolExecutor` (stdlib) to fan out the
    50-ticker universe across `max_workers` threads. A consecutive-failure
    circuit breaker aborts the run if `failure_budget` tickers in a row
    return None — protects the GHA 25-min job budget when all upstreams
    are down.

    Future: when FMP_API_KEY is set, swap to the FMP batch endpoint
    (https://financialmodelingprep.com/api/v3/quote/AAPL,MSFT,...) to cut
    250/day budget consumption. Out of scope for this PR — the dashboard's
    50-ticker baseline universe stays well under all per-source caps.
    """
    raw = _parallel_fetch(
        tickers or [],
        lambda t: fetch_quote(t, use_cache=use_cache),
        max_workers=max_workers,
        failure_budget=failure_budget,
    )
    # raw values are dict | None; cast for the typed return
    return {t: (v if isinstance(v, dict) else None) for t, v in raw.items()}


def fetch_market_caps_batch(tickers: list[str], *,
                            use_cache: bool = True,
                            max_workers: Optional[int] = None,
                            failure_budget: Optional[int] = None,
                            ) -> dict[str, Optional[float]]:
    """Bulk market-cap fetch in parallel with circuit breaker."""
    raw = _parallel_fetch(
        tickers or [],
        lambda t: fetch_market_cap(t, use_cache=use_cache),
        max_workers=max_workers,
        failure_budget=failure_budget,
    )
    return {t: (float(v) if isinstance(v, (int, float)) and v else None)
            for t, v in raw.items()}


# ---------------------------------------------------------------------------
# Adapters registered for `value_screener_runner` injection
# ---------------------------------------------------------------------------
def fetch_prices_default(tickers: list[str]) -> dict[str, Optional[float]]:
    """Drop-in replacement for `value_screener_runner.fetch_prices_via_yfinance`.

    Returns {ticker: price | None}. Caller loops over results — exactly the
    same shape as the legacy yfinance helper.
    """
    out: dict[str, Optional[float]] = {}
    for t in tickers or []:
        q = fetch_quote(t)
        out[t] = q["price"] if q and q.get("price") else None
    return out


def fetch_market_caps_default(tickers: list[str]) -> dict[str, Optional[float]]:
    """Drop-in replacement for `value_screener_runner.fetch_market_caps_via_yfinance`."""
    return fetch_market_caps_batch(tickers)


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    syms = sys.argv[1:] or ["AAPL", "MSFT", "GOOGL"]
    print(f"Quote chain has {len(_QUOTE_CHAIN)} adapters; "
          f"market-cap chain has {len(_MARKETCAP_CHAIN)} adapters.")
    for s in syms:
        q = fetch_quote(s)
        mc = fetch_market_cap(s)
        print(f"  {s}: quote={q} mc={mc}")
