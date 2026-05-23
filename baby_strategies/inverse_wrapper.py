"""
inverse_wrapper — Generic pick transformer that flips direction on a named
source strategy's picks, with optional confidence-band and symbol filters.

Motivating use cases (see docs/TRADING_INSIGHTS_FROM_AI4TRADE.md §6a):
  - quan_engine        (live fwd_wr 2.8%, strong inverse candidate)
  - Value + Quality    (live fwd_wr 7.8%, strong inverse candidate)

Prior knowledge baked in via caller config, not hardcoded:
  - quan_engine confidence 0.60–0.69 is the worst band (19.8% WR); edge is
    concentrated in {TAOUSDT, HYPEUSDT, TRXUSDT}. A sensible first call
    inverts ONLY that band and EXCLUDES those 3 symbols. See
    alpha_engine/elite_scorer.py:497-502 and :63 for the source data.

NOT auto-wired into the scanner. The transform function is called by an
adapter in antigravity_strategies.py (or equivalent) when a human decides
to activate it. This module never imports from alpha_engine — it is pure
dict-in / dict-out.

See docs/superpowers/specs/2026-04-14-inverse-wrapper-design.md.
"""
from __future__ import annotations

import copy
import logging
from typing import Iterable

logger = logging.getLogger(__name__)

_LONG_DIRS = {"LONG", "BUY", "long", "buy"}
_SHORT_DIRS = {"SHORT", "SELL", "short", "sell"}

# Canonical flip map: maps the exact input casing to its inverted form.
_FLIP = {
    "LONG": "SHORT",
    "SHORT": "LONG",
    "BUY": "SELL",
    "SELL": "BUY",
    "long": "short",
    "short": "long",
    "buy": "sell",
    "sell": "buy",
}


def _flip_direction(direction: str) -> str | None:
    """Return the inverted direction, or None if the input is unknown/NEUTRAL."""
    if direction in _FLIP:
        return _FLIP[direction]
    return None


def _swap_prices(entry: float, tp: float, sl: float) -> tuple[float, float]:
    """Given an entry, TP, and SL on the original side, return the TP and SL
    on the inverted side by mirroring each level around the entry price.

    If the original was LONG with TP above entry and SL below, the inverted
    SHORT version has TP below entry (at the mirrored distance) and SL above
    (at the mirrored distance). This preserves the absolute price distance
    of each level — not its ratio.
    """
    tp_distance = tp - entry
    sl_distance = sl - entry
    inverted_tp = entry - tp_distance
    inverted_sl = entry - sl_distance
    return inverted_tp, inverted_sl


def _in_band(confidence: float | None, band: tuple[float, float] | None) -> bool:
    """True if the filter is unset, or the confidence falls inside [lo, hi]."""
    if band is None:
        return True
    if confidence is None:
        return False
    lo, hi = band
    return lo <= float(confidence) <= hi


def transform(
    picks: Iterable[dict],
    source_strategy: str,
    new_strategy_name: str,
    only_if_confidence_in: tuple[float, float] | None = None,
    exclude_symbols: set[str] | frozenset[str] | None = None,
) -> list[dict]:
    """Produce inverted copies of picks belonging to `source_strategy`.

    Arguments:
      picks: iterable of pick dicts. Only picks whose `strategy` field matches
        `source_strategy` are considered; all others are silently skipped.
      source_strategy: strategy name to match (exact equality on the
        `strategy` field).
      new_strategy_name: value to set on the `strategy` field of the inverted
        copies. Must differ from `source_strategy` — otherwise the wrapper
        would overwrite the original tag and collide with the upstream
        aggregator.
      only_if_confidence_in: optional inclusive band `(lo, hi)`. Picks whose
        confidence falls outside are dropped.
      exclude_symbols: optional set of symbols to skip. Used to protect the
        source strategy's known edge subset from being inverted.

    Returns a new list of inverted pick dicts. Original picks are not mutated.

    Each inverted pick has:
      - direction flipped (LONG↔SHORT, BUY↔SELL)
      - take_profit and stop_loss mirrored around entry_price
      - strategy set to new_strategy_name
      - source_system set to "inverse_<source_strategy>"
      - extra.inverted_from populated with audit trail
    """
    if source_strategy == new_strategy_name:
        raise ValueError(
            "new_strategy_name must differ from source_strategy to avoid "
            "aggregator collisions"
        )
    excluded = frozenset(exclude_symbols or ())
    out: list[dict] = []
    n_scanned = 0
    n_wrong_strategy = 0
    n_band_filtered = 0
    n_symbol_excluded = 0
    n_unknown_direction = 0
    for pick in picks:
        n_scanned += 1
        if not isinstance(pick, dict):
            continue
        if pick.get("strategy") != source_strategy:
            n_wrong_strategy += 1
            continue
        if pick.get("symbol") in excluded:
            n_symbol_excluded += 1
            continue
        confidence = pick.get("confidence")
        if not _in_band(confidence, only_if_confidence_in):
            n_band_filtered += 1
            continue
        direction = pick.get("direction") or pick.get("signal")
        flipped = _flip_direction(direction) if direction else None
        if flipped is None:
            n_unknown_direction += 1
            continue
        entry = pick.get("entry_price")
        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")
        if entry is None or tp is None or sl is None:
            n_unknown_direction += 1
            continue
        inverted = copy.deepcopy(pick)
        inverted_tp, inverted_sl = _swap_prices(float(entry), float(tp), float(sl))
        # Preserve whichever direction field the source uses
        if "direction" in pick:
            inverted["direction"] = flipped
        if "signal" in pick:
            inverted["signal"] = flipped
        inverted["take_profit"] = inverted_tp
        inverted["stop_loss"] = inverted_sl
        inverted["strategy"] = new_strategy_name
        inverted["source_system"] = f"inverse_{source_strategy}"
        extra = inverted.setdefault("extra", {})
        extra["inverted_from"] = {
            "original_strategy": source_strategy,
            "original_direction": direction,
            "original_tp": float(tp),
            "original_sl": float(sl),
        }
        out.append(inverted)
    logger.debug(
        "inverse_wrapper.transform: scanned=%d emitted=%d "
        "wrong_strategy=%d band_filtered=%d symbol_excluded=%d unknown_direction=%d",
        n_scanned, len(out), n_wrong_strategy, n_band_filtered,
        n_symbol_excluded, n_unknown_direction,
    )
    return out
