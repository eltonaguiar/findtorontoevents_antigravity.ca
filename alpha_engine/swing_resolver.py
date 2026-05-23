"""Phase 9 swing resolver for swing picks.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows.

Replaces the buggy non-crypto path in `outcome_resolver.py:384-405`. Key
behavioural fix versus the legacy implementation:

* When the next-bar OPEN gaps **through** a stop (LONG: open < stop_loss;
  SHORT: open > stop_loss) the realized exit MUST be the bar OPEN price,
  not the stop price. The legacy path printed the stop value as the exit
  and silently understated losses on gap moves. The
  `test_resolver_uses_open_for_gap_not_intrabar_spot` regression test in
  `tests/test_swing_resolver.py` pins this fix.

Same-bar TP and SL ambiguity is resolved conservatively: SL wins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Optional

from alpha_engine.long_term_pick_contract import is_swing


SwingReason = Literal["tp_hit", "sl_hit", "time_stop", "still_active"]


@dataclass
class BarOHLC:
    """One OHLCV bar. `date` is an ISO-8601 string; everything else float."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class ResolverDecision:
    """Outcome of evaluating a single swing pick against a bar history."""

    should_close: bool
    reason: SwingReason
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    realized_pnl_pct: Optional[float] = None
    bars_held: int = 0
    entry_price: float = 0.0
    take_profit: float = 0.0
    stop_loss: float = 0.0
    triggered_rules: list[str] = field(default_factory=list)


def _pnl_pct(direction: str, entry_price: float, exit_price: float) -> float:
    if entry_price == 0:
        return 0.0
    side = (direction or "").upper()
    if side == "SHORT":
        return (entry_price - exit_price) / entry_price
    # Default: LONG
    return (exit_price - entry_price) / entry_price


class SwingResolver:
    """Resolve swing picks against an OHLCV history.

    Resolution rules (per SYNTHESIS.md §6, Resolver split — locked):

    * LONG TP: any post-entry bar with `bar.high >= take_profit`.
    * LONG SL: any post-entry bar with `bar.low <= stop_loss`.
    * SHORT TP: any post-entry bar with `bar.low <= take_profit`.
    * SHORT SL: any post-entry bar with `bar.high >= stop_loss`.
    * Same-bar TP and SL: SL wins (conservative).
    * Gap fills: if a bar's OPEN is already past the stop (LONG: open < SL;
      SHORT: open > SL), `exit_price = bar.open`. THIS is the bug-fix vs
      the legacy resolver which printed the SL value.
    * Time-stop: if no TP/SL after `max_bars_held` bars, close at the close
      of bar `entry_bar_idx + max_bars_held`.
    * Non-swing picks short-circuit to `still_active`.

    Parameters
    ----------
    win_threshold_pct:
        Reserved for future use (currently informational); a realized
        |pnl_pct| below this can be treated as a draw by the caller.
        Default 0.001 (10bps).
    max_bars_held:
        Hard time-stop in bar count from `entry_bar_idx`. Default 30.
    """

    def __init__(
        self,
        *,
        win_threshold_pct: float = 0.001,
        max_bars_held: int = 30,
    ) -> None:
        if max_bars_held <= 0:
            raise ValueError("max_bars_held must be > 0")
        self._win_threshold_pct = float(win_threshold_pct)
        self._max_bars_held = int(max_bars_held)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def resolve(
        self,
        pick: dict[str, Any],
        bars: list[BarOHLC] | Iterable[BarOHLC],
        entry_bar_idx: int = 0,
    ) -> ResolverDecision:
        # Short-circuit for non-swing picks.
        if not is_swing(pick):
            return ResolverDecision(
                should_close=False,
                reason="still_active",
                entry_price=float(pick.get("entry_price", 0.0) or 0.0),
                take_profit=float(pick.get("take_profit", 0.0) or 0.0),
                stop_loss=float(pick.get("stop_loss", 0.0) or 0.0),
            )

        bars_list = list(bars)
        direction = (pick.get("direction") or "LONG").upper()
        entry_price = float(pick.get("entry_price", 0.0) or 0.0)
        take_profit = float(pick.get("take_profit", 0.0) or 0.0)
        stop_loss = float(pick.get("stop_loss", 0.0) or 0.0)

        # Sanity: entry_bar_idx must point at a valid bar.
        if entry_bar_idx < 0 or entry_bar_idx >= len(bars_list):
            return ResolverDecision(
                should_close=False,
                reason="still_active",
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
            )

        max_bar_idx = min(
            entry_bar_idx + self._max_bars_held,
            len(bars_list) - 1,
        )
        # We start scanning from the bar AFTER entry — entry bar fills at
        # entry_price by construction.
        first_eval_idx = entry_bar_idx + 1
        if first_eval_idx > max_bar_idx:
            # Not enough forward history yet to evaluate.
            return ResolverDecision(
                should_close=False,
                reason="still_active",
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                bars_held=max(0, len(bars_list) - 1 - entry_bar_idx),
            )

        for idx in range(first_eval_idx, max_bar_idx + 1):
            bar = bars_list[idx]
            bars_held = idx - entry_bar_idx

            # --- LONG resolution -------------------------------------------------
            if direction == "LONG":
                # Gap-down through SL — exit at OPEN, not SL.
                if bar.open <= stop_loss:
                    exit_price = float(bar.open)
                    return ResolverDecision(
                        should_close=True,
                        reason="sl_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        triggered_rules=["gap_through_stop"],
                    )

                tp_hit = bar.high >= take_profit
                sl_hit = bar.low <= stop_loss

                # Same-bar ambiguity → SL wins.
                if sl_hit:
                    exit_price = float(stop_loss)
                    return ResolverDecision(
                        should_close=True,
                        reason="sl_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        triggered_rules=(
                            ["same_bar_tp_sl"] if tp_hit else []
                        ),
                    )
                if tp_hit:
                    exit_price = float(take_profit)
                    return ResolverDecision(
                        should_close=True,
                        reason="tp_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                    )

            # --- SHORT resolution -----------------------------------------------
            else:  # SHORT
                # Gap-up through SL — exit at OPEN.
                if bar.open >= stop_loss:
                    exit_price = float(bar.open)
                    return ResolverDecision(
                        should_close=True,
                        reason="sl_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        triggered_rules=["gap_through_stop"],
                    )

                tp_hit = bar.low <= take_profit
                sl_hit = bar.high >= stop_loss

                if sl_hit:
                    exit_price = float(stop_loss)
                    return ResolverDecision(
                        should_close=True,
                        reason="sl_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        triggered_rules=(
                            ["same_bar_tp_sl"] if tp_hit else []
                        ),
                    )
                if tp_hit:
                    exit_price = float(take_profit)
                    return ResolverDecision(
                        should_close=True,
                        reason="tp_hit",
                        exit_price=exit_price,
                        exit_date=bar.date,
                        realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                        bars_held=bars_held,
                        entry_price=entry_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                    )

        # No TP/SL hit within the window. Did we exhaust the budget?
        budget_idx = entry_bar_idx + self._max_bars_held
        if budget_idx <= len(bars_list) - 1:
            stop_bar = bars_list[budget_idx]
            exit_price = float(stop_bar.close)
            return ResolverDecision(
                should_close=True,
                reason="time_stop",
                exit_price=exit_price,
                exit_date=stop_bar.date,
                realized_pnl_pct=_pnl_pct(direction, entry_price, exit_price),
                bars_held=self._max_bars_held,
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
            )

        # Still inside the window with not enough bars to time-stop.
        return ResolverDecision(
            should_close=False,
            reason="still_active",
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            bars_held=max(0, len(bars_list) - 1 - entry_bar_idx),
        )

    def resolve_batch(
        self,
        picks: list[dict[str, Any]],
        bars_map: dict[str, list[BarOHLC]],
    ) -> dict[str, ResolverDecision]:
        out: dict[str, ResolverDecision] = {}
        for pick in picks:
            ticker = pick.get("symbol")
            if not ticker:
                continue
            bars = bars_map.get(ticker)
            if not bars:
                # No history → cannot resolve.
                out[ticker] = ResolverDecision(
                    should_close=False,
                    reason="still_active",
                    entry_price=float(pick.get("entry_price", 0.0) or 0.0),
                    take_profit=float(pick.get("take_profit", 0.0) or 0.0),
                    stop_loss=float(pick.get("stop_loss", 0.0) or 0.0),
                )
                continue
            out[ticker] = self.resolve(pick, bars)
        return out
