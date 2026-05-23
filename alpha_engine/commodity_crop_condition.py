"""IDEA-A factor: USDA NASS Crop Condition for CT=F (Cotton) picks.

Swarm research 2026-05-19: USDA NASS weekly crop condition data provides
a leading supply-side indicator for cotton. "Good + Excellent" percentage
z-scored vs the 5-year same-week average gives a clean fundamental signal:
  - Crop stress (z < -1.5): supply tightening → bullish CT=F LONG
  - Bumper crop (z > +1.5): supply abundant → bearish for CT=F

Score mapping (crop condition z-score):
  crop_z < -1.5           → 75-90  (bullish: crop stress, supply tightening)
  crop_z  -1.5 to  0      → 55-75  (mild positive)
  crop_z   0   to +1.5    → 40-55  (mild negative)
  crop_z > +1.5           → 10-40  (bearish: bumper crop, supply abundant)

Fail-open: returns 50.0 if no USDA_NASS_API_KEY or any API error.
Cache: alpha_engine/data/usda_crop_condition_cache.json, 7-day TTL (weekly data).

Functions:
  crop_condition_score() -> float     -- 0-100, fail-open 50.0
  stamp_pick(pick: dict) -> dict      -- stamps crop_condition_score ONLY
                                         for symbol == 'CT=F'
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any

_CACHE_PATH = (
    Path(__file__).parent / "data" / "usda_crop_condition_cache.json"
)
_CACHE_TTL_S = 7 * 24 * 3600  # 7 days (weekly data)

# In-process fallback (avoids repeated disk reads in same process)
_in_process_cache: dict[str, Any] = {}


def _read_usda_key() -> str | None:
    """Read USDA_NASS_API_KEY from env, then Windows registry fallback."""
    key = os.environ.get("USDA_NASS_API_KEY")
    if key:
        return key
    try:
        import winreg  # type: ignore[import]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg:
            key, _ = winreg.QueryValueEx(reg, "USDA_NASS_API_KEY")
            return key if key else None
    except Exception:
        return None


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _load_cache() -> dict | None:
    """Load JSON cache from disk. Returns None if missing/stale/corrupt."""
    try:
        cached = _in_process_cache.get("disk")
        if cached:
            age = time.time() - cached.get("fetched_at", 0)
            if age < _CACHE_TTL_S:
                return cached
        if _CACHE_PATH.exists():
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            age = time.time() - data.get("fetched_at", 0)
            if age < _CACHE_TTL_S:
                _in_process_cache["disk"] = data
                return data
    except Exception:
        pass
    return None


def _save_cache(payload: dict) -> None:
    """Persist cache dict to disk. Fail-open."""
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        _in_process_cache["disk"] = payload
    except Exception:
        pass


def _parse_good_excellent(observations: list[dict]) -> list[dict[str, Any]]:
    """Extract weekly Good+Excellent % from USDA NASS response rows.

    USDA NASS condition categories: EXCELLENT, GOOD, FAIR, POOR, VERY POOR.
    We sum GOOD + EXCELLENT per week/year (expressed as %).

    Returns list of {"year": int, "week": int, "ge_pct": float} sorted by
    (year, week) ascending.
    """
    # Aggregate by (year, week)
    agg: dict[tuple[int, int], dict[str, float]] = {}
    for row in observations:
        try:
            year = int(row.get("year", 0))
            week = int(row.get("week_ending", "0")[-2:]) if row.get("week_ending") else 0
            # USDA uses "reference_period_desc" like "WEEK #25"
            ref = row.get("reference_period_desc", "")
            if "WEEK" in ref.upper() and week == 0:
                parts = ref.upper().replace("WEEK", "").replace("#", "").strip().split()
                if parts:
                    try:
                        week = int(parts[0])
                    except ValueError:
                        continue
            if year == 0 or week == 0:
                continue
            cat = (row.get("class_desc") or "").upper()
            val_str = row.get("Value", "")
            if val_str in ("", "(D)", "(Z)"):
                continue
            val = float(val_str.replace(",", ""))
            key = (year, week)
            if key not in agg:
                agg[key] = {"GOOD": 0.0, "EXCELLENT": 0.0}
            if cat in ("GOOD", "EXCELLENT"):
                agg[key][cat] = val
        except Exception:
            continue

    result = []
    for (year, week), cats in sorted(agg.items()):
        ge_pct = cats.get("GOOD", 0.0) + cats.get("EXCELLENT", 0.0)
        result.append({"year": year, "week": week, "ge_pct": ge_pct})
    return result


def _compute_crop_z(rows: list[dict[str, Any]]) -> float | None:
    """Compute z-score of most-recent Good+Excellent% vs 5-year same-week average.

    Returns z-score (float) or None if insufficient data.
    """
    if not rows:
        return None
    latest = rows[-1]
    latest_year = latest["year"]
    latest_week = latest["week"]
    latest_ge = latest["ge_pct"]

    # Gather same-week values from prior 5 years
    same_week_vals = [
        r["ge_pct"]
        for r in rows
        if r["week"] == latest_week and r["year"] < latest_year
    ]
    # Use up to last 5 years
    same_week_vals = same_week_vals[-5:]

    if len(same_week_vals) < 2:
        return None

    mean = sum(same_week_vals) / len(same_week_vals)
    variance = sum((x - mean) ** 2 for x in same_week_vals) / (len(same_week_vals) - 1)
    std = math.sqrt(variance)
    if std < 1e-9:
        return 0.0
    return (latest_ge - mean) / std


def _z_to_score(z: float) -> float:
    """Map crop condition z-score to [0, 100]."""
    if z < -1.5:
        # 75-90: more negative → higher (more bullish)
        capped = max(z, -3.0)
        score = 75.0 + (capped - (-1.5)) / (-3.0 - (-1.5)) * (-15.0)
        # at z=-1.5: score=75; at z=-3.0: score=90
        score = 75.0 + (-capped + 1.5) / 1.5 * 15.0
        return round(min(90.0, max(75.0, score)), 2)
    elif z <= 0.0:
        # 55-75: z=-1.5 → 75, z=0 → 55
        score = 55.0 + (-z) / 1.5 * 20.0
        return round(min(75.0, max(55.0, score)), 2)
    elif z <= 1.5:
        # 40-55: z=0 → 55, z=+1.5 → 40
        score = 55.0 - z / 1.5 * 15.0
        return round(min(55.0, max(40.0, score)), 2)
    else:
        # 10-40: z=+1.5 → 40, cap at z=+3.0 → 10
        capped = min(z, 3.0)
        score = 40.0 - (capped - 1.5) / 1.5 * 30.0
        return round(max(10.0, min(40.0, score)), 2)


def _fetch_usda_crop_data(api_key: str) -> list[dict[str, Any]]:
    """Fetch USDA NASS cotton crop condition data. Returns parsed rows."""
    url = (
        "https://quickstats.nass.usda.gov/api/api_GET/"
        f"?key={api_key}"
        "&commodity_desc=COTTON"
        "&statisticcat_desc=CONDITION"
        "&year__GE=2020"
        "&format=JSON"
    )
    import urllib.request

    with urllib.request.urlopen(url, timeout=15) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    observations = raw.get("data", [])
    return _parse_good_excellent(observations)


def crop_condition_score() -> float:
    """Return USDA Cotton crop condition z-score mapped to [0, 100].

    Fail-open: returns 50.0 if no API key or any fetch/parse error.
    Cached in alpha_engine/data/usda_crop_condition_cache.json (7-day TTL).
    """
    # Check in-process + disk cache first
    cached = _load_cache()
    if cached is not None:
        return _safe_float(cached.get("score"), 50.0)

    api_key = _read_usda_key()
    if not api_key:
        return 50.0

    try:
        rows = _fetch_usda_crop_data(api_key)
        z = _compute_crop_z(rows)
        if z is None:
            score = 50.0
        else:
            score = _z_to_score(z)

        payload = {
            "fetched_at": time.time(),
            "score": score,
            "latest_z": z,
            "row_count": len(rows),
        }
        _save_cache(payload)
        return score
    except Exception:
        return 50.0


def stamp_pick(pick: dict) -> dict:
    """Stamp crop_condition_score on CT=F picks in-place.

    Only applies when pick['symbol'] == 'CT=F'.
    Returns the pick dict for chaining. Fail-open: pick unchanged on error.
    """
    try:
        symbol = str(pick.get("symbol", ""))
        if symbol != "CT=F":
            return pick
        pick["crop_condition_score"] = crop_condition_score()
    except Exception:
        pass
    return pick
