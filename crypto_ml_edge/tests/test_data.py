"""
Tests for Data Foundation (Phase 1)
====================================
Verify: no lookahead, stationarity, cache, data quality.
Run: py -m pytest crypto_ml_edge/tests/test_data.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# Test with synthetic data to avoid API calls
def _make_ohlcv(n: int = 100, start: str = "2024-01-01") -> pd.DataFrame:
    """Create synthetic OHLCV for testing."""
    dates = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2
    volume = np.abs(np.random.randn(n) * 1000) + 100

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    }, index=dates)
    df.index.name = "timestamp"
    return df


class TestDataQuality:
    def test_valid_ohlcv_passes(self):
        from crypto_ml_edge.data_quality import validate_ohlcv
        df = _make_ohlcv()
        warnings = validate_ohlcv(df, "TEST")
        # Should pass without critical errors (warnings are OK)
        assert isinstance(warnings, list)

    def test_empty_df_fails(self):
        from crypto_ml_edge.data_quality import validate_ohlcv, DataQualityError
        with pytest.raises(DataQualityError, match="empty"):
            validate_ohlcv(pd.DataFrame(), "TEST")

    def test_missing_columns_fails(self):
        from crypto_ml_edge.data_quality import validate_ohlcv, DataQualityError
        df = _make_ohlcv().drop(columns=["close"])
        with pytest.raises(DataQualityError, match="Missing columns"):
            validate_ohlcv(df, "TEST")

    def test_high_below_low_fails(self):
        from crypto_ml_edge.data_quality import validate_ohlcv, DataQualityError
        df = _make_ohlcv()
        df.iloc[10, df.columns.get_loc("high")] = df.iloc[10]["low"] - 1
        with pytest.raises(DataQualityError, match="high < low"):
            validate_ohlcv(df, "TEST")

    def test_clean_removes_duplicates(self):
        from crypto_ml_edge.data_quality import clean_ohlcv
        df = _make_ohlcv()
        # Introduce a duplicate
        dup = pd.concat([df, df.iloc[[5]]])
        cleaned = clean_ohlcv(dup)
        assert not cleaned.index.has_duplicates

    def test_no_lookahead_passes_correct_data(self):
        from crypto_ml_edge.data_quality import assert_no_lookahead
        df = _make_ohlcv()
        features = df[["open", "high", "low", "volume"]]
        labels = df["close"].shift(-1).dropna()  # Future close as label
        # This should pass — features don't contain the label column
        assert_no_lookahead(features, labels)

    def test_no_lookahead_catches_label_in_features(self):
        from crypto_ml_edge.data_quality import assert_no_lookahead, DataQualityError
        df = _make_ohlcv()
        features = df.copy()
        features["label"] = 1  # Label column in features = lookahead!
        labels = pd.Series(1, index=df.index)
        with pytest.raises(DataQualityError, match="lookahead"):
            assert_no_lookahead(features, labels)


class TestStationarity:
    def test_pct_returns_is_stationary(self):
        from crypto_ml_edge.stationarity import pct_returns, verify_stationarity
        df = _make_ohlcv(500)
        returns = pct_returns(df["close"])
        assert len(returns) == len(df) - 1
        assert verify_stationarity(returns)

    def test_log_returns(self):
        from crypto_ml_edge.stationarity import log_returns
        df = _make_ohlcv()
        lr = log_returns(df["close"])
        assert len(lr) == len(df) - 1
        assert not lr.isna().any()

    def test_frac_diff_produces_output(self):
        from crypto_ml_edge.stationarity import fractional_diff
        df = _make_ohlcv(500)
        fd = fractional_diff(df["close"], d=0.4)
        assert len(fd) > 0
        assert not fd.isna().any()

    def test_make_stationary_no_raw_prices(self):
        from crypto_ml_edge.stationarity import make_stationary
        df = _make_ohlcv(500)
        result = make_stationary(df, method="pct_returns")
        # All price columns should be returns, not raw prices
        # Returns should be small (near zero mean), not large (near 100)
        for col in ["open", "high", "low", "close"]:
            assert abs(result[col].mean()) < 1.0, f"{col} looks like raw prices"

    def test_raw_prices_are_not_stationary(self):
        from crypto_ml_edge.stationarity import verify_stationarity
        df = _make_ohlcv(500)
        # Raw prices with trend should NOT be stationary
        trending = pd.Series(np.cumsum(np.ones(500) * 0.1))
        assert not verify_stationarity(trending)


class TestConfig:
    def test_pairs_exist(self):
        from crypto_ml_edge.config import DEFAULT_PAIRS, CANDIDATE_PAIRS
        assert len(DEFAULT_PAIRS) == 10
        assert len(CANDIDATE_PAIRS) >= 10
        assert all(p.endswith("USDT") for p in DEFAULT_PAIRS)

    def test_cost_model(self):
        from crypto_ml_edge.config import get_total_cost
        cost_btc = get_total_cost("BTCUSDT")
        cost_small = get_total_cost("INJUSDT")
        # BTC should have lower total cost than small-cap
        assert cost_btc < cost_small
        # All costs should be positive and reasonable (< 1%)
        assert 0 < cost_btc < 0.01
        assert 0 < cost_small < 0.01

    def test_timeframes(self):
        from crypto_ml_edge.config import TIMEFRAMES
        assert "1h" in TIMEFRAMES
        assert "4h" in TIMEFRAMES
        assert TIMEFRAMES["1h"]["bars_per_year"] == 8760

    def test_validation_gates(self):
        from crypto_ml_edge.config import MIN_DSR_PROBABILITY, MAX_MODEL_VARIANTS
        assert MIN_DSR_PROBABILITY == 0.95
        assert MAX_MODEL_VARIANTS == 10


class TestGapReport:
    def test_no_gaps(self):
        from crypto_ml_edge.data_quality import compute_gap_report
        df = _make_ohlcv(100)
        report = compute_gap_report(df, "1h")
        assert report.empty

    def test_detects_gap(self):
        from crypto_ml_edge.data_quality import compute_gap_report
        df = _make_ohlcv(100)
        # Remove 5 bars to create a gap
        df = df.drop(df.index[50:55])
        report = compute_gap_report(df, "1h")
        assert len(report) > 0
