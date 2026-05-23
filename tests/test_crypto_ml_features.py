"""
Tests for new P2 ML features: OI momentum + Garman-Klass volatility.

Covers:
  - test_oi_features_zero_fill_when_oi_missing
  - test_garman_klass_vol_positive
  - test_garman_klass_vol_gt_zero_for_real_ohlc
  - integration: new features appear in build_features output

Run:
    py -m pytest tests/test_crypto_ml_features.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_ml_edge.features.engine import (
    build_features,
    compute_oi_features,
    garman_klass_volatility,
    FEATURE_NAMES,
    WARMUP_BARS,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 500, seed: int = 42, freq: str = "1h") -> pd.DataFrame:
    """Synthetic OHLCV with realistic price dynamics."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    log_returns = rng.normal(0.0, 0.005, n)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    noise = rng.uniform(0.001, 0.005, n)
    high   = close * (1.0 + noise)
    low    = close * (1.0 - noise)
    open_  = close * (1.0 + rng.normal(0.0, 0.002, n))
    volume = np.abs(rng.normal(1_000_000.0, 200_000.0, n)) + 10_000.0
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low,
         "close": close, "volume": volume},
        index=dates,
    )
    df.index.name = "timestamp"
    return df


def _make_ohlcv_with_oi(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Synthetic OHLCV with an open_interest column."""
    rng = np.random.default_rng(seed)
    df = _make_ohlcv(n, seed=seed)
    # Realistic OI: starts at 1B, drifts with small random steps
    oi_base = 1_000_000_000.0
    oi_changes = rng.normal(0.0, 0.002, n)
    df["open_interest"] = oi_base * np.exp(np.cumsum(oi_changes))
    return df


# ---------------------------------------------------------------------------
# 1. OI momentum features
# ---------------------------------------------------------------------------

class TestOIFeatures:
    def test_oi_features_zero_fill_when_oi_missing(self):
        """DataFrame without open_interest column must get zeros, not raise."""
        df = _make_ohlcv(100)
        assert "open_interest" not in df.columns
        result = compute_oi_features(df)
        # Both new columns must exist and be exactly 0
        assert "oi_change_pct_4h" in result.columns, \
            "oi_change_pct_4h missing when open_interest absent"
        assert "oi_price_diverge" in result.columns, \
            "oi_price_diverge missing when open_interest absent"
        assert (result["oi_change_pct_4h"] == 0.0).all(), \
            "oi_change_pct_4h should be 0 when open_interest absent"
        assert (result["oi_price_diverge"] == 0).all(), \
            "oi_price_diverge should be 0 when open_interest absent"

    def test_oi_change_pct_4h_present_when_oi_provided(self):
        """When open_interest is available, oi_change_pct_4h should be non-trivial."""
        df = _make_ohlcv_with_oi(200)
        result = compute_oi_features(df)
        # After the first 4 bars the value should be non-zero (OI drifts)
        non_zero = result["oi_change_pct_4h"].iloc[4:].abs() > 0
        assert non_zero.any(), \
            "oi_change_pct_4h is all-zero even though open_interest was provided"

    def test_oi_price_diverge_is_binary(self):
        """oi_price_diverge must only contain 0 or 1."""
        df = _make_ohlcv_with_oi(300)
        result = compute_oi_features(df)
        unique = set(result["oi_price_diverge"].unique())
        assert unique.issubset({0, 1, 0.0, 1.0}), \
            f"oi_price_diverge has non-binary values: {unique}"

    def test_oi_features_in_build_features_output(self):
        """OI features must appear in FEATURE_NAMES and in build_features output."""
        assert "oi_change_pct_4h" in FEATURE_NAMES, \
            "oi_change_pct_4h not in FEATURE_NAMES"
        assert "oi_price_diverge" in FEATURE_NAMES, \
            "oi_price_diverge not in FEATURE_NAMES"
        df = _make_ohlcv(400)
        out = build_features(df)
        assert "oi_change_pct_4h" in out.columns
        assert "oi_price_diverge" in out.columns

    def test_oi_features_zero_in_build_features_without_oi_column(self):
        """build_features with OHLCV-only input zero-fills OI features."""
        df = _make_ohlcv(400)
        out = build_features(df)
        assert (out["oi_change_pct_4h"] == 0.0).all(), \
            "oi_change_pct_4h non-zero despite no open_interest in OHLCV"
        assert (out["oi_price_diverge"] == 0.0).all(), \
            "oi_price_diverge non-zero despite no open_interest in OHLCV"

    def test_compute_oi_does_not_mutate_input(self):
        """compute_oi_features must not mutate its input DataFrame."""
        df = _make_ohlcv(100)
        original_cols = list(df.columns)
        compute_oi_features(df)
        assert list(df.columns) == original_cols, \
            "compute_oi_features mutated the input DataFrame"


# ---------------------------------------------------------------------------
# 2. Garman-Klass volatility
# ---------------------------------------------------------------------------

class TestGarmanKlassVol:
    def test_garman_klass_vol_positive(self):
        """GK vol must always be >= 0 (non-negative by definition of sqrt)."""
        df = _make_ohlcv(500)
        gk = garman_klass_volatility(df, window=14)
        # Drop NaN (warm-up period) before asserting
        gk_clean = gk.dropna()
        assert (gk_clean >= 0.0).all(), \
            f"GK volatility has negative values: min={gk_clean.min():.6f}"

    def test_garman_klass_vol_gt_zero_for_real_ohlc(self):
        """With valid OHLC bars (H > L, non-zero prices), GK must be > 0."""
        df = _make_ohlcv(500)
        # Ensure high > low (guaranteed by construction, but assert anyway)
        assert (df["high"] > df["low"]).all(), "Test data invariant broken: high <= low"
        gk = garman_klass_volatility(df, window=14)
        gk_clean = gk.iloc[WARMUP_BARS:]
        assert (gk_clean > 0.0).all(), \
            f"GK vol not strictly positive; min={gk_clean.min():.6f}"

    def test_garman_klass_vol_finite(self):
        """GK vol must contain no NaN after warm-up and no Inf values."""
        df = _make_ohlcv(500)
        gk = garman_klass_volatility(df, window=14)
        gk_clean = gk.iloc[WARMUP_BARS:]
        assert not gk_clean.isna().any(), \
            "GK vol contains NaN after warm-up period"
        assert not np.isinf(gk_clean).any(), \
            "GK vol contains Inf"

    def test_garman_klass_vol_in_build_features(self):
        """gk_vol_14 must appear in FEATURE_NAMES and build_features output."""
        assert "gk_vol_14" in FEATURE_NAMES, "gk_vol_14 not in FEATURE_NAMES"
        df = _make_ohlcv(500)
        out = build_features(df)
        assert "gk_vol_14" in out.columns
        gk_clean = out["gk_vol_14"].iloc[WARMUP_BARS:]
        assert (gk_clean >= 0.0).all(), \
            "gk_vol_14 has negative values in build_features output"

    def test_garman_klass_vol_reasonable_magnitude(self):
        """Annualised GK vol for simulated data should be in a realistic range.

        Simulated bars have ~0.5% per-bar std; annualised for 1h bars
        that's ~0.5% * sqrt(8760) ≈ 46%.  A generous bound of [0.01, 500%]
        catches runaway or collapsed values.
        """
        df = _make_ohlcv(500)
        gk = garman_klass_volatility(df, window=14)
        gk_clean = gk.iloc[WARMUP_BARS:]
        assert gk_clean.mean() > 0.01, \
            f"GK vol mean={gk_clean.mean():.4f} suspiciously low"
        assert gk_clean.mean() < 5.0, \
            f"GK vol mean={gk_clean.mean():.4f} suspiciously high (>500%)"

    def test_garman_klass_different_window(self):
        """garman_klass_volatility should work with different window sizes."""
        df = _make_ohlcv(500)
        gk_7  = garman_klass_volatility(df, window=7)
        gk_28 = garman_klass_volatility(df, window=28)
        # Both should be non-negative after their respective warm-ups
        assert (gk_7.dropna()  >= 0.0).all()
        assert (gk_28.dropna() >= 0.0).all()
        # Shorter window → more volatile (higher std of gk values)
        assert gk_7.dropna().std() >= gk_28.dropna().std() * 0.5, \
            "Expected shorter GK window to produce more variable estimates"


# ---------------------------------------------------------------------------
# 3. Integration: feature count and column order unchanged
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_feature_count_still_in_budget(self):
        """Adding OI + GK features must not violate the 10-25 budget."""
        assert 10 <= len(FEATURE_NAMES) <= 25, \
            f"FEATURE_NAMES has {len(FEATURE_NAMES)} entries; must be 10-25"

    def test_build_features_column_order_matches_feature_names(self):
        """Output column order must exactly match FEATURE_NAMES."""
        df = _make_ohlcv(400)
        out = build_features(df)
        assert list(out.columns) == FEATURE_NAMES, \
            "Output columns do not match FEATURE_NAMES"

    def test_no_nan_after_warmup_with_new_features(self):
        """New features must not introduce NaN beyond the warm-up window."""
        df = _make_ohlcv(500)
        out = build_features(df)
        clean = out.iloc[WARMUP_BARS:]
        nan_cols = clean.columns[clean.isna().any()].tolist()
        assert not nan_cols, \
            f"NaN found after warm-up in columns: {nan_cols}"
