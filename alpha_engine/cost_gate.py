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
                 s_exit: float = DEFAULT_S_EXIT, cost_multiple: float = 2.0,
                 sigma_eq_median: float | None = None) -> dict:
    """Trade only if captured edge clears ``cost_multiple`` x cost.

    P0.0k redesign (2026-11-20): the original gate filtered on
    ``expected_pct <= cost``, which gates on LOW sigma_eq. But low sigma_eq means
    a quiet residual, and quiet residuals mean-revert MORE reliably than violent
    ones. The gate was screening on absolute forecast magnitude, which penalised
    exactly the regime where the model works. It was anti-informative.

    The redesigned gate CONDITIONS on sigma_eq (trade only when sigma_eq is above
    the median) rather than filtering on it. The cost check becomes a secondary
    gate: even if sigma_eq is high enough, the captured edge must still clear
    cost_multiple x cost.

    Args:
        sigma_eq_median: if provided, the gate requires sigma_eq_frac >= median.
            If None, the sigma_eq condition is skipped (backward compat).
    """
    edge = captured_edge_bps(s_entry, sigma_eq_frac, s_exit)
    need = cost_multiple * float(cost_bps)

    # Condition 1: sigma_eq must be above median (quiet residuals are more
    # reliable; we should NOT trade in low-sigma regimes, but we should also
    # NOT penalise high-sigma trades just because their absolute forecast is
    # large — that was the anti-informative bug).
    sigma_condition_ok = True
    if sigma_eq_median is not None:
        sigma_condition_ok = float(sigma_eq_frac) >= float(sigma_eq_median)

    # Condition 2: captured edge must clear cost_multiple x cost
    cost_condition_ok = edge > need

    trade = sigma_condition_ok and cost_condition_ok

    reason = ""
    if not sigma_condition_ok:
        reason = f"sigma_eq {sigma_eq_frac:.4f} < median {sigma_eq_median:.4f} (quiet regime, skip)"
    elif not cost_condition_ok:
        reason = f"captured_edge {edge:.2f} bps <= required {need:.2f} bps (cost gate)"

    return {
        "trade": trade,
        "captured_edge_bps": round(edge, 3),
        "required_bps": round(need, 3),
        "captured_fraction": round(captured_fraction(s_entry, s_exit), 4),
        "margin_ratio": round(edge / need, 3) if need else None,
        "sigma_condition_ok": sigma_condition_ok,
        "cost_condition_ok": cost_condition_ok,
        "reason": reason if not trade else "OK",
    }
