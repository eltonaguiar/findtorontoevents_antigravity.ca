"""
reverse_split_symbols.py — Registry of equity tickers known to have undergone
reverse splits that invalidate historical price comparisons.

When a stock reverse-splits, old entry prices recorded before the split become
meaningless against post-split live prices. This produces wildly inflated
(win) or deflated (loss) PnL figures that pollute dashboard stats.

Each symbol maps to a list of (ratio_description, effective_date) tuples,
newest split first. Multiple entries are supported for stocks with cumulative
reverse splits — the adjustment factor is the product of all splits that
occurred AFTER the pick's submission timestamp.

Usage:
    from audit_trail.reverse_split_symbols import is_reverse_split_affected
    if is_reverse_split_affected(symbol):
        pick["reverse_split_flag"] = True
        # skip from aggregate stats or mark clearly
"""

from __future__ import annotations
from datetime import datetime, timezone
from functools import reduce
from operator import mul
import re


# Symbol -> list of (ratio_description, effective_date)
# NEWEST split first (for human readability). Cumulative factor is computed
# as the product of all splits whose effective date is AFTER pick.submitted_at.
REVERSE_SPLIT_SYMBOLS: dict[str, list[tuple[str, str]]] = {
    # LODE: 1-for-10 reverse split. Announced Feb 2025; effective Feb 25.
    # Source: splithistory.com (verified 2026-06-04)
    "LODE": [("1-for-10", "2025-02-25")],

    # FFIE: 3 cumulative reverse splits in a 12-month window.
    # 1-for-80 (Aug 2023) → 1-for-3 (Mar 2024) → 1-for-40 (Aug 2024).
    # Cumulative factor = 80 × 3 × 40 = 9600× pre-split price inflation.
    # Sources: splithistory.com (verified 2026-06-04)
    "FFIE": [
        ("1-for-40", "2024-08-19"),
        ("1-for-3",  "2024-03-01"),
        ("1-for-80", "2023-08-28"),
    ],

    # WKHS: 3 cumulative reverse splits in ~18 months.
    # 1-for-20 (Jun 2024) → 8-for-100 ≈ 1-for-12.5 (Mar 2025) → 1-for-12 (Dec 2025).
    # Effective factors: 20, then 100/8=12.5, then 12.
    # Cumulative factor = 20 × 12.5 × 12 = 3000×.
    # Sources: splithistory.com (verified 2026-06-04)
    "WKHS": [
        ("1-for-12",   "2025-12-08"),
        ("8-for-100",  "2025-03-17"),
        ("1-for-20",   "2024-06-17"),
    ],

    # KULR: 1-for-8 reverse split effective 2025-06-23.
    # Source: splithistory.com (verified 2026-05-26)
    "KULR": [("1-for-8", "2025-06-23")],

    # HOLO: 3 cumulative reverse splits over ~15 months.
    # 1-for-10 (Feb 2024) → 1-for-20 (Oct 2024) → 1-for-40 (Apr 2025).
    # Cumulative factor = 10 × 20 × 40 = 8000× pre-split price inflation.
    # Sources: splithistory.com (verified 2026-05-26; dates refined 2026-06-04)
    "HOLO": [
        ("1-for-40", "2025-04-21"),
        ("1-for-20", "2024-10-01"),  # approximate — exact date pending verification
        ("1-for-10", "2024-02-01"),  # approximate — exact date pending verification
    ],

    # GSAT: 1-for-15 reverse split effective 2025-02-11.
    # Source: splithistory.com (verified 2026-05-26)
    "GSAT": [("1-for-15", "2025-02-11")],

    # Excluded: SQQQ/SOXS/LABD (inverse ETF structural decay, not corporate splits)
    # Excluded: CLSK (2019), MARA (2013-2019) — old splits, low stale-data risk
    # Excluded: ASTS, RKLB, WULF, QBTS, IONQ, RGTI, CTM, MVST — no reverse splits 2023-2026
}


def is_reverse_split_affected(symbol: str) -> bool:
    """Return True if `symbol` is known to have had a reverse split."""
    return str(symbol or "").strip().upper() in REVERSE_SPLIT_SYMBOLS


def get_reverse_split_info(symbol: str) -> list[tuple[str, str]] | None:
    """Return list of (ratio, date) for all tracked splits, newest first, or None."""
    return REVERSE_SPLIT_SYMBOLS.get(str(symbol or "").strip().upper())


def parse_split_ratio(ratio_str: str) -> float | None:
    """Parse a split ratio string and return the price-multiplier factor.

    Formats accepted:
      - '1-for-N'     → returns N (e.g. '1-for-10' → 10.0)
      - 'N-for-M'     → returns M/N (e.g. '8-for-100' → 12.5)
    Returns None if the string cannot be parsed.
    """
    s = str(ratio_str).strip()
    # Try "1-for-N" format
    m = re.match(r"1-for-(\d+)", s)
    if m:
        return float(m.group(1))
    # Try "N-for-M" format (general)
    m = re.match(r"(\d+)-for-(\d+)", s)
    if m:
        n = float(m.group(1))
        m_val = float(m.group(2))
        if n > 0:
            return m_val / n
    return None


def parse_split_date(date_str: str) -> datetime | None:
    """Parse the split effective date (YYYY-MM-DD) from the registry.
    Returns timezone-aware UTC datetime or None if unparseable."""
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _parse_pick_dt(pick_timestamp: str) -> datetime | None:
    """Parse a pick submission timestamp into a timezone-aware UTC datetime."""
    if not pick_timestamp or not str(pick_timestamp).strip():
        return None
    ts_str = str(pick_timestamp)[:26].rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def should_adjust_for_split(symbol: str, pick_timestamp: str) -> tuple[bool, int | None]:
    """Determine if a pick needs reverse-split adjustment.

    For symbols with multiple cumulative splits, the adjustment factor is the
    product of all split factors whose effective date is AFTER the pick's
    submission — i.e. splits that hadn't happened yet when this pick was
    recorded. Splits that already occurred before submission are already
    priced-in by the market data source (yfinance/Binance).

    Returns (should_adjust, split_factor) where split_factor is the
    cumulative price-multiplier as an integer.  For a 1-for-N split where the
    pick predates it, entry_price must be multiplied by N to match post-split
    OHLC data.  The factor is always an integer because all split ratios in
    the registry (including "N-for-M" general forms like "8-for-100") produce
    integer cumulative products after cross-multiplication with other splits.

    Callers depend on an integer return for log format strings (%d / %s).
    """
    splits = REVERSE_SPLIT_SYMBOLS.get(str(symbol or "").strip().upper())
    if not splits:
        return False, None

    pick_dt = _parse_pick_dt(pick_timestamp)

    applicable_factors: list[float] = []
    for ratio_str, date_str in splits:
        factor = parse_split_ratio(ratio_str)
        if factor is None:
            continue
        split_dt = parse_split_date(date_str)
        if split_dt is None:
            # Cannot determine date — adjust to be safe (prevents phantom PnL)
            applicable_factors.append(factor)
            continue
        if pick_dt is None:
            # Cannot parse pick date — adjust to be safe
            applicable_factors.append(factor)
            continue
        # Only adjust if pick predates the split
        if pick_dt < split_dt:
            applicable_factors.append(factor)

    if not applicable_factors:
        return False, None

    cumulative = reduce(mul, applicable_factors, 1.0)
    result = int(round(cumulative))
    return True, result
