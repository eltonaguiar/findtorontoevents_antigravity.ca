"""Tests for alpha_engine/commodity_bdi.py

All network calls are mocked — no live API calls.
"""
from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_bdi():
    """Reload module so cache is cleared between tests."""
    if "alpha_engine.commodity_bdi" in sys.modules:
        del sys.modules["alpha_engine.commodity_bdi"]
    import alpha_engine.commodity_bdi as m
    return m


# ---------------------------------------------------------------------------
# ROC → score mapping tests (pure function, no network)
# ---------------------------------------------------------------------------

def test_roc_strongly_positive_gives_high_score():
    """ROC > +5% → score in 75-90."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(0.10)  # +10%
    assert 75.0 <= score <= 90.0, f"Expected 75-90, got {score}"


def test_roc_mildly_positive_gives_mid_high_score():
    """ROC 0-+5% → score in 55-75."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(0.025)  # +2.5%
    assert 55.0 <= score <= 75.0, f"Expected 55-75, got {score}"


def test_roc_mildly_negative_gives_mid_low_score():
    """ROC -5% to 0% → score in 40-55."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(-0.025)  # -2.5%
    assert 40.0 <= score <= 55.0, f"Expected 40-55, got {score}"


def test_roc_strongly_negative_gives_low_score():
    """ROC < -5% → score in 10-40."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(-0.10)  # -10%
    assert 10.0 <= score <= 40.0, f"Expected 10-40, got {score}"


def test_roc_zero_gives_boundary_score():
    """ROC exactly 0 → should give 55 (boundary between mild positive and mild negative)."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(0.0)
    # At boundary: mildly positive branch gives 55 + 0/5*20 = 55
    assert score == 55.0, f"Expected 55.0 at ROC=0, got {score}"


def test_roc_at_plus5_boundary():
    """ROC exactly +5% → 75 (top of mild-positive range)."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(0.05)
    assert score == 75.0, f"Expected 75.0 at ROC=+5%, got {score}"


def test_roc_at_minus5_boundary():
    """ROC exactly -5% → 40 (bottom of mild-negative range)."""
    import alpha_engine.commodity_bdi as m
    score = m._roc_to_score(-0.05)
    assert score == 40.0, f"Expected 40.0 at ROC=-5%, got {score}"


# ---------------------------------------------------------------------------
# bdi_score: fail-open tests
# ---------------------------------------------------------------------------

def test_bdi_score_fail_open_no_key():
    """Returns 50.0 when no FRED API key available."""
    m = _reload_bdi()
    with patch.object(m, "_read_fred_key", return_value=None):
        score = m.bdi_score()
    assert score == 50.0


def test_bdi_score_fail_open_network_error():
    """Returns 50.0 on network error."""
    m = _reload_bdi()
    with patch.object(m, "_read_fred_key", return_value="fake_key"):
        with patch.object(m, "_fetch_bdi_roc", side_effect=Exception("timeout")):
            score = m.bdi_score()
    assert score == 50.0


def test_bdi_score_fail_open_none_roc():
    """Returns 50.0 when _fetch_bdi_roc returns None."""
    m = _reload_bdi()
    with patch.object(m, "_read_fred_key", return_value="fake_key"):
        with patch.object(m, "_fetch_bdi_roc", return_value=None):
            score = m.bdi_score()
    assert score == 50.0


# ---------------------------------------------------------------------------
# bdi_score: cache test
# ---------------------------------------------------------------------------

def test_bdi_score_cached_after_first_call():
    """Second call uses in-process cache without re-fetching."""
    m = _reload_bdi()
    call_count = 0

    def fake_fetch(lookback_days=7):
        nonlocal call_count
        call_count += 1
        return 0.08  # +8%

    with patch.object(m, "_read_fred_key", return_value="fake_key"):
        with patch.object(m, "_fetch_bdi_roc", side_effect=fake_fetch):
            s1 = m.bdi_score()
            s2 = m.bdi_score()

    assert call_count == 1, "Should only fetch once due to caching"
    assert s1 == s2


# ---------------------------------------------------------------------------
# stamp_pick tests
# ---------------------------------------------------------------------------

def test_stamp_pick_skips_non_commodity():
    """stamp_pick does nothing for non-COMMODITY picks."""
    import alpha_engine.commodity_bdi as m
    pick = {"asset_class": "EQUITY", "symbol": "AAPL"}
    result = m.stamp_pick(pick)
    assert "bdi_momentum_score" not in result


def test_stamp_pick_skips_ctf():
    """stamp_pick skips CT=F (soft commodity)."""
    import alpha_engine.commodity_bdi as m
    pick = {"asset_class": "COMMODITY", "symbol": "CT=F"}
    result = m.stamp_pick(pick)
    assert "bdi_momentum_score" not in result


def test_stamp_pick_skips_dba():
    """stamp_pick skips DBA (soft commodity ETF)."""
    import alpha_engine.commodity_bdi as m
    pick = {"asset_class": "COMMODITY", "symbol": "DBA"}
    result = m.stamp_pick(pick)
    assert "bdi_momentum_score" not in result


def test_stamp_pick_stamps_dbb():
    """stamp_pick stamps bdi_momentum_score for DBB (copper/metals)."""
    m = _reload_bdi()
    with patch.object(m, "bdi_score", return_value=78.5):
        pick = {"asset_class": "COMMODITY", "symbol": "DBB"}
        result = m.stamp_pick(pick)
    assert "bdi_momentum_score" in result
    assert result["bdi_momentum_score"] == 78.5


def test_stamp_pick_stamps_uso():
    """stamp_pick stamps bdi_momentum_score for USO (energy)."""
    m = _reload_bdi()
    with patch.object(m, "bdi_score", return_value=62.0):
        pick = {"asset_class": "COMMODITY", "symbol": "USO"}
        result = m.stamp_pick(pick)
    assert result["bdi_momentum_score"] == 62.0


def test_stamp_pick_fail_open_on_exception():
    """stamp_pick does not raise on internal errors; pick unchanged."""
    import alpha_engine.commodity_bdi as m
    pick = {"asset_class": "COMMODITY", "symbol": "DBB"}
    # Simulate internal error
    with patch.object(m, "bdi_score", side_effect=RuntimeError("boom")):
        result = m.stamp_pick(pick)
    # Should not raise and should not have the key
    assert "bdi_momentum_score" not in result


def test_stamp_pick_returns_pick_for_chaining():
    """stamp_pick returns the pick dict (chainable)."""
    m = _reload_bdi()
    with patch.object(m, "bdi_score", return_value=50.0):
        pick = {"asset_class": "COMMODITY", "symbol": "UNG"}
        result = m.stamp_pick(pick)
    assert result is pick
