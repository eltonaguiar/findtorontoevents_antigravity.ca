'''coinglass_integration.py
Utility module to fetch and parse Coinglass Long/Short Ratio data.

The Coinglass public endpoint provides a JSON payload with the current
Long‑Short Ratio for a wide set of crypto symbols.  We only need the
ratio for the symbols we trade, so the helper function extracts the
value for a given symbol and returns it as a float.

If the request fails or the symbol is not present, ``None`` is returned.
'''

import json
import logging
from pathlib import Path
from typing import Optional

import requests

# Coinglass public API endpoint (no API key required for the public view)
COINGLASS_URL = "https://api.coinglass.com/api/v2/longShortRatio"

# Cache the response on disk to avoid hammering the endpoint during back‑tests.
CACHE_PATH = Path(".cache/coinglass_longshort.json")
CACHE_TTL_SECONDS = 300  # 5 minutes


def _load_cache() -> Optional[dict]:
    """Load cached JSON if it is still fresh.

    Returns ``None`` when the cache does not exist or is stale.
    """
    if not CACHE_PATH.is_file():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text())
        ts = data.get("_cached_at", 0)
        if (int(__import__("time").time()) - ts) < CACHE_TTL_SECONDS:
            return data.get("payload")
    except Exception as exc:
        logging.debug("Failed to read Coinglass cache: %s", exc)
    return None


def _save_cache(payload: dict) -> None:
    """Write payload to cache with a timestamp.
    """
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"_cached_at": int(__import__("time").time()), "payload": payload}))


def fetch_long_short_data() -> Optional[dict]:
    """Fetch the raw long‑short data from Coinglass.

    The function first attempts to use the on‑disk cache.  If the cache is
    stale or missing, it performs a GET request, stores the result and
    returns the parsed JSON payload.
    """
    cached = _load_cache()
    if cached is not None:
        return cached

    try:
        resp = requests.get(COINGLASS_URL, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        # The public endpoint wraps the actual list under ``data``.
        data = payload.get("data") or payload
        _save_cache(data)
        return data
    except Exception as exc:
        logging.error("Coinglass request failed: %s", exc)
        return None


def get_long_short_ratio(symbol: str) -> Optional[float]:
    """Return the long‑short ratio for *symbol*.

    The ratio is expressed as ``long / short``.  Values > 1 indicate a net
    long bias, < 1 a net short bias.  The function returns ``None`` when the
    symbol cannot be found.
    """
    data = fetch_long_short_data()
    if not data:
        return None
    # The payload is a list of dicts like ``{"symbol": "BTC", "ratio": 1.73}``
    for entry in data:
        if entry.get("symbol", "").upper() == symbol.upper():
            try:
                return float(entry.get("ratio"))
            except Exception:
                return None
    return None

# ---------------------------------------------------------------------------
# Example usage (run as a script)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    r = get_long_short_ratio(sym)
    print(f"{sym} long‑short ratio = {r}")
