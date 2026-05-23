"""
tests/test_crypto_ml_edge_data_fetcher_failover.py
==================================================
Schema-validation integration tests for crypto_ml_edge.data_fetcher functions
post-migration to alpha_engine.failover_imports.

Per Inception code review on Plan 1: silent zero-pick days are the dominant
failure mode. Each test mocks the failover module returning known-good data
and asserts the caller produces output with the expected DataFrame columns/types.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def good_klines():
    # Binance shape: [ts_ms, o, h, l, c, v, ct, qv, n, tbb, tbq, ig] -- 30 bars
    base_ts = 1700000000000
    return [
        [base_ts + i * 3600000, "100.0", "101.0", "99.0", "100.5",
         "1234.5", base_ts + (i + 1) * 3600000 - 1, "123450", 100, "600", "60000", "0"]
        for i in range(30)
    ]


@pytest.fixture
def good_tickers():
    return [
        {"symbol": "BTCUSDT", "lastPrice": "65432.10",
         "priceChange": "0", "priceChangePercent": "0.19",
         "volume": "10000", "quoteVolume": "650000000"},
        {"symbol": "ETHUSDT", "lastPrice": "3210.50",
         "priceChange": "0", "priceChangePercent": "-0.45",
         "volume": "5000", "quoteVolume": "16000000"},
        {"symbol": "SOLUSDT", "lastPrice": "145.22",
         "priceChange": "0", "priceChangePercent": "1.34",
         "volume": "20000", "quoteVolume": "2900000"},
        {"symbol": "ADAUSDT", "lastPrice": "0.4523",
         "priceChange": "0", "priceChangePercent": "-0.12",
         "volume": "100000", "quoteVolume": "45000"},
        {"symbol": "DOGEUSDT", "lastPrice": "0.0823",
         "priceChange": "0", "priceChangePercent": "2.10",
         "volume": "500000", "quoteVolume": "41000"},
    ]


class TestSingleFetchKlines:
    """_single_fetch_klines -> pd.DataFrame[open, high, low, close, volume, quote_volume]"""

    def test_returns_correct_dataframe_schema_via_failover(self, good_klines):
        from crypto_ml_edge import data_fetcher as df_mod

        with patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_klines", return_value=good_klines):
            df = df_mod._single_fetch_klines("BTCUSDT", "1h", 30)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert len(df) == 30
        expected_cols = {"open", "high", "low", "close", "volume", "quote_volume"}
        assert set(df.columns) == expected_cols
        for col in expected_cols:
            assert df[col].dtype == float
        # Index is datetime
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_returns_empty_dataframe_on_total_failure(self):
        from crypto_ml_edge import data_fetcher as df_mod

        with patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_klines", return_value=[]), \
             patch("requests.get", side_effect=Exception("blocked")), \
             patch.object(df_mod, "_HAS_SHARED_FETCHER", False):
            df = df_mod._single_fetch_klines("BTCUSDT", "1h", 30)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_handles_short_row_padding(self):
        """Failover may return rows with <12 cols; caller pads to Binance shape."""
        from crypto_ml_edge import data_fetcher as df_mod
        # 6-col rows (alpha_engine.crypto_data_failover spec)
        short_klines = [
            [1700000000000 + i * 3600000, "100", "101", "99", "100.5", "1234"]
            for i in range(20)
        ]
        with patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_klines", return_value=short_klines):
            df = df_mod._single_fetch_klines("ETHUSDT", "1h", 20)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20
        assert "close" in df.columns


class TestFetchCurrentFundingRates:
    """fetch_current_funding_rates -> {symbol: float}"""

    def test_failover_path_returns_correct_schema(self):
        from crypto_ml_edge import data_fetcher as df_mod

        rate_map = {
            "BTCUSDT": -0.0001,
            "ETHUSDT": 0.00005,
            "SOLUSDT": -0.0003,
        }

        def fake_funding(sym):
            return rate_map.get(sym)

        # Force direct Binance to fail so failover path executes
        with patch("requests.get", side_effect=Exception("blocked")), \
             patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_funding_rate", side_effect=fake_funding):
            rates = df_mod.fetch_current_funding_rates(
                ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            )

        assert isinstance(rates, dict)
        assert set(rates.keys()) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
        for sym, rate in rates.items():
            assert isinstance(sym, str)
            assert isinstance(rate, float)
        assert rates["BTCUSDT"] == -0.0001

    def test_returns_empty_dict_when_all_sources_fail(self):
        from crypto_ml_edge import data_fetcher as df_mod

        with patch("requests.get", side_effect=Exception("blocked")), \
             patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_funding_rate", return_value=None):
            rates = df_mod.fetch_current_funding_rates(["BTCUSDT", "ETHUSDT"])

        assert rates == {}


class TestGetTopPairsByVolume:
    """get_top_pairs_by_volume -> list[str] (Binance-shape symbols)"""

    def test_failover_returns_sorted_top_pairs(self, good_tickers):
        from crypto_ml_edge import data_fetcher as df_mod

        candidates = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
        with patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_tickers_24h",
                          return_value=(good_tickers, "kucoin")), \
             patch.object(df_mod, "MIN_24H_VOLUME_USD", 0):
            top = df_mod.get_top_pairs_by_volume(n=3, candidates=candidates)

        assert isinstance(top, list)
        assert len(top) == 3
        for sym in top:
            assert isinstance(sym, str)
            assert sym in candidates
        # BTC has highest quoteVolume (650M) -> should be first
        assert top[0] == "BTCUSDT"

    def test_falls_back_to_default_pairs_when_all_fail(self):
        from crypto_ml_edge import data_fetcher as df_mod

        with patch.object(df_mod, "_HAS_AE_FAILOVER", True), \
             patch.object(df_mod, "_ae_fetch_tickers_24h",
                          return_value=([], "none")), \
             patch("requests.get", side_effect=Exception("blocked")):
            top = df_mod.get_top_pairs_by_volume(n=3)

        assert isinstance(top, list)
        assert len(top) == 3
        # DEFAULT_PAIRS fallback
        for sym in top:
            assert isinstance(sym, str)
