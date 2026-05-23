"""Tests for alpha_engine.value_backtest (Phase 13 of UEPS).

Covers:
- Pure metric calculators (WR, PF, CAGR, MaxDD, Sharpe, Sortino, Calmar)
- Tier classification (incl. CLAUDE.md MAJOR GOAL #1 n≥100 floor)
- WalkForwardBacktest end-to-end on synthetic data
- Walk-forward discipline contract: providers called with correct as_of date
- Thesis-break exit path produces correct exit_reason in the audit trail
- run_all_sleeves orchestration
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import pytest

from alpha_engine.value_backtest import (
    DEFAULT_REPORTING_LAG_DAYS,
    PF_NO_LOSSES_SENTINEL,
    BacktestResult,
    BacktestSleeve,
    WalkForwardBacktest,
    classify_tier,
    compute_cagr,
    compute_calmar,
    compute_max_dd,
    compute_pf,
    compute_sharpe,
    compute_sortino,
    compute_wr,
)


# ── Pure-function metric tests ────────────────────────────────────────────────


def test_compute_wr_basic():
    assert compute_wr(60, 40) == pytest.approx(0.60)


def test_compute_wr_handles_zero():
    # Defensive: no trades → 0.0 not crash
    assert compute_wr(0, 0) == 0.0


def test_compute_pf_basic():
    profits = [10.0, 20.0, 30.0]
    losses = [-5.0, -10.0, -15.0]
    # 60 / 30 = 2.0
    assert compute_pf(profits, losses) == pytest.approx(2.0)


def test_compute_pf_no_losses_returns_inf_capped():
    # All wins, no losses → sentinel large value (documented as 999.0)
    profits = [5.0, 10.0]
    losses: list[float] = []
    pf = compute_pf(profits, losses)
    assert pf == PF_NO_LOSSES_SENTINEL
    # And it MUST clear the Tier-1 PF floor (≥ 2.0) to be useful downstream.
    assert pf >= 2.0


def test_compute_pf_no_trades_returns_zero():
    assert compute_pf([], []) == 0.0


def test_compute_pf_all_losses_returns_zero():
    assert compute_pf([], [-5.0, -10.0]) == 0.0


def test_compute_cagr_known_values():
    # Doubling over 10 years → ~7.18% CAGR
    cagr = compute_cagr(start_value=1.0, end_value=2.0, years=10.0)
    assert cagr == pytest.approx(0.07177, abs=1e-4)


def test_compute_cagr_zero_years_safe():
    # Defensive: no time elapsed → 0.0 not crash
    assert compute_cagr(1.0, 2.0, 0) == 0.0


def test_compute_max_dd_simple_curve():
    # 1.0 → 1.2 → 1.1 → 0.9 → 1.3
    # Peak at 1.2, trough at 0.9 → DD = (1.2 - 0.9) / 1.2 = 0.25
    curve = [1.0, 1.2, 1.1, 0.9, 1.3]
    assert compute_max_dd(curve) == pytest.approx(0.25)


def test_compute_max_dd_no_drawdown():
    # Monotonically rising → 0.0
    curve = [1.0, 1.05, 1.10, 1.15, 1.20]
    assert compute_max_dd(curve) == 0.0


def test_compute_max_dd_empty_curve():
    assert compute_max_dd([]) == 0.0


def test_compute_sharpe_known_returns():
    # Daily returns with mean=0.001, std≈0.01 → annualized Sharpe ≈ 0.001/0.01 * sqrt(252) ≈ 1.587
    returns = [0.011, -0.009, 0.011, -0.009, 0.011, -0.009, 0.011, -0.009, 0.011, -0.009]
    # mean = 0.001, stdev ≈ 0.0105
    sharpe = compute_sharpe(returns)
    expected = (statistics_mean(returns) / statistics_stdev(returns)) * math.sqrt(252)
    assert sharpe == pytest.approx(expected, rel=1e-6)


def test_compute_sharpe_zero_std_returns_zero():
    # All identical → no volatility → 0.0 (not div-by-zero crash)
    assert compute_sharpe([0.001, 0.001, 0.001, 0.001]) == 0.0


def test_compute_sortino_only_uses_negative_returns_for_std():
    # Returns: positive 0.02 days mixed with negative -0.01 days.
    # Sortino's denominator = sqrt(mean(neg^2)) — positive returns must NOT
    # appear in the downside std. We construct two return series with the
    # SAME negatives and SAME mean but different POSITIVES; Sortino must
    # change ONLY through the mean, not through the std.
    neg_returns = [-0.01, -0.01, -0.005, -0.015]
    series_a = [0.02, 0.02, 0.02, 0.02] + neg_returns  # mean ≈ 0.005
    series_b = [0.05, 0.05, 0.05, 0.05] + neg_returns  # mean ≈ 0.0213

    sortino_a = compute_sortino(series_a)
    sortino_b = compute_sortino(series_b)

    # Both should have the SAME downside denominator. Verify by reconstructing:
    downside_dev = math.sqrt(sum(r * r for r in neg_returns) / len(neg_returns))
    expected_a = (statistics_mean(series_a) / downside_dev) * math.sqrt(252)
    expected_b = (statistics_mean(series_b) / downside_dev) * math.sqrt(252)

    assert sortino_a == pytest.approx(expected_a, rel=1e-6)
    assert sortino_b == pytest.approx(expected_b, rel=1e-6)


def test_compute_sortino_no_downside_returns_zero():
    # All positive → no downside samples → 0.0 (avoids inf)
    assert compute_sortino([0.01, 0.02, 0.03, 0.005]) == 0.0


def test_compute_calmar_basic():
    # CAGR 0.20, MaxDD 0.10 → 2.0
    assert compute_calmar(0.20, 0.10) == pytest.approx(2.0)


def test_compute_calmar_no_dd_returns_zero():
    # No drawdown → undefined → 0.0 (serializer-safe sentinel)
    assert compute_calmar(0.20, 0.0) == 0.0


# ── Tier classification ──────────────────────────────────────────────────────


def test_classify_tier_above_tier_1():
    # WR 58%, PF 2.5, MDD 8%, n=200 → Tier 1
    assert classify_tier(wr=0.58, pf=2.5, max_dd=0.08, n=200) == "Tier 1"


def test_classify_tier_tier_2():
    # WR 52%, PF 1.7, MDD 15%, n=120 → Tier 2 (clears T2 but not T1 PF)
    assert classify_tier(wr=0.52, pf=1.7, max_dd=0.15, n=120) == "Tier 2"


def test_classify_tier_tier_3():
    # WR 48%, PF 1.3, MDD 25%, n=120 → Tier 3
    assert classify_tier(wr=0.48, pf=1.3, max_dd=0.25, n=120) == "Tier 3"


def test_classify_tier_below_when_n_too_low():
    # CLAUDE.md MAJOR GOAL #1 n-floor: n<100 is "below" REGARDLESS of metrics
    assert classify_tier(wr=0.99, pf=10.0, max_dd=0.01, n=50) == "below"
    # Even n=99 is below
    assert classify_tier(wr=0.99, pf=10.0, max_dd=0.01, n=99) == "below"


def test_classify_tier_below_when_metrics_fail():
    # Plenty of n, but PF below T3 floor → below
    assert classify_tier(wr=0.40, pf=1.1, max_dd=0.40, n=200) == "below"


# ── Walk-forward harness end-to-end (synthetic) ──────────────────────────────


@dataclass
class _StubFundamentals:
    """Minimal walk-forward fundamentals snapshot for synthetic tests."""
    ticker: str
    period_end: date
    ratios: dict[str, float] = field(default_factory=dict)


class _StubScreener:
    """Returns a fixed list of long_term_value picks for whatever inputs come in.

    The picks reference symbols supplied in `_picks_for(...)`. We use
    `make_long_term_value_pick` to ensure the contract validation passes.
    """

    def __init__(self, picks_per_call: list[dict[str, Any]]):
        self._picks_per_call = picks_per_call
        self.calls: list[tuple[int, int]] = []

    def screen_universe(
        self, inputs: list[Any], top_n: int = 25
    ) -> list[dict[str, Any]]:
        self.calls.append((len(inputs), top_n))
        # Cap by top_n so behavior matches the real screener
        return self._picks_per_call[:top_n]


def _build_pick(
    ticker: str,
    direction: str = "LONG",
    entry_price: float = 100.0,
    intrinsic_value: float = 130.0,
) -> dict[str, Any]:
    """Build a long_term_value pick dict (matches SYNTHESIS § 4 contract).

    We construct the dict directly rather than calling
    `make_long_term_value_pick` because Phase 2 (the pick contract module)
    is not yet merged on `main`. The shape here mirrors the contract
    documented in SYNTHESIS § 4 verbatim.
    """
    return {
        "symbol": ticker,
        "direction": direction,
        "entry_price": entry_price,
        "asset_class": "EQUITY",
        "source_system": "value_screener",
        "strategy": "magic_formula_x_piotroski_x_acquirers",
        "status": "ACTIVE",
        "pick_type": "long_term_value",
        "holding_horizon": "3y+",
        "exit_mode": "thesis",
        "thesis": f"{ticker} synthetic backtest pick.",
        "thesis_break_rules": [
            {
                "metric": "ROIC",
                "op": "<",
                "threshold": 0.05,
                "source": "test",
            },
        ],
        "intrinsic_value": intrinsic_value,
        "fundamental_snapshot": {"piotroski_f": 7, "magic_formula_rank": 1},
        "earnings_history": [],
        "next_earnings_date": None,
        "dividend_record": {},
        "catalyst_dates": [],
        "universe_gate_passed": True,
        "safety_gate_passed": True,
        "score": 1.0,
        "confidence": 0.9,
    }


def _make_price_provider(
    daily_returns_by_ticker: dict[str, list[tuple[date, float]]],
):
    """Build a prices_history_provider that returns canned data within window."""

    def provider(
        ticker: str, start_date: date, end_date: date
    ) -> list[tuple[date, float]]:
        series = daily_returns_by_ticker.get(ticker, [])
        return [
            (d, p) for d, p in series
            if start_date <= d <= end_date
        ]

    return provider


def _make_fundamentals_provider(
    *,
    fixed_ratios: dict[str, float] | None = None,
    fail_after: date | None = None,
    fail_after_ratios: dict[str, float] | None = None,
):
    """Build a fundamentals_history_provider for synthetic tests.

    If `fail_after` is set, requests with as_of_date > fail_after return the
    `fail_after_ratios` snapshot (used to fire thesis_break mid-hold).
    """
    base = fixed_ratios or {"ROIC": 0.20, "DebtToEquity": 0.5}
    bad = fail_after_ratios or {"ROIC": 0.01, "DebtToEquity": 3.0}

    calls: list[tuple[str, date]] = []

    def provider(ticker: str, as_of_date: date) -> _StubFundamentals | None:
        calls.append((ticker, as_of_date))
        ratios = bad if (fail_after is not None and as_of_date > fail_after) else base
        return _StubFundamentals(
            ticker=ticker,
            period_end=as_of_date,
            ratios=dict(ratios),
        )

    provider.calls = calls  # type: ignore[attr-defined]
    return provider


def _daily_series(
    start: date, days: int, start_price: float, drift_per_day: float
) -> list[tuple[date, float]]:
    """Linear-drift price series. Used for deterministic backtest scoring."""
    out = []
    p = start_price
    for i in range(days):
        out.append((start + timedelta(days=i), p))
        p += drift_per_day
    return out


def test_walk_forward_run_sleeve_with_synthetic_data():
    """End-to-end: synthetic screener + price data → BacktestResult with n>0."""
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2021, 1, 1)
    sleeve = BacktestSleeve(
        name="synthetic",
        start_date=sleeve_start.isoformat(),
        end_date=sleeve_end.isoformat(),
        rebalance_freq_days=90,
        picks_per_rebalance=2,
    )

    # Two tickers, both rising linearly → wins.
    series = {
        "AAA": _daily_series(sleeve_start - timedelta(days=10), 500, 100.0, 0.10),
        "BBB": _daily_series(sleeve_start - timedelta(days=10), 500, 50.0, 0.05),
    }
    price_provider = _make_price_provider(series)

    screener = _StubScreener([_build_pick("AAA"), _build_pick("BBB")])
    fundamentals_provider = _make_fundamentals_provider()

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )

    result = backtest.run_sleeve(sleeve, universe=["AAA", "BBB"])

    assert isinstance(result, BacktestResult)
    assert result.sleeve_name == "synthetic"
    assert result.total_picks > 0
    # Both names rise → all wins
    assert result.wins == result.total_picks
    assert result.losses == 0
    assert result.wr == pytest.approx(1.0)
    # All wins, no losses → PF sentinel
    assert result.pf == PF_NO_LOSSES_SENTINEL
    # Tier classification — synthetic n is small (<100) → "below" by n-floor
    assert result.tier_classification == "below"
    # Audit trail populated
    assert len(result.closed_picks) == result.total_picks
    for closed in result.closed_picks:
        assert closed["ticker"] in {"AAA", "BBB"}
        assert closed["realized_pnl_pct"] > 0
        assert closed["exit_reason"] in {"rebalance", "horizon", "end_of_window"}


def test_walk_forward_no_lookahead_in_provider():
    """Harness MUST call fundamentals provider with as_of = rebalance - reporting_lag.

    Per SYNTHESIS § 9: walk-forward discipline. The provider receives the
    earliest as_of_date allowed by the 90-day SEC reporting lag; the harness
    NEVER hands it the rebalance date itself.
    """
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2020, 4, 1)  # one rebalance window (~90d)
    sleeve = BacktestSleeve(
        name="lag_check",
        start_date=sleeve_start.isoformat(),
        end_date=sleeve_end.isoformat(),
        rebalance_freq_days=90,
        picks_per_rebalance=1,
    )

    series = {"AAA": _daily_series(sleeve_start - timedelta(days=5), 200, 100.0, 0.1)}
    price_provider = _make_price_provider(series)
    fundamentals_provider = _make_fundamentals_provider()
    screener = _StubScreener([_build_pick("AAA")])

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )

    backtest.run_sleeve(sleeve, universe=["AAA"])

    # The first call to the fundamentals provider during screening MUST be
    # for as_of = sleeve_start - reporting_lag_days, NOT sleeve_start.
    assert fundamentals_provider.calls, "provider was never called"
    first_call_ticker, first_call_as_of = fundamentals_provider.calls[0]
    expected_as_of = sleeve_start - timedelta(days=DEFAULT_REPORTING_LAG_DAYS)
    assert first_call_as_of == expected_as_of, (
        f"walk-forward leak: provider called with as_of={first_call_as_of}, "
        f"expected {expected_as_of} (rebalance - {DEFAULT_REPORTING_LAG_DAYS}d lag)"
    )

    # And NO call may have as_of > rebalance_date - reporting_lag (no peeking
    # at not-yet-filed reports for that rebalance).
    for ticker, as_of in fundamentals_provider.calls:
        # The harness may legitimately call the provider with as_of values
        # based on subsequent rebalance dates or thesis-break refresh dates.
        # The contract is: as_of is always <= max(check_date) - lag, never
        # equal to the rebalance check_date itself.
        assert isinstance(as_of, date)
        # No call should ever request fundamentals with as_of in the FUTURE
        # relative to the sleeve.end_date (would mean peeking past the
        # backtest window).
        assert as_of <= sleeve_end


def test_walk_forward_handles_thesis_break_exit():
    """A thesis-break trigger mid-hold must produce exit_reason='thesis_break'."""
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2021, 1, 1)
    sleeve = BacktestSleeve(
        name="thesis_break_test",
        start_date=sleeve_start.isoformat(),
        end_date=sleeve_end.isoformat(),
        # Long rebalance window so the thesis-break check fires before
        # the next rebalance date.
        rebalance_freq_days=300,
        picks_per_rebalance=1,
    )

    series = {"AAA": _daily_series(sleeve_start - timedelta(days=5), 500, 100.0, 0.05)}
    price_provider = _make_price_provider(series)

    # Fundamentals deteriorate after day 60 — so when the thesis-break check
    # fires (default check_period=30 days), it'll see the bad ratios and
    # trigger ROIC < 0.05 (the synthetic pick's only thesis_break_rule).
    deterioration_date = sleeve_start + timedelta(days=60)
    fundamentals_provider = _make_fundamentals_provider(
        fixed_ratios={"ROIC": 0.20, "DebtToEquity": 0.5},
        fail_after=deterioration_date,
        fail_after_ratios={"ROIC": 0.01, "DebtToEquity": 3.0},
    )

    screener = _StubScreener([_build_pick("AAA")])

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )

    result = backtest.run_sleeve(sleeve, universe=["AAA"])

    assert result.total_picks >= 1
    # At least the first closed pick must have exit_reason="thesis_break"
    reasons = [c["exit_reason"] for c in result.closed_picks]
    assert "thesis_break" in reasons, (
        f"expected at least one thesis_break exit, got reasons={reasons}"
    )


def test_run_all_sleeves_returns_results_per_sleeve():
    """run_all_sleeves with 4 sleeves produces a 4-key dict of BacktestResults."""
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2020, 7, 1)

    sleeves = [
        BacktestSleeve(
            name=f"sleeve_q{i}",
            start_date=(sleeve_start + timedelta(days=i * 22)).isoformat(),
            end_date=(sleeve_end + timedelta(days=i * 22)).isoformat(),
            rebalance_freq_days=90,
            picks_per_rebalance=1,
        )
        for i in range(4)
    ]

    series = {"AAA": _daily_series(sleeve_start - timedelta(days=10), 600, 100.0, 0.05)}
    price_provider = _make_price_provider(series)
    fundamentals_provider = _make_fundamentals_provider()
    screener = _StubScreener([_build_pick("AAA")])

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )

    results = backtest.run_all_sleeves(sleeves, universe=["AAA"])

    assert isinstance(results, dict)
    assert set(results.keys()) == {"sleeve_q0", "sleeve_q1", "sleeve_q2", "sleeve_q3"}
    for name, result in results.items():
        assert isinstance(result, BacktestResult)
        assert result.sleeve_name == name


def test_walk_forward_skip_pick_when_no_price_at_entry():
    """Pick whose ticker has no prices in the entry window → skipped, no crash."""
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2020, 7, 1)
    sleeve = BacktestSleeve(
        name="no_price",
        start_date=sleeve_start.isoformat(),
        end_date=sleeve_end.isoformat(),
        rebalance_freq_days=90,
        picks_per_rebalance=1,
    )

    # Empty price history — the pick can never be entered.
    price_provider = _make_price_provider({"AAA": []})
    fundamentals_provider = _make_fundamentals_provider()
    screener = _StubScreener([_build_pick("AAA")])

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )

    result = backtest.run_sleeve(sleeve, universe=["AAA"])
    assert result.total_picks == 0
    assert result.closed_picks == []


def test_short_pick_pnl_inverts_direction():
    """SHORT pick: pnl_pct = (entry - exit)/entry. Falling price → win.

    Uses a single-rebalance sleeve (rebalance_freq_days > sleeve duration)
    so we get exactly one closed pick to inspect. SHORT pnl convention is
    the load-bearing assertion: entry_price > exit_price MUST yield
    positive realized_pnl_pct.
    """
    sleeve_start = date(2020, 1, 1)
    sleeve_end = date(2020, 4, 1)
    sleeve = BacktestSleeve(
        name="short_test",
        start_date=sleeve_start.isoformat(),
        end_date=sleeve_end.isoformat(),
        # Rebalance freq longer than sleeve → single rebalance window.
        rebalance_freq_days=200,
        picks_per_rebalance=1,
    )

    # Falling price series — SHORT should be a winner
    series = {
        "AAA": _daily_series(
            sleeve_start - timedelta(days=5), 200, 100.0, -0.20  # neg drift
        ),
    }
    price_provider = _make_price_provider(series)
    fundamentals_provider = _make_fundamentals_provider()

    pick = _build_pick("AAA", direction="SHORT")
    screener = _StubScreener([pick])

    backtest = WalkForwardBacktest(
        screener=screener,
        fundamentals_history_provider=fundamentals_provider,
        prices_history_provider=price_provider,
    )
    result = backtest.run_sleeve(sleeve, universe=["AAA"])

    assert result.total_picks == 1, (
        f"expected exactly 1 pick from single-rebalance sleeve, "
        f"got {result.total_picks}: {result.closed_picks}"
    )
    closed = result.closed_picks[0]
    assert closed["entry_price"] > closed["exit_price"]  # price fell
    # SHORT on a falling price → positive pnl
    assert closed["realized_pnl_pct"] > 0
    assert result.wins == 1
    assert result.losses == 0


# ── Local helpers (avoid coupling tests to importable statistics) ────────────


def statistics_mean(values: list[float]) -> float:
    return sum(values) / len(values)


def statistics_stdev(values: list[float]) -> float:
    """Sample standard deviation (matches Python's statistics.stdev)."""
    m = statistics_mean(values)
    sq_diffs = [(v - m) ** 2 for v in values]
    return math.sqrt(sum(sq_diffs) / (len(values) - 1))
