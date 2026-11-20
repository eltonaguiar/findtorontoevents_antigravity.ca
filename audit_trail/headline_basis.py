"""P0.11 (2026-11-20) — every headline WR/PF must publish its denominator.

The dashboard headline was computed on wins+losses+flat but rendered without
saying so, while ~59% of closed picks sat outside it. This module is the single
place that arithmetic lives, so a test can hold it still.
"""

from __future__ import annotations


def headline_basis(total_closed, total_resolved, zero_pnl_count) -> dict:
    """Return the denominator block that must accompany every headline WR/PF."""
    tc = max(int(total_closed or 0), 0)
    tr = max(int(total_resolved or 0), 0)
    z = max(min(int(zero_pnl_count or 0), tr), 0)
    excluded = max(tc - tr, 0)
    return {
        "headline_denominator": tr,
        "headline_covers_closed_pct": round(100.0 * tr / tc, 2) if tc else None,
        "closed_excluded_from_headline": excluded,
        "excluded_closed": excluded,
        "zero_pnl_share_pct": round(100.0 * z / tr, 2) if tr else None,
        "headline_basis": (
            "WR/PF are computed on wins+losses+flat only; every other closed row "
            "is excluded and counted in closed_excluded_from_headline"
        ),
    }
