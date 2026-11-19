"""intrabar_resolver — resolve a pick's first touch within a bar.

Why this exists: daily/time-bar resolution that checks "did TP or SL get hit
today" inflates win rates (stop-first-touch is invisible). audit3 only accepts a
forward row as evidence when ``intrabar_first_touch`` is True
(``alpha_engine/forward_observations.py`` rejects daily-resolved rows). This
module is the resolver that stamp is supposed to come from.

Conventions (deliberately conservative):
* If both the stop and the target fall inside the same bar, the **stop** is
  assumed to have been hit first (no sub-bar data).
* If a bar *opens* beyond the stop (gap-through), the fill is the open price,
  which is worse than the stop — never the stop itself.
* ``LONG``: stop is below, target above. ``SHORT``: stop above, target below.

Stdlib only; no network, no DB.
"""
from __future__ import annotations

from typing import Any, Iterable

RESOLVER_VERSION = "intrabar.v1"


def first_touch(
    bars: Iterable[dict[str, Any]],
    *,
    direction: str,
    entry_price: float,
    stop_loss: float | None,
    take_profit: float | None = None,
) -> dict[str, Any] | None:
    """Return the first stop/target touch, else the time exit.

    ``bars`` are dicts with at least ``high`` and ``low`` (and optionally
    ``open``, ``close``, ``timestamp``), oldest first. Returns None for no bars.
    """
    side = str(direction or "").strip().upper()
    if side not in ("LONG", "SHORT"):
        raise ValueError(f"direction must be LONG or SHORT, got {direction!r}")
    last = None
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        last = bar
        hi = _num(bar.get("high"))
        lo = _num(bar.get("low"))
        op = _num(bar.get("open"))
        if hi is None or lo is None:
            continue
        if side == "LONG":
            hit_stop = stop_loss is not None and lo <= stop_loss
            hit_tp = take_profit is not None and hi >= take_profit
            gapped = op is not None and stop_loss is not None and op <= stop_loss
        else:
            hit_stop = stop_loss is not None and hi >= stop_loss
            hit_tp = take_profit is not None and lo <= take_profit
            gapped = op is not None and stop_loss is not None and op >= stop_loss

        if hit_stop:
            price = op if gapped else stop_loss
            return _result("STOP", price, bar, entry_price,
                           both=bool(hit_tp), gapped=bool(gapped))
        if hit_tp:
            return _result("TP", take_profit, bar, entry_price, both=False,
                           gapped=False)
    if last is None:
        return None
    close = _num(last.get("close"))
    if close is None:
        close = _num(last.get("high"))
    return _result("TIME", close, last, entry_price, both=False, gapped=False)


def stamp_pick(
    pick: dict[str, Any],
    bars: Iterable[dict[str, Any]],
    *,
    entry_price: float | None = None,
) -> dict[str, Any]:
    """Return a copy of ``pick`` with intrabar resolution fields filled in."""
    entry = entry_price if entry_price is not None else _num(pick.get("entry_price"))
    if entry is None:
        raise ValueError("pick has no entry_price and none was supplied")
    res = first_touch(
        bars,
        direction=str(pick.get("direction") or ""),
        entry_price=entry,
        stop_loss=_num(pick.get("stop_loss")),
        take_profit=_num(pick.get("take_profit")),
    )
    out = dict(pick)
    if res is None:
        out["intrabar_first_touch"] = False
        out["resolver_version"] = RESOLVER_VERSION
        return out
    out.update({
        "intrabar_first_touch": True,
        "resolver_version": RESOLVER_VERSION,
        "resolved_outcome": res["outcome"],
        "resolved_price": res["price"],
        "resolved_at": res["timestamp"],
    })
    return out


def _result(outcome: str, price: float | None, bar: dict[str, Any],
            entry: float, *, both: bool, gapped: bool) -> dict[str, Any]:
    pnl = None
    if price is not None and entry:
        move = (price - entry) / entry * 100.0
        pnl = round(move, 4)
    return {
        "outcome": outcome,
        "price": price,
        "pnl_pct": pnl,
        "timestamp": bar.get("timestamp"),
        "same_bar_both": both,
        "gapped": gapped,
        "intrabar_first_touch": True,
        "resolver_version": RESOLVER_VERSION,
    }


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f
