"""Tests for alpha_engine.thesis_resolver.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 14 GHA workflows.

The most important test in this file is
`test_resolver_does_not_close_on_price_drawdown`. The legacy
`outcome_resolver.py:384-405` path mislabeled ~1700 non-crypto picks by
closing on intrabar spot moves; the long-term resolver MUST NOT do that.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from alpha_engine.long_term_pick_contract import make_long_term_value_pick, make_swing_pick
from alpha_engine.thesis_resolver import ResolverDecision, ThesisResolver

# Reuse the fixtures from the contract test module so the two suites stay
# in sync. Importing from a sibling test module is allowed in pytest.
from tests.test_long_term_pick_contract import (
    SAMPLE_DIVIDEND_RECORD,
    SAMPLE_EARNINGS_HISTORY,
    SAMPLE_FUNDAMENTAL_SNAPSHOT,
    SAMPLE_THESIS_BREAK_RULES,
)


HEALTHY_METRICS = {
    "ROIC": 0.18,
    "DebtToEquity": 0.42,
    "ConsecutiveEarningsMisses": 0,
}

BROKEN_ROIC_METRICS = {
    "ROIC": 0.10,  # below the 0.126 threshold
    "DebtToEquity": 0.45,
    "ConsecutiveEarningsMisses": 0,
}


def _make_pick(
    *,
    symbol: str = "AAPL",
    direction: str = "LONG",
    entry_price: float = 180.0,
    intrinsic_value: float = 215.0,
    holding_horizon: str = "3y+",
    entry_date: str | None = "2024-01-01T00:00:00+00:00",
) -> dict:
    pick = make_long_term_value_pick(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        intrinsic_value=intrinsic_value,
        thesis="Trades cheap to intrinsic with strong fundamentals.",
        thesis_break_rules=SAMPLE_THESIS_BREAK_RULES,
        fundamental_snapshot=SAMPLE_FUNDAMENTAL_SNAPSHOT,
        earnings_history=SAMPLE_EARNINGS_HISTORY,
        next_earnings_date="2026-08-01",
        dividend_record=SAMPLE_DIVIDEND_RECORD,
        catalyst_dates=["2026-08-01"],
        holding_horizon=holding_horizon,  # type: ignore[arg-type]
    )
    if entry_date is not None:
        pick["entry_timestamp"] = entry_date
    return pick


def _resolver(metrics: dict) -> ThesisResolver:
    return ThesisResolver(fundamentals_fetcher=lambda _pick: metrics)


# ---------------------------------------------------------------------------
# CRITICAL REGRESSION TEST — drawdown alone never closes a long-term pick.
# ---------------------------------------------------------------------------
def test_resolver_does_not_close_on_price_drawdown():
    """A 25% drawdown with a healthy thesis is NOT a close signal.

    This is the bug that broke ~1700 non-crypto picks via
    outcome_resolver.py. If this test ever fails, the resolver has
    regressed to spot-price closes and the long-term system is unsafe.
    """
    pick = _make_pick(entry_price=180.0)
    resolver = _resolver(HEALTHY_METRICS)

    # Entry was 30 days ago — well inside the 3y+ horizon.
    now = datetime(2024, 1, 31, tzinfo=timezone.utc)
    # Price down 25% from entry.
    decision = resolver.resolve(pick, current_price=135.0, now=now)

    assert isinstance(decision, ResolverDecision)
    assert decision.should_close is False
    assert decision.reason == "still_active"
    assert decision.days_held == 30
    assert decision.triggered_rules == []


def test_resolver_closes_on_thesis_break():
    pick = _make_pick()
    resolver = _resolver(BROKEN_ROIC_METRICS)
    now = datetime(2024, 6, 1, tzinfo=timezone.utc)
    decision = resolver.resolve(pick, current_price=178.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "thesis_break"
    assert any("ROIC" in rule for rule in decision.triggered_rules)


def test_resolver_closes_on_time_stop():
    """1y horizon, 400 days held → time_stop fires."""
    entry = "2023-01-01T00:00:00+00:00"
    pick = _make_pick(holding_horizon="1y", entry_date=entry)
    resolver = _resolver(HEALTHY_METRICS)
    now = datetime(2024, 2, 5, tzinfo=timezone.utc)  # ~400 days later
    decision = resolver.resolve(pick, current_price=200.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "time_stop"
    assert decision.days_held >= 365


def test_resolver_closes_on_iv_attainment_long():
    """LONG: current_price >= IV*0.95 → iv_attained."""
    pick = _make_pick(direction="LONG", intrinsic_value=215.0)
    resolver = _resolver(HEALTHY_METRICS)
    now = datetime(2024, 3, 1, tzinfo=timezone.utc)
    # 215 * 0.95 = 204.25 — anything at/above closes.
    decision = resolver.resolve(pick, current_price=205.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "iv_attained"


def test_resolver_closes_on_iv_attainment_short():
    """SHORT: current_price <= IV*1.05 → iv_attained."""
    pick = _make_pick(direction="SHORT", entry_price=215.0, intrinsic_value=180.0)
    resolver = _resolver(HEALTHY_METRICS)
    now = datetime(2024, 3, 1, tzinfo=timezone.utc)
    # 180 * 1.05 = 189.0 — anything at/below closes.
    decision = resolver.resolve(pick, current_price=188.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "iv_attained"


def test_resolver_only_handles_long_term_value_picks():
    """Swing picks must short-circuit to still_active (not crash)."""
    swing = make_swing_pick(
        symbol="MSFT",
        direction="LONG",
        entry_price=410.0,
        take_profit=440.0,
        stop_loss=395.0,
    )
    resolver = _resolver(HEALTHY_METRICS)
    decision = resolver.resolve(swing, current_price=380.0)
    assert decision.should_close is False
    assert decision.reason == "still_active"


def test_resolver_iv_long_does_not_fire_below_threshold():
    """LONG below IV*0.95 stays active even though direction matches."""
    pick = _make_pick(direction="LONG", intrinsic_value=215.0)
    resolver = _resolver(HEALTHY_METRICS)
    now = datetime(2024, 3, 1, tzinfo=timezone.utc)
    # 215 * 0.95 = 204.25; 200 < threshold → still active.
    decision = resolver.resolve(pick, current_price=200.0, now=now)
    assert decision.should_close is False
    assert decision.reason == "still_active"


def test_resolver_thesis_break_takes_precedence_over_time_stop():
    """Thesis break wins even when the time-stop budget is also exhausted."""
    pick = _make_pick(holding_horizon="1m", entry_date="2024-01-01T00:00:00+00:00")
    resolver = _resolver(BROKEN_ROIC_METRICS)
    now = datetime(2024, 6, 1, tzinfo=timezone.utc)  # well past 30d budget
    decision = resolver.resolve(pick, current_price=180.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "thesis_break"


def test_resolver_thesis_break_takes_precedence_over_iv():
    """Thesis break wins over IV attainment on the same evaluation."""
    pick = _make_pick(direction="LONG", intrinsic_value=215.0)
    resolver = _resolver(BROKEN_ROIC_METRICS)
    now = datetime(2024, 3, 1, tzinfo=timezone.utc)
    decision = resolver.resolve(pick, current_price=210.0, now=now)
    assert decision.should_close is True
    assert decision.reason == "thesis_break"


def test_resolver_handles_missing_entry_timestamp():
    """No entry timestamp → cannot time-stop, must rely on thesis/IV/active."""
    pick = _make_pick(entry_date=None)
    resolver = _resolver(HEALTHY_METRICS)
    decision = resolver.resolve(pick, current_price=170.0)
    assert decision.should_close is False
    assert decision.reason == "still_active"
    assert decision.days_held == 0


def test_resolver_iv_attainment_pct_is_configurable():
    """A 1% tolerance should keep a barely-up stock active."""
    pick = _make_pick(direction="LONG", intrinsic_value=215.0)
    strict = ThesisResolver(
        fundamentals_fetcher=lambda _p: HEALTHY_METRICS,
        iv_attainment_pct=0.01,
    )
    now = datetime(2024, 3, 1, tzinfo=timezone.utc)
    # 215 * 0.99 = 212.85; price=210 stays active.
    decision = strict.resolve(pick, current_price=210.0, now=now)
    assert decision.should_close is False


def test_resolve_batch_handles_mix():
    """Batch with healthy + thesis-broken + time-stopped picks resolves each."""
    healthy = _make_pick(symbol="HEAL", entry_date="2024-06-01T00:00:00+00:00")
    broken = _make_pick(symbol="BRKN", entry_date="2024-06-01T00:00:00+00:00")
    timed = _make_pick(
        symbol="TIME",
        holding_horizon="1m",
        entry_date="2024-01-01T00:00:00+00:00",
    )

    metrics_map = {
        "HEAL": HEALTHY_METRICS,
        "BRKN": BROKEN_ROIC_METRICS,
        "TIME": HEALTHY_METRICS,
    }

    def fetcher(pick):
        return metrics_map[pick["symbol"]]

    resolver = ThesisResolver(fundamentals_fetcher=fetcher)
    now = datetime(2024, 6, 15, tzinfo=timezone.utc)
    out = resolver.resolve_batch(
        [healthy, broken, timed],
        price_map={"HEAL": 170.0, "BRKN": 178.0, "TIME": 175.0},
        now=now,
    )
    assert out["HEAL"].reason == "still_active"
    assert out["BRKN"].reason == "thesis_break"
    assert out["TIME"].reason == "time_stop"


def test_resolve_batch_skips_picks_without_symbol():
    pick_with = _make_pick(symbol="HEAL")
    pick_without = _make_pick(symbol="HEAL")
    pick_without.pop("symbol", None)
    resolver = _resolver(HEALTHY_METRICS)
    out = resolver.resolve_batch(
        [pick_with, pick_without],
        price_map={"HEAL": 170.0},
        now=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
    assert "HEAL" in out
    assert len(out) == 1


def test_resolver_constructor_validates_fetcher():
    with pytest.raises(TypeError):
        ThesisResolver(fundamentals_fetcher="not-callable")  # type: ignore[arg-type]


def test_resolver_constructor_validates_iv_pct():
    with pytest.raises(ValueError):
        ThesisResolver(
            fundamentals_fetcher=lambda _p: {},
            iv_attainment_pct=-0.1,
        )
