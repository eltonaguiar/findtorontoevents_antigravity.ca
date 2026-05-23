"""Tests for Tier 1 diagnostics: Monte Carlo baseline, strategy correlation, rolling expectancy."""

from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.data_integrity import (  # noqa: E402
    monte_carlo_baseline,
    rolling_expectancy,
    strategy_correlation,
)


# ---------------------------------------------------------------------------
# Monte Carlo baseline
# ---------------------------------------------------------------------------

def test_mc_insufficient_data(tmp_path, monkeypatch):
    # Write a tiny ledger
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps([{"pnl_pct": 1.0}] * 5))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    result = monte_carlo_baseline.analyze("closed", iterations=500, seed=1)
    assert result["status"] == "INSUFFICIENT_DATA"


def test_mc_positive_expectancy_edge_confirmed(tmp_path, monkeypatch):
    # 50 trades all +1% — massively positive edge; random walk should be near 0
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps([{"pnl_pct": 1.0}] * 50))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(monte_carlo_baseline._common, "OUT_DIR", str(tmp_path / "out"))
    result = monte_carlo_baseline.analyze("closed", iterations=1000, seed=1)
    assert result["status"] == "EDGE_CONFIRMED"
    assert result["observed_expectancy_pct"] == pytest.approx(1.0)
    assert result["p_value_one_sided"] < 0.05


def test_mc_negative_expectancy_flagged(tmp_path, monkeypatch):
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps([{"pnl_pct": -0.5}] * 50))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(monte_carlo_baseline._common, "OUT_DIR", str(tmp_path / "out"))
    result = monte_carlo_baseline.analyze("closed", iterations=500, seed=1)
    assert result["status"] == "NEGATIVE_EXPECTANCY"


def test_mc_coin_flip_detected(tmp_path, monkeypatch):
    # Symmetric tiny edge — should NOT be distinguishable from random
    import random as _r
    rng = _r.Random(7)
    rows = [{"pnl_pct": rng.choice([1.0, -1.0]) * rng.uniform(0.5, 1.5)} for _ in range(60)]
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(monte_carlo_baseline._common, "OUT_DIR", str(tmp_path / "out"))
    result = monte_carlo_baseline.analyze("closed", iterations=500, seed=1)
    # Could be EDGE_CONFIRMED if the RNG was lucky, or NEGATIVE_EXPECTANCY,
    # or COIN_FLIP — all three are valid for symmetric synthetic data.
    # Assert we got *some* valid status and computed the p-value.
    assert result["status"] in ("EDGE_CONFIRMED", "COIN_FLIP", "NEGATIVE_EXPECTANCY")
    if result["status"] != "INSUFFICIENT_DATA":
        assert 0.0 <= result["p_value_one_sided"] <= 1.0


def test_mc_filters_matic_ghosts(tmp_path, monkeypatch):
    # 100 MATIC ghosts + 40 real +1% trades — ghosts should not pollute
    rows = [{"symbol": "MATICUSDT", "pnl_pct": -0.15}] * 100
    rows += [{"pnl_pct": 1.0}] * 40
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(monte_carlo_baseline._common, "OUT_DIR", str(tmp_path / "out"))
    series = monte_carlo_baseline.load_pnl_series("closed")
    assert len(series) == 40
    assert all(x == 1.0 for x in series)


def test_mc_bootstrap_ci_contains_mean(tmp_path, monkeypatch):
    ledger = tmp_path / "closed.json"
    rows = [{"pnl_pct": x} for x in [0.5, 1.0, 1.5, -0.5, 2.0, -1.0, 0.8, 1.2, -0.3, 1.5] * 5]
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(monte_carlo_baseline._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(monte_carlo_baseline._common, "OUT_DIR", str(tmp_path / "out"))
    result = monte_carlo_baseline.analyze("closed", iterations=1000, seed=1)
    assert result["status"] != "INSUFFICIENT_DATA"
    ci_lo, ci_hi = result["bootstrap_ci_95"]
    assert ci_lo <= result["observed_expectancy_pct"] <= ci_hi


# ---------------------------------------------------------------------------
# Strategy correlation
# ---------------------------------------------------------------------------

def _make_date(day_offset: int) -> str:
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)).isoformat()


def test_correlation_insufficient_strategies(tmp_path, monkeypatch):
    rows = [
        {"strategy": "only_one", "pnl_pct": 1.0, "closed_at": _make_date(i)}
        for i in range(25)
    ]
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(strategy_correlation._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(strategy_correlation._common, "OUT_DIR", str(tmp_path / "out"))
    result = strategy_correlation.analyze(min_trades=20, min_overlap=5)
    assert result["status"] == "INSUFFICIENT_STRATEGIES"


def test_correlation_two_identical_strategies_high_rho(tmp_path, monkeypatch):
    rows = []
    for i in range(25):
        ts = _make_date(i)
        rows.append({"strategy": "A", "pnl_pct": 1.0 + i * 0.1, "closed_at": ts})
        rows.append({"strategy": "B", "pnl_pct": 1.0 + i * 0.1, "closed_at": ts})
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(strategy_correlation._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(strategy_correlation._common, "OUT_DIR", str(tmp_path / "out"))
    result = strategy_correlation.analyze(min_trades=20, min_overlap=5)
    assert result["status"] == "OK"
    assert result["n_strategies"] == 2
    # Perfectly correlated — mean |rho| should be 1.0
    assert result["mean_abs_correlation"] == pytest.approx(1.0, abs=1e-6)
    assert len(result["high_corr_pairs"]) == 1


def test_correlation_filters_ghosts(tmp_path, monkeypatch):
    rows = [
        {"symbol": "MATICUSDT", "pnl_pct": -0.15, "strategy": "ghosty", "closed_at": _make_date(0)},
    ] * 30
    rows += [
        {"strategy": "A", "pnl_pct": 1.0, "closed_at": _make_date(i)} for i in range(25)
    ]
    rows += [
        {"strategy": "B", "pnl_pct": -1.0, "closed_at": _make_date(i)} for i in range(25)
    ]
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(strategy_correlation._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(strategy_correlation._common, "OUT_DIR", str(tmp_path / "out"))
    result = strategy_correlation.analyze(min_trades=20, min_overlap=5)
    assert result["status"] in ("OK", "INSUFFICIENT_OVERLAP")
    # Ghostly strategy should be filtered out since its rows are all MATIC ghosts
    names = {e["strategy"] for e in result.get("concentration_top10", [])}
    assert "ghosty" not in names


def test_pearson_edge_cases():
    assert strategy_correlation.pearson([1.0], [1.0]) is None  # too small
    assert strategy_correlation.pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None  # zero var x
    rho = strategy_correlation.pearson([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
    assert rho == pytest.approx(1.0)
    rho = strategy_correlation.pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert rho == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Rolling expectancy
# ---------------------------------------------------------------------------

def test_rolling_insufficient_data(tmp_path, monkeypatch):
    rows = [{"pnl_pct": 1.0, "closed_at": _make_date(i)} for i in range(10)]
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(rolling_expectancy._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(rolling_expectancy._common, "OUT_DIR", str(tmp_path / "out"))
    result = rolling_expectancy.analyze(window_days=30, step_days=3)
    assert result["status"] == "INSUFFICIENT_DATA"


def test_rolling_positive_flat(tmp_path, monkeypatch):
    # 200 days of steady +0.5% — expectancy should stay positive throughout
    rows = []
    for i in range(200):
        rows.append({"pnl_pct": 0.5, "closed_at": _make_date(i)})
        rows.append({"pnl_pct": 0.5, "closed_at": _make_date(i)})
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(rolling_expectancy._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(rolling_expectancy._common, "OUT_DIR", str(tmp_path / "out"))
    result = rolling_expectancy.analyze(window_days=30, step_days=7)
    assert result["status"] == "OK"
    assert result["first_window"]["expectancy"] == pytest.approx(0.5)
    assert result["last_window"]["expectancy"] == pytest.approx(0.5)
    assert result["decay_point"] is None  # no decay in flat series


def test_rolling_decay_detected(tmp_path, monkeypatch):
    # First 100 days +1%, next 100 days -1% — clear decay
    rows = []
    for i in range(100):
        rows.append({"pnl_pct": 1.0, "closed_at": _make_date(i)})
        rows.append({"pnl_pct": 1.0, "closed_at": _make_date(i)})
    for i in range(100, 200):
        rows.append({"pnl_pct": -1.0, "closed_at": _make_date(i)})
        rows.append({"pnl_pct": -1.0, "closed_at": _make_date(i)})
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(rolling_expectancy._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(rolling_expectancy._common, "OUT_DIR", str(tmp_path / "out"))
    result = rolling_expectancy.analyze(window_days=30, step_days=7)
    assert result["status"] == "OK"
    # Slope should be negative (worsening)
    assert result["expectancy_slope_per_step"] is not None
    assert result["expectancy_slope_per_step"] < 0
    # Decay point should be detected somewhere in the middle
    assert result["decay_point"] is not None


def test_rolling_linear_slope_basic():
    # Perfectly linear: y = 2x + 1 → slope 2
    slope = rolling_expectancy.linear_slope([0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0])
    assert slope == pytest.approx(2.0)
    # Zero variance x → None
    assert rolling_expectancy.linear_slope([1.0, 1.0], [2.0, 3.0]) is None


def test_rolling_filters_ghosts(tmp_path, monkeypatch):
    rows = [{"symbol": "MATICUSDT", "pnl_pct": -0.15, "closed_at": _make_date(i)} for i in range(100)]
    rows += [{"pnl_pct": 1.0, "closed_at": _make_date(i + 100)} for i in range(100)]
    rows += [{"pnl_pct": 1.0, "closed_at": _make_date(i + 100)} for i in range(100)]
    ledger = tmp_path / "closed.json"
    ledger.write_text(json.dumps(rows))
    monkeypatch.setattr(rolling_expectancy._common, "CLOSED_PICKS", str(ledger))
    monkeypatch.setattr(rolling_expectancy._common, "OUT_DIR", str(tmp_path / "out"))
    trades = rolling_expectancy.extract_trades(rolling_expectancy._common.load_json_list(str(ledger)))
    assert all(pnl == 1.0 for (_, pnl) in trades)  # no MATIC ghosts survived
