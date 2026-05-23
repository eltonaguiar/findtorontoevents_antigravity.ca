"""Earnings catalyst filter.

Flags equity symbols whose next earnings announcement is within a configurable
window (default 72 hours). Intended as a gate for the HC (high-conviction)
filter so we can avoid opening new positions into an imminent earnings print.

Primary data path
-----------------
OpenBB Platform (``obb.equity.calendar.earnings``) when an FMP / Intrinio /
Benzinga API key is configured. The ``yfinance`` provider is NOT exposed for
that endpoint in OpenBB 4.7.x, so as a **free-tier fallback** this module
calls ``yfinance.Ticker(sym).calendar`` directly — the same underlying feed
OpenBB's ``equity.fundamental.calendar_events`` uses.

Caching
-------
Per-symbol results are cached for 24h in ``alpha_engine/data/catalyst_cache.json``
to keep us well below yfinance's (informal) ~2000 req/hr ceiling.

Failure mode
------------
Any network / parse error is logged at WARNING and the symbol is simply
omitted from the result. The caller receives an empty dict, never an
exception — this module must never crash the pick pipeline.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

_HERE = Path(__file__).resolve().parent
_CACHE_PATH = _HERE / "data" / "catalyst_cache.json"
_CACHE_TTL_SEC = 24 * 3600


# --------------------------------------------------------------------------- #
# Cache helpers
# --------------------------------------------------------------------------- #
def _load_cache() -> dict:
    try:
        if _CACHE_PATH.exists():
            with _CACHE_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("catalyst_cache read failed (%s); starting empty", exc)
    return {}


def _save_cache(cache: dict) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
        os.replace(tmp, _CACHE_PATH)
    except OSError as exc:
        logger.warning("catalyst_cache write failed: %s", exc)


def _cache_get(symbol: str) -> Optional[str]:
    """Return ISO earnings datetime string if cached entry is still fresh."""
    cache = _load_cache()
    entry = cache.get(symbol.upper())
    if not entry:
        return None
    try:
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
    except (KeyError, ValueError):
        return None
    if (datetime.now(timezone.utc) - fetched_at).total_seconds() > _CACHE_TTL_SEC:
        return None
    return entry.get("earnings_dt")  # may be None (negative cache)


def _cache_set(symbol: str, earnings_dt: Optional[datetime]) -> None:
    cache = _load_cache()
    cache[symbol.upper()] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "earnings_dt": earnings_dt.isoformat() if earnings_dt else None,
    }
    _save_cache(cache)


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
def _fetch_openbb(symbol: str) -> Optional[datetime]:
    """Try OpenBB Platform. Requires FMP/Intrinio/Benzinga key to be configured."""
    try:
        from openbb import obb  # type: ignore
    except ImportError:
        return None
    try:
        today = datetime.now(timezone.utc).date()
        end = today + timedelta(days=90)
        # fmp is the only provider OpenBB 4.7.x exposes for the calendar
        resp = obb.equity.calendar.earnings(
            start_date=str(today), end_date=str(end), provider="fmp"
        )
        rows = [r for r in (resp.results or []) if getattr(r, "symbol", None) == symbol.upper()]
        if not rows:
            return None
        rows.sort(key=lambda r: getattr(r, "report_date", None) or getattr(r, "date", None))
        first = rows[0]
        dt = getattr(first, "report_date", None) or getattr(first, "date", None)
        if isinstance(dt, datetime):
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if dt is not None:
            # date-only -> assume 13:30 UTC (~09:30 ET open); conservative for 72h gate
            return datetime(dt.year, dt.month, dt.day, 13, 30, tzinfo=timezone.utc)
    except Exception as exc:  # OpenBBError, auth errors, network, etc.
        logger.warning("OpenBB earnings lookup failed for %s: %s", symbol, exc)
    return None


def _fetch_yfinance(symbol: str) -> Optional[datetime]:
    """Free-tier fallback via yfinance Ticker.calendar."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        logger.warning("yfinance not installed — cannot resolve earnings for %s", symbol)
        return None
    try:
        cal = yf.Ticker(symbol).calendar
        if not cal:
            return None
        ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if not ed:
            return None
        # yfinance returns [date] or [date_lo, date_hi]; take the earliest
        candidates = ed if isinstance(ed, list) else [ed]
        candidates = [c for c in candidates if c is not None]
        if not candidates:
            return None
        earliest = min(candidates)
        if isinstance(earliest, datetime):
            return earliest if earliest.tzinfo else earliest.replace(tzinfo=timezone.utc)
        # datetime.date -> assume 13:30 UTC (pre-market print); conservative for a 72h gate
        return datetime(
            earliest.year, earliest.month, earliest.day, 13, 30, tzinfo=timezone.utc
        )
    except Exception as exc:
        logger.warning("yfinance earnings lookup failed for %s: %s", symbol, exc)
    return None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def get_next_earnings_dt(symbol: str, use_cache: bool = True) -> Optional[datetime]:
    """Return the next scheduled earnings datetime (UTC) for ``symbol``, or None."""
    if not symbol:
        return None
    sym = symbol.upper().strip()

    if use_cache:
        cached = _cache_get(sym)
        if cached is not None:
            try:
                return datetime.fromisoformat(cached)
            except ValueError:
                pass
        elif sym.upper() in _load_cache():
            # Fresh negative cache hit — respect it
            return None

    dt = _fetch_openbb(sym) or _fetch_yfinance(sym)
    _cache_set(sym, dt)
    return dt


def hours_to_earnings(symbol: str) -> Optional[float]:
    """Hours until next earnings print, or None if unknown / in the past."""
    dt = get_next_earnings_dt(symbol)
    if dt is None:
        return None
    delta = (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0
    if delta < 0:
        return None
    return delta


def filter_imminent_earnings(
    symbols: list[str], threshold_hours: float = 72.0
) -> dict[str, float]:
    """Return {symbol: hours_until_earnings} for symbols within the window."""
    out: dict[str, float] = {}
    for sym in symbols or []:
        try:
            hrs = hours_to_earnings(sym)
        except Exception as exc:  # belt-and-suspenders
            logger.warning("catalyst_filter crash guard for %s: %s", sym, exc)
            continue
        if hrs is not None and hrs <= threshold_hours:
            out[sym.upper().strip()] = round(hrs, 2)
    return out


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    test_symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]
    print(f"catalyst_filter smoke test @ {datetime.now(timezone.utc).isoformat()}")
    print("-" * 72)
    for s in test_symbols:
        dt = get_next_earnings_dt(s)
        hrs = hours_to_earnings(s)
        dt_str = dt.isoformat() if dt else "None"
        hrs_str = f"{hrs:8.2f}h" if hrs is not None else "    N/A"
        print(f"  {s:5s}  next_earnings={dt_str:32s}  hours_until={hrs_str}")
    print("-" * 72)
    flagged = filter_imminent_earnings(test_symbols, threshold_hours=72)
    print(f"filter_imminent_earnings(threshold=72h) -> {flagged}")
    flagged_168 = filter_imminent_earnings(test_symbols, threshold_hours=168)
    print(f"filter_imminent_earnings(threshold=168h) -> {flagged_168}")
