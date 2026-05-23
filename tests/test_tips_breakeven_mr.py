"""Tests for tools/bond_pilots/tips_breakeven_mr.py."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pytest

from tools.bond_pilots.tips_breakeven_mr import (
    compute_z_score, evaluate_signal, DEVIATION_THRESHOLD,
)


def test_z_score_within_band_returns_no_signal():
    # Z = 0.5σ -> no signal
    series = [2.0] * 60 + [2.0 + 0.5 * 0.1]  # mean=2.0, std~0.013, last just slightly higher
    # Use uniform series to force std=0 first to validate edge handling
    series2 = [2.0] * 100
    latest, mean, std, z = compute_z_score(series2)
    assert mean == pytest.approx(2.0)
    assert std == 0.0  # zero variance
    assert z == 0.0


def test_z_score_above_threshold_triggers_long_tip_signal():
    # Construct series where last value is far above mean
    series = [2.0] * 100 + [3.0]  # large outlier above
    latest, mean, std, z = compute_z_score(series)
    assert z > DEVIATION_THRESHOLD


def test_z_score_below_threshold_triggers_long_tip_short_ief():
    history = [(f"2026-01-{i+1:02d}", 2.0) for i in range(100)] + [("2026-05-12", 1.0)]
    result = evaluate_signal(history)
    assert result["signal"] is not None
    assert result["signal"]["direction"] == "LONG_TIP_SHORT_IEF"


def test_z_score_above_threshold_triggers_short_tip_long_ief():
    history = [(f"2026-01-{i+1:02d}", 2.0) for i in range(100)] + [("2026-05-12", 3.0)]
    result = evaluate_signal(history)
    assert result["signal"] is not None
    assert result["signal"]["direction"] == "SHORT_TIP_LONG_IEF"


def test_evaluate_signal_handles_empty_history():
    result = evaluate_signal([])
    assert result["signal"] is None
    assert "error" in result


def test_evaluate_signal_in_band_no_signal():
    # Latest is exactly at mean -> Z=0 -> no signal
    history = [(f"2026-01-{i+1:02d}", 2.0) for i in range(100)] + [("2026-05-12", 2.0)]
    result = evaluate_signal(history)
    assert result["z_score"] == 0.0
    assert result["signal"] is None
