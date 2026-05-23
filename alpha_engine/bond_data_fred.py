"""
BOND Asset-Class Data — FRED Integration
=========================================
Fills the BOND data desert (n=12 resolved trades) by pulling Treasury yields,
yield-curve spreads, TIPS breakevens, and credit spreads from the St. Louis
Fed (FRED) API.

Primary backend:
    fredapi.Fred(api_key=$FRED_API_KEY)

Fallback (no key required, rate-limited):
    pandas_datareader.data.DataReader(series, 'fred', start, end)

Results are cached to disk under alpha_engine/data/fred_cache/ to avoid
re-hitting the API. Cache TTL defaults to 24h; override via `max_age_hours`.

Curated BOND series (see FRED_SERIES dict below):
    DGS2, DGS10, DGS30      — 2/10/30Y Treasury par yields
    T10Y2Y, T10Y3M          — yield-curve spreads (recession signals)
    T10YIE, T5YIE, T5YIFR   — 10Y/5Y/5y5y forward inflation breakevens
    BAMLH0A0HYM2            — ICE BofA US HY option-adjusted spread
    BAMLC0A0CM              — ICE BofA US IG corporate OAS

Usage:
    from alpha_engine.bond_data_fred import fetch_fred_series
    df = fetch_fred_series("DGS10", "2025-04-20", "2026-04-20")

    # Or the bulk helper for strategy research:
    from alpha_engine.bond_data_fred import fetch_bond_bundle
    bundle = fetch_bond_bundle(lookback_days=365)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Curated BOND FRED series
# -----------------------------------------------------------------------------
FRED_SERIES: dict[str, dict] = {
    # Treasury par yields (daily, %)
    "DGS2":          {"desc": "2-Year Treasury Constant Maturity Yield",  "unit": "pct"},
    "DGS10":         {"desc": "10-Year Treasury Constant Maturity Yield", "unit": "pct"},
    "DGS30":         {"desc": "30-Year Treasury Constant Maturity Yield", "unit": "pct"},
    # Yield-curve spreads (daily, pp)
    "T10Y2Y":        {"desc": "10Y - 2Y Treasury Spread",  "unit": "pp"},
    "T10Y3M":        {"desc": "10Y - 3M Treasury Spread",  "unit": "pp"},
    # Inflation breakevens (daily, %)
    "T10YIE":        {"desc": "10Y Breakeven Inflation",    "unit": "pct"},
    "T5YIE":         {"desc": "5Y Breakeven Inflation",     "unit": "pct"},
    "T5YIFR":        {"desc": "5y5y Forward Breakeven",     "unit": "pct"},
    # Credit spreads (daily, pp)
    "BAMLH0A0HYM2":  {"desc": "ICE BofA US HY OAS",         "unit": "pp"},
    "BAMLC0A0CM":    {"desc": "ICE BofA US IG Corp OAS",    "unit": "pp"},
}

# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
_MODULE_DIR = Path(__file__).resolve().parent
CACHE_DIR = _MODULE_DIR / "data" / "fred_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MAX_AGE_HOURS = 24


def _cache_path(series_id: str, start: str, end: str) -> Path:
    key = hashlib.md5(f"{series_id}|{start}|{end}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{series_id}_{key}.json"


def _cache_read(path: Path, max_age_hours: float) -> Optional[list]:
    if not path.exists():
        return None
    age_h = (time.time() - path.stat().st_mtime) / 3600
    if age_h > max_age_hours:
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _cache_write(path: Path, rows: list) -> None:
    try:
        path.write_text(json.dumps(rows))
    except Exception as e:
        logger.warning("cache write failed for %s: %s", path.name, e)


# -----------------------------------------------------------------------------
# Backends
# -----------------------------------------------------------------------------
def _call_with_timeout(fn, args, timeout_s: float):
    """Run ``fn(*args)`` with a hard wall-clock timeout (cross-platform).

    A daemon worker thread + ``join(timeout)`` so a hung FRED backend cannot
    block a CI run for minutes — alpha-engine-bond.yml documents a past 10-min
    FRED stall that got FRED disabled entirely. ``signal.alarm`` is Unix-only
    and unusable on the Windows dev box, hence the thread approach. The
    orphaned thread is daemonized so it cannot keep the process alive.
    """
    import threading

    box: dict = {}

    def _worker() -> None:
        try:
            box["value"] = fn(*args)
        except Exception as e:  # noqa: BLE001 — re-raised on the caller thread
            box["error"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        raise TimeoutError(f"FRED backend exceeded {timeout_s:.0f}s timeout")
    if "error" in box:
        raise box["error"]
    return box.get("value", [])


def _fetch_via_fredapi(series_id: str, start: str, end: str) -> list[dict]:
    from fredapi import Fred
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set")
    fred = Fred(api_key=api_key)
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    rows = []
    for date, val in s.items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        rows.append({"date": date.strftime("%Y-%m-%d"), "value": v})
    return rows


def _fetch_via_pdr(series_id: str, start: str, end: str) -> list[dict]:
    """Fallback: pandas_datareader (no API key required, rate-limited).

    pandas_datareader 0.10.0 is incompatible with pandas >= 3.0 because
    pandas tightened `deprecate_kwarg` argument validation. We monkeypatch
    it to a passthrough decorator before importing pandas_datareader.
    """
    import sys
    import pandas.util._decorators as _pdd
    if not getattr(_pdd, "_bondfred_patched", False):
        def _passthrough(old_arg_name, new_arg_name=None,
                         mapping=None, stacklevel=2):
            def decorator(func):
                return func
            return decorator
        _pdd.deprecate_kwarg = _passthrough
        _pdd._bondfred_patched = True
        for k in list(sys.modules):
            if k.startswith("pandas_datareader"):
                del sys.modules[k]
    from pandas_datareader import data as pdr
    df = pdr.DataReader(series_id, "fred", start, end)
    rows = []
    col = df.columns[0]
    for idx, val in df[col].items():
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if v != v:
            continue
        rows.append({"date": idx.strftime("%Y-%m-%d"), "value": v})
    return rows


def _fetch_via_fred_json(series_id: str, start: str, end: str) -> list[dict]:
    """Direct FRED JSON API (api.stlouisfed.org/fred/series/observations).

    Uses FRED_API_KEY from env. This is the fastest, most reliable backend;
    added 2026-05-18 because fredapi/pandas_datareader are not always installed
    and fredgraph_csv times out on Windows hosts.
    """
    import urllib.request as _urlreq
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set")
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
        f"&observation_start={start}&observation_end={end}&sort_order=asc"
    )
    req = _urlreq.Request(url, headers={"User-Agent": "bond_data_fred/1.0"})
    with _urlreq.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    rows = []
    for obs in data.get("observations", []):
        val_str = obs.get("value", "")
        if val_str in (".", "", "NA"):
            continue
        try:
            rows.append({"date": obs["date"], "value": float(val_str)})
        except (ValueError, KeyError):
            continue
    return rows


def _fetch_via_fredgraph_csv(series_id: str, start: str, end: str) -> list[dict]:
    """Last-resort fallback: public fredgraph.csv endpoint (no key required).

    This is the same endpoint fred.stlouisfed.org/graph uses for CSV export.
    """
    import csv
    import io
    import urllib.request

    url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv"
           f"?id={series_id}&cosd={start}&coed={end}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return []
    # Header is either ["DATE", series_id] or ["observation_date", series_id]
    rows = []
    for row in reader:
        if len(row) < 2:
            continue
        date_str, val_str = row[0], row[1]
        if val_str in (".", "", "NA"):
            continue
        try:
            v = float(val_str)
        except ValueError:
            continue
        rows.append({"date": date_str, "value": v})
    return rows


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def fetch_fred_series(
    series_id: str,
    start: str,
    end: str,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    use_cache: bool = True,
) -> list[dict]:
    """Fetch a FRED series as a list of {'date','value'} dicts.

    Args:
        series_id: FRED series code (e.g., "DGS10")
        start, end: ISO dates "YYYY-MM-DD"
        max_age_hours: cache TTL
        use_cache: set False to force a fresh pull

    Returns:
        list of {"date": "YYYY-MM-DD", "value": float}, asc by date
    """
    # 2026-05-14: SKIP_FRED env var to bypass FRED API in headless/GitHub Actions runs.
    if os.environ.get("SKIP_FRED", "0") == "1":
        logger.debug("[bond_data_fred] SKIP_FRED=1 - skipping fetch for %s", series_id)
        return []
    cache_file = _cache_path(series_id, start, end)
    if use_cache:
        cached = _cache_read(cache_file, max_age_hours)
        if cached is not None:
            logger.debug("cache hit %s [%s..%s]", series_id, start, end)
            return cached

    # Per-backend hard timeout. fredapi / pandas_datareader have no native
    # timeout — without this a stalled backend blocks the whole CI run (the
    # 10-min stall documented in alpha-engine-bond.yml). Override via
    # FRED_FETCH_TIMEOUT_S; default 30s (FRED normally responds in <2s).
    try:
        _fred_timeout = float(os.environ.get("FRED_FETCH_TIMEOUT_S", "30") or 30)
    except (TypeError, ValueError):
        _fred_timeout = 30.0

    last_err: Optional[Exception] = None
    for backend_name, backend in (("fred_json", _fetch_via_fred_json),
                                   ("fredapi", _fetch_via_fredapi),
                                   ("pandas_datareader", _fetch_via_pdr),
                                   ("fredgraph_csv", _fetch_via_fredgraph_csv)):
        try:
            rows = _call_with_timeout(
                backend, (series_id, start, end), _fred_timeout)
            if rows:
                logger.info("fetched %s via %s (%d rows)",
                            series_id, backend_name, len(rows))
                _cache_write(cache_file, rows)
                return rows
        except Exception as e:
            last_err = e
            logger.info("%s failed for %s: %s", backend_name, series_id, e)
            continue

    logger.error("all FRED backends failed for %s: %s", series_id, last_err)
    return []


def fetch_bond_bundle(lookback_days: int = 365,
                      series: Optional[list[str]] = None) -> dict[str, list[dict]]:
    """Pull the full curated BOND series bundle for the last N days."""
    if os.environ.get("SKIP_FRED", "0").strip() == "1":
        return {sid: [] for sid in (series or list(FRED_SERIES.keys()))}
    end = datetime.utcnow().date()
    start = end - timedelta(days=lookback_days)
    ids = series or list(FRED_SERIES.keys())
    out = {}
    for sid in ids:
        out[sid] = fetch_fred_series(sid, start.isoformat(), end.isoformat())
    return out


def summary_stats(rows: list[dict]) -> dict:
    """Compute min/max/median, recent, and 12m-ago comparison."""
    if not rows:
        return {"n": 0}
    vals = [r["value"] for r in rows]
    vals_sorted = sorted(vals)
    n = len(vals)
    median = (vals_sorted[n // 2] if n % 2
              else (vals_sorted[n // 2 - 1] + vals_sorted[n // 2]) / 2)
    latest = rows[-1]
    earliest = rows[0]
    return {
        "n": n,
        "start_date": earliest["date"],
        "end_date": latest["date"],
        "min": min(vals),
        "max": max(vals),
        "median": median,
        "mean": sum(vals) / n,
        "latest_value": latest["value"],
        "latest_date": latest["date"],
        "earliest_value": earliest["value"],
        "earliest_date": earliest["date"],
        "change_abs": latest["value"] - earliest["value"],
        "change_pct": ((latest["value"] - earliest["value"]) / earliest["value"] * 100
                       if earliest["value"] else None),
    }


# -----------------------------------------------------------------------------
# Self-demo
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for sid in ("DGS10", "T10Y2Y"):
        rows = fetch_fred_series(
            sid,
            (datetime.utcnow().date() - timedelta(days=365)).isoformat(),
            datetime.utcnow().date().isoformat(),
        )
        print(f"\n{sid} ({FRED_SERIES[sid]['desc']})")
        print(json.dumps(summary_stats(rows), indent=2, default=str))
