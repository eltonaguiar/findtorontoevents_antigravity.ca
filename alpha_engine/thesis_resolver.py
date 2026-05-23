"""Phase 8 thesis resolver for long_term_value picks.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows.

CRITICAL CONSTRAINT (per SYNTHESIS.md §6, Resolver split — locked):
This resolver MUST NOT close positions on price drawdown alone. Only valid
exits for a long_term_value pick are:
  1. Thesis-break rule triggered (delegated to
     `long_term_pick_contract.evaluate_thesis_break`).
  2. Hard time-stop at the `holding_horizon` expiry.
  3. Intrinsic-value attainment (current_price within `iv_attainment_pct`
     of `intrinsic_value`, side-aware).

The legacy non-crypto path in `outcome_resolver.py:384-405` is broken (it
closes at yfinance spot every run with a 1bp WIN threshold) and must NOT
be reused. This module is the canonical replacement for long-term picks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from alpha_engine.long_term_pick_contract import (
    evaluate_thesis_break,
    is_long_term_value,
)


ResolverReason = Literal["thesis_break", "time_stop", "iv_attained", "still_active"]


# Holding-horizon → calendar-day budget. Anything not listed defaults to
# the longest budget so we err on the side of NOT closing prematurely.
_HORIZON_DAYS: dict[str, int] = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "3m": 90,
    "1y": 365,
    "3y+": 1095,
}


@dataclass
class ResolverDecision:
    """Outcome of evaluating a single long_term_value pick."""

    should_close: bool
    reason: ResolverReason
    triggered_rules: list[str] = field(default_factory=list)
    current_price: Optional[float] = None
    current_metrics: dict[str, float] = field(default_factory=dict)
    days_held: int = 0


def _parse_entry_datetime(pick: dict[str, Any]) -> Optional[datetime]:
    """Best-effort extraction of the pick's entry timestamp.

    Tries (in order): `entry_timestamp`, `entry_time`, `entry_date`,
    `created_at`, `timestamp`. Accepts ISO-8601 strings with or without
    a `Z` suffix, and naive datetimes (which are treated as UTC).
    """
    candidates = (
        "entry_timestamp",
        "entry_time",
        "entry_date",
        "created_at",
        "timestamp",
    )
    for key in candidates:
        raw = pick.get(key)
        if raw is None:
            continue
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                continue
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                # Try date-only
                try:
                    dt = datetime.fromisoformat(text + "T00:00:00+00:00")
                except ValueError:
                    continue
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def _horizon_budget_days(pick: dict[str, Any]) -> int:
    horizon = pick.get("holding_horizon", "3y+")
    return _HORIZON_DAYS.get(horizon, _HORIZON_DAYS["3y+"])


def _iv_attained(
    direction: str,
    current_price: float,
    intrinsic_value: float,
    iv_attainment_pct: float,
) -> bool:
    """Side-aware intrinsic-value attainment check."""
    side = (direction or "").upper()
    if intrinsic_value is None or intrinsic_value <= 0:
        return False
    if side == "LONG":
        # LONG closes when price has rallied to (almost) the IV.
        return current_price >= intrinsic_value * (1.0 - iv_attainment_pct)
    if side == "SHORT":
        # SHORT closes when price has fallen to (almost) the IV.
        return current_price <= intrinsic_value * (1.0 + iv_attainment_pct)
    return False


class ThesisResolver:
    """Resolve long_term_value picks via thesis / IV / time, never drawdown.

    Parameters
    ----------
    fundamentals_fetcher:
        Callable `(pick: dict) -> dict[str, float]` returning the current
        fundamental metrics for the pick's underlying. Keys should match
        the `metric` fields used in the pick's `thesis_break_rules` (e.g.
        "ROIC", "DebtToEquity", "ConsecutiveEarningsMisses"). May return
        `{}` when the data provider is unavailable — in that case no
        thesis-break rule can fire.
    iv_attainment_pct:
        Tolerance for intrinsic-value attainment. Default 0.05 (5%).
    """

    def __init__(
        self,
        fundamentals_fetcher: Callable[[dict[str, Any]], dict[str, float]],
        *,
        iv_attainment_pct: float = 0.05,
    ) -> None:
        if not callable(fundamentals_fetcher):
            raise TypeError("fundamentals_fetcher must be callable")
        if iv_attainment_pct < 0:
            raise ValueError("iv_attainment_pct must be >= 0")
        self._fetch_metrics = fundamentals_fetcher
        self._iv_attainment_pct = float(iv_attainment_pct)

    def resolve(
        self,
        pick: dict[str, Any],
        current_price: float,
        now: Optional[datetime] = None,
    ) -> ResolverDecision:
        """Decide whether to close the pick. Drawdown alone NEVER closes."""
        # Short-circuit: only handle long_term_value picks.
        if not is_long_term_value(pick):
            return ResolverDecision(
                should_close=False,
                reason="still_active",
                current_price=current_price,
                days_held=0,
            )

        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        entry_dt = _parse_entry_datetime(pick)
        days_held = 0 if entry_dt is None else max(
            0, int((now - entry_dt).total_seconds() // 86400)
        )

        # Pull current fundamentals up-front. If the fetcher returns None,
        # treat as empty dict so thesis_break simply won't fire.
        try:
            current_metrics = self._fetch_metrics(pick) or {}
        except Exception:
            current_metrics = {}

        # 1) Thesis break — highest priority.
        broken, triggered = evaluate_thesis_break(pick, current_metrics)
        if broken:
            return ResolverDecision(
                should_close=True,
                reason="thesis_break",
                triggered_rules=triggered,
                current_price=current_price,
                current_metrics=current_metrics,
                days_held=days_held,
            )

        # 2) Intrinsic-value attainment.
        intrinsic_value = pick.get("intrinsic_value")
        direction = pick.get("direction", "LONG")
        if (
            intrinsic_value is not None
            and isinstance(intrinsic_value, (int, float))
            and intrinsic_value > 0
            and _iv_attained(
                direction,
                float(current_price),
                float(intrinsic_value),
                self._iv_attainment_pct,
            )
        ):
            return ResolverDecision(
                should_close=True,
                reason="iv_attained",
                current_price=current_price,
                current_metrics=current_metrics,
                days_held=days_held,
            )

        # 3) Hard time-stop at horizon expiry.
        budget = _horizon_budget_days(pick)
        if entry_dt is not None and days_held >= budget:
            return ResolverDecision(
                should_close=True,
                reason="time_stop",
                current_price=current_price,
                current_metrics=current_metrics,
                days_held=days_held,
            )

        # 4) Healthy thesis — drawdown does NOT close. Stay active.
        return ResolverDecision(
            should_close=False,
            reason="still_active",
            current_price=current_price,
            current_metrics=current_metrics,
            days_held=days_held,
        )

    def resolve_batch(
        self,
        picks: list[dict[str, Any]],
        price_map: dict[str, float],
        now: Optional[datetime] = None,
    ) -> dict[str, ResolverDecision]:
        """Resolve a batch keyed by ticker (`symbol`). Missing prices skip."""
        out: dict[str, ResolverDecision] = {}
        for pick in picks:
            ticker = pick.get("symbol")
            if not ticker:
                continue
            current_price = price_map.get(ticker)
            if current_price is None:
                # No price available — cannot evaluate IV; still try thesis/time.
                # Use NaN-safe default of entry_price so the decision can run.
                current_price = float(pick.get("entry_price", 0.0) or 0.0)
            out[ticker] = self.resolve(pick, float(current_price), now=now)
        return out
