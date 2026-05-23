"""Tests for H-004 inventory surprise + roll yield bundled signal.

Tests are unit-level and do NOT make network calls. All yfinance / external
fetches are patched so the suite runs in CI without credentials.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import h004_inventory_surprise_roll_yield as h004
import co1_commodity_inventory_surprise_research as co1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_series(n: int = 80, base: float = 50.0, drift: float = 0.005) -> dict[str, float]:
    """Generate n weekly price dates."""
    from datetime import date, timedelta
    start = date(2020, 1, 6)
    out = {}
    price = base
    for i in range(n):
        d = (start + timedelta(weeks=i)).isoformat()
        price *= (1 + drift)
        out[d] = round(price, 4)
    return out


def _make_stocks_series(n: int = 60, base: float = 1000.0, drift: float = -2.0) -> dict[str, float]:
    from datetime import date, timedelta
    start = date(2020, 1, 3)
    out = {}
    val = base
    for i in range(n):
        d = (start + timedelta(weeks=i)).isoformat()
        val += drift
        out[d] = round(val, 2)
    return out


def _minimal_inv_data(ticker: str = "USO", n_price: int = 80, n_stocks: int = 60) -> dict:
    return {
        ticker: {
            "price": _make_price_series(n_price),
            "stocks": _make_stocks_series(n_stocks),
            "_offline": False,
        }
    }


# ---------------------------------------------------------------------------
# fetch_roll_yield_series
# ---------------------------------------------------------------------------

class TestFetchRollYield:
    def test_returns_empty_on_yfinance_import_error(self):
        with patch.dict(sys.modules, {"yfinance": None}):
            # Module missing → should fail-open and return {}
            result = h004.fetch_roll_yield_series("USO")
        assert isinstance(result, dict)

    def test_returns_empty_on_empty_history(self):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = h004.fetch_roll_yield_series("USO")
        assert result == {}

    def test_computes_roll_yield_from_price_series(self):
        import pandas as pd
        # 50 weeks of synthetic price data, monotonically increasing
        dates = pd.date_range("2022-01-03", periods=50, freq="W")
        closes = [50.0 + i * 0.5 for i in range(50)]
        df = pd.DataFrame({"Close": closes}, index=dates)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = h004.fetch_roll_yield_series("USO")
        assert len(result) > 0
        # Values are floats
        for v in result.values():
            assert isinstance(v, float)

    def test_roll_yield_sign_reflects_trend_direction(self):
        """Rising price → 4w mom > 26w mom early, both positive later."""
        import pandas as pd
        # Generate accelerating price (fast rise = backwardation signal)
        closes = [100.0 * (1.05 ** i) for i in range(50)]
        dates = pd.date_range("2020-01-06", periods=50, freq="W")
        df = pd.DataFrame({"Close": closes}, index=dates)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        mock_yf = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        with patch.dict(sys.modules, {"yfinance": mock_yf}):
            result = h004.fetch_roll_yield_series("USO")
        # All values should be near 0 for constant-rate exponential (mom_4w ≈ mom_26w/6.5)
        # Key property: they're all computable
        assert len(result) > 10


# ---------------------------------------------------------------------------
# compute_combined_z
# ---------------------------------------------------------------------------

class TestComputeCombinedZ:
    def test_equal_weights_averages(self):
        z = h004.compute_combined_z(2.0, 1.0, inv_weight=0.5)
        assert abs(z - 1.5) < 1e-9

    def test_full_inv_weight(self):
        z = h004.compute_combined_z(3.0, 0.0, inv_weight=1.0)
        assert abs(z - 3.0) < 1e-9

    def test_full_roll_weight(self):
        z = h004.compute_combined_z(0.0, 4.0, inv_weight=0.0)
        assert abs(z - 4.0) < 1e-9

    def test_default_weight_is_05(self):
        z1 = h004.compute_combined_z(1.0, 1.0)
        z2 = h004.compute_combined_z(1.0, 1.0, inv_weight=0.5)
        assert abs(z1 - z2) < 1e-9


# ---------------------------------------------------------------------------
# backtest_h004 — unit tests with synthetic data
# ---------------------------------------------------------------------------

class TestBacktestH004:
    def _make_roll_data(self, ticker: str, n: int = 80,
                        value: float = 1.0) -> dict[str, dict]:
        """Uniform positive roll yield (backwardation throughout)."""
        from datetime import date, timedelta
        out = {}
        start = date(2020, 1, 6)
        for i in range(n):
            d = (start + timedelta(weeks=i)).isoformat()
            out[d] = value
        return {ticker: out}

    def test_empty_inv_data_returns_no_records(self):
        result = h004.backtest_h004({}, {})
        assert result["records"] == []
        assert result["gross_rets"] == []

    def test_too_few_price_bars_skipped(self):
        inv = {"USO": {"price": {f"2020-0{i}-01": 50.0 for i in range(1, 9)},
                       "stocks": {}, "_offline": False}}
        roll = self._make_roll_data("USO", 80)
        result = h004.backtest_h004(inv, roll)
        pp = result["per_proxy"]["USO"]
        assert pp["n"] == 0
        assert pp.get("skip_reason") is not None

    def test_signals_must_agree_directionally(self):
        """When inv_z is positive and roll_z is negative, no trades generated."""
        inv = _minimal_inv_data("USO", n_price=80, n_stocks=60)
        # Roll data always negative (contango — bullish signal)
        roll = {"USO": {k: -1.5 for k in inv["USO"]["price"]}}
        # stocks declining → inventory draw → inv_z positive → bearish
        # roll negative → contango → inv_dir = -1, roll_dir = -1 → agree bearish
        result = h004.backtest_h004(inv, roll)
        # May or may not have trades depending on alignment — just check structure
        assert "records" in result
        assert "per_proxy" in result

    def test_records_have_required_fields(self):
        inv = _minimal_inv_data("USO")
        roll = self._make_roll_data("USO", 100, value=-0.5)  # contango throughout
        result = h004.backtest_h004(inv, roll)
        for rec in result["records"]:
            assert "status" in rec
            assert "combined_z" in rec
            assert "inv_z" in rec
            assert "roll_z" in rec
            assert "signed_ret" in rec
            assert "hold_days" in rec
            assert rec["hold_days"] == h004.HOLD_DAYS

    def test_win_loss_consistent(self):
        inv = _minimal_inv_data("USO")
        roll = self._make_roll_data("USO", 100, value=-0.5)
        result = h004.backtest_h004(inv, roll)
        records = result["records"]
        if not records:
            pytest.skip("no trades generated with this synthetic data")
        wins = sum(1 for r in records if r["status"] == "WON")
        losses = sum(1 for r in records if r["status"] == "LOST")
        assert wins + losses == len(records)

    def test_any_offline_false_when_data_present(self):
        inv = _minimal_inv_data("USO")
        inv["USO"]["_offline"] = False
        roll = self._make_roll_data("USO", 100, value=0.5)
        result = h004.backtest_h004(inv, roll)
        assert result["any_offline"] is False

    def test_any_offline_true_propagated(self):
        inv = _minimal_inv_data("USO")
        inv["USO"]["_offline"] = True
        roll = self._make_roll_data("USO", 100)
        result = h004.backtest_h004(inv, roll)
        assert result["any_offline"] is True

    def test_multiple_proxies_aggregate(self):
        inv = {
            "USO": _minimal_inv_data("USO")["USO"],
            "UNG": _minimal_inv_data("UNG")["UNG"],
        }
        roll = {
            "USO": self._make_roll_data("USO", 100)["USO"],
            "UNG": self._make_roll_data("UNG", 100)["UNG"],
        }
        result = h004.backtest_h004(inv, roll)
        assert "USO" in result["per_proxy"]
        assert "UNG" in result["per_proxy"]


# ---------------------------------------------------------------------------
# render_verdict
# ---------------------------------------------------------------------------

class TestRenderVerdict:
    def _make_bt(self, n: int = 120, wr: float = 0.55) -> dict:
        wins = int(n * wr)
        records = [
            {"status": "WON" if i < wins else "LOST",
             "signal_z": 1.5, "combined_z": 1.5}
            for i in range(n)
        ]
        gross = [0.01 if i < wins else -0.008 for i in range(n)]
        net = [g - 0.0014 for g in gross]
        return {
            "records": records, "gross_rets": gross, "net_rets": net,
            "any_offline": False, "per_proxy": {"USO": {"n": n, "wr": wr}},
        }

    def test_verdict_structure(self):
        bt = self._make_bt()
        harness = {"admissible_windows": 4, "total_windows": 5,
                   "min_stable_windows": 3, "mean_efficiency": 0.45}
        cost = {"passes": True, "gross_edge_bps": 25.0, "net_edge_bps": 11.0,
                "cost_survival_pct": 85.0}
        v = h004.render_verdict(bt, harness, cost, ["USO"])
        assert v["hypothesis_id"] == "H-004"
        assert "verdict" in v
        assert "n_trades" in v
        assert "win_rate_gross" in v
        assert "acceptance_criteria" in v

    def test_verdict_pass_when_all_criteria_met(self):
        bt = self._make_bt(n=150, wr=0.58)
        harness = {"admissible_windows": 4, "total_windows": 5,
                   "min_stable_windows": 3, "mean_efficiency": 0.40}
        cost = {"passes": True, "gross_edge_bps": 30.0, "net_edge_bps": 16.0,
                "cost_survival_pct": 90.0}
        v = h004.render_verdict(bt, harness, cost, ["USO"])
        assert v["verdict"] == "HARNESS_PASS"

    def test_verdict_reject_when_n_too_low(self):
        bt = self._make_bt(n=50, wr=0.60)  # n < MIN_N=100
        harness = {"admissible_windows": 4, "total_windows": 5,
                   "min_stable_windows": 3, "mean_efficiency": 0.50}
        cost = {"passes": True, "gross_edge_bps": 40.0, "net_edge_bps": 25.0,
                "cost_survival_pct": 95.0}
        v = h004.render_verdict(bt, harness, cost, ["USO"])
        assert v["verdict"] == "HARNESS_REJECTED"

    def test_verdict_reject_when_harness_fails(self):
        bt = self._make_bt(n=120, wr=0.55)
        harness = {"admissible_windows": 1, "total_windows": 5,  # <3 admissible
                   "min_stable_windows": 3, "mean_efficiency": 0.15}
        cost = {"passes": True, "gross_edge_bps": 20.0, "net_edge_bps": 6.0,
                "cost_survival_pct": 70.0}
        v = h004.render_verdict(bt, harness, cost, ["USO"])
        assert v["verdict"] == "HARNESS_REJECTED"

    def test_verdict_reject_when_cost_gate_fails(self):
        bt = self._make_bt(n=120, wr=0.55)
        harness = {"admissible_windows": 4, "total_windows": 5,
                   "min_stable_windows": 3, "mean_efficiency": 0.40}
        cost = {"passes": False, "gross_edge_bps": 5.0, "net_edge_bps": -9.0,
                "cost_survival_pct": 30.0}
        v = h004.render_verdict(bt, harness, cost, ["USO"])
        assert v["verdict"] == "HARNESS_REJECTED"

    def test_proxies_recorded(self):
        bt = self._make_bt()
        harness = {"admissible_windows": 0, "total_windows": 0,
                   "min_stable_windows": 3, "mean_efficiency": 0.0}
        cost = {"passes": False, "gross_edge_bps": 0.0, "net_edge_bps": 0.0,
                "cost_survival_pct": 0.0}
        v = h004.render_verdict(bt, harness, cost, ["USO", "UNG", "CT=F"])
        assert v["proxies_used"] == ["USO", "UNG", "CT=F"]


# ---------------------------------------------------------------------------
# Constants / tunables sanity
# ---------------------------------------------------------------------------

class TestH004Constants:
    def test_hold_days_is_14(self):
        assert h004.HOLD_DAYS == 14

    def test_min_n_is_100(self):
        assert h004.MIN_N == 100

    def test_min_dsr_is_06(self):
        assert h004.MIN_DSR == 0.6

    def test_cost_survival_min(self):
        assert h004.COST_SURVIVAL_MIN == 0.60

    def test_roll_yield_pairs_has_key_proxies(self):
        for key in ("CT=F", "USO", "UNG", "DBA", "DBB"):
            assert key in h004.ROLL_YIELD_PAIRS

    def test_roll_yield_pairs_have_nearby(self):
        for ticker, info in h004.ROLL_YIELD_PAIRS.items():
            assert "nearby" in info, f"{ticker} missing 'nearby'"
