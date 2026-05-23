"""Lightweight math utilities for alpha_engine and consumers.

No heavy dependencies (numpy/scipy) — safe for minimal CI containers.
"""
from __future__ import annotations


def compute_profit_factor(
    gross_wins: float,
    gross_losses: float,
    *,
    threshold: float = 0.0,
) -> float | None:
    """Compute Profit Factor with consistent flat-trade handling.

    Args:
        gross_wins: Sum of positive PnL values.
        gross_losses: Sum of absolute negative PnL values.
        threshold: Minimum |PnL| to count toward wins/losses.  Trades with
            |pnl| <= threshold are treated as flat (ignored).  Default 0.0
            preserves legacy behavior.  IMPORTANT — units must match callers'
            pnl scale: dashboard JS passes raw decimal pnl (use 0.01 = 1bp
            to match its FLAT_PNL_THRESHOLD); `prediction_quality_tracker`
            pre-scales pnl by 100 (use 1.0 = 1%).  Always pass `threshold`
            in the same scale as `gross_wins`/`gross_losses`.

    Returns:
        float('inf') if there are real wins above threshold and no real losses.
        0.0          if there are no real wins (and no real losses).
        None         if both gross_wins and gross_losses are effectively zero
                     after thresholding (only flat trades).  Callers should
                     render this as '—' (em-dash) in UIs.
        wins/losses  otherwise.
    """
    real_wins = gross_wins if gross_wins > threshold else 0.0
    real_losses = gross_losses if gross_losses > threshold else 0.0

    if real_losses > 0:
        return real_wins / real_losses
    if real_wins > 0:
        return float("inf")
    return None


def format_profit_factor(pf: float | None) -> str:
    """Human-readable PF string matching dashboard conventions.

    '—'  → no real wins or losses (only flat trades).
    '∞'  → all wins, no losses.
    'N.NN' → normal rounded value.
    """
    if pf is None:
        return "—"
    if pf == float("inf"):
        return "∞"
    return f"{pf:.2f}"
