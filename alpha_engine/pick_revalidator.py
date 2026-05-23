"""Live-quote pick revalidation at trader-read-time.

Background: `smart_picks_engine.py` runs the `tp_already_hit` / `sl_already_hit`
gate at SCAN TIME (every 2h cron). By the time a human or agent reads
`smart_picks.json` and tries to act on a pick, prices have moved 0.5-5%
and the signal may already be played out (TP hit, SL stopped, or R:R
collapsed below the IC-anti-predictive 3.0 threshold).

This module revalidates a pick against a fresh live quote and computes
the R:R from the live price (not signal entry). Three verdicts:

    OK            — pick still actionable, R:R from live within bounds
    PLAYED_OUT    — TP or SL would already be triggered at live price
    R_R_DEGRADED  — live R:R >= 3.0 (anti-predictive per IC analysis)

Per `THEASK.md` recommendation #6 and the recurring null-execution pattern
documented in `updates/2026-05-01-portfolio-update-synthesis.md` (every
gate-passing candidate failed live re-validation across 4 nights).

The module is a pure function over (pick, live_price). It does NOT fetch
quotes itself — callers pass a fresh price obtained however they like
(TV MCP `quote_get`, Binance public API, `equity_price_failover.py`, etc.).
This keeps the revalidator unit-testable and free of HTTP / rate-limit
concerns.
"""
from __future__ import annotations
from typing import Mapping, Any, Literal

# IC-anti-predictive R:R cutoff per `alpha_engine/elite_scorer.py` lines
# 2255-2263 (1,927-pick analysis: R:R IC=-0.127, R:R 3.0+ = 0% historical
# WR). A pick whose R:R from LIVE price exceeds this should not be entered.
DEFAULT_RR_ANTIPRED_CUTOFF = 3.0

Verdict = Literal["OK", "PLAYED_OUT_TP", "PLAYED_OUT_SL", "R_R_DEGRADED", "MISSING_FIELDS", "BAD_DIRECTION"]


def _direction_is_long(direction: str) -> bool:
    return direction.upper().startswith("L") or direction.upper() == "BUY"


def _direction_is_short(direction: str) -> bool:
    return direction.upper().startswith("S") or direction.upper() == "SELL"


def revalidate_pick(
    pick: Mapping[str, Any],
    live_price: float,
    rr_antipred_cutoff: float = DEFAULT_RR_ANTIPRED_CUTOFF,
) -> dict:
    """Return a revalidation result for a pick at the given live_price.

    Result dict shape:
        {
          "verdict": "OK" | "PLAYED_OUT_TP" | "PLAYED_OUT_SL" | "R_R_DEGRADED" | ...,
          "ok": bool,
          "rr_signal": float | None,    # original signal R:R
          "rr_live": float | None,      # live R:R re-anchored from live_price
          "tp_remaining_pct": float,
          "sl_distance_pct": float,
          "reason": str,
        }

    A caller can branch on `result["ok"]` for a binary gate.
    """
    direction = str(pick.get("direction") or "").upper()
    entry = pick.get("entry_price") or pick.get("entry") or 0
    tp = pick.get("take_profit") or pick.get("tp") or 0
    sl = pick.get("stop_loss") or pick.get("sl") or 0

    try:
        entry = float(entry)
        tp = float(tp)
        sl = float(sl)
        live = float(live_price)
    except (TypeError, ValueError):
        return _result("MISSING_FIELDS", False, None, None, 0, 0, "non-numeric price field")

    if entry <= 0 or tp <= 0 or sl <= 0 or live <= 0:
        return _result("MISSING_FIELDS", False, None, None, 0, 0, "missing or zero entry/tp/sl/live")

    is_long = _direction_is_long(direction)
    is_short = _direction_is_short(direction)
    if not (is_long or is_short):
        return _result("BAD_DIRECTION", False, None, None, 0, 0, f"unrecognized direction: {direction!r}")

    # Signal-time R:R (the "advertised" R:R from when the pick was generated)
    if is_long:
        if entry - sl <= 0:
            rr_signal = None
        else:
            rr_signal = (tp - entry) / (entry - sl)
    else:  # short
        if sl - entry <= 0:
            rr_signal = None
        else:
            rr_signal = (entry - tp) / (sl - entry)

    # Played-out check: would the trade be already TP'd or SL'd at live price?
    if is_long:
        if live >= tp:
            return _result("PLAYED_OUT_TP", False, rr_signal, None, 0, 0,
                           f"live {live} >= TP {tp}, signal already won")
        if live <= sl:
            return _result("PLAYED_OUT_SL", False, rr_signal, None, 0, 0,
                           f"live {live} <= SL {sl}, signal already lost")
    else:  # short
        if live <= tp:
            return _result("PLAYED_OUT_TP", False, rr_signal, None, 0, 0,
                           f"live {live} <= TP {tp}, signal already won")
        if live >= sl:
            return _result("PLAYED_OUT_SL", False, rr_signal, None, 0, 0,
                           f"live {live} >= SL {sl}, signal already lost")

    # Live R:R: distance from live to TP / distance from live to SL
    if is_long:
        tp_distance = tp - live
        sl_distance = live - sl
    else:  # short
        tp_distance = live - tp
        sl_distance = sl - live

    if sl_distance <= 0:
        return _result("PLAYED_OUT_SL", False, rr_signal, None, 0, 0,
                       "sl_distance <= 0 unexpectedly")

    rr_live = tp_distance / sl_distance
    tp_remaining_pct = abs(tp_distance / live) * 100
    sl_distance_pct = abs(sl_distance / live) * 100

    # IC-anti-predictive R:R cutoff
    if rr_live >= rr_antipred_cutoff:
        return _result("R_R_DEGRADED", False, rr_signal, rr_live,
                       tp_remaining_pct, sl_distance_pct,
                       f"R:R from live = {rr_live:.2f} >= {rr_antipred_cutoff} (IC anti-pred cutoff)")

    return _result("OK", True, rr_signal, rr_live, tp_remaining_pct, sl_distance_pct,
                   f"R:R from live = {rr_live:.2f}")


def _result(verdict: Verdict, ok: bool, rr_signal, rr_live,
            tp_rem_pct, sl_dist_pct, reason: str) -> dict:
    return {
        "verdict": verdict,
        "ok": ok,
        "rr_signal": rr_signal,
        "rr_live": rr_live,
        "tp_remaining_pct": tp_rem_pct,
        "sl_distance_pct": sl_dist_pct,
        "reason": reason,
    }


def filter_picks_by_live_quote(
    picks_with_quotes: list[tuple[Mapping[str, Any], float]],
    rr_antipred_cutoff: float = DEFAULT_RR_ANTIPRED_CUTOFF,
) -> tuple[list[dict], list[dict]]:
    """Run revalidate_pick on a batch.

    Args:
        picks_with_quotes: list of (pick_dict, live_price) tuples.
        rr_antipred_cutoff: R:R from live above which to drop.

    Returns:
        (kept, dropped) — each pick dict is augmented with a `_revalidation`
        sub-dict carrying the result.
    """
    kept, dropped = [], []
    for pick, live in picks_with_quotes:
        result = revalidate_pick(pick, live, rr_antipred_cutoff)
        annotated = {**pick, "_revalidation": result}
        if result["ok"]:
            kept.append(annotated)
        else:
            dropped.append(annotated)
    return kept, dropped
