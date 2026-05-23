#!/usr/bin/env python3
"""
USDA NASS QuickStats Fetcher (free, public endpoints)
=====================================================
Fetch planting/harvest progress + inventory for major US crops.

Refs:
  - reports/edge_research_synthesis_2026_05_12.md (top-1 candidate: COMMODITY Seasonal)
  - reports/asset_class_research_COMMODITY_2026_05_12_0438Z.md (Grok pick)

API: https://quickstats.nass.usda.gov/api
Public endpoint works with api_key=NONE / api_key omitted on /api/get_counts/
and on /api/api_GET/ when key supplied. For free public use we accept the
documented `api_key=NONE` placeholder and degrade gracefully on failure.

Read-only ingest. Cache to data/usda/<crop>_<report>_<date>.json.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

NASS_BASE = "https://quickstats.nass.usda.gov/api/api_GET/"
TIMEOUT_S = 60

SUPPORTED_CROPS = {"CORN", "WHEAT", "SOYBEANS", "COTTON"}

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "usda"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(crop: str, report: str) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return CACHE_DIR / f"{crop.upper()}_{report}_{today}.json"


def _load_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        LOG.warning("usda cache read failed %s: %s", path, e)
        return None


def _save_cache(path: Path, payload: dict) -> None:
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as e:
        LOG.warning("usda cache write failed %s: %s", path, e)


def _query(params: dict[str, str]) -> dict[str, Any]:
    """Hit NASS QuickStats. Returns {} on any failure."""
    api_key = os.environ.get("USDA_NASS_API_KEY", "NONE")
    q = dict(params)
    q["key"] = api_key
    q["format"] = "JSON"
    url = NASS_BASE + "?" + urllib.parse.urlencode(q)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except Exception as e:  # noqa: BLE001 - graceful degrade
        LOG.warning("usda query failed (%s): %s", params.get("commodity_desc"), e)
        return {}


def _fetch_report(crop: str, statisticcat: str, short_desc_substr: str) -> dict:
    crop = crop.upper()
    if crop not in SUPPORTED_CROPS:
        LOG.warning("usda unsupported crop: %s", crop)
        return {}
    cache = _cache_path(crop, statisticcat.lower())
    cached = _load_cache(cache)
    if cached is not None:
        return cached
    year = datetime.now(timezone.utc).year
    params = {
        "commodity_desc": crop,
        "statisticcat_desc": statisticcat,
        "year__GE": str(year - 1),
        "agg_level_desc": "NATIONAL",
    }
    raw = _query(params)
    rows = raw.get("data", []) if isinstance(raw, dict) else []
    filtered = [
        r for r in rows
        if isinstance(r, dict) and short_desc_substr.lower() in str(r.get("short_desc", "")).lower()
    ]
    payload = {
        "crop": crop,
        "report": statisticcat,
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(filtered),
        "rows": filtered[:200],
    }
    _save_cache(cache, payload)
    return payload


def fetch_planting_progress(crop: str) -> dict:
    """Weekly planting progress (% planted)."""
    return _fetch_report(crop, "PROGRESS", "PCT PLANTED")


def fetch_harvest_progress(crop: str) -> dict:
    """Weekly harvest progress (% harvested)."""
    return _fetch_report(crop, "PROGRESS", "PCT HARVESTED")


def fetch_inventory(crop: str) -> dict:
    """Quarterly stocks / ending inventory."""
    return _fetch_report(crop, "STOCKS", "STOCKS")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for c in ("CORN", "WHEAT"):
        p = fetch_planting_progress(c)
        print(c, "planting rows:", p.get("row_count", 0))
