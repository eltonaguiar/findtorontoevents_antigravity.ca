"""FRED macro data fetcher (pandas-DataFrame API) — opt-in BOND-class sidecar.

Wraps :class:`fredapi.Fred` for the four bond/macro inputs the BOND-team
top-1 ship (LQD-HYG credit-spread mean reversion) needs:

- :func:`get_treasury_curve` — DGS{1MO..30Y} par yields as a DataFrame
- :func:`get_credit_spread`  — HY OAS - IG OAS (default), HY, or IG
- :func:`get_term_premium`   — 10Y - 2Y Treasury (T10Y2Y series)
- :func:`get_breakeven_inflation` — 10Y nominal - TIPS (T10YIE series)

Caching: parquet under ``alpha_engine/data/fred_cache/`` keyed by
``(series_id, start, end)``, default 24h TTL.

Env: requires ``FRED_API_KEY`` (free at
https://fred.stlouisfed.org/docs/api/api_key.html). Public methods raise
:class:`MissingFredApiKey` when unset.

Opt-in sidecar per CLAUDE.md Wire-Up Rule. No production scoring path
imports this yet; follow-up PR wires it into ``bond-agent.yml`` + a new
``bond_credit_spread.py`` strategy.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

_MODULE_DIR = Path(__file__).resolve().parent
CACHE_DIR = _MODULE_DIR / "data" / "fred_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CACHE_TTL_HOURS = 24.0

# 11-point Treasury constant-maturity curve (short -> long).
TREASURY_CURVE_SERIES: dict[str, float] = {
    "DGS1MO": 1 / 12, "DGS3MO": 0.25, "DGS6MO": 0.5,
    "DGS1": 1.0, "DGS2": 2.0, "DGS3": 3.0, "DGS5": 5.0,
    "DGS7": 7.0, "DGS10": 10.0, "DGS20": 20.0, "DGS30": 30.0,
}

CREDIT_SPREAD_SERIES: dict[str, tuple[str, ...]] = {
    "HYG_LQD": ("BAMLH0A0HYM2", "BAMLC0A0CM"),  # HY OAS - IG OAS
    "HY":      ("BAMLH0A0HYM2",),
    "IG":      ("BAMLC0A0CM",),
}


class MissingFredApiKey(RuntimeError):
    """Raised when ``FRED_API_KEY`` is not set in the environment."""


class FredDependencyMissing(RuntimeError):
    """Raised when an optional dep (fredapi/pyarrow) is missing."""


def _require_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError as e:  # pragma: no cover
        raise FredDependencyMissing("pandas required; pip install pandas") from e


def _build_fred_client():
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise MissingFredApiKey(
            "set FRED_API_KEY env var; free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    try:
        from fredapi import Fred
    except ImportError as e:
        raise FredDependencyMissing(
            "fredapi not installed; pip install -r requirements-bond-data.txt"
        ) from e
    return Fred(api_key=api_key)


def _normalize_dates(date_from, date_to) -> tuple[str, str]:
    if isinstance(date_from, (date, datetime)):
        date_from = date_from.strftime("%Y-%m-%d")
    if date_to is None:
        date_to = datetime.utcnow().date().strftime("%Y-%m-%d")
    elif isinstance(date_to, (date, datetime)):
        date_to = date_to.strftime("%Y-%m-%d")
    return str(date_from), str(date_to)


def _cache_path(series_id: str, start: str, end: str) -> Path:
    key = hashlib.md5(f"{series_id}|{start}|{end}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{series_id}_{key}.parquet"


def _cache_read(path: Path, ttl_hours: float):
    # Also check the pickle fallback path written when pyarrow is unavailable.
    pkl_path = path.with_suffix(".pkl")
    # Prefer .parquet; fall back to .pkl if the parquet file doesn't exist.
    read_path = path if path.exists() else (pkl_path if pkl_path.exists() else None)
    if read_path is None:
        return None
    age_h = (datetime.utcnow().timestamp() - read_path.stat().st_mtime) / 3600
    if age_h > ttl_hours:
        return None
    try:
        if read_path.suffix == ".pkl":
            import pickle
            with read_path.open("rb") as f:
                return pickle.load(f)
        return _require_pandas().read_parquet(read_path)
    except Exception as e:  # pragma: no cover
        logger.warning("fred cache read failed for %s: %s", read_path.name, e)
        return None


def _cache_write(path: Path, df) -> None:
    try:
        df.to_parquet(path)
    except Exception as e:
        # Fall back to pickle if pyarrow unavailable.
        try:
            import pickle
            with path.with_suffix(".pkl").open("wb") as f:
                pickle.dump(df, f)
        except Exception:
            logger.warning("fred cache write failed for %s: %s", path.name, e)


def _fetch_series(series_id, start, end, ttl_hours, use_cache):
    pd = _require_pandas()
    cache_file = _cache_path(series_id, start, end)
    if use_cache:
        cached = _cache_read(cache_file, ttl_hours)
        if cached is not None:
            return cached.iloc[:, 0]
    fred = _build_fred_client()
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    s.name = series_id
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index = pd.to_datetime(s.index)
    _cache_write(cache_file, s.to_frame())
    return s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_treasury_curve(
    date_from: Union[str, date, datetime],
    date_to: Optional[Union[str, date, datetime]] = None,
    *,
    use_cache: bool = True,
    ttl_hours: float = DEFAULT_CACHE_TTL_HOURS,
):
    """Fetch the 11-point Treasury par-yield curve as a DataFrame.

    Returns a DataFrame indexed by date with columns
    ``DGS1MO, DGS3MO, ..., DGS30`` (% par yield, NaN where missing).
    """
    pd = _require_pandas()
    start, end = _normalize_dates(date_from, date_to)
    series = {}
    for sid in TREASURY_CURVE_SERIES:
        try:
            series[sid] = _fetch_series(sid, start, end, ttl_hours, use_cache)
        except (MissingFredApiKey, FredDependencyMissing):
            raise
        except Exception as e:  # noqa: BLE001
            logger.warning("get_treasury_curve: %s failed: %s", sid, e)
    if not series:
        return pd.DataFrame()
    return pd.concat(series, axis=1).sort_index().reindex(
        columns=list(TREASURY_CURVE_SERIES.keys())
    )


def get_credit_spread(
    grade: str = "HYG_LQD",
    date_from: Optional[Union[str, date, datetime]] = None,
    date_to: Optional[Union[str, date, datetime]] = None,
    *,
    use_cache: bool = True,
    ttl_hours: float = DEFAULT_CACHE_TTL_HOURS,
):
    """Return a credit-spread series.

    ``grade`` ∈ ``{"HYG_LQD", "HY", "IG"}``. ``HYG_LQD`` (default) =
    HY OAS minus IG OAS, the headline mean-reversion signal. ``date_from``
    defaults to 2 years ago.
    """
    if grade not in CREDIT_SPREAD_SERIES:
        raise ValueError(
            f"unknown grade {grade!r}; choose from {sorted(CREDIT_SPREAD_SERIES)}"
        )
    if date_from is None:
        date_from = datetime.utcnow().date() - timedelta(days=730)
    start, end = _normalize_dates(date_from, date_to)
    sids = CREDIT_SPREAD_SERIES[grade]
    parts = [_fetch_series(s, start, end, ttl_hours, use_cache) for s in sids]
    if grade == "HYG_LQD":
        spread = (parts[0] - parts[1]).dropna()
        spread.name = "HYG_LQD_spread"
        return spread
    out = parts[0]
    out.name = f"{grade}_OAS"
    return out


def get_term_premium(
    date_from: Optional[Union[str, date, datetime]] = None,
    date_to: Optional[Union[str, date, datetime]] = None,
    *,
    use_cache: bool = True,
    ttl_hours: float = DEFAULT_CACHE_TTL_HOURS,
):
    """Return the 10Y - 2Y Treasury spread (FRED ``T10Y2Y``).

    Negative readings have historically led recessions by 6-18 months.
    """
    if date_from is None:
        date_from = datetime.utcnow().date() - timedelta(days=730)
    start, end = _normalize_dates(date_from, date_to)
    s = _fetch_series("T10Y2Y", start, end, ttl_hours, use_cache)
    s.name = "term_premium_10y2y"
    return s


def get_breakeven_inflation(
    date_from: Optional[Union[str, date, datetime]] = None,
    date_to: Optional[Union[str, date, datetime]] = None,
    *,
    use_cache: bool = True,
    ttl_hours: float = DEFAULT_CACHE_TTL_HOURS,
):
    """Return 10Y breakeven inflation (FRED ``T10YIE`` = nominal - TIPS)."""
    if date_from is None:
        date_from = datetime.utcnow().date() - timedelta(days=730)
    start, end = _normalize_dates(date_from, date_to)
    s = _fetch_series("T10YIE", start, end, ttl_hours, use_cache)
    s.name = "breakeven_inflation_10y"
    return s
