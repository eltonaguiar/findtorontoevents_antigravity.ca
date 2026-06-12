"""P1-A: money_ready_verdict intrabar sizing source tests."""
import pytest

from alpha_engine.money_ready_verdict import (
    MIN_INTRABAR_N_FOR_SIZING,
    _sizing_metrics_from_intrabar,
)


class TestSizingMetricsFromIntrabar:
    def test_prefers_intrabar_when_n_sufficient(self, monkeypatch):
        monkeypatch.setenv("MONEY_READY_SIZING_SOURCE", "intrabar")
        n, wr, pf, src = _sizing_metrics_from_intrabar(
            200, 0.57, 1.2, {"n": 88, "wr": 0.42, "pf": 1.13}
        )
        assert src == "intrabar_truth"
        assert n == 88
        assert wr == pytest.approx(0.42)
        assert pf == pytest.approx(1.13)

    def test_insufficient_intrabar_keeps_policy(self, monkeypatch):
        monkeypatch.setenv("MONEY_READY_SIZING_SOURCE", "intrabar")
        n, wr, pf, src = _sizing_metrics_from_intrabar(
            200, 0.57, 1.2, {"n": 12, "wr": 0.75, "pf": 2.0}
        )
        assert src == "insufficient_intrabar"
        assert n == 200
        assert wr == pytest.approx(0.57)

    def test_policy_clean_override(self, monkeypatch):
        monkeypatch.setenv("MONEY_READY_SIZING_SOURCE", "policy_clean")
        n, wr, pf, src = _sizing_metrics_from_intrabar(
            200, 0.57, 1.2, {"n": 88, "wr": 0.42, "pf": 1.13}
        )
        assert src == "policy_clean"
        assert n == 200

    def test_threshold_constant(self):
        assert MIN_INTRABAR_N_FOR_SIZING == 30
