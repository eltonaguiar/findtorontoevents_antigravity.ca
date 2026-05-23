"""Tests for tools/slippage_stress_test.py (B14)."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.slippage_stress_test import (
    _breakeven_multiplier,
    _bucket_stats,
    _label,
    _load_transaction_costs,
    _profit_factor,
    _render_markdown,
    _safe_pnl,
    run_stress_test,
)


# ---------------------------------------------------------------------------
# Unit tests: _safe_pnl
# ---------------------------------------------------------------------------

def test_safe_pnl_numeric():
    assert _safe_pnl({"pnl_pct": 5.0}) == 5.0


def test_safe_pnl_string_numeric():
    assert _safe_pnl({"pnl_pct": "3.14"}) == pytest.approx(3.14)


def test_safe_pnl_missing():
    assert _safe_pnl({}) is None


def test_safe_pnl_non_numeric():
    assert _safe_pnl({"pnl_pct": "n/a"}) is None


# ---------------------------------------------------------------------------
# Unit tests: _profit_factor
# ---------------------------------------------------------------------------

def test_profit_factor_normal():
    wins = [2.0, 3.0]
    losses = [-1.0]
    assert _profit_factor(wins, losses) == pytest.approx(5.0)


def test_profit_factor_all_wins_returns_inf():
    assert _profit_factor([1.0, 2.0], []) == math.inf


def test_profit_factor_no_trades_returns_none():
    assert _profit_factor([], []) is None


def test_profit_factor_all_losses():
    result = _profit_factor([], [-1.0, -2.0])
    assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Unit tests: _bucket_stats
# ---------------------------------------------------------------------------

def test_bucket_stats_basic_cost_deduction():
    # 3 picks at +2% each; base cost 0.30%, multiplier 1.0 → net each +1.70%
    stats = _bucket_stats([2.0, 2.0, 2.0], cost_pct=0.30, multiplier=1.0)
    assert stats["n"] == 3
    assert stats["wr_pct"] == pytest.approx(100.0)
    assert stats["sum_pnl_pct"] == pytest.approx(3 * (2.0 - 0.30))


def test_bucket_stats_2x_multiplier_doubles_cost():
    pnls = [1.0, -0.5]
    stats_1x = _bucket_stats(pnls, cost_pct=0.30, multiplier=1.0)
    stats_2x = _bucket_stats(pnls, cost_pct=0.30, multiplier=2.0)
    # 2× multiplier means 2× cost per trade → sum_pnl 0.30 lower per trade
    assert stats_2x["sum_pnl_pct"] == pytest.approx(stats_1x["sum_pnl_pct"] - 0.30 * 2)


def test_bucket_stats_empty():
    stats = _bucket_stats([], cost_pct=0.30, multiplier=1.0)
    assert stats["n"] == 0
    assert stats["wr_pct"] is None


def test_bucket_stats_strategy_flips_below_zero():
    # Paper WR 100% but tiny PnL: 5 picks at +0.10%; 2× cost 0.60% → all negative
    stats = _bucket_stats([0.10] * 5, cost_pct=0.30, multiplier=2.0)
    assert stats["wr_pct"] == pytest.approx(0.0)
    assert stats["sum_pnl_pct"] < 0


# ---------------------------------------------------------------------------
# Unit tests: _breakeven_multiplier
# ---------------------------------------------------------------------------

def test_breakeven_multiplier_basic():
    # paper_sum_pnl=3.0, base_cost=0.30, n=10 → 3.0/(0.30*10)=1.0
    assert _breakeven_multiplier(3.0, 0.30, 10) == pytest.approx(1.0)


def test_breakeven_multiplier_already_losing():
    # paper sum ≤ 0 → None (ALREADY_LOSING)
    assert _breakeven_multiplier(-1.0, 0.30, 10) is None
    assert _breakeven_multiplier(0.0, 0.30, 10) is None


def test_breakeven_multiplier_zero_n():
    assert _breakeven_multiplier(5.0, 0.30, 0) is None


def test_breakeven_multiplier_zero_cost():
    assert _breakeven_multiplier(5.0, 0.0, 10) is None


# ---------------------------------------------------------------------------
# Unit tests: _label
# ---------------------------------------------------------------------------

def test_label_already_losing():
    assert _label(-1.0, -2.0) == "ALREADY_LOSING"


def test_label_fails_2x():
    assert _label(5.0, -1.0) == "FAILS_2X"


def test_label_survives_2x():
    assert _label(5.0, 3.0) == "SURVIVES_2X"


# ---------------------------------------------------------------------------
# Unit tests: _load_transaction_costs
# ---------------------------------------------------------------------------

def test_load_transaction_costs_returns_dict():
    costs = _load_transaction_costs()
    assert isinstance(costs, dict)
    assert "CRYPTO" in costs
    assert isinstance(costs["CRYPTO"], float)
    assert 0 < costs["CRYPTO"] < 1.0  # percentage, not bps


def test_load_transaction_costs_crypto_value():
    costs = _load_transaction_costs()
    # CRYPTO should be 0.30% per transaction_costs.json
    assert costs["CRYPTO"] == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Integration test: run_stress_test with synthetic data
# ---------------------------------------------------------------------------

SYNTHETIC_DASHBOARD = {
    "picks": {
        "closed": [
            # Strategy A (CRYPTO): 10 trades, all +1.5% — survives 2× at 0.30% cost
            *[{"strategy": "strat_a", "asset_class": "CRYPTO", "pnl_pct": 1.5} for _ in range(10)],
            # Strategy B (CRYPTO): 10 trades, mix of +0.5% and -0.5%
            *[{"strategy": "strat_b", "asset_class": "CRYPTO", "pnl_pct": 0.5} for _ in range(5)],
            *[{"strategy": "strat_b", "asset_class": "CRYPTO", "pnl_pct": -0.5} for _ in range(5)],
            # Strategy C (EQUITY): 8 trades, all -2% — already losing
            *[{"strategy": "strat_c", "asset_class": "EQUITY", "pnl_pct": -2.0} for _ in range(8)],
            # Strategy D: 3 trades — below min_n=5
            *[{"strategy": "strat_d", "asset_class": "CRYPTO", "pnl_pct": 1.0} for _ in range(3)],
        ]
    }
}

SYNTHETIC_COSTS = {
    "version": "1.0",
    "costs": {
        "CRYPTO": {"cost_pct": 0.30, "cost_bps": 30},
        "EQUITY": {"cost_pct": 0.10, "cost_bps": 10},
    },
}


def _write_temp_json(data: dict, suffix: str = ".json") -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False
    )
    json.dump(data, f)
    f.flush()
    return Path(f.name)


@pytest.fixture()
def synthetic_env(tmp_path, monkeypatch):
    dash_path = _write_temp_json(SYNTHETIC_DASHBOARD)
    costs_path = _write_temp_json(SYNTHETIC_COSTS)
    monkeypatch.setattr("tools.slippage_stress_test.DASHBOARD_DATA", dash_path)
    monkeypatch.setattr("tools.slippage_stress_test.TRANSACTION_COSTS_FILE", costs_path)
    monkeypatch.setattr("tools.slippage_stress_test.REPORTS_DIR", tmp_path)
    return tmp_path


def test_run_stress_test_strat_a_survives(synthetic_env):
    result = run_stress_test(min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    assert strats["strat_a"]["status"] == "SURVIVES_2X"


def test_run_stress_test_strat_c_already_losing(synthetic_env):
    result = run_stress_test(min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    assert strats["strat_c"]["status"] == "ALREADY_LOSING"


def test_run_stress_test_strat_d_insufficient(synthetic_env):
    result = run_stress_test(min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    assert strats["strat_d"]["status"] == "INSUFFICIENT_DATA"


def test_run_stress_test_asset_class_filter(synthetic_env):
    result = run_stress_test(asset_class_filter="EQUITY", min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    # strat_a and strat_b are CRYPTO → filtered out
    assert "strat_a" not in strats
    assert "strat_c" in strats


def test_run_stress_test_summary_counts(synthetic_env):
    result = run_stress_test(min_n=5)
    s = result["summary"]
    # strat_a SURVIVES_2X, strat_c ALREADY_LOSING, strat_d INSUFFICIENT, strat_b ?
    assert s["survives_2x"] >= 1
    assert s["already_losing"] >= 1
    assert s["insufficient_data"] >= 1


def test_run_stress_test_paper_pnl_correct(synthetic_env):
    result = run_stress_test(min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    # strat_a: 10 × 1.5% = 15.0%
    assert strats["strat_a"]["paper"]["sum_pnl_pct"] == pytest.approx(15.0)


def test_run_stress_test_2x_cost_deducted(synthetic_env):
    result = run_stress_test(min_n=5)
    strats = {r["strategy"]: r for r in result["strategies"]}
    strat_a = strats["strat_a"]
    paper = strat_a["paper"]["sum_pnl_pct"]
    net_2x = strat_a["scenarios"]["2x_volume"]["sum_pnl_pct"]
    # 2× cost = 2 × 0.30% = 0.60% per trade × 10 = 6.0% total deduction
    assert net_2x == pytest.approx(paper - 0.60 * 10)


def test_run_stress_test_total_picks(synthetic_env):
    result = run_stress_test(min_n=5)
    # 10 + 10 + 8 + 3 = 31 total closed picks
    assert result["total_closed_picks_loaded"] == 31


def test_render_markdown_contains_header(synthetic_env):
    result = run_stress_test(min_n=5)
    md = _render_markdown(result)
    assert "# Slippage Stress Test" in md
    assert "Survives 2× volume" in md
    assert "SURVIVES_2X" not in md  # status codes should not bleed into prose


def test_run_stress_test_recent_closed_fallback(monkeypatch, tmp_path):
    """Verify tool works when 'picks.recent_closed' is used instead of 'picks.closed'."""
    dash = {
        "picks": {
            "recent_closed": [
                {"strategy": "s1", "asset_class": "CRYPTO", "pnl_pct": 2.0}
                for _ in range(6)
            ]
        }
    }
    costs_path = _write_temp_json(SYNTHETIC_COSTS)
    dash_path = _write_temp_json(dash)
    monkeypatch.setattr("tools.slippage_stress_test.DASHBOARD_DATA", dash_path)
    monkeypatch.setattr("tools.slippage_stress_test.TRANSACTION_COSTS_FILE", costs_path)
    monkeypatch.setattr("tools.slippage_stress_test.REPORTS_DIR", tmp_path)
    result = run_stress_test(min_n=5)
    assert result["total_closed_picks_loaded"] == 6
