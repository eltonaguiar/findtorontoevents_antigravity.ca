#!/usr/bin/env python3
"""FRED (Federal Reserve Economic Data) client for macro signals.

Per CLAUDE.md Wire-Up Rule: this is OPT-IN sidecar tooling. It powers
``alpha_engine/etf_economic_momentum.py`` (also opt-in, default OFF) and
caches series to ``data/fred_cache/<series_id>.json`` to keep retrieval
cheap and resilient.

Source: ``reports/edge_research_synthesis_2026_05_12.md`` (Grok-4 idea #2:
ETF Economic Momentum, expected PF 1.65, 12h horizon, FRED-driven).

FRED REST API is free. Set ``FRED_API_KEY`` env var (https://fred.stlouisfed.org).
Without a key, ``fetch_series`` returns ``source='missing'`` rather than
raising, so callers can gracefully degrade.

Series of interest:
  GDPC1 - Real Gross Domestic Product (quarterly, billions, chained 2017$)
  USREC - NBER-based Recession Indicator (monthly, 0/1)
  NAPM  - ISM Manufacturing PMI Composite Index (monthly, level)
  M2SL  - M2 Money Stock (monthly, billions)

Public API:
  fetch_series(series_id, observation_start=None) -> dict
  compute_yoy_growth(series_id, *, fetcher=None) -> float | None
  compute_momentum_zscore(series_id, lookback_days=365, *, fetcher=None) -> float | None
"""
from __future__ import annotations

import json
import logging
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError

logger = logging.getLogger("fred_data_fetcher")

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_DIR = _REPO_ROOT / "data" / "fred_cache"

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_OBSERVATION_START = "2000-01-01"
CACHE_TTL_SECONDS = 6 * 3600  # 6h — FRED updates monthly/quarterly anyway

SUPPORTED_SERIES = ("GDPC1", "USREC", "NAPM", "M2SL")


def _api_key() -> str | None:
    key = os.environ.get("FRED_API_KEY", "").strip()
    return key or None


def _ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def _cache_path(series_id: str, cache_dir: Path | None = None) -> Path:
    base = cache_dir or DEFAULT_CACHE_DIR
    return base / f"{series_id}.json"


def _read_cache(series_id: str, cache_dir: Path | None = None) -> dict[str, Any] | None:
    path = _cache_path(series_id, cache_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ts = data.get("fetched_at")
    if not ts:
        return data
    try:
        fetched = datetime.fromisoformat(str(ts))
    except ValueError:
        return data
    age = (datetime.now(timezone.utc) - fetched).total_seconds()
    if age > CACHE_TTL_SECONDS:
        return None
    return data


def _write_cache(series_id: str, payload: dict[str, Any], cache_dir: Path | None = None) -> None:
    base = cache_dir or DEFAULT_CACHE_DIR
    _ensure_cache_dir(base)
    _cache_path(series_id, base).write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )


def _stdlib_http_get(url: str, user_agent: str = "fred_data_fetcher/1.0") -> str:
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_series(
    series_id: str,
    observation_start: str | None = None,
    *,
    http_get: Callable[[str], str] | None = None,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Fetch a FRED series. Returns ``{'series_id', 'observations', 'source', ...}``.

    Network/auth failures surface as ``source='missing'`` with an ``error``
    field — never raise. Observations are dicts ``{'date': str, 'value': float}``.
    """
    if use_cache:
        cached = _read_cache(series_id, cache_dir)
        if cached is not None:
            return cached

    record: dict[str, Any] = {
        "series_id": series_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "observation_start": observation_start or DEFAULT_OBSERVATION_START,
        "source": "missing",
        "observations": [],
    }

    key = _api_key()
    if not key:
        record["error"] = "FRED_API_KEY not set"
        return record

    http_get = http_get or _stdlib_http_get
    url = (
        f"{FRED_BASE_URL}?series_id={series_id}"
        f"&api_key={key}&file_type=json"
        f"&observation_start={record['observation_start']}"
    )

    try:
        body = http_get(url)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    except Exception as exc:  # noqa: BLE001 - graceful degradation
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    try:
        payload = json.loads(body)
    except (TypeError, ValueError) as exc:
        record["error"] = f"json decode failed: {exc}"
        return record

    raw_obs = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(raw_obs, list):
        record["error"] = "FRED response missing observations list"
        return record

    cleaned: list[dict[str, Any]] = []
    for row in raw_obs:
        date = str(row.get("date") or "").strip()
        val_raw = row.get("value")
        if not date or val_raw in (None, "", "."):
            continue
        try:
            val = float(val_raw)
        except (TypeError, ValueError):
            continue
        cleaned.append({"date": date, "value": val})

    record["source"] = "fred_api_v1"
    record["observations"] = cleaned
    if use_cache:
        try:
            _write_cache(series_id, record, cache_dir)
        except OSError as exc:
            logger.warning("FRED cache write failed for %s: %s", series_id, exc)
    return record


def compute_yoy_growth(
    series_id: str,
    *,
    fetcher: Callable[..., dict[str, Any]] | None = None,
) -> float | None:
    """Year-over-year growth (latest value vs ~365d prior). None on missing data."""
    fetcher = fetcher or fetch_series
    record = fetcher(series_id)
    obs = record.get("observations") or []
    if len(obs) < 2:
        return None

    try:
        obs_sorted = sorted(obs, key=lambda r: r["date"])
    except (KeyError, TypeError):
        return None

    latest = obs_sorted[-1]
    try:
        latest_date = datetime.fromisoformat(latest["date"])
    except (KeyError, ValueError):
        return None
    target = latest_date - timedelta(days=365)

    prior = None
    for row in reversed(obs_sorted[:-1]):
        try:
            row_date = datetime.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue
        if row_date <= target:
            prior = row
            break
    if prior is None:
        prior = obs_sorted[0]

    try:
        prev_val = float(prior["value"])
        curr_val = float(latest["value"])
    except (KeyError, TypeError, ValueError):
        return None
    if prev_val == 0:
        return None
    return (curr_val - prev_val) / abs(prev_val)


def compute_momentum_zscore(
    series_id: str,
    lookback_days: int = 365,
    *,
    fetcher: Callable[..., dict[str, Any]] | None = None,
) -> float | None:
    """Z-score of the latest observation vs the prior ``lookback_days`` window.

    None on insufficient data (n<5) or zero-stdev windows.
    """
    fetcher = fetcher or fetch_series
    record = fetcher(series_id)
    obs = record.get("observations") or []
    if len(obs) < 5:
        return None

    try:
        obs_sorted = sorted(obs, key=lambda r: r["date"])
    except (KeyError, TypeError):
        return None

    latest = obs_sorted[-1]
    try:
        latest_val = float(latest["value"])
        latest_date = datetime.fromisoformat(latest["date"])
    except (KeyError, ValueError, TypeError):
        return None

    cutoff = latest_date - timedelta(days=int(lookback_days))
    window: list[float] = []
    for row in obs_sorted[:-1]:
        try:
            d = datetime.fromisoformat(row["date"])
            v = float(row["value"])
        except (KeyError, ValueError, TypeError):
            continue
        if d >= cutoff:
            window.append(v)

    if len(window) < 5:
        return None
    mean = statistics.fmean(window)
    std = statistics.pstdev(window)
    if std <= 0:
        return None
    return (latest_val - mean) / std


if __name__ == "__main__":  # pragma: no cover
    import sys
    sid = sys.argv[1] if len(sys.argv) > 1 else "NAPM"
    rec = fetch_series(sid)
    print(json.dumps({
        "series_id": sid,
        "source": rec.get("source"),
        "n_obs": len(rec.get("observations") or []),
        "error": rec.get("error"),
    }, indent=2))
