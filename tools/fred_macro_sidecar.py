#!/usr/bin/env python3
"""
Opt-in sidecar: fetch key FRED macro indicators and write tools/data/fred_macro_context.json.

## Wiring Plan
Target caller: alpha_engine/non_crypto_quality_enhancer.py (passes_active_gate)
Wire-up: read tools/data/fred_macro_context.json to add macro_regime field to BOND/FOREX/COMMODITY picks
Expected PR/date: after >=2-week validation showing regime signal lift

This module is STANDALONE. It does NOT import from alpha_engine/, audit_trail/, or any
production pick/score path. It is safe to run independently:
    python tools/fred_macro_sidecar.py
"""

import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "fred_macro_context.json"

# FRED series to fetch. Each entry: (series_id, label, n_observations_to_fetch)
# n > 1 is used only where we need recent history for a derived signal (DTWEXBGS 3-month).
SERIES_CONFIG = [
    ("DFF",          "Fed Funds Rate",          1),
    ("T10Y2Y",       "10Y-2Y Treasury Spread",  1),
    ("UNRATE",       "Unemployment Rate",        1),
    ("CPIAUCSL",     "CPI (All Urban)",          1),
    ("DTWEXBGS",     "USD Broad Index",          65),  # ~3 months of trading days
    ("VIXCLS",       "VIX",                      1),
    ("BAMLH0A0HYM2", "HY Credit Spread",         1),
]


# ---------------------------------------------------------------------------
# FRED fetch helpers
# ---------------------------------------------------------------------------

def _fetch_observations(series_id: str, limit: int) -> list[dict]:
    """Return up to `limit` most-recent FRED observations for `series_id`.

    FRED public API allows unauthenticated requests at ~120/min for public series.
    An empty api_key string is accepted by the endpoint.
    """
    import os
    params = {
        "series_id": series_id,
        "api_key": os.environ.get("FRED_API_KEY", ""),
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    observations = data.get("observations", [])
    # FRED uses "." for missing values
    return [o for o in observations if o.get("value", ".") != "."]


def _latest_value(series_id: str, limit: int = 1) -> tuple[float | None, str | None]:
    """Return (value, date) for the most recent non-missing observation."""
    try:
        obs = _fetch_observations(series_id, limit)
        if not obs:
            return None, None
        # sort_order=desc, so first element is newest
        latest = obs[0]
        return float(latest["value"]), latest["date"]
    except Exception as exc:
        warnings.warn(f"FRED fetch failed for {series_id}: {exc}", stacklevel=2)
        return None, None


def _oldest_value(obs_list: list[dict]) -> tuple[float | None, str | None]:
    """Return (value, date) for the oldest entry in an already-fetched obs list."""
    if not obs_list:
        return None, None
    # obs_list is desc-sorted (newest first), so last element is oldest
    oldest = obs_list[-1]
    try:
        return float(oldest["value"]), oldest["date"]
    except (KeyError, ValueError):
        return None, None


# ---------------------------------------------------------------------------
# Signal derivation
# ---------------------------------------------------------------------------

def _macro_regime(dff: float | None, vix: float | None) -> str:
    """
    tight  = DFF > 4 %
    high_vix = VIX > 20
    Combinations:
        tight  + high_vix  -> tight_high_vix
        tight  + low_vix   -> tight_low_vix
        easy   + high_vix  -> easy_high_vix
        easy   + low_vix   -> easy_low_vix
        any missing        -> unknown
    """
    if dff is None or vix is None:
        return "unknown"
    rate_regime = "tight" if dff > 4.0 else "easy"
    vix_regime  = "high_vix" if vix > 20.0 else "low_vix"
    return f"{rate_regime}_{vix_regime}"


def _bond_signal(t10y2y: float | None) -> str:
    """
    T10Y2Y < -0.5  -> bullish  (deeply inverted curve, recession fear, bonds bid)
    T10Y2Y >  0.0  -> bearish  (steepening / normalization, bonds under pressure)
    otherwise      -> neutral
    """
    if t10y2y is None:
        return "neutral"
    if t10y2y < -0.5:
        return "bullish"
    if t10y2y > 0.0:
        return "bearish"
    return "neutral"


def _forex_signal(usd_now: float | None, usd_old: float | None) -> str:
    """
    3-month USD index change > +1%  -> usd_strong
    3-month USD index change < -1%  -> usd_weak
    otherwise                       -> usd_neutral
    """
    if usd_now is None or usd_old is None or usd_old == 0:
        return "usd_neutral"
    pct_change = (usd_now - usd_old) / usd_old * 100.0
    if pct_change > 1.0:
        return "usd_strong"
    if pct_change < -1.0:
        return "usd_weak"
    return "usd_neutral"


def _commodity_signal(vix: float | None) -> str:
    """
    VIX > 25  -> risk_off
    VIX < 15  -> risk_on
    otherwise -> neutral
    """
    if vix is None:
        return "neutral"
    if vix > 25.0:
        return "risk_off"
    if vix < 15.0:
        return "risk_on"
    return "neutral"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> dict:
    """Fetch all FRED series, derive signals, write JSON, and return the payload."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    series_out: dict[str, dict] = {}
    fetch_errors: list[str] = []

    # --- fetch all series ---------------------------------------------------
    # DTWEXBGS needs multiple observations for the 3-month forex signal
    dtwexbgs_obs: list[dict] = []

    for series_id, label, limit in SERIES_CONFIG:
        print(f"  Fetching {series_id} ({label}) …", end=" ", flush=True)
        try:
            obs_list = _fetch_observations(series_id, limit)
            if not obs_list:
                raise ValueError("no non-missing observations returned")

            latest = obs_list[0]
            value = float(latest["value"])
            date  = latest["date"]

            series_out[series_id] = {
                "value": value,
                "date":  date,
                "label": label,
            }

            if series_id == "DTWEXBGS":
                dtwexbgs_obs = obs_list

            print(f"OK  ({value} on {date})")

        except Exception as exc:
            msg = f"{series_id}: {exc}"
            fetch_errors.append(msg)
            print(f"WARN — {exc}")
            warnings.warn(f"FRED fetch failed for {series_id}: {exc}", stacklevel=2)
            series_out[series_id] = {
                "value": None,
                "date":  None,
                "label": label,
                "error": str(exc),
            }

    # --- extract scalar values for signal derivation ------------------------
    def _sv(sid: str) -> float | None:
        return series_out.get(sid, {}).get("value")

    dff     = _sv("DFF")
    t10y2y  = _sv("T10Y2Y")
    vix     = _sv("VIXCLS")
    usd_now = _sv("DTWEXBGS")

    # USD 3-month-ago value (oldest observation in the fetched window)
    usd_old, _ = _oldest_value(dtwexbgs_obs)

    # --- derive signals -----------------------------------------------------
    macro_regime     = _macro_regime(dff, vix)
    bond_signal      = _bond_signal(t10y2y)
    forex_signal     = _forex_signal(usd_now, usd_old)
    commodity_signal = _commodity_signal(vix)

    # --- build payload ------------------------------------------------------
    payload = {
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "series":            series_out,
        "macro_regime":      macro_regime,
        "bond_signal":       bond_signal,
        "forex_signal":      forex_signal,
        "commodity_signal":  commodity_signal,
        "_meta": {
            "fetch_errors":  fetch_errors,
            "source":        "FRED public API (unauthenticated)",
            "series_ids":    [s[0] for s in SERIES_CONFIG],
            "wiring_status": "opt-in sidecar — not imported by production path",
        },
    }

    # --- write JSON ---------------------------------------------------------
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUTPUT_FILE}")
    print(f"  macro_regime     = {macro_regime}")
    print(f"  bond_signal      = {bond_signal}")
    print(f"  forex_signal     = {forex_signal}")
    print(f"  commodity_signal = {commodity_signal}")
    if fetch_errors:
        print(f"\n  Warnings ({len(fetch_errors)} series had errors):")
        for e in fetch_errors:
            print(f"    - {e}")

    return payload


if __name__ == "__main__":
    print("FRED Macro Sidecar — fetching indicators …\n")
    result = run()
    sys.exit(0)
