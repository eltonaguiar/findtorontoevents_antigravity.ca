"""Tests for crypto_signal_engine.obiflow (M-040 OBI/OFI signal)."""
import pytest

from crypto_signal_engine.obiflow import (
    compute_obi,
    compute_ofi_zscore,
    evaluate_obi_signal,
)


def test_obi_all_bids():
    assert compute_obi(100, 0) == 1.0


def test_obi_all_asks():
    assert compute_obi(0, 100) == -1.0


def test_obi_balanced():
    assert compute_obi(50, 50) == 0.0


def test_obi_zero_volume():
    """Zero total volume should return 0, not raise ZeroDivisionError."""
    assert compute_obi(0, 0) == 0.0


def test_ofi_cold_start_returns_zero():
    """Less than 12 samples is cold-start; z-score must be 0."""
    assert compute_ofi_zscore([0.1]) == 0.0
    assert compute_ofi_zscore([0.1] * 11) == 0.0


def test_ofi_zscore_with_full_window():
    """An extreme last observation against a flat history gives z < -1."""
    history = [0.1] * 47 + [-2.0]  # last obs is a strong outlier
    z = compute_ofi_zscore(history)
    assert z < -1.0


def test_ofi_zscore_flat_returns_zero():
    """Flat history (zero std) should return 0, not raise."""
    history = [0.5] * 48
    assert compute_ofi_zscore(history) == 0.0


def test_evaluate_unavailable_fails_open():
    """When bid/ask are None, signal must be unavailable and blocked=False."""
    r = evaluate_obi_signal("BTCUSDT", None, None)
    assert r["blocked"] is False
    assert r["signal"] == "unavailable"
    assert r["obi"] is None


def test_evaluate_obi_signal_neutral(monkeypatch):
    """Single observation triggers cold-start; signal must be NEUTRAL, blocked=False."""
    monkeypatch.setenv("OBI_GATE_ENFORCE", "0")
    monkeypatch.setenv("OBI_SHADOW_LOG", "0")
    r = evaluate_obi_signal("ETHUSDT", bid_volume=60.0, ask_volume=40.0)
    assert r["signal"] == "NEUTRAL"
    assert r["blocked"] is False
    assert r["obi"] == pytest.approx(0.2, abs=1e-4)
