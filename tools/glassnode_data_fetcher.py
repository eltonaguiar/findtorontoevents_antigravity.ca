"""
Glassnode REST API client (free tier).

Endpoints (free tier limited to BTC + ETH, daily resolution):
  - /v1/metrics/market/mvrv_z_score           -> MVRV Z-Score
  - /v1/metrics/addresses/active_count        -> Daily active addresses
  - /v1/metrics/distribution/balance_exchanges -> Aggregate exchange balance

Requires env var GLASSNODE_API_KEY (free tier sign-up).
Returns None on missing key / timeout / non-200; never raises.

File cache: tools/.cache/glassnode_<metric>_<asset>.json (6h TTL).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

BASE_URL = "https://api.glassnode.com/v1/metrics"
DEFAULT_TIMEOUT = 8
CACHE_TTL_SECONDS = 6 * 3600
SUPPORTED_ASSETS = {"BTC", "ETH"}

_CACHE_DIR = Path(__file__).resolve().parent / ".cache"


def _cache_path(metric: str, asset: str) -> Path:
    safe = metric.replace("/", "_").strip("_")
    return _CACHE_DIR / f"glassnode_{safe}_{asset.upper()}.json"


def _read_cache(path: Path) -> Optional[list]:
    try:
        if not path.exists():
            return None
        if (time.time() - path.stat().st_mtime) > CACHE_TTL_SECONDS:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(path: Path, data: list) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def _get_api_key() -> Optional[str]:
    key = os.environ.get("GLASSNODE_API_KEY", "").strip()
    return key or None


def _fetch_metric(metric_path: str, asset: str,
                  timeout: int = DEFAULT_TIMEOUT) -> Optional[list[dict]]:
    """Fetch a Glassnode metric series. Returns list of {t, v} or None."""
    asset_u = asset.upper()
    if asset_u not in SUPPORTED_ASSETS:
        return None

    cache_p = _cache_path(metric_path, asset_u)
    cached = _read_cache(cache_p)
    if cached is not None:
        return cached

    api_key = _get_api_key()
    if not api_key:
        return None

    qs = urllib.parse.urlencode({
        "a": asset_u,
        "api_key": api_key,
        "i": "24h",
    })
    url = f"{BASE_URL}/{metric_path.lstrip('/')}?{qs}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "alpha-engine/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            raw = resp.read()
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, list):
                return None
            _write_cache(cache_p, data)
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return None
    except Exception:
        return None


def fetch_mvrv_z(asset: str) -> Optional[list[dict]]:
    """Fetch MVRV Z-Score series. Returns list of {t: unix, v: float} or None."""
    return _fetch_metric("market/mvrv_z_score", asset)


def fetch_active_addresses(asset: str) -> Optional[list[dict]]:
    """Fetch daily active addresses series. Returns list of {t, v} or None."""
    return _fetch_metric("addresses/active_count", asset)


def fetch_exchange_balance(asset: str) -> Optional[list[dict]]:
    """Fetch aggregate exchange balance series. Returns list of {t, v} or None."""
    return _fetch_metric("distribution/balance_exchanges", asset)


def latest_value(series: Optional[list[dict]]) -> Optional[float]:
    """Return v of the last datapoint, or None."""
    if not series:
        return None
    try:
        last = series[-1]
        v = last.get("v")
        if v is None:
            return None
        return float(v)
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def trend_30d(series: Optional[list[dict]]) -> Optional[float]:
    """Return (last - mean_first_15_of_last_30) / mean over last ~30 datapoints.
    Positive value => rising trend over the 30-day window. None on insufficient data."""
    if not series or len(series) < 30:
        return None
    try:
        window = series[-30:]
        vals = [float(d["v"]) for d in window if d.get("v") is not None]
        if len(vals) < 30:
            return None
        baseline = sum(vals[:15]) / 15.0
        recent = sum(vals[-15:]) / 15.0
        if baseline == 0:
            return None
        return (recent - baseline) / abs(baseline)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
