"""PBO rows must be the SAME calendar periods (2026-11-20).

The old builders stacked each strategy's own pick sequence onto shared rows
(``v[:T]`` in ``tools/run_anti_overfit_audit.py``, ``[-min_len:]`` in the
sidecar). Two strategies that traded in different months were therefore
compared as if row 0 happened at the same time, so the CPCV split mixed eras and
the PBO logit measured the calendar rather than the selection process.

These tests pin the alignment itself: a pick belongs to the period of its exit
timestamp, a strategy flat in a period is 0.0, and the real periods are what
reach ``cpcv_pbo``.
"""
from __future__ import annotations

import numpy as np
import pytest

from alpha_engine.anti_overfit_validator import (
    align_returns_by_period,
    cpcv_pbo,
)


def _days(month: str, days, ret: float):
    return [(f"2026-{month}-{d:02d}T12:00:00+00:00", ret) for d in days]


def test_picks_land_on_their_own_date_not_on_their_index():
    a = _days("01", range(1, 9), 0.01)
    b = _days("02", range(1, 9), -0.02)
    M, periods, info = align_returns_by_period({"A": a, "B": b}, min_obs=2, period="D")
    assert M.shape == (16, 2)
    assert info["coverage_pct"] == 50.0
    ai, bi = info["strategies"].index("A"), info["strategies"].index("B")
    assert M[0, ai] == pytest.approx(0.01)
    assert M[0, bi] == 0.0
    assert M[-1, bi] == pytest.approx(-0.02)
    assert M[-1, ai] == 0.0


def test_no_row_mixes_two_different_months():
    """The bug in one assertion: stacking would put A's Jan pick beside B's Feb one."""
    a = _days("01", range(1, 9), 0.01)
    b = _days("02", range(1, 9), -0.02)
    M, _periods, info = align_returns_by_period({"A": a, "B": b}, min_obs=2, period="D")
    ai, bi = info["strategies"].index("A"), info["strategies"].index("B")
    assert not any(M[r, ai] != 0 and M[r, bi] != 0 for r in range(M.shape[0]))


def test_same_day_picks_are_averaged():
    a = [("2026-01-05T01:00:00+00:00", 0.02),
         ("2026-01-05T23:00:00+00:00", -0.01),
         ("2026-01-06T00:00:00+00:00", 0.0)]
    b = [("2026-01-05T00:00:00+00:00", 0.01),
         ("2026-01-06T00:00:00+00:00", 0.01)]
    M, _periods, info = align_returns_by_period({"A": a, "B": b}, min_obs=2, period="D")
    ai = info["strategies"].index("A")
    assert M[0, ai] == pytest.approx(0.005)


def test_auto_period_escalates_until_there_are_enough_rows():
    a = [(f"2026-01-{d:02d}T00:00:00+00:00", 0.01) for d in range(1, 6)]
    b = [(f"2026-02-{d:02d}T00:00:00+00:00", 0.01) for d in range(1, 6)]
    M, _periods, info = align_returns_by_period({"A": a, "B": b}, min_obs=2, min_rows=16)
    assert info["period"] == "M"
    assert info["escalated_from"] == ["D", "W"]
    assert M.shape == (2, 2)


def test_one_strategy_is_not_a_pbo_matrix():
    M, periods, info = align_returns_by_period(
        {"A": _days("01", range(1, 5), 0.01)}, min_obs=2
    )
    assert M is None and periods == []
    assert "PBO needs >= 2" in info["note"]


def test_untimestamped_picks_are_dropped_and_counted():
    a = _days("01", range(1, 5), 0.01) + [(None, 0.5), ("not-a-date", 0.5)]
    b = _days("01", range(1, 5), 0.01)
    M, _periods, info = align_returns_by_period({"A": a, "B": b}, min_obs=2, period="D")
    assert info["dropped_untimestamped_picks"] == 2
    assert M.max() == pytest.approx(0.01)  # the two 0.5 outliers never entered


def test_cpcv_pbo_accepts_real_periods_and_validates_them():
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(7)
    T, S = 60, 4
    M = rng.normal(0, 0.01, size=(T, S))
    periods = [d.to_pydatetime() for d in pd.date_range("2024-01-01", periods=T, freq="D")]
    pbo = cpcv_pbo(M, n_folds=6, n_test_groups=2, period_index=periods)
    assert 0.0 <= pbo <= 1.0
    with pytest.raises(ValueError):
        cpcv_pbo(M, n_folds=6, period_index=periods[:-1])
    with pytest.raises(ValueError):
        cpcv_pbo(M, n_folds=6, period_index=list(reversed(periods)))


def test_tool_matrix_is_time_aligned():
    from tools.run_anti_overfit_audit import _build_pbo_matrix

    a = _days("01", range(1, 21), 0.01)
    b = _days("02", range(1, 21), -0.01)
    M, periods, info = _build_pbo_matrix({"A": a, "B": b}, min_obs=10)
    assert M is not None
    assert M.shape == (40, 2)
    assert periods == sorted(periods)
    assert info["period"] == "D"
    assert info["coverage_pct"] == 50.0
