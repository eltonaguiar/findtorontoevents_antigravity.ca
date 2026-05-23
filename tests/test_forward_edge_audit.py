"""Tests for tools/forward_edge_audit.py (B16)."""
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure repo root is on path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.forward_edge_audit import (
    wilson_lower_bound,
    picks_per_week,
    safe_pf,
    compute_strategy_stats,
    generate_artifact,
    load_transaction_costs,
    PF_CAP,
)


class TestWilsonLowerBound:
    def test_all_wins(self):
        lb = wilson_lower_bound(10, 10)
        assert 0.70 < lb < 1.0, "10/10 WR lb should be well above 70%"

    def test_half_wins(self):
        lb = wilson_lower_bound(50, 100)
        assert 0.40 < lb < 0.50, "50/100 WR lb should be between 40-50%"

    def test_zero_wins(self):
        assert wilson_lower_bound(0, 10) == 0.0

    def test_zero_n(self):
        assert wilson_lower_bound(0, 0) == 0.0

    def test_known_case_7_wins_7_trades(self):
        # Wilson 95% lb on (7/7) should be ~64.6%
        lb = wilson_lower_bound(7, 7)
        assert 0.60 < lb < 0.70, f"Expected ~64.6%, got {lb:.3f}"

    def test_result_bounded_0_1(self):
        for wins, n in [(0, 5), (1, 1), (25, 50), (99, 100)]:
            lb = wilson_lower_bound(wins, n)
            assert 0.0 <= lb <= 1.0, f"lb={lb} out of range for wins={wins}, n={n}"

    def test_monotone_in_wins(self):
        lbs = [wilson_lower_bound(k, 20) for k in range(1, 20)]
        assert all(lbs[i] <= lbs[i + 1] for i in range(len(lbs) - 1)), \
            "Wilson lb should be non-decreasing in wins"


class TestPicksPerWeek:
    def test_empty(self):
        assert picks_per_week([]) == 0.0

    def test_single_pick(self):
        assert picks_per_week(["2026-04-01T12:00:00Z"]) == 1.0

    def test_weekly_cadence(self):
        # 5 picks across 4 weeks
        dates = [
            "2026-03-01T00:00:00Z",
            "2026-03-08T00:00:00Z",
            "2026-03-15T00:00:00Z",
            "2026-03-22T00:00:00Z",
            "2026-03-29T00:00:00Z",
        ]
        ppw = picks_per_week(dates)
        assert 1.2 < ppw < 1.4, f"Expected ~1.25 picks/wk for 5 picks in 4 wks, got {ppw}"

    def test_none_values_ignored(self):
        dates = [None, "2026-03-01T00:00:00Z", None, "2026-03-08T00:00:00Z"]
        ppw = picks_per_week(dates)
        assert ppw > 0

    def test_invalid_strings_ignored(self):
        dates = ["not-a-date", "2026-03-01T00:00:00Z", "", "2026-03-08T00:00:00Z"]
        ppw = picks_per_week(dates)
        assert ppw > 0


class TestSafePF:
    def test_normal_pf(self):
        pf, capped = safe_pf(20.0, 10.0)
        assert pf == pytest.approx(2.0)
        assert not capped

    def test_zero_losses(self):
        pf, capped = safe_pf(10.0, 0.0)
        assert pf == PF_CAP
        assert capped

    def test_zero_wins_zero_losses(self):
        pf, capped = safe_pf(0.0, 0.0)
        assert pf == 0.0
        assert not capped

    def test_capped(self):
        pf, capped = safe_pf(1000.0, 1.0)
        assert pf == PF_CAP
        assert capped

    def test_capped_above_boundary(self):
        # PF_CAP * 2 / 1 = 100 > PF_CAP → capped
        pf, capped = safe_pf(PF_CAP * 2.0, 1.0)
        assert pf == PF_CAP
        assert capped

    def test_just_below_cap(self):
        pf, capped = safe_pf(49.0, 1.0)
        assert pf == pytest.approx(49.0)
        assert not capped


class TestComputeStrategyStats:
    def _make_pick(self, strategy="strat_a", asset_class="EQUITY",
                   status="WON", pnl_pct=2.0, symbol="AAPL",
                   closed_at="2026-03-15T12:00:00Z"):
        return {
            "strategy": strategy,
            "asset_class": asset_class,
            "status": status,
            "pnl_pct": pnl_pct,
            "symbol": symbol,
            "closed_at": closed_at,
        }

    def _default_costs(self):
        return {"EQUITY": 0.10, "CRYPTO": 0.30, "FOREX": 0.08, "UNKNOWN": 0.20}

    def test_empty_picks(self):
        rows = compute_strategy_stats([], self._default_costs())
        assert rows == []

    def test_unresolved_excluded(self):
        picks = [self._make_pick(status="UNRESOLVED")]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert rows == []

    def test_basic_aggregation(self):
        picks = [
            self._make_pick(status="WON", pnl_pct=2.0, symbol="AAPL"),
            self._make_pick(status="WON", pnl_pct=3.0, symbol="MSFT"),
            self._make_pick(status="LOST", pnl_pct=-1.0, symbol="AAPL"),
        ]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert len(rows) == 1
        r = rows[0]
        assert r["n"] == 3
        assert r["wins"] == 2
        assert r["wr_pct"] == pytest.approx(66.7, abs=0.1)
        assert r["sum_pnl_pct"] == pytest.approx(4.0)

    def test_after_cost_deduction(self):
        picks = [self._make_pick(status="WON", pnl_pct=1.0, asset_class="EQUITY")]
        costs = {"EQUITY": 0.10}
        rows = compute_strategy_stats(picks, costs)
        assert rows[0]["after_cost_mean_pnl_pct"] == pytest.approx(0.90, abs=0.001)
        assert rows[0]["after_cost_sum_pnl_pct"] == pytest.approx(0.90, abs=0.001)

    def test_survives_gates(self):
        # 10 wins out of 10 → WR=100%, Wilson lb high, after-cost positive
        picks = [self._make_pick(status="WON", pnl_pct=2.0) for _ in range(10)]
        costs = {"EQUITY": 0.10}
        rows = compute_strategy_stats(picks, costs)
        assert rows[0]["both_survive"] is True

    def test_fails_both_gates_when_all_lost(self):
        picks = [self._make_pick(status="LOST", pnl_pct=-2.0) for _ in range(10)]
        costs = {"EQUITY": 0.10}
        rows = compute_strategy_stats(picks, costs)
        assert rows[0]["both_survive"] is False
        assert rows[0]["survives_after_cost"] is False

    def test_symbol_concentration(self):
        # 8 picks on AAPL, 2 on MSFT → top-3 share = 100%
        picks = [self._make_pick(symbol="AAPL") for _ in range(8)]
        picks += [self._make_pick(symbol="MSFT") for _ in range(2)]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert rows[0]["top3_share_pct"] == 100.0

    def test_multi_asset_class_split(self):
        # Same strategy, two asset classes → two rows
        picks = [
            self._make_pick(strategy="s", asset_class="EQUITY", pnl_pct=1.0),
            self._make_pick(strategy="s", asset_class="CRYPTO", pnl_pct=-1.0),
        ]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert len(rows) == 2
        acs = {r["asset_class"] for r in rows}
        assert acs == {"EQUITY", "CRYPTO"}

    def test_small_sample_flag(self):
        picks = [self._make_pick(status="WON", pnl_pct=1.0) for _ in range(15)]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert rows[0]["small_sample_flag"] is True  # n=15 < 20

    def test_no_small_sample_flag_at_20(self):
        picks = [self._make_pick(status="WON", pnl_pct=1.0) for _ in range(20)]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert rows[0]["small_sample_flag"] is False

    def test_pf_capped_on_extreme_strategy(self):
        picks = [self._make_pick(status="WON", pnl_pct=100.0)] + \
                [self._make_pick(status="LOST", pnl_pct=-0.01)]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert rows[0]["pf_capped"] is True
        assert rows[0]["pf"] == PF_CAP

    def test_unknown_asset_class_gets_default_cost(self):
        picks = [self._make_pick(asset_class="UNKNOWN", pnl_pct=0.5)]
        costs = {"EQUITY": 0.10, "UNKNOWN": 0.20}
        rows = compute_strategy_stats(picks, costs)
        assert rows[0]["cost_bps"] == pytest.approx(20.0)

    def test_missing_asset_class_uses_unknown(self):
        picks = [self._make_pick(asset_class=None, pnl_pct=0.5)]
        costs = {"UNKNOWN": 0.20}
        rows = compute_strategy_stats(picks, costs)
        assert rows[0]["cost_bps"] == pytest.approx(20.0)

    def test_wilson_lb_field_present(self):
        picks = [self._make_pick(status="WON") for _ in range(10)]
        rows = compute_strategy_stats(picks, self._default_costs())
        assert "wilson_lb_wr_pct" in rows[0]
        assert rows[0]["wilson_lb_wr_pct"] > 0


class TestGenerateArtifact:
    def _sample_rows(self):
        return [
            {
                "strategy": "test_strat", "asset_class": "EQUITY", "n": 20, "wins": 15,
                "losses": 5, "wr_pct": 75.0, "wilson_lb_wr_pct": 53.0, "pf": 2.5,
                "pf_capped": False, "sum_pnl_pct": 30.0, "mean_pnl_pct": 1.5,
                "cost_bps": 10.0, "after_cost_mean_pnl_pct": 1.4, "after_cost_sum_pnl_pct": 28.0,
                "top3_symbols": ["AAPL", "MSFT"], "top3_share_pct": 60.0,
                "picks_per_week": 2.0, "survives_after_cost": True,
                "survives_wilson_50pct": True, "both_survive": True, "small_sample_flag": False,
            }
        ]

    def test_creates_md_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path, json_path = generate_artifact(
                self._sample_rows(), "2026-04-30", Path(tmpdir)
            )
            assert md_path.exists()
            content = md_path.read_text(encoding="utf-8")
            assert "Forward-Only Edge Audit" in content
            assert "test_strat" in content
            assert "CAVEAT" in content

    def test_creates_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path, json_path = generate_artifact(
                self._sample_rows(), "2026-04-30", Path(tmpdir)
            )
            assert json_path.exists()
            data = json.loads(json_path.read_text(encoding="utf-8"))
            assert "generated_at" in data
            assert "strategies" in data
            assert data["summary"]["survivors_count"] == 1

    def test_survivors_in_section1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = self._sample_rows()
            md_path, _ = generate_artifact(rows, "2026-04-30", Path(tmpdir))
            content = md_path.read_text(encoding="utf-8")
            assert "After-Cost Survivors" in content
            assert "test_strat" in content

    def test_zero_wr_strategy_in_section4(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                {
                    "strategy": "dead_strat", "asset_class": "CRYPTO", "n": 15, "wins": 0,
                    "losses": 15, "wr_pct": 0.0, "wilson_lb_wr_pct": 0.0, "pf": 0.0,
                    "pf_capped": False, "sum_pnl_pct": -30.0, "mean_pnl_pct": -2.0,
                    "cost_bps": 30.0, "after_cost_mean_pnl_pct": -2.3, "after_cost_sum_pnl_pct": -34.5,
                    "top3_symbols": ["BTCUSDT"], "top3_share_pct": 100.0,
                    "picks_per_week": 5.0, "survives_after_cost": False,
                    "survives_wilson_50pct": False, "both_survive": False, "small_sample_flag": True,
                }
            ]
            md_path, _ = generate_artifact(rows, "2026-04-30", Path(tmpdir))
            content = md_path.read_text(encoding="utf-8")
            assert "Zero-WR Strategies" in content
            assert "dead_strat" in content

    def test_opt_in_wiring_status_in_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path, json_path = generate_artifact(
                self._sample_rows(), "2026-04-30", Path(tmpdir)
            )
            content = md_path.read_text(encoding="utf-8")
            assert "OPT-IN SIDECAR" in content
            data = json.loads(json_path.read_text(encoding="utf-8"))
            assert "opt-in sidecar" in data["wiring_status"]


class TestTransactionCosts:
    def test_load_returns_dict(self):
        costs = load_transaction_costs()
        assert isinstance(costs, dict)

    def test_required_classes_present(self):
        costs = load_transaction_costs()
        for ac in ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"]:
            assert ac in costs, f"Missing asset class {ac} in transaction_costs.json"

    def test_cost_values_are_positive(self):
        costs = load_transaction_costs()
        for ac, cost in costs.items():
            assert cost > 0, f"Cost for {ac} is not positive: {cost}"

    def test_crypto_cost_higher_than_equity(self):
        costs = load_transaction_costs()
        assert costs["CRYPTO"] > costs["EQUITY"]

    def test_forex_cheaper_than_commodity(self):
        costs = load_transaction_costs()
        assert costs["FOREX"] < costs["COMMODITY"]


class TestIntegration:
    """Run the tool end-to-end against actual dashboard_data.json if available."""

    def test_runs_against_real_data(self):
        data_file = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
        if not data_file.exists():
            pytest.skip("dashboard_data.json not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            costs = load_transaction_costs()
            with open(data_file) as f:
                dashboard = json.load(f)
            picks = dashboard.get("picks", {}).get("recent_closed", [])
            rows = compute_strategy_stats(picks, costs)
            md_path, json_path = generate_artifact(rows, "2026-04-30", Path(tmpdir))
            assert md_path.exists()
            data = json.loads(json_path.read_text(encoding="utf-8"))
            assert "strategies" in data
            # At least some strategies should be found
            assert len(data["strategies"]) > 0

    def test_survivors_are_valid_subset(self):
        data_file = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
        if not data_file.exists():
            pytest.skip("dashboard_data.json not available")

        costs = load_transaction_costs()
        with open(data_file) as f:
            dashboard = json.load(f)
        picks = dashboard.get("picks", {}).get("recent_closed", [])
        rows = compute_strategy_stats(picks, costs)
        survivors = [r for r in rows if r["both_survive"] and r["n"] >= 10]
        for r in survivors:
            assert r["after_cost_mean_pnl_pct"] > 0
            assert r["wilson_lb_wr_pct"] >= 50.0
