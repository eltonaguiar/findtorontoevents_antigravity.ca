"""
Merge entry / take-profit / stop-loss from multiple picks into one consensus row.

Averaging levels across traders often breaks LONG/SHORT geometry (e.g. mixed
entries). This module tries mean → median → highest-confidence valid anchor,
then partial combinations, so institutional consensus rows stay economically
consistent when TP/SL are present.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Callable, Dict, List, Optional, Tuple

SanityFn = Callable[[Dict[str, Any]], bool]


def _sf(v: Any, default: float = 0.0) -> float:
    try:
        return float(v or default)
    except (TypeError, ValueError):
        return default


def _norm_direction(direction: str) -> str:
    t = str(direction or "LONG").upper().strip()
    if t in ("SELL", "SHORT"):
        return "SHORT"
    return "LONG"


def _collect_levels(picks: List[Dict[str, Any]]) -> Tuple[List[float], List[float], List[float]]:
    entries, tps, sls = [], [], []
    for p in picks:
        e = _sf(p.get("entry_price"))
        if e > 0:
            entries.append(e)
        tp = _sf(p.get("take_profit"))
        if tp > 0:
            tps.append(tp)
        sl = _sf(p.get("stop_loss"))
        if sl > 0:
            sls.append(sl)
    return entries, tps, sls


def _candidate(d: str, e: float, tp: Optional[float], sl: Optional[float]) -> Dict[str, Any]:
    c: Dict[str, Any] = {"direction": _norm_direction(d), "entry_price": e}
    if tp is not None and tp > 0:
        c["take_profit"] = tp
    if sl is not None and sl > 0:
        c["stop_loss"] = sl
    return c


def _anchors_by_confidence(
    picks: List[Dict[str, Any]], direction: str, passes: SanityFn
) -> List[Tuple[float, float, float, float]]:
    """List of (confidence, entry, tp, sl) for picks whose own levels pass sanity."""
    dnorm = _norm_direction(direction)
    out: List[Tuple[float, float, float, float]] = []
    for p in picks:
        e = _sf(p.get("entry_price"))
        tp = _sf(p.get("take_profit"))
        sl = _sf(p.get("stop_loss"))
        if not (e > 0 and tp > 0 and sl > 0):
            continue
        cand = _candidate(dnorm, e, tp, sl)
        if passes(cand):
            conf = _sf(p.get("confidence", p.get("ml_score", 0)))
            out.append((conf, e, tp, sl))
    out.sort(key=lambda x: -x[0])
    return out


def merge_consensus_price_levels(
    picks: List[Dict[str, Any]],
    direction: str,
    passes_sanity: SanityFn,
) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """
    Return (entry, tp, sl, method_tag). None means omit that field on the consensus row.
    """
    if not picks:
        return None, None, None, "none"
    dnorm = _norm_direction(direction)
    entries, tps, sls = _collect_levels(picks)

    def try_triple(e: float, tp: float, sl: float, tag: str):
        if e <= 0 or tp <= 0 or sl <= 0:
            return None
        cand = _candidate(dnorm, e, tp, sl)
        if passes_sanity(cand):
            return round(e, 8), round(tp, 8), round(sl, 8), tag
        return None

    # 1) Mean of all available levels
    if entries and tps and sls:
        r = try_triple(sum(entries) / len(entries), sum(tps) / len(tps), sum(sls) / len(sls), "mean")
        if r:
            return r

    # 2) Median
    if entries and tps and sls:
        r = try_triple(median(entries), median(tps), median(sls), "median")
        if r:
            return r

    # 3) Highest-confidence underlying pick that already passes sanity
    anchors = _anchors_by_confidence(picks, direction, passes_sanity)
    if anchors:
        _, e, tp, sl = anchors[0]
        return round(e, 8), round(tp, 8), round(sl, 8), "anchor_highest_confidence"

    # 4) Mean entry + TP/SL from best anchor (recheck geometry)
    if entries and anchors:
        e_mean = sum(entries) / len(entries)
        _, _, tp, sl = anchors[0]
        r = try_triple(e_mean, tp, sl, "mean_entry_anchor_tp_sl")
        if r:
            return r

    # 5) Entry only (mean) if we have entries — leave TP/SL unset
    if entries:
        e_mean = sum(entries) / len(entries)
        cand = _candidate(dnorm, e_mean, None, None)
        if passes_sanity(cand):
            return round(e_mean, 8), None, None, "entry_mean_only"

    # 6) Any positive entry from first pick
    e0 = _sf(picks[0].get("entry_price"))
    if e0 > 0:
        return round(e0, 8), None, None, "first_pick_entry_only"

    return None, None, None, "none"
