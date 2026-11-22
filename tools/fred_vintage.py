"""ALFRED / FRED point-in-time vintage fetch (P0.8, 2026-11-20).

Macro features joined on the *observation* date use data that did not exist
then — revisions leak future information. Joining on the *vintage* date fixes
it. This tool fetches the observations as they stood on a given date.

Usage:
  python3 tools/fred_vintage.py CPIAUCSL --as-of 2026-01-15
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

API = "https://api.stlouisfed.org/fred/series/observations"
CACHE_DIR = Path("data/fred_vintages")


def _http_get(url: str) -> str:      # injectable for tests
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode()


def fetch_vintage(series_id: str, as_of: str, api_key: str | None = None,
                  fetch=_http_get, cache_dir: str | os.PathLike | None = None) -> dict:
    key = api_key or os.environ.get("FRED_API_KEY", "")
    if not key:
        raise RuntimeError("FRED_API_KEY not set")
    cache = Path(cache_dir or CACHE_DIR) / f"{series_id}_{as_of}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    url = (f"{API}?series_id={series_id}&api_key={key}&file_type=json"
           f"&realtime_start={as_of}&realtime_end={as_of}")
    payload = json.loads(fetch(url))
    obs = [{"date": o.get("date"), "value": o.get("value")}
           for o in payload.get("observations", [])]
    out = {"series_id": series_id, "as_of": as_of,
           "vintage": payload.get("realtime_start"), "n": len(obs),
           "observations": obs}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("series_id")
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()
    out = fetch_vintage(args.series_id, args.as_of)
    print(json.dumps({k: v for k, v in out.items() if k != "observations"}, indent=1))


if __name__ == "__main__":
    main()
