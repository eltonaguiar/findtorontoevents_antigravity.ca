"""Tests for the combiner + pre-registered vol-cap selection rule."""
from combined_book import combiner


def test_inverse_vol_weights_sum_to_one():
    vols = {"a": 0.20, "b": 0.10}
    w = combiner.inverse_vol_weights(vols)
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["a"] < w["b"]  # lower vol gets more weight


def test_apply_per_sleeve_cap_clips_and_renormalizes():
    weights = {"a": 0.6, "b": 0.2, "c": 0.2}
    capped = combiner.apply_per_sleeve_cap(weights, cap=0.40)
    assert all(v <= 0.40 + 1e-9 for v in capped.values())
    assert abs(sum(capped.values()) - 1.0) < 1e-6


def test_max_drawdown_computed_correctly():
    eq = [1.0, 1.2, 0.9, 1.1]
    assert abs(combiner.max_drawdown(eq) - (0.9 / 1.2 - 1.0)) < 1e-9


def test_select_vol_cap_picks_5_when_6_breaks():
    pre = {0.06: -0.165, 0.05: -0.144}
    assert combiner.select_vol_cap(pre) == 0.05


def test_select_vol_cap_picks_highest_viable():
    pre = {0.10: -0.12, 0.08: -0.10, 0.05: -0.08}
    assert combiner.select_vol_cap(pre) == 0.10
