"""Deterministic tests for the stop-fill overshoot measurement."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.stop_fill_overshoot import overshoot_stats  # noqa: E402


def _row(entry, stop, exit_price, pnl, asset_class="CRYPTO", status="STOPPED"):
    return {
        "entry_price": entry,
        "stop_loss": stop,
        "exit_price": exit_price,
        "pnl_pct": pnl,
        "status": status,
        "asset_class": asset_class,
    }


def test_normal_case_reports_planned_realized_and_overshoot():
    rows = [
        _row(100.0, 98.0, 97.0, -3.0),
        _row(100.0, 98.0, 98.0, -2.0),
    ]
    stats = overshoot_stats(rows)
    overall = stats["overall"]
    assert overall["n_stopped"] == 2
    assert overall["n_skipped"] == 0
    assert overall["n_exit_at_stop"] == 1
    assert overall["n_exit_off_stop"] == 1
    assert overall["mean_planned_risk_pct"] == 2.0
    assert overall["mean_realized_loss_pct"] == 2.5
    assert overall["mean_overshoot_pp"] == 0.5
    assert overall["median_planned_risk_pct"] == 2.0
    assert overall["median_realized_loss_pct"] == 2.5
    assert overall["median_overshoot_pp"] == 0.5
    assert set(stats["by_asset_class"]) == {"CRYPTO"}


def test_per_class_buckets_are_independent():
    rows = [
        _row(100.0, 98.0, 97.0, -3.0, asset_class="CRYPTO"),
        _row(50.0, 45.0, 44.0, -2.0, asset_class="EQUITY"),
    ]
    stats = overshoot_stats(rows)
    assert stats["by_asset_class"]["CRYPTO"]["mean_planned_risk_pct"] == 2.0
    assert stats["by_asset_class"]["EQUITY"]["mean_planned_risk_pct"] == 10.0
    assert stats["overall"]["n_stopped"] == 2


def test_zero_and_invalid_planned_risk_are_skipped():
    rows = [
        _row(100.0, 100.0, 99.0, -1.0),
        _row(-100.0, -102.0, -103.0, -1.0),
        _row(0.0, -1.0, 0.0, -1.0),
        _row(100.0, None, 99.0, -1.0),
        {"entry_price": 100.0, "stop_loss": 98.0, "pnl_pct": -2.0},
        "not a dict",
        _row(100.0, 98.0, 97.0, -3.0),
    ]
    overall = overshoot_stats(rows)["overall"]
    assert overall["n_stopped"] == 1
    assert overall["n_skipped"] == 6
    assert overall["mean_planned_risk_pct"] == 2.0
    assert overall["mean_realized_loss_pct"] == 3.0
    assert overall["mean_overshoot_pp"] == 1.0


def test_empty_input_reports_zero_counts_and_null_stats():
    stats = overshoot_stats([])
    overall = stats["overall"]
    assert overall["n_stopped"] == 0
    assert overall["n_skipped"] == 0
    assert overall["n_exit_at_stop"] == 0
    assert overall["n_exit_off_stop"] == 0
    for key in ("mean_planned_risk_pct", "mean_realized_loss_pct",
                "mean_overshoot_pp", "median_planned_risk_pct",
                "median_realized_loss_pct", "median_overshoot_pp"):
        assert overall[key] is None
    assert stats["by_asset_class"] == {}


def test_mean_and_median_are_distinct_statistics():
    rows = [_row(100.0, 99.0, 99.0, -1.0) for _ in range(4)]
    rows.append(_row(100.0, 90.0, 90.0, -10.0))
    overall = overshoot_stats(rows)["overall"]
    assert overall["mean_planned_risk_pct"] == 2.8
    assert overall["median_planned_risk_pct"] == 1.0
    assert overall["mean_realized_loss_pct"] == 2.8
    assert overall["median_realized_loss_pct"] == 1.0
    assert overall["mean_overshoot_pp"] == 0.0
    assert overall["median_overshoot_pp"] == 0.0


def test_exit_at_stop_uses_relative_tolerance():
    rows = [
        _row(100.0, 98.0, 98.0 + 1e-12, -2.0),
        _row(100.0, 98.0, 97.5, -2.5),
    ]
    overall = overshoot_stats(rows)["overall"]
    assert overall["n_exit_at_stop"] == 1
    assert overall["n_exit_off_stop"] == 1
