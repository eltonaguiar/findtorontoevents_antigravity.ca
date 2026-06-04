"""
reverse_split_symbols.py — Registry of equity tickers known to have undergone
reverse splits that invalidate historical price comparisons.

When a stock reverse-splits, old entry prices recorded before the split become
meaningless against post-split live prices. This produces wildly inflated
(win) or deflated (loss) PnL figures that pollute dashboard stats.

Add any ticker here as soon as a reverse split is announced or detected.
Each entry carries the split ratio and effective date so future audits can
replay adjusted prices if needed.

Usage:
    from audit_trail.reverse_split_symbols import is_reverse_split_affected
    if is_reverse_split_affected(symbol):
        pick["reverse_split_flag"] = True
        # skip from aggregate stats or mark clearly
"""

from __future__ import annotations
from datetime import datetime, timezone

# Symbol -> (ratio_description, effective_date_or_note)
REVERSE_SPLIT_SYMBOLS: dict[str, tuple[str, str]] = {
    "LODE": ("1-for-10", "2025-02-05"),
    "FFIE": ("1-for-40", "2024-01-01"),
    "WKHS": ("1-for-20", "2024-01-01"),
    "KULR": ("1-for-8", "2025-06-23"),
    "HOLO": ("1-for-40", "2025-04-21"),  # cumulative: 1-for-10 (2024-02) + 1-for-20 (2024-10) + 1-for-40 (2025-04)
    "GSAT": ("1-for-15", "2025-02-11"),
    # Excluded: SQQQ/SOXS/LABD (inverse ETF structural decay, not corporate splits)
    # Excluded: CLSK (2019), MARA (2013-2019) — old splits, low stale-data risk
}


def is_reverse_split_affected(symbol: str) -> bool:
    """Return True if `symbol` is known to have had a reverse split."""
    return str(symbol or "").strip().upper() in REVERSE_SPLIT_SYMBOLS


def get_reverse_split_info(symbol: str) -> tuple[str, str] | None:
    """Return (ratio, note) or None."""
    return REVERSE_SPLIT_SYMBOLS.get(str(symbol or "").strip().upper())


def parse_split_ratio(ratio_str: str) -> int | None:
    """Parse '1-for-N' ratio string, return N or None."""
    import re
    m = re.match(r"1-for-(\d+)", str(ratio_str))
    return int(m.group(1)) if m else None


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


def should_adjust_for_split(symbol: str, pick_timestamp: str) -> tuple[bool, int | None]:
    """Determine if a pick needs reverse-split adjustment.

    Returns (should_adjust, split_factor) where split_factor is the N
    from '1-for-N'.  Adjustment is only needed if the pick was submitted
    BEFORE the reverse split effective date.
    """
    info = REVERSE_SPLIT_SYMBOLS.get(str(symbol or "").strip().upper())
    if not info:
        return False, None
    factor = parse_split_ratio(info[0])
    if not factor:
        return False, None
    split_dt = parse_split_date(info[1])
    if not split_dt:
        # Cannot determine date — adjust to be safe (prevents phantom PnL)
        return True, factor
    # Parse pick timestamp
    pick_dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            pick_dt = datetime.strptime(str(pick_timestamp)[:26].rstrip("Z"), fmt.rstrip("Z"))
            pick_dt = pick_dt.replace(tzinfo=timezone.utc)
            break
        except (ValueError, TypeError):
            continue
    if pick_dt is None:
        # Cannot parse pick date — adjust to be safe
        return True, factor
    # Only adjust if pick predates the split
    return pick_dt < split_dt, factor
