#!/usr/bin/env python3
"""
H-024 — G10 Carry: FRED 3-Month Rate Spread Z-Score Harness
============================================================
Pre-registered per M-107. OPT-IN RESEARCH SIDECAR.

Hypothesis: G10 carry — FRED 3-month OIS/policy rate spread z-score
discriminates FOREX pick outcomes. Long high-rate currency, short low-rate
currency. Z-score > +1.5 sigma vs 52-week mean is a favorable carry signal.

Method:
  1. Fetch FRED policy-rate series for each G10 currency (free CSV, no key)
     If FRED is unreachable, fall back to embedded historical rate table.
  2. For each FOREX closed pick, extract base/quote currencies from symbol
  3. Compute carry_spread = rate(quote) - rate(base) at pick entry_date
  4. Compute 52-week z-score of carry_spread -> carry_z
  5. Run walk-forward Cohen's d (eff) across 14-day rolling windows
  6. Admissible if eff >= 0.30 in same direction across >= 3 windows

Acceptance criteria (H-024):
  eff_floor: 0.30
  min_windows_admissible: 3
  same_sign: True

Fallback rates:
  G10 central bank policy rates (2021-2026) are embedded as a static table
  so the harness runs offline if FRED is unavailable. Monthly granularity.
  Sources: BIS, ECB, BoE, BoJ, RBNZ, RBA, BoC, SNB public releases.

Usage:
    python tools/hypothesis/h024_g10_carry_harness.py
    python tools/hypothesis/h024_g10_carry_harness.py --json
    python tools/hypothesis/h024_g10_carry_harness.py --carry-threshold 1.0
    python tools/hypothesis/h024_g10_carry_harness.py --offline
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLOSED_PATH = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
CACHE_PATH = REPO_ROOT / "alpha_engine" / "data" / "g10_carry_cache.json"
OUTPUT_PATH = REPO_ROOT / "reports" / "h024_g10_carry_harness.json"

FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
FRED_CACHE_TTL_HOURS = 24
FRED_TIMEOUT_SEC = 15

# Harness thresholds matching H-024 acceptance criteria
EFF_FLOOR = 0.30
MIN_WINDOWS = 3
WINDOW_DAYS = 14
CARRY_Z_LOOKBACK_DAYS = 365  # 52-week lookback for z-score
CARRY_Z_THRESHOLD = 1.0      # hypothesis says 1.5, we test 1.0 as floor

WIN_STATUSES = {"WIN", "WON", "TARGET_HIT", "TP_HIT", "CLOSED_WIN"}
LOSS_STATUSES = {"LOSS", "LOST", "SL_HIT", "STOPPED", "CLOSED_LOSS", "EXPIRED"}

# G10 currency -> FRED series ID (policy / 3m OIS proxy)
# Primary: try list[0] first, fall back to subsequent entries on 404
G10_FRED_SERIES: dict[str, list[str]] = {
    "USD": ["FEDFUNDS", "SOFR", "DFF"],
    "GBP": ["BOEBR", "IUDSOIA"],
    "EUR": ["ECBDFR", "ECBESTRVOLWGTTRMDMNRT"],
    "JPY": ["IR3TCD01JPM156N", "IR3TIB01JPM156N"],
    "AUD": ["IR3TCD01AUM156N"],
    "NZD": ["IR3TCD01NZM156N"],
    "CAD": ["IR3TCD01CAM156N"],
    "CHF": ["IR3TCD01CHM156N"],
    "NOK": ["IR3TCD01NOM156N"],
    "SEK": ["IR3TCD01SEM156N"],
}

# ---------------------------------------------------------------------------
# Embedded fallback rate table (monthly, central bank policy rates %)
# Covers 2021-01 to 2026-05. Used when FRED is unreachable.
# Sources: Fed, BoE, ECB, BoJ, RBA, RBNZ, BoC, SNB, Norges Bank, Riksbank.
# ---------------------------------------------------------------------------
# fmt: off
_FALLBACK_RATES: dict[str, list[tuple[str, float]]] = {
    # (YYYY-MM-DD, rate_pct)
    "USD": [
        ("2021-01-01", 0.09), ("2021-04-01", 0.07), ("2021-07-01", 0.10),
        ("2021-10-01", 0.08), ("2022-01-01", 0.08), ("2022-03-01", 0.33),
        ("2022-05-01", 0.83), ("2022-07-01", 2.33), ("2022-09-01", 3.08),
        ("2022-11-01", 3.83), ("2023-01-01", 4.33), ("2023-03-01", 4.65),
        ("2023-05-01", 5.08), ("2023-07-01", 5.33), ("2023-09-01", 5.33),
        ("2023-11-01", 5.33), ("2024-01-01", 5.33), ("2024-03-01", 5.33),
        ("2024-06-01", 5.33), ("2024-09-01", 5.08), ("2024-11-01", 4.83),
        ("2024-12-01", 4.58), ("2025-01-01", 4.33), ("2025-03-01", 4.33),
        ("2025-06-01", 4.33), ("2025-09-01", 4.33), ("2025-12-01", 4.33),
        ("2026-01-01", 4.33), ("2026-03-01", 4.33), ("2026-05-01", 4.33),
    ],
    "GBP": [
        ("2021-01-01", 0.10), ("2021-07-01", 0.10), ("2021-12-01", 0.25),
        ("2022-02-01", 0.50), ("2022-03-01", 0.75), ("2022-05-01", 1.00),
        ("2022-06-01", 1.25), ("2022-08-01", 1.75), ("2022-09-01", 2.25),
        ("2022-11-01", 3.00), ("2022-12-01", 3.50), ("2023-02-01", 4.00),
        ("2023-03-01", 4.25), ("2023-05-01", 4.50), ("2023-06-01", 5.00),
        ("2023-08-01", 5.25), ("2023-11-01", 5.25), ("2024-01-01", 5.25),
        ("2024-08-01", 5.00), ("2024-11-01", 4.75), ("2025-02-01", 4.50),
        ("2025-03-01", 4.50), ("2025-05-01", 4.25), ("2025-08-01", 4.00),
        ("2025-11-01", 3.75), ("2026-01-01", 3.75), ("2026-05-01", 3.75),
    ],
    "EUR": [
        ("2021-01-01", 0.00), ("2022-07-01", 0.00), ("2022-09-01", 0.75),
        ("2022-11-01", 1.50), ("2022-12-01", 2.00), ("2023-02-01", 2.50),
        ("2023-03-01", 3.00), ("2023-05-01", 3.25), ("2023-06-01", 3.50),
        ("2023-07-01", 3.75), ("2023-09-01", 4.00), ("2023-11-01", 4.00),
        ("2024-01-01", 4.00), ("2024-06-01", 3.75), ("2024-09-01", 3.50),
        ("2024-10-01", 3.25), ("2024-12-01", 3.00), ("2025-01-01", 2.75),
        ("2025-03-01", 2.50), ("2025-04-01", 2.25), ("2025-06-01", 2.00),
        ("2025-09-01", 1.75), ("2025-12-01", 1.75), ("2026-01-01", 1.75),
        ("2026-05-01", 1.75),
    ],
    "JPY": [
        ("2021-01-01", -0.10), ("2022-01-01", -0.10), ("2023-01-01", -0.10),
        ("2024-01-01", -0.10), ("2024-03-01", 0.10), ("2024-07-01", 0.25),
        ("2024-10-01", 0.25), ("2025-01-01", 0.50), ("2025-03-01", 0.50),
        ("2025-06-01", 0.50), ("2025-09-01", 0.75), ("2025-12-01", 0.75),
        ("2026-01-01", 0.75), ("2026-05-01", 0.75),
    ],
    "AUD": [
        ("2021-01-01", 0.10), ("2022-05-01", 0.35), ("2022-06-01", 0.85),
        ("2022-07-01", 1.35), ("2022-08-01", 1.85), ("2022-09-01", 2.35),
        ("2022-10-01", 2.60), ("2022-11-01", 2.85), ("2022-12-01", 3.10),
        ("2023-02-01", 3.35), ("2023-03-01", 3.60), ("2023-05-01", 3.85),
        ("2023-06-01", 4.10), ("2023-11-01", 4.35), ("2024-01-01", 4.35),
        ("2024-08-01", 4.35), ("2025-02-01", 4.10), ("2025-04-01", 3.85),
        ("2025-07-01", 3.60), ("2025-10-01", 3.35), ("2026-01-01", 3.35),
        ("2026-05-01", 3.35),
    ],
    "NZD": [
        ("2021-01-01", 0.25), ("2021-10-01", 0.50), ("2021-11-01", 0.75),
        ("2022-02-01", 1.00), ("2022-04-01", 1.50), ("2022-05-01", 2.00),
        ("2022-07-01", 2.50), ("2022-08-01", 3.00), ("2022-10-01", 3.50),
        ("2022-11-01", 4.25), ("2023-02-01", 4.75), ("2023-04-01", 5.25),
        ("2023-05-01", 5.50), ("2023-07-01", 5.50), ("2024-01-01", 5.50),
        ("2024-08-01", 5.25), ("2024-10-01", 4.75), ("2024-11-01", 4.25),
        ("2025-02-01", 3.75), ("2025-04-01", 3.50), ("2025-07-01", 3.25),
        ("2025-10-01", 3.00), ("2026-01-01", 3.00), ("2026-05-01", 3.00),
    ],
    "CAD": [
        ("2021-01-01", 0.25), ("2022-03-01", 0.50), ("2022-04-01", 1.00),
        ("2022-06-01", 1.50), ("2022-07-01", 2.50), ("2022-09-01", 3.25),
        ("2022-10-01", 3.75), ("2022-12-01", 4.25), ("2023-01-01", 4.50),
        ("2023-03-01", 4.50), ("2023-06-01", 4.75), ("2023-07-01", 5.00),
        ("2023-09-01", 5.00), ("2024-01-01", 5.00), ("2024-06-01", 4.75),
        ("2024-07-01", 4.50), ("2024-09-01", 4.25), ("2024-10-01", 3.75),
        ("2024-12-01", 3.25), ("2025-01-01", 3.00), ("2025-03-01", 2.75),
        ("2025-04-01", 2.75), ("2025-06-01", 2.75), ("2026-01-01", 2.75),
        ("2026-05-01", 2.75),
    ],
    "CHF": [
        ("2021-01-01", -0.75), ("2022-01-01", -0.75), ("2022-06-01", -0.25),
        ("2022-09-01", 0.50), ("2022-12-01", 1.00), ("2023-03-01", 1.50),
        ("2023-06-01", 1.75), ("2023-09-01", 1.75), ("2024-01-01", 1.75),
        ("2024-03-01", 1.50), ("2024-06-01", 1.25), ("2024-09-01", 1.00),
        ("2024-12-01", 0.50), ("2025-03-01", 0.25), ("2025-06-01", 0.00),
        ("2025-09-01", 0.00), ("2026-01-01", 0.00), ("2026-05-01", 0.00),
    ],
    "NOK": [
        ("2021-01-01", 0.00), ("2021-09-01", 0.25), ("2021-12-01", 0.50),
        ("2022-03-01", 0.75), ("2022-06-01", 1.25), ("2022-08-01", 1.75),
        ("2022-09-01", 2.25), ("2022-11-01", 2.50), ("2023-01-01", 2.75),
        ("2023-03-01", 3.00), ("2023-05-01", 3.25), ("2023-06-01", 3.75),
        ("2023-08-01", 4.00), ("2023-09-01", 4.25), ("2023-12-01", 4.50),
        ("2024-01-01", 4.50), ("2024-12-01", 4.50), ("2025-03-01", 4.50),
        ("2025-06-01", 4.25), ("2025-09-01", 4.00), ("2025-12-01", 3.75),
        ("2026-01-01", 3.75), ("2026-05-01", 3.50),
    ],
    "SEK": [
        ("2021-01-01", 0.00), ("2022-05-01", 0.25), ("2022-07-01", 0.75),
        ("2022-09-01", 1.75), ("2022-11-01", 2.50), ("2023-01-01", 3.00),
        ("2023-04-01", 3.50), ("2023-06-01", 3.75), ("2023-09-01", 4.00),
        ("2023-11-01", 4.00), ("2024-01-01", 4.00), ("2024-05-01", 3.75),
        ("2024-08-01", 3.50), ("2024-09-01", 3.25), ("2024-11-01", 2.75),
        ("2025-01-01", 2.50), ("2025-03-01", 2.25), ("2025-05-01", 2.00),
        ("2025-09-01", 1.75), ("2025-12-01", 1.75), ("2026-01-01", 1.75),
        ("2026-05-01", 1.75),
    ],
}
# fmt: on


# ---------------------------------------------------------------------------
# FRED CSV fetching
# ---------------------------------------------------------------------------

def _fetch_fred_series(series_id: str) -> list[tuple[date, float]]:
    """Fetch a FRED CSV series. Returns sorted list of (date, value) tuples."""
    url = FRED_BASE_URL.format(series_id=series_id)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (research-sidecar; H-024)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=FRED_TIMEOUT_SEC) as r:
            text = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP {e.code} for {series_id}") from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise ValueError(f"Network error for {series_id}: {e}") from e

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("DATE"):
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            d = date.fromisoformat(parts[0].strip())
            val_str = parts[1].strip()
            if val_str in (".", "", "NA"):
                continue
            val = float(val_str)
            rows.append((d, val))
        except (ValueError, TypeError):
            continue
    return sorted(rows, key=lambda x: x[0])


def _build_fallback_rates() -> dict[str, dict[date, float]]:
    """Build rates from embedded static table."""
    result: dict[str, dict[date, float]] = {}
    for ccy, entries in _FALLBACK_RATES.items():
        d_map: dict[date, float] = {}
        for ds, val in entries:
            d_map[date.fromisoformat(ds)] = val
        result[ccy] = d_map
    return result


def load_g10_rates(
    force_refresh: bool = False,
    offline: bool = False,
) -> tuple[dict[str, dict[date, float]], str]:
    """
    Return ({currency: {date: rate}}, source_label).
    Tries: cache -> FRED live -> embedded fallback.
    """
    if not offline:
        # Check cache
        if not force_refresh and CACHE_PATH.exists():
            try:
                raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                ts = datetime.fromisoformat(raw.get("fetched_at", "2000-01-01"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
                if age_h < FRED_CACHE_TTL_HOURS:
                    print(f"[H-024] Using cached G10 rates ({age_h:.1f}h old)")
                    result: dict[str, dict[date, float]] = {}
                    for ccy, series in raw.get("rates", {}).items():
                        result[ccy] = {date.fromisoformat(k): v for k, v in series.items()}
                    return result, "fred_cache"
            except Exception:
                pass

        # Try FRED live
        result = {}
        fetched_series: dict[str, dict[str, float]] = {}
        fred_success = 0

        for ccy, series_list in G10_FRED_SERIES.items():
            rows = None
            used_series = None
            for series_id in series_list:
                try:
                    print(f"[H-024] Fetching FRED {series_id} ({ccy})...")
                    rows = _fetch_fred_series(series_id)
                    used_series = series_id
                    break
                except ValueError as e:
                    print(f"[H-024]   Skipping {series_id}: {e}")
                    continue

            if rows:
                d_map = {d: v for d, v in rows}
                result[ccy] = d_map
                fetched_series[ccy] = {d.isoformat(): v for d, v in rows}
                print(f"[H-024]   {ccy}: {len(rows)} obs via {used_series}")
                fred_success += 1
            else:
                result[ccy] = {}
                fetched_series[ccy] = {}

        if fred_success >= 4:
            # Enough FRED data — save cache and return
            try:
                CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                CACHE_PATH.write_text(json.dumps({
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "rates": fetched_series,
                }, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[H-024] Warning: cache write failed: {e}")
            return result, "fred_live"
        else:
            print(f"[H-024] FRED returned {fred_success}/{len(G10_FRED_SERIES)} series "
                  f"— falling back to embedded rate table")

    print("[H-024] Using embedded G10 policy rate fallback table (2021-2026)")
    return _build_fallback_rates(), "embedded_fallback"


# ---------------------------------------------------------------------------
# Rate interpolation and carry spread
# ---------------------------------------------------------------------------

def _get_rate_at(series: dict[date, float], target: date) -> float | None:
    """
    Get the rate for a date using the most recent available observation
    on or before target (forward-fill / step function).
    """
    if not series:
        return None
    best = None
    for d in sorted(series.keys(), reverse=True):
        if d <= target:
            best = d
            break
    if best is None:
        return None
    return series[best]


def build_spread_series(
    base_ccy: str,
    quote_ccy: str,
    rates: dict[str, dict[date, float]],
    start_date: date,
    end_date: date,
) -> dict[date, float]:
    """
    Build daily carry_spread = rate(quote) - rate(base) for the date range.
    Uses monthly FRED observations forward-filled between release dates.
    """
    base_series = rates.get(base_ccy, {})
    quote_series = rates.get(quote_ccy, {})

    if not base_series or not quote_series:
        return {}

    result: dict[date, float] = {}
    d = start_date
    while d <= end_date:
        r_base = _get_rate_at(base_series, d)
        r_quote = _get_rate_at(quote_series, d)
        if r_base is not None and r_quote is not None:
            result[d] = r_quote - r_base
        d += timedelta(days=1)
    return result


def compute_carry_zseries(
    spread_series: dict[date, float],
    lookback_days: int = CARRY_Z_LOOKBACK_DAYS,
) -> dict[date, float]:
    """Rolling z-score of carry spread over lookback_days window."""
    sorted_dates = sorted(spread_series.keys())
    z: dict[date, float] = {}
    for i, d in enumerate(sorted_dates):
        window_start = d - timedelta(days=lookback_days)
        window_vals = [spread_series[dd] for dd in sorted_dates[:i+1]
                       if dd >= window_start]
        if len(window_vals) < 10:
            continue
        mu = sum(window_vals) / len(window_vals)
        var = sum((v - mu) ** 2 for v in window_vals) / max(len(window_vals) - 1, 1)
        sigma = math.sqrt(var)
        if sigma < 1e-9:
            z[d] = 0.0
        else:
            z[d] = (spread_series[d] - mu) / sigma
    return z


# ---------------------------------------------------------------------------
# Symbol parsing
# ---------------------------------------------------------------------------

G10_CURRENCIES = set(G10_FRED_SERIES.keys())


def _parse_currencies(symbol: str) -> tuple[str, str] | None:
    """
    Extract (base, quote) from a FOREX symbol like EURUSD=X, GBPJPY=X, etc.
    Returns None if currencies aren't G10 or can't be parsed.
    """
    sym = symbol.upper().replace("=X", "").replace("_X", "").strip()

    # Standard 6-char pairs (EURUSD, GBPJPY, etc.)
    if len(sym) == 6 and sym[:3] in G10_CURRENCIES and sym[3:] in G10_CURRENCIES:
        return sym[:3], sym[3:]

    # Try common separators
    for sep in ("/", "-", "_"):
        if sep in sym:
            parts = sym.split(sep, 1)
            if (len(parts) == 2 and parts[0] in G10_CURRENCIES
                    and parts[1] in G10_CURRENCIES):
                return parts[0], parts[1]

    return None


# ---------------------------------------------------------------------------
# Pick helpers
# ---------------------------------------------------------------------------

def _parse_dt(s: Any) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            clean = str(s)[:26].strip()
            # Strip timezone offset for naive parse
            dt = datetime.strptime(clean.replace("+00:00", "").replace("Z", ""), fmt.replace("%z", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _is_win(pick: dict) -> bool | None:
    status = str(pick.get("status") or "").upper()
    if status in WIN_STATUSES:
        return True
    if status in LOSS_STATUSES:
        return False
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    return None


def load_forex_picks() -> list[dict]:
    """Load closed FOREX picks with resolvable outcomes."""
    picks = json.loads(CLOSED_PATH.read_text(encoding="utf-8"))
    out = []
    for p in picks:
        ac = str(p.get("asset_class") or "").upper()
        if ac != "FOREX":
            continue
        if _is_win(p) is None:
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Carry z-score joining
# ---------------------------------------------------------------------------

def enrich_picks_with_carry(
    picks: list[dict],
    rates: dict[str, dict[date, float]],
    carry_z_threshold: float = CARRY_Z_THRESHOLD,
) -> list[dict]:
    """
    For each pick, compute carry_spread and carry_z at entry_date.
    Adds keys: base_ccy, quote_ccy, carry_spread, carry_z, carry_signal.
    Skips picks where currencies can't be parsed or data is unavailable.
    """
    # Pre-compute spread + z series per currency pair to avoid redundant work
    pair_spread_cache: dict[tuple[str, str], dict[date, float]] = {}
    pair_z_cache: dict[tuple[str, str], dict[date, float]] = {}

    enriched = []
    skipped_parse = 0
    skipped_data = 0

    for p in picks:
        symbol = str(p.get("symbol") or "")
        pair = _parse_currencies(symbol)
        if pair is None:
            skipped_parse += 1
            continue

        base_ccy, quote_ccy = pair

        # Entry date
        entry_dt = _parse_dt(
            p.get("entry_date") or p.get("created_at") or p.get("open_date")
        )
        if entry_dt is None:
            skipped_data += 1
            continue
        entry_d = entry_dt.date()

        # Build spread series for this pair if not cached
        if pair not in pair_spread_cache:
            earliest = date(2021, 1, 1)
            spread_s = build_spread_series(
                base_ccy, quote_ccy, rates,
                start_date=earliest,
                end_date=date.today(),
            )
            pair_spread_cache[pair] = spread_s
            pair_z_cache[pair] = compute_carry_zseries(spread_s)

        spread_s = pair_spread_cache[pair]
        z_s = pair_z_cache[pair]

        # Find spread and z at entry date (with tolerance: look back up to 35 days)
        carry_spread = None
        carry_z = None
        for delta in range(35):
            d_try = entry_d - timedelta(days=delta)
            if carry_spread is None and d_try in spread_s:
                carry_spread = spread_s[d_try]
            if carry_z is None and d_try in z_s:
                carry_z = z_s[d_try]
            if carry_spread is not None and carry_z is not None:
                break

        if carry_spread is None or carry_z is None:
            skipped_data += 1
            continue

        enriched.append({
            **p,
            "base_ccy": base_ccy,
            "quote_ccy": quote_ccy,
            "carry_spread": carry_spread,
            "carry_z": carry_z,
            # Signal: favorable carry = carry_z > threshold (long high-rate, short low-rate)
            "carry_signal": "FAVORABLE" if carry_z > carry_z_threshold else "UNFAVORABLE",
        })

    print(f"[H-024] Enrichment: {len(enriched)} enriched, "
          f"{skipped_parse} skipped (non-G10 symbol), "
          f"{skipped_data} skipped (no rate data)")
    return enriched


# ---------------------------------------------------------------------------
# Eff computation (Cohen's d)
# ---------------------------------------------------------------------------

def _cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Cohen's d: mean(a) - mean(b) / pooled SD."""
    if not group_a or not group_b:
        return 0.0
    n1, n2 = len(group_a), len(group_b)
    m1 = sum(group_a) / n1
    m2 = sum(group_b) / n2
    var1 = sum((x - m1) ** 2 for x in group_a) / max(n1 - 1, 1)
    var2 = sum((x - m2) ** 2 for x in group_b) / max(n2 - 1, 1)
    pooled_std = math.sqrt(
        (var1 * (n1 - 1) + var2 * (n2 - 1)) / max(n1 + n2 - 2, 1)
    )
    if pooled_std < 1e-12:
        return 0.0
    return (m1 - m2) / pooled_std


# ---------------------------------------------------------------------------
# Walk-forward harness
# ---------------------------------------------------------------------------

def run_walk_forward(picks_enriched: list[dict], carry_z_threshold: float) -> dict:
    """
    Run rolling walk-forward eff across WINDOW_DAYS windows.
    For each window: compare carry_z of WON vs LOST picks.
    Positive eff_z means winners had higher carry_z (favorable for hypothesis).
    """
    now = datetime.now(timezone.utc)
    windows = []

    for i in range(20):  # up to 20 windows = 280 days back
        end = now - timedelta(days=i * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)

        won_z: list[float] = []
        lost_z: list[float] = []
        won_spread: list[float] = []
        lost_spread: list[float] = []
        fav_won = 0
        fav_total = 0

        for p in picks_enriched:
            entry_dt = _parse_dt(
                p.get("entry_date") or p.get("created_at") or p.get("open_date")
            )
            if entry_dt is None:
                continue
            if not (start <= entry_dt < end):
                continue

            outcome = _is_win(p)
            cz = p.get("carry_z")
            cs = p.get("carry_spread")
            if cz is None or cs is None:
                continue

            sig = p.get("carry_signal")
            if sig == "FAVORABLE":
                fav_total += 1
                if outcome is True:
                    fav_won += 1

            if outcome is True:
                won_z.append(cz)
                won_spread.append(cs)
            elif outcome is False:
                lost_z.append(cz)
                lost_spread.append(cs)

        n = len(won_z) + len(lost_z)
        wr = len(won_z) / n if n > 0 else None

        window_rec: dict = {
            "window_end": end.date().isoformat(),
            "window_start": start.date().isoformat(),
            "n_won": len(won_z),
            "n_lost": len(lost_z),
            "n_total": n,
            "win_rate": round(wr, 4) if wr is not None else None,
            "mean_carry_z_won": round(sum(won_z) / len(won_z), 4) if won_z else None,
            "mean_carry_z_lost": round(sum(lost_z) / len(lost_z), 4) if lost_z else None,
            "mean_spread_won": round(sum(won_spread) / len(won_spread), 4) if won_spread else None,
            "mean_spread_lost": round(sum(lost_spread) / len(lost_spread), 4) if lost_spread else None,
            "eff_z": round(_cohens_d(won_z, lost_z), 4),
            "eff_spread": round(_cohens_d(won_spread, lost_spread), 4),
            "favorable_n": fav_total,
            "favorable_wr": (round(fav_won / fav_total, 4) if fav_total > 0 else None),
        }
        windows.append(window_rec)

    # Assess admissibility
    populated = [w for w in windows if w["n_total"] >= 5]
    qualifying = [w for w in populated if abs(w["eff_z"]) >= EFF_FLOOR]

    admissible_count = len(qualifying)
    if qualifying:
        signs = [math.copysign(1, w["eff_z"]) for w in qualifying]
        dominant_sign = max(set(signs), key=signs.count)
        same_sign = all(s == dominant_sign for s in signs)
    else:
        dominant_sign = 0.0
        same_sign = False

    verdict = "ADMISSIBLE" if (
        admissible_count >= MIN_WINDOWS and same_sign
    ) else "KILL"

    # Overall stats across all enriched picks
    all_favorable = [p for p in picks_enriched if p.get("carry_signal") == "FAVORABLE"]
    all_unfavorable = [p for p in picks_enriched if p.get("carry_signal") == "UNFAVORABLE"]
    fav_wr_all = (sum(1 for p in all_favorable if _is_win(p) is True) / len(all_favorable)
                  if all_favorable else None)
    unfav_wr_all = (sum(1 for p in all_unfavorable if _is_win(p) is True) / len(all_unfavorable)
                    if all_unfavorable else None)

    # Carry-spread breakdown by pair
    pairs_seen: dict[str, dict] = {}
    for p in picks_enriched:
        key = f"{p.get('base_ccy','?')}{p.get('quote_ccy','?')}"
        if key not in pairs_seen:
            pairs_seen[key] = {"n": 0, "won": 0, "carry_z_sum": 0.0}
        pairs_seen[key]["n"] += 1
        if _is_win(p) is True:
            pairs_seen[key]["won"] += 1
        pairs_seen[key]["carry_z_sum"] += float(p.get("carry_z", 0))

    pair_summary = {
        k: {
            "n": v["n"],
            "wr": round(v["won"] / v["n"], 3) if v["n"] > 0 else None,
            "mean_carry_z": round(v["carry_z_sum"] / v["n"], 3) if v["n"] > 0 else None,
        }
        for k, v in sorted(pairs_seen.items(), key=lambda x: -x[1]["n"])
    }

    return {
        "hypothesis": "H-024",
        "verdict": verdict,
        "admissible_windows": admissible_count,
        "min_required": MIN_WINDOWS,
        "same_sign": same_sign,
        "dominant_direction": (
            "CARRY_POSITIVE" if dominant_sign > 0
            else "CARRY_NEGATIVE" if dominant_sign < 0
            else "NONE"
        ),
        "eff_floor": EFF_FLOOR,
        "carry_z_threshold": carry_z_threshold,
        "n_enriched_picks": len(picks_enriched),
        "n_favorable_picks": len(all_favorable),
        "n_unfavorable_picks": len(all_unfavorable),
        "favorable_wr_overall": round(fav_wr_all, 4) if fav_wr_all is not None else None,
        "unfavorable_wr_overall": round(unfav_wr_all, 4) if unfav_wr_all is not None else None,
        "pair_summary": pair_summary,
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="H-024 G10 Carry harness")
    parser.add_argument("--json", action="store_true", help="Output full JSON result")
    parser.add_argument(
        "--carry-threshold", type=float, default=CARRY_Z_THRESHOLD,
        help=f"Carry z-score threshold for FAVORABLE signal (default: {CARRY_Z_THRESHOLD})"
    )
    parser.add_argument(
        "--force-refresh", action="store_true",
        help="Force-refresh FRED cache"
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Skip FRED fetch; use embedded fallback rate table only"
    )
    args = parser.parse_args()

    carry_z_threshold = args.carry_threshold

    print("[H-024] Loading G10 rate series...")
    rates, rate_source = load_g10_rates(
        force_refresh=args.force_refresh,
        offline=args.offline,
    )
    available = [ccy for ccy, s in rates.items() if s]
    missing = [ccy for ccy, s in rates.items() if not s]
    print(f"[H-024] Rate source: {rate_source}")
    print(f"[H-024] Available: {available}")
    if missing:
        print(f"[H-024] Missing: {missing}")

    print("[H-024] Loading FOREX closed picks...")
    picks = load_forex_picks()
    print(f"[H-024] {len(picks)} resolved FOREX picks loaded")

    if not picks:
        result = {
            "hypothesis": "H-024",
            "verdict": "KILL",
            "error": "No FOREX closed picks found",
            "windows": [],
        }
    else:
        print("[H-024] Enriching picks with carry z-score...")
        picks_enriched = enrich_picks_with_carry(picks, rates, carry_z_threshold=carry_z_threshold)

        if not picks_enriched:
            result = {
                "hypothesis": "H-024",
                "verdict": "KILL",
                "error": "No picks could be enriched with carry data",
                "n_forex_picks": len(picks),
                "n_enriched_picks": 0,
                "admissible_windows": 0,
                "windows": [],
            }
        else:
            print("[H-024] Running walk-forward eff...")
            result = run_walk_forward(picks_enriched, carry_z_threshold)

    result["asset_class"] = "FOREX"
    result["rate_source"] = rate_source
    result["currencies_available"] = available
    result["currencies_missing"] = missing
    result["total_forex_picks"] = len(picks)
    result["run_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*62}")
        print(f"H-024 G10 Carry Harness")
        print(f"{'='*62}")
        print(f"Rate source:          {rate_source}")
        print(f"Verdict:              {result.get('verdict')}")
        print(f"Admissible windows:   {result.get('admissible_windows')}/{result.get('min_required')} required")
        print(f"Same sign:            {result.get('same_sign')}")
        print(f"Direction:            {result.get('dominant_direction', 'N/A')}")
        print(f"Carry z threshold:    {carry_z_threshold}")
        print(f"Enriched picks:       {result.get('n_enriched_picks')} / {result.get('total_forex_picks')} FOREX")
        fav_wr = result.get("favorable_wr_overall")
        unfav_wr = result.get("unfavorable_wr_overall")
        if fav_wr is not None:
            print(f"Favorable carry WR:   {fav_wr:.1%}  (n={result.get('n_favorable_picks')})")
        if unfav_wr is not None:
            print(f"Unfavorable carry WR: {unfav_wr:.1%}  (n={result.get('n_unfavorable_picks')})")
        print(f"Output:               {OUTPUT_PATH}")

        # Pair breakdown
        pair_summary = result.get("pair_summary", {})
        if pair_summary:
            print(f"\n{'Pair':<10} {'N':>5} {'WR':>7} {'MeanCarryZ':>12}")
            for pair, s in list(pair_summary.items())[:10]:
                wr_str = f"{s['wr']:.1%}" if s.get("wr") is not None else "n/a"
                mz = f"{s['mean_carry_z']:.3f}" if s.get("mean_carry_z") is not None else "n/a"
                print(f"{pair:<10} {s['n']:>5} {wr_str:>7} {mz:>12}")

        populated_windows = [w for w in result.get("windows", []) if w["n_total"] >= 5]
        if populated_windows:
            print(f"\n{'Window end':<14} {'N':>5} {'WR':>7} {'EFF_Z':>8} "
                  f"{'Fav WR':>8} {'Fav N':>7}")
            for w in populated_windows[:12]:
                wr_str = f"{w['win_rate']:.1%}" if w.get("win_rate") is not None else "n/a"
                ez = w["eff_z"]
                fav_wr_str = (f"{w['favorable_wr']:.1%}" if w.get("favorable_wr") is not None
                              else "n/a")
                fn = w.get("favorable_n", 0)
                print(f"{w['window_end']:<14} {w['n_total']:>5} {wr_str:>7} "
                      f"{ez:>8.3f} {fav_wr_str:>8} {fn:>7}")
        else:
            print("\n[No windows with n>=5 found — date range may be too narrow for windowing]")
            # Show raw windows with any data
            for w in result.get("windows", [])[:8]:
                if w["n_total"] > 0:
                    wr_str = f"{w['win_rate']:.1%}" if w.get("win_rate") is not None else "n/a"
                    print(f"  {w['window_end']}: n={w['n_total']} wr={wr_str} "
                          f"eff_z={w['eff_z']:.3f}")

        print(f"\nNote: FOREX picks span only {result.get('total_forex_picks',0)} closed trades "
              f"({picks[0].get('entry_date','?') if picks else '?'} – "
              f"{picks[-1].get('entry_date','?') if picks else '?'}). "
              f"Walk-forward requires multi-month history; verdict is likely KILL "
              f"due to n-floor constraints.")


if __name__ == "__main__":
    main()
