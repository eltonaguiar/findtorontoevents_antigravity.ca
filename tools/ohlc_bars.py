#!/usr/bin/env python3
"""ohlc_bars.py — daily OHLC bar source for first-touch re-resolution.

Verified 2026-11-22: Binance public klines answer without a key; Stooq returns a
JS proof-of-work challenge page instead of CSV, so it is NOT usable here and
yfinance/Stooq are left out on purpose rather than wired in silently failing.

Cache lives in /tmp so thousands of bar files never enter the repo.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

CACHE = Path("/tmp/ohlc_cache")
CACHE.mkdir(parents=True, exist_ok=True)
BASE = "https://api.binance.com/api/v3/klines"
TTL = 6 * 3600


def _get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ohlc-bars/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def binance_symbol(sym: str) -> str:
    s = re.sub(r"[^A-Za-z]", "", str(sym)).upper()
    if s.endswith("USDT"):
        return s
    if s.endswith("USD"):
        return s + "T"
    return s + "USDT"


def daily_bars(symbol: str, days: int = 600) -> list:
    """[[date, open, high, low, close], ...] oldest first. Raises on failure."""
    key = binance_symbol(symbol)
    path = CACHE / f"{key}.json"
    if path.exists() and time.time() - path.stat().st_mtime < TTL:
        return json.loads(path.read_text())
    out, start = [], int((time.time() - (days + 5) * 86400) * 1000)
    while True:
        chunk = json.loads(_get(f"{BASE}?symbol={key}&interval=1d"
                                f"&startTime={start}&limit=1000"))
        if not chunk:
            break
        for k in chunk:
            out.append([time.strftime("%Y-%m-%d", time.gmtime(k[0] / 1000)),
                        float(k[1]), float(k[2]), float(k[3]), float(k[4])])
        if len(chunk) < 1000:
            break
        start = chunk[-1][0] + 86_400_000
    path.write_text(json.dumps(out))
    return out
