"""Cost-implied trade gate, corrected for captured reversion (2026-11-20).

The first pass compared the FULL reversion distance ``|s| * sigma_eq`` against
round-trip cost. With exit at ``|s_exit|`` the trade captures only
``(|s_entry| - |s_exit|) / |s_entry|`` of that distance — 60% at the standard
1.25 / 0.5 calibration — so the margin was overstated by ~67%.
"""

from __future__ import annotations

DEFAULT_S_ENTRY = 1.25
DEFAULT_S_EXIT = 0.5


def captured_fraction(s_entry: float, s_exit: float = DEFAULT_S_EXIT) -> float:
    s_entry = abs(float(s_entry))
    if s_entry == 0:
        return 0.0
    return max((s_entry - abs(float(s_exit))) / s_entry, 0.0)


def captured_edge_bps(s_entry: float, sigma_eq_frac: float, s_exit: float = DEFAULT_S_EXIT) -> float:
    """Expected gross edge in bps, on the distance actually captured.

    ``sigma_eq_frac`` is a plain return fraction (0.02 = 2%), NOT a percent.
    """
    return captured_fraction(s_entry, s_exit) * abs(float(s_entry)) * float(sigma_eq_frac) * 10_000.0


def should_trade(s_entry: float, sigma_eq_frac: float, cost_bps: float,
                 s_exit: float = DEFAULT_S_EXIT, cost_multiple: float = 2.0) -> dict:
    """Trade only if captured edge clears ``cost_multiple`` x cost."""
    edge = captured_edge_bps(s_entry, sigma_eq_frac, s_exit)
    need = cost_multiple * float(cost_bps)
    return {
        "trade": edge > need,
        "captured_edge_bps": round(edge, 3),
        "required_bps": round(need, 3),
        "captured_fraction": round(captured_fraction(s_entry, s_exit), 4),
        "margin_ratio": round(edge / need, 3) if need else None,
    }
