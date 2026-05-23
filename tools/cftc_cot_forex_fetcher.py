#!/usr/bin/env python3
"""CFTC COT Financial-Futures (FX) fetcher — sidecar for forex_cot_reversal.

Source: CFTC public Socrata endpoint (Financial Futures: 6dca-aqww).
Optional: Quandl ``CFTC/`` codes if ``QUANDL_API_KEY`` is set (free tier).

Universe (CFTC Financial-Futures contract codes):
  EURUSD <- 6E  (EUR FX)            code 099741
  GBPUSD <- 6B  (GBP STG)           code 096742
  USDJPY <- 6J  (JPN YEN, inverted) code 097741
  AUDUSD <- 6A  (AUD)               code 232741

Activation gate (per CLAUDE.md Wire-Up Rule, default OFF):
  FOREX_COT_REVERSAL_ENABLED=1   -- required to perform any network fetch.

Without that var, fetch_cot(...) returns ``{"contract": code, "reports": []}``
so callers/tests can exercise the graceful-failure path deterministically.

Cache: ``data/cftc_cot_forex/<contract>_latest.json`` (atomic write).

This file does NOT register any pick generator caller. ``forex_cot_reversal``
imports it as the sole consumer; see that module for the Wiring Plan.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# CFTC Financial-Futures contract codes for the FX majors.
FOREX_CONTRACTS: dict[str, dict] = {
    "EURUSD": {"code": "099741", "futures_code": "6E", "name": "EURO FX",
               "invert_for_usd_base": False},
    "GBPUSD": {"code": "096742", "futures_code": "6B", "name": "BRITISH POUND",
               "invert_for_usd_base": False},
    "USDJPY": {"code": "097741", "futures_code": "6J", "name": "JAPANESE YEN",
               "invert_for_usd_base": True},  # YEN futures are USD/JPY inverted
    "AUDUSD": {"code": "232741", "futures_code": "6A", "name": "AUSTRALIAN DOLLAR",
               "invert_for_usd_base": False},
}

LOOKBACK_WEEKS = 60  # >= 52 so percentile window is fully populated
CACHE_DIR = _REPO_ROOT / "data" / "cftc_cot_forex"
SOCRATA_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


def _is_enabled() -> bool:
    return os.environ.get("FOREX_COT_REVERSAL_ENABLED") == "1"


def _quandl_key() -> Optional[str]:
    return os.environ.get("QUANDL_API_KEY") or None


def _fetch_socrata(contract_code: str, limit: int = LOOKBACK_WEEKS) -> Optional[list]:
    """Public CFTC Socrata endpoint. Returns reports list or None on failure."""
    try:
        params = urllib.parse.urlencode({
            "$where": f"cftc_contract_market_code='{contract_code}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": str(limit),
        })
        url = f"{SOCRATA_URL}?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (cftc_cot_forex_fetcher)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [COT-FX] Socrata fetch failed for {contract_code}: {e}")
        return None


def _fetch_quandl(contract_code: str, api_key: str,
                  limit: int = LOOKBACK_WEEKS) -> Optional[list]:
    """Quandl CFTC dataset fallback. Returns Socrata-shaped reports or None.

    Quandl returns column-oriented JSON; we re-key to the small subset of
    fields downstream code uses (noncomm long/short, commercial long/short,
    report_date_as_yyyy_mm_dd).
    """
    try:
        url = (f"https://www.quandl.com/api/v3/datasets/CFTC/"
               f"{contract_code}_F_L_ALL.json?api_key={api_key}&limit={limit}")
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (cftc_cot_forex_fetcher)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
        rows = raw.get("dataset", {}).get("data", []) or []
        cols = raw.get("dataset", {}).get("column_names", []) or []
        idx = {name: i for i, name in enumerate(cols)}

        def _g(row: list, key_options: list[str], default: int = 0) -> int:
            for k in key_options:
                if k in idx:
                    try:
                        return int(row[idx[k]] or 0)
                    except (TypeError, ValueError):
                        return default
            return default

        out: list[dict] = []
        for row in rows:
            date = row[0] if row else ""
            out.append({
                "report_date_as_yyyy_mm_dd": str(date)[:10],
                "noncomm_positions_long_all": _g(
                    row, ["Noncommercial Long", "Noncommercial Longs"]),
                "noncomm_positions_short_all": _g(
                    row, ["Noncommercial Short", "Noncommercial Shorts"]),
                "comm_positions_long_all": _g(
                    row, ["Commercial Long", "Commercial Longs"]),
                "comm_positions_short_all": _g(
                    row, ["Commercial Short", "Commercial Shorts"]),
            })
        return out
    except Exception as e:
        print(f"  [COT-FX] Quandl fetch failed for {contract_code}: {e}")
        return None


def fetch_cot(symbol: str, limit: int = LOOKBACK_WEEKS,
              use_cache: bool = True) -> dict:
    """Fetch COT reports for a FOREX_CONTRACTS symbol.

    Returns ``{"contract": code, "symbol": symbol, "reports": [...]}`` or
    ``{"contract": code, "symbol": symbol, "reports": []}`` on any failure
    or when the FOREX_COT_REVERSAL_ENABLED gate is OFF (default).
    """
    info = FOREX_CONTRACTS.get(symbol)
    if info is None:
        return {"contract": "", "symbol": symbol, "reports": []}
    code = info["code"]
    empty = {"contract": code, "symbol": symbol, "reports": []}

    if not _is_enabled():
        return empty

    reports: Optional[list] = None
    qk = _quandl_key()
    if qk:
        reports = _fetch_quandl(info["futures_code"], qk, limit=limit)
    if not reports:
        reports = _fetch_socrata(code, limit=limit)
    if not reports:
        # Last-resort: cached file (only if explicitly allowed).
        if use_cache:
            cache_path = CACHE_DIR / f"{symbol}_latest.json"
            try:
                if cache_path.exists():
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    return {"contract": code, "symbol": symbol,
                            "reports": cached.get("reports", []),
                            "from_cache": True}
            except Exception:
                pass
        return empty

    # Persist cache (best-effort).
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = CACHE_DIR / f"{symbol}_latest.json"
        tmp = cache_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(),
                       "contract": code, "symbol": symbol,
                       "reports": reports}, f)
        os.replace(tmp, cache_path)
    except Exception as e:
        print(f"  [COT-FX] cache write failed for {symbol}: {e}")

    return {"contract": code, "symbol": symbol, "reports": reports}


def fetch_all(limit: int = LOOKBACK_WEEKS) -> dict[str, dict]:
    """Fetch the full FX major universe. Returns {symbol: result}."""
    return {sym: fetch_cot(sym, limit=limit) for sym in FOREX_CONTRACTS}


if __name__ == "__main__":
    print(f"FOREX_COT_REVERSAL_ENABLED={os.environ.get('FOREX_COT_REVERSAL_ENABLED')}")
    print(f"QUANDL_API_KEY set: {bool(_quandl_key())}")
    out = fetch_all()
    for sym, res in out.items():
        n = len(res.get("reports", []))
        print(f"  {sym}: {n} reports (contract {res.get('contract')})")
