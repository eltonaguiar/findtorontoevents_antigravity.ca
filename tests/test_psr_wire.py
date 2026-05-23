"""
Tests for PSR (Probabilistic Sharpe Ratio) wiring into calculate_smart_score.

Covers:
  1. ``alpha_engine.risk_metrics.psr`` raw API on synthetic returns.
  2. ``psr_points`` mapping for high-edge / coin-flip / negative-edge sources.
  3. n<MIN_TRADES_FOR_PSR fallback to caller-supplied legacy trust-tier points.
  4. End-to-end: calculate_smart_score uses PSR points when source has >=30
     closed trades, falls back to legacy trust tier when it does not.
"""

import numpy as np
import pytest

from alpha_engine import risk_metrics as rm
from alpha_engine.risk_metrics import (
    MIN_TRADES_FOR_PSR,
    psr,
    psr_for_source,
    psr_points,
    reset_psr_cache,
)


# ── Raw PSR API ─────────────────────────────────────────────────────────────

def test_psr_high_sharpe_returns_high_probability():
    """Strong positive-edge synthetic series should give PSR close to 1."""
    rng = np.random.default_rng(seed=42)
    # mean +0.5%, std 1.0% — annualised Sharpe ~7.9, well above target 0.
    returns = rng.normal(loc=0.005, scale=0.01, size=100)
    val = psr(returns, benchmark_sharpe=0.0)
    assert 0.95 <= val <= 1.0, f"expected high PSR, got {val}"


def test_psr_zero_mean_returns_near_half():
    """Truly zero-mean series should give PSR == 0.5 (no edge, no anti-edge).

    We center the noise to remove finite-sample drift in the mean — without
    this, even seed=7 produces a sample mean of ~-13 bps which the PSR math
    correctly reads as a strongly negative Sharpe and collapses to ~0.
    """
    rng = np.random.default_rng(seed=7)
    returns = rng.normal(loc=0.0, scale=0.01, size=200)
    returns = returns - returns.mean()  # force zero sample mean
    val = psr(returns, benchmark_sharpe=0.0)
    assert 0.45 <= val <= 0.55, f"expected ~0.5 PSR, got {val}"


def test_psr_negative_edge_returns_low_probability():
    """Negative-edge series should give PSR well below 0.5."""
    rng = np.random.default_rng(seed=11)
    returns = rng.normal(loc=-0.003, scale=0.01, size=150)
    val = psr(returns, benchmark_sharpe=0.0)
    assert val < 0.20, f"expected low PSR, got {val}"


def test_psr_handles_empty_input():
    """Empty input must not crash; returns 0.0."""
    assert psr([], benchmark_sharpe=0.0) == 0.0


def test_psr_handles_constant_input():
    """Zero-variance input returns 0.0 (degenerate Sharpe)."""
    val = psr([0.01] * 50, benchmark_sharpe=0.0)
    assert val == 0.0


# ── psr_points mapping ──────────────────────────────────────────────────────

def test_psr_points_anchors():
    """Verify the 0/0.5/0.8/0.95 anchors map to the documented points."""
    # Patch the cache directly so we don't depend on dashboard_data.json.
    rm._PSR_CACHE = {
        "src_zero": {"psr": 0.20, "n": 100},
        "src_half": {"psr": 0.50, "n": 100},
        "src_decent": {"psr": 0.80, "n": 100},
        "src_pub": {"psr": 0.95, "n": 100},
        "src_perfect": {"psr": 1.00, "n": 100},
    }
    rm._PSR_CACHE_BUILT_AT = float("inf")  # never refresh during this test

    try:
        assert psr_points("src_zero") == pytest.approx(0.0, abs=1e-6)
        assert psr_points("src_half") == pytest.approx(6.0, abs=1e-6)
        assert psr_points("src_decent") == pytest.approx(9.0, abs=1e-6)
        assert psr_points("src_pub") == pytest.approx(12.0, abs=1e-6)
        assert psr_points("src_perfect") == pytest.approx(12.0, abs=1e-6)
    finally:
        reset_psr_cache()


def test_psr_points_monotone():
    """Higher PSR -> more points across the full range."""
    rm._PSR_CACHE = {
        f"s_{i}": {"psr": p, "n": 100}
        for i, p in enumerate([0.1, 0.3, 0.5, 0.7, 0.85, 0.97])
    }
    rm._PSR_CACHE_BUILT_AT = float("inf")
    try:
        pts = [psr_points(f"s_{i}") for i in range(6)]
        assert pts == sorted(pts), f"expected monotone, got {pts}"
        # Bounded to [0, 12].
        assert all(0.0 <= p <= 12.0 for p in pts)
    finally:
        reset_psr_cache()


# ── n<MIN_TRADES_FOR_PSR fallback ───────────────────────────────────────────

def test_psr_for_source_returns_none_for_unknown_source():
    """Unknown source -> None (caller falls back)."""
    reset_psr_cache()
    rm._PSR_CACHE = {}  # explicitly empty, no rebuild
    rm._PSR_CACHE_BUILT_AT = float("inf")
    try:
        assert psr_for_source("does_not_exist") is None
    finally:
        reset_psr_cache()


def test_psr_points_uses_fallback_when_source_missing():
    """If source not in cache (n<30 path), psr_points returns fallback_pts."""
    rm._PSR_CACHE = {}
    rm._PSR_CACHE_BUILT_AT = float("inf")
    try:
        assert psr_points("brand_new_source", fallback_pts=10.0) == 10.0
        assert psr_points("brand_new_source", fallback_pts=0.0) == 0.0
    finally:
        reset_psr_cache()


def test_min_trades_constant_value():
    """The threshold constant must have the documented value (30)."""
    assert MIN_TRADES_FOR_PSR == 30


# ── End-to-end: calculate_smart_score uses PSR ──────────────────────────────

def test_calculate_smart_score_uses_psr_when_source_has_data():
    """A pick with a high-PSR source should score >= than the same pick on a low-PSR source.

    All other smart-score components are held constant — the only varying
    input is source_system, so any score delta proves the PSR component is wired.
    """
    from audit_trail.quality_gates import calculate_smart_score

    rm._PSR_CACHE = {
        "high_edge_src": {"psr": 0.95, "n": 100},   # -> 12 pts
        "weak_edge_src": {"psr": 0.30, "n": 100},   # ~1.2 pts
    }
    rm._PSR_CACHE_BUILT_AT = float("inf")

    base_pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "take_profit": 63000.0,   # +5% TP
        "stop_loss": 58800.0,     # -2% SL  -> R:R ≈ 2.5 (sweet-spot band)
        "score": 65,
        "confidence": 0.75,
        "asset_class": "CRYPTO",
        "trade_timeframe": "INTRADAY",
        "trust_tier": "UNKNOWN",  # ensures fallback isn't activated
        "trust_score": 0,
        "forward_wr": 55,
        "forward_trades": 12,
    }

    pick_high = dict(base_pick, source_system="high_edge_src")
    pick_low = dict(base_pick, source_system="weak_edge_src")

    try:
        score_high = calculate_smart_score(pick_high)
        score_low = calculate_smart_score(pick_low)
        assert score_high > score_low, (
            f"PSR wiring broken: high-edge source ({score_high}) "
            f"did not outscore low-edge source ({score_low})"
        )
        # The PSR delta between 0.95 and 0.30 should map to ~10+ points
        # difference (12.0 vs ~1.2).
        assert (score_high - score_low) >= 8.0
    finally:
        reset_psr_cache()


def test_calculate_smart_score_falls_back_when_source_unknown():
    """Pick with PROVEN trust tier and an unknown source should still
    receive the legacy 15-pt PROVEN bonus via the fallback path."""
    from audit_trail.quality_gates import calculate_smart_score

    rm._PSR_CACHE = {}
    rm._PSR_CACHE_BUILT_AT = float("inf")

    base = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "take_profit": 63000.0,
        "stop_loss": 58800.0,
        "score": 65,
        "confidence": 0.75,
        "asset_class": "CRYPTO",
        "trade_timeframe": "INTRADAY",
        "forward_wr": 55,
        "forward_trades": 12,
        "source_system": "tiny_n_source",
    }
    pick_proven = dict(base, trust_tier="PROVEN")
    pick_unknown_tier = dict(base, trust_tier="UNKNOWN", trust_score=0)

    try:
        score_proven = calculate_smart_score(pick_proven)
        score_unknown = calculate_smart_score(pick_unknown_tier)
        # Legacy fallback: PROVEN gets +15 (unless weak_edge), UNKNOWN gets +0.
        # So PROVEN must score strictly higher.
        assert score_proven > score_unknown
        assert (score_proven - score_unknown) >= 10.0
    finally:
        reset_psr_cache()
