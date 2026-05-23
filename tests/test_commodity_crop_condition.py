"""Tests for alpha_engine/commodity_crop_condition.py

All network calls are mocked — no live API calls.
"""
from __future__ import annotations

import sys
import time
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_crop():
    """Reload module so caches are cleared between tests."""
    for key in list(sys.modules.keys()):
        if "commodity_crop_condition" in key:
            del sys.modules[key]
    import alpha_engine.commodity_crop_condition as m
    # Clear in-process cache
    m._in_process_cache.clear()
    return m


# ---------------------------------------------------------------------------
# z-score → score mapping tests (pure function, no network)
# ---------------------------------------------------------------------------

def test_z_below_minus1_5_gives_high_score():
    """crop_z < -1.5 → score in 75-90 (bullish: crop stress)."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(-2.0)
    assert 75.0 <= score <= 90.0, f"Expected 75-90, got {score}"


def test_z_between_minus1_5_and_zero_gives_mid_high_score():
    """crop_z in [-1.5, 0] → score in 55-75."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(-0.75)
    assert 55.0 <= score <= 75.0, f"Expected 55-75, got {score}"


def test_z_between_zero_and_plus1_5_gives_mid_low_score():
    """crop_z in [0, 1.5] → score in 40-55."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(0.75)
    assert 40.0 <= score <= 55.0, f"Expected 40-55, got {score}"


def test_z_above_plus1_5_gives_low_score():
    """crop_z > +1.5 → score in 10-40 (bearish: bumper crop)."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(2.0)
    assert 10.0 <= score <= 40.0, f"Expected 10-40, got {score}"


def test_z_zero_gives_55():
    """crop_z = 0 → score exactly 55 (boundary: mild-positive → mild-negative)."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(0.0)
    assert score == 55.0, f"Expected 55.0 at z=0, got {score}"


def test_z_minus1_5_boundary():
    """crop_z = -1.5 → score exactly 75 (boundary: bullish → mild-positive)."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(-1.5)
    assert score == 75.0, f"Expected 75.0 at z=-1.5, got {score}"


def test_z_plus1_5_boundary():
    """crop_z = +1.5 → score exactly 40 (boundary: mild-negative → bearish)."""
    import alpha_engine.commodity_crop_condition as m
    score = m._z_to_score(1.5)
    assert score == 40.0, f"Expected 40.0 at z=+1.5, got {score}"


# ---------------------------------------------------------------------------
# crop_condition_score: fail-open tests
# ---------------------------------------------------------------------------

def test_crop_score_fail_open_no_key():
    """Returns 50.0 when no USDA_NASS_API_KEY available."""
    m = _reload_crop()
    with patch.object(m, "_read_usda_key", return_value=None):
        with patch.object(m, "_load_cache", return_value=None):
            score = m.crop_condition_score()
    assert score == 50.0


def test_crop_score_fail_open_network_error():
    """Returns 50.0 on network error."""
    m = _reload_crop()
    with patch.object(m, "_read_usda_key", return_value="fake_key"):
        with patch.object(m, "_load_cache", return_value=None):
            with patch.object(m, "_fetch_usda_crop_data", side_effect=Exception("timeout")):
                score = m.crop_condition_score()
    assert score == 50.0


def test_crop_score_uses_cache():
    """Returns cached score without re-fetching."""
    m = _reload_crop()
    cached_payload = {
        "fetched_at": time.time(),
        "score": 82.5,
        "latest_z": -1.8,
        "row_count": 50,
    }
    with patch.object(m, "_load_cache", return_value=cached_payload):
        score = m.crop_condition_score()
    assert score == 82.5


def test_crop_score_computes_from_api():
    """Computes and caches score when API returns valid data."""
    m = _reload_crop()

    # Mock rows with crop stress (low G+E). Historical values vary so std > 0.
    mock_rows = [
        {"year": 2020, "week": 25, "ge_pct": 53.0},
        {"year": 2021, "week": 25, "ge_pct": 57.0},
        {"year": 2022, "week": 25, "ge_pct": 55.0},
        {"year": 2023, "week": 25, "ge_pct": 59.0},
        {"year": 2024, "week": 25, "ge_pct": 56.0},
        {"year": 2025, "week": 25, "ge_pct": 38.0},  # stressed year
    ]

    with patch.object(m, "_read_usda_key", return_value="fake_key"):
        with patch.object(m, "_load_cache", return_value=None):
            with patch.object(m, "_fetch_usda_crop_data", return_value=mock_rows):
                with patch.object(m, "_save_cache"):
                    score = m.crop_condition_score()

    # Stressed crop (below average) → score > 55
    assert score > 55.0, f"Expected score > 55 for stressed crop, got {score}"


# ---------------------------------------------------------------------------
# stamp_pick tests
# ---------------------------------------------------------------------------

def test_stamp_pick_only_ctf():
    """stamp_pick only stamps CT=F picks."""
    m = _reload_crop()
    with patch.object(m, "crop_condition_score", return_value=80.0):
        pick = {"symbol": "CT=F", "asset_class": "COMMODITY"}
        result = m.stamp_pick(pick)
    assert "crop_condition_score" in result
    assert result["crop_condition_score"] == 80.0


def test_stamp_pick_skips_non_ctf():
    """stamp_pick does nothing for non-CT=F picks."""
    import alpha_engine.commodity_crop_condition as m
    pick = {"symbol": "DBB", "asset_class": "COMMODITY"}
    result = m.stamp_pick(pick)
    assert "crop_condition_score" not in result


def test_stamp_pick_skips_equity():
    """stamp_pick does nothing for EQUITY picks even if symbol matches somehow."""
    import alpha_engine.commodity_crop_condition as m
    pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
    result = m.stamp_pick(pick)
    assert "crop_condition_score" not in result


def test_stamp_pick_fail_open_on_exception():
    """stamp_pick does not raise on internal errors; pick unchanged."""
    import alpha_engine.commodity_crop_condition as m
    pick = {"symbol": "CT=F", "asset_class": "COMMODITY"}
    with patch.object(m, "crop_condition_score", side_effect=RuntimeError("boom")):
        result = m.stamp_pick(pick)
    assert "crop_condition_score" not in result


def test_stamp_pick_returns_pick_for_chaining():
    """stamp_pick returns the pick dict (chainable)."""
    m = _reload_crop()
    with patch.object(m, "crop_condition_score", return_value=50.0):
        pick = {"symbol": "CT=F", "asset_class": "COMMODITY"}
        result = m.stamp_pick(pick)
    assert result is pick


# ---------------------------------------------------------------------------
# _compute_crop_z tests
# ---------------------------------------------------------------------------

def test_compute_crop_z_returns_none_on_empty():
    """Returns None when no rows provided."""
    import alpha_engine.commodity_crop_condition as m
    assert m._compute_crop_z([]) is None


def test_compute_crop_z_returns_none_insufficient_history():
    """Returns None when fewer than 2 same-week historical values."""
    import alpha_engine.commodity_crop_condition as m
    rows = [{"year": 2025, "week": 25, "ge_pct": 55.0}]
    assert m._compute_crop_z(rows) is None


def test_compute_crop_z_negative_for_low_ge():
    """z-score is negative when current G+E% is below historical average."""
    import alpha_engine.commodity_crop_condition as m
    # Historical values vary around ~65%, current 40% → z should be negative
    rows = [
        {"year": 2020, "week": 25, "ge_pct": 63.0},
        {"year": 2021, "week": 25, "ge_pct": 67.0},
        {"year": 2022, "week": 25, "ge_pct": 65.0},
        {"year": 2023, "week": 25, "ge_pct": 64.0},
        {"year": 2024, "week": 25, "ge_pct": 66.0},
        {"year": 2025, "week": 25, "ge_pct": 40.0},  # well below avg
    ]
    z = m._compute_crop_z(rows)
    assert z is not None
    assert z < 0.0, f"Expected negative z for low G+E, got {z}"


def test_compute_crop_z_positive_for_high_ge():
    """z-score is positive when current G+E% is above historical average."""
    import alpha_engine.commodity_crop_condition as m
    # Historical values vary around ~50%, current 75% → z should be positive
    rows = [
        {"year": 2020, "week": 25, "ge_pct": 48.0},
        {"year": 2021, "week": 25, "ge_pct": 52.0},
        {"year": 2022, "week": 25, "ge_pct": 50.0},
        {"year": 2023, "week": 25, "ge_pct": 49.0},
        {"year": 2024, "week": 25, "ge_pct": 51.0},
        {"year": 2025, "week": 25, "ge_pct": 75.0},  # well above avg
    ]
    z = m._compute_crop_z(rows)
    assert z is not None
    assert z > 0.0, f"Expected positive z for high G+E, got {z}"
