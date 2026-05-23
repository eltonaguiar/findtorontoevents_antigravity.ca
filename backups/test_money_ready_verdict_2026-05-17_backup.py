"""Tests for M-061: money_ready_verdict() unified edge verdict."""
import pytest
from unittest.mock import patch


def _make_picks(n_won, n_lost, asset_class="COMMODITY", strategy="test_strat"):
    picks = []
    for i in range(n_won):
        picks.append({
            "strategy": strategy, "asset_class": asset_class,
            "status": "WON", "pnl_pct": 0.05,
        })
    for i in range(n_lost):
        picks.append({
            "strategy": strategy, "asset_class": asset_class,
            "status": "LOST", "pnl_pct": -0.02,
        })
    return picks


class TestMoneyReadyVerdict:
    def test_insufficient_data_below_min_n(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict, MIN_N_CLASS
        picks = _make_picks(10, 5, asset_class="BOND")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        assert results["BOND"]["verdict"] == "INSUFFICIENT_DATA"
        assert results["BOND"]["n_resolved"] == 15
        assert results["BOND"]["n_ok"] is False

    def test_not_ready_poor_wr(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(10, 90, asset_class="FOREX")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        assert results["FOREX"]["verdict"] in ("NOT_READY", "INSUFFICIENT_DATA")
        assert results["FOREX"]["wr"] < 0.50

    def test_money_ready_high_edge(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        # High WR, high PF, sufficient n — should be MONEY_READY or at minimum WATCH
        picks = _make_picks(n_won=400, n_lost=100, asset_class="COMMODITY", strategy="cot_positioning")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        assert results["COMMODITY"]["wr"] == pytest.approx(0.80, abs=0.01)
        assert results["COMMODITY"]["pf"] > 1.5
        assert results["COMMODITY"]["verdict"] in ("MONEY_READY", "WATCH")

    def test_blocked_strategies_excluded(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(200, 50, strategy="bad_strat")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value={"bad_strat"}):
                with patch("alpha_engine.money_ready_verdict._load_dashboard_health", return_value={}):
                    results = money_ready_verdict()
        assert "COMMODITY" not in results or results["COMMODITY"]["n_resolved"] == 0

    def test_asset_class_filter(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = (
            _make_picks(100, 50, asset_class="COMMODITY")
            + _make_picks(100, 50, asset_class="EQUITY")
        )
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict(asset_class="COMMODITY")
        assert "COMMODITY" in results
        assert "EQUITY" not in results

    def test_returns_expected_keys(self):
        from alpha_engine.money_ready_verdict import money_ready_verdict
        picks = _make_picks(60, 40, asset_class="ETF")
        with patch("alpha_engine.money_ready_verdict._load_picks", return_value=picks):
            with patch("alpha_engine.money_ready_verdict._load_blocked", return_value=set()):
                results = money_ready_verdict()
        r = results["ETF"]
        for key in ("n_resolved", "wr", "pf", "n_ok", "wr_ok", "pf_ok", "dsr_ok", "pbo_ok", "spa_ok", "verdict"):
            assert key in r, f"Missing key: {key}"
        assert r["verdict"] in ("MONEY_READY", "WATCH", "NOT_READY", "INSUFFICIENT_DATA")
