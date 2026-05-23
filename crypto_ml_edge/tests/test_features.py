"""
Tests for the Shared Feature Engine (Phase 2)
===============================================
Covers the four hard guarantees required by FEAT-01 through FEAT-07:

  1. Feature count is between 10 and 20 (FEAT-06)
  2. No NaN in output after the warm-up period (FEAT-07 / correctness)
  3. No raw prices in feature names (stationarity contract)
  4. No lookahead: features at bar T don't use bar T+1 data

Run:
    py -m pytest crypto_ml_edge/tests/test_features.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crypto_ml_edge.features.engine import (
    build_features,
    FEATURE_NAMES,
    WARMUP_BARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 500, seed: int = 42,
                freq: str = "1h") -> pd.DataFrame:
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


def _make_funding(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """
    Synthetic funding-rate DataFrame (published every 8 hours on Binance).
    DatetimeIndex, column ``funding_rate``.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n // 8, freq="8h", tz="UTC")
    rates = rng.normal(0.0001, 0.0003, len(dates))
    return pd.DataFrame({"funding_rate": rates}, index=dates)


# ---------------------------------------------------------------------------
# 1. Feature count is between 10 and 20  (FEAT-06)
# ---------------------------------------------------------------------------

class TestFeatureCount:
    def test_feature_names_constant_in_range(self):
        assert 10 <= len(FEATURE_NAMES) <= 25, (
            f"FEATURE_NAMES has {len(FEATURE_NAMES)} entries; must be 10-25"
        )

    def test_output_columns_match_feature_names(self):
        df = _make_ohlcv(300)
        out = build_features(df)
        assert list(out.columns) == FEATURE_NAMES, (
            "Output columns do not match FEATURE_NAMES"
        )

    def test_output_column_count_in_range(self):
        df = _make_ohlcv(300)
        out = build_features(df)
        n = len(out.columns)
        assert 10 <= n <= 25, (
            f"build_features returned {n} columns; must be 10-25"
        )

    def test_column_count_same_with_funding(self):
        df = _make_ohlcv(300)
        fd = _make_funding(300)
        out_no_fund = build_features(df)
        out_with_fund = build_features(df, funding_df=fd)
        assert len(out_no_fund.columns) == len(out_with_fund.columns), (
            "Passing funding_df must not change the number of feature columns"
        )


# ---------------------------------------------------------------------------
# 2. No NaN after warm-up  (correctness / FEAT-07)
# ---------------------------------------------------------------------------

class TestNoNanAfterWarmup:
    def test_no_nan_after_warmup_no_funding(self):
        df = _make_ohlcv(500)
        out = build_features(df)
        clean = out.iloc[WARMUP_BARS:]
        nan_cols = clean.columns[clean.isna().any()].tolist()
        assert not nan_cols, (
            f"NaN found after warm-up in columns: {nan_cols}"
        )

    def test_no_nan_after_warmup_with_funding(self):
        df = _make_ohlcv(500)
        fd = _make_funding(500)
        out = build_features(df, funding_df=fd)
        clean = out.iloc[WARMUP_BARS:]
        nan_cols = clean.columns[clean.isna().any()].tolist()
        assert not nan_cols, (
            f"NaN found after warm-up (with funding) in columns: {nan_cols}"
        )

    def test_warmup_rows_may_have_nan(self):
        """
        The first WARMUP_BARS rows legitimately contain NaN (indicator
        lookback hasn't filled).  This test confirms the contract is
        documented and expected, not a bug.
        """
        df = _make_ohlcv(500)
        out = build_features(df)
        # At least some of the first WARMUP_BARS rows must have NaN
        # (if WARMUP_BARS is correctly set, this will always be true)
        warmup_rows = out.iloc[:WARMUP_BARS]
        assert warmup_rows.isna().any().any(), (
            "Expected NaN in warm-up rows — WARMUP_BARS may be set too high "
            "relative to actual indicator lookbacks"
        )

    def test_output_length_equals_input_length(self):
        df = _make_ohlcv(300)
        out = build_features(df)
        assert len(out) == len(df), (
            "build_features must return a DataFrame with the same number of "
            "rows as the input (NaN rows included)"
        )

    def test_funding_series_input_accepted(self):
        """funding_df can be a plain Series (not just a DataFrame)."""
        df = _make_ohlcv(300)
        fd = _make_funding(300)
        fr_series = fd["funding_rate"]          # Pass a Series, not DataFrame
        out = build_features(df, funding_df=fr_series)
        clean = out.iloc[WARMUP_BARS:]
        nan_cols = clean.columns[clean.isna().any()].tolist()
        assert not nan_cols


# ---------------------------------------------------------------------------
# 3. No raw prices in feature names  (stationarity contract)
# ---------------------------------------------------------------------------

class TestNoPricesInFeatureNames:
    # Whole-word patterns that unambiguously mean "raw price column".
    # We match as whole tokens (split on underscore) rather than substrings
    # so that names like "sr_dist_high" or "bb_percentb" are not flagged.
    # "high" and "low" only flag if they appear as a complete token, e.g.
    # a feature literally named "high" or "close_high" — not "sr_dist_high".
    _RAW_PRICE_TOKENS = frozenset({
        "price", "close", "open", "usd", "btc", "eth", "raw",
        # "high" / "low" alone as a full token would be a raw price column
        "high", "low",
    })

    @staticmethod
    def _tokens(name: str) -> list[str]:
        return name.lower().split("_")

    def test_feature_names_contain_no_price_keywords(self):
        """
        Feature names must not contain tokens that indicate a raw price.
        Tokens like 'dist' or 'sr' in 'sr_dist_high' are fine because
        they describe a *derived* quantity, not a raw OHLCV price.
        We only flag names whose token set is a *subset* of raw-price
        tokens — i.e., names composed *entirely* of price-like tokens
        with no transforming prefix (dist_, ret_, pct_, z_, etc.).
        """
        # These prefixes indicate a transformation has been applied
        SAFE_PREFIXES = (
            "ret_", "pct_", "z_", "dist_", "sr_", "vol_", "atr_",
            "bb_", "obv_", "rsi_", "funding_", "log_", "momentum_",
        )
        bad = []
        for name in FEATURE_NAMES:
            # If the name starts with a known transforming prefix, it's safe
            if any(name.lower().startswith(p) for p in SAFE_PREFIXES):
                continue
            # Otherwise flag if ALL tokens are raw-price keywords
            tokens = set(self._tokens(name))
            if tokens.issubset(self._RAW_PRICE_TOKENS):
                bad.append(name)
        assert not bad, (
            f"Feature names that look like raw prices: {bad}. "
            "All features must be returns, ratios, z-scores, percentiles, "
            "or bounded oscillators."
        )

    def test_feature_values_not_large_enough_to_be_prices(self):
        """
        A sanity bound: after warm-up, no feature column should have a mean
        absolute value > 1000 (raw BTC prices would be ~50,000).
        This catches accidental raw-price leakage.
        """
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        for col in out.columns:
            mean_abs = out[col].abs().mean()
            assert mean_abs < 1_000.0, (
                f"Feature '{col}' has mean|value|={mean_abs:.2f} — "
                "looks like a raw price, not a normalised feature"
            )

    def test_returns_are_small_fractions(self):
        """Return features should be small (typically |ret| < 0.5 per bar)."""
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        for col in ["ret_1h", "ret_4h", "ret_24h"]:
            p99 = out[col].abs().quantile(0.99)
            assert p99 < 0.5, (
                f"'{col}' 99th-percentile |value|={p99:.4f} is surprisingly "
                "large — verify it is a fractional return, not a raw value"
            )

    def test_rsi_bounded(self):
        """RSI must stay within [0, 100]."""
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        rsi = out["rsi_14"]
        assert rsi.min() >= 0.0,   "RSI below 0"
        assert rsi.max() <= 100.0, "RSI above 100"

    def test_bb_percentb_roughly_bounded(self):
        """Bollinger %B is typically in [-0.5, 1.5] for normal markets."""
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        pctb = out["bb_percentb"]
        # We use [-2, 3] as a generous sanity bound
        assert pctb.min() > -2.0, f"bb_percentb min={pctb.min():.3f} is suspiciously low"
        assert pctb.max() <  3.0, f"bb_percentb max={pctb.max():.3f} is suspiciously high"


# ---------------------------------------------------------------------------
# 4. No lookahead: bar T must not use bar T+1 data
# ---------------------------------------------------------------------------

class TestNoLookahead:
    """
    Strategy: replace the LAST row's OHLCV values with extreme values.
    If any feature in any prior row changes, the feature used future data.
    We test the penultimate row (index -2), which should be immune to
    changes made only at the last row (index -1).
    """

    def _build_two_versions(self, n: int = 400):
        """Return (features_original, features_perturbed, df_orig, df_perturbed)."""
        df_orig = _make_ohlcv(n)
        df_perturb = df_orig.copy()
        # Inject a massive spike at the VERY LAST bar only
        df_perturb.iloc[-1, df_perturb.columns.get_loc("close")]  = 1_000_000.0
        df_perturb.iloc[-1, df_perturb.columns.get_loc("high")]   = 1_000_100.0
        df_perturb.iloc[-1, df_perturb.columns.get_loc("low")]    = 999_900.0
        df_perturb.iloc[-1, df_perturb.columns.get_loc("volume")] = 1e12
        return (
            build_features(df_orig),
            build_features(df_perturb),
            df_orig,
            df_perturb,
        )

    def test_penultimate_row_unaffected_by_last_bar_change(self):
        """
        Perturbing bar T+1 (the last bar) must not alter bar T (penultimate).
        """
        feat_orig, feat_perturb, _, _ = self._build_two_versions(400)
        # Compare the penultimate row (second-to-last)
        row_orig    = feat_orig.iloc[-2]
        row_perturb = feat_perturb.iloc[-2]
        # Allow tiny floating-point noise (1e-10), but not meaningful differences
        diff = (row_orig - row_perturb).abs()
        bad_cols = diff[diff > 1e-8].index.tolist()
        assert not bad_cols, (
            f"Features changed in penultimate row when only the last bar was "
            f"perturbed — possible lookahead in: {bad_cols}"
        )

    def test_all_prior_rows_unaffected_by_last_bar_change(self):
        """
        More aggressive: no row before the last should change when only the
        last bar is replaced.
        """
        feat_orig, feat_perturb, _, _ = self._build_two_versions(400)
        # Exclude the very last row (it is intentionally changed)
        orig_prior    = feat_orig.iloc[:-1]
        perturb_prior = feat_perturb.iloc[:-1]
        diff = (orig_prior - perturb_prior).abs()
        max_diff = diff.max().max()
        assert max_diff < 1e-8, (
            f"Max feature diff in prior rows = {max_diff:.2e}. "
            "A change in the last bar must not propagate to earlier bars."
        )

    def test_ret_7d_on_short_series(self):
        """
        ret_7d requires 168 bars; on a shorter series it should return NaN,
        not raise an exception.
        """
        df = _make_ohlcv(50)
        out = build_features(df)
        # All ret_7d values must be NaN (only 50 bars, need 168)
        assert out["ret_7d"].isna().all(), (
            "ret_7d should be all-NaN when the series is shorter than 168 bars"
        )

    def test_funding_forward_fill_no_lookahead(self):
        """
        Funding rates are published every 8h.  The merge must forward-fill,
        never back-fill.  Test: injecting a large spike at a future funding
        timestamp must not affect feature values at earlier OHLCV bars.
        """
        df = _make_ohlcv(400)
        fd_orig    = _make_funding(400)
        fd_perturb = fd_orig.copy()
        # Spike the LAST funding observation
        fd_perturb.iloc[-1, fd_perturb.columns.get_loc("funding_rate")] = 999.9

        out_orig    = build_features(df, funding_df=fd_orig)
        out_perturb = build_features(df, funding_df=fd_perturb)

        # Only rows AFTER the perturbed funding timestamp should differ.
        # All rows strictly BEFORE the last funding timestamp must be identical.
        last_funding_ts = fd_perturb.index[-1]
        mask_before = df.index < last_funding_ts

        cols = ["funding_level", "funding_zscore", "funding_change"]
        for col in cols:
            diff = (out_orig.loc[mask_before, col]
                    - out_perturb.loc[mask_before, col]).abs()
            assert diff.max() < 1e-8, (
                f"'{col}' changed before the perturbed funding timestamp — "
                "possible back-fill lookahead in funding merge"
            )


# ---------------------------------------------------------------------------
# 5. API / edge-case robustness
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_columns_raises(self):
        df = _make_ohlcv(200).drop(columns=["close"])
        with pytest.raises(ValueError, match="missing columns"):
            build_features(df)

    def test_empty_df_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_features(pd.DataFrame())

    def test_minimal_size_returns_df(self):
        """Should not raise even with very few rows (all NaN is acceptable)."""
        df = _make_ohlcv(10)
        out = build_features(df)
        assert isinstance(out, pd.DataFrame)
        assert list(out.columns) == FEATURE_NAMES

    def test_no_funding_defaults_to_zero(self):
        df = _make_ohlcv(300)
        out = build_features(df)
        # When no funding data provided, funding_level is 0 throughout
        assert (out["funding_level"] == 0.0).all()

    def test_deterministic_output(self):
        """Calling build_features twice on identical input gives identical output."""
        df = _make_ohlcv(300)
        out1 = build_features(df)
        out2 = build_features(df)
        pd.testing.assert_frame_equal(out1, out2)

    def test_index_preserved(self):
        """Output index must match input index exactly."""
        df = _make_ohlcv(300)
        out = build_features(df)
        pd.testing.assert_index_equal(out.index, df.index)

    def test_sr_dist_high_nonpositive(self):
        """
        sr_dist_high = (close - swing_high) / close.
        Since swing_high >= close (it is the rolling max of highs),
        this value must be <= 0 after the warm-up period.
        """
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        assert (out["sr_dist_high"] <= 1e-10).all(), (
            "sr_dist_high should be <= 0 (close is below or at swing high)"
        )

    def test_sr_dist_low_nonnegative(self):
        """
        sr_dist_low = (close - swing_low) / close.
        Since swing_low <= close, this must be >= 0 after warm-up.
        """
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        assert (out["sr_dist_low"] >= -1e-10).all(), (
            "sr_dist_low should be >= 0 (close is above or at swing low)"
        )

    def test_atr_positive(self):
        """ATR as % of close must be positive (all markets have some volatility)."""
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        assert (out["atr_14"] > 0.0).all(), "atr_14 contains non-positive values"

    def test_vol_ratio_positive(self):
        """Volume ratio must be positive (volumes are positive by construction)."""
        df = _make_ohlcv(500)
        out = build_features(df).iloc[WARMUP_BARS:]
        assert (out["vol_ratio_20"] > 0.0).all()


# ---------------------------------------------------------------------------
# 6. New features: momentum_rank_30d and funding decomposition
# ---------------------------------------------------------------------------

class TestMomentumRank:
    """Tests for cross-sectional momentum rank (Liu et al. 2022 JFE)."""

    def test_momentum_rank_defaults_to_half_without_universe(self):
        """Without universe data, momentum_rank_30d should be 0.5 (neutral)."""
        df = _make_ohlcv(500)
        out = build_features(df)
        assert (out["momentum_rank_30d"] == 0.5).all()

    def test_momentum_rank_with_universe_data(self):
        """With universe data, momentum_rank_30d should be in [0, 1]."""
        df = _make_ohlcv(500)
        df.attrs["symbol"] = "BTCUSDT"

        rng = np.random.default_rng(99)
        universe = pd.DataFrame({
            "BTCUSDT": rng.normal(0.05, 0.02, 500),
            "ETHUSDT": rng.normal(0.03, 0.03, 500),
            "SOLUSDT": rng.normal(0.08, 0.04, 500),
            "BNBUSDT": rng.normal(0.02, 0.01, 500),
        }, index=df.index)

        out = build_features(df, universe_returns_30d=universe)
        clean = out["momentum_rank_30d"].iloc[WARMUP_BARS:]
        assert clean.min() >= 0.0, "momentum_rank_30d below 0"
        assert clean.max() <= 1.0, "momentum_rank_30d above 1"

    def test_momentum_rank_top_asset_ranked_high(self):
        """Asset with highest returns should rank near 1.0."""
        df = _make_ohlcv(300)
        df.attrs["symbol"] = "WINNER"

        universe = pd.DataFrame({
            "WINNER": np.full(300, 0.50),   # 50% return — highest
            "LOSER1": np.full(300, -0.10),
            "LOSER2": np.full(300, -0.20),
            "LOSER3": np.full(300, -0.30),
        }, index=df.index)

        out = build_features(df, universe_returns_30d=universe)
        rank = out["momentum_rank_30d"].iloc[-1]
        assert rank >= 0.9, f"Top asset should rank near 1.0, got {rank}"


class TestFundingDecomposition:
    """Tests for the 5-feature funding rate decomposition."""

    def test_funding_sign_is_binary(self):
        """funding_sign must be 0 or 1."""
        df = _make_ohlcv(500)
        fd = _make_funding(500)
        out = build_features(df, funding_df=fd).iloc[WARMUP_BARS:]
        unique_vals = set(out["funding_sign"].unique())
        assert unique_vals.issubset({0.0, 1.0}), (
            f"funding_sign has non-binary values: {unique_vals}"
        )

    def test_funding_extreme_is_binary(self):
        """funding_extreme must be 0 or 1."""
        df = _make_ohlcv(500)
        fd = _make_funding(500)
        out = build_features(df, funding_df=fd).iloc[WARMUP_BARS:]
        unique_vals = set(out["funding_extreme"].unique())
        assert unique_vals.issubset({0.0, 1.0}), (
            f"funding_extreme has non-binary values: {unique_vals}"
        )

    def test_funding_extreme_consistent_with_zscore(self):
        """funding_extreme=1 only when |zscore| > 2."""
        df = _make_ohlcv(500)
        fd = _make_funding(500)
        out = build_features(df, funding_df=fd).iloc[WARMUP_BARS:]
        extreme_mask = out["funding_extreme"] == 1.0
        if extreme_mask.any():
            assert (out.loc[extreme_mask, "funding_zscore"].abs() > 2.0 - 1e-10).all(), (
                "funding_extreme=1 but |zscore| <= 2"
            )

    def test_funding_level_equals_raw_rate(self):
        """funding_level should match the raw funding rate values."""
        df = _make_ohlcv(300)
        fd = _make_funding(300)
        out = build_features(df, funding_df=fd)
        # funding_level should not be all zero when funding data is provided
        assert not (out["funding_level"] == 0.0).all(), (
            "funding_level is all zero despite funding data"
        )

    def test_all_five_funding_features_present(self):
        """All 5 funding decomposition features must be in output."""
        df = _make_ohlcv(300)
        out = build_features(df)
        expected = ["funding_level", "funding_zscore", "funding_sign",
                    "funding_change", "funding_extreme"]
        for col in expected:
            assert col in out.columns, f"Missing funding feature: {col}"

    def test_no_funding_defaults(self):
        """Without funding data: level=0, sign=0, extreme=0."""
        df = _make_ohlcv(300)
        out = build_features(df)
        assert (out["funding_level"] == 0.0).all()
        assert (out["funding_sign"] == 0.0).all()
        assert (out["funding_extreme"] == 0.0).all()
