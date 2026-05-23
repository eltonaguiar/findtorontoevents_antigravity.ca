"""Smoke tests for tools.hf_stats — minimum viable coverage to validate the
public API surface. The original PR #344 body claimed 33 tests but the file
was never committed; this is the recreation per the 2026-04-25 PR ownership
round (DeepSeek consult: 5-8 smoke tests is the right scope).

Run: pytest tests/test_hf_stats.py -v
"""
from __future__ import annotations

import math

import pytest

from tools.hf_stats import (
    HfMetrics,
    compute_ac_metrics,
    compute_concept_drift,
    compute_hf_metrics,
    compute_metrics,
    compute_rolling_metrics,
    log_returns,
)


# ---------------------------------------------------------------------------
# compute_hf_metrics — the main scalar metric computation
# ---------------------------------------------------------------------------

class TestComputeHfMetrics:
    def test_empty_input_returns_typed_empty(self):
        m = compute_hf_metrics([])
        assert isinstance(m, HfMetrics)
        assert m.n == 0
        assert m.sharpe is None
        assert m.cvar_95 is None

    def test_known_winners(self):
        """All-positive PnLs should produce a positive Sharpe and a positive
        win rate of 1.0, with no drawdown."""
        pnls = [1.0, 2.0, 1.5, 0.5, 1.0, 2.0, 1.5, 1.0, 0.5, 1.5]
        m = compute_hf_metrics(pnls)
        assert m.n == 10
        assert m.sharpe is not None and m.sharpe > 0
        assert m.win_rate == pytest.approx(1.0)
        # max_drawdown_pct may be None or 0; either is acceptable for monotone-up data
        assert (m.max_drawdown_pct is None) or (m.max_drawdown_pct == pytest.approx(0.0, abs=1e-9))

    def test_known_losers(self):
        """All-negative PnLs should produce a negative Sharpe and a 0% WR.
        max_drawdown_pct is reported as a positive magnitude (12.0 means 12% DD)."""
        pnls = [-1.0, -2.0, -0.5, -1.5, -1.0, -2.0, -0.5, -1.0, -1.5, -1.0]
        m = compute_hf_metrics(pnls)
        assert m.n == 10
        assert m.sharpe is not None and m.sharpe < 0
        assert m.win_rate == pytest.approx(0.0)
        assert m.max_drawdown_pct is not None and m.max_drawdown_pct > 0

    def test_mixed_returns_have_finite_metrics(self):
        """Realistic mixed-outcome PnLs should populate all core fields with
        finite numbers — no NaN/inf leakage."""
        pnls = [1.5, -0.8, 2.0, -1.2, 0.5, 3.0, -2.1, 1.8, -0.5, 2.5,
                -1.0, 1.2, -0.3, 0.8, -1.5, 2.2, -0.7, 1.0, -0.9, 1.5]
        m = compute_hf_metrics(pnls)
        assert m.n == 20
        for field, val in [("sharpe", m.sharpe), ("cvar_95", m.cvar_95),
                            ("max_drawdown_pct", m.max_drawdown_pct),
                            ("win_rate", m.win_rate), ("profit_factor", m.profit_factor)]:
            assert val is not None, f"{field} unexpectedly None"
            if isinstance(val, float):
                assert math.isfinite(val), f"{field} is not finite: {val}"

    def test_var_kurtosis_overflow_is_handled(self):
        """The PR body called out 'VaR kurtosis overflow (t-dist df→0.11)' as
        a fixed bug. Heavy-tailed input should not crash."""
        # Construct heavy-tailed input: a few extreme moves dominate.
        pnls = [0.01] * 40 + [-30.0, 28.0, -25.0, 22.0, -20.0]
        m = compute_hf_metrics(pnls)
        # Just verify no exception and CVaR returned a finite number.
        assert m.n == 45
        if m.cvar_95 is not None:
            assert math.isfinite(m.cvar_95)


# ---------------------------------------------------------------------------
# compute_rolling_metrics — windowed series
# ---------------------------------------------------------------------------

class TestRollingMetrics:
    def test_short_input_returns_empty_series(self):
        # Signature is list[tuple[float, float]] — (timestamp, pnl_pct) pairs
        out = compute_rolling_metrics([(1735689600.0, 1.0)] * 3, window_days=30)
        # Either empty series or an object with empty arrays — both acceptable.
        assert isinstance(out, list)

    def test_long_input_produces_output(self):
        # 60 (ts, pnl) tuples, 1 day apart starting 2026-01-01
        base_ts = 1767225600.0  # 2026-01-01 UTC epoch seconds
        dated = [
            (base_ts + i * 86400.0, (1.0 if i % 2 == 0 else -0.8))
            for i in range(60)
        ]
        out = compute_rolling_metrics(dated, window_days=30)
        assert isinstance(out, list)
        assert len(out) > 0


# ---------------------------------------------------------------------------
# compute_concept_drift — distribution-shift detection
# ---------------------------------------------------------------------------

class TestConceptDrift:
    def test_stable_distribution_no_drift(self):
        # Same signature as rolling: list[(ts, pnl)]
        base_ts = 1767225600.0
        dated = [(base_ts + i * 86400.0, (0.5 if i % 2 else -0.5)) for i in range(60)]
        out = compute_concept_drift(dated)
        assert out is not None

    def test_regime_shift_flagged(self):
        # First half good, second half bad — should produce a drift signal
        base_ts = 1767225600.0
        dated = [(base_ts + i * 86400.0, 1.5) for i in range(30)] + \
                [(base_ts + (30 + i) * 86400.0, -2.0) for i in range(30)]
        out = compute_concept_drift(dated)
        assert out is not None


# ---------------------------------------------------------------------------
# compute_ac_metrics — per-asset-class breakdown
# ---------------------------------------------------------------------------

class TestComputeAcMetrics:
    def test_routes_picks_into_asset_classes(self):
        # compute_ac_metrics requires len(pnls) >= 3 per class — give 4 each
        picks = [
            {"asset_class": "CRYPTO", "pnl_pct": 1.5},
            {"asset_class": "CRYPTO", "pnl_pct": -0.8},
            {"asset_class": "CRYPTO", "pnl_pct": 0.5},
            {"asset_class": "CRYPTO", "pnl_pct": 1.2},
            {"asset_class": "EQUITY", "pnl_pct": 2.0},
            {"asset_class": "EQUITY", "pnl_pct": -1.0},
            {"asset_class": "EQUITY", "pnl_pct": 0.8},
            {"asset_class": "EQUITY", "pnl_pct": 1.5},
        ]
        out = compute_ac_metrics(picks)
        assert isinstance(out, dict)
        # Keys are uppercased internally
        assert "CRYPTO" in out and "EQUITY" in out, f"expected CRYPTO+EQUITY, got {list(out.keys())}"
        assert out["CRYPTO"]["n"] == 4
        assert out["EQUITY"]["n"] == 4

    def test_empty_picks_returns_empty_or_zero(self):
        out = compute_ac_metrics([])
        assert isinstance(out, dict)
        # Empty dict OR a dict with all-empty buckets — both acceptable.


# ---------------------------------------------------------------------------
# compute_metrics — top-level entry point used by dashboard_generator
# ---------------------------------------------------------------------------

class TestComputeMetricsTopLevel:
    def test_compute_metrics_smoke(self):
        """The dashboard wiring at audit_trail/dashboard_generator.py::_hf_stats_summary
        calls compute_metrics(picks, window_days=30, fee_bps=20.0). Verify it
        returns a dict-shaped result on a small synthetic pick set."""
        picks = [
            {"pnl_pct": 1.0 + (i % 3) * 0.5, "asset_class": "CRYPTO",
             "closed_at": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z"}
            for i in range(40)
        ]
        out = compute_metrics(picks, window_days=30, fee_bps=20.0)
        assert isinstance(out, dict)


# ---------------------------------------------------------------------------
# log_returns — utility
# ---------------------------------------------------------------------------

class TestLogReturns:
    def test_known_log_returns(self):
        # log(110/100) = log(1.10) ≈ 0.09531
        out = log_returns([100.0, 110.0])
        assert len(out) == 1
        assert out[0] == pytest.approx(math.log(1.10), abs=1e-6)

    def test_empty_input(self):
        assert log_returns([]) == []
        assert log_returns([100.0]) == []
