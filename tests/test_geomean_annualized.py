"""Unit tests for the fixed total_pnl_pct_geomean_annualized computation.

Covers:
  - Normal case: realistic equity curve, plausible CAGR returned.
  - Explosive/degenerate input: result is hard-clamped, never 9999.
  - Thin data (< 2 trades, < 30-day span): returns None.
  - Bankrupt curve: clamps to the -99.9 floor, not -infinity or NaN.

The function intentionally lives at module-import scope in
``audit_trail.dashboard_generator``. We import it directly.
"""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from audit_trail.dashboard_generator import (  # noqa: E402
    _ANNUALIZED_CEIL_PCT,
    _ANNUALIZED_FLOOR_PCT,
    _annualize_cagr,
    _compound_per_day_geomean_annualized,
)


def _mk_pick(ts: str, pnl_pct: float) -> dict:
    return {"timestamp": ts, "pnl_pct": pnl_pct}


def _spread(start: str, n: int, pnl_each: float, days_span: int):
    """Create n picks spread linearly across `days_span` days starting at start."""
    t0 = datetime.fromisoformat(start)
    out = []
    for i in range(n):
        frac = (i / max(1, n - 1)) if n > 1 else 0.0
        t = t0 + timedelta(days=frac * days_span)
        out.append(_mk_pick(t.isoformat(), pnl_each))
    return out


# ---------- _annualize_cagr direct ----------


def test_annualize_cagr_normal():
    # 2x equity over 365.25 days → +100% CAGR.
    out = _annualize_cagr(2.0, 1.0, 365.25)
    assert out is not None
    assert 99.0 < out < 101.0


def test_annualize_cagr_clamps_explosive_upside():
    # 1000x equity in 30 days → astronomical CAGR; must clamp to ceiling.
    out = _annualize_cagr(1000.0, 1.0, 30.0)
    assert out == _ANNUALIZED_CEIL_PCT
    assert out < 9999  # never the old sentinel


def test_annualize_cagr_clamps_floor_on_blowup():
    out = _annualize_cagr(1e-9, 1.0, 90.0)
    assert out == _ANNUALIZED_FLOOR_PCT


def test_annualize_cagr_thin_returns_none():
    assert _annualize_cagr(1.5, 1.0, 5.0) is None
    assert _annualize_cagr(1.5, 1.0, 0.0) is None


def test_annualize_cagr_bad_inputs_return_none():
    assert _annualize_cagr(0.0, 1.0, 90.0) is None
    assert _annualize_cagr(1.0, 0.0, 90.0) is None
    assert _annualize_cagr(-1.0, 1.0, 90.0) is None


# ---------- _compound_per_day_geomean_annualized ----------


def test_thin_trade_count_returns_none():
    # Only 1 trade — below _ANNUALIZE_MIN_TRADES.
    picks = [_mk_pick("2026-01-01T00:00:00", 1.0)]
    assert _compound_per_day_geomean_annualized(picks) is None


def test_thin_span_returns_none():
    # 5 trades but span only 10 days — below _ANNUALIZE_MIN_DAYS.
    picks = _spread("2026-01-01T00:00:00", n=5, pnl_each=0.5, days_span=10)
    assert _compound_per_day_geomean_annualized(picks) is None


def test_normal_case_returns_sane_cagr():
    # 60 trades, +0.3% each, over 180 days → modest positive CAGR, in bounds.
    picks = _spread("2026-01-01T00:00:00", n=60, pnl_each=0.3, days_span=180)
    out = _compound_per_day_geomean_annualized(picks)
    assert out is not None
    assert _ANNUALIZED_FLOOR_PCT < out < _ANNUALIZED_CEIL_PCT
    # Equity ≈ 1.003**60 ≈ 1.197; annualized over 180d ≈ ~41%. Allow loose band.
    assert 20.0 < out < 80.0


def test_explosive_input_is_clamped_not_9999():
    # 200 trades, capped at +10% each (the function's max_pnl_pct), 31 days.
    # Equity = 1.10**200 = ~1.9e8 ; annualized factor 365.25/31 ≈ 11.78.
    # Naive computation → ~1e94 % CAGR. Must clamp to ceiling, never 9999.
    picks = _spread("2026-01-01T00:00:00", n=200, pnl_each=50.0, days_span=31)
    out = _compound_per_day_geomean_annualized(picks)
    assert out is not None
    assert out == _ANNUALIZED_CEIL_PCT
    assert out != 9999.0
    assert out < 1000.0


def test_bankrupt_curve_clamps_to_floor():
    # A long stream of large losses (capped at -10%/trade) should drive
    # equity toward zero and clamp to the floor (or at minimum a strongly
    # negative, in-bounds value — never NaN/inf and never above 0).
    picks = _spread("2026-01-01T00:00:00", n=200, pnl_each=-50.0, days_span=120)
    out = _compound_per_day_geomean_annualized(picks)
    assert out is not None
    assert out <= -90.0
    assert out >= _ANNUALIZED_FLOOR_PCT


def test_no_picks_returns_none():
    assert _compound_per_day_geomean_annualized([]) is None


def test_malformed_timestamps_skipped():
    picks = [
        _mk_pick("not-a-date", 1.0),
        _mk_pick("", 1.0),
    ] + _spread("2026-01-01T00:00:00", n=10, pnl_each=0.2, days_span=90)
    out = _compound_per_day_geomean_annualized(picks)
    assert out is not None
    assert _ANNUALIZED_FLOOR_PCT <= out <= _ANNUALIZED_CEIL_PCT


def test_result_never_equals_old_sentinel():
    """Regression guard: the field must never emit the 9999 sentinel again."""
    # Try several pathological inputs.
    cases = [
        _spread("2026-01-01T00:00:00", n=500, pnl_each=10.0, days_span=30),
        _spread("2026-01-01T00:00:00", n=2, pnl_each=10.0, days_span=30),
        _spread("2026-01-01T00:00:00", n=1000, pnl_each=5.0, days_span=60),
    ]
    for picks in cases:
        out = _compound_per_day_geomean_annualized(picks)
        assert out != 9999.0
        if out is not None:
            assert _ANNUALIZED_FLOOR_PCT <= out <= _ANNUALIZED_CEIL_PCT
            assert math.isfinite(out)
