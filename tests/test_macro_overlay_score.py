"""Tests for alpha_engine.macro_overlay_score linear helper."""

from alpha_engine.macro_overlay_score import linear_macro_score_from_series


def test_linear_macro_empty_weights():
    assert linear_macro_score_from_series({"vix": 20}, {"weights": {}}) is None
    assert linear_macro_score_from_series({"vix": 20}, {"weights": None}) is None


def test_linear_macro_computes():
    doc = {"intercept": 1.0, "weights": {"vix": 0.1, "cpi_yoy": -0.05}}
    s = linear_macro_score_from_series({"vix": 10, "cpi_yoy": 2.0}, doc)
    assert s is not None
    assert abs(s - (1.0 + 1.0 + (-0.1))) < 1e-9
