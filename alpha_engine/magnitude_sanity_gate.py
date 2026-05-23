"""magnitude_sanity_gate.py — reject picks with implausible TP/SL magnitudes (M-108).

THE PROBLEM
-----------
A pick's edge can pass DSR, PBO and White's Reality Check and still be
un-tradeable if its take-profit is a backtest fantasy. Found 2026-05-18:
`ml_enhanced_FETUSDT_1d_B_lightgbm` carries an implied take-profit of
24-62% (mean +40%) on a 1-DAY crypto horizon. No executable systematic
strategy has a 40% take-profit — the "win rate" is just the chance a
volatile altcoin tags an enormous target. The statistical tests cannot catch
this: they test "is this return multiple-testing noise", not "is this target
realistically reachable".

This gate sits UPSTREAM of the statistical tests. It rejects a pick whose
implied move (|TP-entry|/entry, |SL-entry|/entry) exceeds what is plausible
for that asset class at any retail holding horizon.

Pure functions, no I/O at import. Conservative caps — they are the MAX
plausible move, set generously so only genuine fantasy is flagged.
"""
from __future__ import annotations

from typing import Optional

# Max plausible single-trade move (fraction of entry) per asset class.
# These are deliberately GENEROUS upper bounds — a pick only fails if its
# target is beyond what that class plausibly reaches in a retail holding
# window. CRYPTO is widest (alts are volatile) yet still flags FETUSDT's 40%.
MAX_MOVE_PCT_BY_CLASS: dict[str, float] = {
    "CRYPTO":    0.25,   # 25% — generous; flags the 40-62% ml_enhanced fantasy
    "MEMECOIN":  0.40,   # memecoins genuinely move more; still capped
    "EQUITY":    0.15,
    "ETF":       0.12,
    "COMMODITY": 0.15,
    "FUTURES":   0.15,
    "FOREX":     0.06,   # FX rarely moves >6% on a retail trade
    "BOND":      0.05,
}
_DEFAULT_MAX_MOVE = 0.20

# Below this, the "target" is sub-noise — effectively no real TP/SL.
MIN_MOVE_PCT = 0.0008  # 8bp — below a round-trip cost, the target is noise.


def max_move_for(asset_class: Optional[str]) -> float:
    """Max plausible move fraction for an asset class."""
    if not asset_class:
        return _DEFAULT_MAX_MOVE
    return MAX_MOVE_PCT_BY_CLASS.get(asset_class.upper(), _DEFAULT_MAX_MOVE)


def implied_move_pct(entry: float, target: Optional[float]) -> Optional[float]:
    """Absolute implied move of `target` from `entry`, as a fraction.
    Returns None if either price is missing/non-positive."""
    try:
        e = float(entry)
        t = float(target) if target is not None else None
    except (TypeError, ValueError):
        return None
    if t is None or e <= 0 or t <= 0:
        return None
    return abs(t - e) / e


def is_magnitude_plausible(pick: dict) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means the pick's TP or SL magnitude is
    implausible for its asset class and the pick should be rejected at
    emission. reason is "" when ok.

    Fail-open: a pick with no entry_price or no TP/SL is NOT failed here
    (a different gate owns missing-TP/SL); this gate only judges magnitude
    when the prices are present.
    """
    ac = pick.get("asset_class")
    cap = max_move_for(ac)
    entry = pick.get("entry_price")
    try:
        if entry is None or float(entry) <= 0:
            return True, ""
    except (TypeError, ValueError):
        return True, ""

    tp_move = implied_move_pct(entry, pick.get("take_profit"))
    sl_move = implied_move_pct(entry, pick.get("stop_loss"))

    if tp_move is not None and tp_move > cap:
        return False, ("TP_MAGNITUDE_IMPLAUSIBLE: implied TP %.1f%% > %s cap "
                        "%.0f%%" % (tp_move * 100,
                                    str(ac or "?"), cap * 100))
    if sl_move is not None and sl_move > cap:
        return False, ("SL_MAGNITUDE_IMPLAUSIBLE: implied SL %.1f%% > %s cap "
                        "%.0f%%" % (sl_move * 100, str(ac or "?"), cap * 100))
    if tp_move is not None and 0 < tp_move < MIN_MOVE_PCT:
        return False, ("TP_SUB_NOISE: implied TP %.3f%% below the %.2f%% "
                        "round-trip-cost floor" % (tp_move * 100,
                                                   MIN_MOVE_PCT * 100))
    return True, ""
